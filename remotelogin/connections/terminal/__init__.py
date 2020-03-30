import contextlib

import collections
import functools
import inspect
import logging
import re
import socket
import time

import fdutils.timer
from remotelogin.connections.exceptions import ConnectionExpectTimeoutError
from remotelogin.connections.base import term, mixins

from remotelogin.connections import constants, decorators

from io import StringIO

from remotelogin.connections.terminal import shells, channel
from remotelogin.connections import settings, expect, exceptions, base
import fdutils

log = logging.getLogger(__name__)


__author__ = "Filinto Duran (duranto@gmail.com)"


PASSWORD_PROMPT_REGEX = r"(?i)password[^:]*:"
SUDO_PASSWORD_PROMPT_REGEX = r"(?i).*Password[^:]*:\s*"


def _remove_cmd_from_buffer(
    buff, cmd_line_counter, cmd_lines, cmd_lines_num, cmd_removed
):
    """ helper function for _expect_cmd """
    for cmd_line in cmd_lines[cmd_line_counter:]:
        command_at = buff.find(cmd_line)
        if command_at != -1:
            cmd_line_counter += 1
            buff = buff[command_at + len(cmd_line) :]
            if cmd_line_counter == cmd_lines_num:
                cmd_removed = True

    return buff, cmd_removed


def _get_string_to_match(buff, _check_match):
    string_to_match = buff

    # we are limiting the comparison to sections between the reset_on_sep char value (like new line)
    nl_index = buff.find("\n")
    # if we find a separator string/char
    while nl_index != -1:
        string_to_match = buff[:nl_index]
        # buff is initialized with the section after the reset_on_sep char for comparison
        buff = buff[nl_index + 1 :]
        # compare against our expected values
        if _check_match(string_to_match):
            break

        nl_index = buff.find("\n")
    else:  # nobreak
        return string_to_match, buff, False

    return None, None, True


def expand_connections(connections):
    """ when the connections variable passed to TerminalConnection is a mix of items we flatten the list here """
    ret = []
    for conn in connections:
        if isinstance(conn, TerminalConnection):
            ret.extend(expand_connections(conn.connections))
        elif isinstance(conn, collections.Sequence):
            ret.extend(expand_connections(conn))
        else:
            ret.append(conn)
    return ret


def get_ask_resp_list_by_name(ask_response_list):

    no_names = []
    ask_resp_list_by_name = {}

    for i, ask_resp in enumerate(ask_response_list):
        if (
            isinstance(ask_resp, str)
            and ask_resp.lower().strip() == term.DEFAULT_PROMPT_NAME
        ):
            ask_resp_list_by_name[term.DEFAULT_PROMPT_NAME] = term.ExpectPrompt()
        else:
            ask_resp["index"] = i
            if ask_resp.get("name", None):
                ask_resp_list_by_name[str(ask_resp["name"])] = ask_resp
            else:
                no_names.append(i)

    if no_names:
        idx = no_names[0]
        while no_names:
            while str(idx) in ask_resp_list_by_name:
                idx += 1
            ask_resp_list_by_name[str(idx)] = ask_response_list[no_names[0]]
            no_names.pop(0)
            idx += 1

    return ask_resp_list_by_name


def create_expectedregex_objects(ask_response_list, kwargs, remove_prompt_to_compare):

    ask_resp_list_by_name = get_ask_resp_list_by_name(ask_response_list)

    expect_list = {}

    flags = kwargs.pop("flags", 0)
    for name, r in ask_resp_list_by_name.items():
        if isinstance(r, collections.MutableMapping):
            if r.get("name", None) is None:
                r["name"] = name
            r = term.ExpectAndResponse.from_dict(**r)
            ask_resp_list_by_name[name] = r

        else:
            r = r.clone()

        expect_list[name] = expect.ExpectedRegex(
            r.expect,
            name=name,
            flags=r.flags or flags,
            remove_prompt_to_compare=remove_prompt_to_compare,
        )

    return expect_list, ask_resp_list_by_name


