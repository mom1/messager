# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-03-30 12:35:08
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-08 00:38:54
import argparse
import logging
import os
import socket
from random import randint

import clients
from convert import Converter
from jim import Message
from settings import Settings, default_settings

logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s: %(message)s',
)


class Client(clients.AbstractClient):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.logger = logging.getLogger(type(self).__name__)
        self.client = kwargs.get('client', clients.ClientConsole())
        self.sock = socket.socket()

    def connect(self, *args, **kwargs):
        self.logger.debug(f'connect to server {setting.get("host")}:{setting.get("port")}')
        self.sock.connect((setting.get('host'), setting.get('port')))
        self.sock.sendall(bytes(Message.presence(user=setting.get('user', None))))
        resp_mes = self.sock.recv(setting.get('buffer_size', 1024))
        response = Message(loads=resp_mes)
        if response.response != 200:
            return self.logger.debug(f'connect error: {response}')
        for messsage in self.client.connect(*args, **kwargs):
            if messsage is not False and messsage:
                self.send_data(messsage)
            elif messsage is False:
                self.sock.close()
                break

    def input_data(self, *args, **kwargs):
        self.client.input_data(*args, **kwargs)

    def prep_data(self, data=None, loads=None):
        self.logger.debug(f'prepare data for :{data}')
        param = {'loads': loads} if loads else {'action': 'msg', 'text': data}
        return Message(**param)

    def send_data(self, mes, *args, **kwargs):
        self.logger.debug(f'{"*" * 15} DATA SEND TO SERVER {"*" * 15}')
        self.sock.sendall(bytes(self.prep_data(mes)))
        self.receive_data()

    def receive_data(self, *args, **kwargs):
        data = self.sock.recv(setting.get('buffer_size', 1024))
        self.client.show_mes(self.prep_data(loads=data))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs='?')
    parser.add_argument(
        '--client',
        default='console',
        nargs='?',
        choices=['gui', 'console'],
        help='Client for run (default "console")',
    )
    parser.add_argument(
        '-e',
        '--encoding',
        default=default_settings.get('ENCODING', None),
        nargs='?',
        help=f'Encoding (default "{default_settings.get("ENCODING")}")',
    )
    parser.add_argument(
        '-a',
        '--address',
        default=default_settings.get('HOST', None),
        nargs='?',
        help=f'IP (default "{default_settings.get("HOST")}")',
    )
    parser.add_argument(
        '-p',
        '--port',
        default=default_settings.get('PORT'),
        nargs='?',
        help=f'Port (default "{default_settings.get("PORT")}")',
    )
    parser.add_argument(
        '-u',
        '--user',
        default=f'Anonymous_{randint(1, 1000)}',
        nargs='?',
        help='User name (default Anonymous_XXXX)',
    )
    namespace = parser.parse_args()

    environ = {k: v for k, v in os.environ.items() if k in default_settings}
    command_line_args = {k: v for k, v in vars(namespace).items() if v}
    config = [{}]

    if namespace.client == 'gui':
        pass
    else:
        client = clients.ClientConsole()

    if namespace.config:
        conv = Converter(file_name=namespace.config)
        config = []
        for row in conv.read():
            config.append({k.lower(): v for k, v in row.items()})
    setting = Settings.get_instance(command_line_args, *config, environ)
    Client(client=client).connect()
