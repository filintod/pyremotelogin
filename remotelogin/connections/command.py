import logging

from remotelogin.connections.base import mixins

from fdutils.strings import is_fieldname_in_formatted_string

from .terminal import channel
from .base import term


log = logging.getLogger(__name__)

__author__ = 'Filinto Duran (duranto@gmail.com)'


class CommandConnection(term.ConnectionWithTerminal, mixins.CanExecuteCommands,):
    """ connection that is purely text based like when doing telnet from an ssh session """

    ARGUMENTS_ALLOWED = term.ConnectionWithTerminal.ARGUMENTS_ALLOWED + ('cmd', 'username', 'password')

    def _open_terminal_channel(self, **kwargs):
        pass

    def __init__(self, cmd, **kwargs):
        self.cmd = cmd
        self.username = kwargs.pop('username', '')
        self.password = kwargs.pop('password', '')
        kwargs.setdefault('expected_prompt', None)
        if kwargs['expected_prompt'] and is_fieldname_in_formatted_string(kwargs['expected_prompt'], 'username'):
            kwargs['expected_prompt'] = kwargs['expected_prompt'].format(username=self.username)
        super(CommandConnection, self).__init__(**kwargs)

    def _open_transport(self, **kwargs):
        pass

    def _close_transport(self):
        self.send

    def _get_shell_and_conn_string(self, **kwargs):
        kwargs.pop('parent', None)
        shell = channel.TerminalShell(self, **kwargs)

        return shell, self.cmd
