# -*- coding: utf-8 -*-
"""Графический интерфейс взаимодействия с пользователем."""
# @Author: MaxST
# @Date:   2019-07-31 09:03:14
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-10 00:38:26

import base64
import logging
from pathlib import Path

from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.PublicKey import RSA
from dynaconf import settings
from PyQt5 import uic
from PyQt5.Qt import QAction
from PyQt5.QtCore import QObject, QSettings, pyqtSlot
from PyQt5.QtGui import QIcon, QPixmap, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QDialog, QMainWindow, QMessageBox

from .db import User, UserHistory, UserMessages
from .errors import ContactExists, ContactNotExists, NotFoundUser
from .jim_mes import Message

logger = logging.getLogger('gui')


class SaveGeometryMixin(object):
    """Миксин сохранения геометрии."""

    def init_ui(self):
        """Инициализация."""
        self.restore_size_pos()

    def restore_size_pos(self):
        """Востановление размера и позиции."""
        self.settings = QSettings(type(self).__name__, settings.USER_NAME)
        size = self.settings.value('size', None)
        pos = self.settings.value('pos', None)
        if size:
            self.resize(size)
        if pos:
            self.move(pos)

    def closeEvent(self, e):  # noqa
        """Запись позиции и размера при закрытии.

        Args:
            e: [description]
        """
        if hasattr(self, 'save_size'):
            self.save_size()
        self.settings.setValue('size', self.size())
        self.settings.setValue('pos', self.pos())
        e.accept()


