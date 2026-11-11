"""Target selection (temporary; m11 does the real one), LOS (i) of a model box and the tracking thread, without
Gazebo, PX4 or the model."""

import csv
import math
from pathlib import Path

import numpy as np
import pytest

import algilama
import goruntu
import hedef
import kamera
import kayit
import takip
import yuruyus

CM3 = kamera.Camera(2304, 1296, 1773.9, 1773.9, 1152.0, 648.0)  # models/x500_tez, ideal pinhole
# a lens with strong barrel distortion and an off-centre principal point: the chain must undo it
DISTORTED = kamera.Camera(2304, 1296, 1500.0, 1502.0, 1160.0, 640.0, (-0.30, 0.10, 0.001, -0.0005, -0.02))
TILT = math.radians(45)
CAM_POS = np.array([0.151, 0.0, -0.035])  # camera_link in models/x500_tez (Gazebo FLU)
CAM_R = np.array([[math.cos(TILT), 0, math.sin(TILT)], [0, 1, 0], [-math.sin(TILT), 0, math.cos(TILT)]])


def box(u0: float, v0: float, u1: float, v1: float, guven: float = 0.8) -> algilama.Kutu:
    return algilama.Kutu(u0, v0, u1, v1, guven, 0, "Person")


def referee(target: tuple[float, float, float, float], visible: bool = True, t: float = 60.0) -> takip.Referee:
    return takip.Referee(t, target, visible, (1.0, 0.0, 0.0), 0.0)


def test_first_lock_takes_the_box_that_overlaps_the_referee_most() -> None:
    """The referee stands in for the operator who picks the target: no lock without it, and none on a box that is
    not over the target."""
    s = takip.Selection()
    target = (1000.0, 500.0, 1060.0, 680.0)
    boxes = [box(400, 500, 460, 680, 0.9), box(1005, 505, 1062, 690, 0.6), box(990, 480, 1100, 700, 0.7)]
    assert (s.step(boxes, None).state, s.step(boxes, None).reason) == ("kilitsiz", "hakem_yok")
    assert s.step(boxes, referee(target, visible=False)).reason == "hedef_gorunmuyor"
    assert s.step([boxes[0]], referee(target)).reason == "kutu_eslesmedi"  # a box, but on somebody else
    c = s.step(boxes, referee(target))
    assert (c.state, c.index, c.box, c.lock_no) == ("ilk_kilit", 1, boxes[1], 1)
    assert c.lock_iou == pytest.approx(algilama.iou(boxes[1], target))  # 0.82, the 0.45 box loses
    assert (s.locks, s.relocks, s.losses) == (1, 0, 0)


def test_tracking_takes_the_nearest_box_inside_the_gate() -> None:
    """While locked: the box whose centre is nearest to the previous choice, at most 1.5 diagonals away; the
    referee is not asked (it would be cheating)."""
    s = takip.Selection()
    first = box(1000, 500, 1060, 680)  # centre (1030, 590), diagonal 189.7 px -> gate 284.6 px
    s.step([first], referee((1000, 500, 1060, 680)))
    gate = 1.5 * math.hypot(60, 180)
    near, far = box(1030, 510, 1090, 690), box(1500, 500, 1560, 680)
    c = s.step([far, near], None)
    assert (c.state, c.index, c.box) == ("izleme", 1, near)
    assert c.gate == pytest.approx((1030.0, 590.0, gate)) and c.distance == pytest.approx(math.hypot(30, 10))

    # the gate is centred on the last choice (now `near`, centre (1060, 600)) with its own diagonal
    inside = box(1060 + 0.99 * gate - 30, 510, 1060 + 0.99 * gate + 30, 690)
    assert s.step([inside], referee((0, 0, 1, 1))).state == "izleme"  # a wrong referee box changes nothing
    centre = (1060 + 0.99 * gate, 600.0)
    outside = box(centre[0] + 1.01 * gate - 30, 510, centre[0] + 1.01 * gate + 30, 690)
    c = s.step([outside], None)
    assert (c.state, c.box, c.misses) == ("eslesmedi", None, 1)
    assert c.gate == pytest.approx((*centre, gate)) and c.distance == pytest.approx(1.01 * gate)


def test_lock_drops_after_ten_processed_frames_without_a_match_and_the_referee_locks_again() -> None:
    s = takip.Selection()
    target = (1000.0, 500.0, 1060.0, 680.0)
    s.step([box(*target)], referee(target))
    for k in range(1, takip.LOST_AFTER):
        c = s.step([], referee(target))
        assert (c.state, c.misses, c.box, c.lock_no) == ("eslesmedi", k, None, 1)
    c = s.step([box(1600, 500, 1660, 680)], referee(target))  # 10th processed frame, only a far box
    assert (c.state, c.misses, c.box) == ("kilit_kaybi", takip.LOST_AFTER, None) and s.losses == 1
    c = s.step([box(1600, 500, 1660, 680), box(1002, 498, 1061, 684)], referee(target))
    assert (c.state, c.index, c.lock_no) == ("yeniden_kilit", 1, 2)
    assert (s.locks, s.relocks, s.losses) == (2, 1, 1)

    # a match before the 10th miss keeps the lock and starts the count again
    for _ in range(takip.LOST_AFTER - 1):
        s.step([], None)
    assert s.step([box(1004, 500, 1063, 684)], None).state == "izleme"
    assert s.step([], None).misses == 1 and s.losses == 1


