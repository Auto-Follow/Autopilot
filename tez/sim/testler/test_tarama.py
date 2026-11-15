"""Camera tilt x height x distance scan (tarama.py): the grid, the scenario of each combination, resuming an
interrupted scan, the per-run numbers the scan adds and the decision rule (gates, group scores, stage-2 candidates);
without Gazebo, PX4 or the model."""

import json
import math
from pathlib import Path

import pandas as pd
import pytest

import hedef
import tarama

VFOV_HALF_DEG = math.degrees(math.atan2(648.0, 1773.9))  # 20.07 deg, models/x500_tez


def test_the_distance_that_centres_the_person_and_the_frame_check() -> None:
    """d = h / tan(tilt) (the camera report's rule: at 45 deg height = distance); the person (feet 0 m, head 1.75 m)
    must be inside the vertical field of view at level flight, with a margin, or the combination is not flown."""
    assert tarama.centre_distance(45.0, 8.0) == pytest.approx(8.0)
    assert tarama.centre_distance(30.0, 8.0) == pytest.approx(13.86, abs=0.01)
    assert tarama.centre_distance(30.0, 4.0) == pytest.approx(6.93, abs=0.01)
    v = tarama.view(45.0, 8.0, 8.0)
    cam_h = 8.0 + tarama.CAMERA_ABOVE_HOME_M + tarama.HOME_ABOVE_GROUND_M
    assert v["ayak_deg"] == pytest.approx(math.degrees(math.atan2(cam_h, 8.0 - 0.151)), abs=1e-6)
    assert v["bas_deg"] == pytest.approx(math.degrees(math.atan2(cam_h - 1.75, 8.0 - 0.151)), abs=1e-6)
    assert v["alt_kenar_deg"] == pytest.approx(45.0 + VFOV_HALF_DEG, abs=0.01) and v["sigar"]
    assert tarama.view(30.0, 4.0, 8.0)["sigar"]  # the user's example (camera report: 30 deg, 4 m / 8 m)
    assert not tarama.view(30.0, 15.0, 8.0)["sigar"]  # feet 62 deg below the horizon, the image ends at 50
    assert not tarama.view(45.0, 4.0, 1.5)["sigar"]


def test_the_margins_of_each_combination_against_the_users_own_figures() -> None:
    """Geometric columns (not scored): the camera's near / far ground limit at level flight, the approach margin
    (distance - near limit: coming this much closer puts the feet below the image), the fall-behind margin (far
    limit - distance), the ground width the image covers across the person's feet (corner: room to slip out sideways),
    the slant range and the depression angle to the person's body centre. The user's figures (14.11) take the camera
    at height h right above base_link; here it is h + 0.192 m above the ground (home 0.227 m, camera 0.035 m below
    base_link) and 0.151 m ahead: the approach margin comes out ≈ 0.3 m smaller, the widths are the same."""
    users = {  # (tilt, h, d): (approach margin, width) from the user's message
        (45.0, 8.0, 8.0): (4.3, 14.7),
        (45.0, 10.0, 10.0): (5.4, 18.4),
        (30.0, 4.0, 8.0): (4.7, 11.6),
        (30.0, 6.0, 10.4): (5.4, 15.6),
        (30.0, 8.0, 13.9): (7.2, 20.8),
    }
    for (tilt, h, d), (approach, width) in users.items():
        m = tarama.margins(tilt, h, d)
        cam_h = h + tarama.CAMERA_ABOVE_HOME_M + tarama.HOME_ABOVE_GROUND_M
        near = 0.151 + cam_h / math.tan(math.radians(tilt + VFOV_HALF_DEG))
        assert m["yakin_sinir_m"] == pytest.approx(near) and m["yaklasma_payi_m"] == pytest.approx(d - near)
        assert m["yaklasma_payi_m"] == pytest.approx(approach - 0.3, abs=0.12)
        assert m["genislik_m"] == pytest.approx(width, abs=0.1)
        far = 0.151 + cam_h / math.tan(math.radians(tilt - VFOV_HALF_DEG))
        assert m["uzak_sinir_m"] == pytest.approx(far) and m["geri_kalma_payi_m"] == pytest.approx(far - d)
        assert m["egik_mesafe_m"] == pytest.approx(math.hypot(d - 0.151, cam_h - 0.9))
        assert m["bakis_deg"] == pytest.approx(math.degrees(math.atan2(cam_h - 0.9, d - 0.151)))
    assert tarama.margins(30.0, 8.0, 13.9)["yaklasma_payi_m"] > tarama.margins(45.0, 10.0, 10.0)["yaklasma_payi_m"]


