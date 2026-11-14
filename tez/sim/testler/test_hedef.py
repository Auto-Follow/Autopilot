"""Scenario files: validation messages, the target path and its ground truth."""

import json
import re
from pathlib import Path

import numpy as np
import pytest

import hedef
import kamera

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


def test_drone_mode_is_gone(tmp_path: Path) -> None:
    """drone.mod selected the removed skeleton mode; takip.kaynak replaces it."""
    old = GOOD.replace("drone: {yukseklik_m: 10}", "drone: {yukseklik_m: 10, mod: tez}")
    with pytest.raises(ValueError, match=r"drone\.mod: .*takip\.kaynak"):
        hedef.load(write(tmp_path, old))


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


# --- Faz A scenario blocks and command line (spec 2026-11-10-m06-sim-ortami "Senaryo alanları", task group 2) ---

FULL = GOOD.replace(
    "takip: {kaynak: yok}\n",
    """takip:
  kaynak: tez_los
  mod_adi: Tez Auto Follow
  los: hakem
  px4_baslat: [tez_auto_follow start]
  px4_parametreleri: {FLW_TGT_DST: 9, MPC_XY_VEL_MAX: 0.5}
algilama: {model: ~/modeller/m.pt, imgsz: 960, conf: 0.4, sinif: Person, cekirdek: 2}
gecikme: {ek_ms: 200, titresim_ms: 20, saat_ofset_ms: -5, saat_kayma_ppm: 50}
kusurlar: {}
video: {mp4: false, qgc: true}
""",
)


def test_new_blocks_have_defaults_and_are_read(tmp_path: Path) -> None:
    """takip, algilama, gecikme, kusurlar, video: absent = the defaults of the spec table; written = read."""
    sc = hedef.load(write(tmp_path, GOOD.replace("takip: {kaynak: yok}\n", "")))
    assert sc.tracking == hedef.Tracking(source="yok", mode_name=None, los="model", px4_start=(), px4_params=())
    assert sc.detection == hedef.Detection(enabled=True, model=None, imgsz=None, conf=0.25, class_name=None, cores=4)
    assert sc.delay == hedef.Delay(extra_ms=0.0, jitter_ms=0.0, clock_offset_ms=0.0, clock_drift_ppm=0.0)
    assert sc.defects == {} and sc.video == hedef.Video(mp4=True, qgc=False, keep_frames=False)
    assert sc.tracking_source == "yok"

    sc = hedef.load(write(tmp_path, FULL))
    t = sc.tracking
    assert (t.source, t.mode_name, t.los, t.px4_start) == (
        "tez_los",
        "Tez Auto Follow",
        "hakem",
        ("tez_auto_follow start",),
    )
    assert [(p.name, p.value, p.source) for p in t.px4_params] == [
        ("FLW_TGT_DST", 9, "takip.px4_parametreleri"),
        ("MPC_XY_VEL_MAX", 0.5, "takip.px4_parametreleri"),
    ]
    assert sc.detection == hedef.Detection(True, Path.home() / "modeller" / "m.pt", 960, 0.4, "Person", 2)
    assert sc.delay == hedef.Delay(200.0, 20.0, -5.0, 50.0)
    assert sc.defects == {}  # Faz A: every camera defect off (a Faz B field is refused, test_kusurlar.py)
    assert sc.video == hedef.Video(mp4=False, qgc=True)


