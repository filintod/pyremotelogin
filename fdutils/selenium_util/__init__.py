# -*- coding: utf-8 -*-
import contextlib
import functools
import logging
import os
import re
import threading
import time

from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.remote import webelement
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select

from fdutils import files
from fdutils.decorators import retry
from fdutils.html import parse_html_table, parse_html_table_row_headers
from fdutils.selenium_util.drivers import get_driver_from_name
from fdutils.selenium_util import locator_utils as loc
from fdutils.selenium_util import settings

log = logging.getLogger(__name__)

# ##########     THREAD LOCAL STORAGE FOR THINK TIME     ################### #
thread_local_think_time = threading.local()
thread_local_think_time.v = 0
# ########################################################################## #


#  ##############################################################################################################  #
#  MONKEY PATCH WebElement._execute to insert a delay before any action on an element (after it is found and retrieved)
#  ##############################################################################################################  #
def _execute_with_think_time(f):
    """ decorates webelement.Webelement._execute method to include a think time """

    @functools.wraps(f)
    def w(*args, **kwargs):
        r = f(*args, **kwargs)
        time.sleep(thread_local_think_time.v)
        return r
    return w


webelement.WebElement._execute = _execute_with_think_time(webelement.WebElement._execute)

LATEST_JQUERY_GOOGLE_HOSTED = '3.2.1'


