#!/usr/bin/env python3
"""Camera frames for kosu.mp4 (task group 8) and the live H.264 stream to QGroundControl (task group 11).

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/goruntu_yayini.py --qgc --model <file.pt>
                            standalone, next to a running sim (tez/sim/calistir.sh + QGC by hand): the drone camera
                            with the boxes of its own detector; no referee, no target selection, nothing goes to PX4
    ... --qgc               the same without a detector: the camera only

In a scenario run (senaryo.py) this module is one process ("spawn", like the model process): gz-transport, the JPEG
work and the H.264 encoder stay off the main process, which keeps MAVLink and the referee. With a model it takes the
camera messages the model process receives anyway (FrameShare: a shared-memory ring, no second 9 MB x 30 Hz
subscription, which cost the RTF ~0.06); without one, and once the model has stopped (the landing), it subscribes
itself with subscribe_raw. Only the header of each message is read (goruntu.stamp) to keep the frames on the 15 fps
grid of sim time (GridPicker: every second camera frame). One worker thread reads each kept frame once without copying
it (frame_pixels), scales it to 1280x720 into buffers kept from frame to frame (Scaler) and
  - (--qgc / video.qgc) draws the newest boxes on a copy (video.draw_live: the referee's box of the target blue, the
    model's boxes red, the chosen one thick, "HEDEF YOK") and pushes it into the GStreamer pipeline of spec 10:
    appsrc -> queue leaky=downstream -> videoconvert -> x264enc zerolatency -> rtph264pay -> udpsink 127.0.0.1:5600.
    QGC 5.1.4 shows it as "UDP h.264 Video Stream" on port 5600; ffplay opens it with yayin.sdp (Ubuntu's VLC 3.0.20
    cannot: it is built without live555, so without RTP from an SDP). Every grid frame of
    the whole run is streamed (takeoff included), not only the recording window;
  - inside the referee's recording window writes the clean frame (no boxes) as JPEG (quality 90) to
    kareler/<t_us>.jpg; video.py puts kosu.mp4 together from the files after the run.
The boxes come from the main process: one JSON datagram per processed model frame on 127.0.0.1:5610 (BoxMessage:
that frame's boxes, the chosen one and the referee's box of the target in the same frame; takip.Tracker builds it).
They belong to an older frame than the one shown (the model takes ~0.1 s), so they lag behind the person as in
kosu.mp4; boxes older than BOX_STALE_S are not drawn.

Nothing piles up: a stream-only frame is not queued behind another one and a frame with a newer one waiting behind
it is not streamed (the stream shows the newest); the recording keeps every grid frame of its window, and if the
worker falls that far behind a full queue drops the new frame and counts it (the video then shows the frame before).
The process stays out of Gazebo's and the model's way: OpenCV on one thread, the scaling in two cheap steps (box
filter to exactly half, then bilinear: 3.4 ms on one core instead of 16 ms) and a lower CPU priority (nice), so under
contention it is the recorder that drops frames, not the simulation that slows down. Its CPU time over the recording
window goes into its books (implementation/gorev-grubu-11.md: what recording and streaming cost the RTF).

    rec = FrameRecorder(out / "kareler", qgc=True); rec.start()   # before the simulation (folder None: stream only)
    rec.begin(sim_time) ... rec.end(sim_time)                     # the referee's recording window (senaryo.fly)
    books = rec.stop()                                            # what was kept, written, streamed, dropped
"""

import argparse
import functools
import importlib.util
import json
import math
import multiprocessing as mp
import os
import queue
import resource
import signal
import socket
import sys
import threading
import time
import traceback
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")  # protobuf 7.x in ~/.local
os.environ.setdefault("GZ_IP", "127.0.0.1")  # same as calistir.sh

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import algilama  # noqa: E402
import goruntu  # noqa: E402
import kayit  # noqa: E402

FPS = 15  # [frames per s of sim time] of kosu.mp4 and the stream: every second frame of the 30 Hz camera
GRID_TOLERANCE = 0.3  # [slots] a frame within 0.3 / 15 s = 20 ms of a grid time takes that slot (frames: 32/36 ms)
FRAME_SIZE = (1280, 720)  # [px] width, height of a kept frame (the video's camera panel) and of the stream
JPEG_QUALITY = 90
FRAMES_DIR = "kareler"
QUEUE_FRAMES = 6  # raw 9 MB messages waiting for the worker; one more is dropped and counted
RECORDER_NICE = 5  # lower CPU priority of the recorder process than Gazebo, PX4 and the model
READY_TIMEOUT = 30.0  # [s] for the recorder process to come up
STOP_TIMEOUT = 60.0  # [s] for its worker to empty the queue at the end

# live stream, spec 10 (QGC 5.1.4: Application Settings -> Video -> "UDP h.264 Video Stream", port 5600)
STREAM_HOST, STREAM_PORT = "127.0.0.1", 5600  # QGC on this laptop; 5600 is QGC's default video port
STREAM_QUEUE = 2  # [frames] in the leaky queue in front of the encoder; older ones are dropped
BITRATE_KBPS = 2000
KEY_INT_MAX = 15  # [frames] a key frame every 1 s at 15 fps: after a lost packet the picture heals within 1 s
# x264 opens a slice thread per core by default; one thread encodes the same frames with ~20 % less CPU (0.215 -> 0.17
# cores for the whole stream) for +1.3 ms of encoding delay (bench, implementation/gorev-grubu-11.md): the sim's RTF
# matters more here than a millisecond
ENCODER_THREADS = 1
PAYLOAD_TYPE = 96  # dynamic RTP payload type of H.264 (yayin.sdp says the same)
MTU = 1400  # [bytes] RTP packets stay under a Wi-Fi link's MTU (the Pi's stream later; m24)
BOX_HOST, BOX_PORT = "127.0.0.1", 5610  # boxes, main process -> stream (one JSON datagram per model frame)
# watching without QGC: ffplay (the pinned ffmpeg package) with yayin.sdp; RTP from a local SDP file must be allowed,
# no buffering for a live picture
FFPLAY_OPTIONS = "-protocol_whitelist file,udp,rtp -fflags nobuffer -flags low_delay"
BOX_STALE_S = 1.0  # [s sim] boxes of a frame older than this are not drawn: the model fell silent
BOX_EARLY_S = 0.1  # [s sim] boxes of a frame this much newer than the shown one are still drawn
MAX_BOXES = 64  # per message; more is refused (the model finds a handful)
MAX_MESSAGE_BYTES = 16384  # one datagram; 64 boxes are ~2.5 kB
MAX_STATE_CHARS = 32
LATENCY_SAMPLES = 20000  # [frames] kept for the stream's percentiles (~22 min at 15 fps)
STATUS_EVERY_S = 10.0  # [s wall] status line of the standalone stream


