# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-08-23 07:50:08
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-01 15:43:10
import asyncio
import base64
import binascii
import hmac
import logging
import os
import socket
import struct

from dynaconf import settings
from PyQt5.QtCore import QObject, QThread, pyqtSignal

from .db import DBManager
from .decorators import login_required_db  # noqa
from .descriptors import PortDescr
from .jim_mes import Message

# from .metaclasses import ServerVerifier

app_name = 'server'
logger = logging.getLogger(app_name)
db = DBManager(app_name)


class ServerA(QThread):
    """Асинхронный сервер

    not support cli yet

    Attributes:
        port: [description]

    Methods:
        notify: Уведомление о событии.
            Args:
                event: Строка имени произошедшего события.
        attach: Подписка на события сервера.
            Args:
                observer: Объект наблюдатель.
                event: Строка имени события.
        detach: Отписаться от события.
            Args:
                observer: Объект наблюдатель.
                event: Строка имени события.
    """

    port = PortDescr()
    update = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.started = False
        self._observers = {}
        self.auth = {}
        self.protocol = None
        self.router = router.init(self)

    def init_socket(self):
        """Инициализация сокета."""
        self.sock = socket.socket()
        self.port = settings.as_int('PORT')
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((settings.get('host'), self.port))
        self.sock.settimeout(0.5)
        self.sock.listen(settings.get('max_connections'))
        self.started = True
        logger.info(f'start with {settings.get("host")}:{self.port}')
        self.notify('start_server')

    async def async_start(self):
        self.loop = asyncio.get_running_loop()
        self.server = await self.loop.create_server(lambda: AsyncServerProtocol(self), sock=self.sock)

        try:
            async with self.server:
                await self.server.serve_forever()
        except KeyboardInterrupt:
            logger.debug('closed')
        except Exception as error:
            logger.error(error, exc_info=True)
        finally:
            logger.debug('stoped')
            self.notify('stoped_server')

    def run(self):
        self.notify('init_db')
        self.init_socket()
        self.notify('init_socket')
        asyncio.run(self.async_start())

    def stop(self):
        self.started = False
        self.server.close()
        self.sock.close()
        logger.debug('stoped')

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
        return True

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

    def service_update_lists(self, code=205, excep=None):
        for k, v in self.loop._transports.items():
            if v is excep:
                continue
            proto = v.get_protocol()
            if proto:
                proto.write(Message(response=code))


class AsyncServerProtocol(asyncio.Protocol):
    """Протокол TCP

    Сначала читаем первые 4 байта в них содержится размер данных.
    Далее читаем с размером по умолчанию до целевого размера.

    Attributes:
        CHUNK_SIZE: размер части в начале данных содержащий размер всей части
    """
    CHUNK_SIZE = 4

    def __init__(self, thread, *args, **kwargs):
        self._thread = thread
        super().__init__(*args, **kwargs)

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        logger.info(f'Установлено соединение с ПК {peername}')
        self.transport = transport
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
        logger.debug(f'Client say: {self.long_data.decode(settings.get("encoding", "utf-8"))}')
        mes = Message(self.long_data)
        self.long_data = b''
        response = self._thread.run_command(self, mes)
        if response:
            logger.debug(f'send response')

    def connection_lost(self, exc):
        logger.info('The connection was closed')
        ip, port = self.transport.get_extra_info('peername')
        user = db.ActiveUsers.objects(ip_addr=ip, port=port).first()
        if user:
            self._thread.run_command(self, Message(**{
                settings.ACTION: settings.EXIT,
                settings.USER: user.oper.username,
            }))

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

    def notify(self, event, *args, **kwargs):
        self._thread.notify(event, self, *args, **kwargs)

    def close(self):
        self.transport.close()

    def service_update_lists(self, code=205):
        self._thread.service_update_lists(code=code, excep=self.transport)

    def get_user_tr(self, user_name):
        act_user = db.ActiveUsers.by_name(user_name)
        if not act_user:
            return
        for k, v in self._thread.loop._transports.items():
            if v is self:
                continue
            ip, port = v.get_extra_info('peername')
            if act_user.ip_addr == ip and act_user.port == port:
                return v


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


class MessageCommand:
    """Отправить сообщение."""

    name = settings.MESSAGE

    @login_required_db
    def update(self, proto, msg, *args, **kwargs):
        if msg.is_valid():
            dest_user = getattr(msg, settings.DESTINATION, None)
            src_user = getattr(msg, settings.SENDER, None)
            dest = proto.get_user_tr(dest_user)
            if not dest:
                db.Chat.create_msg(msg)
                db.UserHistory.proc_message(src_user, dest_user)
                logger.info(f'Пользователь {dest_user} не зарегистрирован на сервере, отправка сообщения невозможна.')
                return
            proto.write(msg, dest)
            db.UserHistory.proc_message(src_user, dest_user)
            db.Chat.create_msg(msg, True)
            logger.info(f'Отправлено сообщение пользователю {dest_user} от пользователя {src_user}.')
            proto.notify(f'done_{self.name}')


