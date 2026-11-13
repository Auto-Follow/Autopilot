"""Camera frames for kosu.mp4 (goruntu_yayini.py) without Gazebo: which frames are kept (the 15 fps grid of sim time
inside the recording window, every second camera frame), the JPEG of a frame, and that a busy writer drops and counts
frames instead of piling them up."""

import math
import threading
from pathlib import Path

import cv2
import numpy as np
import pytest
from gz.msgs10.image_pb2 import Image

import goruntu_yayini


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

    def stuck(raw: bytes, path: Path) -> None:
        started.set()
        release.wait(5.0)
        path.write_bytes(raw)

    busy = goruntu_yayini.FrameSink(tmp_path / "dolu", queue_frames=2, write=stuck)
    grid = [k / 15 for k in range(30, 36)]  # six frames on the grid
    busy.offer(image_bytes(grid[0]), 0.0, math.nan)
    assert started.wait(5.0)  # the writer holds the first one
    for t in grid[1:]:
        busy.offer(image_bytes(t), 0.0, math.nan)
    release.set()
    books = busy.close()
    assert books["secilen"] == 6 and books["yazilan"] == 3 and books["dusen"] == 3
