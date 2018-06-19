import collections
import logging
import os
import re
import fdutils

log = logging.getLogger(__name__)


# variable compile regular expression to find double curly brace variables
variable_re = re.compile(r'{{\s*(?P<name>[^\s}]+)\s*}}')


# system variables to substitute in settings file
system_variables = {'__USER_HOME__': os.path.expanduser('~'),
                    '__PWD__': os.getcwd()}


def _resolve_variables(variables):
    """ resolves variables that might depend on other variables """

    resolved = []
    variables = {k: dict(value=v) for (k,v) in variables.items()}

    for v in (v for v in variables):
        found = variable_re.findall(variables[v]['value'])
        if not found:
            resolved.append(v)
        elif any(f not in variables for f in found if f not in system_variables):
            raise ValueError('There might be a typo as there is one or more variable names ({}) that cannot be found'
                             ''.format(found))
        else:
            variables[v]['depends_on'] = set(found)

    def get_value_match(m):
        variable_name = m.group('name')
        if variable_name in system_variables:
            return system_variables[variable_name]
        else:
            return variables[variable_name]['value']

    while len(resolved) != len(variables):
        for v in (v for v in variables if v not in resolved):
            dependent_resolved = [k for k in variables[v]['depends_on'] if k in resolved or k in system_variables]
            for d in dependent_resolved:
                variables[v]['value'] = variable_re.sub(get_value_match, variables[v]['value'])

                variables[v]['depends_on'].remove(d)
            if not variables[v]['depends_on']:
                resolved.append(v)

    return {k: variables[k]['value'] for k in variables}


def _replace_variable(value, variables):
    if isinstance(value, str):
        variables_names = [v.replace(' ', '') for v in variable_re.findall(value)]

        if not variables_names:
            return value

        if not any(v in variables or v in system_variables for v in variables_names):
            log.warning('Settings File problems:\n\n'
                        'We found some possible variable names ({}) but none of the variables defined is one of '
                        'them we will not do any replacement'.format(variables_names))
            return value

        def get_value_match(m):
            variable_name = m.group('name')
            return system_variables[variable_name] if variable_name in system_variables else variables[variable_name]
        value = variable_re.sub(get_value_match, value)

    return value


def _replace_variables_in_settings(settings, variables):
    if variables:
        for k,v in ((k,v) for (k,v) in settings.items() if v):
            if isinstance(v, collections.MutableMapping):
                _replace_variables_in_settings(v, variables)
            elif fdutils.lists.is_list_or_tuple(v):
                for i, v_item in enumerate(v):
                    v[i] = _replace_variable(v_item, variables)
            else:
                settings[k] = _replace_variable(v, variables)

    return settings
