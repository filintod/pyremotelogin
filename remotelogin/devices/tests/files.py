import pytest

from remotelogin.devices.base import DeviceBase
from remotelogin.devices.base_db import Device

DEF_CONN_DICT = dict(proto='ssh', user=dict(username='learner', password='mypassword'), port=922,
                     expected_prompt=r'{username}@.+?:~\$ ')


DEF_CONN_DICT_KEY = dict(proto='ssh', user=dict(username='mysshuser', key_filename='my_priv_key'), port=922,
                         expected_prompt=r'{username}@.+?:~\$ ')

DEF_CONN_DICT_KEY_ENC = dict(proto='ssh', port=922,
                             user=dict(username='mysshuser', key_filename='my_priv_key_enc', key_password='mypassword'),
                             expected_prompt=r'{username}@.+?:~\$ ')


DEF_TELNET_CONN_DICT = dict(proto='telnet', user=dict(username='learner', password='mypassword'), port=923,
                            expected_prompt=r'{username}@.+?:~\$ ')

USERS = dict(learner=dict(password='mypassword', expected_prompt=r'{username}@.+?:~\$ ', username='learner'),
             mysshuser=dict(password='mypassword', key_filename='my_priv_key_enc', key_password='mypassword',
                            expected_prompt=r'{username}@.+?:~\$ ', username='mysshuser'))

import os
here = os.path.abspath(os.path.dirname(__file__))
files_folder = os.path.join(here, 'testfiles')


def test_put_file_with_already_opened_connection():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with d.conn.open() as conn:
        d.files.put(os.path.join(files_folder, 'conn_settings.yaml'))


def test_upload_file_with_already_opened_connection():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with d.conn.open() as conn:
        d.files.upload(os.path.join(files_folder, 'conn_settings.yaml'))


def test_put_file_without_ready_to_use_open_conn_for_a_user():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost',
                   connections=dict(default=conn_info),
                   users={'mysshuser': {'password': 'mypassword'}})
    d.files.put(os.path.join(files_folder, 'conn_settings.yaml'), user='mysshuser')

    with d.conn.open(user='mysshuser') as conn:
        print(conn.check_output('ls -l'))
        assert conn.check_output('[ -f conn_settings.yaml ] && echo Good || echo Bad') == 'Good'
        conn.send_cmd('rm conn_settings.yaml')


def test_put_on_all_ssh_tunnel():
    hops = [
            {'host': '127.0.0.1', 'user': USERS['learner'], 'port': 922,},
            {'host': '127.0.0.1', 'user': USERS['learner']}
          ]

    d = Device('localhost',
               connections=dict(ssh={}),
               users=USERS,
               tunnels=dict(default=dict(hops=hops)))
    with d.conn.open(tunnel='default'):
        d.files.put(os.path.join(files_folder, 'conn_settings.yaml'))

def test_put_on_all_ssh_tunnel_with_scp_on_device():
    hops = [
            {'host': '127.0.0.1', 'user': USERS['learner'], 'port': 922,},
            {'host': '127.0.0.1', 'user': USERS['learner']}
          ]

    d = Device('localhost',
               connections=dict(ssh={'file_transfer_protocol': 'scp'}),
               users=USERS,
               tunnels=dict(default=dict(hops=hops)))
    with d.conn.open(tunnel='default'):
        d.files.put(os.path.join(files_folder, 'conn_settings.yaml'))


def test_get_on_mix_tunnel():
    hops = [
            {'host': '127.0.0.1', 'user': USERS['learner'], 'port': 922,},
            {'host': '127.0.0.1', 'user': USERS['learner']},
            {'host': '127.0.0.1', 'user': USERS['learner'], 'proto': 'telnet'}
          ]

    d = Device('localhost',
               connections=dict(ssh={'user': 'learner'}),
               users=USERS,
               tunnels=dict(default=dict(hops=hops)))
    with d.conn.open(tunnel='default'):
          d.files.get('conn_settings.yaml')


def test_put_on_mix_tunnel():
    hops = [
            {'host': '127.0.0.1', 'user': USERS['learner'], 'port': 922,},
            {'host': '127.0.0.1', 'user': USERS['learner']},
            {'host': '127.0.0.1', 'user': USERS['learner'], 'proto': 'telnet'}
          ]

    d = Device('localhost',
               connections=dict(ssh={'user': 'learner'}),
               users=USERS,
               tunnels=dict(default=dict(hops=hops)))
    with d.conn.open(tunnel='default'):
        d.files.put(os.path.join(files_folder, 'conn_settings.yaml'))

    print(d.conn['ssh'].conversations_string())

