# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-08 22:07:08
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-14 20:40:47

from dynaconf import settings
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.uix.screenmanager import Screen
from kivymd.theming import ThemeManager
from kivymd.toast import toast
from kivymd.uix.navigationdrawer import NavigationDrawerIconButton

from uix.chat_screen import ChatScreen
from uix.connection import Connection
from uix.contacts import Contacts
from uix.theming import Theming
from uix.find_contact import FinContact


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
            Clock.schedule_once(lambda *_: method(**kwargs), 0.1)


class TalkativePhoneApp(EventServerMixin, App):
    title = 'Talkative Phone'
    theme_cls = ThemeManager()
    theme_cls.primary_palette = settings.get('primary', 'BlueGray')
    theme_cls.accent_palette = settings.get('accent', 'Gray')
    theme_cls.theme_style = settings.get('style', 'Dark')
    main_widget = None
    client = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.Window = Window
        self.events = {
            f'fail_{settings.AUTH}': self.exit_,
            f'fail': self.exit_,
            f'done_{settings.AUTH}': self.done_connect,
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
        self.add_screen(ChatScreen())
        self.add_screen(Theming())
        self.add_screen(InfoPage())

    def add_screen(self, screen):
        self.main_widget.ids.scr_mngr.add_widget(screen)

    def show_screen(self, name_item):
        self.main_widget.ids.scr_mngr.current = name_item.lower()

    def done_connect(self, **kwargs):
        self.main_widget.ids.nav_drawer.ids.list.remove_widget(self.main_widget.ids.nav_drawer.ids.connect_widget)
        self.add_screen(FinContact())
        self.show_screen('contacts')

    def show_info(self, msg):
        screen = 'info'
        info = self.main_widget.ids.scr_mngr.get_screen(screen)
        info.update_info(msg)
        Clock.schedule_once(lambda *_: self.show_screen(screen), 0.1)


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
