from io import StringIO
import shlex
import socket
import subprocess
import logging
import sys
from queue import Empty
import select
import selectors

from remotelogin.connections.utils import to_bytes
from .terminal import channel, terminal_connection_wrapper
from . import settings, constants
from .base import mixins, term
import fdutils as utils
import shutil


log = logging.getLogger(__name__)

__author__ = 'Filinto Duran (duranto@gmail.com)'


ON_WINDOWS = sys.platform == 'win32'

default_selector = selectors.DefaultSelector()


def read_from_file_and_put_in_queue(fd, buff=settings.BUFFER_SIZE):
    try:
        data = fd.read(buff)
        if len(data):
            return data.decode(encoding=settings.DECODE_ENCODING_TYPE, errors=settings.DECODE_ERROR_ARGUMENT_VALUE)
        else:
            return utils.parallel.POISON_PILL
    except Exception as e:
        log.exception('problems reading buffer. closing...')
        return utils.parallel.POISON_PILL


# TODO: move to registering events and/or asyncio
def enqueue_output_unix(fd):
    #default_selector.register(fd, selectors.EVENT_READ, read_from_file_and_put_in_queue)
    rfd, wfd, efd = select.select([fd], [], [])
    if rfd:
        return read_from_file_and_put_in_queue(fd)
    else:
        return utils.parallel.POISON_PILL


# TODO: look into twisted fdesc to handle non-blocking file descriptors in Windows
def enqueue_output_win(out):
    # windows only seem to work with 1 byte buffer reliably but slower.
    return read_from_file_and_put_in_queue(out, 1)


if not ON_WINDOWS:
    import fcntl
    import os
    enqueue_output = enqueue_output_unix

    def set_non_blocking(fd):
        fcntl.fcntl(fd, fcntl.F_SETFL, fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK)

else:
    enqueue_output = enqueue_output_win

    def set_non_blocking(*args):
        pass


class LocalConnection(term.ConnectionWithTerminal, mixins.CanExecuteCommands, mixins.CanTransferFiles):
    """
    A connection to the machine running this script to abstract the send_command method when talking to self

    It can also be used when trying to reuse terminal connections capabilities/expect via local machine.

    On windows it is not as performant as reads are not yet non-blocking until we find a solution like using
    Twisted fdesc

    This is not a replacement for simple subprocess methods and we actually use it to do all exchanges.
    """

    def __init__(self, use_std_error=False, with_shell=False, shell_app=None, redirect_stderr=True, **kwargs):
        self.use_std_error = use_std_error
        self._buffer = ''
        kwargs.setdefault('timeout', settings.CONNECTION_LOCAL_TIMEOUT)
        join_timeout = kwargs.pop('join_timeout', None)
        super(LocalConnection, self).__init__(**kwargs)
        self.nb_join_timeout = join_timeout or (self.timeout if ON_WINDOWS else self.NON_BLOCKING_JOIN_TIMEOUT)
        self.shell_app = shell_app or self.os.shell_app
        self.with_shell = with_shell
        self.host = 'localhost'
        self.redirect_stderr = redirect_stderr

    def _base_repr(self):
        base_set = super(LocalConnection, self)._base_repr()
        specific = {('use_std_error', False), ('shell_app', True)}
        return base_set | specific

    def _is_active(self):
        return self._transport and self._transport.poll() is None

    def _close_transport(self):
        try:
            self._transport.terminate()
        except:
            pass

    def _check_output(self, command, **kwargs):
        # sends single command and closes file descriptors
        kwargs.setdefault('shell', self.with_shell)
        command = command.strip()

        try:
            return subprocess.check_output(shlex.split(command), stderr=subprocess.STDOUT, **kwargs)\
                .decode(encoding=settings.DECODE_ENCODING_TYPE, errors=settings.DECODE_ERROR_ARGUMENT_VALUE)
        except:
            log.exception('Problems with cmd. Check the command syntax. Also remember that in some cases the command '
                          'is part of the shell, so you need to create the local connection with_shell=True')
            raise

    def _open_pipe(self):
        """

        Returns: subprocess.Popen

        """
        client = subprocess.Popen(self.shell_app, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT if self.redirect_stderr else subprocess.PIPE, shell=True)

        client.timeout = self.timeout
        set_non_blocking(client.stdout)
        set_non_blocking(client.stderr)

        def stop_process():
            client.terminate()
            client.wait()
            client.stdin.close()
            client.stdout.close()
            client.stderr.close()

        # duct tape popen so the thread can call close as expected
        client.close = stop_process

        return client

    def _check_output_nb(self, command, *args, **kwargs):

        command += self.new_line

        client = self._open_pipe()

        client.stdin.write(to_bytes(command))
        client.stdin.flush()

        return dict(target=enqueue_output, args=(client.stdout,)), client

    def _open_terminal_channel(self, **kwargs):
        return LocalTerminalChannel(self, self._open_pipe(), **kwargs)

    def _get_shell_and_conn_string(self, parent, **kwargs):
        kwargs.setdefault('expected_prompt', self.expected_prompt)
        shell = channel.TerminalShell(self, **kwargs)
        conn_string = self.shell_app
        return shell, conn_string

    def _get_file(self, remote_file, local_path):
        shutil.copy2(remote_file, local_path)

    def _open_transport(self, **kwargs):
        pass

    def _put_file(self, local_file, remote_path):
        shutil.copy2(local_file, remote_path)


