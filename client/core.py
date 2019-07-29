# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-22 23:36:43
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-29 13:29:39
import logging
import socket
import threading
import time
from commands import main_commands

from dynaconf import settings

from db import DBManager, User, UserHistory, UserMessages
from errors import ContactExists
from jim_mes import Message
from metaclasses import ClientVerifier

app_name = 'client'

logger = logging.getLogger(app_name)

sock_lock = threading.Lock()

database_lock = threading.Lock()


class SocketMixin(object):
    def send_message(self, mes):
        with sock_lock:
            try:
                self.sock.send(bytes(mes))
            except OSError as err:
                if err.errno:
                    print('Потеряно соединение с сервером.')
                    logger.critical('Потеряно соединение с сервером.', exc_info=True)
                    exit(1)
            except (Exception, BrokenPipeError):
                print('Потеряно соединение с сервером.')
                logger.critical('Потеряно соединение с сервером.', exc_info=True)
                exit(1)

    def read_data(self):
        with sock_lock:
            try:
                data = self.sock.recv(settings.get('max_package_length', 1024))
            # Вышел таймаут соединения если errno = None, иначе обрыв соединения.
            except OSError as err:
                if err.errno:
                    logger.critical(f'Потеряно соединение с сервером.')
                    exit(1)
            else:
                return Message(data) if data else None


class Client(SocketMixin, metaclass=ClientVerifier):
    def __init__(self, *args, **kwargs):
        self.sock = None
        super().__init__()
        self.init_socket()

    def init_socket(self):
        self.sock = socket.socket()
        self.sock.settimeout(1)

    def connect(self):
        self.sock.connect((settings.get('HOST'), settings.as_int('PORT')))
        logger.debug(f'Start with {settings.get("host")}:{settings.get("port")}')
        self.send_message(Message.presence())
        message = self.read_data()
        logger.debug(f'Установлено соединение с сервером. Ответ сервера: {message}')
        print(f'Установлено соединение с сервером.')
        self.database = DBManager(app_name)

        self.update_user_list()
        self.update_contacts_list()
        sender = ClientSender(self.sock)
        sender.daemon = True
        sender.start()

        reciver = ClientReader(self.sock)
        reciver.daemon = True
        reciver.start()

        # Watchdog основной цикл, если один из потоков завершён, то значит или потеряно соединение или пользователь
        # ввёл exit. Поскольку все события обработываются в потоках, достаточно просто завершить цикл.
        try:
            while True:
                time.sleep(1)
                if not reciver.is_alive() or not sender.is_alive():
                    break
        except KeyboardInterrupt:
            self.send_message(Message.exit_request())
            logger.debug('User closed')

    def update_user_list(self):
        """Функция запроса списка известных пользователей"""
        logger.debug(f'Запрос списка известных пользователей {settings.USER_NAME}')
        self.send_message(Message(**{
            settings.ACTION: settings.USERS_REQUEST,
            settings.USER: settings.USER_NAME,
        }))
        response = self.read_data()
        if response and response.response == 202:
            with database_lock:
                User.save_all((User(username=user) for user in getattr(response, settings.LIST_INFO, []) if User.filter_by(username=user).count() == 0))
        else:
            logger.error('Ошибка запроса списка известных пользователей.')

    def update_contacts_list(self):
        """Функция запрос контакт листа"""
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
            logger.error('Ошибка запроса списка известных пользователей.')


class ClientReader(threading.Thread, SocketMixin):
    """ Класс-приёмник сообщений с сервера. Принимает сообщения, выводит в консоль."""
    def __init__(self, sock):
        self.sock = sock
        self.db_lock = database_lock
        super().__init__()

    def run(self):
        """Основной цикл приёмника сообщений, принимает сообщения, выводит в консоль. Завершается при потере соединения."""
        while True:
            time.sleep(1)
            message = self.read_data()
            if not message:
                continue
            if message.is_valid():
                sender = getattr(message, settings.SENDER, None)
                print(f'\r\nMessage from {sender}:\n{message}')
                with self.db_lock:
                    UserHistory.proc_message(sender, settings.USER_NAME)
                    UserMessages.create(sender=User.by_name(sender), receiver=User.by_name(settings.USER_NAME), message=str(message))
                logger.info(f'Получено сообщение от пользователя {sender}:\n{message}')
            else:
                logger.error(f'Получено некорректное сообщение с сервера: {message}')


class ClientSender(threading.Thread, SocketMixin):
    """Класс формировки и отправки сообщений на сервер и взаимодействия с пользователем."""
    def __init__(self, sock):
        self.sock = sock
        self.db_lock = database_lock
        super().__init__()

    def run(self):
        """Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения"""
        main_commands.print_help()
        while True:
            command = input('Введите команду: ')
            if not main_commands.run(command, self):
                print('Команда не распознана. help - вывести поддерживаемые команды.')
