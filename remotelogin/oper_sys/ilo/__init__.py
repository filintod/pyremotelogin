from remotelogin.oper_sys.base import OSBase
from . import shellcommands


class iLOOS(OSBase):
    shell_cmds_module = shellcommands
    ssh_app = 'ssh'
    name = 'ilo'
    expected_prompt = r'</>hpiLO-> '
    can_resize_pty = False
    cd_expected_prompt = r'<{pwd}/>hpiLO-> '
