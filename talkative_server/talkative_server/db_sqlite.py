# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-05-25 22:33:58
# @Last Modified by:   MaxST
# @Last Modified time: 2019-08-30 08:08:24
import datetime
import enum
import logging
import threading
from pathlib import Path

import sqlalchemy as sa
from dynaconf import settings
from sqlalchemy import desc, func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.declarative.api import as_declarative
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
from sqlalchemy_utils import PasswordType

from .errors import NotFoundUser

logger = logging.getLogger('server__db')
database_lock = threading.Lock()


def init_sqlite(db_settings):
    db_name = Path(db_settings.get('NAME'))
    db_name.parent.mkdir(parents=True, exist_ok=True)
    engine = sa.create_engine(
        f'{db_settings.get("ENGINE", "sqlite")}:///{db_name}',
        echo=settings.get('DEBUG_SQL', False),
        connect_args=db_settings.get('CONNECT_ARGS'),
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = scoped_session(session_factory)

    Core.set_session(session())
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
    updated = sa.Column(sa.DateTime, default=sa.func.now(), onupdate=sa.func.utc_timestamp())
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


class User(Core):
    """Таблица пользователей.

    Содержит основной функционал взаимодействия.

    Attributes:
        id: Идентификатор
        username: Имя пользователя
        descr: Описание
        password: Пароль шифрованный поддерживает сравнение
        auth_key: Ключ авторизации
        pub_key: Публичный ключ шифрования
        last_login: Последний вход на сервер (дата время)

    """

    id = sa.Column(sa.Integer, sa.ForeignKey(Core.id, ondelete='CASCADE'), primary_key=True)  # noqa
    auth_key = sa.Column(sa.String())
    avatar = sa.Column(sa.BLOB)
    descr = sa.Column(sa.String(300))
    last_login = sa.Column(sa.DateTime)
    password = sa.Column(PasswordType(schemes=['pbkdf2_sha512']), nullable=False, unique=False)
    pub_key = sa.Column(sa.String())
    username = sa.Column(sa.String(30), unique=True, nullable=False)

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

    @classmethod
    def login_user(cls, username, **kwargs):
        """Логирование при входе пользователя."""
        user = cls.by_name(username)
        if not user:
            kwargs['password'] = kwargs.get('password', 'placeholder')
            user = cls.create(username=username, **kwargs)
        user.last_login = datetime.datetime.now()
        user.pub_key = kwargs.get('pub_key')
        user.save()
        param = {
            'oper': user,
            'ip_addr': str(kwargs.get('ip_addr', '')),
            'port': kwargs.get('port', None),
        }
        ActiveUsers.create(**param)
        UserHistory.create(type_row=TypeHistory.login, **param)

    @classmethod
    def logout_user(cls, username, **kwargs):
        """Логирование при выходе."""
        user = cls.by_name(username)
        if not user:
            logger.warn(str(NotFoundUser(username)))
        ActiveUsers.delete_qs(ActiveUsers.filter_by(oper=user))
        UserHistory.create(
            type_row=TypeHistory.logout,
            oper=user,
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
        return Contact.filter_by(owner=self, contact=contact).count() != 0

    def add_contact(self, contact_name):
        """Добавляет пользователя с переданным именем в контакты текущего пользователя.

        Args:
            contact_name: имя добавляемого контакта

        """
        cont = User.by_name(contact_name)
        if cont and not self.has_contact(contact_name):
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
        if cont and self.has_contact(contact_name):
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

    @classmethod
    def by_name(cls, username):
        """Возвращает объект пользователя по его имени."""
        user = User.by_name(username)
        return cls.query().filter(cls.oper == user).first()


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

    owner = relationship('User', backref='contacts', foreign_keys=[owner_id])
    contact = relationship('User', foreign_keys=[contact_id])

    @classmethod
    def get_by_owner_contact(cls, owner, contact):
        """Возвращает записи фильтрованные по владельцу и контакту."""
        return cls.query().filter_by(owner=owner, contact=contact).first()