def test_the_plan_lists_every_combination_once_and_says_why_one_is_left_out(tmp_path: Path) -> None:
    """Tilts x heights x (centre distance times each factor) + the report's extra distances (8 m), rounded to 0.1 m;
    a distance closer than DEDUPE_M to one already planned for the same tilt and height is not planned twice; a
    combination the person does not fit in is listed as left out, with the reason."""
    plan = tarama.make_plan(
        tmp_path, "takip_yuruyen", tilts=(30.0, 45.0), heights=(8.0, 15.0), factors=(0.8, 1.0, 1.25), extra=(8.0,)
    )
    ids = [c["id"] for c in plan["bilesimler"]]
    assert len(ids) == len(set(ids))
    by = {(c["egim_deg"], c["yukseklik_m"], c["mesafe_m"]): c for c in plan["bilesimler"]}
    assert (45.0, 8.0, 8.0) in by and by[(45.0, 8.0, 8.0)]["tur"] == "merkez"  # 8 m extra is the centre itself
    assert (45.0, 8.0, 6.4) in by and (45.0, 8.0, 10.0) in by  # the report's 6.5-10 m range at 8 m
    assert by[(30.0, 8.0, 8.0)]["tur"] == "rapor_8m" and by[(30.0, 8.0, 13.9)]["tur"] == "merkez"
    assert (30.0, 15.0, 8.0) not in by
    left = {(a["egim_deg"], a["yukseklik_m"], a["mesafe_m"]): a for a in plan["atlanan"]}
    assert "kadraja sığmıyor" in left[(30.0, 15.0, 8.0)]["neden"]
    assert json.loads((tmp_path / "plan.json").read_text(encoding="utf-8"))["bilesimler"] == plan["bilesimler"]
    again = tarama.make_plan(
        tmp_path, "takip_yuruyen", tilts=(30.0, 45.0), heights=(8.0, 15.0), factors=(0.8, 1.0, 1.25), extra=(8.0,)
    )
    assert again["bilesimler"] == plan["bilesimler"]  # the same grid twice: the same ids and files


def test_a_second_band_is_added_to_the_same_plan(tmp_path: Path) -> None:
    """plan --ekle: another band (here the low heights, other factors) joins the plan; what was planned stays."""
    first = tarama.make_plan(tmp_path, "takip_yuruyen", tilts=(45.0,), heights=(10.0,), factors=(1.0, 1.25), extra=())
    both = tarama.make_plan(
        tmp_path, "takip_yuruyen", tilts=(30.0, 45.0), heights=(4.0, 10.0), factors=(1.0,), extra=(8.0,), append=True
    )
    ids = [c["id"] for c in both["bilesimler"]]
    assert ids[: len(first["bilesimler"])] == [c["id"] for c in first["bilesimler"]] and len(ids) == len(set(ids))
    assert "e30_h4_d8.0" in ids and "e45_h10_d12.5" in ids
    assert tarama.read_plan(tmp_path)["bilesimler"] == both["bilesimler"]


