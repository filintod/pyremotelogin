import re
import time

import pytest

import remotelogin.connections.exceptions
from remotelogin.connections import ssh, telnet, constants
from remotelogin.connections.exceptions import BadSshKeyPasswordError
from remotelogin.devices import exceptions, properties
from remotelogin.devices.vendors import linux
from remotelogin.devices.base import DeviceBase
from remotelogin.devices.base_db import Device
from remotelogin.devices.base_db_named import TableNamedDevice
from remotelogin.devices.exceptions import UnknownConnectionError, DuplicatedConnectionError, ConnectionInstanceOpenError
from remotelogin.devices.tests.utils import update_db_config

DEF_CONN_DICT = dict(proto='ssh', user=dict(username='learner', password='textingcanwait'), port='922',
                     expected_prompt=r'{username}@.+?:~\$ ')

RPI_CONN_DICT = dict(proto='ssh', user=dict(username='pi', password='raspberry',
                                            expected_prompt=r'{username}@raspberrypi:~\$'))



DEF_CONN_DICT_KEY = dict(proto='ssh', user=dict(username='mysshuser', key_filename='my_priv_key'), port=922,
                         expected_prompt=r'{username}@.+?:~\$ ')

DEF_CONN_DICT_KEY_ENC = dict(proto='ssh', port=922,
                             user=dict(username='mysshuser',
                                       key_filename='my_priv_key_enc',
                                       key_password='textingcanwait'),
                             expected_prompt=r'{username}@.+?:~\$ ')

USERS = dict(learner=dict(password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ', username='learner'),
             mysshuser=dict(password='textingcanwait', key_filename='my_priv_key_enc', key_password='textingcanwait',
                            expected_prompt=r'{username}@.+?:~\$ ', username='mysshuser'))



DEF_TELNET_CONN_DICT = dict(proto='telnet', user=dict(username='learner', password='textingcanwait'), port=923,
                            expected_prompt=r'{username}@.+?:~\$ ')


# def test_ssh_raspberrypi():
#     d = DeviceBase('192.0.2.7', connections=dict(default=RPI_CONN_DICT))
#     with d.conn.open():
#         assert d.conn.check_output('whoami') == d.users.default.username
#         print(d.conn.prompt_found)


def test_ssh_check_default_via_add_ssh():
    d = DeviceBase('localhost', ip_type='ipv4')
    conn_info = dict(DEF_CONN_DICT)
    conn_info.pop('proto')
    d.conn.add_ssh('default', **conn_info)
    assert d.conn.default.cls == ssh.SshConnection
    assert d.conn.default.port == 922
    assert d.conn.default.interface is None
    assert d.interfaces.default.default_ip == '127.0.0.1'
    assert d.conn.default.user == d.users['learner']


def test_ssh_via_device_connections():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info), ip_type='ipv4')
    assert d.conn.default.cls == ssh.SshConnection
    assert d.conn.default.user == d.users.default
    assert d.users.default.username == 'learner'
    assert d.users.default.password == 'textingcanwait'
    assert d.conn.default.port == 922
    assert d.conn.default.host == '127.0.0.1'

def test_adding_via_device_not_as_dict_raises_TypeError():
    conn_info = dict(DEF_CONN_DICT)
    print(conn_info)
    with pytest.raises(TypeError):
        d = DeviceBase('localhost', connections=dict(conn_info), ip_type='ipv4')

def test_trying_to_get_info_from_unopen_conn_raises_ConnectionInstanceOpenError():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info), ip_type='ipv4')
    with pytest.raises(ConnectionInstanceOpenError):
        d.conn.check_output('hostname')

def test_adding_same_connection_raises_DuplicateConnectionError():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info), ip_type='ipv4')
    with pytest.raises(DuplicatedConnectionError):
        d.conn.add_ssh('default', DEF_CONN_DICT)

def test_proto_embedded_in_name():
    # if we put the name of a connection with an embedded protocol name we will think it is that protocol
    conn_info = dict(DEF_CONN_DICT)
    # remove proto
    conn_info.pop('proto')
    d = DeviceBase('localhost', connections=dict(ssh=conn_info), ip_type='ipv4')
    assert d.conn.default.cls == ssh.SshConnection
    assert d.conn.default.user == d.users.default

    assert d.users.default.username == 'learner'
    assert d.users.default.password == 'textingcanwait'

    assert d.conn.default.port == 922
    assert d.conn.default.host == '127.0.0.1'

def test_no_proto_provided_embedded_in_name_raises_ConnectionError():
    conn_info = dict(DEF_CONN_DICT)
    # remove proto
    conn_info.pop('proto')
    with pytest.raises(ConnectionError):
        d = DeviceBase('localhost', connections=dict(default=conn_info), ip_type='ipv4')

def test_passing_bad_arguments_in_connection_raises_TypeError():
    conn_info = dict(DEF_CONN_DICT)
    conn_info['user2'] = 'myuser'
    # remove proto
    with pytest.raises(TypeError):
        d = DeviceBase('localhost', connections=dict(default=conn_info), ip_type='ipv4')

    conn_info.pop('user2')
    d = DeviceBase('localhost', connections=dict(default=conn_info), ip_type='ipv4')
    with pytest.raises(TypeError):
        d.conn.open(userpass='unknown arg')

