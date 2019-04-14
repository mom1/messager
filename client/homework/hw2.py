# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-13 12:10:44
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-14 23:56:01
import re
from commands import main_commands, AbstractCommand

from jim_mes import Converter, dispatcher
from pathlib import Path


class CommandHomeWork2(AbstractCommand):
    # name = 'home_work_2'
    name = 'hw2'

    column = ['Изготовитель системы', 'Название ОС', 'Код продукта', 'Тип системы']
    re_column = [re.compile(r'(?im)(%s):\s*(.+)' % r.lower()) for r in column]

    templates = {k: v for k, v in zip(column, re_column)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = []

    def execute(self, *args, **kwargs):
        self.logd('Prepare raw data')
        self.get_data()
        conv = Converter(logger=self.logger)
        data = self.data

        for type_ in dispatcher.get_objects().keys():
            file = conv.write(data, type_)
            data = conv.read(file)
            self.logd(data)
            # alternative conv.convert_file_to(source_file, dest_type) -> new_file_name

    def get_data(self):
        for path in sorted(Path('data/').rglob('*.txt')):
            self.logd(f'Collect data from {path.name}')
            raw_data = path.read_text(encoding='cp1251')
            self.make_data(path.stem, raw_data)

    def make_data(self, name, raw_data):
        row = {}
        for key, reg in self.templates.items():
            _, value = reg.findall(raw_data)[0]
            row[key] = value
        self.data.append(row)

    def logd(self, *args):
        self.logger.debug(*args)


main_commands.reg_cmd(CommandHomeWork2)
