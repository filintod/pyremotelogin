import logging
import uuid

from fdutils.capabilities import WithCapabilities


log = logging.getLogger(__name__)

__author__ = 'Filinto Duran (duranto@gmail.com)'


class WithSimpleUserManagement:
    """ utility mixin to add simple user management functionality.
        all actions are related to the root group but sub-groups can easily
        be created by using the self.groups attribute directly

    """

    def __init__(self):
        self.groups = Group('root')

    def add_user(self, user):
        """ adds an user to the root group or to the group defined in group_name

        """
        self.groups.add_user(user)

    def remove_user(self, username):
        self.groups.remove_user_by_name(username)

    def get_users(self):
        return self.groups.get_all_users()

    def get_users_capable_of(self, capabilities):
        return self.groups.get_users_capable_of(capabilities)


class User(WithCapabilities):

    def __init__(self, name, userid=None, username='', password='', key_filename=None, location=''):
        self.name = name
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.location = location
        self.id = userid or uuid.uuid4()
        super(User, self).__init__()

    def get_dict(self):
        return dict(name=self.name, username=self.username, password=self.password, key_filename=self.key_filename)


class Group(WithCapabilities):
    """ Simple group class. We are not limiting the users to be in only one group or doing any kind of RBAC permitting

    """

    def __init__(self, name):
        self.name = name
        self.groups = dict()
        self.users = dict()
        super(Group, self).__init__()

    def add_user(self, *user):
        for u in user:
            self.users[u.username] = u
        return True

    def remove_user_by_name(self, *username):
        for u in username:
            try:
                del(self.users[u])
            except:
                pass

    def add(self, *group):
        """ add groups given by objects

        """
        ret = []
        for g in group:
            self.groups[g.name] = g
            ret.append(g)

        return ret[0] if len(ret) == 1 else ret

    def add_by_name(self, *group_name):
        """ add groups given by name

        """
        return self.add(*[Group(name) for name in group_name])

    def remove(self, *name):
        """ This will remove it and everything underneath will be GC !!

        """
        for g in name:
            try:
                group, parent = self.find_with_parent(g)
                del parent.groups[g]
            except:
                log.error('Group ({}) was either not found or could not be deleted'.format(g))

    def get_users_capable_of(self, capabilities):
        """ Generator for list of users capable of something

        """
        for u in self.get_all_users():
            if u.can(capabilities):
                yield u

    def get_all_users_with_groups(self):
        """ Generator for list of users. If users are related to more than one group they will show duplicated

        """
        for name, value in self.users.items():
            yield value, self
        for kid_name, kid in self.groups.items():
            for u, g in kid.get_all_users_with_groups():
                yield u, g

    def get_all_users(self):
        for u, g in self.get_all_users_with_groups():
            yield u

    def __len__(self):
        return len(list(self.get_all_users()))

    def remove_user(self, *user):
        return self.remove(*[u.name for u in user])

    def remove_user_from_all(self, *username):
        self.remove_user_by_name(*username)
        for kid_name, kid_group in self.groups.items():
            kid_group.remove_user_from_all(*username)

    def get_user(self, username):
        if username in self.users:
            return self.users[username]
        for kid_name, kid_group in self.groups.items():
            u = kid_group.get_user(username)
            if u:
                return u
        return None

    def find_with_parent(self, group_name):
        """ tries to find the group

        """
        if group_name == self.name or group_name in self.groups:
            return self.groups[group_name], self
        for kid_name, kid_group in self.groups.items():
            found, parent = kid_group.find_with_parent(group_name)
            if found is not None:
                return found, parent
        return None, None

    def find(self, group_name):
        group, parent = self.find_with_parent(group_name)
        return group

    def find_user(self, username):
        for u in self.get_all_users():
            if u.name == username:
                return u