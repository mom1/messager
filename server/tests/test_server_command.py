# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-15 00:11:16
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-16 00:05:05
import logging
from commands import main_commands, Presence

from jim_mes import Message
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s: %(message)s',
)

p = Path('.')
for item in p.glob('**/*/*.py'):
    if item.parent.stem == 'tests':
        continue
    __import__(f'{item.parent.stem}.{item.stem}', globals(), locals())


class TestPresence(object):
    def test_execute(self):
        logger = logging.getLogger('Server')
        request = Message.presence()
        response = main_commands.run(request, logger=logger)
        assert response.response == 200


class TestComander(object):
    test_cls = Presence
    name_reg = 'test_presence'

    def test_run(self):
        assert TestPresence().test_execute() is None

    def test_reg_cmd(self):
        main_commands.reg_cmd(self.test_cls, self.name_reg)
        assert self.name_reg in main_commands.commands and main_commands.commands[self.name_reg] == self.test_cls

    def test_unreg_cmd(self):
        main_commands.unreg_cmd(self.name_reg)
        assert self.name_reg not in main_commands.commands