@pytest.mark.parametrize(
    "block, message",
    [
        ("algilama: {esik: 0.3}", "algilama: bilinmeyen alan"),
        ("algilama: {etkin: evet}", "algilama.etkin: true/false"),
        ("algilama: {conf: 1.5}", "algilama.conf: 0'dan büyük"),
        ("algilama: {imgsz: 640.5}", "algilama.imgsz: tam sayı"),
        ("algilama: {imgsz: 16}", "algilama.imgsz: en az 32"),
        ("algilama: {cekirdek: 0}", "algilama.cekirdek: en az 1"),
        ("algilama: {sinif: -1}", "algilama.sinif"),
        ("algilama: {model: 3}", "algilama.model"),
        ("algilama: true", "algilama: sözlük"),
        ("gecikme: {ek_ms: -1}", "gecikme.ek_ms: en az 0"),
        ("gecikme: {saat_ofset_ms: .nan}", "gecikme.saat_ofset_ms: sonlu"),
        ("gecikme: {kayma: 1}", "gecikme: bilinmeyen alan"),
        ("kusurlar: [gurultu]", "kusurlar: sözlük"),
        ("kusurlar: {gurultu: {sigma: 2}}", "kusurlar.gurultu: Faz B'de uygulanacak"),
        ("kusurlar: {bulanik: 1}", "kusurlar: bilinmeyen alan"),
        ("video: {mp4: 1}", "video.mp4: true/false"),
        ("video: {kareleri_sakla: true}", "video: bilinmeyen alan"),
        ("takip: {los: lazer}", "takip.los: ['model', 'hakem']"),
        ("takip: {px4_baslat: modul start}", "takip.px4_baslat: komut listesi"),
        ("takip: {px4_baslat: ['']}", "takip.px4_baslat[0]"),
        ("takip: {kaynak: tez_los, mod_adi: 3}", "takip.mod_adi: PX4 mod adı"),
    ],
)
def test_new_block_mistakes_name_the_field(tmp_path: Path, block: str, message: str) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        hedef.load(write(tmp_path, GOOD.replace("takip: {kaynak: yok}\n", block + "\n")))


def test_tez_los_needs_a_mode_name(tmp_path: Path) -> None:
    """The external mode is chosen by its AVAILABLE_MODES name (never by number): tez_los without one is refused."""
    with pytest.raises(ValueError, match=r"takip\.mod_adi: .*zorunlu.*--mod-adi"):
        hedef.load(write(tmp_path, GOOD.replace("kaynak: yok", "kaynak: tez_los")))
    cli = hedef.CommandLine(mode_name="Tez Auto Follow")
    assert hedef.load(write(tmp_path, GOOD.replace("kaynak: yok", "kaynak: tez_los")), cli).tracking.mode_name == (
        "Tez Auto Follow"
    )
    assert hedef.load(write(tmp_path, GOOD.replace("kaynak: yok", "kaynak: tez_los, mod_adi: Hold"))).tracking == (
        hedef.Tracking(source="tez_los", mode_name="Hold")
    )
    with pytest.raises(ValueError, match=r"takip\.mod_adi"):
        hedef.load(write(tmp_path, GOOD), hedef.CommandLine(source="tez_los"))


def test_model_los_needs_the_detector(tmp_path: Path) -> None:
    """LOS (i) comes from the model's boxes: with the model off it is refused, follow_me / tez_los then need hakem."""
    off = GOOD.replace("takip: {kaynak: yok}", "takip: {kaynak: yok, los: model}\nalgilama: {etkin: false}")
    with pytest.raises(ValueError, match=r"takip\.los: model.*algılama kapalı"):
        hedef.load(write(tmp_path, off))
    explicit = write(tmp_path, GOOD.replace("kaynak: yok", "kaynak: yok, los: model"))
    with pytest.raises(ValueError, match=r"takip\.los: model.*algılama kapalı"):
        hedef.load(explicit, hedef.CommandLine(no_model=True))
    # no LOS asked for: the open loop without a model has none (F1 runs like this from group 4 on)
    sc = hedef.load(write(tmp_path, GOOD), hedef.CommandLine(no_model=True))
    assert (sc.detection.enabled, sc.tracking.los) == (False, None)
    follow = write(tmp_path, GOOD.replace("kaynak: yok", "kaynak: follow_me"))
    with pytest.raises(ValueError, match=r"takip\.los: .*follow_me.*hakem"):
        hedef.load(follow, hedef.CommandLine(no_model=True))
    sc = hedef.load(follow, hedef.CommandLine(no_model=True, los="hakem"))
    assert (sc.detection.enabled, sc.tracking.los) == (False, "hakem")


