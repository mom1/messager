# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-06-02 17:42:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-31 11:32:29
import binascii
import hashlib
import sys
import time
from ipaddress import ip_address
from pathlib import Path

from dynaconf import settings
from dynaconf.loaders import yaml_loader as loader
from PyQt5 import uic
from PyQt5.QtCore import QSettings, Qt, pyqtSlot
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (QApplication, QDialog, QFileDialog, QMainWindow,
                             QMessageBox)

from .db import DBManager

if getattr(sys, 'frozen', False):
    # frozen
    cfile = Path(sys.executable).parent
else:
    cfile = Path(__file__).parent

db = DBManager()


class SaveGeometryMixin(object):
    """Миксин сохранения геометрии."""
    def init_ui(self):
        """Инициализация."""
        self.restore_size_pos()

    def restore_size_pos(self):
        """Востановление размера и позиции."""
        self.settings = QSettings('talkative_server', type(self).__name__)
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
        self.settings.setValue('size', self.size())
        self.settings.setValue('pos', self.pos())
        e.accept()


class ServerGUI(object):
    """Класс прослойка."""
    def __init__(self, server):
        """Инициализация.

        Args:
            server: транспортный сервер

        """
        super().__init__()
        global main_window
        main_window = ServerMainWindow(server)


class ServerMainWindow(SaveGeometryMixin, QMainWindow):
    """Основное окно программы."""
    def __init__(self, server):
        """Инициализация.

        Args:
            server: транспортный сервер

        """
        self.server = server
        super().__init__()
        self.server.update.connect(self.update)
        self.server.start()
        uic.loadUi(cfile.joinpath(Path('templates/server_settings.ui')), self)

        self.events = {
            'auth_new_user': self.update_active_users,
            settings.EXIT: self.update_active_users,
            'action_refresh': self.update_active_users,
            'action_history': self.history_open,
            'action_config': self.config_open,
            'action_add_user': self.add_user_open,
            'action_restart_server': self.action_restart_serv,
        }
        self.register_event()
        time.sleep(1)
        self.init_ui()

    def register_event(self):
        """Регистрация событий."""
        for event in self.events.keys():
            self.server.attach(self, event)

        for action in self.toolBar.actions():
            method = self.events.get(action.objectName())
            if method:
                action.triggered.connect(method)

    def init_ui(self):
        """Инициализация интерфейса."""
        super().init_ui()
        if self.server.started:
            self.statusBar().showMessage('Server Working')
        else:
            self.statusBar().showMessage('Server not Working')
        self.update_active_users()
        self.show()

    @pyqtSlot(dict)
    def update(self, kwargs):
        """Метод принимающий события.

        Args:
            kwargs: Параметры

        """
        event = kwargs.get('event')
        method = self.events.get(event)
        if method:
            method(**kwargs)

    def update_active_users(self, *args, **kwargs):
        """Обновление списка активных пользователей."""
        list_user = QStandardItemModel()
        list_user.setHorizontalHeaderLabels(['Пользователь', 'HOST:PORT', 'Последний вход'])
        for auser in db.ActiveUsers.objects.all():
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
        """Открытие окна истории."""
        global stat_window
        stat_window = HistoryWindow(main_window)

    def config_open(self):
        """Открытие окна настроек сервера."""
        global config_window
        config_window = ConfigWindow(main_window)

    def add_user_open(self):
        """Открытие окна добавления пользователя."""
        global add_user_window
        add_user_window = AddUserWindow(main_window, self.server)

    def action_restart_serv(self):
        """Перезапуск сервера"""
        server = type(self.server)
        self.server.stop()
        time.sleep(1)
        while self.server.is_alive():
            time.sleep(1)
        self.server = server()
        self.server.daemon = True
        self.server.start()


class HistoryWindow(SaveGeometryMixin, QDialog):
    """Класс окна с историей пользователей."""
    def __init__(self, parent):
        """Инициализация.

        Args:
            parent: родительское окно

        """
        self.parent_gui = parent
        super().__init__()
        uic.loadUi(cfile.joinpath(Path('templates/history_messages.ui')), self)
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса."""
        super().init_ui()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.update_messages()
        self.show()

    def update_messages(self):
        """Обновление списка пользователей."""
        list_ = QStandardItemModel()
        list_.setHorizontalHeaderLabels(['Пользователь', 'Последний вход', 'Сообщений отправлено', 'Сообщений получено'])
        for auser in db.User.objects.all():
            user = QStandardItem(auser.username)
            user.setEditable(False)
            last_login = QStandardItem(str(auser.last_login.replace(microsecond=0) if auser.last_login else 'Не входил'))
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
    """Класс окна настроек."""
    def __init__(self, parent):
        """Инициализация."""
        self.parent_gui = parent
        super().__init__()
        uic.loadUi(cfile.joinpath(Path('templates/config_server.ui')), self)
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса."""
        super().init_ui()
        self.setAttribute(Qt.WA_DeleteOnClose)
        db_def = Path(settings.get('DATABASES.SERVER.NAME'))

        def open_file_dialog():
            """Функция обработчик открытия окна выбора папки."""
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
        """Сохранение настроек сервера."""
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

        loader.write(Path('user_settings.yaml'), for_save)
        msg_box.information(config_window, 'OK', 'Настройки успешно сохранены!')


class AddUserWindow(SaveGeometryMixin, QDialog):
    """Класс окна добавления пользователя."""
    def __init__(self, parent, server):
        """Инициализация."""
        self.parent_gui = parent
        self.server = server
        super().__init__()
        uic.loadUi(cfile.joinpath(Path('templates/add_user.ui')), self)
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса."""
        super().init_ui()
        self.messages = QMessageBox()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.buttonBox.accepted.connect(self.save_data)
        self.show()

    def save_data(self):
        """Функция проверки правильности ввода и сохранения в базу нового пользователя."""
        if not self.editUser.text():
            self.messages.critical(self, 'Ошибка', 'Не указано имя пользователя.')
            return
        elif self.editPass2.text() != self.editPass1.text():
            self.messages.critical(self, 'Ошибка', 'Введённые пароли не совпадают.')
            return
        elif db.User.by_name(self.editUser.text()):
            self.messages.critical(self, 'Ошибка', 'Пользователь уже существует.')
            return
        else:
            hash_ = binascii.hexlify(hashlib.pbkdf2_hmac(
                'sha512',
                self.editPass1.text().encode('utf-8'),
                self.editUser.text().encode('utf-8'),
                10000,
            ))
            db.User.objects.create(username=self.editUser.text(), password=self.editPass1.text(), auth_key=hash_)
            self.messages.information(self, 'Успех', 'Пользователь успешно зарегистрирован.')
            # Рассылаем клиентам сообщение о необходимости обновить справочники
            self.server.service_update_lists()


if __name__ == '__main__':

    class FakeServer():
        """Фейк для тестов"""  # noqa

        def attach(self, *args, **kwargs):  # noqa
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
