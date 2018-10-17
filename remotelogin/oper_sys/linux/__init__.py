import re
import logging
import types

from . import shellcommands

from remotelogin.connections.decorators import WithConnection
import fdutils
from .. import unix


log = logging.getLogger(__name__)
__author__ = 'Filinto Duran (duranto@gmail.com)'


class LinuxOS(unix.UnixOS):

    # standard commands as strings
    shell_cmds_module = shellcommands
    name = 'linux'

    def get_tcp_connection_pairs(self, state='ESTABLISHED', filtered_by=None, conn=None, std_err_to_null=False):
        filterby = "grep '%s'|" % filtered_by if filtered_by else ''
        netstat_cmd = r"{}|grep {}|{} awk '!/(127\.0\.0\.1|::1|netstat)/ {{print $4,$5}}'" \
                      "".format(self.cmd_netstat('tcp', as_text=True, std_err_to_null=std_err_to_null), state, filterby)
        # TODO: IPv6 address need to be better tune as ::1 might be part of another address not the loopback
        netstat_listen_cmd = r"{}|grep LISTEN|awk '!/(127\.0\.0\.1|::1|netstat)/ {{print $4}}'" \
                             "".format(self.cmd_netstat('tcp', as_text=True, std_err_to_null=std_err_to_null))
        return self.tcp_get_connections_from_list(netstat_cmd, netstat_listen_cmd, sep=':',
                                                  all_interfaces=r'(0\.0\.0\.0|::)', conn=conn)

    def is_module_installed(self, module):
        """ check if linux module is installed"""
        str_out, str_err = self.send_command('lsmod | grep ' + module)
        return bool(str_out and re.search(module, str_out))


    # TODO: it is failing on vms, maybe use textfsm
    @WithConnection()
    def ifconfig_parser(self, interface, conn=None):
        ifconfig_list = ['']

        ifconfig_re = re.compile(r"^(?P<interface>[A-z]+\d+)\s+Link\s+encap:(?P<encapsulation>[A-z]+)\s+HWaddr\s+(?P<mac>[a-fA-F\d:]+)\s+" +
                                 r"inet6? addr:(?P<ip>[\d\.:]+)\s+Bcast:(?P<bcast>[\d\.]+)\s+Mask:(?P<mask>[\d\.]+).*" +
                                 r"MTU:(?P<mtu>[\d\.]+)\s+Metric:(?P<metric>[\d\.]+)\s+" +
                                 r"RX packets:(?P<rx_packets>[\d\.]+)\s+errors:(?P<rx_errors>[\d\.]+)\s+dropped:(?P<rx_dropped>[\d\.]+)\s+overruns:(?P<rx_overruns>[\d\.]+)\s+frame:(?P<rx_frame>[\d\.]+)\s+" +
                                 r"TX packets:(?P<tx_packets>[\d\.]+)\s+errors:(?P<tx_errors>[\d\.]+)\s+dropped:(?P<tx_dropped>[\d\.]+)\s+overruns:(?P<tx_overruns>[\d\.]+)\s+carrier:(?P<tx_carrier>[\d\.]+)\s+" +
                                 r"collisions:(?P<collisions>\d+)\s+txqueuelen:(\d+)\s+" +
                                 r"RX bytes:(?P<rx_bytes>\d+)\s+\([\d\.]+ ..B\)\s+TX bytes:(?P<tx_bytes>\d+)\s+\([\d\.]+ ..B\).*")

        ifconfig_string, err = conn.check_output('ifconfig -a ' + interface)
        if not isinstance(ifconfig_string, list):
            ifconfig_string = ifconfig_string.splitlines()
        for l in ifconfig_string:
            if l.strip():
                if ifconfig_list[-1]:
                    ifconfig_list[-1] += ' '
                ifconfig_list[-1] += l
            else:
                if len(ifconfig_list[-1]):
                    ifconfig_list.append('')

        ret = dict()
        for i in ifconfig_list:
            m = ifconfig_re.match(i)

            if m:
                match_dict = m.groupdict()
                ret[match_dict.pop('interface')] = types.SimpleNamespace(**match_dict)
            else:
                log.debug('Did not match anything on:' + str(ifconfig_string))

        return ret[interface] if ret else None

    @WithConnection('root')
    def get_mem_stats(self, pid, conn=None):
        """ taken from https://raw.githubusercontent.com/pixelb/ps_mem/master/ps_mem.py

        :param pid:
        :param conn:
        :return:
        """
        out, err = conn.check_output('cat /proc/{}/smaps'.format(pid))
        Private_lines = []
        Shared_lines = []
        Pss_lines = []
        have_pss = 0
        for line in out:
            if line.startswith("Shared"):
                Shared_lines.append(line)
            elif line.startswith("Private"):
                Private_lines.append(line)
            elif line.startswith("Pss"):
                have_pss = 1
                Pss_lines.append(line)
        Shared = sum([int(line.split()[1]) for line in Shared_lines])
        Private = sum([int(line.split()[1]) for line in Private_lines])
        if have_pss:
            pss_adjust = 0.5  # add 0.5KiB as this avg error due to trunctation
            Pss = sum([float(line.split()[1]) + pss_adjust for line in Pss_lines])
            Shared = Pss - Private

        return Private, Shared

    @WithConnection()
    def free_mem(self, conn=None):
        """ gets the free command output and parses it

        :param conn:
        :return:
        """
        out, err = conn.check_output('free')
        mem = dict(total=0, used=0, free=0)
        swap = dict(total=0, used=0, free=0)
        buff = dict(total=0, used=0, free=0)
        if out:
            for line in out[1:]:
                line = line.strip()
                if line.startswith('Mem'):
                    mem['total'], mem['used'], mem['free'] = line.split()[1:4]
                elif line.startswith('Swap'):
                    swap['total'], swap['used'], swap['free'] = line.split()[1:4]
                elif line.startswith('-/+ buffers/cache:'):
                    buff['used'], buff['free'] = line[len('-/+ buffers/cache:'):].split()
        return dict(memory=mem, swap=swap, buffered=buff)

    @WithConnection()
    def file_system_space(self, conn=None, block_size='m'):
        """ parses the output for df and uses the block_size (k or m)

        :param conn:
        :param bytes_flag:
        :return:
        """
        out, err = conn.check_output('df -' + block_size)
        fs = dict()
        if out:
            for line in out[1:]:
                line = line.strip()
                if line:
                    s = line.split()
                    fs[(s[0], s[5])] = dict(blocks=s[1], used=s[2], available=s[3], percentage=s[4], mounted=s[5])
        return fs

    @WithConnection()
    def get_memory_per_process(self, conn=None, processes=()):
        mem = dict()
        out, err = conn.check_output(self.cmd.get_pid_and_cmd_from_ps(as_text=True, std_err_to_null=True))
        for line in out[1:]:
            line = line.strip()
            if not line:
                continue
            pid_cmd = line.split(None, 1)
            if len(pid_cmd) <= 1:
                continue
            pid, cmd = pid_cmd
            if processes and all([cmd.get_img_coord(p) == -1 for p in processes]):
                continue
            cmd_args = ''
            if len(cmd.split(None, 1)) > 1:
                cmd, cmd_args = cmd.split(None, 1)
            mem[(cmd, pid)] = dict(args=cmd_args, memory=self.get_mem_stats(pid, conn=conn))
        return mem