# -*- coding: utf-8 -*-
from cx_Freeze import Executable, setup

build_exe_options = {
    'packages': ['talkative_server', 'dynaconf'],
}
setup(name='talkative_server',
      version='0.1.2',
      description='talkative_server',
      options={'build_exe': build_exe_options},
      executables=[Executable(
          'talkative_server/__main__.py',
          # base='Win32GUI',
          targetName='server.exe',
      )])
