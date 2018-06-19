from fdutils.config import load_config, environment_settings
from fdutils.db import create_session, create_all, drop_all


def update_db_config(drop=True, create=True):
    import os
    test_path = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(test_path, 'conn_settings.yaml')

    load_config(file_path)

    if 'password_file' in environment_settings['vault']:
        environment_settings['vault']['password_file'] = os.path.join(test_path,
                                                                      environment_settings['vault']['password_file'])

    create_session()

    if drop:
        drop_all()

    if create:
        create_all()