# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-07-25 08:36:49
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-08 21:10:39


class NotFoundUser(Exception):
    """Ошибка поиска пользователя."""

    def __init__(self, user):
        """Инициализация.

        Args:
            user: пользователь

        """
        self.user = user

    def __str__(self):
        """Приведение к строке."""
        return f'User {self.user} did not found'
