from . import shellcommands
from ..linux import LinuxOS

__author__ = 'Filinto Duran (duranto@gmail.com)'


# TODO: break unix/linux to a bare and expand from there
class BusyBoxOS(LinuxOS):
    """
    Embedded Linux device
    """
    name = 'busybox'
    cmd = shellcommands.get_instance()
