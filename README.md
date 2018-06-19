Remotelogin: SSH/Telnet/Local login helper
==========================================

**Note: This package will only run in Python version 3.4+**

The remotelogin package has three main packages:

- connections
- devices
- fdutils

------
## remotelogin.connections
This package contains abstractions to connections to a device.
The connection can be via SSH, Telnet, or command line for local connections.
A connection can be command-only, where no terminal is required but
no profile is loaded and probably no file wildcard expansion is allowed;
or a TerminalConnection where we have full terminal interactivity with profiles
loaded and can keep our environment variables on.


An example of simple ssh connection:

``` python
from remotelogin.connections.ssh import SshConnection
ssh = SshConnection(host='127.0.0.1',
                    username='learner',
                    password='textingcanwait')

with ssh.open() as conn:
    print('My Hostname is: {}'.format(conn.check_output('hostname')))
```        

A multi-hop connection, where we want to connect to a target device but
 we first need to connect to one or more intermediate devices:

``` python
from remotelogin.connections.ssh import SshConnection
from remotelogin.connections.telnet import TelnetConnection
from remotelogin.connections.terminal import TerminalConnection

vm_info=dict(host="127.0.0.1",
             username="learner",
             password="textingcanwait",
             expected_prompt=r'learner\@ubuntu\:\~\$')

hop1=SshConnection(**vm_info)
hop2=TelnetConnection(**vm_info)
target=SshConnection(**vm_info)

multihop = TerminalConnection(hop1, hop2, target)

with multihop.open() as conn:
    # printing the full conversation through the three connections 
    print(conn.get_conversation_string())

```

------

## remotelogin.devices
This package contains a higher layer abstraction for devices that is
comprise of a set of connections, a set of users, a set of files related
to the device, and a set of services (even though this last one is not implemented)

------

## remotelogin.fdutils
This package contains a set of utilities that range from tools to use selenium (fdutils.selenium_util),
to files utilities (fdutils.files), to tools to donwload resources from the web (fdutils.web),
and several others that I frequently used.  They are not all needed for
the remotelogin package but I usually keep them together for my own benefit.

The tools in this package can be used by itself usually,
and they are actually use by the connections and devices packages.