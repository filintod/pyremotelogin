import logging

from sqlalchemy import event

from .base import DeviceWithEncryptionSettings
from .utils import transform_password
from remotelogin.connections import settings

from fdutils import db

log = logging.getLogger(__name__)


class DeviceDeclarativeBase(db.DeclarativeBase):

    __abstract__ = True

    @staticmethod
    def _return_device_if_conn_present(d):
        try:
            d.conn
            return d
        except Exception:
            log.warning('Problems Loading Device: We are probably trying to load a device that did not load properly '
                        'probably because of bad encryption password. Check your password, change it and save/reload')
            return d

    @classmethod
    def get_by_hostname(cls, host):
        return cls._return_device_if_conn_present(cls.query.filter_by(host=host).first())
    get_by_host = get_by_hostname

    @classmethod
    def get_by_filters_cursor(cls, **filters):
        return cls._return_device_if_conn_present(cls.query.filter_by(**filters))

    @classmethod
    def get_by_filters_all(cls, **filters):
        return cls._return_device_if_conn_present(cls.query.filter_by(**filters).all())

    def _data_to_json(self, item_manager):

        data = item_manager.make_serializable()

        if self.encrypt_passwords:
            transform_password(data, lambda value: self.crypto_engine.encrypt(value).decode(
                encoding=settings.DECODE_ENCODING_TYPE, errors=settings.DECODE_ERROR_ARGUMENT_VALUE
            ))

        return data

    def save(self):
        self.connectionsjson = self._data_to_json(self.conn)
        self.usersjson = self._data_to_json(self.users)
        self.interfacesjson = self._data_to_json(self.interfaces)
        self.tunnelsjson = self._data_to_json(self.tunnels)

        self.dbsession.add(self)
        self.dbsession.commit()


class Device(DeviceWithEncryptionSettings, DeviceDeclarativeBase):
    """ A device with database capability and refresh event to call init on reloads

        Passwords by default will be encrypted
    """
    __tablename__ = 'devices'


@event.listens_for(Device, 'refresh')
def receive_refresh(target, context, attrs):
    target.init()


# copied from https://stackoverflow.com/a/41665572/1132603 to deal with warnings when not using
# a subclass with defined polymorphic os
# @event.listens_for(Device, 'mapper_configured')
# def receive_mapper_configured(mapper, class_):
#     class FallbackToParentPolymorphicMap(dict):
#         def __missing__(self, key):
#             # return parent Item's mapper for undefined polymorphic_identity
#             return mapper
#
#     new_polymorphic_map = FallbackToParentPolymorphicMap()
#     new_polymorphic_map.update(mapper.polymorphic_map)
#     mapper.polymorphic_map = new_polymorphic_map
#
#     # for prevent 'incompatible polymorphic identity' warning, not necessarily
#     mapper._validate_polymorphic_identity = None