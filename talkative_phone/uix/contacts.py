# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-08 23:10:00
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-14 21:46:59
import base64

from dynaconf import settings
from kivy.app import App
from kivy.core.image import Image as CoreImage
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen
# from kivymd.toast import toast
from kivymd.uix.button import MDIconButton
from kivymd.uix.list import ILeftBody, ILeftBodyTouch

from db import User


class Contacts(Screen):
    def __init__(self, **kwargs):
        self.set_template()
        self.app = App.get_running_app()
        super().__init__(**kwargs)
        self.app.events[f'done_{settings.USERS_REQUEST}'] = self.make_data
        self.app.events[f'done_{settings.GET_CHATS}'] = self.make_data

    def set_template(self):
        Builder.load_file('templates/contacts.kv')

    def make_data(self, *args, **kwargs):
        Logger.info('Подготовка контактов')
        user = User.by_name(settings.USER_NAME)
        data = []
        search = kwargs.get('search', '')
        objects = user.get_chats(search) if kwargs.get('contacts', True) else user.not_contacts(search)
        for x in objects:
            username = str(x.username)
            if x.avatar:
                img = CoreImage('data:image/' + 'png;base64,' + base64.b64encode(x.avatar).decode('ascii')).texture
            else:
                img = CoreImage('./templates/img/avatar.png').texture
            data.append({
                'viewclass': 'RVRow',
                'text': username,
                'callback': self.select_active,
                'image': img,
            })
        self.ids.rv_main.data = data

    def select_active(self, row):
        # toast(f'Нажато {row.text}')
        app = App.get_running_app()
        app.main_widget.ids.toolbar.title = row.text
        app.show_screen('chat')


class AvatarSampleWidget(ILeftBody, Image):
    pass


class IconLeftSampleWidget(ILeftBodyTouch, MDIconButton):
    pass
