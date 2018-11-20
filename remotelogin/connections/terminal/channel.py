import logging

from ..base import term
from ..terminal.shells import ShellLoginInformation
from .. import settings

log = logging.getLogger(__name__)


class TerminalShell:
    def __init__(self, conn, **shell_kwargs):
        if hasattr(conn, "username"):
            shell_kwargs.setdefault(
                "ask_response_list",
                term.get_ask_resp_list_for_new_connection(
                    conn.username, conn.password, conn.expected_prompt
                ),
            )
        shell_kwargs.setdefault("expected_prompt", conn.expected_prompt)
        shell_kwargs.setdefault("skip_prompt_check", conn.skip_prompt_check)
        self.shell = ShellLoginInformation(**shell_kwargs)
        self.shell.update_from_conn(conn)
        self.os = conn.os


class TerminalChannel(TerminalShell):
    """ channel created by the ConnectionWithTerminal open_terminal method. it will contain connection, channel, and shell information

    """

    def __init__(self, conn, channel, **shell_kwargs):
        """

        Args:
            channel: channel created by the connection
            conn: connection that created this object
            **shell_kwargs:

        Returns:

        """
        super(TerminalChannel, self).__init__(conn, **shell_kwargs)
        self.channel = channel  # implemented connection link
        self.conn = conn
        self._resize_pty(cols=self.shell.cols, rows=self.shell.rows)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def send(self, data):
        raise NotImplementedError

    def recv(self, buffer_size=settings.BUFFER_SIZE):
        """ non-blocking receive method

        Args:
            buffer_size:

        Returns:

        """
        raise NotImplementedError

    def resize_pty(self, cols=0, rows=0):
        self._resize_pty(cols=(cols or self.shell.cols), rows=(rows or self.shell.rows))

    def _resize_pty(self, **kwargs):
        raise NotImplementedError

    @property
    def timeout(self):
        return self.channel.timeout

    @timeout.setter
    def timeout(self, timeout):
        self.channel.timeout = timeout

    def set_keepalive(self, interval=settings.SOCKET_KEEPALIVE_PERIOD):
        raise NotImplementedError

    def set_prompt(self, new_prompt):
        self.shell.expected_prompt = new_prompt
        self.send(self.os.cmd.set_prompt(self.os.get_unique_prompt()))

    def is_active(self):
        raise NotImplementedError

    def close(self):
        try:
            self._close()
        except Exception:
            log.exception("problems closing channel self._close method")
        try:
            self.conn.close()
        except Exception:
            log.exception("problems closing channel connection")

    def _close(self):
        pass