class RecorderError(RuntimeError):
    """The recorder / stream process did not come up (a port in use, GStreamer missing...)."""


def frame_name(t: float) -> str:
    """File name of a kept frame: its sim time in microseconds, zero padded (sorts in time)."""
    return f"{round(t * 1e6):012d}.jpg"


def frame_time(path: Path) -> float:
    """[s sim] capture time of a kept frame from its file name."""
    return int(path.stem) / 1e6


def frame_pixels(raw: bytes | memoryview) -> np.ndarray:
    """The RGB pixels (height, width, 3) of a serialized drone camera message, a view into it: nothing is copied
    (kayit.read_image). Copying 9 MB per frame cost the worker more in page faults than the scaling itself
    (gorev-grubu-11.md); the scaled frame is a new array. ValueError if the pixels do not fill width x height x 3."""
    img = kayit.read_image(raw)
    if len(img.data) != img.width * img.height * 3 or not img.width:
        raise ValueError(
            f"kamera karesi RGB değil ya da boyutu tutmuyor: {img.width}x{img.height}, {len(img.data)} bayt"
        )
    return np.frombuffer(img.data, np.uint8).reshape(img.height, img.width, 3)


def scale_frame(rgb: np.ndarray) -> np.ndarray:
    """One camera frame (RGB, any size) -> FRAME_SIZE BGR: box filter to half the size (the fast integer case, no
    aliasing), then bilinear to FRAME_SIZE."""
    half = cv2.resize(rgb, (rgb.shape[1] // 2, rgb.shape[0] // 2), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(cv2.resize(half, FRAME_SIZE, interpolation=cv2.INTER_LINEAR), cv2.COLOR_RGB2BGR)


class Scaler:
    """scale_frame into buffers kept from frame to frame (one per worker thread): a fresh 7.6 MB of intermediate arrays
    per frame cost ~3 ms of page faults, about as much as the scaling itself (gorev-grubu-11.md). The returned frame
    is overwritten by the next call."""

    def __init__(self) -> None:
        self._half: np.ndarray | None = None
        self._small = np.empty((FRAME_SIZE[1], FRAME_SIZE[0], 3), np.uint8)
        self._bgr = np.empty_like(self._small)

    def __call__(self, rgb: np.ndarray) -> np.ndarray:
        half = (rgb.shape[0] // 2, rgb.shape[1] // 2, 3)
        if self._half is None or self._half.shape != half:
            self._half = np.empty(half, np.uint8)
        cv2.resize(rgb, (half[1], half[0]), dst=self._half, interpolation=cv2.INTER_AREA)
        cv2.resize(self._half, FRAME_SIZE, dst=self._small, interpolation=cv2.INTER_LINEAR)
        return cv2.cvtColor(self._small, cv2.COLOR_RGB2BGR, dst=self._bgr)


def save_jpeg(bgr: np.ndarray, path: Path) -> None:
    """A scaled frame -> JPEG, written to a temporary name and renamed, so a stopped run never leaves half a file
    under a frame's name."""
    ok, data = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise RuntimeError(f"{path.name}: JPEG kodlanamadı")
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(data.tobytes())
    tmp.replace(path)


def write_jpeg(rgb: np.ndarray, path: Path) -> None:
    """One camera frame (RGB, any size) -> FRAME_SIZE JPEG."""
    save_jpeg(scale_frame(rgb), path)


class GridPicker:
    """Keeps the camera frame nearest every 1/FPS s of sim time inside the window [start, end] (start NaN = not
    started yet, end NaN = still open): with the camera at 30 Hz, every second frame. A slot is taken once; a slot
    whose frame was lost stays empty, the next slots do not shift."""

    def __init__(self, fps: int = FPS, tolerance: float = GRID_TOLERANCE) -> None:
        self.fps = fps
        self.tolerance = tolerance
        self.last: int | None = None

    def pick(self, t: float, start: float, end: float) -> int | None:
        """The slot (round(t * fps)) the frame at sim time t takes, or None."""
        if not math.isfinite(t) or not t >= start or (math.isfinite(end) and t > end):
            return None
        x = t * self.fps
        slot = round(x)
        if abs(x - slot) > self.tolerance or (self.last is not None and slot <= self.last):
            return None
        self.last = slot
        return slot


# --- boxes: main process -> stream (UDP 5610) -----------------------------------------------------------------------


@dataclass(frozen=True)
class BoxMessage:
    """What the stream draws over its frames: the boxes of one processed model frame and the referee's box of the
    target in that same frame. Boxes are pixel edges in the full camera image (2304x1296), u right, v down."""

    t: float  # [s sim] capture of the model's frame
    boxes: tuple[tuple[float, float, float, float, float], ...] = ()  # (u0, v0, u1, v1, guven), most confident first
    chosen: int | None = None  # the target's box in `boxes` (takip.Selection), None: none chosen
    state: str = ""  # takip.Choice.state; "hakem" without a model, "tek" standalone
    no_target: bool = False  # this frame's TEZ_LOS says "no target" (what PX4 got)
    referee: tuple[float, float, float, float] | None = None  # the target's visible pixels; None: hidden, no referee


def _finite(values: Sequence[object], n: int, where: str) -> tuple[float, ...]:
    if not isinstance(values, list | tuple) or len(values) != n:
        raise ValueError(f"{where}: {n} sayı olmalı")
    if not all(isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v) for v in values):
        raise ValueError(f"{where}: sonlu sayılar olmalı")
    return tuple(float(v) for v in values)


def _box(values: Sequence[object], n: int, where: str) -> tuple[float, ...]:
    box = _finite(values, n, where)
    if not (box[0] <= box[2] and box[1] <= box[3]):
        raise ValueError(f"{where}: u0 <= u1 ve v0 <= v1 olmalı")
    if n == 5 and not 0.0 <= box[4] <= 1.0:
        raise ValueError(f"{where}: güven 0..1 olmalı")
    return box


def check(msg: BoxMessage) -> BoxMessage:
    """The message with plain floats; ValueError for anything that must not be drawn (both ends call it)."""
    if not (isinstance(msg.t, int | float) and math.isfinite(msg.t)):
        raise ValueError("t: sonlu bir sim zamanı olmalı")
    if len(msg.boxes) > MAX_BOXES:
        raise ValueError(f"kutular: en çok {MAX_BOXES}")
    boxes = tuple(_box(b, 5, f"kutu {i}") for i, b in enumerate(msg.boxes))
    chosen = msg.chosen
    if chosen is not None and not (
        isinstance(chosen, int) and not isinstance(chosen, bool) and 0 <= chosen < len(boxes)
    ):
        raise ValueError(f"secilen: 0..{len(boxes) - 1} ya da boş olmalı")
    if not isinstance(msg.state, str) or len(msg.state) > MAX_STATE_CHARS:
        raise ValueError(f"secim: en çok {MAX_STATE_CHARS} karakterlik bir metin olmalı")
    if not isinstance(msg.no_target, bool):
        raise ValueError("hedef_yok: true/false olmalı")
    referee = _box(msg.referee, 4, "hakem") if msg.referee is not None else None
    return BoxMessage(float(msg.t), boxes, chosen, msg.state, msg.no_target, referee)


KEYS = {"v", "t", "kutular", "secilen", "secim", "hedef_yok", "hakem"}
VERSION = 1


def pack(msg: BoxMessage) -> bytes:
    """BoxMessage -> one UDP datagram (JSON); ValueError if it is not a valid message."""
    m = check(msg)
    data = {
        "v": VERSION,
        "t": m.t,
        "kutular": [[round(c, 1) for c in b[:4]] + [round(b[4], 3)] for b in m.boxes],
        "secilen": m.chosen,
        "secim": m.state,
        "hedef_yok": m.no_target,
        "hakem": [round(c, 1) for c in m.referee] if m.referee is not None else None,
    }
    return json.dumps(data, separators=(",", ":"), allow_nan=False, ensure_ascii=False).encode()


def _no_constant(name: str) -> float:
    raise ValueError(f"{name}: JSON'da sayı değil")


def unpack(data: bytes) -> BoxMessage:
    """One datagram -> BoxMessage; ValueError if it is not one (bad JSON, unknown or missing keys, NaN, ranges)."""
    if len(data) > MAX_MESSAGE_BYTES:
        raise ValueError(f"mesaj {MAX_MESSAGE_BYTES} bayttan büyük")
    try:
        d = json.loads(data.decode(), parse_constant=_no_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"JSON değil: {e}") from None
    if not isinstance(d, dict) or set(d) != KEYS:
        raise ValueError(f"alanlar {sorted(KEYS)} olmalı")
    if d["v"] != VERSION:
        raise ValueError(f"sürüm {VERSION} olmalı, gelen: {d['v']!r}")
    if not isinstance(d["kutular"], list) or (d["hakem"] is not None and not isinstance(d["hakem"], list)):
        raise ValueError("kutular ve hakem liste olmalı")
    if not isinstance(d["t"], int | float) or isinstance(d["t"], bool):
        raise ValueError("t: sayı olmalı")
    referee = tuple(d["hakem"]) if d["hakem"] is not None else None
    boxes = tuple(tuple(b) if isinstance(b, list) else b for b in d["kutular"])
    return check(BoxMessage(d["t"], boxes, d["secilen"], d["secim"], d["hedef_yok"], referee))


def fresh(msg: BoxMessage | None, frame_t: float) -> bool:
    """The message's boxes may be drawn on the frame captured at frame_t [s sim]."""
    return msg is not None and -BOX_EARLY_S <= frame_t - msg.t <= BOX_STALE_S


def standalone_message(r: algilama.FrameResult) -> BoxMessage:
    """Standalone mode: the boxes of the stream's own detector only (no referee, no selection, no LOS)."""
    return BoxMessage(r.t, tuple((k.u0, k.v0, k.u1, k.v1, k.guven) for k in r.kutular[:MAX_BOXES]), state="tek")


class BoxSender:
    """Main process side: send() a BoxMessage to the stream; never blocks, never raises (the tracking thread calls
    it). A message that does not pass check() is not sent and is counted."""

    def __init__(self, port: int = BOX_PORT, host: str = BOX_HOST) -> None:
        self._addr = (host, port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(False)
        self._lock = threading.Lock()
        self._counts = {"gonderildi": 0, "gecersiz": 0, "hata": 0}
        self.errors: list[str] = []

    def send(self, msg: BoxMessage) -> str:
        try:
            data = pack(msg)
        except ValueError as e:
            return self._count("gecersiz", f"geçersiz kutu mesajı (t = {msg.t}): {e}")
        try:
            self._sock.sendto(data, self._addr)
        except OSError as e:  # a full socket buffer drops the message; the stream draws the next one
            return self._count("hata", f"kutu mesajı gönderilemedi: {e}")
        return self._count("gonderildi")

    def _count(self, result: str, error: str = "") -> str:
        with self._lock:
            self._counts[result] += 1
            if error and len(self.errors) < 10:
                self.errors.append(error)
        return result

    def counts(self) -> dict:
        with self._lock:
            return dict(self._counts)

    def close(self) -> None:
        self._sock.close()


class LatestBoxes:
    """The newest BoxMessage (one slot; put() from any thread)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._msg: BoxMessage | None = None

    def put(self, msg: BoxMessage) -> None:
        with self._lock:
            self._msg = msg

    def latest(self) -> BoxMessage | None:
        with self._lock:
            return self._msg


class BoxListener(LatestBoxes):
    """Stream side of UDP 5610: a thread keeps the newest valid message; refused ones are counted."""

    def __init__(self, port: int = BOX_PORT, host: str = BOX_HOST) -> None:
        super().__init__()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self._sock.bind((host, port))
        except OSError as e:
            self._sock.close()
            raise RecorderError(
                f"kutu portu UDP {host}:{port} açılamadı ({e}): başka bir görüntü yayını açık olabilir "
                "(goruntu_yayini.py)"
            ) from None
        self._sock.settimeout(0.2)
        self.port = self._sock.getsockname()[1]
        self._counts = {"alinan": 0, "gecersiz": 0}
        self._errors: list[str] = []
        self._closed = threading.Event()
        self._thread = threading.Thread(target=self._run, name="tez-kutu-dinleyici", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._closed.is_set():
            try:
                data = self._sock.recv(MAX_MESSAGE_BYTES + 1)
            except TimeoutError:
                continue
            except OSError:
                return
            try:
                msg = unpack(data)
            except ValueError as e:
                with self._lock:
                    self._counts["gecersiz"] += 1
                    if len(self._errors) < 10:
                        self._errors.append(str(e))
                continue
            with self._lock:
                self._counts["alinan"] += 1
                self._msg = msg

    def counts(self) -> dict:
        with self._lock:
            return dict(self._counts) | {"hatalar": list(self._errors)}

    def close(self) -> None:
        self._closed.set()
        self._thread.join(2.0)
        self._sock.close()


# --- the H.264 RTP stream ------------------------------------------------------------------------------------------


@functools.cache
def gst() -> ModuleType:
    """GStreamer through PyGObject (apt python3-gi, gir1.2-gstreamer-1.0; tez/env/VERSIONS.md), initialised once per
    process; ImportError / ValueError if it is not installed."""
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst

    Gst.init(None)
    return Gst


def pipeline_description(
    host: str = STREAM_HOST, port: int = STREAM_PORT, size: tuple[int, int] = FRAME_SIZE, fps: int = FPS
) -> str:
    """The GStreamer pipeline of spec 10 (gst-launch syntax). do-timestamp: a frame's time is when it was pushed (the
    stream plays in wall time like the real one); the queue in front of the encoder drops old frames, never waits."""
    w, h = size
    return " ! ".join(
        (
            f"appsrc name=src is-live=true format=time do-timestamp=true "
            f"caps=video/x-raw,format=BGR,width={w},height={h},framerate={fps}/1",
            f"queue name=sizdiran leaky=downstream max-size-buffers={STREAM_QUEUE} max-size-bytes=0 max-size-time=0",
            "videoconvert",
            "video/x-raw,format=I420",
            f"x264enc tune=zerolatency speed-preset=ultrafast bitrate={BITRATE_KBPS} key-int-max={KEY_INT_MAX} "
            f"threads={ENCODER_THREADS}",
            "video/x-h264,profile=constrained-baseline",
            f"rtph264pay config-interval=1 pt={PAYLOAD_TYPE} mtu={MTU}",
            f"udpsink host={host} port={port} sync=false async=false",
        )
    )


def _percentile(values: Sequence[float], q: float) -> float:
    return float(np.percentile(values, q)) if values else math.nan


class LiveStream:
    """The pipeline; show() draws the newest boxes on a copy of a scaled frame and pushes it (the worker thread)."""

    def __init__(
        self,
        boxes: Callable[[], BoxMessage | None],
        host: str = STREAM_HOST,
        port: int = STREAM_PORT,
        standalone: bool = False,
    ) -> None:
        """boxes: the newest BoxMessage (BoxListener.latest, LatestBoxes.latest); standalone: no referee, no
        selection (the texts say so)."""
        import video  # the camera panel's drawing; imported here because video imports this module

        self._draw = video.draw_live
        # draw once before GStreamer starts any thread: every module and font the drawing needs is loaded now (a
        # measurement script that first loaded matplotlib while a pipeline ran crashed in the import; gorev-grubu-11)
        self._draw(np.zeros((FRAME_SIZE[1], FRAME_SIZE[0], 3), np.uint8), 0.0, None, 2 * FRAME_SIZE[0], standalone)
        self._gst = gst()
        self._boxes = boxes
        self.standalone = standalone
        self.target = f"udp://{host}:{port}"
        gs = self._gst
        try:
            self._pipeline = gs.parse_launch(pipeline_description(host, port))
        except Exception as e:  # noqa: BLE001 - GLib.Error: an element is missing (VERSIONS.md lists the packages)
            raise RecorderError(f"yayın hattı kurulamadı: {e}") from None
        self._src = self._pipeline.get_by_name("src")
        self._pipeline.get_by_name("sizdiran").connect("overrun", self._overrun)
        self._bus = self._pipeline.get_bus()
        self._lock = threading.Lock()
        self._counts = {"verilen": 0, "kutulu": 0, "itme_hatasi": 0, "kuyruk_tasmasi": 0}
        self._times: list[float] = [math.nan, math.nan]  # [s sim] first, last pushed frame
        self._walls: list[float] = [math.nan, math.nan]  # [s monotonic] when they were pushed
        self._ms: deque[float] = deque(maxlen=LATENCY_SAMPLES)  # [ms wall] draw + push of a frame
        self._late_ms: deque[float] = deque(maxlen=LATENCY_SAMPLES)  # [ms wall] arrival at this process -> pushed
        self.errors: list[str] = []
        if self._pipeline.set_state(gs.State.PLAYING) == gs.StateChangeReturn.FAILURE:
            self._check_bus()
            self._pipeline.set_state(gs.State.NULL)
            raise RecorderError("yayın hattı başlamadı: " + ("; ".join(self.errors) or "nedeni bilinmiyor"))

    def _overrun(self, _queue: object) -> None:
        with self._lock:
            self._counts["kuyruk_tasmasi"] += 1  # the encoder fell behind; the leaky queue dropped an old frame

    def show(self, t: float, frame: np.ndarray, camera_width: int, arrival: float) -> None:
        """Push the frame captured at sim time t (FRAME_SIZE BGR; not changed) with the newest boxes drawn on it;
        camera_width [px]: of the camera image the boxes are in; arrival [s monotonic]: when it reached the process."""
        start = time.perf_counter()
        msg = self._boxes()
        img = self._draw(frame.copy(), t, msg, camera_width, self.standalone)
        gs = self._gst
        # bytes, not a memoryview: PyGObject converts a memoryview item by item (80 ms per frame, gorev-grubu-11.md)
        result = self._src.emit("push-buffer", gs.Buffer.new_wrapped(np.ascontiguousarray(img).tobytes()))
        pushed = time.monotonic()
        with self._lock:
            if result != gs.FlowReturn.OK:
                self._counts["itme_hatasi"] += 1
                if len(self.errors) < 10:
                    self.errors.append(f"{t:.3f} s: push-buffer {result.value_nick}")
            else:
                self._counts["verilen"] += 1
                self._counts["kutulu"] += fresh(msg, t)
                if math.isnan(self._times[0]):
                    self._times[0], self._walls[0] = t, pushed
                self._times[1], self._walls[1] = t, pushed
            self._ms.append((time.perf_counter() - start) * 1000.0)
            self._late_ms.append((pushed - arrival) * 1000.0)
        self._check_bus()

    def _check_bus(self) -> None:
        gs = self._gst
        while (m := self._bus.pop_filtered(gs.MessageType.ERROR | gs.MessageType.WARNING)) is not None:
            err, _debug = m.parse_error() if m.type == gs.MessageType.ERROR else m.parse_warning()
            with self._lock:
                if len(self.errors) < 10:
                    self.errors.append(f"{m.src.get_name()}: {err.message}")

    def counts(self) -> dict:
        """The stream's books: frames pushed, with fresh boxes, refused by the pipeline, dropped by its queue;
        their sim and wall rate; draw + push time and arrival -> push delay [ms]."""
        with self._lock:
            c, ms, late = dict(self._counts), list(self._ms), list(self._late_ms)
            (t0, t1), (w0, w1) = self._times, self._walls
            errors = list(self.errors)
        n = c["verilen"]
        return c | {
            "hedef": self.target,
            "ilk_t": t0,
            "son_t": t1,
            "hiz_sim_hz": (n - 1) / (t1 - t0) if n > 1 and t1 > t0 else math.nan,
            "hiz_duvar_hz": (n - 1) / (w1 - w0) if n > 1 and w1 > w0 else math.nan,
            "kare_ms_ort": float(np.mean(ms)) if ms else math.nan,
            "kare_ms_maks": float(np.max(ms)) if ms else math.nan,
            "gecikme_ms_p50": _percentile(late, 50),
            "gecikme_ms_p95": _percentile(late, 95),
            "gecikme_ms_maks": float(np.max(late)) if late else math.nan,
            "hatalar": errors,
        }

    def close(self) -> dict:
        """End the stream (end-of-stream, pipeline to NULL); returns counts(). Repeatable."""
        if self._pipeline is not None:
            self._src.emit("end-of-stream")
            self._check_bus()
            self._pipeline.set_state(self._gst.State.NULL)
            self._pipeline = None
        return self.counts()


# --- the worker -----------------------------------------------------------------------------------------------------


class FrameSink:
    """The recorder without gz-transport: offer() every camera message (transport thread, returns at once); a worker
    thread decodes and scales each kept frame once, gives it to the stream (if any) and writes the JPEG of the
    recording window (folder None: no recording); close() waits for it and returns the recording's books."""

    def __init__(
        self,
        folder: Path | None,
        queue_frames: int = QUEUE_FRAMES,
        save: Callable[[np.ndarray, Path], None] = save_jpeg,
        stream: LiveStream | None = None,
    ) -> None:
        self.folder = folder
        if folder is not None:
            folder.mkdir(parents=True, exist_ok=True)
        self._save = save
        self._stream = stream
        self._scale = Scaler()  # used by the worker thread only
        self._record_picker = GridPicker()
        self._stream_picker = GridPicker()
        self._queue: queue.Queue[tuple | None] = queue.Queue(maxsize=queue_frames)
        self._waiting = 0  # frames in the queue (not the end marker)
        self._lock = threading.Lock()
        self._counts = {"kamera_karesi": 0, "secilen": 0, "yazilan": 0, "dusen": 0, "hatali": 0, "ezilen": 0}
        self._live = {"secilen": 0, "atlanan": 0, "hatali": 0, "ezilen": 0}
        self._times: list[float] = []  # [s sim] written frames
        self._ms: list[float] = []  # [ms wall] decode + scale + JPEG + write per written frame
        self.errors: list[str] = []
        self._thread = threading.Thread(target=self._work, name="tez-video-yazici", daemon=True)
        self._thread.start()

    def offer(
        self,
        raw: bytes | memoryview,
        start: float,
        end: float,
        arrival: float | None = None,
        valid: Callable[[], bool] | None = None,
    ) -> None:
        """A camera message; [start, end]: the recording window in sim time (NaN: not started / still open); arrival
        [s monotonic]: when it reached this process (or the model process); valid: for a message in FrameShare's ring,
        whether its slot still holds it (checked after the frame is read)."""
        arrival = time.monotonic() if arrival is None else arrival
        with self._lock:
            self._counts["kamera_karesi"] += 1
            t = goruntu.stamp(raw[: goruntu.HEAD_BYTES])
            record = self.folder is not None and self._record_picker.pick(t, start, end) is not None
            live = self._stream is not None and self._stream_picker.pick(t, -math.inf, math.nan) is not None
            self._counts["secilen"] += record
            self._live["secilen"] += live
            if not record and (not live or self._waiting):  # a stream frame never waits behind another one
                self._live["atlanan"] += live
                return
            try:
                self._queue.put_nowait((t, raw, record, live, arrival, valid))
                self._waiting += 1
            except queue.Full:
                self._counts["dusen"] += record
                self._live["atlanan"] += live

    def _work(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    return
                with self._lock:
                    self._waiting -= 1
                self._handle(*item)
            finally:
                self._queue.task_done()

    def _handle(
        self,
        t: float,
        raw: bytes | memoryview,
        record: bool,
        live: bool,
        arrival: float,
        valid: Callable[[], bool] | None,
    ) -> None:
        start = time.perf_counter()
        try:
            rgb = frame_pixels(raw)
            small = self._scale(rgb)
        except Exception as e:  # noqa: BLE001 - one bad frame must not end the recording; counted and reported
            if valid is None or valid():
                self._fail(record, live, t, e)
                return
        if valid is not None and not valid():  # its ring slot was written again while it was read: maybe torn
            with self._lock:
                self._counts["ezilen"] += record
                self._live["ezilen"] += live
            return
        prepared = time.perf_counter()
        if live:
            with self._lock:
                newer = self._waiting > 0  # a newer frame waits: the stream shows that one
                self._live["atlanan"] += newer
            if not newer:
                try:
                    self._stream.show(t, small, rgb.shape[1], arrival)
                except Exception as e:  # noqa: BLE001 - the stream's failure is not the recording's
                    self._fail(False, True, t, e)
        if not record:
            return
        saving = time.perf_counter()
        try:
            self._save(small, self.folder / frame_name(t))
        except Exception as e:  # noqa: BLE001 - counted and reported
            self._fail(True, False, t, e)
            return
        with self._lock:
            self._counts["yazilan"] += 1
            self._times.append(t)
            self._ms.append((prepared - start + time.perf_counter() - saving) * 1000.0)

    def _fail(self, record: bool, live: bool, t: float, e: Exception) -> None:
        with self._lock:
            self._counts["hatali"] += record
            self._live["hatali"] += live
            if len(self.errors) < 10:
                self.errors.append(f"{t:.3f} s: {type(e).__name__}: {e}")

    def wait_idle(self) -> None:
        """Until the worker has handled every frame offered so far."""
        self._queue.join()

    def counts(self) -> dict:
        with self._lock:
            ms = list(self._ms)
            return dict(self._counts) | {
                "ilk_t": min(self._times) if self._times else math.nan,
                "son_t": max(self._times) if self._times else math.nan,
                "yazma_ms_ort": float(np.mean(ms)) if ms else math.nan,
                "yazma_ms_maks": float(np.max(ms)) if ms else math.nan,
                "hatalar": list(self.errors),
            }

    def stream_counts(self) -> dict:
        """Grid frames picked for the stream, skipped (a newer one waited, the queue was full) and failed."""
        with self._lock:
            return dict(self._live)

    def close(self, timeout: float = STOP_TIMEOUT) -> dict:
        """Let the worker finish the queued frames, then the recording's books."""
        try:
            self._queue.put(None, timeout=timeout)
        except queue.Full:
            self.errors.append("yazıcı kuyruğu boşalmadı")
        self._thread.join(timeout)
        if self._thread.is_alive():
            self.errors.append(f"yazıcı {timeout:.0f} s içinde bitmedi")
        return self.counts()


# --- frames from the model process' subscription --------------------------------------------------------------------

# [frames] in the shared ring: a slot is written again 8 / 15 s later, more than the recorder's queue holds
SHARE_SLOTS = QUEUE_FRAMES + 2
SHARE_SLOT_BYTES = 10 * 2**20  # [bytes] one camera message (2304x1296 RGB: 8.96 MB)


class FrameShare:
    """The camera messages the model process receives anyway, handed to the recorder process: the model process' frame
    reader copies every grid frame into a shared-memory ring (FrameTap) and says so on a queue; the recorder copies it
    out (ShareReader). The camera then has one 9 MB x 30 Hz subscriber less: that subscription alone cost the RTF
    ~0.06 (implementation/gorev-grubu-11.md). Made in the main process before both processes start (shared memory
    crosses into a spawned process only as one of its arguments): tap() goes to algilama.ModelProcess, the share
    itself to FrameRecorder."""

    def __init__(self, slots: int = SHARE_SLOTS, slot_bytes: int = SHARE_SLOT_BYTES) -> None:
        ctx = mp.get_context("spawn")
        self.slots, self.slot_bytes = slots, slot_bytes
        self.buffer = ctx.RawArray("B", slots * slot_bytes)
        self.seqs = ctx.RawArray("q", slots)  # seqlock per slot: -1 being written, n: holds shared frame n
        self.queue = ctx.Queue()  # (slot, n, bytes, arrival) per shared frame; None: no more frames

    def tap(self) -> "FrameTap":
        return FrameTap(self)


class FrameTap:
    """Writer side of FrameShare, in the model process: offer() every camera message from its frame reader's thread;
    the grid frames (GridPicker, all of the run) go into the ring. Never raises: the model's frames come first."""

    def __init__(self, share: FrameShare) -> None:
        self._share = share
        self._picker: GridPicker | None = None  # made in the model process, like the view
        self._view: memoryview | None = None
        self._n = 0
        self.counts = {"paylasilan": 0, "buyuk": 0, "hata": 0}
        self.errors: list[str] = []

    def offer(self, raw: bytes, arrival: float) -> None:
        """A camera message; arrival [s monotonic]: when the model process received it."""
        share = self._share
        try:
            if self._view is None:
                self._view, self._picker = memoryview(share.buffer).cast("B"), GridPicker()
            if self._picker.pick(goruntu.stamp(raw[: goruntu.HEAD_BYTES]), -math.inf, math.nan) is None:
                return
            if len(raw) > share.slot_bytes:  # another camera: the recorder subscribes itself
                self.counts["buyuk"] += 1
                if self.counts["buyuk"] == 1:
                    share.queue.put_nowait(None)
                return
            if self.counts["buyuk"]:
                return
            self._n += 1
            k = self._n % share.slots
            share.seqs[k] = -1
            self._view[k * share.slot_bytes : k * share.slot_bytes + len(raw)] = raw
            share.seqs[k] = self._n
            share.queue.put_nowait((k, self._n, len(raw), arrival))
            self.counts["paylasilan"] += 1
        except Exception as e:  # noqa: BLE001 - counted; the model's reader goes on
            self.counts["hata"] += 1
            if len(self.errors) < 10:
                self.errors.append(f"{type(e).__name__}: {e}")

    def close(self) -> dict:
        """No more frames (the model process stops); its books."""
        self._share.queue.put(None)
        return dict(self.counts) | {"hatalar": list(self.errors)}


class ShareReader:
    """Reader side of FrameShare, in the recorder process: a thread hands each shared frame on without copying it,
    on_frame(view, arrival, valid): `view` is the message in the ring, valid() says whether its slot still holds it
    (seqlock: the user checks it after reading, so a frame written over meanwhile is dropped, never used torn). A
    frame already written over when its notice comes is dropped and counted here. `ended` is set once the model
    process sends no more."""

    def __init__(self, share: FrameShare, on_frame: Callable[[memoryview, float, Callable[[], bool]], None]) -> None:
        self._share = share
        self._view = memoryview(share.buffer).cast("B")
        self._on_frame = on_frame
        self._lock = threading.Lock()
        self._counts = {"alinan": 0, "ezilen": 0, "hata": 0}
        self.ended = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="tez-paylasilan-kareler", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        share = self._share
        while not self._stop.is_set():
            try:
                item = share.queue.get(timeout=0.2)
            except queue.Empty:
                continue
            except (EOFError, OSError):
                break
            if item is None:
                break
            k, n, size, arrival = item
            if share.seqs[k] != n:
                with self._lock:
                    self._counts["ezilen"] += 1
                continue
            start = k * share.slot_bytes
            try:
                self._on_frame(self._view[start : start + size], arrival, lambda k=k, n=n: share.seqs[k] == n)
            except Exception:  # noqa: BLE001 - counted; FrameSink counts its own errors
                with self._lock:
                    self._counts["hata"] += 1
                continue
            with self._lock:
                self._counts["alinan"] += 1
        self.ended.set()

    def counts(self) -> dict:
        with self._lock:
            return dict(self._counts) | {"bitti": self.ended.is_set()}

    def close(self) -> dict:
        self._stop.set()
        self._thread.join(2.0)
        return self.counts()


# --- the recorder process (scenario runs) ---------------------------------------------------------------------------


def _cpu_s() -> float:
    """[s] CPU time of this process so far, every thread (the worker, gz-transport, GStreamer's encoder)."""
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime


class _CpuWindow:
    """This process' CPU over the recording window: sampled when the main process opens and closes it."""

    def __init__(self) -> None:
        self.wall0, self.cpu0 = time.monotonic(), _cpu_s()
        self.window: list[tuple[float, float]] = []  # (wall, cpu) at the start and the end of the window

    def poll(self, start: float, end: float) -> None:
        if len(self.window) == 0 and math.isfinite(start) or len(self.window) == 1 and math.isfinite(end):
            self.window.append((time.monotonic(), _cpu_s()))

    def books(self) -> dict:
        wall, cpu = time.monotonic() - self.wall0, _cpu_s() - self.cpu0
        out = {"pid": os.getpid(), "cpu_s": cpu, "duvar_s": wall, "cekirdek": cpu / wall if wall > 0 else math.nan}
        if len(self.window) == 2:
            (w0, c0), (w1, c1) = self.window
            out |= {"pencere_cpu_s": c1 - c0, "pencere_duvar_s": w1 - w0}
            out["pencere_cekirdek"] = (c1 - c0) / (w1 - w0) if w1 > w0 else math.nan
        return out


def recorder_process(
    folder: str | None,
    topic: str,
    start: "mp.sharedctypes.Synchronized",
    end: "mp.sharedctypes.Synchronized",
    messages: "mp.Queue",
    stop: "mp.synchronize.Event",
    qgc: bool = False,
    box_port: int = BOX_PORT,
    stream_port: int = STREAM_PORT,
    share: FrameShare | None = None,
) -> None:
    """Entry of the recorder process: ("hazir", info) or ("hata", text), then ("bitti", books) once `stop` is set.
    share: the frames come from the model process (FrameShare); once it sends no more (the model stops when the
    recording ends) the process subscribes to the camera itself if it still needs frames (the stream during the
    landing, or a recording window still open)."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # Ctrl+C: the main process stops it, so the books still come
    os.nice(RECORDER_NICE)
    cv2.setNumThreads(1)
    cpu = _CpuWindow()
    listener = stream = reader = None
    own: list[float] = []  # [s monotonic] when this process subscribed to the camera itself
    try:
        from gz.transport13 import Node, SubscribeOptions

        if qgc:
            listener = BoxListener(box_port)
            stream = LiveStream(listener.latest, port=stream_port)
        sink = FrameSink(Path(folder) if folder is not None else None, stream=stream)
        node = Node()

        def on_image(raw: bytes, _info: object) -> None:
            sink.offer(raw, start.value, end.value)

        def subscribe() -> None:
            if not node.subscribe_raw(topic, on_image, goruntu.IMAGE_TYPE, SubscribeOptions()):
                raise RuntimeError(f"{topic} konusuna abone olunamadı")
            own.append(time.monotonic())

        if share is not None:
            reader = ShareReader(share, lambda raw, arrival, ok: sink.offer(raw, start.value, end.value, arrival, ok))
        else:
            subscribe()
    except Exception:  # noqa: BLE001 - the main process reports it and starts nothing
        for part in (stream, listener, reader):
            if part is not None:
                part.close()
        messages.put(("hata", traceback.format_exc(limit=3)))
        return
    source = "model süreci (paylaşılan bellek)" if share is not None else "kendi aboneliği"
    info = {"konu": topic, "klasor": folder, "pid": os.getpid(), "yayin": stream.target if stream else None}
    messages.put(("hazir", info | {"kaynak": source}))
    problems: list[str] = []
    while not stop.wait(0.2):
        cpu.poll(start.value, end.value)
        if reader is not None and reader.ended.is_set() and not own and (qgc or math.isnan(end.value)):
            try:
                subscribe()
            except Exception as e:  # noqa: BLE001 - reported with the books
                problems.append(f"kendi aboneliğine geçilemedi: {e}")
                own.append(math.nan)
    if own and math.isfinite(own[0]):
        node.unsubscribe(topic)
    books = sink.close()
    books["kaynak"] = source
    if reader is not None:
        books["paylasim"] = reader.close() | {"kendi_aboneligi_s": own[0] - cpu.wall0 if own else None}
    if stream is not None:
        books["yayin"] = sink.stream_counts() | stream.close() | {"kutu_mesaji": listener.counts()}
        listener.close()
    books["surec"] = cpu.books()
    books["hatalar"] = books.get("hatalar", []) + problems
    messages.put(("bitti", books))


class FrameRecorder:
    """The recorder process seen from the main process (senaryo.py). folder: kareler/ of the run (None: no kosu.mp4
    frames); qgc: also the live stream to QGC, with the boxes from BoxSender on box_port; share: the frames come from
    the model process (its tap() went to algilama.ModelProcess), else the process subscribes to the camera itself."""

    def __init__(
        self,
        folder: Path | None,
        topic: str = goruntu.CAMERA_TOPIC,
        qgc: bool = False,
        box_port: int = BOX_PORT,
        stream_port: int = STREAM_PORT,
        share: FrameShare | None = None,
    ) -> None:
        ctx = mp.get_context("spawn")
        self.folder = folder
        self.qgc = qgc
        self._start = ctx.Value("d", math.nan)
        self._end = ctx.Value("d", math.nan)
        self._stop = ctx.Event()
        self._messages = ctx.Queue()
        self._proc = ctx.Process(
            target=recorder_process,
            args=(
                str(folder) if folder is not None else None,
                topic,
                self._start,
                self._end,
                self._messages,
                self._stop,
                qgc,
                box_port,
                stream_port,
                share,
            ),
            name="tez-video-kareleri",
            daemon=True,
        )
        self.books: dict | None = None

    def start(self, timeout: float = READY_TIMEOUT) -> dict:
        """Start the process and wait until it listens to the camera; RecorderError if it does not come up."""
        self._proc.start()
        try:
            kind, payload = self._messages.get(timeout=timeout)
        except queue.Empty:
            self._end_process()
            raise RecorderError(f"video kare kaydedicisi / yayın {timeout:.0f} s içinde açılmadı") from None
        if kind == "hata":
            self._end_process()
            raise RecorderError(f"video kare kaydedicisi / yayın açılamadı: {payload}")
        return payload

    def begin(self, t: float) -> None:
        """Keep frames from sim time t on."""
        self._start.value = t

    def end(self, t: float) -> None:
        """Keep no frame after sim time t."""
        self._end.value = t

    def stop(self, timeout: float = STOP_TIMEOUT) -> dict:
        """Stop the process and return its books ({"hata": ...} if they never came). Repeatable."""
        if self.books is not None:
            return self.books
        if self._proc.pid is None:
            self.books = {"hata": "kaydedici başlatılmadı"}
            return self.books
        self._stop.set()
        try:
            kind, payload = self._messages.get(timeout=timeout)
            self.books = payload if kind == "bitti" else {"hata": str(payload)}
        except queue.Empty:
            self.books = {"hata": f"kaydedici {timeout:.0f} s içinde defterini göndermedi"}
        self._end_process()
        return self.books

    def _end_process(self) -> None:
        self._proc.join(10)
        if self._proc.is_alive():
            self._proc.terminate()
            self._proc.join(5)
            if self._proc.is_alive():
                self._proc.kill()
                self._proc.join(5)


# --- standalone: goruntu_yayini.py --qgc [--model <file>] ----------------------------------------------------------


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--qgc",
        action="store_true",
        help=f"QGroundControl'e canlı video: H.264 RTP, udp://{STREAM_HOST}:{STREAM_PORT} (tek başına gerekli)",
    )
    ap.add_argument("--model", metavar="YOL", help="kendi algılayıcısı: bu .pt dosyasının kutuları çizilir")
    ap.add_argument("--imgsz", type=int, metavar="PX", help="model giriş boyutu; varsayılan .pt'deki eğitim değeri")
    ap.add_argument("--conf", type=float, default=0.25, help="güven eşiği (0..1]; varsayılan 0.25")
    ap.add_argument("--sinif", metavar="AD|NO", help="sınıf adı veya numarası; varsayılan adı 'person' olan")
    ap.add_argument("--cekirdek", type=int, default=4, help="modelin torch iş parçacığı sayısı; varsayılan 4")
    return ap


def _model_file(args: argparse.Namespace) -> algilama.ModelFile | None:
    """The detector's file (checked like senaryo.py does), None without --model; ValueError / FileNotFoundError /
    ModuleNotFoundError say what is wrong."""
    if not 0.0 < args.conf <= 1.0 or args.cekirdek < 1 or (args.imgsz is not None and args.imgsz < 32):
        raise ValueError("--conf (0..1], --cekirdek >= 1, --imgsz >= 32 olmalı")
    if args.model is None:
        return None
    model = algilama.inspect_model(Path(args.model).expanduser(), algilama.load_catalog())
    if importlib.util.find_spec("ultralytics") is None:  # only the model process imports it
        raise ModuleNotFoundError("ultralytics kurulu değil: tez/env/model-requirements.txt (tez/env/VERSIONS.md)")
    return model


def _say(text: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not args.qgc:
        print(
            "Tek başına çalışmada bu araç yalnız QGC'ye canlı yayın yapar: --qgc ile çalıştırın (senaryo koşusunda "
            "yayını senaryo.py --qgc açar).",
            file=sys.stderr,
        )
        return 2
    try:
        model_file = _model_file(args)
    except (ValueError, FileNotFoundError, ModuleNotFoundError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    cv2.setNumThreads(1)
    boxes = LatestBoxes()
    try:
        stream = LiveStream(boxes.latest, standalone=True)
    except (RecorderError, ImportError, ValueError) as e:
        print(f"Yayın açılamadı: {e}", file=sys.stderr)
        return 2
    from gz.transport13 import Node, SubscribeOptions

    sink = FrameSink(None, stream=stream)
    node = Node()
    if not node.subscribe_raw(
        goruntu.CAMERA_TOPIC,
        lambda raw, _i: sink.offer(raw, math.nan, math.nan),
        goruntu.IMAGE_TYPE,
        SubscribeOptions(),
    ):
        print(f"{goruntu.CAMERA_TOPIC} konusuna abone olunamadı", file=sys.stderr)
        stream.close()
        return 2
    _say(f"Canlı yayın: {goruntu.CAMERA_TOPIC} -> H.264 RTP {stream.target} (1280x720, {FPS} kare/sim-s)")
    _say("QGC 5.1.4: Uygulama Ayarları -> Video -> Kaynak 'UDP h.264 Video Stream', port 5600")
    _say(f"QGC'siz: ffplay {FFPLAY_OPTIONS} -i {Path(__file__).resolve().parent / 'yayin.sdp'}")
    model, code = None, 0
    try:
        if model_file is not None:
            settings = algilama.ModelSettings(model_file.path, args.imgsz, args.conf, args.sinif, args.cekirdek)
            model = algilama.ModelProcess(settings, lambda r, _alinma: boxes.put(standalone_message(r)))
            _say(
                f"Model açılıyor: {model_file.path.name} (sha256 {model_file.sha256[:12]}…), CPU, "
                f"{args.cekirdek} çekirdek"
            )
            info = model.start()
            _say(
                f"Model hazır: sınıf {info['sinif']} ({info['sinif_adi']}), imgsz {info['imgsz']}, conf {info['conf']}"
            )
        else:
            _say("Model yok (--model verilmedi): kutusuz yayın")
        _say("Hakem ve hedef seçimi yok; PX4'e hiçbir şey gönderilmez. Durdurmak için Ctrl+C")
        _status_loop(sink, stream, model)
    except KeyboardInterrupt:
        _say("Durduruluyor...")
    except algilama.ModelError as e:
        print(f"Model hatası: {e}", file=sys.stderr)
        code = 2
    finally:
        node.unsubscribe(goruntu.CAMERA_TOPIC)
        if model is not None:
            model.stop()
        sink.close()
        c = stream.close()
        _say(f"Yayın bitti: {c['verilen']} kare gönderildi, {c['kutulu']} karede kutu vardı; hatalar {c['hatalar']}")
    return code


def _status_loop(sink: FrameSink, stream: LiveStream, model: algilama.ModelProcess | None) -> None:
    last = 0
    while True:
        time.sleep(STATUS_EVERY_S)
        c = stream.counts()
        if sink.counts()["kamera_karesi"] == 0:
            _say(f"Kamera karesi gelmiyor ({goruntu.CAMERA_TOPIC}): sim açık mı? (tez/sim/calistir.sh)")
            continue
        results = f"; model {model.results} kare işledi" if model is not None else ""
        _say(
            f"yayın: {c['verilen']} kare (son {STATUS_EVERY_S:.0f} s'de {(c['verilen'] - last) / STATUS_EVERY_S:.1f} "
            f"kare/s), son kare t = {c['son_t']:.1f} s{results}"
        )
        last = c["verilen"]


if __name__ == "__main__":
    sys.exit(main())
