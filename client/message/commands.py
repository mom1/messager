# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-23 08:56:24
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-27 16:35:06
import logging
from commands import AbstractCommand, main_commands

from dynaconf import settings

from jim_mes import Message

logger = logging.getLogger('client__message')


class MessageCommand(AbstractCommand):
    """Отправить сообщение. Кому и текст будет запрошены отдельно."""
    name = 'message'

    def execute(self, client, *args, **kwargs):
        to = input('Введите получателя сообщения\n:')
        message_txt = input('Введите сообщение для отправки\n:')
        message = Message(**{
            settings.ACTION: settings.MESSAGE,
            settings.SENDER: settings.USER_NAME,
            settings.DESTINATION: to,
            settings.MESSAGE_TEXT: message_txt,
        })
        logger.debug(f'Сформировао сообщение: {message} для {to}')
        client.send_message(message)
        logger.info(f'Отправлено сообщение для пользователя {to}')
        return True


main_commands.reg_cmd(MessageCommand)
