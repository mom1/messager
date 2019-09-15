# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-08 23:10:00
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-15 20:17:33
import base64

from dynaconf import settings
from kivy.app import App
from kivy.core.image import Image as CoreImage
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen
from kivymd.toast import toast
from kivymd.uix.button import MDIconButton
from kivymd.uix.list import ILeftBodyTouch, IRightBodyTouch

from db import User
from db import database_lock as db_lock
from errors import ContactExists, ContactNotExists, NotFoundUser
from jim_mes import Message

logger = Logger


class Contacts(Screen):
    def __init__(self, **kwargs):
        self.set_template()
        self.set_viewclass()
        self.app = App.get_running_app()
        super().__init__(**kwargs)
        self.app.events[f'done_{settings.USERS_REQUEST}'] = self.make_data
        self.app.events[f'done_{settings.GET_CHATS}'] = self.make_data

    def set_template(self):
        Builder.load_file('templates/contacts.kv')

    def set_viewclass(self):
        self.viewclass_item = 'RVRowDel'

    def get_raw_data(self, **kwargs):
        user = User.by_name(settings.USER_NAME)
        search = kwargs.get('search', '')
        return user.get_chats(search) if kwargs.get('contacts', True) else user.not_contacts(search)

    def make_data(self, *args, **kwargs):
        logger.info('Подготовка контактов')
        data = self.prepare_data(self.get_raw_data(**kwargs))
        self.set_data(data)

    def prepare_data(self, objects):
        data = []
        for x in objects:
            username = str(x.username)
            if x.avatar:
                img = CoreImage('data:image/' + 'png;base64,' + base64.b64encode(x.avatar).decode('ascii')).texture
            else:
                img = CoreImage('./templates/img/avatar.png').texture
            data.append({
                'viewclass': self.viewclass_item,
                'text': username,
                'callback': self.select_active,
                'callback_del': self.del_active,
                'image': img,
            })
        return data

    def set_data(self, data):
        self.ids.rv_main.data = data

    def select_active(self, row):
        self.app.main_widget.ids.toolbar.title = row.text
        self.app.show_screen('chat')

    def del_active(self, row):
        user = User.by_name(settings.USER_NAME)
        name_contact = row.text
        try:
            with db_lock:
                chat = user.del_contact(name_contact)
            self.app.client.notify(f'send_{settings.MESSAGE}', msg=Message(**{
                settings.ACTION: settings.DEL_CONTACT,
                settings.USER: settings.USER_NAME,
                settings.ACCOUNT_NAME: name_contact,
            }))
            self.app.send_chat(chat)
        except (ContactExists, NotFoundUser, ContactNotExists) as e:
            toast('Ошибка\n' + str(e))
            logger.error(e)
        else:
            self.make_data()


class AvatarSampleWidget(ILeftBodyTouch, Image):
    pass


class DelWidget(IRightBodyTouch, MDIconButton):
    pass
