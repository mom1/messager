# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-03-30 12:35:08
# @Last Modified by:   MaxST
# @Last Modified time: 2019-06-01 18:55:08
import argparse
import logging
import os
import selectors
import socket
import threading
from commands import main_commands
from pathlib import Path
from random import randint

from jim_mes import Converter, Message

import clients
from settings import Settings, default_settings

logging.basicConfig(
    level=logging.CRITICAL,
    format='%(name)s: %(message)s',
)

sel = selectors.DefaultSelector()


class Client(clients.AbstractClient):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.logger = logging.getLogger(type(self).__name__)
        self.client = kwargs.get('client', clients.ClientConsole())
        self.sock = socket.socket()
        self.sock.setblocking(False)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        sel.register(self.sock, events)

    def connect(self, *args, **kwargs):
        self.logger.debug(f'connect to server {setting.get("host")}:{setting.get("port")}')
        self.sock.connect_ex((setting.get('host'), setting.get('port')))
        self.sock.sendall(bytes(Message.presence(user=setting.get('user', None))))
        try:
            thread = threading.Thread(target=self.receive_data, daemon=True)
            thread.start()
            while True:
                events = sel.select(timeout=1)
                for _, mask in events:
                    if mask & selectors.EVENT_WRITE:
                        messsage = self.input_data()
                        if messsage is not False and messsage:
                            is_command = main_commands.run(self.prep_data(messsage), logger=self.logger)
                            if is_command:
                                continue
                            self.send_data(messsage)

                        elif messsage is False:
                            self.sock.close()
                            break
        except KeyboardInterrupt:
            self.logger.debug('')
            self.logger.debug('connect closed')
            return False

    def input_data(self, *args, **kwargs):
        return self.client.input_data(*args, **kwargs)

    def prep_data(self, data=None, loads=None, **kwargs):
        self.logger.debug(f'prepare data for :{data or loads}')
        kwargs['user'] = setting.get('user', None)
        if 'action' not in kwargs:
            kwargs['action'] = 'msg'
            kwargs['text'] = data
        param = {'loads': loads} if loads else kwargs
        return Message(**param)

    def send_data(self, mes='', *args, **kwargs):
        self.logger.debug(f'{"*" * 15} DATA SEND TO SERVER {"*" * 15}')
        self.sock.sendall(bytes(self.prep_data(mes, **kwargs)))

    def receive_data(self, *args, **kwargs):
        while True:
            events = sel.select(timeout=None)
            print(events)
            for _, mask in events:
                if mask & selectors.EVENT_READ:
                    data = self.sock.recv(setting.get('buffer_size', 1024))
                    response = self.prep_data(loads=data)
                    if response.action == 'request':
                        resp = self.input_data(text=response.text)
                        self.send_data(action=response.destination, param=resp)
                    self.client.show_mes(response)


if __name__ == '__main__':
    environ = {k.lower(): v for k, v in os.environ.items() if k in default_settings}
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
        default=environ.get('user', f'Anonymous_{randint(1, 1000)}'),
        nargs='?',
        help='User name (default Anonymous_XXXX)',
    )
    parser.add_argument('-r', '--receiver', dest='receiver', action='store_true')
    parser.set_defaults(receiver=False)
    namespace = parser.parse_args()

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

    p = Path('./client')
    for item in p.glob('**/*/*.py'):
        __import__(f'{item.parent.stem}.{item.stem}', globals(), locals())

    Client(client=client).connect()
