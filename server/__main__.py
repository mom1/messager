# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-06 23:40:29
# @Last Modified by:   MaxST
# @Last Modified time: 2019-06-01 18:56:23
import argparse
import dis
import logging
import os
import select
import socket
import threading
from commands import main_commands
from pathlib import Path

from jim_mes import Converter, Message

from db import DBManager
from settings import Settings, default_settings


class PortDescr(object):
    """docstring for PortDescr self """

    def __init__(self, port=7777):
        super().__init__()
        self._port = port

    def __set__(self, inst, value):
        if isinstance(value, int) and 65535 > value >= 0:
            self._port = value
        else:
            raise ValueError('Порт должен быть int и 65535 > port >= 0')

    def __get__(self, inst, inst_type=None):
        return self._port


class ServerVerifier(type):
    def __new__(cls, name, bases, attr_dict):
        """
            Тут находим объявление сокета и проверяем его инициализацию,
            кэшируем имя атрибута
        """
        cls.store_soc = None
        for key, val in attr_dict.items():
            assert not isinstance(val, socket.socket), 'Создание сокетов на уровне классов запрещенно'
            if key == '__classcell__' or isinstance(val, PortDescr):
                continue
            instrs = tuple(dis.Bytecode(val))
            glob_soc = (tuple(filter(lambda x: x.opname == 'LOAD_GLOBAL' and x.argval == 'socket', instrs)) or (None, ))[0]
            cls.store_soc = next((i for i in instrs[instrs.index(glob_soc):] if i.opname == 'STORE_ATTR'), None) if not cls.store_soc and glob_soc else cls.store_soc
            tcp_param = next((j for j in instrs[instrs.index(glob_soc):instrs.index(cls.store_soc)] if j.arg == 13), None) if glob_soc and cls.store_soc else None
            if tcp_param:
                assert tcp_param.argval == 'SOCK_STREAM', 'Использование сокетов возможно только по TCP'
        return super().__new__(cls, name, bases, attr_dict)

    def __init__(cls, name, bases, attr_dict):
        """
            Т.к в предыдущей функции использовался дикт
            мы могли пропустить вызовы интересующего метода
            тут еще раз просматриваем все и ищем вызовы.
            Но т.к. __new__ и __init__ вызываются последовательно
            для каждого класса остается дыра в виде вызова в родительском классе.
        """
        if cls.store_soc:
            checks_meth = ('connect', )
            for key, val in attr_dict.items():
                if key == '__classcell__' or isinstance(val, PortDescr):
                    continue
                instrs = tuple(dis.Bytecode(val))
                socks = (i for i in instrs if i.argval == cls.store_soc.argval)
                for sock in socks:
                    calls = instrs[instrs.index(sock) + 1]
                    # python 3.7 !!!LOAD_METHOD!!!
                    assert not (calls.argval in checks_meth and calls.opname == 'LOAD_METHOD'), f'Для сокетов запрещенно вызывать методы {checks_meth}'
        super().__init__(name, bases, attr_dict)


class Server(metaclass=ServerVerifier):
    port = PortDescr()

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.sock = socket.socket()
        self.port = int(setting.get('port'))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((setting.get('host'), self.port))
        self.sock.listen(setting.get('workers'))
        # self.sock.settimeout(0.3)
        self.sock.setblocking(False)
        self.logger = logging.getLogger(type(self).__name__)
        self.connections, self.outputs, self.inputs = [], [], []

    def run(self):
        DBManager.get_instance()
        try:
            self.logger.info(f'start with {setting.get("host")}:{self.port}')
            while True:
                try:
                    client, address = self.sock.accept()
                except OSError:
                    pass
                else:
                    self.connections.append(client)
                    self.logger.info(f'Connect client from {address}')
                finally:
                    r = []
                    w = []
                    try:
                        r, w, _ = select.select(self.connections, self.connections, [], 0)
                    except Exception:
                        self.logger.error('Exception until I/O select', exc_info=True)

                    self.receive(r)
                    self.process()
                    self.send(w)

        except KeyboardInterrupt:
            self.sock.close()
            self.logger.debug('closed')

    def receive(self, clients):
        self.to_thread(clients, self.read_client_data)

    def read_client_data(self, client):
        try:
            data = client.recv(setting.get('buffer_size', 1024))
        except Exception:
            return
        if not data:
            return
        self.logger.debug(f'Client say: {data.decode(setting.get("encoding", "utf-8"))}')
        self.inputs.append(Message(loads=data))

    def process(self):
        while len(self.inputs):
            mes = self.inputs.pop(0)
            response = main_commands.run(mes, logger=self.logger)
            if response:
                self.logger.debug('send response')
                self.outputs.append(response)
            else:
                text_resp = f'Server is not know this a command "{mes.action}"'
                self.logger.error(text_resp, exc_info=True)
                self.outputs.append(Message.error_resp(text_resp))
                self.inputs.append(mes)

    def send(self, clients):
        while len(self.outputs):
            mes = self.outputs.pop(0)
            self.to_thread(clients, self.write_client_data, mes)

    def write_client_data(self, client, mes):
        client.sendall(bytes(mes))

    def to_thread(self, clients, target, *args):
        for client in clients:
            thread = threading.Thread(
                target=target,
                args=(client, *args),
            )
            thread.start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs='?')
    parser.add_argument('-e', '--encoding', default=default_settings.get('ENCODING', None), nargs='?', help=f'Encoding (default "{default_settings.get("ENCODING")}")')
    parser.add_argument('-a', '--address', default=default_settings.get('HOST', None), nargs='?', help=f'IP (default "{default_settings.get("HOST")}")')
    parser.add_argument('-p', '--port', default=default_settings.get('PORT'), nargs='?', help=f'Port (default "{default_settings.get("PORT")}")')
    namespace = parser.parse_args()

    environ = {k: v for k, v in os.environ.items() if k in default_settings}
    command_line_args = {k: v for k, v in vars(namespace).items() if v}
    config = [{}]

    if namespace.config:
        conv = Converter(file_name=namespace.config)
        config = []
        for row in conv.read():
            config.append({k.lower(): v for k, v in row.items()})
    setting = Settings.get_instance(command_line_args, *config, environ)

    # loging
    error_handler = logging.FileHandler(f'server/log/Server_error.log', encoding=setting.get('encoding'))
    error_handler.setLevel(logging.ERROR)
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(module)s: %(message)s',
        handlers=[
            error_handler,
            logging.FileHandler(f'server/log/Server.log', encoding=setting.get('encoding')),
            logging.StreamHandler(),
        ],
    )
    # modules command and other
    p = Path('./server')
    for item in p.glob('**/*/*.py'):
        if item.parent.stem == 'tests':
            continue
        __import__(f'{item.parent.stem}.{item.stem}', globals(), locals())

    Server().run()
