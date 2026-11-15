"""The live referee stream must not fall behind as a run goes on (implementation/gorev-grubu-17-on-kamera-acisi.md,
"Canlı hakem akışı").

Gazebo 8's segmentation camera (gz-sensors 8.2.2) appends one more `frame_id` entry to the header of every frame it
publishes and never clears them: after a minute of recording a labels_map frame carries ~2000 of them. Parsed with the
pure Python protobuf, every frame got slower and filled the heap, full garbage collections came every ~0.3 s and the
gz-transport thread of the main process fell behind at ~70 s: the referee's rows came after the model's results and no
re-lock was possible. The frame is now read from its raw bytes, the header's entries skipped unread. No Gazebo, PX4 or
model needed."""

import math
import time
from pathlib import Path

import numpy as np
import pytest
from gz.msgs10.camera_info_pb2 import CameraInfo
from gz.msgs10.image_pb2 import Image
from gz.msgs10.pose_v_pb2 import Pose_V

import algilama
import goruntu
import hedef
import kayit
import takip
import yuruyus

FRAME_ID = "x500_tez_0::camera_link::segmentasyon"  # what Gazebo writes into every entry (measured, 13.11)


def gazebo_labels_map(
    t: float, labels: np.ndarray, entries: int = 1, stamp_first: bool = True, header: bool = True
) -> bytes:
    """A labels_map frame as Gazebo publishes it after `entries` frames: (h, w) labels in the third channel and the
    header's frame_id entry repeated `entries` times. stamp_first=False writes the stamp after the entries (another
    writer's field order, still valid protobuf)."""
    h, w = labels.shape
    pixels = np.zeros((h, w, 3), np.uint8)
    pixels[:, :, 2] = labels
    msg = Image(width=w, height=h, step=3 * w, data=pixels.tobytes(), pixel_format_type=3)
    if not header:
        return msg.SerializeToString()
    sec, nsec = int(t), round((t - int(t)) * 1e9)
    if stamp_first:
        msg.header.stamp.sec, msg.header.stamp.nsec = sec, nsec
    for _ in range(entries):
        entry = msg.header.data.add()
        entry.key = "frame_id"
        entry.value.append(FRAME_ID)
    raw = msg.SerializeToString()
    if not stamp_first:  # header = entries ... then the stamp: append a second header field with only the stamp
        later = Image()
        later.header.stamp.sec, later.header.stamp.nsec = sec, nsec
        raw += later.SerializeToString()  # protobuf merges a repeated embedded message field
    return raw


def test_a_segmentation_frame_is_read_from_its_raw_bytes() -> None:
    """kayit.read_image gives the same time, size and pixels as the protobuf message, whatever the header holds."""
    rng = np.random.default_rng(1)
    labels = rng.integers(0, 14, (6, 8), dtype=np.uint8)
    for t, entries, stamp_first in ((24.256, 1, True), (97.384, 2200, True), (61.0, 0, True), (60.032, 5, False)):
        raw = gazebo_labels_map(t, labels, entries, stamp_first)
        frame = kayit.read_image(raw)
        msg = Image.FromString(raw)
        assert frame.t == pytest.approx(msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9, abs=1e-12)
        assert frame.t == pytest.approx(t, abs=1e-9)
        assert (frame.width, frame.height) == (8, 6)
        assert bytes(frame.data) == msg.data
        assert np.array_equal(kayit.label_channel(frame), labels)
    no_header = kayit.read_image(gazebo_labels_map(0.0, labels, header=False))
    assert no_header.t == 0.0 and np.array_equal(kayit.label_channel(no_header), labels)


def test_a_broken_frame_is_refused_with_a_reason() -> None:
    labels = np.ones((4, 4), np.uint8)
    raw = gazebo_labels_map(30.0, labels, 3)
    with pytest.raises(ValueError, match="kesik"):
        kayit.read_image(raw[:-5])  # the pixels end too early
    with pytest.raises(ValueError, match="boyut"):
        kayit.label_channel(kayit.ImageFrame(30.0, 4, 4, memoryview(b"\x00" * 10)))


