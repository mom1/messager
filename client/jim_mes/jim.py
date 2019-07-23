# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-07 11:20:56
# @Last Modified by:   maxst
# @Last Modified time: 2019-07-23 11:06:34
import time

from dynaconf import settings

from .convert import Converter


class Message(object):
    def __init__(self, loads=None, **kwargs):
        self.conv = Converter(type='json')
        date_format = kwargs.pop('date_format', '%Y-%m-%d %H:%M:%S')
        self.delimiter = kwargs.pop('delimiter', '\r\n')
        if loads:
            self.__raw = self.conv.reads(loads)
        else:
            self.__raw = kwargs
        self.__raw['time'] = time.strftime(date_format)
        self.required = (settings.ACTION, settings.SENDER, settings.DESTINATION, settings.MESSAGE_TEXT)

    def __bytes__(self):
        return f'{self.conv.dumps(self.__raw)}{self.delimiter}'.encode()

    def __str__(self):
        response = getattr(self, settings.MESSAGE_TEXT, self.__raw) or self.__raw
        resp = self.__raw.get('response', None)
        if resp == 400:
            response = f'client error:\n{self.error}'
        elif resp == 500:
            response = f'server error:\n{self.error}'
        return f'{response}'

    def __getattr__(self, attr):
        if attr and attr not in vars(self) and not hasattr(type(self), attr):
            return self.__raw[attr] if attr in self.__raw else None
        return super().__getattr__(attr)

    def is_valid(self):
        val = True
        for attr in self.required:
            if attr not in self.__raw:
                val = False
                break
        if settings.USER_NAME and val and getattr(self, settings.DESTINATION, None) != settings.USER_NAME:
            val = False
        return val

    @property
    def user_account_name(self):
        try:
            name = self.__raw.get('user', self.__raw.get(settings.DESTINATION))
        except ValueError:
            return None
        return name

    @classmethod
    def success(cls, response=200, **kwargs):
        return cls(response=response, **kwargs)

    @classmethod
    def error_resp(cls, text, **kwargs):
        return cls(response=400, error=text, **kwargs)

    @classmethod
    def error_request(cls, text, **kwargs):
        return cls(action=settings.ERROR, msg=text, **kwargs)

    @classmethod
    def presence(cls, type_='status', user=None, **kwargs):
        return cls(action=settings.PRESENCE, type=type_, user=user or settings.USER_NAME, **kwargs)

    @classmethod
    def exit_request(cls, user=None, **kwargs):
        return cls(action=settings.EXIT, user=user or settings.USER_NAME, **kwargs)
