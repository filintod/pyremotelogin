import functools
import logging
import os
import weakref

import fdutils as utils
from .base import Manager
from .. import exceptions

log = logging.getLogger(__name__)

try:
    from os import scandir
except ImportError:
    try:
        from scandir import scandir
    except ImportError:
        print('Please install scandir (pip install scandir) or use a new Python (>=Python 3.5)')
        raise


def get_local_name_from_file_path(file_name, file_prefix, local_folder_location, timestamp_files, overwrite):
    file_path = os.path.join(local_folder_location, file_prefix + os.path.basename(file_name))
    if timestamp_files:
        file_path = utils.files.get_filename_timestamped(file_path)

    if not overwrite:
        return utils.files.name_if_file_exists(file_path, add_index=True)
    else:
        return file_path


def get_file_func_and_args(cat_cmd, conn, timeout, via_cat):
    if not via_cat:
        get_file = conn.get_file
        kwargs = {}
    else:
        get_file = conn.get_file_via_cat
        kwargs = dict(timeout=timeout, buffer_size=64000, cat_cmd=cat_cmd)
    return get_file, kwargs


class FileHandlerWrapper:

    def __init__(self, filepath, handler, manager):
        self.__handler = handler
        self.__path = filepath
        self.__manager = weakref.proxy(manager)

    def __getattr__(self, item):
        return getattr(self.__handler, item)

    def write(self, data):
        self.__handler.write(data)

    def read(self, *n):
        return self.__handler.read(*n)

    def __enter__(self):
        return self.__handler

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.__manager.close_file(self.__path)

    def close_on_manager_del(self):
        self.__handler.close()


