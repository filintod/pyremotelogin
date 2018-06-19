import os
from fdutils.config import register_settings


DEFAULT_STORAGE_FOLDER = os.path.expanduser("~")
ENCRYPT_PASSWORDS_IN_DB = False
LOCATION = ''

# ENV_TO_VARS = {}

register_settings(globals(), 'devices')