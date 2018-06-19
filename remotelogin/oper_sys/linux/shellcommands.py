import fdutils
from ..unix import shellcommands

import logging
log = logging.getLogger(__name__)


class LinuxShellCmds(shellcommands.UnixShellCmds):

    def restart(self, wait_time_min=0):
        return '/usr/sbin/shutdown -r +' + str(wait_time_min)

    def shutdown(self, wait_time_min=0):
        return '/usr/sbin/shutdown -h +' + str(wait_time_min)

    def add_user(self, username, user_full_name, home_directory='', shell='/bin/bash', group_name='', secondary_groups=''):
        if not home_directory:
            home_directory = '/home/' + username
        if secondary_groups:
            secondary_groups = ' -G "' + secondary_groups + '" '
        return ('/usr/sbin/useradd -d "%s" -m -s %s -c "%s" -g "%s" %s "%s"' %
               (home_directory, shell, user_full_name, group_name, secondary_groups, username))

    def snoop(self, *args):
        return "/usr/sbin/tcpdump " + ' '.join([str(a) for a in args])

    # #############      NTP Functions     ###############################
    def force_ntp_sync(self):
        # TODO: __ALL__
        pass

    def change_ntpclient_config(self, ntp_servers, add=True, restart_svc=False):
        """ change ntp.conf file in solaris server

        @param ntp_servers: one or more ntp servers ip or fqdn
        @param add: flag to indicate if we are going to add or delete servers
        @param restart_svc: flag to indicate if we want to restart ntp client service

        """
        if not fdutils.lists.is_sequence(ntp_servers):
            ntp_servers = [ntp_servers]
        ntp_servers = ['server ' + s for s in ntp_servers]
        restart = '' if not restart_svc else '/etc/init.d/ntpd restart'
        if add:
            ntp_servers = '\n'.join(ntp_servers)
            return 'echo -e "{0}" >> /etc/ntp.conf;{1}'.format(ntp_servers, restart)
        else:
            ntp_servers = '|'.join(ntp_servers)
            return "sed '/({0})/ d' /etc/ntp.conf > ntp.conf.bak; " \
                   "mv ntp.conf.bak /etc/ntp.conf;{1} ".format(ntp_servers, restart)

    def restart_ntp(self):
        return '/etc/init.d/ntpd restart'

    ##############      Policy Based Routing Functions     ###############################
    def add_routing_table(self, name, id):
        return "echo '{}={}' >> /etc/iproute2/rt_tables"

    def add_rule(self, src='', dst='', marking='', tos='', pref=0, table_lookup='', filter_by=''):
        """
        :param src: source ip address to match. it can have a subnet prefix
        :param dst: destination ip address to match
        :param marking: hex value with a conmark to match
        :param tos: type of service to match
        :param table_lookup: table id or table name or [main|local|default], of the table to use for the packets that match the filter rule
        :param pref: prefernce value to give to this rule
        :param filter_by: one of [prohibit|reject|unreachable] to assign to packets that match the filter
        """
        # TODO: __ALL__
        return "ip rule add "

    def add_mark_packets(self, src='', dst='', iface='', oface='', marking=''):
        pass

    def flush_arp_table(self):
        return 'ip -s -s neigh flush all'

    ##############      Utils Functions     ###############################

    def get_fields_from_text(self, first=1, last=0, fields=()):
        """ using awk and/or cat split a string given first, last or fields. Remember that index starts at 1 not 0

        :param int first: first element to start getting fields from
        :param int last: last element to include in list of fields
        :param list of int or tuple of int fields: a list of field numbers to include

        """
        if not first and not last and not fields:
            return 'cat'

        # return from first til NF
        if not last and not fields:
            return "awk '{{for (i={};i<=NF;i++) {{printf \"%s \", $i}}; printf \"\\n\";}}'".format(first)

        # return from first til last
        if not fields:
            return "awk '{{for (i={};i<={} and i<=NF;i++) {{printf \"%s \", $i}}; printf \"\\n\";}}'".format(first, last)

        if not first:
            return "awk '{{print {}}}".format(' '.join(['$' + str(i) for i in fields]))

        awk_array = ''
        for p in fields:
            awk_array += 'f[{}]=1;'.format(p)

        return "awk '{{{}; for (i=1; i<=NF; i++) {{ if (i>={} || (i in f)) printf \"%s \", $i}}; printf \"\\n\";}}'" \
               "".format(awk_array, first)

    def get_ps_with_args(self):
        return 'ps -Af'

    def get_pid_and_cmd_from_ps(self):
        return 'ps -Af | ' + self.get_fields_from_text(first=6, fields=(2,))


Instance = None


def get_instance():
    global Instance
    if Instance is None:
        Instance = LinuxShellCmds()
    return Instance
