from sqlalchemy.orm import sessionmaker

from .exceptions import DatabaseNotDefinedException
from .sabase import DeclarativeBase, _DeclarativeBaseWithTableName
from . import vendors
from .samixin import SessionMixin

engine = Session = DB_SESSION = None


def create_session(environment_settings=None, force=False, settings_group='db'):
    global engine
    global Session
    global DB_SESSION

    if environment_settings is None:
        from fdutils.config import environment_settings

    # create db engine and main session
    try:
        if 'db' in environment_settings[settings_group] or 'service_name' in environment_settings[settings_group]:

            if force or not DB_SESSION:
                if environment_settings[settings_group]['vendor'].lower() == 'sqllite':
                    import os
                    environment_settings[settings_group]['db'] = \
                        os.path.normpath(environment_settings[settings_group]['db'])

                engine = vendors.create_from_vendor(**environment_settings[settings_group]).conn
                Session = sessionmaker(bind=engine)
                DB_SESSION = Session()
                SessionMixin.set_session(DB_SESSION)

    except KeyError:
        pass


def set_session(session):
    SessionMixin.set_session(session)


def get_session():
    if DB_SESSION is None:
        raise DatabaseNotDefinedException('You have not configured the database in the environment yaml file')
    return DB_SESSION


def create_all():
    DeclarativeBase.metadata.create_all(engine)
    _DeclarativeBaseWithTableName.metadata.create_all(engine)


def drop_all():
    DeclarativeBase.metadata.drop_all(engine)
    _DeclarativeBaseWithTableName.metadata.drop_all(engine)