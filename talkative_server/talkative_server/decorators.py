# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-21 11:33:54
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-31 20:10:08
import inspect
import logging
from functools import wraps

from dynaconf import settings

from .db import DBManager
from .jim_mes import Message

logger = logging.getLogger('decorators')
db = DBManager('server')


def get_name_by_frame(frame):
    """Получить имя по фрейму.

    Args:
        frame: Фрейм

    """
    name = []
    module = inspect.getmodule(frame)
    if module:
        name.append(module.__name__)
    if 'self' in frame.f_locals:
        name.append(frame.f_locals['self'].__class__.__name__)
    codename = frame.f_code.co_name
    if codename != '<module>':  # top level usually
        name.append(codename)  # function or a method

    del frame

    return '.'.join(name)


def log(func):
    """Декоратор логирования."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        stack = inspect.stack()
        caller_name = get_name_by_frame(stack[1][0])
        curr_name = f'{func.__module__}.{func.__qualname__}'

        del stack

        logger.debug(f'caller "{caller_name}" call this "{ curr_name }"')
        return func(*args, **kwargs)

    return wrapper


def login_required(func):
    """Декоратор проверяющий авторизацию.

    Args:
        func: декорируемая функция

    Returns:
        Результат выполнения декорируемой функции

    Raises:
        TypeError: если пользователь не авторизован

    """
    def checker(*args, **kwargs):
        serv = args[1]
        mes = args[2]
        con1 = getattr(mes, settings.ACCOUNT_NAME, '')
        con2 = getattr(mes, settings.SENDER, '')
        client = serv.names.get(mes.user_account_name) or serv.names.get(con1) or serv.names.get(con2)
        if not client:
            logger.critical('Ошибка login_required')
            raise TypeError
        return func(*args, **kwargs)

    return checker


def login_required_db(func):
    def checker(*args, **kwargs):
        user = None
        for x in args:
            if isinstance(x, Message):
                user = db.User.by_name(x.user_account_name)
                break
        for k, v in kwargs.items():
            if isinstance(v, Message):
                user = db.User.by_name(v.user_account_name)
                break

        if not user or not user.user_activity:
            logger.critical('Ошибка login_required')
            raise TypeError

        return func(*args, **kwargs)

    return checker
