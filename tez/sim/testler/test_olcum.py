"""Metrics of a run (olcum.py) on hand-made tables: no Gazebo, PX4 or model; each expected value is worked out in the
test (spec 2026-11-10-m06-sim-ortami "Ölçüt Tanımları")."""

import math
import re
from pathlib import Path

import numpy as np
import pytest

import algilama
import goruntu
import kamera
import konumlama
import olcum

REPO = Path(__file__).resolve().parents[3]
SPEC = REPO / "agent-os/specs/2026-11-10-m06-sim-ortami/spec.md"
CM3 = kamera.Camera(2304, 1296, 1773.9, 1773.9, 1152.0, 648.0)
TARGET = (1000.0, 400.0, 1100.0, 600.0)  # the target's referee box [px]
OTHER = (1400.0, 400.0, 1500.0, 600.0)  # another person's


def kutu(u0: float, v0: float, u1: float, v1: float) -> algilama.Kutu:
    return algilama.Kutu(u0, v0, u1, v1, 0.8, 0, "Person")


def referee_row(t: float, visible: bool = True, other: tuple = OTHER, **more: object) -> dict:
    row = {
        "t": t,
        "gorunur": visible,
        **dict(zip(("hedef_kutu_u0", "hedef_kutu_v0", "hedef_kutu_u1", "hedef_kutu_v1"), TARGET, strict=True)),
    }
    row |= dict(zip(("insan1_kutu_u0", "insan1_kutu_v0", "insan1_kutu_u1", "insan1_kutu_v1"), other, strict=True))
    return row | more


def model_row(t: float, chosen: tuple | None, **more: object) -> dict:
    row = {"t_us": algilama.time_key(t), "t": t, "secilen_kutu": None if chosen is None else 0}
    for k, v in zip(("u0", "v0", "u1", "v1"), chosen or (math.nan,) * 4, strict=True):
        row[f"secilen_{k}"] = v
    return row | more


def test_every_key_of_the_spec_table_is_measured() -> None:
    """The keys of "Ölçüt Tanımları" (second column, {a,b} expanded) are exactly olcum.KEYS: ozet.json gets each of
    them in every run, NaN where a metric does not apply."""
    text = SPEC.read_text(encoding="utf-8").split("## Ölçüt Tanımları", 1)[1].split("\n## ", 1)[0]
    keys = []
    for line in text.splitlines():
        cells = line.split("|")
        if len(cells) > 3 and "`" in cells[2]:
            keys += [k for p in re.findall(r"`([^`]+)`", cells[2]) if "." not in p for k in olcum._expand(p)]
    assert len(keys) == len(set(keys))
    assert set(keys) == set(olcum.KEYS)


def test_nav_state_names_are_px4s() -> None:
    ui = (REPO / "src/lib/modes/ui.hpp").read_text(encoding="utf-8")
    names = re.findall(r'"([^"]+)"', ui.split("nav_state_names[")[1].split("};")[0])
    assert list(olcum.NAV_STATE_NAMES) == names and olcum.NAV_STATE_NAMES[19] == "Follow Target"


