"""Camera frames for kosu.mp4 (task group 8); the live H.264 stream to QGroundControl comes in task group 11.

The recorder runs in its own process ("spawn", like the model process): gz-transport and the JPEG work stay off the
main process, which keeps MAVLink and the referee. It subscribes to the drone camera with subscribe_raw; the callback
reads only the header of each message (goruntu.stamp) and keeps the frames that fall on the 15 fps grid of sim time
inside the recording window (GridPicker: every second camera frame). A worker thread decodes them, scales them to
1280x720 and writes JPEG (quality 90) to kareler/<t_us>.jpg. Nothing else happens during the run: video.py puts the
video together afterwards from the files, so recording costs the run little (measured in
implementation/gorev-grubu-08.md). If the worker falls behind, a full queue drops the new frame and counts it (the
video then shows the frame before for that 1/15 s); nothing piles up in memory.

The process stays out of Gazebo's and the model's way: OpenCV on one thread (by default it spreads every resize over
all cores), the scaling in two cheap steps (box filter to exactly half, then bilinear to 1280x720: 3.4 ms on one core
instead of 16 ms for a direct box filter) and a lower CPU priority (nice), so under contention it is the recorder
that drops frames, not the simulation that slows down.

    rec = FrameRecorder(out / "kareler"); rec.start()   # before the simulation, like the model process
    rec.begin(sim_time) ... rec.end(sim_time)           # the referee's recording window (senaryo.fly)
    books = rec.stop()                                  # after the simulation: what was kept, written, dropped
"""

import math
import multiprocessing as mp
import os
import queue
import signal
import threading
import time
import traceback
from collections.abc import Callable
from pathlib import Path

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")  # protobuf 7.x in ~/.local
os.environ.setdefault("GZ_IP", "127.0.0.1")  # same as calistir.sh

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import goruntu  # noqa: E402

FPS = 15  # [frames per s of sim time] of kosu.mp4: every second frame of the 30 Hz camera
GRID_TOLERANCE = 0.3  # [slots] a frame within 0.3 / 15 s = 20 ms of a grid time takes that slot (frames: 32/36 ms)
FRAME_SIZE = (1280, 720)  # [px] width, height of a kept frame (the video's camera panel)
JPEG_QUALITY = 90
FRAMES_DIR = "kareler"
QUEUE_FRAMES = 6  # raw 9 MB messages waiting for the writer; one more is dropped and counted
RECORDER_NICE = 5  # lower CPU priority of the recorder process than Gazebo, PX4 and the model
READY_TIMEOUT = 30.0  # [s] for the recorder process to come up
STOP_TIMEOUT = 60.0  # [s] for its writer to empty the queue at the end


def frame_name(t: float) -> str:
    """File name of a kept frame: its sim time in microseconds, zero padded (sorts in time)."""
    return f"{round(t * 1e6):012d}.jpg"


def frame_time(path: Path) -> float:
    """[s sim] capture time of a kept frame from its file name."""
    return int(path.stem) / 1e6


