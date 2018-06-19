from remotelogin.devices.base import DeviceBase
from remotelogin.devices.base_db import Device
from remotelogin.devices.settings import DEFAULT_STORAGE_FOLDER
from remotelogin.devices.tests.utils import update_db_config
from remotelogin.oper_sys.linux import LinuxOS
from remotelogin.oper_sys.windows import WindowsOS
import os
import pytest


def test_base():
    d = DeviceBase('localhost')
    assert d.os.__class__ == LinuxOS


def test_default_ip():
    d = DeviceBase('localhost', default_ip_address='127.0.0.1')
    assert d.default_ip_address == '127.0.0.1'


def test_default_ip_any_ip_type():
    d = DeviceBase('localhost')
    assert d.default_ip_address in ('::1', '127.0.0.1')


def test_default_ip_ipv4():
    d = DeviceBase('localhost', ip_type='ipv4')
    assert d.default_ip_address == '127.0.0.1'


def test_default_ip_ipv6():
    d = DeviceBase('localhost', ip_type='ipv6')
    assert d.default_ip_address == '::1'


def test_base_other_os():
    d = DeviceBase('localhost', os_name='Windows')
    assert d.os.__class__ == WindowsOS


def test_base_bad_os():
    with pytest.raises(ValueError):
        d = DeviceBase('localhost', os_name='klWindowssOS')


def test_storage_folder():
    """ a device will have a folder """
    cur_path = os.path.realpath('.')
    d = DeviceBase('localhost', storage_path=cur_path)
    assert d.folder == os.path.join(cur_path, 'localhost')


def test_storage_folder_default():
    """ a device will have a folder """
    d = DeviceBase('localhost')
    assert d.folder == os.path.join(DEFAULT_STORAGE_FOLDER, 'localhost')


def test_device_persintence():
    update_db_config()
    cur_path = os.path.realpath('.')
    d = Device('localhost', storage_path=cur_path)
    assert d.folder == os.path.join(cur_path, 'localhost')
    d.save()

    d2 = Device.get_by_hostname('localhost')
    assert d2.folder == os.path.join(cur_path, 'localhost')


def test_base_other_os_persistence():
    update_db_config()

    d = Device('localhost', os_name='Windows')
    assert d.os.__class__ == WindowsOS
    d.save()

    d2 = Device.get_by_hostname('localhost')
    assert d2.os.__class__ == WindowsOS


def test_default_ip_persistent():
    update_db_config()
    d = Device('localhost', default_ip_address='127.0.0.1')
    assert d.default_ip_address == '127.0.0.1'

    d.save()

    d2 = Device.get_by_hostname('localhost')
    assert d2.default_ip_address == '127.0.0.1'