def test_model_metrics_find_choose_and_mistake() -> None:
    """Four processed frames: found (and a false positive), missed, the wrong person chosen (dressed like the
    target), and the target hidden (it does not count for finding it)."""
    shifted = kutu(1010, 400, 1110, 600)  # IoU with TARGET: 90 * 200 / (2 * 100 * 200 - 90 * 200) = 9/11
    far = kutu(100, 100, 150, 200)  # nobody there
    on_other = kutu(1400, 400, 1500, 600)
    frames = [60.0, 60.1, 60.2, 60.3]
    rows = [
        model_row(60.0, (1010, 400, 1110, 600)),
        model_row(60.1, None),
        model_row(60.2, (1400, 400, 1500, 600)),
        model_row(60.3, (1010, 400, 1110, 600)),
    ]
    boxes = {
        algilama.time_key(60.0): (shifted, far),
        algilama.time_key(60.1): (),
        algilama.time_key(60.2): (on_other,),
        algilama.time_key(60.3): (shifted,),
    }
    refs = [referee_row(t, visible=t != 60.3) for t in frames] + [referee_row(59.0)]  # 59 s: before the window
    m = olcum.model_metrics(rows, boxes, refs, 60.0, 61.0, others=1, same_clothes=frozenset({1}))
    assert (m["model_kare"], m["hedef_gorunur_islenen"], m["iou05_kare_sayisi"]) == (4, 3, 1)
    assert m["algilama_orani"] == pytest.approx(1 / 3) and m["kacirma_orani"] == pytest.approx(2 / 3)
    assert m["iou_ort"] == pytest.approx(9 / 11) and m["iou_p50"] == pytest.approx(9 / 11)
    assert m["iou_max"] == pytest.approx(9 / 11)  # the hidden frame's box counts for the check, not for finding
    assert m["secim_dogru_orani"] == pytest.approx(1 / 3)  # 60.0 of the three visible frames
    assert m["secili_kare_orani"] == pytest.approx(3 / 4)
    assert m["yanlis_kisi_orani"] == pytest.approx(1 / 4) and m["yanlis_kisi_ayni_kiyafet_orani"] == pytest.approx(
        1 / 4
    )
    assert m["yanlis_pozitif_kare_basi"] == pytest.approx(1 / 4)  # the box far off in the first frame
    other_clothes = olcum.model_metrics(rows, boxes, refs, 60.0, 61.0, others=1)
    assert other_clothes["yanlis_kisi_ayni_kiyafet_orani"] == 0.0
    nothing = olcum.model_metrics([], {}, refs, 60.0, 61.0)
    assert math.isnan(nothing["algilama_orani"]) and math.isnan(nothing["iou_ort"])


def test_los_error_and_its_systematic_part() -> None:
    """The chosen box's LOS (i) against the referee's LOS (ii): 1 deg to the right in one frame, 1 deg down in the
    other; a frame whose chosen box is not the target does not count."""
    truth = kamera.camera_to_body(math.radians(45)) @ np.array([0.0, 0.0, 1.0])  # (cos 45, 0, sin 45), body FRD
    one = math.radians(1.0)
    right = math.cos(one) * truth + math.sin(one) * np.array([0.0, 1.0, 0.0])  # exactly 1 deg off, to the right
    down = math.cos(one) * truth + math.sin(one) * np.array([-truth[2], 0.0, truth[0]])  # and 1 deg further down
    los = {f"los_govde_{k}": v for k, v in zip("xyz", truth, strict=True)}
    refs = [referee_row(t, **los) for t in (60.0, 60.1, 60.2)]
    rows = [
        model_row(60.0, TARGET, **{f"los_i_{k}": v for k, v in zip("xyz", right, strict=True)}),
        model_row(60.1, TARGET, **{f"los_i_{k}": v for k, v in zip("xyz", down, strict=True)}),
        model_row(60.2, OTHER, **{f"los_i_{k}": v for k, v in zip("xyz", -truth, strict=True)}),
    ]
    m = olcum.los_metrics(rows, refs, 60.0, 61.0)
    assert m["los_aci_kare"] == 2
    assert m["los_aci_hatasi_ort_deg"] == pytest.approx(1.0, abs=1e-9)
    assert m["los_aci_hatasi_maks_deg"] == pytest.approx(1.0, abs=1e-9)
    th, tv, _ = kamera.deviation(truth, "body")
    (rh, rv, _), (dh, dv, _) = kamera.deviation(right, "body"), kamera.deviation(down, "body")
    assert m["los_sapma_farki_yatay_ort_deg"] == pytest.approx(((rh - th) + (dh - th)) / 2, abs=1e-9)
    assert m["los_sapma_farki_dikey_ort_deg"] == pytest.approx(((rv - tv) + (dv - tv)) / 2, abs=1e-9)
    assert dv - tv == pytest.approx(1.0, abs=1e-9) and dh - th == pytest.approx(0.0, abs=1e-9)


