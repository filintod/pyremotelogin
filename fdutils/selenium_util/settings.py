import os

"""
Download the drivers for the browsers to selenium_drivers folder:

chrome: https://sites.google.com/a/chromium.org/chromedriver/downloads
firefox: https://github.com/mozilla/geckodriver/releases
"""
DEFAULT_DRIVER_EXECUTABLE = 'chrome'
MAX_LENGTH_FUNCTION_NAME_TO_RECORD = 40
WEB_DRIVER_EXECUTABLES_PATH = os.environ.get('SELENIUM_DRIVERS_PATH', None)
WEB_DRIVER_OPEN_TIMEOUT = 10
REMOTE_PORT = 4444
IMPLICIT_WAIT = 10
THINK_TIME = 0.5
SCREEN_SHOTS_FOLDER = 'selenium_shots'
DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), 'seleniumutils_downloads')
HIGHLIGHTING_COLOR = 'orange'
HIGHLIGHTING_SIZE = 4
HIGHLIGHTING_TIME = 0.6
ENABLE_SCREENSHOT_HIGHTLIGHTING = False
ENABLE_HIGHTLIGHTING = False


HEADLESS = False
HEADLESS_DISPLAY_WIDTH = 1024
HEADLESS_DISPLAY_HEIGHT = 768

SELENIUM_MIME_TO_SAVE = ("application/csv", "text/csv", "text/css", "application/zip", "application/x-gzip",
                         "application/gzip",
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                         "application/msword", "application/vnd.ms-powerpoint", "application/vnd.ms-excel",
                         "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                         "application/vnd.ms-access",
                         "application/pdf", "application/xml", "application/json", "application/octet-stream",
                         "application/download",  "application/exe", "application/x-exe")

# update settings with environment settings


def after_update():
    """ call this function after an update to global fdutil.config.settings variable"""
    if HEADLESS:
        try:
            import pyvirtualdisplay
        except ImportError:
            print('#' * 80)
            print(
                'When doing Headless testing we expect to have pyvirtualdisplay to manage xvfb available and it is not')
            print('You can install it with "pip3 install pyvirtualdisplay"')
            print('#' * 80)
            raise

    if WEB_DRIVER_EXECUTABLES_PATH and WEB_DRIVER_EXECUTABLES_PATH not in os.environ['PATH']:
        os.environ['PATH'] += ';' + WEB_DRIVER_EXECUTABLES_PATH


from fdutils.config import register_settings
register_settings(globals(), 'selenium',
                  paths_vars=['SELENIUM_WEB_DRIVER_EXECUTABLES', 'DOWNLOAD_FOLDER'],
                  after_update=after_update)
