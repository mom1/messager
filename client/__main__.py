# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-03-30 12:35:08
# @Last Modified by:   Max ST
# @Last Modified time: 2019-03-30 17:20:27
import logging
import subprocess
import tempfile
from sys import platform

import settings

logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s: %(message)s',
)


class Client(object):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.logger = logging.getLogger(type(self).__name__)
        self.client = kwargs.get('client', ClientConsole())

    def connect(self, *args, **kwargs):
        self.client.connect(*args, **kwargs)

    def input_data(self, *args, **kwargs):
        self.client.input_data(*args, **kwargs)

    def send_data(self, *args, **kwargs):
        self.client.send_data(*args, **kwargs)

    def receive_data(self, *args, **kwargs):
        self.client.receive_data(*args, **kwargs)


class ClientConsole(object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(type(self).__name__)

    def connect(self, *args, **kwargs):
        self.logger.debug('connect')
        try:
            while True:
                message = self.input_data()
                message = self.send_data(message)
                message = self.receive_data(message)
        except KeyboardInterrupt:
            self.logger.debug('')
            self.logger.debug('connect closed')

    def input_data(self, *args, **kwargs):
        return input('Enter data to send\n:')

    def toggle_data(self, data):
        response = data
        if isinstance(data, (str)):
            self.logger.debug('encode data')
            response = data.encode(settings.ENCODING)
        if isinstance(data, (bytes)):
            self.logger.debug('decode data')
            response = data.decode(settings.ENCODING)
        return response

    def prepare_data_send(self, data):
        self.logger.debug(f'prepare send_data for :{data}')
        return self.toggle_data(data)

    def prepare_data_receiv(self, data):
        self.logger.debug(f'prepare receiv_data for :{data}')
        return self.toggle_data(data)

    def send_data(self, data, **kwargs):
        data_send = self.prepare_data_send(data)
        self.logger.debug(f'{"*" * 15} DATA SEND TO SERVER {"*" * 15}')
        self.logger.debug(f'Send Data:{data_send}')
        return data_send

    def receive_data(self, data, **kwargs):
        data_receiv = self.prepare_data_receiv(data)
        self.logger.debug(f'{"*" * 15} DATA RECEIVED FROM SERVER {"*" * 15}')
        self.logger.debug(f'Received Data:{data_receiv}')
        return data_receiv


class ClientHomeWork(ClientConsole):
    task1 = {
        'list1': ['разработка', 'сокет', 'декоратор'],
        'list2': [
            b'\xd1\x80\xd0\xb0\xd0\xb7\xd1\x80\xd0\xb0\xd0\xb1\xd0\xbe\xd1\x82\xd0\xba\xd0\xb0',
            b'\xd1\x81\xd0\xbe\xd0\xba\xd0\xb5\xd1\x82',
            b'\xd0\xb4\xd0\xb5\xd0\xba\xd0\xbe\xd1\x80\xd0\xb0\xd1\x82\xd0\xbe\xd1\x80',
        ],
    }

    task2 = {'list1': [b'class', b'function', b'method']}
    task3 = {'list1': ['attribute', 'класс', 'функция', 'type']}
    task4 = {'list1': ['разработка', 'администрирование', 'protocol', 'standard']}
    task5 = {'list1': ['yandex.ru', 'youtube.com']}
    task6 = {'list1': ['сетевое программирование', 'сокет', 'декоратор']}

    def connect(self, *args, **kwargs):

        self.logger.debug(
            '1. Каждое из слов «разработка», «сокет», «декоратор» представить в строковом формате\n' +
            'и проверить тип и содержание соответствующих переменных. Затем с помощью онлайн-конвертера преобразовать\n' +
            'строковые представление в формат Unicode и также проверить тип и содержимое переменных.')
        for word in self.task1['list1']:
            self.logger.debug(f'word: {word} type: {type(word)}')

        for word in self.task1['list2']:
            self.logger.debug(f'word: {word.decode(settings.ENCODING)} type: {type(word)}')
        self.logger.debug('\n')

        self.logger.debug(
            '2. Каждое из слов «class», «function», «method» записать в байтовом типе без преобразования в\n' +
            'последовательность кодов (не используя методы encode и decode) и определить тип, содержимое и\n' +
            'длину соответствующих переменных.')
        for word in self.task2['list1']:
            self.logger.debug(f'word: {word} type: {type(word)} len: {len(word)}')
        self.logger.debug('\n')

        self.logger.debug('3. Определить, какие из слов «attribute», «класс», «функция», «type» невозможно записать в байтовом типе.')
        for word in self.task3['list1']:
            if all(ord(char) < 128 for char in word):
                self.logger.debug(f'word: «{word}» can be written in byte')
            else:
                self.logger.debug(f'word: «{word}» cannot be written in byte')
        self.logger.debug('\n')

        self.logger.debug(
            '4. Преобразовать слова «разработка», «администрирование», «protocol», «standard» из строкового\n' +
            'представления в байтовое и выполнить обратное преобразование (используя методы encode и decode).')
        for word in self.task4['list1']:
            self.logger.debug(f'source word: {word}')
            word = self.toggle_data(word)
            self.logger.debug(f'«{word}»')
            word = self.toggle_data(word)
            self.logger.debug(f'«{word}»')
        self.logger.debug('\n')

        self.logger.debug(
            '5. Выполнить пинг веб-ресурсов yandex.ru, youtube.com и преобразовать результаты из байтовового\n' +
            'в строковый тип на кириллице.')
        for word in self.task5['list1']:
            is_win = False
            if 'win' in platform.lower():
                args = ['ping', word]
                is_win = True
            else:
                args = ['ping', '-c4', word]
            sub_ping = subprocess.Popen(args, stdout=subprocess.PIPE)
            log = ''
            for line in sub_ping.stdout:
                log += line.decode() if not is_win else line.decode('cp866')
            self.logger.debug(log)
        self.logger.debug('\n')

        self.logger.debug(
            '6. Создать текстовый файл test_file.txt, заполнить его тремя строками: «сетевое программирование»,\n' +
            '«сокет», «декоратор». Проверить кодировку файла по умолчанию. Принудительно открыть файл в\n' +
            'формате Unicode и вывести его содержимое.')

        with tempfile.NamedTemporaryFile(prefix='test_file', suffix='.txt') as ntf:
            for word in self.task6['list1']:
                ntf.write(word.encode(settings.ENCODING) + b'\n')
            ntf.seek(0)

            with open(ntf.name) as f_enc:
                self.logger.debug(f'encoding default: {f_enc.encoding}')

            with open(ntf.name, encoding=settings.ENCODING) as f:
                self.logger.debug(f'\n{"".join(f)}')


if __name__ == '__main__':
    Client(client=ClientHomeWork()).connect()