def test_latency_statistics_and_the_lock_by_window() -> None:
    """TEZ_LOS by send time; invalid and refused ones by capture time; p95 by linear interpolation (numpy)."""

    def attempt(t: float, sent_at: float, ms: float, sonuc: str = "gonderildi", target: int = 1) -> dict:
        return {"t": t, "gonderim_sim": sent_at, "uctan_uca_ms": ms, "sonuc": sonuc, "hedef": target}

    attempts = [
        attempt(59.88, 59.99, 110.0),  # sent before the window
        attempt(59.9, 60.02, 120.0),  # captured before, sent inside: counts
        attempt(60.1, 60.24, 140.0, target=0),
        attempt(60.5, 60.66, 160.0),
        attempt(60.7, 60.8, 100.0),
        attempt(60.8, math.nan, math.nan, "gecersiz"),
        attempt(60.85, math.nan, math.nan, "hiz_siniri"),
    ]
    for a in attempts:
        a |= {"ek_gecikme_ms": 0.03, "hazir_ms": a["uctan_uca_ms"] - 1.0}
    events = [
        {"t": 59.0, "olay": "ilk_kilit"},
        {"t": 60.3, "olay": "kilit_kaybi"},
        {"t": 60.4, "olay": "yeniden_kilit"},
    ]
    m = olcum.stream_metrics(attempts, events, 60.0, 61.0)
    assert (m["tez_los_gonderilen"], m["tez_los_hedef_yok"], m["tez_los_gecersiz"], m["tez_los_reddedilen"]) == (
        4,
        1,
        1,
        1,
    )
    assert m["tez_los_hizi_hz"] == pytest.approx(4.0)
    assert m["uctan_uca_ms_ort"] == pytest.approx(130.0) and m["uctan_uca_ms_p50"] == pytest.approx(130.0)
    assert m["uctan_uca_ms_p95"] == pytest.approx(157.0) and m["uctan_uca_ms_maks"] == 160.0
    assert (m["kilit_kaybi_sayisi"], m["yeniden_kilit_sayisi"]) == (1, 1)


def test_frames_processed_skipped_and_their_times() -> None:
    """Window 60.0..60.2 s: received 60.02 .. 60.18 (5), processed 60.06 and 60.18, replaced 60.02, 60.10, 60.14;
    of the 6 camera frames 60.19 never reached the reader; a replaced frame whose header was not read has no time."""
    rows = [
        {
            "t_us": algilama.time_key(t),
            "t": t,
            "model_ms": ms,
            "cozme_ms": 1.0,
            "kusur_ms": 0.0,
            "ulasma_ms": 20.0,
            "bekleme_ms": 5.0,
            "islem_ms": 66.0,
            "teslim_ms": 1.0,
        }
        for t, ms in ((59.94, 50.0), (60.06, 60.0), (60.18, 70.0))
    ]
    skipped = [goruntu.Skipped(i, t, 0.0) for i, t in enumerate((59.86, 59.90, 60.02, 60.10, 60.14, math.nan))]
    refs = [{"t": t} for t in (59.86, 59.90, 59.94, 59.98, 60.02, 60.06, 60.10, 60.14, 60.18, 60.19)]
    m = olcum.frame_metrics(rows, skipped, refs, 60.0, 60.2)
    assert (m["uretilen"], m["islenen"], m["atlanan"]) == (5, 2, 3)
    assert (m["kamera_karesi"], m["okuyucuya_ulasmayan"], m["zamani_okunamayan_atlanan"]) == (6, 1, 1)
    assert m["atlanan_kare_orani"] == pytest.approx(1 - 2 / 5) and m["islenen_kare_hizi_hz"] == pytest.approx(10.0)
    assert (m["model_ms_ort"], m["model_ms_maks"], m["ulasma_ms_ort"]) == (65.0, 70.0, 20.0)


