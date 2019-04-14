# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-04 22:05:30
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-14 23:48:16
from settings import Settings

settings = Settings.get_instance()


class Comander(object):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.commands = {}

    def run(self, request, *args, **kwargs):
        response = False
        print(self.commands)
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
        self.logger = kwargs.pop('logger', None)

    def execute(self, message, **kwargs):
        pass


class Presence(AbstractCommand):

    def execute(self, message, **kwargs):
        return type(message).success()


main_commands.reg_cmd(Presence, 'presence')
