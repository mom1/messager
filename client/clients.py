# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-04 20:50:07
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-07 13:14:45
import commands
import logging

from settings import Settings

settings = Settings.get_instance()


class AbstractClient(object):
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
        self.commander = commands.Comander(self)
        self.commander.reg_cmd(commands.CommandHomeWork1(self.logger, self.toggle_data))
        self.commander.reg_cmd(commands.CommandHomeWork2(self.logger))

    def connect(self, *args, **kwargs):
        try:
            while True:
                message = self.input_data()
                if self.commander.run(message):
                    continue
                yield message
        except KeyboardInterrupt:
            self.logger.debug('')
            self.logger.debug('connect closed')
            yield False

    def input_data(self, *args, **kwargs):
        return input('Enter data to send\n:')

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
        self.logger.info(str(data))