def test_another_base_path_joins_the_plan_at_the_same_settings(tmp_path: Path) -> None:
    """plan --ekle --temel kivrimli_yuruyus (stage 2): the same tilt, height and distance on another path is its own
    combination, not a repeat of the takip_yuruyen one; a repeat is only looked for among the same base's."""
    first = tarama.make_plan(tmp_path, "takip_yuruyen", tilts=(45.0,), heights=(10.0,), factors=(1.0,), extra=())
    both = tarama.make_plan(
        tmp_path, "kivrimli_yuruyus", tilts=(45.0,), heights=(10.0,), factors=(1.0,), extra=(), append=True
    )
    ids = [c["id"] for c in both["bilesimler"]]
    assert ids == [first["bilesimler"][0]["id"], "kivrimli_yuruyus_e45_h10_d10.0"]
    assert [c["temel"] for c in both["bilesimler"]] == ["takip_yuruyen", "kivrimli_yuruyus"]
    assert hedef.load(both["bilesimler"][1]["senaryo"]).start == pytest.approx((10.0, 0.0))
    again = tarama.make_plan(
        tmp_path, "kivrimli_yuruyus", tilts=(45.0,), heights=(10.0,), factors=(1.0,), extra=(8.0,), append=True
    )
    assert [c["id"] for c in again["bilesimler"]] == ids + ["kivrimli_yuruyus_e45_h10_d8.0"]  # its own repeats only
    left = tarama.make_plan(tmp_path, "kivrimli_yuruyus", (30.0,), (15.0,), (), (8.0,), append=True)["atlanan"]
    assert [(a["temel"], a["mesafe_m"]) for a in left] == [("kivrimli_yuruyus", 8.0)]


def test_a_combination_flies_the_base_path_shifted_so_the_person_starts_centred(tmp_path: Path) -> None:
    """The variant of takip_yuruyen: same path shape and timing, shifted east so the person starts d ahead of the
    drone (centred in the image at take-off); height, FLW_TGT_DST and tilt of the combination; the tracking block of
    the template (follow_me, model, FLW_TGT_RS 0.3) for every base, kivrimli_yuruyus too."""
    plan = tarama.make_plan(tmp_path, "takip_yuruyen", tilts=(30.0,), heights=(8.0,), factors=(1.0,), extra=())
    c = plan["bilesimler"][0]
    sc = hedef.load(c["senaryo"])
    base = hedef.load("takip_yuruyen")
    assert sc.camera.tilt_deg == 30.0 and sc.altitude == 8.0 and sc.world == "duz_alan"
    assert sc.start == pytest.approx((13.9, 0.0))
    assert (sc.track.x - base.track.x) == pytest.approx(13.9 - base.start[0])
    assert sc.track.y == pytest.approx(base.track.y) and sc.end_time == pytest.approx(base.end_time)
    params = {p.name: p.value for p in sc.tracking.px4_params}
    assert params == {"FLW_TGT_HT": 8.0, "FLW_TGT_DST": 13.9, "FLW_TGT_RS": 0.3}
    assert (sc.tracking.source, sc.tracking.los) == ("follow_me", "model")

    wander = tarama.make_plan(
        tmp_path / "k", "kivrimli_yuruyus", tilts=(45.0,), heights=(10.0,), factors=(1.0,), extra=()
    )
    k = hedef.load(wander["bilesimler"][0]["senaryo"])
    assert k.tracking.source == "follow_me" and {p.name: p.value for p in k.tracking.px4_params}["FLW_TGT_RS"] == 0.3
    assert k.start == pytest.approx((10.0, 0.0)) and k.behaviour.seed == hedef.load("kivrimli_yuruyus").behaviour.seed


