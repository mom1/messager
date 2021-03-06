# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-20 10:44:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-25 00:43:57
import argparse
import logging
import logging.config
import os
import sys
import time
from pathlib import Path

from dynaconf import settings
from PyQt5.QtWidgets import QApplication

from talkative_server.async_core import ServerA
from talkative_server.cli import CommandLineInterface
from talkative_server.core import Server
from talkative_server.gui import ServerGUI

if getattr(sys, 'frozen', False):
    # frozen
    cfile = Path(sys.executable).parent
else:
    cfile = Path(__file__).parent

cwd = cfile
os.environ['ROOT_PATH_FOR_DYNACONF'] = str(cwd)


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.description = 'Talkative - Server Messager for study'
    parser.add_argument('--config', nargs='?')
    parser.add_argument('-e', '--encoding', nargs='?', help=f'Encoding (default "{settings.get("ENCODING")}")')
    parser.add_argument('-a', '--host', nargs='?', help=f'IP (default "{settings.get("HOST")}")')
    parser.add_argument('-p', '--port', nargs='?', help=f'Port (default "{settings.get("PORT")}")')
    parser.add_argument('--no-async', dest='no_async', action='store_true', help='Start do not async server')
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
    namespace = parser.parse_args()

    if namespace.config:
        settings.load_file(path=namespace.config)

    for k, v in vars(namespace).items():
        if not v:
            continue
        settings.set(k, v)

    _configure_logger(namespace.verbose)


def _configure_logger(verbose=0):
    class MaxLevelFilter(logging.Filter):
        """Filters (lets through) all messages with level < LEVEL."""
        def __init__(self, level):
            self.level = level

        def filter(self, record):  # noqa
            return record.levelno <= self.level and record.module in ('server', 'Converter', 'decorators', 'asyncio', 'async_core', 'core')

    root_logger = logging.root
    level = settings.get('LOGGING_LEVEL')

    log_dir = cwd.joinpath(Path(settings.get('LOG_DIR')))
    log_dir.mkdir(parents=True, exist_ok=True)

    stream_handler = logging.StreamHandler()
    stream_handler.addFilter(MaxLevelFilter(level))
    log_error = Path(f'{log_dir}/Server_error.log')
    error_handler = logging.FileHandler(log_error, encoding=settings.get('encoding'))
    error_handler.setLevel(logging.ERROR)
    log_file = Path(f'{log_dir}/Server.log')
    file_log = logging.FileHandler(log_file, encoding=settings.get('encoding'))
    file_log.addFilter(MaxLevelFilter(logging.INFO))
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[
            error_handler,
            file_log,
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

# modules command and other
p = cwd
if getattr(sys, 'frozen', False):
    # frozen
    p = cwd.joinpath(Path('lib/talkative_server'))

for item in p.rglob('*.py'):
    if item.parent.stem == 'tests' or item.parent.stem == 'talkative_server':
        continue
    __import__(f'talkative_server.{item.parent.stem}.{item.stem}', globals(), locals())

if settings.get('no_async'):
    serv = Server()
    serv.daemon = True
    serv.start()
else:
    serv = ServerA()


time.sleep(1)

if settings.get('console'):
    CommandLineInterface().main_loop()
elif settings.get('gui'):
    sys.argv += ['-style', 'Fusion']
    app = QApplication(sys.argv)
    ServerGUI(serv)
    sys.exit(app.exec_())
else:
    pass
