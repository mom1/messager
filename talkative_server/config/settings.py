# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-19 17:38:37
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-23 22:32:43
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
ACCOUNT_NAME = 'account_name'
ACTION = 'action'
DATA = 'bin'
DESTINATION = 'to'
SENDER = 'from'
TIME = 'time'
USER = 'user'

# Прочие ключи, используемые в протоколе
ADD_CONTACT = 'add'
AVA_INFO = 'edit_ava'
AUTH = 'auth'
DEL_CONTACT = 'remove'
ERROR = 'error'
EXIT = 'exit'
GET_CONTACTS = 'get_contacts'
LIST_INFO = 'data_list'
MESSAGE = 'message'
MESSAGE_TEXT = 'mess_text'
PRESENCE = 'presence'
PUBLIC_KEY = 'pubkey'
PUBLIC_KEY_REQUEST = 'pubkey_need'
RESPONSE = 'response'
USERS_REQUEST = 'get_users'

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
NO_ASYNC = False

# Colors
COLOR_MESSAGE_IN = '#a40000;'
COLOR_MESSAGE_OUT = 'green'
