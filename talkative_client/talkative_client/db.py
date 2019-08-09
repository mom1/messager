# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-05-25 22:33:58
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-10 00:38:07
import enum
import logging
from pathlib import Path

import sqlalchemy as sa
from dynaconf import settings
from sqlalchemy import desc, func
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.declarative.api import as_declarative
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, relationship
from sqlalchemy_utils import PasswordType

from .errors import (ContactExists, ContactNotExists, NotFoundContact,
                     NotFoundUser)

logger = logging.getLogger('client__db')


class DBManager(object):
    """Менеджер инициатор БД."""
    def __init__(self, envs, *args, **kwargs):
        """Инициализация.

        Args:
            envs: имя области БД
            *args: доп. параметры
            **kwargs: доп. параметры

        """
        self.envs = envs
        super().__init__()
        self._setup(*args, **kwargs)

    @staticmethod
    @sa.event.listens_for(Engine, 'connect')
    def set_sqlite_pragma(dbapi_connection, connection_record=None):
        """Параметры подключения к БД.

        Пока не знаю как от этого отделаться при других бекэндах

        Args:
            dbapi_connection: [description]
            connection_record: [description] (default: {None})

        """
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA synchronous = 0')
        cursor.execute('PRAGMA mmap_size = 268435456')
        cursor.execute('PRAGMA cache_size = 20480')  # 20 mb
        cursor.close()

    def _setup(self, *args, **kwargs):
        """Установка БД.

        Args:
            *args: доп. параметры
            **kwargs: доп. параметры

        """
        try:
            db_settings = settings.get(f'DATABASES.{self.envs}')
        except Exception as e:
            logger.critical('DATABASES setting required')
            raise e

        db_name = Path(db_settings.get('NAME', '').format(**{'user': settings.USER_NAME}))
        db_name.parent.mkdir(parents=True, exist_ok=True)
        self.engine = sa.create_engine(
            f'{db_settings.get("ENGINE", "sqlite")}:///{db_name}',
            echo=settings.get('DEBUG_SQL', False),
            connect_args=db_settings.get('CONNECT_ARGS'),
        )
        Base.metadata.create_all(self.engine)
        session = sa.orm.sessionmaker(bind=self.engine)()
        Core.set_session(session)
        ActiveUsers.delete_all()


@as_declarative()
class Base(object):
    """Базовый класс для таблиц.

    Attributes:
        id: Общее поле оно же ссылка

    """
    @declared_attr
    def __tablename__(cls):  # noqa
        """Имя таблицы в БД для класса

        Returns:
            имя таблицы это имя класса в ловер-кейсе
            str

        """
        return cls.__name__.lower()

    def __repr__(self):
        """Понятный репр для понимания."""
        return f'<{type(self).__name__}s({", ".join(i.key + "=" + str(getattr(self, i.key)) for i in self.__table__.columns)})>'

    id = sa.Column(sa.Integer, primary_key=True)  # noqa