def walk(t0: float = 50.0, t1: float = 80.0, rate: float = 30.0) -> list[dict]:
    """A target that stands at (10, 0) until 60 s, then walks east at 1.4 m/s. The drone, 8 m up (camera 8 m):
    until 60 s it goes half round the standing target at 8 m, from east (orbit 0 deg, ENU) through north to west;
    then it stays 8 m behind (west) except 70..71 s, when it is 2 m behind, and 74..76 s, when it is beside it
    (north). Feet and head in the frame except while near (70..71 s: the feet are below the image)."""
    out = []
    for t in np.arange(t0, t1, 1.0 / rate):
        moving = t >= 60.0
        tx = 10.0 + (1.4 * (t - 60.0) if moving else 0.0)
        if not moving:
            a = math.radians(180.0 * (t - t0) / (60.0 - t0))
            dx, dy = 8.0 * math.cos(a), 8.0 * math.sin(a)
        elif 70.0 <= t < 71.0:
            dx, dy = -2.0, 0.0
        elif 74.0 <= t < 76.0:
            dx, dy = 0.0, 8.0
        else:
            dx, dy = -8.0, 0.0
        near = 70.0 <= t < 71.0
        out.append(
            {
                "t": float(t),
                "dron_x": tx + dx,
                "dron_y": dy,
                "kamera_z": 8.0,
                "hedef_x": tx,
                "hedef_y": 0.0,
                "hedef_yaw": 0.0,
                "hedef_hiz": 1.4 if moving else 0.0,
                "yatay_mesafe": math.hypot(dx, dy),
                "ayak_gorunur": not near,
                "bas_gorunur": True,
            }
        )
    return out


def test_distance_frame_and_behind_angle_of_a_follow_run() -> None:
    rows = walk()
    m, events = olcum.tracking_metrics(rows, 60.0, 80.0, CM3, following=True, follow_distance=8.0)
    assert m["en_az_yatay_mesafe_m"] == pytest.approx(2.0) and 70.0 <= m["en_az_yatay_mesafe_t_s"] < 71.0
    assert m["yakin_mesafe_3m_suresi_s"] == pytest.approx(1.0, abs=0.04) and m["yakin_mesafe_3m_olay_sayisi"] == 1
    assert events[0]["baslangic_s"] == pytest.approx(70.0, abs=0.04) and events[0]["en_az_m"] == pytest.approx(2.0)
    vfov_half = math.atan2(648.0, 1773.9)  # 20.07 deg
    near = 8.0 / math.tan(math.radians(45.0) + vfov_half) + 0.151
    assert m["kadraj_yakin_sinir_m"] == pytest.approx(near) and near == pytest.approx(3.870, abs=0.001)
    assert m["kadraj_uzak_sinir_m"] == pytest.approx(8.0 / math.tan(math.radians(45.0) - vfov_half) + 0.151)
    assert m["kadraj_yakin_sinir_alti_s"] == pytest.approx(1.0, abs=0.04)  # 2 m < 3.9 m
    assert m["kadraj_uzak_sinir_ustu_s"] == 0.0
    assert (
        m["ayak_kadrajda_orani"] == pytest.approx(19 / 20, abs=0.002)
        and m["hedef_kadrajda_orani"] == m["ayak_kadrajda_orani"]
    )
    # behind = west of an east-walking target: 0 deg, except the 2 s beside it (90 deg)
    assert m["arkada_kalma_hatasi_ort_deg"] == pytest.approx(90.0 * 2 / 20, abs=0.5)
    assert m["arkada_kalma_hatasi_maks_deg"] == pytest.approx(90.0)
    assert m["arkada_kalma_hatasi_90_ustu_s"] == 0.0  # beside, not ahead
    assert m["yatay_mesafe_hatasi_ort_m"] == pytest.approx((6.0 * 1 + 0.0 * 19) / 20, abs=0.05)
    assert m["baslangic_yorunge_donusu_deg"] == pytest.approx(180.0, abs=1.0)  # east -> north -> west, 50..60 s
    assert m["yuruyus_basi_yorunge_donusu_deg"] == pytest.approx(0.0, abs=1.0)  # behind from the first step
    hovering, _ = olcum.tracking_metrics(rows, 60.0, 80.0, CM3, following=False)
    assert math.isnan(hovering["arkada_kalma_hatasi_ort_deg"]) and math.isnan(hovering["baslangic_yorunge_donusu_deg"])
    assert hovering["en_az_yatay_mesafe_m"] == pytest.approx(2.0)  # the distance counts in every source
    assert math.isnan(hovering["yatay_mesafe_hatasi_ort_m"])


