# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-01 21:30:28
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-02 02:09:36
import logging
import logging.config
import os
import sys
import time
from pathlib import Path

import kivy
from Cryptodome.PublicKey import RSA
from dynaconf import settings
from dynaconf.loaders import yaml_loader as loader
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.recycleview import RecycleView
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from talkative_phone.async_core import ClientTransport
from talkative_phone.db import User

kivy.require('1.11.1')
if getattr(sys, 'frozen', False):
    # frozen
    cfile = Path(sys.executable).parent
else:
    cfile = Path(__file__).parent

cwd = cfile
os.environ['ROOT_PATH_FOR_DYNACONF'] = str(cwd)

Builder.load_string('''
<ContactsPage>:
    viewclass: 'Label'
    RecycleBoxLayout:
        default_size: None, dp(56)
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
        orientation: 'vertical'
''')


class LayoutMixin:
    def do_layout(self, *args, **kwargs):
        super().do_layout()
        width, height = Window.size
        if width < 300:
            Window.size = 300, Window.size[1]
        if height < 300:
            Window.size = Window.size[0], 300


class ConnectPage(LayoutMixin, GridLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.cols = 2
        self.padding = 10
        self.spacing = 10
        self.add_widget(Label(text='Login:'))
        self.username = TextInput(text='maxst' or '', multiline=False)
        self.add_widget(self.username)

        self.add_widget(Label(text='Password:'))
        self.password = TextInput(text='123', password=True, multiline=False)
        self.add_widget(self.password)

        self.add_widget(Label())

        self.btnJoin = Button(text='join')
        self.btnJoin.bind(on_press=self.join_button)
        self.add_widget(self.btnJoin)

        self.events = {
            # f'new_{settings.MESSAGE}': self.incoming_message,
            # f'done_{settings.USERS_REQUEST}': self.should_update_contact,
            # f'done_{settings.GET_CHATS}': self.should_update_contact,
            # f'done_{settings.PUBLIC_KEY_REQUEST}': self.make_encryptor,
            f'fail_{settings.AUTH}': self.exit_,
            f'fail': self.exit_,
        }

    def register_event(self):
        """Регистрация событий."""
        for event in self.events.keys():
            self.client.attach(self, event)

    def update(self, **kwargs):
        """Приемник событий.

        пробрасывает события интерфейсу

        Args:
            **kwargs: Параметры

        """
        event = kwargs.get('event')
        logger.info(f'gui catch {event}')
        method = self.events.get(event)
        if method:
            method(**kwargs)

    def join_button(self, instance):
        global logger
        username = self.username.text
        password = self.password.text
        settings.set('USER_NAME', username)
        settings.set('PASSWORD', password)
        info = f'Attempt to join {settings.HOST}:{settings.PORT} as {username}'
        chat_app.info_page.update_info(info)
        chat_app.screen_manager.current = 'Info'

        _configure_logger(settings.get('LOGGING_LEVEL'))
        logger = logging.getLogger('client_phone')
        logger.info('test')
        logger.debug(f'Connect to server {settings.get("host")}:{settings.get("port")} with name "{settings.USER_NAME}"')
        logger.warning('warning')
        logger.critical('critical')
        _process_key()
        Clock.schedule_once(self.connect, 1)

    def connect(self, *_):
        self.client = ClientTransport()
        self.client.daemon = True
        self.register_event()
        self.client.start()
        time.sleep(1)

        # chat_app.create_chat_page()
        chat_app.create_contact_page()
        chat_app.screen_manager.current = 'Contacts'

    def exit_(self, msg='Error auth', **kwargs):
        show_error(msg)


class InfoPage(LayoutMixin, GridLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.message = Label(halign='center', valign='middle', font_size=30)
        self.message.bind(width=self.update_text_width)
        self.add_widget(self.message)

    def update_text_width(self, *_):
        self.message.text_size = (self.message.width * 0.9, None)

    def update_info(self, message):
        self.message.text = str(message)


class ScrollableLabel(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = GridLayout(cols=1, size_hint_y=None)
        self.add_widget(self.layout)

        self.chat_history = Label(size_hint_y=None, markup=True)
        self.scroll_to_point = Label()

        self.layout.add_widget(self.chat_history)
        self.layout.add_widget(self.scroll_to_point)

    def update_chat_history(self, message):

        self.chat_history.text += '\n' + message

        self.layout.height = self.chat_history.texture_size[1] + 15
        self.chat_history.height = self.chat_history.texture_size[1]
        self.chat_history.text_size = (self.chat_history.width * 0.98, None)

        self.scroll_to(self.scroll_to_point)

    def update_chat_history_layout(self, _=None):
        self.layout.height = self.chat_history.texture_size[1] + 15
        self.chat_history.height = self.chat_history.texture_size[1]
        self.chat_history.text_size = (self.chat_history.width * 0.98, None)


class ChatPage(LayoutMixin, GridLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.rows = 2

        self.history = ScrollableLabel(height=Window.size[1] * 0.9, size_hint_y=None)
        self.add_widget(self.history)

        self.new_message = TextInput(width=Window.size[0] * 0.8, size_hint_x=None, multiline=False)
        self.send = Button(text='Send')
        self.send.bind(on_press=self.send_message)

        bottom_line = GridLayout(cols=2)
        bottom_line.add_widget(self.new_message)
        bottom_line.add_widget(self.send)
        self.add_widget(bottom_line)

        Window.bind(on_key_down=self.on_key_down)
        Clock.schedule_once(self.focus_text_input, 1)
        self.bind(size=self.adjust_fields)

    def adjust_fields(self, *_):
        if Window.size[1] * 0.1 < 50:
            new_height = Window.size[1] - 50
        else:
            new_height = Window.size[1] * 0.9
        self.history.height = new_height

        if Window.size[0] * 0.2 < 160:
            new_width = Window.size[0] - 160
        else:
            new_width = Window.size[0] * 0.8
        self.new_message.width = new_width

        Clock.schedule_once(self.history.update_chat_history_layout, 0.01)

    def on_key_down(self, instance, keyboard, keycode, text, modofiers):
        if keycode == 40:
            self.send_message()

    def send_message(self, *_):
        msg = self.new_message.text
        self.new_message.text = ''
        if msg:
            self.history.update_chat_history(f'[color=dd2020]{settings.USER_NAME}[/color] > {msg}')
            # TODO: send msg to socket

        Clock.schedule_once(self.focus_text_input, 0.1)

    def focus_text_input(self, *_):
        self.new_message.focus = True

    def incomming_message(self, username, msg):
        self.history.update_chat_history(f'[color=20dd20]{username}[/color] > {msg}')


class ContactsPage(RecycleView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        user = User.by_name(settings.USER_NAME)
        self.data = [{'text': str(x.username)} for x in user.get_chats()]


class AppTalkative(App):
    def build(self):
        self.screen_manager = ScreenManager()
        self.connect_page = ConnectPage()
        self.add_screen('Connect', self.connect_page)

        self.info_page = InfoPage()
        self.add_screen('Info', self.info_page)

        return self.screen_manager

    def create_chat_page(self):
        self.chat_page = ChatPage()
        self.add_screen('Chat', self.chat_page)

    def create_contact_page(self):
        self.contact_page = ContactsPage()
        self.add_screen('Contacts', self.contact_page)

    def add_screen(self, name, obj):
        screen = Screen(name=name)
        screen.add_widget(obj)
        self.screen_manager.add_widget(screen)


def show_error(message):
    chat_app.info_page.update_info(message)
    chat_app.screen_manager.current = 'Info'
    Clock.schedule_once(sys.exit, 10)


def _process_key(*_):
    """Загружаем ключи с файла, если же файла нет, то генерируем новую пару."""
    secret = f'.secret.{settings.USER_NAME}.yaml'
    settings.INCLUDES_FOR_DYNACONF.append(secret)
    key_file = Path.cwd().joinpath(Path(f'{secret}'))

    user_name = settings.get('USER_NAME')
    passwd = settings.get('PASSWORD')

    settings.load_file(path=key_file)
    settings.set('USER_NAME', user_name)
    settings.set('PASSWORD', passwd)
    key = settings.get('USER_KEY')
    if not key:
        keys = RSA.generate(2048, os.urandom)
        key = keys.export_key().decode('ascii')
        loader.write(key_file, {'DEFAULT': {
            'USER_KEY': key,
            'PASSWORD': settings.PASSWORD,
        }})
        settings.load_file(path=key_file)
        key = settings.get('USER_KEY')


def _configure_logger(verbose=0):
    class MaxLevelFilter(logging.Filter):
        """Filters (lets through) all messages with level < LEVEL"""
        def __init__(self, level):
            self.level = level

        def filter(self, record):  # noqa
            return record.levelno <= self.level
            # and record.module in ('client', 'Converter', 'decorators', 'asyncio', 'async_core', 'core')

    root_logger = logging.root
    level = settings.get('LOGGING_LEVEL')

    log_dir = cwd.joinpath(Path(settings.get('LOG_DIR')))
    log_dir.mkdir(parents=True, exist_ok=True)

    stream_handler = logging.StreamHandler()
    # stream_handler.addFilter(MaxLevelFilter(level))
    # stream_handler.addFilter()
    log_file_err = Path(f'{log_dir}/Client_{settings.USER_NAME}_error.log')
    error_handler = logging.FileHandler(log_file_err, encoding=settings.get('encoding'))
    error_handler.setLevel(logging.ERROR)
    log_file = Path(f'{log_dir}/Client_{settings.USER_NAME}.log')
    file_handler = logging.FileHandler(log_file, encoding=settings.get('encoding'))
    file_handler.addFilter(MaxLevelFilter(logging.INFO))
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[
            error_handler,
            file_handler,
            stream_handler,
        ],
    )

    if verbose == 0:
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG

    root_logger.setLevel(level)


chat_app = AppTalkative()
chat_app.run()