class LocalTerminalChannel(channel.TerminalChannel):

    def __init__(self, conn, channel, **shell_kwargs):
        """

        Args:
            process (LocalConnection):
            **shell_kwargs:

        Returns:

        """
        shell_kwargs.setdefault('timeout', settings.CONNECTION_LOCAL_TIMEOUT)
        shell_kwargs.setdefault('connect_timeout', settings.CONNECTION_LOGIN_LOCAL_TIMEOUT)
        super(LocalTerminalChannel, self).__init__(conn, channel, **shell_kwargs)

        self.thread_out = utils.parallel.ThreadLoopWithQueue(enqueue_output, args=(self.channel.stdout,),
                                                             recv_data_timeout=settings.NON_BLOCKING_RECEIVED_DATA_TIMEOUT)
        self.thread_out.start()

    def _close(self):
        #self.thread_out.join(timeout=0.1)
        self.thread_out.stop()
        import time
        time.sleep(0.1)

    def set_keepalive(self, interval=settings.SOCKET_KEEPALIVE_PERIOD):
        pass

    def _resize_pty(self, cols, rows):
        self.send(self.os.cmd.resize_pty(cols, rows))

    def is_active(self):
        return self.channel.poll() is None

    def send(self, msg):
        try:
            self.channel.stdin.write(to_bytes(msg))
            self.channel.stdin.flush()
            log.debug('Sent: ' + msg)
        except ValueError:
            log.exception('io error - reraising as socket.error')

            raise socket.error

    def recv(self, buffer_size=0):
        # for interactive comm
        r = StringIO()
        count = 0
        buffer_size = buffer_size or settings.BUFFER_SIZE
        try:
            while count < buffer_size:
                try:
                    new = self.thread_out.queue.get(timeout=settings.TELNET_TIMEOUT_RECV)
                    count += len(new)
                    r.write(new)

                except Empty:
                    if not count:
                        return constants.SOCKET_RECV_NOT_READY
                    break

            return r.getvalue()

        except ValueError:
            log.exception("IO operation error")
            return 0

    @property
    def timeout(self):
        return self.thread_out.recv_data_timeout

    @timeout.setter
    def timeout(self, timeout):
        self.thread_out.recv_data_timeout = timeout


def LocalTerminalConnection(host='', **kwargs):
    return terminal_connection_wrapper(LocalConnection, host, **kwargs)