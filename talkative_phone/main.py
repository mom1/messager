# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-08 22:07:08
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-15 17:43:01
from dynaconf import settings
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.theming import ThemeManager
from kivymd.toast import toast
from kivymd.uix.dialog import MDInputDialog
from kivymd.uix.navigationdrawer import NavigationDrawerIconButton

from db import Chat, User
from db import database_lock as db_lock
from jim_mes import Message
from uix.chat_screen import ChatScreen
from uix.connection import Connection
from uix.contacts import Contacts
from uix.create_group import CreateGroup
from uix.find_contact import FinContact
from uix.theming import Theming


class EventServerMixin:
    events = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
    is_connected = BooleanProperty(False)

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
        # self.hide_widget(self.main_widget.ids.nav_drawer.ids.create_group)
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

    def get_screen(self, name_item):
        return self.main_widget.ids.scr_mngr.get_screen(name_item.lower())

    def done_connect(self, **kwargs):
        self.is_connected = True
        self.main_widget.ids.nav_drawer.ids.list.remove_widget(self.main_widget.ids.nav_drawer.ids.exit_app)
        self.make_menu()
        self.add_screen(FinContact())
        self.add_screen(CreateGroup())
        self.show_screen('contacts')

    def make_menu(self):
        self.main_widget.ids.nav_drawer.add_widget(MenuItem(
            text='Создать группу',
            icon='account-group',
            use_active=False,
            # screen='create_group',
            on_rel=self.open_create_group_dialog,
        ))
        self.main_widget.ids.nav_drawer.add_widget(MenuItem(
            text='Настройки',
            icon='settings',
            use_active=False,
            screen='Theming',
        ))
        self.main_widget.ids.nav_drawer.add_widget(self.main_widget.ids.nav_drawer.ids.exit_app)

    def show_info(self, msg):
        screen = 'info'
        info = self.get_screen(screen)
        info.update_info(msg)
        Clock.schedule_once(lambda *_: self.show_screen(screen), 0.1)

    def hide_widget(self, wid, dohide=True):
        if hasattr(wid, 'saved_attrs'):
            if not dohide:
                wid.height, wid.size_hint_y, wid.opacity, wid.disabled = wid.saved_attrs
                del wid.saved_attrs
        elif dohide:
            wid.saved_attrs = wid.height, wid.size_hint_y, wid.opacity, wid.disabled
            wid.height, wid.size_hint_y, wid.opacity, wid.disabled = 0, None, 0, True

    def open_create_group_dialog(self):
        def result(text_button, instance):
            current_user = User.by_name(settings.USER_NAME)
            text = str(instance.text_field.text)
            if instance.text_field.text:
                chat = Chat.filter_by(name=text).first()
                if chat:
                    toast('Ошибка Создание чата\nТакая группа уже существует')
                    return

                with db_lock:
                    chat = Chat.create(name=text, owner=current_user, is_personal=False)
                    chat.members.append(current_user)
                    chat.save()
                cg = self.get_screen('create_group')
                cg.instance_chat = chat
                print('set chat', cg.instance_chat)
                self.show_screen('create_group')
            toast(instance.text_field.text)

        input_dialog = MDInputDialog(
            title='Введите название группы',
            hint_text='Имя группы',
            size_hint=(0.8, 0.4),
            text_button_ok='Ok',
            events_callback=result,
        )
        input_dialog.open()

    def send_chat(self, chat):
        self.client.notify(f'send_{settings.MESSAGE}',
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


class MenuItem(NavigationDrawerIconButton):
    screen = StringProperty()

    def __init__(self, **kwargs):
        self.on_rel = kwargs.pop('on_rel', None)
        super().__init__(**kwargs)

    def on_release(self):
        toast(self.text)
        if self.screen:
            App.get_running_app().show_screen(self.screen)
        elif self.on_rel:
            self.on_rel()


if __name__ == '__main__':
    TalkativePhoneApp().run()
