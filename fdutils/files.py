import collections
import functools
import glob
import logging
import os
import re
import time
from datetime import datetime

from fdutils.strings import get_string_index_info

log = logging.getLogger(__name__)


def slugify(text, delim='_', lowercase=True):
    """ simple slugify of text """
    text = str(text).strip()

    _punct_re = re.compile(r'[\s!"#$%&\'()*\-/<=>?@\[\\\]^_`{|},\.;:]+')

    """Generates an slightly worse ASCII-only slug."""
    result = []
    if lowercase:
        text = text.lower()
    for word in _punct_re.split(text):
        if word:
            result.append(word)
    return str(delim.join(result))


def get_filename_suffixed(file_path, suffix, sep='_', is_folder=False):
    """ returns a filename suffixed with a word (before extension)

    Args:
        file_path: filename to sufix (ie: myfile.ext)
        suffix: suffix to add to filename (ie: suffix='new' then result will be myfile_new.ext
        sep: separates the old filename with the suffix

    Returns:

    """
    if not is_folder:
        name, ext = os.path.splitext(file_path)
    else:
        name = file_path
        ext = ''
    return name + sep + suffix + ext


def get_filename_timestamped(file_path, timestamp=None, is_folder=False):
    """ stamp a filename with an added timestamp or string (new_stamp) between the filename and the extension

    """
    return get_filename_suffixed(file_path, timestamp or get_timestamp(), is_folder=is_folder)


def _get_filename_index_info(file_path, is_folder):
    """ stamp a filename with an added indexed incremented to what it had before

    """
    if not is_folder:
        name, ext = os.path.splitext(file_path)
    else:
        name = file_path
        ext = ''
    return get_string_index_info(name) + (ext,)


def _get_filename_index_value(file_path):
    """ stamp a filename with an added indexed incremented to what it had before

    """
    file_idx_re = re.compile(r'^(?P<name>.+?)_(?P<idx>\d+)$')
    name, ext = os.path.splitext(file_path)
    m = file_idx_re.match(name)
    if m:
        return int(m.group('idx'))
    else:
        return -1


def get_filename_indexed(file_path, is_folder=False):
    """ stamp a filename with an added indexed incremented to what it had before

    """
    name, underscore, idx, ext = _get_filename_index_info(file_path, is_folder)

    if idx is None:
        idx = 0

    name = name + underscore
    highest_idx_file = sorted(glob.glob('{}*{}'.format(name, ext)),
                              key=lambda x: _get_filename_index_value(x), reverse=True)
    if highest_idx_file:
        name, underscore, idx, ext = _get_filename_index_info(highest_idx_file[0], is_folder)
        name = name + underscore
        if idx is None:
            idx = 0

    return '{}{:02d}{}'.format(name, idx + 1, ext)


def split_filepath_into_components(file_path):
    """ splits a file path a/b/c/d/e into a list of [a,b,c,d,e]

    :param file_path:
    :return:
    """
    folders = []
    while 1:
        file_path, folder = os.path.split(file_path)

        if folder != "":
            folders.append(folder)
        else:
            if file_path != "":
                folders.append(file_path)

            break

    folders.reverse()
    return folders


def duplicate_file_with_stamp(file_path):
    """ make a copy of a file name on the same folder. Time stamp the new file if no new file name is given.

    """
    import shutil

    new_file_name = get_filename_timestamped(file_path)
    shutil.copy(file_path, new_file_name)
    return new_file_name


def replace_text_in_file(file_path, replace_this, for_that, case_insensitive=False, is_regex=False, keep_copy=False,
                         number_of_subs=0):
    """ replace a string or regex (if is_regex is set) from a file given in file_path, with another string.

        This is a replacement for sed if needed.

    @param str file_path: path to the file to be changed
    @param str replace_this: string or regex to match and replace
    @param str for_that: string that will replace the match
    @param bool case_insensitive: flag to indicate if case is important
    @param bool is_regex: flag to indicate if replace_this is a regular expression or a plain string
    @param bool keep_copy: flag to keep copy of original file or not. The original file will be timestamped
    @param int number_of_subs: number of times to do the substitution. A zero means replace all
    @rtype: tuple

    """

    if not is_regex:
        replace_this = re.escape(replace_this)

    new_file_path = duplicate_file_with_stamp(file_path) if keep_copy else file_path

    import fileinput

    for current_line in fileinput.input(file_path, inplace=True):
        current_line, num_subs_made = re.subn(replace_this, for_that, current_line,
                                              flags=(re.IGNORECASE if case_insensitive else 0), count=number_of_subs)
        number_of_subs = 0 if not number_of_subs else (number_of_subs - num_subs_made)

    return file_path, new_file_path