def test_add_unimplemented_protocol_raises_NotImplementedProtocolError():
    conn_info = dict(DEF_CONN_DICT)
    conn_info['proto'] = 'cmd'
    with pytest.raises(exceptions.NotImplementedProtocolError):
        DeviceBase('localhost', connections=dict(default=conn_info))

def test_ssh_allow_non_expected_prompt():
    conn_info = dict(DEF_CONN_DICT)
    conn_info.pop('expected_prompt')
    conn_info['allow_non_expected_prompt'] = True
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with d.conn.open():
        assert d.conn.check_output('whoami') == d.users.default.username

def test_telnet_allow_non_expected_prompt():
    conn_info = dict(DEF_TELNET_CONN_DICT)
    conn_info.pop('expected_prompt')
    conn_info['allow_non_expected_prompt'] = True
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    assert d.conn.default.cls == telnet.TelnetConnectionUnwrapped
    with d.conn.open():
        assert d.conn.check_output('whoami') == d.users.default.username

def test_context_manager():
    #Creating simple context manager from functions with contextlib.contextmanager
    #The SshConnection object already includes a context manager but creating new ones from functionsis fairly easy using the contextmanager decorator from the contextlib package.
    import contextlib
    import re
    import socket
    import sys
    from remotelogin.connections import ssh
    hostname = socket.gethostname()
    # I'm thinking that if the platform is linux we are in the VM if not then we are on the host
    # using the forwarded port
    ssh_port = 22 if (sys.platform == 'linux') else 922
    expected_prompt = r"learner@{hostname}:~\$ ".format(hostname=hostname)
    ssh_conn = ssh.SshConnection(host='127.0.0.1', username='learner', password='textingcanwait', port=ssh_port,
                                 expected_prompt=expected_prompt)

    @contextlib.contextmanager
    def telnet_connection_in_ssh(ssh_conn):
        try:
            with ssh_conn.open_terminal() as conn:
                print("Test envi will change the prompt when entering (if possible) to make it more unique: ",
                      conn.prompt)

                conn.send_cmd('telnet localhost -l learner').\
                     expect_regex('password', flags=re.I, chain=True).\
                     send_hidden_cmd('textingcanwait').\
                     expect_new_prompt(expected_prompt)

                yield conn
        finally:
            ssh_conn.close()

    def get_hostname_in_telnet_in_ssh(ssh_conn):
        with telnet_connection_in_ssh(ssh_conn) as conn:
            assert conn.check_output('whoami') == 'learner'

    get_hostname_in_telnet_in_ssh(ssh_conn)

def test_set_default_conn_explicitely():
    d = DeviceBase('localhost', connections=dict(default=DEF_TELNET_CONN_DICT, ssh=DEF_CONN_DICT))
    d.conn.set_default('ssh')
    assert d.conn.default.cls == ssh.SshConnection
    d.conn.set_default('default')
    assert d.conn.default.cls == telnet.TelnetConnectionUnwrapped

def test_set_default_conn_explicitely_bad_name_raises_UnknownConnectionError():
    d = DeviceBase('localhost', connections=dict(default=DEF_TELNET_CONN_DICT, ssh=DEF_CONN_DICT))
    with pytest.raises(UnknownConnectionError):
        d.conn.set_default('ssh2')

def test_set_default_conn_implicitely_in_device_creation():
    d = DeviceBase('localhost', connections=dict(default=DEF_TELNET_CONN_DICT, ssh=DEF_CONN_DICT, default_name='ssh'))
    assert d.conn.default.cls == ssh.SshConnection
    d = DeviceBase('localhost', connections=dict(default=DEF_TELNET_CONN_DICT, ssh=DEF_CONN_DICT, default_name='default'))
    assert d.conn.default.cls == telnet.TelnetConnectionUnwrapped

def test_set_bad_default_conn_implicitely_in_device_creation_raises_UnknownConnectionError():
    with pytest.raises(UnknownConnectionError):
        DeviceBase('localhost', connections=dict(default=DEF_TELNET_CONN_DICT, ssh=DEF_CONN_DICT, default_name='ssh2'))

def test_closig_explicitely_without_with():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    d.conn.open()
    assert d.conn.check_output('whoami') == d.users.default.username
    d.conn.close()

def test_closig_explicitely_using_instance_name():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    d.conn.open(instance_name='another')
    assert d.conn.check_output('whoami') == d.users.default.username
    d.conn.close(instance_name='another')

def test_closig_explicitely_using_wrong_name_raises_UnknownConnectionError():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    d.conn.open(instance_name='another')
    assert d.conn.check_output('whoami') == d.users.default.username
    with pytest.raises(UnknownConnectionError):
        d.conn.close(name='bad name')

