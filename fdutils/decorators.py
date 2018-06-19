import contextlib
import functools
import time
from datetime import datetime
from functools import wraps

import fdutils.timer
from fdutils.exceptions import RetriesExceededError, CapabilityError
from fdutils import lists, classes

__author__ = 'Filinto Duran (duranto@gmail.com)'

import logging
log = logging.getLogger(__name__)

THREADING_EXEC_ASYNC_IS_DAEMON = True


def execute_at(server_ip):
    """ decorator to execute command on remote server
    """
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):

            return f(*args, **kwargs)
        return wrapper
    return deco


def delay(d, after=0):
    """ decorator to add a delay before an action. A delay after is also added If after is given.
    :param float d: delay to add before in seconds
    :param float after: delay to after the action in seconds

    """
    before = abs(d)
    after = abs(after)

    def deco_delay(func):
        @wraps(func)
        def f(*args, **kwargs):
            bef_local = before
            time.sleep(bef_local)
            ret = func(*args, **kwargs)
            if after:
                bef_local = after
            time.sleep(bef_local)
            return ret
        return f
    return deco_delay


# rename from six library: https://github.com/JioCloud/python-six/blob/master/six.py reraise function
def reraise(exception_type, exception_instance, traceback=None):

    if exception_instance is None:
        exception_instance = exception_type()

    if exception_instance.__traceback__ is not traceback:
        raise exception_instance.with_traceback(traceback)

    raise exception_instance


def retry(tries, delay=3, backoff=1, exceptions_to_check=(Exception,), exceptions_to_not_retry=(),
          retry_when=None, retries_timeout=0,
          function_timeout=0, fail_silently=False, return_value_when_fail_silent=None,
          exception_to_raise_when_fail=None, raise_last_exception_when_fail=True, max_delay=None,
          f=None, args=(), **kwargs):
    """ Retry decorator function that will retry the decorated function for the number of 'tries' waiting 'delay'
        between retries and increasing 'delay' by the 'backoff' value multiplier, when an exception occurs if
        exceptions_to_check matches the exception is true or if retry_when is check and the lambda function
        returns true. If the number of retries is exceeded we will raise an exception unless we have retry_for check
        and the return value (not the lambda) has a value other than None (i.e. False, '', etc, will be returned)

     :param int tries: number of times to try the decorated function
     :param float delay: time to wait before retrying
     :param int backoff: exponential backoff if more than 1
     :param tuple of Exception exceptions_to_check:  tuple or single list of exceptions that we will allow to
                                                    continue retrying if an exception is raised and not one of the tuples
                                                    the retry will stop and raise the exception
     :param retry_when: a lambda or function that if return true will make the function to be retried
     :param float retries_timeout: if not 0, it will be the maximum amount of time that we will retry the
                                   function and the retries. i.e. tries = 20 but retries_timeout = 60,
                                   retries_timeout might be reach before retries reache 20
     :param float function_timeout: if not 0, it will be the maximum amount of time that we will let the function run
                                    on every retry. One needs to have a finally statement if we are dealing with file
                                    handlers or sockets to properly close them.
     :param bool fail_silently: flag that if True indicates that a failure to execute the command after the given
                                retries should not raise an exception
     :param bool raise_last_exception_when_fail: flag to indicate to raise the last exception caught instead of
                                                 RetriesExceededError when retries are more than max
     :param function f: a function to call. If this is not None this will be similar to retry()(f)(*args, **kwargs)
     :param list or tuple args: arguments to pass to f when using retry not as decorator but like a function
     :raise: RetriesExceededException: if it has retry more than 'tries' times with exceptions being raise

     >>> # retry my_function up to three times waiting 30 seconds the first time, 60 seconds the 2nd time and 120 seconds the 3rd
     >>> from fdutils.decorators import retry
     >>> @retry(3, delay=30, backoff=2)
     >>> def my_function():
     >>>     print 'done'

     >>> # retry my_function up to three times waiting 30 seconds every time there is a wardrobe_malfunction_exception when executing it
     >>> from fdutils.decorators import retry
     >>> @retry(3, delay=30, backoff=1, exceptions_to_check=wardrobe_malfunction_exception)
     >>> def my_function()...

      # another way to call retry in an inline way instead that is useful inside another function
      retry(3, delay=30, backoff=1)(my_function)(*my_function_args, **my_function_kwargs)

    Args:
        return_value_when_fail_silent:
        exception_to_raise_when_fail:
        exception_to_raise_when_fail:

    """
    start_time = datetime.now()

    if backoff < 1:
        raise ValueError("backoff must be greater than 1")

    tries = int(tries)
    if tries <= 0:
        raise ValueError("tries must be greater than 0")

    if delay <= 0:
        raise ValueError("delay must be greater than 0")

    if f is not None:
        # we are not using it as a decorator but as a function
        return retry(tries, delay, backoff, exceptions_to_check, exceptions_to_not_retry, retry_when, retries_timeout,
                     function_timeout, fail_silently, return_value_when_fail_silent, exception_to_raise_when_fail,
                     raise_last_exception_when_fail, max_delay)(f)(*args, **kwargs)

    exceptions_to_check = lists.to_sequence(exceptions_to_check, list)
    if function_timeout:
        exceptions_to_check.append(TimeoutError)
    exceptions_to_check = tuple(exceptions_to_check)

    if return_value_when_fail_silent is not None:
        fail_silently = True

    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            remaining_tries, _delay, _start_time = tries, delay, start_time   # make enclosed variables mutable
            return_value = original_exception = exc_info = None

            with fdutils.timer.SimpleTimer(retries_timeout) as retries_timer:

                while remaining_tries > 0 and not retries_timer.has_expired:

                    return_value = original_exception = exc_info = None

                    try:

                        with fdutils.timer.SimpleTimer(function_timeout, raise_timeouterror=True):
                            # Here we finally call the real function with the respective arguments
                            return_value = f(*args, **kwargs)

                        # did not get an exception but check if we have a function to call first
                        if not (retry_when and retry_when(return_value)):
                            # everything pass, return value
                            return return_value

                        else:
                            error = 'We will retry as the Lambda/Function was True for ' + str(return_value)

                    except exceptions_to_check as original_exception:

                        # is exception instance of one defined not to be retried
                        if any([isinstance(original_exception, exc) for exc in exceptions_to_not_retry]):
                            raise

                        else:
                            # store exception in case we need to return it
                            import sys
                            exc_info = sys.exc_info()
                            log.exception('>>Retry Failed<<')
                            error = original_exception

                    remaining_tries -= 1
                    if remaining_tries > 1:

                        msg = "{}.\nRetrying {}/{} in {} seconds...".format(str(error), (tries - remaining_tries),
                                                                            tries, _delay)
                        log.warning(msg)
                        time.sleep(_delay)

                        _delay *= backoff
                        if max_delay is not None and 0 < max_delay < _delay:
                            _delay = max_delay

            log.error('Ran out of retries in ' + f.__name__)

            if retry_when and return_value is not None and exc_info is not None:

                log.debug('We are returning a value {} as we are checking against a lambda/function and the '
                          'value is not None'.format(str(return_value)))
                return return_value

            if exc_info is not None and not fail_silently:

                if raise_last_exception_when_fail and exc_info:
                    reraise(*exc_info)

                elif exception_to_raise_when_fail:
                    raise exception_to_raise_when_fail

                else:
                    raise RetriesExceededError(tries, exc_info) from original_exception    # Ran out of tries :-(

            else:
                log.debug('Retries Exceeded but bypassing raising exception per silent_failure flag given '
                          'to retry function method was set to fail silently...')

                return return_value_when_fail_silent

        return f_retry

    return deco_retry


