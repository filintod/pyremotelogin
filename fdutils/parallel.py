import fdutils
import threading
import time
import logging
import queue
from io import StringIO, BytesIO

log = logging.getLogger(__name__)

# TODO: Maybe Switch to AsyncIO or Curio (https://github.com/dabeaz/curio) or Trio (https://github.com/python-trio/trio)

POISON_PILL = None


class ThreadLoop(threading.Thread):

    def __init__(self, target, args=(), kwargs=None, stop_switch=None, run_timeout=0, join_timeout=None,
                 sleep_time_between_execution=0, call_on_stop=None, **thread_kwargs):
        """ An implementation of a thread loop with several (optional) stop triggers stop_switch provided by caller
            and run_timeout (creates another thread Timer that will set the stop switch when finished)

            This is a helper instead of having to write our own loop with a stop switch event via stop_switch
            if you don't provide one.  The target function SHOULD NOT block and can return a value even though this
            is discarded unless we use the ThreadLoopWithQueue below.

        Args:
            target (types.FunctionType): a NON-BLOCKING function to call. Different to usual target functions this function
                                         SHOULD NOT have a forever loop as we are implementing it here. The function
                                         should return a value if we are using the ThreadLoopWithQueue or we will
                                         be inserting None all the time into the Queue
            args (list or tuple): list of arguments to pass to target function
            kwargs (dict): dictionary to pass to target function
            stop_switch (threading.Event): an event switch to kill thread
            run_timeout (float): timeout if given to run the thread for
            join_timeout (float): timeout for join
            sleep_time_between_execution (float): the main loop executed in run will wait this time between calling
                                                  the target function
            call_on_stop (list of tuples(target, args, kwargs)): if provided this will be a list of functions to call
                                                                 after the thread has stopped
        """
        thread_kwargs.setdefault('daemon', True)
        super(ThreadLoop, self).__init__(target=target, args=args, kwargs=kwargs, **thread_kwargs)
        self.stop_switch = stop_switch or threading.Event()

        self.stop_after_timer = threading.Timer(run_timeout, self._timeout_stop) if run_timeout else None
        self.join_timeout = join_timeout
        self.sleep_time_between_executions = sleep_time_between_execution
        self._execution_timeout = threading.Event()
        self._lock = threading.Lock()
        self._call_on_stop = fdutils.lists.to_sequence(call_on_stop)
        self.call_on_stop_finished = threading.Event()

    @property
    def stop_after_secs(self):
        return self.stop_after_timer.interval if self.stop_after_timer else None

    @stop_after_secs.setter
    def stop_after_secs(self, stop_after):
        self.stop_after_timer.interval = stop_after if self.stop_after_timer else None

    def should_stop(self):
        return self.stop_switch.is_set()

    def run(self):
        self._execution_timeout.clear()

        if self.stop_after_secs:
            if self.daemon:
                self.stop_after_timer.setDaemon(True)
            self.stop_after_timer.start()

        try:
            while not self.should_stop():
                self._run_target()
                if self.sleep_time_between_executions:
                    time.sleep(self.sleep_time_between_executions)
        finally:
            # from threading.Thread.run:

            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self._target, self._args, self._kwargs

        self.cancel_timers()

    def _run_target(self):
        return self._target(*self._args, **self._kwargs)

    def join(self, **kwargs):
        kwargs.setdefault('timeout', self.join_timeout)
        super(ThreadLoop, self).join(**kwargs)

    def stop(self):
        self.stop_switch.set()
        self.cancel_timers()
        if self._call_on_stop:
            self.join()
            try:
                exceptions = []
                for (target, args, kwargs) in self._call_on_stop:
                    try:
                        target(*args, **kwargs)
                    except Exception as e:
                        exceptions.append(e)
                if any(exceptions):
                    raise Exception('Problems with one or more of the methods called at stop') from exceptions[0]
                self.call_on_stop_finished.set()
            except Exception:
                log.exception('problems while executing callback on stop. Execution will continue')

    def add_call_on_stop(self, target, args=(), kwargs=None):
        kwargs = kwargs or {}
        self._call_on_stop.append((target, args, kwargs))

    def _timeout_stop(self):
        self._execution_timeout.set()
        self.stop()

    def cancel_timers(self):
        if self.stop_after_timer:
            self.stop_after_timer.cancel()


class ThreadLoopWithMultipleStopSwitches(ThreadLoop):

    def __init__(self, target, other_stop_switches=None, **kwargs):
        super().__init__(target, **kwargs)
        self._other_stop_switches = fdutils.lists.to_sequence(other_stop_switches) if other_stop_switches else []

    def add_stop_switch(self, e):
        self._other_stop_switches.append(e)

    def should_stop(self):
        return super().should_stop() or any(e.is_set() for e in self._other_stop_switches)


class ThreadLoopWithQueue(ThreadLoop):
    """ A stoppable thread loop with a Queue to receive data from the target function. We add another
        way to stop the thread by checking for a POISON_PILL in the queue.
    """

    def __init__(self, target, args=(), kwargs=None, q=None, recv_data_timeout=0,
                 sleep_timeout_when_no_data=0.001, text_queue=True, keep_copy=False, **thread_kwargs):
        """

        Args:
            q (queue.Queue): a queue provided or we would create one
            recv_data_timeout (float): a time to wait
            sleep_timeout_when_no_data:
            text_queue:
            **thread_kwargs:
        """

        super(ThreadLoopWithQueue, self).__init__(target, args=args, kwargs=kwargs, **thread_kwargs)
        self.queue = q or queue.Queue()
        self._is_text = text_queue
        if keep_copy:
            self.get_data = self._get_data_copy
            self._queue_data_copy = StringIO() if text_queue else BytesIO()
        else:
            self.get_data = self._get_data
            self._queue_data_copy = None
        self.recv_data_timeout = recv_data_timeout
        self.sleep_timeout_when_no_data = sleep_timeout_when_no_data

    def _run_target(self):
        start_time = time.time()
        while True:
            try:
                data = super()._run_target()
                if data == POISON_PILL:
                    self.stop()
                    break
                elif data:
                    self.queue.put(data)
            except queue.Empty:
                time.sleep(self.sleep_timeout_when_no_data)
                break

            if self.should_stop() or (self.recv_data_timeout and (time.time() - start_time) > self.recv_data_timeout):
                break

    def _get_data_copy(self, all=False):
        try:
            while True:
                self._queue_data_copy.write(self.queue.get_nowait())
        except queue.Empty:
            pass

        if all:
            return self._queue_data_copy.getvalue()
        else:
            return self._queue_data_copy.read()

    def _get_data(self, all=False):
        data = []

        try:
            while True:
                data.append(self.queue.get_nowait())
        except queue.Empty:
            pass

        if self._is_text:
            return ''.join(data)
        else:
            return b''.join(data)

    def get_all_data(self):
        return self.get_data(True)