def test_an_interrupted_scan_does_not_fly_finished_combinations_again(tmp_path: Path) -> None:
    """durum.json says which combinations are done; a new `kos` skips them, flies the rest, records each one as soon
    as it is done (an interruption loses at most the combination in flight)."""
    plan = tarama.make_plan(tmp_path, "takip_yuruyen", tilts=(40.0, 45.0), heights=(10.0,), factors=(1.0,), extra=())
    flown: list[str] = []

    def fake_toplu(c: dict, out: Path, repeat: int, extra: list[str]) -> int:
        flown.append(c["id"])
        if len(flown) == 2 and c["id"] == plan["bilesimler"][1]["id"] and not (tmp_path / "kesildi").exists():
            (tmp_path / "kesildi").write_text("")
            raise KeyboardInterrupt
        out.mkdir(parents=True)
        (out / "toplu.json").write_text(json.dumps({"kosu_sayisi": repeat, "kosular": []}), encoding="utf-8")
        return 0

    with pytest.raises(KeyboardInterrupt):
        tarama.run_stage(tmp_path, "asama1", 1, [], runner=fake_toplu)
    state = json.loads((tmp_path / "asama1" / "durum.json").read_text(encoding="utf-8"))
    assert list(state["bitti"]) == [plan["bilesimler"][0]["id"]]
    tarama.run_stage(tmp_path, "asama1", 1, [], runner=fake_toplu)
    assert flown == [c["id"] for c in plan["bilesimler"]] + [plan["bilesimler"][1]["id"]]
    tarama.run_stage(tmp_path, "asama1", 1, [], runner=fake_toplu)  # all done: nothing flies
    assert len(flown) == 3
    only = tarama.run_stage(
        tmp_path, "asama2", 3, ["--los", "hakem"], only=[plan["bilesimler"][1]["id"]], runner=fake_toplu
    )
    assert only == [plan["bilesimler"][1]["id"]] and flown[-1] == plan["bilesimler"][1]["id"]


def run_folder(root: Path, name: str, last_follow: float, heights: list[float]) -> Path:
    """A run folder with the files the scan reads besides ozet.json: follow_target.csv, dogru_cevap.csv."""
    folder = root / name
    folder.mkdir(parents=True)
    pd.DataFrame(
        {"t": [30.0, 60.0, last_follow, last_follow + 1.0], "sonuc": ["gonderildi"] * 3 + ["hiz_siniri"]}
    ).to_csv(folder / "follow_target.csv", index=False)
    t = [60.0 + 0.5 * k for k in range(len(heights))]
    pd.DataFrame(
        {
            "t": t,
            "gorunur": [True] * len(heights),
            "hedef_kutu_v0": [400.0] * len(heights),
            "hedef_kutu_v1": [400.0 + h for h in heights],
            "bas_v": [405.0] * len(heights),
            "ayak_v": [395.0 + h for h in heights],
        }
    ).to_csv(folder / "dogru_cevap.csv", index=False)
    return folder


def test_how_much_closer_the_drone_came_and_where_the_person_left_the_image(tmp_path: Path) -> None:
    """Per run: FLW_TGT_DST - the closest horizontal distance from the walk on, in the stop (the 3 s before the corner
    that starts after a stop and 1 s into it) and after each turn (8 s from its start); how long the person's body
    centre was out of the image below, at a side and above it."""
    folder = tmp_path / "r"
    folder.mkdir()
    t = [60.0 + 0.1 * k for k in range(300)]  # 60..89.9 s
    dist = [10.0 - (4.0 if 71.0 <= x < 72.0 else 0.0) - (7.0 if 79.0 <= x < 79.5 else 0.0) for x in t]
    v = [1400.0 if 79.0 <= x < 80.0 else (-50.0 if 85.0 <= x < 86.0 else 600.0) for x in t]
    u = [2500.0 if 82.0 <= x < 83.0 else 1150.0 for x in t]
    pitch = [12.0 if 79.0 <= x < 79.5 else 0.0 for x in t]  # nose up while braking at the corner
    pd.DataFrame(
        {
            "t": t,
            "yatay_mesafe": dist,
            "merkez_u": u,
            "merkez_v": v,
            "dron_pitch_deg": pitch,
            "kamera_z": [8.19] * len(t),
        }
    ).to_csv(folder / "dogru_cevap.csv", index=False)
    corners = [
        {"baslangic_s": 60.3, "durus_s": 34.0, "donus_deg": None},
        {"baslangic_s": 73.0, "durus_s": 3.0, "donus_deg": 92.0},
        {"baslangic_s": 77.6, "durus_s": 0.0, "donus_deg": 87.0},
    ]
    m = tarama.approach_numbers(folder, start=60.0, distance=10.0, corners=corners, tilt_deg=45.0)
    assert m["yaklasma_m"] == pytest.approx(7.0) and m["kose_yaklasma_m"] == pytest.approx(7.0)
    assert m["durma_yaklasma_m"] == pytest.approx(4.0)
    assert m["kadraj_disi_alt_s"] == pytest.approx(1.0, abs=0.11) and m["kadraj_disi_yan_s"] == pytest.approx(
        1.0, abs=0.11
    )
    assert m["kadraj_disi_ust_s"] == pytest.approx(1.0, abs=0.11)
    # the near limit with the drone's own pitch: nose 12 deg up lifts the image's bottom edge to 45 + 20.07 - 12 deg
    assert m["burun_kalkisi_maks_deg"] == pytest.approx(12.0)
    near_up = 8.19 / math.tan(math.radians(45.0 + VFOV_HALF_DEG - 12.0)) + 0.151
    assert m["dinamik_pay_asimi_m"] == pytest.approx(near_up - 3.0, abs=1e-6)  # 3 m away at that moment