class Presence:
    name = settings.PRESENCE

    def update(self, proto, msg, *args, **kwargs):
        user = db.User.by_name(msg.user_account_name)
        if not user:
            logger.info('Пользователь не зарегистрирован.')
            return proto.write(Message.error_resp('Пользователь не зарегистрирован.'))

        if user.user_activity:
            logger.info('Имя пользователя уже занято.')
            return proto.write(Message.error_resp('Имя пользователя уже занято.'))

        random_str = binascii.hexlify(os.urandom(64))
        digest = hmac.new(user.auth_key, random_str).digest()
        proto._thread.auth[user.username] = (digest, getattr(msg, settings.PUBLIC_KEY, ''))
        proto.write(Message(response=511, **{settings.ACTION: settings.AUTH, settings.DATA: random_str.decode('ascii')}))
        proto.notify(f'done_{self.name}')


class Auth:
    name = 'auth'

    def update(self, proto, msg, *args, **kwargs):
        user = db.User.by_name(msg.user_account_name)
        if not user:
            return proto.write(Message.error_resp('Пользователь не зарегистрирован.'))
        client_digest = binascii.a2b_base64(getattr(msg, settings.DATA, ''))
        digest, pub_key = proto._thread.auth.pop(user.username, (None, None))
        if digest and hmac.compare_digest(digest, client_digest):
            proto.write(Message(response=212, **{settings.ACTION: settings.AUTH}))
            client_ip, client_port = proto.transport.get_extra_info('peername')
            db.User.login_user(user.username, ip_addr=client_ip, port=client_port, pub_key=pub_key)
            proto.notify('auth_new_user')
        else:
            proto.write(Message(response=412, error='Ошибка авторизации', **{settings.ACTION: settings.AUTH}))


class UserListCommand:
    name = settings.USERS_REQUEST

    @login_required_db
    def update(self, proto, msg, *args, **kwargs):
        lst = []
        for user in db.User.objects.all():
            lst.append((user.username, base64.b64encode(user.avatar).decode('ascii') if user.avatar else None))
        proto.write(Message.success(202, **{
            settings.LIST_INFO: lst,
            settings.ACTION: settings.USERS_REQUEST,
        }))
        proto.notify(f'done_{self.name}')


class AddContactCommand:
    """Обрабатывает запросы на добавление контакта."""

    name = settings.ADD_CONTACT

    @login_required_db
    def update(self, proto, msg, *args, **kwargs):
        src_user = getattr(msg, settings.USER, None)
        contact = getattr(msg, settings.ACCOUNT_NAME, None)
        user = db.User.by_name(src_user)
        if contact:
            user.add_contact(contact)
            proto.write(Message.success())
        else:
            proto.write(Message.error_resp('Не найден контакт'))
        logger.info(f'User {src_user} add contact {contact}')
        proto.notify(f'done_{self.name}')


class EditChatCommand:
    """Обрабатывает запросы на добавление/изменение чата."""

    name = settings.EDIT_CHAT

    @login_required_db
    def update(self, proto, msg, *args, **kwargs):
        user = db.User.by_name(getattr(msg, settings.USER, None))
        data = getattr(msg, settings.DATA, None)
        chat = db.Chat.objects(name=data.get('name')).first()
        code_resp = 201

        if chat:
            chat.update(set__members=[db.User.by_name(m) for m in data.get('members', [])])
            code_resp = 202
        else:
            chat = db.Chat.objects.create(
                name=data.get('name'),
                owner=db.User.by_name(data.get('owner')),
                is_personal=data.get('is_personal'),
                members=[db.User.by_name(m) for m in data.get('members', [])],
            )
        proto.write(Message.success(code_resp))
        logger.info(f'User {user} edit chat {chat.name}')
        proto.service_update_lists(206)
        proto.notify(f'done_{self.name}')


class DelChatCommand:
    """Обрабатывает запросы на удаление контакта."""

    name = settings.DEL_CHAT

    @login_required_db
    def update(self, proto, msg, *args, **kwargs):
        """Выполнение."""
        user = db.User.by_name(getattr(msg, settings.USER, None))
        data = getattr(msg, settings.DATA, None)
        chat = db.Chat.objects(name=data.get('name')).first()

        if chat:
            chat.delete()
            proto.write(Message.success())
            logger.info(f'User {user} del chat {data.get("name")}')
            proto.service_update_lists(206)
            proto.notify(f'done_{self.name}')


