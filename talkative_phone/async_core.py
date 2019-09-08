# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-08-23 17:30:42
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-08 22:12:00
import asyncio
import base64
import binascii
import hashlib
import hmac
import logging
import struct
import threading

from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.PublicKey import RSA
from dynaconf import settings
from PyQt5.QtCore import QByteArray, QObject, pyqtSignal

from db import Chat, DBManager, User
from db import database_lock as db_lock
from descriptors import PortDescr
from errors import ContactExists
from jim_mes import Message
# from .metaclasses import ClientVerifier

app_name = 'client_phone'
logger = logging.getLogger(app_name)


class ClientTransport(threading.Thread):
    """[summary].

    [description]

    """
    port = PortDescr()
    update = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.started = False
        self._observers = {}
        self.auth = {}
        self.transport = None
        self.protocol = None
        self.router = router.init(self)
        self.decrypter = PKCS1_OAEP.new(RSA.import_key(settings.get('USER_KEY')))

    async def async_start(self):
        self.loop = asyncio.get_running_loop()
        self.on_con_lost = self.loop.create_future()
        self.transport, self.protocol = await self.loop.create_connection(
            lambda: AsyncClientProtocol(self),
            settings.get('HOST'),
            settings.as_int('PORT'),
        )

        # Wait until the protocol signals that the connection
        # is lost and close the transport.
        try:
            await self.on_con_lost
        except KeyboardInterrupt:
            logger.debug('closed')
        except Exception as error:
            logger.error(error, exc_info=True)
        finally:
            logger.debug('stoped')
            self.transport.close()

    def run(self):
        self.database = DBManager('client')
        self.notify('init_db')
        try:
            asyncio.run(self.async_start())
        except Exception as e:
            logger.error(e, exc_info=True)
            # import ipdb; ipdb.set_trace()
            self.notify('fail', msg=str(e))

    def is_alive(self):
        return self.started

    def notify(self, event, proto=None, msg=None, **kwargs):
        logger.info(f'Свершилось событие {event}')
        obs = self._observers.get(event, []) or []
        kwargs['event'] = event
        kwargs['thread'] = self
        protocol = proto or self.protocol
        for observer in obs:
            if isinstance(observer, QObject):
                self.update.emit({**{'proto': protocol, 'msg': msg}, **kwargs})
            else:
                observer.update(proto=protocol, msg=msg, **kwargs)

    def attach(self, observer, event):
        obs = self._observers.get(event, []) or []
        obs.append(observer)
        self._observers[event] = obs
        logger.info(f'{observer} подписался на событие {event}')

    def detach(self, observer, event):
        obs = self._observers.get(event, []) or []
        obs.remove(observer)
        self._observers[event] = obs
        logger.info(f'{observer} отписался от события {event}')

    def run_command(self, proto, mes):
        action = getattr(mes, settings.ACTION, None) or getattr(mes, settings.RESPONSE, None)
        if action:
            self.notify(action, proto, mes)
        else:
            logger.debug(f'Пустая команда {action}')


