# -*- coding: utf-8 -*-
"""Графический интерфейс взаимодействия с пользователем."""
# @Author: MaxST
# @Date:   2019-07-31 09:03:14
# @Last Modified by:   MaxST
# @Last Modified time: 2019-09-01 15:02:39

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
from PyQt5.QtCore import QSettings, QThread, pyqtSlot
from PyQt5.QtGui import QIcon, QPixmap, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (QDialog, QInputDialog, QMainWindow, QMenu,
                             QMessageBox)

from .db import Chat, User
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
        self.settings = QSettings('talkative_client', f'{settings.USER_NAME}__{type(self).__name__}')
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
        self.chat_members = []
        self.encryptors = None
        uic.loadUi(self.join(Path('templates/client.ui')), self)
        self.events = {
            f'new_{settings.MESSAGE}': self.incoming_message,
            f'done_{settings.USERS_REQUEST}': self.should_update_contact,
            f'done_{settings.GET_CHATS}': self.should_update_contact,
            f'done_{settings.PUBLIC_KEY_REQUEST}': self.make_encryptor,
            f'fail_{settings.AUTH}': self.exit_,
        }
        self.register_event()
        self.thread.start()
        time.sleep(1)
        self.current_user = User.by_name(settings.USER_NAME)
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
        self.btnAddUser.setVisible(False)
        self.update_contact()
        self.listContact.doubleClicked.connect(self.select_active_user)
        self.editMessages.clear()
        self.lblContact.setText('')
        self.btnSend.clicked.connect(self.send_message)
        self.btnBold.clicked.connect(self.set_bold)
        self.btnItalic.clicked.connect(self.set_italic)
        self.btnUnder.clicked.connect(self.set_underline)
        self.editFind.textChanged.connect(self.search_contact)
        self.btnAddUser.clicked.connect(self.add_user_to_current_group)

        self.states = {
            'exists': QIcon(QPixmap(str(self.join(Path('templates/img/list-contacts.png'))))),
            'new': QIcon(QPixmap(str(self.join(Path('templates/img/add-contacts.png'))))),
            'user': QIcon(QPixmap(str(self.join(Path('templates/img/user.png'))))),
            'group': QIcon(QPixmap(str(self.join(Path('templates/img/create-group.png'))))),
            'default': self.menuBtn.icon(),
        }
        self.menuBtn.setMenu(self.make_menu())
        self.btnSmiles.setMenu(self.make_menu_smile())
        action = QAction('Удалить', self)
        action.triggered.connect(self.del_contact)
        self.listContact.addAction(action)
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
        action.setIcon(self.states['default'])
        action.triggered.connect(lambda: self.switch_list_state('default'))

        action = menu.addAction('Создать группу')
        action.setIcon(self.states['group'])
        action.triggered.connect(self.create_group)

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

    def create_group(self):
        text, ok = QInputDialog.getText(self, 'Создание группы', 'Название группы:')
        if ok:
            text = str(text)
            chat = Chat.filter_by(name=text).first()
            if chat:
                self.MsgBox.information(self, 'Создание чата', 'Такая группа уже существует')
                return

            with db_lock:
                chat = Chat.create(name=text, owner=self.current_user, is_personal=False)
                chat.members.append(self.current_user)
                chat.save()
            self.add_user_to_group(chat)

    def add_user_to_group(self, chat):
        ok = True
        while ok:
            items = [u.username for u in User.query().filter(User.id.notin_([i.id for i in chat.members])).all()]
            if not items:
                break
            item, ok = QInputDialog.getItem(self, 'Выберите участников для перкращения нажмите отмену', 'Участник:', items)
            if ok and item:
                chat.members.append(User.by_name(item))
            chat.save()

        self.send_chat(chat)
        self.should_update_contact()

    def add_user_to_current_group(self):
        self.add_user_to_group(Chat.filter_by(name=self.current_chat).first())

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
        logger.info(f'gui catch {event}')
        method = self.events.get(event)
        if method:
            method(**kwargs)

    def save_size(self):
        """Сохранение состояния сплитера."""
        self.settings.setValue('splitter', self.splitter.saveState())

    def update_contact(self, text=''):
        """Обновление списка контактов."""
        user = self.current_user
        if not user:
            return
        with db_lock:
            if self.contacts_list_state != 'new':
                contacts = user.get_chats(text)
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
            if self.current_chat == i:
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

        user = User.by_name(self.current_chat)
        chat = Chat.filter_by(name=self.current_chat).first() or next((c for c in user.get_chats() if c.is_personal), None)
        obj = user or chat

        self.chat_members = chat.members
        self.current_chat = chat.name
        for cm in self.chat_members:
            if self.current_user == cm:
                continue
            self.client.notify(settings.PUBLIC_KEY_REQUEST, contact=cm.username)
        self.make_encryptor()

        self.lblContact.setText(f'{obj.username}')
        self.btnAddUser.setVisible(not chat.is_personal)

        if obj:
            self.fill_chat()
            if obj.avatar:
                ava = QPixmap()
                ava.loadFromData(obj.avatar)
                self.lblAvatar.setPixmap(ava)
                self.lblAvatar.setVisible(True)
            else:
                self.lblAvatar.clear()
                self.lblAvatar.setVisible(False)

    def fill_chat(self):
        """Заполнение чата."""
        with db_lock:
            messages = Chat.chat_hiltory(self.current_chat, 20)
        user = self.current_user
        style_mes_out = self.STYLE_OUT_MES.read_text().format
        style_mes_in = self.STYLE_IN_MES.read_text().format
        self.editMessages.clear()
        mes_list = []
        with db_lock:
            for message in messages:
                if message.sender.username == user.username:
                    style_mes = style_mes_out
                    color = settings.COLOR_MESSAGE_OUT
                else:
                    style_mes = style_mes_in
                    color = settings.COLOR_MESSAGE_IN
                mes_list.append(style_mes(color=color, text=message.text, created=message.created, user_name=message.sender.username))
        self.editMessages.setHtml(''.join(mes_list))

    def incoming_message(self, *args, **kwargs):
        msg = kwargs.get('msg')
        if self.current_chat in (getattr(msg, settings.SENDER, None), msg.chat):
            self.fill_chat()

    def should_update_contact(self, **kwargs):
        self.update_contact()
        self.select_active_user(current_chat=self.current_chat)

    def make_encryptor(self, **kwargs):
        with db_lock:
            self.encryptors = {u.username: PKCS1_OAEP.new(RSA.import_key(u.pub_key)) for u in self.chat_members if u.pub_key}

    def send_message(self, extra=None):
        """Отправка сообщения."""
        text = extra or self.editMessage.text()
        if not self.current_chat or not text:
            return
        if not self.encryptors:
            self.select_active_user()
            time.sleep(1)
            if not self.encryptors:
                logger.warn(f'Нет ключа для этого чата {self.current_chat}')
                self.MsgBox.critical(self, 'Ошибка', 'Нет ключа для этого чата')
                return

        for username, encryptor in self.encryptors.items():
            mes_crypted = encryptor.encrypt(text.encode('utf8'))
            message = self.make_message(username, base64.b64encode(mes_crypted).decode('ascii'))

            self.client.notify(f'send_{settings.MESSAGE}', msg=message)

        Chat.create_msg(message, text=text)

        self.editMessage.clear()
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
        user = self.current_user
        try:
            with db_lock:
                chat = user.add_contact(self.current_chat)
            self.client.notify(f'send_{settings.MESSAGE}',
                               msg=Message(**{
                                   settings.ACTION: settings.ADD_CONTACT,
                                   settings.USER: settings.USER_NAME,
                                   settings.ACCOUNT_NAME: self.current_chat,
                               }))
            self.send_chat(chat)
        except (ContactExists, NotFoundUser, ContactNotExists) as e:
            self.MsgBox.critical(self, 'Ошибка', str(e))
            logger.error(e)
        else:
            self.switch_list_state('default')

    def del_contact(self):
        """Удаление контакта."""
        user = self.current_user
        name_contact = self.listContact.currentIndex().data()
        try:
            with db_lock:
                chat = user.del_contact(name_contact)
            self.client.notify(f'send_{settings.MESSAGE}', msg=Message(**{
                settings.ACTION: settings.DEL_CONTACT,
                settings.USER: settings.USER_NAME,
                settings.ACCOUNT_NAME: name_contact,
            }))
            self.send_chat(chat)
        except (ContactExists, NotFoundUser, ContactNotExists) as e:
            self.MsgBox.critical(self, 'Ошибка', str(e))
            logger.error(e)
        else:
            self.editMessages.clear()
            self.lblContact.setText('')
            self.lblAvatar.clear()
            self.update_contact()

    def search_contact(self, text):
        self.update_contact(text)

    def send_chat(self, chat):
        self.client.notify(
            f'send_{settings.MESSAGE}',
            msg=Message(**{
                settings.ACTION: settings.EDIT_CHAT,
                settings.USER: settings.USER_NAME,
                settings.DATA: {
                    'name': chat.name,
                    'owner': chat.owner.username if chat.owner else None,
                    'is_personal': chat.is_personal,
                    'members': [i.username for i in chat.members],
                },
            }))
