# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-14 19:55:09
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-14 21:37:23
from dynaconf import settings
from kivy.lang import Builder
from kivy.logger import Logger

from db import User
from db import database_lock as db_lock
from errors import ContactExists, ContactNotExists, NotFoundUser
from jim_mes import Message

from .contacts import Contacts

logger = Logger


class FinContact(Contacts):
    def set_template(self):
        Builder.load_file('templates/find_contact.kv')

    def on_enter(self, *largs):
        self.app.main_widget.ids.toolbar.title = 'Найти контакты'
        self.app.main_widget.ids.toolbar.left_action_items = [['arrow-left', lambda x: self.app.show_screen('contacts')]]
        self.make_data(contacts=False)

    def on_leave(self, *largs):
        self.app.main_widget.ids.toolbar.left_action_items = [['menu', lambda x: self.app.root.toggle_nav_drawer()]]
        self.app.main_widget.ids.toolbar.title = 'Контакты'
        self.app.main_widget.ids.toolbar.right_action_items = [['account-search', lambda x: self.app.show_screen('find_contact')]]
        self.make_data()

    def select_active(self, row):
        # toast(f'Нажато {row.text}')
        self.add_contact(row.text)
        self.app.show_screen('contacts')

    def add_contact(self, current_chat):
        """Добавление контакта."""
        user = User.by_name(settings.USER_NAME)
        try:
            with db_lock:
                chat = user.add_contact(current_chat)
            self.app.client.notify(f'send_{settings.MESSAGE}',
                                   msg=Message(**{
                                       settings.ACTION: settings.ADD_CONTACT,
                                       settings.USER: settings.USER_NAME,
                                       settings.ACCOUNT_NAME: current_chat,
                                   }))
            self.send_chat(chat)
        except (ContactExists, NotFoundUser, ContactNotExists) as e:
            self.app.show_info('Ошибка\n' + str(e))
            logger.error(e)

    def send_chat(self, chat):
        self.app.client.notify(f'send_{settings.MESSAGE}',
                               msg=Message(
                                   **{
                                       settings.ACTION: settings.EDIT_CHAT,
                                       settings.USER: settings.USER_NAME,
                                       settings.DATA: {
                                           'name': chat.name,
                                           'owner': chat.owner.username if chat.owner else None,
                                           'is_personal': chat.is_personal,
                                           'members': [i.username for i in chat.members],
                                       },
                                   }))