class UserAuth(SaveGeometryMixin, QDialog):
    """Окно авторизации пользователя."""

    def __init__(self):  # noqa
        super().__init__()
        uic.loadUi(Path(__file__).parent.joinpath(Path('templates/auth_client.ui')), self)
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса."""
        self.buttonBox.accepted.connect(self.accept_auth)
        self.show()

    def accept_auth(self):
        """Подтверждение введеных данных."""
        self.accepted = True

    def get_auth(self):
        """Вовзращает введеные данные."""
        return self.editName.text(), self.editPass.text()


class ClientGui(QObject):
    """Класс прослойка."""

    def __init__(self, client):  # noqa
        super().__init__()
        global main_window
        main_window = ClientMainWindow(client)

    def is_alive(self):  # noqa
        return False

    @pyqtSlot(Message)
    def update(self, *args, **kwargs):
        """Приемник событий.

        пробрасывает события интерфейсу

        Args:
            *args: Параметры
            **kwargs: Параметры

        """
        main_window.update(*args, **kwargs)


class ClientMainWindow(SaveGeometryMixin, QMainWindow):
    """Основное окно.

    Attributes:
        STYLE_IN_MES: Стиль входящих сообщений
        STYLE_OUT_MES: Стиль исходящих сообщений

    """

    STYLE_IN_MES = Path(__file__).parent.joinpath(Path('templates/style_in_message.html'))
    STYLE_OUT_MES = Path(__file__).parent.joinpath(Path('templates/style_out_message.html'))

    def __init__(self, client):  # noqa
        self.client = client
        super().__init__()
        uic.loadUi(Path(__file__).parent.joinpath(Path('templates/client.ui')), self)
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса."""
        super().init_ui()
        self.setWindowTitle(f'You are: {settings.USER_NAME}')
        self.MsgBox = QMessageBox()
        self.contacts_list_state = 'exists'
        self.current_chat = None
        self.update_contact()
        self.listContact.doubleClicked.connect(self.select_active_user)
        self.editMessages.clear()
        self.lblContact.setText('')
        self.btnSend.clicked.connect(self.send_message)
        self.addContact.clicked.connect(self.switch_list_state)
        action = QAction('Удалить', self)
        action.triggered.connect(self.del_contact)
        self.listContact.addAction(action)
        self.encryptor = None
        self.show()

    def restore_size_pos(self):
        """Восстановление состояния сплитера."""
        super().restore_size_pos()
        splitter_sizes = self.settings.value('splitter', None)
        if splitter_sizes is not None:
            self.splitter.restoreState(splitter_sizes)

    def save_size(self):
        """Сохранение состояния сплитера."""
        self.settings.setValue('splitter', self.splitter.saveState())

    def update_contact(self):
        """Обновление контактов."""
        user = User.by_name(settings.USER_NAME)
        if not user:
            return
        if self.contacts_list_state != 'new':
            contacts_list = [i.contact.username for i in user.contacts]
        else:
            contacts_list = [i.username for i in user.not_contacts()]

        self.contacts_model = QStandardItemModel()
        index = None
        for i in sorted(contacts_list):
            item = QStandardItem(i)
            item.setEditable(False)
            self.contacts_model.appendRow(item)
            if self.current_chat and self.current_chat == i:
                index = item.index()
        self.listContact.setModel(self.contacts_model)
        if index:
            self.listContact.setCurrentIndex(index)

    def select_active_user(self):
        """Выбор активного пользователя."""
        self.current_chat = self.listContact.currentIndex().data()
        if self.contacts_list_state == 'new':
            self.add_contact()
        else:
            request = Message(**{
                settings.ACTION: settings.PUBLIC_KEY_REQUEST,
                settings.SENDER: settings.USER_NAME,
                settings.DESTINATION: self.current_chat,
            })
            self.client.send_message(request)
        self.lblContact.setText(f'{self.current_chat}:')
        self.fill_chat()

    def fill_chat(self):
        """Заполнение чата."""
        messages = UserMessages.chat_hiltory(self.current_chat, 20)

        self.editMessages.clear()
        mes_list = []
        stop = len(messages) + 1
        for i in range(-1, -stop, -1):
            message = messages[i]
            if message.receiver.username == self.current_chat:
                style_mes = self.STYLE_OUT_MES.read_text().format
                color = settings.COLOR_MESSAGE_OUT
            else:
                style_mes = self.STYLE_IN_MES.read_text().format
                color = settings.COLOR_MESSAGE_IN
            mes_list.append(style_mes(color=color, text=message.message, created=message.created))
        self.editMessages.setHtml(''.join(mes_list))

    def update(self, message):
        """Разборщик внешних событий.

        Args:
            message: :py:class:`~jim_mes.Message`

        """
        if message.response == 205:
            if self.contacts_list_state == 'new':
                self.update_contact()
        elif message.response == 511:
            if self.current_chat == getattr(message, settings.ACCOUNT_NAME, ''):
                key = getattr(message, settings.DATA, '')
                self.encryptor = PKCS1_OAEP.new(RSA.import_key(key))
        elif getattr(message, settings.SENDER, None) == self.current_chat:
            self.fill_chat()

    def send_message(self):
        """Отправка сообщения."""
        if not self.current_chat or not self.editMessage.text():
            return
        if not self.encryptor:
            logger.warn(f'Нет ключа для этого чата {self.current_chat}')
            self.MsgBox.critical(self, 'Ошибка', 'Нет ключа для этого чата')
            return
        mes_crypted = self.encryptor.encrypt(self.editMessage.text().encode('utf8'))
        message = self.make_message(base64.b64encode(mes_crypted).decode('ascii'))
        self.client.send_message(message)
        with self.client.db_lock:
            UserHistory.proc_message(settings.USER_NAME, self.current_chat)
            UserMessages.create(sender=User.by_name(settings.USER_NAME), receiver=User.by_name(self.current_chat), message=self.editMessage.text())
        self.editMessage.clear()
        self.fill_chat()

    def make_message(self, text=''):
        """Создать объект сообщения.

        Args:
            text: [description] (default: {''})

        Returns:
            :py:class:`~jim_mes.Message`

        """
        return Message(**{
            settings.ACTION: settings.MESSAGE,
            settings.SENDER: settings.USER_NAME,
            settings.DESTINATION: self.current_chat,
            settings.MESSAGE_TEXT: text,
        })

    def switch_list_state(self):
        """Переключатель окна с контактами в разные состояния."""
        self.editMessages.clear()
        self.lblContact.setText('')
        if self.contacts_list_state != 'new':
            self.contacts_list_state = 'new'
            icon = QIcon(QPixmap(str(Path(__file__).parent.joinpath(Path('templates/img/list-contacts.png')))))
        else:
            self.contacts_list_state = 'exists'
            icon = QIcon(QPixmap(str(Path(__file__).parent.joinpath(Path('templates/img/add-contacts.png')))))
        self.addContact.setIcon(icon)
        self.update_contact()

    def add_contact(self):
        """Добавление контакта."""
        user = User.by_name(settings.USER_NAME)
        try:
            user.add_contact(self.current_chat)
            self.client.send_message(Message(**{
                settings.ACTION: settings.ADD_CONTACT,
                settings.USER: settings.USER_NAME,
                settings.ACCOUNT_NAME: self.current_chat,
            }))
        except (ContactExists, NotFoundUser, ContactNotExists) as e:
            self.MsgBox.critical(self, 'Ошибка', str(e))
            logger.error(e)
        else:
            self.switch_list_state()

    def del_contact(self):
        """Удаление контакта."""
        user = User.by_name(settings.USER_NAME)
        name_contact = self.listContact.currentIndex().data()
        try:
            user.del_contact(name_contact)
            self.client.send_message(Message(**{
                settings.ACTION: settings.DEL_CONTACT,
                settings.USER: settings.USER_NAME,
                settings.ACCOUNT_NAME: name_contact,
            }))
        except (ContactExists, NotFoundUser, ContactNotExists) as e:
            self.MsgBox.critical(self, 'Ошибка', str(e))
            logger.error(e)
        else:
            self.update_contact()