def test_reading_a_frame_does_not_slow_down_as_gazebos_header_grows() -> None:
    """The bug: the frame at the end of a long run (20 000 entries ~ 11 minutes of Gazebo at 30 Hz) must be read as
    fast as the first one. The pure Python protobuf took ~0.3 s for it; the raw reader skips the entries unread."""
    labels = np.zeros((648, 1152), np.uint8)  # the referee's segmentation size (models/x500_tez)
    labels[300:420, 560:600] = 1
    first, late = gazebo_labels_map(25.0, labels, 1), gazebo_labels_map(700.0, labels, 20_000)
    assert len(late) - len(first) > 900_000  # ~51 bytes per frame, as Gazebo's grew (13.11)

    def fastest(raw: bytes) -> float:
        best = math.inf
        for _ in range(5):
            t0 = time.perf_counter()
            kayit.label_channel(kayit.read_image(raw))
            best = min(best, time.perf_counter() - t0)
        return best

    assert fastest(late) < 0.005  # [s] a camera frame comes every 33 ms
    assert fastest(late) < 5 * fastest(first) + 0.001


class FakeNode:
    """gz.transport13.Node as the Recorder uses it: subscriptions by topic, typed or raw."""

    def __init__(self) -> None:
        self.typed: dict[str, object] = {}
        self.raw: dict[str, object] = {}

    def subscribe(self, msg_type: type, topic: str, callback: object) -> bool:
        self.typed[topic] = callback
        return True

    def subscribe_raw(self, topic: str, callback: object, msg_type: str, options: object) -> bool:
        assert msg_type == "gz.msgs.Image"
        self.raw[topic] = callback
        return True

    def unsubscribe(self, topic: str) -> bool:
        self.typed.pop(topic, None)
        self.raw.pop(topic, None)
        return True


def standing(start: tuple[float, float]) -> hedef.Scenario:
    sc = hedef.Scenario("t", "", "duz_alan", 10.0, start, 60.0, 5.0)
    sc.track, sc.walk_end = yuruyus.plan(start, 60.0, [("wait", 1.0)], yuruyus.Behaviour())
    return sc


def pose_v(t: float) -> Pose_V:
    """The drone 10 m up at the origin facing east, its camera_link 0.151 m ahead pitched 45 deg down."""
    msg = Pose_V()
    msg.header.stamp.sec, msg.header.stamp.nsec = int(t), round((t - int(t)) * 1e9)
    drone = msg.pose.add()
    drone.name, drone.position.z, drone.orientation.w = kayit.DRONE_MODEL, 10.0, 1.0
    cam = msg.pose.add()
    cam.name, cam.position.x, cam.position.z = kayit.CAMERA_LINK, 0.151, -0.035
    half = math.radians(45) / 2
    cam.orientation.w, cam.orientation.y = math.cos(half), math.sin(half)
    return msg


def camera_info(t: float) -> CameraInfo:
    msg = CameraInfo(width=2304, height=1296)
    msg.header.stamp.sec, msg.header.stamp.nsec = int(t), round((t - int(t)) * 1e9)
    msg.intrinsics.k.extend([1773.9, 0.0, 1152.0, 0.0, 1773.9, 648.0, 0.0, 0.0, 1.0])
    return msg


