import ipaddress
import itertools
import logging
import weakref
from uuid import uuid4, UUID

from remotelogin.connections import terminal, ssh, telnet, command, local
from remotelogin.devices.exceptions import (UserAuthenticationValuesError, NotImplementedProtocolError,
                                            NoDefaultInterfaceError)
from remotelogin.connections.exceptions import NoDefaultUserError
from fdutils import lists, net

log = logging.getLogger(__name__)


def v_to_str(value):
    if any(isinstance(value, cls) for cls in (UUID, ipaddress._IPAddressBase)):
        return str(value)
    return value


class WithSlots:

    @classmethod
    def check_args_from_dict(cls, cls_dict):
        if any([k not in cls.__slots__ for k in cls_dict]):
            raise KeyError('{} only allowed the following keys: {}. You provided: {}'
                           ''.format(cls.__name__, cls.__slots__, cls_dict.keys()))

    def copy(self):
        import copy
        return copy.copy(self)

    @classmethod
    def get_cls_kwargs(cls, kwargs):
        cls_kwargs = {k: v for (k, v) in kwargs.items() if k in cls.__slots__}
        for k in cls_kwargs:
            del kwargs[k]
        return cls_kwargs

    def __eq__(self, other):
        return all([getattr(self, k) == getattr(other, k) for k in self.__slots__ if k != 'id'])


class UserInfo(WithSlots):
    __slots__ = ('fullname', 'username', 'password', 'key_filename', 'key_password', 'location', 'id', 'email',
                 'expected_prompt', 'name', 'key_cert')

    NAME_IN_MANAGER = 'users'

    def __init__(self, username='', password='', fullname='', id=None, key_filename=None, key_password=None, key_cert=None,
                 location='', email='', expected_prompt=None, name=''):
        self.fullname = fullname
        self.username = username or name
        self.password = password
        self.key_filename = key_filename
        self.key_password = key_password
        self.location = location
        self.id = id or uuid4()
        self.email = email
        self.expected_prompt = expected_prompt
        self.name = name or username
        self.key_cert = key_cert

    def get_kwargs(self, keys):
        return {k: getattr(self, k) for k in self.__slots__ if k in keys and getattr(self, k) is not None}

    def update(self, other):
        list(itertools.starmap(setattr, ((self, k, getattr(other, k))
                                         for k in self.__slots__ if getattr(other, k))))

    # @property
    # def name(self):
    #     return self.username
    #
    # @name.setter
    # def name(self, value):
    #     self.username = value


def _get_ips_from_ip_attr(ip, hostname):
    ret = []
    for _ip in lists.to_sequence(ip):
        try:
            ips = [ipaddress.ip_address(_ip)]

        except ValueError:
            ips = [ipaddress.ip_address(_) for _ in net.nslookup_all(ip)]

        ret.extend(_ for _ in ips if _ not in ret)

    if hostname:
        ips = [ipaddress.ip_address(_) for _ in net.nslookup_all(hostname)]
        ret.extend(_ for _ in ips if _ not in ret)

    return ret


class InterfaceInfo(WithSlots):

    __slots__ = ('name', 'mac', 'ip', 'capacity', 'gateways', 'namespace', 'hostname')
    NAME_IN_MANAGER = 'interfaces'

    def __init__(self, name='', mac='', ip=(), capacity='', gateways=(), hostname='', namespace=''):
        self.mac = mac
        self.ip = _get_ips_from_ip_attr(ip, hostname)
        if not self.ip:
            raise ValueError('You need to provide value for ip or hostname of the interface')
        self.capacity = capacity
        self.gateways = lists.to_sequence(gateways)
        self.name = name or str(self.ip[0])
        self.namespace = namespace
        self.hostname = hostname

    @property
    def default_ip(self):
        return str(self.ip[0])

    @property
    def default_ipv6(self):
        for ip in self.ip:
            if isinstance(ip, ipaddress.IPv6Address):
                return ip
        return None


