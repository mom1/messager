# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-21 12:27:35
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-17 20:42:59
import logging
import select
import socket
import struct
import threading

from dynaconf import settings

from .commands import main_commands
from .db import DBManager
from .descriptors import PortDescr
from .jim_mes import Message
from .metaclasses import ServerVerifier

app_name = 'server'
logger = logging.getLogger(app_name)

database_lock = threading.Lock()


class Server(threading.Thread, metaclass=ServerVerifier):
    """Основной транспортный сервер.

    Не блокирующий сервер приема сообщений и обработки

    Attributes:
        port: Дескриптор значения порта для подключения
        clients: Лист сокетов подключенных клиентов
        messages: Список сообщений для обработки
        started: Признак запущенности сервера :)
        db_lock: Блокировщик потока доступа к БД
        _observers: Подписчики на события сервера (языковая реализация)

    """

    port = PortDescr()

    def __init__(self):
        """Инициализация."""
        super().__init__()
        self.clients = []
        self.messages = []
        self.names = {}
        self.started = False
        self.db_lock = database_lock
        self._observers = {}

    def attach(self, observer, event):
        """Подписка на события сервера.

        список событий не фиксирован

        Args:
            observer: Объект наблюдатель.
            event: Строка имени события.

        Returns:
            Признак удачного выполнения
            bool

        """
        obs = self._observers.get(event, []) or []
        obs.append(observer)
        self._observers[event] = obs
        logger.info(f'{observer} подписался на событие {event}')
        return True

    def detach(self, observer, event):
        """Отписаться от события.

        Args:
            observer: Объект наблюдатель.
            event: Строка имени события.

        Returns:
            Признак удачного выполнения
            bool

        """
        obs = self._observers.get(event, []) or []
        obs.remove(observer)
        self._observers[event] = obs
        logger.info(f'{observer} отписался от события {event}')
        return True

    def notify(self, event):
        """Уведомление о событии.

        У подписчика вызывается метод **update**

        Args:
            event: Строка имени произошедшего события.

        """
        obs = self._observers.get(event, []) or []
        for observer in obs:
            observer.update(self, event)

    def init_socket(self):
        """Инициализация сокета."""
        self.sock = socket.socket()
        self.port = settings.as_int('PORT')
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((settings.get('host'), self.port))
        self.sock.settimeout(1)
        self.sock.listen(settings.get('max_connections'))
        self.started = True
        logger.info(f'start with {settings.get("host")}:{self.port}')

    def run(self):
        """Запуск основного цикла."""
        self.init_socket()
        self.database = DBManager(app_name)
        try:
            while self.started:
                # Ждём подключения, если таймаут вышел, ловим исключение.
                try:
                    client, client_address = self.sock.accept()
                except OSError:
                    pass
                else:
                    logger.info(f'Установлено соединение с ПК {client_address}')
                    self.clients.append(client)

                recv_data = []
                send_data = []
                # Проверяем на наличие ждущих клиентов
                try:
                    if self.clients:
                        recv_data, send_data, _ = select.select(self.clients, self.clients, [], 0)
                except OSError:
                    continue

                # принимаем сообщения и если ошибка, исключаем клиента.
                if recv_data:
                    for client_with_message in recv_data:
                        self.read_client_data(client_with_message)
                self.process(send_data)
        except KeyboardInterrupt:
            self.sock.close()
            self.started = False
            logger.debug('closed')

    def stop(self):
        self.started = False
        self.sock.close()
        logger.debug('stoped')

    def read_client_data(self, client):
        """Чтение из сокета.

        Args:
            client: Сокет клиента из которого будет производится чтение

        """
        mes = self.read_data(client)
        if mes:
            if mes.action == settings.get('presence'):
                mes.client = client
            self.messages.append(mes)

    def read_data(self, client):
        mes = None
        try:
            raw_msglen = self.recvall(4, client)
            if not raw_msglen:
                return
            msglen = struct.unpack('>I', raw_msglen)[0]
            # Получение данных
            data = self.recvall(msglen, client)
        except Exception:
            logger.info(f'Клиент {client.getpeername()} отключился от сервера.')
            self.clients.remove(client)
        else:
            if not data:
                return
            logger.debug(f'Client say: {data.decode(settings.get("encoding", "utf-8"))}')
            mes = Message(data)
        return mes

    def recvall(self, n, sock):
        """Функция для получения n байт или возврата None если получен EOF

        Args:
            n: Количество получаемых байт
            sock: Сокет для чтения

        Returns:
            Полученные данные
            bytes
        """
        data = b''
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return
            data += packet
        return data

    def write_client_data(self, client, mes):
        """Запись в сокет.

        При возникновении BrokenPipeError удаляем клиента из списка прослушивания

        Args:
            client: Сокет клиента в который будет производится запись
            mes: Объект сообщения который будет записан

        """
        try:
            msg = bytes(mes)
            msg = struct.pack('>I', len(msg)) + msg
            client.sendall(msg)
        except BrokenPipeError:
            self.clients.remove(client)
            client.close()

    def process(self, send_data):
        """Обработка сообщений и команд.

        Перебор сообщений и отправка их основному объекту команд

        Args:
            send_data: Набор сокетов клиентов готовых к приему сообщений

        """
        try:
            for mes in self.messages:
                response = main_commands.run(self, mes, send_data=send_data)
                if response:
                    logger.debug(f'send response')
        except Exception:
            logger.error('Error process message', exc_info=True)
        self.messages.clear()

    def service_update_lists(self):
        """Сервисное сообщение 205 с требованием клиентам обновить списки."""
        for name, client in self.names.items():
            try:
                self.write_client_data(client, Message(response=205))
            except OSError:
                self.clients.remove(client)
                del self.names[name]
