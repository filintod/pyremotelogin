import collections
import functools
import logging
import threading
import weakref
from functools import partialmethod

from remotelogin.devices.exceptions import (ConnectionInstanceOpenError, DuplicatedConnectionError,
                                          UnknownConnectionError, UnknownUserError)
from remotelogin.devices.properties import ConnectionInfo, UserInfo, KNOWN_CONNECTION_PROTOCOLS
from fdutils.db import NoDBSessionError

from .base import ManagerWithItems

log = logging.getLogger(__name__)


class OpenConnectionInstanceUser:
    """ helper class to avoid having a user of an open connection closing the connection inadvertently
        when used in a context (with ...)
    """

    def __init__(self, open_connection):
        self.__conn = weakref.proxy(open_connection)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    def __getattr__(self, item):
        return getattr(self.__conn, item)


class OpenConnectionInstance:
    """ class needed to keep track of the connection and properly capture when the connection is closed
        so we can retrieve the data related to the device """

    def __init__(self, manager, conn_name, instance_name, user, tunnel=None, interface=None, **other_conn_args):
        self.__tunnel = tunnel
        self.__conn = None
        self.conn_name = conn_name
        self.instance_name = instance_name
        self.__manager = manager
        self.__interface = interface
        self.__is_close = False
        self.__other_conn_args = other_conn_args
        self._user = user

        # do the opening
        self.__open()

    @property
    def identifier(self):
        return self.conn_name, self.instance_name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.__is_close:
            self.__close()

    def __del__(self):
        if not self.__is_close:
            self.__close()

    def __getattr__(self, item):
        if not item.startswith('_OpenConnectionInstance'):
            return getattr(self.__conn, item)
        raise AttributeError(item)

    def close(self):
        return self.__close()

    @property
    def username(self):
        return self._user.username

    @property
    def password(self):
        return self._user.password

    @property
    def expected_prompt(self):
        return self._user.expected_prompt

    def __open(self):
        self.__conn, self.conn_name, self._user, self.instance_name = \
            self.__manager._open(self._user, self.conn_name, self.instance_name,
                                 self.__other_conn_args, self.__tunnel, self.__interface)
        return self

    def close_on_manager_del(self):
        self.__conn.close()

    # TODO: use os cmd to exit instead of hardcoded exit cmd
    def __close(self):
        if self.__conn:
            self.__manager._delete_open_connection_instance(self.conn_name, self.instance_name)
            if self.__tunnel:
                self.__conn.send_cmd('exit')
            self.__conn.close()
            self.__is_close = True


