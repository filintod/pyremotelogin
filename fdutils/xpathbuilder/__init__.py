import sys
from . import node

from fdutils.xml import patch_htmlelement
patch_htmlelement()


class XPathBuilderNS:

    def __init__(self, namespace=''):
        self.namespace = namespace
        self.root = node.Node('/', ns=self.namespace)
        self.anystrip = self.all_._.strip()
        self.any = self.all()
        self._ = node.Node(ns=self.namespace)._

    def Node(self, *args, **kwargs):
        kwargs['ns'] = self.namespace
        return node.Node(*args, **kwargs)

    def XPNS(self, namespace):
        return XPathBuilderNS(namespace)

    def __getattr__(self, item):
        return getattr(self.root(), item)

    def __call__(self, node):
        return self.Node(node, ns=self.namespace)


sys.modules[__name__] = XPathBuilderNS()