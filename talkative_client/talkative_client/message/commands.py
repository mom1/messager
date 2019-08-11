# -*- coding: utf-8 -*-
# @Author: maxst
# @Date:   2019-07-23 08:56:24
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-11 12:16:05
import logging

from dynaconf import settings
from tabulate import tabulate

from talkative_client.commands import AbstractCommand, main_commands
from talkative_client.db import User, UserHistory, UserMessages
from talkative_client.jim_mes import Message

logger = logging.getLogger('client__message')


class MessageCommand(AbstractCommand):
    """Отправить сообщение. Кому и текст будет запрошены отдельно."""

    name = 'message'

    def execute(self, client, *args, **kwargs):  # noqa
        to = input('Введите получателя сообщения\n:').strip()
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
        with client.db_lock:
            UserHistory.proc_message(settings.USER_NAME, to)
            UserMessages.create(sender=User.by_name(settings.USER_NAME), receiver=User.by_name(to), message=str(message))
        return True


class HistoryCommand(AbstractCommand):
    """История сообщений."""

    name = 'hist'

    def execute(self, client, *args, **kwargs):  # noqa
        command = input('in - показать входящие\nout - показать исходящие\nпросто Enter - показать все\n:').strip()
        tab = []
        with client.db_lock:
            user = User.by_name(settings.USER_NAME)
            if command == 'in':
                for r in user.received_messages:
                    tab.append({'Сообщение от': r.sender.username, 'Дата': r.created, 'Текст': r.message})
            elif command == 'out':
                for r in user.sents_messages:
                    tab.append({'Сообщение пользователю': r.receiver.username, 'Дата': r.created, 'Текст': r.message})
            else:
                for r in UserMessages.all():
                    tab.append({'Сообщение от': r.sender.username, 'Сообщение пользователю': r.receiver.username, 'Дата': r.created, 'Текст': r.message})
        print()
        print(tabulate(
            tab,
            headers='keys',
            tablefmt='rst',
        ))
        print()
        return True


main_commands.reg_cmd(MessageCommand)
main_commands.reg_cmd(HistoryCommand)
