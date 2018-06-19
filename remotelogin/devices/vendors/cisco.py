import logging
import re

from remotelogin.connections.settings import SOCKET_TIMEOUT, SOCKET_TIMEOUT_FOR_LOGIN
from remotelogin.connections.decorators import WithInteractiveConnection
from remotelogin.connections.exceptions import ExpectNotFound
from remotelogin.connections.telnet import TelnetConnection
from remotelogin.devices.base import DeviceBase
from remotelogin.connections.expect import ExpectedRegex
from remotelogin.oper_sys.cisco import CiscoIOS, CiscoIOSACE


__author__ = 'Filinto Duran (duranto@gmail.com)'

log = logging.getLogger(__name__)


def _enter_enable(inter, device, *args, **kwargs):
    """ enters the enable area of the configuration

    :param inter:
    :param args:
    :param kwargs:
    :return:
    """
    cmd = inter.send_cmd('enble').expect_istr('Password:')
    if cmd.any_matches:
        inter.send_cmd(device.enable_password if device.enable_password else inter.con.password).expect_new_prompt()
    else:
        raise ExpectNotFound('Password was not return for enable command')


class CiscoDevice(DeviceBase, CiscoIOS):
    def __init__(self, enable_password='', config_password='', **kwargs):
        super(CiscoDevice, self).__init__(**kwargs)
        self.preferred_connection_type = 'ssh'
        self.is_level_privileged = False
        self.enable_password = enable_password
        self.config_password = config_password

    def open_enable(self, inter=None, conn=None, socket_timeout=SOCKET_TIMEOUT,
                    login_timeout=SOCKET_TIMEOUT_FOR_LOGIN, close_socket_on_exit=True):
        if inter is None:
            inter = self.open_terminal(conn=conn, socket_timeout=socket_timeout, login_timeout=login_timeout,
                                       close_socket_on_exit=close_socket_on_exit).open()
        _enter_enable(inter, self)
        return inter


class CiscoSwitch(CiscoDevice):
    def __init__(self, **kwargs):
        super(CiscoSwitch, self).__init__(**kwargs)
        self.preferred_connection_type = TelnetConnection
        self.is_level_privileged = False