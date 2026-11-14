"""The sim's default camera mount and Follow Me setting since the decision of 14.11 (implementation/
gorev-grubu-17-on-kamera-acisi.md, sections 18 and 20): camera 35 deg below the nose, 9 m height, 12.9 m behind the
person. One value (kamera.NOMINAL_TILT_DEG) reaches the Gazebo model, the tracking side's computations, the scenarios
and the video; the 45 deg scenarios stay for comparison under names that say so; a run flown before the tilt was a
setting keeps the mount Gazebo recorded for it. The real mount is not built yet: it is measured on the vehicle."""

import dataclasses
import inspect
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest
import yaml

import hedef
import kamera
import konumlama
import olcum
import takip
import tarama

CHOSEN_TILT_DEG = 35.0  # [deg] section 18: the only setting through the gate in the rule's 3 runs on both paths
CHOSEN_HEIGHT_M = 9.0  # [m] FLW_TGT_HT (drone.yukseklik_m)
CHOSEN_DISTANCE_M = 12.9  # [m] FLW_TGT_DST
CM3 = kamera.Camera(2304, 1296, 1773.9, 1773.9, 1152.0, 648.0)  # models/x500_tez, ideal pinhole
SCENARIOS = hedef.SIM_DIR / "senaryolar"
NO_TILT = """
ad: varsayilan
drone: {yukseklik_m: 9}
takip: {kaynak: follow_me, px4_parametreleri: {FLW_TGT_DST: 12.9}}
hedef:
  baslangic: [12.9, 0]
  yol:
    - {nokta: [24.9, 0], hiz_mps: 1.4}
zamanlama: {baslama_s: 60, son_bekleme_s: 5}
"""


def raw(name: str) -> dict:
    return yaml.safe_load((SCENARIOS / f"{name}.yaml").read_text(encoding="utf-8"))


def camera_pitch(model_sdf: Path) -> float:
    root = ET.parse(model_sdf).getroot()
    link = next(e for e in root.iter("link") if e.get("name") == "camera_link")
    return float(link.find("pose").text.split()[4])


def test_the_default_tilt_has_one_source_and_the_drone_model_flies_it(tmp_path: Path) -> None:
    """kamera.NOMINAL_TILT_DEG is the chosen 35 deg; models/x500_tez is pitched by it, so a scenario without a kamera
    block flies the model as it is (no tilted copy); every default of the tracking side, the metrics, the video and
    the scan comes from that one constant."""
    assert kamera.NOMINAL_TILT_DEG == CHOSEN_TILT_DEG
    model = hedef.SIM_DIR / "models" / "x500_tez" / "model.sdf"
    assert camera_pitch(model) == pytest.approx(math.radians(CHOSEN_TILT_DEG), abs=1e-6)
    assert hedef.model_tilt_deg() == pytest.approx(kamera.NOMINAL_TILT_DEG, abs=1e-4)

    path = tmp_path / "s.yaml"
    path.write_text(NO_TILT, encoding="utf-8")
    sc = hedef.load(str(path))
    assert sc.camera.tilt_deg == kamera.NOMINAL_TILT_DEG
    assert hedef.settings(sc)["kamera"] == {"egim_deg": CHOSEN_TILT_DEG}
    out = tmp_path / "kosu"
    out.mkdir()
    assert hedef.camera_model(sc, out) is None and not list(out.glob("x500_tez*"))

    assert konumlama.MOUNT_PITCH_DOWN == pytest.approx(math.radians(kamera.NOMINAL_TILT_DEG))
    assert konumlama.NOMINAL_MOUNT == pytest.approx(kamera.camera_to_body(math.radians(CHOSEN_TILT_DEG)))
    assert takip.NOMINAL_MOUNT is konumlama.NOMINAL_MOUNT
    h = np.array([9.0])
    assert olcum.frame_limits(CM3, h) == pytest.approx(olcum.frame_limits(CM3, h, CHOSEN_TILT_DEG))
    import video

    defaults = {
        "video.Run.tilt_deg": next(f.default for f in dataclasses.fields(video.Run) if f.name == "tilt_deg"),
        "olcum.RunData.camera_tilt_deg": next(
            f.default for f in dataclasses.fields(olcum.RunData) if f.name == "camera_tilt_deg"
        ),
        "tarama.approach_numbers": inspect.signature(tarama.approach_numbers).parameters["tilt_deg"].default,
    }
    assert defaults == dict.fromkeys(defaults, kamera.NOMINAL_TILT_DEG)


