# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-05-25 22:33:58
# @Last Modified by:   MaxST
# @Last Modified time: 2019-06-01 16:39:20
import enum

import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.declarative.api import as_declarative
from sqlalchemy_utils import PasswordType

from settings import Settings

settings = Settings.get_instance()


@as_declarative(metadata=sa.MetaData(schema=settings.get('db_name')))
class Base(object):
    @declared_attr
    def __tablename__(cls):  # noqa
        return cls.__name__.lower()

    def __repr__(self):
        return f'<{type(self).__name__}s({", ".join(i.key + "=" + str(getattr(self, i.key)) for i in self.__table__.columns)})>'

    id = sa.Column(sa.Integer, primary_key=True)  # noqa


class DBManager(object):
    __instance = None

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._setup(*args, **kwargs)

    @classmethod
    def get_instance(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = cls(*args, **kwargs)
        return cls.__instance

    @staticmethod
    @sa.event.listens_for(Engine, 'connect')
    def set_sqlite_pragma(dbapi_connection, connection_record=None):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA synchronous = 0')
        cursor.execute('PRAGMA mmap_size = 268435456')
        # cursor.execute('PRAGMA cache_size = 20480') 20 mb
        cursor.execute('PRAGMA cache_size = 2048')
        cursor.close()

    def _setup(self, *args, **kwargs):
        self.engine = sa.create_engine('sqlite://', echo=False, connect_args={'check_same_thread': False})
        self.db_name = settings.get('db_name')
        self.engine.execute('ATTACH DATABASE ? AS ? ', (f'server/{self.db_name}.db', '{0}'.format(self.db_name)))
        Base.metadata.create_all(self.engine)
        Core.set_session(sa.orm.sessionmaker(bind=self.engine)())


class Core(Base):
    created = sa.Column(sa.DateTime, default=sa.func.now())
    updated = sa.Column(sa.DateTime, default=sa.func.now(), onupdate=sa.func.utc_timestamp())
    active = sa.Column(sa.Boolean, default=False)
    sort = sa.Column(sa.Integer, default=0)

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

    def delete(self):
        self._session.delete(self)
        self._session.flush()


class User(Core):
    id = sa.Column(sa.Integer, sa.ForeignKey(Core.id), primary_key=True)  # noqa
    username = sa.Column(sa.String(30), unique=True, nullable=False)
    descr = sa.Column(sa.String(300))
    password = sa.Column(PasswordType(schemes=['pbkdf2_sha512']), nullable=False, unique=False)


class TypeHistory(enum.Enum):
    login = 1
    logout = 2
    ch_pass = 3
    add_contact = 4
    del_contact = 5


class UserHistory(Core):
    id = sa.Column(sa.Integer, sa.ForeignKey(Core.id), primary_key=True)  # noqa
    oper_id = sa.Column(sa.ForeignKey('user.id', ondelete='CASCADE'))
    ip_addr = sa.Column(sa.String(30))
    type_row = sa.Column(sa.Enum(TypeHistory))


class Contact(Core):
    id = sa.Column(sa.Integer, sa.ForeignKey(Core.id), primary_key=True)  # noqa
    owner_id = sa.Column(sa.ForeignKey('user.id', ondelete='CASCADE'))
    contact_id = sa.Column(sa.ForeignKey('user.id'))
