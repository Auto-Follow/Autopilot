"""Corners of the person's path, how fast PX4 caught up with them, and the near passes (< 6 m) with their cause and
the decomposition of how much closer than FLW_TGT_DST the drone came (olcum.py; spec 2026-11-10-m06-sim-ortami
"Ölçüt Tanımları", task group 9). Hand-made tables only: no Gazebo, PX4 or model; each expected value is worked out
here."""

import math

import numpy as np
import pytest

import konumlama
import olcum

WORLD = konumlama.WorldGeo(47.397971057728974, 8.546163739800146, 0.0)  # tez/sim/worlds spherical_coordinates


def target(t: float) -> tuple[float, float, float, float]:
    """(x, y, speed, ENU yaw) of a person who stands at (10, 0) until 60 s, walks east at 1.4 m/s until 68 s, stands
    3 s, runs north at 3 m/s until 74 s, then walks west at 1.4 m/s until 80 s and stands (sharp corners: the course
    changes in one frame)."""
    if t < 60.0:
        return 10.0, 0.0, 0.0, 0.0
    if t < 68.0:
        return 10.0 + 1.4 * (t - 60.0), 0.0, 1.4, 0.0
    if t < 71.0:
        return 21.2, 0.0, 0.0, 0.0
    if t < 74.0:
        return 21.2, 3.0 * (t - 71.0), 3.0, math.pi / 2
    if t < 80.0:
        return 21.2 - 1.4 * (t - 74.0), 9.0, 1.4, math.pi
    return 12.8, 9.0, 0.0, math.pi


def times(t0: float = 25.0, t1: float = 90.0) -> np.ndarray:
    return np.round(t0 + np.arange(round((t1 - t0) * 30)) / 30.0, 6)


def rows(t0: float = 25.0, t1: float = 90.0, near: dict | None = None, behind: object = None) -> list[dict]:
    """Referee rows at 30 Hz. The drone is 8 m west of the person (south before 60 s), or `behind(t, x, y)` -> (dx, dy)
    from the person; near: {(start, end): distance} puts it that close (west of the person) in those spans."""
    out = []
    for t in times(t0, t1):
        x, y, speed, yaw = target(float(t))
        dx, dy = (0.0, -8.0) if t < 60.0 else (-8.0, 0.0)
        if behind is not None:
            dx, dy = behind(float(t), x, y)
        for (a, b), d in (near or {}).items():
            if a <= t < b:
                dx, dy = -d, 0.0
        out.append(
            {
                "t": float(t),
                "hedef_x": x,
                "hedef_y": y,
                "hedef_hiz": speed,
                "hedef_yaw": yaw,
                "dron_x": x + dx,
                "dron_y": y + dy,
                "yatay_mesafe": math.hypot(dx, dy),
            }
        )
    return out


def px4(**arrays: np.ndarray) -> olcum.Px4Follow:
    """A Px4Follow with only the given series (the others empty)."""
    empty = np.zeros(0)
    base = {
        "est_t": empty,
        "est_xy": np.zeros((0, 2)),
        "est_vel": np.zeros((0, 2)),
        "est_stale": np.zeros(0, dtype=bool),
        "st_t": empty,
        "course": empty,
        "orbit": empty,
        "follow_angle": empty,
        "filtered_xy": np.zeros((0, 2)),
        "aim_xy": np.zeros((0, 2)),
        "sp_t": empty,
        "setpoint_xy": np.zeros((0, 2)),
    }
    return olcum.Px4Follow(**(base | arrays))


def test_legs_of_the_path_and_their_corners() -> None:
    """Three legs: east from standing (60 s), north after a 3 s stop (71 s: 90 deg from east), west without stopping
    (74 s: another 90 deg). A leg starts where the person first moves within 20 deg of its direction."""
    legs = olcum.legs(rows())
    assert [round(g["yon_deg"]) for g in legs] == [90, 0, 270]
    assert [g["baslangic_s"] for g in legs] == pytest.approx([60.0, 71.0, 74.0])
    assert legs[0]["onceki_yon_deg"] is None and math.isnan(legs[0]["donus_deg"])
    assert [g["donus_deg"] for g in legs[1:]] == pytest.approx([90.0, 90.0])
    assert [g["durus_s"] for g in legs] == pytest.approx([35.0, 3.0, 0.0], abs=0.04)
    assert [g["tur"] for g in legs] == ["kalkis", "kalkis", "donus"]
    assert legs[2]["bitis_s"] == pytest.approx(80.0, abs=0.04)
    # a gentle bend (< 45 deg) is no corner: the leg goes on
    bend = rows(behind=None)
    for r in bend:
        if 64.0 <= r["t"] < 68.0:
            r["hedef_yaw"] = math.radians(20.0)
    assert [round(g["yon_deg"]) for g in olcum.legs(bend)][1:] == [0, 270] and len(olcum.legs(bend)) == 3
    # a referee row without the person's yaw (NaN) does not wipe out the course after it (np.unwrap carries NaN on)
    gap = rows()
    for r in gap:
        if 65.0 <= r["t"] < 65.1:
            r["hedef_yaw"] = math.nan
    assert [round(g["yon_deg"]) for g in olcum.legs(gap)] == [90, 0, 270]


