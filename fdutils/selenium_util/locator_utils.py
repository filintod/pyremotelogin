import functools
import logging
from functools import partial

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from fdutils import xpathbuilder as xp
from fdutils.decorators import context_if
from fdutils.strings import is_string_formatted

log = logging.getLogger(__name__)


_RAW_LOCATORS = []


def locator_or_string(no_wait=False, no_highlight=False):
    def deco(f):
        """ decorator to provide an alternative to a locator to return either raw string or a locator object """
        _RAW_LOCATORS.append(f)
        @functools.wraps(f)
        def w(*args, **kwargs):
            as_str = kwargs.pop('as_str', False)
            _raw = f(*args, **kwargs)
            return _raw if as_str else locator(_raw, no_wait, no_highlight)
        return w
    return deco


def add_str_to_raw_locators(module_name):
    """ adds a suffix "_str" to all raw locators in a module
     
        This way if we want a string for locator x we can call x_str() instead of x(as_str=True).

        From the module where your you want to call it like:
        
            add_str_to_raw_locators(__name__)
    """
    import sys
    m = sys.modules[module_name]
    for f in [l for l in dir(m) if l in [f.__name__ for f in _RAW_LOCATORS]]:
        setattr(m, f + '_str', partial(getattr(m, f), as_str=True))


class ParameterizedLocator:
    def __init__(self, site_locator_instance, sel_util):
        self.sl = site_locator_instance
        self.sel_util = sel_util

    def __call__(self, *args, **kwargs):
        return self.sl.context_find(self.sel_util, self.sl.locator_value.format(*args, **kwargs))

    def __getitem__(self, item):
        if isinstance(item, slice):
            return [self.sl.context_find(self.sel_util, self.sl.locator_value.format(i))
                    for i in range(item.start, item.stop, item.step)]
        else:
            return self.sl.context_find(self.sel_util, self.sl.locator_value.format(item))


class site_locator:
    """ lazy evaluated class descriptor for locators evaluated every time it is called (no caching in this method).

    """

    def context_find(self, site_self, locator_value):
        """ puts context around execution of find element """
        with context_if(self.no_highlight, site_self.temp_no_highlight):
            with context_if(self.is_safe, site_self.without_wait):
                return site_self.driver.find_element(self.locator_by, locator_value)

    def __init__(self, by, value, no_wait=False, no_highlight=False):
        self.locator_by, self.locator_value = by, value
        self.is_safe = no_wait
        self.no_highlight = no_highlight

    def __get__(self, site_self, cls):
        if site_self is None or site_self.driver is None:
            return None
        try:
            if is_string_formatted(self.locator_value):
                return ParameterizedLocator(self, site_self)
            else:
                return self.context_find(site_self, self.locator_value)

        except NoSuchElementException:
            return None

    def __set__(self, site_self, value):
        try:
            self.__get__(site_self, None).enter_text(value)
        except AttributeError:
            log.exception('problems settings value on locator')


def parse_selector(t, default_by=None):
    """ simplify defining selectors for find operations by using simple strings

    :param t:
    :return:
    """

    if not isinstance(t, str):
        return t

    t = str(t)

    # By Name
    if t.startswith('name='):
        return By.NAME, t[len('name='):]
    elif t.startswith('n='):
        return By.NAME, t[2:]

    # By CSS
    elif t.startswith('.'):
        return By.CLASS_NAME, t[1:]
    elif t.startswith('css='):
        return By.CSS_SELECTOR, t[4:]
    elif t[0] in ('#', '>', '*', ':', '['):
        return By.CSS_SELECTOR, t
    elif t.startswith('id='):
        return By.ID, t[3:]

    # By Link value
    elif t.startswith('link='):
        return By.LINK_TEXT, t[5:]
    elif t.startswith('plink='):
        return By.PARTIAL_LINK_TEXT, t[6:]
    elif t.startswith('a='):
        return By.LINK_TEXT, t[2:]

    # By XPATH
    elif t.startswith('xp='):
        return By.XPATH, t[3:]
    elif t.startswith('xpath='):
        return By.XPATH, t[6:]
    elif t.startswith('/') or t.startswith('(/'):
        return By.XPATH, t

    # By Tag Name
    elif t.startswith('tag='):
        return By.TAG_NAME, t[4:]
    elif t.startswith('t='):
        return By.TAG_NAME, t[2:]

    elif default_by:
        return default_by, t
    else:
        raise AttributeError('unknown value ({}) to guess selector'.format(t))


def locator(locator_str, no_wait=False, no_highlight=False):
    """ creates site_locator object from the locator_str
     If the locator_str contains formatting expected arguments ({})
     then the locator will be a parameterized_locator that you will need to pass the parameter when called
    """
    by, value = parse_selector(locator_str)
    return site_locator(by, value, no_wait, no_highlight)


def _encode_label(label, as_str, insensitive):
    if not as_str and not label.startswith('(?i)') and insensitive:
        label = '(?i)' + label
    return label


def get_label_locator(label, insensitive=False, as_str=False):
    return xp.all()._text.startswith(_encode_label(label, as_str, insensitive))


@locator_or_string()
def input_x_by_label(label, input_type=None, preceded=True, indexed=False, insensitive=False, as_str=False):
    """

    Args:
        label: value to match the label before/after input element. if label is prefix with (?i) the match will be case
               insensitive
        input_type: type of input
        preceded: flag to indicate that the label is before the input
        indexed: flag to indicate that we want to crate an indexed locator that can then be use as locator[1]
        insensitive: flag to indicate we want to check the label with insensitive case.
                     you can also use (?i) in the label to do the same
        as_str: flag to indicate we just want the string of the locator instead of a full locator object

    Returns:

    """
    p_locator = label_before if preceded else label_after
    return p_locator(_encode_label(label, as_str, insensitive))('input')(type=input_type).render() +\
           ('[{}]' if indexed else '[1]')


@locator_or_string()
def button(value='', indexed=False, insensitive=True, type='submit', after=None,  **attr):
    #attr = {k: _encode_label(v, as_str, insensitive) for k,v in attr.items()}

    if type == 'submit':
        after = after.next_input if after else xp.all_input
        button = after._type('submit')
    else:
        button = after.next_button if after else xp.all_button

    if value:
        button = button._value(('&' if insensitive else '') + value)

    return button(**attr).render() + ('[{}]' if indexed else '[1]')


def label_before(label, insensitive=False, as_str=False):
    return get_label_locator(label, insensitive, as_str).next


def label_after(label, insensitive=False):
    return get_label_locator(label, insensitive).previous


password_input = partial(input_x_by_label, input_type='password')
text_input = partial(input_x_by_label, input_type='text')

checkbox = partial(input_x_by_label, input_type='checkbox', preceded=False)
checkbox_after = partial(input_x_by_label, input_type='checkbox')

radio = partial(input_x_by_label, input_type='radio', preceded=False)
radio_button = radio
radio_after = partial(input_x_by_label, input_type='radio')
radio_button_after = radio_after

text_input_indexed = partial(input_x_by_label, input_type='text', indexed=True)

file_input = partial(input_x_by_label, input_type='file')