import functools

import fdutils as utils
from fdutils.selenium_util.settings import MAX_LENGTH_FUNCTION_NAME_TO_RECORD


def path(expected_path):
    """ decorator to get to the relative page given and check that we have landed on it 
        before calling the decorated function

    :param expected_path:
    :return:
    """
    def get_final_path(websvc):
        new_path = websvc.url

        if expected_path[0] != '/' and websvc.url[-1] != '/':
            return new_path + '/' + expected_path
        return new_path + expected_path

    def deco(f):
        @functools.wraps(f)
        def w(sel_util, *args, **kwargs):

            final_path = get_final_path(sel_util)

            sel_util.open_url(final_path)

            if sel_util.driver.current_url != final_path:
                raise Exception('Wrong current path (expected= {}  - current= {})!!!'
                                ''.format(final_path, sel_util.driver.current_url))
            else:
                return f(sel_util, *args, **kwargs)
        return w

    return deco


def based_path(base):
    def pathf(expected_path):
        return path(base + expected_path)

    return pathf


without_highlight = utils.decorators.context_decorator('temp_no_highlight')
without_wait = utils.decorators.context_decorator('without_wait')


def with_screen_shot(before=True, after=True, name_to_use=''):
    """ decorator to retrieve the screen shot at the beginning and end of the called method.
        This decorator should be used only on Site instance methods or it will raise an Exception

    There are two hidden kwargs that can be passed to alter the behavior of this decorator on running time:
        get_screen_shot: flag to tell the system to get the shot even if there is no test attached to it
        name_to_use_for_shot: string to be used for the name (appended to the timestamp) instead of the function name

    :param before: flag to indicate that we want a shot before the function
    :param after: flag to indicate that we want a shot after the function
    :return:
    """

    def function_deco(f):
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):

            name_for_shot = kwargs.pop('name_to_use_for_shot', name_to_use)
            f_name = name_for_shot if name_for_shot else f.__name__[:MAX_LENGTH_FUNCTION_NAME_TO_RECORD]

            if before:
                self.get_screenshot('before_' + f_name, True)

            ret = f(self, *args, **kwargs)

            if after:
                self.get_screenshot('after_' + f_name, True)

            return ret

        return wrapper

    return function_deco