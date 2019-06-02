# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-06-02 17:42:30
# @Last Modified by:   MaxST
# @Last Modified time: 2019-06-02 23:12:02
import sys
import time
from PyQt5 import uic
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem

app = QApplication(sys.argv)


class ServerThread(QThread):
    def __init__(self, server):
        self.server = server
        super().__init__()

    def run(self):
        self.server.run()


class ServerGUI(QMainWindow):
    def __init__(self, server=None):
        super().__init__()
        uic.loadUi('server/templates/main_server.ui', self)
        self.server = server
        self.th_server = ServerThread(server)

    def run(self):
        self.th_server.start()
        sett = self.server.settings()
        self.editHost.setText(sett.get('host'))
        self.editPort.setText(str(sett.get('port')))
        self.editEncoding.setText(sett.get('encoding'))
        self.editDbname.setText(sett.get('db_name'))
        self.set_clients()
        self.show()
        sys.exit(app.exec_())

    def set_clients(self):
        from db import DBManager, User
        while not self.server.start:
            time.sleep(2)
        DBManager.get_instance()._setup()
        self.tableClients.setRowCount(0)
        for i, user in enumerate(User.all()):
            self.tableClients.insertRow(i)
            self.tableClients.setItem(i, 0, QTableWidgetItem(str(user.username)))
            self.tableClients.setItem(i, 1, QTableWidgetItem(str(user.descr)))
            self.tableClients.setItem(i, 2, QTableWidgetItem(str(user.last_login())))
            self.tableClients.setItem(i, 3, QTableWidgetItem(str(len(user.contacts))))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ServerGUI()
    window.show()
    sys.exit(app.exec_())
