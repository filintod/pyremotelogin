import pytest
import time
from fdutils.timer import SimpleTimer


def test_simple_timer_zero():
    s = SimpleTimer(0)
    assert not s.has_expired
    assert s.has_not_expired

def test_simple_timer_value():
    s = SimpleTimer(0.5).start()
    t0 = time.time()
    while s.has_not_expired:
        time.sleep(0.1)
    assert 0.6 > time.time() - t0 > 0.5
    assert s.has_expired

def test_simple_timer_cancel():
    s = SimpleTimer(0.5).start()
    s.cancel()
    assert s.cancelled
    assert not s.has_not_expired
    assert not s.has_expired
    assert not s.started

def test_simple_timer_reset_restart():
    s = SimpleTimer(0.5).start()
    time.sleep(.4)
    s.cancel()
    assert s.cancelled

    s.reset()
    s.start()
    time.sleep(.45)
    s.cancel()
    assert s.cancelled

    s.restart()
    time.sleep(.45)
    s.cancel()
    assert s.has_not_expired

def test_simple_timer_raise_TimeoutError():
    s = SimpleTimer(0.5, raise_timeouterror=True).start()

    with pytest.raises(TimeoutError):
        while s.has_not_expired:
            time.sleep(0.1)

def test_simple_timer_is_running():
    s = SimpleTimer(0.5)
    assert not s.is_running
    s.start()
    assert s.is_running
    s.cancel()
    assert not s.is_running
    assert s.is_not_running

    s.restart()
    while s.has_not_expired:
        time.sleep(0.1)
    assert s.is_not_running
