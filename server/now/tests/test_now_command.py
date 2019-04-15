# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-15 00:11:16
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-15 23:35:51
import logging
from commands import main_commands

from jim_mes import Message
from pathlib import Path

from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s: %(message)s',
)

p = Path('.')
for item in p.glob('**/*/*.py'):
    if item.parent.stem == 'tests':
        continue
    __import__(f'{item.parent.stem}.{item.stem}', globals(), locals())


class TestNowCommand(object):
    def test_execute(self):
        logger = logging.getLogger('Server')
        request = Message(action='msg', text='!now')
        response = main_commands.run(request, logger=logger)
        data = datetime.strptime(str(response), '%Y-%m-%d %H:%M:%S.%f')
        assert datetime.now() - data < timedelta(seconds=1)
