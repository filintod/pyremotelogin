import collections
import json
import threading
import weakref

from fdutils import func


class Manager:

    UnknownItemError = ValueError
    DuplicatedItemError = ValueError

    def __init__(self, device):
        self._dev = weakref.proxy(device)
        self._default = None
        self.manager_lock = threading.Lock()

    def close_all(self):
        pass

    def _cls_name(self):
        return self.__class__.__name__.title()

    @property
    def users(self):
        return self._dev.users

    @property
    def interfaces(self):
        return self._dev.interfaces

    @property
    def tunnels(self):
        return self._dev.tunnels


class ManagerWithItems(Manager):

    ItemCls = None
    ItemTypeName = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._items = {}
        self._default_item_name = None

    @property
    def default(self):
        """ retrieves default connection information object """
        return self._items[self._default_item_name] if self._default_item_name else None

    def _add_instance_method(self, name, instance):
        if isinstance(instance, collections.MutableMapping):
            self.ItemCls.check_args_from_dict(instance)
            instance = self.ItemCls(**instance)
        else:
            instance = instance.copy()

        instance.name = name

        return instance, {}, instance.name

    def delete(self, name):
        if self._default_item_name == name:
            raise ValueError('This {name} is the default but you have not defined a new default {cls} '
                             'before deleting it'.format(name=name, cls=self.ItemTypeName))
        del self._items[name]

    def __getitem__(self, name):
        try:
            return self._items[name or self._default_item_name]
        except KeyError:
            raise self.UnknownItemError('This {cls} ({name}) is not known. You need to add it first or '
                                        'check your spelling'.format(name=name, cls=self._cls_name()))

    def set_default(self, name):
        """ the setter user a known user given by username """
        self.__getitem__(name)
        self._default_item_name = name
        return self

    def make_serializable(self):
        data = json.loads(json.dumps({name: item for name, item in self.items()}, default=func.default_json))
        if self._default_item_name:
            data['default_name'] = self._default_item_name

        return data

    def check_item_unique(self, item):
        return True

    def add(self, name_or_instance, set_as_default=False, **kwargs):
        """ add an item to the device.

            Args:
                name_or_instance (str or cls): the name of the item or an instance
                set_as_default (bool): flag to indicate that we want this item to be the default to be used by
                                       connections without item name
                kwargs (dict): arguments to pass to cls if creating a new instance
        """
        with self.manager_lock:

            if not isinstance(name_or_instance, str) and not isinstance(name_or_instance, self.ItemCls):
                raise TypeError('The argument name_or_instance has to be a string '
                                '(the interface name) or an instance of an Interface class')

            name = name_or_instance.name if isinstance(name_or_instance, self.ItemCls) else name_or_instance.strip()

            if not name:
                raise ValueError('You cannot pass an empty value for name of Item')

            if name not in self._items:

                if isinstance(name_or_instance, self.ItemCls):
                    instance = name_or_instance
                else:
                    self.ItemCls.check_args_from_dict(kwargs)
                    instance = self.ItemCls(name=name, **kwargs)
                    self.check_item_unique(instance)

                if set_as_default or not self._items:
                    self._default_item_name = instance.name

                self._items[name] = instance
                return instance

            else:
                raise self.DuplicatedItemError('This name ({}) has already been used'.format(name))

    # TODO: better refactor default_tunnel mess
    def add_all(self, default_name=None, default_tunnel=None, **items):
        """ adds one or more users given by the list users.

        Args:
            interfaces (dict): list of users to add given as a dictionary with the keys being the username
                          if username not provided on the values
            default_name (str): username to set as the default from the ones given in users, if there is no
        """
        for instance in items.values():
            if not (isinstance(instance, collections.MutableMapping) or isinstance(instance, self.ItemCls)):
                raise TypeError('You can only provide a dict like type or a {cls} type but you provided an item as '
                                'a type: {type}'.format(cls=self.ItemCls, type=str(type(instance))))

        self._add_multiple(self.ItemTypeName, self._add_instance_method, default_name=default_name,
                           default_tunnel=default_tunnel, **items)
        return self

    def add_dbelements_to_instance(self, dbelements, elements):

        if isinstance(dbelements, collections.Mapping) and dbelements:
            self.add_all(**dbelements)

        if elements:
            self.add_all(**elements)

        return self

    def __iter__(self):
        for item in self._items.values():
            yield item

    def items(self):
        return self._items.items()

    def __contains__(self, item):
        if isinstance(item, str):
            return item in self._items
        if isinstance(item, self.ItemCls):
            return item.name in self._items
        return False

    # TODO: refactor default_tunnel to be only used in connections
    def _add_multiple(self, item_type, item_add_method, default_name=None, default_tunnel=None, **items):
        if not items:
            return

        if default_name is not None and not isinstance(default_name, str):
            raise ValueError('The default_name {} name should be a string'.format(item_type))

        if default_tunnel is not None and not isinstance(default_tunnel, str):
            raise ValueError('The default_tunnel {} tunnel should be a string'.format(item_type))

        default_found = False
        for name, item in items.items():
            args, kwargs, item_name = item_add_method(name, item)

            if not isinstance(args, collections.Sequence):
                args = [args]

            is_default = bool(default_name and default_name == item_name)
            if is_default:
                default_found = True

            kwargs['set_as_default'] = is_default
            if default_tunnel:
                kwargs['default_tunnel'] = default_tunnel

            self.add(*args, **kwargs)

        if default_name and not default_found:
            raise self.UnknownItemError('We were given a default name ({default_name}) but none of the {item_type} '
                                        'provided had that value'.format(default_name=default_name, item_type=item_type))