def test_orbit_turn_ignores_hover_jitter() -> None:
    """A drone hovering 8 m from a standing target with 2 cm of noise at 30 Hz turns ~0 deg, not the sum of the
    noise (taken every ORBIT_STEP_S)."""
    rng = np.random.default_rng(1)
    t = np.arange(0.0, 30.0, 1 / 30)
    angle = np.degrees(np.arctan2(rng.normal(0, 0.02, t.size), 8.0 + rng.normal(0, 0.02, t.size)))
    assert olcum.orbit_turn(t, angle, 0.0, 30.0) < 15.0
    assert np.abs(np.diff(angle)).sum() > 50.0  # summed at 30 Hz it would look like a turn


def test_px4s_follow_target_status() -> None:
    """follow_target_status every 400 ms: the course stays at its initial 0 (north) until the target walks fast
    enough; the orbit angle setpoint turns 0 -> 180 deg while the target stands (north -> south of it) and
    180 -> 270 deg once it walks east (course 90 deg NED); the course error against the true one while walking."""
    t = np.round(np.arange(27.0, 80.0, 0.4), 6)
    course = np.where(t >= 62.0, math.radians(90.0), 0.0)
    orbit = np.radians(np.interp(t, [27.0, 37.0, 62.0, 70.0], [0.0, 180.0, 180.0, 270.0]))
    status = {"timestamp": t * 1e6, "tracked_target_course": course, "orbit_angle_setpoint": orbit}

    def truth(s: float) -> tuple:
        return (0.0, 0.0, 0.0, 1.4 if s >= 60.0 else 0.0, "walk")  # ENU yaw 0 = east = NED course 90

    m = olcum.follow_status_in_ulog(status, 60.0, 80.0, truth)
    assert m["px4_durum_sayisi"] == t.size and (m["px4_rota_ilk_deg"], m["px4_yorunge_acisi_ilk_deg"]) == (0.0, 0.0)
    assert m["px4_rota_kuzey_varsayimi_s"] == pytest.approx(62.2 - 27.0, abs=1e-6)  # first sample >= 62 s: 62.2 s
    assert m["px4_yorunge_donusu_baslangic_deg"] == pytest.approx(180.0, abs=0.5)
    # 60..70 s; the samples at 69.8 and 70.2 s straddle the end of the turn: 268.875 deg at 70 s
    assert m["px4_yorunge_donusu_yuruyus_basi_deg"] == pytest.approx(88.875, abs=1e-6)
    walking = t[(t >= 60.0) & (t <= 80.0)]
    late = (walking < 62.0).sum()  # course still 0 while the target walks east: 90 deg off
    assert m["px4_rota_hatasi_ort_deg"] == pytest.approx(90.0 * late / walking.size)
    assert olcum.follow_status_in_ulog(None, 60.0, 80.0)["px4_durum_sayisi"] == 0


def test_mode_timeline_and_how_long_the_mode_held() -> None:
    """vehicle_status of the two ULog files (the logger restarted at 27.5 s): takeoff, hold, Follow Target from
    27 s, Land from 88 s; the run switched at 27.1 s, so the wanted nav_state is 19."""
    t = np.array([10.0, 20.0, 25.0, 26.0, 27.0, 27.6, 50.0, 88.0, 95.0])
    nav = np.array([4, 17, 4, 4, 19, 19, 19, 18, 18])
    line = olcum.mode_timeline({"timestamp": t * 1e6, "nav_state": nav})
    assert [(s["nav_state"], s["ad"]) for s in line] == [
        (4, "Hold"),
        (17, "Takeoff"),
        (4, "Hold"),
        (19, "Follow Target"),
        (18, "Land"),
    ]
    wanted = olcum.wanted_nav_state(line, 27.1)
    assert wanted == 19
    assert olcum.mode_kept(line, wanted, 60.0, 90.0) == pytest.approx(28.0 / 30.0)
    assert math.isnan(olcum.mode_kept(line, None, 60.0, 90.0))
    changes = [(27.1, "Follow Target"), (88.2, "Land")]
    assert olcum.mavlink_mode_kept(changes, "Follow Target", 60.0, 90.0) == pytest.approx(28.2 / 30.0)


def test_tez_los_in_a_ulog_without_debug_vect_has_every_key() -> None:
    """A run whose ULog holds no debug_vect (no TEZ_LOS reached PX4) still has every key (the log line of a run with
    no link to PX4 failed on a missing one)."""
    m = olcum.tez_los_in_ulog(None, 60.0, 90.0, [])
    assert m["tez_los_px4_sayisi"] == 0 and m["tez_los_px4_eslesen"] == 0
    assert all(k in m for k in ("uctan_uca_px4_ms_ort", "px4_varis_eksi_gonderim_ms_min", "tez_los_px4_hizi_hz"))


