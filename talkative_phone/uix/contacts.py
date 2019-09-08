# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-08 23:10:00
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-08 23:15:08
from kivy.app import App
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.uix.screenmanager import Screen


class Contacts(Screen):
    def __init__(self, **kwargs):
        Builder.load_file('templates/contacts.kv')
        super().__init__(**kwargs)
