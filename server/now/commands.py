# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-14 21:52:33
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-14 22:04:24
from commands import main_commands, AbstractCommand
from jim_mes import Message
from datetime import datetime


class NowCommand(AbstractCommand):

    def execute(self, *args, **kwargs):
        return Message(action='now', text=str(datetime.now()))


main_commands.reg_cmd(NowCommand, 'now')
