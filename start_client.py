# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-05-20 10:10:28
# @Last Modified by:   MaxST
# @Last Modified time: 2019-05-24 22:23:21
import argparse
from pathlib import PurePath, Path
import os

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--count', nargs='?', default=1)
namespace = parser.parse_args()

client_path = Path.cwd().joinpath(PurePath('client/'))

for _ in range(namespace.count):
    os.system(f'python {client_path} -r &')
    os.system(f'python {client_path}')
