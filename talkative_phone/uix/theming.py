# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-14 10:56:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-14 11:00:53
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivymd.uix.picker import MDThemePicker


class Theming(Screen):
    def __init__(self, **kwargs):
        Builder.load_file('templates/theming.kv')
        super().__init__(**kwargs)
        self.md_theme_picker = MDThemePicker()

    def theme_picker_open(self):
        self.md_theme_picker.open()
