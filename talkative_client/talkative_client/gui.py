# -*- coding: utf-8 -*-
"""Графический интерфейс взаимодействия с пользователем."""
# @Author: MaxST
# @Date:   2019-07-31 09:03:14
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-26 09:59:51

import base64
import logging
import sys
import time
from pathlib import Path

from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.PublicKey import RSA
from dynaconf import settings
from PyQt5 import uic
from PyQt5.Qt import QAction
from PyQt5.QtCore import QObject, QSettings, pyqtSlot, QThread
from PyQt5.QtGui import QIcon, QPixmap, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QDialog, QMainWindow, QMenu, QMessageBox

from .db import User, UserHistory, UserMessages
from .db import database_lock as db_lock
from .errors import ContactExists, ContactNotExists, NotFoundUser
from .gui_profile import UserWindow
from .jim_mes import Message

logger = logging.getLogger('gui')
if getattr(sys, 'frozen', False):
    # frozen
    cfile = Path(sys.executable).parent
else:
    cfile = Path(__file__).parent


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
        uic.loadUi(cfile.joinpath(Path('templates/auth_client.ui')), self)
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса."""
        super().init_ui()
        self.buttonBox.accepted.connect(self.accept_auth)
        self.show()

    def accept_auth(self):
        """Подтверждение введеных данных."""
        self.accepted = True

    def get_auth(self):
        """Вовзращает введеные данные."""
        return self.editName.text(), self.editPass.text()


class ClientGui(object):
    """Класс прослойка."""
    def __init__(self, client):  # noqa
        super().__init__()
        global main_window
        main_window = ClientMainWindow(client)

    def is_alive(self):  # noqa
        return False


class ClientMainWindow(SaveGeometryMixin, QMainWindow):
    """Основное окно.

    Attributes:
        STYLE_IN_MES: Стиль входящих сообщений
        STYLE_OUT_MES: Стиль исходящих сообщений

    """
    join = cfile.joinpath
    STYLE_IN_MES = join(Path('templates/style_in_message.html'))
    STYLE_OUT_MES = join(Path('templates/style_out_message.html'))
    states = {}

    def __init__(self, client):  # noqa
        super().__init__()
        self.client = client
        self.thread = QThread()
        self.client.moveToThread(self.thread)
        self.thread.started.connect(self.client.run)
        self.client.update.connect(self.update)
        self.thread.start()
        uic.loadUi(self.join(Path('templates/client.ui')), self)
        self.events = {
            f'new_{settings.MESSAGE}': self.incoming_message,
            f'done_{settings.USERS_REQUEST}': self.should_update_contact,
            f'done_{settings.PUBLIC_KEY_REQUEST}': self.make_encryptor,
            f'fail_{settings.AUTH}': self.exit_,
        }
        self.register_event()
        self.init_ui()

    def exit_(self, **kwargs):
        sys.exit(1)

    def register_event(self):
        """Регистрация событий."""
        for event in self.events.keys():
            self.client.attach(self, event)

    def init_ui(self):
        """Инициализация интерфейса."""
        super().init_ui()
        self.setWindowTitle(f'You are: {settings.USER_NAME}')
        self.MsgBox = QMessageBox()
        self.contacts_list_state = 'exists'
        self.current_chat = None
        self.lblAvatar.setVisible(False)
        self.update_contact()
        self.listContact.doubleClicked.connect(self.select_active_user)
        self.editMessages.clear()
        self.lblContact.setText('')
        self.btnSend.clicked.connect(self.send_message)
        self.btnBold.clicked.connect(self.set_bold)
        self.btnItalic.clicked.connect(self.set_italic)
        self.btnUnder.clicked.connect(self.set_underline)
        self.editFind.textChanged.connect(self.search_contact)
        self.states = {
            'exists': QIcon(QPixmap(str(self.join(Path('templates/img/list-contacts.png'))))),
            'new': QIcon(QPixmap(str(self.join(Path('templates/img/add-contacts.png'))))),
            'user': QIcon(QPixmap(str(self.join(Path('templates/img/user.png'))))),
            'default': self.menuBtn.icon(),
        }
        self.menuBtn.setMenu(self.make_menu())
        self.btnSmiles.setMenu(self.make_menu_smile())
        action = QAction('Удалить', self)
        action.triggered.connect(self.del_contact)
        self.listContact.addAction(action)
        self.encryptor = None
        self.show()

    def set_bold(self):
        f = self.editMessages.currentFont()
        f.setBold(not f.bold())
        self.editMessages.setFont(f)

    def set_italic(self):
        f = self.editMessages.currentFont()
        f.setItalic(not f.italic())
        self.editMessages.setFont(f)

    def set_underline(self):
        f = self.editMessages.currentFont()
        f.setUnderline(not f.underline())
        self.editMessages.setFont(f)

    def make_menu(self):
        """Формирует меню основной кнопки

        Returns:
            Возвращает подготовленное меню
            QMenu
        """
        menu = QMenu(self)
        action = menu.addAction('Контакы')
        action.setIcon(self.states['exists'])
        action.triggered.connect(lambda: self.switch_list_state('exists'))

        action = menu.addAction('Новый контакт')
        action.setIcon(self.states['new'])
        action.triggered.connect(lambda: self.switch_list_state('new'))

        action = menu.addAction('Профиль')
        action.setIcon(self.states['new'])
        action.triggered.connect(lambda: self.profile_open())

        return menu

    def make_menu_smile(self):
        """Формирует меню смайликов

        Returns:
            Возвращает подготовленное меню
            QMenu
        """
        menu = QMenu(self)
        pixmap = QPixmap(str(self.join(Path('templates/img/ab.gif'))))
        icon = QIcon(pixmap)
        action = menu.addAction(icon, '')
        action.triggered.connect(lambda: self.send_message(extra='<img src="%s" />' % ('talkative_client/templates/img/ab.gif')))

        pixmap = QPixmap(str(self.join(Path('templates/img/ac.gif'))))
        icon = QIcon(pixmap)
        action = menu.addAction(icon, '')
        action.triggered.connect(lambda: self.send_message(extra='<img src="%s" />' % ('talkative_client/templates/img/ac.gif')))

        pixmap = QPixmap(str(self.join(Path('templates/img/ai.gif'))))
        icon = QIcon(pixmap)
        action = menu.addAction(icon, '')
        action.triggered.connect(lambda: self.send_message(extra='<img src="%s" />' % ('talkative_client/templates/img/ai.gif')))

        return menu

    def profile_open(self):
        global profile_window
        profile_window = UserWindow(self)

    def restore_size_pos(self):
        """Восстановление состояния сплитера."""
        super().restore_size_pos()
        splitter_sizes = self.settings.value('splitter', None)
        if splitter_sizes is not None:
            self.splitter.restoreState(splitter_sizes)

    @pyqtSlot(dict)
    def update(self, kwargs):
        """Приемник событий.

        пробрасывает события интерфейсу

        Args:
            kwargs: Параметры

        """
        event = kwargs.get('event')
        method = self.events.get(event)
        if method:
            method(**kwargs)

    def save_size(self):
        """Сохранение состояния сплитера."""
        self.settings.setValue('splitter', self.splitter.saveState())

    def update_contact(self, text=''):
        """Обновление контактов."""
        user = User.by_name(settings.USER_NAME)
        if not user:
            return
        with db_lock:
            if self.contacts_list_state != 'new':
                contacts = user.get_contacts(text)
            else:
                contacts = user.not_contacts(text)
        contacts_list = [(i.username, i.avatar) for i in contacts]
        self.contacts_model = QStandardItemModel()
        index = None

        for i, ava in contacts_list:
            item = QStandardItem(i)
            item.setEditable(False)
            pava = QPixmap()
            pava.loadFromData(ava)
            item.setIcon(QIcon(pava))
            self.contacts_model.appendRow(item)
            if self.current_chat and self.current_chat == i:
                index = item.index()
        self.listContact.setModel(self.contacts_model)
        if index:
            self.listContact.setCurrentIndex(index)

    def select_active_user(self, index_model=None, current_chat=None):
        """Выбор активного пользователя."""
        self.current_chat = current_chat or self.listContact.currentIndex().data()
        if not self.current_chat:
            return
        if self.contacts_list_state == 'new':
            self.add_contact()

        self.client.notify(settings.PUBLIC_KEY_REQUEST, contact=self.current_chat)
        self.make_encryptor()

        self.lblContact.setText(f'{self.current_chat}')
        user = User.by_name(self.current_chat)
        if user:
            self.fill_chat()
            if user.avatar:
                ava = QPixmap()
                ava.loadFromData(user.avatar)
                self.lblAvatar.setPixmap(ava)
                self.lblAvatar.setVisible(True)

    def fill_chat(self):
        """Заполнение чата."""
        with db_lock:
            messages = UserMessages.chat_hiltory(self.current_chat, 20)
            stop = len(messages) + 1
        style_mes_out = self.STYLE_OUT_MES.read_text().format
        style_mes_in = self.STYLE_IN_MES.read_text().format
        self.editMessages.clear()
        mes_list = []
        with db_lock:
            for i in range(-1, -stop, -1):
                message = messages[i]
                if message.receiver.username == self.current_chat:
                    style_mes = style_mes_out
                    color = settings.COLOR_MESSAGE_OUT
                else:
                    style_mes = style_mes_in
                    color = settings.COLOR_MESSAGE_IN
                mes_list.append(style_mes(color=color, text=message.message, created=message.created))
        self.editMessages.setHtml(''.join(mes_list))

    def incoming_message(self, *args, **kwargs):
        print('incoming_message ' * 5)
        msg = kwargs.get('msg')
        if getattr(msg, settings.SENDER, None) == self.current_chat:
            self.fill_chat()

    def should_update_contact(self, **kwargs):
        self.update_contact()
        self.select_active_user(current_chat=self.current_chat)

    def make_encryptor(self, **kwargs):
        rest_user = User.by_name(self.current_chat)
        if rest_user.pub_key:
            self.encryptor = PKCS1_OAEP.new(RSA.import_key(rest_user.pub_key))

    def send_message(self, extra=None):
        """Отправка сообщения."""
        text = extra or self.editMessage.text()
        if not self.current_chat or not text:
            return
        if not self.encryptor:
            self.select_active_user()
            time.sleep(1)
            if not self.encryptor:
                logger.warn(f'Нет ключа для этого чата {self.current_chat}')
                self.MsgBox.critical(self, 'Ошибка', 'Нет ключа для этого чата')
                return
        mes_crypted = self.encryptor.encrypt(text.encode('utf8'))
        message = self.make_message(base64.b64encode(mes_crypted).decode('ascii'))

        self.client.notify(f'send_{settings.MESSAGE}', msg=message)
        with db_lock:
            UserHistory.proc_message(settings.USER_NAME, self.current_chat)
            UserMessages.create(sender=User.by_name(settings.USER_NAME), receiver=User.by_name(self.current_chat), message=text)

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

    def switch_list_state(self, state=None):
        """Переключатель окна с контактами в разные состояния."""
        self.editMessages.clear()
        self.lblContact.setText('')
        if self.contacts_list_state != state:
            self.contacts_list_state = state if state != 'default' else 'exists'
            self.update_contact()
            self.menuBtn.setIcon(self.states[state])

    def add_contact(self):
        """Добавление контакта."""
        user = User.by_name(settings.USER_NAME)
        try:
            with db_lock:
                user.add_contact(self.current_chat)
            self.client.notify(f'send_{settings.MESSAGE}', msg=Message(**{
                settings.ACTION: settings.ADD_CONTACT,
                settings.USER: settings.USER_NAME,
                settings.ACCOUNT_NAME: self.current_chat,
            }))
        except (ContactExists, NotFoundUser, ContactNotExists) as e:
            self.MsgBox.critical(self, 'Ошибка', str(e))
            logger.error(e)
        else:
            self.switch_list_state('default')

    def del_contact(self):
        """Удаление контакта."""
        user = User.by_name(settings.USER_NAME)
        name_contact = self.listContact.currentIndex().data()
        try:
            with db_lock:
                user.del_contact(name_contact)
            self.client.notify(f'send_{settings.MESSAGE}', msg=Message(**{
                settings.ACTION: settings.DEL_CONTACT,
                settings.USER: settings.USER_NAME,
                settings.ACCOUNT_NAME: name_contact,
            }))
        except (ContactExists, NotFoundUser, ContactNotExists) as e:
            self.MsgBox.critical(self, 'Ошибка', str(e))
            logger.error(e)
        else:
            self.update_contact()

    def search_contact(self, text):
        self.update_contact(text)
