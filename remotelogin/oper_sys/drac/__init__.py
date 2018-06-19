from remotelogin.oper_sys.base import OSBase
from . import shellcommands


class DellDrac(OSBase):
    shell_cmds_module = shellcommands
    ssh_app = 'ssh'
    name = 'drac'
    expected_prompt = 'racadm> '
    can_resize_pty = False
