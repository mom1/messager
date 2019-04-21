# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-19 09:31:57
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-20 20:47:31
import inspect
import logging
from functools import wraps

logger = logging.getLogger('decorators')


def get_name_by_frame(frame):
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
    def wrapper(request, *args, **kwargs):
        stack = inspect.stack()
        caller_name = get_name_by_frame(stack[1][0])
        curr_name = f'{func.__module__}.{func.__qualname__}'

        del stack

        logger.debug(f'caller "{caller_name}" call this "{ curr_name }"')
        return func(request, *args, **kwargs)

    return wrapper
