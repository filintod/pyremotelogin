import remotelogin.devices.base
import remotelogin.devices.properties
from remotelogin.devices.exceptions import UnknownUserError, DuplicatedUserError
import pytest


def get_device_and_user():
    my_device = remotelogin.devices.base.DeviceBase('test')
    user = remotelogin.devices.properties.UserInfo('test_user', 'test_user_password')
    return my_device, user


def get_device_and_user_dict():
    my_device = remotelogin.devices.base.DeviceBase('test')
    user = dict(username='test_user', password='test_user_password')
    return my_device, user


def test_add_single_user_via_device_bad_type_not_dictionary():
    user = remotelogin.devices.properties.UserInfo('test_user', 'test_user_password')
    with pytest.raises(TypeError):
        # must pass a dictionary
        remotelogin.devices.base.DeviceBase('test', users=user)


def test_add_empty_string_as_username_raises_ValueError():
    with pytest.raises(ValueError):
        # must pass a dictionary
        remotelogin.devices.base.DeviceBase('test', users={'': {}})


def test_add_single_user_via_device():
    user = remotelogin.devices.properties.UserInfo(password='test_user_password')
    dev = remotelogin.devices.base.DeviceBase('test', users=dict(test_user=user))
    assert dev.users.default.password == user.password
    assert dev.users.default.username == 'test_user'
    assert dev.users.default.name == 'test_user'

def test_add_single_from_User():
    my_device, user = get_device_and_user()
    my_device.users.add(user)
    assert my_device.users.default.password == user.password
    assert my_device.users.default.username == 'test_user'
    assert my_device.users.default.name == 'test_user'


def test_add_multiple_from_User():
    my_device, user = get_device_and_user()
    user2 = remotelogin.devices.properties.UserInfo(password='test_user_password')
    user3 = remotelogin.devices.properties.UserInfo(password='test_user_password')

    my_device.users.add_all(test_user=user, user2=user2, user3=user3)

    assert my_device.users.users['user3'].name == 'user3'
    assert my_device.users.users['user3'].username == 'user3'
    assert my_device.users.users['user2'].name == 'user2'
    assert my_device.users.users['user2'].username == 'user2'


def test_add_multiple_from_User_diff_name_in_passed_args():
    """ usernames in dictionary are like aliases if there is a username property already present"""
    my_device, user = get_device_and_user()
    user2 = remotelogin.devices.properties.UserInfo(username='user2', password='test_user_password2')
    user3 = remotelogin.devices.properties.UserInfo(username='user3', password='test_user_password3')

    my_device.users.add_all(test_user=user, user4=user2, user5=user3, default_name='user4')

    assert my_device.users.default.username == 'user2'

    assert my_device.users.users['user4'] is not user2
    assert my_device.users.users['user4'].username == 'user2'
    assert my_device.users.users['user4'].password == 'test_user_password2'
    assert my_device.users.users['user5'] is not user3
    assert my_device.users.users['user5'].username == 'user3'
    assert my_device.users.users['user5'].password == 'test_user_password3'


def test_add_multiple_from_User_via_device():

    user2 = remotelogin.devices.properties.UserInfo(password='test_user_password')
    user3 = remotelogin.devices.properties.UserInfo(password='test_user_password')
    my_device = remotelogin.devices.base.DeviceBase('test', users=dict(user2=user2, user3=user3))
    assert my_device.users.users['user3'].username ==  'user3'
    assert my_device.users.users['user2'].username == 'user2'

def test_add_multiple_from_User_set_last_as_default():
    my_device, user = get_device_and_user()
    user2 = remotelogin.devices.properties.UserInfo(password='test_user_password')
    user3 = remotelogin.devices.properties.UserInfo(password='test_user_password')
    my_device.users.add_all(test_user=user, user2=user2, user3=user3, default_name='user3')
    assert my_device.users.default.username == 'user3'


