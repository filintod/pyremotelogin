import re
import fdutils


class ExpectedRegex:

    def __init__(self, regex=None, flags=0, name='', remove_prompt_to_compare=True, callback=None):
        """ Container to hold information about an expected regex value

        :param regex: value to look for. If the value is empty or None, we then will try to match against the prompt.
                       It is important to know that the last character might be a newline,
                       so if we get a regex searching for a string ending in a character we might not find it as the
                       last character is always a new line so to match against the last character use
                       a regex like /^.*[character]\n?$/
                       Also we are removing the prompt to compare for any case except where the expect value is None
        :type regex: str or RegexObject or None
        :param int re_flags: any of regular expression flags re.I, re.L, re.M, re.S or re.DOTALL
        """

        self.regex_object = regex
        self.callback = callback

        if regex is not None:
            self.regex_object = fdutils.regex.to_regex(regex, flags)

        self.match_object = None
        """:type: MatchObject"""
        self.remove_prompt_to_compare = remove_prompt_to_compare
        self.name = name

    def _exec_regex(self, method, data):
        self.match_object = method(data)
        if self.match_object and self.callback:
            self.callback(self.match_object)
        return self.match_object

    def search(self, data):
        return self._exec_regex(self.regex_object.search, data)

    def match(self, data):
        return self._exec_regex(self.regex_object.match, data)

    def clone(self):
        return ExpectedRegex(self.regex_object, name=self.name, remove_prompt_to_compare=self.remove_prompt_to_compare,
                             callback=self.callback)

    def __repr__(self):
        if self.regex_object:
            regex = self.regex_object.pattern
            flags = fdutils.regex.regex_flag_to_repr(self.regex_object.flags)
        else:
            regex = 'None'
            flags = 0
        return "ExpectedRegex(regex=r'{}', flags={}, name='{}', remove_prompt_to_compare={})".format(
            regex, flags, self.name, self.remove_prompt_to_compare
        )

    def __str__(self):
        matching_for = 'prompt' if self.regex_object is None else self.regex_object.pattern
        name = ' (named: {}) :'.format(self.name) if self.name else ''
        return "Matching for {}{}".format(name, matching_for)

    def reset(self):
        self.match_object = None

    @property
    def value(self):
        if self.match_object:
            m = self.match_object
            return m.string[m.start():m.end()]
        else:
            return None

    @property
    def string_before_match(self):
        if self.match_object:
            m = self.match_object
            return m.string[:m.start()]
        return None

    @property
    def ok(self):
        return self.match_object is not None
    was_matched = ok


class ExpectedString(ExpectedRegex):
    def __init__(self, string, flags=0, name='', remove_prompt_to_compare=True):
        super(ExpectedString, self).__init__(re.escape(string), flags, name, remove_prompt_to_compare)


class ExpectedPrompt(ExpectedRegex):
    def __init__(self, name='', **kwargs):
        super(ExpectedPrompt, self).__init__(None, name=name)
