import contextlib
import functools
import inspect
import logging

from remotelogin.devices.exceptions import ConnectionInstanceOpenError
from fdutils import lists

log = logging.getLogger(__name__)


@contextlib.contextmanager
def device_connection(device, f, kwargs):
    """ decorator that retrieves the conn from the kwargs or
        opens a new instance if no connection was present
    """
    try:
        conn = kwargs.pop('conn', None) or device.conn.get_open_instance()
        close_after = False

    except ConnectionInstanceOpenError:
        conn = device.conn.open()
        close_after = True

    try:
        if __has_conn_or_kwargs(f):
            kwargs['conn'] = conn
        yield conn

    finally:
        if close_after:
            conn.close()


def __has_conn_or_kwargs(f):
    s = inspect.signature(f)
    if 'conn' in s.parameters:
        return True
    return any([p for p, v in s.parameters.items() if v.kind==inspect.Parameter.VAR_KEYWORD])


def with_connection(f):
    """ decorator that retrieves the conn from the kwargs or
        opens a new instance if no connection was present
    """
    @functools.wraps(f)
    def deco(self, *args, **kwargs):
        with device_connection(self, f, kwargs):
            return f(self, *args, **kwargs)
    return deco


def cmd(f):
    """ runs a set of commands given by the list return by the decorated function"""
    @functools.wraps(f)
    def deco(self, *args, **kwargs):
        with device_connection(self, f, kwargs) as conn:
            cmds = lists.to_sequence(f(self, *args, **kwargs))
            log.debug('Terminal: Sending command {}'.format(cmds))
            for cmd in cmds:
                conn.send_cmd(cmd)
    return deco


def get_cmd(f):
    """ runs a command given by a string

    Args:
        f:

    Returns:

    """
    @functools.wraps(f)
    def deco(self, *args, **kwargs):
        with device_connection(self, f, kwargs) as conn:
            cmds = f(self, *args, **kwargs)
            log.debug('Terminal: Sending command {}'.format(cmds))
            return conn.check_output(cmds)
    return deco