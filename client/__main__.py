# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-03-30 12:35:08
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-04 22:01:04
import logging

import clients

logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s: %(message)s',
)


class Client(clients.AbstractClient):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.logger = logging.getLogger(type(self).__name__)
        self.client = kwargs.get('client', clients.ClientConsole())

    def connect(self, *args, **kwargs):
        self.client.connect(*args, **kwargs)

    def input_data(self, *args, **kwargs):
        self.client.input_data(*args, **kwargs)

    def send_data(self, *args, **kwargs):
        self.client.send_data(*args, **kwargs)

    def receive_data(self, *args, **kwargs):
        self.client.receive_data(*args, **kwargs)


if __name__ == '__main__':
    Client(client=clients.ClientConsole()).connect()