def test_px4_catching_up_with_the_corners_and_the_overshoot() -> None:
    """PX4's course (follow_target_status, every 400 ms) turns east at 61.2 s, north at 72.4 s, west at 75.6 s: 1.2,
    1.4 and 1.6 s after the corners. At the west corner the drone stays south of the person for 1 s (90 deg off
    "behind" = east), then 0.5 s north-west of it (135 deg: ahead), then east (0 deg)."""

    def behind(t: float, x: float, y: float) -> tuple[float, float]:
        if t < 60.0:
            return 0.0, -8.0
        if t < 71.0:
            return -8.0, 0.0
        if t < 75.0:
            return 0.0, -8.0
        if t < 75.5:
            return 8.0 * math.cos(math.radians(135.0)), 8.0 * math.sin(math.radians(135.0))
        return 8.0, 0.0

    referee = rows(behind=behind)
    st_t = np.round(26.0 + 0.4 * np.arange(160), 6)
    course = np.radians(np.select([st_t >= 75.6, st_t >= 72.4, st_t >= 61.2], [270.0, 0.0, 90.0], 0.0))
    m, corners = olcum.corner_metrics(olcum.legs(referee), referee, px4(st_t=st_t, course=course), following=True)
    assert [c["px4_yetisme_s"] for c in corners] == pytest.approx([1.2, 1.4, 1.6], abs=1e-6)
    assert [c["arkada_kalma_maks_deg"] for c in corners] == pytest.approx([0.0, 0.0, 135.0], abs=0.5)
    assert corners[2]["arkada_kalma_90_ustu_s"] == pytest.approx(0.5, abs=0.04)
    assert m["kose_sayisi"] == 3 and m["kose_px4_yetisme_ort_s"] == pytest.approx(1.4)
    assert m["kose_px4_yetisme_maks_s"] == pytest.approx(1.6) and m["kose_px4_yetismedi_sayisi"] == 0
    assert m["kose_arkada_kalma_maks_deg"] == pytest.approx(135.0, abs=0.5)
    assert m["kose_arkada_kalma_90_ustu_s"] == pytest.approx(0.5, abs=0.04)
    assert m["kose_3_px4_yetisme_s"] == pytest.approx(1.6) and m["kose_1_yon_deg"] == pytest.approx(90.0)
    # PX4 never turns west before the end: not caught up (searched until the next corner or the end)
    late = np.radians(np.select([st_t >= 72.4, st_t >= 61.2], [0.0, 90.0], 0.0))
    m, corners = olcum.corner_metrics(olcum.legs(referee), referee, px4(st_t=st_t, course=late), following=True)
    assert math.isnan(corners[2]["px4_yetisme_s"]) and not corners[2]["px4_yetisti"]
    assert m["kose_px4_yetismedi_sayisi"] == 1 and m["kose_px4_yetisme_maks_s"] == pytest.approx(1.4)
    # without a follow mode or without PX4's status: the corners are there, the rest is NaN
    m, corners = olcum.corner_metrics(olcum.legs(referee), referee, None, following=False)
    assert m["kose_sayisi"] == 3 and math.isnan(m["kose_px4_yetisme_ort_s"])
    assert math.isnan(m["kose_arkada_kalma_maks_deg"]) and math.isnan(m["kose_px4_yetismedi_sayisi"])


NEAR = {(40.0, 41.0): 5.0, (66.5, 67.0): 5.5, (69.0, 69.5): 5.0, (75.0, 76.0): 2.0, (86.0, 87.0): 4.0}


def sent(t0: float = 26.0, t1: float = 84.0, step: float = 0.2, offset: tuple = (0.0, 0.0)) -> list[dict]:
    """FOLLOW_TARGET that went out: captured every `step` s from t0 to t1, sent 0.1 * step later, at the person's
    true position + offset."""
    out = []
    for tc in np.round(np.arange(t0, t1 + 1e-9, step), 6):
        x, y, _, _ = target(float(tc))
        out.append(
            {
                "t": float(tc),
                "gonderim_sim": round(float(tc) + step / 2, 6),
                "x": x + offset[0],
                "y": y + offset[1],
                "gercek_x": x,
                "gercek_y": y,
                "sonuc": "gonderildi",
            }
        )
    return out


