from operator import itemgetter
import re

#TODO: provide a render function that will make a display filter from a bpf

# Utility to create Berkley Packet Filters for pcap/tcpdump/snoop capture filters
#
# ########  NOT the same as display filters in Wireshark (do not use on wireshark)!!!!!!!   ##############
#
# snoop has some specific format that the SolarisOS will provide.

# BPF can also be used to create more succint/faster iptables rules:
#       https://www.lowendtalk.com/discussion/47469/bpf-a-bytecode-for-filtering

from .structures import Range
from . import lists

PORT_RANGE_REGEX = re.compile('^(\d+)\-(\d+)$')


class BPFComponentBase:
    # bpf keywords
    __HOST__ = 'host'
    __NET__ = 'net'
    __PORT__ = 'port'
    __PORTRANGE__ = 'portrange'
    __VLAN__ = 'vlan'
    __TCPFLAGS__ = 'tcpflags'

    def __init__(self, name, validate='', range_name=''):
        self.bpf_keyword = name
        self.bpf_range_keyword = range_name
        self.validate = validate
        self._not = []
        self._a = []

    def __nonzero__(self):
        """ check for empty filter used in add_prepend function

        """
        return bool(self._not or self._a)

    def _convert_values(self, values):
        return values

    def _remove_range(self, list_to_remove, remove_this):
        return list_to_remove

    def _merge_range(self, list_to_merge):
        """ merge IP or port ranges

        """
        return list_to_merge

    def _get_list(self, to):
        if to == 'not':
            main = self._not
            remove = 'a'
        else:
            main = self._a
            remove = 'not'
        return main, remove

    # TODO: decide if there should be a dns resolution to filter addresses
    def add_prepend(self, to, *add, **kwargs):
        """ add a filter to the bpf. This action will overwrite any previous allow or denied value. There is no dns resolution to filter

        """
        prepend = kwargs.get('proto', '') or kwargs.get('p', '')
        add = self._convert_values(add)

        if self.validate and any([not re.match(self.validate, str(a)) for a in add]):
            raise ValueError

        if prepend:
            prepend += ' '

        # generate a list with the prepend + filter values if they don't already exists in corresponding filter list
        def _gen_prepend_list(current_list):
            return [(prepend, a) for a in add if (prepend, a) not in current_list]

        # append the values to the corresponding filter list
        main, remove = self._get_list(to)

        main.extend(_gen_prepend_list(main))
        self.remove_prepend(remove, *add, **kwargs)

        self._merge_range(main)

    def remove_prepend(self, to, *remove, **kwargs):

        prepend = kwargs.pop('proto', '')
        if prepend:
            prepend += ' '

        remove = self._convert_values(remove)

        def _gen_prepend_list(current_list):
            return [(prepend, a) for a in remove if (prepend, a) in current_list]

        main, negated = self._get_list(to)
        lists.del_from_list(main, _gen_prepend_list(main))

        self._remove_range(main, remove)

    def allow(self, *items, **kwargs):
        """ allow packets with values in items

        """
        self.add_prepend('a', *items, **kwargs)

    def deny(self, *items, **kwargs):
        """ drop packets with values in items

        """

        self.add_prepend('not', *items, **kwargs)

    def del_allow(self, *items, **kwargs):
        """ allow packets with values in items

        """
        self.remove_prepend('a', *items, **kwargs)

    def del_deny(self, *items, **kwargs):
        """ delete drop packets with values in items

        """
        self.remove_prepend('not', *items, **kwargs)

    def _render_item(self, item, prepend='', prev='', device=None):
        return_str = prev
        if item:
            if prepend:
                prepend += ' '

            for a in item:
                # TODO: design a more elegant way to represent pre-pending order of keywords
                if return_str:
                    return_str += ' or '
                keyword = self.bpf_keyword
                val = str(a[1])
                if isinstance(a[1], Range):
                    if a[1].length == 1:
                        val = a[1].start
                    else:
                        if device is None or not hasattr(device.os.cmd, 'get_port_range_bpf_key_value'):
                            keyword = self.bpf_range_keyword
                        else:
                            return_str += device.os.cmd.get_port_range_bpf_key_value(
                                a[0], prepend, a[1], self.bpf_keyword, self.bpf_range_keyword)
                            continue
                return_str += '{0}{1}{2} {3}'.format(a[0], prepend, keyword, val)

        return return_str

    def render(self, previous=None, device=None):
        render_str = ''
        if self:

            tmp_str = self._render_item(self._a, device=device)
            if tmp_str:
                render_str = '(' + tmp_str + ')'

            tmp_str = self._render_item(self._not, device=device)
            if tmp_str:
                if render_str:
                    render_str += ' and '
                render_str += 'not (' + tmp_str + ')'

        if previous is not None:
            if render_str:
                return previous + ' and ' + render_str
            return previous
        return render_str

    def render_for_display(self, previous=None):
        """ renders the bpf filter for display like tshark or wireshark (http://www.wireshark.org/docs/dfref/)

        """
        # TODO: ALL

        pass


