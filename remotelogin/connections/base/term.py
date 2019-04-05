import logging
import abc
import re

from remotelogin.oper_sys.base import OSBase
from . import Connection, ip
from .. import exceptions, settings
import fdutils
from remotelogin import oper_sys

log = logging.getLogger(__name__)


def _parse_count(count):
    start_end = count.split(',')

    if len(start_end) > 1:
        start = int(start_end[0])
        end = int(start_end[1])

    else:
        start = start_end[0].strip()
        if start.endswith('+'):
            end = None
            start = int(start[:-1])
        else:
            end = int(start)
            start = 1

    return start, end


DEFAULT_PROMPT_NAME = 'prompt'
DEFAULT_PROMPT_EXPECT = None
DEFAULT_PROMPT_RESPONSE = None


class ExpectAndResponse:
    def __init__(self, expect, response, required=False, hidden=False, name='', flags=re.I|re.M, index=0, count=1,
                 require=False, **kwargs):
        """

        Args:
            expect: a regular expression value
            response: a string to respond
            required: whether this expect is required
            hidden: whether we should send the response as hidden value (for passwords)
            name: a name so we can identify this expect
            flags: regular expression flags
            index: the index where we want it to appear
            count: 0 -> zero or more, 'No+' from No to infinite, 'No, Nf' No to Nf, N explicit N times
            require: alias for required in case of typos
        """

        self.expect = expect
        self.response = response
        self.required = required or require
        self.hidden = hidden
        self.name = name
        self.flags = flags
        self.index = index
        self._count = '0'  # count definition
        self._start = self._end = None
        self.count = str(count)
        self.kwargs = kwargs
        self._matches = 0   # current count

    @property
    def count(self):
        return self._count

    @count.setter
    def count(self, v):
        self._count = v
        self._start, self._end = _parse_count(v)

    def clone(self):
        import copy
        return copy.copy(self)

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get(self, item, default=None):
        try:
            return getattr(self, item)
        except AttributeError:
            if default:
                return default
            raise

    def reinit_matches(self):
        self._matches = 0

    def match_found(self):
        self._matches += 1
        return self.are_matches_enough(), self.continue_checking()

    def are_matches_enough(self):
        """ checks whether the count value is enough to say that we are satisfied with attribute count
        """
        return self._start == 0 and self._end == 0 or \
               self._start >= self._matches and (self._end is None or self._matches >= self._end)

    def continue_checking(self):
        """ checks whether the count value is enough to say that we are satisfied with attribute count
        """
        return not (self._start >= self._matches and self._end is not None and self._matches >= self._end)

    @classmethod
    def from_dict(cls, **data):
        expect = data.pop('expect', data.pop('e', None))

        if expect is None:  # this is a prompt expectation
            name = data.pop('name', DEFAULT_PROMPT_NAME)
            return cls(DEFAULT_PROMPT_EXPECT, DEFAULT_PROMPT_RESPONSE, name=name, required=True)

        response = data.pop('response', data.pop('r', None))
        if response is None:
            raise ValueError('response attribute should be provided in expect and response list')
        return cls(expect, response, **data)


class ExpectPasswordAndResponse(ExpectAndResponse):
    def __init__(self, response, expect=r'(password)\s?\:', hidden=True, required=True, name='password'):
        super().__init__(expect, response, required=required, hidden=hidden, name=name)


class ExpectUsernameAndResponse(ExpectAndResponse):
    def __init__(self, response, expect=r'(username|login)\s?\:\s*$', hidden=False, required=False, name='username'):
        super().__init__(expect, response, required=required, hidden=hidden, name=name)


class ExpectPrompt(ExpectAndResponse):
    def __init__(self, expect=None, required=True, name=DEFAULT_PROMPT_NAME):
        super().__init__(expect, None, required=required, name=name)


def get_ask_resp_list_for_new_connection(username='', password='', prompt=None):

    resp_list = [ExpectPrompt(prompt, required=bool(prompt))]

    if username:
        resp_list.append(ExpectUsernameAndResponse(username))
    if password:
        resp_list.append(ExpectPasswordAndResponse(password))

    return resp_list


