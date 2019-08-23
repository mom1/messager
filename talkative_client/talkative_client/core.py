# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-22 23:36:43
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-24 00:32:46
import base64
import binascii
import hashlib
import hmac
import logging
import socket
import struct
import sys
import threading
import time

from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.PublicKey import RSA
from dynaconf import settings
from PyQt5.QtCore import QByteArray, QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

from .commands import main_commands
from .db import DBManager, User, UserHistory, UserMessages
from .errors import ContactExists, ServerError
from .gui import ClientGui
from .jim_mes import Message
from .metaclasses import ClientVerifier

app_name = 'client'

logger = logging.getLogger(app_name)

sock_lock = threading.Lock()

database_lock = threading.Lock()
client = None


class SocketMixin(object):
    """Миксин взаимодействия с сокетом."""
    def send_message(self, mes):
        """Отправка сообщения.

        Args:
            mes: :py:class:`~jim_mes.Message`

        """
        with sock_lock:
            try:
                msg = bytes(mes)
                msg = struct.pack('>I', len(msg)) + msg
                self.sock.send(msg)
            except OSError as err:
                if err.errno:
                    print('Потеряно соединение с сервером.')
                    logger.critical('Потеряно соединение с сервером.', exc_info=True)
            except (BrokenPipeError):
                print('Потеряно соединение с сервером.')
                logger.critical('Потеряно соединение с сервером.', exc_info=True)

    def read_data(self):
        """Прием сообщения."""
        with sock_lock:
            try:
                raw_msglen = self.recvall(4)
                if not raw_msglen:
                    return
                msglen = struct.unpack('>I', raw_msglen)[0]
                data = self.recvall(msglen)
            # Вышел таймаут соединения если errno = None, иначе обрыв соединения.
            except OSError as err:
                if err.errno:
                    logger.critical(f'Потеряно соединение с сервером.')
                    sys.exit(1)
            else:
                return Message(data) if data else None

    def recvall(self, n):
        """Функция для получения n байт или возврата None если получен EOF

        Args:
            n: Количество получаемых байт

        Returns:
            Полученные данные
            bytes
        """
        data = b''
        while len(data) < n:
            try:
                packet = self.sock.recv(n - len(data))
            except socket.timeout:
                return data
            if not packet:
                return
            data += packet
        return data


class Client(SocketMixin, metaclass=ClientVerifier):
    """Центральный класс аля watchdog

    нужно переписать

    """
    def __init__(self, *args, **kwargs):
        """Инициализация."""
        self.sock = None
        self.db_lock = database_lock
        super().__init__()
        self.init_socket()

    def init_socket(self):
        """Инициализация сокета."""
        self.sock = socket.socket()
        self.sock.settimeout(1.5)

    def connect(self):
        """Соединение с сервером.

        И основной цикл

        Raises:
            ServerError: При ошибочном запросе

        """
        global client
        client = None
        connected = False
        for i in range(5):
            logger.info(f'Попытка подключения №{i + 1}')
            try:
                self.sock.connect((settings.get('HOST'), settings.as_int('PORT')))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                break
            time.sleep(1)

        if not connected:
            logger.critical('Не удалось установить соединение с сервером')
            sys.exit(1)

        logger.debug(f'Start with {settings.get("host")}:{settings.get("port")}')
        self.database = DBManager(app_name)
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
        self.send_message(Message.presence())

        message = self.read_data()

        response = getattr(message, settings.RESPONSE, None)
        while True:
            if response == 200:
                break
            elif response == 205:
                # ?????
                break
            elif response == 400:
                raise ServerError(getattr(message, settings.ERROR, ''))
            elif response == 511:
                # Если всё нормально, то продолжаем процедуру авторизации.
                ans_data = getattr(message, settings.DATA, '')
                digest = hmac.new(user.auth_key, ans_data.encode('utf-8')).digest()
                response = Message(response=511, **{settings.DATA: binascii.b2a_base64(digest).decode('ascii'), settings.USER: user.username, settings.ACTION: settings.AUTH})
                self.send_message(response)
                message = self.read_data()
                if not message:
                    logger.error(f'Авторизация не пройдена')
                    sys.exit(1)
                response = getattr(message, settings.RESPONSE, None)
                user.active = True
                user.save()
            else:
                logger.error(f'Принят неизвестный код подтверждения {response}')
                return

        logger.debug(f'Установлено соединение с сервером. Ответ сервера: {message}')
        print(f'Установлено соединение с сервером.')

        self.update_user_list()
        self.update_contacts_list()

        receiver = ClientReader(self)
        receiver.daemon = True
        receiver.setDaemon(True)
        receiver.start()

        if settings.get('console'):
            client = ClientSender(self.sock)
            receiver.attach(client, settings.get('event_new_message'))
            client.daemon = True
            client.start()
        elif settings.get('gui'):
            sys.argv += ['-style', 'Fusion']
            app = QApplication(sys.argv)
            client = ClientGui(self)
            receiver.new_message.connect(client.update)
            receiver.up_all_users.connect(client.update)
            receiver.response_key.connect(client.update)
            app.exec_()

        # Watchdog основной цикл, если один из потоков завершён, то значит или потеряно соединение или пользователь
        # ввёл exit. Поскольку все события обрабатываются в потоках, достаточно просто завершить цикл.
        try:
            while True:
                time.sleep(1)
                if not receiver.is_alive() or not client or not client.is_alive():
                    break
        except KeyboardInterrupt:
            pass
        self.exit_client()

    def exit_client(self):
        """Отправка информации о выходе."""
        self.send_message(Message.exit_request())
        logger.debug('User closed')
        time.sleep(0.5)
        sys.exit(0)

    def update_user_list(self):
        """Функция запроса списка известных пользователей."""
        logger.debug(f'Запрос списка известных пользователей {settings.USER_NAME}')
        self.send_message(Message(**{
            settings.ACTION: settings.USERS_REQUEST,
            settings.USER: settings.USER_NAME,
        }))
        response = self.read_data()
        if response and response.response == 202:
            with database_lock:
                lst = []
                for username, ava in getattr(response, settings.LIST_INFO, []):
                    user = User.by_name(username=username)
                    if user:
                        if ava:
                            user.avatar = QByteArray.fromBase64(base64.b64decode(ava))
                    else:
                        user = User(username=username, password='placeholder', avatar=ava)
                    lst.append(user)
                User.save_all(lst)
        else:
            logger.error('Ошибка запроса списка известных пользователей.')

    def update_contacts_list(self):
        """Функция запрос контакт листа."""
        logger.debug(f'Запрос контакт листа для пользователя {settings.USER_NAME}')
        self.send_message(Message(**{
            settings.ACTION: settings.GET_CONTACTS,
            settings.USER: settings.USER_NAME,
        }))
        response = self.read_data()
        if response and response.response == 202:
            with database_lock:
                user = User.by_name(settings.USER_NAME)
                for contact in getattr(response, settings.LIST_INFO, []):
                    try:
                        user.add_contact(contact)
                    except ContactExists:
                        pass
        else:
            logger.error('Ошибка запроса списка контактов пользователей.')