class BPFComponent(BPFComponentBase):
    # bpf keywords
    __HOST__ = 'host'
    __NET__ = 'net'
    __PORT__ = 'port'
    __PORTRANGE__ = 'portrange'
    __VLAN__ = 'vlan'
    __TCPFLAGS__ = 'tcpflags'

    def __init__(self, name, validate='', range_name=''):
        super(BPFComponent, self).__init__(name, validate, range_name)
        self._from = []
        self._to = []
        self._not_from = []
        self._not_to = []
        self._for_tcp = []
        self._not_for_tcp = []
        self._for_udp = []
        self._not_for_udp = []

    def __nonzero__(self):
        """ check for empty filter used in add_prepend function

        """
        return bool(self._from or self._to or self._not or self._not_from or self._a or self._not_to)

    def _get_list(self, to):
        if to == 'from':
            main = self._from
            remove = 'not from'
        elif to == 'to':
            main = self._to
            remove = 'not to'
        elif to == 'not':
            main = self._not
            remove = 'a'
        elif to == 'not from':
            main = self._not_from
            remove = 'from'
        elif to == 'not to':
            main = self._not_to
            remove = 'to'
        else:
            main = self._a
            remove = 'not'
        return main, remove

    def allow_from(self, *items, **kwargs):
        """ allow packets with values coming from items """
        self.add_prepend('from', *items, **kwargs)

    def allow_to(self, *items, **kwargs):
        """ allow packets with values destined to items """
        self.add_prepend('to', *items, **kwargs)

    def deny_from(self, *items, **kwargs):
        """ drop packets with values from to items """
        self.add_prepend('not from', *items, **kwargs)

    def deny_to(self, *items, **kwargs):
        """ drop packets going to """
        self.add_prepend('not to', *items, **kwargs)

    def del_allow_from(self, *items, **kwargs):
        self.remove_prepend('from', *items, **kwargs)

    def del_allow_to(self, *items, **kwargs):
        self.remove_prepend('to', *items, **kwargs)

    def del_deny_from(self, *items, **kwargs):
        self.remove_prepend('not from', *items, **kwargs)

    def del_deny_to(self, *items, **kwargs):
        self.remove_prepend('not to', *items, **kwargs)

    def render(self, previous=None, device=None):
        render_str = ''
        if self:

            tmp_str = self._render_item(self._a, device=device)
            tmp_str = self._render_item(self._from, 'src', tmp_str, device=device)
            tmp_str = self._render_item(self._to, 'dst', tmp_str, device=device)
            if tmp_str:
                render_str = '(' + tmp_str + ')'

            tmp_str = self._render_item(self._not, device=device)
            tmp_str = self._render_item(self._not_from, 'src', tmp_str, device=device)
            tmp_str = self._render_item(self._not_to, 'dst', tmp_str, device=device)
            if tmp_str:
                if render_str:
                    render_str += ' and '
                render_str += 'not (' + tmp_str + ')'

        if previous is not None:
            if render_str:
                return previous + ' and ' + render_str
            return previous
        return render_str

    def render_for_display(self, previous=None):
        """ renders the bpf filter for display like tshark or wireshark (http://www.wireshark.org/docs/dfref/)

        """
        # TODO: ALL

        pass


class BPFComponentVLAN(BPFComponentBase):
    def __init__(self):
        super(BPFComponentVLAN, self).__init__(BPFComponent.__VLAN__, r"\d+")


