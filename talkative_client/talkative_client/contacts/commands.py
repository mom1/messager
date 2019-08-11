# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-07-27 16:26:55
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-11 12:16:07
import logging

from dynaconf import settings
from tabulate import tabulate

from talkative_client.commands import AbstractCommand, main_commands
from talkative_client.db import User
from talkative_client.errors import ContactExists, ContactNotExists, NotFoundUser
from talkative_client.jim_mes import Message as Msg

logger = logging.getLogger('client__contacts')


class GetContactsCommand(AbstractCommand):
    """Получить список контактов."""

    name = 'contacts'

    def execute(self, client, *args, **kwargs):
        user = User.by_name(settings.USER_NAME)
        tab = []
        for contact in user.contacts:
            tab.append({'Контакты': contact.contact.username})
        print()
        print(tabulate(
            tab,
            headers='keys',
            tablefmt='rst',
        ))
        print()
        return True


class EditContactsCommand(AbstractCommand):
    """Редактирование контактов."""

    name = 'edit'

    def execute(self, client, *args, **kwargs):
        """Выполнение изменение контактов.

        #. add - добавляет контакт
        #. del - удаляет контакт

        Args:
            client: [description]
            *args: [description]
            **kwargs: [description]

        Returns:
            [description]
            bool

        """
        command = input('add - добавить контакт\ndel - удалить контакт\n:').strip()
        name_contact = input('Введите имя\n:').strip()
        with client.db_lock:
            user = User.by_name(settings.USER_NAME)
            try:
                if command == 'add':
                    user.add_contact(name_contact)
                    client.send_message(Msg(**{
                        settings.ACTION: settings.ADD_CONTACT,
                        settings.USER: settings.USER_NAME,
                        settings.ACCOUNT_NAME: name_contact,
                    }))
                elif command == 'del':
                    user.del_contact(name_contact)
                    client.send_message(Msg(**{
                        settings.ACTION: settings.DEL_CONTACT,
                        settings.USER: settings.USER_NAME,
                        settings.ACCOUNT_NAME: name_contact,
                    }))
            except NotFoundUser as e:
                print(e)
                logger.error(e)
            except (ContactExists, NotFoundUser, ContactExists, ContactNotExists) as e:
                print(e)
                logger.error(e)
            GetContactsCommand().execute(client, *args, **kwargs)
        return True


main_commands.reg_cmd(GetContactsCommand)
main_commands.reg_cmd(EditContactsCommand)
