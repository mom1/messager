# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-19 17:38:37
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-06 21:49:44
import logging

# Debug
DEBUG = True
DEBUG_SQL = False

# network
PORT = 7777
HOST = '127.0.0.1'
MAX_CONNECTIONS = 5
MAX_PACKAGE_LENGTH = 1024
ENCODING = 'utf-8'

# log
LOGGING_LEVEL = logging.DEBUG
LOG_DIR = 'log'

# Прококол JIM основные ключи:
ACTION = 'action'
TIME = 'time'
USER = 'user'
ACCOUNT_NAME = 'account_name'
SENDER = 'from'
DESTINATION = 'to'
DATA = 'bin'

# Прочие ключи, используемые в протоколе
PRESENCE = 'presence'
RESPONSE = 'response'
ERROR = 'error'
MESSAGE = 'message'
MESSAGE_TEXT = 'mess_text'
EXIT = 'exit'
GET_CONTACTS = 'get_contacts'
LIST_INFO = 'data_list'
DEL_CONTACT = 'remove'
ADD_CONTACT = 'add'
USERS_REQUEST = 'get_users'
PUBLIC_KEY = 'pubkey'
PUBLIC_KEY_REQUEST = 'pubkey_need'

EVENT_NEW_MESSAGE = 'new_message'

# DB
DATABASES = {
    'default': {
        'ENGINE': 'sqlite',
        'NAME': 'db/db_talkative.db',
    },
    'server': {
        'ENGINE': 'sqlite',
        'NAME': 'db/db_server.db',
        'CONNECT_ARGS': {
            'check_same_thread': False,
        },
    },
    'client': {
        'ENGINE': 'sqlite',
        'NAME': 'db/db_client_{user}.db',
        'CONNECT_ARGS': {
            'check_same_thread': False,
        },
    },
}

# Oper
USER_NAME = None
GUI = True  # do gui start default?
CONSOLE = not GUI  # do console start default?

# Colors
COLOR_MESSAGE_IN = '#a40000;'
COLOR_MESSAGE_OUT = 'green'