def seconds_to_hour_min_sec(secs):
    """ simple formatter

    :param secs:
    :return:
    """
    hours = int(secs / 3600)
    secs -= hours * 3600
    mins = int(secs / 60)
    secs -= mins * 60
    return '{:02d}:{:02d}:{:02d}'.format(hours, mins, int(secs))


def get_timestamp():
    from time import strftime
    return strftime('%Y%m%d_%H%M%S')


def get_files_sorted_by_creation(dirpath, match="*.*", reverse=False):
    from stat import S_ISREG, ST_CTIME, ST_MODE

    # get all entries in the directory w/ stats
    entries = (os.path.join(dirpath, fn) for fn in glob.glob(dirpath + "/" + match))
    entries = ((os.stat(path), path) for path in entries)

    # leave only regular files, insert creation date
    entries = ((stat[ST_CTIME], path) for stat, path in entries if S_ISREG(stat[ST_MODE]))

    return sorted(entries, reverse=reverse)


class Tailer:
    """ Implements tailing and heading functionality like GNU tail and head commands. """
    line_terminators = ('\r\n', '\n', '\r')

    def __init__(self, file_name, read_size=1024, num_lines=0, end=True):
        self.read_size = read_size
        self.file = file_name
        self.start_pos = self.file.tell()
        self.num_lines = num_lines
        self.captured_data = []
        if end:
            self.seek_end()

    def seek_end(self):
        self.captured_data = []
        self.seek(0, 2)

    def seek(self, pos, whence=0):
        self.file.seek(pos, whence)

    def read(self, read_size=None):
        if read_size:
            read_str = self.file.read(read_size)
        else:
            read_str = self.file.read()

        return len(read_str), read_str

    def seek_line(self):
        """\
        Searches backwards from the current file position for a line terminator
        and seeks to the character after it.
        """
        pos = end_pos = self.file.tell()
        read_size = self.read_size
        if pos > read_size:
            pos -= read_size
        else:
            pos = 0
            read_size = end_pos

        self.seek(pos)

        bytes_read, read_str = self.read(read_size)

        if bytes_read and read_str[-1] in self.line_terminators:
            # The last charachter is a line terminator, don't count this one
            bytes_read -= 1

            if read_str[-2:] == '\r\n' and '\r\n' in self.line_terminators:
                # found crlf
                bytes_read -= 1

        while bytes_read > 0:
            # Scan backward, counting the newlines in this bufferfull
            i = bytes_read - 1
            while i >= 0:
                if read_str[i] in self.line_terminators:
                    self.seek(pos + i + 1)
                    return self.file.tell()
                i -= 1

            if pos == 0 or pos - self.read_size < 0:
                # Not enought lines in the buffer, send the whole file
                self.seek(0)
                return None

            pos -= self.read_size
            self.seek(pos)

            bytes_read, read_str = self.read(self.read_size)

        return None

    def iterator(self):
        """\
        Return the last lines of the file.
        """
        i = 1

        while True:
            prev_pos = self.file.tell()
            new_pos = self.seek_line()
            if not new_pos:
                new_pos = 0

            data = self.file.read(prev_pos - new_pos)
            self.seek(new_pos)
            if data:
                i += 1
                self.captured_data.append(data.strip())
                yield data.strip()
                if not new_pos or (self.num_lines and i > self.num_lines):
                    raise StopIteration()
            else:
                raise StopIteration()

    def __iter__(self):
        return self.iterator()

    def close(self):
        self.file.close()


def get_gmt_offset_by(timestr, seconds):
    """  returns a gmt time as string with some seconds added to it

    """
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(timestr) + seconds))


def name_if_file_exists(full_path_filename, add_index=False):
    """ Checks if the filename (full path) exists and add a timestamp if it does or an index.
        It does not change the name of an existing file, this will usually be used as the name of file

    Args:
        add_index (bool):
        full_path_filename (str):

    Returns:
        str: the new name for the file if there was a file with the same name, if not, return the same full_path_filename
    """
    if not os.path.exists(full_path_filename):
        return full_path_filename

    new_full_path_filename = full_path_filename
    tries = 0

    while os.path.exists(new_full_path_filename) and tries < 10:
        if add_index:
            new_full_path_filename = get_filename_indexed(new_full_path_filename)
        else:
            new_full_path_filename = get_filename_timestamped(full_path_filename)

        log.debug('File already exists. Will check ' + new_full_path_filename)

        tries += 1

    if tries >= 10:
        raise Exception('There must be some racing condition as we tried using 10 different timestamp and '
                        'they did not work. Check your code for any threading/multiprocess issue !!')

    return new_full_path_filename

