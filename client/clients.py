# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-04 20:50:07
# @Last Modified by:   MaxST
# @Last Modified time: 2019-05-25 10:23:32
import dis
import logging
import socket

from settings import Settings

settings = Settings.get_instance()


class ClientVerifier(type):
    def __new__(cls, name, bases, attr_dict):
        """
            Тут находим объявление сокета и проверяем его инициализацию,
            кэшируем имя атрибута
        """
        cls.store_soc = None
        for key, val in attr_dict.items():
            assert not isinstance(val, socket.socket), 'Создание сокетов на уровне классов запрещенно'
            if key == '__classcell__':
                continue
            instrs = tuple(dis.Bytecode(val))
            glob_soc = (tuple(filter(lambda x: x.opname == 'LOAD_GLOBAL' and x.argval == 'socket', instrs)) or (None, ))[0]
            cls.store_soc = next((i for i in instrs[instrs.index(glob_soc):] if i.opname == 'STORE_ATTR'), None) if not cls.store_soc and glob_soc else cls.store_soc
            tcp_param = next((j for j in instrs[instrs.index(glob_soc):instrs.index(cls.store_soc)] if j.arg == 13), None) if glob_soc and cls.store_soc else None
            if tcp_param:
                assert tcp_param.argval == 'SOCK_STREAM', 'Использование сокетов возможно только по TCP'
        return super().__new__(cls, name, bases, attr_dict)

    def __init__(cls, name, bases, attr_dict):
        """
            Т.к в предыдущей функции использовался дикт
            мы могли пропустить вызовы интересующего метода
            тут еще раз просматриваем все и ищем вызовы.
            Но т.к. __new__ и __init__ вызываются последовательно
            для каждого класса остается дыра в виде вызова в родительском классе.
        """
        if cls.store_soc:
            checks_meth = ('accept', 'listen')
            for key, val in attr_dict.items():
                if key == '__classcell__':
                    continue
                instrs = tuple(dis.Bytecode(val))
                socks = (i for i in instrs if i.argval == cls.store_soc.argval)
                for sock in socks:
                    calls = instrs[instrs.index(sock) + 1]
                    # python 3.7 !!!LOAD_METHOD!!!
                    assert not (calls.argval in checks_meth and calls.opname == 'LOAD_METHOD'), f'Для сокетов запрещенно вызывать методы {checks_meth}'
        super().__init__(name, bases, attr_dict)


class AbstractClient(metaclass=ClientVerifier):
    def connect(self, *args, **kwargs):
        pass

    def input_data(self, *args, **kwargs):
        pass

    def send_data(self, *args, **kwargs):
        pass

    def receive_data(self, *args, **kwargs):
        pass

    def report(self, *args, **kwargs):
        pass


class ClientConsole(AbstractClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(type(self).__name__)

    def connect(self, *args, **kwargs):
        try:
            while True:
                yield self.input_data()
        except KeyboardInterrupt:
            self.logger.debug('')
            self.logger.debug('connect closed')
            yield False

    def input_data(self, *args, **kwargs):
        text = kwargs.get('text', 'Enter data to send')
        return input(f'{text}\n:')

    def toggle_data(self, data):
        response = data
        if isinstance(data, (str)):
            self.logger.debug('encode data')
            response = data.encode(settings.get('encoding'))
        if isinstance(data, (bytes)):
            self.logger.debug('decode data')
            response = data.decode(settings.get('encoding'))
        return response

    def prepare_data_send(self, data):
        self.logger.debug(f'prepare send_data for :{data}')
        return self.toggle_data(data)

    def prepare_data_receiv(self, data):
        self.logger.debug(f'prepare receiv_data for :{data}')
        return self.toggle_data(data)

    def send_data(self, data, **kwargs):
        data_send = self.prepare_data_send(data)
        self.logger.debug(f'Send Data:{data_send}')
        return data_send

    def receive_data(self, data, **kwargs):
        self.logger.debug(f'{"*" * 15} DATA RECEIVED FROM SERVER {"*" * 15}')
        self.logger.debug(f'Received Data:{data}')
        return data

    def show_mes(self, data):
        print(str(data))
