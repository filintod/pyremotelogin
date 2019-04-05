import re
import string

import functools


def escape_string(s, encoding='utf-8'):
    """ escape unicode characters """
    if not isinstance(s, bytes):
        s = s.encode(encoding=encoding)
    return s.decode('unicode-escape', errors='ignore')


def get_list_of_formatter_names(s, return_index_if_empty=True, parsed_formatter=None):
    l = list()
    parsed_formatter = parsed_formatter or string.Formatter().parse(s)
    for i, k in enumerate([format_element[1] for format_element in parsed_formatter if format_element[1] is not None]):
        if k and k not in l or not k:
            l.append(k or (i if return_index_if_empty else ''))
    return l


def is_string_formatted(s, return_parsed_list=False):
    """ check if a string has formatted characters (with curly braces) """
    l = list(string.Formatter().parse(s))
    if len(l) == 1 and l[0][0] == s:
        is_formatted = False
    else:
        is_formatted = True

    if return_parsed_list:
        return is_formatted, l

    return is_formatted


def is_fieldname_in_formatted_string(s, field_name):
    is_formatted, parsed_format = is_string_formatted(s, True)
    if not is_formatted:
        return False
    else:
        return any([v[1] == field_name for v in parsed_format])


def convert_to_list_of_strings(data):

    ret = []
    import numbers
    if not (isinstance(data, str) or isinstance(data, numbers.Number)):
        for e in data:
            ret.append(str(e))
    else:
        ret = [str(data)]
    return ret


def split_on_uppercase(s, keep_contiguous=False):
    """
    >>> split_on_uppercase('theLongWindingRoad')
    ['the', 'Long', 'Winding', 'Road']
    >>> split_on_uppercase('TheLongWindingRoad')
    ['The', 'Long', 'Winding', 'Road']
    >>> split_on_uppercase('TheLongWINDINGRoadT', True)
    ['The', 'Long', 'WINDING', 'Road', 'T']
    >>> split_on_uppercase('ABC')
    ['A', 'B', 'C']
    >>> split_on_uppercase('ABCD', True)
    ['ABCD']
    >>> split_on_uppercase('')
    ['']

    Args:
        s: string
        keep_contiguous bool: flag to indicate we want to keep contiguous uppercase chars together

    Returns:

    """

    string_length = len(s)
    is_lower_around = (lambda: s[i-1].islower() or
                       string_length > (i + 1) and s[i + 1].islower())

    start = 0
    parts = []
    for i in range(1, string_length):
        if s[i].isupper() and (not keep_contiguous or is_lower_around()):
            parts.append(s[start: i])
            start = i
    parts.append(s[start:])

    return parts


def split_on_title_case_return_string(s):
    return ' '.join(split_on_uppercase(s, True))


def split_on_underscore_return_title_case(s):
    l = list()
    for p in s.split('_'):
        l.append(p[0].upper() + (p[1:] if len(p) > 1 else ''))
    return l


def split_method_or_class_name_return_title_string(s):
    return ' '.join([split_on_title_case_return_string(s) for s in split_on_underscore_return_title_case(s)])


def camel_case_to_python(s):
    parts = split_on_uppercase(s, True)
    return '_'.join(parts)


def cast(value, *types):
    for t in types:
        try:
            return t(value)
        except Exception:
            pass


@functools.lru_cache()
def get_text_fsm(textfsm_template_file):
    import textfsm
    with open(textfsm_template_file) as f:
        return textfsm.TextFSM(f)


def parse_textfsm(textfsm_template_file, text, eof=True):
    tfsm = get_text_fsm(textfsm_template_file)
    r = tfsm.ParseText(text, eof)
    return [dict(zip(tfsm.header, l)) for l in r]


def parse_textfsm_single(textfsm_template_file, text, eof=True):
    tfsm = get_text_fsm(textfsm_template_file)
    r = tfsm.ParseText(text, eof)
    if len(r) > 1:
        raise TypeError('The parsed result contains more than one record')
    elif not r:
        raise ValueError('We did not get any parsed data')
    else:
        return dict(zip(tfsm.header, r[0]))


def get_string_index_info(s):
    """ gets information from strings of the format title_index where index is a number """
    file_idx_re = re.compile(r'^(?P<name>.+?)_(?P<idx>\d+)$')
    m = file_idx_re.match(s)
    idx = None
    underscore = '_'
    if m:
        s = m.group('name')
        idx = int(m.group('idx'))
    else:
        if s.endswith('_'):
            underscore = ''

    return s, underscore, idx
