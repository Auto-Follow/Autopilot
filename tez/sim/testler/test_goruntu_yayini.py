"""Camera frames for kosu.mp4 and the live stream to QGroundControl (goruntu_yayini.py) without Gazebo: which frames
are kept (the 15 fps grid of sim time inside the recording window, every second camera frame), the JPEG of a frame,
that a busy writer drops and counts frames instead of piling them up; the boxes the main process sends on UDP 5610
(the model result and the referee's box of that frame), the H.264 RTP pipeline and its frames with the boxes drawn, the
standalone mode (its own detector, no referee, no LOS) and the one worker that serves the stream and the recording."""

import dataclasses
import json
import math
import multiprocessing as mp
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np
import pytest
from gz.msgs10.image_pb2 import Image

import algilama
import goruntu
import goruntu_yayini
import takip
import video

ARACLAR = Path(goruntu_yayini.__file__).resolve().parent


def camera_times(start: float, end: float) -> list[float]:
    """Drone camera stamps: 30 Hz on the 4 ms physics step, so 32 / 36 ms apart (3 frames per 100 ms)."""
    return [round(round(k / 30 / 0.004) * 0.004, 3) for k in range(math.ceil(start * 30), math.floor(end * 30) + 1)]


def image_bytes(t: float, width: int = 8, height: int = 4, colour: tuple[int, int, int] = (0, 0, 0)) -> bytes:
    """A serialized gz.msgs.Image like the drone camera's (R8G8B8, header stamp first)."""
    msg = Image(width=width, height=height, step=3 * width, pixel_format_type=3)
    msg.header.stamp.sec, msg.header.stamp.nsec = int(t), round((t - int(t)) * 1e9)
    msg.data = np.tile(np.array(colour, np.uint8), width * height).tobytes()
    return msg.SerializeToString()


def test_frames_on_the_15_fps_grid_of_sim_time_inside_the_window() -> None:
    """The frame nearest every 1/15 s of sim time (within 20 ms) is kept: every second camera frame, slots without a
    gap; nothing before the window starts (start NaN = not yet) or after it ends. A frame lost in transport leaves
    its slot empty and does not shift the others."""
    times = camera_times(0.9, 2.1)
    picker = goruntu_yayini.GridPicker()
    assert all(picker.pick(t, math.nan, math.nan) is None for t in times[:10])  # the window has not started
    picker = goruntu_yayini.GridPicker()
    kept = [(t, slot) for t in times if (slot := picker.pick(t, 1.0, 2.0)) is not None]
    assert [slot for _, slot in kept] == list(range(15, 31))
    assert all(abs(t - slot / 15) <= 0.020 for t, slot in kept)
    assert set(np.diff([times.index(t) for t, _ in kept])) == {2}  # every second frame

    lost = [t for t in times if abs(t - 20 / 15) > 0.020]  # the frame of slot 20 never arrived
    picker = goruntu_yayini.GridPicker()
    slots = [slot for t in lost if (slot := picker.pick(t, 1.0, math.nan)) is not None]  # end NaN: still open
    assert 20 not in slots and slots[:5] == [15, 16, 17, 18, 19] and slots[5:8] == [21, 22, 23]


def test_jpeg_of_a_camera_frame(tmp_path: Path) -> None:
    """2304x1296 RGB -> 1280x720 JPEG (quality 90) named by the frame's sim time in microseconds; colours stay where
    they are (RGB in, the file is a normal JPEG)."""
    rgb = np.zeros((1296, 2304, 3), np.uint8)
    rgb[:, :1152] = (200, 30, 30)  # left half red
    path = tmp_path / goruntu_yayini.frame_name(61.068)
    goruntu_yayini.write_jpeg(rgb, path)
    img = cv2.imread(str(path))  # BGR
    assert img.shape == (720, 1280, 3)
    assert abs(int(img[360, 300, 2]) - 200) < 8 and abs(int(img[360, 300, 0]) - 30) < 8
    assert img[360, 1000].max() < 10
    assert path.name == "000061068000.jpg" and goruntu_yayini.frame_time(path) == pytest.approx(61.068)
    assert not list(tmp_path.glob("*.tmp"))  # written whole, then renamed


