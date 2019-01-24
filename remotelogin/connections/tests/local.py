from remotelogin.connections import local
import time

from remotelogin.connections.ssh import SshConnection

local = local.LocalConnection(with_shell=True)
print(local)


def test_private_key_encrypted(self):
    ssh = SshConnection(host='github-libvirt2.r1.01a.as1.gaikai.org', username='fduran',
                        key_filename='/home/fduran/.ssh/id_crt', key_password='6wt5sEQ5LL8b',
                        key_public='/home/fduran/.ssh/id_rsa.pub')
    # ssh = SshConnection(host='esq1.r2.03.snaa.gaikai.org', username='fduran',
    #                     key_filename='/home/fduran/.ssh/id_crt_priv_clear')

    ssh.open()
    # SHA256:IowKDSEO7s+Ab0Oai2Iw0mzbL0rXRCev5seYo/nImMk
    # SHA256:IowKDSEO7s+Ab0Oai2Iw0mzbL0rXRCev5seYo/nImMk


with local.open() as l:
    print(l.check_output('ls -l'))


print("after...")
exit()
to = [time.time()]
import re
local.expected_prompt=re.compile(r'C:\\.+\\tests>')
t = local.open_terminal(cols=20)

with t:
    print(t.prompt_found)
    to.append(time.time())
    t.set_prompt("hello>")
    to.append(time.time())
    t._transport.resize_pty(cols=20)
    to.append(time.time())
    t.send_with_stderr('dirr jlajdflajlfkjaldjflka jlaj lfkjlasjflaj aljflakjdflaksj')
    to.append(time.time())
    print(t.recv_wait(0.1))
    to.append(time.time())
    exp = new_prompt = t.send_cmd('dir').send_cmd('cd ..').expect_new_prompt()
    to.append(time.time())
#    print(exp.value)
    print(t.check_output('dir'))
    to.append(time.time())
print([to[i]-to[0] for i in range(len(to))])
# on windows plink takes some time to start
plink_connect_timeout = 2
rdo_conn = SshConnection('localhost', username='learner', password='mypassword',
                         port=922, connect_timeout=plink_connect_timeout).through(local)
with rdo_conn:
    print(rdo_conn.check_output('ls -lt'))

