from .xf_func import get_rendered_node


get_node = lambda n: n or '*'

class WithAxes:

    # from .node import Node
    # class AxisNode(Node):
    #     def __init__(self, ax):
    #
    #
    #     def __call__(self, *args, **kwargs):
    #alll = AxisNode()

    NON_ALLOWED_AX_PREFIX = ['n']

    def __axes(self, axes_string):
        from .node import Node

        return Node(get_rendered_node(self) + axes_string, ns=self._ns)

    @property
    def any(self):
        return self.all('*')

    def all(self, node=''):
        return self.__axes("/" + get_node(node))

    def self(self, node=''):
        return self.__axes("self::" + get_node(node))

    def current(self):
        return self.__axes(".")

    def parent(self):
        return self.__axes("..")

    def text(self):
        return self.__axes("text()")

    def n(self, node):
        return self.__axes(get_node(node))
    # synonyms
    node = n

    def descendants(self, node=''):
        return self.__axes("/" + get_node(node))
    # synonyms
    descendant = descendants

    def children(self, node=''):
        return self.__axes("child::" + get_node(node))
    # synonyms
    child = children

    def descendants_or_self(self, node=''):
        return self.__axes("descendant-or-self::" + get_node(node))
    # synonyms
    descendant_or_self = descendants_or_self

    def ancestors(self, node=''):
        return self.__axes("ancestor::" + get_node(node))
    # synonyms
    ancestor = ancestors

    def ancestors_or_self(self, node=''):
        return self.__axes('ancestor-or-self::' + get_node(node))

    def prev_siblings(self, node=''):
        return self.__axes("preceding-sibling::" + get_node(node))
    # synonyms
    prevs = preceding_sibling = preceding_siblings = p_siblings = p_sibling = p_sib = prev_siblings

    def next_siblings(self, node=''):
        return self.__axes("following-sibling::" + get_node(node))
    # synonyms
    nexts = following_sibling = following_siblings = n_sibling = n_siblings = n_sib = next_siblings

    def prev_nodes(self, node=''):
        return self.__axes("preceding::" + get_node(node))
    # synonyms
    prev = previous = preceding = prev_nodes

    def next_nodes(self, node=''):
        return self.__axes("following::" + get_node(node))
    # synonyms
    following = next = next_nodes