# TODO: Selenium Remote Server capability
# TODO: Appium
class SeleniumUtil(object):
    def __init__(self, base_url="",
                 driver=None,
                 driver_kwargs=None,
                 enable_highlighting=False,
                 enable_screen_shot_highlight=False,
                 implicit_wait=0,
                 think_time=0,
                 download_folder='',
                 screen_shots_folder='',
                 highlighting_color='',
                 highlighting_size=0,
                 highlighting_time=0,
                 remote_ip=None,
                 remote_port=None,
                 desired_capability=None,
                 headless=None,
                 display_width=None,
                 display_height=None
                 ):
        """ This is a wrapper around webdriver selenium

        Args:
            base_url (str): a HTTP(S) url like http://www.google.com
            driver (WebDriver): any of the configured webdriver objects in drivers.py (FirefoxDriver or ChromeDriver)
            driver_kwargs (dict): any custom kwargs for the drivers
            enable_highlighting (bool): highlight every find element statement
            enable_screen_shot_highlight (bool): get a screenshot after the highlight
            implicit_wait (float): how long to wait to find an element
            think_time (float): delay after every command to mimic human behavior
            download_folder (str): path to save downloaded files folder. By default it will be seleniumutils_downloads under this folder.
            screen_shots_folder (str): path to save screenshots
            highlighting_color (str): this is a css valid color (ie: red, blue, #FF0000). Check https://www.w3schools.com/cssref/css_colors.asp
            highlighting_size (int): border size.

        """

        if isinstance(driver, str):
            driver = get_driver_from_name(driver)

        if driver is None:
            driver = get_driver_from_name(settings.DEFAULT_DRIVER_EXECUTABLE)

        self.web_driver = driver
        self._driver_kwargs = driver_kwargs or {}
        self.driver = None  # type: WebDriver

        self.url = base_url if base_url.startswith('http') else ("http://" + base_url) if base_url else ''
        self.accept_next_alert = True

        self.download_folder = download_folder or settings.DOWNLOAD_FOLDER
        self.implicit_wait = implicit_wait or settings.IMPLICIT_WAIT
        screen_shots_folder = screen_shots_folder or os.path.join(self.download_folder, settings.SCREEN_SHOTS_FOLDER)
        self.screen_shot_folder = os.path.realpath(screen_shots_folder)
        self.think_time = think_time

        self._is_driver_open = False
        self._default_find_element_method = self._default_find_elements_method = None

        self._enable_highlighted_find_elements = enable_highlighting or settings.ENABLE_HIGHTLIGHTING
        self._screen_shot_highlights = enable_screen_shot_highlight or settings.ENABLE_SCREENSHOT_HIGHTLIGHTING
        self._highlighting_color = highlighting_color or settings.HIGHLIGHTING_COLOR
        self._highlighting_size = highlighting_size or settings.HIGHLIGHTING_SIZE
        self._highlighting_time = highlighting_time or settings.HIGHLIGHTING_TIME


        # headless vars
        self._headless = headless or settings.HEADLESS
        self._display_height = display_height
        self._display_width = display_width

        self._create_download_shots_folders()

        self._remote_ip = remote_ip
        self._remote_port = remote_port or settings.REMOTE_PORT
        self._desired_capability = desired_capability

        self._jquery_available = self._jquery_checked = False

    def _create_download_shots_folders(self):
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)

        if not os.path.exists(self.screen_shot_folder):
            os.makedirs(self.screen_shot_folder)

        log.info('Selenium Files Download Folder: ' + self.download_folder)
        log.info('Selenium Screenshots Download Folder: ' + self.download_folder)

    def set_think_time(self, think_time=None):
        """ sets the time the system waits before executing a command.

        Args:
            think_time:

        Returns:

        """
        think_time = think_time or self.think_time
        thread_local_think_time.v = think_time

    def __getattr__(self, item):
        """ proxy operations to webdriver for unknowns

        :param item:
        :return:
        """
        if item != 'driver':
            return getattr(self.driver, item)
        raise KeyError(item)

    @property
    def is_driver_open(self):
        return self._is_driver_open

    def get_window_height(self):
        js = "return Math.max(document.body.scroll{0}, document.body.offset{0}, " \
             "document.documentElement.client{0}, document.documentElement.scroll{0}, " \
             "document.documentElement.offset{0});"

        real_windows_height = self.driver.execute_script(js.format('Height'))
        viewport_height = self.driver.execute_script("return window.innerHeight")

        return real_windows_height, viewport_height

    def open_base(self):
        try:
            self.restore_wait()
            self.driver.get(self.url)
            self.set_think_time()

            return self

        except Exception:
            log.exception('Problems opening base url {}'.format(self.url))
            self.driver.quit()
            raise

    def open(self, **driver_kwargs):
        from fdutils.lists import setdefault
        driver_kwargs = setdefault(driver_kwargs, self._driver_kwargs,
                                   headless=self._headless,
                                   display_width=self._display_width,
                                   display_height=self._display_height)

        if not self.is_driver_open:
            self.driver = self.web_driver.get_driver(self.download_folder, **driver_kwargs)
            self._is_driver_open = True

            self._default_find_element_method = self.driver.find_element
            self._default_find_elements_method = self.driver.find_elements

            if self._enable_highlighted_find_elements:
                self.turn_on_highlighted_find_elements(self._highlighting_color, self._highlighting_size)

        if self.url:
            self.open_base()

        return self

    def __enter__(self):
        return self.open()

    def open_path(self, relative_url):
        """ relative jump to a section of the site with base URL defined in self.base_url

        :param relative_url:
        :return:
        """
        self.driver.get(self.url.rstrip('/') + '/' + relative_url.lstrip('/'))

    def open_url(self, url):
        """ absolute site url open instead of the relative one done with goto

        :param url:
        :return:
        """

        self.driver.get(url)

    def parse_html_table(self, selector, **kwargs):
        return parse_html_table(self.get_inner_html_as_xml(selector, 'table'), **kwargs)

    def parse_html_table_row_headers(self, selector, **kwargs):
        return parse_html_table_row_headers(self.get_inner_html_as_xml(selector, 'table'), **kwargs)

    @contextlib.contextmanager
    def based_on(self, url):
        """ temporary change of base url for a section of code """
        old_base = self.url
        self.url = url
        yield
        self.url = old_base

    def get_page_source(self):
        """ retrieves the page source code and removes the xhtml header from the xml tag at the beginning.

            Note: Use judiciously or namespace conflict might appear.
                if that happen, use the namespace as you would:
                        like    =>     xml.xpath(xpath, namespaces={'ns': XHTML_NAMESPACE})

            This hack will save some typing as we would not need all those namespace additions on every xpath search

        :return:
        """
        return self.driver.page_source.replace('xmlns="http://www.w3.org/1999/xhtml"', '')

    def close(self):
        try:
            if self.driver:
                self.driver.quit()
        finally:
            self._is_driver_open = False
            self.driver = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        return self.close()

    def get(self, item, no_highlight=False, default_by=None):
        """
        Returns:
            webelement.WebElement
        """
        if not isinstance(item, WebElement):
            if no_highlight:
                return self._default_find_element_method(*loc.parse_selector(item, default_by=default_by))
            else:
                return self.driver.find_element(*loc.parse_selector(item, default_by=default_by))
        return item

    def get_if_visible(self, item):
        e = self.get(item, no_highlight=True)
        if e.is_displayed():
            return e
        else:
            return None

    def get_or_none(self, item):
        try:
            return self.get(item)
        except NoSuchElementException:
            return None

    def __getitem__(self, item):
        return self.get(item)

    def get_screenshot(self, file_path='', folder_path='', fixed_header_loc=None, fixed_footer_loc=None):
        """ utility to get a screenshot and store it to the appropriate folder.
            Also call the test it is related to if there is one. Folder should exists or it will raise an exception

        :return:
        """
        if not file_path:
            file_path = files.get_filename_timestamped(self.driver.title + '.png')

        elif not file_path.endswith('.png'):
            file_path += '.png'

        folder_path = folder_path or self.screen_shot_folder
        file_name = os.path.join(folder_path, file_path)
        wnd_height, viewport_height = self.get_window_height()
        if viewport_height + 100 > wnd_height :
            self.driver.get_screenshot_as_file(file_name)
        else:
            self.fullpage_screenshot(file_name, viewport_height, fixed_header_loc, fixed_footer_loc)
        return file_name

    def fullpage_screenshot(self, file_name, viewport_height=0, fixed_header_loc=None, fixed_footer_loc=None):
        """ gets the full page screenshot by stitching together screenshots of the pages while scrolling down
            from http://seleniumpythonqa.blogspot.com/2015/08/generate-full-page-screenshot-in-chrome.html

        Args:
            file_name:
            viewport_height:

        Returns:

        """

        from PIL import Image
        import io

        driver = self.driver
        total_width = driver.execute_script("return document.body.offsetWidth")
        total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
        viewport_width = driver.execute_script("return document.body.clientWidth")
        if viewport_height == 0:
            viewport_height = driver.execute_script("return window.innerHeight")
        rectangles = []

        def remote_fixed_section(locator):
            time.sleep(0.1)
            driver.execute_script("arguments[0].setAttribute('style', 'position: absolute; top: 0px;');", locator)

        i = 0
        while i < total_height:
            ii = 0
            top_height = i + viewport_height

            if top_height > total_height:
                top_height = total_height

            while ii < total_width:
                top_width = ii + viewport_width

                if top_width > total_width:
                    top_width = total_width

                rectangles.append((ii, i, top_width, top_height))

                ii = ii + viewport_width

            i = i + viewport_height

        stitched_image = Image.new('RGB', (total_width, total_height))
        previous = None
        part = 0

        for rectangle in rectangles:
            if previous is not None:
                driver.execute_script("window.scrollTo({0}, {1})".format(rectangle[0], rectangle[1]))
                if fixed_footer_loc:
                    remote_fixed_section(fixed_footer_loc)
                if fixed_header_loc:
                    remote_fixed_section(fixed_footer_loc)
                if fixed_header_loc or fixed_footer_loc:
                    time.sleep(0.1)

            screenshot = Image.open(io.BytesIO(driver.get_screenshot_as_png()))

            if rectangle[1] + viewport_height > total_height:
                offset = (rectangle[0], total_height - viewport_height)
            else:
                offset = (rectangle[0], rectangle[1])

            stitched_image.paste(screenshot, offset)

            del screenshot
            part = part + 1
            previous = rectangle

        driver.execute_script("window.scrollTo({0}, {1})".format(0, 0))
        time.sleep(.1)
        stitched_image.save(file_name)

    def select_multiple(self, select_element, select_values, raise_exception_if_value_missing=True):
        """ Select multiple values in a select box

        :param select_element: name, id or value to find the select element
        :param by: By.Name, By.XPATH, etc depending how you want to find the element
        :param tuple or list select_values: list of values to pick from the select box
        """

        element = self.get(select_element)
        s = Select(element)
        for v in select_values:
            try:
                s.select_by_value(v)
            except NoSuchElementException:
                if raise_exception_if_value_missing:
                    raise

    def maximize(self):
        self.driver.maximize_window()

    def get_inner_html(self, selector):
        """ gets the complete html content of the object defined as shown to the user
            (including any dynamically generated content)

        """
        return "".join([self.driver.execute_script("return arguments[0].innerHTML;", e)
                        for e in self.get_list(selector)])

    def get_inner_html_as_xml(self, selector, outer_node=None):
        """ gets the inner html and preparse it as an lxml object
        Returns:
            lxml.ElementTree
        """
        from lxml import html

        if outer_node:
            node_open = '<{}>'.format(outer_node)
            node_close = '</{}>'.format(outer_node)
        else:
            node_open = node_close = ''
        return html.fromstring(node_open + self.get_inner_html(selector) + node_close)

    def is_element_present(self, what, return_element=False):
        try:
            e = self.get(what)
            return e if return_element else True
        except NoSuchElementException as e:
            return None if return_element else False

    def is_element_present_and_displayed(self, what):
        e = self.is_element_present(what, True)
        return e.is_displayed() if e else False

    def _alert_accept_cancel(self, accept=True):
        """

        :param accept:
        :return:
        """

        try:
            alert = self.driver.switch_to.alert
            if accept:
                alert.accept()
            else:
                alert.dismiss()
        except NoAlertPresentException:
            log.debug('Alert is not present, so we are not doing any action')
            raise

    def alert_cancel(self):
        """ utility function to press cancel on alert if present

        """
        self._alert_accept_cancel(False)

    def alert_accept(self):
        """ utility function to press accept on alert if present

        """
        self._alert_accept_cancel(True)

    def switch_to_alert_if_present(self):
        try:
            return self.driver.switch_to.alert
        except NoAlertPresentException:
            return None

    def set_element_style(self, elem, style):
        if isinstance(elem, str):
            elem = self.get(elem)
        self.driver.execute_script("arguments[0].setAttribute('style', '{style}')".format(style=style), elem)

    def highlight_element_border(self, elem, color='orange', size=4):
        self.set_element_style(elem, 'border: {size}px solid {color};'.format(color=color, size=size))

    def turn_on_highlighted_find_elements(self, color=None, size=None):
        color = color or self._highlighting_color
        size = size or self._highlighting_size

        def highlight_element(elem):
            self.highlight_element_border(elem, color, size)
            time.sleep(self._highlighting_time)
            if self._screen_shot_highlights:
                self.get_screenshot()
            try:
                with self.without_wait():
                    self.set_element_style(elem, '')
            except Exception:
                pass

        def highlight_find_element(*args):
            elem = self._default_find_element_method(*args)

            highlight_element(elem)
            return elem

        def highlight_find_elements(*args):
            elems = self._default_find_elements_method(*args)

            for elem in elems:
                highlight_element(elem)

            return elems

        if self.driver:
            self.driver.find_element = highlight_find_element
            self.driver.find_elements = highlight_find_elements

    def turn_off_highlighted_find_elements(self):
        self.driver.find_element = self._default_find_element_method
        self.driver.find_elements = self._default_find_elements_method

    @contextlib.contextmanager
    def temp_no_highlight(self):
        was_highlighted = self._enable_highlighted_find_elements
        if was_highlighted:
            self.turn_off_highlighted_find_elements()
        try:
            yield
        finally:
            if was_highlighted:
                self.turn_on_highlighted_find_elements()

    @contextlib.contextmanager
    def temp_highlight(self):
        was_highlighted = self._enable_highlighted_find_elements
        if not was_highlighted:
            self.turn_on_highlighted_find_elements()
        try:
            yield
        finally:
            if not was_highlighted:
                self.turn_off_highlighted_find_elements()

    @contextlib.contextmanager
    def screenshot_before_after(self, file_name='', folder_path=''):
        """ gets a screen shot before and after a with context

        Args:
            file_name: name of file (it will be suffixed with _before and _after). if not given we will use the title of the page
            folder_path: folder path where to store the images

        Returns:

        """
        folder_path = folder_path or self.screen_shot_folder
        file_path = os.path.join(folder_path, file_name)

        self.get_screenshot(files.get_filename_suffixed(file_path, 'before'))
        yield
        self.get_screenshot(files.get_filename_suffixed(file_path, 'after'))

    def close_alert_and_get_its_text(self):
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        finally:
            self.accept_next_alert = True

    def move_mouse_to(self, selector, x=0, y=0, return_action_chain=False):
        e = selector if isinstance(selector, webelement.WebElement) else self.get(selector)
        ac = ActionChains(self.driver).move_to_element_with_offset(e, x, y)
        if return_action_chain:
            return ac
        else:
            ac.perform()

    def move_mouse_to_and_click(self, selector, x=0, y=0):
        """ good to click on offset elements like arrows in tree menus
            or when there is some kind of overlay that disappears when
            the mouse moves over an element
        """
        self.move_mouse_to(selector, x, y, return_action_chain=True).click().perform()

    def click_element(self, selector, default_by=None):
        self.get(selector, default_by=default_by).click()

    def bypass_wait(self):
        self.driver.implicitly_wait(0)

    def restore_wait(self):
        """ restores selenium implicit wait

        """
        self.driver.implicitly_wait(self.implicit_wait)

    @contextlib.contextmanager
    def using_frame(self, frame_selector):
        """  Utility to create a frame context to be used with "with". 
             The selector should always only find one item or this will break

        :param frame_selector:
        :param by:
        :return:
        """
        self.driver.switch_to.frame(self.get(frame_selector))
        yield
        self.driver.switch_to.default_content()

    def get_list(self, selector, no_highlight=False):
        """ find and return multiple elements

        Args:
            selector:

        Returns:

        """
        if isinstance(selector, WebElement):
            return [selector]
        else:
            if no_highlight:
                return self._default_find_elements_method(*loc.parse_selector(selector))
            else:
                return self.driver.find_elements(*loc.parse_selector(selector))

    def get_list_if_visible(self, selector, no_highlight=False):
        """ find and return multiple elements if they are currently displayed

        Args:
            selector:

        Returns:

        """
        l = self.get_list(selector, no_highlight=no_highlight)
        return [e for e in l if e.is_displayed()]

    @contextlib.contextmanager
    def temp_implicit_wait(self, wait):
        """ context utility to define a section to run with certain wait and then return to default implicit wait

        :return:
        """
        self.driver.implicitly_wait(wait)
        yield
        self.restore_wait()

    def without_wait(self):
        """ creates a context section where there is no implicit wait to be use inside a page that we know all elements
            will be there or when we want it to fail quickly

        :return:
        """
        return self.temp_implicit_wait(0)

    @contextlib.contextmanager
    def temp_think_time(self, think_time):
        """ context to set a think time different to default while in the context and return to old after """
        old_think_time = self.think_time
        self.set_think_time(think_time)
        yield
        self.set_think_time(old_think_time)

    # TODO: think of a better way to handle a long script as that is not possible with this
    def execute_script(self, script, will_return_value=False, wait_timeout=10, script_args=()):
        """ executes script and polls a local temporary variable to check its value """

        script = re.sub('^\s*(.+)[\n\s]*$', r'\1', script, flags=re.MULTILINE)  # shorten script str

        if will_return_value:
            script_var = 'window.__fdvar=undefined;window.__fdvar=' + script
            self.driver.execute_script(script_var)
            if not retry(wait_timeout, 1, retry_when=lambda x: x is True)(
                    self.driver.execute_script)("return (typeof window.__fdvar == 'undefined')"):
                val = self.driver.execute_script('return window.__fdvar')
                # clean/remove  variable
                try:
                    self.driver.execute_script('delete window.__fdvar')
                except Exception:
                    log.exception('problems deleting temp variable __fdvar in javascript')
                return val
        else:
            return self.driver.execute_script(script, *script_args)

    def execute_script_and_get_value(self, script, wait_timeout=10):
        return self.execute_script(script, True, wait_timeout)

    def check_jquery_availability(self, force_check=False, page_object=None):
        """ checks wheather jQuery is available already on the target site  """
        page = page_object or self
        if not page._jquery_checked or force_check:
            page._jquery_available = self.driver.execute_script("return (typeof jQuery != 'undefined');")
            page._jquery_checked = True
        return page._jquery_available

    def load_jquery(self, jquery_version=LATEST_JQUERY_GOOGLE_HOSTED, force_check=False, page_object=None):
        self.check_jquery_availability(force_check, page_object=page_object)
        page = page_object or self

        if page._jquery_available:
            return
        else:
            s = ("""function loadHeadElement(scriptUrl){
                        var head =  document.getElementsByTagName('head')[0];
                        var script = document.createElement('script');
                        var done = false;
                        script.type = 'text/javascript';
                        script.src = scriptUrl;
                        script.onload = script.onreadystatechange = (function() {
                            if (!done && (!this.readyState || this.readyState == 'loaded' || 
                                          this.readyState == 'complete')){
                                 done = true;
                                 script.onload = script.onreadystatechange = null;
                                 head.removeChild(script);
                                 callback();
                            }
                        });
                        head.appendChild(script);                       
                    };
                    loadHeadElement('https://ajax.googleapis.com/ajax/libs/jquery/{}/jquery.js');
                    return;
                   """.format(jquery_version))
            # flatten script
            # send removing spaces and new lines
            self.execute_script(''.join(s.strip() for s in s.splitlines()))
            retry(3, fail_silently=True)(self.check_jquery_availability)(True, page_object=page_object)


def _enter_text(elem, text, append=False, prepend=False, clear=True):
    """ enter text on an element found by its Name attribute.

    if there is no need to append or prepend then we just clear the text before inserting the new one
    """
    pre = app = u''

    if prepend:
        pre = elem.value()
    elif append:
        app = elem.value()
    if clear:
        elem.clear()
    elem.send_keys((pre + text + app))


################################################################################################
#            MONKEY PATCHING SELENIUM to use enter_text, get, [], findm, etc.
################################################################################################
webelement.WebElement.enter_text = _enter_text
webelement.WebElement.get = lambda self, item: self.find_element(*loc.parse_selector(item))
webelement.WebElement.__getitem__ = webelement.WebElement.get
webelement.WebElement.get_list = lambda self, item: self.find_elements(*loc.parse_selector(item))
webelement.WebElement.get_list_if_visible = lambda self, item: [e for e in self.get_list(item) if e.is_displayed()]
webelement.WebElement.__getattr__ = lambda self, item: self.get_attribute(item)
webelement.WebElement.select_by_value = lambda self, value: Select(self).select_by_value(value)
webelement.WebElement.select_by_visible = lambda self, value: Select(self).select_by_visible_text(value)