@pytest.mark.parametrize(
    "params, command_line, message",
    [
        ("{flw_tgt_dst: 8}", (), "takip.px4_parametreleri: 'flw_tgt_dst' PX4 parametre adı değil"),
        ("{FLW_TGT_DISTANCE_M: 8}", (), "takip.px4_parametreleri: 'FLW_TGT_DISTANCE_M' PX4 parametre adı değil"),
        ("{FLW_TGT_DST: sekiz}", (), "takip.px4_parametreleri: FLW_TGT_DST: değer sayı olmalı"),
        ("[FLW_TGT_DST]", (), "takip.px4_parametreleri: {AD: sayı}"),
        ("{MIS_TAKEOFF_ALT: 5}", (), "takip.px4_parametreleri: MIS_TAKEOFF_ALT: kalkış yüksekliğini drone.yukseklik_m"),
        ("{}", ("flw_tgt_dst=8",), "--param 'flw_tgt_dst=8'"),
        ("{}", ("MIS_TAKEOFF_ALT=5",), "--param: MIS_TAKEOFF_ALT: kalkış yüksekliğini drone.yukseklik_m"),
    ],
)
def test_px4_parameters_follow_the_file_rules(
    tmp_path: Path, params: str, command_line: tuple[str, ...], message: str
) -> None:
    """takip.px4_parametreleri and --param go through the .params parser of group 1 (same name and number rules)."""
    text = GOOD.replace("takip: {kaynak: yok}", f"takip: {{kaynak: yok, px4_parametreleri: {params}}}")
    with pytest.raises(ValueError, match=re.escape(message)):
        hedef.load(write(tmp_path, text), hedef.CommandLine(params=command_line))


def test_command_line_overrides_the_scenario_into_the_settings(tmp_path: Path) -> None:
    """senaryo.py flags replace the YAML values; ozet.json "ayarlar" holds every setting the run uses."""
    import senaryo

    text = GOOD.replace(
        "takip: {kaynak: yok}",
        "takip: {kaynak: yok, px4_parametreleri: {FLW_TGT_DST: 9, MPC_XY_VEL_MAX: 8}}\n"
        "algilama: {conf: 0.4, cekirdek: 2}\nvideo: {qgc: false}",
    )
    argv = ["--senaryo", write(tmp_path, text), "--takip", "tez_los", "--mod-adi", "Tez Auto Follow", "--los", "hakem"]
    argv += ["--model", "~/m.pt", "--imgsz", "960", "--conf", "0.5", "--sinif", "0", "--modelsiz"]
    argv += ["--param", "FLW_TGT_DST=10", "--param", "FLW_TGT_HT=12", "--px4-baslat", "tez_auto_follow start"]
    argv += ["--gecikme-ms", "200", "--qgc", "--videosuz", "--kareleri-sakla"]
    args = senaryo.parser().parse_args(argv)
    s = senaryo.settings(hedef.load(args.senaryo, senaryo.command_line(args)))

    assert set(s) == {
        "takip",
        "algilama",
        "gecikme",
        "kusurlar",
        "video",
        "kamera",
        "px4_parametreleri",
        "henuz_bagli_degil",
    }
    assert s["kamera"] == {
        "egim_deg": kamera.NOMINAL_TILT_DEG
    }  # the sim's default mount unless kamera.egim_deg / --kamera-egim (test_kamera_egimi, test_varsayilan_montaj)
    assert s["takip"] == {
        "kaynak": "tez_los",
        "mod": "Tez Auto Follow",
        "mod_adi": "Tez Auto Follow",
        "los": "hakem",
        "px4_baslat": ["tez_auto_follow start"],
    }
    assert s["algilama"] == {
        "etkin": False,
        "model": str(Path.home() / "m.pt"),
        "imgsz": 960,
        "conf": 0.5,
        "sinif": 0,
        "cekirdek": 2,
    }
    assert s["gecikme"] == {"ek_ms": 200.0, "titresim_ms": 0.0, "saat_ofset_ms": 0.0, "saat_kayma_ppm": 0.0}
    assert s["video"] == {"mp4": False, "qgc": True, "kareleri_sakla": True} and s["kusurlar"] == {}
    params = s["px4_parametreleri"]
    # every start parameter, load order files -> scenario -> --param: the last one wins and says where it came from
    assert params["FLW_TGT_DST"] == {"deger": 10, "kaynak": "--param"}
    assert params["MPC_XY_VEL_MAX"] == {"deger": 8, "kaynak": "takip.px4_parametreleri"}
    assert params["FLW_TGT_HT"] == {"deger": 12, "kaynak": "--param"}
    assert params["IMU_GYRO_CUTOFF"]["kaynak"].startswith("gercek_dron.params:")
    assert params["SDLOG_PROFILE"]["deger"] == 163
    assert s["henuz_bagli_degil"] == {}  # model off, LOS from the referee, no MP4: nothing waits for a later group
    json.dumps(s)  # straight into ozet.json


