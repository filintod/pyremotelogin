import contextlib
import io
import logging
import select
import time

import paramiko
import scp
import fdutils
from paramiko import SFTPClient
from remotelogin.connections import base, exceptions, settings
from remotelogin.connections.base import term, mixins
import remotelogin.connections.constants
from remotelogin.connections.exceptions import BadSshKeyPasswordError, NoDefaultUserError
from remotelogin.connections.terminal import channel, terminal_connection_wrapper

log = logging.getLogger(__name__)


def get_ask_resp_list_for_new_connection(password, prompt=None):
    return [term.ExpectPasswordAndResponse(password),
            term.ExpectPasswordAndResponse(password, expect=r'passphrase for key'),  # for ssh-agent
            term.ExpectAndResponse(r'are you sure you want to continue .+', 'yes', name='unknown_key'),
            term.ExpectPrompt(prompt, required=bool(prompt))]


#TODO: set known keys location
class SshConnection(term.IPConnectionWithTerminal, mixins.CanExecuteCommands, mixins.CanTransferFiles):
    """ SSH-type connection

        Args:
            hostname:
            key_filename (str): path to the private key to use
            allow_unknown_keys (bool): defaults to True to allow unknown keys from servers
            keep_alive_period (int): defaults to settings.SOCKET_KEEPALIVE_PERIOD
            file_transfer_protocol (str): defaults to 'sftp'. can also be 'scp'

        Returns:
    """

    _IANA_SVC_NAME = 'ssh'
    AUTHENTICATION_KEYS = term.IPConnectionWithTerminal.AUTHENTICATION_KEYS + \
                                 ('key_filename', 'key_password', 'key_cert')
    AUTHENTICATION_KEYS_COMBINATIONS = (('username', 'password'),
                                        ('username', 'key_filename'))
    ARGUMENTS_ALLOWED = term.IPConnectionWithTerminal.ARGUMENTS_ALLOWED + \
                        ('key_filename', 'key_password', 'allow_unknown_keys', 'ssh_app', 'file_transfer_protocol',
                         'proxy_jump', 'key_cert', 'use_agent')

    def __init__(self, host='', key_filename=None, allow_unknown_keys=True, ssh_app=None, key_password=None,
                 key_cert=None, keep_alive_period=0, file_transfer_protocol='sftp', ssh_app_kwargs=None,
                 proxy_jump=None, use_agent=False, **kwargs):

        self.file_transfer_protocol = file_transfer_protocol
        if self.file_transfer_protocol not in ('sftp', 'scp'):
            raise AttributeError("File transfer protocol can only be sftp or scp.")

        self.nb_join_timeout = kwargs.pop('join_timeout', None) or self.NON_BLOCKING_JOIN_TIMEOUT
        super(SshConnection, self).__init__(host=host, **kwargs)

        self.key_filename = key_filename
        self.key_password = key_password
        self.key_cert = key_cert # for ssh signed public keys
        self.use_agent = use_agent
        self._paramiko_key_policy = None
        self._allow_unknown_keys = None
        self.allow_unknown_keys = allow_unknown_keys
        self.keep_alive_period = keep_alive_period or settings.SOCKET_KEEPALIVE_PERIOD
        self.ssh_app = ssh_app or self.os.ssh_app
        self.ssh_app_kwargs = ssh_app_kwargs or {}
        self.proxy_jump = proxy_jump
        self._paramiko_transport = None

    @property
    def allow_unknown_keys(self):
        return self._allow_unknown_keys

    @allow_unknown_keys.setter
    def allow_unknown_keys(self, value):
        self._allow_unknown_keys = value
        self._paramiko_key_policy = paramiko.AutoAddPolicy() if self.allow_unknown_keys else paramiko.RejectPolicy()

    @property
    def key_policy(self):
        return self._paramiko_key_policy

    def _base_repr(self):
        base_set = super(SshConnection, self)._base_repr()
        specific = {('key_filename', True), ('allow_unknown_keys', False), ('keep_alive_period', False),
                    ('key_password', 'your key file password'), ('file_transfer_protocol', True)}
        return base_set | specific

    @property
    def ssh_transport(self):
        return self._paramiko_transport

    @property
    def is_open(self):
        try:
            return self._is_open and self.ssh_transport.active
        except AttributeError:
            return False

    def open_tunnel(self, host, port, timeout=None, src_host='', src_port=0):
        error_msg = "Tunnel could not be created to {}:{}".format(host, port)
        try:
            tunnel = self.ssh_transport.open_channel(kind='direct-tcpip',
                                                     dest_addr=(host, int(port)),
                                                     src_addr=(src_host, src_port),
                                                     timeout=timeout)
        except Exception:
            log.exception(error_msg)
            raise ConnectionError

        else:
            if tunnel is None:
                log.error(error_msg)
                raise ConnectionError

            return tunnel

    def open_proxyjump(self, connect_timeout=None):
        """ goes through tunnel """
        self.proxy_jump.open()
        timeout = connect_timeout if connect_timeout is not None else self.connect_timeout
        return self.proxy_jump.open_tunnel(self.host, self.port, timeout)

    def _set_default_credentials_all(self, kwargs, defaults):
        if self.key_filename and not defaults.get('pkey'):
            defaults['key_filename'] = self.key_filename

        defaults['password'] = self.password

        fdutils.lists.setdefault_inplace(kwargs, username=self.username, port=self.port, timeout=self.connect_timeout,
                                         **defaults)

        if not kwargs['username']:
            raise NoDefaultUserError('Username has not been defined for this connection!!!')

        # make sure port is integer
        kwargs['port'] = int(kwargs['port'])

    def _set_default_credentials_for_shell(self, parent, kwargs):
        defaults = {}
        dev_null = parent.os.dev_null if parent else self.os.dev_null

        if self.allow_unknown_keys:
            # allow unknown hosts and send them to the trash
            defaults['options'] = '-o UserKnownHostsFile={null} -o StrictHostKeyChecking=no'.format(null=dev_null)

        # check if we alrady have tty to add -T
        # if parent and hasattr(parent, 'current') and isinstance(parent.current, LocalTerminalChannel):
        #     defaults['tty'] = '-T'

        self._set_default_credentials_all(kwargs, defaults)

    def _try_cryptography_direct_pkey(self, filepath, filekey):
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization
        if hasattr(filepath, "read"):
            filepath.seek(0)
            return serialization.load_pem_private_key(filepath.read().encode(),
                                                      password=filekey.encode(),
                                                      backend=default_backend())
        with open(filepath, "rb") as key_file:
            return serialization.load_pem_private_key(key_file.read(),
                                                      password=filekey.encode(),
                                                      backend=default_backend())

    def _set_default_credentials(self, kwargs):
        self.transport.set_missing_host_key_policy(self.key_policy)
        defaults = {}

        if self.key_filename:
            defaults['allow_agent'] = False
            defaults['look_for_keys'] = False

            try:
                if isinstance(self.key_filename, io.IOBase):
                    self.key_filename.seek(0)
                    func = paramiko.RSAKey.from_private_key
                else:
                    func = paramiko.RSAKey.from_private_key_file
                defaults['pkey'] = func(self.key_filename, password=self.key_password)

            except paramiko.ssh_exception.SSHException:
                if self.key_password:
                    try:
                        defaults['pkey'] = paramiko.RSAKey(key=self._try_cryptography_direct_pkey(self.key_filename,
                                                                                                  self.key_password))
                    except Exception:
                        log.exception('problems with key or file type')
                        raise BadSshKeyPasswordError('Your password might be wrong for this key file ({})'
                                                     ''.format(self.key_filename))

            if self.key_cert:
                try:
                    defaults['pkey'].load_certificate(self.key_cert)
                except Exception:
                    # hack to work around paramiko lack of support for openssl signed public key
                    #   until I submit a pr on paramiko
                    with open(self.key_cert) as f:
                        ptype, blob = f.read().split(None, 2)
                        if ptype.endswith("@openssh.com"):
                            raise

                        from paramiko import message, pkey
                        from base64 import decodebytes
                        defaults['pkey'].public_blob = pkey.PublicBlob(ptype, decodebytes(blob.encode()))

        self._set_default_credentials_all(kwargs, defaults)

    def _open_transport(self, **kwargs):
        """ Opens an SSH connection.

        """
        self.transport = paramiko.SSHClient()

        if not self.transport:
            raise ConnectionError

        else:
            self._set_default_credentials(kwargs)

            log.debug('Opening SSH connection to ({}) with user ({})'.format(self.host, self.username))

            try:
                if self.proxy_jump and 'sock' not in kwargs:
                    kwargs['sock'] = self.open_proxyjump()

                def connect():
                    self.transport.connect(self.host, **kwargs)
                    self._paramiko_transport = self.transport.get_transport()

                if hasattr(self.os, 'monkey_patch_ssh'):
                    with self.os.monkey_patch_ssh():
                        connect()
                else:
                    connect()

            except paramiko.ssh_exception.AuthenticationException:
                raise exceptions.AuthenticationException

            except paramiko.ssh_exception.SSHException as exc:
                if not self.allow_unknown_keys:
                    raise exceptions.PermissionDeniedError('Host key policy is set to only allow known keys. '
                                                           'Check if this host {} is part of your allowed ones'
                                                           ''.format(self.host))
                else:
                    raise ConnectionError from exc

            except Exception as exc:
                log.exception("There are problems with the SSH connection")
                raise ConnectionError from exc

            self.set_keepalive(self.keep_alive_period)

            return self

    def _is_active(self):
        return self.ssh_transport.is_active()

    def _pop_window_packet_size(self, kwargs):
        return {'window_size': kwargs.pop('window_size', settings.DEFAULT_TRANSPORT_WINDOW_SIZE),
                'max_packet_size': kwargs.pop('max_packet_size', settings.DEFAULT_TRANSPORT_MAX_PACKET_SIZE)}

    def _check_output_nb(self, command, *args, **kwargs):

        def put_into_queue(c):
            rl, wl, xl = select.select([c], [], [], 1)
            if c in rl:
                return chan.recv(self.buffer_size).decode(encoding=settings.DECODE_ENCODING_TYPE,
                                                          errors=settings.DECODE_ERROR_ARGUMENT_VALUE)
            else:
                return fdutils.parallel.POISON_PILL

        chan = self.ssh_transport.open_session()
        if kwargs.get('get_pty', False):
            chan.get_pty()
        chan.settimeout(self.timeout)
        chan.exec_command(command)
        return dict(target=put_into_queue, args=(chan,)), chan

    def _paramiko_exec_command_with_channel(self, command, bufsize=-1, timeout=None, get_pty=False, **kwargs):
        """ copied from paramiko.client but returning the channel so we can reuse it"""
        chan = self.ssh_transport.open_session(**self._pop_window_packet_size(kwargs))
        if get_pty:
            chan.get_pty()
        chan.settimeout(timeout)
        chan.exec_command(command)
        stdin = chan.makefile('wb', bufsize)
        stdout = chan.makefile('r', bufsize)
        stderr = chan.makefile_stderr('r', bufsize)
        return stdin, stdout, stderr, chan

    def _close_transport(self):
        self.transport.close()
        self._paramiko_transport = None
        try:
            if self.proxy_jump:
                self.proxy_jump.close()
        except Exception:
            log.exception('Problems closing proxy jump')

    def _check_output(self, command, *args, **kwargs):
        # extend/reduce socket timeout according to command if given. It will change it
        # for this command only as the channel will be closed after executing

        stdin, out, err, chan = self._paramiko_exec_command_with_channel(command, **kwargs)
        errorout = err.read().decode()

        if len(errorout) and errorout.find('no tty present') >= 0:
            # did not work without tty. request terminal first
            stdin, out, err, chan = self._paramiko_exec_command_with_channel(command, get_pty=True, **kwargs)
            errorout = err.read().decode()

        if errorout:
            if chan.exit_status_ready():
                exit_status = chan.recv_exit_status()
            else:
                exit_status = exceptions.RECV_EXIT_STATUS_UNKNOWN
            raise exceptions.CalledProcessError(exit_status, command, output=errorout)

        return out.read().decode()

    def _open_terminal_channel(self, **kwargs):
        return SshTerminalChannel(self, self.transport.invoke_shell(), **kwargs)

    @contextlib.contextmanager
    def _get_ftp_client(self, window_size=None, max_packet_size=None, buffer_size=None):
        """ opens an sftp or scp channel and closes it after execution finished

        Returns:

        """
        window_size = window_size or settings.SFTP_SCP_WINDOW_SIZE
        max_packet_size = max_packet_size or settings.SFTP_SCP_MAX_PACKET_SIZE
        buffer_size = buffer_size or settings.SFTP_SCP_BUFFER_SIZE

        c = None

        try:
            if self.file_transfer_protocol == 'sftp':
                c = SFTPClient.from_transport(self.ssh_transport,
                                              window_size=window_size,
                                              max_packet_size=max_packet_size)
            else:
                c = scp.SCPClient(self.ssh_transport, buff_size=buffer_size)

            yield c
        finally:
            try:
                if c:
                    c.close()
            except Exception:
                log.exception('problems closing sftp/scp client')

    def _put_file(self, local_file, remote_path, **put_kwargs):
        with self._get_ftp_client(**put_kwargs) as ftp:
            if isinstance(local_file, io.IOBase):
                return ftp.putfo(local_file, remote_path)
            return ftp.put(local_file, remote_path)

    def _get_file(self, remote_file, local_path, keep_channel_open=False, **get_kwargs):
        with self._get_ftp_client(**get_kwargs) as ftp:
            ftp.get(remote_file, local_path)

    def set_keepalive(self, interval=0):
        self.ssh_transport.set_keepalive(interval or settings.SOCKET_KEEPALIVE_PERIOD)

    @base.Connection.timeout.setter
    def timeout(self, timeout):
        """ Warning: sets the timeout on the socket so it will change it for all channels open using this connection instance.

        :param timeout:
        :return:invalid syntax (<string>, line 1)
        """
        self.ssh_transport.sock.settimeout(timeout)
        self._timeout = timeout

    # TODO: implement ssh keys with passwords instead of relying on ssh-agent
    def _get_shell_and_conn_string(self, parent=None, **kwargs):
        from ..terminal import channel
        self._set_default_credentials_for_shell(parent, kwargs)

        username = kwargs.pop('username', self.username)
        password = kwargs.pop('password', self.password)
        use_agent = kwargs.pop('use_agent', self.use_agent)
        port = kwargs.pop('port', self.port)
        key_filename = kwargs.pop('key_filename', '')
        options = kwargs.pop('options', '')
        ssh_app = self.ssh_app if parent is None else parent.os.ssh_app

        key_file = ('-i ' + key_filename) if key_filename else ''
        if self.key_password and not self.use_agent:
            raise NotImplementedError('SSH Key Password has not been Implemented yet. You can use ssh-agent (use_agent=True) to '
                                      'keep your key password on the server as an interim solution.')
        use_agent = '-A' if use_agent else ''

        if not key_filename and not use_agent:
            ask_response_list = get_ask_resp_list_for_new_connection(password,
                                                                     kwargs.get('expected_prompt',
                                                                                self.expected_prompt))
        else:
            ask_response_list = []

        kwargs.setdefault('ask_response_list', ask_response_list)

        if ssh_app is None:
            raise ConnectionError('This os ({}) does not have a terminal ssh application available.\n'
                                  'You can also provide one when instantiating by passing the value '
                                  'in the parameter ssh_app'.format(self.os.__name__))
        tty = kwargs.pop('tty', '-tt')
        shell = channel.TerminalShell(self, **kwargs)

        # ssh_app.create_connection_string(port=port, username=username, key_filename=key_filename,
        #                                  host=self.host, args=args)

        if 'plink' in ssh_app:
            options = ''
            port_arg = '-P'
        else:
            port_arg = '-p'

        conn_string = '"{ssh}" {port_arg} {port} {key_file} {use_agent} {options} -l {user} {tty} {host}'.format(
            ssh=ssh_app, key_file=key_file, user=username, host=self.host, port=port, options=options,
            port_arg=port_arg, tty=tty, use_agent=use_agent)

        return shell, conn_string


