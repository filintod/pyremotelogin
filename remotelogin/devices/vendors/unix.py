from remotelogin.devices.base import DeviceBase

__author__ = 'Filinto Duran (duranto@gmail.com)'

import logging
log = logging.getLogger(__name__)


class UnixDevice(DeviceBase):

    DEFAULT_CONN_NAME = 'ssh'
    gnu_path = ''   # path to gnu commands that on solaris is usually different to linux

    __mapper_args__ = {'polymorphic_identity': 'unix'}

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('os_name', 'unix')
        super(UnixDevice, self).__init__(*args, **kwargs)