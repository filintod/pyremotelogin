from .__version__ import __version__

# need to call settings files to set settings up and register any function
from .devices import settings
from .connections import settings

from fdutils.config import load_default, environment_settings
"""
    We are looking for an environment variable called DEVICECONN_SETTINGS that points to a yaml file
    similar to deviceconn_settings.yaml so we can load the settings. otherwise use the default settings in this file 
    if found
"""
load_default()