def gazebo_quat(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """Gazebo model orientation (ENU world, FLU body) of Euler angles [deg] (z-y-x)."""
    r, p, y = (math.radians(a) / 2 for a in (roll, pitch, yaw))
    return np.array(
        [
            math.cos(r) * math.cos(p) * math.cos(y) + math.sin(r) * math.sin(p) * math.sin(y),
            math.sin(r) * math.cos(p) * math.cos(y) - math.cos(r) * math.sin(p) * math.sin(y),
            math.cos(r) * math.sin(p) * math.cos(y) + math.sin(r) * math.cos(p) * math.sin(y),
            math.cos(r) * math.cos(p) * math.sin(y) - math.sin(r) * math.sin(p) * math.cos(y),
        ]
    )


def standing(at: tuple[float, float]) -> hedef.Scenario:
    sc = hedef.Scenario("t", "", "duz_alan", 10.0, at, 60.0, 5.0)
    sc.track, sc.walk_end = yuruyus.plan(at, 60.0, [("wait", 1.0)], yuruyus.Behaviour())
    return sc


@pytest.mark.parametrize("camera", [CM3, DISTORTED], ids=["cm3", "bozulmali"])
@pytest.mark.parametrize(
    "attitude, ahead, left",
    [((0, 0, 0), 9.0, 0.0), ((4, -11, 35), 11.0, 3.0), ((-7, 15, 210), 7.5, -2.5), ((2, 24, -60), 6.0, 1.5)],
)
def test_los_of_a_box_round_the_true_centre_matches_the_referee(
    camera: kamera.Camera, attitude: tuple[float, float, float], ahead: float, left: float
) -> None:
    """Known pose and target -> the referee projects the body centre into the frame (kamera.project) -> a box round
    that pixel -> LOS (i) through camera_info + nominal 45 deg mount: the same direction as the referee's los_govde."""
    p_model = np.array([3.0, -2.0, 10.0])
    heading = math.radians(attitude[2])  # place the target ahead of the drone's nose
    at = (
        p_model[0] + ahead * math.cos(heading) - left * math.sin(heading),
        p_model[1] + ahead * math.sin(heading) + left * math.cos(heading),
    )
    row = kayit.truth_row(70.0, standing(at), camera, p_model, gazebo_quat(*attitude), CAM_POS, CAM_R)
    assert row["kadrajda"]
    u, v = row["merkez_u"], row["merkez_v"]
    los = takip.los_of_box(camera, box(u - 31, v - 97, u + 31, v + 97))
    truth = np.array([row["los_govde_x"], row["los_govde_y"], row["los_govde_z"]])
    assert np.linalg.norm(los) == pytest.approx(1.0, abs=1e-12)
    assert takip.angle_deg(los, truth) < 0.01


class FakeLink:
    """What the tracking thread needs from px4_baglanti.Vehicle."""

    def __init__(self) -> None:
        self.sent: list[tuple[int, tuple | None]] = []

    def send_los(self, time_usec: int, vec: np.ndarray | None) -> None:
        self.sent.append((time_usec, None if vec is None else tuple(vec)))


def model_result(t: float, boxes: list[algilama.Kutu], alinma: float) -> algilama.FrameResult:
    return algilama.FrameResult(
        t, round(t * 30), alinma - 0.1, alinma - 0.08, alinma - 0.01, 1.0, 0.0, 70.0, tuple(boxes), ()
    )


class FakeClock:
    """time.monotonic stand-in: the test decides when "now" is."""

    def __init__(self, start: float) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t


def test_model_results_and_referee_frames_become_tez_los_and_rows(tmp_path: Path) -> None:
    """Tracking thread (spec 5, tasks 5.5): model result -> selection -> LOS (i) -> delay line -> one TEZ_LOS per
    processed frame (NaN = no target) -> algilama.csv row with the selection, the LOS and the times; every attempt in
    tez_los.csv. The referee's frames only feed the lock while the source is the model."""
    clock = goruntu.SimClock()
    for k in range(1001):  # real time: monotonic 1000 s = sim 60 s
        clock.add(sim=60.0 + k * 0.01, wall=1000.0 + k * 0.01)
    now = FakeClock(1000.0)
    detections = algilama.DetectionLog(tmp_path, clock, takip.ROW_COLUMNS)
    tr = takip.Tracker("model", clock, tmp_path, detections, camera=lambda: CM3, now=now)
    target = (1000.0, 500.0, 1060.0, 680.0)
    row = {"t": 61.0, "gorunur": True, "los_govde_x": 0.7, "los_govde_y": 0.0, "los_govde_z": 0.7}
    row |= dict(zip(("hedef_kutu_u0", "hedef_kutu_v0", "hedef_kutu_u1", "hedef_kutu_v1"), target, strict=True))

    def processed(t: float, boxes: list[algilama.Kutu], at: float) -> None:
        now.t = at
        tr.on_model(model_result(t, boxes, at), at)

    processed(60.9, [box(*target)], 1001.02)  # no link yet, no referee yet
    link = FakeLink()
    tr.attach(link)
    tr.on_referee(61.0, row, 1001.05)
    tr.wait_idle()
    processed(61.0, [box(*target)], 1001.12)
    processed(61.1, [], 1001.22)
    processed(61.1, [], 1001.25)  # the same frame again: never sent twice
    tr.close()
    detections.close()

    with (tmp_path / "algilama.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [r["secim"] for r in rows] == ["kilitsiz", "ilk_kilit", "eslesmedi", "eslesmedi"]
    assert [r["tez_los_sonuc"] for r in rows] == ["baglanti_yok", "gonderildi", "gonderildi", "ayni_kare"]
    assert rows[0]["kilitsiz_neden"] == "hakem_yok" and rows[1]["secilen_kutu"] == "0"
    los = [float(rows[1][f"los_i_{k}"]) for k in "xyz"]
    assert los == pytest.approx(list(takip.los_of_box(CM3, box(*target))), abs=1e-6)
    assert [float(rows[1][f"tez_los_{k}"]) for k in "xyz"] == pytest.approx(los, abs=1e-6)
    assert rows[2]["tez_los_x"] == "" and rows[2]["los_i_x"] == ""  # NaN: hedef yok
    assert float(rows[1]["uctan_uca_ms"]) == pytest.approx(120.0, abs=0.01)  # capture 61.0 s -> sent at 61.12 s sim
    assert float(rows[1]["takip_ms"]) == pytest.approx(0.0) and float(rows[1]["ek_gecikme_ms"]) == pytest.approx(0.0)

    assert link.sent[0] == (61_000_000, pytest.approx(tuple(los), abs=1e-6)) and link.sent[1] == (61_100_000, None)
    with (tmp_path / "tez_los.csv").open(encoding="utf-8") as f:
        attempts = list(csv.DictReader(f))
    assert [(a["t_us"], a["kaynak"], a["hedef"], a["sonuc"]) for a in attempts] == [
        ("60900000", "model", "0", "baglanti_yok"),
        ("61000000", "model", "1", "gonderildi"),
        ("61100000", "model", "0", "gonderildi"),
        ("61100000", "model", "0", "ayni_kare"),
    ]
    s = tr.summary()
    assert s["sonuclar"]["gonderildi"] == 2 and s["kilit"]["olaylar"][0]["olay"] == "ilk_kilit"
    assert s["kilit"]["olaylar"][0]["t"] == pytest.approx(61.0)


def test_referee_source_sends_every_camera_frame_and_nan_while_the_target_is_hidden(tmp_path: Path) -> None:
    """LOS (ii): the referee's los_govde of every camera frame while the target is visible, NaN otherwise (also
    before the recording, when there is no referee yet); the model's rows still get the selection and LOS (i)."""
    clock = goruntu.SimClock()
    for k in range(1001):
        clock.add(sim=60.0 + k * 0.01, wall=1000.0 + k * 0.01)
    now = FakeClock(1000.0)
    tr = takip.Tracker("hakem", clock, tmp_path, None, camera=lambda: CM3, now=now)
    link = FakeLink()
    tr.attach(link)
    seen = {"t": 0.0, "gorunur": True, "los_govde_x": 0.6, "los_govde_y": 0.0, "los_govde_z": 0.8}
    seen |= {"hedef_kutu_u0": 1.0, "hedef_kutu_v0": 1.0, "hedef_kutu_u1": 9.0, "hedef_kutu_v1": 9.0}
    frames = [(60.000, None), (60.032, seen), (60.068, seen | {"gorunur": False}), (60.100, seen)]
    for t, row in frames:
        now.t = 1000.0 + (t - 60.0) + 0.040  # the referee's row is ready 40 ms after the capture
        tr.on_referee(t, None if row is None else row | {"t": t}, now.t)
        tr.wait_idle()
    tr.close()
    assert link.sent == [
        (60_000_000, None),
        (60_032_000, pytest.approx((0.6, 0.0, 0.8))),
        (60_068_000, None),
        (60_100_000, pytest.approx((0.6, 0.0, 0.8))),
    ]
    with (tmp_path / "tez_los.csv").open(encoding="utf-8") as f:
        attempts = list(csv.DictReader(f))
    assert {a["kaynak"] for a in attempts} == {"hakem"}
    assert [float(a["hazir_ms"]) for a in attempts] == pytest.approx([40.0] * 4, abs=0.01)
    assert [float(a["uctan_uca_ms"]) for a in attempts] == pytest.approx([40.0] * 4, abs=0.01)
