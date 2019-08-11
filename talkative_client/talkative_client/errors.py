# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-07-25 08:36:49
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-08 23:49:47


class NotFoundUser(Exception):
    """Ошибка не найден пользователь."""

    def __init__(self, user):  # noqa
        self.user = user

    def __str__(self):  # noqa
        return f'User {self.user} did not found'


class NotFoundContact(NotFoundUser):
    """Не найден контакт."""

    def __str__(self):  # noqa
        return f'Contact {self.user} did not found'


class ContactExists(Exception):
    """Контакт существует."""

    def __init__(self, user):  # noqa
        self.user = user

    def __str__(self):  # noqa
        return f'Contact {self.user} already exists'


class ContactNotExists(Exception):
    """Контакт не существует."""

    def __init__(self, user):  # noqa
        self.user = user

    def __str__(self):  # noqa
        return f'Contact {self.user} not exists'


class ServerError(Exception):
    """Ошибка сервера."""

    def __init__(self, text):  # noqa
        self.text = text

    def __str__(self):  # noqa
        return self.text