class ConnectionWithTerminal(Connection, abc.ABC):
    ARGUMENTS_ALLOWED = Connection.ARGUMENTS_ALLOWED + ('os', 'new_line', 'expected_prompt', 'timeout_for_prompt',
                                                        'skip_prompt_check') + OSBase.OS_KWARGS
    AUTHENTICATION_KEYS = Connection.AUTHENTICATION_KEYS
    CHECK_ECHO = False

    @abc.abstractmethod
    def _open_transport(self, **kwargs):
        raise NotImplementedError

    def __init__(self, os='linux', new_line='\n', expected_prompt=None, timeout_for_prompt=0,
                 skip_prompt_check=False, **kwargs):

        if not isinstance(os, OSBase):
            os_kwargs, kwargs = OSBase.pop_os_properties_from_kwargs(**kwargs)
            os = oper_sys.os_factory(os, **os_kwargs)

        self.os = os
        self.new_line = new_line
        self.expected_prompt = expected_prompt or os.expected_prompt
        self.timeout_for_prompt = timeout_for_prompt or settings.TIMEOUT_FOR_PROMPT
        self.skip_prompt_check = skip_prompt_check
        super(ConnectionWithTerminal, self).__init__(**kwargs)

    def _base_repr(self):
        base_set = super(ConnectionWithTerminal, self)._base_repr()
        specific = {('os', False), ('expected_prompt', True), ('timeout_for_prompt', True)}
        return base_set | specific

    @property
    def can_change_prompt(self):
        return self.os.can_change_prompt

    def open_terminal(self, **kwargs):
        from .. import terminal
        t = terminal.TerminalConnection(self, **kwargs)
        return t.open()

    def open_terminal_channel(self, **shell_kwargs):
        return self._open_terminal_channel(**shell_kwargs)

    @abc.abstractmethod
    def _open_terminal_channel(self, **kwargs):
        raise NotImplementedError

    def open_terminal_from_terminal(self, term_tunnel, **kwargs):
        """ in this case we are opening a terminal using a command like command from the original terminal instead
            of a direct connection and use our expect functions to manage the rest.

            Every connection type should implement the _get_shell_and_conn_string function where

        Args:
            term_tunnel:
            **kwargs:

        Returns:

        """
        kwargs.setdefault('connect_timeout', term_tunnel.connect_timeout)
        terminal_shell, conn_string = self._get_shell_and_conn_string(parent=term_tunnel, **kwargs)

        term_tunnel.send_cmd(conn_string, force_flush=True)
        if len(terminal_shell.shell.ask_response_list):

            match_set = term_tunnel.expect_ask_response_list(
                terminal_shell.shell.ask_response_list,
                timeout=self.connect_timeout,
                stop_after_getting='prompt',
                timeout_after_first_match=min(self.connect_timeout, settings.SOCKET_TIMEOUT_FOR_LOGIN),
                remove_prompt_to_compare=False
            )

            if terminal_shell.shell.expected_prompt and 'prompt' not in match_set:
                raise exceptions.ExpectLoginError('we got into a loop of the system askings and we keep responding')

        return terminal_shell

    @abc.abstractmethod
    def _get_shell_and_conn_string(self, **wargs):
        """ creates a terminal and a connection string needed to connect using the connection protocol """
        raise NotImplementedError


class IPConnectionWithTerminal(ConnectionWithTerminal, ip.IPConnection):

    def _get_shell_and_conn_string(self, **wargs):
        raise NotImplementedError

    def _open_transport(self, **kwargs):
        raise NotImplementedError

    def _open_terminal_channel(self, **kwargs):
        raise NotImplementedError

    ARGUMENTS_ALLOWED = tuple(set(ConnectionWithTerminal.ARGUMENTS_ALLOWED) |
                              set(ip.IPConnection.ARGUMENTS_ALLOWED))
    AUTHENTICATION_KEYS = tuple(set(ConnectionWithTerminal.AUTHENTICATION_KEYS) |
                                       set(ip.IPConnection.AUTHENTICATION_KEYS))

    def __init__(self, **kwargs):
        kwargs.setdefault('expected_prompt', None)
        if kwargs['expected_prompt'] and \
                fdutils.strings.is_fieldname_in_formatted_string(kwargs['expected_prompt'], 'username'):

            kwargs['expected_prompt'] = kwargs['expected_prompt'].format(username=kwargs.get('username', ''))
        super(IPConnectionWithTerminal, self).__init__(**kwargs)
