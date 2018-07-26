import binascii
import contextlib
import functools
import logging
import os
import re

from .. import exceptions, settings
from ..decorators import must_be_open
import fdutils

log = logging.getLogger(__name__)


class CanExecuteCommands:

    def _get_cmd(self, cmd, use_sudo, stderr_to_tmp):

        if stderr_to_tmp or getattr(self, 'stderr_to_tmp', False):
            err_file = self.current.os.path().join(self.current.os.temp, 'stderr_' + fdutils.crypto.base64_hash(cmd)[:50])

            if not cmd.find(' 2>') != -1 and stderr_to_tmp:
                # set stderr to the file. first check there is no & (nonblock run) at end of cmd
                if re.search('\s&\s*$', cmd):
                    cmd = re.sub('\s&\s*$', ' 2>{} & '.format(err_file), cmd)
                else:
                    cmd += ' 2>' + err_file

        if use_sudo:
            if 'sudo ' not in cmd:
                cmd = self.os.sudo + ' ' + cmd

        return cmd

    @must_be_open
    def check_output(self, command, use_sudo=False, stderr_to_tmp=False, metadata=None, **kwargs):
        """ sends a command to a connection and returns the results as a string

        :param str command: command to send to the connection
        :param str return_type: one of string, stream or list
        :param str or None metadata:
        :rtype: (list, list)
        :return: a tuple stringout, error. stringout and error are lists of strings (one line per element)
        """
        log.debug("{} - Sending cmd: {}".format(self.__class__.__name__, command))
        command = self._get_cmd(command, use_sudo, stderr_to_tmp)
        self.data.new_sent(command, metadata=metadata)
        try:
            command = command.strip()
            output = self._check_output(command, **kwargs).rstrip('\n')
        except exceptions.CalledProcessError as exc:
            log.error("{} execution failed ({}):".format(command, exc.returncode, exc.output))
            self.data.new_received(exc.output)
            raise
        else:
            log.debug("{} succeeded. Output:{}".format(self.__class__.__name__, output))
            if hasattr(output, 'read'):  # for file-like classes
                out_ret = output.read()
            else:
                out_ret = output

            self.data.new_received(out_ret)
            return out_ret
    check_sudo_output = functools.partialmethod(check_output, use_sudo=True)

    @must_be_open
    def check_output_nb(self, command, metadata=None, **kwargs):
        """ sends a command to a connection non-blocking and start a thread to wait for the response

        :param str command: command to send to the connection
        :param str return_type: one of string, stream or list
        :rtype: fdutils.parallel.StoppableThreadWithTextQueue

        :return:
        :rtype: fdutils.parallel.StoppableThreadWithQueueAndCallback
        """

        def callback(th):
            self.data.new_received(th.get_data())

        log.debug("{} - Sending cmd: {}".format(self.__class__.__name__, command))
        self.data.new_sent(command, metadata=metadata)

        recv_data_timeout = settings.NON_BLOCKING_RECEIVED_DATA_TIMEOUT
        run_timeout = kwargs.pop('timeout', 0)

        command = command.strip()
        target_out, channel = self._check_output_nb(command, **kwargs)

        th_out = fdutils.parallel.ThreadLoopWithQueue(
            target_out['target'], args=target_out['args'], run_timeout=run_timeout, join_timeout=self.nb_join_timeout,
            recv_data_timeout=recv_data_timeout)
        th_out.add_call_on_stop(callback, args=(th_out,))
        th_out.add_call_on_stop(channel.close)
        th_out.start()

        return th_out

    def _check_output(self, command, **kwargs):
        pass

    def _check_output_nb(self, command, **kwargs):
        pass


