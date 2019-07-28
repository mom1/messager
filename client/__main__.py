# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-20 10:44:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-28 21:13:26
import argparse
import logging
import logging.config
from pathlib import Path

from dynaconf import settings

from core import Client


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.description = 'Talkative - Client Messager for study'
    parser.add_argument('--config', nargs='?')
    parser.add_argument('-e', '--encoding', nargs='?', help=f'Encoding (default "{settings.get("ENCODING")}")')
    parser.add_argument('-a', '--host', nargs='?', help=f'IP (default "{settings.get("HOST")}")')
    parser.add_argument('-p', '--port', nargs='?', help=f'Port (default "{settings.get("PORT")}")')
    parser.add_argument(
        '-v',
        '--verbose',
        action='count',
        default=settings.get('LOGGING_LEVEL'),
        help=f'Increase verbosity of log output (default "{settings.get("LOGGING_LEVEL")}")',
    )
    parser.add_argument('-g', '--gui', dest='gui', action='store_true', help='Start GUI')
    parser.set_defaults(gui=False)

    parser.add_argument('-n', '--name', nargs='?', help=f'Name user for connect')

    namespace = parser.parse_args()

    if namespace.config:
        settings.load_file(path=namespace.config)

    for k, v in vars(namespace).items():
        if not v:
            continue
        settings.set(k, v)
    if namespace.name:
        settings.set('USER_NAME', namespace.name)
    _configure_logger(namespace.verbose)


def _configure_logger(verbose=0):
    class MaxLevelFilter(logging.Filter):
        """Filters (lets through) all messages with level < LEVEL"""
        def __init__(self, level):
            self.level = level

        def filter(self, record):  # noqa
            return record.levelno < self.level

    root_logger = logging.root
    level = settings.get('LOGGING_LEVEL')

    log_dir = Path(settings.get('LOG_DIR'))
    log_dir.mkdir(parents=True, exist_ok=True)

    stream_handler = logging.StreamHandler()
    stream_handler.addFilter(MaxLevelFilter(level))
    log_file_err = Path(f'{log_dir}/Client_error.log')
    error_handler = logging.FileHandler(log_file_err, encoding=settings.get('encoding'))
    error_handler.setLevel(logging.ERROR)
    log_file = Path(f'{log_dir}/Client.log')
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[
            error_handler,
            logging.FileHandler(log_file, encoding=settings.get('encoding')),
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


arg_parser()

try:
    while not settings.USER_NAME:
        settings.USER_NAME = input('Введите имя пользователя\n:')
except KeyboardInterrupt:
    exit(0)

logger = logging.getLogger('client')
logger.debug(f'Connect to server {settings.get("host")}:{settings.get("port")} with name "{settings.USER_NAME}"')

print(f'Клиентский модуль запущен с именем: {settings.USER_NAME}')

# modules command and other
p = Path('./client')
for item in p.glob('**/*/*.py'):
    if item.parent.stem == 'tests':
        continue
    __import__(f'{item.parent.stem}.{item.stem}', globals(), locals())

client = Client()
client.connect()