class SshTerminalChannel(channel.TerminalChannel):

    def send(self, string):
        self.channel.sendall(string.encode(encoding=settings.ENCODE_ENCODING_TYPE,
                                           errors=settings.ENCODE_ERROR_ARGUMENT_VALUE))

    def send_bytes(self, data):
        self.channel.sendall(data)

    def recv(self, buffer_size=0):

        if not self.channel.recv_ready():
            time.sleep(settings.SSH_RECV_READY_SLEEP)

        if self.channel.recv_ready():
            data = self.channel.recv(buffer_size or settings.BUFFER_SIZE)
            if data == '':
                return 0
            else:
                return data.decode(encoding=settings.DECODE_ENCODING_TYPE,
                                   errors=settings.DECODE_ERROR_ARGUMENT_VALUE)
        else:
            return remotelogin.connections.constants.SOCKET_RECV_NOT_READY

    def set_keepalive(self, interval=settings.SOCKET_KEEPALIVE_PERIOD):
        pass

    def _resize_pty(self, cols, rows):
        self.channel.resize_pty(cols, rows)

    def is_active(self):
        return not (self.channel.closed or
                    self.channel.eof_received or
                    self.channel.eof_sent or
                    not self.channel.active)


def SshTerminalConnection(host='', **kwargs):
    return terminal_connection_wrapper(SshConnection, host, **kwargs)
