import unittest

from fdutils.bpf import *
from remotelogin.devices.vendors.linux import LinuxDevice


__author__ = 'filinto'


class TestBPF(unittest.TestCase):

    def test_bpf(self):

        b = BPFFilter()
        b.hosts.allow('www.google.com', 'www.yahoo.com', '10.10.13.67')
        self.assertTrue(b.render() == 'ip and (host www.google.com or host www.yahoo.com or host 10.10.13.67)')

        b.hosts.del_allow('www.google.com')
        self.assertTrue(b.render() == 'ip and (host www.yahoo.com or host 10.10.13.67)')

        b.ports.allow(22, 20, 80, 443)
        self.assertTrue(b.render() == "ip and (host www.yahoo.com or host 10.10.13.67) and "
                                      "(port 20 or port 22 or port 80 or port 443)")

        b.ports.allow(Range(1, 20), '80-88')
        self.assertTrue(b.render() == "ip and (host www.yahoo.com or host 10.10.13.67) and "
                                      "(portrange 1-20 or port 22 or portrange 80-88 or port 443)")

        b.ports.del_allow(Range(1, 15))
        self.assertTrue(b.render() == "ip and (host www.yahoo.com or host 10.10.13.67) and "
                                      "(portrange 16-20 or port 22 or portrange 80-88 or port 443)")

        b.ports.del_allow(Range(17, 18))
        self.assertTrue(b.render() == "ip and (host www.yahoo.com or host 10.10.13.67) and "
                                      "(port 16 or portrange 19-20 or port 22 or portrange 80-88 or port 443)")

        b.set_protocol('ip6')

        b.hosts.deny('10.10.13.24')
        b.hosts.deny('1.2.3.4', '5.6.7.8', 'www.yahoo.com')
        print(b.render())

        print(b.render(device=LinuxDevice('localhost')))
        b.tcp_flags.allow('tcp-syn')

        b.hosts.allow('1.2.3.4', '5.6.7.8')
        b.subnets.deny('192.0.0.0/8')
        b.hosts.allow_from('www.turuta.com')
        print(b.render())
        b.hosts.deny_from('www.turuta.com')
        print(b.render())
        b.hosts.allow_to('www.facebook.com', '1.2.3.4')
        b.ports.allow('1-14')
        print(b.render())
        b.ports.deny('1-14')
        print(b.render())
        b.ports.allow('118-119', '15-29', '22-23', p='tcp')

        print(b.render(device=LinuxDevice('localhost')))

        with self.assertRaises(ValueError):
            b.ports.allow('d')

        print(b.render())
        b.ports.del_allow(22, 21)
        print(b.render())
        b.vlans.allow(115,200,255)
        b.vlans.deny(1,2,3)
        print(b.render())