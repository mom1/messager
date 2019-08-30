# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-08-23 07:50:08
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-30 11:54:17
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

from .descriptors import PortDescr
from .jim_mes import Message
# from .metaclasses import ServerVerifier

app_name = 'server'
logger = logging.getLogger(app_name)
db = DBManager(app_name)

from .decorators import login_required_db  # noqa


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

    def notify(self, event, *args, **kwargs):
        logger.info(f'Свершилось событие {event}')
        obs = self._observers.get(event, []) or []
        for observer in obs:
            if isinstance(observer, QObject):
                self.update.emit({**{'event': event}, **kwargs})
            else:
                observer.update(self, event, *args, **kwargs)

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

    def service_update_lists(self, excep=None):
        for k, v in self.loop._transports.items():
            if v is excep:
                continue
            proto = v.get_protocol()
            if proto:
                proto.write(Message(response=205))


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

    def notify(self, *args, **kwargs):
        self._thread.notify(*args, **kwargs)

    def close(self):
        self.transport.close()

    def service_update_lists(self):
        self._thread.service_update_lists(excep=self.transport)

    def get_user_tr(self, user_name):
        act_user = db.ActiveUsers.by_name(user_name)
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
        self.source.attach(cmd, name)


router = Router()


class MessageCommand:
    """Отправить сообщение."""

    name = settings.MESSAGE

    @login_required_db
    def update(self, event, proto, msg, *args, **kwargs):
        if msg.is_valid():
            dest_user = getattr(msg, settings.DESTINATION, None)
            src_user = getattr(msg, settings.SENDER, None)
            dest = proto.get_user_tr(dest_user)
            if not dest:
                logger.error(f'Пользователь {dest_user} не зарегистрирован на сервере, отправка сообщения невозможна.')
                return
            proto.write(msg, dest)
            db.UserHistory.proc_message(src_user, dest_user)
            logger.info(f'Отправлено сообщение пользователю {dest_user} от пользователя {src_user}.')
            proto.notify(f'done_{settings.MESSAGE}')


class Presence:
    name = settings.PRESENCE

    def update(self, event, proto, msg, *args, **kwargs):
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
        proto.notify(f'done_{settings.PRESENCE}')


class Auth:
    name = 'auth'

    def update(self, event, proto, msg, *args, **kwargs):
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
    def update(self, event, proto, msg, *args, **kwargs):
        lst = []
        for user in db.User.objects.all():
            lst.append((user.username, base64.b64encode(user.avatar).decode('ascii') if user.avatar else None))
        proto.write(Message.success(202, **{
            settings.LIST_INFO: lst,
            settings.ACTION: settings.USERS_REQUEST,
        }))
        proto.notify(f'done_{settings.USERS_REQUEST}')


class AddContactCommand:
    """Обрабатывает запросы на добавление контакта."""

    name = settings.ADD_CONTACT

    @login_required_db
    def update(self, event, proto, msg, *args, **kwargs):
        src_user = getattr(msg, settings.USER, None)
        contact = getattr(msg, settings.ACCOUNT_NAME, None)
        user = db.User.by_name(src_user)
        if contact:
            user.add_contact(contact)
            proto.write(Message.success())
        else:
            proto.write(Message.error_resp('Не найден контакт'))
        logger.info(f'User {src_user} add contact {contact}')
        proto.notify(f'done_{settings.ADD_CONTACT}')


class DelContactCommand:
    """Обрабатывает запросы на удаление контакта."""

    name = settings.DEL_CONTACT

    @login_required_db
    def update(self, event, proto, msg, *args, **kwargs):
        """Выполнение."""
        src_user = getattr(msg, settings.USER, None)
        contact = getattr(msg, settings.ACCOUNT_NAME, None)
        user = db.User.by_name(src_user)
        if contact:
            user.del_contact(contact)
            proto.write(Message.success())
        logger.info(f'User {src_user} del contact {contact}')
        proto.notify(f'done_{settings.DEL_CONTACT}')


class ListContactsCommand:
    """Обрабатывает запросы на получение списка контактов пользователя."""

    name = settings.GET_CONTACTS

    @login_required_db
    def update(self, event, proto, msg, *args, **kwargs):
        user = db.User.by_name(msg.user_account_name)
        proto.write(Message.success(202, **{settings.LIST_INFO: [c.username for c in user.contacts], settings.ACTION: settings.GET_CONTACTS}))
        logger.info(f'User {user.username} get list contacts')
        proto.notify(f'done_{settings.GET_CONTACTS}')


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
        proto.notify(f'done_{settings.PUBLIC_KEY_REQUEST}')


class EditAvatar:
    """Изменение аватара."""

    name = settings.AVA_INFO

    @login_required_db
    def update(self, event, proto, msg, *args, **kwargs):
        user = db.User.by_name(msg.user_account_name)
        ava = getattr(msg, settings.DATA, None)
        if user and ava:
            user.avatar = base64.b64decode(ava)
            user.save()
            logger.info(f'Ava saved for user {user.username}')
            proto.notify(f'done_{settings.AVA_INFO}')
            proto.service_update_lists()


class ExitCommand:
    """Выход пользователя."""

    name = settings.EXIT

    @login_required_db
    def update(self, event, proto, msg, *args, **kwargs):
        user = db.User.by_name(msg.user_account_name)
        if user:
            client_ip, client_port = proto.transport.get_extra_info('peername')
            proto.close()
            db.User.logout_user(user.username, ip_addr=client_ip, port=client_port)
            logger.info(f'User {user.username} log off')
            proto.notify(f'done_{settings.EXIT}')


router.reg_command(Presence)
router.reg_command(Auth)
router.reg_command(UserListCommand)
router.reg_command(ListContactsCommand)
router.reg_command(EditAvatar)
router.reg_command(RequestKeyCommand)
router.reg_command(DelContactCommand)
router.reg_command(AddContactCommand)
router.reg_command(MessageCommand)
router.reg_command(ExitCommand)
