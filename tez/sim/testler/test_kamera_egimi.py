"""Camera tilt as a scenario setting (kamera.egim_deg, --kamera-egim): one value reaches the Gazebo model of the run
and every computation of the tracking side (LOS (i), flat-ground position, the camera's near limit, the video), so a
30 deg run is measured with a 30 deg camera everywhere. The default (kamera.NOMINAL_TILT_DEG, models/x500_tez) is the
sim's mount, 35 deg since the decision of task group 17 (test_varsayilan_montaj)."""

import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

import algilama
import hedef
import kamera
import konumlama
import olcum
import senaryo
import takip

CM3 = kamera.Camera(2304, 1296, 1773.9, 1773.9, 1152.0, 648.0)  # models/x500_tez, ideal pinhole
VFOV_HALF = math.atan2(648.0, 1773.9)  # 20.07 deg
ORIGIN = konumlama.GeoPoint(47.3979711, 8.5461637, 488.27)
HOME_D = -0.031
GROUND_D = HOME_D + konumlama.GROUND_BELOW_HOME_M
SCENARIO = """
ad: egim
drone: {yukseklik_m: 8}
takip: {kaynak: follow_me, px4_parametreleri: {FLW_TGT_DST: 13.9}}
hedef:
  baslangic: [13.9, 0]
  yol:
    - {nokta: [25.9, 0], hiz_mps: 1.4}
zamanlama: {baslama_s: 60, son_bekleme_s: 5}
"""


def write(tmp_path: Path, text: str) -> str:
    path = tmp_path / "s.yaml"
    path.write_text(text, encoding="utf-8")
    return str(path)


def history(t: float, q: np.ndarray, p: np.ndarray) -> konumlama.PoseHistory:
    h = konumlama.PoseHistory()
    for dt in (-0.02, 0.0, 0.02):
        h.add_attitude(t + dt, q)
        h.add_position(t + dt, p)
    h.set_origin(ORIGIN)
    h.set_home(np.array([0.0, 0.0, HOME_D]), ORIGIN.alt - HOME_D)
    return h


def level_quat(yaw_deg: float, pitch_deg: float = 0.0) -> np.ndarray:
    """(w, x, y, z) of body FRD -> NED with roll 0 (3-2-1 Euler angles [deg])."""
    p, y = math.radians(pitch_deg) / 2, math.radians(yaw_deg) / 2
    return np.array(
        [math.cos(p) * math.cos(y), -math.sin(p) * math.sin(y), math.sin(p) * math.cos(y), math.cos(p) * math.sin(y)]
    )


@pytest.mark.parametrize("tilt", [30.0, 35.0, 40.0, 45.0])
@pytest.mark.parametrize("pitch", [0.0, -8.0, 6.0])
def test_a_known_pose_goes_pixel_to_ground_and_back_with_the_scenario_tilt(tilt: float, pitch: float) -> None:
    """Drone 8 m up, a ground point where that tilt looks: NED point -> pixel of a camera tilted `tilt` -> a box
    standing on it -> Locator with the same mount -> the same point within 1 cm; LOS (i) of a box centred on the
    person's body is the true direction. The default mount (another tilt) on the same pixel puts the point metres
    away."""
    t = 70.0
    mount = kamera.camera_to_body(math.radians(tilt))
    q = level_quat(25.0, pitch)
    p = np.array([2.0, -1.0, -8.0])
    c_bn = kamera.quat_to_dcm(*q)
    cam = p + c_bn @ konumlama.NOMINAL_OFFSET_FRD
    ahead = (GROUND_D - cam[2]) / math.tan(math.radians(tilt))  # the optical axis meets the ground here (level)
    heading = math.radians(25.0)
    ground = np.array([p[0] + ahead * math.cos(heading), p[1] + ahead * math.sin(heading), GROUND_D])
    foot = CM3.project(mount.T @ c_bn.T @ (ground - cam))
    assert foot is not None and CM3.contains(*foot)
    box = algilama.Kutu(foot[0] - 30.0, foot[1] - 200.0, foot[0] + 30.0, foot[1], 0.9, 0, "Person")

    fix = konumlama.Locator(mount=mount).locate(box, t, CM3, history(t, q, p))
    assert fix.status == "hesaplandi" and np.linalg.norm(fix.ned - ground) < 0.01
    wrong = konumlama.Locator().locate(box, t, CM3, history(t, q, p))  # the default tilt assumed
    if tilt != kamera.NOMINAL_TILT_DEG:
        assert not wrong.ok or np.linalg.norm(wrong.ned - ground) > 1.0

    centre = ground + np.array([0.0, 0.0, -0.9])  # body centre 0.9 m above the feet (kayit.TARGET_POINTS)
    uv = CM3.project(mount.T @ c_bn.T @ (centre - cam))
    centred = algilama.Kutu(uv[0] - 30.0, uv[1] - 90.0, uv[0] + 30.0, uv[1] + 90.0, 0.9, 0, "Person")
    true_body = c_bn.T @ (centre - cam)
    assert kamera.angle_deg(takip.los_of_box(CM3, centred, mount), true_body) < 0.01


