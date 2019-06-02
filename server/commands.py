# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-04 22:05:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-06-02 12:59:12
import logging

from db import User, UserHistory


class Comander(object):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.commands = {}

    def run(self, request, *args, **kwargs):
        response = False
        name_cmd = request.action
        if request.action == 'msg':
            if (request.text or '').startswith('!'):
                name_cmd = request.text[1:]
            else:
                name_cmd = (request.text or '').split()[0]
            if not self.commands.get(name_cmd, None):
                name_cmd = request.action
        cmd = self.commands.get(name_cmd, None)
        if cmd:
            response = cmd(*args, **kwargs).execute(request, *args, **kwargs)
            print(response)
            response = True if not response else response
        return response

    def reg_cmd(self, command, name=None):
        name = getattr(command, 'name', None) if not name else name
        if name in self.commands:
            raise ValueError(f'Name exists {name}')
        self.commands[name] = command

    def unreg_cmd(self, command):
        if command in self.commands:
            del self.commands[command]


main_commands = Comander()


class AbstractCommand(object):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.logger = kwargs.pop('logger', logging.getLogger('Server'))

    def execute(self, message, **kwargs):
        pass

    def validate(self, *args, **kwargs):
        pass


class Presence(AbstractCommand):
    def execute(self, message, **kwargs):
        user = User.by_name(message.user)
        UserHistory.create(
            oper_id=user.id if user else 0,
            type_row='login',
            ip_addr=str(kwargs.get('addr', '')),
        )
        return type(message).success()


main_commands.reg_cmd(Presence, 'presence')
