import logging
import re

from .results import ExpectResults
from .. import exceptions
from .value import ExpectedRegex

log = logging.getLogger(__name__)
__author__ = 'Filinto Duran (duranto@gmail.com)'

""" Usage:

    terminal.send("dir").expect(r"home", flags=re.I)
    terminal.send("dir").expect_string(r"home")
    terminal.send("dir").expect_istring(r"home")
    terminal.send("dir").expect_any(<ExpectAny object>)
    terminal.send("dir").expect_all(<ExpectAny object>)
    match = terminal.send("dir").expect_all_in_sequence(<ExpectAny object>)

    if match.found:
        value = match.value     # same as match.get_value_of(0)
        values = match.values
        re_object = match.re_match_object
        re_objects = match.re_match_objects

    if match.matched_all:
        pass

    if match.matched_all_in_sequence:
        pass

    terminal.send("dir").expect_prompt()
    terminal.send("dir")

    # future fsm option
    expect_any = ExpectAny()
    f = expect_any.add("first", regex=r"home", flags=0)
    expect_any.del("first")
    s = expect_any.add("second", regex=r"home (sweet) home", flags=0)
    expect_any.update_transition_map({
        'initial': 'green',
        'events': [
            {'name': 'warn', 'src': 'green', 'dst': 'yellow'},
            {'name': 'panic', 'src': 'yellow', 'dst': 'red'},
            {'name': 'calm', 'src': 'red', 'dst': 'yellow'},
            {'name': 'clear', 'src': 'yellow', 'dst': 'green'}
        ]
    })
"""


