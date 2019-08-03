# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-22 23:36:43
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-02 03:45:24
import logging
import socket
import sys
import threading
import time
from commands import main_commands

from dynaconf import settings
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

from db import DBManager, User, UserHistory, UserMessages
from errors import ContactExists
from gui import ClientGui
from jim_mes import Message
from metaclasses import ClientVerifier

app_name = 'client'

logger = logging.getLogger(app_name)

sock_lock = threading.Lock()

database_lock = threading.Lock()
client = None


class SocketMixin(object):
    def send_message(self, mes):
        with sock_lock:
            try:
                self.sock.send(bytes(mes))
            except OSError as err:
                if err.errno:
                    print('Потеряно соединение с сервером.')
                    logger.critical('Потеряно соединение с сервером.', exc_info=True)
            except (BrokenPipeError):
                print('Потеряно соединение с сервером.')
                logger.critical('Потеряно соединение с сервером.', exc_info=True)

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
        self.db_lock = database_lock
        super().__init__()
        self.init_socket()

    def init_socket(self):
        self.sock = socket.socket()
        self.sock.settimeout(1)

    def connect(self):
        global client
        client = None
        self.sock.connect((settings.get('HOST'), settings.as_int('PORT')))
        logger.debug(f'Start with {settings.get("host")}:{settings.get("port")}')
        self.send_message(Message.presence())
        message = self.read_data()
        logger.debug(f'Установлено соединение с сервером. Ответ сервера: {message}')
        print(f'Установлено соединение с сервером.')
        self.database = DBManager(app_name)

        self.update_user_list()
        self.update_contacts_list()

        receiver = ClientReader(self.sock)
        receiver.daemon = True
        receiver.setDaemon(True)
        receiver.start()

        if settings.get('console'):
            client = ClientSender(self.sock)
            receiver.attach(client, settings.get('event_new_message'))
            client.daemon = True
            client.start()
        elif settings.get('gui'):
            app = QApplication(sys.argv)
            client = ClientGui(self)
            receiver.new_message.connect(client.update)
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
        self.send_message(Message.exit_request())
        logger.debug('User closed')
        time.sleep(0.5)
        exit(0)

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


class ClientReader(threading.Thread, SocketMixin, QObject):
    """ Класс-приёмник сообщений с сервера. Принимает сообщения, выводит в консоль."""

    new_message = pyqtSignal(Message)

    def __init__(self, sock):
        self.sock = sock
        self.db_lock = database_lock
        self._observers = {}
        self.message = None
        # super().__init__()
        # Вызываем конструктор предка
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
                with self.db_lock:
                    UserHistory.proc_message(sender, settings.USER_NAME)
                    UserMessages.create(sender=User.by_name(sender), receiver=User.by_name(settings.USER_NAME), message=str(self.message))
                self.notify(settings.get('event_new_message'))
                self.new_message.emit(self.message)
                logger.info(f'Получено сообщение от пользователя {sender}:\n{self.message}')
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
        """Уведомление о событии

        [description]
        :param event: [description]
        :type event: [type]
        """
        obs = self._observers.get(event, []) or []
        for observer in obs:
            observer.update(self, event)
        # self.new_message.emit(message[SENDER])


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

    def update(self, reader, event):
        if event == settings.get('event_new_message'):
            sender = getattr(reader.message, settings.SENDER, None)
            print(f'\r\nMessage from {sender}:\n{reader.message}')