def test_near_passes_their_cause_and_the_share_of_distances() -> None:
    """Five spans closer than 6 m in the recording (mode switch -> end): 40 s, the person still stands (follow
    start); 66.5 s on a straight walk with fresh positions and nothing else (other); 69 s right after the person
    stopped (stop / sudden start); 75 s, 1 s after the corner west (corner); 86 s, after 2 s without a FOLLOW_TARGET
    (lock loss / stale estimate). The distance shares are over the same recording."""
    referee = rows(near=NEAR)
    legs = olcum.legs(referee)
    locks = [{"t": 85.0, "olay": "kilit_kaybi"}]
    m, events = olcum.near_passes(referee, 60.0, legs, sent(), locks, None, 8.0, "follow_me")
    assert [e["baslangic_s"] for e in events] == pytest.approx([40.0, 66.5, 69.0, 75.0, 86.0])
    assert [e["sebep"] for e in events] == ["takip_basi", "diger", "durma_hizlanma", "kose", "kilit_kaybi"]
    assert [e["en_az_m"] for e in events] == pytest.approx([5.0, 5.5, 5.0, 2.0, 4.0])
    assert events[3]["kose_s"] == pytest.approx(74.0) and "durma_hizlanma" in events[3]["etkenler"]
    assert events[4]["olcum_yasi_baslangicta_s"] == pytest.approx(2.0, abs=1e-6)
    assert "olcum_boslugu" in events[4]["etkenler"] and events[1]["olcum_yasi_baslangicta_s"] <= 0.3
    assert events[2]["hiz_degisimi_mps"] == pytest.approx(1.4)
    assert all(math.isnan(e["ayristirma"]["toplam_m"]) for e in events)  # no PX4 internals given
    assert m["yakin_gecis_6m_olay_sayisi"] == 5 and m["yakin_gecis_6m_suresi_s"] == pytest.approx(4.0, abs=1e-6)
    assert m["yakin_gecis_en_az_m"] == pytest.approx(2.0)
    assert {k: m[f"yakin_gecis_{k}_sayisi"] for k in olcum.NEAR_PASS_CAUSES} == {
        "takip_basi": 1,
        "kilit_kaybi": 1,
        "kose": 1,
        "durma_hizlanma": 1,
        "konum_kaymasi": 0,
        "diger": 1,
        "takip_yok": 0,
    }
    total = 65.0
    assert m["mesafe_4m_alti_orani"] == pytest.approx(1.0 / total, abs=1e-6)
    assert m["mesafe_6m_alti_orani"] == pytest.approx(4.0 / total, abs=1e-6)
    assert m["mesafe_6_10m_orani"] == pytest.approx(61.0 / total, abs=1e-6) and m["mesafe_10m_ustu_orani"] == 0.0
    # the drone does not follow ("yok", Hold): the person walked to it
    _, hovering = olcum.near_passes(referee, 60.0, legs, (), (), None, None, "yok")
    assert {e["sebep"] for e in hovering} == {"takip_yok"}


def test_decomposition_of_a_near_pass_from_px4s_internals() -> None:
    """At 66.5 s the drone is 5.5 m behind (west of) the person walking east: 2.5 m closer than FLW_TGT_DST 8. Along
    the direction PX4 wants it from its target (orbit 270 deg NED: west), that is the sum of: the drone 0.5 m short of
    its setpoint P (towards the person), PX4's filtered target F 0.5 m ahead of its estimate E, E 0.3 m ahead of the
    last FOLLOW_TARGET S, S 1.34 m ahead of where the person was when its frame was captured (0.1 s earlier), and
    -0.14 m for the person having walked on since then. The position error is the largest: konum kayması."""
    referee = rows(60.0, 68.0, near={(66.5, 67.0): 5.5})
    t = np.round(np.arange(60.0, 68.0, 0.2), 6)
    walk = np.array([[target(float(s))[0], 0.0] for s in t])
    follow = px4(
        est_t=t,
        est_xy=walk + [1.5, 0.0],
        est_vel=np.tile([0.0, 1.4], (t.size, 1)),
        est_stale=np.zeros(t.size, dtype=bool),
        st_t=t,
        course=np.full(t.size, math.pi / 2),
        orbit=np.full(t.size, -math.pi / 2),
        follow_angle=np.full(t.size, math.pi),
        filtered_xy=walk + [2.0, 0.0],
        aim_xy=walk + [-6.0, 0.0],
        sp_t=t,
        setpoint_xy=walk + [-6.0, 0.0],
    )
    ft = sent(60.0, 68.0, step=0.1, offset=(1.34, 0.0))
    _, events = olcum.near_passes(referee, 60.0, olcum.legs(referee), ft, (), follow, 8.0, "follow_me")
    (e,) = events
    parts = e["ayristirma"]
    assert parts["toplam_m"] == pytest.approx(2.5, abs=1e-6)
    assert parts["dron_m"] == pytest.approx(0.5, abs=1e-6) and parts["px4_suzgec_m"] == pytest.approx(0.5, abs=1e-6)
    assert parts["px4_ongoru_m"] == pytest.approx(0.3, abs=1e-6)
    assert parts["konum_hatasi_m"] == pytest.approx(1.34, abs=1e-6)
    assert parts["olcum_yasi_m"] == pytest.approx(-0.14, abs=1e-6) and parts["kalan_m"] == pytest.approx(0.0, abs=1e-6)
    assert e["baskin_etken"] == "konum_hatasi_m" and e["sebep"] == "konum_kaymasi" and "konum_kaymasi" in e["etkenler"]
    assert e["px4_hiz_kestirimi_mps"] == pytest.approx(1.4) and e["px4_rota_deg"] == pytest.approx(90.0)
    # the same event with the position error pushing the drone away (towards it): no konum kayması
    away = sent(60.0, 68.0, step=0.1, offset=(-0.5, 0.0))
    _, (e,) = olcum.near_passes(referee, 60.0, olcum.legs(referee), away, (), follow, 8.0, "follow_me")
    assert e["ayristirma"]["konum_hatasi_m"] == pytest.approx(-0.5, abs=1e-6) and e["sebep"] == "diger"


