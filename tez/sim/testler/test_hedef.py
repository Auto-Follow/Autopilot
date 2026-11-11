"""Scenario files: validation messages, the target path and its ground truth."""

import re
from pathlib import Path

import numpy as np
import pytest

import hedef

GOOD = """
ad: deneme
drone: {yukseklik_m: 10}
takip: {kaynak: yok}
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


def test_scenario_times_follow_the_motion(sc: hedef.Scenario) -> None:
    # 2 s wait, 10 m walk, 3 s wait, 9 m run (+ starting, stopping and turning a person needs)
    assert sc.walk_end > 60.0 + 2 + 10 / 1.0 + 3 + 9 / 3.0
    assert sc.end_time == sc.walk_end + 5.0
    assert sc.path_length() == pytest.approx(19.0, abs=0.3)
    # setting off north after the wait steps round on the tight arc: up to its radius (+ wander) east of the point
    assert sc.bounds() == pytest.approx((10.0, 20.0, 0.0, 9.0), abs=0.5)


def test_truth_at_the_scenario_points(sc: hedef.Scenario) -> None:
    assert sc.truth(0.0)[:2] == (10.0, 0.0)
    assert sc.truth(61.9)[3] == 0.0  # still waiting
    assert sc.truth(1e6)[:2] == pytest.approx((20.0, 9.0))
    assert set(sc.track.kind) == {"stand", "walk", "run"}


def test_behaviour_block(tmp_path: Path) -> None:
    text = GOOD.replace("  baslangic: [10, 0]", "  baslangic: [10, 0]\n  davranis: {dogal: false, tohum: 2}")
    sc = hedef.load(write(tmp_path, text))
    assert not sc.behaviour.natural and sc.behaviour.seed == 2
    assert sc.walk_end == pytest.approx(60.0 + 2 + 10 + 3 + 3, abs=0.05)


def test_actor_follows_the_track(sc: hedef.Scenario) -> None:
    sdf = hedef.actors_sdf(sc)
    assert "<loop>true</loop>" in sdf
    assert sdf.count("<trajectory ") == len(hedef._runs(sc.track.kind)) + 1
    assert sdf.split("</trajectory>")[0].count("<waypoint>") == 2  # standing until the start: two points
    for part in sdf.split("<trajectory ")[1:]:
        stamps = [float(t) for t in re.findall(r"<time>([\d.]+)</time>", part)]
        assert stamps[0] == 0.0  # every trajectory restarts its clock
        kind = re.search(r'type="([a-z]+)', part).group(1)
        assert {float(z) for z in re.findall(r"<pose>\S+ \S+ (\S+) ", part)} == {hedef.ACTOR_HIP_HEIGHT}
        if kind != "stand":
            assert max(np.diff(stamps)) <= hedef.WAYPOINT_STEP + 1e-6


def test_every_moving_trajectory_has_its_own_animation_file_spelling(sc: hedef.Scenario) -> None:
    """gz-sim 8 applies <interpolate_x> only to the first trajectory per animation file path."""
    sdf = hedef.actors_sdf(sc)
    moving = re.findall(r'<trajectory id="\d+" type="((?:walk|run)_\d+)">', sdf)
    assert len(moving) >= 2
    paths = {}
    for name in moving:
        m = re.search(rf'<animation name="{name}"><filename>([^<]+)</filename><interpolate_x>true', sdf)
        assert m, name
        paths[name] = m.group(1)
        assert re.fullmatch(r"model://insan/meshes/(\./)*(walk|run)_tez\.dae", m.group(1))
    assert len(set(paths.values())) == len(paths)


@pytest.mark.parametrize(
    "change, message",
    [
        (("ad: deneme", "ad: deneme\nfazla: 1"), "bilinmeyen alan"),
        (("kaynak: yok", "kaynak: uydu"), "takip.kaynak"),
        (("kaynak: yok", "kaynak: yok, hiz: 1"), "takip"),
        (("yukseklik_m: 10", "yukseklik_m: 1"), "en az 2.0"),
        (("baslangic: [10, 0]", "baslangic: [10]"), "hedef.baslangic"),
        (("hiz_mps: 3.0", "hiz_mps: 9"), "en fazla 6 m/s"),
        (("baslangic: [10, 0]", "baslangic: [10, 0]\n  davranis: {dogal: evet}"), "hedef.davranis.dogal"),
        (("baslangic: [10, 0]", "baslangic: [10, 0]\n  davranis: {sapma: 1}"), "hedef.davranis"),
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


def test_tracking_source_defaults_to_none(tmp_path: Path) -> None:
    """No takip block = open loop: the drone holds position (PX4 "Hold") while the target walks."""
    assert hedef.load(write(tmp_path, GOOD)).tracking_source == "yok"
    assert hedef.load(write(tmp_path, GOOD.replace("takip: {kaynak: yok}\n", ""))).tracking_source == "yok"


def test_drone_mode_is_gone_and_later_sources_are_refused(tmp_path: Path) -> None:
    """drone.mod selected the removed skeleton mode; follow_me / tez_los are wired in later task groups."""
    old = GOOD.replace("drone: {yukseklik_m: 10}", "drone: {yukseklik_m: 10, mod: tez}")
    with pytest.raises(ValueError, match=r"drone\.mod: .*takip\.kaynak"):
        hedef.load(write(tmp_path, old))
    for source, group in (("follow_me", 6), ("tez_los", 5)):
        with pytest.raises(ValueError, match=rf"takip\.kaynak: .*Görev grubu {group}"):
            hedef.load(write(tmp_path, GOOD.replace("kaynak: yok", f"kaynak: {source}")))


def test_unknown_scenario_lists_the_known_ones() -> None:
    with pytest.raises(FileNotFoundError, match="yuruyen_insan"):
        hedef.load("boyle_bir_senaryo_yok")


def test_shipped_scenarios_load() -> None:
    for path in (hedef.SIM_DIR / "senaryolar").glob("*.yaml"):
        assert hedef.load(str(path)).track is not None


def test_world_without_shadows(sc: hedef.Scenario, tmp_path: Path) -> None:
    text = hedef.write_world(sc, tmp_path, "<!-- extra -->", shadows=False).read_text()
    assert "<shadows>true</shadows>" not in text and "<cast_shadows>true" not in text
    assert text.index('<actor name="hedef">') < text.index("<!-- extra -->") < text.index("</world>")


CROWD = (
    GOOD
    + """
