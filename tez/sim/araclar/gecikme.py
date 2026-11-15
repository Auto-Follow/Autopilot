"""Capture -> PX4 delay line of the simulation and the clock model of the sent time stamps (spec
2026-11-10-m06-sim-ortami, 4.).

Every TEZ_LOS message passes through one DelayLine between the tracking thread and the MAVLink link. A message leaves
no earlier than its ready time plus its extra delay and never before the message put in ahead of it: the order is
kept like on a real serial link, where a late message holds up the ones behind it. The moment it leaves is its release
stamp (serbest), so the extra delay is measured, not assumed. With no delay and nothing waiting, a message leaves at
once in the caller's thread: no extra thread hop on the path whose latency is being measured.

The line counts in its own clock. The tracking side gives it the sim clock (takip.Tracker): the delay stands for a
latency of the real system (Pi, Hailo, serial link), and the vehicle - PX4 in lockstep included - lives in sim time; a
wall-clock delay would reach PX4 shortened by the real time factor (RTF ~0.85-0.95 with the model on the CPU).

LinkDelay (gecikme.ek_ms, gecikme.titresim_ms): the delay of one message is ek_ms plus a uniform jitter in
[-titresim_ms, +titresim_ms] (the convention of Linux netem's "delay TIME JITTER"), never below 0, drawn from a
generator seeded with JITTER_SEED: the same scenario draws the same delays in the same order.

ClockModel (gecikme.saat_ofset_ms, gecikme.saat_kayma_ppm): the companion computer's clock that stamps TEZ_LOS
(DEBUG_VECT.time_usec) = capture time + offset + drift x elapsed time. The elapsed time is the capture time itself:
the sim clock starts with the simulation and PX4 boots with it in lockstep (within ~4 ms), so this is a clock that was
right at boot and drifts since. PX4 v1.17.0 does not read time_usec (debug_vect.timestamp is the arrival time), so the
model changes what is sent and logged, not what PX4 does (spec "Varsayımlar" 2).

Faz A defaults: everything 0, the line adds nothing and time_usec is the capture time.
"""

import math
import random
import threading
import time
from collections import deque
from collections.abc import Callable

CLOSE_TIMEOUT = 5.0  # [s] for the waiting messages to leave when the line is closed
JITTER_SEED = 0  # seed of the jitter draws (fixed: a scenario's runs draw the same delays)


class LinkDelay:
    """Delay of each message on the capture -> PX4 path [ms of the line's clock]: extra_ms + U(-jitter_ms, jitter_ms),
    at least 0; seeded."""

    def __init__(self, extra_ms: float = 0.0, jitter_ms: float = 0.0, seed: int = JITTER_SEED) -> None:
        if not (math.isfinite(extra_ms) and extra_ms >= 0 and math.isfinite(jitter_ms) and jitter_ms >= 0):
            raise ValueError(f"gecikme: ek_ms ve titresim_ms sonlu ve en az 0 olmalı, gelen: {extra_ms}, {jitter_ms}")
        self.extra_ms = float(extra_ms)
        self.jitter_ms = float(jitter_ms)
        self.seed = seed
        self._rng = random.Random(seed)
        self._lock = threading.Lock()

    def draw_ms(self) -> float:
        """The next message's delay [ms]. Without jitter always extra_ms (and the generator is not used)."""
        if self.jitter_ms == 0.0:
            return self.extra_ms
        with self._lock:
            offset = self._rng.uniform(-self.jitter_ms, self.jitter_ms)
        return max(0.0, self.extra_ms + offset)


class ClockModel:
    """The clock that stamps the sent TEZ_LOS: time_usec = t + offset_ms + drift_ppm x t (t = capture, sim s)."""

    def __init__(self, offset_ms: float = 0.0, drift_ppm: float = 0.0) -> None:
        if not (math.isfinite(offset_ms) and math.isfinite(drift_ppm)):
            raise ValueError(f"gecikme: saat_ofset_ms ve saat_kayma_ppm sonlu olmalı, gelen: {offset_ms}, {drift_ppm}")
        self.offset_ms = float(offset_ms)
        self.drift_ppm = float(drift_ppm)

    def time_usec(self, t: float) -> int:
        """DEBUG_VECT.time_usec of the frame captured at sim time t [s]; never below 0 (the field is unsigned: a clock
        running behind stamps the first frames 0). With offset and drift 0 exactly round(t * 1e6), the capture time."""
        stamped = t + self.offset_ms / 1000.0 + self.drift_ppm * 1e-6 * t
        return max(0, round(stamped * 1e6))


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
        """deliver: sends one message (item, release time [s, `clock`]); extra_ms [ms of `clock`]: default delay of a
        message; clock [s]: the clock of the ready and release times and of the delay, e.g. the monotonic wall clock
        or the sim clock. The line's thread sleeps in wall seconds for what is left in `clock` seconds and looks
        again, so a clock that runs slower than the wall clock (sim time at RTF < 1) is never overshot."""
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
        the message put in ahead of it. A message with no delay and nothing ahead of it leaves at once, whatever the
        clock says (a converted clock such as the sim clock can read a hair behind `ready`). A ready time that is not
        a number (no clock yet) cannot be timed: the message leaves at once, behind any waiting one. RuntimeError
        after close()."""
        delay = self.extra_ms if extra_ms is None else extra_ms
        with self._cond:
            if self._closed:
                raise RuntimeError("gecikme hattı kapalı")
            due = ready + delay / 1000.0
            if self._last_due > due:
                due = self._last_due
            if math.isfinite(due):
                self._last_due = due
            if self._queue or (due > ready and due > self._clock()):
                self._queue.append((due, item))
                if self._thread is None:
                    self._thread = threading.Thread(target=self._run, name=self._name, daemon=True)
                    self._thread.start()
                self._cond.notify_all()
                return
        released = self._clock()
        self._deliver(item, max(released, ready) if math.isfinite(released) and math.isfinite(ready) else released)

    def _run(self) -> None:
        while True:
            with self._cond:
                while True:
                    if self._queue:
                        due, item = self._queue[0]
                        now = self._clock()
                        wait = due - now
                        if not wait > 0:  # due (or not a number: cannot be timed, leaves now)
                            break
                        self._cond.wait(wait)
                    elif self._closed:
                        return
                    else:
                        self._cond.wait()
            try:
                self._deliver(item, now)
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