class AsyncClientProtocol(asyncio.Protocol):

    CHUNK_SIZE = 4

    def __init__(self, thread, *args, **kwargs):
        self._thread = thread
        super().__init__(*args, **kwargs)

    def connection_made(self, transport):
        self.transport = transport
        user = User.by_name(settings.USER_NAME)
        hash_ = binascii.hexlify(hashlib.pbkdf2_hmac(
            'sha512',
            settings.get('password').encode('utf-8'),
            settings.USER_NAME.encode('utf-8'),
            10000,
        ))
        if user:
            user.password = settings.get('password')
            user.auth_key = hash_
            user.active = False
        else:
            user = User(username=settings.USER_NAME, password=settings.get('password'), auth_key=hash_)
        with db_lock:
            user.save()
        logger.debug('Установлено соединение с сервером.')

        self.write(Message.presence())
        self.def_size, self.transport.max_size, self.cur_size = self.transport.max_size, self.CHUNK_SIZE, self.CHUNK_SIZE
        self._thread.notify('new_connect')
        self.long_data = b''

    def data_received(self, data):
        if len(data) == self.CHUNK_SIZE:
            self.cur_size = struct.unpack('>I', data)[0]
            self.transport.max_size = min(self.cur_size, self.def_size)
            return
        self.long_data += data

        if self.cur_size > len(self.long_data):
            return

        self.transport.max_size = self.cur_size = self.CHUNK_SIZE
        if len(self.long_data) < 1024:
            logger.debug(f'Server say: {self.long_data.decode(settings.get("encoding", "utf-8"))}')
        else:
            logger.debug(f'Server say message len {len(self.long_data)}')

        mes = Message(self.long_data)
        self.long_data = b''
        self._thread.run_command(self, mes)

    def connection_lost(self, exc):
        print('The server closed the connection')
        self._thread.on_con_lost.set_result(True)

    def write(self, msg, transport=None):
        transport = transport or self.transport
        if not isinstance(msg, bytes):
            msg = bytes(msg)
        try:
            msg = struct.pack('>I', len(msg)) + msg
            transport.write(msg)
            logger.info(f'send {msg}')
        except BrokenPipeError:
            transport.close()

    def close(self):
        self._thread.on_con_lost.set_result(True)

    def notify(self, event, *args, **kwargs):
        self._thread.notify(event, self, *args, **kwargs)

    @property
    def decrypter(self):
        if not hasattr(self, '_decrypter'):
            self._decrypter = self._thread.decrypter
        return self._decrypter


class Router:
    def __init__(self):
        self.commands = []
        self.source = None

    def reg_command(self, command, name=None):
        name = getattr(command, 'name', None) if not name else name
        if name and command:
            self.commands.append((name, command))
            if self.source:
                self.init_cmd(command, name)

    def unreg_command(self, command, name=None):
        name = getattr(command, 'name', None) if not name else name
        self.commands = [(n, c) for n, c in self.commands if n != name]
        if self.source:
            self.source.detach(command, name)

    def init(self, source):
        self.source = source
        for name, cmd in self.commands:
            self.init_cmd(cmd, name)

    def init_cmd(self, cmd, name):
        if hasattr(cmd, '__name__'):
            cmd = cmd()
        self.source.attach(cmd, name)


router = Router()


class ClientAuth:
    name = settings.AUTH

    def update(self, proto, msg, *args, **kwargs):
        user = User.by_name(settings.USER_NAME)
        ans_data = getattr(msg, settings.DATA, '')
        code = getattr(msg, settings.RESPONSE, '')
        if code == 511:
            digest = hmac.new(user.auth_key, ans_data.encode('utf-8')).digest()
            proto.write(Message(response=511, **{
                settings.ACTION: settings.AUTH,
                settings.DATA: binascii.b2a_base64(digest).decode('ascii'),
                settings.USER: user.username,
            }))
            proto.notify('done_511')
        elif code == 212:
            user.active = True
            with db_lock:
                user.save()
            proto.notify(f'done_{self.name}')
        elif code == 412:
            logger.error(f'{msg}')
            proto.notify(f'fail_{self.name}')


class ClientError:
    name = 400

    def update(self, event, proto, msg, *args, **kwargs):
        logger.error(f'{msg}')
        # proto.close()


class GetAllUsers:
    name = settings.USERS_REQUEST

    def update(self, proto, msg=None, **kwargs):
        code = getattr(msg, settings.RESPONSE, '')
        if code == 202:
            lst = []
            for username, ava in getattr(msg, settings.LIST_INFO, []):
                user = User.by_name(username=username)
                if user:
                    if ava:
                        user.avatar = QByteArray.fromBase64(base64.b64decode(ava))
                else:
                    user = User(username=username, password='placeholder', avatar=QByteArray.fromBase64(base64.b64decode(ava)) if ava else None)
                lst.append(user)
            with db_lock:
                User.save_all(lst)
            proto.notify(f'done_{self.name}')
        else:
            proto.write(Message(**{
                settings.ACTION: settings.USERS_REQUEST,
                settings.USER: settings.USER_NAME,
            }))
            proto.notify(f'send_{self.name}')


