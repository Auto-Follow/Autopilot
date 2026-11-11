"""Capture -> PX4 delay line of the simulation (spec 2026-11-10-m06-sim-ortami, 4.).

Every TEZ_LOS message passes through one DelayLine between the tracking thread and the MAVLink link. A message leaves
no earlier than its ready time plus its extra delay and never before the message put in ahead of it: the order is
kept like on a real serial link, where a late message holds up the ones behind it. The moment it leaves is its release
stamp (serbest), so the extra delay is measured, not assumed.

Part 1 (task group 5): the line and the release stamp; every run has no extra delay (gecikme.ek_ms 0; other values are
refused before the simulation starts until task group 12 wires them in together with the jitter and the clock model
of the sent time stamps). With no delay and nothing waiting, a message leaves at once in the caller's thread: no extra
thread hop on the path whose latency is being measured.
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable

CLOSE_TIMEOUT = 5.0  # [s] for the waiting messages to leave when the line is closed


class DelayLine:
    """put() from one producer thread; deliver(item, serbest) runs in that thread when the message can leave at once,
    else in the line's own thread, always in the order of put()."""

    def __init__(
        self,
        deliver: Callable[[object, float], None],
        extra_ms: float = 0.0,
        clock: Callable[[], float] = time.monotonic,
        name: str = "tez-gecikme",
    ) -> None:
        """deliver: sends one message (item, release time [s, `clock`]); extra_ms [ms]: default delay of a message;
        clock: monotonic wall clock [s] of the ready and release times."""
        self.extra_ms = extra_ms
        self._deliver = deliver
        self._clock = clock
        self._name = name
        self._cond = threading.Condition()
        self._queue: deque[tuple[float, object]] = deque()  # (due time, item); the head stays until it is delivered
        self._last_due = -math.inf
        self._closed = False
        self._thread: threading.Thread | None = None

    @property
    def pending(self) -> int:
        """Messages waiting in the line (the one being delivered by the line's thread included)."""
        with self._cond:
            return len(self._queue)

    def put(self, item: object, ready: float, extra_ms: float | None = None) -> None:
        """Send `item`, ready at `ready` [s, clock], after `extra_ms` [ms] (None: the line's delay) and never before
        the message put in ahead of it. RuntimeError after close()."""
        delay = self.extra_ms if extra_ms is None else extra_ms
        with self._cond:
            if self._closed:
                raise RuntimeError("gecikme hattı kapalı")
            due = max(ready + delay / 1000.0, self._last_due)
            self._last_due = due
            if self._queue or due > self._clock():
                self._queue.append((due, item))
                if self._thread is None:
                    self._thread = threading.Thread(target=self._run, name=self._name, daemon=True)
                    self._thread.start()
                self._cond.notify_all()
                return
        self._deliver(item, self._clock())

    def _run(self) -> None:
        while True:
            with self._cond:
                while True:
                    if self._queue:
                        due, item = self._queue[0]
                        wait = due - self._clock()
                        if wait <= 0:
                            break
                        self._cond.wait(wait)
                    elif self._closed:
                        return
                    else:
                        self._cond.wait()
            try:
                self._deliver(item, self._clock())
            finally:
                with self._cond:  # removed only now: a put() meanwhile queues behind it instead of overtaking it
                    self._queue.popleft()
                    self._cond.notify_all()

    def close(self, timeout: float = CLOSE_TIMEOUT) -> None:
        """Let the waiting messages leave (at most `timeout` [s]), then refuse new ones. Repeatable."""
        with self._cond:
            self._closed = True
            self._cond.notify_all()
            thread = self._thread
        if thread is not None:
            thread.join(timeout)
