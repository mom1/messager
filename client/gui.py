# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-07-31 09:03:14
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-02 04:02:23
# from dynaconf.loaders import yaml_loader as loader
import logging
from pathlib import Path

from dynaconf import settings
from PyQt5 import uic
from PyQt5.Qt import QAction
from PyQt5.QtCore import QObject, QSettings, pyqtSlot
from PyQt5.QtGui import QIcon, QPixmap, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from db import User, UserHistory, UserMessages
from errors import ContactExists, NotFoundUser, ContactNotExists
from jim_mes import Message

logger = logging.getLogger('gui')


class SaveGeometryMixin(object):
    def init_ui(self):
        self.restore_size_pos()

    def restore_size_pos(self):
        self.settings = QSettings(type(self).__name__, settings.USER_NAME)
        size = self.settings.value('size', None)
        pos = self.settings.value('pos', None)
        if size:
            self.resize(size)
        if pos:
            self.move(pos)

    def closeEvent(self, e):  # noqa
        # Write window size and position to config file
        if hasattr(self, 'save_size'):
            self.save_size()
        self.settings.setValue('size', self.size())
        self.settings.setValue('pos', self.pos())
        e.accept()


class ClientGui(QObject):
    def __init__(self, client):
        super().__init__()
        global main_window
        main_window = ClientMainWindow(client)

    def is_alive(self):
        return False

    @pyqtSlot(Message)
    def update(self, *args, **kwargs):
        main_window.update(*args, **kwargs)


class ClientMainWindow(SaveGeometryMixin, QMainWindow):
    STYLE_IN_MES = '''
                    <p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">
                    <span style=" vertical-align:super;">
                        {created}
                    </span>
                    </p>
                    <p style="margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">
                        <span style=" color:{color};">
                            {text}
                        </span>
                    </p>'''.format
    STYLE_OUT_MES = '''
                    <p align="right" style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">
                        <span style=" vertical-align:super;">
                            {created}
                        </span>
                    </p>
                    <p align="right" style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">
                        <span style=" color:{color};">
                            {text}
                        </span>
                    </p>'''.format

    def __init__(self, client):
        self.client = client
        super().__init__()
        uic.loadUi(Path('client/templates/client.ui'), self)
        self.init_ui()

    def init_ui(self):
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

        self.show()

    def restore_size_pos(self):
        super().restore_size_pos()
        splitter_sizes = self.settings.value('splitter', None)
        if splitter_sizes is not None:
            self.splitter.restoreState(splitter_sizes)

    def save_size(self):
        self.settings.setValue('splitter', self.splitter.saveState())

    def update_contact(self):
        user = User.by_name(settings.USER_NAME)
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
        self.current_chat = self.listContact.currentIndex().data()
        if self.contacts_list_state == 'new':
            self.add_contact()
        self.lblContact.setText(f'{self.current_chat}:')
        self.fill_chat()

    def fill_chat(self):
        messages = UserMessages.chat_hiltory(self.current_chat, 20)

        self.editMessages.clear()
        mes_list = []
        stop = len(messages) + 1
        for i in range(-1, -stop, -1):
            message = messages[i]
            if message.receiver.username == self.current_chat:
                style_mes = self.STYLE_OUT_MES
                color = settings.COLOR_MESSAGE_OUT
            else:
                style_mes = self.STYLE_IN_MES
                color = settings.COLOR_MESSAGE_IN
            mes_list.append(style_mes(color=color, text=message.message, created=message.created))
        self.editMessages.setHtml(''.join(mes_list))

    def update(self, message):
        if getattr(message, settings.SENDER, None) == self.current_chat:
            self.fill_chat()

    def send_message(self):
        if not self.current_chat or not self.editMessage.text():
            return
        message = self.make_message(self.editMessage.text())
        self.client.send_message(message)
        with self.client.db_lock:
            UserHistory.proc_message(settings.USER_NAME, self.current_chat)
            UserMessages.create(sender=User.by_name(settings.USER_NAME), receiver=User.by_name(self.current_chat), message=str(message))
        self.editMessage.clear()
        self.fill_chat()

    def make_message(self, text=''):
        return Message(**{
            settings.ACTION: settings.MESSAGE,
            settings.SENDER: settings.USER_NAME,
            settings.DESTINATION: self.current_chat,
            settings.MESSAGE_TEXT: text,
        })

    def switch_list_state(self):
        self.editMessages.clear()
        self.lblContact.setText('')
        if self.contacts_list_state != 'new':
            self.contacts_list_state = 'new'
            icon = QIcon(QPixmap('client/templates/img/list-contacts.png'))
        else:
            self.contacts_list_state = 'exists'
            icon = QIcon(QPixmap('client/templates/img/add-contacts.png'))
        self.addContact.setIcon(icon)
        self.update_contact()

    def add_contact(self):
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
