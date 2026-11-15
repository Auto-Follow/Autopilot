"""kamera_montaji.yaml (the copy-from file for people and teammates' tools) must say what the simulation really uses:
models/x500_tez/model.sdf, kamera.NOMINAL_TILT_DEG and the takip_yuruyen scenario."""

import math
import xml.etree.ElementTree as ET

import pytest
import yaml

import hedef
import kamera

YAML = hedef.SIM_DIR / "kamera_montaji.yaml"
SDF = hedef.SIM_DIR / "models" / "x500_tez" / "model.sdf"


@pytest.fixture(scope="module")
def doc() -> dict:
    return yaml.safe_load(YAML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def camera_link() -> ET.Element:
    root = ET.parse(SDF).getroot()
    link = next(e for e in root.iter("link") if e.get("name") == "camera_link")
    return link


def test_tilt_matches_kamera_py_and_sdf(doc: dict, camera_link: ET.Element) -> None:
    tilt = doc["montaj"]["egim_asagi_deg"]
    assert tilt == pytest.approx(kamera.NOMINAL_TILT_DEG)
    pose = [float(v) for v in camera_link.find("pose").text.split()]
    assert math.degrees(pose[4]) == pytest.approx(tilt, abs=1e-4)


def test_position_matches_sdf_in_flu_and_frd(doc: dict, camera_link: ET.Element) -> None:
    pose = [float(v) for v in camera_link.find("pose").text.split()]
    assert doc["montaj"]["konum_base_link_flu_m"] == pytest.approx(pose[:3])
    x, y, z = pose[:3]
    assert doc["montaj"]["konum_base_link_frd_m"] == pytest.approx([x, -y, -z])


def test_image_sensor_matches_sdf(doc: dict, camera_link: ET.Element) -> None:
    sensor = next(s for s in camera_link.iter("sensor") if s.get("type") == "camera")
    cam = doc["kamera"]
    assert float(sensor.find("camera/horizontal_fov").text) == pytest.approx(cam["yatay_fov_rad"])
    assert int(sensor.find("camera/image/width").text) == cam["genislik_px"]
    assert int(sensor.find("camera/image/height").text) == cam["yukseklik_px"]
    assert float(sensor.find("update_rate").text) == pytest.approx(cam["fps"])
    assert sensor.find("topic").text == cam["gazebo_konulari"]["goruntu"]
    vfov = 2 * math.degrees(math.atan(math.tan(cam["yatay_fov_rad"] / 2) * cam["yukseklik_px"] / cam["genislik_px"]))
    assert vfov == pytest.approx(cam["dikey_fov_deg"], abs=0.05)


def test_flight_proposal_matches_takip_yuruyen(doc: dict) -> None:
    scen = yaml.safe_load((hedef.SIM_DIR / "senaryolar" / "takip_yuruyen.yaml").read_text(encoding="utf-8"))
    prop = doc["ucus_onerisi"]
    assert scen["drone"]["yukseklik_m"] == pytest.approx(prop["yukseklik_m"])
    assert scen["takip"]["px4_parametreleri"]["FLW_TGT_DST"] == pytest.approx(prop["geride_durma_m"])
    expected = prop["yukseklik_m"] / math.tan(math.radians(doc["montaj"]["egim_asagi_deg"]))
    assert prop["geride_durma_m"] == pytest.approx(expected, abs=0.05)
