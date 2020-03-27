import logging
import os
import threading
import weakref

from sqlalchemy import orm, Column, Integer, String, Boolean, TypeDecorator, Binary, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_propertycan_change_prompt

from remotelogin import oper_sys
from remotelogin.connections import settings
from remotelogin.devices.exceptions import ConnectionInstanceOpenError
from remotelogin.devices.settings import DEFAULT_STORAGE_FOLDER, ENCRYPT_PASSWORDS_IN_DB, LOCATION

import fdutils as utils
from fdutils import crypto
from fdutils.db.types import ToJSONCapable
from remotelogin.devices.utils import transform_password, get_ip_from_default_or_hostname

from . import managers

log = logging.getLogger(__name__)


class OSColumn(ToJSONCapable):
    """Enables OS class storage by encoding and decoding on the fly."""
    impl = String

    def process_bind_param(self, value, dialect):
        return super().process_bind_param(value.serialize(), dialect)

    def process_result_value(self, value, dialect):
        os_info = super().process_result_value(value, dialect)
        return oper_sys.os_factory(os_info['name'], **os_info['kwargs'])


# TODO: finish save conversations
# TODO: create user/group tables
# TODO: create RBAC for group/users and methods to allow/forbid actions depending on them
# TODO: use servers in tunnel hops
# TODO: shrink __init__ and move most of it to init (sa.reconstructor)
# TODO: remove default_ip_address
# TODO: fix hack to force error on retrieving object with bad password
# TODO: add connection shell information to database
class DeviceBase:
    """
    A Devices defines general functionality and implementation for all devices like name, add connection,
    start snoop, get log files, etc. Particular implementation of some functions will be done by the derivatives of
    Device.

    This is also a mixing for sqlalchemy to use to store device information in a database.  To do that you need
    to inherit from DeviceBase and a SqlAlchemy Declarative base like the one found in fdutils.db.sabase.DeclarativeBase
    """

    id = Column(Integer, primary_key=True, autoincrement=True)
    _host = Column('host', String)
    description = Column(String, default='')
    location = Column(String, default='')
    serial = Column(String, default='')
    vendor = Column(String, default='')
    hw_version = Column(String, default='')
    fw_version = Column(String, default='')
    os_version = Column(String, default='')
    model = Column(String, default='')
    encrypt_passwords = Column(Boolean, default=False)
    encrypt_salt = Column(Binary)
    save_conversations = Column(Boolean, default=True)
    os = Column(OSColumn)
    folder = Column(String, default='')
    admin = Column(String, default='')
    group = Column(String, default='')

    # TODO: change to JSON column type
    connectionsjson = Column('connections', ToJSONCapable)
    tunnelsjson = Column('tunnels', ToJSONCapable)
    usersjson = Column('users', ToJSONCapable)
    interfacesjson = Column('interfaces', ToJSONCapable)
    #facts = Column(ToJSONCapable)

    __table_args__ = (
        UniqueConstraint('host', 'location', 'serial'),
    )

    crypto_engine = None

    EXPECTED_PROMPT = None

    def __init__(self, host='', os_name='', default_ip_address=None, description='', location='',
                 storage_path='', users=None, connections=None, interfaces=None, tunnels=None,
                 save_conversations=True, ip_type='ipv4', encrypt_passwords=False,
                 serial='', vendor='', hw_version='', os_version='', model='', fw_version='',
                 hostname='', admin='None', group='', can_change_prompt=None, facts=None):
        """ initializes the device

        Args:
            host (str): hostname/ip of device
            description (str):
            location (str): physical location
            storage_path (str): path to where to store files locally related to the device (ie connection data files)
            os_name: type of OS to use
            default_ip_address: the default ip address to use to connect to it
            users (dict): dictionary to be passed to managers.users.User.add_users
            connections (dict): dictionary to be passed to managers.connections.Connection.add_connections
            ip_type (str): ipv4 or ipv6
            save_conversations (bool): save conversations of connections or not [True]
            facts (dict): facts about the device (memory, processes, commands available, etc.)
        """
        self.id = None
        self._host = hostname or host
        self.description = description
        self.location = location or LOCATION
        self.admin = admin
        self.group = group
        self.can_change_prompt = can_change_prompt

        self.save_conversations = save_conversations
        self.folder = os.path.join(os.path.normpath(os.path.expanduser(storage_path or DEFAULT_STORAGE_FOLDER)),
                                   utils.files.slugify(self._host))

        self._is_folder_created = False

        # new device  info
        self.serial = serial
        self.vendor = vendor
        self.hw_version = hw_version
        self.os_version = os_version
        self.fw_version = fw_version
        self.model = model

        # managers
        self.conn = self.files = self.users = self.interfaces = self.tunnels = None

        self.cmd = None
        self.os = self.init_os(os_name)
        self.encrypt_passwords = encrypt_passwords
        self.lock = self._services = self.encrypt_salt = self.crypto_engine = None

        self.init(users=users, connections=connections, interfaces=interfaces, tunnels=tunnels)

        # default connection will use this to connect to it
        default_ip_address = get_ip_from_default_or_hostname(host, default_ip_address, ip_type)
        if default_ip_address and default_ip_address not in self.interfaces.ip_addresses:
            self.interfaces.add('default', ip=default_ip_address)

    @property
    def connections(self):
        return self.conn

    @property
    def default_ip_address(self):
        if self.interfaces.default:
            return self.interfaces.default.default_ip
        return ''

    @hybrid_property
    def host(self):
        return self._host

    @host.setter
    def host(self, host):
        host_ip = get_ip_from_default_or_hostname(host)
        if host_ip and host_ip not in self.interfaces.ip_addresses:
            self.interfaces.add(host, ip=host_ip)

    def init_os(self, os_name):
        if isinstance(os_name, oper_sys.base.OSBase):
            return os_name    # a device will have an os
        else:
            return oper_sys.os_factory(os_name, can_change_prompt=self.can_change_prompt)
                                       #,can_resize_pty=None, reset_prompt_on_exit=None, default_prompt=None,
                                       # can_disable_history=None)

    @orm.reconstructor
    def init(self, **kwargs):

        self.crypto_engine = None

        if self.encrypt_passwords:
            self._decrypt_data()

        self.conn = managers.connections.ConnectionsManager(self)
        self.files = managers.files.FilesManager(self)
        self.users = managers.users.UsersManager(self)
        self.interfaces = managers.interfaces.InterfacesManager(self)
        self.tunnels = managers.tunnels.TunnelsManager(self)
        self.cmd = DeviceCommand(self)

        self.lock = threading.RLock()
        self._services = None

        self.users.add_dbelements_to_instance(self.usersjson, kwargs.get('users', None))
        self.tunnels.add_dbelements_to_instance(self.tunnelsjson, kwargs.get('tunnels', None))
        self.interfaces.add_dbelements_to_instance(self.interfacesjson, kwargs.get('interfaces', None))
        self.conn.add_dbelements_to_instance(self.connectionsjson, kwargs.get('connections', None))

        self.init_instance()

    def _decrypt_data(self):
        crypto_engine = crypto.get_default_crypto_engine().clone(salt=self.encrypt_salt)
        for attr_name in ('tunnelsjson', 'connectionsjson', 'usersjson', 'interfacesjson'):
            attr = getattr(self, attr_name, None)
            if attr:
                transform_password(attr, lambda value: crypto_engine.decrypt(
                    value.encode(encoding=settings.ENCODE_ENCODING_TYPE,
                                 errors=settings.ENCODE_ERROR_ARGUMENT_VALUE)))

        if not self.encrypt_salt:
            self.encrypt_salt = crypto_engine.salt
        self.crypto_engine = crypto_engine

    def init_instance(self):
        pass

    def __str__(self):
        return "Device {} at {}".format(self._host, self.default_ip_address)

    def _get_lazy_mgr(self, attr, mgr):
        if getattr(self, attr, None) is None:
            setattr(self, attr, mgr(self))

        return getattr(self, attr)

    @property
    def svcs(self):
        """
        Returns:
            managers.services.ServicesManager: a service manager
        """
        return self._get_lazy_mgr('_services', managers.services.ServicesManager)

    def close(self):
        mgrs = ('_services', 'connections', 'files')
        if all([a in self.__dict__ for a in mgrs]):
            for svc in mgrs:
                try:
                    if getattr(self, svc, False):
                        getattr(self, svc).close_all()
                except Exception:
                    if log:
                        log.exception('Problems closing {}'.format(svc))

    def __getattr__(self, item):
        """ defaults to send commands to the default connection """
        if 'conn' in self.__dict__ and self.conn:
            try:
                return getattr(self.conn, item)
            except ConnectionInstanceOpenError:
                raise ConnectionInstanceOpenError(
                    'There are two possible options for this error here: '
                    '\n - There are No Open Connections and you were trying a connection method "{method}".'
                    '\n - There is a typo in calling "{method}" item.'.format(method=item))
        raise AttributeError


class OSCmd:
    def __init__(self, dev, cmd):
        self.dev = dev
        self.cmd = cmd

    def __call__(self, *args, **kwargs):
        return self.dev.conn.check_output(self.cmd(*args, **kwargs))


class DeviceCommand:

    def __init__(self, device):
        self.device = weakref.proxy(device)
        self.__cmds = {}

    def __getattr__(self, item):
        if item not in self.__cmds:
            self.__cmds[item] = OSCmd(self.device, getattr(self.device.os.cmd, item))
        return self.__cmds[item]


class DeviceWithEncryptionSettings(DeviceBase):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('encrypt_passwords', ENCRYPT_PASSWORDS_IN_DB)
        super().__init__(*args, **kwargs)
