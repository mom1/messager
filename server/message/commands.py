# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-21 13:07:02
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-21 15:47:17
from commands import main_commands, AbstractCommand
from jim_mes import Message


class MsgCommand(AbstractCommand):
    name = 'msg'

    def execute(self, request, *args, **kwargs):
        if not self.validate(request):
            return Message.error_resp('request is not valid')
        return request

    def validate(self, request, *args, **kwargs):
        dest = request.destination
        if not dest:
            dest = request.text.split(':')[0] if request.text else ''
            request.destination = dest
        exp = (
            request.action == self.name,
            request.text,
            # dest,
            request.time,
            request.user,
        )
        return all(exp)


main_commands.reg_cmd(MsgCommand)
