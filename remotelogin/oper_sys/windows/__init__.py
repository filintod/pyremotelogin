import os
import subprocess

import re
from datetime import datetime

from remotelogin.connections import settings
from .. import base
from fdutils.files import get_executable_path
from fdutils.lists import is_list_or_tuple

__author__ = 'Filinto Duran (duranto@gmail.com)'

import logging
log = logging.getLogger(__name__)
from . import shellcommands

BEG_CERT = '-----BEGIN CERTIFICATE-----'
BEG_CERT_LEN = len(BEG_CERT)
END_CERT = '-----END CERTIFICATE-----'
END_CERT_LEN = len(END_CERT)


class Arg:
    def __init__(self, arg, mytype=str, can_have_spaces=False):
        self.arg = arg
        self.type = mytype
        self.can_have_spaces= can_have_spaces

    def validate(self, name, other):
        if not isinstance(other, self.type):
            raise TypeError('Bad type for argument ({})'.format(name))


class SSHApp:
    args = {'options': Arg('-o', list),
            'username': Arg('-l'),
            'password': Arg('-pwd', can_have_spaces=True),
            'key_filename': Arg('-i', can_have_spaces=True),
            'port': Arg('-p', int),
            'enable_tty': Arg('-t', bool),
            'disable_tty': Arg('-T', bool)
            }

    def __init__(self, app_path='ssh'):
        self.app_path = app_path

    def create_connection_string(self, remote_host, **kwargs):
        args = []
        for k,v in kwargs.items():
            if k in self.args:

                if isinstance(v, str):
                    v = '"' + v + '"'

                if not is_list_or_tuple(self.args[k]) and is_list_or_tuple(v):
                    raise ValueError('This argument ({}) is not expected to be a list an you provided a list ({})'
                                     ''.format(k, v))
                elif is_list_or_tuple(v):
                    for value in v:
                        args.append(self.args[k] + ' ' + value)

                # elif :





        # if args:
        #     args = ' ' + args
        # if password:
        #     password = ' -pw {password}'.format(password=password)
        # if key_filename:
        #     key_filename = ' i "{}"'.format(key_filename)
        # return 'plink -p {port} -l {username}{args}{password}{keyfile} {host} {args}' \
        #        ''.format(port=port, username=username, args=args, password=password, keyfile=key_filename, host=host)


class PuttyPLinkString(SSHApp):

    def create_connection_string(self, port, key_filename, args, username, password, host, **kwargs):
        if args:
            args = ' ' + args
        if password:
            password = ' -pw {password}'.format(password=password)
        if key_filename:
            key_filename = ' i "{}"'.format(key_filename)
        return 'plink -P {port} -l {username}{args}{password}{keyfile} {host}' \
               ''.format(port=port, username=username, args=args, password=password, keyfile=key_filename, host=host)


class WindowsOS(base.OSBase):

    cmd = shellcommands.get_instance()
    dev_null = 'nul'
    temp = r'%USERPROFILE%\AppData\Local\Temp'
    ssh_app = None
    sudo = 'runas /profile /user:Administrator'
    name = 'windows'

    # TODO: check on windows 10
    def _get_ssh_app(self):
        """  try to find windows ssh either.

        this only works on local connections not on remote

        WINDOWS ssh apps we are looking for:
                plink (https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html)
                windows openssh (https://github.com/PowerShell/Win32-OpenSSH/releases)
        Returns: str or None

        """
        # path_ssh = get_executable_path('ssh.exe')
        # if path_ssh:
        #     return path_ssh
        path_putty = get_executable_path('plink.exe', win_program_file_loc='PUTTY')
        if path_putty:
            return path_putty
        return None

    def __init__(self, can_change_prompt=True):
        super(WindowsOS, self).__init__(can_change_prompt=can_change_prompt)
        self.ssh_app = self._get_ssh_app()
        self.shell_app = os.environ.get('CSIDL_SYSTEM', r'c:\Windows\System32')  + '\cmd.exe'

    @property
    def path(self):
        import ntpath
        return ntpath

    def __repr__(self):
        return "WindowsOS()"

    def connect_to_folder(self, folder_path, username, password, domain):
        if not self.path().isdir(folder_path):
            if domain:
                domain = domain.rstrip('\\').lstrip('.') + '\\'

            if username:
                username = username.lstrip('\\')

            mount_command = "net use {} /delete".format(folder_path)
            os.system(mount_command)
            mount_command = "net use /user:{} {} {}".format(domain + username, folder_path, password)
            os.system(mount_command)
            backup_storage_available = os.path.isdir(folder_path)

            if not backup_storage_available:
                print("could not login to " + folder_path)
                return False
        return True

    def base64_clean(self, data):
        beg_cert = data.find(BEG_CERT)
        if beg_cert == -1:
            return data
        return data[data[beg_cert + BEG_CERT_LEN + 1: data.rfind(END_CERT) - 1]]

    def md5sum_clean(self, data):
        lines = data.splitlines()
        if lines[0] and lines[0].startswith('MD5 hash of'):
            return lines[1].lower().replace(' ', '')
        raise ValueError('No MD5 data found')

    def get_info_from_list_file(self, dir_data, filename):
        for line in dir_data.splitlines():
            if filename in line:
                modify_date, modify_time, ampm, size, name = line.split()
                modify_datetime = datetime.strptime('{date} {time} {ampm}'.format(date=modify_date,
                                                                                  time=modify_time, ampm=ampm),
                                                    '%Y/%m/%d %I:%M %p',)

                return modify_datetime, size

        raise FileExistsError('did not find the file')


