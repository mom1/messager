# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-07-27 15:40:19
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-11 13:41:03
import logging

from dynaconf import settings

from talkative_server.commands import AbstractCommand, main_commands
from talkative_server.db import User
from talkative_server.decorators import login_required
from talkative_server.jim_mes import Message as Msg

logger = logging.getLogger('server__contacts')


class AddContactCommand(AbstractCommand):
    """Обрабатывает запросы на добавление контакта."""

    name = settings.ADD_CONTACT

    @login_required
    def execute(self, serv, msg, *args, **kwargs):
        """Выполнение."""
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
    """Обрабатывает запросы на удаление контакта."""

    name = settings.DEL_CONTACT

    @login_required
    def execute(self, serv, msg, *args, **kwargs):
        """Выполнение."""
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
    """Обрабатывает запросы на получение списка контактов пользователя."""

    name = settings.GET_CONTACTS

    @login_required
    def execute(self, serv, msg, *args, **kwargs):
        """Выполнение."""
        src_user = getattr(msg, settings.USER, None)
        user = User.by_name(src_user)
        serv.write_client_data(serv.names.get(src_user), Msg.success(202, **{settings.LIST_INFO: [c.contact.username for c in user.contacts]}))
        logger.info(f'User {src_user} get list contacts')
        return True


class RequestKeyCommand(AbstractCommand):
    """Обрабатывает запросы на получение списка контактов пользователя."""

    name = settings.PUBLIC_KEY_REQUEST

    @login_required
    def execute(self, serv, msg, *args, **kwargs):
        """Выполнение."""
        dest_user = getattr(msg, settings.DESTINATION, None)
        src_user = getattr(msg, settings.SENDER, None)
        user = User.by_name(dest_user)
        conn = serv.names.get(src_user)
        if user and user.pub_key:
            mes = Msg(response=511, **{settings.DATA: user.pub_key, settings.ACCOUNT_NAME: dest_user})
        else:
            mes = Msg.error_resp('Ошибка определения ключа')
        serv.write_client_data(conn, mes)
        logger.info(f'User {src_user} get pub_key {dest_user}')
        return True


main_commands.reg_cmd(AddContactCommand)
main_commands.reg_cmd(DelContactCommand)
main_commands.reg_cmd(ListContactsCommand)
main_commands.reg_cmd(RequestKeyCommand)
