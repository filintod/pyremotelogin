import unittest

from ..telnet import TelnetConnection
from ..ssh import SshConnection
from ..terminal import TerminalConnection

user=dict(username='learner', password='textingcanwait', expected_prompt= 'learner\\@ltduran\\:\\~\\$\\ ')


class TelnetTests(unittest.TestCase):

    def test_telnet(self):
        pass

    def test_basic_connection(self):
        conn = TelnetConnection('localhost', port=923, **user)
        cmd = 'ls'
        import time
        t0 = time.time()
        with conn:
            print(time.time()-t0)
            print(conn.check_output(cmd))
            res = conn.send_cmd('ifconfig').expect_all('RX', 'TX')

        NEW_SSH_USERNAME = 'mysshuser'
        PASSWORD = 'textingcanwait'

        with conn as term:
            print(term.check_sudo_output('useradd -m -d /home/{NEW_SSH_USERNAME} {NEW_SSH_USERNAME}'
                                         ''.format(NEW_SSH_USERNAME=NEW_SSH_USERNAME)))
            term.send_sudo_cmd('passwd {NEW_SSH_USERNAME}'.format(NEW_SSH_USERNAME=NEW_SSH_USERNAME))\
                .send_confirmed_password(PASSWORD).expect_prompt()
            print(term.check_output('cat /etc/passwd | grep {NEW_SSH_USERNAME}'.format(NEW_SSH_USERNAME=NEW_SSH_USERNAME)))

        print(res)

    def test_multihop(self):
        hop1 = SshConnection(host="127.0.0.1", port=922, **user)
        hop2 = TelnetConnection(host="127.0.0.1", connect_timeout=0.4, **user)
        hop3 = SshConnection(host="127.0.0.1", username="learner", password="textingcanwait", connect_timeout=0.4)

        multihop = TerminalConnection(SshConnection('127.0.0.1', port=922, **user),
                                  SshConnection('127.0.0.1', connect_timeout=0.4, **user))
        with multihop:
            multihop.is_open

    def test_ssh_through_telnet(self):
        ssh = TerminalConnection(SshConnection('127.0.0.1', port=922, **user),
                                  SshConnection('127.0.0.1', connect_timeout=0.4, **user),
                                 SshConnection('127.0.0.1', connect_timeout=0.4, **user),
                                  SshConnection('127.0.0.1', connect_timeout=0.4, **user),
                                  TerminalConnection([SshConnection('127.0.0.1', connect_timeout=0.3, **user),
                                                      SshConnection('127.0.0.1', connect_timeout=0.4, **user),
                                 SshConnection('127.0.0.1',connect_timeout=0.4,  **user),
                                                      SshConnection('127.0.0.1', connect_timeout=0.4, **user)]),
                                 check_same_prompt_when_opening_terminal=False

        )
        ssh.use_unique_prompt = False
        cmd = 'hostname'
        expected = 'server2\n'
        import time
        t0 =time.time()
        with ssh:
            print(ssh.check_output(cmd))
        print(time.time() - t0)


