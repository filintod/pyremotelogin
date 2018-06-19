import logging

from remotelogin.devices.exceptions import UnknownInterfaceError, DuplicatedInterfaceError
from remotelogin.devices.properties import InterfaceInfo
from .base import ManagerWithItems

log = logging.getLogger(__name__)


class InterfacesManager(ManagerWithItems):

    UnknownItemError = UnknownInterfaceError
    DuplicatedItemError = DuplicatedInterfaceError
    ItemCls = InterfaceInfo
    ItemTypeName = 'interfaces'

    def __init__(self, *args, **kwargs):
        self._items = {}
        super(InterfacesManager, self).__init__(*args, **kwargs)

    def get_ip_addresses(self, with_namespace=False):
        if not with_namespace:
            return [str(ip) for item in self._items.values() for ip in item.ip]
        else:
            return [(item.namespace, str(ip)) for item in self._items.values() for ip in item.ip]

    @property
    def ip_addresses(self):
        return self.get_ip_addresses()

    def check_item_unique(self, item):
        """ checks no two interfaces share namespace, ip address """
        current_ip_addresses = self.get_ip_addresses(with_namespace=True)
        return not any((item.namespace, ip) in current_ip_addresses for ip in item.ip)

    def __contains__(self, item):
        default = super().__contains__(item)
        if not default:
            if isinstance(item, str):
                return item in self.ip_addresses
            elif isinstance(item, self.ItemCls):
                return any(ip in item.ip for ip in self.ip_addresses)

        return default