def retry_for_minutes(minutes, retry_every_secs, **kwargs):
    """ a retry decorator that execute a given function a maximum time in minutes and retry every amount of seconds

    """
    tries = int(minutes * 60 / retry_every_secs)
    return retry(tries, delay=retry_every_secs, backoff=1, retries_timeout=int(60 * minutes), **kwargs)


def retry_and_fail_silent(*args, **kwargs):
    kwargs.setdefault('fail_silently', True)
    return retry(*args, **kwargs)


def retry_when(tries, when, *args, **kwargs):
    if not callable(when):
        raise TypeError("when parameter should be a function or lambda")
    kwargs.setdefault('retry_when', when)
    return retry(tries, *args, **kwargs)


def try_silent(return_value=None, expected_exception=Exception):
    """ try a function and if fail do not raise exception. use cautiously

    :return:
    """
    def real_function(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except expected_exception:
                log.exception('Function Error was executed and failed silently')
                return return_value
        return wrapper
    return real_function


def capable_of(capability, continue_if_not_capable=False):
    """ functionality capability decorator on classes that has WithCapabilities mixin

    """
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if args[0].is_not_capable_of(capability):
                if continue_if_not_capable:
                    return None
                else:
                    raise CapabilityError(capability)
            return f(*args, **kwargs)
        return wrapper
    return deco


def timeit(f):
    """ decorator function to time execution of some method and log the time on the log sink

    """

    def timed(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        total_time = time.time() - ts

        log.debug('Total Time to Execute {}: {} seconds'.format(f.__name__, total_time))

        return total_time, result

    return timed


class lazy_property:
    """ meant to be used for lazy evaluation of an object attribute. property should represent non-mutable data,
        as it replaces itself (the __get__ is not call again).
    """

    def __init__(self, fget):
        self.fget = fget
        self.func_name = fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return None
        value = self.fget(obj)
        setattr(obj, self.func_name, value)
        return value


@contextlib.contextmanager
def context_if(flag, context_func, *context_func_args, **context_func_kwargs):
    """ sets a context around a statement if the flag is true
        
        you would called it like:
        
            with context_if(flag, context):
                my_function()
    
    """

    if flag:
        with context_func(*context_func_args, **context_func_kwargs):
            yield
    else:
        yield


def is_instance_of_context_mgr(obj):
    return hasattr(obj, '__enter__') and hasattr(obj, '__exit__')


def context_decorator(method_name_or_func, func_before=None, func_after=None):
    """ decorates a function with a context given by a method of the object where this is applied to
        or by a func
    """
    if not (isinstance(method_name_or_func, str) or is_instance_of_context_mgr(method_name_or_func)):
        raise TypeError('the method or name provided ({}) is not a string or ContextManager'
                        ''.format(method_name_or_func))

    def _context_decor(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            self = f.__self__ if hasattr(f, '__self__') and f.__self__ else args[0]
            with getattr(self, method_name_or_func)():
                if func_before is not None:
                    func_before()

                ret = f(*args, **kwargs)

                if func_after is not None:
                    func_after()

                return ret

        return wrapper
    return _context_decor
