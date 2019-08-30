# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-05-25 22:33:58
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-30 09:35:54
import logging
import sys
import threading

import sqlalchemy as sa
from dynaconf import settings
from sqlalchemy.engine import Engine

from .metaclasses import SingletonMeta

logger = logging.getLogger('server__db')
database_lock = threading.Lock()


class DBManager(metaclass=SingletonMeta):
    """Менеджер инициатор БД."""
    def __init__(self, envs, *args, **kwargs):
        """Инициализация.

        Args:
            envs: имя области БД
            *args: доп. параметры
            **kwargs: доп. параметры

        """
        self.envs = envs
        super().__init__()
        self._setup(*args, **kwargs)

    @staticmethod
    @sa.event.listens_for(Engine, 'connect')
    def set_sqlite_pragma(dbapi_connection, connection_record=None):
        """Параметры подключения к БД.

        Пока не знаю как от этого отделаться при других бекэндах

        Args:
            dbapi_connection: [description]
            connection_record: [description] (default: {None})

        """
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA synchronous = 0')
        cursor.execute('PRAGMA mmap_size = 268435456')
        cursor.execute('PRAGMA cache_size = 20480')  # 20 mb
        cursor.close()

    def _setup(self, *args, **kwargs):
        """Установка БД.

        Args:
            *args: доп. параметры
            **kwargs: доп. параметры

        """
        db = settings.get('DATABASES')

        if not db:
            logger.critical('DATABASES setting required')
            sys.exit(1)
        self.db_settings = db.get(self.envs, db.get('default'))
        if not self.db_settings:
            logger.critical(f'DATABASE setting need for {self.envs}')
            sys.exit(1)

        engine = self.db_settings.get('ENGINE')
        if not self.db_settings:
            logger.critical(f'Fill ENGINE in database settings')
            sys.exit(1)

        self.module = __import__(f'talkative_server.db_{engine.lower()}', globals(), locals(), ['*'])

        if hasattr(self.module, f'init_{engine.lower()}'):
            getattr(self.module, f'init_{engine.lower()}')(self.db_settings)

    def __getattr__(self, attr):
        return getattr(self.module, attr)