class ConnectionsManager(ManagerWithItems):

    DEFAULT_INSTANCE_NAME = 'default'
    UnknownItemError = UnknownConnectionError
    DuplicatedItemError = DuplicatedConnectionError
    ItemCls = ConnectionInfo
    ItemTypeName = 'connections'

    def __init__(self, *args, **kwargs):
        self._open_instances = threading.local()
        self._conn_locks = {}
        self.default_tunnel = kwargs.pop('default_tunnel', '')
        super(ConnectionsManager, self).__init__(*args, **kwargs)

    def __enter__(self):
        """ default context opens the default connection """
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def open_instances(self):
        """ lazy create thread local _open_instances object """
        if not self._open_instances.__dict__:
            self._open_instances.conn = {}
        return self._open_instances.conn

    def make_serializable(self):
        data = super().make_serializable()
        if self.default_tunnel:
            data['default_tunnel'] = self.default_tunnel
        return data

    def get_open_instance(self, name=None, instance_name=None, user=None, open_if_close=False, tunnel=None,
                          interface=None):
        """ retrieves an open connection identified by the name and instance """
        def raise_or_return_new():
            if not open_if_close:
                raise ConnectionInstanceOpenError('This connection name ({}) is not open. Open it first'.format(name))
            else:
                return self.open(name=name, instance_name=instance_name, user=user, tunnel=tunnel, interface=interface)

        if not self.open_instances and not open_if_close:
            raise ConnectionInstanceOpenError('There are no open connections')

        open_conn = None

        if name:
            if name in self.open_instances:
                open_conn = self.open_instances[name]
        else:
            open_instances = list(self.open_instances.values())
            if open_instances:
                open_conn = open_instances[0]

        if not open_conn:
            return raise_or_return_new()

        if not instance_name:
            # just get the first open instance
            if not user and not tunnel and not interface:
                instance_name = list(open_conn.keys())[0]
            else:
                instance_name = self._get_instance_name_and_check_exists_for_user(self.DEFAULT_INSTANCE_NAME,
                                                                                  open_conn, user)

        elif instance_name not in open_conn:
            instance_name = self._get_instance_name_and_check_exists_for_user(instance_name, open_conn, user)

        return OpenConnectionInstanceUser(open_conn[instance_name])

    get_open_instance_or_new = functools.partialmethod(get_open_instance, open_if_close=True)

    def _get_instance_name_and_check_exists_for_user(self, instance_name, open_conn, username):
        instance_name_with_user = self._get_instance_name_augmented(instance_name,
                                                                    user_or_username=username)
        if instance_name_with_user not in open_conn:
            if username is not None and username not in self.users:
                raise UnknownUserError('Unknown user: ' + username)
            else:
                raise ConnectionInstanceOpenError('This instance name ({}) is not open'.format(instance_name))
        else:
            instance_name = instance_name_with_user
        return instance_name

    def _get_connection_instance_lock(self, conn_name, instance_name):
        """ creates a thread lock for every tuple conn_name instance_name """
        with self.manager_lock:
            if not (conn_name, instance_name) in self._conn_locks:
                self._conn_locks[(conn_name, instance_name)] = threading.Lock()
            return self._conn_locks[(conn_name, instance_name)]
                                      
    def _delete_open_connection_instance(self, name, instance):
        """ delete open connection instance and if there are no more open instances for a connection it removes
            the reference key from the open_instances dictionary
        """
        with self._get_connection_instance_lock(name, instance):
            del self.open_instances[name][instance]
            if not self.open_instances[name]:
                del self.open_instances[name]

    def _get_instance_name_augmented(self, instance_name, user_or_username=None, tunnel=None, interface=None):
        if not user_or_username:
            user_or_username = self.users.default

        tunnel_name = tunnel or self.tunnels.default.name if self.tunnels.items() else 'default'
        interface_name = interface or self.interfaces.default.name if self.interfaces.items() else 'default'

        username = user_or_username.username if isinstance(user_or_username, UserInfo) else user_or_username

        return '$$'.join((instance_name, username, tunnel_name, interface_name))

    def _add_multiple(self, item_type, func, default_name=None, default_tunnel=None, **items):
        if default_tunnel:
            self.default_tunnel = default_tunnel
        return super()._add_multiple(item_type, func, default_name=default_name, **items)

    def _check_instance_name_not_taken_and_open(self, conn_name, instance_name, user, tunnel, interface):

        instance_name = self._get_instance_name_augmented(instance_name, user, tunnel, interface)

        if (instance_name in self.open_instances.get(conn_name, ()) and
                self.open_instances[conn_name][instance_name].is_open):
            raise DuplicatedConnectionError(
                'This connection {} is already open on instance {}.'
                ''.format(conn_name, instance_name))
        return instance_name

    def _open(self, user, name, instance_name, conn_kwargs, tunnel, interface):
        """ creates a new connection session and opens it. it will open the default connection if name is not given
            this is used by the OpenConnectionInstance to do the opening of the connection

        Args:
            name (str):
            user:
            instance_name: name for instance of connection
            tunnel:
        :return:
        """

        with self._get_connection_instance_lock(name, instance_name):

            conn, user, instance_name = self._items[name].new_open_instance(user, instance_name, tunnel, interface,
                                                                            **conn_kwargs)

            return conn, name, user, instance_name

    def get_all_conversations(self):
        return {c: self._items[c].conversations() for c in self._items}

    def get_all_conversations_flat(self, conn_names=()):
        return {c: self._items[c].conversations_flat()
                for c in self._items if not conn_names or c in conn_names}

    def get_all_conversations_flat_default(self):
        return self.get_all_conversations_flat(self._default_item_name)

    def open(self, name=None, user=None, instance_name=None, tunnel=None, interface=None, **conn_args):
        """ Opens a connection instance given by name of the connection and an instance name
            in case we have more than one instance of the same name """

        name = name or self._default_item_name
        instance_name = instance_name or self.DEFAULT_INSTANCE_NAME

        open_instance = OpenConnectionInstance(self, name, instance_name, user, tunnel, interface, **conn_args)

        if open_instance.conn_name not in self.open_instances:
            self.open_instances[open_instance.conn_name] = {}

        self.open_instances[open_instance.conn_name][open_instance.instance_name] = open_instance

        log.debug('Connection {} with instance name {} and user {} was open successfully'
                  ''.format(open_instance.conn_name, instance_name, user))

        return open_instance

    def open_from_terminal(self):
        pass

    def close(self, name=None, instance_name=None, user=None, interface=None, tunnel=None):
        name = name or self._default_item_name
        username = self[name].user.username if self[name].user else user
        instance_name = self._get_instance_name_augmented(instance_name or self.DEFAULT_INSTANCE_NAME,
                                                          username, tunnel=tunnel, interface=interface)

        try:
            self.open_instances[name][instance_name].close()
        except KeyError as e:
            msg = 'Cannot close unknown connection name "{}" with instance "{}"'.format(name, instance_name)
            log.exception(msg)
            raise UnknownConnectionError(msg) from e

    def _add_instance_method(self, name, info):
            # to not destroy original value

            if not isinstance(info, collections.MutableMapping):
                raise TypeError('You can only provide a dict like type as connection info and you provided: ' +
                                str(type(info)))

            info = dict(info)  # local copy to avoid destroying
            proto = info.pop('proto', None)
            if not proto:
                try:
                    proto = next(p for p in sorted(KNOWN_CONNECTION_PROTOCOLS, key=lambda x: len(x), reverse=True)
                                 if p in name)
                except StopIteration:
                    raise ConnectionError("No proto provided in connection info. You could also provide the proto "
                                          "implicitly by naming the connection info with the proto embedded like "
                                          "my_conn_ssh or my_conn_telnet or my_conn_ssh_cmd")

            return (proto, name), info, name

    def add(self, proto, name, set_as_default=False, user=None, **conn_arguments):
        """

        Args:
            conn_cls (remotelogin.connections.base.Connection): class of the connection any of the ones defined in
                                                              KNOWN_CONNECTION_PROTOCOLS
            name (str):  name given for the connection, and the way to open it
            set_as_default (bool): flag to indicate that we want to set this connection as the default
            user (str): name of user to use for this connection if no username is provided when opening
            **conn_arguments: arguments to pass when we open this type of connection.
                              The arguments will be augmented if needed with the device information,
                              also if there is user information here, we will create a user in the device if it does not
                              exists already

        Returns:

        """

        if name in self._items:
            raise DuplicatedConnectionError("This connection (name: {}) has already been added... "
                                            "Please use a different one".format(name))

        # if 'host' not in conn_arguments:
        #     conn_arguments['host'] = self._dev.default_ip_address

        conn_arguments.pop('proto', None)

        # set the connection as default if it is the first one, or if the flag is given

        is_default = set_as_default or len(self._items) == 0

        conn_arguments.setdefault('os', self._dev.os)

        self._items[name] = ConnectionInfo(proto, name, self, user, **conn_arguments)

        if is_default:
            self._default_item_name = name

    add_telnet = partialmethod(add, 'telnet')
    add_ssh = partialmethod(add, 'ssh')
    add_cmd = partialmethod(add, 'command')
    #TODO: add_local

    def close_all(self):
        for conn_open_instances in self.open_instances.values():
            for conn in conn_open_instances.values():
                try:
                    conn.close_on_manager_del()
                except Exception:
                    if log:
                        log.exception("Problems closing connection {} on device {}"
                                      "".format(conn.identifier, self._dev.hostname))

    def __getattr__(self, item):
        """ defaults to forward any action to the default open connection. If no connection is open it will raise a
            ConnectionInstanceOpenError
        """
        try:
            return getattr(self.get_open_instance(), item)
        except ConnectionInstanceOpenError:
            if item == 'is_open':
                return False
            elif item == 'dbsession':
                raise NoDBSessionError
            else:
                raise

ConnectionsManager.add_connections = ConnectionsManager.add_all
