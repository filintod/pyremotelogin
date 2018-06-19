from .unix import UnixDevice

__author__ = 'Filinto Duran (duranto@gmail.com)'


class LinuxDevice(UnixDevice):

    __mapper_args__ = {'polymorphic_identity': 'linux'}

    def __init__(self, *args, **kwargs):
        kwargs['os_name'] = 'linux'
        super(LinuxDevice, self).__init__(*args, **kwargs)
