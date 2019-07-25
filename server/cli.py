# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-07-23 22:59:32
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-25 09:24:59
import logging
from commands import AbstractCommand, icommands

from db import User

logger = logging.getLogger('cli')


class CommandLineInterface(object):
    def main_loop(self):
        icommands.print_help()
        try:
            while True:
                command = input('Введите комманду\n:')
                if not icommands.run(self, command):
                    print('Команда не распознана. help - вывести поддерживаемые команды.')
        except KeyboardInterrupt:
            logger.debug('User closed')


class QuitCommand(AbstractCommand):
    """Завершение работы сервера"""
    name = 'quit'

    def execute(self, cli, command, **kwargs):
        exit(0)


class UserListCommand(AbstractCommand):
    """Список известных пользователей"""
    name = 'users'

    def execute(self, cli, command, **kwargs):
        for user in User.all():
            print(f'Пользователь {user.username}, последний вход: {user.last_login}')
        return True


icommands.reg_cmd(QuitCommand)
icommands.reg_cmd(UserListCommand)
