"""Drone camera frames for the model: only the newest frame, the books of the skipped ones, sim <-> wall clock.

The camera publishes 2304x1296 RGB at 30 Hz in sim time (models/x500_tez) and Gazebo does not wait for Python. When the
model is slower than the camera, a frame that arrives while it is busy replaces the waiting one, and the replaced
frame is counted as skipped (atlanan). One slot, no queue: the model never works on an old frame and nothing piles up.

The gz-transport callback keeps only the raw message, its arrival time (time.monotonic) and a counter. The message is
decoded only for the frame the model takes; of a replaced frame only its first bytes are kept, which hold its header,
so the books also know the sim time of every skipped frame (stamp()).

SimClock pairs the world clock (/world/<world>/clock, sim time) with this computer's monotonic clock, so wall times
(arrival, model start and end) can be given in sim seconds and the real time factor (RTF) can be measured. Gazebo
writes its system time into every clock message when it publishes it; the pairing uses that time, not the moment the
callback runs, which a busy process (pure Python protobuf of the referee's frames, MAVLink) delays by tens of ms.
time.monotonic is the same clock in every process of this computer, so times taken in the model process compare.
"""

import bisect
import math
import os
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")  # protobuf 7.x in ~/.local
os.environ.setdefault("GZ_IP", "127.0.0.1")  # same as calistir.sh

import numpy as np  # noqa: E402
from gz.msgs10.clock_pb2 import Clock  # noqa: E402
from gz.msgs10.header_pb2 import Header  # noqa: E402
from gz.msgs10.image_pb2 import Image  # noqa: E402

CAMERA_TOPIC = "/x500_tez/kamera/image"  # models/x500_tez, sensor "imager"
IMAGE_TYPE = "gz.msgs.Image"
CLOCK_TYPE = "gz.msgs.Clock"
CLOCK_RATE = 100  # [msg/s] world clock subscription (Gazebo publishes it every 4 ms physics step)
RGB_INT8 = 3  # gz.msgs.PixelFormatType of the drone camera (R8G8B8)
# First bytes kept of a replaced frame: the header is field 1 and comes first (stamp + frame id, ~60 bytes)
HEAD_BYTES = 256
LOG_LIMIT = 900  # replaced frames listed between two takes (30 s at 30 Hz); more are counted, not listed
CLOCK_RECENT = 6000  # clock pairs kept for wall -> sim conversions (60 s at 100 Hz)
CLOCK_COARSE_S = 1.0  # [s sim] spacing of the clock pairs kept for the whole run (RTF)


@dataclass(frozen=True)
class Arrival:
    """One camera message as it reached the reader."""

    sira: int  # 1, 2, ... in arrival order
    varis: float  # [s, time.monotonic] arrival in this computer's clock
    head: bytes  # the first HEAD_BYTES of the serialized message (its header)


@dataclass(frozen=True)
class Frame:
    """A drone camera frame as the model gets it."""

    rgb: np.ndarray  # (height, width, 3) uint8 RGB, a read-only view of the message (1296 x 2304 x 3)
    t: float  # [s, sim] capture: the Gazebo header stamp, the same time as PX4's in SITL
    varis: float  # [s, monotonic] arrival at the reader
    sira: int  # the reader's frame counter


@dataclass(frozen=True)
class Skipped:
    """A frame that was replaced by a newer one before the model took it."""

    sira: int
    t: float  # [s, sim]; NaN if its header was not in the kept bytes
    varis: float  # [s, monotonic]


