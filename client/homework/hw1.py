# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-13 12:08:00
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-14 23:55:17
import subprocess
import tempfile
from sys import platform

from commands import main_commands, AbstractCommand
from settings import Settings


settings = Settings.get_instance()


class CommandHomeWork1(AbstractCommand):
    # name = 'home_work_1'
    name = 'hw1'

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

    def execute(self, *args, **kwargs):
        self.logger.debug(
            '1. Каждое из слов «разработка», «сокет», «декоратор» представить в строковом формате\n' +
            'и проверить тип и содержание соответствующих переменных. Затем с помощью онлайн-конвертера преобразовать\n' +
            'строковые представление в формат Unicode и также проверить тип и содержимое переменных.')
        for word in self.task1['list1']:
            self.logger.debug(f'word: {word} type: {type(word)}')

        for word in self.task1['list2']:
            self.logger.debug(f'word: {word.decode(settings.get("encoding"))} type: {type(word)}')
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
            word = word.encode(settings.get('encoding'))
            self.logger.debug(f'«{word}»')
            word = word.decode(settings.get('encoding'))
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
                ntf.write(word.encode(settings.get('encoding')) + b'\n')
            ntf.seek(0)

            with open(ntf.name) as f_enc:
                self.logger.debug(f'encoding default: {f_enc.encoding}')

            with open(ntf.name, encoding='utf-16le') as f:
                self.logger.debug(f'\n{"".join(f)}')


main_commands.reg_cmd(CommandHomeWork1)
