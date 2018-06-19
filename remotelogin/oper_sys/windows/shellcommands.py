__author__ = 'Filinto Duran (duranto@gmail.com)'

import logging
log = logging.getLogger(__name__)
from .. import base


def escape_cmd_msg(message):
    replace_dict = (('%', '%%'),
                    ('^', '^^'),
                    ('&', '^&'),
                    ('<', '^<'),
                    ('>', '^>'),
                    ('|', '^|'),
                    ("'", "^'"),
                    ('`', '^`'),
                    (',', '^,'),
                    (';', '^;'),
                    ('=', '^='),
                    ('(', '^('),
                    (')', '^)'),
                    ('!', '^^!'),
                    ("\\", "\\\\"),
                    ('[', r'\['),
                    (']', r'\]'),
                    ('"', r'\"'))
    for r, v in replace_dict:
        message = message.replace(r, v)
    return message


class Win32ShellCmds(base.OSCommands):

    CAT = 'type'

    def set_prompt(self, prompt):
        # there are more though...  http://www.hanselman.com/blog/ABetterPROMPTForCMDEXEOrCoolPromptEnvironmentVariablesAndANiceTransparentMultiprompt.aspx
        escape_chars = [('$', '$$'),
                        ('&', '$A'),
                        ('|', '$B'),
                        ('>', '$G'),
                        ('<', '$L'),
                        ('=', '$Q'),
                        (' ', '$S'),
                        ]
        for c, esc in escape_chars:
            prompt = prompt.replace(c, esc)

        return "PROMPT=" + prompt

    def cat_to_file(self, file_path, message):
        """ creates a long line of echo commands

        :param file_path:
        :param message:
        :return:
        """
        ret = ''
        for line in message.splitlines():
            ret += "echo {} >> {} & ".format(escape_cmd_msg(line), file_path)
        return ret

    def setcronjob(self, command, crontab=None, user=None, password=None, ):
        """

        Args:
            command:
            crontab: dictionary (minute='*', hour='*', day='*', month='*', weekday='*'. Follow crontab format)
            user:
            password:

        Returns:

        """

    def resize_pty(self, cols, rows):
        return "mode CON: COLS={} LINES={}".format(cols, rows)

    def base64(self, file):
        return 'certutil -encode "{}" __base64temp__ & type __base64temp__ & del __base64temp__'.format(file)

    def _base64_to_file(self, base64file, file_decoded, encode=''):
        return 'certutil -{} "{}" "{}"'.format(encode, base64file, file_decoded)

    def base64_encode_to_file(self, file_decoded, base64file):
        return self._base64_to_file(file_decoded, base64file, 'encode')

    def base64_decode_to_file(self, base64file, file_decoded):
        return self._base64_to_file(base64file, file_decoded, 'decode')

    def md5checksum(self, file):
        return 'certutil -hashfile "{}" MD5'.format(file)

    def remove(self, file_path, force=True):
        flags = '-f' if force else ''
        return "del {flags} {file_path}".format(flags=flags, file_path=file_path)

    def move(self, current_file_path, new_file_path, overwrite=True):
        cmd = 'move '
        if overwrite:
            cmd += '/Y '
        return cmd + "{} {}".format(current_file_path, new_file_path)


Instance = None


def get_instance():
    global Instance
    if Instance is None:
        Instance = Win32ShellCmds()
    return Instance
