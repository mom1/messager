# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-04 22:05:30
# @Last Modified by:   maxst
# @Last Modified time: 2019-07-23 12:51:20
import logging

from dynaconf import settings

from jim_mes import Message

logger = logging.getLogger('commands')


class Comander(object):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.commands = {}

    def run(self, request, *args, **kwargs):
        response = None
        name_cmd = request.action
        cmd = self.commands.get(name_cmd, None)
        if cmd:
            logger.debug(f'I found command {cmd}')
            response = cmd(*args, **kwargs).execute(request, *args, **kwargs)
        return response

    def reg_cmd(self, command, name=None):
        name = getattr(command, 'name', None) if not name else name
        if name in self.commands:
            raise ValueError(f'Name exists {name}')
        self.commands[name] = command

    def unreg_cmd(self, command):
        if command in self.commands:
            del self.commands[command]


class AbstractCommand(object):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def execute(self, message, **kwargs):
        pass

    def validate(self, *args, **kwargs):
        pass


class Presence(AbstractCommand):
    def execute(self, message, serv, **kwargs):
        if message.user_account_name not in serv.names:
            serv.names[message.user_account_name] = message.client
            mes = Message.success(**{settings.DESTINATION: message.user_account_name})
        else:
            serv.clients.remove(message.client)
            mes = Message.error_resp('Имя пользователя уже занято.', user=message.user_account_name)
        serv.write_client_data(message.client, mes)

        return True


class ExitCommand(AbstractCommand):
    name = 'exit'

    def execute(self, message, serv, **kwargs):
        client = serv.names.get(message.user_account_name)
        if client:
            serv.clients.remove(client)
            client.close()
            del serv.names[message.user_account_name]


main_commands = Comander()
main_commands.reg_cmd(Presence, 'presence')
main_commands.reg_cmd(ExitCommand)