# TODO: implement __str__ to show tunnel connections
# TODO: implement not allowing password unencrypted unless flag set to True
# TODO: check if base connection was open before we first try to open it so we don't close it at __exit__
# TODO: implement setting encoding/decoding type instead of using only settings values
# TODO: implement rtt attribute into delay
class TerminalConnection(
    base.Connection, mixins.CanExecuteCommands, mixins.CanTransferFiles
):
    """ utility class to handle interactive connections with expect-like functionality and login tracking """

    def __init__(
        self,
        *connections,
        close_base_on_exit=True,
        allow_non_expected_prompt=False,
        stderr_to_tmp=False,
        check_same_prompt_when_opening_terminal=True,
        data_stream=None,
        use_unique_prompt=True,
        rtt=0.5,
        enable_proxyjump=True,
        allow_passwords_unencrypted=False,
        chain_all_expects=False,
        encoding_type=None,
        encoding_errors=None,
        decoding_type=None,
        decoding_errors=None,
        unbuffered_stream=False,
        remove_empty_on_stream=False,
        **shell_kwargs
    ):
        """

        Args:
            base_conn (channel.TerminalChannel):
            close_base_on_exit (bool): flag to indicate that we want to close the base connection on __exit__ method
                                       set it to False if you want to keep the base open
            allow_non_expected_prompt:
            stderr_to_tmp:
            data_stream (IOBase or func): a data stream IO or a function to call when starting a connection
            use_unique_prompt (bool): flag to indicate that we want to set a unique prompt if available on the os
            enable_proxyjump (bool): flag to indicate that we should try to start the tunneled ssh connections using
                                     paramiko proxyjump functionality (only works on first SSH connections)
            allow_passwords_unencrypted (bool): flag to indicate that we want to allow sending passwords over
                                                unencrypted channels (like Telnet)
            decode_data_as_str (bool): flag to indicate that the data will be decoded to string
            encoding_type (str): the encoding type argument to use when encoding bytes
            encoding_errors (str): the encoding errors argument to use when encoding bytes
            decoding_type (str): the encoding type argument to use when decoding bytes
            decoding_errors (str): the encoding errors argument to use when decoding bytes
            chain_all_expects (bool): set all expect methods to return self instead of expect result object


        Returns:

        """
        self._start_connection_idx = 0
        connections = expand_connections(connections)

        self._terminals = []  # hackish - dummy shell object to get pass the super init
        self.__base_chan_kwargs = shell_kwargs
        super(TerminalConnection, self).__init__(
            unbuffered_stream=unbuffered_stream,
            remove_empty_on_stream=remove_empty_on_stream,
        )

        self.check_same_prompt_when_opening_terminal = (
            check_same_prompt_when_opening_terminal
        )
        self.connections = list(connections)
        self._close_base_on_exit = close_base_on_exit
        self.use_unique_prompt = use_unique_prompt

        self.stderr_to_tmp = stderr_to_tmp
        self.rtt = rtt
        self.allow_non_expected_prompt = allow_non_expected_prompt
        self.enable_proxyjump = enable_proxyjump
        if inspect.isfunction(data_stream):
            self._data_stream_func = data_stream
            data_stream = None
        else:
            self._data_stream_func = None
        self.data_stream = data_stream

        # last command sent
        self.last_cmd_sent = ""
        self._encoding_type = encoding_type or settings.ENCODE_ENCODING_TYPE
        self._encoding_errors = encoding_errors or settings.ENCODE_ERROR_ARGUMENT_VALUE
        self._decoding_type = decoding_type or settings.DECODE_ENCODING_TYPE
        self._decoding_errors = decoding_errors or settings.DECODE_ERROR_ARGUMENT_VALUE

        self._chain_all_expects = chain_all_expects

        self.sleep_time_after_no_data = settings.SOCKET_TIME_SLEEP_NO_DATA_SELECT
        self._last_cmd_was_hidden = False

        self.allow_password_unencrypted = allow_passwords_unencrypted

    def __repr__(self):
        base_conn = []

        for c in self.connections:
            base_conn.append(c.__repr__())

        return (
            "TerminalConnection({base_conn}, close_base_on_exit={close_on_exit}, "
            "allow_unknown_prompt={allow_prompt}, stderr_to_tmp={stderr}, enable_proxyjump={enable_proxyjump}, "
            "use_unique_prompt={use_unique_prompt}),"
            "allow_password_unencrypted={allow_password_unencrypted}"
            "".format(
                base_conn=base_conn,
                close_on_exit=self._close_base_on_exit,
                allow_prompt=self.allow_non_expected_prompt,
                stderr=self.stderr_to_tmp,
                use_unique_prompt=self.use_unique_prompt,
                enable_proxyjump=self.enable_proxyjump,
                allow_password_unencrypted=self.allow_password_unencrypted,
            )
        )

    def _open_transport(self, **kwargs):
        try:
            if not self.connections:
                raise ConnectionError(
                    "This terminal does not have any connection assigned"
                )
            conn_idx = self._open_base(kwargs)

            # multi level login
            for conn in self.connections[conn_idx:]:
                self.open_terminal_from_terminal(conn)

        except ConnectionError:
            self._close_transport()
            log.exception("problems connecting...")
            raise

        # override expected prompt if allowed
        if self.allow_non_expected_prompt:
            self.connections[
                self._start_connection_idx
            ].expected_prompt = self._terminals[0].shell.expected_prompt

    # TODO: add tunnel information to Starting Terminal Session message
    def _open_base(self, kwargs):
        idx = self._set_start_ssh_proxyjump_conn()
        self._start_connection_idx = idx
        if idx:
            self._start_connection_idx -= 1

        self.connections[self._start_connection_idx].open()
        kwargs = fdutils.lists.setdefault(kwargs, self.__base_chan_kwargs)
        self.transport = self.connections[
            self._start_connection_idx
        ].open_terminal_channel(**kwargs)
        self.transport.set_keepalive(settings.SOCKET_KEEPALIVE_PERIOD)
        if self._data_stream_func and not self.data_stream:
            self.data_stream = self._data_stream_func()

        self._setup_login_and_prompt(
            self.transport,
            "Starting Terminal Session with " + self.transport.conn.host,
        )
        return idx or 1

    def _set_start_ssh_proxyjump_conn(self):
        from ..ssh import SshConnection

        idx = 0
        if self.enable_proxyjump:
            while idx < len(self.connections) and isinstance(
                self.connections[idx], SshConnection
            ):
                idx += 1

            if idx:
                for i in range(idx - 1, 0, -1):
                    if not self.connections[i].proxy_jump:
                        self.connections[i].proxy_jump = self.connections[i - 1]
        return idx

    def open_terminal_from_terminal(self, conn, **kwargs):
        return self._setup_login_and_prompt(
            conn.open_terminal_from_terminal(self, **kwargs), msg="OPENING NEW TERMINAL"
        )

    # TODO: change the 400,80 hardcoded values to terminal shell or setting values
    # TODO: if can_change_prompt is set but we never got it to change but we had a expected prompt different to previous one
    #       and it change we should supposed that we did enter successfully or has a flag to allow it even if different
    def _setup_login_and_prompt(self, terminal, msg="STARTING CONNECTION"):
        self.data.new_sent(
            ">>> {} <<<\n".format(msg),
            data_stream=self.data_stream,
            send_msg_format=None,
            host=self.host
        )
        self.find_login_info(terminal)
        curr = self.current
        curr.shell.prompt_found = curr.shell.expected_prompt

        if curr.os.can_disable_history:
            self.send_cmd_prompt(curr.os.cmd.disable_history())

        if self.use_unique_prompt and curr.shell.can_change_prompt:
            self.set_prompt(new_prompt=self.os.get_unique_prompt())

        self.flush_recv()

        if curr.os.can_resize_pty:
            self.send_cmd(curr.os.cmd.resize_pty(curr.shell.cols, curr.shell.rows)).expect_prompt(
                chain=True
            ).flush_recv()

        return self

    def _close_transport(self):
        if not self.transport:
            return
        try:
            curr = self.current

            # send exit
            self.send_cmd(curr.os.cmd.exit())

            if (
                    self.use_unique_prompt
                    and isinstance(curr, channel.TerminalChannel)
                    and curr.shell.can_change_prompt
                    and curr.os.reset_prompt_on_exit
                    and curr.os.default_prompt
            ):
                try:
                    self.set_prompt(new_prompt=curr.os.default_prompt)
                except Exception:
                    log.exception(
                        "Problems resetting default prompt ({})".format(
                            curr.os.default_prompt
                        )
                    )
            self._terminals = []
            self.last_cmd_sent = ""

            if self.transport and self._close_base_on_exit:
                self.transport.close()

        except Exception:
            log.exception("problems closing terminal transport")

    # TODO: make a copy of conn to avoid overwriting conn info.... how deep???
    @decorators.must_be_close
    def through(self, conn):
        if isinstance(conn, TerminalConnection):
            self.connections = list(conn.connections) + self.connections
        else:
            self.connections.insert(0, conn)
        return self

    def _is_active(self):
        return self.is_open and self.transport.is_active()

    @property
    def os(self):
        return self.current.os

    @property
    def host(self):
        try:
            return self.transport.conn.host
        except AttributeError:
            log.warning("trying to get host from not opened terminal")
            return None

    @property
    def prompt(self):
        return self.current.shell.expected_prompt

    @prompt.setter
    def prompt(self, value):
        self.current.shell.expected_prompt = value

    @property
    def prompt_found(self):
        return self.current.shell.prompt_found

    # TODO: check if we can remove this property if we don't see any need to double new lines
    @property
    def new_line(self):
        try:
            return self.current.shell.new_line
        except Exception:
            return "\n"

    @new_line.setter
    def new_line(self, value):
        self.current.shell.new_line = value

    @property
    def current(self):
        """ current terminal channel (TerminalShell object) """
        try:
            if self._terminals:
                return self._terminals[-1]
            else:
                return self.connections[self._start_connection_idx]
        except Exception:
            return None

    @property
    def current_conn(self):
        return self.connections[-1]

    @property
    def username(self):
        return self.current.conn.username

    @property
    def password(self):
        return self.current.conn.password

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        self._timeout = self.current.shell.timeout = int(value)

    def recv(self, buffer_size=None):
        """ this will call the non-blocking receive on the transport,
            remove ansi codes if present, record the data to the data_stream
            and return the data received
        """
        data = self.transport.recv(buffer_size or self.buffer_size)
        if data:
            data = fdutils.regex.strip_ansi_codes_from_buffer(data)
            # data = MULTILINE_REDUCER.sub(data, r"\n")
            self.data.new_received(data)
        return data

    def recv_wait(self, wait_for, buffer_size=None):
        """ a receive with a timer to wait looping through recv and buffering the received data """
        data = ""
        t0 = time.time()
        while (time.time() - t0) < wait_for:
            d = self.recv(buffer_size)
            if d:
                data += d
        return data

    def _is_current_terminal_socket(self):
        return (
            len(self.connections) == 1 or len(self._terminals) == 1
        ) and not isinstance(self.current.conn, TerminalConnection)

    def get_file(self, *args, **kwargs):
        if self._is_current_terminal_socket():
            return self.current.conn.get_file(*args, **kwargs)
        else:
            return self.get_file_via_cat(*args, **kwargs)

    get = get_file

    def put_file(self, *args, **kwargs):
        if self._is_current_terminal_socket():
            return self.current.conn.put_file(*args, **kwargs)
        else:
            return self.put_file_via_cat(*args, **kwargs)

    put = put_file

    def get_response(self, timeout=0.05, force_ctrl_c=False):
        """

        Args:
            timeout: time to wait before forcing a ctrl-c to the previous action

        Returns:

        """
        return self.flush_recv(
            timeout=timeout, force_ctrl_c=force_ctrl_c
        ).data.get_last_recv()

    def __get_last_line_prompt(self, data_received_lines):
        last_line = data_received_lines.pop()
        # len_last_line_split = len(last_line.split())
        # if len_last_line_split >= 2:
        #     last_line = last_line.split(maxsplit=len_last_line_split - 1)[-1]
        return last_line

    def _get_banner_and_prompt(self, terminal, previous_prompt=None):
        """ Get information about a new login (message of the day and prompt).

        It cycles reading a socket until it times out to automatically retrieve the banner message (motd) and the prompt.
        If given the expected_prompt, we will only wait until we get expected_prompt or login_timeout whoever is first

        """

        # send a new line
        self.send_line(force_flush=True, flush_timeout=settings.FLUSH_RECV_TIMEOUT * 2)
        data_received, prompt_timer_expired, prompt_found = self._find_prompt(
            terminal, terminal.shell.expected_prompt
        )

        if not data_received:
            raise exceptions.ExpectLoginError(
                "Did not get any banner message or prompt???"
            )

        data_received_lines = data_received.splitlines()
        prompt = re.escape(
            (prompt_found or self.__get_last_line_prompt(data_received_lines)).rstrip(
                "\n"
            )
        )
        banner = data_received[: data_received.find(prompt) or len(data_received)]

        if (
            previous_prompt
            and prompt == previous_prompt
            and self.check_same_prompt_when_opening_terminal
            and (
                not terminal.shell.expected_prompt
                or terminal.shell.expected_prompt != prompt
            )
            and not terminal.shell.skip_prompt_check
            and (
                not len(self._terminals) or self._terminals[-1].shell.can_change_prompt
            )
        ):
            raise exceptions.ExpectLoginError(
                "The prompt is still the same ({}). "
                "We might have not logged into anywhere".format(previous_prompt)
            )

        elif (
            not self.allow_non_expected_prompt
            and terminal.shell.expected_prompt
            and prompt_timer_expired
        ):
            raise exceptions.ExpectLoginError(
                "The expected prompt {} is different to the one we got {} . "
                "We might be in the wrong place or the expected prompt is wrong"
                "".format(terminal.shell.expected_prompt, prompt)
            )
        else:
            if prompt_timer_expired and terminal.shell.expected_prompt:
                log.info(
                    "Prompt {} different to expected {} and . You might need to update it"
                    "".format(terminal.shell.expected_prompt, prompt)
                )

            return banner, prompt

    def _find_prompt(self, terminal, new_prompt=None, timeout=0):
        if new_prompt:
            if fdutils.regex.is_instance_of_regex(new_prompt):
                prompt_regex = new_prompt
            else:
                prompt_regex = re.compile(new_prompt, re.M | re.I)
        else:
            prompt_regex = None

        data_received = ""
        prompt_found = None
        timer_expired = True
        timeout = timeout or terminal.shell.timeout_for_prompt

        t0 = time.time()

        while True:
            data = self.recv()
            if data:
                data_received += data
                if prompt_regex:
                    m = prompt_regex.search(data_received)
                    if m:
                        prompt_found = m.group(0)
                        timer_expired = False
                        break
                    time.sleep(self.sleep_time_after_no_data)
                    continue

            elif (time.time() - t0) > timeout:
                break

            time.sleep(self.sleep_time_after_no_data)

        return data_received, timer_expired, prompt_found

    def set_prompt(self, new_prompt, timeout=0):

        if new_prompt == self.prompt:
            return True

        self.send_cmd(self.current.os.cmd.set_prompt(new_prompt))
        try:
            self.send_line().get_new_prompt(new_prompt=new_prompt, timeout=timeout)
        except ConnectionExpectTimeoutError:
            log.error(
                "Problems when trying to set the new prompt. Check if the OS can change prompt"
            )
            raise

        return self

    def set_unique_prompt(self, unique=None):
        self.set_prompt(new_prompt=(unique or self.os.get_unique_prompt()))

    def _check_output_nb(self, command, **kwargs):
        if self._is_current_terminal_socket():
            return self.current_conn._check_output_nb(command, **kwargs)
        else:
            raise NotImplementedError(
                "we have not implemented non blocking in terminal mode"
            )

    def check_output(
        self,
        command,
        use_sudo=False,
        stderr_to_tmp=False,
        stderr_to_out=False,
        recv_stream=None,
        return_stderr=False,
        **kwargs
    ):
        self.flush_recv()
        kwargs["reset_buffer"] = True
        command = self._get_cmd(command, use_sudo, stderr_to_tmp)
        send = self.send_with_stderr if stderr_to_out else self.send_cmd

        send(command, recv_stream=recv_stream)

        if use_sudo:
            password = kwargs.pop("password", self.current_conn.password)
            e = self.expect(
                expect.ExpectedRegex(SUDO_PASSWORD_PROMPT_REGEX, name="password"),
                expect.ExpectedPrompt(),
                **kwargs
            )
            if e.ok and e.index == 0:
                send(
                    password, recv_stream=recv_stream, is_hidden=True, title="Password"
                )
                e = self.expect_prompt(**kwargs)
        else:
            e = self.expect_prompt(**kwargs)

        if e.any_matched:
            log.debug("<<< Matched Received: \n" + e.string_before)
            result = e.string_before.strip("\n")
            if command != self.new_line:
                command_loc = result.find(command)
                if command_loc != -1:
                    result = result[command_loc + len(command) :].lstrip()
                else:
                    log.debug("<<< did not find command: \n" + command)

            return result

        raise exceptions.CalledProcessError(
            -1,
            command,
            "Did not find prompt ({}). "
            "This is the output we got: {}"
            "".format(self.prompt, self.data.get_last_recv()),
        )

    check_sudo_output = functools.partialmethod(check_output, use_sudo=True)

    send_recv = check_output

    def flush_recv(self, force_ctrl_c=True, timeout=settings.FLUSH_RECV_TIMEOUT):
        """ flushes the receive buffer
        Args:
            force_ctrl_c:  flag to indicate that if we timeout try sending a control c,
                           in case we have a long running task
            timeout: timeout to keep reading the buffer while data is present

        Returns:

        """
        t0 = time.time()
        flush_data = 1
        while flush_data:
            try:
                flush_data = self.recv()
                if (time.time() - t0) > timeout:
                    break
            except Exception:
                break

        remaining_time = timeout - (time.time() - t0)

        # if we have data and we timedout and force ctrl c is on, send ctrl-c and re-flush
        if remaining_time < 0 and flush_data and force_ctrl_c:
            self.send_ctrl_c()
            return self.flush_recv(False)

        elif remaining_time > 0:
            time.sleep(0.01)
            return self.flush_recv(False, timeout=remaining_time)

        return self

    def send_cmd(self, cmd, flush=True, force_flush=False, flush_timeout=settings.FLUSH_RECV_TIMEOUT, **send_kwargs):
        if flush and self.last_cmd_sent or force_flush:
            self.flush_recv(timeout=flush_timeout)
        return self.send(cmd, True, **send_kwargs)

    send_hidden_cmd = functools.partialmethod(send_cmd, is_hidden=True)

    def send_cmd_prompt(self, cmd, **send_kwargs):
        """ send a command and wait for prompt before continuing """
        timeout = send_kwargs.pop("timeout", 0)
        self.send_cmd(cmd, **send_kwargs).expect_prompt(timeout=timeout)
        return self

    send_cmd_ep = send_cmd_prompt

    @contextlib.contextmanager
    def send_cmd_new_prompt_context(
        self, cmd, expected_prompt=None, exit_cmd="exit", **send_kwargs
    ):
        """ send a command and wait for a new prompt before continuing and create a terminal in terminal context """
        curr_prompt = self.prompt
        self.send_cmd(cmd, **send_kwargs).expect_new_prompt(expected_prompt)
        try:
            yield
        finally:
            if exit_cmd:
                self.send("\n").send_cmd(exit_cmd)
            self.expect_new_prompt(curr_prompt)

    def get_conversation_list(self):
        return self.data.get_timed_conversation_list()

    def get_conversation_string(
        self, template="\n>>> Sent ({date}): >>{sent}<<\n\nReceived: {received}"
    ):
        return "\n".join(
            template.format(
                date=s["time"], sent=s["sent"].strip(), received=s["received"]
            )
            for s in self.data.get_timed_conversation_list()
        )

    def send_cmds(self, *cmds, time_between=0.1, flush=True, **send_kwargs):
        if flush and self.last_cmd_sent:
            self.flush_recv()
        for cmd in cmds:
            self.send(cmd, True, **send_kwargs)
            time.sleep(time_between)
        return self

    def send_sudo_cmd(
        self,
        cmd,
        password=None,
        password_regex=SUDO_PASSWORD_PROMPT_REGEX,
        continue_if_no_passwd=True,
        sudo_password_prompt_timeout=1,
        **send_kwargs
    ):
        try:
            self.send_cmd("sudo " + cmd, **send_kwargs).expect_regex(
                password_regex, timeout=sudo_password_prompt_timeout
            )

        except socket.timeout:
            if not continue_if_no_passwd:
                log.exception("did not find password and was required")
                raise
        else:
            self.send_hidden_cmd(password or self.current.conn.password, **send_kwargs)

        return self

    def send_sudo_cmd_prompt(self, cmd, **kwargs):
        """ This sends a sudo command and then expect for the same prompt, don't use it if creating a new context """
        self.send_sudo_cmd(cmd, **kwargs).expect_prompt()
        return self

    send_sudo_cmd_ep = send_sudo_cmd_prompt

    def send_confirmed_password(
        self,
        password=None,
        password_regex=PASSWORD_PROMPT_REGEX,
        is_hidden=True,
        timeout=2,
        **send_kwargs
    ):
        password = password or self.current.conn.password
        send_kwargs.setdefault("title", "Password")

        self.expect_regex(password_regex, timeout=timeout)
        self.send_cmd(password, is_hidden=is_hidden, **send_kwargs).expect_regex(
            password_regex, timeout=timeout
        )
        send_kwargs["title"] = "Confirmed Password"
        return self.send_cmd(
            password, is_hidden=is_hidden, **send_kwargs
        ).expect_prompt(chain=True)

    def send_ctrl_c(self):
        return self.send("\x03").send_line(False)

    def send_line(self, flush=True, **send_kwargs):
        return self.send_cmd("", flush, **send_kwargs)

    enter = send_line

    def send_with_stderr(self, cmd, flush=True, **send_kwargs):
        return self.send_cmd(cmd + " 2>&1", flush, **send_kwargs)

    def send(
        self,
        cmd,
        new_line=False,
        metadata=None,
        recv_stream=None,
        record=True,
        is_hidden=False,
        title="",
    ):
        cmd = str(cmd).strip()
        if new_line:
            # add new line to command if not given already
            if not cmd or cmd[-len(self.new_line)] != self.new_line:
                cmd += self.new_line

        self.transport.send(cmd)
        self.last_cmd_sent = cmd
        self.data.new_sent(
            cmd,
            metadata=metadata,
            data_stream=recv_stream or self.data_stream,
            record=record,
            hide=is_hidden,
            title=title,
            host=self.host
        )
        self._last_cmd_was_hidden = is_hidden
        return self

    send_hidden = functools.partialmethod(send, is_hidden=True)

    # TODO: be able to execute different callback per match
    def expect(
        self,
        *expect_value_list,
        flags=0,
        remove_prompt_to_compare=True,
        all_matches_required=False,
        all_matches_in_sequence=False,
        callback=None,
        multiple=False,
        store=None,
        **kwargs
    ):
        """ execute a expect on one or more patterns

        Args:
            *expect_value_list:
            flags (int): regular expression flags to apply to all regexes
            remove_prompt_to_compare (bool): in most cases we want to compare without the prompt,
                                             in some cases we want to check for the prompt (like when checking for prompt)
            all_matches_required (bool): whether accept the match only if all matches are found
            all_matches_in_sequence (bool): whether to accept a match when all matches appeared in order
            callback (function):
            multiple (bool):
            store (list): if not None we will append values for each expect
            **kwargs:

        Returns:
            expect.Expect

        """
        exp_object = expect.Expect(
            self.last_cmd_sent,
            all_matches_in_sequence=all_matches_in_sequence,
            all_matches_required=all_matches_required,
            continue_matching=multiple,
        )

        if callback and not callable(callback):
            raise ValueError("The call_back should be a function")

        for v in expect_value_list:
            if not isinstance(v, expect.ExpectedRegex):
                v = expect.ExpectedRegex(
                    v, flags=flags, remove_prompt_to_compare=remove_prompt_to_compare
                )
            exp_object.add(v)

        chain = kwargs.pop("chain", store is not None or self._chain_all_expects)

        ret = self._expect_cmd(exp_object, **kwargs)

        if callback:
            callback(ret)

        if store is not None:
            store.append(ret)

        if chain:
            return self
        else:
            return ret.results()

    # TODO: add expect new prompt
    def expect_ask_response_list(
        self,
        ask_response_list,
        stop_after_getting=None,
        timeout_after_first_match=0,
        remove_prompt_to_compare=True,
        chain=False,
        **kwargs
    ):
        """ simple procedure to go through a list of expected values and their corresponding responses

            There are some conditions that might break the required statement on some of the items in the list:
                - if there is an item with response=None we suspect is the prompt and we break
                - if stop_after_getting is set and we match a name in it we break

        Args:
            ask_response_list (list of dict or list of term.ExpectAndResponse):
            stop_after_getting (str): name of ExpectAndResponse object that if matched would trigger returning
            remove_prompt_to_compare (bool): whether we want to remove prompt to compare all the expects
            chain (bool): whether to return self (chain=True) or return the dictionary of results
            timeout_after_first_match (int): timeout to assign to all the expects after first match
            **kwargs (dict): default parameters for each expect

        Returns:

        """

        # separate values with names from those without name and also add an index to each
        expect_list, ask_resp_list_by_name = create_expectedregex_objects(
            ask_response_list, kwargs, remove_prompt_to_compare
        )

        stop_after_getting = fdutils.lists.to_sequence(stop_after_getting)

        i = 0
        match_set = set()
        match_list = {}
        _kwargs = kwargs

        while len(expect_list):
            exp = self.expect(*expect_list.values(), **kwargs)

            quota_filled, continue_checking = ask_resp_list_by_name[
                exp.name
            ].match_found()

            if quota_filled:
                match_set.add(exp.name)
                match_list[exp.name] = expect_list[exp.name]

            if not continue_checking:
                del expect_list[exp.name]

            if ask_resp_list_by_name[exp.name].response is not None:
                self.send_cmd(
                    ask_resp_list_by_name[exp.name].response,
                    is_hidden=ask_resp_list_by_name[exp.name].hidden,
                )
            else:  # implicit prompt
                break

            any_required_left = any(
                ask_resp_list_by_name[l].required for l in expect_list
            )

            if (
                stop_after_getting
                and exp.name in stop_after_getting
                or not any_required_left
            ):
                break

            kwargs = ask_resp_list_by_name[exp.name].kwargs or _kwargs

            # change timeout for next expect
            if timeout_after_first_match:
                kwargs["timeout"] = timeout_after_first_match

            i += 1

        if chain:
            return self
        else:
            return match_list

    def expect_all(self, *expect_value_list, **kwargs):
        kwargs["all_matches_required"] = True
        return self.expect(*expect_value_list, **kwargs)

    def expect_multiple(self, *expect_value_list, **kwargs):
        kwargs["multiple"] = True
        return self.expect(*expect_value_list, **kwargs)

    def expect_all_in_sequence(self, *expect_value_list, **kwargs):
        kwargs["all_matches_required"] = True
        kwargs["all_matches_in_sequence"] = True
        return self.expect(*expect_value_list, **kwargs)

    def expect_regex(self, regex, **kwargs):
        return self.expect(regex, **kwargs)

    def expect_string(self, string, flags=0, remove_prompt_to_compare=True, **kwargs):
        return self.expect(
            expect.ExpectedString(
                string, flags=flags, remove_prompt_to_compare=remove_prompt_to_compare
            ),
            **kwargs
        )

    expect_str = expect_string

    def expect_prompt(self, timeout=0, **kwargs):
        return self.expect(expect.ExpectedPrompt(), timeout=timeout, **kwargs)

    ep = expect_prompt

    def expect_istring(self, string, flags=0, remove_prompt_to_compare=True, **kwargs):
        flags |= re.I
        kwargs["flags"] = flags

        return self.expect(
            expect.ExpectedString(
                string, flags=flags, remove_prompt_to_compare=remove_prompt_to_compare
            ),
            **kwargs
        )

    expect_istr = expect_istring

    # TODO need consistency on return of all expect methods
    def expect_new_prompt(self, new_prompt=None, set_unique_prompt=False, timeout=0):
        self.get_new_prompt(timeout=timeout, new_prompt=new_prompt)
        if set_unique_prompt:
            self.set_unique_prompt()

        return self

    def expect_different_prompt(self, new_prompt=None, set_unique_prompt=False, timeout=0):
        curr_prompt = self.prompt
        self.expect_new_prompt(new_prompt, set_unique_prompt, timeout)
        if curr_prompt == self.prompt:
            raise exceptions.PromptNotFoundError("the new prompt is the same as the old prompt")
        return self

    def find_login_info(self, terminal):

        if terminal == self.current:
            raise ValueError(
                "The channel provided is the same as the current. There must be an error."
            )

        old_prompt = self.prompt if self._terminals else None
        terminal.shell.banner, terminal.shell.expected_prompt = self._get_banner_and_prompt(
            terminal, old_prompt
        )
        self._terminals.append(terminal)
        return self

    def expect_logout(self):
        old_shell = self._terminals.pop()
        try:
            exp = self.send_line().expect_prompt()
            if not exp.any_matched:
                raise exceptions.ExpectLoginError(
                    "expecting logout but did "
                    "not get the previous terminal prompt: " + self.prompt
                )
            else:
                return exp
        except Exception:
            self._terminals.append(old_shell)
            raise

    def get_new_prompt(self, timeout=0, update=True, new_prompt=None, chain=False):
        data, timer_expired, prompt_found = self._find_prompt(
            self.current, new_prompt=new_prompt, timeout=timeout
        )

        if not data or new_prompt and not prompt_found:
            if self.last_cmd_sent == "\n":
                cmd = "PROPMT"
            else:
                cmd = self.last_cmd_sent.strip()
            if not new_prompt:
                raised_data = data
            elif data:
                raised_data = (
                    "Prompt was not found for cmd ({}). Expected ({}) but got ({})"
                    "".format(cmd, new_prompt, data.splitlines()[-1])
                )
            else:
                raised_data = (
                    "Prompt was not found for cmd ({}). Expected ({}) but got no data"
                    "".format(cmd, new_prompt)
                )
            log.error(
                "PROMPT NOT FOUND: we got so far: " + self.get_conversation_string()
            )
            raise exceptions.PromptNotFoundError(
                raised_data
                if not self._last_cmd_was_hidden
                else raised_data.replace(self.last_cmd_sent, settings.HIDDEN_DATA_MSG)
            )

        elif update:
            self.prompt = re.escape(prompt_found or data.splitlines()[-1])

        if chain:
            return self
        return self.prompt

    def record(
        self,
        timeout=None,
        record_stop_signal=None,
        output_stream=None,
        time_to_sleep_between_recv=None,
        silent=False,
    ):
        """ records the data received from the terminal to an output_stream
            useful for recording files that change overtime in a tail or to capture log messages

        Args:
            timeout (float): time to record (if given)
            record_stop_signal (threading.Event): event object signaling when to stop
            output_stream (io._IOBase): a stream sink where to send the data to
            time_to_sleep_between_recv (float):
            silent (bool): whether to send data to the stream sink. If set to True no recording will happen

        Returns:

        """

        time_to_sleep_between_recv = (
            time_to_sleep_between_recv or self.sleep_time_after_no_data
        )
        timer = fdutils.timer.get_timer_from_timeout(timeout)

        stream = None if silent else (output_stream or StringIO())

        while not (
            timer.has_expired
            or self.stop_signal.is_set()
            or record_stop_signal
            and record_stop_signal.is_set()
        ):

            recv = self.recv()

            if recv == 0:
                self.close()
                log.error(
                    "recv command return empty string. End side might have been closed!"
                )
                raise ConnectionError

            elif recv != constants.SOCKET_RECV_NOT_READY and not silent:
                stream.write(recv)

            else:
                time.sleep(time_to_sleep_between_recv)

        return stream

    # TODO: define a circular buffer of new lines
    # TODO: reset buffer on chain match
    def _expect_cmd(
        self,
        expect_cmd,
        timeout=None,
        reset_on_new_line=False,
        buffer_size=None,
        reset_buffer=False,
    ):
        def _check_match(comp_buff):
            return comp_buff and expect_cmd.find_expected_values_and_prompt_in_buffer(
                comp_buff, self.prompt
            )

        # accumulated responses from server
        if reset_buffer:
            buff = ""
        else:
            buff = self.data.get_last_recv()
            if buff and _check_match(buff):
                return expect_cmd

        # reset expected values counter in case we are reusing an expect object
        expect_cmd.reset()

        # flag to check if at least one recv was successful before socket timeout
        received_anything = False

        # timer
        timer = fdutils.timer.get_timer_from_timeout(timeout or self.timeout)

        match_found = False
        recv = 0
        while not (match_found or timer.has_expired or self.stop_signal.is_set()):

            try:
                recv = self.recv(buffer_size)

            except socket.timeout:

                log.debug("Did not receive any data for a while " + str(expect_cmd))

                if not received_anything:
                    log.error(
                        "Did not receive any data before the socket timeout ({}). Increase the timeout or "
                        "check the command or system under test.".format(
                            str(self.transport.timeout)
                        )
                    )
                    raise ConnectionError

            if recv == 0:
                self.close()
                log.error(
                    "recv command return empty string. End side might have been closed!"
                )
                raise ConnectionError

            elif recv != constants.SOCKET_RECV_NOT_READY:
                received_anything = True

                buff += recv

                if _check_match(buff):
                    break

                if reset_on_new_line:
                    new_line_split = buff.rfind("\n") + 1
                    if new_line_split != 0:
                        buff = buff[new_line_split:]

            else:  # SOCKET_RECV_NOT_READY
                time.sleep(self.sleep_time_after_no_data)
        else:  # no break
            if timer.has_expired:
                buff = buff[-settings.BUFFER_SIZE_TO_RETURN_WHEN_ERROR :]
                if self._last_cmd_was_hidden:
                    buff = buff.replace(self.last_cmd_sent, settings.HIDDEN_DATA_MSG)

                raise exceptions.ConnectionExpectTimeoutError(
                    "Failed to match ({}) before timeout of ({}) secs.\n"
                    "Last {} chars: \n{}".format(
                        expect_cmd.expect_values,
                        timeout or self.timeout,
                        settings.BUFFER_SIZE_TO_RETURN_WHEN_ERROR,
                        buff,
                    )
                )

        return expect_cmd

    # TODO: add _update_loging to process that is not doing anything
    def _update_login(self, results, number_of_lines_for_prompt, new_line, shell=None):
        results.seek(0)
        welcome_message_lines = results.read().splitlines()
        prompt = "\n".join(
            welcome_message_lines[
                len(welcome_message_lines) - number_of_lines_for_prompt :
            ]
        )

        if shell is None:
            shell = shells.ShellLoginInformation()

        # checks if expected prompt is the one we got and if we are not skipping the check raise an exception
        if (
            shell.expected_prompt is None
            and re.search(self.prompt, prompt)
            and not shell.skip_prompt_check
        ):
            raise exceptions.ExpectLoginError

        shell.update(
            welcome_message=welcome_message_lines[:-number_of_lines_for_prompt],
            expected_prompt=prompt,
            number_of_lines_for_prompt=number_of_lines_for_prompt,
            new_line=new_line,
        )
        # do not copy if it is already added
        if self._terminals[-1] != shell:
            self._terminals.append(shell)


