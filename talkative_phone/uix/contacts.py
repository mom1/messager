# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-08 23:10:00
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-09 23:10:57
import base64

from dynaconf import settings
from kivy.app import App
from kivy.core.image import Image as CoreImage
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.metrics import dp
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen
from kivymd.uix.button import MDIconButton
from kivymd.uix.list import ILeftBody, ILeftBodyTouch

from db import User


class Contacts(Screen):
    def __init__(self, **kwargs):
        Builder.load_file('templates/contacts.kv')
        super().__init__(**kwargs)

    def make_data(self, *_):
        user = User.by_name(settings.USER_NAME)
        self.ids.rv_main.data = [{
            'viewclass':
            'RVRow',
            'text':
            str(x.username),
            'image':
            CoreImage('data:image/' + 'png;base64,' + base64.b64encode(x.avatar).decode('ascii')).texture if x.avatar else CoreImage('./templates/img/avatar.png').texture,
        } for x in user.get_chats()]


class AvatarSampleWidget(ILeftBody, Image):
    pass


class IconLeftSampleWidget(ILeftBodyTouch, MDIconButton):
    pass