indexed_name_if_file_exists = functools.partial(name_if_file_exists, add_index=True)


def json_utils_default(obj):
    """ defaults function used by json.dumps function to make datetime values javascript compatible

    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def get_process_id(name, args=None):
    """ try to find the process which name starts with name and with arguments given by args

    @rtype: psutil.Process or None

    """
    import psutil
    for pid in psutil.get_pid_list():
        try:
            proc = psutil.Process(pid)
        except psutil.error.NoSuchProcess:      # in case a process dies in the middle of this
            continue
        if proc.name.find(name) >= 0:
            pass
        if proc.name.find(name) >= 0 and args and args == proc.cmdline[1:]:
            return proc
    return None


def are_objects_the_same(a, b, attrib=None):
    """ utility for __eq__ comparison for objects

    :param a: object a (self in __eq__)
    :param b: object b (other in __eq__)
    :param list or tuple attrib: list of attributes to compare objects. If none we will use vars to retrieve the attributes from a (self)

    """
    if attrib is None:
        attrib = vars(a)
    for att in attrib:
        if not getattr(a, att) == getattr(b, att):
            return False
    return True


def cmd_output_split_parser(out, columns=(), starts_at=0, stops_at=0, split_re='\s+', column_info_at=-1,
                            start_after_columns_line=False):
    """  Function to parse the output from a command in a shell

    :param out: list with the values separated by split_re regex
    :param columns: list of column names
    :param starts_at: line where to start reading from
    :param stops_at: line where to stop reading at. This will usually be zero to mean read all or negative to read until the last N line
    :param split_re: the regex expression to use to split the values
    :param column_info_at: if we want to retrieve the information about the columns from a line instead of from the columns argument
    :param start_after_columns_line: this will try to find the start where the columns line is by finding a line with the columns values given on the argument columns
    :return: dictionary with the key being the first column and the value being either a dictionary with the keys being the columns from 1
    """
    def add_columns(key, values):
        if not key in ret:
            ret[key] = dict()
        for i, c in enumerate(columns[1:]):
            if i > len(values):
                return
            ret[key][c] = values[i]

    continuation = re.compile('^\s{4,}')
    ret = collections.OrderedDict()
    last = ''
    split_number = len(columns) - 1
    stop = len(out) if not stops_at else stops_at

    if column_info_at != -1:
        columns = re.split(split_re, out[column_info_at])
    elif start_after_columns_line:
        column_i = [v.lower() for v in columns]
        found = False
        for starts_at, line in enumerate(out):
            if column_i == [v.lower() for v in re.split(split_re, line, split_number)]:
                found = True
                starts_at += 1
                break
        if not found:
            raise Exception('Header Columns not found')

    if len(out) > starts_at:
        for v in out[starts_at:stop]:
            # check if line is empty:
            if not v.strip():
                continue
            # check if line is continuation:
            if continuation.match(v):
                add_columns(last, re.split(split_re, v, split_number))
                continue
            a = re.split(split_re, v, split_number)
            last = a[0]
            if len(a) > split_number:
                add_columns(last, a[1:])
            elif len(a) == 1:
                ret[a[0]] = dict()
    # as the prompt changes with the cd we need a way to remove the prompt element added that was not removed during the expect processing
    return ret


def return_list_of_files_sorted_by_date(folder, newest_first=True, count=None, extension='', include_folder=True, starts_with=''):
    """

    :param folder: folder where files are located
    :param newest_first: date sorted
    :param count: how many to return or None to return all
    :param starts_with: if given we will filter files by files that starts with this string
    :return:
    """
    from stat import S_ISREG, ST_CTIME, ST_MODE
    import os

    # get all entries in the directory w/ stats
    entries = (os.path.join(folder, fn) for fn in os.listdir(folder) if fn.startswith(starts_with) and fn.endswith(extension))
    entries = ((os.stat(path), path) for path in entries)

    # leave only regular files, insert creation date
    entries = ((stat[ST_CTIME], path)
               for stat, path in entries if S_ISREG(stat[ST_MODE]))

    if count is not None and count <= 0:
        count = None
    if include_folder:
        return [path for cdate, path in sorted(entries, reverse=newest_first)[:count]]
    else:
        return [os.path.basename(path) for cdate, path in sorted(entries, reverse=newest_first)[:count]]


def modify_filename(filename_path, prepend='', append='', timestamp=False):
    """ modifies the filename part of a path

    """
    filepath, filename_whole = os.path.split(filename_path)
    filename, ext = os.path.splitext(filename_whole)
    new_filename_path = os.path.join(filepath, prepend + filename + append + ext)
    if timestamp:
        return get_filename_timestamped(new_filename_path)
    return new_filename_path


def set_attribute_against_dict(self, info, dictionary):
    """ sets attributes values to an object

    :param info:
    :param dictionary:
    :return:
    """
    for key, val in info.items():
        if key in dictionary:
            setattr(self, dictionary[key], val)


def utc_now():
    """ type helper function

    :return:
    """
    return datetime.utcnow().replace(microsecond=0)


def md5_checksum_stream(s):
    """ calculate md5 for a stream in case of a large file that cannot be hold in memory

    :param s: stream
    :return:
    """
    import hashlib
    m = hashlib.md5()
    while True:
        data = s.read(8192)
        if not data:
            break
        m.update(data)
    return m.hexdigest()


def md5_checksum(filePath):
    """ calculates md5 using the md5_checksum_stream function

    :param filePath:
    :return:
    """
    with open(filePath, 'rb') as fh:
        return md5_checksum_stream(fh)

# following functions modified
# from selenium.driver.firefox.webdriver.py

# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

def get_default_windows_location(exec_names, win_program_file_loc):
    program_files = [os.getenv("PROGRAMFILES", r"C:\Program Files"),
                     os.getenv("PROGRAMFILES(X86)", r"C:\Program Files (x86)")]
    for path in program_files:
        for file in exec_names:
            for filepath in sorted(glob.glob(os.path.join(path, win_program_file_loc, file)),
                               key=lambda x: len(x), reverse=True):
                if os.access(filepath, os.X_OK):
                    return filepath
    return ""


def find_exe_in_registry(keys):
    if not keys:
        return ""
    try:
        from _winreg import OpenKey, QueryValue, HKEY_LOCAL_MACHINE, HKEY_CURRENT_USER
    except ImportError:
        from winreg import OpenKey, QueryValue, HKEY_LOCAL_MACHINE, HKEY_CURRENT_USER
    import shlex
    command = ""
    for path in keys:
        try:
            key = OpenKey(HKEY_LOCAL_MACHINE, path)
            command = QueryValue(key, "")
            break
        except OSError:
            try:
                key = OpenKey(HKEY_CURRENT_USER, path)
                command = QueryValue(key, "")
                break
            except OSError:
                pass
    else:
        return ""

    if not command:
        return ""

    return shlex.split(command)[0]


def get_executable_path(exec_names, osx_default_start_cmd=None, win_program_file_loc='', registry_keys=()):
    """Return the command to start firefox."""
    import platform
    import os
    import sys
    import shutil

    if isinstance(exec_names, str):
        exec_names = [exec_names]

    # try which first
    for name in exec_names:
        path = shutil.which(name)
        if path:
            return path

    err_msg = "Could not find {} in your system PATH. Please specify the binary location or install or add to PATH" \
              "".format(exec_names)
    start_cmd = None

    # try finding on common places
    if platform.system() == "Darwin" and osx_default_start_cmd:
        start_cmd = osx_default_start_cmd
        if not os.path.exists(start_cmd):
            start_cmd = os.path.expanduser("~") + start_cmd
    elif platform.system() == "Windows":
        start_cmd = find_exe_in_registry(registry_keys)
        if not start_cmd and win_program_file_loc:
            start_cmd = get_default_windows_location(exec_names, win_program_file_loc)
    elif platform.system() == 'Java' and 'nt' in sys.builtin_module_names:
        start_cmd = get_default_windows_location(win_program_file_loc)

    if not start_cmd:
        raise RuntimeError(err_msg)

    return start_cmd


def csv_data_class(filepath, index_by, headers=(), headers_mapping=None, csv_has_headers=True):
    """ function to convert a csv into a dictionary with the keys being defined by index_by and the values
        being a SimpleNamespace instance

    Args:
        filepath (str):
        index_by (str):
        headers (list or tuple):
        headers_mapping (dict): a dictionary to map the headers name to new names
        csv_has_headers (bool):

    Returns:

    """
    import types
    import csv

    if not csv_has_headers and not headers:
        raise Exception('There were no headers provided and you say that csv does not have headers')

    results = {}

    with open(filepath, newline='') as csvf:
        reader = csv.reader(csvf)
        csv_headers = []
        while csv_has_headers and not csv_headers:
            try:
                csv_headers = next(reader)
            except StopIteration:
                raise Exception("There does not seem to be anything in this csv file")

        headers = headers or csv_headers

        if headers_mapping:
            headers = [headers_mapping.get(h, h) for h in headers]

        for row in reader:
            d = dict(zip(headers, row))
            key = d.pop(index_by)
            if key in results:
                raise Exception('We cannot have duplicate indexes')
            results[key] = types.SimpleNamespace(**d)

    return results