@pytest.mark.parametrize("tilt", [30.0, 45.0])
def test_the_near_and_far_ground_limits_follow_the_tilt(tilt: float) -> None:
    """olcum.frame_limits: h / tan(tilt +- vfov/2) + the camera's 0.151 m ahead of base_link; the default is the
    default mount (kamera.NOMINAL_TILT_DEG). At a tilt smaller than half the vertical field of view the top edge sees
    the sky: no far limit."""
    h = np.array([8.0, 10.0])
    near, far = olcum.frame_limits(CM3, h, tilt)
    a = math.radians(tilt)
    assert near == pytest.approx(h / math.tan(a + VFOV_HALF) + 0.151)
    assert far == pytest.approx(h / math.tan(a - VFOV_HALF) + 0.151)
    nominal = olcum.frame_limits(CM3, h)
    assert nominal[0] == pytest.approx(h / math.tan(math.radians(kamera.NOMINAL_TILT_DEG) + VFOV_HALF) + 0.151)
    assert np.isinf(olcum.frame_limits(CM3, h, 15.0)[1]).all()
    assert olcum.frame_limits(CM3, np.array([8.0]), 30.0)[0][0] == pytest.approx(6.85, abs=0.01)  # 45: 3.87


def test_tracker_sends_the_los_of_its_mount(tmp_path: Path) -> None:
    """takip.Tracker(mount=...): LOS (i) of the chosen box uses the run's mount, not the default one."""
    import goruntu

    clock = goruntu.SimClock()
    for k in range(101):
        clock.add(sim=60.0 + k * 0.01, wall=1000.0 + k * 0.01)
    mount = kamera.camera_to_body(math.radians(30.0))
    detections = algilama.DetectionLog(tmp_path, clock, takip.ROW_COLUMNS)
    tr = takip.Tracker("model", clock, tmp_path, detections, camera=lambda: CM3, now=lambda: 1000.5, mount=mount)
    target = (1000.0, 500.0, 1060.0, 680.0)
    row = {"t": 60.2, "gorunur": True, "los_govde_x": 0.7, "los_govde_y": 0.0, "los_govde_z": 0.7}
    row |= dict(zip(("hedef_kutu_u0", "hedef_kutu_v0", "hedef_kutu_u1", "hedef_kutu_v1"), target, strict=True))
    tr.on_referee(60.2, row, 1000.3)
    tr.wait_idle()
    result = algilama.FrameResult(
        60.2, 1806, 1000.3, 1000.31, 1000.39, 1.0, 0.0, 70.0, (algilama.Kutu(*target, 0.8, 0, "Person"),), ()
    )
    tr.on_model(result, 1000.4)
    tr.close()
    detections.close()
    r = detections.rows[-1]
    los = np.array([r["los_i_x"], r["los_i_y"], r["los_i_z"]], dtype=float)
    expected = mount @ CM3.pixel_to_los(1030.0, 590.0)
    assert los == pytest.approx(expected, abs=1e-6)
    middle = algilama.Kutu(1122.0, 558.0, 1182.0, 738.0, 0.8, 0, "Person")  # centred on the principal point
    angle = kamera.angle_deg(takip.los_of_box(CM3, middle, mount), takip.los_of_box(CM3, middle))
    assert angle == pytest.approx(kamera.NOMINAL_TILT_DEG - 30.0)


def test_the_scenario_tilt_is_checked_and_the_command_line_replaces_it(tmp_path: Path) -> None:
    """kamera.egim_deg: default the sim's mount (35 deg); a number in TILT_RANGE_DEG; --kamera-egim replaces it; the
    run's settings (ozet.json "ayarlar") carry it."""
    sc = hedef.load(write(tmp_path, SCENARIO))
    assert sc.camera.tilt_deg == kamera.NOMINAL_TILT_DEG == 35.0
    assert hedef.settings(sc)["kamera"] == {"egim_deg": 35.0}
    thirty = hedef.load(write(tmp_path, SCENARIO + "kamera: {egim_deg: 30}\n"))
    assert thirty.camera.tilt_deg == 30.0
    cli = hedef.load(write(tmp_path, SCENARIO + "kamera: {egim_deg: 30}\n"), hedef.CommandLine(camera_tilt_deg=40.0))
    assert cli.camera.tilt_deg == 40.0
    lo, hi = hedef.TILT_RANGE_DEG
    for text, message in [
        ("kamera: {egim_deg: otuz}\n", "kamera.egim_deg: sayı olmalı"),
        (f"kamera: {{egim_deg: {hi + 1}}}\n", f"kamera.egim_deg: {lo:g}–{hi:g}° arasında olmalı"),
        ("kamera: {egim_deg: -5}\n", "kamera.egim_deg"),
        ("kamera: {aci: 30}\n", "kamera: bilinmeyen alan(lar) ['aci']"),
    ]:
        with pytest.raises(ValueError, match=re.escape(message)):
            hedef.load(write(tmp_path, SCENARIO + text))
    with pytest.raises(ValueError, match=re.escape("(--kamera-egim)")):
        hedef.load(write(tmp_path, SCENARIO), hedef.CommandLine(camera_tilt_deg=80.0))

    args = senaryo.parser().parse_args(["--senaryo", write(tmp_path, SCENARIO), "--kamera-egim", "35"])
    s = senaryo.settings(hedef.load(args.senaryo, senaryo.command_line(args)))
    assert s["kamera"] == {"egim_deg": 35.0}
    json.dumps(s)


