import socket

from fdutils.files import log


def nslookup_all(ip, family=None):
    """ returns a list of IPv4/IPv6 addresses related to an IP/HOST

    """
    family = socket.AF_INET if family == 'ipv4' else socket.AF_INET6 if family == 'ipv6' else 0
    output = socket.getaddrinfo(ip, 0, family=family)
    ret = []
    try:
        for o in output:
            ret.append(o[4][0])
    except socket.gaierror:
        pass
    return ret


def set_socket_keepalive(sock, interval, interval_sec=3, max_fails=5):
    import platform
    system = platform.system()

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, bool(interval))

    if interval:

        if system == 'Linux':
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, interval)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)

        elif system == 'Windows':
            sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, interval, interval_sec))

        elif system == 'Darwin':
            TCP_KEEPALIVE = 0x10
            sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, interval_sec)


def nslookup(ip):
    return nslookup_all(ip, socket.AF_INET)


def nslookup_v6(ip):
    return nslookup_all(ip, socket.AF_INET6)


def get_list_of_syn_timestamps_from_host(pcap_file, host_ip):
    """ using libpcap filter the pcap file using the BPF filter for tcp-syn and host src ip
        Good for finding frequency of host trying to connect to the server where this pcap file was captured
    """

    pc = pcap.pcap(pcap_file)
    # set BPF filter
    pc.setfilter('tcp[tcpflags]&tcp-syn=tcp-syn and src host ' + host_ip)
    prev_ts = 0
    list_ts = []
    for ts, pkt in pc:
        if not prev_ts:
            prev_ts = ts
        list_ts.append(ts - prev_ts)
        prev_ts = ts
    return list_ts


def check_tcp_3way_handshake_established(pcap_file, src, dst):
    """ Using libpcap filter the pcap file using the BPF filter for tcp-syn, tcp-syn-ack and tcp-ack and no fin or rst
    We are going to check 3way handshake is executed
    """
    from pcap import pcap
    import dpkt
    pc = pcap(pcap_file)
    # set BPF filter for these two hosts and tcp flags of interest
    pc.setfilter('tcp[tcpflags]&(tcp-syn|tcp-ack|tcp-fin|tcp-rst)>1 and host {0} and host {1}'.format(src, dst))
    syn_sent = syn_ack_sent = False
    src_port = dst_port = first_syn = prev_seq = 0
    for ts, pkt in pc:
        eth = dpkt.ethernet.Ethernet(pkt)
        ip = eth.data
        tcp = ip.data

        # look for the first syn from src
        if not tcp.flags & (dpkt.tcp.TH_ACK | dpkt.tcp.TH_SYN):
            continue

        # convert to string
        ip_src = socket.inet_ntoa(ip.src)
        ip_dst = socket.inet_ntoa(ip.dst)
        ack = tcp.ack
        seq = tcp.seq
        if tcp.flags & dpkt.tcp.TH_SYN and ip_src == src:
            syn_sent = True
            syn_ack_sent = False
            src_port = tcp.sport
            dst_port = tcp.dport
            first_syn = ts
            prev_seq = seq
            log.info("Syn found...at " + str(ts))

        elif (tcp.flags & (dpkt.tcp.TH_SYN | dpkt.tcp.TH_ACK) and ip_dst == src and ip_src == dst and syn_sent and
              ack == (prev_seq + 1) and src_port == tcp.dport and dst_port == tcp.sport):

            syn_ack_sent = True
            prev_seq = seq
            log.info("Syn-Ack found...at " + str(ts))

        elif (tcp.flags & dpkt.tcp.TH_ACK and ip_src == src and ip_dst == dst and syn_ack_sent and
              ack == (prev_seq + 1) and src_port == tcp.sport and dst_port == tcp.dport):

            # connection established

            return True, first_syn
        elif src_port in (tcp.sport, tcp.dport) or dst_port in (tcp.sport, tcp.dport):  # tcp fin or rst for tcp connection sent before connection established
            syn_sent = syn_ack_sent = False

    return False, 0


def get_local_ips():
    """ gets local ip addresses on this machine

    :return:
    """
    import psutils
    local_ips = set()
    for v in [k.values() for k in [netifaces.ifaddresses(iff) for iff in netifaces.interfaces()]]:
        for a in [addr[0]['addr'] for addr in v if addr[0]['addr']]:
            local_ips |= {a}
    return list(local_ips)