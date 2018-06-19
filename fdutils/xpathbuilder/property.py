import functools

from .string_lower import (translate_lower, lowercase, uppercase, get_modifier,
                           value_contains, value_startswith, value_endswith, value_strip)
from .xf_func import xf_deco, _xf, LogicOperatorMixin, get_rendered_node


# TODO: implement start, end, contains


class Property(LogicOperatorMixin):
    NON_ALLOWED_PROP_PREFIX = 'render', 'copy'

    def __init__(self, name, node):
        self._name = name
        self._node = node
        self._inverted = False

    def copy(self):
        new_prop = Property(self._name, self._node)
        new_prop._inverted = self._inverted
        new_prop._is_number = self._is_number
        return new_prop

    def _xf(self, name, *args, **kwargs):
        return_property = kwargs.pop('prop', False)
        xf = _xf(name, self._name, *args, **kwargs)

        if not return_property:
            return self._node.where(xf)

        else:
            new_prop = self.copy()
            new_prop._name = xf
            return new_prop

    def __call__(self, *values, **kwargs):

        if values:
            predicate_or = ''
            for value in values:
                new_value, insensitive, negate, starts, contains, endswith, strip = get_modifier(value, **kwargs)
                if new_value:

                    # if starts:
                    #     return self.startswith(value, **kwargs)
                    prop = self._name

                    if strip:
                        prop = value_strip(prop)

                    if insensitive:
                        prop = translate_lower(prop)
                        new_value = new_value.lower()

                    if starts:
                        predicate = value_startswith(prop, new_value)
                    elif contains:
                        predicate = value_contains(prop, new_value)
                    elif endswith:
                        predicate = value_endswith(prop, new_value)
                    else:
                        predicate = '{}="{}"'.format(prop, new_value)

                    if negate:
                        predicate = 'not(' + predicate + ')'

                    if not predicate_or:
                        predicate_or += predicate
                    else:
                        predicate_or += ' or ' + predicate

            if predicate_or:
                return self._node.where(predicate_or)

        return self._name

    def eq(self, value):
        return self.__call__(value)

    def eq_i(self, value):
        return self.__call__(value, insensitive=True)

    def ne(self, value):
        return self.__call__(value, negate=True)

    def ne_i(self, value):
        return self.__call__(value, negate=True, insensitive=True)

    def __getattr__(self, item):
        if item.startswith('not_'):
            return functools.partial(getattr(self, item[4:]), negate=True)

        return getattr(self._node, item)

    # TODO: add the possibility of passing a value to a _xf object
    def __getitem__(self, item):
        if self._name != '.':
            raise AttributeError('This is only allowed on the current property "_"')
        return getattr(self._node, '_' + item)

    def render(self):
        rendered = get_rendered_node(self._node) + self._name
        if self._inverted:
            rendered = "not(" + rendered + ")"
        return rendered

    def __str__(self):
        return self.render()

    # ###########################################################################
    # ###               Comparison Functions
    # ###########################################################################

    def __bf(self, s, other):
        """ boolean comparison """
        return self._node.where(self._name + " " + s + " " + str(other))

    def lt(self, other):
        return self.__bf("<", other)

    def lte(self, other):
        return self.__bf("<=", other)

    def gt(self, other):
        return self.__bf(">", other)

    def gte(self, other):
        return self.__bf(">=", other)

    # ###########################################################################
    # ###               String Functions
    # ###########################################################################

    @xf_deco()
    def starts_with(self, value, **kwargs):
        pass

    startswith = starts_with

    @xf_deco(func_name='starts-with', insensitive=True)
    def starts_with_i(self, value, **kwargs):
        pass
    # synonyms
    istartswith = startswith_i = starts_with_i

    _ends_with_kwargs = dict(func_name='ends-with',
                             args_format='substring({node}, string-length({node}) - string-length({values[0]}) + 1)',
                             compare_to_value=True)

    @xf_deco(**_ends_with_kwargs)
    def ends_with(self, value, **kwargs):
        pass

    endswith = ends_with

    @xf_deco(insensitive=True, **_ends_with_kwargs)
    def ends_with_i(self, value, **kwargs):
        pass
    # synonyms
    iendswith = endswith_i = ends_with_i

    @xf_deco()
    def contains(self, value, **kwargs):
        pass

    @xf_deco(func_name='contains', insensitive=True)
    def contains_i(self, value, **kwargs):
        pass
    icontains = contains_i

    @xf_deco(func_name='contains')
    def has(self, value, **kwargs):
        pass

    @xf_deco(func_name='contains', insensitive=True)
    def has_i(self, value, **kwargs):
        pass

    @xf_deco()
    def substring(self, start, length=None):
        pass

    @xf_deco()
    def substring_after(self, other):
        pass

    @xf_deco()
    def substring_before(self, other):
        pass

    @xf_deco(func_name='string-length')
    def len(self, other):
        pass

    @xf_deco(func_name='normalize-space', prop=True)
    def strip(self):
        pass

    def lower(self):
        return self._xf('translate', uppercase, lowercase, prop=True)

    def upper(self):
        return self._xf('translate', lowercase, uppercase, prop=True)

    @xf_deco(func_name='re:test', rawstring=True)
    def re(self, regex, *flags):
        """ regular expression using EXSLT namespace more at http://lxml.de/2.0/xpathxslt.html

            It can NOT be use in selenium!!!
        """
        pass

    # ###########################################################################
    # ###               Number Functions
    # ###########################################################################

    @xf_deco(func_name='number', prop=True)
    def to_number(self):
        pass

    @xf_deco(func_name='ceiling', prop=True)
    def ceil(self):
        pass

    @xf_deco(prop=True)
    def floor(self):
        pass

    @xf_deco()
    def sum(self, other):
        pass

    @xf_deco(args_format='{values[0]}', func_name='', node_string='text()', compare_to_node=True)
    def text(self, other):
        pass
    t = text
