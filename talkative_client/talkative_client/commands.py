# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-04 22:05:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-10 00:37:32
import logging
import time
from collections import OrderedDict

from tabulate import tabulate

from .jim_mes import Message

logger = logging.getLogger('commands')


class Comander(object):
    """Основной командир, распределяет команды.

    Attributes:
        commands: Хранилище команд

    """

    def __init__(self, *args, **kwargs):
        """Инициализация."""
        super().__init__()
        self.commands = {}

    def run(self, name_cmd, *args, **kwargs):
        """Основной цикл запуска команд.

        Args:
            serv: экземпляр класса :py:class:`~core.Server`
            request: экземпляр класса :py:class:`~jim_mes.Message`
            *args: дополнительные параметры для команды
            **kwargs: дополнительные параметры для команды

        Returns:
            Возвращаем ответ команды
            bool

        """
        response = None
        cmd = self.commands.get(name_cmd, None)
        if cmd:
            logger.debug(f'I found command {cmd}')
            response = cmd(*args, **kwargs).execute(*args, **kwargs)
        elif name_cmd == 'help':
            response = self.print_help()
        return response

    def reg_cmd(self, command, name=None):
        """Регистрация команды.

        Регистрирует команду по переданному имени или атрибуту name

        Args:
            command: класс команды унаследованный от :py:class:`~AbstractCommand`
            name: имя для регистрации (default: {None})

        Raises:
            ValueError: Если имя для регистрации уже занято

        """
        name = getattr(command, 'name', None) if not name else name
        if name in self.commands:
            raise ValueError(f'Name exists {name}')
        self.commands[name] = command

    def unreg_cmd(self, command):
        """Отмена регистрации команды.

        Args:
            command: имя команды для удаления

        """
        if command in self.commands:
            del self.commands[command]

    def print_help(self):
        """Функция выводящия справку по использованию."""
        print('Поддерживаемые команды:')
        sort_dict = OrderedDict(sorted(self.commands.items()))
        print(tabulate(((k, v.__doc__) for k, v in sort_dict.items())))
        print('help - Вывести подсказки по командам')
        return True


class AbstractCommand(object):
    """Абстрактный класс команды."""

    def __init__(self, *args, **kwargs):
        """Инициализация."""
        super().__init__()

    def execute(self, message, **kwargs):
        """Выполнение."""
        pass


class ExitCommand(AbstractCommand):
    """Выход пользователя.

    Attributes:
        name: имя команды

    """

    name = 'exit'

    def execute(self, client, *args, **kwargs):
        """Выполнение."""
        client.send_message(Message.exit_request())
        print('Завершение соединения.')
        logger.info('Завершение работы по команде пользователя.')
        # Задержка неоходима, чтобы успело уйти сообщение о выходе
        time.sleep(0.5)
        exit(0)


main_commands = Comander()
main_commands.reg_cmd(ExitCommand)
