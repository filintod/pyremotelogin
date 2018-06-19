import inspect
import logging

from fdutils import crypto

log = logging.getLogger(__name__)


def get_class_that_defined_method(meth):
    if inspect.ismethod(meth):
        for cls in inspect.getmro(meth.__self__.__class__):
           if cls.__dict__.get(meth.__name__) is meth:
                return cls
        meth = meth.__func__  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0])
        if isinstance(cls, type):
            return cls
    return None


def default_json(o, encrypt=False, crypto_engine=None):
    """ makes some serializing interpretations of objects for json """
    from uuid import UUID
    import ipaddress

    str_classes = UUID, ipaddress._IPAddressBase

    if any(isinstance(o, str_cls) for str_cls in str_classes):
        return str(o)

    if hasattr(o, 'to_json'):
        ret = o.to_json()

    elif o.__dict__:
        ret = o.__dict__

    elif o.__slots__:
        ret = {k:getattr(o, k) for k in o.__slots__ if not k.startswith('_')}

    else:
        raise TypeError

    if encrypt and 'password' in ret:
        crypto_engine = crypto_engine or crypto.get_default_crypto_engine()
        ret['password'] = crypto_engine.encrypt(ret['password'])

    return ret