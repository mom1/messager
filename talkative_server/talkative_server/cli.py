# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-07-23 22:59:32
# @Last Modified by:   maxst
# @Last Modified time: 2019-08-09 23:09:38
import logging

from tabulate import tabulate

from .commands import AbstractCommand, icommands
from .db import ActiveUsers, TypeHistory, User, UserHistory

logger = logging.getLogger('cli')


class CommandLineInterface(object):
    """Интерфейс командной строки.

    Принимает команды и передает их на обработку

    """

    def main_loop(self):
        """Основной цикл ждет ввода команды или Ctrl+C для выхода."""
        icommands.print_help()
        try:
            while True:
                command = input('Введите команду\n:')
                if not icommands.run(self, command):
                    print('Команда не распознана. help - вывести поддерживаемые команды.')
        except KeyboardInterrupt:
            logger.debug('User closed')


class QuitCommand(AbstractCommand):
    """Завершение работы сервера.

    Команда выхода из интерфейса сервера

    Attributes:
        name: имя команды в интерфейсе

    """

    name = 'quit'

    def execute(self, cli, command, **kwargs):
        """Выполнение команды.

        Args:
            cli: объект класса :py:class:`~CommandLineInterface`
            command: имя команды для выполнения
            **kwargs: дополнительные параметры

        """
        exit(0)


class UserListCommand(AbstractCommand):
    """Список известных пользователей.

    Выводит полный список всех пользователей

    Attributes:
        name: имя команды в интерфейсе

    """

    name = 'users'

    def execute(self, cli, command, **kwargs):
        """Выполнение команды.

        Args:
            cli: объект класса :py:class:`~CommandLineInterface`
            command: имя команды для выполнения
            **kwargs: дополнительные параметры

        Returns:
            Возвращает результат выполнения
            bool

        """
        tab = []
        for user in User.all():
            tab.append({'Пользователь': user.username, 'Последний вход': user.last_login})
        print()
        print(tabulate(
            tab,
            headers='keys',
            tablefmt='rst',
        ))
        print()
        return True


class ConnectedUsersCommand(AbstractCommand):
    """Список подключенных пользователей.

    Attributes:
        name: имя команды в интерфейсе

    """

    name = 'connected'

    def execute(self, cli, command, **kwargs):
        """Выполнение команды.

        Args:
            cli: объект класса :py:class:`~CommandLineInterface`
            command: имя команды для выполнения
            **kwargs: дополнительные параметры

        Returns:
            Возвращает результат выполнения
            bool

        """
        tab = []
        for auser in ActiveUsers.all():
            tab.append({
                'Пользователь': auser.oper.username,
                'HOST:PORT': f'{auser.ip_addr}:{auser.port}',
                'Последний вход': auser.oper.last_login,
            })
        print()
        print(tabulate(
            tab,
            headers='keys',
            tablefmt='rst',
        ))
        print()
        return True


class LoginHistoryCommand(AbstractCommand):
    """История входов пользователя.

    Attributes:
        name: имя команды в интерфейсе

    """

    name = 'loghist'

    def execute(self, cli, command, **kwargs):
        """Выполнение команды.

        Args:
            cli: объект класса :py:class:`~CommandLineInterface`
            command: имя команды для выполнения
            **kwargs: дополнительные параметры

        Returns:
            Возвращает результат выполнения
            bool

        """
        tab = []
        name = input('Введите имя пользователя для просмотра истории.\nДля вывода всей истории, просто нажмите Enter\n:')
        if name:
            user = User.by_name(name)
            qs = [i for i in user.history if i.type_row == TypeHistory.login]
        else:
            qs = UserHistory.all()

        for story in qs:
            tab.append({
                'Пользователь': story.oper.username,
                'Время входа': story.created,
                'HOST:PORT': f'{story.ip_addr}:{story.port}',
            })
        print()
        print(tabulate(
            tab,
            headers='keys',
            tablefmt='rst',
        ))
        print()
        return True


icommands.reg_cmd(QuitCommand)
icommands.reg_cmd(UserListCommand)
icommands.reg_cmd(ConnectedUsersCommand)
icommands.reg_cmd(LoginHistoryCommand)
