import logging
import os
import platform

from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

from fdutils.selenium_util import settings
from fdutils import files

log = logging.getLogger(__name__)

# TODO: implement remote selenium drivers with DesiredCapabilities


def get_driver_executable_path(driver_name, driver_executables_folder):

    if driver_name == 'chrome':
        executable = 'chromedriver'

    elif driver_name == 'firefox':
        executable = 'geckodriver'

    elif driver_name == 'ie':
        executable = 'geckodriver'

    else:
        raise AttributeError('This driver {} has not been programmed to be used'.format(driver_name))

    if platform.system() == 'Windows':
        executable += '.exe'

    return os.path.join(driver_executables_folder or settings.WEB_DRIVER_EXECUTABLES_PATH or '', executable)


def get_version(full_path_exec):
    import subprocess

    exec_folder, in_path_exec = os.path.split(full_path_exec)

    try:
        append = '|more' if  platform.system() == "Windows" else ''
        version = (subprocess.check_output(in_path_exec + ' --version' + append, shell=True).
                   decode().strip().rsplit(maxsplit=1)[1])

    except (FileNotFoundError, subprocess.SubprocessError):
        if platform.system() == "Windows":
            version = subprocess.check_output(
                'wmic datafile where name="{}" get Version /Value'.format(full_path_exec.replace('\\', '\\\\')))\
                .decode().strip().split('=')[1]
        else:
            raise FileNotFoundError('Did not find {} on usual places nor in PATH. '
                                    'Please add firefox executable to PATH environment variable.'.format(in_path_exec))

    return int(version.split('.')[0])


def _start_virtual_display(width, height):
    from pyvirtualdisplay import Display
    d = Display(visible=0, size=(width, height))
    d.start()
    if d.stderr or not d.is_alive():
        raise Exception('Could not open headless Display with width({}) and height ({}). StdErr: {}'
                        ''.format(width, height, d.stderr))
    return d


class WithDisplay:

    _version_found_ = None
    _start_cmd_path_ = None

    MIN_VERSION_NATIVE_HEADLESS = 0
    PROGRAM_NAMES = ['']
    OS_X_DEF_PATH = ''
    WIN_PROGRAM_PATH = ''
    NATIVE_HEADLESS = False

    @classmethod
    def get_program_path(cls):
        return files.get_executable_path(cls.PROGRAM_NAMES,
                                         osx_default_start_cmd=cls.OS_X_DEF_PATH,
                                         win_program_file_loc=cls.WIN_PROGRAM_PATH)

    @classmethod
    def native_headless(cls):
        if not cls.NATIVE_HEADLESS and cls.MIN_VERSION_NATIVE_HEADLESS > 0:
            if not cls._version_found_:
                cls._version_found_ = get_version(cls.get_program_path())

            cls.NATIVE_HEADLESS = cls._version_found_ >= cls.MIN_VERSION_NATIVE_HEADLESS

        return cls.NATIVE_HEADLESS

    def quit(self):
        try:
            super().quit()
        except Exception:
            log.exception('problems sending quit message to driver')
        finally:
            if self._display:
                try:
                    self._display.stop()
                except Exception:
                    log.exception('virtual display stop signal problem')
                    try:
                        self._display.sendstop()
                    except Exception:
                        pass
                finally:
                    self._display = None

    @classmethod
    def get_driver(cls, download_folder, **kwargs):
        display = None
        display_width = kwargs.pop('display_width', None) or settings.HEADLESS_DISPLAY_WIDTH
        display_height = kwargs.pop('display_height', None) or settings.HEADLESS_DISPLAY_HEIGHT

        kwargs.setdefault('timeout', settings.WEB_DRIVER_OPEN_TIMEOUT)

        if kwargs.get('headless') and not cls.native_headless():
            display = _start_virtual_display(display_width, display_height)

        try:
            driver = cls._get_driver(download_folder, **kwargs)
        except Exception:
            if display:
                display.stop()
            raise

        driver._display = display
        return driver


