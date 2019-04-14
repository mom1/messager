# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-13 11:50:20
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-14 22:34:04
from commands import main_commands, AbstractCommand
from jim_mes import Message


class EchoCommand(AbstractCommand):
    name = 'echo'

    def execute(self, request, *args, **kwargs):
        if not request.param:
            return Message(action='request', text='Enter text for echo', destination=self.name)
        return Message(action='msg', text=request.param)


main_commands.reg_cmd(EchoCommand, EchoCommand.name)
