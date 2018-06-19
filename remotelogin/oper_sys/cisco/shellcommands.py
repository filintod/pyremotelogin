from __future__ import absolute_import

__author__ = 'Filinto Duran (duranto@gmail.com)'

import logging
log = logging.getLogger(__name__)
from .. import base


class CiscoIOSShellCmds(base.OSCommands):

    CAT = 'type'

    def set_prompt(self, prompt):
        return "set prompt " + prompt

    def resize_pty(self, cols, rows):
        return r"terminal length 0\nterminal width {}".format(cols)

    def md5checksum(self, file_path):
        return 'verify /md5 {}'.format(file_path)
    md5sum = md5checksum
