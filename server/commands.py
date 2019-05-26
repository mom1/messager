# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-04 22:05:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-05-26 01:22:21
import logging

from helpers import log


class Comander(object):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.commands = {}

    @log
    def run(self, request, *args, **kwargs):
        response = False
        if request.action == 'msg' and (request.text or '').startswith('!'):
            cmd = self.commands.get(request.text[1:], None)
        else:
            cmd = self.commands.get(request.action, None)
        if cmd:
            response = cmd(*args, **kwargs).execute(request, *args, **kwargs)
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
        return type(message).success()


main_commands.reg_cmd(Presence, 'presence')
