Server
======

Серверный модуль мессенджера. Обрабатывает сообщения, хранит публичные ключи клиентов.

Использование:

``python server [-h] [--config [CONFIG]] [-e [ENCODING]] [-a [HOST]] [-p [PORT]] [-v] [-g | -c]``

Опциональные аргументы:

-h, --help                           show this help message and exit

--config CONFIG                      File config

-e ENCODING, --encoding ENCODING     Encoding (default "utf-8")

-a HOST, --host HOST                 IP (default "127.0.0.1")

-p PORT, --port PORT                 Port (default "7777")

-v, --verbose                        Increase verbosity of log output (default "10")

-g, --gui                            Start GUI Configuration

-c, --console                        Start cli



server.cli module
-----------------

.. automodule:: cli
   :members:
   :undoc-members:
   :show-inheritance:

server.commands module
----------------------

.. automodule:: commands
   :members:
   :undoc-members:
   :show-inheritance:

server.core module
------------------

.. automodule:: core
   :members:
   :undoc-members:
   :show-inheritance:

server.db module
----------------

.. automodule:: db
   :members:
   :undoc-members:
   :show-inheritance:

server.decorators module
------------------------

.. automodule:: decorators
   :members:
   :undoc-members:
   :show-inheritance:

server.descriptors module
-------------------------

.. automodule:: descriptors
   :members:
   :undoc-members:
   :show-inheritance:

server.errors module
--------------------

.. automodule:: errors
   :members:
   :undoc-members:
   :show-inheritance:

server.gui module
-----------------

.. automodule:: gui
   :members:
   :undoc-members:
   :show-inheritance:

server.metaclasses module
-------------------------

.. automodule:: metaclasses
   :members:
   :undoc-members:
   :show-inheritance:

Subpackages
-----------

.. toctree::

   server.jim_mes
