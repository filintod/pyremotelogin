from datetime import datetime

from .. import base
from . import shellcommands
import fdutils
import re

import logging
import collections
log = logging.getLogger(__name__)


class UnixOS(base.OSBase):
    """
    """
    shell_cmds_module = shellcommands
    gnu_path = ''   # path to gnu commands that on solaris is usually different to linux
    dev_null = '/dev/null'
    temp = '/tmp'
    ssh_app = "ssh"
    shell_app = "/bin/bash -i"
    sudo = 'sudo'
    name = 'unix'

    def __init__(self, **kwargs):
        kwargs.setdefault('can_change_prompt', True)
        super(UnixOS, self).__init__(**kwargs)

    @property
    def path(self):
        import posixpath
        return posixpath

    def get_ping_response(self, host, count=4, interface='', size=64, conn=None):

        with conn:
            o, e = conn.send_cmd(self.cmd.ping(host, count, interface, size))

        if o[-1].get_img_coord('bad address ') >= 0:
            # bad hostname (couldnot resolve)
            raise Exception('Bad host ' + o[-1])

        lost_re = re.compile(r'^(?P<sent>\d+)[\w\s]+,\s+(?P<receive>\d+)[\w\s]+,\s+(?P<lost>\d+)')
        m = lost_re.match(o[-1])
        rtt = ()
        if lost_re.match(o[-1]):
            # we lost all packets
            packets = (m.group('sent'), m.group('receive'), m.group('lost'))
        else:
            m = re.search(r'(?P<min>[\d\.]+)/(?P<avg>[\d\.]+)/(?P<max>[\d\.]+)\s+ms$', o[-1])
            rtt = (m.group('min'), m.group('avg'), m.group('max'))
            m = lost_re.match(o[-2])
            packets = (m.group('sent'), m.group('receive'), m.group('lost'))
        return packets, rtt

    def tail_file_until(self, filename, start_pattern, callback, copy_pattern='', stop_pattern='', time_to_wait=None,
                        read_from=10, conn=None):
        """ Funtion to tail a text (like a log file) file until a pattern is shown and then call the callback function and return

        @param filename: file path on device that we want to tail to
        @param start_pattern: regex that we want to start copying from. If no stop_pattern, then this will be the stop pattern
        @param copy_pattern: regex to copy lines from
        @param stop_pattern: regex to indicate the last line to copy and return
        @param callback: function name to call when we find the pattern
        @param time_to_wait: optional parameter to define how many seconds to let the tail go on
        @param read_from: number of lines to start the tail from, so when we execute this command we will start x lines from the last

        Return:
            It does not return any value but calls a function when it finishes if it does not time outs first

        Exceptions:
            Raises exception if it times out

        """
        log.debug('Tailing File {0} for pattern "{1}" for {2}'.format(filename, stop_pattern, str(time_to_wait)))

        if not stop_pattern:
            cmd = """sh -c '{0} -f -n {1} {2} | awk "/{3}/ {{print; exit;}}" ' """.format(
                self.cmd.tail(), read_from, filename, start_pattern)
        else:
            cmd = ("""sh -H -c ''{0} -f -n {1} {2} |
            awk "{{ if (/{3}/ && !triggered) {{ triggered=1; print; }}
                    else {{ if (triggered && /{4}/) {{ print; if (/{5}/) {{ exit; }} }} }} }}"' """.
                   format(self.cmd.tail(self.gnu_path), read_from, filename, start_pattern,
                          copy_pattern, stop_pattern))

        with conn:
            return conn.send_cmd(cmd).expect_prompt(timeout=time_to_wait)

    # TODO: fix!!!! extracted from connections.terminal.
    def _can_execute_as_sudo(self, cmd):
        """ checks if cmd is one of the sudo commands available.
        The parsing of the sudo list will leave arguments out to compare. So this check is not exhaustive.

        :param cmd:
        :return:
        """

        def _check():
            # TODO: do a better check of command with command line arguments instead of only the first split
            # TODO: add more checks against command line arguments
            return (self._channels[-1].sudo_list[0] == 'ALL' or
                    cmd in self._channels[-1].sudo_list or cmd.split()[0] in self._channels[-1].sudo_list)

        if cmd == '-l' or (self._channels[-1].sudo_list and _check()):
            return True

        if not self._channels[-1].sudo_list:
            # retrieve shell sudo list
            sudo_cmds, err = self.check_output('-l', use_sudo=True, return_type='list', stderr_to_tmp=False)
            start_sudo = False
            for sudo_cmd in sudo_cmds:
                if start_sudo:
                    sudo_cmd = sudo_cmd.strip()
                    if re.match(r'\([^\)]+\) ALL', sudo_cmd):
                        self._channels[-1].sudo_list = ['ALL']
                        return True
                    self._channels[-1].sudo_list.append(sudo_cmd.split(' ')[2])
                elif sudo_cmd.get_img_coord('may run the following commands on this host') > -1:
                    start_sudo = True

            return _check()

        return False

    def get_tcp_connections_as_dict(self, conn=None, family='', state='', **kwargs):
        """ gets tcp connections and return it as a dictionary like d['LISTEN'] = a list of dictionary objects with keys local_ip, local_port, remote_ip and remote_port

        :param conn:
        :param family:
        :param state:
        :return:
        """
        connections, e = conn.check_output(self.get_tcp_connections(state=state, as_text=True, family=family, filter_netstat_stderr=True, **kwargs))
        ret = collections.defaultdict(list)
        for conn in connections:
            local_addr, external_addr, state = conn.split()
            local_ip, local_port = local_addr.split(':')
            external_ip, external_port = external_addr.split(':')
            ret[state].append(dict(local_ip=local_ip, local_port=local_port, remote_ip=external_ip, remote_port=external_port))
        return ret

    # TODO : this command can be made into a one unix-liner so it can be a regular @cmd method
    def get_uptime(self, conn=None):
        """ get current uptime of system in days, hours, minutes

         @rtype: tuple: days, hours, minutes
        """
        conn = self.open_default_connection() if conn is None else conn
        out, err = conn.send_command("uptime | awk '{print $3, $4, $5}'")
        uptime = out[0].replace(',', '').strip().split()
        if uptime[1].startswith('day'):
            days = uptime[0]
            hours_min = uptime[2]
        else:
            days = 0
            hours_min = uptime[0]
        hours_min = hours_min.split(':') if ':' in hours_min else [0, hours_min]
        return int(days), int(hours_min[0]), int(hours_min[1])

    def tcp_get_connections_from_list(self, netstat_cmd, netstat_listen_cmd, sep, all_interfaces=r'\*', conn=None):
        """ Convert return list of tcp connection pairs from the netstat command. The list would look like:

        10.10.13.35:22 10.10.13.24:17520 on linux (sep=:)
        127.0.0.1.38912 127.0.0.1.5432 on solaris (sep=.)
        """
        connections = []

        # TODO: maybe put all commands to be sshed into one line separated by semi-colon, or implement a multicommand 'send_command' function tha returns a list of results for every command
        # split netstat listen addresses to get the ports and addresses it is listening on:
        o, e = conn.check_output(netstat_listen_cmd)    # o is output string, e is error
        listening_on = collections.defaultdict(list)
        if not e and o:
            for line in o:
                ip, port = line.strip().rsplit(sep, 1)
                if ip == all_interfaces:
                    ip = 'ALL'
                listening_on[ip].append(port)

        # split netstat response pair
        o, e = conn.check_output(netstat_cmd)
        if not e and o:
            for line in o:
                ips = line.strip().split()
                ip_1, port_1 = ips[0].rsplit(sep, 1)     # local ip and port
                ip_2, port_2 = ips[1].rsplit(sep, 1)
                if port_1 in listening_on['ALL'] or (ip_1 in listening_on and port_1 in listening_on[ip_1]):     # this is a connection to a local service
                    tcp = fdutils.structures.TcpConnection(ip_1, port_1, ip_2, port_2)
                else:
                    tcp = fdutils.structures.TcpConnection(ip_2, port_2, ip_1, port_1)
                connections.append(tcp)

        return connections

    def get_all_my_current_inet_addresses(self, conn=None):
        inet, err = self.send_command(r"ifconfig -a|grep 'inet '|awk '!/(127\.0\.0\.1|::1)/ {print $2}'")
        addresses = []
        if inet:
            for addr in inet:
                addresses.append(addr.strip().split(':')[-1])
        return addresses

    def file_system_disk_space(self):
        out, err = self.send_command('df -h')
        return fdutils.files.cmd_output_split_parser(out,
                                                   ('filesystem', 'size', 'used', 'available', 'use', 'mounted_on'), 1)

    def md5sum_clean(self, data):
        if 'no such file' in data.lower():
            raise ValueError('No MD5 sum or no file found')
        return data.split()[0].lower()

    def get_info_from_list_file(self, dir_data, filename):
        for line in dir_data.splitlines():
            if filename in line:
                mode, _, gowner, owner, size, modify_date, modify_time, name = line.split()
                modify_datetime = datetime.strptime('{date} {time}'.format(date=modify_date, time=modify_time),
                                                    '%Y-%m-%d %H:%M',)

                return modify_datetime, size
        raise FileExistsError('did not find the file')

