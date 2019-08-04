# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-07-25 08:36:49
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-27 22:43:25


class NotFoundUser(Exception):
    def __init__(self, user):
        self.user = user

    def __str__(self):
        return f'User {self.user} did not found'


class NotFoundContact(NotFoundUser):
    def __str__(self):
        return f'Contact {self.user} did not found'


class ContactExists(Exception):
    def __init__(self, user):
        self.user = user

    def __str__(self):
        return f'Contact {self.user} already exists'


class ContactNotExists(Exception):
    def __init__(self, user):
        self.user = user

    def __str__(self):
        return f'Contact {self.user} not exists'


class ServerError(Exception):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text
