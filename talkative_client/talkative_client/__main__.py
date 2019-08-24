# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-20 10:44:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-25 00:29:56
import argparse
import asyncio
import logging
import logging.config
import os
import sys
import time
from pathlib import Path

from Cryptodome.PublicKey import RSA
from dynaconf import settings
from dynaconf.loaders import yaml_loader as loader
from PyQt5.QtWidgets import QApplication, QMessageBox

from talkative_client.async_core import ClientTransport
from talkative_client.core import Client
from talkative_client.gui import ClientGui, UserAuth

if getattr(sys, 'frozen', False):
    # frozen
    cfile = Path(sys.executable).parent
else:
    cfile = Path(__file__).parent

cwd = cfile
os.environ['ROOT_PATH_FOR_DYNACONF'] = str(cwd)

sys.argv += ['-style', 'Fusion']
client_app = QApplication(sys.argv)
auth = UserAuth()
message = QMessageBox()


def arg_parser():
    global auth
    parser = argparse.ArgumentParser()
    parser.description = 'Talkative - Client Messager for study'
    parser.add_argument('--config', nargs='?')
    parser.add_argument('-e', '--encoding', nargs='?', help=f'Encoding (default "{settings.get("ENCODING")}")')
    parser.add_argument('-a', '--host', nargs='?', help=f'IP (default "{settings.get("HOST")}")')
    parser.add_argument('-p', '--port', nargs='?', help=f'Port (default "{settings.get("PORT")}")')
    parser.add_argument('--no-async', dest='no_async', action='store_true', help='Start do not async client')
    parser.set_defaults(no_async=False)
    parser.add_argument(
        '-v',
        '--verbose',
        action='count',
        default=settings.get('LOGGING_LEVEL'),
        help=f'Increase verbosity of log output (default "{settings.get("LOGGING_LEVEL")}")',
    )
    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument('-g', '--gui', dest='gui', action='store_true', help='Start GUI Configuration')
    log_group.set_defaults(gui=settings.get('GUI'))
    log_group.add_argument('-c', '--console', dest='console', action='store_true', help='Start cli')
    log_group.set_defaults(console=settings.get('console'))

    parser.add_argument('-n', '--name', nargs='?', help='Name user for connect')
    parser.add_argument('--password', nargs='?', help='User password')

    namespace = parser.parse_args()

    if namespace.config:
        settings.load_file(path=namespace.config)

    for k, v in vars(namespace).items():
        if not v:
            continue
        settings.set(k, v)

    if namespace.name and namespace.password:
        settings.set('USER_NAME', namespace.name)
        passwd = namespace.password
    else:
        if settings.GUI:
            client_app.exec_()
            if auth.accepted:
                user_name, passwd = auth.get_auth()
                if not user_name or not passwd:
                    message.critical(auth, 'Ошибка', 'Логин или пароль не заданны')
                    sys.exit(0)
        else:
            user_name = settings.USER_NAME
            try:
                while not user_name or not passwd:
                    user_name = input('Введите имя пользователя\n:')
                    passwd = input('Введите пароль\n:')
            except KeyboardInterrupt:
                sys.exit(0)
    del auth
    settings.set('USER_NAME', user_name)
    settings.set('PASSWORD', passwd)

    _configure_logger(namespace.verbose)
    _process_key()


def _configure_logger(verbose=0):
    class MaxLevelFilter(logging.Filter):
        """Filters (lets through) all messages with level < LEVEL"""
        def __init__(self, level):
            self.level = level

        def filter(self, record):  # noqa
            return record.levelno <= self.level
            # and record.module in ('client', 'Converter', 'decorators', 'asyncio', 'async_core', 'core')

    root_logger = logging.root
    level = settings.get('LOGGING_LEVEL')

    log_dir = cwd.joinpath(Path(settings.get('LOG_DIR')))
    log_dir.mkdir(parents=True, exist_ok=True)

    stream_handler = logging.StreamHandler()
    stream_handler.addFilter(MaxLevelFilter(level))
    log_file_err = Path(f'{log_dir}/Client_{settings.USER_NAME}_error.log')
    error_handler = logging.FileHandler(log_file_err, encoding=settings.get('encoding'))
    error_handler.setLevel(logging.ERROR)
    log_file = Path(f'{log_dir}/Client_{settings.USER_NAME}.log')
    file_handler = logging.FileHandler(log_file, encoding=settings.get('encoding'))
    file_handler.addFilter(MaxLevelFilter(logging.INFO))
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[
            error_handler,
            file_handler,
            stream_handler,
        ],
    )

    if verbose == 0:
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG

    root_logger.setLevel(level)


def _process_key():
    """Загружаем ключи с файла, если же файла нет, то генерируем новую пару."""
    secret = f'.secret.{settings.USER_NAME}.yaml'
    settings.INCLUDES_FOR_DYNACONF.append(secret)
    key_file = Path.cwd().joinpath(Path(f'{secret}'))
    settings.load_file(path=key_file)
    key = settings.get('USER_KEY')
    if not key:

        keys = RSA.generate(2048, os.urandom)
        key = keys.export_key().decode('ascii')
        loader.write(key_file, {'DEFAULT': {
            'USER_KEY': key,
            'PASSWORD': settings.PASSWORD,
        }})
        settings.load_file(path=key_file)
        key = settings.get('USER_KEY')


arg_parser()

logger = logging.getLogger('client')
logger.debug(f'Connect to server {settings.get("host")}:{settings.get("port")} with name "{settings.USER_NAME}"')

print(f'Клиентский модуль запущен с именем: {settings.USER_NAME}')

if settings.get('no_async'):
    # modules command and other
    p = cwd
    if getattr(sys, 'frozen', False):
        # frozen
        p = cwd.joinpath(Path('lib/talkative_client'))

    for item in p.rglob('*.py'):
        if item.parent.stem == 'tests' or item.parent.stem == 'talkative_client':
            continue
        __import__(f'talkative_client.{item.parent.stem}.{item.stem}', globals(), locals())

    client = Client()
    client.connect()
else:
    client = ClientTransport()

    class WaitAuth:
        is_wait = True

        def update(self, c, event, *args, **kwargs):
            logger.info('WaitAuth', event)
            if event == 'done_auth':
                self.is_wait = False
            elif event == 'fail__auth':
                sys.exit()

        def wait(self):
            while self.is_wait:
                time.sleep(2)

    waiter = WaitAuth()
    client.attach(waiter, 'done_auth')
    client.attach(waiter, 'fail__auth')

    time.sleep(1)

    # waiter.wait()

    sys.argv += ['-style', 'Fusion']
    app = QApplication(sys.argv)
    client_gui = ClientGui(client)
    sys.exit(app.exec_())
    # receiver.new_message.connect(client.update)
    # receiver.up_all_users.connect(client.update)
    # receiver.response_key.connect(client.update)
    # sys.exit(app.exec_())
