from functools import wraps
import logging

from . import exceptions
from fdutils import lists

log = logging.getLogger(__name__)

__author__ = 'Filinto Duran (duranto@gmail.com)'


def must_be_open(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not args[0].is_open:
            raise exceptions.ConnectionNotOpenError('Cannot execute a command without opening connection first')
        return f(*args, **kwargs)
    return wrap


def must_be_close(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if args[0].is_open:
            raise exceptions.ConnectionOpenError('Cannot execute this command while the connection is still open.')
        return f(*args, **kwargs)
    return wrap


# TODO: refactor to take into account 'conn' not as a kwarg but as an arg using getcallargs
def _open_conn_on_function(func, conn_name, use_shell, *args, **kwargs):
    """ opens connection on device as long as we don't already receive a connection (regular or interactive) given by the arguments conn

    :param func:
    :param conn_name:
    :param use_shell:
    :param args:
    :param kwargs:
    :return: the arguments object to use on the function with the conn kwarg with the open connection
    :rtype: dict
    """
    func, args, kwargs = func.reformat_args_to_signature(func, *args, **kwargs)
    prev_conn = kwargs.pop('conn', None)
    device = args[0]

    if prev_conn is None:
        # we are not given any previous connection. So we are going to either use
        # the connection whose name was given to the decorator (ie WithConnectin(my_connection_name) or
        # use the default connection of the device

        if not hasattr(device, 'default_connection'):
            # this is not a device quite probably a service
            device = device.device_assigned_to

        # augment kwargs with the connection already open
        conn = device.open_default_connection() if conn_name is None else device.open_connection(conn_name)

        from .terminal import TerminalConnection
        if use_shell and not isinstance(conn, TerminalConnection):
            # we want to use the shell so start an interactive session
            kwargs['conn'] = TerminalConnection(conn).open()
        else:
            kwargs['conn'] = conn
        is_conn_new = True

    else:
        # we were given a previous connection so let's use it instead of opening a new one
        # first let's check that if we were given a connection name on the decorator that the
        # connection we are using has the same name as this is a restriction
        if conn_name and prev_conn.base_name and prev_conn.base_name != conn_name:
            log.error('This connection name required ({}) does not match the connection that was sent to be used ({})'.format(
                conn_name, prev_conn.name))
            raise ConnectionError('Wrong connection provided')
        elif not prev_conn.is_open:
            # open the connection if for some reason we re given a connection that is not open
            prev_conn.open()

        if use_shell:
            from .terminal import shells
            from .terminal import TerminalConnection

            if not isinstance(prev_conn, TerminalConnection):
                if isinstance(prev_conn, shells.ShellLoginInformation):
                    prev_conn = TerminalConnection(prev_conn, close_base_on_exit=False).open()
                else:
                    raise ValueError('The connection provided ({}) cannot be '
                                     'used as a terminal connection'.format(prev_conn.__class__.__name__))

        kwargs['conn'] = prev_conn
        is_conn_new = False

    return func, args, kwargs, is_conn_new


class WithConnection:
    """ decorator class to open a connection in a device in case a connection is not given

    """
    def __init__(self, conn_name=None, conn_requirement=None, use_terminal=False, observers=None):
        """

        :param conn_name: name of the connection to be use taken from one of the connections added to the device. If Not set then we will use the default connection
        :param conn_requirement: any required capability
        :param use_terminal: flag to indicate that we want to use the shell with the connection.
        :param observers: this is an instance of ObservableEvents in case we want to trigger some actions before connecting,
                          after login (before function execution) and after closing connection

        """
        self.requirements = lists.to_sequence(conn_requirement, set)
        self.conn_name = conn_name
        self.use_terminal = use_terminal

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            raw_func, args, kwargs, is_conn_new = _open_conn_on_function(func, self.conn_name,
                                                                         self.use_terminal, *args, **kwargs)

            if is_conn_new:
                try:
                    f = raw_func(*args, **kwargs)
                finally:
                    kwargs['conn'].close()
            else:
                f = raw_func(*args, **kwargs)
            return f

        return wrapper


class WithInteractiveConnection(WithConnection):
    def __init__(self, *args, **kwargs):
        kwargs.pop('use_shell', None)
        kwargs['use_shell'] = True
        super(WithInteractiveConnection, self).__init__(*args, **kwargs)
