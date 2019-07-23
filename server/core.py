# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-21 12:27:35
# @Last Modified by:   maxst
# @Last Modified time: 2019-07-23 12:50:58
import logging
import select
import socket
import threading
from commands import main_commands

from dynaconf import settings

from descriptors import PortDescr
from jim_mes import Message
from metaclasses import ServerVerifier

logger = logging.getLogger('server')


class Server(metaclass=ServerVerifier):
    port = PortDescr()

    def __init__(self):
        self.clients = []
        self.messages = []
        self.names = {}
        self.started = False

    def init_socket(self):
        self.sock = socket.socket()
        self.port = settings.as_int('PORT')
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((settings.get('host'), self.port))
        self.sock.settimeout(0.5)
        self.sock.listen(settings.get('max_connections'))
        self.started = True
        logger.info(f'start with {settings.get("host")}:{self.port}')

    def main_loop(self):
        self.init_socket()
        try:
            while True:
                # Ждём подключения, если таймаут вышел, ловим исключение.
                try:
                    client, client_address = self.sock.accept()
                except OSError:
                    pass
                else:
                    logger.info(f'Установлено соедение с ПК {client_address}')
                    self.clients.append(client)

                recv_data = []
                send_data = []
                # Проверяем на наличие ждущих клиентов
                try:
                    if self.clients:
                        recv_data, send_data, _ = select.select(self.clients, self.clients, [], 0)
                except OSError:
                    pass

                # принимаем сообщения и если ошибка, исключаем клиента.
                if recv_data:
                    for client_with_message in recv_data:
                        self.to_thread(client_with_message, self.read_client_data)
                self.process(send_data)
        except KeyboardInterrupt:
            self.sock.close()
            logger.debug('closed')

    def read_client_data(self, client):
        try:
            data = client.recv(settings.get('max_package_length', 1024))
        except Exception:
            logger.info(f'Клиент {client.getpeername()} отключился от сервера.')
            self.clients.remove(client)
        if not data:
            return
        logger.debug(f'Client say: {data.decode(settings.get("encoding", "utf-8"))}')
        mes = Message(data)
        if mes.action == settings.get('presence'):
            mes.client = client
        self.messages.append(mes)

    def write_client_data(self, client, mes):
        try:
            client.sendall(bytes(mes))
        except BrokenPipeError:
            self.clients.remove(client)
            client.close()

    def process(self, send_data):
        try:
            for mes in self.messages:
                response = main_commands.run(mes, self, send_data=send_data)
                if response:
                    logger.debug(f'send response')
        except Exception:
            logger.error('Error process message', exc_info=True)
        self.messages.clear()

    def to_thread(self, client, target, *args):
        thread = threading.Thread(
            target=target,
            daemon=True,
            args=(client, *args),
        )
        thread.start()
