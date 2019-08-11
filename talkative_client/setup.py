# -*- coding: utf-8 -*-
from cx_Freeze import Executable, setup

build_exe_options = {
    'packages': ['talkative_client', 'dynaconf'],
}
setup(name='talkative_client',
      version='0.1.2',
      description='talkative_client',
      options={'build_exe': build_exe_options},
      executables=[Executable(
          'talkative_client/__main__.py',
          # base='Win32GUI',
          targetName='client.exe',
      )])
