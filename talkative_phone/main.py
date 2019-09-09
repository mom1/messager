# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-08 22:07:08
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-10 00:04:41

from dynaconf import settings
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.uix.screenmanager import Screen
from kivymd.theming import ThemeManager
from kivymd.toast import toast

from uix.connection import Connection
from uix.contacts import Contacts


class EventServerMixin:
    events = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.events = {
        #     f'new_{settings.MESSAGE}': self.incoming_message,
        #     f'done_{settings.USERS_REQUEST}': self.should_update_contact,
        #     f'done_{settings.GET_CHATS}': self.should_update_contact,
        #     f'done_{settings.PUBLIC_KEY_REQUEST}': self.make_encryptor,
        #     f'fail_{settings.AUTH}': self.exit_,
        #     f'fail': self.exit_,
        # }

    def register_event(self):
        """Регистрация событий."""
        app = App.get_running_app()
        if not app.client:
            return
        for event in self.events.keys():
            app.client.attach(self, event)

    def update(self, **kwargs):
        """Приемник событий.

        пробрасывает события интерфейсу

        Args:
            **kwargs: Параметры

        """
        event = kwargs.get('event')
        Logger.info(f'gui catch {event}')
        method = self.events.get(event)
        if method:
            method(**kwargs)


class TalkativePhoneApp(EventServerMixin, App):
    title = 'Talkative Phone'
    theme_cls = ThemeManager()
    theme_cls.primary_palette = 'BlueGray'
    theme_cls.accent_palette = 'Gray'
    theme_cls.theme_style = 'Dark'
    main_widget = None
    client = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.Window = Window
        self.events = {
            f'fail_{settings.AUTH}': self.exit_,
            f'fail': self.exit_,
            f'done_{settings.AUTH}': lambda **kwargs: self.show_screen('contacts'),
            400: lambda **kwargs: toast(f'{kwargs.get("msg", "Error")}'),
        }

    def exit_(self, *args, **kwargs):
        toast('Error! App will be closed.')
        Clock.schedule_once(self.stop, 5)

    def build(self):
        self.main_widget = Builder.load_file('templates/talkativephone.kv')
        return self.main_widget

    def on_start(self):
        self.add_screen(Connection())
        self.add_screen(Contacts())
        self.add_screen(InfoPage())
        # self.root.ids.nav_drawer.add_widget(NavigationDrawerIconButton(icon='checkbox-blank-circle', text='Item menu %d' % i, on_release=lambda x, y=i: self.callback(x, y)))
        # for i in range(15):
        #     self.root.ids.nav_drawer.add_widget(
        #     NavigationDrawerIconButton(
        #         icon='checkbox-blank-circle', text='Item menu %d' % i, on_release=lambda x, y=i: self.callback(x, y)))

    def add_screen(self, screen):
        self.main_widget.ids.scr_mngr.add_widget(screen)

    def show_screen(self, name_item):
        self.main_widget.ids.scr_mngr.current = name_item.lower()


class InfoPage(Screen):
    def __init__(self, *args, **kwargs):
        Builder.load_string("""
<InfoPage>
    name: 'info'

    GridLayout:
        id: grid
        cols: 1

        MDLabel:
            id: message
            font_style: 'H4'
            theme_text_color: 'Primary'
            halign: 'center'
            valign: 'middle'
            height: self.texture_size[1]
        """)
        super().__init__(**kwargs)

    def update_info(self, message):
        self.ids.message.text = str(message)


if __name__ == '__main__':
    TalkativePhoneApp().run()
