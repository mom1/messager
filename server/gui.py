# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-06-02 17:42:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-28 19:24:55
import sys

from dynaconf import settings
from PyQt5 import uic
from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow

from db import ActiveUsers, DBManager, User


class ServerGUI(QMainWindow):
    def __init__(self, server):
        self.server = server
        super().__init__()
        uic.loadUi('server/templates/server_settings.ui', self)

        self.restore_size_pos()

        self.events = {
            settings.PRESENCE: self.update_active_users,
            settings.EXIT: self.update_active_users,
            'action_refresh': self.update_active_users,
            'action_history': self.history_open,
        }
        self.register_event()
        self.init_ui()

    def register_event(self):
        for event, _ in self.events.items():
            self.server.attach(self, event)

        for action in self.toolBar.actions():
            method = self.events.get(action.objectName())
            if method:
                action.triggered.connect(method)

    def restore_size_pos(self):
        self.settings = QSettings('ServerGUI', 'server')
        size = self.settings.value('size', None)
        pos = self.settings.value('pos', None)
        if size:
            self.resize(size)
        if pos:
            self.move(pos)

    def init_ui(self):
        self.statusBar().showMessage('Server Working')
        self.update_active_users()
        self.show()

    def update(self, serv, event):
        method = self.events.get(event)
        if method:
            method(serv)

    def update_active_users(self, serv=None):
        list_user = QStandardItemModel()
        list_user.setHorizontalHeaderLabels(['Пользователь', 'HOST:PORT', 'Последний вход'])
        for auser in ActiveUsers.all():
            user = QStandardItem(auser.oper.username)
            user.setEditable(False)
            ip_port = QStandardItem(f'{auser.ip_addr}:{auser.port}')
            ip_port.setEditable(False)
            time_in = QStandardItem(str(auser.oper.last_login.replace(microsecond=0)))
            time_in.setEditable(False)
            list_user.appendRow([user, ip_port, time_in])

        self.active_users.setModel(list_user)
        self.active_users.resizeColumnsToContents()
        self.active_users.resizeRowsToContents()

    def history_open(self):
        global stat_window
        stat_window = HistoryWindow()

    def closeEvent(self, e):  # noqa
        # Write window size and position to config file
        self.settings.setValue('size', self.size())
        self.settings.setValue('pos', self.pos())
        e.accept()


class HistoryWindow(QDialog):
    """Класс окна с историей пользователей"""
    def __init__(self):
        super().__init__()
        uic.loadUi('server/templates/history_messages.ui', self)
        self.restore_size_pos()
        self.init_ui()

    def init_ui(self):
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.update_messages()
        self.show()

    def update_messages(self):
        list_ = QStandardItemModel()
        list_.setHorizontalHeaderLabels(['Пользователь', 'Последний вход', 'Сообщений отправлено', 'Сообщений получено'])
        for auser in User.all():
            user = QStandardItem(auser.username)
            user.setEditable(False)
            last_login = QStandardItem(str(auser.last_login.replace(microsecond=0)))
            last_login.setEditable(False)
            sent = QStandardItem(str(auser.sent))
            sent.setEditable(False)
            accepted = QStandardItem(str(auser.accepted))
            accepted.setEditable(False)
            list_.appendRow([user, last_login, sent, accepted])

        self.tbMessages.setModel(list_)
        self.tbMessages.resizeColumnsToContents()
        self.tbMessages.resizeRowsToContents()

    def restore_size_pos(self):
        self.settings = QSettings('HistoryWindow', 'server')
        size = self.settings.value('size', None)
        pos = self.settings.value('pos', None)
        if size:
            self.resize(size)
        if pos:
            self.move(pos)

    def closeEvent(self, e):  # noqa
        # Write window size and position to config file
        self.settings.setValue('size', self.size())
        self.settings.setValue('pos', self.pos())
        e.accept()


if __name__ == '__main__':

    class FakeServer():
        def attach(self, *args, **kwargs):
            pass

    app = QApplication(sys.argv)
    DBManager('server')
    mw = ServerGUI(FakeServer())
    # mw.statusBar().showMessage('Test Statusbar Message')
    # test_list = QStandardItemModel(mw)
    # test_list.setHorizontalHeaderLabels(['Имя Клиента', 'IP Адрес', 'Порт', 'Время подключения'])
    # test_list.appendRow([QStandardItem('1'), QStandardItem('2'), QStandardItem('3')])
    # test_list.appendRow([QStandardItem('4'), QStandardItem('5'), QStandardItem('6')])
    # mw.active_users.setModel(test_list)
    # mw.active_users.resizeColumnsToContents()
    sys.exit(app.exec_())
