"""Scenario files: validation messages, the target path and its ground truth."""

import math
from pathlib import Path

import pytest

import hedef

GOOD = """
ad: deneme
drone: {yukseklik_m: 10, mod: tez}
hedef:
  baslangic: [10, 0]
  yol:
    - {dur_s: 2}
    - {nokta: [20, 0], hiz_mps: 1.0}
    - {dur_s: 3}
    - {nokta: [20, 9], hiz_mps: 3.0}
zamanlama: {baslama_s: 60, son_bekleme_s: 5}
basari: {kadrajda_kalma_min: 0.9}
"""


def write(tmp_path: Path, text: str) -> str:
    path = tmp_path / "s.yaml"
    path.write_text(text, encoding="utf-8")
    return str(path)


@pytest.fixture
def sc(tmp_path: Path) -> hedef.Scenario:
    return hedef.load(write(tmp_path, GOOD))


def test_segments_and_times(sc: hedef.Scenario) -> None:
    kinds = [s.kind for s in sc.segments]
    assert kinds == ["stand", "stand", "walk", "stand", "run", "stand"]
    assert sc.segments[2].t0 == 62.0 and sc.segments[2].t1 == 72.0
    assert sc.walk_end == 75.0 + 3.0
    assert sc.end_time == 83.0
    assert sc.path_length() == pytest.approx(19.0)
    assert sc.bounds() == (10.0, 20.0, 0.0, 9.0)


def test_waiting_target_faces_its_first_direction(sc: hedef.Scenario) -> None:
    assert sc.segments[0].yaw == sc.segments[1].yaw == 0.0  # first move is east
    assert sc.segments[4].yaw == pytest.approx(math.pi / 2)
    assert sc.segments[-1].yaw == pytest.approx(math.pi / 2)  # keeps facing north at the end


def test_truth_along_the_path(sc: hedef.Scenario) -> None:
    assert sc.truth(0.0)[:2] == (10.0, 0.0)
    x, y, yaw, speed, kind = sc.truth(67.0)
    assert (x, y, speed, kind) == (pytest.approx(15.0), 0.0, pytest.approx(1.0), "walk")
    assert sc.truth(76.5)[:2] == (pytest.approx(20.0), pytest.approx(4.5))
    assert sc.truth(1e6)[:2] == (20.0, 9.0)


def test_actor_waypoints_every_0_2_s(sc: hedef.Scenario) -> None:
    sdf = hedef.actor_sdf(sc)
    walk = sdf.split('type="walk"')[1].split("</trajectory>")[0]
    assert walk.count("<waypoint>") == 10 / hedef.WAYPOINT_STEP + 1
    assert "<loop>true</loop>" in sdf


@pytest.mark.parametrize(
    "change, message",
    [
        (("ad: deneme", "ad: deneme\nfazla: 1"), "bilinmeyen alan"),
        (("mod: tez", "mod: ucus"), "drone.mod"),
        (("yukseklik_m: 10", "yukseklik_m: 1"), "en az 2.0"),
        (("baslangic: [10, 0]", "baslangic: [10]"), "hedef.baslangic"),
        (("hiz_mps: 3.0", "hiz_mps: 9"), "en fazla 6 m/s"),
        (("nokta: [20, 0]", "nokta: [10, 0]"), "aynı yer"),
        (("{dur_s: 3}", "{dur_s: 3, hiz_mps: 1}"), "hedef.yol[2]"),
        (("baslama_s: 60", "baslama_s: 10"), "zamanlama.baslama_s"),
        (("kadrajda_kalma_min: 0.9", "kadraj: 0.9"), "basari"),
        (("yukseklik_m: 10", "yukseklik_m: on"), "sayı olmalı"),
    ],
)
def test_mistakes_name_the_field(tmp_path: Path, change: tuple[str, str], message: str) -> None:
    with pytest.raises(ValueError, match=message.replace("[", r"\[").replace(".", r"\.")):
        hedef.load(write(tmp_path, GOOD.replace(*change)))


def test_unknown_scenario_lists_the_known_ones() -> None:
    with pytest.raises(FileNotFoundError, match="yuruyen_insan"):
        hedef.load("boyle_bir_senaryo_yok")


def test_shipped_scenarios_load() -> None:
    for path in (hedef.SIM_DIR / "senaryolar").glob("*.yaml"):
        assert hedef.load(str(path)).segments


def test_world_without_shadows(sc: hedef.Scenario, tmp_path: Path) -> None:
    text = hedef.write_world(sc, tmp_path, "<!-- extra -->", shadows=False).read_text()
    assert "<shadows>true</shadows>" not in text and "<cast_shadows>true" not in text
    assert text.index('<actor name="hedef">') < text.index("<!-- extra -->") < text.index("</world>")
