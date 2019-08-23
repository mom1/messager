# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-08-23 17:30:42
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-24 01:35:31
import asyncio
import base64
import binascii
import hashlib
import hmac
import logging
import os
import socket
import struct
import threading

from dynaconf import settings

from .db import DBManager, User
from .descriptors import PortDescr
from .jim_mes import Message
from .metaclasses import ClientVerifier

app_name = 'client'
logger = logging.getLogger(app_name)


class ClientTransport(threading.Thread, metaclass=ClientVerifier):
    """[summary].

    [description]

    """
    port = PortDescr()

    def __init__(self):
        super().__init__()
        self.started = False
        self._observers = {}
        self.auth = {}
        self.router = router.init(self)

    async def async_start(self):
        self.loop = asyncio.get_running_loop()
        self.on_con_lost = self.loop.create_future()
        self.transport, self.protocol = await self.loop.create_connection(lambda: AsyncClientProtocol(self), settings.get('HOST'), settings.as_int('PORT'))

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
        self.database = DBManager(app_name)
        self.notify('init_db')
        asyncio.run(self.async_start())

    def is_alive(self):
        return self.started

    def notify(self, event, *args, **kwargs):
        logger.info(f'Свершилось событие {event}')
        obs = self._observers.get(event, []) or []
        for observer in obs:
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
        user.save()
        logger.debug('Установлено соединение с сервером.')

        self.write(Message.presence())
        self.def_size, self.transport.max_size, self.cur_size = self.transport.max_size, self.CHUNK_SIZE, self.CHUNK_SIZE
        self._thread.notify('new_connect')
        self.long_data = b''

    def data_received(self, data):
        if len(data) == self.CHUNK_SIZE:
            self.cur_size = struct.unpack('>I', data)[0]
            self.transport.max_size = self.def_size
            return
        self.long_data += data

        if self.cur_size > len(self.long_data):
            return

        self.transport.max_size = self.cur_size = self.CHUNK_SIZE
        logger.debug(f'Server say: {self.long_data.decode(settings.get("encoding", "utf-8"))}')
        mes = Message(self.long_data)
        self.long_data = b''
        self._thread.run_command(self, mes)

    def connection_lost(self, exc):
        print('The server closed the connection')
        # self._thread.on_con_lost.set_result(True)

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

    def notify(self, *args, **kwargs):
        self._thread.notify(*args, **kwargs)


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


class ClientAuth:
    name = settings.AUTH

    def update(self, event, proto, msg, *args, **kwargs):
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
            user.save()
            proto.notify(f'done_{settings.AUTH}')
        elif code == 412:
            logger.error(f'{msg}')
            proto.notify(f'fail_{settings.AUTH}')


class ClientError:
    name = 400

    def update(self, event, proto, msg, *args, **kwargs):
        logger.error(f'{msg}')
        proto.close()


router.reg_command(ClientAuth)
router.reg_command(ClientError)
