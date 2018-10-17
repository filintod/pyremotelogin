import logging
import re
import struct
import telnetlib

from remotelogin.connections import constants

from fdutils.decorators import retry
from fdutils import net
from . import settings
from .terminal import channel, terminal_connection_wrapper
from .base import term


log = logging.getLogger(__name__)

__author__ = 'Filinto Duran (duranto@gmail.com)'


class TelnetConnectionUnwrapped(term.IPConnectionWithTerminal):
    """ wrapper around standard telnetlib library to make it behave like other remotelogin.connections

    """

    _IANA_SVC_NAME = 'telnet'
    CHECK_ECHO = True
    USERNAME_REQUIRED = False

    def __init__(self, host='', telnet_app='telnet', keep_alive_period=0, **kwargs):
        self._buffer = ''
        self.keep_alive_period = keep_alive_period or settings.SOCKET_KEEPALIVE_PERIOD
        kwargs.setdefault('connect_timeout', settings.SOCKET_TIMEOUT_FOR_LOGIN_TELNET)
        self.telnet_app = telnet_app or getattr(self.os, 'telnet_app', None)
        super(TelnetConnectionUnwrapped, self).__init__(host=host, **kwargs)

    def _is_active(self):
        try:
            self._transport.sock.sendall(telnetlib.IAC + telnetlib.NOP)
            return True
        except Exception:
            pass
        self.close()
        return False

    def open_terminal(self, **kwargs):
        return self.open(**kwargs)

    def _open_transport(self, **kwargs):
        try:
            port = int(kwargs.pop('port', self.port))
            timeout = float(kwargs.pop('timeout', self.timeout))
            client = telnetlib.Telnet(self.host, port, timeout=timeout)
        except Exception:
            raise ConnectionError

        client.sock_avail()

        if not client:
            raise ConnectionError

        self.set_keepalive(self.keep_alive_period, transport=client)

        if self.username:
            self._get_login_prompt(client)

        if self.password:
            m = client.expect([re.compile(br"password:\s*", flags=re.I)], self.connect_timeout)
            if m[1]:
                client.write((self.password + "\n").encode('ascii'))
            else:
                raise ConnectionError('could not connect did not find the Password prompt')

        self._transport = client
        self._is_open = True

        return self

    @retry(2, 5)
    def _get_login_prompt(self, client):
        m = client.expect([re.compile(br'(username|login)(\s\w*)*:', flags=re.I)],
                          self.connect_timeout)
        if m[1]:
            client.write((self.username + "\n").encode('ascii'))
        else:
            raise ConnectionError('could not connect as did not find expected username or login prompt pattern')

    def set_keepalive(self, interval=settings.SOCKET_KEEPALIVE_PERIOD, transport=None):
        transport = transport or self._transport
        net.set_socket_keepalive(transport.sock, interval)

    def _get_shell_and_conn_string(self, parent=None, **kwargs):
        shell = channel.TerminalShell(self, **kwargs)

        conn_string = 'telnet {host} {port}'.format(host=self.host, port=self.port)

        return shell, conn_string

    def _open_terminal_channel(self, **kwargs):
        return TelnetTerminalChannel(self, self, **kwargs)


def TelnetConnection(host='', **kwargs):
    return terminal_connection_wrapper(TelnetConnectionUnwrapped, host, **kwargs)


class TelnetTerminalChannel(channel.TerminalChannel):

    def send(self, data):
        self.channel._transport.write(data.encode(encoding=settings.ENCODE_ENCODING_TYPE,
                                                  errors=settings.ENCODE_ERROR_ARGUMENT_VALUE))

    def set_keepalive(self, interval=0):
        self.channel.set_keepalive(interval or settings.SOCKET_KEEPALIVE_PERIOD)

    def is_active(self):
        self.channel.is_active()

    @channel.TerminalChannel.timeout.setter
    def timeout(self, timeout):
        self.channel._transport.sock.settimeout(timeout)
        self.channel._timeout = timeout

    def recv(self, buffer_size=0):
        # telnet reads until new line or timeout reading
        try:
            data = self.channel._transport.read_until(b'\n', settings.TELNET_TIMEOUT_RECV)\
                .decode(encoding=settings.DECODE_ENCODING_TYPE, errors=settings.DECODE_ERROR_ARGUMENT_VALUE)
            return data if data else constants.SOCKET_RECV_NOT_READY
        except EOFError:
            return 0

    def _resize_pty(self, cols=settings.SHELL_COLS, rows=settings.SHELL_ROWS):
        # set the pty width and height
        naws_command = struct.pack('!BBBHHBB',
                                   255, 250, 31,    # IAC SB NAWS
                                   cols, rows,
                                   255, 240)        # IAC SE
        self.channel._transport.sock.sendall(naws_command)