# TODO: use a general User database that can be reuse on different devices/tunnels/etc
# TODO: use general device table for each hop device
class TunnelInfo(WithSlots):

    __slots__ = ('name', 'hops')
    NAME_IN_MANAGER = 'tunnels'
    PROTO_2_CONN_TYPES = {'ssh': ssh.SshConnection,
                          'telnet': telnet.TelnetConnectionUnwrapped,
                          'local': local.LocalConnection,
                          'command': command.CommandConnection}

    def __init__(self, name='default', hops=()):
        if not hops:
            raise ValueError('The List of Hops in Proxy Jump should be provided')
        self.hops = list(lists.to_sequence(hops))
        self.name = name

        for hop in self.hops:
            self._verify_hop(hop)

    def get_connections(self):
        for hop in self.hops:
            kwargs = dict(hop)
            conn = self.PROTO_2_CONN_TYPES[kwargs.pop('proto')]
            user = kwargs.pop('user', None)
            if user:
                kwargs.update(user.get_kwargs(conn.ARGUMENTS_ALLOWED))
            yield conn(**kwargs)

    def _verify_hop(self, hop):

        host = hop.get('host', None)

        proto = hop.get('proto', 'ssh').lower()

        if not host and proto in ('ssh', 'telnet'):
            raise ValueError('You need to specify all host values for each proxy jump doing ssh or telnet')

        if proto not in self.PROTO_2_CONN_TYPES:
            raise ConnectionError('The attribute "proto" of one of the hops should be one of {}'
                                  ''.format(', '.join(self.PROTO_2_CONN_TYPES)))

        hop['proto'] = proto

        if proto == 'command':
            if 'cmd' not in hop:
                raise ConnectionError('A command should provide the "cmd" attribute to execute')

            if 'host' in hop or 'port' in hop:
                raise ConnectionError('A command should not get a "host" or "port" attribute')

        user = hop.get('user', None)

        if user is None:
            if proto in ('ssh', 'telnet'):
                raise ValueError('There are problems in the definition of user in connection ({})'.format(hop))

        elif isinstance(user, dict):
            hop['user'] = UserInfo(**user)

        elif not isinstance(user, UserInfo):
            raise ValueError('For the time being We need a full user information or a UserInfo Object in hops')

        if 'port' in hop:
            hop['port'] = int(hop['port'])


def _check_connection_arguments(conn_args, cls):
    if any([k not in cls.ARGUMENTS_ALLOWED for k in conn_args if k != 'user']):
        raise TypeError('One or more of the keys/attributes ({keys_provided}) for the connection are not\n'
                        'allowed for the connection type ({conn_type}).  \nAllowed attributes are: {allowed}'
                        ''.format(keys_provided=conn_args.keys(), conn_type=cls,
                                  allowed=cls.ARGUMENTS_ALLOWED))


