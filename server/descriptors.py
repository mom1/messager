# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-21 12:32:49
# @Last Modified by:   maxst
# @Last Modified time: 2019-07-21 12:33:21
import logging


logger = logging.getLogger('descriptors')


class PortDescr(object):
    """docstring for PortDescr self """

    def __init__(self, port=7777):
        super().__init__()
        self._port = port

    def __set__(self, inst, value):
        if isinstance(value, int) and 65535 > value >= 0:
            self._port = value
        else:
            raise ValueError('Порт должен быть int и 65535 > port >= 0')

    def __get__(self, inst, inst_type=None):
        return self._port
