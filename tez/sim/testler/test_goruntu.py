"""Frame reader without Gazebo: the newest frame only, the skipped frames' books, decoding, sim <-> wall clock."""

import math

import numpy as np
import pytest
from gz.msgs10.clock_pb2 import Clock
from gz.msgs10.image_pb2 import Image

import goruntu


def image_bytes(t: float, width: int = 4, height: int = 2, fill: int = 0, pixel_format: int = 3) -> bytes:
    """A serialized gz.msgs.Image like the drone camera's (header stamp, frame id, RGB rows)."""
    msg = Image(width=width, height=height, step=3 * width, pixel_format_type=pixel_format)
    msg.header.stamp.sec, msg.header.stamp.nsec = int(t), round((t - int(t)) * 1e9)
    entry = msg.header.data.add()
    entry.key = "frame_id"
    entry.value.append("x500_tez_0::camera_link::imager")
    msg.data = (np.arange(3 * width * height, dtype=np.uint8) + fill).tobytes()
    return msg.SerializeToString()


def test_only_the_newest_frame_is_kept_and_replaced_frames_are_counted() -> None:
    slot = goruntu.LatestFrame()
    for i, t in enumerate((1.000, 1.032, 1.068)):  # three frames while the model is busy
        slot.put(image_bytes(t, fill=10 * i), varis=100.0 + i)
    raw, newest, skipped = slot.take(timeout=0.0)
    frame = goruntu.decode(raw, newest)
    assert (frame.t, frame.sira, frame.varis) == (pytest.approx(1.068), 3, 102.0)
    assert frame.rgb[0, 0, 0] == 20  # the third frame's pixels, not an older one
    assert [a.sira for a in skipped] == [1, 2]
    assert [goruntu.stamp(a.head) for a in skipped] == pytest.approx([1.000, 1.032])  # their sim times are known
    assert slot.take(timeout=0.01) is None  # an old frame is never handed out again

    slot.put(image_bytes(1.100), varis=103.0)
    books = slot.counts()
    assert books == {"uretilen": 4, "verilen": 1, "atlanan": 2, "bekleyen": 1, "listesiz_atlanan": 0}
    assert books["uretilen"] == books["verilen"] + books["atlanan"] + books["bekleyen"]

    # the list of skipped frames is bounded too; what falls off it is still counted
    small = goruntu.LatestFrame(log_limit=2)
    for i in range(5):
        small.put(image_bytes(2.0 + i / 30), varis=float(i))
    _, newest, skipped = small.take(timeout=0.0)
    assert newest.sira == 5 and [a.sira for a in skipped] == [3, 4]
    assert small.counts()["atlanan"] == 4 and small.counts()["listesiz_atlanan"] == 2


def test_decoding_the_camera_message() -> None:
    raw = image_bytes(61.032, width=4, height=2, fill=7)
    frame = goruntu.decode(raw, goruntu.Arrival(9, 50.0, raw[: goruntu.HEAD_BYTES]))
    assert frame.rgb.shape == (2, 4, 3) and frame.rgb.dtype == np.uint8
    assert frame.rgb[1, 3].tolist() == [7 + 21, 7 + 22, 7 + 23]  # row-major RGB as published
    assert not frame.rgb.flags.writeable  # a view of the message: nothing downstream changes it in place
    assert frame.t == pytest.approx(61.032) and goruntu.stamp(raw) == pytest.approx(61.032)
    assert math.isnan(goruntu.stamp(raw[:5])) and math.isnan(goruntu.stamp(b""))  # header not complete
    with pytest.raises(ValueError, match="RGB"):
        goruntu.decode(image_bytes(1.0, pixel_format=4), goruntu.Arrival(1, 0.0, b""))


def test_sim_clock_maps_wall_time_and_measures_the_real_time_factor() -> None:
    clock = goruntu.SimClock()
    assert math.isnan(clock.to_sim(1.0)) and math.isnan(clock.rtf(0.0, 1.0))
    for k in range(1001):  # wall 100..110 s at 100 Hz; the sim runs at 0.8 of real time from sim 10 s
        clock.add(sim=10.0 + 0.8 * k * 0.01, wall=100.0 + k * 0.01)
    assert clock.to_sim(100.005) == pytest.approx(10.004)
    assert clock.to_sim(110.5) == pytest.approx(18.4)  # after the newest message: at the last rate
    assert clock.wall_at(14.0) == pytest.approx(105.0)
    assert clock.rtf(10.0, 18.0) == pytest.approx(0.8)
    assert clock.rtf_min(10.0, 18.0, span=2.0) == pytest.approx(0.8)

    # Gazebo stamps the clock message with its system time when it publishes it: a late callback in a busy process
    # does not shift the pairing (receipt at monotonic 501.0 s, realtime - monotonic = 1.7e9 s)
    msg = Clock()
    msg.sim.sec, msg.sim.nsec = 61, 500_000_000
    msg.system.sec, msg.system.nsec = 1_700_000_500, 960_000_000  # published 40 ms before it was received
    assert goruntu.clock_pair(msg, realtime=1_700_000_501.0, monotonic=501.0) == pytest.approx((61.5, 500.96))
    msg.ClearField("system")  # without it: the receipt time
    assert goruntu.clock_pair(msg, realtime=1_700_000_501.0, monotonic=501.0) == pytest.approx((61.5, 501.0))
