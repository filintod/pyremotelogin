from remotelogin.devices.base import DeviceWithEncryptionSettings
from fdutils import db


class TableNamedDevice(DeviceWithEncryptionSettings, db.DeclarativeBaseWithTableName):
    __abstract__ = True