def test_takip_yuruyen_flies_the_chosen_setting_on_the_path_the_scan_flew() -> None:
    """takip_yuruyen: 9 m / 12.9 m with the default camera (no kamera block: one source), FLW_TGT_RS 0.3 stays; the
    walk of yuruyen_insan shifted east so the person starts 12.9 m ahead (centred in the image at take-off), the same
    path, timing and tracking as the scan's 35 deg / 9 m / 12.9 m combination."""
    follow, walk = hedef.load("takip_yuruyen"), hedef.load("yuruyen_insan")
    assert "kamera" not in raw("takip_yuruyen")
    assert follow.camera.tilt_deg == kamera.NOMINAL_TILT_DEG
    assert (follow.altitude, follow.tracking.source, follow.tracking.los) == (CHOSEN_HEIGHT_M, "follow_me", "model")
    assert [(p.name, p.value, p.source) for p in follow.tracking.px4_params] == [
        ("FLW_TGT_HT", CHOSEN_HEIGHT_M, "drone.yukseklik_m (follow_me)"),
        ("FLW_TGT_DST", CHOSEN_DISTANCE_M, "takip.px4_parametreleri"),
        ("FLW_TGT_RS", 0.3, "takip.px4_parametreleri"),
    ]
    shift = CHOSEN_DISTANCE_M - walk.track.x[0]
    assert follow.track.x[0] == pytest.approx(CHOSEN_DISTANCE_M)
    assert follow.track.x == pytest.approx(walk.track.x + shift) and follow.track.y == pytest.approx(walk.track.y)
    assert follow.end_time == pytest.approx(walk.end_time) and follow.start_time == walk.start_time
    assert tarama.view(CHOSEN_TILT_DEG, CHOSEN_HEIGHT_M, CHOSEN_DISTANCE_M)["sigar"]
    scan = tarama.variant(raw("yuruyen_insan"), raw("takip_yuruyen"), 35.0, 9.0, 12.9, "e35_h9_d12.9")
    assert scan["hedef"]["baslangic"] == raw("takip_yuruyen")["hedef"]["baslangic"]
    assert scan["hedef"]["yol"] == raw("takip_yuruyen")["hedef"]["yol"]
    assert scan["takip"] == raw("takip_yuruyen")["takip"]
    hedef.check_wired(follow)


@pytest.mark.parametrize(("name", "height"), [("takip_yuruyen_45_8m", 8.0), ("takip_yuruyen_45_10m", 10.0)])
def test_the_45_degree_mount_scenarios_say_so_in_their_name_and_file(name: str, height: float, tmp_path: Path) -> None:
    """The 45 deg settings of task group 9 (8 m / 8 m) and of the user's decision 14.11 (10 m / 10 m) stay for
    comparison: kamera.egim_deg 45 written in the file (a default change does not move them), the walk of
    yuruyen_insan unchanged (the person starts 10 m ahead, as in those runs), FLW_TGT_RS 0.3; the old name
    takip_yuruyen_8m is gone. Their run gets a 45 deg copy of the model."""
    assert not (SCENARIOS / "takip_yuruyen_8m.yaml").exists()
    assert raw(name)["kamera"] == {"egim_deg": 45}
    sc, walk = hedef.load(name), hedef.load("yuruyen_insan")
    assert sc.camera.tilt_deg == 45.0
    assert (sc.altitude, sc.tracking.source, sc.tracking.los) == (height, "follow_me", "model")
    assert [(p.name, p.value) for p in sc.tracking.px4_params] == [
        ("FLW_TGT_HT", height),
        ("FLW_TGT_DST", height),
        ("FLW_TGT_RS", 0.3),
    ]
    assert np.array_equal(sc.track.x, walk.track.x) and np.array_equal(sc.track.y, walk.track.y)
    out = tmp_path / "kosu"
    out.mkdir()
    copy = hedef.camera_model(sc, out)
    assert copy is not None and camera_pitch(copy / "model.sdf") == pytest.approx(math.radians(45.0), abs=1e-6)
    hedef.check_wired(sc)