def test_sink_writes_the_window_and_drops_when_the_writer_is_busy(tmp_path: Path) -> None:
    """FrameSink (the recorder process without gz-transport): grid frames inside the window become JPEGs; while the
    writer is stuck, a full queue drops new frames and counts them, the transport thread never waits."""
    sink = goruntu_yayini.FrameSink(tmp_path / "kareler", queue_frames=16)  # the test offers them all at once
    for t in camera_times(0.9, 1.6):
        sink.offer(image_bytes(t, colour=(10, 200, 10)), 1.0, 1.5)
    books = sink.close()
    files = sorted((tmp_path / "kareler").glob("*.jpg"))
    assert [round(goruntu_yayini.frame_time(f) * 15) for f in files] == list(range(15, 23))
    assert books["kamera_karesi"] == len(camera_times(0.9, 1.6)) and books["secilen"] == books["yazilan"] == 8
    assert books["dusen"] == 0 and books["hatali"] == 0
    assert books["ilk_t"] == pytest.approx(1.0) and books["son_t"] == pytest.approx(1.468)

    release = threading.Event()
    started = threading.Event()

    def stuck(frame: np.ndarray, path: Path) -> None:
        started.set()
        release.wait(5.0)
        path.write_bytes(frame.tobytes())

    busy = goruntu_yayini.FrameSink(tmp_path / "dolu", queue_frames=2, save=stuck)
    grid = [k / 15 for k in range(30, 36)]  # six frames on the grid
    busy.offer(image_bytes(grid[0]), 0.0, math.nan)
    assert started.wait(5.0)  # the writer holds the first one
    for t in grid[1:]:
        busy.offer(image_bytes(t), 0.0, math.nan)
    release.set()
    books = busy.close()
    assert books["secilen"] == 6 and books["yazilan"] == 3 and books["dusen"] == 3


# --- live stream (task group 11) ------------------------------------------------------------------------------------

# one processed model frame as the main process sends it: two boxes, the first one chosen, the referee's box of the
# target in the same frame (pixel edges in the 2304x1296 camera image)
MSG = goruntu_yayini.BoxMessage(
    t=61.068,
    boxes=((1000.0, 500.0, 1060.0, 680.0, 0.83), (300.0, 400.0, 350.0, 560.0, 0.41)),
    chosen=0,
    state="izleme",
    no_target=False,
    referee=(1002.5, 498.0, 1061.0, 684.0),
)


def wait_for(condition: Callable[[], bool], timeout: float = 3.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.01)
    return condition()


def kutu(u0: float, v0: float, u1: float, v1: float, guven: float = 0.8) -> algilama.Kutu:
    return algilama.Kutu(u0, v0, u1, v1, guven, 0, "Person")


def model_result(t: float, boxes: list[algilama.Kutu]) -> algilama.FrameResult:
    return algilama.FrameResult(t, round(t * 30), 1000.0, 1000.01, 1000.1, 1.4, 0.0, 85.0, tuple(boxes), ())


