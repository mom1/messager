# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-03-30 12:35:39
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-21 12:32:12
from collections import ChainMap

default_settings = {
    'ENCODING': 'utf-8',
    'HOST': 'localhost',
    'PORT': 7777,
    'USER': None,
}


class Settings(ChainMap):
    __instance = None

    @classmethod
    def get_instance(cls, *args, **kwargs):
        if not cls.__instance or args:
            args += ({k.lower(): v for k, v in default_settings.items()},)
            cls.__instance = Settings(*args, **kwargs)
        return cls.__instance
