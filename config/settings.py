# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-19 17:38:37
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-23 22:56:04
import logging

DEBUG = True

PORT = 7777
HOST = '127.0.0.1'

MAX_CONNECTIONS = 5
MAX_PACKAGE_LENGTH = 1024
ENCODING = 'utf-8'

LOGGING_LEVEL = logging.DEBUG

LOG_DIR = 'log'

# Прококол JIM основные ключи:
ACTION = 'action'
TIME = 'time'
USER = 'user'
ACCOUNT_NAME = 'account_name'
SENDER = 'from'
DESTINATION = 'to'

# Прочие ключи, используемые в протоколе
PRESENCE = 'presence'
RESPONSE = 'response'
ERROR = 'error'
MESSAGE = 'message'
MESSAGE_TEXT = 'mess_text'
EXIT = 'exit'

DB_NAME = 'st_mes'

USER_NAME = None
GUI = False  # start gui default
