# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-04 22:05:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-23 23:38:17
import logging
import time

from dynaconf import settings

from jim_mes import Message

logger = logging.getLogger('commands')


class Comander(object):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.commands = {}

    def run(self, name_cmd, *args, **kwargs):
        response = None
        cmd = self.commands.get(name_cmd, None)
        if cmd:
            logger.debug(f'I found command {cmd}')
            response = cmd(*args, **kwargs).execute(*args, **kwargs)
        elif name_cmd == 'help':
            response = self.print_help()
        return response

    def reg_cmd(self, command, name=None):
        name = getattr(command, 'name', None) if not name else name
        if name in self.commands:
            raise ValueError(f'Name exists {name}')
        self.commands[name] = command

    def unreg_cmd(self, command):
        if command in self.commands:
            del self.commands[command]

    def print_help(self):
        '''Функция выводящяя справку по использованию'''
        print('Поддерживаемые команды:')
        for key, cmd in self.commands.items():
            print(f'{key} - {cmd.__doc__}')
        print('help - Вывести подсказки по командам')
        return True


class AbstractCommand(object):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def execute(self, message, **kwargs):
        pass

    def validate(self, *args, **kwargs):
        pass


class ExitCommand(AbstractCommand):
    '''Выход из программы'''
    name = 'exit'

    def execute(self, client, *args, **kwargs):
        client.send_message(Message.exit_request())
        print('Завершение соединения.')
        logger.info('Завершение работы по команде пользователя.')
        # Задержка неоходима, чтобы успело уйти сообщение о выходе
        time.sleep(0.5)
        exit(0)


main_commands = Comander()
main_commands.reg_cmd(ExitCommand)
