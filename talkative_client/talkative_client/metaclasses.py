# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-07-23 12:44:33
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-09 00:17:20
import dis
import socket


class ClientVerifier(type):
    """Верификатор клиента."""

    def __new__(cls, name, bases, attr_dict):
        """Тут находим объявление сокета и проверяем его инициализацию.

        кэшируем имя атрибута

        """
        cls.store_soc = None
        except_ = ('__classcell__', '__doc__')
        for key, val in attr_dict.items():
            assert not isinstance(val, socket.socket), 'Создание сокетов на уровне классов запрещенно'
            if key in except_:
                continue
            instrs = tuple(dis.Bytecode(val))
            glob_soc = (tuple(filter(lambda x: x.opname == 'LOAD_GLOBAL' and x.argval == 'socket', instrs)) or (None, ))[0]
            cls.store_soc = next((i for i in instrs[instrs.index(glob_soc):] if i.opname == 'STORE_ATTR'), None) if not cls.store_soc and glob_soc else cls.store_soc
            tcp_param = next((j for j in instrs[instrs.index(glob_soc):instrs.index(cls.store_soc)] if j.opname == 'LOAD_ATTR' and j.arg == 2), None) if glob_soc and cls.store_soc else None
            if tcp_param:
                assert tcp_param.argval == 'SOCK_STREAM', 'Использование сокетов возможно только по TCP'
        return super().__new__(cls, name, bases, attr_dict)

    def __init__(cls, name, bases, attr_dict):
        """Т.к в предыдущей функции использовался дикт.

        Мы могли пропустить вызовы интересующего метода
        тут еще раз просматриваем все и ищем вызовы.
        Но т.к. __new__ и __init__ вызываются последовательно
        для каждого класса остается дыра в виде вызова в родительском классе.
        """
        if cls.store_soc:
            checks_meth = ('accept', 'listen')
            except_ = ('__classcell__', '__doc__')
            for key, val in attr_dict.items():
                if key in except_:
                    continue
                instrs = tuple(dis.Bytecode(val))
                socks = (i for i in instrs if i.argval == cls.store_soc.argval)
                for sock in socks:
                    calls = instrs[instrs.index(sock) + 1]
                    # python 3.7 !!!LOAD_METHOD!!!
                    assert not (calls.argval in checks_meth and calls.opname == 'LOAD_METHOD'), f'Для сокетов запрещенно вызывать методы {checks_meth}'
        super().__init__(name, bases, attr_dict)
