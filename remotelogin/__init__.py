from .__version__ import __version__
import logging
log = logging.getLogger(__name__)
# need to call settings files to set settings up and register any function
try:
    from .devices import settings
except ModuleNotFoundError:
    log.warning("Problems importing Device Settings. Disregard is not using devices...")
from .connections import settings

from fdutils.config import load_default, environment_settings
"""
    We are looking for an environment variable called DEVICECONN_SETTINGS that points to a yaml file
    similar to deviceconn_settings.yaml so we can load the settings. otherwise use the default settings in this file 
    if found
"""
load_default()