# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-05-25 22:33:58
# @Last Modified by:   MaxST
# @Last Modified time: 2019-07-25 09:07:45
import datetime
import enum
import logging

import sqlalchemy as sa
from dynaconf import settings
from sqlalchemy import desc, func
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.declarative.api import as_declarative
from sqlalchemy.orm import relationship
from sqlalchemy_utils import PasswordType

from errors import NotFoundUser

logger = logging.getLogger('server__db')


class DBManager(object):
    def __init__(self, envs, *args, **kwargs):
        self.envs = envs
        super().__init__()
        self._setup(*args, **kwargs)

    @staticmethod
    @sa.event.listens_for(Engine, 'connect')
    def set_sqlite_pragma(dbapi_connection, connection_record=None):
        # Пока не знаю как от этого отделаться при других бекэндах
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA synchronous = 0')
        cursor.execute('PRAGMA mmap_size = 268435456')
        cursor.execute('PRAGMA cache_size = 20480')  # 20 mb
        cursor.close()

    def _setup(self, *args, **kwargs):
        db = settings.get('DATABASES')
        if not db:
            logger.critical('DATABASES setting required')
            exit(1)
        db_settings = db.get(self.envs, db.get('default'))
        if not db_settings:
            logger.critical(f'DATABASE setting need for {self.envs}')
            exit(1)
        self.engine = sa.create_engine(
            f'{db_settings.get("ENGINE", "sqlite")}:///{db_settings.get("NAME")}',
            echo=settings.get('DEBUG_SQL', False),
            connect_args=db_settings.get('CONNECT_ARGS'),
        )
        Base.metadata.create_all(self.engine)
        session = sa.orm.sessionmaker(bind=self.engine)()
        Core.set_session(session)
        ActiveUsers.delete_all()


@as_declarative()
class Base(object):
    @declared_attr
    def __tablename__(cls):  # noqa
        return cls.__name__.lower()

    def __repr__(self):
        return f'<{type(self).__name__}s({", ".join(i.key + "=" + str(getattr(self, i.key)) for i in self.__table__.columns)})>'

    id = sa.Column(sa.Integer, primary_key=True)  # noqa


class Core(Base):
    building_type = sa.Column(sa.String(32), nullable=False)
    created = sa.Column(sa.DateTime, default=sa.func.now())
    updated = sa.Column(sa.DateTime, default=sa.func.now(), onupdate=sa.func.utc_timestamp())
    active = sa.Column(sa.Boolean, default=False)
    sort = sa.Column(sa.Integer, default=0)

    @declared_attr
    def __mapper_args__(cls):  # noqa
        if cls.__name__ == 'Core':
            return {'polymorphic_on': cls.building_type}
        return {'polymorphic_identity': cls.__name__.lower()}

    def fill(self, **kwargs):
        for name, val in kwargs.items():
            setattr(self, name, val)
        return self

    @classmethod
    def set_session(cls, session):
        cls._session = session

    @classmethod
    def query(cls):
        return cls._session.query(cls)

    @classmethod  # noqa
    def all(cls):
        return cls.query().all()

    @classmethod
    def first(cls):
        return cls.query().first()

    @classmethod
    def create(cls, **kwargs):
        return cls().fill(**kwargs).save()

    def save(self):
        self._session.add(self)
        self._session.commit()
        return self

    @classmethod
    def get(cls, id_):
        return cls.query().get(id_)

    @classmethod  # noqa
    def filter(cls, **kwargs):
        return cls.query().filter(**kwargs)

    @classmethod
    def filter_by(cls, **kwargs):
        return cls.query().filter_by(**kwargs)

    def delete(self):
        self._session.delete(self)
        self._session.commit()

    @classmethod
    def delete_qs(cls, qs):
        """delete queryset"""
        for item in qs:
            item.delete()
        cls._session.commit()

    @classmethod
    def delete_all(cls):
        cls.delete_qs(cls.all())


class User(Core):
    id = sa.Column(sa.Integer, sa.ForeignKey(Core.id, ondelete='CASCADE'), primary_key=True)  # noqa
    username = sa.Column(sa.String(30), unique=True, nullable=False)
    descr = sa.Column(sa.String(300))
    password = sa.Column(PasswordType(schemes=['pbkdf2_sha512']), nullable=False, unique=False)
    last_login = sa.Column(sa.DateTime)

    @classmethod
    def by_name(cls, username):
        return cls.query().filter(func.lower(cls.username) == username).first()

    def get_last_login(self):
        return getattr(UserHistory.query().filter_by(
            oper=self,
            type_row=TypeHistory.login,
        ).order_by(desc(UserHistory.created)).first(), 'created', 'Newer login')

    @classmethod
    def login_user(cls, username, **kwargs):
        user = cls.by_name(username)
        if not user:
            user = cls.create(username=username, password='placeholder')
        user.last_login = datetime.datetime.now()
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
        user = cls.by_name(username)
        if not user:
            logger.warn(str(NotFoundUser(username)))
            # raise NotFoundUser(username)
        ActiveUsers.delete_qs(ActiveUsers.filter_by(oper=user))
        UserHistory.create(
            type_row=TypeHistory.logout,
            oper=user,
            ip_addr=str(kwargs.get('ip_addr', '')),
            port=kwargs.get('port', None),
        )


class TypeHistory(enum.Enum):
    login = 1
    logout = 2
    ch_pass = 3
    add_contact = 4
    del_contact = 5


class UserHistory(Core):
    id = sa.Column(sa.Integer, sa.ForeignKey(Core.id, ondelete='CASCADE'), primary_key=True)  # noqa
    oper_id = sa.Column(sa.ForeignKey('user.id', ondelete='CASCADE'))
    ip_addr = sa.Column(sa.String(30))
    type_row = sa.Column(sa.Enum(TypeHistory))
    port = sa.Column(sa.Integer)

    oper = relationship('User', backref='history', foreign_keys=[oper_id])


class ActiveUsers(Core):
    id = sa.Column(sa.Integer, sa.ForeignKey(Core.id, ondelete='CASCADE'), primary_key=True)  # noqa
    oper_id = sa.Column(sa.ForeignKey('user.id', ondelete='CASCADE'))
    ip_addr = sa.Column(sa.String(30))
    port = sa.Column(sa.Integer)

    oper = relationship('User', backref='user_activity', foreign_keys=[oper_id])


class Contact(Core):
    id = sa.Column(sa.Integer, sa.ForeignKey(Core.id, ondelete='CASCADE'), primary_key=True)  # noqa
    owner_id = sa.Column(sa.ForeignKey('user.id', ondelete='CASCADE'))
    contact_id = sa.Column(sa.ForeignKey('user.id'))

    owner = relationship('User', backref='contacts', foreign_keys=[owner_id])
    contact = relationship('User', foreign_keys=[contact_id])

    @classmethod
    def get_by_owner_contact(cls, owner, contact):
        return cls.query().filter_by(owner=owner, contact=contact).first()
