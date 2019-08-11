# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-05-20 18:10:48
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-07 11:51:41

import ipaddress
import platform
import subprocess

from tabulate import tabulate

is_win = platform.system().lower() == 'windows'
param = '-n' if is_win else '-c'

# 1. Написать функцию host_ping(), в которой с помощью утилиты ping будет проверяться доступность сетевых узлов. Аргументом функции является список,
# в котором каждый сетевой узел должен быть представлен именем хоста или ip-адресом. В функции необходимо перебирать ip-адреса и проверять
# их доступность с выводом соответствующего сообщения («Узел доступен», «Узел недоступен»). При этом ip-адрес сетевого узла должен
# создаваться с помощью функции ip_address().


def host_ping(hosts, is_print=True):
    for host in hosts:
        try:
            ip = ipaddress.ip_address(host)
        except Exception:
            ip = host
        command = ['ping', param, '1', str(ip)]
        response = subprocess.run(command, shell=is_win, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        mes = 'Узел доступен' if response.returncode == 0 else 'Узел не доступен'
        if is_print:
            yield print(f'{ip}: {mes}')
        else:
            key = 'Reachable' if response.returncode == 0 else 'Unreachable'
            yield {key: ip}


# 2. Написать функцию host_range_ping() для перебора ip-адресов из заданного диапазона.
# Меняться должен только последний октет каждого адреса.
# По результатам проверки должно выводиться соответствующее сообщение.


def host_range_ping(start, end, is_print=True):
    try:
        start_ip = ipaddress.ip_address(start)
        end_ip = ipaddress.ip_address(end)
        start_ip, end_ip = sorted((start_ip, end_ip))
    except Exception:
        print('Не верные параметры')
        return
    ips = []

    while start_ip <= end_ip:
        ips.append(start_ip)
        start_ip += 1

    return [i for i in host_ping(ips, is_print)]


# 3. Написать функцию host_range_ping_tab(), возможности которой основаны на функции из примера 2.
# Но в данном случае результат должен быть итоговым по всем ip-адресам, представленным в табличном формате (использовать модуль tabulate).
# Таблица должна состоять из двух колонок и выглядеть примерно так:
# Reachable
# 10.0.0.1
# 10.0.0.2
# Unreachable
# 10.0.0.3
# 10.0.0.4


def host_range_ping_tab(start, end):
    print(tabulate(host_range_ping(start, end, is_print=False), headers='keys'))


if __name__ == '__main__':
    list(host_ping(('192.168.0.1', 'ya.ru', 'babayaga')))
    host_range_ping('192.168.0.1', '192.168.0.3')
    host_range_ping_tab('192.168.0.1', '192.168.0.3')
