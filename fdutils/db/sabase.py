from sqlalchemy.ext.declarative import declarative_base, declared_attr
from .samixin import SessionMixin

_Base = declarative_base()


class DeclarativeBase(_Base, SessionMixin):
    __abstract__ = True


class _DeclarativeBaseWithTableName:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()


_DeclarativeBaseWithTableName = declarative_base(cls=_DeclarativeBaseWithTableName)


class DeclarativeBaseWithTableName(_DeclarativeBaseWithTableName, SessionMixin):
    __abstract__ = True
