import contextlib
import logging

from ..base import OSBase
from . import shellcommands

log = logging.getLogger(__name__)

__author__ = 'Filinto Duran (duranto@gmail.com)'


# from https://github.com/paramiko/paramiko/issues/750
def _override_check_dsa_parameters(parameters):
    """Override check_dsa_parameters from cryptography's dsa.py

    Allows for shorter or longer parameters.p to be returned from the server's host key. This is a
    HORRIBLE hack and a security risk, please remove if possible!
    """

    from cryptography import utils

    # if utils.bit_length(parameters.p) not in [1024, 2048, 3072]:
    # raise ValueError("p is {}, must be exactly 1024, 2048, or 3072 bits long".format(utils.bit_length(parameters.p)))
    if utils.bit_length(parameters.q) not in [160, 256]:
        raise ValueError("q must be exactly 160 or 256 bits long")

    if not (1 < parameters.g < parameters.p):
        raise ValueError("g, p don't satisfy 1 < g < p.")


class AlcatelOS(OSBase):
    cmd = shellcommands.AlcatelShellCmds()
    ssh_app = 'ssh'
    name = 'alcatel'
    expected_prompt = r'(\-\>\s+|' + OSBase.unique_prompt_re + r'\s+)'
    default_prompt = '-> '
    unique_prompt_format = '@@fidozqkyPROMPT@@'
    reset_prompt_on_exit = True

    def __init__(self, can_change_prompt=True):
        super().__init__(can_change_prompt=can_change_prompt)

    @contextlib.contextmanager
    def monkey_patch_ssh(self):

        from cryptography.hazmat.primitives.asymmetric import dsa

        old_dsa = dsa._check_dsa_parameters
        try:
            dsa._check_dsa_parameters = _override_check_dsa_parameters
            yield
        finally:
            dsa._check_dsa_parameters = old_dsa
