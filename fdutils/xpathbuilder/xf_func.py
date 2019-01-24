import functools

from .string_lower import (translate_lower, get_modifier, value_contains, value_startswith,
                           value_endswith, value_strip)

# TODO: check if we can refactor the string manipulation with property call section
def _xf(f_name, node, *values, **kwargs):
    """ (x)path (f)unction object to function conversion

    Args:
        f_name:
        node_string:
        value:
        insensitive:
        negate:

    Returns:

    """
    args_format = kwargs.pop('args_format', None) # args_format should include a {node} and a {values} attributes
    compare_to_node = kwargs.pop('compare_to_node', None)
    compare_to_value = kwargs.pop('compare_to_value', None)
    node_string = kwargs.pop('node_string', str(node))
    values = list(values)

    new_value, insensitive, negate, starts, contains, endswith, strip = get_modifier(*values, **kwargs)

    if new_value:
        values[0] = new_value

    if strip:
        node_string = value_strip(node_string)

    if insensitive:
        # make mutable
        values = [str(v).lower() for v in values]
        node_string = translate_lower(node_string)

    for i, v in enumerate(values):
        from .node import Node
        if isinstance(v, Node):
            values[i] = str(v)
        else:
            values[i] = '"' + v + '"'

    if starts and not f_name.startswith('start'):
        values[0] = value_startswith(node_string, values[0])
    elif contains and not f_name.startswith('contains'):
        values[0] = value_contains(node_string, values[0])
    elif endswith and not f_name.startswith('ends'):
        values[0] = value_endswith(node_string, values[0])

    if args_format:
        func_string = args_format.format(f_name=f_name, values=values, node=node_string)
    else:
        values = [node_string] + values
        func_string = '{}({})'.format(f_name, ', '.join(values))

    if not starts and not contains and not endswith:
        if compare_to_node:
            func_string = node_string + '=' + func_string
        elif compare_to_value:
            func_string = values[0] + '=' + func_string

    if negate:
        func_string = 'not(' + func_string + ')'

    return func_string


def xf_deco(**deco_kwargs):
    func_name = deco_kwargs.get('func_name', '')

    def f(func):
        functools.wraps(func)
        def w(self, *args, **kwargs):
            kwargs.update(deco_kwargs)
            return self._xf(func_name or func.__name__.replace('_', '-'), *args, **kwargs)
        return w
    return f


def get_rendered_node(node):
    """ tries to reduce the string to convert all nodes (//*) to // when needed

    Args:
        node:

    Returns:

    """
    r = node.render()

    if len(r) >= 3 and r[-3:] == '//*':
        return r[:-3] + "//"

    elif len(r) >= 2 and r[-2:] == '//':
        return r[:-2] + "//"

    else:
        return r.rstrip('/') + '/'


class LogicOperatorMixin:
    def _logical_join(self, other, logic, before=False):

        from .node import Node
        new_node = Node()

        if before:
            new_node.clauses.append(logic)

        new_node.clauses.append("(" + self.render() + ")")

        if not before:
            new_node.clauses.append(logic)

        new_node.clauses.append("(" + other.render() + ")")

        return new_node

    def __and__(self, other):
        return self._logical_join(other, 'and')

    def __or__(self, other):
        return self._logical_join(other, 'or')

    def __invert__(self):
        new_node = self.copy()
        new_node._inverted = not new_node._inverted
        return new_node
