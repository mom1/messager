# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-11 21:33:59
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-15 17:25:59
# from datetime import datetime

# from Cryptodome.PublicKey import RSA
from dynaconf import settings
from kivy.app import App
# from Cryptodome.Cipher import PKCS1_OAEP
from kivy.clock import Clock
# from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.utils import escape_markup

from uix.common_gui import CommonGUI

logger = Logger


class ChatScreen(CommonGUI, Screen):
    def __init__(self, **kwargs):
        Builder.load_file('templates/chat_screen.kv')
        self.app = App.get_running_app()
        super().__init__(**kwargs)
        Window.bind(on_key_down=self.on_key_down)
        self.ids.new_message.ids.field.text_validate_unfocus = False
        self.app.events[f'new_{settings.MESSAGE}'] = self.recive_message
        self.app.events[f'done_{settings.PUBLIC_KEY_REQUEST}'] = self.make_encryptor

    def back(self, *args):
        self.app.main_widget.ids.toolbar.left_action_items = [['menu', lambda x: self.app.root.toggle_nav_drawer()]]
        self.app.show_screen('contacts')

    def on_key_down(self, instance, keyboard, keycode, text, modofiers):
        if keycode == 40:
            self.send_message()

    def get_client(self):
        return getattr(self.app, 'client', None)

    def get_msg_text(self):
        return self.ids.new_message.text

    def clear_msg_text(self):
        self.ids.new_message.text = ''
        Clock.schedule_once(self.focus_text_input, 0.2)

    def get_current_chat(self):
        return self.app.main_widget.ids.toolbar.title

    def set_current_chat(self, chat):
        menu = []
        if not chat.is_personal:
            menu = [['account-multiple-plus', lambda x: self.edit_group(chat)]]
        self.app.main_widget.ids.toolbar.right_action_items = menu
        self.current_chat = chat.name or ''

    def edit_group(self, chat):
        group = self.app.get_screen('create_group')
        group.instance_chat = chat
        self.app.show_screen(group.name)

    def set_view_obj(self, obj):
        self.app.main_widget.ids.toolbar.title = obj.username or ''

    def set_ava(self, ava):
        # TODO: Avatar to tolbar?
        pass

    def focus_text_input(self, *_):
        self.ids.new_message.focus = True

    # for fill_chat

    def get_template_out_mes(self):
        return '[size=10][color={color}] [size=8]{created}[/size][/color][/size]\n{text}\n'.format

    def get_template_in_mes(self):
        return '[size=10][color={color}][b]{user_name}[/b] [size=8]{created}[/size][/color][/size]\n{text}\n'.format

    def set_text_to_chat(self, mes_list):
        Clock.schedule_once(lambda *_: self.ids.history.update_chat(mes_list), 0.2)

    def clear_chat(self):
        Clock.schedule_once(lambda *_: self.ids.history.set_in(''), 0.1)
        Clock.schedule_once(lambda *_: self.ids.history.set_out(''), 0.1)

    def escape(self, msg):
        return escape_markup(msg)


class ScrollableLabel(ScrollView):
    def update_chat(self, messages):
        types = {1: self.append_in, 0: self.append_out}
        for msg in messages:
            for type_msg, text in msg.items():
                types[type_msg](text)

    def set_in(self, msg):
        self._set_chat_common(msg, self.ids.incoming_messages)

    def set_out(self, msg):
        self._set_chat_common(msg, self.ids.outcoming_messages)

    def append_in(self, msg, sync=True):
        self._append_chat_common(msg, self.ids.incoming_messages)
        if sync:
            msg = '\n'.join((' ' * len(i) for i in msg.split('\n')))
            self.append_out(msg + '\n', sync=False)

    def append_out(self, msg, sync=True):
        self._append_chat_common(msg, self.ids.outcoming_messages)
        if sync:
            msg = '\n'.join((' ' * len(i) for i in msg.split('\n')))
            self.append_in(msg + '\n', sync=False)

    def _set_chat_common(self, msg, widget):
        widget.text = msg
        self.update_chat_history_layout()
        self.scroll_to(self.ids.scroll_to_point)

    def _append_chat_common(self, msg, widget):
        msg = widget.text + msg
        self._set_chat_common(msg, widget)

    def update_chat_history_layout(self, *_):
        height = max(self.ids.outcoming_messages.texture_size[1], self.ids.incoming_messages.texture_size[1])
        self.ids.layout.height = height + 80


class MyMDTextFieldClear(BoxLayout):
    hint_text = StringProperty()
    text = StringProperty()
    password = BooleanProperty(False)
    focus = BooleanProperty(False)
    password_mask = StringProperty('*')

    def refresh_field(self, instance_field, instance_clear_button):
        def refresh_field(interval):
            instance_clear_button.custom_color = (instance_field.line_color_normal)
            instance_field.focus = True
            instance_field.text = ''

        Clock.schedule_once(refresh_field, 0.2)
