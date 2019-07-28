import platform
import subprocess

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
        process.append(subprocess.Popen(f'python server', **params))
        # Запускаем клиентов:
        for i in range(clients_count):
            process.append(subprocess.Popen(f'python client -n test{i + 1}', **params))
    elif action == 'x':
        while process:
            process.pop().kill()