class B64DecoderWriter:

    def __init__(self, output_io, cmd):
        self.output_io = output_io
        self.buffer = []
        self.cmd = cmd
        self.cmd_removed = False

    def write(self, data):
        if not data:
            return

        rn = data.rfind('\n')

        if rn >= 0:
            buff_data, new_data = data[:rn], data[rn+1:]
            self.buffer.append(buff_data)
            data_to_decode = ''.join(self.buffer)
            if not self.cmd_removed:
                cmd_pos = data_to_decode.find(self.cmd)
                if cmd_pos >= 0:
                    data_to_decode = data_to_decode[len(self.cmd):].lstrip()
                self.cmd_removed = True
            if data_to_decode:
                self.output_io.write(binascii.a2b_base64(data_to_decode))
            # reset buffer
            self.buffer = [new_data] if new_data else []
        else:
            self.buffer.append(data)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.output_io.write(binascii.a2b_base64(''.join(self.buffer)))


# TODO: add multiple file upload/download sequential/parallel(threaded or coroutines)
def get_local_path_from_remote_file(remote_file, local_path='', overwrite=False, local_folder=None):
    remote_file_base = os.path.basename(remote_file)
    if not local_path:
        if not local_folder:
            local_path = remote_file_base
        else:
            local_path = os.path.join(local_folder, remote_file_base)

    if os.path.exists(local_path) and not overwrite:
        local_path = fdutils.files.get_filename_indexed(local_path)
    return local_path


def _check_local_file(local_path, remote_file):
    if os.path.exists(local_path):
        return local_path
    else:
        raise exceptions.FileTransferError('Problems retrieving the file ({}) to local ({})'
                                           ''.format(remote_file, local_path))


@contextlib.contextmanager
def _get_file_common(remote_file, local_path, replace, local_folder):
    local_path = get_local_path_from_remote_file(remote_file, local_path, replace, local_folder)
    yield local_path
    _check_local_file(local_path, remote_file)



from paramiko import SFTPAttributes