def test_boxes_reach_the_stream_on_udp_5610_and_bad_messages_are_refused(tmp_path: Path) -> None:
    """Spec 10: in a scenario run the main process sends, per processed model frame, its boxes, the chosen one and the
    referee's box of the target in that same frame as one JSON datagram to 127.0.0.1:5610. Both ends check it (two-sided
    validation): nothing non-finite, out of range or unknown is sent or drawn, and each refusal is counted."""
    assert (goruntu_yayini.BOX_HOST, goruntu_yayini.BOX_PORT) == ("127.0.0.1", 5610)
    data = goruntu_yayini.pack(MSG)
    assert goruntu_yayini.unpack(data) == MSG
    sent = json.loads(data)
    assert sent["t"] == 61.068 and sent["kutular"][0] == [1000.0, 500.0, 1060.0, 680.0, 0.83]
    assert sent["secilen"] == 0 and sent["hakem"] == [1002.5, 498.0, 1061.0, 684.0] and sent["hedef_yok"] is False

    nan, refused = math.nan, dataclasses.replace
    for bad in (
        refused(MSG, t=math.inf),
        refused(MSG, boxes=((nan, 500.0, 1060.0, 680.0, 0.8),)),
        refused(MSG, boxes=((1000.0, 500.0, 1060.0, 680.0, 1.5),)),  # confidence over 1
        refused(MSG, chosen=2),  # no third box
        refused(MSG, referee=(1061.0, 498.0, 1002.5, 684.0)),  # right edge left of the left one
    ):
        with pytest.raises(ValueError):
            goruntu_yayini.pack(bad)
    for raw in (
        b"{",
        b"[]",
        json.dumps(sent | {"fazla": 1}).encode(),
        json.dumps({k: v for k, v in sent.items() if k != "t"}).encode(),
        data.replace(b"61.068", b"NaN"),
        json.dumps(sent | {"kutular": [[1, 1, 2, 2, 0.5]] * (goruntu_yayini.MAX_BOXES + 1), "secilen": None}).encode(),
        b" " * (goruntu_yayini.MAX_MESSAGE_BYTES + 1),
    ):
        with pytest.raises(ValueError):
            goruntu_yayini.unpack(raw)

    listener = goruntu_yayini.BoxListener(port=0)  # any free port; the run uses BOX_PORT
    sender = goruntu_yayini.BoxSender(port=listener.port)
    other = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        other.sendto(b"bozuk", ("127.0.0.1", listener.port))
        assert sender.send(MSG) == "gonderildi"
        assert wait_for(lambda: listener.latest() == MSG)
        heard = listener.counts()
        assert (heard["alinan"], heard["gecersiz"]) == (1, 1) and len(heard["hatalar"]) == 1
        assert sender.send(refused(MSG, chosen=5)) == "gecersiz"
        assert sender.counts() == {"gonderildi": 1, "gecersiz": 1, "hata": 0}
    finally:
        other.close()
        sender.close()
        listener.close()

    # the tracking side builds the message of every processed frame: its boxes, the selection's choice, the referee's
    # box of the same frame; "HEDEF YOK" when the frame's TEZ_LOS says no target
    clock = goruntu.SimClock()
    for k in range(1001):
        clock.add(sim=60.0 + k * 0.01, wall=1000.0 + k * 0.01)
    got: list[goruntu_yayini.BoxMessage] = []
    tr = takip.Tracker("model", clock, tmp_path, None, camera=lambda: None, now=lambda: 1001.2, overlay=got.append)
    target = (1000.0, 500.0, 1060.0, 680.0)
    row = {"t": 61.0, "gorunur": True, "los_govde_x": 0.7, "los_govde_y": 0.0, "los_govde_z": 0.7}
    row |= dict(zip(("hedef_kutu_u0", "hedef_kutu_v0", "hedef_kutu_u1", "hedef_kutu_v1"), target, strict=True))
    tr.on_referee(61.0, row, 1001.05)
    tr.wait_idle()
    tr.on_model(model_result(61.0, [kutu(300, 400, 350, 560, 0.9), kutu(1002, 498, 1061, 684, 0.7)]), 1001.12)
    tr.on_model(model_result(61.1, []), 1001.22)
    tr.close()
    assert got[0] == goruntu_yayini.BoxMessage(
        61.0, ((300, 400, 350, 560, 0.9), (1002, 498, 1061, 684, 0.7)), 1, "ilk_kilit", False, target
    )
    assert got[1] == goruntu_yayini.BoxMessage(61.1, (), None, "eslesmedi", True, None)  # no referee row for 61.1 s

    # no model (--modelsiz) with the referee's LOS: the stream gets the referee's box of every camera frame
    got.clear()
    tr = takip.Tracker("hakem", clock, tmp_path, None, camera=lambda: None, now=lambda: 1001.2, overlay=got.append)
    tr.on_referee(61.0, row, 1001.05)
    tr.on_referee(61.032, row | {"t": 61.032, "gorunur": False}, 1001.08)
    tr.wait_idle()
    tr.close()
    assert got == [
        goruntu_yayini.BoxMessage(61.0, (), None, "hakem", False, target),
        goruntu_yayini.BoxMessage(61.032, (), None, "hakem", True, target),
    ]


def free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def near_colour(img: np.ndarray, u: float, v: float, bgr: tuple[int, int, int], tolerance: int = 70) -> bool:
    """A pixel within 3 px of (u, v) close to the colour (H.264 blurs a thin line a little)."""
    patch = img[round(v) - 3 : round(v) + 4, round(u) - 3 : round(u) + 4].astype(int)
    return bool((np.abs(patch - np.array(bgr)).max(axis=2) <= tolerance).any())