def _camera_pitch(model_sdf: Path) -> float:
    root = ET.parse(model_sdf).getroot()
    link = next(e for e in root.iter("link") if e.get("name") == "camera_link")
    return float(link.find("pose").text.split()[4])


def test_the_gazebo_model_of_a_run_has_the_scenario_tilt(tmp_path: Path) -> None:
    """models/x500_tez (the default mount) is never changed: at its tilt the world includes it as it is; at another
    tilt the run folder gets a copy whose camera_link (camera and referee segmentation camera) is pitched by the
    scenario's tilt, and the world includes that copy by its absolute path."""
    assert hedef.model_tilt_deg() == pytest.approx(kamera.NOMINAL_TILT_DEG, abs=1e-4)
    original = (hedef.SIM_DIR / "models" / "x500_tez" / "model.sdf").read_text(encoding="utf-8")

    out = tmp_path / "kosu_varsayilan"
    out.mkdir()
    sc = hedef.load(write(tmp_path, SCENARIO))
    world = hedef.write_world(sc, out).read_text(encoding="utf-8")
    assert "<uri>model://x500_tez</uri>" in world and not list(out.glob("x500_tez*"))
    assert hedef.camera_model(sc, out) is None

    out = tmp_path / "kosu30"
    out.mkdir()
    sc = hedef.load(write(tmp_path, SCENARIO + "kamera: {egim_deg: 30}\n"))
    world = hedef.write_world(sc, out).read_text(encoding="utf-8")
    copy = out / "x500_tez_egim30" / "model.sdf"
    assert f"<uri>{copy.parent}</uri>" in world and "model://x500_tez<" not in world
    assert _camera_pitch(copy) == pytest.approx(math.radians(30.0), abs=1e-6)
    assert (copy.parent / "model.config").is_file()
    text = copy.read_text(encoding="utf-8")
    assert text.count("<sensor ") == 2 and "<uri>model://x500</uri>" in text  # both cameras ride on camera_link
    assert text == original.replace("0.151 0 -0.035 0 0.610865 0", "0.151 0 -0.035 0 0.523599 0")  # nothing else
    assert (hedef.SIM_DIR / "models" / "x500_tez" / "model.sdf").read_text(encoding="utf-8") == original
    model = hedef.SIM_DIR / "models" / "x500_tez" / "model.sdf"
    assert _camera_pitch(model) == pytest.approx(math.radians(kamera.NOMINAL_TILT_DEG), abs=1e-6)


@pytest.mark.parametrize("tilt", [30.0, 45.0])
def test_the_tilt_gazebo_reports_is_read_back_from_the_mount(tilt: float) -> None:
    """kayit.Recorder turns camera_link's orientation (Gazebo FLU, pitch + = optical axis down) into C_cb; the run
    compares its tilt with the scenario's (kamera.tilt_of_mount)."""
    import kayit

    a = math.radians(tilt)
    r_rel = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])  # pitch about FLU y
    c_cb = kayit.camera_to_body_dcm(r_rel)
    assert c_cb == pytest.approx(kamera.camera_to_body(a), abs=1e-12)
    assert kamera.tilt_of_mount(c_cb) == pytest.approx(tilt, abs=1e-9)


def test_a_model_without_the_expected_camera_pose_is_refused(tmp_path: Path) -> None:
    """If models/x500_tez ever changes so that the camera_link pose is not found, the copy is refused (the run
    stops before Gazebo starts) instead of flying with a camera that silently kept the default tilt."""
    broken = tmp_path / "model.sdf"
    broken.write_text("<sdf><model name='x500_tez'><link name='camera_link'/></model></sdf>", encoding="utf-8")
    with pytest.raises(ValueError, match="camera_link"):
        hedef.tilted_model_sdf(broken.read_text(encoding="utf-8"), 30.0)


def test_the_video_draws_the_near_limit_of_the_runs_tilt(tmp_path: Path) -> None:
    """video.load: the tilt comes from ozet.json "ayarlar" (command line included), else from the scenario copy."""
    import test_video

    import video

    folder = test_video.run_folder(tmp_path)
    summary = json.loads((folder / "ozet.json").read_text(encoding="utf-8"))
    assert video.load(folder).tilt_deg == kamera.NOMINAL_TILT_DEG  # no ayarlar.kamera, no recorded mount
    summary["ayarlar"]["kamera"] = {"egim_deg": 30.0}
    (folder / "ozet.json").write_text(json.dumps(summary), encoding="utf-8")
    run = video.load(folder)
    assert run.tilt_deg == 30.0
    m = video.moment(run, 60.5, None, False)
    cam_z = 7.965
    assert m.near_limit == pytest.approx(cam_z / math.tan(math.radians(30.0) + VFOV_HALF) + 0.151)
