import functools

from .axes import WithAxes
from .nodeset import NodeSetFunctions
from .xf_func import _xf, LogicOperatorMixin
from .property import Property

PROP_METHODS = sorted([m for m in dir(Property)
                                        if not m.startswith('_') and m not in Property.NON_ALLOWED_PROP_PREFIX],
                                       key=lambda s: len(s), reverse=True)

AXES_METHODS = sorted([m for m in dir(WithAxes)
                                        if not m.startswith('_') and m not in WithAxes.NON_ALLOWED_AX_PREFIX],
                                       key=lambda s: len(s), reverse=True)


def _check_item_against(item, against, strict):
    for method in against:
        if not strict and item.startswith(method) or strict and item == method:
            return method
    return ''


def _check_properties_against_item(item, strict=True):
    return _check_item_against(item, PROP_METHODS, strict)


def _check_axes_against_item(item, strict=False):
    return _check_item_against(item, AXES_METHODS, strict)


# TODO: make into str class to be able to pass to lxml.xpath method without casting
class Node(WithAxes, NodeSetFunctions, LogicOperatorMixin, str):

    AXES_METHODS = []

    def __new__(cls, node='.', version=1, ns='', inverted=False):
        if ns and node[0] != '.':
            slash, value = node.rsplit('/', maxsplit=1)
            if value and not ':' in value:
                node = slash + '/' + ns + ':' + value
        self = super().__new__(cls)
        self._node = node
        self._ns = ns
        self.version = version
        self.clauses = []
        self._inverted = inverted
        return self

    def len(self):
        return len(self.render())

    # change str methods/attributes to node methods
    for method in (m for m in dir(str) if not m.startswith('_') and
            not m in dir(NodeSetFunctions) and
            not m in dir(WithAxes) and not m in dir(LogicOperatorMixin)):
        exec("{method}=property(lambda self: self.node('{method}'))\n".format(method=method))

    def copy(self):
        n = Node(self._node, ns=self._ns, inverted=self._inverted, version=self.version)
        n.clauses = list(self.clauses)
        return n

    __copy__ = copy

    def render(self):
        last_one = -1 if (self.clauses and self.clauses[-1] == 'or') else None
        clause_data = ' '.join(self.clauses[:last_one])
        if clause_data:
            if self._node == '.':
                clause_data = "({})".format(clause_data)
                rendered = clause_data
            else:
                clause_data = "[{}]".format(clause_data)
                rendered = self._node + clause_data
        else:
            rendered = self._node

        if self._inverted:
            rendered = "not(" + rendered + ")"
        return rendered

    def __str__(self):
        return self.render()

    def __unicode__(self):
        return self.render()

    def __or__(self, other):
        if isinstance(other, Node):
            return self.render() + '|' + other.render()
        elif isinstance(other, str):
            return self.render() + '|' + other
        raise TypeError('don\'t know how to join with this other type {}'.format(type(other)))

    def encode(self, *args, **kwargs):
        return str(self).encode(*args, **kwargs)

    def __repr__(self):
        return self.render()

    def __eq__(self, other):
        return self.render() == other.render()

    def _xf(self, name, *args, **kwargs):
        return _xf(name, self, *args, **kwargs)

    def where(self, clause):

        def replace_not_equal(clause):
            for neq in {'!=', '<>'}:
                if neq in clause:
                    return "not({})".format(clause.replace(neq, '='))
            else:
                return clause

        new_node = self.copy()

        if hasattr(clause, 'render'):
            clause = clause.render()
        else:
            clause = replace_not_equal(clause)
            if self.clauses and self.clauses[-1] not in ('or', 'and', 'not'):
                new_node.clauses.append("and")
        new_node.clauses.append(clause)
        return new_node

    def __getattr__(self, item):
        """ makes the following possible:
              .- all_input =>//input
              .- _ => .
              .- all_ => //*
              .- _id => @id
              .- not_ => not(.)
              .- not_id => not(@id)
              .- or_ => or(.)
              .- or_id => or @id
        """
        def add_or_and_clause(name):
            method = getattr(self, item[len(name):])
            if self.clauses and not self.clauses[-1] == name:
                self.clauses.append(name)
            return method

        if item.startswith('_'):
            item = item[1:]

            if item == '':
                return Property(".", self)

            elif item in ('text', 't'):
                return Property("text()", self)

            elif _check_axes_against_item(item):
                method = _check_axes_against_item(item)
                return getattr(Node(ns=self._ns), method)(item[len(method) + 1:])

            elif _check_properties_against_item(item):
                method = _check_properties_against_item(item)
                return getattr(Property('.', self), method)

            else:
                return Property("@" + item, self)

        elif item.startswith('not_'):
            return functools.partial(getattr(self, item[3:]), negate=True)

        elif item.startswith('or_'):
            return add_or_and_clause('or')

        elif item.startswith('and_'):
            return add_or_and_clause('and')

        elif _check_axes_against_item(item):
            method = _check_axes_against_item(item)
            item = item[len(method) + 1:]
            return getattr(self, method)(item)

        if isinstance(self, Node) and self == Node():
            return Node(item, ns=self._ns)
        else:
            return self.node(item)

    def __getitem__(self, item):
        return Node(self.render() + "[{}]".format(item), ns=self._ns)

    def __call__(self, *args, **kwargs):
        if not args and not kwargs:
            return self

        if kwargs:
            items = self
            for k,v in kwargs.items():
                items = items._[k](v)
            return items
        else:
            return self.copy()._(args[0])

