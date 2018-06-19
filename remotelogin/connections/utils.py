import fdutils
from remotelogin.connections import settings


def set_expected_prompt_with_username(kwargs, username):
    kwargs.setdefault('expected_prompt', r'\[{username}@.+?\s~\]\$ ')
    if kwargs['expected_prompt'] and fdutils.strings.is_fieldname_in_formatted_string(kwargs['expected_prompt'], 'username'):
        kwargs['expected_prompt'] = kwargs['expected_prompt'].format(username=username)


def to_bytes(s):
    if isinstance(s, bytes):
        return s
    try:
        return s.encode(encoding=settings.ENCODE_ENCODING_TYPE, errors=settings.ENCODE_ERROR_ARGUMENT_VALUE)
    except (TypeError, AttributeError):
        return s


def to_str(b):
    if isinstance(b, str):
        return b
    try:
        return b.decode(encoding=settings.ENCODE_ENCODING_TYPE, errors=settings.ENCODE_ERROR_ARGUMENT_VALUE)
    except (TypeError, AttributeError):
        return b