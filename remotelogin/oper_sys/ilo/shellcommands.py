import logging

from remotelogin.oper_sys.base import OSCommands

log = logging.getLogger(__name__)


class iLOShellCmds(OSCommands):

    def cat_to_file(self, file_path, message):
        raise NotImplementedError

    def remove(self, file_path):
        raise NotImplementedError

    def list_file(self, file_path):
        raise NotImplementedError


Instance = None


def get_instance():
    global Instance
    if Instance is None:
        Instance = iLOShellCmds()
    return Instance