class ClientReader(threading.Thread, SocketMixin, QObject):
    """Класс-приёмник сообщений с сервера. Принимает сообщения, выводит в консоль."""

    new_message = pyqtSignal(Message)
    up_all_users = pyqtSignal(Message)
    response_key = pyqtSignal(Message)

    def __init__(self, parent):
        """Инициализация.

        Args:
            parent: родительский поток

        """
        self.parent = parent
        self.sock = parent.sock
        self.db_lock = database_lock
        self._observers = {}
        self.message = None
        self.decrypter = PKCS1_OAEP.new(RSA.import_key(settings.get('USER_KEY')))
        threading.Thread.__init__(self)
        QObject.__init__(self)

    def run(self):
        """Основной цикл приёмника сообщений, принимает сообщения, выводит в консоль. Завершается при потере соединения."""
        while True:
            time.sleep(1)
            self.message = self.read_data()
            if not self.message:
                continue
            if self.message.is_valid():
                sender = getattr(self.message, settings.SENDER, None)
                mes_ecrypted = base64.b64decode(str(self.message))
                decrypted_message = self.decrypter.decrypt(mes_ecrypted)
                with self.db_lock:
                    UserHistory.proc_message(sender, settings.USER_NAME)
                    UserMessages.create(
                        sender=User.by_name(sender),
                        receiver=User.by_name(settings.USER_NAME),
                        message=decrypted_message.decode('utf8'),
                    )
                self.notify(settings.get('event_new_message'))
                self.new_message.emit(self.message)
                logger.info(f'Получено сообщение от пользователя {sender}:\n{self.message}')
            elif self.message.response == 205:
                self.parent.update_user_list()
                self.up_all_users.emit(self.message)
            elif self.message.response == 511:
                pub_key = getattr(self.message, settings.DATA, '')
                rest_user = User.by_name(getattr(self.message, settings.ACCOUNT_NAME, ''))
                rest_user.pub_key = pub_key
                rest_user.save()
                self.response_key.emit(self.message)
            elif self.message.response == 200:
                pass
            else:
                logger.error(f'Получено некорректное сообщение с сервера: {self.message}')

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
        return True

    def notify(self, event):
        """Уведомление о событии.

        Args:
            event: имя события

        """
        obs = self._observers.get(event, []) or []
        for observer in obs:
            observer.update(self, event)


class ClientSender(threading.Thread, SocketMixin):
    """Класс формировки и отправки сообщений на сервер и взаимодействия с пользователем."""
    def __init__(self, sock):
        """Инициализация.

        Args:
            sock: сокет для работы миксина

        """
        self.sock = sock
        self.db_lock = database_lock
        super().__init__()

    def run(self):
        """Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения."""
        main_commands.print_help()
        while True:
            command = input('Введите команду: ')
            if not main_commands.run(command, self):
                print('Команда не распознана. help - вывести поддерживаемые команды.')

    def update(self, reader, event):
        """Уведомление о новом сообщении.

        Args:
            reader: чтец
            event: событие

        """
        if event == settings.get('event_new_message'):
            sender = getattr(reader.message, settings.SENDER, None)
            print(f'\r\nMessage from {sender}:\n{reader.message}')