class Core(Base):
    """Ядро для всех таблиц.

    Содержит общие для всех поля и функционал

    Attributes:
        building_type: Тип записи что бы знать из какой таблицы
        created: Дата время создания записи
        updated: Дата время изменения записи
        active: Признак активной записи
        sort: поле сортировки

    """

    building_type = sa.Column(sa.String(32), nullable=False)
    created = sa.Column(sa.DateTime, default=sa.func.now())
    updated = sa.Column(sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    active = sa.Column(sa.Boolean, default=False)
    sort = sa.Column(sa.Integer, default=0)

    @declared_attr
    def __mapper_args__(cls):  # noqa
        """Полиморфный маппер.

        Заполняет building_type именем класса

        """
        if cls.__name__ == 'Core':
            return {'polymorphic_on': cls.building_type}
        return {'polymorphic_identity': cls.__name__.lower()}

    def fill(self, **kwargs):
        """Заполнение полей объекта.

        Args:
            **kwargs: дикт где ключи имена, а значения значение полей таблицы

        Returns:
            Возвращает тек. объект
            object

        """
        for name, val in kwargs.items():
            setattr(self, name, val)
        return self

    @classmethod
    def set_session(cls, session):
        """Установка текущей сессии.

        Args:
            session: :class:`.Session`

        """
        cls._session = session

    @classmethod
    def query(cls, *args):
        """Возвращает объект для фильтрации и отборов.

        Args:
            *args: доп. параметры.

        Returns:
            Возвращает объект для отборов
            object

        """
        if not args:
            return cls._session.query(cls)
        return cls._session.query(*args)

    @classmethod  # noqa
    def all(cls):
        """Возвращает все записи объекта/таблицы."""
        return cls.query().all()

    @classmethod
    def first(cls):
        """Возвращает первую запись из отбора."""
        return cls.query().first()

    @classmethod
    def create(cls, **kwargs):
        """Создание новой записи.

        Args:
            **kwargs: дикт где ключи имена, а значения значение полей таблицы

        Returns:
            Возвращает созданный объект
            object

        """
        return cls().fill(**kwargs).save()

    def save(self):
        """Сохранение объекта.

        Сохранение всех изменений

        Returns:
            Возвращает сохраненный объект
            object

        """
        self._session.add(self)
        self._session.commit()
        return self

    @classmethod
    def get(cls, id_):
        """Получить один объект по ид.

        Args:
            id_: идентификатор записи для получения

        Returns:
            Возвращает найденный объект
            object

        """
        return cls.query().get(id_)

    @classmethod  # noqa
    def filter(cls, **kwargs):
        """Фильтрация таблицы.

        Стандартная фильтрация с указание полей и значений

        Args:
            **kwargs: параметры фильтрации

        Returns:
            Возвращает результат фильтрации
            object

        """
        return cls.query().filter(**kwargs)

    @classmethod
    def filter_by(cls, **kwargs):
        """Фильтр с упрощенным синтаксисом."""
        return cls.query().filter_by(**kwargs)

    def delete(self):
        """Удаление текущей записи."""
        self._session.delete(self)
        self._session.commit()

    @classmethod
    def delete_qs(cls, qs):
        """Удаление списка записей.

        По одной что бы удалились связанные записи в родительской таблице

        """
        for item in qs:
            item.delete()
        cls._session.commit()

    @classmethod
    def delete_all(cls):
        """Удалить все записи из заблицы."""
        cls.delete_qs(cls.all())

    @classmethod
    def save_all(cls, qs):
        """Сохранить все записи из списка.

        Args:
            qs: список объектов бд

        """
        for item in qs:
            cls._session.add(item)
        cls._session.commit()


class User(Core):
    """Таблица пользователей.

    Содержит основной функционал взаимодействия.

    Attributes:
        id: Идентификатор
        username: Имя пользователя
        descr: Описание
        password: Пароль шифрованный поддерживает сравнение
        auth_key: Ключ авторизации
        last_login: Последний вход на сервер (дата время)

    """

    id = sa.Column(sa.Integer, sa.ForeignKey(Core.id, ondelete='CASCADE'), primary_key=True)  # noqa
    username = sa.Column(sa.String(30), unique=True, nullable=False)
    descr = sa.Column(sa.String(300))
    password = sa.Column(PasswordType(schemes=['pbkdf2_sha512']), nullable=False, unique=False)
    auth_key = sa.Column(sa.String())
    last_login = sa.Column(sa.DateTime)

    @classmethod
    def by_name(cls, username):
        """Возвращает объект пользователя по его имени."""
        return cls.query().filter(func.lower(cls.username) == username.lower()).first()

    def get_last_login(self):
        """Хитрый способ получения времени последнего входа."""
        return getattr(UserHistory.query().filter_by(
            oper=self,
            type_row=TypeHistory.login,
        ).order_by(desc(UserHistory.created)).first(), 'created', 'Newer login')

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
        return Contact.filter_by(owner=self, contact=contact).count() != 0

    def add_contact(self, contact_name):
        """Добавляет пользователя с переданным именем в контакты текущего пользователя.

        Args:
            contact_name: имя добавляемого контакта

        """
        cont = User.by_name(contact_name)
        if not cont:
            raise NotFoundUser(contact_name)
        if self.has_contact(contact_name):
            raise ContactExists(contact_name)
        self.contacts.append(Contact(contact=cont))
        self.history.append(UserHistory(type_row=TypeHistory.add_contact, note=contact_name))
        self.save()

    def del_contact(self, contact_name):
        """Удаляет контакт.

        Удаляет контакт из контактов текущего пользователя

        Args:
            contact_name: имя контакта

        """
        cont = User.by_name(contact_name)
        if not cont:
            raise NotFoundContact(contact_name)
        if not self.has_contact(contact_name):
            raise ContactNotExists(contact_name)
        self.contacts.remove(Contact.filter_by(owner=self, contact=cont).one())
        self.history.append(UserHistory(type_row=TypeHistory.del_contact, note=contact_name))
        self.save()

    @hybrid_property
    def sent(self):
        """Количество отправленных сообщений."""
        return UserHistory.filter_by(oper=self, type_row=TypeHistory.mes_sent).count()

    @hybrid_property
    def accepted(self):
        """Количество полученных сообщений."""
        return UserHistory.filter_by(oper=self, type_row=TypeHistory.mes_accepted).count()

    def not_contacts(self):
        """Возвращает не контактов."""
        subquery = self._session.query(Contact.contact_id).filter(Contact.owner_id == self.id)
        query = self.query().filter(~User.id.in_(subquery), User.id != self.id)
        return query.all()


class TypeHistory(enum.Enum):
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
    mes_history = 8


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

    id = sa.Column(sa.Integer, sa.ForeignKey(Core.id, ondelete='CASCADE'), primary_key=True)  # noqa
    oper_id = sa.Column(sa.ForeignKey('user.id', ondelete='CASCADE'))
    ip_addr = sa.Column(sa.String(30))
    type_row = sa.Column(sa.Enum(TypeHistory))
    port = sa.Column(sa.Integer)
    note = sa.Column(sa.String())

    oper = relationship('User', backref='history', foreign_keys=[oper_id])

    @classmethod
    def proc_message(cls, scr, dest):
        """Фиксация отправленного или пришедшего сообщения.

        Args:
            scr: отправитель
            dest: получатель

        """
        cls.create(oper=User.by_name(scr), type_row=TypeHistory.mes_sent)
        cls.create(oper=User.by_name(dest), type_row=TypeHistory.mes_accepted)


class ActiveUsers(Core):
    """Активные пользователи.

    Пользователи находящиеся онлайн

    Attributes:
        id: Идентификатор
        oper_id: пользователь
        ip_addr: ИП адрес пользователя
        port: Порт подключения
        oper: обратная ссылка на пользователя

    """

    id = sa.Column(sa.Integer, sa.ForeignKey(Core.id, ondelete='CASCADE'), primary_key=True)  # noqa
    oper_id = sa.Column(sa.ForeignKey('user.id', ondelete='CASCADE'))
    ip_addr = sa.Column(sa.String(30))
    port = sa.Column(sa.Integer)

    oper = relationship('User', backref='user_activity', foreign_keys=[oper_id])


class Contact(Core):
    """Список контактов.

    Attributes:
        id: Идентификатор
        owner_id: Владелец
        contact_id: Контакт
        owner: обратная ссылка на владельца
        contact: Обратная ссылка на контакт

    """

    id = sa.Column(sa.Integer, sa.ForeignKey(Core.id, ondelete='CASCADE'), primary_key=True)  # noqa
    owner_id = sa.Column(sa.ForeignKey('user.id', ondelete='CASCADE'))
    contact_id = sa.Column(sa.ForeignKey('user.id', ondelete='CASCADE'))

    owner = relationship('User', backref=backref('contacts', order_by='Contact.contact_id'), foreign_keys=[owner_id])
    contact = relationship('User', foreign_keys=[contact_id])

    @classmethod
    def get_by_owner_contact(cls, owner, contact):
        """Возвращает записи фильтрованные по владельцу и контакту."""
        return cls.query().filter_by(owner=owner, contact=contact).first()


class UserMessages(Core):
    """Пользовательские сообщения.

    Хранилище сообщений

    Attributes:
        id: Идентификатор
        sender_id: ИД отправителя
        receiver_id: ИД получателя
        message: текст сообщения
        sender: Отправитель
        receiver: Получатель

    """

    id = sa.Column(sa.Integer, sa.ForeignKey(Core.id, ondelete='CASCADE'), primary_key=True)  # noqa
    sender_id = sa.Column(sa.ForeignKey('user.id', ondelete='CASCADE'))
    receiver_id = sa.Column(sa.ForeignKey('user.id', ondelete='CASCADE'))
    message = sa.Column(sa.Text())

    sender = relationship('User', backref='sents_messages', foreign_keys=[sender_id])
    receiver = relationship('User', backref='received_messages', foreign_keys=[receiver_id])

    @classmethod
    def chat_hiltory(cls, username, limit=100):
        """Получение истории чата.

        Args:
            username: имя пользователя
            limit: ограничение по количеству сообщений (default: {100})

        Returns:
            лист сообщений

        """
        user = User.by_name(username) if isinstance(username, str) else username
        return cls.query().filter((cls.sender == user) | (cls.receiver == user)).order_by(desc(cls.created)).limit(limit).all()


# Отладка
if __name__ == '__main__':
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    database = DBManager('server')
    User.login_user('1111', ip_addr='192.168.1.113', port=8080)
    User.login_user('McG2', ip_addr='192.168.1.112', port=8081)
    User.login_user('test1', ip_addr='192.168.1.100', port=8082)
    # Все пользователи
    # pp.pprint(User.all())
    # Активные пользователи
    # pp.pprint(ActiveUsers.all())
    User.logout_user('McG2', ip_addr='192.168.1.113', port=8081)
    # История по пользователю
    McG2 = User.by_name('McG2')
    # pp.pprint(McG2.history)
    # История по всем
    # pp.pprint(UserHistory.all())
    # Работа с контактами
    cont_1111 = User.by_name('1111')
    test1 = User.by_name('test1')
    McG2.add_contact('1111')
    McG2.add_contact('test1')
    cont_1111.add_contact('McG2')
    McG2.add_contact('Noop')

    # pp.pprint(McG2.contacts)
    # pp.pprint(cont_1111.contacts)
    McG2.del_contact('test1')
    pp.pprint(McG2.contacts)
    pp.pprint(McG2.history)
    UserHistory.proc_message('McG2', '1111')
    # История
    print(McG2.username, 'sent:', McG2.sent, 'accepted:', McG2.accepted)
    print(cont_1111.username, 'sent:', cont_1111.sent, 'accepted:', cont_1111.accepted)