def test_the_scan_adds_whether_the_person_was_lost_and_how_big_they_looked(tmp_path: Path) -> None:
    """Per run: the person counts as lost if the last FOLLOW_TARGET that went out is more than 3 s (PX4's stale time)
    before the end; the median height of the person's referee box and what the model sees of it at its imgsz."""
    kept = tarama.run_numbers(run_folder(tmp_path, "a", 88.0, [200.0, 180.0, 220.0]), end=90.0, imgsz=640)
    assert kept["kisi_sonda_kayip"] == 0.0 and kept["son_follow_target_s"] == 88.0
    assert kept["kisi_kutu_boyu_px"] == 200.0 and kept["kisi_model_girisi_px"] == pytest.approx(200.0 * 640 / 2304)
    lost = tarama.run_numbers(run_folder(tmp_path, "b", 80.0, [150.0]), end=90.0, imgsz=640)
    assert lost["kisi_sonda_kayip"] == 1.0 and lost["sonda_kayip_s"] == pytest.approx(10.0)
    # the model never found the person: no FOLLOW_TARGET ever went out, so no follow_target.csv either (it is
    # opened with the first attempt); the stock mode never followed: lost, like the rule says (found in stage 1)
    never = run_folder(tmp_path, "c", 80.0, [80.0])
    (never / "follow_target.csv").unlink()
    m = tarama.run_numbers(never, end=90.0, imgsz=640)
    assert m["kisi_sonda_kayip"] == 1.0 and math.isnan(m["son_follow_target_s"])
    assert not tarama.gate([{"en_az_yatay_mesafe_m": 26.0, **m}])["gecti"]


def combo(i: int, tilt: float, h: float, d: float, **metrics: float) -> dict:
    defaults = {
        "en_az_yatay_mesafe_m": 4.0,
        "mesafe_6m_alti_orani": 0.02,
        "mesafe_4m_alti_orani": 0.0,
        "kisi_sonda_kayip": 0.0,
        "kilit_kaybi_sayisi": 3.0,
        "en_uzun_kayip_s": 1.0,
        "hedef_kadrajda_orani": 0.9,
        "gorunur_kalma": 0.9,
        "algilama_orani": 0.6,
        "kisi_kutu_boyu_px": 180.0,
        "konum_hatasi_ort_m": 0.3,
        "konum_hatasi_p95_m": 0.6,
        "arkada_kalma_hatasi_ort_deg": 40.0,
        "bagil_mesafe_hatasi": 0.15,
        "baslangic_yorunge_donusu_deg": 200.0,
        "kose_px4_yetisme_ort_s": 2.0,
        "kose_px4_yetismedi_sayisi": 0.0,
        "kose_arkada_kalma_maks_deg": 140.0,
    }
    runs = [{**defaults, **metrics}]
    return {"id": f"c{i}", "egim_deg": tilt, "yukseklik_m": h, "mesafe_m": d, "tur": "merkez", "kosular": runs}