def test_tez_los_messages_that_reached_px4_are_counted_from_the_ulog_columns() -> None:
    """debug_vect in the ULog (pyulog: one int8 column per character of the name); only TEZ_LOS counts, other
    DEBUG_VECT senders share the topic (spec "Varsayımlar" 1)."""
    names = ["TEZ_LOS", "TEZ_LOS", "BASKA", "TEZ_LOS", "TEZ_LOS"]
    data = {"timestamp": np.array([59.99e6, 60.0e6, 60.01e6, 61.5e6, 62.01e6])}
    for i in range(10):
        data[f"name[{i}]"] = np.array([ord(n[i]) if i < len(n) else 0 for n in names], dtype=np.int8)
    assert list(olcum.debug_names(data)) == names
    for k, v in zip("xyz", ([0.6, 0.6, 0.0, math.nan, 0.8], [0.0] * 5, [0.8, 0.8, 1.0, math.nan, 0.6]), strict=True):
        data[k] = np.array(v, dtype=np.float32)
    m = olcum.tez_los_in_ulog(data, 60.0, 62.0)
    assert (m["tez_los_px4_sayisi"], m["tez_los_px4_hizi_hz"]) == (2, pytest.approx(1.0))
    # the logged ones are matched to the sent ones by their values (PX4 drops time_usec): PX4 arrival - capture
    sent = [
        {"t": 59.88, "x": 0.6, "y": 0.0, "z": 0.8, "gonderim_sim": 59.998},
        {"t": 61.38, "x": math.nan, "y": math.nan, "z": math.nan, "gonderim_sim": 61.498},  # NaN: ambiguous, skipped
        {"t": 61.89, "x": 0.8, "y": 0.0, "z": 0.6, "gonderim_sim": 62.007},
    ]
    m = olcum.tez_los_in_ulog(data, 60.0, 62.5, sent)
    assert m["tez_los_px4_sayisi"] == 3 and m["tez_los_px4_eslesen"] == 2  # the NaN one at 61.5 s is not matched
    assert m["uctan_uca_px4_ms_ort"] == pytest.approx(120.0, abs=0.01)
    assert m["px4_varis_eksi_gonderim_ms_ort"] == pytest.approx(2.5, abs=0.01)  # arrived 2 and 3 ms after the send


def test_follow_target_in_the_ulog_and_where_px4_thought_the_target_was() -> None:
    """follow_target (the logger keeps one sample per 500 ms) and follow_target_estimator (every 200 ms): its estimate
    against where the target really was at the same PX4 time (= sim time in SITL), and how long it was stale (no
    FOLLOW_TARGET for 3 s: PX4 keeps the last position and stops moving it)."""
    world = konumlama.WorldGeo(47.397971057728974, 8.546163739800146, 0.0)
    target = {"timestamp": np.array([59.5e6, 60.0e6, 60.5e6, 61.0e6, 62.9e6])}
    t = np.round(np.arange(60.0, 63.001, 0.2), 6)
    geo = [world.to_geodetic(10.0 + (s - 60.0) - 0.3, 2.0) for s in t]  # 0.3 m behind a target walking east at 1 m/s
    estimator = {
        "timestamp": t * 1e6,
        "valid": np.array([0] + [1] * (len(t) - 1), dtype=np.uint8),  # the first one before any fusion
        "stale": (t >= 62.0).astype(np.uint8),
        "lat_est": np.array([math.nan] + [g[0] for g in geo[1:]]),
        "lon_est": np.array([math.nan] + [g[1] for g in geo[1:]]),
    }
    m = olcum.follow_target_in_ulog(target, estimator, 60.0, 63.0, world, lambda s: (10.0 + (s - 60.0), 2.0))
    assert (m["follow_target_px4_sayisi"], m["follow_target_px4_hizi_hz"]) == (4, pytest.approx(4 / 3))
    assert m["px4_kestirim_hatasi_ort_m"] == pytest.approx(0.3, abs=1e-6)
    assert m["px4_kestirim_hatasi_maks_m"] == pytest.approx(0.3, abs=1e-6)
    assert m["px4_kestirim_gecerli_orani"] == pytest.approx(15 / 16)
    assert m["px4_kestirim_bayat_s"] == pytest.approx(1.0)  # 62.0 -> 63.0 s
    assert olcum.follow_target_in_ulog(None, None, 60.0, 63.0, world, None)["follow_target_px4_sayisi"] == 0


