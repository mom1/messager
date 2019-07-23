# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-20 10:44:30
# @Last Modified by:   maxst
# @Last Modified time: 2019-07-22 23:13:02
import argparse
import logging
import logging.config
from pathlib import Path

from dynaconf import settings
from core import Server


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.description = "Talkative - Server Messager for study"
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
    parser.add_argument('-g', '--gui', dest='gui', action='store_true', help='Start GUI Configuration')
    parser.set_defaults(gui=False)
    namespace = parser.parse_args()

    if namespace.config:
        settings.load_file(path=namespace.config)

    for k, v in vars(namespace).items():
        if not v:
            continue
        setattr(settings, k.upper(), v)

    _configure_logger(namespace.verbose)


def _configure_logger(verbose=0):
    root_logger = logging.root
    log_dir = Path(settings.get('LOG_DIR'))
    log_dir.mkdir(parents=True, exist_ok=True)
    error_handler = logging.FileHandler(f'{log_dir}/Server_error.log', encoding=settings.get('encoding'))
    error_handler.setLevel(logging.ERROR)
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[
            error_handler,
            logging.FileHandler(f'{log_dir}/Server.log', encoding=settings.get('encoding')),
            logging.StreamHandler(),
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
p = Path('./server')
for item in p.glob('**/*/*.py'):
    if item.parent.stem == 'tests':
        continue
    __import__(f'{item.parent.stem}.{item.stem}', globals(), locals())


serv = Server()
serv.main_loop()