def test_the_decision_rule_gates_scores_and_ranks() -> None:
    """Gates first (every run: at least 3 m from the person, the person not lost at the end, the run valid), then a
    score per group (min-max over the combinations that passed, best = 1) and the mean of the groups; nothing is
    reduced to one number before the table: every group's score and the raw values stay."""
    combos = [
        combo(1, 45.0, 10.0, 10.0),
        combo(2, 30.0, 8.0, 13.9, algilama_orani=0.8, kisi_kutu_boyu_px=185.0),
        combo(3, 45.0, 8.0, 8.0, en_az_yatay_mesafe_m=1.2),  # comes within 3 m: out
        combo(4, 35.0, 10.0, 14.3, kisi_sonda_kayip=1.0),  # lost the person: out
        combo(5, 40.0, 12.0, 14.3, konum_hatasi_ort_m=0.6, konum_hatasi_p95_m=1.2),
    ]
    table = tarama.rank(combos)
    by = {r["id"]: r for r in table}
    assert not by["c3"]["kapi"]["gecti"] and "en az yatay mesafe" in by["c3"]["kapi"]["neden"]
    assert not by["c4"]["kapi"]["gecti"] and "kaybedildi" in by["c4"]["kapi"]["neden"]
    passed = [r for r in table if r["kapi"]["gecti"]]
    assert sorted(r["sira"] for r in passed) == [1, 2, 3] and all(
        r["sira"] is None for r in table if not r["kapi"]["gecti"]
    )
    assert set(by["c1"]["puanlar"]) == set(tarama.GROUPS)
    assert by["c2"]["puanlar"]["algilama"] > by["c1"]["puanlar"]["algilama"]  # found more
    assert by["c5"]["puanlar"]["konum"] == 0.0 and by["c1"]["puanlar"]["konum"] == 1.0
    assert by["c1"]["puanlar"]["geometri"] > by["c2"]["puanlar"]["geometri"]  # 45 deg: more horizon margin
    total = sum(by["c1"]["puanlar"].values()) / len(tarama.GROUPS)
    assert by["c1"]["toplam"] == pytest.approx(total)
    assert by["c1"]["sim_puani"] == pytest.approx(
        sum(v for k, v in by["c1"]["puanlar"].items() if k != "geometri") / (len(tarama.GROUPS) - 1)
    )
    assert by["c1"]["geometri"]["ufuk_payi_deg"] == pytest.approx(45.0 - VFOV_HALF_DEG, abs=0.01)
    assert by["c2"]["geometri"]["zemin_duyarliligi"] == pytest.approx(13.9 / 8.0)


def test_stage_two_takes_the_best_of_each_tilt_then_the_next_best_and_the_references() -> None:
    """Candidates: among the combinations that passed the gates, the best of each tilt, then the next best overall
    up to `count`; the 45 deg 8/8 and 10/10 references always fly (whatever their gates said)."""
    combos = [
        combo(1, 45.0, 10.0, 10.0),
        combo(2, 45.0, 12.0, 12.0, algilama_orani=0.9),
        combo(3, 30.0, 8.0, 13.9),
        combo(4, 30.0, 10.0, 17.3, algilama_orani=0.1),
        combo(5, 40.0, 10.0, 11.9, en_az_yatay_mesafe_m=2.0),  # the only 40 deg one fails: no 40 deg candidate
        combo(6, 45.0, 8.0, 8.0, en_az_yatay_mesafe_m=1.0),
    ]
    table = tarama.rank(combos)
    chosen = tarama.candidates(table, count=3)
    ids = [c["id"] for c in chosen]
    best45 = min((r for r in table if r["egim_deg"] == 45.0 and r["kapi"]["gecti"]), key=lambda r: r["sira"])["id"]
    assert ids[:2] == sorted([best45, "c3"], key=lambda i: next(r["sira"] for r in table if r["id"] == i))
    assert len([i for i in ids if i not in ("c1", "c6")]) >= 2 and "c5" not in ids
    refs = {c["id"]: c["neden"] for c in chosen}
    assert "başvuru" in refs["c6"] and "c1" in refs
