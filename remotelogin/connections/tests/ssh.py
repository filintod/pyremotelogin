import re
import unittest

import time
from remotelogin.connections.ssh import SshConnection
from remotelogin.connections.terminal import TerminalConnection


user=dict(username='learner', password='textingcanwait', expected_prompt= 'learner\\@ltduran\\:\\~\\$\\ ')
conn_default = dict(host='127.0.0.1', port=922)
conn_default.update(user)

USER_KEY = dict(username='mysshuser', key_filename='my_priv_key', expected_prompt=r'{username}@.+?:~\$ ')

USER_ENC_KEY = dict(username='mysshuser', key_filename='my_priv_key_enc',
                    key_password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')


class SshTests(unittest.TestCase):

    def test_telnet(self):
        pass

    def test_ssh_basic_connection(self):
        ssh = SshConnection(**conn_default)

        cmd = 'ls'
        with ssh:
            ls = ssh.check_output(cmd)

    def test_ssh_get_large_file(self):
        ssh = SshConnection(**conn_default)

        cmd = 'ls'
        import time
        with ssh:
            t = time.time()
            ls = ssh.put_file('recalls.zip')
            print(time.time() - t)

    def test_ssh_terminal_connection_send_cmd_check_output_b2b(self):
        ssh = SshConnection(**conn_default)
        cmd = 'whoami'

        t0 = time.time()
        with ssh.open_terminal(connect_timeout=0.1) as t:
            whoami = t.send_cmd('mkdir testing').check_output('whoami')
            print(t.get_conversation_string())

        # check we got our expected files/folders
        self.assertEqual(whoami, 'learner')


    def test_ssh_terminal_connection(self):
        ssh = SshConnection(**conn_default)
        cmd = 'whoami'

        t0 = time.time()
        with ssh.open_terminal(connect_timeout=0.1) as t:
            print(time.time() - t0)
            ls = t.check_output(cmd)
            print(t.get_conversation_string())

        # check we got our expected files/folders
        self.assertEqual(ls, user['username'])

        # check data sent/received stored in self.data structure is correct
        conv = t.data.get_conversation_list()

    def test_ssh_terminal_sudo_connection(self):
        ssh = SshConnection('localhost', port=2220, username='cumulus', password='cumulus')
        cmd = 'ls'
        expected = 'cumulus_demo\s+keystonerc_demo'
        with ssh.open_terminal(login_timeout=0.1) as t:
            ls = t.check_output(cmd)
            exp = t.send_cmd('sudo su -').expect_new_prompt()
            if exp.matched:
                print(t.check_output('cat /etc/ssh/sshd_config'))

    def test_ssh_basic_connection_with_keys(self):
        ssh = SshConnection('localhost', username='cumulus', port=2220, key_file_name='id_rsa')
        cmd = 'ls'
        expected = 'cumulus_demo\nkeystonerc_demo\n'
        with ssh:
            ls = ssh.check_output(cmd)

        # check we got our expected files/folders
        self.assertEqual(ls, expected)

        # check data sent/received stored in self.data structure is correct
        conv = ssh.data.get_conversation_list()
        self.assertEquals(conv[0][0], cmd)
        self.assertEquals(conv[0][1], expected)

    def test_ssh_basic_connection_nb(self):
        ssh = SshConnection('localhost', port=2220, username='cumulus', password='cumulus')
        cmd = 'ls'
        expected = 'cumulus_demo\nkeystonerc_demo\n'
        with ssh:
            th = ssh.check_output_nb(cmd)
            th.join()
            ls = th.get_all_data()
        # check we got our expected files/folders
        self.assertEqual(ls, expected)

        # check data sent/received stored in self.data structure is correct
        conv = ssh.data.get_conversation_list()
        self.assertEquals(conv[0][0], cmd)
        self.assertEquals(conv[0][1], expected)

    def test_ssh_tunnel_terminal_conn(self):
        ssh = TerminalConnection([SshConnection('127.0.0.1', port=922, **user),
                                  SshConnection('127.0.0.1', **user),
                                  SshConnection('127.0.0.1', **user),
                                  SshConnection('127.0.0.1', **user)])
        cmd = 'hostname'
        import time
        t0 =time.time()
        with ssh:
            ls = ssh.check_output(cmd)
        print(time.time() - t0)

    def test_ssh_terminal_exec_list(self):
        ssh = TerminalConnection(SshConnection('127.0.0.1', port=922, **user))
        with ssh:
            ssh.send_sudo_cmd('adduser testuser').\
                    expect_ask_response_list([#{'e': 'already exists', 'name': 'exists'},
                                               {'e': 'new password:', 'r': user['password'], 'count': 2},
                                               {'e': 'full name', 'r': 'test user'},
                                               {'e': 'room number', 'r': '1'},
                                               {'e': 'work phone', 'r': '111111'},
                                               {'expect': 'home phone', 'response': '111111'},
                                               {'expect': 'other', 'r': 'other'},
                                               {'e': 'Is the information correct', 'r': 'Y'},
                                               'prompt'],
                stop_after_getting=['prompt', 'exists'])
            ssh.check_sudo_output('deluser testuser')
            print(ssh.get_conversation_string())

    def test_ssh_telnet_tunnel_terminal_conn(self):
        from remotelogin.connections.telnet import TelnetConnection
        from remotelogin.connections.command import CommandConnection
        ssh = TerminalConnection([SshConnection('127.0.0.1', port=922, **user),
                                  CommandConnection('telnet 127.0.0.1', can_change_prompt=False,
                                                    os='cisco', **user),
                                  SshConnection('127.0.0.1', **user),
                                  SshConnection('127.0.0.1', **user)])
        cmd = 'hostname'
        import time
        t0 =time.time()
        with ssh:
            ls = ssh.check_output(cmd)
            print(ssh.get_conversation_string())
        print(time.time() - t0)

    def test_ssh_tunnel_proxyjump(self):
        ssh = SshConnection(
            proxy_jump=SshConnection(
                proxy_jump=SshConnection(
                    proxy_jump=SshConnection(**conn_default),
                    host='127.0.0.1', **user),
                host='127.0.0.1', **user),
            host='127.0.0.1', **user)
        cmd = 'hostname'
        import time
        t0 =time.time()
        with ssh.open_terminal() as ssh:
            print('\n' + ssh.check_output(cmd))
        print(time.time() - t0)

    def test_ssh_tunnel_proxyjump_mixed_users(self):
        ssh = SshConnection(
            proxy_jump=SshConnection(
                proxy_jump=SshConnection(
                    proxy_jump=SshConnection(**conn_default),
                    host='127.0.0.1', **USER_KEY),
                host='127.0.0.1', **user),
            host='127.0.0.1', **USER_ENC_KEY)
        cmd = 'hostname'
        import time
        t0 = time.time()
        with ssh:
            print('\n' + ssh.check_output(cmd))

        print(time.time() - t0)

    def test_ssh_tunnel_proxyjump_mixed_users_terminal(self):
        ssh = TerminalConnection(SshConnection(
            proxy_jump=SshConnection(
                proxy_jump=SshConnection(
                    proxy_jump=SshConnection(**conn_default),
                    host='127.0.0.1', **USER_KEY),
                host='127.0.0.1', **user),
            host='127.0.0.1', **USER_ENC_KEY))
        cmd = 'hostname'
        import time
        t0 = time.time()
        with ssh:
            print('\n1-' + ssh.check_output(cmd))
            print(ssh.prompt_found)

        print(time.time() - t0)

    def test_ssh_through_ssh(self):
        ssh = SshConnection('127.0.0.1', **user).through(
            SshConnection('127.0.0.1', **user).through(
            SshConnection('127.0.0.1', **user).through(
            SshConnection('127.0.0.1', port=922, **user)
        )))
        cmd = 'hostname'
        import time
        t0 =time.time()
        with ssh:
            ssh.data.get_conversation_list
            ls = ssh.check_output(cmd)
        print(time.time() - t0)

    def test_ssh_timeout(self):
        ssh = SshConnection('localhost', port=2220, username='cumulus',
                            password='cumulus', os='linux', connect_timeout=0.2)
        cmd = 'tail -f /var/log/messages'
        import time

        t = time.time()
        with ssh.open_terminal() as term:
            t0 = time.time()
            print(t0-t)
            try:
                ls = term.check_output(cmd, use_sudo=True, timeout=8)
                print(ls)
            except:
                pass
            self.assertEquals(8, int(time.time() - t0))
            e = term.send_ctrl_c().expect_prompt()
            self.assertTrue(e.matched)
            print(term.data.get_conversation_list())

        # check we got our expected files/folders

