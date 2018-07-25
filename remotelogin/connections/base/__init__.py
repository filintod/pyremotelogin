import logging
import threading

from .. import settings, decorators
from .data import DataExchange

log = logging.getLogger(__name__)


class Connection:
    """ Template class that defines common attributes and methods to work with Network Protocol Connections to Network Services.
        A connection is defined as ip address, port, username and password, and its capabilities. Subclasses will define the methods

    """

    # The default connection command is what one would usually type to connect using this connection
    # this is use when doing multilevel connections to open the next connection
    NEEDS_AUTHENTICATION = False
    AUTHENTICATION_KEYS = ()
    ARGUMENTS_ALLOWED = 'buffer_size', 'connect_timeout'
    NON_BLOCKING_JOIN_TIMEOUT = settings.NON_BLOCKING_JOIN_TIMEOUT       # 5 seconds

    def __init__(self, timeout=0, connect_timeout=0, unbuffered_stream=False, remove_empty_on_stream=False):

        # session information
        self._timeout = timeout or settings.SOCKET_TIMEOUT
        self.connect_timeout = connect_timeout or settings.SOCKET_TIMEOUT_FOR_LOGIN
        self.data = None
        self.buffer_size = settings.BUFFER_SIZE

        self._transport = None
        self._is_open = False
        self._unbuffered = unbuffered_stream
        self._remove_empty_on_stream = remove_empty_on_stream

        # threading locks/events
        self.lock = None
        self.stop_signal = None

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not(self.__eq__(other))

    @property
    def is_open(self):
        return self._is_open

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout

    def _base_repr(self):
        """ creates a dictionary with the parameters needed to create the class

        The key will be the attribute name and the value will be a tuple (attribute value, is attribute string)

        """
        return {('timeout', False), ('new_line', True), ('connect_timeout', False)}

    def __base_repr_generator(self, base_repr):
        for k, is_str in base_repr:
            if isinstance(is_str, str):
                yield (k, is_str, True)
            yield (k, getattr(self, k), is_str)

    def _base_repr_to_kwargs(self, base_repr=None):
        if base_repr is None:
            base_repr = self._base_repr()
        return dict([(k,v) for (k, v, _) in self.__base_repr_generator(base_repr)])

    def _base_repr_to_string(self, base_repr):
        """ converts a dictionary created with _base_repr and returns a string that can be use in the __repr__ method"""
        s = []
        for k, v, is_str in self.__base_repr_generator(base_repr):
            v = str(v)
            s.append(k + '=' + (('"' + v + '"') if is_str else v))
        return ', '.join(s)

    def copy(self):
        import copy
        return copy.deepcopy(self)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self._base_repr_to_string(self._base_repr()))

    def open(self, **kwargs):
        """ you need to open the connection first before using it in a context statement

        Args:
            **kwargs:

        Returns:

        """

        if self.is_open:
            log.debug('Connection {} Already Opened: '.format(self))
        else:
            self.__init_open_connection__(kwargs.pop('unbuffered', self._unbuffered), self._remove_empty_on_stream)
            self._open_transport(**kwargs)
            self._is_open = True

        return self

    def __init_open_connection__(self, unbuffered, remove_empty_on_stream):
        self.lock = threading.Lock()
        self.stop_signal = threading.Event()
        self.data = DataExchange(unbuffered, remove_empty_on_stream)

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.close()
        except:
            pass

    def close(self):
        if getattr(self, 'lock', None):
            with self.lock:
                if self._is_open:
                    self._is_open = False
                    if self._transport:
                        try:
                            self._close_transport()
                        except:
                            log.exception("Problems closing: " + str(self))

                    self._transport = None

    __del__ = close

    # ####################      ABSTRACT METHODS        ##########################################

    def _open_transport(self, **kwargs):
        """ the actual open of the instance required by every type of connection

        Args:
            **kwargs:

        Returns:

        """
        raise NotImplementedError

    def _close_transport(self):
        """ Close real instance (paramiko, TELNET or cmd)
        """
        self._transport.close()

    @decorators.must_be_close
    def through(self, conn):
        from .. import terminal
        if isinstance(conn, terminal.TerminalConnection):
            t = terminal.TerminalConnection(self)
            t.through(conn)
            return t
        else:
            return terminal.TerminalConnection(conn, self)