class GetContacts:
    name = settings.GET_CONTACTS

    def update(self, proto, msg=None, *args, **kwargs):
        code = getattr(msg, settings.RESPONSE, '')
        if code == 202:
            user = User.by_name(settings.USER_NAME)
            for contact in getattr(msg, settings.LIST_INFO, []):
                try:
                    with db_lock:
                        user.add_contact(contact)
                except ContactExists:
                    pass
            proto.notify(f'done_{self.name}')
        else:
            proto.write(Message(**{
                settings.ACTION: settings.GET_CONTACTS,
                settings.USER: settings.USER_NAME,
            }))
            proto.notify(f'send_{self.name}')


class GetChatsCommand:
    name = settings.GET_CHATS

    def update(self, proto, msg=None, *args, **kwargs):
        code = getattr(msg, settings.RESPONSE, '')
        if code == 202:
            Chat.chats_merge(getattr(msg, settings.LIST_INFO, []))
            proto.notify(f'done_{self.name}')
        else:
            proto.write(Message(**{
                settings.ACTION: settings.GET_CHATS,
                settings.USER: settings.USER_NAME,
            }))
            proto.notify(f'send_{self.name}')


class GetMessagesCommand:
    name = settings.GET_MESSAGES

    def update(self, proto, msg=None, *args, **kwargs):
        proto.write(Message(**{
            settings.ACTION: self.name,
            settings.USER: settings.USER_NAME,
        }))
        proto.notify(f'send_{self.name}')


class MessageCommand:
    name = settings.MESSAGE

    def update(self, proto, msg=None, *args, **kwargs):
        if isinstance(msg, Message) and msg.is_valid():
            sender = getattr(msg, settings.SENDER, None)
            mes_ecrypted = base64.b64decode(str(msg))
            decrypted_message = proto.decrypter.decrypt(mes_ecrypted)
            Chat.create_msg(msg, text=decrypted_message.decode('utf8'))
            proto.notify(f'new_{self.name}', msg)
            logger.info(f'Получено сообщение от пользователя {sender}')


class SendMessageCommand:
    name = f'send_{settings.MESSAGE}'

    def update(self, proto, msg, *args, **kwargs):
        proto.write(msg)
        proto.notify(f'done_{self.name}')


class RequestKeyCommand:
    name = settings.PUBLIC_KEY_REQUEST

    def update(self, proto, msg=None, *args, **kwargs):
        code = getattr(msg, settings.RESPONSE, '')
        if not msg:
            dest = kwargs.get('contact')
            if not dest:
                logger.info('Не указан контакт чей ключ нужно получить')
                return
            proto.write(Message(**{
                settings.ACTION: settings.PUBLIC_KEY_REQUEST,
                settings.SENDER: settings.USER_NAME,
                settings.DESTINATION: dest,
            }))
            proto.notify(f'send_{self.name}')
        elif code == 202:
            pub_key = getattr(msg, settings.DATA, '')
            with db_lock:
                rest_user = User.by_name(getattr(msg, settings.ACCOUNT_NAME, ''))
                rest_user.pub_key = pub_key
                rest_user.save()
            proto.notify(f'done_{self.name}')


router.reg_command(ClientAuth)
router.reg_command(ClientError)
router.reg_command(GetAllUsers)
router.reg_command(GetChatsCommand)
router.reg_command(GetAllUsers, f'done_{settings.AUTH}')
router.reg_command(GetChatsCommand, f'done_{settings.AUTH}')
router.reg_command(GetMessagesCommand, f'done_{settings.GET_CHATS}')
router.reg_command(GetAllUsers, 205)
router.reg_command(GetChatsCommand, 206)
router.reg_command(MessageCommand)
router.reg_command(RequestKeyCommand)
router.reg_command(SendMessageCommand)
