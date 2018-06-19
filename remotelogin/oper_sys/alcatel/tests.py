from remotelogin.devices import DeviceBase


def test_alcatel():
    users={'admin': {'password': 'switch'}}
    d = DeviceBase(host='192.168.1.250', users=users, connections={'ssh':{}}, os_name='alcatel')
    with d.conn.open() as conn:
        print(conn.check_output('show vlan port'))
