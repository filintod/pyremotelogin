lowercase = 'abcdefghijklmnopqrstuvwxyzàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿžšœ'
uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸŽŠŒ'


def translate_lower(node_string):
    return 'translate({}, "{}", "{}")'.format(node_string, uppercase, lowercase)


def _get_value_quoted(value):
    if not value.startswith('"'):
        value = '"' + value
    if not value.endswith('"'):
        value += '"'
    return value


def value_strip(node_string):
    return 'normalize-space({})'.format(node_string)


def value_contains(node_string, value):
    return 'contains({}, {})'.format(node_string, _get_value_quoted(value))


def value_startswith(node_string, value):
    return 'starts-with({}, {})'.format(node_string, _get_value_quoted(value))


def value_endswith(node_string, value):
    return 'substring({node}, string-length({node}) - string-length({value}) + 1)={value}' \
           ''.format(node=node_string, value=_get_value_quoted(value))


# TODO: finish ends and contains sections or remove


def get_modifier(*value, **kwargs):

    negate = kwargs.get('negate', False)
    insensitive = kwargs.get('insensitive', False)
    rawstring = kwargs.pop('rawstring', False)

    starts = contains = endswith = strip = False

    if value:
        value = str(value[0])

        value = value.lstrip()

        if not rawstring:
            if value.startswith('(?i)'):
                insensitive = True
                value = value[4:]

            control_cmds = '!~^*$&#'
            first_char = value[0]

            if first_char == '\\' and len(value)>1 and value[1] in control_cmds:
                # escaping
                value = value[1:]

            while first_char in control_cmds:

                if first_char in '!~':
                    negate = True
                elif first_char == '^':
                    starts = True
                elif first_char == '*':
                    contains = True
                elif first_char == '$':
                    endswith = True
                elif first_char == '&':
                    insensitive = True
                elif first_char == '#':
                    strip = True

                if starts or contains or endswith or insensitive or negate or strip:
                    value = value[1:]

                first_char = value[0]

            if starts and endswith:  # if we want it to start and to ends with it set it to equal comparison
                starts = endswith = contains = False

    return value, insensitive, negate, starts, contains, endswith, strip