def test_live_stream_is_the_spec_pipeline_and_its_frames_arrive_with_the_boxes(tmp_path: Path) -> None:
    """Spec 10: appsrc (BGR 1280x720 15/1, live) -> queue leaky=downstream max-size-buffers=2 -> videoconvert (I420) ->
    x264enc zerolatency ultrafast 2000 kbit/s key-int-max=15, constrained-baseline -> rtph264pay config-interval=1 pt=96
    mtu=1400 -> udpsink 127.0.0.1:5600 sync=false; yayin.sdp describes it for VLC. Then the real thing on a free port:
    frames pushed with a box message come out of an H.264 RTP receiver with the chosen box red and the referee's
    box blue where the 2304x1296 camera pixels put them."""
    desc = goruntu_yayini.pipeline_description()
    parts = [p.split() for p in desc.split(" ! ")]
    assert [p[0] for p in parts] == [
        "appsrc",
        "queue",
        "videoconvert",
        "video/x-raw,format=I420",
        "x264enc",
        "video/x-h264,profile=constrained-baseline",
        "rtph264pay",
        "udpsink",
    ]
    props = {p[0]: dict(kv.split("=", 1) for kv in p[1:]) for p in parts}
    assert props["appsrc"]["is-live"] == "true" and props["appsrc"]["format"] == "time"
    assert props["appsrc"]["caps"] == "video/x-raw,format=BGR,width=1280,height=720,framerate=15/1"
    assert props["queue"]["leaky"] == "downstream" and props["queue"]["max-size-buffers"] == "2"
    assert props["x264enc"] == {
        "tune": "zerolatency",
        "speed-preset": "ultrafast",
        "bitrate": "2000",
        "key-int-max": "15",
        "threads": "1",  # one encoder thread: ~20 % less CPU for +1.3 ms (gorev-grubu-11.md)
    }
    assert {k: props["rtph264pay"][k] for k in ("config-interval", "pt", "mtu")} == {
        "config-interval": "1",
        "pt": "96",
        "mtu": "1400",
    }
    assert {k: props["udpsink"][k] for k in ("host", "port", "sync")} == {
        "host": "127.0.0.1",
        "port": "5600",
        "sync": "false",
    }
    sdp = (ARACLAR / "yayin.sdp").read_text(encoding="ascii").splitlines()
    assert {"c=IN IP4 127.0.0.1", "m=video 5600 RTP/AVP 96", "a=rtpmap:96 H264/90000"} <= set(sdp)

    try:
        gst = goruntu_yayini.gst()
    except (ImportError, ValueError):
        pytest.skip("GStreamer (python3-gi) kurulu değil")
    needed = ("appsrc", "x264enc", "rtph264pay", "udpsrc", "rtph264depay", "avdec_h264", "appsink")
    if not all(gst.ElementFactory.find(e) for e in needed):
        pytest.skip("GStreamer öğeleri eksik (tez/env/VERSIONS.md: gstreamer1.0-plugins-ugly, gstreamer1.0-libav)")
    port = free_udp_port()
    receiver = gst.parse_launch(
        f'udpsrc port={port} caps="application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000" '
        "! rtph264depay ! avdec_h264 ! videoconvert ! video/x-raw,format=BGR ! appsink name=out sync=false"
    )
    receiver.set_state(gst.State.PLAYING)
    receiver.get_state(5 * gst.SECOND)
    message = dataclasses.replace(MSG, referee=(1500.0, 500.0, 1560.0, 680.0))  # apart from the model's box
    stream = goruntu_yayini.LiveStream(lambda: message, port=port)
    try:
        grey = np.full((720, 1280, 3), 90, np.uint8)
        for k in range(15):
            stream.show(message.t + 0.1 + k / 30, grey, 2304, time.monotonic())  # boxes 0.1-0.57 s old: fresh
            time.sleep(0.02)
        sample = receiver.get_by_name("out").emit("try-pull-sample", 5 * gst.SECOND)
        assert sample is not None
        caps = sample.get_caps().get_structure(0)
        assert (caps.get_value("width"), caps.get_value("height")) == (1280, 720)
        buf = sample.get_buffer()
        ok, mapped = buf.map(gst.MapFlags.READ)
        img = np.frombuffer(mapped.data, np.uint8).reshape(720, 1280, 3).copy()
        buf.unmap(mapped)
    finally:
        books = stream.close()
        receiver.set_state(gst.State.NULL)
    s = 1280 / 2304
    assert near_colour(img, 1000 * s, 590 * s, video.MODEL_BGR)  # the chosen box's left edge, thick red
    assert near_colour(img, 1500 * s, 590 * s, video.TARGET_BGR)  # the referee's box, blue
    assert not near_colour(img, 1280 / 2, 120, video.WARNING_BGR, 40)  # a target: no "HEDEF YOK"
    assert books["verilen"] == 15 and books["kutulu"] == 15 and books["itme_hatasi"] == 0
    assert books["hedef"] == f"udp://127.0.0.1:{port}"