# TODO: put buffer as file or put stream as file
class CanTransferFiles:

    def _get_remote_path(self, local_file, remote_path, remote_folder):
        if not remote_path:
            remote_path = os.path.basename(local_file)

            if remote_folder:
                remote_path = self.os.path.join(remote_folder, remote_path)
        return remote_path

    @must_be_open
    def put_file(self, local_file, remote_path='', remote_folder='', replace=True,
                 check_md5=False, remove_if_bad_md5=False, **put_kwargs):
        remote_path = self._get_remote_path(local_file, remote_path, remote_folder)
        attr = self._put_file(local_file, remote_path, **put_kwargs)
        if attr is None:
            attr = self._get_stat_on_remote_file(remote_path)
            local_size = os.stat(local_file).st_size
            if attr.st_size != local_size:
                raise IOError('File size on remote system ({}) different to local system ({})'
                              ''.format(attr.st_size, local_size))
        else:
            attr.filename = remote_path

        if check_md5:
            self._check_md5_put(local_file, remote_path, remove_if_bad_md5)

        return attr

    def _get_stat_on_remote_file(self, remote_path):
        m_time, size = self.os.get_info_from_list_file(self.check_output(self.os.cmd.list_file(remote_path)),
                                                       remote_path)
        attr = SFTPAttributes()
        attr.st_size = int(size)
        attr.st_mtime = m_time
        attr.filename = remote_path

        return attr

    put = put_file

    def _put_file(self, local_file, remote_path, **put_kwargs):
        raise NotImplementedError

    @must_be_open
    def put_file_via_cat(self, local_file, remote_path='', remote_folder='', replace=True,
                         check_md5=False, remove_if_bad_md5=False, **put_kwargs):
        """ puts a file using txt messages or base64 encoded data.  Not meant to be used for large files

        Args:
            local_file:
            remote_path:
            remote_folder:
            **put_kwargs:

        Returns:

        """

        remote_path = self._get_remote_path(local_file, remote_path, remote_folder)

        if replace and check_md5:
            remote_path += settings.TEMP_FILE_EXTENSION

        with open(local_file, 'rb') as f:
            data = f.read()

        if not self.os.cmd.HAS_BASE64:
            log.warning('Transferring file as text mode as this OS ({}) does not seem to have a base64 cmd.'
                        'We will be using using cat method ({})'.format(self.os.name, self.os.cmd.CAT))
            self.send_cmd_prompt(self.os.cmd.cat_to_file(remote_path, data), **put_kwargs)
        else:
            data = binascii.b2a_base64(data).decode()[:-1] # remove newline char
            self.send_cmd_prompt(self.os.cmd.cat_to_file(remote_path + '.b64', data), **put_kwargs)
            self.send_cmd_prompt(self.os.cmd.base64_decode_to_file(remote_path + '.b64', remote_path), **put_kwargs)
            self.send_cmd_prompt(self.os.cmd.remove(remote_path + '.b64'), **put_kwargs)

        if check_md5:
            self._check_md5_put(local_file, remote_path, remove_if_bad_md5, replace)

        fattr = self._get_stat_on_remote_file(remote_path)

        return fattr

    @contextlib.contextmanager
    def _md5_same_on_files(self, local_file, remote_path):
        md5sum = self.os.md5sum_clean(self.check_output(self.os.cmd.md5checksum(remote_path)))
        yield md5sum == fdutils.files.md5_checksum(local_file)

    def _check_md5_put(self, local_file, remote_path, remove_if_bad_md5, replace):
        if not self._md5_same_on_files(local_file, remote_path):
            log.info('Deleting put file as MD5sum does not match local file checksum')
            if remove_if_bad_md5:
                self.send_cmd_prompt(self.os.cmd.remove(remote_path))
            raise exceptions.FileTransferError('Checksums of files after PUT are not equal')

        if replace:
            new_remote_path = remote_path[:-len(settings.TEMP_FILE_EXTENSION)]
            self.send_cmd_prompt(self.os.move(remote_path, new_remote_path, overwrite=True))

    def _check_md5_get(self, local_file, remote_path, remove_if_bad_md5):
        if not self._md5_same_on_files(local_file, remote_path):
            log.info('Deleting get file as MD5sum does not match remote file checksum')
            if remove_if_bad_md5:
                os.remove(local_file)
            raise exceptions.FileTransferError('Checksums of files after GET are not equal')

    put_via_cat = put_file_via_cat

    @must_be_open
    def get_file(self, remote_file, local_path='', replace=False, local_folder=None,
                 check_md5=False, remove_if_bad_md5=False, **get_kwargs):
        """

        Args:
            remote_file:
            local_path: the full path to the file locally
            local_folder: path to a directory where to download the file if local_path not given
            replace:
            timestamp:

        Returns:

        """
        with _get_file_common(remote_file, local_path, replace, local_folder) as local_path:
            self._get_file(remote_file, local_path, **get_kwargs)

        return os.path.abspath(local_path)

    get = get_file

    @must_be_open
    def get_file_via_cat(self, remote_file, local_path='', base64_func=None, use_sudo=False, replace=False,
                         local_folder=None, check_md5=False, remove_if_bad_md5=False, **kwargs):

        with _get_file_common(remote_file, local_path, replace, local_folder) as local_path:

            with open(local_path, 'wb') as file_stream:

                if base64_func is None and not self.os.cmd.HAS_BASE64:
                    log.warning('Transferring file as text mode as this OS ({}) does not seem to have a base64 cmd.'
                                'We will be using using cat method ({})'.format(self.os.name, self.os.cmd.CAT))
                    cat_cmd = self.os.cat(remote_file)
                    stream = file_stream
                else:
                    base64_func = base64_func or self.os.cmd.base64
                    cat_cmd = base64_func(remote_file)
                    stream = B64DecoderWriter(file_stream, cat_cmd)

                self.check_output(cat_cmd, use_sudo=use_sudo,recv_stream=stream,
                                  reset_on_new_line=True, **kwargs)

        if check_md5:
            self._check_md5_get(local_path, remote_file, remove_if_bad_md5)
            md5sum = self.os.md5sum_clean(self.check_output(self.os.cmd.md5checksum(remote_file)))

            if md5sum != fdutils.files.md5_checksum(local_path):
                raise exceptions.FileTransferError('Checksums are not equal')

        return os.path.abspath(local_path)

    get_via_cat = get_file_via_cat

    def _get_file(self, remote_file, local_path, **get_kwargs):
        raise NotImplementedError