class ConnectionInfo:
    """ class used to store information related to a connection class and its arguments
        like a metaclass
    """
    __slots__ = ('proto', '_cls', 'kwargs', 'manager', 'name', '_conn_cls', 'user', 'data', 'expected_prompt',
                 'all_kwargs', 'interface', 'tunnel')

    def __init__(self, proto, name, manager, user=None, interface=None, tunnel=None, **conn_args):

        if proto not in KNOWN_CONNECTION_PROTOCOLS:
            raise NotImplementedProtocolError('The proto ({}) is not an implemented protocol. '
                                              'Current implemented protocols: {}'
                                              ''.format(proto, KNOWN_CONNECTION_PROTOCOLS.keys()))

        self.proto = proto
        self._cls = KNOWN_CONNECTION_PROTOCOLS[proto]()
        self.all_kwargs = dict(conn_args)

        _check_connection_arguments(conn_args, self._cls)

        if hasattr(self._cls, 'set_terminal_kwargs'):
            self._cls.set_terminal_kwargs(conn_args)

        self.manager = weakref.proxy(manager)
        self.data = {}
        self.name = name
        self.expected_prompt = conn_args.get('expected_prompt', None)
        self._conn_cls = (self._cls.wrapped_connection
                          if isinstance(self._cls, terminal.TerminalConnectionWrapper)
                          else self._cls)

        self.user = self._get_default_instance(UserInfo, user)
        self.interface = self._get_default_instance(InterfaceInfo, interface)
        self.tunnel = self._get_default_instance(TunnelInfo, tunnel)
        # dropping any information related to user passed by mistake here
        for user_arg in ('username', 'password', 'key_filename', 'key_password', 'key_cert'):
            if user_arg in conn_args:
                log.warning('This connection was passed a user argument ({}). We are dropping it to avoid any issues. '
                            'You need to add the user using device.users object'.format(user_arg))
                del conn_args[user_arg]
        self.kwargs = dict(conn_args)
        # force int on port
        if 'port' in self.kwargs:
            self.kwargs['port'] = int(self.kwargs['port'])

    def to_json(self):
        ret = dict(self.all_kwargs)
        ret.pop('data_stream', None)
        if self.interface:
            ret.pop('host', None)
        ret['proto'] = self.proto

        if self.expected_prompt:
            ret['expected_prompt'] = self.expected_prompt

        for item in ('user', 'interface', 'tunnel'):
            item_instance = getattr(self, item)
            if item_instance:
                ret[item] = item_instance.name

        if 'os' in ret:
            del ret['os']

        return ret

    def _get_default_instance(self, cls, default_value):
        """ gets default instance for Interface, User or Tunnel given the provided value """

        if not default_value:
            return None

        manager_instance = getattr(self.manager, cls.NAME_IN_MANAGER)

        if isinstance(default_value, str):
            return manager_instance[default_value]

        if isinstance(default_value, dict):
            default_value = cls(**default_value)

        if isinstance(default_value, cls):
            if default_value not in manager_instance:
                manager_instance.add(default_value)
            elif default_value != manager_instance[default_value.name]:
                raise ValueError(
                    'This {item_name} ({name}) is already defined in the device but it has different attribute'
                    ' values please define it correctly.'.format(item_name=cls.__name__, name=default_value.name))
            return default_value

        raise ValueError('The value provided for {} cannot be converted to the proper class. Check attributes'
                         ''.format(cls.__name__))

    @property
    def cls(self):
        return self._conn_cls

    @property
    def host(self):
        return self.kwargs.get('host', self.manager.interfaces.default.default_ip)

    def _set_conn_credentials_args(self, user):
        """ if the connection does not provide the username we will use the device user credential """

        if user:
            user = self.manager.users[user]
        else:
            user = self.user or self.manager.users.default
        
            if not user:
                raise NoDefaultUserError('you need to provide a user or set the device or '
                                         'connection with a default user')

        kwargs = user.get_kwargs(self._conn_cls.ARGUMENTS_ALLOWED)

        if self._conn_cls.NEEDS_AUTHENTICATION:
            for combination in self.cls.AUTHENTICATION_KEYS_COMBINATIONS:
                if all([getattr(user, key) for key in combination]):
                    break
            else: # nobreak
                comb_str = (' and '.join(combination) for combination in self.cls.AUTHENTICATION_KEYS_COMBINATIONS)
                raise UserAuthenticationValuesError('\n\nThe user "{}" does not have any of the required combinations '
                                                    'information to login correctly.\nAllowed combinations: {}'
                                                    ''.format(user.username, ' or '.join(comb_str)))

        if self.expected_prompt:
            kwargs['expected_prompt'] = self.expected_prompt

        return kwargs, user

    def _set_conn_interface_args(self, interface, conn_args):
        """ if the connection does not provide the username we will use the device user credential """

        if interface:
            interface = self.manager.interfaces[interface]
        else:
            interface = self.interface or self.manager.interfaces.default

            if not interface:
                raise NoDefaultInterfaceError('you need to provide an interface or set the device or '
                                              'connection with a default interface')

        ip_type = conn_args.pop('ip_type', 'ipv4').lower()

        conn_args['host'] = interface.default_ipv6 if ip_type == 'ipv6' else interface.default_ip

        return conn_args

    def __getattr__(self, item):
        if item != 'kwargs' and item in self.kwargs:
            return self.kwargs[item]
        raise AttributeError

    def __setattr__(self, key, value):
        if key not in self.__slots__:
            self.kwargs[key] = self.all_kwargs[key] = value
        else:
            super(ConnectionInfo, self).__setattr__(key, value)

    def create_proxy_jump_connections(self, kwargs, tunnel):
        if tunnel:
            tunnel = self.manager.tunnels[tunnel]
        elif self.tunnel:
            tunnel = self.tunnel
        elif self.manager.default_tunnel:
            tunnel = self.manager.tunnels[self.manager.default_tunnel]

        if tunnel:
            kwargs['tunnel'] = list(tunnel.get_connections())

    def new_open_instance(self, user, instance_name, tunnel, interface, **conn_kwargs):

        kwargs = dict(self.kwargs)
        
        user_kwargs, user = self._set_conn_credentials_args(user)
        self._set_conn_interface_args(interface, conn_kwargs)

        instance_name = self.manager._check_instance_name_not_taken_and_open(self.name, instance_name, user,
                                                                             tunnel, interface)

        kwargs.update(conn_kwargs)
        kwargs.update(user_kwargs)

        self.create_proxy_jump_connections(kwargs, tunnel)
        instance = self._cls(**kwargs).open()

        if instance_name not in self.data:
            self.data[instance_name] = []

        if hasattr(instance, 'prompt_found') and instance.prompt_found:
            username = user_kwargs.get('username', None)
            gral_prompt = instance.prompt_found.replace(user.username, '{username}')
            if username:
                self.manager.users[user.name].expected_prompt = gral_prompt

            self.expected_prompt = gral_prompt

        self.data[instance_name].append(instance.data)

        return instance, user, instance_name

    def data_conversations_iterator(self, instance_names=()):
        for instance_name, instance_conversations in ((name, v) for (name, v) in self.data.items()
                                                     if not instance_names or name in instance_names):
            for data in instance_conversations:
                yield instance_name, data.get_timed_conversation_list()

    def conversations(self, instance_names=()):
        ret = {}

        for instance_name, conversation in self.data_conversations_iterator(instance_names):
            if instance_name not in ret:
                ret[instance_name] = []
            ret[instance_name].append(conversation)

        return ret

    def conversations_flat(self, instance_names=()):
        conversations = []

        for instance_name, conversation in self.data_conversations_iterator(instance_names):
            conversations.extend(conversation)

        return sorted(conversations, key=lambda m: m['time'])

    def conversations_string(self, template='\n>>> Sent ({date}): >>{sent}<<\n\nReceived: {received}'):
        return '\n'.join(template.format(date=s['time'], sent=s['sent'].strip(), received=s['received'])
                         for s in self.conversations_flat())

    def __enter__(self):
        return self.manager.open(self.name)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.manager.close(self.name)

    def open(self, user=None, instance_name=None, **conn_args):
        return self.manager.open(self.name, user, instance_name, **conn_args)

    def close(self, instance_name=None):
        self.manager.close(self.name, instance_name)


KNOWN_CONNECTION_PROTOCOLS = dict(ssh=lambda: terminal.TerminalConnectionWrapper(ssh.SshConnection),
                                  telnet=lambda: terminal.TerminalConnectionWrapper(telnet.TelnetConnectionUnwrapped),
                                  command=lambda: terminal.TerminalConnectionWrapper(command.CommandConnection)
                                  )