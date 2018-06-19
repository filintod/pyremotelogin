import collections
import time

from fdutils.classes import log
from fdutils.files import seconds_to_hour_min_sec


class SimpleTimer:
    """  Simple non-threaded timer. To be used in a loop to check for time pass the timeout

    >>> with SimpleTimer(10) as t:
    >>>     print "my timer"

    """
    def __init__(self, timeout, raise_timeouterror=False):
        self.timeout = 0 if timeout is None else float(timeout)
        self.raise_exception = raise_timeouterror
        self.cancelled = self._timed_out = self.started = False
        self._loop_started = False
        if self.timeout < 0:
            raise ValueError

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.raise_exception and self.has_expired:
            pass
        self.cancel()

    def __str__(self):
        return '<fdutils.SimpleTimer - timeout: {} {}>'.format(self.timeout, ' - will raise Exception' if self.raise_exception else '')

    def start(self, force=False):
        if self.started and not force:
            raise Exception('Trying to start the timer but it was already started before')

        if self.timeout:
            self.cancelled = self._timed_out = self._loop_started = False
            self.started = True
            self.start_time = time.time()
            log.debug('Starting timer {} with timeout {}'.format(str(self), self.timeout))
        else:
            log.debug('Timeout is 0 so we are not executing any timingout operation')
        return self

    def restart(self):
        self.reset()
        return self.start()

    def reset(self):
        self.start_time = time.time()
        log.debug('Resetting timer {} with timeout {}'.format(str(self), self.timeout))

    def cancel(self):
        if not (self._timed_out or self.has_expired):
            self.cancelled = True
            self._timed_out = self.started = False
            log.debug('Cancelling timer ' + str(self))
        # we don't do anything if it was already timed out

    @property
    def has_not_expired(self):
        if self.cancelled:
            return False
        return not self.has_expired

    @property
    def has_expired(self):
        if self._timed_out:
            return True

        elif self.cancelled:
            return False

        elif self.started and not self.cancelled:
            self._timed_out = (time.time() - self.start_time) > self.timeout
            if self.raise_exception and self._timed_out:
                raise TimeoutError

        return self._timed_out

    def run_and_sleep(self, sleep_timeout, sleep_on_enter=False):
        """ utility method to use in while loops like while timer.run_and_sleep()
            it will introduce a sleep before continue with the loop"""
        if not self.started:
            self.start()

        if not self.has_expired:
            if sleep_on_enter or self._loop_started:
                time.sleep(sleep_timeout)
            else:
                self._loop_started = True

    def sleep_and_run(self, sleep_timeout):
        return self.run_and_sleep(sleep_timeout, True)

    def time_so_far(self, easy_read=False):
        """ time waited so far. if td is set to True, it will return a timedelta object for easy conversion

        """
        so_far = time.time() - self.start_time
        if easy_read:
            return seconds_to_hour_min_sec(so_far)
        return so_far


def check_until(func_to_check, timeout, check_interval):
    with SimpleTimer(timeout) as timer:
        while not (func_to_check() or timer.has_expired):
            time.sleep(check_interval)


class Chronometer:
    """ utility to get timing info of running sections

    """
    def __init__(self, start=False, start_tag=''):
        self.time_points = list()
        if start:
            self.start(start_tag)

    def _add_point(self, tag, action):
        # don't add redundant tags
        if action != 'cont' and len(self.time_points) and self.time_points[-1][2] == action:
            return
        self.time_points.append((tag if tag else ('t' + str(len(self.time_points))), time.time(), action))

    def add_point(self, tag=''):
        # if we have not started or last tag was a stop then start it
        if not len(self.time_points) or self.time_points[-1][2] == 'stop':
            self.start(tag)
        else:
            self._add_point(tag, 'cont')

    def stop(self, tag=''):
        # don't add stop if you have not started
        if len(self.time_points):
            self._add_point(tag, 'stop')

    def start(self, tag=''):
        self._add_point(tag, 'start')

    def restart(self, tag=''):
        self.clear()
        self.start(tag)

    def clear(self):
        self.time_points = list()

    def results(self, stop=True):
        if stop:
            self.stop()
        res = collections.OrderedDict()
        for i in range(len(self.time_points) - 1):
            (tag, t, action) = self.time_points[i]
            res[tag] = self.time_points[i + 1][1] - t
        return res

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def get_timer_from_timeout(timeout):
    """ helper function for _expect_cmd """
    if hasattr(timeout, 'has_expired'):
        timer = timeout
    else:
        timer = SimpleTimer(timeout)

    if not timer.started:
        timer.start()

    return timer