def write_jpeg(rgb: np.ndarray, path: Path) -> None:
    """One camera frame (RGB, any size) -> FRAME_SIZE JPEG; written to a temporary name and renamed, so a stopped run
    never leaves half a file under a frame's name. Scaling: box filter to half the size (the fast integer case, no
    aliasing), then bilinear to FRAME_SIZE."""
    half = cv2.resize(rgb, (rgb.shape[1] // 2, rgb.shape[0] // 2), interpolation=cv2.INTER_AREA)
    small = cv2.resize(half, FRAME_SIZE, interpolation=cv2.INTER_LINEAR)
    ok, data = cv2.imencode(".jpg", cv2.cvtColor(small, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise RuntimeError(f"{path.name}: JPEG kodlanamadı")
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(data.tobytes())
    tmp.replace(path)


def write_message(raw: bytes, path: Path) -> None:
    """A serialized drone camera message -> JPEG (the pixels are decoded only here, in the writer thread)."""
    write_jpeg(goruntu.decode(raw, goruntu.Arrival(0, 0.0, b"")).rgb, path)


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


class FrameSink:
    """The recorder without gz-transport: offer() every camera message (transport thread, returns at once), a worker
    thread writes the kept ones; close() waits for it and returns the books."""

    def __init__(
        self,
        folder: Path,
        queue_frames: int = QUEUE_FRAMES,
        write: Callable[[bytes, Path], None] = write_message,
    ) -> None:
        self.folder = folder
        folder.mkdir(parents=True, exist_ok=True)
        self._write = write
        self._picker = GridPicker()
        self._queue: queue.Queue[tuple[float, bytes] | None] = queue.Queue(maxsize=queue_frames)
        self._lock = threading.Lock()
        self._counts = {"kamera_karesi": 0, "secilen": 0, "yazilan": 0, "dusen": 0, "hatali": 0}
        self._times: list[float] = []  # [s sim] written frames
        self._ms: list[float] = []  # [ms wall] decode + scale + JPEG + write per frame
        self.errors: list[str] = []
        self._thread = threading.Thread(target=self._work, name="tez-video-yazici", daemon=True)
        self._thread.start()

    def offer(self, raw: bytes, start: float, end: float) -> None:
        with self._lock:
            self._counts["kamera_karesi"] += 1
            t = goruntu.stamp(raw[: goruntu.HEAD_BYTES])
            if self._picker.pick(t, start, end) is None:
                return
            self._counts["secilen"] += 1
        try:
            self._queue.put_nowait((t, raw))
        except queue.Full:
            with self._lock:
                self._counts["dusen"] += 1

    def _work(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            t, raw = item
            t0 = time.perf_counter()
            try:
                self._write(raw, self.folder / frame_name(t))
            except Exception as e:  # noqa: BLE001 - one bad frame must not end the recording; counted and reported
                with self._lock:
                    self._counts["hatali"] += 1
                    if len(self.errors) < 10:
                        self.errors.append(f"{t:.3f} s: {type(e).__name__}: {e}")
                continue
            with self._lock:
                self._counts["yazilan"] += 1
                self._times.append(t)
                self._ms.append((time.perf_counter() - t0) * 1000.0)

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

    def close(self, timeout: float = STOP_TIMEOUT) -> dict:
        """Let the writer finish the queued frames, then the books."""
        try:
            self._queue.put(None, timeout=timeout)
        except queue.Full:
            self.errors.append("yazıcı kuyruğu boşalmadı")
        self._thread.join(timeout)
        if self._thread.is_alive():
            self.errors.append(f"yazıcı {timeout:.0f} s içinde bitmedi")
        return self.counts()


def recorder_process(
    folder: str,
    topic: str,
    start: "mp.sharedctypes.Synchronized",
    end: "mp.sharedctypes.Synchronized",
    messages: "mp.Queue",
    stop: "mp.synchronize.Event",
) -> None:
    """Entry of the recorder process: ("hazir", info) or ("hata", text), then ("bitti", books) once `stop` is set."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # Ctrl+C: the main process stops it, so the books still come
    os.nice(RECORDER_NICE)
    cv2.setNumThreads(1)
    try:
        from gz.transport13 import Node, SubscribeOptions

        sink = FrameSink(Path(folder))
        node = Node()

        def on_image(raw: bytes, _info: object) -> None:
            sink.offer(raw, start.value, end.value)

        if not node.subscribe_raw(topic, on_image, goruntu.IMAGE_TYPE, SubscribeOptions()):
            raise RuntimeError(f"{topic} konusuna abone olunamadı")
    except Exception:  # noqa: BLE001 - the main process reports it and records no frames
        messages.put(("hata", traceback.format_exc(limit=3)))
        return
    messages.put(("hazir", {"konu": topic, "klasor": folder, "pid": os.getpid()}))
    while not stop.wait(0.2):
        pass
    node.unsubscribe(topic)
    messages.put(("bitti", sink.close()))


class FrameRecorder:
    """The recorder process seen from the main process (senaryo.py)."""

    def __init__(self, folder: Path, topic: str = goruntu.CAMERA_TOPIC) -> None:
        ctx = mp.get_context("spawn")
        self.folder = folder
        self._start = ctx.Value("d", math.nan)
        self._end = ctx.Value("d", math.nan)
        self._stop = ctx.Event()
        self._messages = ctx.Queue()
        self._proc = ctx.Process(
            target=recorder_process,
            args=(str(folder), topic, self._start, self._end, self._messages, self._stop),
            name="tez-video-kareleri",
            daemon=True,
        )
        self.books: dict | None = None

    def start(self, timeout: float = READY_TIMEOUT) -> dict:
        """Start the process and wait until it listens to the camera; RuntimeError if it does not come up."""
        self._proc.start()
        try:
            kind, payload = self._messages.get(timeout=timeout)
        except queue.Empty:
            self._end_process()
            raise RuntimeError(f"video kare kaydedicisi {timeout:.0f} s içinde açılmadı") from None
        if kind == "hata":
            self._end_process()
            raise RuntimeError(f"video kare kaydedicisi açılamadı: {payload}")
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
