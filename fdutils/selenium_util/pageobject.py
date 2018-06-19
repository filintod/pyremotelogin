import logging
import time

from fdutils.timer import SimpleTimer
from fdutils.selenium_util import SeleniumUtil, locator_utils as loc
from fdutils.selenium_util.decorators import without_highlight, without_wait

log = logging.getLogger(__name__)

DEFAULT_MAIN_CLASS = 'SectionMainClass'
DEFAULT_MENU_FACTORY_CLASS = 'MenuFactory'


class PageObject:
    """ simple Page Object class """
    url = ''
    load_page = True
    default_section_main_class_name = DEFAULT_MAIN_CLASS
    page_object_modules_format = '{}'  # by default the name of the module would be use here

    def __init__(self, url: str = '', parent=None,
                 sel_util=None, section_name='', **sel_util_kwargs):

        self.url = (url or self.url).lstrip('/')
        self.parent = parent
        self.sel_util = None
        self._jquery_available = self._jquery_checked = False

        self.section_name = section_name
        """:type:SeleniumUtil"""

        if not self.url.startswith('http'):
            if parent:
                parent_url_folder = parent.url.rsplit('/', maxsplit=1)[0]
                self.url = parent_url_folder + '/' + self.url

            else:
                self.url = 'http://' + self.url

        if not self.url and not parent:
            raise Exception('You need to provide an IP or URL for the PageObject')

        if parent:
            self.sel_util = self.parent.sel_util
            self.root = self.parent.root

        else:
            self.sel_util = sel_util or SeleniumUtil(self.url, **sel_util_kwargs)
            self.root = self
            self._cached_pages = {}
            self._sections = {}
            self._menu_clicks_history = ()  # for SPA menu clicks

    def get_page_object(self, page_class, **kwargs):
        """ cache instances """
        if page_class not in self.root._cached_pages:
            kwargs.setdefault('parent', self)
            po = page_class(**kwargs)
            self.root._cached_pages[page_class] = po
        return self.root._cached_pages[page_class]

    def _open_page_object(self, page_class):
        return self.get_page_object(page_class).open()

    def __getattr__(self, item):
        if self.parent:
            return getattr(self.parent, item)
        else:
            return getattr(self.sel_util, item)

    def __getitem__(self, item):
        if self.parent:
            return self.parent[item]
        else:
            return self.sel_util[item]

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self, time_to_wait_to_page_complete=10):

        if not self.parent:
            self.sel_util.open()

        elif self.load_page:
            self.sel_util.open_url(self.url)

        with SimpleTimer(time_to_wait_to_page_complete) as timer:
            while not self.page_is_loaded and timer.run_and_sleep(1):
                pass

        # if self.landing_page_class:
        #     return self.get_page_object(self.landing_page_class)
        return self

    @property
    def page_is_loaded(self):
        return True

    def close(self):
        if self.parent is None and self.sel_util and self.sel_util.is_driver_open:
            self.sel_util.close()

    def __del__(self):
        # overrides default closure of window for pages with parents
        self.close()

    loc_loading_indicator = None

    @without_highlight
    def wait_for_loading_indicator_to_disappear(self, timeout=30):
        if self.loc_loading_indicator:
            t0 = time.time()
            while time.time() - t0 < timeout:
                time.sleep(2)
                if not self.get_if_visible(self.loc_loading_indicator):
                    break

    def _we_are_in_section(self):
        """ This will be overridden by subclasses that want to check the clicks do take them to a particular section """
        return True

    @without_highlight
    @without_wait
    def we_are_in_section(self, timeout=5):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self._we_are_in_section():
                return True
            time.sleep(1)

    def _get_section_by_module(self, module_name, parent=None, **kwargs):
        """ gets the page object section usually coming from a property in a page object class 

            kwargs can have the 
        """

        section_name = self.page_object_modules_format.format(module_name)

        if section_name not in self.root._sections:

            import importlib

            kwargs['parent'] = parent or self

            kwargs.setdefault('section_name', section_name)

            module = importlib.import_module(section_name)
            section_class = getattr(module,
                                    self.default_section_main_class_name,
                                    None)
            if section_class is None:
                section_class = getattr(module, DEFAULT_MENU_FACTORY_CLASS)

            self.root._sections[section_name] = self.get_page_object(section_class, **kwargs)
            if not self.root._sections[section_name].section_name:
                self.root._sections[section_name].section_name = section_name

        return self.root._sections[section_name]

    def _get_section(self, section_class, parent=None, **kwargs):
        """ gets the page object section usually coming from a property in a page object class 

            kwargs can have the 
        """

        section_name = section_class.__module__ + '.' + section_class.__name__

        if section_name not in self.root._sections:

            kwargs['parent'] = parent or self
            kwargs.setdefault('section_name', kwargs['parent'].section_name + '_' + section_name)

            self.root._sections[section_name] = self.get_page_object(section_class, **kwargs)
            if not self.root._sections[section_name].section_name:
                self.root._sections[section_name].section_name = section_name

        return self.root._sections[section_name]

    def iterate_over_clicks_check_history(self, clicks, force=False):
        for i, element in enumerate(clicks):
            is_new = (i >= len(self.root._menu_clicks_history) or element != self.root._menu_clicks_history[i] or force)
            yield is_new, element

    def clicks_to_section(self, clicks, force=False):
        """ clicks on a series of menu-related links usually to go to a page object section in the site
        
         Args:
             clicks (list): list of string locators (don't use site locators here as the comparison will break it)
             force (bool): flag to indicate if we want to reclick on a menu that was already clicked at earlier
        """

        new_clicks = []

        for is_new, element in self.iterate_over_clicks_check_history(clicks, force):
            if is_new:
                from selenium.webdriver.common.by import By
                self.sel_util.click_element(element, default_by=By.LINK_TEXT)
                try:
                    self.wait_for_loading_indicator_to_disappear()
                except Exception:
                    log.exception('Problems with loading indicator maybe not properly located')
            new_clicks.append(element)
        self.root._menu_clicks_history = new_clicks
        return self

    def load_jquery(self, **kwargs):
        kwargs['page_object'] = self
        return self.sel_util.load_jquery(**kwargs)


