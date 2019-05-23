# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-05-20 10:10:28
# @Last Modified by:   MaxST
# @Last Modified time: 2019-05-23 22:03:41
import argparse
import platform
from subprocess import Popen, PIPE

is_win = platform.system().lower() == 'windows'
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--count', nargs='?', default=1)
namespace = parser.parse_args()
clients = []

print(namespace.count)
if namespace.count:
    for _ in range(namespace.count):
        clients.append(Popen(
            ['python', 'client', '-r'],
            shell=True,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        ))
        clients.append(Popen(
            ['python', 'client'],
            shell=True,
        ))

print(clients)
