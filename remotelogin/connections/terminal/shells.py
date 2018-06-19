from .. import settings

__author__ = 'Filinto Duran (duranto@gmail.com)'


class ShellLoginInformation:
    """ utility class for multilevel logins

    """
    # TODO: if arguments are added function pass_args should be changed to reflect it
    def __init__(self,
                 connect_timeout=0,
                 timeout_for_prompt=0,
                 timeout=0,
                 number_of_lines_for_prompt=1,
                 expected_prompt=None,
                 can_change_prompt=False,
                 banner_message='',
                 cols=0,
                 rows=0,
                 new_line='\n',
                 skip_prompt_check=False,
                 ask_response_list=None,
                 root_pwd='/',
                 disable_history=None):
        """
        :param str password_regex_expected: regex or str to expect to receive as question from server
        :param str confirmation_message_expect: in case of ssh if the server we are connecting we have never connected to we would need to know what to expect (this can be str or regex)
        :param bool username_requested: flag to indicate weather we need to enter the username or we can just use username@x.y.z.a for ssh or telnet not expecting any username
        :param str username_word_expect: str or regex to expect in case we need to enter username specially for telnet
        :param float login_timeout: seconds to wait for login to complete
        :param int number_of_lines_for_prompt: number of lines as part of the prompt
        :param str expected_prompt: if given this will be what the login will wait for instead of the timeout. If prompt is not found before the login timeout it will raise an exception
        :param str file_transfer_method: any of: ascii, sftp, scp. To know if we can execute this commands
        """
        import fdutils
        if fdutils.regex.is_instance_of_regex(expected_prompt):
            number_of_lines_for_prompt = len(expected_prompt.pattern.splitlines())
        else:
            number_of_lines_for_prompt = len(expected_prompt.splitlines()) if expected_prompt else number_of_lines_for_prompt
        self.connect_timeout = connect_timeout or settings.SOCKET_TIMEOUT_FOR_LOGIN
        self.timeout_for_prompt = timeout_for_prompt or settings.TIMEOUT_FOR_PROMPT
        self.number_of_lines_for_prompt = number_of_lines_for_prompt
        self.new_line = new_line
        self.banner = banner_message
        self.expected_prompt = expected_prompt
        self.prompt_found = expected_prompt
        self.can_change_prompt = can_change_prompt
        self.cols = cols or settings.SHELL_COLS
        self.rows = rows or settings.SHELL_ROWS
        self.timeout = timeout or settings.SOCKET_TIMEOUT
        self.sudo_list = list()
        self.skip_prompt_check = skip_prompt_check
        self.ask_response_list = ask_response_list or []
        self.pwd = root_pwd
        self.disable_history = disable_history if disable_history is not None else settings.DISABLE_HISTORY_RECORDING

    def update_from_conn(self, conn):
        update = 'timeout', 'connect_timeout', 'expected_prompt', 'can_change_prompt', 'timeout_for_prompt'
        for attr in [a for a in update if hasattr(conn, a)]:
            setattr(self, attr, getattr(conn, attr))

    def update(self, **properties):
        self.__dict__.update(properties)

