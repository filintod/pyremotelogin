from remotelogin.devices.base import DeviceBase

__author__ = 'Filinto Duran (duranto@gmail.com)'

import logging
log = logging.getLogger(__name__)


class WindowsDevice(DeviceBase):
    __mapper_args__ = {'polymorphic_identity': 'windows'}

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('os_name', 'windows')
        super(WindowsDevice, self).__init__(*args, **kwargs)