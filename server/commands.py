# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-04 22:05:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-04 19:41:39
import binascii
import hmac
import logging
import os
from collections import OrderedDict

from dynaconf import settings
from tabulate import tabulate

from db import User
from decorators import login_required
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
            user = User.by_name(message.user_account_name)
            if not user:
                mes = Message.error_resp('Пользователь не зарегистрирован.', user=message.user_account_name)
            else:
                random_str = binascii.hexlify(os.urandom(64))
                digest = hmac.new(user.auth_key, random_str).digest()
                message_auth = Message(response=511, **{settings.DATA: random_str.decode('ascii')})
                try:
                    serv.write_client_data(message.client, message_auth)
                except OSError:
                    serv.clients.remove(message.client)
                data = Message(message.client.recv(settings.get('max_package_length', 1024)))
                client_digest = binascii.a2b_base64(getattr(data, settings.DATA, ''))

                if data.response == 511 and hmac.compare_digest(digest, client_digest):
                    serv.names[message.user_account_name] = message.client
                    mes = Message.success(**{settings.DESTINATION: message.user_account_name})
                    client_ip, client_port = message.client.getpeername()
                    User.login_user(message.user_account_name, ip_addr=client_ip, port=client_port, pub_key=getattr(message, settings.PUBLIC_KEY, ''))
                    serv.notify(self.name)
        else:
            serv.clients.remove(message.client)
            mes = Message.error_resp('Имя пользователя уже занято.', user=message.user_account_name)
        serv.write_client_data(message.client, mes)

        return True


class ExitCommand(AbstractCommand):
    """Выход пользователя"""
    name = settings.EXIT

    @login_required
    def execute(self, serv, message, **kwargs):
        client = serv.names.get(message.user_account_name)
        if client:
            client_ip, client_port = client.getpeername()
            serv.clients.remove(client)
            client.close()
            del serv.names[message.user_account_name]
            User.logout_user(message.user_account_name, ip_addr=client_ip, port=client_port)
            serv.notify(self.name)


class UserListCommand(AbstractCommand):
    """Список известных пользователей"""
    name = settings.USERS_REQUEST

    @login_required
    def execute(self, serv, msg, **kwargs):
        src_user = getattr(msg, settings.USER, None)
        serv.write_client_data(serv.names.get(src_user), Message.success(202, **{settings.LIST_INFO: [u.username for u in User.all()]}))
        return True


icommands = Comander()
main_commands = Comander()
main_commands.reg_cmd(Presence)
main_commands.reg_cmd(ExitCommand)
main_commands.reg_cmd(UserListCommand)
