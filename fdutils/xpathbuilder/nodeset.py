from .property import Property


class NodeSetFunctions:
    @property
    def node_name(self):
        p = self._xf('local-name')
        return Property(p, self)

    @property
    def node_name_ns(self):
        p = self._xf('name')
        return Property(p, self)

    @property
    def count(self):
        p = self._xf('count')
        return Property(p, self)

    @property
    def pos(self):
        p = self._xf('pos')
        return Property(p, self)