# TODO: get this with inspect.signature
def set_terminal_kwargs(kwargs):
    return dict(
        close_base_on_exit=kwargs.pop("close_base_on_exit", True),
        allow_non_expected_prompt=kwargs.pop("allow_non_expected_prompt", False),
        data_stream=kwargs.pop("data_stream", None),
        stderr_to_tmp=kwargs.pop("stderr_to_tmp", False),
        rtt=kwargs.pop("rtt", 0.5),
        check_same_prompt_when_opening_terminal=kwargs.pop(
            "check_same_prompt_when_opening_terminal", True
        ),
    )


def update_default_kwargs_on_call(kwargs, default_kwargs):
    new_kwargs = dict(default_kwargs)
    keys_to_update = [k for k in default_kwargs if k in kwargs]
    for k in keys_to_update:
        new_kwargs[k] = kwargs.pop(k)
    return new_kwargs


# TODO: should it be metaclass??
class TerminalConnectionWrapper:
    """ Helper class to enclose a connection with Terminal. similar to a metaclass """

    def __init__(self, wrapped_connection, host="", **kwargs):
        self.wrapped_connection = wrapped_connection
        self.host = host
        self.terminal_kwargs = set_terminal_kwargs(kwargs)
        self.wrapped_connection_kwargs = kwargs
        self.ARGUMENTS_ALLOWED = wrapped_connection.ARGUMENTS_ALLOWED + tuple(
            self.terminal_kwargs.keys()
        )

    def __call__(self, *args, **kwargs):

        tunnel = kwargs.pop("tunnel", None)

        if "host" in self.wrapped_connection.ARGUMENTS_ALLOWED:
            kwargs.setdefault("host", self.host)
        elif tunnel:
            kwargs.pop("host", None)
        else:
            raise ConnectionError(
                "We have not implemented having a command connection without a tunnel"
            )

        # pop arguments destined for TerminalConnection
        terminal_kwargs = update_default_kwargs_on_call(kwargs, self.terminal_kwargs)

        # put back default connection arguments
        kwargs.update(self.wrapped_connection_kwargs)

        w_conn = self.wrapped_connection(*args, **kwargs)

        if tunnel:
            tunnel.append(w_conn)
            connections = tunnel
        else:
            connections = [w_conn]

        return TerminalConnection(connections, **terminal_kwargs)

    def open_terminal_from_terminal(self, term_tunnel, **kwargs):
        return self.wrapped_connection(**kwargs).open_terminal_from_terminal(
            term_tunnel
        )

    def __getattr__(self, item):
        # anything else let the wrapped connection take care
        return getattr(self.wrapped_connection, item)


def terminal_connection_wrapper(wrapped_connection, host="", **kwargs):
    tcw = TerminalConnectionWrapper(wrapped_connection, host)
    set_terminal_kwargs(kwargs)
    return tcw(**kwargs)
