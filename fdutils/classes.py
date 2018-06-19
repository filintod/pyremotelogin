import json
import threading
import logging
import weakref

log = logging.getLogger(__name__)


__author__ = 'Filinto Duran (duranto@gmail.com)'


class ThreadSafeWeakChildLinkMap:
    def __init__(self):
        self._children = weakref.WeakValueDictionary()
        self._lock = threading.Lock()

    def put(self, child, child_id=None):
        if child_id is None:
            import uuid
            child_id = uuid.uuid4()
        with self._lock:
            self._children[child_id] = child

    def get(self, child_id):
        with self._lock:
            return self._children.get(child_id, None)

    def delete(self, child_id):
        with self._lock:
            try:
                del self._children[child_id]
            except KeyError:
                pass

    def values(self):
        with self._lock:
            return list(self._children.values())

    def __iter__(self):
        children = self.values()
        for child in children:
            yield child


# custom json encoder
class JsonEncoder(json.JSONEncoder):
    """ return the json encoder method if class has a for_json method """

    def default(self, obj):
        if hasattr(obj, 'for_json'):
            return obj.for_json()
        return json.JSONEncoder.default(self, obj)


def mixin(instance, mixin_class):
    """  Dynamically mixes a mixin class into an object
    Args:
        instance:  current object instance
        mixin_class:  the class whose functions and attributes we want to mix into instance

    Returns:

    """
    import types

    for name in mixin_class.__dict__:
        if name.startswith('__') and name.endswith('__'):
            continue
        elif isinstance(mixin_class.__dict__[name], types.FunctionType):
            # bind function to instance
            instance.__dict__[name] = mixin_class.__dict__[name].__get__(instance)
        else:
            instance.__dict__[name] = mixin_class.__dict__[name]


def get_class(kls):
    """ function to get a reference to a class from a class name

    similar to:
     cls = "library.module.class"
     m = library.module
     m = getattr(m, 'module.class')     # now m = module.class
     m = getattr(m, 'class')            # now m = class
    """
    import importlib
    module, klass = kls.rsplit('.', 1)
    m = importlib.import_module(module)
    return getattr(m, klass)


class Singleton:
    # from http://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html#id2
    __instance = None

    def __new__(cls, val):
        if Singleton.__instance is None:
            Singleton.__instance = object.__new__(cls)
            Singleton.__instance.val = val
        return Singleton.__instance
