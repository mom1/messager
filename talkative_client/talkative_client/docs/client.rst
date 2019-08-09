Client
======

Клиентское приложение для обмена сообщениями. Поддерживает
отправку сообщений пользователям которые находятся в сети, сообщения шифруются
с помощью алгоритма RSA с длинной ключа 2048 bit.

Использование:

``client [-h] [--config [CONFIG]] [-e [ENCODING]] [-a [HOST]] [-p [PORT]] [-v] [-g | -c] [-n [NAME]] [--password [PASSWORD]]``

Опциональные аргументы:

-h, --help                           show this help message and exit

--config CONFIG                      File config

-e ENCODING, --encoding ENCODING     Encoding (default "utf-8")

-a HOST, --host HOST                 IP (default "127.0.0.1")

-p PORT, --port PORT                 Port (default "7777")

-v, --verbose                        Increase verbosity of log output (default "10")

-g, --gui                            Start GUI Configuration

-c, --console                        Start cli

-n NAME, --name NAME                 Name user for connect

--password PASSWORD                  User password

Subpackages
-----------

.. toctree::

   client.jim_mes

client.commands module
----------------------

.. automodule:: commands
   :members:
   :undoc-members:
   :show-inheritance:

client.core module
------------------

.. automodule:: core
   :members:
   :undoc-members:
   :show-inheritance:

client.db module
----------------

.. automodule:: db
   :members:
   :undoc-members:
   :show-inheritance:

client.errors module
--------------------

.. automodule:: errors
   :members:
   :undoc-members:
   :show-inheritance:

client.gui module
-----------------

.. automodule:: gui
   :members:
   :undoc-members:
   :show-inheritance:

client.metaclasses module
-------------------------

.. automodule:: metaclasses
   :members:
   :undoc-members:
   :show-inheritance:
