# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-07-27 15:40:19
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-27 16:24:57
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
        if msg.is_valid():
            src_user = getattr(msg, settings.USER, None)
            contact = getattr(msg, settings.ACCOUNT_NAME, None)
            user = User.by_name(src_user)
            user.add_contact(contact)
            serv.write_client_data(serv.names.get(src_user), Msg.success())
            logger.info(f'User {src_user} add contact {contact}')
        return True


class DelContactCommand(AbstractCommand):
    """Обрабатывает запросы на удаление контакта"""
    name = settings.DEL_CONTACT

    def execute(self, serv, msg, *args, **kwargs):
        if msg.is_valid():
            src_user = getattr(msg, settings.USER, None)
            contact = getattr(msg, settings.ACCOUNT_NAME, None)
            user = User.by_name(src_user)
            user.del_contact(contact)
            serv.write_client_data(serv.names.get(src_user), Msg.success())
            logger.info(f'User {src_user} del contact {contact}')
        return True


class ListContactsCommand(AbstractCommand):
    """Обрабатывает запросы на получение списка контактов пользователя"""
    name = settings.GET_CONTACTS

    def execute(self, serv, msg, *args, **kwargs):
        if msg.is_valid():
            src_user = getattr(msg, settings.USER, None)
            user = User.by_name(src_user)
            serv.write_client_data(serv.names.get(src_user), Msg.success(202, **{settings.LIST_INFO: [c.username for c in user.contact]}))
            logger.info(f'User {src_user} get list contacts')
        return True


main_commands.reg_cmd(AddContactCommand)
main_commands.reg_cmd(DelContactCommand)
main_commands.reg_cmd(ListContactsCommand)