class LatestFrame:
    """One slot that only ever holds the newest frame; put() from the transport thread, take() from the model."""

    def __init__(self, log_limit: int = LOG_LIMIT) -> None:
        self._cond = threading.Condition()
        self._raw: bytes | None = None
        self._newest: Arrival | None = None
        self._replaced: deque[Arrival] = deque(maxlen=log_limit)  # since the last take
        self._received = 0  # uretilen: frames that reached the reader
        self._taken = 0  # verilen: frames handed to the model
        self._skipped = 0  # atlanan: frames replaced before the model took them
        self._unlisted = 0  # skipped frames that fell off the bounded list (still counted above)

    def put(self, raw: bytes, varis: float) -> None:
        """Store a new frame; a frame still waiting is replaced and counted as skipped."""
        with self._cond:
            self._received += 1
            if self._newest is not None:
                self._skipped += 1
                if len(self._replaced) == self._replaced.maxlen:
                    self._unlisted += 1
                self._replaced.append(self._newest)
            self._raw, self._newest = raw, Arrival(self._received, varis, raw[:HEAD_BYTES])
            self._cond.notify()

    def take(self, timeout: float) -> tuple[bytes, Arrival, list[Arrival]] | None:
        """The newest frame (raw message, its arrival) and the frames it replaced; None if none came in `timeout` [s].
        A frame is handed out once."""
        with self._cond:
            if self._newest is None and not self._cond.wait_for(lambda: self._newest is not None, timeout):
                return None
            raw, newest, replaced = self._raw, self._newest, list(self._replaced)
            self._raw = self._newest = None
            self._replaced.clear()
            self._taken += 1
            return raw, newest, replaced

    def counts(self) -> dict[str, int]:
        """The books: uretilen = verilen + atlanan + bekleyen at any moment."""
        with self._cond:
            return {
                "uretilen": self._received,
                "verilen": self._taken,
                "atlanan": self._skipped,
                "bekleyen": int(self._newest is not None),
                "listesiz_atlanan": self._unlisted,
            }


def _varint(data: bytes, pos: int) -> tuple[int, int]:
    """Protobuf base-128 varint at data[pos] -> (value, position after it); IndexError if it is cut off."""
    value = shift = 0
    while True:
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, pos
        shift += 7


def stamp(head: bytes) -> float:
    """Sim time [s] in the header of a serialized gz message (header = field 1, written first) from its first bytes;
    NaN if the header is not complete in them."""
    if not head or head[0] != 0x0A:  # field 1, length-delimited
        return math.nan
    try:
        length, pos = _varint(head, 1)
    except IndexError:
        return math.nan
    if pos + length > len(head):
        return math.nan
    header = Header.FromString(head[pos : pos + length])
    return header.stamp.sec + header.stamp.nsec * 1e-9


def decode(raw: bytes, arrival: Arrival) -> Frame:
    """The camera message -> Frame; the pixels stay in the message's buffer (no copy, read-only)."""
    msg = Image.FromString(raw)
    if msg.pixel_format_type != RGB_INT8 or msg.step != 3 * msg.width or len(msg.data) != msg.step * msg.height:
        raise ValueError(
            f"kamera karesi RGB_INT8 (R8G8B8) değil ya da boyutu tutmuyor: biçim {msg.pixel_format_type}, "
            f"{msg.width}x{msg.height}, step {msg.step}, {len(msg.data)} bayt"
        )
    rgb = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.width, 3)
    return Frame(rgb, msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9, arrival.varis, arrival.sira)


class FrameReader:
    """The drone camera through gz-transport (subscribe_raw); the callback only fills a LatestFrame and, with `also`,
    hands the message on (goruntu_yayini.FrameTap: the video's frames without a second subscription)."""

    def __init__(self, topic: str = CAMERA_TOPIC, also: Callable[[bytes, float], None] | None = None) -> None:
        from gz.transport13 import Node, SubscribeOptions

        self.topic = topic
        self.slot = LatestFrame()
        self._also = also
        self._node = Node()
        if not self._node.subscribe_raw(topic, self._on_image, IMAGE_TYPE, SubscribeOptions()):
            raise RuntimeError(f"{topic} konusuna abone olunamadı")

    def _on_image(self, raw: bytes, _info: object) -> None:
        arrival = time.monotonic()
        self.slot.put(raw, arrival)
        if self._also is not None:
            self._also(raw, arrival)

    def take(self, timeout: float) -> tuple[bytes, Arrival, list[Arrival]] | None:
        return self.slot.take(timeout)

    def close(self) -> None:
        self._node.unsubscribe(self.topic)


def clock_pair(msg: Clock, realtime: float, monotonic: float) -> tuple[float, float]:
    """(sim time, monotonic wall time) [s] of a world clock message received at `realtime` (time.time) =
    `monotonic` (time.monotonic): the wall time is Gazebo's own publishing time (system field) on this computer's
    monotonic clock; without it, the receipt time."""
    sim = msg.sim.sec + msg.sim.nsec * 1e-9
    if not msg.HasField("system"):
        return sim, monotonic
    return sim, msg.system.sec + msg.system.nsec * 1e-9 - (realtime - monotonic)


