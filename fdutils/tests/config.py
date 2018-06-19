import os
from fdutils import config

cur_dir = os.path.split(os.path.abspath(__file__))[0]


def test_resolving_variables():
    settings = config.load_config(os.path.join(cur_dir, 'files', 'rglibsettings.yaml'))
    assert settings['db'] == {'vendor': 'sqllite',
                             'host': None,
                             'port': None,
                             'db': 'C:\\Users\\duran\\PycharmProjects\\rglib\\cms_db.db'}
    assert settings['soap_keys'] == {'certfile': 'C:\\Users\\duran\\PycharmProjects\\rglib\\keys\\webservices.cert',
                                     'keyfile': 'C:\\Users\\duran\\PycharmProjects\\rglib\\keys\\webservices_enc.key\\C:\\Users\\duran\\PycharmProjects\\rglib\\PycharmProjects\\rglib',
                                     'password_file': 'C:\\Users\\duran\\rglib\\soap_key_password',
                                     'other': os.path.expanduser('~'),
                                     'other_userhome': os.path.join(os.path.expanduser('~'), '.local', 'other', 'other')}

def test_parse_config():
    from fdutils.selenium_util import settings as selsettings
    from remotelogin.devices import settings as devsettings

    user_home = os.path.expanduser('~')
    rglib_folder = os.path.join(user_home, 'PycharmProjects', 'rglib')
    rglib_folder2 = rglib_folder + os.path.sep + os.path.join('PycharmProjects', 'rglib')

    assert selsettings.WEB_DRIVER_EXECUTABLES_PATH is None
    assert devsettings.DEFAULT_STORAGE_FOLDER == user_home

    settings = config.parse_config(os.path.join(cur_dir, 'files', 'rglibsettings.yaml'))
    assert settings['db'] == {'vendor': 'sqllite',
                             'host': None,
                             'port': None,
                             'db': os.path.join(rglib_folder, 'cms_db.db')}
    assert settings['soap_keys'] == {'certfile': os.path.join(rglib_folder, 'keys', 'webservices.cert'),
                                     'keyfile': os.path.join(rglib_folder, 'keys', 'webservices_enc.key') +
                                                os.path.sep + rglib_folder2,
                                     'password_file': os.path.join(user_home, 'rglib', 'soap_key_password'),
                                     'other': user_home,
                                     'other_userhome': os.path.join(user_home, '.local', 'other', 'other')}
    assert selsettings.WEB_DRIVER_EXECUTABLES_PATH == 'testing'
    assert devsettings.DEFAULT_STORAGE_FOLDER == os.path.join(user_home, 'rglib')
