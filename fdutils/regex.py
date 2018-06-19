import re

RE_TYPE = re.compile('').__class__


def is_instance_of_regex(o):
    return isinstance(o, RE_TYPE)


def to_regex(r, flags=0):
    """ converts string to compiled regex if it is not already a regex object """
    if not is_instance_of_regex(r):
        return re.compile(r, flags=flags)
    else:
        return r


def regex_flag_to_repr(flags):
    """ converts regex flags to a __repr__ style string """
    ret = []
    for re_name, re_flag in {'re.IGNORECASE': re.IGNORECASE,
                             're.MULTILINE': re.MULTILINE,
                             're.DOTALL': re.DOTALL}.items():
        if flags & re_flag:
            ret.append(re_name)

    return '|'.join(ret)


def create_terminal_invisible_strip_regex(as_bytes=False, encoding='utf-8', errors='ignore'):
    """ used to remove invisible characters (colors, esc, etc.) in terminal connections """
    # http://vt100.net/docs/vt100-ug/chapter3.html
    # http://umich.edu/~archive/apple2/misc/programmers/vt100.codes.txt
    # http://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h2-Functions-using-CSI-_-ordered-by-the-final-character_s_
    CSI = chr(27) + r'\['
    VT100 = CSI + r'([\?\>]?\d+(;\d+)*)?' + r'[\@A-Za-z]'
    KEYPAD = CSI + r'=\d+h'
    BELL = chr(7)
    R = r'\r'
    strip = [VT100, KEYPAD, BELL, R]

    if not as_bytes:
        ansi = '({})'.format('|'.join(strip))
    else:
        ansi = b'(' + b'|'.join(s.encode(encoding=encoding, errors=errors) for s in strip) + b')'
    return re.compile(ansi)


ANSI_FILTER_REGEX = None
ANSI_FILTER_REGEX_BYTES = None


def strip_ansi_codes_from_buffer(buffer):
    global ANSI_FILTER_REGEX
    if ANSI_FILTER_REGEX is None:
        ANSI_FILTER_REGEX = create_terminal_invisible_strip_regex()

    # while '\x08' in buffer:
    #     m = re.search(r'\x08+', buffer, flags=re.M)
    #     if m:
    #         buffer = buffer[:m.regs[0][0] * 2 - m.regs[0][1]]+buffer[m.regs[0][1]:]
    #     else:
    #         break

    return ANSI_FILTER_REGEX.sub('', buffer)


def strip_ansi_codes_from_buffer_bytes(buffer, encoding='utf-8', error='ignore'):
    global ANSI_FILTER_REGEX_BYTES
    if ANSI_FILTER_REGEX_BYTES is None:
        ANSI_FILTER_REGEX_BYTES = create_terminal_invisible_strip_regex(True, encoding=encoding, errors=error)

    return ANSI_FILTER_REGEX_BYTES.sub(b'', buffer)
