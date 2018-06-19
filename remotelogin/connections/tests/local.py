from remotelogin.connections import local
import time

from remotelogin.connections.ssh import SshConnection

local = local.LocalConnection(with_shell=True, os='windows')
print(local)
with local.open() as l:
    print(l.check_output('dir\n'))
    th = l.check_output_nb('dir\n')
    time.sleep(1)
    print(th.get_all_data())

print("after...")
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
rdo_conn = SshConnection('localhost', username='learner', password='textingcanwait',
                         port=922, connect_timeout=plink_connect_timeout).through(local)
with rdo_conn:
    print(rdo_conn.check_output('ls -lt'))

