# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-06 23:40:29
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-19 11:44:20
import argparse
import logging
import os
import socket
from commands import main_commands

from jim_mes import Converter, Message
from pathlib import Path
from settings import Settings, default_settings


class Server(object):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((setting.get('host'), setting.get('port')))
        self.sock.listen(setting.get('workers'))
        self.logger = logging.getLogger(type(self).__name__)

    def run(self):
        try:
            self.logger.info(f'start with {setting.get("host")}:{setting.get("port")}')
            while True:
                client, address = self.sock.accept()
                with client:
                    self.logger.info(f'Connect client from {address}')
                    while True:
                        data = client.recv(setting.get('buffer_size', 1024))
                        if not data:
                            break
                        self.logger.debug(f'Client say: {data.decode(setting.get("encoding", "utf-8"))}')
                        mes = Message(loads=data)
                        response = main_commands.run(mes, logger=self.logger)
                        if response:
                            self.logger.debug('send response')
                            client.sendall(bytes(response))
                        else:
                            text_resp = f'Server is not know this a command "{mes.action}"'
                            self.logger.error(text_resp, exc_info=True)
                            client.sendall(bytes(Message.error_resp(text_resp)))
        except KeyboardInterrupt:
            self.sock.close()
            self.logger.debug('closed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs='?')
    parser.add_argument('-e',
                        '--encoding',
                        default=default_settings.get('ENCODING', None),
                        nargs='?',
                        help=f'Encoding (default "{default_settings.get("ENCODING")}")')
    parser.add_argument('-a',
                        '--address',
                        default=default_settings.get('HOST', None),
                        nargs='?',
                        help=f'IP (default "{default_settings.get("HOST")}")')
    parser.add_argument('-p',
                        '--port',
                        default=default_settings.get('PORT'),
                        nargs='?',
                        help=f'Port (default "{default_settings.get("PORT")}")')
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