class SimClock:
    """Sim time <-> this computer's monotonic clock, from the world clock topic (or add() in tests)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._recent: deque[tuple[float, float]] = deque(maxlen=CLOCK_RECENT)  # (sim, wall), for conversions
        self._sims: list[float] = []  # one pair per CLOCK_COARSE_S of sim time for the whole run (RTF)
        self._walls: list[float] = []
        self._node = None

    def subscribe(self, world: str) -> None:
        """Follow /world/<world>/clock, throttled to CLOCK_RATE messages per second."""
        from gz.transport13 import Node, SubscribeOptions

        options = SubscribeOptions()
        options.msgs_per_sec = CLOCK_RATE
        self._node = Node()
        if not self._node.subscribe_raw(f"/world/{world}/clock", self._on_clock, CLOCK_TYPE, options):
            raise RuntimeError(f"/world/{world}/clock konusuna abone olunamadı")

    def _on_clock(self, raw: bytes, _info: object) -> None:
        realtime, monotonic = time.time(), time.monotonic()
        self.add(*clock_pair(Clock.FromString(raw), realtime, monotonic))

    def add(self, sim: float, wall: float) -> None:
        with self._lock:
            if self._recent and sim < self._recent[-1][0]:  # a new world (time restarted): start over
                self._recent.clear()
                self._sims.clear()
                self._walls.clear()
            self._recent.append((sim, wall))
            if not self._sims or sim - self._sims[-1] >= CLOCK_COARSE_S:
                self._sims.append(sim)
                self._walls.append(wall)

    @property
    def sim_time(self) -> float:
        """[s] newest sim time; NaN before the first message."""
        with self._lock:
            return self._recent[-1][0] if self._recent else math.nan

    def to_sim(self, wall: float) -> float:
        """Sim time [s] at a monotonic wall time; after the newest message at the rate of the last ten; NaN before
        any message or before the kept pairs."""
        with self._lock:
            pairs = self._recent
            if not pairs:
                return math.nan
            if wall >= pairs[-1][1]:
                s0, w0 = pairs[max(0, len(pairs) - 11)]
                s1, w1 = pairs[-1]
                rate = (s1 - s0) / (w1 - w0) if w1 > w0 else 1.0
                return s1 + rate * (wall - w1)
            for i in range(len(pairs) - 1, 0, -1):  # newest first: conversions are for the last fraction of a second
                (s0, w0), (s1, w1) = pairs[i - 1], pairs[i]
                if w0 <= wall <= w1:
                    return s0 if w1 == w0 else s0 + (s1 - s0) * (wall - w0) / (w1 - w0)
            return math.nan

    def wall_at(self, sim: float) -> float:
        """Monotonic wall time [s] when the sim reached `sim` [s]; NaN outside the run."""
        with self._lock:
            sims, walls = list(self._sims), list(self._walls)
            if self._recent and self._recent[-1][0] > sims[-1]:
                sims.append(self._recent[-1][0])
                walls.append(self._recent[-1][1])
        if not sims or not sims[0] <= sim <= sims[-1]:
            return math.nan
        i = min(max(bisect.bisect_left(sims, sim), 1), len(sims) - 1)
        s0, s1, w0, w1 = sims[i - 1], sims[i], walls[i - 1], walls[i]
        return w0 if s1 == s0 else w0 + (w1 - w0) * (sim - s0) / (s1 - s0)

    def rtf(self, sim_from: float, sim_to: float) -> float:
        """Real time factor over sim_from..sim_to [s]: sim seconds per wall second; NaN if not covered."""
        w0, w1 = self.wall_at(sim_from), self.wall_at(sim_to)
        return (sim_to - sim_from) / (w1 - w0) if w1 > w0 else math.nan

    def rtf_min(self, sim_from: float, sim_to: float, span: float = 5.0) -> float:
        """Lowest RTF over consecutive `span` [s sim] pieces of sim_from..sim_to (a slow stretch the mean hides)."""
        values = []
        t = sim_from
        while t + span <= sim_to + 1e-9:
            values.append(self.rtf(t, t + span))
            t += span
        values = [v for v in values if not math.isnan(v)]
        return min(values) if values else math.nan
