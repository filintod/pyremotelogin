import logging

from remotelogin.devices.exceptions import UnknownUserError, DuplicatedUserError
from remotelogin.devices.properties import UserInfo
from .base import ManagerWithItems

log = logging.getLogger(__name__)


class UsersManager(ManagerWithItems):

    UnknownItemError = UnknownUserError
    DuplicatedItemError = DuplicatedUserError
    ItemCls = UserInfo
    ItemTypeName = 'users'

    def __init__(self, *args, **kwargs):
        self._default_item_name = None
        super(UsersManager, self).__init__(*args, **kwargs)

    def add(self, user_or_username, set_as_default=False, **kwargs):
        """ add a user to the device.

            Args:
                user_or_username (str or UserInfo): the name of the username or a User instance
                set_as_default (bool): flag to indicate that we want this user to be the default to be used by
                                       connections without username
                kwargs (dict): arguments to pass to User if creating a user
        """
        user = super().add(user_or_username, set_as_default=set_as_default, **kwargs)

        if user.expected_prompt == -1 and self.default and self.default.expected_prompt != -1:
            user.expected_prompt = self.default.expected_prompt

        return user

    def _add_instance_method(self, name, instance):
        instance, d, name = super()._add_instance_method(name, instance)
        if not instance.username:
            instance.username = name

        return instance, d, name
