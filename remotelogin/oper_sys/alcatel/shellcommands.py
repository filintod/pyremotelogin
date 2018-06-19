import logging
log = logging.getLogger(__name__)
from .. import base


class AlcatelShellCmds(base.OSCommands):

    CAT = 'type'

    def set_prompt(self, prompt):
        return "session prompt default  " + prompt

    def resize_pty(self, cols, rows):
        return r"tty {rows} {cols}".format(cols=min(max(cols, 150), 150), rows=min(max(rows, 150), 150))


def get_instance():
    global Instance
    if Instance is None:
        Instance = AlcatelShellCmds()
    return Instance