def test_add_multiple_from_User_set_bad_as_default_raises_UnknownUserError():
    my_device, user = get_device_and_user()
    user2 = remotelogin.devices.properties.UserInfo(password='test_user_password')
    user3 = remotelogin.devices.properties.UserInfo(password='test_user_password')
    with pytest.raises(UnknownUserError):
        my_device.users.add_all(test_user=user, user2=user2, user3=user3, default_name='user32')


def test_set_default_user_explicitely():
    my_device, user = get_device_and_user()
    user2 = remotelogin.devices.properties.UserInfo(password='test_user_password')
    user3 = remotelogin.devices.properties.UserInfo(password='test_user_password')
    my_device.users.add_all(test_user=user, user2=user2, user3=user3)
    my_device.users.set_default('user2')
    assert my_device.users.default.username == 'user2'


def test_set_default_user_explicitely_bad_name_raises_UnknownUserError():
    my_device, user = get_device_and_user()
    user2 = remotelogin.devices.properties.UserInfo(password='test_user_password')
    user3 = remotelogin.devices.properties.UserInfo(password='test_user_password')
    my_device.users.add_all(test_user=user, user2=user2, user3=user3)
    with pytest.raises(UnknownUserError):
        my_device.users.set_default('user22')


def test_add_same_twice_from_User():
    my_device, user = get_device_and_user()
    my_device.users.add(user)
    with pytest.raises(DuplicatedUserError):
        my_device.users.add(user)


def test_add_single_from_dict_raises_type_error_when_passing_dict_instead_of_str():
    my_device, user = get_device_and_user_dict()
    with pytest.raises(TypeError):
        my_device.users.add(user)


def test_add_single_from_params():
    my_device, user = get_device_and_user_dict()
    username = user.pop('username')
    my_device.users.add(username, **user)
    assert my_device.users.default.username is username


def test_multiple_from_params():
    my_device, user = get_device_and_user_dict()
    user2 = dict(password='p2')
    user3 = dict(password='p3')
    my_device.users.add_all(user=user, user2=user2, user3=user3, default_name='user3')
    assert my_device.users.users['user3'].username == 'user3'
    assert my_device.users.users['user2'].username == 'user2'
    assert my_device.users.default.username == 'user3' and my_device.users.default.password == 'p3'


def test_add_single_from_wrong_params():
    my_device, user = get_device_and_user_dict()
    username = user.pop('username')
    user['my_other_param'] = 'hello there'
    with pytest.raises(KeyError):
        my_device.users.add(username, **user)


def test_delete_user():
    my_device, user = get_device_and_user_dict()
    user2 = dict(password='p2')
    user3 = dict(password='p3')
    my_device.users.add_all(user=user, user2=user2, user3=user3, default_name='user3')
    assert my_device.users['user3'].username == 'user3'
    assert my_device.users['user2'].username == 'user2'
    assert my_device.users.default.username == 'user3' and my_device.users.default.password == 'p3'
    my_device.users.delete('user2')
    with pytest.raises(UnknownUserError):
        my_device.users['user2']


def test_delete_default_user_raises_ValueError():
    my_device, user = get_device_and_user_dict()
    user3 = dict(password='p3')
    my_device.users.add_all(user=user, user3=user3, default_name='user3')
    assert my_device.users['user3'].username == 'user3'
    assert my_device.users.default.username == 'user3' and my_device.users.default.password == 'p3'
    with pytest.raises(ValueError):
        my_device.users.delete('user3')


def test_iterate_over_users():
    my_device, user = get_device_and_user_dict()
    user2 = dict(password='p2')
    user3 = dict(password='p3')
    my_device.users.add_all(user=user, user2=user2, user3=user3, default_name='user3')
    assert my_device.users['user3'].username == 'user3'
    assert my_device.users['user2'].username == 'user2'
    assert my_device.users.default.username == 'user3' and my_device.users.default.password == 'p3'
    assert [my_device.users['user'], my_device.users['user2'], my_device.users['user3']] == list(sorted(my_device.users, key=lambda u:u.username))