def test_the_recorder_takes_the_referees_frames_raw_and_joins_them() -> None:
    """While recording, the segmentation topic is taken as raw bytes (not parsed by the protobuf module); a frame
    with Gazebo's grown header still becomes the joined referee frame for the tracking side, with the target's
    visible pixels and box."""
    got: list[tuple[float, dict | None]] = []
    node = FakeNode()
    rec = kayit.Recorder(standing((10.0, 0.0)), "duz_alan", lambda t, row, ready: got.append((t, row)), node=node)
    assert kayit.SEG_TOPIC not in node.typed and kayit.SEG_TOPIC not in node.raw  # only while recording
    pose_cb = node.typed["/world/duz_alan/dynamic_pose/info"]
    info_cb = node.typed[f"{kayit.CAMERA_TOPIC}/camera_info"]
    pose_cb(pose_v(60.000))
    rec.start()
    assert kayit.SEG_TOPIC in node.raw and kayit.SEG_TOPIC not in node.typed
    labels = np.zeros((648, 1152), np.uint8)
    labels[300:420, 560:600] = kayit.TARGET_LABEL
    node.raw[kayit.SEG_TOPIC](gazebo_labels_map(60.032, labels, 2200), None)
    info_cb(camera_info(60.032))
    pose_cb(pose_v(60.040))
    rec.stop()
    assert kayit.SEG_TOPIC not in node.raw
    assert len(got) == 1 and got[0][0] == pytest.approx(60.032)
    row = got[0][1]
    assert row["gorunur"] and row["hedef_piksel"] == 120 * 40 * kayit.SEG_SCALE**2
    assert (row["hedef_kutu_u0"], row["hedef_kutu_v0"], row["hedef_kutu_u1"], row["hedef_kutu_v1"]) == (
        560 * kayit.SEG_SCALE,
        300 * kayit.SEG_SCALE,
        600 * kayit.SEG_SCALE,
        420 * kayit.SEG_SCALE,
    )
    assert rec.errors == []


def test_the_referees_lateness_is_measured_in_every_tracking_source(tmp_path: Path) -> None:
    """How long after the capture the referee's frame reached the tracking side (sim ms), for the run's summary,
    and the symptom itself: unlocked model frames that found no referee (hakem_yok) although the referee's frame of
    the same capture came later. With the model as the source a late referee shows only as re-locks that never
    happen, so both are counted."""
    clock = goruntu.SimClock()
    for k in range(1001):  # real time: monotonic 1000 s = sim 60 s
        clock.add(sim=60.0 + k * 0.01, wall=1000.0 + k * 0.01)
    tr = takip.Tracker("model", clock, tmp_path, None, camera=lambda: None)

    def referee_row(t: float) -> dict:
        return {"t": t, "gorunur": True, "los_govde_x": 1.0, "los_govde_y": 0.0, "los_govde_z": 0.0}

    late = [35.0] * 8 + [140.0, 900.0]  # [ms] the last two came after the model's result would have
    times = [61.0 + i / 30.0 for i in range(len(late))]
    for t, ms in zip(times[:8], late[:8], strict=True):
        tr.on_referee(t, referee_row(t), 1000.0 + (t - 60.0) + ms / 1000.0)
    tr.wait_idle()
    for t in times[8:]:  # unlocked (no box ever matched): the model's result asks for a referee that is not there
        tr.on_model(algilama.FrameResult(t, round(t * 30), 0.0, 0.0, 0.0, 1.0, 0.0, 70.0, (), ()), 0.0)
    for t, ms in zip(times[8:], late[8:], strict=True):
        tr.on_referee(t, referee_row(t), 1000.0 + (t - 60.0) + ms / 1000.0)
    tr.on_referee(64.0, None, 1004.0)  # outside the recording: no referee, not measured
    tr.wait_idle()
    tr.close()
    s = tr.summary()["hakem_akisi"]
    assert s["kare"] == 10
    assert s["gecikme_ms_p50"] == pytest.approx(35.0, abs=0.01)
    assert s["gecikme_ms_maks"] == pytest.approx(900.0, abs=0.01)
    assert s["gec_kare"] == 2 and s["gec_esik_ms"] == takip.REFEREE_LATE_MS
    assert s["hakem_yok_kare"] == 2 and s["hakem_sonradan_gelen_kare"] == 2