def test_ekf_yaw_error_and_the_measured_declination_from_the_ulog() -> None:
    """The EKF's yaw 2 deg ahead of the true one; the magnetometer measures a field of declination +3.41 deg
    (PX4's WMM at the world origin) in the body frame of the true attitude."""
    t = np.arange(55.0, 95.0, 0.01)
    true_yaw = np.radians(30.0 + 20.0 * np.sin(t / 5.0))

    def quats(yaw: np.ndarray) -> dict:
        return {f"q[{i}]": v for i, v in enumerate((np.cos(yaw / 2), 0 * yaw, 0 * yaw, np.sin(yaw / 2)))}

    att = {"timestamp": t * 1e6} | quats(true_yaw + math.radians(2.0))
    truth = {"timestamp": t * 1e6} | quats(true_yaw)
    decl, incl = math.radians(3.406), math.radians(63.16)
    ned = np.array([math.cos(incl) * math.cos(decl), math.cos(incl) * math.sin(decl), math.sin(incl)]) * 0.48
    body = np.array([kamera.rot_z(y).T @ ned for y in true_yaw]).T  # level flight: body = R_z(yaw)^T * NED
    mag = {"timestamp": t * 1e6, "x": body[0], "y": body[1], "z": body[2]}
    m = olcum.attitude_in_ulog(att, truth, mag, 60.0, 90.0)
    assert m["ekf_yaw_hatasi_ulog_ort_deg"] == pytest.approx(2.0, abs=1e-6)
    assert m["ekf_yaw_hatasi_ulog_maks_deg"] == pytest.approx(2.0, abs=1e-6)
    assert m["mag_sapma_olculen_deg"] == pytest.approx(3.406, abs=1e-6)


def test_measure_writes_every_key() -> None:
    """A run without a model, TEZ_LOS or ULog ("yok", --modelsiz) still gets every key of the spec table."""
    data = olcum.RunData(start=60.0, end=80.0, referee=walk(), source="yok", camera=CM3)
    m, sections = olcum.measure(data)
    assert set(olcum.KEYS) - {
        "yatay_mesafe_min_m",
        "yatay_mesafe_ort_m",
        "yatay_mesafe_max_m",
        "kadrajda_kalma",
        "gorunur_kalma",
        "en_uzun_kayip_s",
        "dron_yukseklik_ort_m",
        "rtf_ort",
    } <= set(m)
    assert m["en_az_yatay_mesafe_m"] == pytest.approx(2.0) and math.isnan(m["algilama_orani"])
    assert sections["yakin_mesafe"]["esik_m"] == olcum.NEAR_DISTANCE_M and len(sections["yakin_mesafe"]["olaylar"]) == 1


def test_run_log_lines_of_every_tracking_source(capsys: pytest.CaptureFixture[str]) -> None:
    """senaryo.py's summary lines take the measured keys of every tracking source: "yok" has no FLW_TGT_DST (a
    kalabalik_park run of task group 7 stopped there before writing its report), a run without values has NaN."""
    import senaryo

    m, _ = olcum.measure(olcum.RunData(start=60.0, end=80.0, referee=walk(), source="yok", camera=CM3))
    m |= {"yatay_mesafe_ort_m": 7.5, "yatay_mesafe_max_m": 8.0, "kadrajda_kalma": 0.9}
    senaryo._geometry_log_lines(m, "yok", None)
    senaryo._geometry_log_lines(m, "follow_me", 8.0)
    empty = dict.fromkeys(olcum.KEYS, math.nan) | {"en_az_yatay_mesafe_t_s": math.nan}
    senaryo._geometry_log_lines(empty, "tez_los", None)
    out = capsys.readouterr().out
    assert "Takip (yok)" in out and "FLW_TGT_DST 8" in out and "arkada kalma" in out


