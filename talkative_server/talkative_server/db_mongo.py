# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-08-29 21:53:57
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-30 11:33:45
import logging
import sys
from datetime import datetime

from dynaconf import settings
from mongoengine import (BinaryField, BooleanField, DateTimeField, Document,
                         ImageField, IntField, LazyReferenceField, ListField,
                         ReferenceField, StringField, connect)

from .errors import NotFoundUser

logger = logging.getLogger('server__db')


def init_mongo(db_settings):
    global db
    credential = {'username': db_settings.get('USERNAME'), 'password': db_settings.get('PASSWORD'), 'authentication_source': 'admin'}
    db = connect(db_settings.get('NAME'), **credential)

    ActiveUsers.objects.delete()


class Core(Document):
    created = DateTimeField(default=datetime.utcnow)
    updated = DateTimeField(default=datetime.utcnow)
    active = BooleanField(default=False)
    sort = IntField(default=0)

    # meta = {'allow_inheritance': True}
    meta = {'abstract': True}


# class Contact(EmbeddedDocument):
#     """Список контактов.

#     Attributes:
#         id: Идентификатор
#         owner_id: Владелец
#         contact_id: Контакт
#         owner: обратная ссылка на владельца
#         contact: Обратная ссылка на контакт

#     """

#     contact = LazyReferenceField('User', reverse_delete_rule=CASCADE)


class TypeHistory(object):
    """Перечислитель типов записей в истории.

    Attributes:
        login: Вход
        logout: Выход
        ch_pass: Смена пароля
        add_contact: Добавлен контакт
        del_contact: Удален контакт
        mes_sent: Отправленно сообщение
        mes_accepted: Принято сообщение

    """

    login = 1
    logout = 2
    ch_pass = 3
    add_contact = 4
    del_contact = 5
    mes_sent = 6
    mes_accepted = 7

    choices = (
        (login, 'login'),
        (logout, 'logout'),
        (ch_pass, 'ch_pass'),
        (add_contact, 'add_contact'),
        (del_contact, 'del_contact'),
        (mes_sent, 'mes_sent'),
        (mes_accepted, 'mes_accepted'),
    )


class UserHistory(Core):
    """История пользователя.

    Хранит информацию о действиях пользователя

    Attributes:
        id: Идентификатор
        oper_id: ИД пользователя
        ip_addr: ИП адрес
        type_row: тип истории
        port: Порт подключения
        note: примечание
        oper: обратная ссылка на пользователя

    """

    oper = ReferenceField('User')
    ip_addr = StringField(max_length=30)
    type_row = IntField(choices=TypeHistory.choices)  # TypeHistory
    port = IntField()
    note = StringField()

    @classmethod
    def proc_message(cls, scr, dest):
        """Фиксация отправленного или пришедшего сообщения.

        Args:
            scr: отправитель
            dest: получатель

        """
        user = User.by_name(scr)
        if user:
            cls.objects.create(oper=user, type_row=TypeHistory.mes_sent)
        user = User.by_name(dest)
        if user:
            cls.objects.create(oper=user, type_row=TypeHistory.mes_accepted)


class User(Core):
    auth_key = BinaryField()
    avatar = BinaryField()
    descr = StringField(max_length=300)
    last_login = DateTimeField()
    password = StringField()
    # sa.Column(PasswordType(schemes=['pbkdf2_sha512']), nullable=False, unique=False)
    pub_key = StringField()
    username = StringField(max_length=30, unique=True, null=False, required=True)

    contacts = ListField(ReferenceField('self'))

    @property
    def user_activity(self):
        return ActiveUsers.objects(oper=self).all()

    @property
    def history(self):
        return UserHistory.objects(oper=self).all()

    @classmethod
    def by_name(cls, username):
        """Возвращает объект пользователя по его имени."""
        try:
            return cls.objects.get(username=username.lower())
        except Exception:
            return None

    @classmethod
    def login_user(cls, username, **kwargs):
        """Логирование при входе пользователя."""
        user = cls.by_name(username)
        if not user:
            kwargs['password'] = kwargs.get('password', 'placeholder')
            user = cls.objects.create(username=username, **kwargs)
        user.last_login = datetime.now()
        user.pub_key = kwargs.get('pub_key')
        user.save()
        param = {
            'oper': user,
            'ip_addr': str(kwargs.get('ip_addr', '')),
            'port': kwargs.get('port', None),
        }

        ActiveUsers.objects.create(**param)
        UserHistory.objects.create(type_row=TypeHistory.login, **param)

    @classmethod
    def logout_user(cls, username, **kwargs):
        """Логирование при выходе."""
        user = cls.by_name(username)
        if not user:
            logger.warn(str(NotFoundUser(username)))
        ActiveUsers.objects(oper=user).delete()
        UserHistory.objects.create(
            type_row=TypeHistory.logout,
            ip_addr=str(kwargs.get('ip_addr', '')),
            port=kwargs.get('port', None),
        )

    def has_contact(self, contact_name):
        """Проверка на контакт.

        Проверяет есть ли переданное имя в контактах текущего пользователя

        Args:
            contact_name: проверяемое имя

        Returns:
            Результат проверки
            bool

        """
        contact = User.by_name(contact_name) if contact_name else None
        if not contact:
            return False
        return contact in self.contacts

    def add_contact(self, contact_name):
        """Добавляет пользователя с переданным именем в контакты текущего пользователя.

        Args:
            contact_name: имя добавляемого контакта

        """
        cont = User.by_name(contact_name)
        if cont and not self.has_contact(contact_name):
            self.update(push__contacts=cont)
            self.save()
            UserHistory.objects.create(oper=self, type_row=TypeHistory.add_contact, note=contact_name)

    def del_contact(self, contact_name):
        """Удаляет контакт.

        Удаляет контакт из контактов текущего пользователя

        Args:
            contact_name: имя контакта

        """
        cont = User.by_name(contact_name)
        if cont and self.has_contact(contact_name):
            self.update(pull__contacts=cont)
            self.save()
            UserHistory.objects(oper=self, type_row=TypeHistory.del_contact, note=contact_name).delete()

    @property
    def sent(self):
        """Количество отправленных сообщений."""
        return len([i for i in self.history if i.type_row == TypeHistory.mes_sent])

    @property
    def accepted(self):
        """Количество полученных сообщений."""
        return len([i for i in self.history if i.type_row == TypeHistory.mes_accepted])


class ActiveUsers(Core):
    """Активные пользователи.

    Пользователи находящиеся онлайн

    Attributes:
        ip_addr: ИП адрес пользователя
        port: Порт подключения
        oper: обратная ссылка на пользователя

    """

    oper = ReferenceField(User)
    ip_addr = ip_addr = StringField(max_length=30)
    port = IntField()
    port = IntField()

    @classmethod
    def by_name(cls, username):
        """Возвращает объект пользователя по его имени."""
        user = User.by_name(username)
        return cls.objects(oper=user).first()


if __name__ == '__main__':
    init_mongo({'USERNAME': 'root', 'PASSWORD': 'root', 'NAME': 'db_server'})
    import ipdb
    ipdb.set_trace()
    user = User.by_name('maxst')
