# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-22 23:36:43
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-23 23:51:04
import logging
import socket
import threading
import time
from commands import main_commands

from dynaconf import settings

from jim_mes import Message
from metaclasses import ClientVerifier

logger = logging.getLogger('client')


class Client(metaclass=ClientVerifier):
    def __init__(self, *args, **kwargs):
        self.sock = None
        super().__init__()
        self.init_socket()

    def init_socket(self):
        self.sock = socket.socket()

    def connect(self):
        self.sock.connect((settings.get('HOST'), settings.as_int('PORT')))
        logger.debug(f'Start with {settings.get("host")}:{settings.get("port")}')
        self.sock.sendall(bytes(Message.presence()))
        try:
            data = self.sock.recv(settings.get('max_package_length', 1024))
            message = Message(data)
        except Exception:
            logger.error('Error connect to server', exc_info=True)
        logger.debug(f'Установлено соединение с сервером. Ответ сервера: {message}')
        print(f'Установлено соединение с сервером.')

        reciver = ClientReader(self.sock)
        reciver.daemon = True
        reciver.start()

        sender = ClientSender(self.sock)
        sender.daemon = True
        sender.start()

        # Watchdog основной цикл, если один из потоков завершён, то значит или потеряно соединение или пользователь
        # ввёл exit. Поскольку все события обработываются в потоках, достаточно просто завершить цикл.
        try:
            while True:
                time.sleep(1)
                if not reciver.is_alive() or not sender.is_alive():
                    break
        except KeyboardInterrupt:
            logger.debug('User closed')


class ClientReader(threading.Thread):
    ''' Класс-приёмник сообщений с сервера. Принимает сообщения, выводит в консоль.'''
    def __init__(self, sock):
        self.sock = sock
        super().__init__()

    def run(self):
        '''Основной цикл приёмника сообщений, принимает сообщения, выводит в консоль. Завершается при потере соединения.'''
        while True:
            try:
                message = self.read_data()
                if message:
                    if message.is_valid():
                        sender = getattr(message, settings.SENDER, None)
                        print(f'Message from {sender}:\n{message}')
                        logger.info(f'Получено сообщение от пользователя {sender}:\n{message}')
                    else:
                        logger.error(f'Получено некорректное сообщение с сервера: {message}')
            except Exception:
                logger.critical(f'Потеряно соединение с сервером.', exc_info=True)
                break

    def read_data(self):
        data = self.sock.recv(settings.get('max_package_length', 1024))
        if not data:
            return
        return Message(data)


class ClientSender(threading.Thread):
    '''Класс формировки и отправки сообщений на сервер и взаимодействия с пользователем.'''
    def __init__(self, sock):
        self.sock = sock
        super().__init__()

    def send_message(self, mes):
        try:
            self.sock.sendall(bytes(mes))
        except Exception:
            logger.critical('Потеряно соединение с сервером.')
            exit(1)

    def run(self):
        '''Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения'''
        main_commands.print_help()
        while True:
            command = input('Введите команду: ')
            if not main_commands.run(command, self):
                print('Команда не распознана. help - вывести поддерживаемые команды.')