def test_jitter_of_the_standing_target_and_the_speed_px4_makes_of_it() -> None:
    """Follow start (mode switch -> the person starts walking): the person stands at (10, 0), the drone is west of it.
    The FOLLOW_TARGET positions sit 0.5 m towards the drone and jump +-0.1 m east-west: spread 0.1 m, frame to frame
    0.2 m, 0.5 m towards the drone, 5 per second. PX4's estimator turns that into speeds of 0.5 / 1.5 / 0.2 / 1.2 m/s
    (all of it made up: the person stands), half of them at or above the 1 m/s that updates its course, and its
    course changed twice. Samples outside the follow start do not count; without a mode switch everything is NaN."""
    sent = []
    for k in range(10):  # 30.0 .. 31.8 s, every 0.2 s
        t = 30.0 + 0.2 * k
        x = 9.5 + (0.1 if k % 2 == 0 else -0.1)
        sent.append({"t": t, "gonderim_sim": t + 0.1, "x": x, "y": 0.0, "gercek_x": 10.0, "gercek_y": 0.0})
        sent[-1]["sonuc"] = "gonderildi"
    sent.append({"t": 70.0, "gonderim_sim": 70.1, "x": 30.0, "y": 0.0, "gercek_x": 10.0, "gercek_y": 0.0})
    sent[-1]["sonuc"] = "gonderildi"  # walking: not the follow start
    sent.append(dict(sent[0], t=31.9, gonderim_sim=31.95, x=50.0, sonuc="hiz_siniri"))  # refused: never reached PX4
    referee = [{"t": t, "dron_x": 2.0, "dron_y": 0.0} for t in np.arange(25.0, 80.0, 0.5)]
    speeds = [(0.3, 0.4), (1.2, 0.9), (0.0, 0.2), (0.0, -1.2)]  # NE: 0.5, 1.5, 0.2, 1.2 m/s
    est = {
        "timestamp": np.array([26.0, 40.0, 41.0, 42.0, 43.0, 65.0]) * 1e6,
        "valid": np.array([1, 1, 1, 1, 1, 1]),
        "vel_est[0]": np.array([9.0] + [n for n, _ in speeds] + [9.0]),
        "vel_est[1]": np.array([9.0] + [e for _, e in speeds] + [9.0]),
    }
    status = {
        "timestamp": np.array([26.0, 30.0, 35.0, 40.0, 45.0, 66.0]) * 1e6,
        "tracked_target_course": np.array([2.0, 0.0, 1.0, 1.0, -2.0, 0.5]),
    }
    m = olcum.follow_start_metrics(sent, referee, 27.0, 60.0, est, status)
    assert m["follow_target_titresim_baslangic_m"] == pytest.approx(0.1)
    assert m["follow_target_ardisik_fark_baslangic_p50_m"] == pytest.approx(0.2)
    assert m["follow_target_drona_dogru_baslangic_m"] == pytest.approx(0.5)
    assert m["follow_target_hizi_baslangic_hz"] == pytest.approx(10 / 33.0)
    assert m["px4_kestirim_hizi_baslangic_ort_mps"] == pytest.approx(0.85)
    assert m["px4_kestirim_hizi_baslangic_maks_mps"] == pytest.approx(1.5)
    assert m["px4_kestirim_hizi_baslangic_p95_mps"] == pytest.approx(np.percentile([0.5, 1.5, 0.2, 1.2], 95))
    assert m["px4_kestirim_hizi_baslangic_1mps_orani"] == pytest.approx(0.5)
    assert m["px4_rota_degisimi_baslangic_sayisi"] == 2  # 26 s is before the mode switch, 66 s after the start
    none = olcum.follow_start_metrics(sent, referee, None, 60.0, est, status)
    assert set(none) == set(m) and all(math.isnan(v) for v in none.values())
    quiet = olcum.follow_start_metrics(sent, referee, 27.0, 60.0, None, None)  # no follow_target topics in the ULog
    assert math.isnan(quiet["px4_kestirim_hizi_baslangic_ort_mps"]) and quiet["follow_target_titresim_baslangic_m"] > 0
