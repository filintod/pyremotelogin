import abc
import re


RANDOM_PROMPT_LENGTH = 8


class OSCommands:
    """ base class for OS commands that return strings
    """
    __metaclass__ = abc.ABCMeta

    CAT = ''
    HAS_BASE64 = False

    def set_prompt(self, prompt):
        """sets the prompt in the os"""
        return ''

    @abc.abstractmethod
    def cat_to_file(self, file_path, message):
        """ append message to file """

    def cat(self, file_path):
        return self.CAT + ' ' + file_path

    def resize_pty(self, cols, rows):
        return "stty cols {} rows {}".format(cols, rows)

    def exit(self):
        return "exit"

    @abc.abstractmethod
    def remove(self, file_path):
        """ removes file """

    @abc.abstractclassmethod
    def list_file(self, file_path):
        """ list a file with last modified time and size """

    def cd(self, new_folder):
        return "cd {}".format(new_folder)

    def disable_history(self):
        pass

    def enable_history(self):
        pass


def set_locals(klass, locs, OS_KWARGS_TYPES):
    for l in [l for l in locs if not hasattr(klass, l)]:
        if l in OS_KWARGS_TYPES and locs[l] is None:
        setattr(klass, l, locs[l])


class OSBase:
    """

    """
    cmd = None
    shell_cmds_module = None
    name = 'base'
    expected_prompt = None

    # for connection local and tunnels
    shell_app = None    # used on local connections
    ssh_app = None
    telnet_app = None

    # use when reset_prompt_on_exit is True to reset the prompt to its default
    default_prompt = None
    # if the os allows to set the prompt but the prompt change is permanent we want to put it back to what it was
    reset_prompt_on_exit = False

    unique_prompt_format = '@@{random}@PWN@# '
    unique_prompt_re = re.escape(unique_prompt_format).replace(re.escape('{random}'), r'\S+')

    can_resize_pty = True
    can_change_prompt = False
    can_disable_history = False

    @classmethod
    def pop_os_properties_from_kwargs(cls, **kwargs):
        os_props = {}
        for k in cls.OS_KWARGS:
            if k in kwargs:
                os_props[k] = kwargs.pop(k)
        return os_props, kwargs

    OS_KWARGS = 'can_resize_pty', 'can_change_prompt', 'can_disable_history', 'reset_prompt_on_exit', 'default_prompt'
    OS_KWARGS_TYPES = dict(can_resize_pty=bool, can_change_promp=bool, can_disable_history=bool,
                           reset_prompt_on_exit=bool)

    # NOTE: if we change/add kwargs we need to synchronize arguments in DeviceBase.init_os method
    def __init__(self, can_change_prompt=None, can_resize_pty=None, reset_prompt_on_exit=None, default_prompt=None,
                 can_disable_history=None, shell_app=None, telnet_app=None, ssh_app=None):
        # this should be the first method to be called DON"T MOVE or we might have other locals
        set_locals(self, locals(), OSBase.OS_KWARGS_TYPES)

        if reset_prompt_on_exit and not default_prompt:
            raise AttributeError('If the OS will do reset_prompt_on_exit you need to define the default_prompt')

        if not self.cmd and not self.shell_cmds_module:
            self.cmd = OSCommands()

        elif not self.cmd:
            self.cmd = self.shell_cmds_module.get_instance()

    def base64_clean(self, data):
        return data

    def get_unique_prompt(self):
        import random
        import string

        random_string = [string.ascii_lowercase[int(random.random() * len(string.ascii_lowercase))]
                         for _ in range(RANDOM_PROMPT_LENGTH)]
        return self.unique_prompt_format.format(random=''.join(random_string))

    def serialize(self):
        return dict(name=self.name,
                    kwargs=dict(can_change_prompt=self.can_change_prompt, can_resize_pty=self.can_resize_pty,
                                reset_prompt_on_exit=self.reset_prompt_on_exit, default_prompt=self.default_prompt,
                                can_disable_history=self.can_disable_history, shell_app=self.shell_app,
                                telnet_app=self.telnet_app, ssh_app=self.ssh_app))
