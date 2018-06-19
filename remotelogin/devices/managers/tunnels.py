import logging

from remotelogin.devices.exceptions import UnknownTunnelError, DuplicatedTunnelError
from remotelogin.devices.properties import TunnelInfo
from .base import ManagerWithItems

log = logging.getLogger(__name__)


class TunnelsManager(ManagerWithItems):

    UnknownItemError = UnknownTunnelError
    DuplicatedItemError = DuplicatedTunnelError
    ItemCls = TunnelInfo
    ItemTypeName = 'tunnels'

    def __init__(self, *args, **kwargs):
        self._items = {}
        super(TunnelsManager, self).__init__(*args, **kwargs)