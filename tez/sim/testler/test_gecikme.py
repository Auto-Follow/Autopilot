"""Capture -> PX4 delay line, part 1 (task group 5): the order is kept and every message gets its release stamp.
The artificial delay, its jitter and the clock model of the sent time stamps follow in task group 12."""

import threading
import time

import pytest

import gecikme


def test_messages_leave_in_order_no_earlier_than_their_delay() -> None:
    out: list[tuple[str, float, str]] = []
    line = gecikme.DelayLine(lambda item, serbest: out.append((item, serbest, threading.current_thread().name)))

    now = time.monotonic()
    line.put("a", now)  # no delay and nothing waiting: leaves at once, in the caller's thread
    assert out == [("a", pytest.approx(now, abs=0.05), threading.current_thread().name)]

    start = time.monotonic()
    line.put("b", start, extra_ms=60.0)
    line.put("c", start, extra_ms=0.0)  # ready earlier than "b" but must not overtake it
    line.put("d", start + 0.07, extra_ms=10.0)
    line.close()
    assert [item for item, *_ in out] == ["a", "b", "c", "d"]
    released = {item: serbest for item, serbest, _ in out}
    assert released["b"] >= start + 0.060 and released["c"] >= released["b"]
    assert released["d"] >= start + 0.080
    assert line.pending == 0
    with pytest.raises(RuntimeError):
        line.put("e", time.monotonic())
