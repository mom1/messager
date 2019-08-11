# -*- coding: utf-8 -*-
"""Набор дескрипторов."""
# @Author: maxst
# @Date:   2019-07-21 12:32:49
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-08 21:09:21
import logging


logger = logging.getLogger('descriptors')


class PortDescr(object):
    """Дескриптор порта.

    проверяет значение на вхождение в диапозон

    """

    def __init__(self, port=7777):
        """Инициация.

        Args:
            port: порт подклюбчения (default: {7777})

        """
        super().__init__()
        self._port = port

    def __set__(self, inst, value):
        """Присваивание значения.

        Args:
            inst: Инстанс
            value: Значение

        Raises:
            ValueError: При не выполнении условий

        """
        if isinstance(value, int) and 65535 > value >= 1024:
            self._port = value
        else:
            raise ValueError('Порт должен быть от 1024 до 65536')

    def __get__(self, inst, inst_type=None):
        """Получение значения.

        Args:
            inst: инстанс
            inst_type: тип инстанса (default: {None})

        Returns:
            Возвращает значение
            int

        """
        return self._port
