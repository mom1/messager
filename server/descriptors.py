# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-21 12:32:49
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-29 01:30:24
import logging


logger = logging.getLogger('descriptors')


class PortDescr(object):
    """docstring for PortDescr self """

    def __init__(self, port=7777):
        super().__init__()
        self._port = port

    def __set__(self, inst, value):
        if isinstance(value, int) and 65535 > value >= 1024:
            self._port = value
        else:
            raise ValueError('Порт должен быть от 1024 до 65536')

    def __get__(self, inst, inst_type=None):
        return self._port