class BPFComponentPort(BPFComponent):
    def __init__(self):
        super(BPFComponentPort, self).__init__(BPFComponent.__PORT__, r"\d+(\-\d+)?", BPFComponent.__PORTRANGE__)

    def _convert_values(self, values):

        values = list(values)

        for i, item in enumerate(values):
            if isinstance(item, Range):
                continue
            m = PORT_RANGE_REGEX.match(str(item))
            if m:
                values[i] = Range(int(m.group(1)), int(m.group(2)))
            else:
                values[i] = Range(int(item), int(item))
        return values

    def _return_range(self, val):
        return val if isinstance(val, Range) else Range(val, val)

    # TODO: this is doing a linear comparison and I don't expect to be an issue but if needed try to implement a sorted tree
    def _merge_range(self, list_to_merge):
        """ compares and compresses ranges

        :param list of Range:

        """
        s = sorted(list_to_merge, key=itemgetter(1))
        j = 0
        for i in range(len(list_to_merge) - 1):
            if s[j][1].overlaps(s[i + 1][1]) or s[j][1].is_contiguous_to(s[i + 1][1]):
                s[j][1].union_update(s[i + 1][1])
            else:
                j += 1
                s[j] = s[i + 1]
        for i, v in enumerate(s):
            list_to_merge[i] = v

        del list_to_merge[j + 1:]

    # TODO: this is doing a linear comparison and sorting and I don't expect to be an issue but if needed try to implement a sorted tree for list of Ranges
    def _remove_range(self, list_to_remove, remove_this):
        """ compares and compresses ranges

        :param list of Range:

        """
        if not list_to_remove or not remove_this:
            return
        j = 0
        new_list = []
        current_list = sorted(list_to_remove, key=itemgetter(1))
        removal_list = sorted(remove_this)
        for current_to, current_range in current_list:
            while j < len(removal_list) and removal_list[j] << current_range:
                j += 1
            if j < len(removal_list) and not removal_list[j] >> current_range:
                diff = current_range.difference(removal_list[j], split_if_needed=True)
                if type(diff) is tuple:
                    new_list.append((current_to, diff[0]))
                    new_list.append((current_to, diff[1]))
                elif diff is not None:
                    new_list.append((current_to, diff))
                continue
            new_list.append((current_to, current_range))

        for i, v in enumerate(new_list):
            if i < len(list_to_remove):
                list_to_remove[i] = v
            else:
                list_to_remove.append(v)

        del list_to_remove[i + 1:]

# TCP control flags
tcpflags = 13       # byte location of tcp flag in tcp header
TH_FIN = 0x01		# end of data
TH_SYN = 0x02		# synchronize sequence numbers
TH_RST = 0x04		# reset connection
TH_PUSH = 0x08		# push
TH_ACK = 0x10		# acknowledgment number set
TH_URG = 0x20		# urgent pointer set
TH_ECE = 0x40		# ECN echo, RFC 3168
TH_CWR = 0x80		# congestion window reduced
TH_SYN_ACK = TH_SYN | TH_ACK


class BPFFilter:
    # TODO: IPV6 tcp filtering
    # protocols
    __IPV4__ = 'ip'
    __TCP__ = 'tcp'
    __UDP__ = 'udp'
    __IPV6__ = 'ip6'
    __PING__ = 'icmp'
    __PING6__ = 'icmp6'

    # tcp flags
    __SYN__ = 'tcp-syn'
    __ACK__ = 'tcp-ack'
    __SYNACK__ = 'tcp-syn|tcp-ack'
    __FIN__ = 'tcp-fin'
    __RST__ = 'tcp-rst'
    __PSH__ = 'tcp-push'

    __ALLOWED_TCP_FLAGS__ = (__PSH__, __RST__, __SYN__, __SYNACK__, __ACK__, __FIN__)
    __ALLOWED_PROTOCOLS__ = ('ip', 'ip6', 'tcp', 'ether', 'udp', 'wlan', 'arp', 'icmp')

    def __init__(self, proto='ip', is_multicast=False):
        self.hosts = BPFComponent(BPFComponent.__HOST__)
        self.ports = BPFComponentPort()
        self.tcp_flags = BPFComponent(BPFComponent.__TCPFLAGS__, "({})".format("|".join(BPFFilter.__ALLOWED_TCP_FLAGS__)))
        self.subnets = BPFComponent(BPFComponent.__NET__)
        self.vlans = BPFComponentVLAN()
        self.custom = []    # raw bpf given by user. no validation done
        self.set_protocol(proto, is_multicast)

    def set_protocol(self, proto, is_multicast=False):

        if proto not in self.__ALLOWED_PROTOCOLS__:
            raise AttributeError('Protocol value ({}) not in allowed ones ({})'
                                 ''.format(proto, ','.join(self.__ALLOWED_PROTOCOLS__)))

        if is_multicast and proto not in ('ip', 'ip6'):
            raise AttributeError('is_multicast can only be applied to ip or ip6 protocols, and you set the protocol to:'
                                 ' ' + proto)
        self.proto = proto
        self.is_multicast = is_multicast

    def _root(self):
        r = self.proto
        if self.is_multicast:
            r += ' multicast'
        return r

    def add_custom(self, custom_filter):
        """ hand written BPF filter. BPF Reference: http://biot.com/capstats/bpf.html

        """
        self.custom.append(custom_filter)

    # TODO: TCPFLAGS, VLANS, CUSTOM
    def render(self, device=None):
        render_str = self.hosts.render(self._root(), device=device)
        render_str = self.ports.render(render_str, device=device)
        render_str = self.subnets.render(render_str, device=device)
        render_str = self.vlans.render(render_str, device=device)

        return render_str