import logging

from ..base import OSBase
from . import shellcommands

log = logging.getLogger(__name__)

__author__ = 'Filinto Duran (duranto@gmail.com)'


#decorator to check if system is in privileged level before executing function
def privilege_level_required(f):
    def deco_retry(*args, **kwargs):
        if not args[0].is_level_privileged:
            log.error('Trying to execute a function that needs System to be in Privilege Mode')
            raise Exception
        return f(*args, **kwargs)
    return deco_retry


class CiscoIOS(OSBase):
    cmd = shellcommands.CiscoIOSShellCmds()
    ssh_app = 'ssh'
    name = 'cisco'

    def __init__(self, can_change_prompt=True):
        super(CiscoIOS, self).__init__(can_change_prompt=can_change_prompt)
        self.is_level_privileged = False

    def enable(self, password='', conn=None):
        password = password if password else self.connections.password
        conn.send_command_after_expected_response('en', 'Password: ', password)
        # disable pauses on return buffers
        self.is_level_privileged = False

    def md5sum_clean(self, data):
        if 'no such file' in data.lower():
            raise ValueError('No MD5 sum or no file found')
        return data.splitlines()[-1].split('=')[1].lower().strip()

    def enter_config(self, conn=None):
        conn.send_command('config t')
        self.is_level_privileged = True

    def show_running_configuration(self, conn=None):
        return conn.check_output('sh run')

    def ssh_enable(self):
        """
        conf t
ip domain-name domain
crypto key generate rsa
aaa new-model
#aaa authentication login default local
#aaa authorization exec default local
aaa authorization network default local
username admin password 0 <your password>
        """
        pass

    @privilege_level_required
    def updown_interface(self, interface, up=True, conn=None):
        conn.check_output('int ' + interface)
        if up:
            self.cmd('no shutdown')
        else:
            self.cmd('shutdown')
        conn.check_output('exit')


class CiscoIOSACE(CiscoIOS):

    def show_authentication_stats(self, device='server', **kwargs):
        if not device == 'server' and not device == 'client':
            log.error('This command can only accept a device value of "sever" or "client" ')
            raise Exception
        return self.cmd('show stats crypto {0} authentication'.format(device), **kwargs)[0]

    def retrieve_list_of_crypto_files(self, **kwargs):
        files, error = self.cmd('show crypto files', **kwargs)
        return files

    def export_crypto_file(self, file_name, **kwargs):
        export_key, error = self.cmd('crypto export ' + file_name, **kwargs)