class FirefoxDriver(WithDisplay, webdriver.Firefox):

    MIN_VERSION_NATIVE_HEADLESS = 55
    PROGRAM_NAMES = ["firefox", "iceweasel"]
    OS_X_DEF_PATH = "/Applications/Firefox.app/Contents/MacOS/firefox-bin"
    WIN_PROGRAM_PATH = r'Mozilla Firefox'

    @classmethod
    def _get_driver(cls, download_folder, disable_caching=True, allow_popups=True, allow_untrusted_ssl=True,
                   disable_proxy=False, driver_executables_folder=None, cmd_line_args=(), headless=None, **kwargs):
        """

        Args:
            download_folder:
            disable_caching:
            allow_popups:
            allow_untrusted_ssl:
            disable_proxy:
            driver_executables_folder:
            cmd_line_args:
            **kwargs: FirefoxDriver kwargs.  It can also contain firefox_binary path to the firefox executable in case we want to use a
                      different version (ie dev version)

        Returns:

        """
        profile = webdriver.FirefoxProfile()
        if headless is None:
            headless = settings.HEADLESS

        profile.accept_untrusted_certs = allow_untrusted_ssl
        profile.assume_untrusted_cert_issuer = allow_untrusted_ssl

        preferences = [("browser.helperApps.neverAsk.saveToDisk", ','.join(settings.SELENIUM_MIME_TO_SAVE)),
                       ("browser.download.manager.showWhenStarting", False),
                       ("browser.download.manager.showAlertOnComplete", False),
                       ("browser.download.panel.shown", False),
                       ("browser.download.dir", download_folder),
                       ("browser.download.folderList", 2),
                       ("browser.download.useDownloadDir", True),
                       ("browser.download.closeWhenDone", True),
                       ("browser.helperApps.deleteTempFileOnExit", True),
                       ("browser.download.useWindow", False),
                       ("toolkit.startup.max_resumed_crashes", "-1"),
                       ("browser.allowpopups", allow_popups)]

        if disable_caching:
            preferences.extend([("browser.cache.disk.enable", False),
                                ("browser.cache.memory.enable", False),
                                ("browser.cache.offline.enable", False),
                                ("network.http.use-cache", False)])

        if disable_proxy:
            preferences.append(("network.proxy.type", 0))

        for k, v in preferences:
            profile.set_preference(k, v)

        profile.update_preferences()

        firefox_binary = FirefoxBinary(kwargs.get('firefox_binary'))

        if headless and cls.NATIVE_HEADLESS:
            cmd_line_args = list(cmd_line_args)
            cmd_line_args.append('--headless')
            os.environ['MOZ_HEADLESS'] = 1

        if cmd_line_args:
            firefox_binary.add_command_line_options(*cmd_line_args)

        # https://seleniumhq.github.io/selenium/docs/api/javascript/module/selenium-webdriver/firefox/index.html
        return cls(firefox_profile=profile,
                   executable_path=get_driver_executable_path('firefox', driver_executables_folder),
                   **kwargs)


class ChromeDriver(WithDisplay, webdriver.Chrome):

    MIN_VERSION_NATIVE_HEADLESS = 59
    PROGRAM_NAMES = ["chrome"]
    OS_X_DEF_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    WIN_PROGRAM_PATH = r'Google\Chrome\Application\chrome.exe'

    @classmethod
    def _get_driver(cls, download_folder, disable_caching=True, allow_popups=True, allow_untrusted_ssl=True,
                   disable_proxy=False, driver_executables_folder=None, cmd_line_args=None, headless=None,
                   **kwargs):

        chrome_options = webdriver.ChromeOptions()
        disable_dns_caching = kwargs.pop('disable_dns_caching', None)
        start_maximized = kwargs.pop('start_maximized', True)

        if headless is None:
            headless = settings.HEADLESS

        # if disable_caching:
        #     import warnings
        #     warnings.warn('There is a bug in Chrome "https://bugs.chromium.org/p/chromedriver/issues/detail?id=504"'
        #                   'that might make your tests fail when taking screenshots')

        prefs = {"download.default_directory": download_folder,
                 "download.prompt_for_download": False,
                 "safebrowsing.enabled": True}

        options = [(disable_caching, '--incognito'),
                   (start_maximized, '--start-maximized'),
                   (disable_dns_caching, '--dns-prefetch-disable'),
                   (allow_popups, '--disable-popup-blocking'),
                   (allow_untrusted_ssl, '--ignore-certificate-errors'),
                   (True, '--safebrowsing-disable-download-protection'),
                   (disable_proxy, '--no-proxy-server'),
                   (headless and cls.NATIVE_HEADLESS, '--headless')]

        for option in [v for k, v in options if k]:
            chrome_options.add_argument(option)

        if cmd_line_args:
            list(map(chrome_options.add_argument, cmd_line_args))

        chrome_options.add_experimental_option("prefs", prefs)
        return cls(executable_path=get_driver_executable_path('chrome', driver_executables_folder),
                   chrome_options=chrome_options, **kwargs)


def get_driver_from_name(name):
    _name = name.lower().strip()
    if _name in ('chrome', 'google'):
        return ChromeDriver
    elif _name in ('firefox', 'mozilla'):
        return FirefoxDriver
    # elif _name in ('ie', 'internet explorer'):
    #     return IEDriver
    else:
        raise Exception('We have not created an implementation of this driver ({})'.format(name))