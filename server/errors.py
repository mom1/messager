# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-07-25 08:36:49
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-25 08:39:23


class NotFoundUser(Exception):
    def __init__(self, user):
        self.user = user

    def __str__(self):
        return f'User {self.user} did not found'
