# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-23 10:34:37
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-28 20:03:49
import logging
from commands import AbstractCommand, main_commands

from dynaconf import settings

from db import UserHistory

logger = logging.getLogger('server__message')


class MessageCommand(AbstractCommand):
    """Отправить сообщение. Кому и текст будут запрошены отдельно."""
    name = 'message'

    def execute(self, serv, msg, *args, **kwargs):
        send_data = kwargs.get('send_data') or []
        if msg.is_valid():
            dest_user = getattr(msg, settings.DESTINATION, None)
            src_user = getattr(msg, settings.SENDER, None)
            dest = serv.names.get(dest_user)
            if not dest:
                logger.error(f'Пользователь {dest_user} не зарегистрирован на сервере, отправка сообщения невозможна.')
                return False
            elif dest not in send_data:
                logger.info(f'Связь с клиентом с именем {dest_user} была потеряна')
                serv.clients.remove(dest)
                del serv.names[dest_user]
                return False
            serv.write_client_data(dest, msg)
            logger.info(f'Отправлено сообщение пользователю {dest_user} от пользователя {src_user}.')
            with serv.db_lock:
                UserHistory.proc_message(src_user, dest_user)
            serv.notify(self.name)
        return True


main_commands.reg_cmd(MessageCommand)