def test_ssh_allow_non_expected_prompt_longer_conn_timeout():
    conn_info = dict(DEF_CONN_DICT)
    conn_info.pop('expected_prompt')
    conn_info['timeout_for_prompt'] = 2
    conn_info['allow_non_expected_prompt'] = True
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    t0 = time.time()
    with d.conn.open():
        assert d.conn.check_output('whoami') == d.users.default.username
    assert time.time() - t0 >= 2

def test_ssh_longer_conn_timeout_has_no_effect_if_prompt_set():
    conn_info = dict(DEF_CONN_DICT)
    conn_info['timeout_for_prompt'] = 5
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    t0 = time.time()
    with d.conn.open():
        assert d.conn.check_output('whoami') == d.users.default.username
    assert time.time() - t0 < 1

def test_ssh_via_open_connection():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    conn_instance = d.conn.open()
    assert d.conn.check_output('whoami') == d.users.default.username
    conn_instance.close()

def test_ssh_conn_with_no_user_info_raises_NoDefaultUserError():
    conn_info = dict(DEF_CONN_DICT)
    # removing user info
    conn_info.pop('user');
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with pytest.raises(remotelogin.connections.exceptions.NoDefaultUserError):
        d.conn.open()

def test_ssh_conn_with_no_user_raises_NoDefaultUserError():
    conn_info = dict(DEF_CONN_DICT)
    # removing user info
    conn_info.pop('user');
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with pytest.raises(remotelogin.connections.exceptions.NoDefaultUserError):
        d.conn.open()

def test_ssh_conn_with_no_interface_info_raises_NoDefaultInterfaceError():
    conn_info = dict(DEF_CONN_DICT)
    # removing user info
    d = DeviceBase(connections=dict(default=conn_info))
    with pytest.raises(exceptions.NoDefaultInterfaceError):
        d.conn.open()


def test_ssh_conn_open_via_with():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    import time
    t0 = time.time()

    with d.conn.open():
        print(time.time()-t0)
        assert d.conn.check_output('whoami') == d.users.default.username

def test_ssh_conn_open_via_with_without_open():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with d.conn:
        assert d.conn.check_output('whoami') == d.users.default.username

def test_ssh_conn_instance_get_open_instances_return_current():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with d.conn as c:
        assert d.conn.check_output('whoami') == d.users.default.username
        assert c.prompt_found == d.conn.get_open_instance().prompt_found

def test_ssh_conn_instance_get_open_instances_raises_ConnectionInstanceOpenError():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with pytest.raises(exceptions.ConnectionInstanceOpenError):
        assert d.conn.get_open_instances()

def test_ssh_conn_open_try_to_open_same_instance_name_raises_DuplicatedConnectionError():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with d.conn.open() as c1:
        assert c1.check_output('whoami') == d.users.default.username
        with pytest.raises(exceptions.DuplicatedConnectionError):
            d.conn.open()

def test_ssh_conn_open_multiple_instances_same_connection():
    conn_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with d.conn.open() as c1:
        assert c1.check_output('whoami') == d.users.default.username
        with d.conn.open(instance_name='c2') as c2:
            assert c2.check_output('whoami') == d.users.default.username

def test_telnet_conn_open_multiple_instances_same_connection():
    conn_info = dict(DEF_TELNET_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with d.conn.open() as c1:
        assert c1.check_output('whoami') == d.users.default.username
        with d.conn.open(instance_name='c2') as c2:
            assert c2.check_output('whoami') == d.users.default.username

def test_ssh_telnet_conn_open():
    telnet_info = dict(DEF_TELNET_CONN_DICT)
    ssh_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(default=telnet_info, ssh=ssh_info, default_name='default'))
    with d.conn.open() as c1:
        assert c1.check_output('whoami') == telnet_info['user']['username']
        with d.conn.open('ssh') as c2:
            assert c2.check_output('whoami') == ssh_info['user']['username']

    conversations = d.conn.get_all_conversations_flat()
    assert conversations['default'][-1]['sent'] == 'whoami\n'
    assert conversations['ssh'][-1]['sent'] == 'whoami\n'

def test_ssh_conversations_saved_same_instance():
    ssh_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(ssh=ssh_info))
    with d.conn.open() as c1:
        c1.check_output('whoami')

    with d.conn.open() as c1:
        c1.check_output('hostname')

    # using get_all_conversations (more useful with multiple instance names)
    conversations = d.conn.get_all_conversations()['ssh']
    assert conversations[c1.instance_name][-1][-1]['sent'] == 'hostname\n'
    assert conversations[c1.instance_name][-2][-1]['sent'] == 'whoami\n'

    # using get_all_conversations_flat
    conversations = d.conn.get_all_conversations_flat()['ssh']
    assert conversations[-1]['sent'] == 'hostname\n'


