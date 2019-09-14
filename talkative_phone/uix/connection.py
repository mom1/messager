# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-08 19:35:46
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-14 19:41:29
import os
import time
from pathlib import Path

from Cryptodome.PublicKey import RSA
from dynaconf import settings
from dynaconf.loaders import yaml_loader as loader
from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.uix.screenmanager import Screen

from async_core import ClientTransport


class Connection(Screen):
    def __init__(self, **kwargs):
        Builder.load_file('templates/connection.kv')
        super().__init__(**kwargs)

    def show_password(self, field, button):
        field.password = not field.password
        field.focus = True
        button.icon = 'eye' if button.icon == 'eye-off' else 'eye-off'

    def connect(self):
        app = App.get_running_app()
        settings.set('user_name', self.ids.field_username.text)
        settings.set('password', self.ids.field_password.text)
        screen = 'info'
        info = app.main_widget.ids.scr_mngr.get_screen(screen)
        info.update_info(f'Attempt to join {settings.HOST}:{settings.PORT} as {settings.USER_NAME}')

        Clock.schedule_once(lambda *_: app.show_screen(screen), 0.1)

        Logger.debug(f'Connect to server {settings.get("host")}:{settings.get("port")} with name "{settings.USER_NAME}"')
        self.process_key()

        app.client = ClientTransport()
        app.client.daemon = True
        app.register_event()
        app.client.start()
        time.sleep(1)

    def process_key(self, *_):
        """Загружаем ключи с файла, если же файла нет, то генерируем новую пару."""
        secret = f'.secret.{settings.USER_NAME}.yaml'
        settings.INCLUDES_FOR_DYNACONF.append(secret)
        key_file = Path.cwd().joinpath(Path(f'{secret}'))

        user_name = settings.get('USER_NAME')
        passwd = settings.get('PASSWORD')

        settings.load_file(path=str(key_file))
        settings.set('USER_NAME', user_name)
        settings.set('PASSWORD', passwd)
        key = settings.get('USER_KEY')
        if not key:
            keys = RSA.generate(2048, os.urandom)
            key = keys.export_key().decode('ascii')
            loader.write(key_file, {'DEFAULT': {
                'USER_KEY': key,
                'PASSWORD': settings.PASSWORD,
            }})
            settings.load_file(path=str(key_file))
            key = settings.get('USER_KEY')
