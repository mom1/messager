# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-07-23 22:59:32
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-23 23:50:30
import logging
from commands import AbstractCommand, icommands

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


class Quit(AbstractCommand):
    '''Завершение работы сервера'''
    name = 'quit'

    def execute(self, cli, command, **kwargs):
        exit(0)


icommands.reg_cmd(Quit)
