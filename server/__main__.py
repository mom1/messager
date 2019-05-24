# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-06 23:40:29
# @Last Modified by:   MaxST
# @Last Modified time: 2019-05-24 22:46:29
import argparse
import logging
import os
import select
import socket
import threading
from commands import main_commands
from pathlib import Path

from jim_mes import Converter, Message

from settings import Settings, default_settings


class Server(object):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((setting.get('host'), setting.get('port')))
        self.sock.listen(setting.get('workers'))
        self.sock.settimeout(0)
        self.logger = logging.getLogger(type(self).__name__)
        self.connections, self.outputs, self.inputs = [], [], []

    def run(self):
        try:
            self.logger.info(f'start with {setting.get("host")}:{setting.get("port")}')
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