# TODO: add a finite state machine (like fysom or something simpler)
class Expect:
    """ Container object for information about the execution of expect commands. One command could expect different outputs

    """
    def __init__(self, cmd='', expected_regex_list=None, timeout=0, all_matches_required=False,
                 continue_matching=False, all_matches_in_sequence=False, fsm=None):
        """

        Args:
            cmd (str): command to execute (to be filtered)
            expected_regex_list (list of ExpectedRegex): list of expected regex objects
            timeout (float): how long to wait to find the match
            all_matches_required (bool): weather we want all the expected matches to be found and not return from the
                                         expect until timeout or we found all the matches
            continue_matching (bool): is we want to check for all the matches even if we found a match earlier but
                                      we don't required all to be matched to allow the expect to break
            all_matches_in_sequence (bool): weather the matches should match the sequence given in the list of matches

        Returns:

        """
        # ####################          Args        ###########################
        self.cmd = str(cmd)
        self.expect_values = expected_regex_list or []
        self.all_matches_required = all_matches_required
        self.continue_matching = continue_matching
        self.matches_should_be_in_sequence = all_matches_in_sequence
        self.timeout = timeout
        # ######################################################################

        # check we were not given two expected values with the same name (note: we do allow repeated empty)
        self.__check_expect_list_conflict()

        # flag: we got one match
        self.any_matched = False

        # flag: all expects in the list were matched
        self.all_matched = False

        # flag: all matches were in sequence (needed when matches_should_be_in_sequence is set)
        self.all_matched_in_sequence = False

        # flag: indicate we got matches that satisfies all our conditions (all
        self.ok = False

        # keeps track of internal information
        self._matched_index_list = []
        self._match_name_to_index = {}
        self.__check_expect_list_conflict()

    def __str__(self):
        return 'Command: ' + self.cmd + ' | Expected Values: ' + ' | '.join([str(s) for s in self.expect_values])

    def __check_expect_list_conflict(self):
        """ check that list of commands do not contain duplicate names

        :param list of CmdExpectRegexList expected_value_list: list of commands to check

        """
        names_found = set()
        for index, exp in self.expect_values:
            if exp.name:
                if exp.name in names_found:
                    raise exceptions.ExpectListNameConflict
                names_found.add(exp.name)
                self._match_name_to_index[exp.name] = index
        return True

    # TODO: finish state machine
    def add_fms_map(self):
        """ adds a finite state machine definition per fysom format (check library)

        Returns:

        """
        raise NotImplementedError

    def results(self):
        return ExpectResults(self)

    ##############################################################################################
    # the following are helpers to handle results instead of writing a facade to results
    # @property
    # def value(self):
    #     return self[self.index].value
    # matched_value = value
    #
    # @property
    # def matched_values(self):
    #     return {index: self[index].value for index in self._matched_index_list}
    # values = matched_values
    #
    # @property
    # def string_before_matches(self):
    #     return {index: self[index].string_before_match for index in self._matched_index_list}
    # strings_before = string_before_matches
    #
    # @property
    # def string_before_match(self):
    #     return self[self.index].string_before_match
    # string_before = string_before_match
    #
    # @property
    # def matched_object(self):
    #     return self[self.index].match_object
    #
    # @property
    # def matched_name(self):
    #     return self[self.index].name
    #
    # @property
    # def matched_index(self):
    #     return self._matched_index_list[0]

    def __getitem__(self, item):
        try:
            int(item)
            return self.expect_values[item]
        except ValueError:
            return self.expect_values[self._match_name_to_index[item]]

    def get(self, item):
        return self[item]

    def delete(self, item):
        """ removes an element from the expected value elements

        Args:
            item:

        Returns:

        """
        try:
            item_to_delete = int(item)
            is_dict = False
        except ValueError:
            item_to_delete = self._match_name_to_index[item]
            is_dict = True

        del self.expect_values[item_to_delete]
        if is_dict:
            del self._match_name_to_index[item]
        # update _match_name_to_index
        for k in [k for (k,v) in self._match_name_to_index.items() if v >= item_to_delete]:
            self._match_name_to_index[k] -= 1

    def add(self, exp_reg_value_obj):
        """ adds an expected value object to the list

        Args:
            exp_reg_value_obj:

        Returns:

        """
        if exp_reg_value_obj.name:
            if exp_reg_value_obj.name in self._match_name_to_index:
                raise exceptions.ExpectListNameConflict
            else:
                self._match_name_to_index[exp_reg_value_obj.name] = len(self.expect_values)
        self.expect_values.append(exp_reg_value_obj)
        return self

    def add_regex(self, regex, flags=0, name='', remove_prompt_to_compare=True):
        return self.add(ExpectedRegex(regex=regex, flags=flags, name=name,
                                      remove_prompt_to_compare=remove_prompt_to_compare))

    def add_string(self, string, **kwargs):
        return self.add_regex(re.escape(string), **kwargs)

    def add_istring(self, string, **kwargs):
        kwargs.setdefault('flags', 0)
        kwargs['flags'] |= re.I
        return self.add_regex(re.escape(string), **kwargs)

    def add_prompt(self, **kwargs):
        return self.add_regex(None, **kwargs)

    def reset(self):
        # reset the expected value object in case we are reusing it
        for ev in self.expect_values:
            ev.reset()

        self.any_matched = self.all_matched = self.all_matched_in_sequence = self.ok = False
        self._matched_index_list = []

    def get_matched_objects_list(self):
        """ return a list of regex objects that have matched/or not the different expected values     """
        return [value.match_object for value in self.expect_values]

    # FIXME: multiple matches same value with re.finditer
    def find_expected_values_and_prompt_in_buffer(self, buff, prompt):
        """ Cycles through all the ExpectValues and check if the given value matches one of the expected values.
            Also the expected commands would contain the matched object for later retrieval

        :param str buff: buffer received via socket so far
        :param str prompt: the user prompt to remove if needed (default behavior)
        :rtype: bool

        """
        prompt_found_at_end = re.search(prompt + "\s*$", buff, re.MULTILINE)

        self.all_matched = False
        for expect_index, expect_value in enumerate(self.expect_values):

            if expect_value.regex_object:

                if expect_value.remove_prompt_to_compare and prompt_found_at_end:
                    buff_no_prompt = buff[:prompt_found_at_end.start()]

                else:
                    buff_no_prompt = buff

                expect_value.search(buff_no_prompt)

            else:
                # we are searching for the prompt if the regex_object is empty or None
                expect_value.match_object = prompt_found_at_end

            if expect_value.match_object:

                log.debug("Found match for: " + str(expect_value))
                self.any_matched = True

                # continue next match values or return on first match

                self._matched_index_list.append(expect_index)  # to implement all_matches_in_sequence

                if not (self.all_matches_required or self.continue_matching):
                    break

        self.all_matched = all([expect_value.match_object is not None for expect_value in self.expect_values])

        if not self.all_matches_required:
            self.ok = self.any_matched
        elif not self.matches_should_be_in_sequence:
            self.ok = self.all_matched
        else:
            if self.all_matched:
                self.all_matched_in_sequence = (range(len(self.expect_values)) ==
                                                     self._matched_index_list[len(self._matched_index_list) -
                                                                              len(self.expect_values):])

            self.ok = self.all_matched_in_sequence
        return self.ok


EXPECT_PROMPT = ExpectedRegex(name='prompt')