class AuthenticatedPageObject(PageObject):
    login_page_object = None

    def __init__(self, *args, **kwargs):
        username = kwargs.pop('username', '')
        password = kwargs.pop('password', '')

        super(AuthenticatedPageObject, self).__init__(*args, **kwargs)

        if not (self.parent or username or password):
            raise LoginProblemsError('You need to define either the username or password')

        self.is_authenticated = False

        if not self.parent:
            self.username = username
            self.password = password

    def open(self, time_to_wait_to_page_complete=10, opening_login=False):

        super(AuthenticatedPageObject, self).open(time_to_wait_to_page_complete)

        if not self.is_authenticated and not opening_login:
            auth_page = self.get_page_object(self.login_page_object).open(opening_login=True)
            auth_page.enter_username_password()

        return self


class LoginProblemsError(Exception):
    """ when something happened during login into """


class PageObjectLogin(AuthenticatedPageObject):

    username_locator = loc.text_input('(?i)Username')
    password_locator = loc.password_input('(?i)Password')
    submit_locator = loc.button()
    login_setup_locator = None

    def __init__(self, *args, **kwargs):
        super(PageObjectLogin, self).__init__(*args, **kwargs)
        self.login_successful = False

    def was_login_successful(self, *args):
        return self.login_successful

    def before_entering_username_password(self):
        pass

    def after_clicking_submit_locator(self):
        pass

    def enter_username_password(self, username='', password='', redirect=None):
        username = username or self.username
        password = password or self.password

        if not self.login_successful:

            if self.login_setup_locator:
                self.login_setup_locator.click()

            self.before_entering_username_password()

            self.username_locator = username
            self.password_locator = password

            if self.submit_locator:
                self.submit_locator.click()

            if self.was_login_successful(username):
                self.login_successful = True
                self.after_clicking_submit_locator()
                if redirect:
                    return redirect(parent=self.parent)
                else:
                    return self
            else:
                raise LoginProblemsError('Username {} or password {} are not correct'.format(username, password))


class SPAWithMenuMixin:
    """ multi-level menu SPA open page mixin """

    CLICKS_TO_SECTION = ()

    def we_are_in_section(self):
        if any((a[0] for a in self.iterate_over_clicks_check_history(self.CLICKS_TO_SECTION))):
            return False
        return super(SPAWithMenuMixin, self).we_are_in_section()

    def open(self):
        with self.sel_util.without_wait():
            if self.we_are_in_section():
                return self
        return self.clicks_to_section(self.CLICKS_TO_SECTION)


class PageObjectMenuItem(SPAWithMenuMixin, PageObject):
    """ Basic Page Object Menu Item page"""