def test_settings_of_later_groups_stop_the_run(tmp_path: Path) -> None:
    """tasks.md 2.5: a setting a later task group wires in, given with a non-default value, stops the run before the
    simulation starts and names the group; left at its default it is listed as not in effect yet."""
    good = write(tmp_path, GOOD)
    sc = hedef.load(good)
    hedef.check_wired(sc)  # defaults only: the run may start
    assert hedef.settings(sc)["henuz_bagli_degil"] == {}  # kosu.mp4 is made since group 8
    later = [
        (hedef.CommandLine(px4_start=("x start",)), "takip.px4_baslat / --px4-baslat: Görev grubu 10'da"),
        (hedef.CommandLine(qgc=True), "video.qgc: true (--qgc): Görev grubu 11'de"),
        (hedef.CommandLine(delay_ms=200.0), "gecikme.ek_ms: 200.0 (--gecikme-ms): Görev grubu 12'de"),
    ]
    for cli, message in later:
        with pytest.raises(ValueError, match=re.escape(message)):
            hedef.check_wired(hedef.load(good, cli))
    # wired already: start parameters, no model, no video, the model's settings (group 4), TEZ_LOS with an external
    # mode chosen by name and the referee's LOS (group 5), kept video frames (group 8)
    hedef.check_wired(hedef.load(good, hedef.CommandLine(params=("FLW_TGT_DST=10",), no_model=True, no_video=True)))
    hedef.check_wired(hedef.load(good, hedef.CommandLine(keep_frames=True)))
    hedef.check_wired(hedef.load(good, hedef.CommandLine(source="tez_los", mode_name="Hold", los="hakem")))
    hedef.check_wired(
        hedef.load(good, hedef.CommandLine(source="tez_los", mode_name="Yok", no_model=True, los="hakem"))
    )
    model = hedef.CommandLine(model="~/m.pt", imgsz=960, conf=0.5, class_name="Person")
    hedef.check_wired(hedef.load(write(tmp_path, GOOD + "algilama: {cekirdek: 2}\n"), model))

    # the Follow Me scenario (tasks.md 2.4): the walk of yuruyen_insan, wired since group 6; 9 m / 12.9 m with the walk
    # shifted east since the decision of 14.11 (task group 17, test_varsayilan_montaj); the 45 deg 10 m / 10 m and the
    # 8 m / 8 m of task groups 6-9 stay as takip_yuruyen_45_10m and takip_yuruyen_45_8m on the walk as it was
    follow, walk = hedef.load("takip_yuruyen"), hedef.load("yuruyen_insan")
    assert (follow.altitude, follow.tracking.source, follow.tracking.los) == (9.0, "follow_me", "model")
    assert follow.track.x == pytest.approx(walk.track.x + 2.9) and follow.track.y == pytest.approx(walk.track.y)
    hedef.check_wired(follow)
    hedef.check_wired(hedef.load("takip_yuruyen", hedef.CommandLine(los="hakem", no_model=True)))
    for name, height in (("takip_yuruyen_45_10m", 10.0), ("takip_yuruyen_45_8m", 8.0)):
        old = hedef.load(name)
        assert (old.altitude, old.tracking.source, old.tracking.los) == (height, "follow_me", "model")
        assert np.array_equal(old.track.x, walk.track.x) and old.end_time == pytest.approx(follow.end_time)
        hedef.check_wired(old)


