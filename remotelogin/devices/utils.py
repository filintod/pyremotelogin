import collections
import logging

import fdutils as utils

log = logging.getLogger(__name__)


def transform_password(values, crypto_engine_function):
    """ transform a structure by encrypting/decrypting any value in a dictionary for any key that contains the word
        'password'
    """
    for _k, _v in values.items():
        if isinstance(_v, collections.MutableMapping):
            transform_password(_v, crypto_engine_function)
        elif utils.lists.is_list_or_tuple(_v):
            for _vv in (_vv for _vv in _v if isinstance(_vv, collections.MutableMapping)):
                transform_password(_vv, crypto_engine_function)
        elif 'password' in _k and _v:
            values[_k] = crypto_engine_function(_v)


def get_ip_from_default_or_hostname(hostname, default_ip='', ip_type=''):
    """ in case default ip is not given we try to get it from the hostname """
    if ip_type.lower() in ('v4', '4', 4, 'ipv4', 'ip4'):
        family = 'ipv4'
    elif ip_type.lower() in ('v6', '6', 6, 'ipv6', 'ip6'):
        family = 'ipv6'
    else:
        family = None

    if not default_ip and hostname:
        try:
            ip_from_hostname = utils.net.nslookup_all(hostname, family)
            if ip_from_hostname:
                return ip_from_hostname[0]
        except Exception:
            log.debug('Problems doing an nslookup of ' + str(hostname))
            return ''
    else:
        return default_ip