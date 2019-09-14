# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-09-14 16:58:29
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-14 19:30:42
import base64
import logging
import time

from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.PublicKey import RSA
from dynaconf import settings

from db import Chat, User
from db import database_lock as db_lock
from jim_mes import Message

logger = logging.getLogger('gui')


class CommonGUI:
    """Общая функциональность гуи чата.

    Будет использоваться в QTClient. KivyClient and CliClient

    Attributes:
        client: Транспорт для отправки пример ClientTransport
        type_msg_in: тип входящих сообщений
        type_msg_out: тип исходящих сообщений

    """

    client = None
    type_msg_in = 1
    type_msg_out = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = self.get_client() or kwargs.get('client')
        self.chat_members = []
        self.current_user = self.get_current_user() or kwargs.get('current_user')
        self.current_chat = ''
        self.encryptors = None

    def get_client(self):
        return self.client

    def get_current_user(self):
        return User.by_name(settings.USER_NAME) if hasattr(User, '_session') else None

    def get_template_out_mes(self):
        return ''

    def get_template_in_mes(self):
        return ''

    def set_text_to_chat(self, mes_list):
        pass

    def clear_chat(self):
        pass

    def escape(self, msg):
        return msg

    def fill_chat(self):
        with db_lock:
            messages = Chat.chat_hiltory(self.current_chat, settings.MAX_MESSAGE_IN_CHAT)
        user = self.current_user

        style_mes_out = self.get_template_out_mes()
        style_mes_in = self.get_template_in_mes()

        self.clear_chat()

        mes_list = []
        with db_lock:
            for message in messages:
                if message.sender.username == user.username:
                    style_mes = style_mes_out
                    color = settings.COLOR_MESSAGE_OUT
                    type_msg = self.type_msg_out
                else:
                    style_mes = style_mes_in
                    color = settings.COLOR_MESSAGE_IN
                    type_msg = self.type_msg_in
                mes_list.append({
                    type_msg: style_mes(color=color, text=self.escape(message.text), created=message.created, user_name=message.sender.username),
                })

        self.set_text_to_chat(mes_list)

    def get_msg_text(self):
        return ''

    def clear_msg_text(self):
        pass

    def get_current_chat(self):
        return ''

    def set_current_chat(self, chat):
        pass

    def set_view_obj(self, obj):
        pass

    def critical(self, msg):
        logger.critical(msg)

    def make_encryptor(self, **kwargs):
        with db_lock:
            self.encryptors = {u.username: PKCS1_OAEP.new(RSA.import_key(u.pub_key)) for u in self.chat_members if u.pub_key}

    def set_ava(self, ava):
        pass

    def clear_ava(self):
        pass

    def set_active(self, current_chat=None):
        """Выбор активного пользователя."""
        chat_name = current_chat or self.get_current_chat()
        if not self.current_user:
            self.current_user = self.get_current_user()
        if not chat_name:
            return

        user = User.by_name(chat_name)
        chat = Chat.filter_by(name=chat_name).first() or next((c for c in user.get_chats() if c.is_personal), None)
        obj = user or chat

        self.chat_members = chat.members
        self.current_chat = chat.name
        self.set_current_chat(chat)
        self.set_view_obj(obj)
        client = self.get_client()
        for cm in self.chat_members:
            if self.current_user == cm:
                continue
            client.notify(settings.PUBLIC_KEY_REQUEST, contact=cm.username)
        self.make_encryptor()

        if obj:
            self.fill_chat()
            if obj.avatar:
                self.set_ava(obj.avatar)
            else:
                self.clear_ava()

    def recive_message(self, *args, **kwargs):
        msg = kwargs.get('msg')
        if self.current_chat in (getattr(msg, settings.SENDER, None), msg.chat):
            self.fill_chat()

    def send_message(self, extra=None):
        """Отправка сообщения."""
        text = extra or self.get_msg_text()
        if not self.current_chat or not text:
            return
        if not self.encryptors:
            self.set_active()
            time.sleep(1)
            if not self.encryptors:
                logger.warn(f'Нет ключа для этого чата {self.current_chat}')
                self.critical('Нет ключа для этого чата')
                return

        client = self.get_client()
        for username, encryptor in self.encryptors.items():
            mes_crypted = encryptor.encrypt(text.encode('utf8'))
            message = self.make_message(username, base64.b64encode(mes_crypted).decode('ascii'))
            client.notify(f'send_{settings.MESSAGE}', msg=message)

        Chat.create_msg(message, text=text)

        self.clear_msg_text()
        self.fill_chat()

    def make_message(self, username, text=''):
        """Создать объект сообщения.

        Args:
            username: (str) Name destination
            text: [description] (default: {''})

        Returns:
            :py:class:`~jim_mes.Message`

        """
        return Message(**{
            settings.ACTION: settings.MESSAGE,
            settings.SENDER: settings.USER_NAME,
            settings.DESTINATION: username,
            settings.MESSAGE_TEXT: text,
            'chat': self.current_chat,
        })
