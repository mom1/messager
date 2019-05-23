# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-05-20 18:10:48
# @Last Modified by:   MaxST
# @Last Modified time: 2019-05-23 22:57:12

import ipaddress
import platform
import subprocess
from tabulate import tabulate

is_win = platform.system().lower() == 'windows'
param = '-n' if is_win else '-c'


def host_ping(hosts, is_print=True):
    for host in hosts:
        try:
            ip = ipaddress.ip_address(host)
        except Exception:
            ip = host
        command = ['ping', param, '1', str(ip)]
        response = subprocess.run(command,
                                  shell=is_win,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        mes = 'Узел доступен' if response.returncode == 0 else 'Узел не доступен'
        if is_print:
            yield print(f'{ip}: {mes}')
        else:
            key = 'Reachable' if response.returncode == 0 else 'Unreachable'
            yield {key: ip}


# list(host_ping(('192.168.0.1', 'ya.ru', 'babayaga')))


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


# host_range_ping('192.168.0.1', '192.168.0.20')


def host_range_ping_tab(start, end):
    print(tabulate(host_range_ping(start, end, is_print=False), headers='keys'))


# host_range_ping_tab('192.168.0.1', '192.168.0.20')