def test_standalone_stream_draws_its_own_model_boxes_and_sends_no_los(capsys: pytest.CaptureFixture) -> None:
    """Spec 10, standalone (a running sim, QGC by hand): goruntu_yayini.py --qgc --model <file> draws the boxes of its
    own detector; there is no referee box, no target selection and no LOS: the stream process has no MAVLink at all."""
    r = model_result(70.0, [kutu(1000, 500, 1060, 680, 0.9), kutu(300, 400, 350, 560, 0.5)])
    msg = goruntu_yayini.standalone_message(r)
    assert msg == goruntu_yayini.BoxMessage(
        70.0, ((1000, 500, 1060, 680, 0.9), (300, 400, 350, 560, 0.5)), None, "tek", False, None
    )
    code = (
        "import sys, goruntu_yayini, video; "
        "goruntu_yayini.parser().parse_args(['--qgc', '--model', 'x.pt']); "
        "print(sorted(m for m in sys.modules if m.split('.')[0] in {'pymavlink', 'px4_baglanti', 'takip', 'senaryo'}))"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=ARACLAR, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "[]"
    assert goruntu_yayini.main(["--model", "x.pt"]) == 2  # without --qgc it starts nothing
    assert "--qgc" in capsys.readouterr().err


class Stream:
    """LiveStream stand-in: what it was shown."""

    def __init__(self) -> None:
        self.shown: list[tuple[float, tuple, int]] = []

    def show(self, t: float, frame: np.ndarray, camera_width: int, arrival: float) -> None:
        self.shown.append((t, frame.shape, camera_width))


def test_one_worker_serves_the_stream_and_the_recording(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With the stream on, every grid frame of the run is streamed (not only the recording window) and the window's
    frames are also written; each frame is read and scaled once for both. When frames wait, the stream shows only
    the newest (no lag piles up), the recording still keeps every one."""
    decoded: list[float] = []
    read = goruntu_yayini.frame_pixels
    monkeypatch.setattr(goruntu_yayini, "frame_pixels", lambda raw: decoded.append(1.0) or read(raw))

    live = Stream()
    sink = goruntu_yayini.FrameSink(tmp_path / "kareler", stream=live)
    for t in camera_times(0.9, 1.6):
        sink.offer(image_bytes(t), 1.0, 1.5)
        sink.wait_idle()
    books = sink.close()
    assert [round(t * 15) for t, *_ in live.shown] == list(range(14, 25))  # 0.933 ... 1.6 s, window or not
    assert {shape for _, shape, _ in live.shown} == {(720, 1280, 3)} and {w for *_, w in live.shown} == {8}
    files = sorted((tmp_path / "kareler").glob("*.jpg"))
    assert [round(goruntu_yayini.frame_time(f) * 15) for f in files] == list(range(15, 23))
    assert len(decoded) == 11 and books["yazilan"] == 8
    assert sink.stream_counts() == {"secilen": 11, "atlanan": 0, "hatali": 0, "ezilen": 0}

    release, started = threading.Event(), threading.Event()

    def stuck(frame: np.ndarray, path: Path) -> None:
        started.set()
        release.wait(5.0)
        path.write_bytes(b"jpeg")

    live = Stream()
    busy = goruntu_yayini.FrameSink(tmp_path / "dolu", stream=live, save=stuck)
    grid = [k / 15 for k in range(30, 34)]
    busy.offer(image_bytes(grid[0]), 0.0, math.nan)
    assert started.wait(5.0)  # shown, now the writer holds it
    for t in grid[1:]:
        busy.offer(image_bytes(t), 0.0, math.nan)
    release.set()
    books = busy.close()
    assert [round(t * 15) for t, *_ in live.shown] == [30, 33]  # 31 and 32 had a newer frame waiting behind them
    assert books["yazilan"] == 4 and busy.stream_counts()["atlanan"] == 2


def share_writer(share: goruntu_yayini.FrameShare, frames: list[bytes]) -> None:
    """The model process' side of test_the_recorder_takes_the_frames_the_model_process_receives (spawned)."""
    tap = share.tap()
    for raw in frames:
        tap.offer(raw, 1000.0)
        time.sleep(0.02)  # the camera's pace, roughly: the reader keeps up
    tap.close()


def test_the_recorder_takes_the_frames_the_model_process_receives() -> None:
    """11.6: a second subscription to the 9 MB x 30 Hz camera cost the RTF ~0.06, so the recorder takes the frames the
    model process receives anyway: every grid frame of the run (every second camera frame) crosses a spawned process
    through shared memory byte for byte; a slot written again before the reader copied it is dropped, never handed
    on torn; the end of the model process (or a frame too big for the ring) is seen, so the recorder can subscribe
    itself."""
    times = camera_times(0.9, 1.6)
    frames = [image_bytes(t, colour=(k, 7, 9)) for k, t in enumerate(times)]
    picker = goruntu_yayini.GridPicker()
    grid = [raw for raw, t in zip(frames, times, strict=True) if picker.pick(t, -math.inf, math.nan) is not None]
    assert len(grid) == 11
    share = goruntu_yayini.FrameShare(slots=4, slot_bytes=4096)
    got: list[tuple[bytes, float, bool]] = []

    def keep(view: memoryview, arrival: float, valid: Callable[[], bool]) -> None:
        got.append((bytes(view), arrival, valid()))  # read, then ask whether the slot still held it

    reader = goruntu_yayini.ShareReader(share, keep)
    proc = mp.get_context("spawn").Process(target=share_writer, args=(share, frames))
    proc.start()
    proc.join(120)
    assert proc.exitcode == 0 and reader.ended.wait(5.0)
    assert [raw for raw, *_ in got] == grid and {(a, ok) for _, a, ok in got} == {(1000.0, True)}
    assert reader.close() == {"alinan": 11, "ezilen": 0, "hata": 0, "bitti": True}

    # the reader 6 frames behind a 4-slot ring: the two oldest were written over, the rest come whole
    share = goruntu_yayini.FrameShare(slots=4, slot_bytes=4096)
    tap = share.tap()
    on_grid = [image_bytes(k / 15, colour=(k, 1, 2)) for k in range(30, 36)]
    for raw in on_grid:
        tap.offer(raw, 2000.0)
    got.clear()
    reader = goruntu_yayini.ShareReader(share, keep)
    books = tap.close()
    assert reader.ended.wait(5.0) and [raw for raw, *_ in got] == on_grid[2:]
    assert reader.close()["ezilen"] == 2 and books["paylasilan"] == 6
    # a frame written over after its notice came: valid() says so, and the worker drops it instead of using it
    share = goruntu_yayini.FrameShare(slots=2, slot_bytes=4096)
    tap = share.tap()
    held: list[tuple[memoryview, Callable[[], bool]]] = []
    reader = goruntu_yayini.ShareReader(share, lambda view, arrival, valid: held.append((view, valid)))
    tap.offer(on_grid[0], 0.0)
    assert wait_for(lambda: len(held) == 1) and held[0][1]()
    tap.offer(on_grid[1], 0.0)
    tap.offer(on_grid[2], 0.0)  # the third frame goes into the first one's slot (2 slots)
    assert wait_for(lambda: len(held) == 3) and not held[0][1]() and held[2][1]()
    sink = goruntu_yayini.FrameSink(None, stream=Stream())
    sink.offer(held[0][0], 0.0, math.nan, 0.0, held[0][1])
    sink.wait_idle()
    assert sink.stream_counts()["ezilen"] == 1 and sink.close()["hatali"] == 0
    tap.close()
    reader.close()

    # a frame bigger than a slot (another camera): nothing more is shared and the reader ends
    share = goruntu_yayini.FrameShare(slots=2, slot_bytes=64)
    tap = share.tap()
    reader = goruntu_yayini.ShareReader(share, lambda view, arrival, valid: None)
    tap.offer(image_bytes(2.0), 0.0)
    assert reader.ended.wait(5.0) and tap.counts["buyuk"] == 1 and tap.counts["paylasilan"] == 0