def test_ssh_conversations_saved_diff_instance_name():
    ssh_info = dict(DEF_CONN_DICT)
    d = DeviceBase('localhost', connections=dict(ssh=ssh_info))
    with d.conn.open() as c1:
        c1.check_output('whoami')
        name1 = c1.instance_name

    with d.conn.open(instance_name='the_other') as c1:
        c1.check_output('hostname')
        name2 = c1.instance_name

    # using get_all_conversations  as we have two conversations the indexes are relative to the instance
    conversations = d.conn.get_all_conversations()['ssh']
    assert conversations[name2][-1][-1]['sent'] == 'hostname\n'
    assert conversations[name1][-1][-1]['sent'] == 'whoami\n'

    # using get_all_conversations_flat. here we get the same as with the same instance name as we are flattening it
    conversations = d.conn.get_all_conversations_flat()['ssh']
    assert conversations[-1]['sent'] == 'hostname\n'

def test_multiple_users():
    DEF_CONN_DICT = dict(proto='ssh', port=922, expected_prompt=r'{username}@.+?:~\$ ')
    user1 = properties.UserInfo(password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    user2 = properties.UserInfo(password='textingcanwait', expected_prompt='\$ ')
    d = DeviceBase('localhost', connections=dict(ssh=DEF_CONN_DICT),
                   users=dict(learner=user1, mysshuser=user2, default_name='learner'))
    with d.conn.open(user='learner') as user1_conn:
        assert user1_conn.check_output('whoami') == 'learner'

    with d.conn.open(user='mysshuser') as user1_conn:
        assert user1_conn.check_output('whoami') == 'mysshuser'


def test_multiple_interfaces():
    DEF_CONN_DICT = dict(proto='ssh', port=922, expected_prompt=r'{username}@.+?:~\$ ')
    user1 = properties.UserInfo(password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    d = DeviceBase('localhost', connections=dict(ssh=DEF_CONN_DICT),
                   users=dict(learner=user1),
                   interfaces=dict(default=dict(ip='127.0.0.1'),
                                   second=dict(ip='1.2.3.4'), default_name='second'))

    with pytest.raises(ConnectionError):
        with d.conn.open() as user1_conn:
            assert user1_conn.check_output('whoami') == 'learner'

    with d.conn.open(interface='default') as user1_conn:
        assert user1_conn.check_output('whoami') == 'learner'

def test_userinfo_in_conn():
    user1 = properties.UserInfo(password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ',
                                                  username='learner')
    DEF_CONN_DICT = dict(proto='ssh', port=922, expected_prompt=r'{username}@.+?:~\$ ', user=user1)
    user2 = properties.UserInfo(password='textingcanwait', expected_prompt='\$ ')
    d = DeviceBase('localhost', connections=dict(ssh=DEF_CONN_DICT),
                   users=dict(mysshuser=user2))
    with d.conn.open() as user1_conn:
        assert user1_conn.check_output('whoami') == 'learner'

def test_multiple_users_default_user_in_conn():
    DEF_CONN_DICT = dict(proto='ssh', port=922, expected_prompt=r'{username}@.+?:~\$ ', user='mysshuser')
    user1 = properties.UserInfo(password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    user2 = properties.UserInfo(password='textingcanwait', expected_prompt='\$ ')
    d = DeviceBase('localhost', connections=dict(ssh=DEF_CONN_DICT),
                   users=dict(learner=user1, mysshuser=user2, default_name='learner'))
    with d.conn.open() as user1_conn:
        assert user1_conn.check_output('whoami') == 'mysshuser'


def test_multiple_users_overrride_conn():
    DEF_CONN_DICT = dict(proto='ssh', username='my_default_user', port=922, expected_prompt=r'{username}@.+?:~\$ ')
    user1 = properties.UserInfo(password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    user2 = properties.UserInfo(password='textingcanwait', expected_prompt='\$ ')
    d = DeviceBase('localhost', connections=dict(ssh=DEF_CONN_DICT),
                   users=dict(learner=user1, mysshuser=user2, default_name='learner'))
    with d.conn.open(user='learner') as user1_conn:
        assert user1_conn.check_output('whoami') == 'learner'

    with d.conn.open(user='mysshuser') as user1_conn:
        assert user1_conn.check_output('whoami') == 'mysshuser'

def test_multiple_users_no_expected_prompt():
    DEF_CONN_DICT = dict(proto='ssh', port=922, expected_prompt=r'{username}@.+?:~\$ ')
    user1 = properties.UserInfo(password='textingcanwait', expected_prompt=None)
    user2 = properties.UserInfo(password='textingcanwait', expected_prompt=None)
    d = DeviceBase('localhost', connections=dict(ssh=DEF_CONN_DICT),
                   users=dict(learner=user1, mysshuser=user2))
    d.users.set_default('learner')
    with d.conn.open(user='learner') as user1_conn:
        assert user1_conn.check_output('whoami') == 'learner'

    with d.conn.open(user='mysshuser') as user1_conn:
        assert user1_conn.check_output('whoami') == 'mysshuser'

def test_ssh_key_conn_open_via_with():
    conn_info = dict(DEF_CONN_DICT_KEY)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with d.conn.open():
        assert d.conn.check_output('whoami') == d.users.default.username

def test_ssh_key():
    conn_info = dict(DEF_CONN_DICT_KEY_ENC)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with d.conn.open():
        assert d.conn.check_output('whoami') == d.users.default.username


def test_ssh_key_wrong_key_pass_raises_BadSshKeyPasswordError():
    conn_info = dict(DEF_CONN_DICT_KEY_ENC)
    conn_info['user']['key_password'] = 'wrong'
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with pytest.raises(BadSshKeyPasswordError):
        d.conn.open()


def test_ssh_connection_via_connection_info_using_with():
    conn_info = dict(DEF_CONN_DICT_KEY)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with d.conn.default as c:
        assert c.check_output('whoami') == d.users.default.username


def test_ssh_connection_via_connection_info_using_open_close():
    conn_info = dict(DEF_CONN_DICT_KEY)
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    c = d.conn.default.open()
    assert c.check_output('whoami') == d.users.default.username
    d.conn.default.close()


def test_ssh_connection_with_file_storage_of_converstation():
    conn_info = dict(DEF_CONN_DICT)

    from io import StringIO
    mystream = StringIO()
    conn_info['data_stream'] = mystream
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with d.conn.open():
        try:
            assert d.conn.check_output('whoami') == d.users.default.username
        except:
            raise

def test_ssh_connection_with_different_file_storage_of_converstation_for_new_open_connection():
    conn_info = dict(DEF_CONN_DICT)

    from io import StringIO
    mystream = StringIO()
    conn_info['data_stream'] = mystream
    d = DeviceBase('localhost', connections=dict(default=conn_info))
    d.os.can_change_prompt = False
    with d.conn.open():
        assert d.conn.check_output('whoami') == d.users.default.username

    from io import StringIO
    mystream2 = StringIO()
    with d.conn.open(data_stream=mystream2):
        try:
            assert d.conn.check_output('whoami') == d.users.default.username
        except:
            raise
    assert mystream.getvalue().splitlines()[-4:] == mystream2.getvalue().splitlines()[-4:]

def test_expected_prompt_from_connection_is_used_when_user_does_nor_provide_it():
    DEF_CONN_DICT = dict(proto='ssh', port=922, expected_prompt=r'{username}@.+?:~\$ ')
    user1 = properties.UserInfo(password='textingcanwait')
    d = DeviceBase('localhost', connections=dict(ssh=DEF_CONN_DICT),
                   users=dict(learner=user1))
    with d.conn.open(user='learner') as user1_conn:
        assert user1_conn.check_output('whoami') == 'learner'

def test_send_cmds_to_default_connections_from_device_level_attributes():
    conn_info = dict(DEF_CONN_DICT)

    d = DeviceBase('localhost', connections=dict(default=conn_info))
    # default context for connection opens the default connection
    with d.conn:

        # unknown method on device defaults to send to default open connection
        assert d.check_output('whoami') == d.users.default.username


def test_send_cmds_with_typo_on_open_conn_raises_AttributeError():
    conn_info = dict(DEF_CONN_DICT)

    d = DeviceBase('localhost', connections=dict(default=conn_info))
    # default context for connection opens the default connection
    with pytest.raises(AttributeError):
        with d.conn:
            # unknown method on device defaults to send to default open connection
            d.check_outputt('whoami')


def test_send_cmds_to_default_connections_from_device_level_attributes_to_not_open_conn_raises_ConnectionInstanceOpenError():
    conn_info = dict(DEF_CONN_DICT)

    d = DeviceBase('localhost', connections=dict(default=conn_info))
    with pytest.raises(ConnectionInstanceOpenError):
        assert d.check_output('whoami') == d.users.default.username


def test_device_open_connection_with_user_lacking_all_auth_keys_raises_UserAuthenticationValuesError():
    DEF_CONN_DICT = dict(proto='ssh',
                         user=dict(username='my_default_user'), port=922, expected_prompt=r'{username}@.+?:~\$ ')
    d = DeviceBase('localhost', connections=dict(ssh=DEF_CONN_DICT))
    with pytest.raises(exceptions.UserAuthenticationValuesError):
        with d.conn.open(user='my_default_user'):
            pass


def test_device_uses_currently_open_connection_when_using_connection_cmd_directly():
    DEF_CONN_DICT = dict(proto='ssh', username='my_default_user', port=922, expected_prompt=r'{username}@.+?:~\$ ')
    user1 = properties.UserInfo(password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    user2 = properties.UserInfo(password='textingcanwait', expected_prompt='\$ ')
    d = DeviceBase('localhost', connections=dict(ssh=DEF_CONN_DICT),
                   users=dict(learner=user1, mysshuser=user2, default_name='learner'))
    with d.conn.open(user='mysshuser'):
        assert d.check_output('whoami') == 'mysshuser'

def test_device_add_set_prompt_while_connecting():
    DEF_CONN_DICT = dict(proto='ssh', port=922)
    user1 = properties.UserInfo(password='textingcanwait', expected_prompt=r'{username}@.+?\:\~\$ ')
    d = DeviceBase('localhost', connections=dict(ssh=DEF_CONN_DICT), users=dict(learner=user1))
    d.os.can_change_prompt = True
    d.os.cmd.set_prompt = lambda prompt: 'export PS1=' + str(prompt)
    with d.conn.open():
        assert re.search(constants.UNIQUE_PROMPT_RE, d.conn.prompt)


def test_device_add_set_prompt_implicit_by_device_os():
    DEF_CONN_DICT = dict(proto='ssh', port=922)
    user1 = properties.UserInfo(password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    d = linux.LinuxDevice('localhost', connections=dict(ssh=DEF_CONN_DICT), users=dict(learner=user1))
    with d.conn.open():
        assert re.search(constants.UNIQUE_PROMPT_RE, d.conn.prompt)


def test_connection_override_device_os_set_prompt():
    DEF_CONN_DICT = dict(proto='ssh', port=922)
    user1 = properties.UserInfo(password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    d = linux.LinuxDevice('localhost', connections=dict(ssh=DEF_CONN_DICT), users=dict(learner=user1))
    d.os.can_change_prompt = False
    with d.conn.open():
        assert re.search(user1.expected_prompt.format(username='learner'),
                         d.conn.prompt.replace('\\', '')) is not None


def test_saving_restoring_connections_to_db():
    update_db_config()

    DEF_CONN_DICT = dict(proto='ssh', port=922)
    user1 = properties.UserInfo(password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    d = Device('localhost', connections=dict(ssh=DEF_CONN_DICT), users=dict(learner=user1))
    d.os.can_change_prompt = False
    with d.conn.open():
        assert re.search(user1.expected_prompt.format(username='learner'),
                         d.conn.prompt.replace('\\', '')) is not None

    try:
        d.save()
    except Exception:
        from fdutils.db import sasessioninit
        #d.dbsession.rollback()
        raise

    d2 = Device.get_by_hostname('localhost')
    with d2.conn.open():
        assert re.search(user1.expected_prompt.format(username='learner'),
                         d2.conn.prompt_found.replace('\\', '')) is not None


def test_saving_restoring_connections_to_db_custom_name():
    class Devices2(TableNamedDevice):
        pass

    update_db_config()

    DEF_CONN_DICT = dict(proto='ssh', port=922)
    user1 = properties.UserInfo(password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    d = Devices2('localhost', connections=dict(ssh=DEF_CONN_DICT), users=dict(learner=user1))
    d.os.can_change_prompt = False
    with d.conn.open():
        assert re.search(user1.expected_prompt.format(username='learner'),
                         d.conn.prompt.replace('\\', '')) is not None

    try:
        d.save()
    except Exception:
        from fdutils.db import sasessioninit
        #d.dbsession.rollback()
        raise

    d2 = Devices2.get_by_hostname('localhost')
    with d2.conn.open():
        assert re.search(user1.expected_prompt.format(username='learner'),
                         d2.conn.prompt_found.replace('\\', '')) is not None


def test_cmd_connection_no_tunnel():
    user1 = properties.UserInfo(username='learner',
                                                  password='textingcanwait',
                                                  expected_prompt=r'{username}@.+?:~\$ ')
    d = Device('localhost',
               connections=dict(t={'proto': 'command', 'cmd': 'telnet 127.0.0.1', 'user': user1, 'can_change_prompt': False}),
               users=dict(learner=user1))
    with pytest.raises(ConnectionError):
        with d.conn.open():
            try:
                if not d.check_output('whoami') == d.users.default.username:
                    raise Exception
                else:
                    assert True
            except Exception:
                import pprint
                pprint.pprint(d.conn.get_all_conversations_flat())

                raise


def test_multihop():
    user1 = properties.UserInfo(username='learner',
                                                  password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    hops = [
            {'host': '127.0.0.1', 'user': user1, 'port': 922, 'password': 'textingcanwait'},
            {'host': '127.0.0.1', 'user': user1},
            {'user': user1, 'proto': 'command', 'cmd': 'telnet 127.0.0.1', 'can_change_prompt': False}
          ]

    d = Device('localhost',
               connections=dict(cmd={'tunnel': dict(hops=hops),
                                     'proto': 'command', 'cmd': 'telnet 127.0.0.1'}),
               users=dict(learner=user1))
    try:
        with d.conn.open():

            if not d.check_output('whoami') == d.users.default.username:
                raise Exception
            else:
                assert True
                print(d.check_output('netstat -ant|grep -v TIME_WAIT'))
    except Exception:
        import pprint
        pprint.pprint(d.conn.get_all_conversations_flat())

        raise


def test_multihop_hostname_interface():
    user1 = properties.UserInfo(username='learner',
                                                  password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    hops = [
            {'host': '127.0.0.1', 'user': user1, 'port': 922, 'password': 'textingcanwait'},
            {'host': '127.0.0.1', 'user': user1},
            {'user': user1, 'proto': 'command', 'cmd': 'telnet 127.0.0.1', 'can_change_prompt': False}
          ]

    d = Device('localhost_name',
               connections=dict(cmd={'tunnel': dict(hops=hops),
                                     'proto': 'command', 'cmd': 'telnet 127.0.0.1'}),
               interfaces=dict(default={'ip': 'localhost'}),
               users=dict(learner=user1))
    try:
        with d.conn.open():

            if not d.check_output('whoami') == d.users.default.username:
                raise Exception
            else:
                assert True
                print(d.check_output('netstat -ant|grep -v TIME_WAIT'))
    except Exception:
        import pprint
        pprint.pprint(d.conn.get_all_conversations_flat())

        raise


def test_multihop_tunnel_tunnel_defined():
    user1 = properties.UserInfo(username='learner',
                                                  password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    tunnel = dict(name='t1',
                  hops=[
                      {'host': '127.0.0.1', 'user': user1, 'port': 922, 'password': 'textingcanwait'},
                      {'host': '127.0.0.1', 'user': user1, 'proto': 'telnet'},
                      {'host': '127.0.0.1', 'user': user1}
                  ])

    d = Device('localhost',
               connections=dict(ssh={'tunnel': tunnel}),
               users=dict(learner=user1))
    with d.conn.open():
        try:
            if not d.check_output('whoami') == d.users.default.username:
                raise Exception
            else:
                assert True
        except Exception:
            import pprint
            pprint.pprint(d.conn.get_all_conversations_flat())
            raise

def test_multihop_tunnel_tunnel_by_name():
    user1 = properties.UserInfo(username='learner', password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    tunnel = dict(
                  hops=[
                      {'host': '127.0.0.1', 'user': user1, 'port': 922, 'password': 'textingcanwait'},
                      {'host': '127.0.0.1', 'user': user1, 'proto': 'telnet'},
                      {'host': '127.0.0.1', 'user': user1}
                  ])

    d = Device('localhost',
               connections=dict(ssh={}),
               users=dict(learner=user1),
               tunnels=dict(t1=tunnel))
    with d.conn.open(tunnel='t1'):
        try:
            if not d.check_output('whoami') == d.users.default.username:
                raise Exception
            else:
                assert True
        except Exception:
            import pprint
            pprint.pprint(d.conn.get_all_conversations_flat())
            raise


def test_multihop_mix_proto_tunnel_as_list_of_hops():
    user1 = properties.UserInfo(username='learner', password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    hops = [
        {'host': '127.0.0.1', 'user': user1, 'port': 922, 'password': 'textingcanwait'},
        {'host': '127.0.0.1', 'user': user1, 'proto': 'telnet'},
        {'host': '127.0.0.1', 'user': user1}
    ]

    d = Device('localhost',
               connections=dict(ssh={'tunnel': dict(hops=hops)}),
               users=dict(learner=user1))
    import time
    t0 = time.time()


    with d.conn.open():
        print(time.time() - t0)
        try:
            if not d.check_output('whoami') == d.users.default.username:
                raise Exception
            else:
                assert True
        except Exception:
            import pprint
            pprint.pprint(d.conn.get_all_conversations_flat())
            raise


def test_multihop_tunnel_default_tunnel():
    user1 = properties.UserInfo(username='learner', password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    tunnel = dict(
                  hops=[
                      {'host': '127.0.0.1', 'user': user1, 'port': 922, 'password': 'textingcanwait'},
                      {'host': '127.0.0.1', 'user': user1, 'proto': 'telnet'},
                      {'host': '127.0.0.1', 'user': user1}
                  ])

    d = Device('localhost',
               connections=dict(ssh={},
                                default_tunnel='t1'),
               users=dict(learner=user1),
               tunnels=dict(t1=tunnel))
    with d.conn.open():
        try:
            if not d.check_output('whoami') == d.users.default.username:
                raise Exception
            else:
                assert True
        except Exception:
            import pprint
            pprint.pprint(d.conn.get_all_conversations_flat())
            raise

    d.conn.default_tunnel = ''
    with pytest.raises(ConnectionError):
        with d.conn.open():
            d.check_output('netstat -ant|grep 22|grep ESTABLISHED|wc -l')


def test_multihop_tunnel_proto_tunnel_as_name():
    user1 = properties.UserInfo(username='learner',
                                                  password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    hops = [
        {'host': '127.0.0.1', 'user': user1, 'port': 922, 'password': 'textingcanwait'},
        {'host': '127.0.0.1', 'user': user1},
        {'host': '127.0.0.1', 'user': user1}
    ]

    d = DeviceBase('localhost',
               connections=dict(ssh={'tunnel': 'default'}),
               tunnels=dict(default={'hops': hops}),
               users=dict(learner=user1))
    with d.conn.open():
        try:
            if not d.check_output('whoami') == d.users.default.username:
                raise Exception
            else:
                assert True
        except Exception:
            import pprint
            pprint.pprint(d.conn.get_all_conversations_flat())
            raise

    print('hello')


def test_saving_restoring_connections_multihop_to_db():
    update_db_config()

    user1 = properties.UserInfo(username='learner',
                                                  password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    jump_boxes = [
            {'host': '127.0.0.1', 'user': user1, 'port': 922},
            {'host': '127.0.0.1', 'user': user1},
            {'host': '127.0.0.1', 'user': user1}
          ]

    d = Device('localhost',
               connections=dict(ssh={'tunnel': dict(hops=jump_boxes)}),
               users=dict(learner=user1), encrypt_passwords=True)

    t0 = time.time()
    d.os.can_change_prompt = False
    with d.conn.open():
        print(time.time() - t0)
        assert re.search(user1.expected_prompt.format(username='learner'),
                         d.conn.prompt.replace('\\', '')) is not None

    try:
        d.save()
    except Exception:
        from fdutils.db import sasessioninit
        #d.dbsession.rollback()
        raise

    t0 = time.time()
    d2 = Device.get_by_hostname('localhost')
    with d2.conn.open():
        print(time.time() - t0)
        assert re.search(user1.expected_prompt.format(username='learner'),
                         d2.conn.prompt_found.replace('\\', '')) is not None
    t0 = time.time()
    with d2.conn.open():
        print(time.time() - t0)
        assert re.search(user1.expected_prompt.format(username='learner'),
                         d2.conn.prompt_found.replace('\\', '')) is not None


def test_saving_restoring_connections_multihop_to_db_reload():
    update_db_config(False, False)

    user1 = properties.UserInfo(username='learner',
                                                  password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')

    t0 = time.time()
    d2 = Device.get_by_host('localhost')
    with d2.conn.open():
        print(time.time() - t0)
        assert re.search(user1.expected_prompt.format(username='learner'),
                         d2.conn.prompt_found.replace('\\', '')) is not None
    t0 = time.time()
    with d2.conn.open():
        print(time.time() - t0)
        assert re.search(user1.expected_prompt.format(username='learner'),
                         d2.conn.prompt_found.replace('\\', '')) is not None


def test_remove_user_related_info_from_connection():

    DEF_CONN_DICT = dict(proto='ssh', port=922, username='user2',
                         password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')
    user1 = properties.UserInfo(password='textingcanwait', expected_prompt=r'{username}@.+?:~\$ ')

    d = DeviceBase('localhost', connections=dict(ssh=DEF_CONN_DICT), users=dict(learner=user1))
    d.os.can_change_prompt = False

    for user_attr in ('username', 'password', 'key_filename', 'key_password'):
        with pytest.raises(AttributeError):
            getattr(d.conn.default, user_attr)

def test_opening_closing_wihtout_context():
    connections = {'ssh': {'user': 'learner', 'port': 922},  # default user for ssh will be learner
                   'telnet': {'user': 'learner'},  # default user for telnet will be mysshuser
                   'default_name': 'ssh'}
    users = {'learner': {'password': 'textingcanwait'},
             'mysshuser': {'password': 'textingcanwait'},
             'default_name': 'mysshuser'}

    d = DeviceBase('localhost', connections=connections, users=users)
    d.conn.open()
    d.check_output('whoami')
    d.conn.close()
    assert True

def test_mixed_default_values_user_conn():
    connections = {'ssh': {'user': 'default', 'port': 922},  # default user for ssh will be default (username is learner)
                   'telnet': {'user': 'mysshuser'},  # default user for telnet will be mysshuser
                   'default_name': 'ssh'}
    users = {'default': {'password': 'textingcanwait', 'username': 'learner'},
             'mysshuser': {'password': 'textingcanwait'},
             'default_name': 'mysshuser'}
    d = DeviceBase('localhost', connections=connections, users=users)
    d.conn.open()
    d.check_output('whoami')
    d.conn.close()
    assert True


def test_tunnel_open_sockets():
    users = {'default': {'password': 'textingcanwait', 'username': 'learner'},
             'mysshuser': {'password': 'textingcanwait'},
             'default_name': 'mysshuser'}
    connections = {'ssh': {'user': 'default'},  # default user for ssh will be default (username is learner)
                   'telnet': {'user': 'mysshuser'},  # default user for telnet will be mysshuser
                   'default_name': 'ssh'}
    tunnels = {'default':
                   {'hops': [{'host': '127.0.0.1', 'port': 922,
                              'user': users['default']
                              }]
                    }}
    dev2 = DeviceBase(host='localhost',
                 users=users,
                 connections=connections,
                 tunnels=tunnels,
                 os_name='linux', # by default it is linux anyway
                 storage_path='.' # where to store any files downloaded from the device
            )
    with dev2.conn.open(user='mysshuser', tunnel='default') as conn:
        print(dev2.check_output('netstat -ant | grep ESTABLISHED|grep 22'))


def test_mix_tunnel_encrypted_keys_after_telnet_raises_notimplementederror():
    """ we raise an error if we try to send ssh key password using telnet """
    hops = [
            {'host': '127.0.0.1', 'user': USERS['learner'], 'port': 922,},
            {'host': '127.0.0.1', 'user': USERS['learner']},
            {'host': '127.0.0.1', 'user': USERS['learner'], 'proto': 'telnet'}
          ]

    d = Device('localhost',
               connections=dict(ssh={}),
               users=USERS,
               tunnels=dict(default=dict(hops=hops)))
    with pytest.raises(NotImplementedError):
        with d.conn.open(tunnel='default', user='mysshuser'):  # using mysshuser for the connection after the tunnel
            pass
