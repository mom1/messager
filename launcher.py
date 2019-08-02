# -*- coding: utf-8 -*-
import platform
import subprocess
import time

params = {}
if platform.system().lower() == 'windows':
    params = {'creationflags': subprocess.CREATE_NEW_CONSOLE}
process = []


while True:
    action = input('Выберите действие: q - выход , s - запустить сервер и клиенты, x - закрыть все окна:')
    if action == 'q':
        break
    elif action == 's':
        clients_count = int(input('Введите количество тестовых клиентов для запуска: '))
        # Запускаем сервер!
        process.append(subprocess.Popen(['python', 'server'], **params))
        time.sleep(1)
        # Запускаем клиентов:
        for i in range(clients_count):
            process.append(subprocess.Popen(['python', 'client', '-n', f'test{i + 1}'], **params))
    elif action == 'x':
        while process:
            process.pop().kill()