def _in_view(tilt_deg: float, height: float, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Per point of a walk: the person's feet and head (0 and 1.75 m) both inside the image of the drone hovering
    level at (0, 0) facing east, `height` above home (Gazebo ENU; body FRD: forward = east, right = south)."""
    mount = kamera.camera_to_body(math.radians(tilt_deg))
    cam = np.array([konumlama.NOMINAL_OFFSET_FRD[0], 0.0, height - konumlama.NOMINAL_OFFSET_FRD[2]])
    cam[2] += konumlama.GROUND_BELOW_HOME_M
    ok = np.ones(len(x), dtype=bool)
    for k, (px, py) in enumerate(zip(x, y, strict=True)):
        for z in (0.0, tarama.HEAD_M):
            d = np.array([px, py, z]) - cam
            uv = CM3.project(mount.T @ np.array([d[0], -d[1], -d[2]]))
            ok[k] &= uv is not None and CM3.contains(*uv)
    return ok


def test_kalabalik_park_keeps_the_target_in_view_with_the_default_mount() -> None:
    """kalabalik_park (hover, takip yok) flies the default camera at the chosen height: the target (feet and head)
    stays in the image along its whole walk, as it did at 45 deg / 10 m. At 10 m the default camera would not see
    the target standing at its start for the first 60 s (below the image): why the scenario's height changed."""
    sc = hedef.load("kalabalik_park")
    assert "kamera" not in raw("kalabalik_park") and sc.camera.tilt_deg == kamera.NOMINAL_TILT_DEG
    assert (sc.altitude, sc.tracking.source) == (CHOSEN_HEIGHT_M, "yok")
    x, y = sc.track.x[::20], sc.track.y[::20]
    assert _in_view(sc.camera.tilt_deg, sc.altitude, x, y).all()
    assert _in_view(45.0, 10.0, x, y).all()  # the scenario as it was designed (13.11)
    assert not _in_view(kamera.NOMINAL_TILT_DEG, 10.0, x[:1], y[:1]).any()  # the start, at the old height


def test_an_old_run_keeps_the_mount_it_flew_with(tmp_path: Path) -> None:
    """video.load: the tilt comes from ozet.json "ayarlar" (command line included); a run flown before the tilt was a
    setting has none, its scenario copy has no kamera block and the default has changed since: its tilt is the
    mount Gazebo recorded (ozet.json "kamera_montaji"), 45 deg for every run before 14.11; only without either the
    default."""
    import test_video

    import video

    folder = test_video.run_folder(tmp_path)
    scenario = yaml.safe_load((folder / "senaryo.yaml").read_text(encoding="utf-8"))
    scenario.pop("kamera", None)
    (folder / "senaryo.yaml").write_text(yaml.safe_dump(scenario, allow_unicode=True), encoding="utf-8")
    summary = json.loads((folder / "ozet.json").read_text(encoding="utf-8"))
    summary["ayarlar"].pop("kamera", None)
    summary["kamera_montaji"] = {"dcm_optik_govde": kamera.camera_to_body(math.radians(45.0)).tolist()}
    (folder / "ozet.json").write_text(json.dumps(summary), encoding="utf-8")
    assert video.load(folder).tilt_deg == pytest.approx(45.0)

    summary["ayarlar"]["kamera"] = {"egim_deg": 30.0}
    (folder / "ozet.json").write_text(json.dumps(summary), encoding="utf-8")
    assert video.load(folder).tilt_deg == 30.0

    summary["ayarlar"].pop("kamera")
    summary["kamera_montaji"] = None
    (folder / "ozet.json").write_text(json.dumps(summary), encoding="utf-8")
    assert video.load(folder).tilt_deg == kamera.NOMINAL_TILT_DEG
