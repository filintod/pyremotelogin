from fdutils.decorators import lazy_property


class ExpectResults:
    """ container to duplicate expect result values to not lose it and make it easier to call """

    def __init__(self, e):
        self.ok = e.ok
        self.any_matched = e.any_matched
        self.all_matched = e.all_matched
        self.all_matched_in_sequence = e.all_matched_in_sequence

        self._mil = list(e._matched_index_list)
        self.multiple = len(self._mil) > 1

        if self.any_matched:
            self._strs_before = {index: e.expect_values[index].string_before_match for index in self._mil}
            self._values = {index: e.expect_values[index].value for index in self._mil}
            self._names = {index: e.expect_values[index].name for index in self._mil}
        else:
            self.multiple = self._mil = None

    @lazy_property
    def value(self):
        if self.multiple:
            raise ValueError('The result has more than one result')
        return self._values[self._mil[0]]

    @lazy_property
    def string_before(self):
        if self.multiple:
            raise ValueError('The result has more than one result')
        return self._strs_before[self._mil[0]]

    def values(self):
        return self._values

    def strings_before(self):
        return self._strs_before

    @lazy_property
    def index(self):
        if self.multiple:
            raise ValueError('The result has more than one result')
        return self._mil[0]

    def indexes(self):
        return self._mil

    @lazy_property
    def name(self):
        if self.multiple:
            raise ValueError('The result has more than one result')
        return self._names[self._mil[0]]

    def names(self):
        return self._names

# class ExpectResultsOld:
#     """ Container to manage the results given from an execute expect list
#
#     """
#
#     def __init__(self, cmd, ):
#         self.cmd_line = []
#         self.expect_cmd = []
#         """:type: list of ExpectCmdMultiple"""
#
#     def __str__(self):
#         # TODO: better define the string to return
#         return self.get_execution_string()
#
#     def get_execution_string(self):
#         return ''.join(self.cmd_line)
#
#     def get_cmd_match(self, index, value_name=''):
#         """ get regex match for the command defined by the index
#
#         :param index: the array index from 0 to len(array)-1. It could also be negative
#         :param str value_name: if given tries to return the matched RegexObj for the ExpectValue whose name is value-name
#         :rtype: RegexObj or List of RegexObj
#
#         """
#         if abs(index) >= len(self.expect_cmd):
#             raise IndexError
#
#         if not value_name:
#             return self.expect_cmd[index].get_match_values()
#         return self.expect_cmd[index].get_match_by_name(value_name)
#
#     def get_last_match(self, value_name=''):
#         return self.get_cmd_match(-1, value_name)
#
#     def __iter__(self):
#         for i in self.cmd_line:
#             yield self.cmd_line[i], self.expect_cmd[i]
#
#     def get_cmd_match_by_name(self, name):
#         """ get regex match for the command defined by the name if there is a command with this name
#
#         """
#
#     def append(self, cmd_line, expect_cmd):
#         """ append the command line string that resulted from executing the expect command, it also appends the command
#
#         :param str cmd_line: string tha resulted from executing expect_cmd
#         :param CmdExpectRegexList expect_cmd: expect command executed
#
#         """
#         self.cmd_line.append(cmd_line)
#         self.expect_cmd.append(expect_cmd)