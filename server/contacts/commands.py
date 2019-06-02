# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-06-01 19:01:08
# @Last Modified by:   MaxST
# @Last Modified time: 2019-06-02 14:04:14
from commands import AbstractCommand, main_commands

from jim_mes import Message

from db import Contact, User


class AddContactCommand(AbstractCommand):
    name = 'add_contact'

    def execute(self, request, *args, **kwargs):
        if not request.param:
            return Message(action='request', text='Enter user name for add', destination=self.name)

        contact = User.by_name(request.param)
        owner = User.by_name(request.user)
        if contact and owner:
            try:
                Contact.create(owner=owner, contact=contact)
            except Exception:
                return Message(response='500')
        else:
            return Message(response='400', text='Contact not found')
        return Message(response='201')


class DelContactCommand(AbstractCommand):
    name = 'del_contact'

    def execute(self, request, *args, **kwargs):
        if not request.param:
            return Message(action='request', text='Enter user name for del', destination=self.name)

        user = User.by_name(request.user)
        contact = User.by_name(request.param)
        if contact and user:
            try:
                cont = Contact.get_by_owner_contact(user, contact)
                if cont:
                    cont.delete()
            except Exception:
                return Message(response='500')
        else:
            return Message(response='400', text='Contact or user not found')
        return Message(response='202')


class GetContactCommand(AbstractCommand):
    name = 'get_contacts'

    def execute(self, request, *args, **kwargs):
        contacts = User.by_name(request.user).contacts
        return Message(response='202', alert=[i.contact.username for i in contacts])


main_commands.reg_cmd(AddContactCommand)
main_commands.reg_cmd(DelContactCommand)
main_commands.reg_cmd(GetContactCommand)