def test_px4_follow_internals_from_the_ulog_into_the_world() -> None:
    """follow_target_estimator lat/lon (absolute), follow_target_status desired_position_raw and trajectory_setpoint
    (NED from the EKF origin of vehicle_local_position) land on the world points they were made from (< 1 cm); F is
    desired_position_raw - FLW_TGT_DST (cos, sin)(course + follow angle); stale comes along."""
    ref = (47.3979, 8.5462)
    proj = konumlama.MapProjection(*ref)

    def ned(x: float, y: float) -> tuple[float, float]:
        lat, lon, _ = WORLD.to_geodetic(x, y)
        return proj.project(lat, lon)

    e_lat, e_lon, _ = WORLD.to_geodetic(12.0, 3.0)
    f_n, f_e = ned(13.0, 3.5)  # F
    course, fa = 0.0, math.pi  # north, follow from behind: desired raw = F - 8 m north
    s_n, s_e = ned(6.0, 3.0)  # setpoint
    topics = olcum.Topics(
        {
            "follow_target_estimator": {
                "timestamp": np.array([70e6, 70.2e6]),
                "lat_est": np.array([e_lat, e_lat]),
                "lon_est": np.array([e_lon, e_lon]),
                "vel_est[0]": np.array([1.0, 1.0]),
                "vel_est[1]": np.array([0.0, 0.0]),
                "valid": np.array([1, 1]),
                "stale": np.array([0, 1]),
            },
            "follow_target_status": {
                "timestamp": np.array([70e6]),
                "tracked_target_course": np.array([course]),
                "follow_angle": np.array([fa]),
                "orbit_angle_setpoint": np.array([math.pi]),
                "desired_position_raw[0]": np.array([f_n - 8.0]),
                "desired_position_raw[1]": np.array([f_e]),
            },
            "trajectory_setpoint": {
                "timestamp": np.array([70e6]),
                "position[0]": np.array([s_n]),
                "position[1]": np.array([s_e]),
            },
            "vehicle_local_position": {
                "timestamp": np.array([1e6]),
                "ref_lat": np.array([ref[0]]),
                "ref_lon": np.array([ref[1]]),
            },
        }
    )
    f = olcum.Px4Follow.from_topics(topics, WORLD, 8.0)
    assert f.est_xy[0] == pytest.approx([12.0, 3.0], abs=0.01) and list(f.est_stale) == [False, True]
    assert f.filtered_xy[0] == pytest.approx([13.0, 3.5], abs=0.01)
    assert f.aim_xy[0] == pytest.approx([13.0, -4.5], abs=0.01)
    assert f.setpoint_xy[0] == pytest.approx([6.0, 3.0], abs=0.01)
    now = f.at(70.1)
    assert now["E"] == pytest.approx([12.0, 3.0], abs=0.01) and now["stale"] is False and now["speed"] == 1.0
    assert olcum.Px4Follow.from_topics(olcum.Topics({}), WORLD, 8.0) is None
    no_ref = olcum.Topics({k: v for k, v in topics.data.items() if k != "vehicle_local_position"})
    partial = olcum.Px4Follow.from_topics(no_ref, WORLD, 8.0)
    assert np.isnan(partial.filtered_xy).all() and partial.est_xy[0] == pytest.approx([12.0, 3.0], abs=0.01)
