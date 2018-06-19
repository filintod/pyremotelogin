from .. import base
import re

import fdutils

__author__ = 'Filinto Duran (duranto@gmail.com)'

import logging
log = logging.getLogger(__name__)


class UnixShellCmds(base.OSCommands):

    BIN = '/bin/'
    SUDO_BIN = '/sbin/'
    USR_BIN = '/usr' + BIN
    USR_SUDO_BIN = '/usr' + SUDO_BIN

    CAT = 'cat'
    HAS_BASE64 = True

    def disable_history(self):
        return "set +o history"

    def enable_history(self):
        return "set -o history"

    def set_prompt(self, prompt):
        return "export PS1='{}'".format(prompt)

    def exit_status(self):
        return "echo $?"

    def cat_to_file(self, file_path, message, delimiter='$$$FILE_DELIMITER_DEVICECONN$$$'):
        return 'cat > {path} << {delim}\n{message}\n{delim}'.format(path=file_path, delim=delimiter, message=message)

    def file_size(self, file_path):
        return "ls -lt {} |awk '{{print $5}}'".format(file_path)

    def nohup_cmd(self, cmd, *args, **kwargs):
        return self.detached_cmd(cmd, *args, **kwargs)

    def detached_cmd(self, cmd, *args, **kwargs):
        """ executes a command detached from the caller (to be run in the background)
        """
        return "{} </dev/null >/dev/null &".format(cmd)

    def list_directories(self, name='*', root_folder='/', recursive=False, newest_first=True, details=False):
        flags = '-d' + ('u' if recursive else '') + ('t' if newest_first else '') + ('l' if details else '')
        return 'ls {} {}/{}/'.format(flags, root_folder, name)

    def get_newest_directory(self, name='*', folder='/', details=False):
        ls = self.list_directories(name=name, root_folder=folder, details=details)
        return ls + ' | awk "NR==1 {print}"'

    def get_newest_file(self, name='*', folder='~', details=False):
        flags = '-t' + ('l' if details else '')
        return 'ls {} {}/{} | awk "NR==1 {{print}}"'.format(flags, folder, name)

    def netstat(self, protocol='tcp', family=''):
        """ OS specific to call netstat

        :param protocol: 'tcp' or 'udp'
        :param family: 'inet' (default), 'inet6'

        """
        protocol = '--' + protocol if protocol else ''
        family = (' -A ' + family) if family else ''
        return 'netstat -an ' + protocol + family

    def get_tcp_connections(self, state='', filter_loopback=True, family='', filter_netstat_stderr=False, **kwargs):
        """ get all connections using a series of netstat and grep

        :param state: if given it will only return information about tcp sockets on this state (LISTEN, ESTABLISHED, SYN-SENT, SYN-WAIT, SYN-ACK, CLOSE-WAIT, etc.)
                      it can be more than one state if separated by pipes as bit-wise ORs i.e. LISTEN|ESTABLISHED
        :return:
        """
        filter_loopback = r"!/(127\.0\.0\.1|::1)/" if filter_loopback else ''

        filter_by_state = ("|grep -E '(" + state + ")'") if state else ''

        return "{} {}|awk '{} {{print $4, $5, $6}}'".format(
            self.netstat('tcp', family=family),
            filter_by_state, filter_loopback)

    def ping(self, host, count=4, interface='', size=64):
        # 1 packets transmitted, 0 packets received, 100% packet loss

        if interface:
            interface = ('-I ' + interface)
        return "ping -c {} -s {} {} {}".format(count, size, interface, host)

    def tail(self, gnu_path):
        return gnu_path + 'tail '

    def add_user_to_group_linux_only(self, username, group_name):   # linux
        return '/usr/sbin/usermod -a -G {0} {1}'.format(group_name, username)

    def set_environment_variable(self, variable, value, append_to=False):

        append = '${' + variable + '}:' if append_to else ''
        return 'export {}={}{}'.format(variable, append, value)

    def remove_environment_variable(self, variable):
        return 'unset ' + variable

    def add_group_to_user(self, username, group_name):   # linux and solaris
        # TODO: see if there is a nicer way instead of this cumbersome one
        return ('/usr/bin/groups {0}|awk \'BEGIN{{ORS=""}}{{print $1;for(i=2;i<=NF;i++){{printf ","$i}};'
                'print ",{1}"}}\'|xargs -I GGROUPSS /usr/sbin/usermod -G GGROUPSS {0}'.format(username, group_name))

    # TODO: this will not remove the primary group
    def remove_user_from_group(self, username, group_name):   # linux and solaris
        # TODO: see if there is a nicer way instead of this cumbersome one
        return ('/usr/bin/groups {0} | sed \'s/{1}//\' | awk \'BEGIN{{ORS=""}}{{print $1;for(i=2;i<=NF;i++){{printf ","$i}};'
                '}}\'| xargs -I GGROUPSS /usr/sbin/usermod -G GGROUPSS {0}'.format(username, group_name))

    def change_user_home_dir(self, username, new_home):
        return 'usermod -m -d {} {}'.format(new_home, username)

    def get_user_groups(self, username):
        return '/usr/bin/groups ' + username

    def get_nic_information(self):
        # TODO: ALL
        pass

    def get_routing_table(self):
        # TODO: ALL
        pass

    def split_string_into_case_insensitive_regex(self, string):
        """ Linux/Solaris unified way to do a case insensitive comparison
        """
        new_str = ""
        for c in string:
            new_str += "[" + c.lower() + c.upper() + "]"
        return new_str

    def add_host(self, ip_addr, host_name):
        return 'echo "{} {}" >> /etc/hosts'.format(ip_addr, host_name)

    def sub_in_file(self, replace_this, for_that, file_path, new_file_path=None, case_insensitive=False,
                    only_lines_matching='', is_regex=False, get_copy=False, append_if_no_match=False):
        """
            @param DeviceBase self: an instance of Device and in particular a kind of *nix device
            @param str replace_this: the value we want to replace. If the flag is_regex is set to True then we would not try to escape characters
            @param str for_that: string to replace the match for
            @param str file_path: path to file to replace string on
            @param bool is_regex: flag to indicate if the search should be as a literal (is_regex is False) or as a regex
            @param str new_file_path: if we are creating a copy of the file and doing the substitution on that file
            @param bool append_if_no_match: flag to indicate if we will append the for_that if we don't find any matches for replace_this
            # we don't use sed -i because it might fail in the middle and leave a messed up file, rare event but could happen
        """
        if not is_regex:
            replace_this = re.escape(replace_this)
            only_lines_matching = re.escape(only_lines_matching)

        if not new_file_path:
            new_file_path = file_path

        if get_copy:
            if not self.get_files(self, file_path):
                log.error('Problems getting the copy of the file ' + file_path)
                return False

        if case_insensitive:
            replace_this = self.split_string_into_case_insensitive_regex(replace_this)

        only_lines_matching = '/{}/ '.format(self.split_string_into_case_insensitive_regex(only_lines_matching)) \
            if only_lines_matching else ''

        if append_if_no_match:
            return """sed -e '{0}s/{1}/{2}/' -e t -e '1 s/^./{2}/' {3} > {3}.bak && mv {3}.bak {4}"""\
                   .format(only_lines_matching, replace_this, for_that, file_path, new_file_path)
        else:
            return "sed '{0}s/{1}/{2}/g' {3} > {3}.bak && mv {4}.bak {4}".format(only_lines_matching, replace_this,
                                                                               for_that, file_path, new_file_path)

    def snoop(self, *args):
        return "/usr/sbin/snoop " + fdutils.lists.join_as_str(' ', args)

    def get_start_snoop_to_file_cmd(self, filename, max_packets, device, bpf_filter=''):
        """ OS specific function to start snoop command as call by device

        """
        return (' -s ' + str(1500) +
                ' -w ' + filename +
                ' -c ' + str(max_packets) +
                ' -i ' + device +
                ' "' + bpf_filter + '"')

    def find_process(self, process_name):
        return "ps -ef | grep {} | grep -v grep | awk '{{print $2}}'".format(process_name)

    def kill_process(self, process_name):
        return self.find_process(process_name) + " | xargs -I {} kill -9 {}"

    def resize_pty(self, cols, rows):
        return "stty cols {} rows {}".format(cols, rows)

    def base64(self, file):
        return 'base64 "{}"'.format(file)

    def _base64_to_file(self, base64file, file_decoded, encode):
        return 'base64 {} "{}" > "{}"'.format(encode, base64file, file_decoded)

    def base64_encode_to_file(self, file_decoded, base64file):
        return self._base64_to_file(file_decoded, base64file, '')

    def base64_decode_to_file(self, base64file, file_decoded):
        return self._base64_to_file(base64file, file_decoded, '-d')

    def md5checksum(self, file_path):
        return 'md5sum "{}"'.format(file_path)
    md5sum = md5checksum

    def remove(self, file_path, force=True):
        flags = '-f' if force else ''
        return "rm {flags} {file_path}".format(flags=flags, file_path=file_path)

    def list_file(self, file_path):
        return "ls -l --time-style long-iso {}".format(file_path)

    def move(self, current_file_path, new_file_path, overwrite=True):
        cmd = 'mv '
        if overwrite:
            cmd += '-f '
        return cmd + "{} {}".format(current_file_path, new_file_path)


Instance = None


def get_instance():
    global Instance
    if Instance is None:
        Instance = UnixShellCmds()
    return Instance