class FilesManager(Manager):

    def __init__(self, *args, **kwargs):
        self.is_folder_created = False
        super(FilesManager, self).__init__(*args, **kwargs)
        self._dev_folder = self._dev.folder
        self._file_handlers_open = {}

    def _create_folder(self):

        try:
            if not os.path.exists(self._dev_folder):
                os.makedirs(self._dev_folder)

            self.is_folder_created = True

            return True

        except Exception:
            log.error("Cannot create download folder {} on device {}... Exiting"
                      "".format(self._dev.folder, self._dev.hostname))
            raise exceptions.DeviceFolderError

    def check_or_create_device_folder(self):
        return self.is_folder_created or self._create_folder()

    def __iter__(self):
        for entry in scandir(self._dev.folder):
            if not entry.name.startswith('.') and entry.is_file():
                yield entry.name

    def upload(self, local_files, remote_path='', device_files_path=None, device_folder_location='', remote_folder='',
               conn_name=None, **conn_kwargs):
        """ uploads a series of files given by local_files, to the device.

         Args:
            local_files (list): list of file paths in the local server that we want to upload to this device
            device_files_path (list): list of file paths on the device for every file given in local_files. If given this should be of the same size of local_files
            device_folder_location (str): this is used if device_files_path is not given. if neither of them is given the files will be uploaded to the home dir of the user
            conn_kwargs (dict): user, interface and/or tunnel name to use for the connection
         Returns:
              list: list of paths of the files uploaded at the device

        """
        device_files_path = device_files_path or remote_path
        device_files_path = utils.lists.to_sequence(device_files_path) if device_files_path else []
        local_files = utils.lists.to_sequence(local_files)

        if device_files_path and not len(device_files_path) == len(local_files):
            raise ValueError('Number of files path do not match between local and remote')

        uploaded_files_path = dict()

        device_folder_location = device_folder_location or remote_folder

        if device_folder_location:
            device_folder_location += self._dev.os.path.sep

        conn_name = conn_name or conn_kwargs.pop('name', None)
        with self._dev.conn.get_open_instance(name=conn_name, open_if_close=True, **conn_kwargs) as conn:
            for i, file_path in enumerate(local_files):
                if not device_files_path:
                    remote_file = self._dev.os.path.join(device_folder_location, os.path.basename(file_path))
                else:
                    remote_file = device_files_path[i]

                if not os.path.isabs(file_path):
                    file_path = os.path.join(self._dev_folder, file_path)

                conn.put_file(file_path, remote_file)
                uploaded_files_path[file_path] = remote_file

        return uploaded_files_path
    put = upload

    def get(self, remote_files, local_path=None, file_prefix='', local_folder_location='', via_cat=False, conn_name=None,
            timeout=None, cat_cmd=None, timestamp_files=False, replace=False, local_folder='', **conn_kwargs):
        """ get all files defined in files to local_path directory without doing any checks
            returns a dictionary with the keys being the same files sent and the values
            being the new names of the file on the local directory

        Args:
            local_path (str or list): if provided it will replace the original file name and default location
            remote_files (str or list of str): a filepath or a list of filepaths on the device
            file_prefix (str): prefix to set each file when downloaded to the local host
            local_folder_location (str): local host folder where to put the downloaded files.
                                         if empty we will use de default folder
            via_cat (bool): flag to indicate that we want to use the cat operator instead of a file transfer (sftp/scp)
            conn_name (str): name of connection to use
            timeout (float):
            cat_cmd (str): in case we want to use a particular cat command when doing transfers via cat
            timestamp_files (bool): to timestamp downloaded files or not
            conn_kwargs (dict): user, interface and tunnel to pass to open method of connection

        Returns:

        """

        files_received = dict()
        remote_files = utils.lists.to_sequence(remote_files)
        local_folder_location = local_folder_location or local_folder
        local_path = utils.lists.to_sequence(local_path) if local_path else []

        if local_path and len(local_path) != len(remote_files):
            raise ValueError('Number of files path do not match between local and remote')

        if not local_folder_location:
            self.check_or_create_device_folder()
            local_folder_location = self._dev_folder
        else:
            local_folder_location = os.path.normpath(local_folder_location)

        conn_name = conn_name or conn_kwargs.pop('name', None)
        with self._dev.conn.get_open_instance(name=conn_name, open_if_close=True, **conn_kwargs) as conn:

            get_file, kwargs = get_file_func_and_args(cat_cmd or self._dev.os.cmd.CAT, conn, timeout, via_cat)

            for file_name in [f.strip() for f in remote_files]:

                local_name = get_local_name_from_file_path(file_name, file_prefix, local_folder_location,
                                                           timestamp_files, replace)

                try:
                    kwargs['replace'] = replace
                    get_file(file_name, local_name, **kwargs)
                    files_received[file_name] = local_name

                except IOError:
                    log.exception("error with local IO... when getting file: " + file_name)
                    pass

                except Exception:
                    log.exception("error with getting file:  " + file_name)
                    pass

        return files_received

    get_via_cat = functools.partialmethod(get, via_cat=True)

    def open_new_file(self, filepath, mode, is_singleton=False, **kwargs):

        filepath_orig = filepath

        if not os.path.split(filepath)[0]:
            self.check_or_create_device_folder()
            filepath = os.path.join(self._dev_folder, filepath)

        filepath_index = utils.files.indexed_name_if_file_exists(filepath)

        with self.manager_lock:
            if is_singleton:
                filepath_id = filepath_orig
            else:
                filepath_id = filepath_index

            if filepath_id not in self._file_handlers_open:
                handler = FileHandlerWrapper(filepath_id, open(filepath_index, mode, **kwargs), self)
                self._file_handlers_open[filepath_id] = handler
                return handler
            else:
                raise exceptions.FileAlreadyOpenOnDeviceError

    def get_open_file_handler(self, filepath):
        return self._file_handlers_open[filepath]

    def close_file(self, filepath):
        with self.manager_lock:
            if filepath not in self._file_handlers_open:
                raise exceptions.FileNotOpenOnDeviceError('This file path is not open at the moment')
            self._file_handlers_open[filepath].close_on_manager_del()
            del self._file_handlers_open[filepath]

    def close_file_if_open(self, filepath):
        try:
            self.close_file(filepath)
        except exceptions.FileNotOpenOnDeviceError:
            pass

    def close_all(self):
        for filepath in list(self._file_handlers_open):
            try:
                self.close_file(filepath)
            except Exception:
                log.exception('problems closing file: ' + filepath)

