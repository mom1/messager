# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-07 11:20:56
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-09 00:13:53
import time

from Cryptodome.PublicKey import RSA
from dynaconf import settings

from .convert import Converter


class Message(object):
    """Класс сообщения.

    Отдает свои атребуты как ключи из данных и без генерации
    ошибок

    """

    def __init__(self, loads=None, **kwargs):  # noqa
        self.conv = Converter(type='json')
        date_format = kwargs.pop('date_format', '%Y-%m-%d %H:%M:%S')
        self.delimiter = kwargs.pop('delimiter', '\r\n')
        if loads:
            self.__raw = self.conv.reads(loads)
        else:
            self.__raw = kwargs
        self.__raw['time'] = time.strftime(date_format)
        self.required = (settings.ACTION, settings.SENDER, settings.DESTINATION, settings.MESSAGE_TEXT)

    def __bytes__(self):  # noqa
        return f'{self.conv.dumps(self.__raw)}{self.delimiter}'.encode()

    def __str__(self):  # noqa
        response = getattr(self, settings.MESSAGE_TEXT, self.__raw) or self.__raw
        resp = self.__raw.get('response', None)
        if resp == 400:
            response = f'client error:\n{self.error}'
        elif resp == 500:
            response = f'server error:\n{self.error}'
        return f'{response}'

    def __getattr__(self, attr):  # noqa
        if attr and attr not in vars(self) and not hasattr(type(self), attr):
            return self.__raw[attr] if attr in self.__raw else None
        return super().__getattr__(attr)

    def is_valid(self):
        """Проверка на валидность сообщения."""
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
        """Имя пользователя."""
        try:
            name = self.__raw.get('user', self.__raw.get(settings.DESTINATION))
        except ValueError:
            return None
        return name

    @classmethod
    def success(cls, response=200, **kwargs):
        """Сообщение об успехе.

        Args:
            response: код ответа (default: {200})
            **kwargs: доп. параметры

        Returns:
            Возвращает себя инициализированного
            Message

        """
        return cls(response=response, **kwargs)

    @classmethod
    def error_resp(cls, text, **kwargs):
        """Ошибка запроса пользователя.

        Args:
            text: [description]
            **kwargs: [description]

        Returns:
            Возвращает себя инициализированного
            Message

        """
        return cls(response=400, error=text, **kwargs)

    @classmethod
    def error_request(cls, text, **kwargs):
        """Ошибка.

        Args:
            text: [description]
            **kwargs: [description]

        Returns:
            Возвращает себя инициализированного
            Message

        """
        return cls(action=settings.ERROR, msg=text, **kwargs)

    @classmethod
    def presence(cls, type_='status', user=None, pub_key=None, **kwargs):
        """Презентационное сообщение.

        Args:
            user: имя пользователя (default: {None})
            type_: тип (default: {'status'})
            **kwargs: доп. параметры

        Returns:
            Возвращает себя инициализированного
            Message

        """
        kwargs[settings.PUBLIC_KEY] = pub_key or RSA.import_key(settings.get('USER_KEY')).publickey().export_key().decode('ascii')
        return cls(action=settings.PRESENCE, type=type_, user=user or settings.USER_NAME, **kwargs)

    @classmethod
    def exit_request(cls, user=None, **kwargs):
        """Сообщение о завершении сеанса.

        Args:
            user: имя пользователя (default: {None})
            **kwargs: [description]

        Returns:
            [description]
            [type]

        """
        return cls(action=settings.EXIT, user=user or settings.USER_NAME, **kwargs)