def ipconfig(all=False):
    return subprocess.check_output("ipconfig {}".format("/all" if all else ""), shell=True).decode(encoding=settings.DECODE_ENCODING_TYPE,
                                                                                                   errors =settings.DECODE_ERROR_ARGUMENT_VALUE)


def hostname():
    return subprocess.check_output("hostname").decode('utf-8').strip()


# TODO: use textfsm
def if_parse(output):

    result = {}
    current_element = ""
    for row in output.splitlines():
        if row:
            if row[0] != ' ':
                current_element = row.strip(' :')
                if 'adapter' in current_element:
                    adapter_type, current_element = current_element.split(' adapter ')

                result[current_element] = dict()
            else:
                if ':' in row:
                    key, value = row.split(':', 1)
                    result[current_element][key.strip(' .')] = [value.strip()]
                else:
                    result[current_element][row].append(row.strip())
    return result


def neighbors_parse(ipv6=False, interface=""):
    output = subprocess.check_output("netsh int ipv{} {} show neighbor"
                                     "".format("6" if ipv6 else "4", ("interface="+interface) if interface else ""),
                                     shell=True).decode(encoding=settings.DECODE_ENCODING_TYPE,
                                                        errors=settings.DECODE_ERROR_ARGUMENT_VALUE)
    result = {}
    current_element = ""
    for row in output.splitlines():
        if row.strip():
            if row.startswith('Interface'):
                k, v = row.split(":", 1)
                current_element = v.strip()
                result[current_element] = dict()
            else:
                if not row.startswith('Internet') and not row.startswith('----'):
                    entry = re.split('\s+', row, 2)
                    if len(entry) == 3:
                        ip, mac, entry_type = entry
                    else:
                        ip, entry_type = entry
                        mac = ''
                    result[current_element][ip.strip()] = dict(mac=mac.strip(), type=entry_type.strip())
    return result


def enable(interface_name="DUT_LAN", enable=True):
    subprocess.check_output("netsh interface set \"interface\" {} {}ABLED".format(
        interface_name, "EN" if enable else "DIS")).decode(encoding=settings.DECODE_ENCODING_TYPE,
                                                           errors=settings.DECODE_ERROR_ARGUMENT_VALUE)


def disable(interface_name="DUT_LAN"):
    return enable(interface_name, False)


def dhcp_renew(interface_name="DUT_LAN", ipv6=False, renew=True):
    return subprocess.check_output("ipconfig /re{}{} {} ".format("new" if renew else "lease", "6" if ipv6 else "",
                                                                 interface_name)).decode(
        encoding=settings.DECODE_ENCODING_TYPE, errors=settings.DECODE_ERROR_ARGUMENT_VALUE)


def dhcp_release(interface_name="DUT_LAN", ipv6=False):
    return dhcp_renew(interface_name, ipv6, False)


def flush_dns():
    subprocess.call("ipconfig /flushdns")


def _get_version_interface(addr, interface):
    netsh = "netsh int ipv" + ("6" if ':' in addr else "4") + " "
    if interface:
        interface = "interface=\"{}\"".format(interface)
    return netsh, interface


def delete_info(interface, host, info_type):
    """ deletes information (dnsserver, neighbor, from an interface
    """
    netsh, interface = _get_version_interface(host, interface)

    if host:
        host = "address=" + host
    subprocess.call(netsh + " delete {} \"{}\" {}".format(interface, host, info_type))


def flush_neighbors(interface="", host="", flush_type=""):
    return delete_info(interface, host, 'neighbors')


def route_add(destination, prefix, gw, interface="", site_prefix=""):
    netsh, interface = _get_version_interface(destination, interface)
    if site_prefix:
        site_prefix = "siteprefixlength=" + site_prefix
    subprocess.call(netsh + 'add route {}/{} {} nexthop={}  {}'.format(destination, prefix, interface, gw, site_prefix))


def route_del(destination, prefix, gw="", interface=""):
    netsh, interface = _get_version_interface(destination, interface)
    subprocess.call(netsh + 'delete route {}/{} {} {}'.format(destination, prefix, interface,
                                                              ("nexthop=" + gw) if gw else ""))


