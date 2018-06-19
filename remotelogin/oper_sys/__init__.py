from . import base, busybox, cisco, linux, unix, windows, alcatel, ilo

__author__ = 'Filinto Duran (duranto@gmail.com)'


# TODO: autoregister/plugin vendors
def os_factory(os_name='', **os_kwargs):
    """ returns an OS instance. defaults to LinuxOS

    Args:
        os_name:

    Returns: remotelogin.oper_sys.base.OSBase

    """
    if not os_name:
        return linux.LinuxOS()

    os_name = os_name.lower()

    platform_to_object = dict(
        linux=linux.LinuxOS,
        win=windows.WindowsOS,
        windows=windows.WindowsOS,
        win32=windows.WindowsOS,
        darwin=unix.UnixOS,
        alcatel=alcatel.AlcatelOS,
        cisco=cisco.CiscoIOS,
        ios=cisco.CiscoIOS,
        ilo=ilo.iLOOS,
        cisco_ace=cisco.CiscoIOSACE,
        busybox=busybox.BusyBoxOS
    )
    for _os, _os_obj in platform_to_object.items():
        if os_name.startswith(_os):
            return _os_obj(**os_kwargs)
    else:
        raise ValueError('This os ({}) is not defined yet'.format(os_name))
