# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-04 22:05:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-26 00:11:25
import logging
from collections import OrderedDict

from dynaconf import settings
from tabulate import tabulate

from db import User
from jim_mes import Message

logger = logging.getLogger('commands')


class Comander(object):
    def __init__(self, *args, **kwargs):
        super().__init__()
        cls_store = kwargs.get('cls_store', dict)
        self.commands = cls_store()

    def run(self, serv, request, *args, **kwargs):
        response = None
        name_cmd = request.action if isinstance(request, Message) else request
        cmd = self.commands.get(name_cmd, None)
        if cmd:
            logger.debug(f'I found command {cmd}')
            response = cmd(*args, **kwargs).execute(serv, request, *args, **kwargs)
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
        """Функция выводящяя справку по использованию"""
        print('Поддерживаемые команды:')
        sort_dict = OrderedDict(sorted(self.commands.items()))
        print(tabulate(((k, v.__doc__) for k, v in sort_dict.items())))
        print('help - Вывести подсказки по командам')
        return True


class AbstractCommand(object):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def execute(self, serv, message, **kwargs):
        pass


class Presence(AbstractCommand):
    """Пользователь представился"""
    name = settings.PRESENCE

    def execute(self, serv, message, **kwargs):
        if message.user_account_name not in serv.names:
            serv.names[message.user_account_name] = message.client
            mes = Message.success(**{settings.DESTINATION: message.user_account_name})
            client_ip, client_port = message.client.getpeername()
            User.login_user(message.user_account_name, ip_addr=client_ip, port=client_port)
        else:
            serv.clients.remove(message.client)
            mes = Message.error_resp('Имя пользователя уже занято.', user=message.user_account_name)
        serv.write_client_data(message.client, mes)

        return True


class ExitCommand(AbstractCommand):
    """Выход пользователя"""
    name = settings.EXIT

    def execute(self, serv, message, **kwargs):
        client = serv.names.get(message.user_account_name)
        if client:
            client_ip, client_port = client.getpeername()
            serv.clients.remove(client)
            client.close()
            del serv.names[message.user_account_name]
            User.logout_user(message.user_account_name, ip_addr=client_ip, port=client_port)


icommands = Comander()
main_commands = Comander()
main_commands.reg_cmd(Presence)
main_commands.reg_cmd(ExitCommand)
