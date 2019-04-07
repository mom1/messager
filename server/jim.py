# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-07 11:20:56
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-08 00:13:02
import time
from convert import Converter
from settings import Settings

settings = Settings.get_instance()


class Message(object):
    def __init__(self, loads=None, **kwargs):
        self.conv = Converter(type='json')
        if loads:
            self.__raw = self.conv.reads(loads)
        else:
            self.__raw = kwargs
        self.__raw['time'] = time.strftime(settings.get('date_format'))

    def __bytes__(self):
        return f'{self.conv.dumps(self.__raw)}{settings.get("delimiter")}'.encode()

    def __str__(self):
        return '{mes}'.format(mes=self.__raw['text'])

    def __getattr__(self, attr):
        if attr and attr not in vars(self) and not hasattr(type(self), attr):
            return self.__raw[attr] if attr in self.__raw else None
        return super().__getattr__(attr)

    @property
    def user_account_name(self):
        try:
            name = self.__raw['user']['account_name']
        except ValueError:
            return None
        return name

    @classmethod
    def success(cls, response=200, **kwargs):
        return cls(response=response, **kwargs)

    @classmethod
    def error(cls, text, **kwargs):
        return cls(response=400, error=text, **kwargs)

    @classmethod
    def error_request(cls, text, **kwargs):
        return cls(action='error', msg=text, **kwargs)

    @classmethod
    def presence(cls, type_='status', user=None):
        return cls(action='presence', type=type_, user=user)
