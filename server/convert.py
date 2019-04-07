# -*- coding: utf-8 -*-
# @Author: Max ST
# @Date:   2019-04-05 01:21:21
# @Last Modified by:   Max ST
# @Last Modified time: 2019-04-07 13:32:20
import csv
import json
import logging
import tempfile

from io import StringIO
from pathlib import Path
from yaml import dump, load

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class PrototypeDispatcher(object):
    def __init__(self):
        self._objects = {}

    def get_objects(self):
        """Get all objects"""
        return self._objects

    def register_object(self, name, obj):
        """Register an object"""
        self._objects[name] = obj

    def unregister_object(self, name):
        """Unregister an object"""
        del self._objects[name]


dispatcher = PrototypeDispatcher()


class Converter(object):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.type = kwargs.get('type', 'yaml')
        self.file_name = kwargs.get('file_name', None)
        self.logger = kwargs.get('logger', logging.getLogger(type(self).__name__))

    def read(self, data=None):
        self.file_name = data if data else self.file_name
        self.define_convert()
        self.logd(f'read from {self.type}')
        return self.convert().read(self.file_name)

    def reads(self, data):
        self.define_convert()
        self.logd(f'read from {self.type}')
        return self.convert().reads(data)

    def write(self, data, type_=None):
        if type_:
            self.type = type_
            self.file_name = None
        self.define_convert()
        self.logd(f'write to {self.type}')
        self.file_name = self.convert().write(data)
        self.logd(self.file_name)
        return self.file_name

    def dumps(self, data):
        self.define_convert()
        self.logd(f'dumps to {self.type}')
        return self.convert().dumps(data)

    def define_convert(self):
        if self.file_name:
            path = Path(self.file_name)
            self.type = path.suffix.strip('.')

        if self.type:
            self.convert = dispatcher.get_objects().get(self.type)

    def logd(self, *args):
        self.logger.debug(*args)

    def convert_file_to(self, file_name, to_type='csv'):
        self.file_name = file_name
        self.write(self.read(), to_type)
        return self.file_name


class Csv(object):

    def read(self, file_name):
        with Path(file_name).open() as f:
            reader = csv.DictReader(f)
            return [r for r in reader]

    def write(self, data):
        response = None
        writer = None
        with tempfile.NamedTemporaryFile(mode='w', prefix='test_file', suffix='.csv', delete=False) as ntf:
            for d in data:
                if not writer:
                    writer = csv.DictWriter(ntf, fieldnames=d.keys())
                    writer.writeheader()
                break
            writer.writerows(data)
            response = ntf.name
        return response

    def reads(self, data):
        f = StringIO(data)
        reader = csv.DictReader(f)
        return [r for r in reader]

    def dumps(self, data):
        stream = StringIO()
        getvalue = stream.getvalue
        writer = None
        for d in data:
            if not writer:
                writer = csv.DictWriter(stream, fieldnames=d.keys())
                writer.writeheader()
            break
        writer.writerows(data)
        return getvalue()


class Json(object):
    def read(self, file_name):
        with Path(file_name).open() as f:
            return json.load(f)

    def reads(self, data):
        return json.loads(data)

    def write(self, data):
        response = None
        with tempfile.NamedTemporaryFile(mode='w', prefix='test_file', suffix='.json', delete=False) as ntf:
            response = ntf.name
            json.dump(data, ntf, sort_keys=True, indent=4, ensure_ascii=False)
        return response

    def dumps(self, data):
        return json.dumps(data)


class Yaml(object):
    def read(self, file_name):
        with Path(file_name).open() as f:
            return load(f, Loader=Loader)

    def reads(self, data):
        f = StringIO(data)
        return load(f, Loader=Loader)

    def write(self, data):
        response = None
        with tempfile.NamedTemporaryFile(mode='w', prefix='test_file', suffix='.yaml', delete=False) as ntf:
            response = ntf.name
            dump(data, ntf, default_flow_style=False, allow_unicode=True, indent=4)
        return response

    def dumps(self, data):
        return dump(data, default_flow_style=False, allow_unicode=True, indent=4)


dispatcher.register_object('csv', Csv)
dispatcher.register_object('json', Json)
dispatcher.register_object('yaml', Yaml)
