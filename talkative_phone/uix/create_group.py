# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-15 13:21:59
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-15 19:10:28
# from dynaconf import settings
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import ObjectProperty
from kivymd.uix.chip import MDChip

from db import User

from .contacts import Contacts

logger = Logger


class CreateGroup(Contacts):
    instance_chat = ObjectProperty(allownone=True)

    def set_template(self):
        Builder.load_file('templates/create_group.kv')

    def set_viewclass(self):
        self.viewclass_item = 'RVRow'

    def on_enter(self, *largs):
        title = f'Добавление участников в группу {self.instance_chat.name}'
        self.app.main_widget.ids.toolbar.title = title
        self.app.main_widget.ids.toolbar.left_action_items = [['arrow-left', lambda x: self.app.show_screen('contacts')]]
        self.app.main_widget.ids.toolbar.right_action_items = []
        self.update_chips()
        self.make_data()

    def on_leave(self, *largs):
        self.app.main_widget.ids.toolbar.left_action_items = [['menu', lambda x: self.app.root.toggle_nav_drawer()]]
        self.ids.list_members.clear_widgets()

    def select_active(self, row):
        self.instance_chat.members.append(User.by_name(row.text))
        self.update_chips()

    def del_chip(self, username, *args):
        self.instance_chat.members.remove(User.by_name(username))
        self.update_chips()

    def update_chips(self):
        self.instance_chat.save()
        self.app.send_chat(self.instance_chat)
        self.ids.list_members.clear_widgets()
        for user in self.instance_chat.members:
            chip = MDChip(label=user.username, callback=self.del_chip)
            chip.icon = ''
            self.ids.list_members.add_widget(chip)
        self.make_data()

    def get_raw_data(self, **kwargs):
        search = kwargs.get('search', '')
        data = []
        if not self.instance_chat:
            return data
        for u in User.query().filter(User.id.notin_([i.id for i in self.instance_chat.members])).all():
            if search and search not in u.username:
                continue
            data.append(u)
        return data
