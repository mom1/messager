# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-06-02 17:42:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-29 01:27:35
import sys
from ipaddress import ip_address
from pathlib import Path

from dynaconf import settings
from dynaconf.loaders import yaml_loader as loader
from PyQt5 import uic
from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (QApplication, QDialog, QFileDialog, QMainWindow,
                             QMessageBox)

from db import ActiveUsers, DBManager, User


class SaveGeometryMixin(object):
    def init_ui(self):
        self.restore_size_pos()

    def restore_size_pos(self):
        self.settings = QSettings(type(self).__name__, 'server')
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


class ServerGUI(SaveGeometryMixin, QMainWindow):
    def __init__(self, server):
        self.server = server
        super().__init__()
        uic.loadUi(Path('server/templates/server_settings.ui'), self)

        self.events = {
            settings.PRESENCE: self.update_active_users,
            settings.EXIT: self.update_active_users,
            'action_refresh': self.update_active_users,
            'action_history': self.history_open,
            'action_config': self.config_open,
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

    def init_ui(self):
        super().init_ui()
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
        stat_window = HistoryWindow(self)

    def config_open(self):
        global config_window
        config_window = ConfigWindow(self)


class HistoryWindow(SaveGeometryMixin, QDialog):
    """Класс окна с историей пользователей"""
    def __init__(self, parent):
        self.parent_gui = parent
        super().__init__()
        uic.loadUi(Path('server/templates/history_messages.ui'), self)
        self.init_ui()

    def init_ui(self):
        super().init_ui()
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


class ConfigWindow(SaveGeometryMixin, QDialog):
    """Класс окна настроек """
    def __init__(self, parent):
        self.parent_gui = parent
        super().__init__()
        uic.loadUi(Path('server/templates/config_server.ui'), self)
        self.init_ui()

    def init_ui(self):
        super().init_ui()
        db_def = Path(settings.get('DATABASES.SERVER.NAME'))

        def open_file_dialog():
            """Функция обработчик открытия окна выбора папки"""
            global dialog
            dialog = QFileDialog(config_window, 'Путь до папки с БД', str(db_def.parent.absolute()))
            path_d = dialog.getExistingDirectory()
            if path_d:
                path_d = str(Path(path_d))
                self.ledPath.clear()
                self.ledPath.insert(path_d)

        self.btnPath.clicked.connect(open_file_dialog)
        self.ledPath.insert(str(db_def.parent.absolute()))
        self.ledNameDB.insert(str(db_def.name))
        self.ledIp.insert(str(ip_address(settings.get('HOST'))))
        self.ledPort.insert(str(settings.get('PORT')))
        self.btnBox.accepted.connect(self.save_server_config)
        self.show()

    def save_server_config(self):
        for_save = {}
        msg_box = QMessageBox()
        db_path = Path(self.ledPath.text())
        db_name = Path(self.ledNameDB.text())
        db_name = db_name if db_name.suffix else db_name.with_suffix('db')
        db = db_path.joinpath(db_name)
        try:
            db = db.relative_to(Path.cwd())
        except Exception:
            pass
        try:
            port = self.parent_gui.server.port = int(self.ledPort.text())
        except Exception as e:
            return msg_box.warning(config_window, 'Ошибка', str(e))
        # set settings
        settings.set('HOST', self.ledIp.text())
        settings.set('PORT', port)
        settings.DATABASES.SERVER.NAME = str(db)
        for_save['DEFAULT'] = set_dict = settings.as_dict()
        for_save['DEFAULT']['DATABASES'] = set_dict['DATABASES'].to_dict()

        loader.write(Path('config/user_settings.yaml'), for_save, merge=True)
        msg_box.information(config_window, 'OK', 'Настройки успешно сохранены!')


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