def test_follow_me_scenario_uses_the_chosen_flw_tgt_rs() -> None:
    """Decision 1 (13.11): the Follow Me scenarios set FLW_TGT_RS 0.3, the sim's choice; the real vehicle's 22.08
    parameters have 0.1 and gercek_dron.params is not changed for it. PX4 clamps the parameter to 0.1..1.0
    (TargetEstimator::update_filter_gains): a value outside would silently be another one (the 0.05 of task 9.8)."""
    assert "FLW_TGT_RS" not in {p.name for p in hedef.load("yuruyen_insan").tracking.px4_params}
    for name in ("takip_yuruyen", "takip_yuruyen_45_10m", "takip_yuruyen_45_8m"):
        rs = {p.name: p for p in hedef.load(name).tracking.px4_params}["FLW_TGT_RS"]
        assert rs.value == 0.3 and 0.1 <= rs.value <= 1.0 and rs.source == "takip.px4_parametreleri"
    assert not (hedef.SIM_DIR / "senaryolar" / "takip_yuruyen_10m.yaml").exists()  # the 10/10 is takip_yuruyen_45_10m
    assert "FLW_TGT_RS" not in (hedef.SIM_DIR / "parametreler" / "gercek_dron.params").read_text(encoding="utf-8")


def test_follow_me_flies_at_the_scenario_height_unless_flw_tgt_ht_is_given(tmp_path: Path) -> None:
    """Follow Me keeps FLW_TGT_HT above home: without the parameter in the scenario or on the command line it is
    drone.yukseklik_m (the take-off height), loaded after the .params files like a scenario parameter; given, it
    stays as given. Other tracking sources leave it alone."""
    follow = hedef.load("takip_yuruyen")
    assert [(p.name, p.value, p.source) for p in follow.tracking.px4_params] == [
        ("FLW_TGT_HT", 9.0, "drone.yukseklik_m (follow_me)"),
        ("FLW_TGT_DST", 12.9, "takip.px4_parametreleri"),
        ("FLW_TGT_RS", 0.3, "takip.px4_parametreleri"),
    ]
    low = hedef.load("takip_yuruyen_45_8m")
    assert [(p.name, p.value) for p in low.tracking.px4_params] == [
        ("FLW_TGT_HT", 8.0),
        ("FLW_TGT_DST", 8),
        ("FLW_TGT_RS", 0.3),
    ]
    high = write(tmp_path, GOOD.replace("kaynak: yok", "kaynak: follow_me"))  # GOOD flies at 10 m
    params = hedef.settings(hedef.load(high))["px4_parametreleri"]
    assert params["FLW_TGT_HT"] == {"deger": 10.0, "kaynak": "drone.yukseklik_m (follow_me)"}
    assert params["FLW_TGT_DST"]["kaynak"].startswith("gercek_dron.params:")  # 8 m from the real vehicle
    given = hedef.load(high, hedef.CommandLine(params=("FLW_TGT_HT=15",)))
    assert [(p.name, p.value, p.source) for p in given.tracking.px4_params] == [("FLW_TGT_HT", 15, "--param")]
    scenario = write(tmp_path, GOOD.replace("kaynak: yok", "kaynak: follow_me, px4_parametreleri: {FLW_TGT_HT: 9}"))
    assert [(p.name, p.value) for p in hedef.load(scenario).tracking.px4_params] == [("FLW_TGT_HT", 9)]
    assert hedef.load(write(tmp_path, GOOD)).tracking.px4_params == ()  # yok: Hold, no Follow Me parameters
