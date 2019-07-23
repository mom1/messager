# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-21 11:33:54
# @Last Modified by:   maxst
# @Last Modified time: 2019-07-21 11:54:49
import inspect
import logging
from functools import wraps
from dynaconf import settings

logger = logging.getLogger('decorators')


def get_name_by_frame(frame):
    print(settings.PORT)
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
    @wraps(func)
    def wrapper(*args, **kwargs):
        stack = inspect.stack()
        caller_name = get_name_by_frame(stack[1][0])
        curr_name = f'{func.__module__}.{func.__qualname__}'

        del stack

        logger.debug(f'caller "{caller_name}" call this "{ curr_name }"')
        return func(*args, **kwargs)

    return wrapper