diger_insanlar:
  - baslangic: [5, 5]
    gecikme_s: 3
    kiyafet: {ust: kirmizi, alt: siyah, ten: koyu}
    yol:
      - {nokta: [15, 5], hiz_mps: 1.4}
      - {nokta: [15, -5], hiz_mps: 2.5}
  - baslangic: [0, -5]
    yol:
      - {dur_s: 5}
"""
)


def test_other_people(tmp_path: Path) -> None:
    sc = hedef.load(write(tmp_path, CROWD))
    assert len(sc.others) == 2 and sc.clothes == hedef.Clothes()
    first = sc.others[0]
    assert first.clothes == hedef.Clothes("kirmizi", "siyah", "koyu")
    assert first.track.at(62.9)[:2] == (5.0, 5.0)  # waits for its 3 s delay
    assert first.track.at(1e6)[:2] == pytest.approx((15.0, -5.0))
    assert sc.others[1].track.at(1e6)[:2] == (0.0, -5.0)


def test_animation_spellings_unique_over_all_actors(tmp_path: Path) -> None:
    """The gz-sim interpolate_x check is per file path for the whole scene, not per actor."""
    sdf = hedef.actors_sdf(hedef.load(write(tmp_path, CROWD)))
    paths = re.findall(r"<filename>(model://insan/meshes/(?:\./)*(?:walk|run)_tez\.dae)</filename>", sdf)
    assert len(paths) >= 4 and len(set(paths)) == len(paths)
    assert re.findall(r'<actor name="([^"]+)"', sdf) == ["hedef", "insan_1", "insan_2"]
    labels = [int(v) for v in re.findall(r"<label>(\d+)</label>", sdf)]
    assert labels == [hedef.TARGET_LABEL, hedef.OTHER_LABEL, hedef.OTHER_LABEL + 1]
    assert "giysi_kirmizi_siyah_koyu.dae" in sdf and "meshes/walk.dae</filename></skin>" in sdf


@pytest.mark.parametrize(
    "change, message",
    [
        (("ust: kirmizi", "ust: pembe"), "diger_insanlar[0].kiyafet.ust"),
        (("ten: koyu", "ten: mavi"), "diger_insanlar[0].kiyafet.ten"),
        (("gecikme_s: 3", "gecikme: 3"), "diger_insanlar[0]"),
        (("hiz_mps: 2.5", "hiz_mps: 8"), "diger_insanlar[0].yol[1].hiz_mps"),
    ],
)
def test_other_people_mistakes(tmp_path: Path, change: tuple[str, str], message: str) -> None:
    with pytest.raises(ValueError, match=message.replace("[", r"\[").replace(".", r"\.")):
        hedef.load(write(tmp_path, CROWD.replace(*change)))


def test_nobody_walks_through_a_tree(tmp_path: Path) -> None:
    import dunya

    tree = dunya.load("cayir").trees[0]
    text = GOOD.replace("baslangic: [10, 0]", f"baslangic: [{tree.x - 5}, {tree.y}]").replace(
        "ad: deneme", "ad: deneme\ndunya: cayir"
    )
    text = text.replace("{nokta: [20, 0], hiz_mps: 1.0}", f"{{nokta: [{tree.x + 5}, {tree.y}], hiz_mps: 1.0}}")
    with pytest.raises(ValueError, match="ağaç gövdesinden geçiyor"):
        hedef.load(write(tmp_path, text))


def test_skin_colours(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    meshes = tmp_path / "models" / "insan" / "meshes"
    meshes.mkdir(parents=True)
    effect = '<effect id="{}"><color sid="ambient">0 0 0 1</color><color sid="diffuse">0 0 0 1</color></effect>'
    (meshes / "walk.dae").write_text("".join(effect.format(e) for e in hedef.MATERIALS.values()))
    monkeypatch.setattr(hedef, "SIM_DIR", tmp_path)
    clothes = hedef.Clothes("beyaz", "siyah", "acik")
    hedef.make_skin(clothes)
    text = (meshes / clothes.skin_file()).read_text()
    assert text.count("0.7800 0.7800 0.7600 1") == 2 and text.count("0.0300 0.0300 0.0350 1") == 2
    assert text.count("0.9000 0.6800 0.5500 1") == 2
