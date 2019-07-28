# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-07-27 15:40:19
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-28 20:06:46
import logging
from commands import AbstractCommand, main_commands

from dynaconf import settings
from db import User
from jim_mes import Message as Msg

logger = logging.getLogger('server__contacts')


class AddContactCommand(AbstractCommand):
    """Обрабатывает запросы на добавление контакта"""
    name = settings.ADD_CONTACT

    def execute(self, serv, msg, *args, **kwargs):
        src_user = getattr(msg, settings.USER, None)
        contact = getattr(msg, settings.ACCOUNT_NAME, None)
        user = User.by_name(src_user)
        if contact:
            with serv.db_lock:
                user.add_contact(contact)
            serv.write_client_data(serv.names.get(src_user), Msg.success())
            serv.notify(self.name)
        else:
            serv.write_client_data(serv.names.get(src_user), Msg.error_resp('Не найден контакт'))
        logger.info(f'User {src_user} add contact {contact}')
        return True


class DelContactCommand(AbstractCommand):
    """Обрабатывает запросы на удаление контакта"""
    name = settings.DEL_CONTACT

    def execute(self, serv, msg, *args, **kwargs):
        src_user = getattr(msg, settings.USER, None)
        contact = getattr(msg, settings.ACCOUNT_NAME, None)
        user = User.by_name(src_user)
        if contact:
            with serv.db_lock:
                user.del_contact(contact)
            serv.write_client_data(serv.names.get(src_user), Msg.success())
            serv.notify(self.name)
        logger.info(f'User {src_user} del contact {contact}')
        return True


class ListContactsCommand(AbstractCommand):
    """Обрабатывает запросы на получение списка контактов пользователя"""
    name = settings.GET_CONTACTS

    def execute(self, serv, msg, *args, **kwargs):
        src_user = getattr(msg, settings.USER, None)
        user = User.by_name(src_user)
        serv.write_client_data(serv.names.get(src_user), Msg.success(202, **{settings.LIST_INFO: [c.contact.username for c in user.contacts]}))
        logger.info(f'User {src_user} get list contacts')
        return True


main_commands.reg_cmd(AddContactCommand)
main_commands.reg_cmd(DelContactCommand)
main_commands.reg_cmd(ListContactsCommand)
