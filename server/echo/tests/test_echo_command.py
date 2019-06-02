# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-15 00:11:16
# @Last Modified by:   MaxST
# @Last Modified time: 2019-06-01 22:32:58
from settings import Settings

settings = Settings.get_instance()
settings['db_name'] = 'test'

import logging  # noqa
from commands import main_commands  # noqa
from pathlib import Path  # noqa

from jim_mes import Message  # noqa
from db import DBManager  # noqa


logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s: %(message)s',
)

DBManager.get_instance()

p = Path('.')
for item in p.glob('**/*/*.py'):
    if item.parent.stem == 'tests':
        continue
    __import__(f'{item.parent.stem}.{item.stem}', globals(), locals())


class TestEchoCommand(object):
    def test_execute(self):
        logger = logging.getLogger('Server')
        request = Message(action='msg', text='!echo')
        response = main_commands.run(request, logger=logger)
        assert response.action == 'request' and response.text == 'Enter text for echo' and response.destination == 'echo'

        test_text = 'text for repet'
        response = main_commands.run(Message(action='echo', param=test_text), logger=logger)
        assert response.action == 'msg' and response.text == test_text