class ListContactsCommand:
    """Обрабатывает запросы на получение списка контактов пользователя."""

    name = settings.GET_CONTACTS

    @login_required_db
    def update(self, proto, msg, *args, **kwargs):
        user = db.User.by_name(msg.user_account_name)
        proto.write(Message.success(202, **{settings.LIST_INFO: [c.username for c in user.contacts], settings.ACTION: settings.GET_CONTACTS}))
        logger.info(f'User {user.username} get list contacts')
        proto.notify(f'done_{self.name}')


class ListChatsCommand:
    """Обрабатывает запросы на получение списка контактов пользователя."""

    name = settings.GET_CHATS

    @login_required_db
    def update(self, proto, msg, *args, **kwargs):
        user = db.User.by_name(msg.user_account_name)
        proto.write(
            Message.success(
                202, **{
                    settings.LIST_INFO: [{
                        'name': c.name,
                        'owner': c.owner.username if c.owner else None,
                        'avatar': c.avatar,
                        'is_personal': c.is_personal,
                        'members': [i.username for i in c.members],
                    } for c in user.chats],
                    settings.ACTION:
                    settings.GET_CHATS,
                }))
        logger.info(f'User {user.username} get list chats')
        proto.notify(f'done_{self.name}')


class ListMessagesCommand:
    """Обрабатывает запросы на получение списка писем."""

    name = settings.GET_MESSAGES

    @login_required_db
    def update(self, proto, msg, *args, **kwargs):
        user = db.User.by_name(msg.user_account_name)
        for msg in db.Messages.objects(receiver=user, received=False):
            proto.write(Message(**{
                settings.ACTION: settings.MESSAGE,
                settings.SENDER: msg.sender.username,
                settings.DESTINATION: msg.receiver.username,
                settings.MESSAGE_TEXT: msg.text,
                'chat': msg.chat.name,
            }))
            msg.received = True
            msg.save()
        logger.info(f'User {user.username} get list messages')
        proto.notify(f'done_{self.name}')


class RequestKeyCommand:
    """Обрабатывает запросы на получение ключа шифрования для пользователя."""

    name = settings.PUBLIC_KEY_REQUEST

    @login_required_db
    def update(self, event, proto, msg, *args, **kwargs):
        dest_user = getattr(msg, settings.DESTINATION, None)
        src_user = getattr(msg, settings.SENDER, None)
        user = db.User.by_name(dest_user)
        if user and user.pub_key:
            mes = Message(response=202, **{
                settings.DATA: user.pub_key,
                settings.ACCOUNT_NAME: dest_user,
                settings.ACTION: settings.PUBLIC_KEY_REQUEST,
            })
        else:
            mes = Message.error_resp('Ошибка определения ключа')
        proto.write(mes)
        logger.info(f'User {src_user} get pub_key {dest_user}')
        proto.notify(f'done_{self.name}')


class EditAvatar:
    """Изменение аватара."""

    name = settings.AVA_INFO

    @login_required_db
    def update(self, proto, msg, *args, **kwargs):
        user = db.User.by_name(msg.user_account_name)
        ava = getattr(msg, settings.DATA, None)
        if user and ava:
            user.avatar = base64.b64decode(ava)
            user.save()
            logger.info(f'Ava saved for user {user.username}')
            proto.notify(f'done_{self.name}')
            proto.service_update_lists()
            proto.service_update_lists(206)


class ExitCommand:
    """Выход пользователя."""

    name = settings.EXIT

    @login_required_db
    def update(self, proto, msg, *args, **kwargs):
        user = db.User.by_name(msg.user_account_name)
        if user:
            client_ip, client_port = proto.transport.get_extra_info('peername')
            proto.close()
            db.User.logout_user(user.username, ip_addr=client_ip, port=client_port)
            logger.info(f'User {user.username} log off')
            proto.notify(f'done_{self.name}')


router.reg_command(Presence)
router.reg_command(Auth)
router.reg_command(UserListCommand)
router.reg_command(ListContactsCommand)
router.reg_command(ListChatsCommand)
router.reg_command(EditAvatar)
router.reg_command(RequestKeyCommand)
router.reg_command(DelChatCommand)
router.reg_command(AddContactCommand)
router.reg_command(EditChatCommand)
router.reg_command(MessageCommand)
router.reg_command(ListMessagesCommand)
router.reg_command(ExitCommand)
