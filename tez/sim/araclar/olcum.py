"""Metrics of one scenario run: every key of spec 2026-11-10-m06-sim-ortami "Ölçüt Tanımları" (KEYS), for ozet.json
"olcutler". No thresholds: the numbers are measured only (m01 sets the success criteria).

Only the recording window counts (zamanlama.baslama_s -> scenario end), with two documented exceptions: the orbit turn
"at the start of tracking" (from the mode switch until the target starts walking, and its first YURUYUS_BASI_S) and the
PX4 course assumption, which both describe what happens before and right at the start of the window, and the near
passes (< CLOSE_PASS_M) with the shares of the distance and the corners of the person's path, which cover the whole
recording (mode switch -> end, what kosu.mp4 shows). A metric that does not apply to a run is NaN (e.g.
geolocation_hatasi without FOLLOW_TARGET, arkada_kalma without a follow mode).

Inputs (RunData): the referee's rows (kayit.Recorder.snapshot(): one per camera frame, Gazebo truth), the model's
processed frames (algilama.DetectionLog: algilama.csv rows, kutular, skipped frames), the tracking side's TEZ_LOS /
FOLLOW_TARGET attempts and lock events (takip.Tracker), the camera (camera_info), PX4's ULog files of the run
(ucus_once.ulg + ucus.ulg) and the mode the run asked for. Frames join on round(t * 1e6) (algilama.time_key).

Groups: (a) model: does a box find the target, which box was chosen, wrong person, false positives; (b) LOS: the
chosen box's line of sight against the referee's; (c) time: frames, latency, the TEZ_LOS stream and what PX4 logged;
(d) tracking: distance, frame, behind angle, orbit turns, mode, positions, FOLLOW_TARGET and PX4's estimate of it,
the corners and the near passes, each split into what brought the drone closer (Px4Follow, decompose()).
"""

import math
import statistics
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

import algilama
import kamera
import konumlama
from algilama import Kutu

IOU_MATCH = algilama.IOU_MATCH  # a box with this IoU to the target's referee box found the target (0.5)
PERSON_IOU = 0.3  # a box with this IoU to some person's referee box belongs to that person (wrong person, FP)
NEAR_DISTANCE_M = 3.0  # [m] decision 3 (12.11): warn when the drone comes closer; a proposal for m01, not a threshold
MOVING_SPEED = 0.5  # [m/s] the target walks: the behind angle is defined (its direction of motion is known)
OVERSHOOT_DEG = 90.0  # [deg] behind-angle error above this: the drone is beside or ahead of the target
ORBIT_STEP_S = 0.5  # [s] orbit angle sampled this often for the turn sums (hover jitter does not add up)
ORBIT_MIN_DISTANCE_M = 1.0  # [m] closer than this the angle around the target is not defined
YURUYUS_BASI_S = 10.0  # [s] "start of the walk": the second turn of the stock mode happens here
PX4_COURSE_SPEED = 1.0  # [m/s] PX4 updates the target course only above this (TARGET_SPEED_DEADZONE_...)
CAMERA_AHEAD_M = float(konumlama.NOMINAL_OFFSET_FRD[0])  # [m] camera ahead of base_link
PX4_MATCH_S = 0.06  # [s] a logged TEZ_LOS belongs to a sent one with the same values at most this far in time
PX4_MATCH_VALUE = 2e-6  # tez_los.csv keeps 6 decimals, PX4 float32
TEZ_LOS_NAME = "TEZ_LOS"  # px4_baglanti.TEZ_LOS_NAME (not imported: the metrics do not need pymavlink)
DEBUG_NAME_CHARS = 10  # debug_vect.name is char[10]
# PX4 v1.17.0 nav_state -> the name PX4 shows (src/lib/modes/ui.hpp nav_state_names; test_olcum checks it)
NAV_STATE_NAMES = (
    "Manual",
    "Altitude",
    "Position",
    "Mission",
    "Hold",
    "Return",
    "Position Slow",
    "7: unallocated",
    "Altitude Cruise",
    "9: unallocated",
    "Acro",
    "11: UNUSED",
    "Descend",
    "Termination",
    "Offboard",
    "Stabilized",
    "16: UNUSED2",
    "Takeoff",
    "Land",
    "Follow Target",
    "Precision Landing",
    "Orbit",
    "VTOL Takeoff",
    *(f"External {i}" for i in range(1, 9)),
)
STATS = ("ort", "p50", "p95", "maks")


def _expand(pattern: str) -> list[str]:
    """'a_{x,y}_b' -> ['a_x_b', 'a_y_b'] (the notation of the spec's table)."""
    if "{" not in pattern:
        return [pattern]
    head, rest = pattern.split("{", 1)
    options, tail = rest.split("}", 1)
    return [k for option in options.split(",") for k in _expand(head + option + tail)]


# Every key of spec "Ölçüt Tanımları", in the table's order; measure() writes each of them (NaN where it does not
# apply). test_olcum checks this list against the spec's table.
KEY_PATTERNS = (
    # (a) model
    "algilama_orani",
    "kacirma_orani",
    "iou_ort",
    "iou_p50",
    "secim_dogru_orani",
    "yanlis_kisi_orani",
    "yanlis_kisi_ayni_kiyafet_orani",
    "yanlis_pozitif_kare_basi",
    "yeniden_kilit_sayisi",
    "kilit_kaybi_sayisi",
    "secili_kare_orani",
    # (b) LOS
    "los_aci_hatasi_{ort,p50,p95,maks}_deg",
    "los_aci_kare",
    "los_sapma_farki_{yatay,dikey}_ort_deg",
    # (c) time
    "model_ms_{ort,p95}",
    "ulasma_ms_ort",
    "bekleme_ms_ort",
    "uctan_uca_ms_{ort,p50,p95,maks}",
    "uctan_uca_px4_ms_{ort,p95}",
    "px4_varis_eksi_gonderim_ms_{ort,p95,min}",
    "tez_los_px4_eslesen",
    "islenen_kare_hizi_hz",
    "atlanan_kare_orani",
    "rtf_ort",
    "tez_los_px4_sayisi",
    "tez_los_px4_hizi_hz",
    "tez_los_px4_orani",
    "tez_los_gonderilen",
    "tez_los_hedef_yok",
    "tez_los_gecersiz",
    "tez_los_reddedilen",
    "tez_los_hizi_hz",
    # (d) tracking
    "yatay_mesafe_{min,ort,max}_m",
    "kadrajda_kalma",
    "gorunur_kalma",
    "en_uzun_kayip_s",
    "dron_yukseklik_ort_m",
    "en_az_yatay_mesafe_m",
    "yakin_mesafe_3m_suresi_s",
    "yakin_mesafe_3m_olay_sayisi",
    "kadraj_yakin_sinir_m",
    "kadraj_yakin_sinir_alti_s",
    "kadraj_uzak_sinir_m",
    "kadraj_uzak_sinir_ustu_s",
    "hedef_kadrajda_orani",
    "ayak_kadrajda_orani",
    "arkada_kalma_hatasi_{ort,p95,maks}_deg",
    "arkada_kalma_hatasi_90_ustu_s",
    "baslangic_yorunge_donusu_deg",
    "yuruyus_basi_yorunge_donusu_deg",
    "mod_korunma_orani",
    "geolocation_hatasi_{ort,p95}_m",
    "yatay_mesafe_hatasi_ort_m",
    "geolocation_hatasi_{p50,maks}_m",
    "geolocation_hatasi_gonderimde_{ort,p95}_m",
    "follow_target_gonderilen",
    "follow_target_hizi_hz",
    "follow_target_konumsuz_kare",
    "follow_target_uctan_uca_ms_{ort,p95,maks}",
    "konum_hatasi_{ort,p50,p95,maks}_m",
    "konum_kare",
    "konum_hatasi_gercek_pozla_{ort,p95}_m",
    "konum_durumlari",
    "ekf_yaw_hatasi_{ort,maks}_deg",
    "ekf_yatay_konum_hatasi_{ort,maks}_m",
    "ekf_yaw_hatasi_ulog_{ort,maks}_deg",
    "mag_sapma_olculen_deg",
    "follow_target_px4_sayisi",
    "px4_kestirim_hatasi_{ort,p50,p95,maks}_m",
    "px4_kestirim_gecerli_orani",
    "px4_kestirim_bayat_s",
    "px4_rota_kuzey_varsayimi_s",
    "px4_rota_hatasi_{ort,p95}_deg",
    "px4_yorunge_donusu_baslangic_deg",
    "px4_yorunge_donusu_yuruyus_basi_deg",
    "follow_target_titresim_baslangic_m",
    "follow_target_ardisik_fark_baslangic_p50_m",
    "follow_target_drona_dogru_baslangic_m",
    "follow_target_hizi_baslangic_hz",
    "px4_kestirim_hizi_baslangic_{ort,p95,maks}_mps",
    "px4_kestirim_hizi_baslangic_1mps_orani",
    "px4_rota_degisimi_baslangic_sayisi",
    "mesafe_4m_alti_orani",
    "mesafe_6m_alti_orani",
    "mesafe_6_10m_orani",
    "mesafe_10m_ustu_orani",
    "yakin_gecis_6m_olay_sayisi",
    "yakin_gecis_6m_suresi_s",
    "yakin_gecis_en_az_m",
    "yakin_gecis_{takip_basi,kilit_kaybi,kose,durma_hizlanma,konum_kaymasi,diger,takip_yok}_sayisi",
    "kose_sayisi",
    "kose_px4_yetisme_{ort,maks}_s",
    "kose_px4_yetismedi_sayisi",
    "kose_arkada_kalma_maks_deg",
    "kose_arkada_kalma_90_ustu_s",
)
KEYS = tuple(k for p in KEY_PATTERNS for k in _expand(p))


# --- small helpers ------------------------------------------------------------------------------------------------


def stats(name: str, values: Iterable[float], kinds: Sequence[str] = STATS, unit: str = "") -> dict:
    """{name_kind_unit: value} for kinds ort (mean), pNN (percentile), maks, min; NaN values are left out, an empty
    list gives NaN."""
    values = [float(v) for v in values if v is not None and not math.isnan(v)]
    out = {}
    for kind in kinds:
        key = f"{name}_{kind}{unit}"
        if not values:
            out[key] = math.nan
        elif kind == "ort":
            out[key] = statistics.fmean(values)
        elif kind == "maks":
            out[key] = max(values)
        elif kind == "min":
            out[key] = min(values)
        else:
            out[key] = float(np.percentile(values, float(kind[1:])))
    return out


def wrap_deg(a: float | np.ndarray) -> float | np.ndarray:
    """Angle [deg] into -180..180."""
    return (np.asarray(a) + 180.0) % 360.0 - 180.0 if isinstance(a, np.ndarray) else (a + 180.0) % 360.0 - 180.0


def durations(t: np.ndarray) -> np.ndarray:
    """[s] how long each sample stands for: until the next one; the last one as long as the one before it."""
    if t.size < 2:
        return np.zeros(t.size)
    d = np.diff(t)
    return np.append(d, d[-1])


def intervals(t: np.ndarray, mask: np.ndarray) -> list[tuple[float, float]]:
    """[(start, end)] [s] of the runs where mask holds; a run ends at the first sample where it does not."""
    spans, start = [], None
    for i, (ti, m) in enumerate(zip(t, mask, strict=True)):
        if m and start is None:
            start = ti
        elif not m and start is not None:
            spans.append((float(start), float(ti)))
            start = None
        if i == len(t) - 1 and start is not None:
            spans.append((float(start), float(ti)))
    return spans


def target_box(ref: Mapping) -> tuple[float, float, float, float]:
    return tuple(float(ref.get(f"hedef_kutu_{k}", math.nan)) for k in ("u0", "v0", "u1", "v1"))


def person_box(ref: Mapping, i: int) -> tuple[float, float, float, float]:
    return tuple(float(ref.get(f"insan{i}_kutu_{k}", math.nan)) for k in ("u0", "v0", "u1", "v1"))


def chosen_box(row: Mapping) -> tuple[float, float, float, float] | None:
    if row.get("secilen_kutu") is None:
        return None
    return tuple(float(row[f"secilen_{k}"]) for k in ("u0", "v0", "u1", "v1"))


def wrong_person(box: Sequence[float] | Kutu, ref: Mapping, others: int) -> int | None:
    """The other person (insan<i>, 1-based) a chosen box is on by the referee of its frame: IoU with that person's
    box at least PERSON_IOU and bigger than with the target's (yanlis_kisi_orani); None if the box is on the target or
    on nobody. The video's "YANLIŞ KİŞİ" uses this too, so its moments are the metric's frames."""
    on_target = algilama.iou(box, target_box(ref))
    scores = {i: algilama.iou(box, person_box(ref, i)) for i in range(1, others + 1)}
    other = max(scores, key=scores.get, default=None)
    if other is not None and scores[other] >= PERSON_IOU and scores[other] > on_target:
        return other
    return None


def _inside(t: float, start: float, end: float) -> bool:
    return start <= t <= end


def _by_key(rows: Iterable[Mapping]) -> dict[int, Mapping]:
    return {algilama.time_key(r["t"]): r for r in rows}


# --- (a) model --------------------------------------------------------------------------------------------------


def model_metrics(
    rows: Sequence[Mapping],
    boxes: Mapping[int, Sequence[Kutu]],
    referee: Sequence[Mapping],
    start: float,
    end: float,
    others: int = 0,
    same_clothes: frozenset[int] = frozenset(),
) -> dict:
    """The model's processed frames of the window against the referee of the same frame.

    others: number of other people in the scenario (insan1..insanN); same_clothes: those dressed like the target."""
    refs = _by_key(r for r in referee if _inside(r["t"], start, end))
    frames = [(r, refs[r["t_us"]]) for r in rows if _inside(r["t"], start, end) and r["t_us"] in refs]
    visible = [(r, ref) for r, ref in frames if ref.get("gorunur")]
    ious, found = [], 0
    best_any = math.nan
    for r, ref in frames:
        score = max((algilama.iou(b, target_box(ref)) for b in boxes.get(r["t_us"], ())), default=0.0)
        best_any = score if math.isnan(best_any) else max(best_any, score)
        if ref.get("gorunur") and score >= IOU_MATCH:
            found += 1
            ious.append(score)
    right = sum(
        1 for r, ref in visible if (b := chosen_box(r)) is not None and algilama.iou(b, target_box(ref)) >= IOU_MATCH
    )
    wrong = wrong_same = false_pos = chosen = 0
    for r, ref in frames:
        people = [target_box(ref)] + [person_box(ref, i) for i in range(1, others + 1)]
        false_pos += sum(
            1 for b in boxes.get(r["t_us"], ()) if max((algilama.iou(b, p) for p in people), default=0.0) < PERSON_IOU
        )
        b = chosen_box(r)
        if b is None:
            continue
        chosen += 1
        other = wrong_person(b, ref, others)
        if other is not None:
            wrong += 1
            wrong_same += other in same_clothes
    n, nv = len(frames), len(visible)
    m = {
        "model_kare": n,
        "hedef_gorunur_islenen": nv,
        "iou05_kare_sayisi": found,
        "iou_max": best_any,
        "algilama_orani": found / nv if nv else math.nan,
        "kacirma_orani": 1.0 - found / nv if nv else math.nan,
        "secim_dogru_orani": right / nv if nv else math.nan,
        "secili_kare_orani": chosen / n if n else math.nan,
        "yanlis_kisi_orani": wrong / n if n else math.nan,
        "yanlis_kisi_ayni_kiyafet_orani": wrong_same / n if n else math.nan,
        "yanlis_pozitif_kare_basi": false_pos / n if n else math.nan,
    }
    return m | stats("iou", ious, ("ort", "p50"))


def frame_metrics(
    rows: Sequence[Mapping], skipped: Sequence, referee: Sequence[Mapping], start: float, end: float
) -> dict:
    """Frames and times of the window: uretilen = frames that reached the model process (processed + replaced),
    kamera_karesi = the referee's camera frames, okuyucuya_ulasmayan = those the reader never got; model_ms, the time
    to reach the model process (ulasma, sim ms) and the wait for the model (bekleme)."""
    inside = [r for r in rows if _inside(r["t"], start, end)]
    gone = [s for s in skipped if _inside(s.t, start, end)]  # NaN (header not read) is never inside
    received = {r["t_us"] for r in inside} | {algilama.time_key(s.t) for s in gone}
    frames = {algilama.time_key(x["t"]) for x in referee if _inside(x["t"], start, end)}
    produced = len(inside) + len(gone)
    m = {
        "uretilen": produced,
        "islenen": len(inside),
        "atlanan": len(gone),
        "atlanan_kare_orani": 1.0 - len(inside) / produced if produced else math.nan,
        "islenen_kare_hizi_hz": len(inside) / (end - start) if end > start else math.nan,
        "kamera_karesi": len(frames),
        "okuyucuya_ulasmayan": len(frames - received),
        "zamani_okunamayan_atlanan": sum(math.isnan(s.t) for s in skipped),
    }
    for name, kinds in (
        ("model_ms", ("ort", "p95", "maks")),
        ("cozme_ms", ("ort",)),
        ("kusur_ms", ("ort",)),
        ("ulasma_ms", ("ort", "p95")),
        ("bekleme_ms", ("ort",)),
        ("islem_ms", ("ort", "p95")),
        ("teslim_ms", ("ort", "maks")),
    ):
        m |= stats(name, (r[name] for r in inside), kinds)
    return m


# --- (b) LOS -----------------------------------------------------------------------------------------------------


def los_metrics(rows: Sequence[Mapping], referee: Sequence[Mapping], start: float, end: float) -> dict:
    """LOS (i) of the chosen box against the referee's LOS (ii) (los_govde) of the same frame, where the chosen box is
    the target (IoU >= 0.5) and the target is visible; in the model source this is the sent TEZ_LOS. The deviation
    difference (kamera.deviation, right and down positive) shows a systematic offset."""
    refs = _by_key(r for r in referee if _inside(r["t"], start, end))
    angles, horizontal, vertical = [], [], []
    for r in rows:
        ref = refs.get(r.get("t_us"))
        b = chosen_box(r)
        if ref is None or b is None or not ref.get("gorunur") or algilama.iou(b, target_box(ref)) < IOU_MATCH:
            continue
        los = [float(r[f"los_i_{k}"]) for k in "xyz"]
        truth = [float(ref[f"los_govde_{k}"]) for k in "xyz"]
        if not all(math.isfinite(v) for v in los + truth):
            continue
        angles.append(kamera.angle_deg(los, truth))
        h, v, _ = kamera.deviation(np.array(los), "body")
        th, tv, _ = kamera.deviation(np.array(truth), "body")
        horizontal.append(h - th)
        vertical.append(v - tv)
    m = stats("los_aci_hatasi", angles, STATS, "_deg") | {"los_aci_kare": len(angles)}
    m["los_sapma_farki_yatay_ort_deg"] = statistics.fmean(horizontal) if horizontal else math.nan
    m["los_sapma_farki_dikey_ort_deg"] = statistics.fmean(vertical) if vertical else math.nan
    return m


# --- (c) the TEZ_LOS stream and the lock --------------------------------------------------------------------------


def stream_metrics(attempts: Sequence[Mapping], events: Sequence[Mapping], start: float, end: float) -> dict:
    """TEZ_LOS of the window: sent ones by send time (what PX4 can log in the window), invalid and refused ones by
    the capture time of their frame; the lock events by their frame time."""
    sent = [a for a in attempts if a["sonuc"] == "gonderildi" and _inside(a["gonderim_sim"], start, end)]
    tried = [a for a in attempts if _inside(a["t"], start, end)]
    span = end - start
    m = {
        "tez_los_gonderilen": len(sent),
        "tez_los_hedef_yok": sum(1 for a in sent if not a["hedef"]),
        "tez_los_gecersiz": sum(1 for a in tried if a["sonuc"] == "gecersiz"),
        "tez_los_reddedilen": sum(1 for a in tried if a["sonuc"] in ("ayni_kare", "eski_kare", "hiz_siniri")),
        "tez_los_hizi_hz": len(sent) / span if span > 0 else math.nan,
    }
    m |= stats("uctan_uca_ms", (a["uctan_uca_ms"] for a in sent))
    m |= stats("ek_gecikme_ms", (a["ek_gecikme_ms"] for a in sent), ("ort", "maks"))
    m |= stats("hazir_ms", (a["hazir_ms"] for a in sent), ("ort", "p95"))
    inside = [e for e in events if _inside(e["t"], start, end)]
    m["kilit_kaybi_sayisi"] = sum(1 for e in inside if e["olay"] == "kilit_kaybi")
    m["yeniden_kilit_sayisi"] = sum(1 for e in inside if e["olay"] == "yeniden_kilit")
    return m


# --- (d) tracking: positions and FOLLOW_TARGET ------------------------------------------------------------------


def follow_metrics(attempts: Sequence[Mapping], rows: Sequence[Mapping], start: float, end: float) -> dict:
    """FOLLOW_TARGET of the window: sent by send time (what PX4 can have fused), refused by capture time; how far the
    sent position was from the target at the capture time (geolocation_hatasi) and at the send time (the target
    walked on meanwhile). NaN without FOLLOW_TARGET."""
    span = end - start
    sent = [a for a in attempts if a["sonuc"] == "gonderildi" and _inside(a["gonderim_sim"], start, end)]
    tried = [a for a in attempts if _inside(a["t"], start, end)]
    m = {
        "follow_target_gonderilen": len(sent),
        "follow_target_hizi_hz": len(sent) / span if span > 0 else math.nan,
        "follow_target_reddedilen": sum(1 for a in tried if a["sonuc"] in ("ayni_kare", "eski_kare", "hiz_siniri")),
        "follow_target_gecersiz": sum(1 for a in tried if a["sonuc"] == "gecersiz"),
        "follow_target_konumsuz_kare": sum(
            1 for r in rows if _inside(r["t"], start, end) and r.get("ft_sonuc") == "konum_yok"
        ),
    }
    m |= stats("follow_target_uctan_uca_ms", (a["uctan_uca_ms"] for a in sent), ("ort", "p95", "maks"))
    m |= stats("geolocation_hatasi", (a["hata_m"] for a in sent), STATS, "_m")
    return m | stats("geolocation_hatasi_gonderimde", (a["hata_gonderimde_m"] for a in sent), ("ort", "p95"), "_m")


def position_metrics(
    rows: Sequence[Mapping],
    referee: Sequence[Mapping],
    start: float,
    end: float,
    camera: kamera.Camera | None = None,
    mount: tuple | None = None,
    world: konumlama.WorldGeo | None = None,
    origin: konumlama.GeoPoint | None = None,
) -> dict:
    """The box positions of the window (every tracking source): how often there was one and why not, and where the
    chosen box was the target (IoU >= 0.5) how far it was from the target, with the EKF pose (what goes to PX4) and
    with the true pose and mount (the box's own part; mount = (offset FLU, C_cb) from Gazebo). The EKF's yaw and
    position against Gazebo's at the frames' capture times (origin: the EKF origin, GPS_GLOBAL_ORIGIN)."""
    frames = [r for r in rows if _inside(r["t"], start, end) and "konum" in r]
    refs = _by_key(referee)
    px4 = konumlama.MapProjection(origin.lat, origin.lon) if origin is not None else None
    errors, true_errors, yaw_errors, ekf_errors = [], [], [], []
    for r in frames:
        ref = refs.get(r["t_us"])
        if ref is None:
            continue
        if math.isfinite(r.get("ekf_yaw_deg", math.nan)):
            yaw_errors.append(wrap_deg(r["ekf_yaw_deg"] - ref["dron_yaw_deg"]))
            if px4 is not None and world is not None:
                x, y, _ = world.to_local(*px4.reproject(r["ekf_n"], r["ekf_e"]))
                ekf_errors.append(math.hypot(x - ref["dron_x"], y - ref["dron_y"]))
        b = chosen_box(r)
        if r["konum"] != "hesaplandi" or not ref.get("gorunur") or b is None:
            continue
        if algilama.iou(b, target_box(ref)) < IOU_MATCH:
            continue
        errors.append(r["konum_hatasi_m"])
        if camera is not None and mount is not None and mount[0] is not None:
            x, y = konumlama.true_pose_hit(camera, (r["ayak_u"], r["ayak_v"]), ref, mount[0], mount[1])
            true_errors.append(math.hypot(x - ref["hedef_x"], y - ref["hedef_y"]))
    statuses = Counter(r["konum"] for r in frames)
    m = {"konum_hesaplanan": statuses["hesaplandi"], "konum_durumlari": dict(statuses), "konum_kare": len(errors)}
    m |= stats("konum_hatasi", errors, STATS, "_m")
    m |= stats("konum_hatasi_gercek_pozla", true_errors, ("ort", "p95"), "_m")
    m |= stats("ekf_yaw_hatasi", yaw_errors, ("ort",), "_deg")
    m["ekf_yaw_hatasi_maks_deg"] = max((abs(v) for v in yaw_errors), default=math.nan)
    return m | stats("ekf_yatay_konum_hatasi", ekf_errors, ("ort", "maks"), "_m")


# --- (d) tracking: geometry from the referee ----------------------------------------------------------------------


def _columns(rows: Sequence[Mapping], names: Sequence[str]) -> dict[str, np.ndarray]:
    return {n: np.array([float(r.get(n, math.nan)) for r in rows], dtype=float) for n in names}


def frame_limits(
    camera: kamera.Camera | None, camera_height: np.ndarray, tilt_deg: float = kamera.NOMINAL_TILT_DEG
) -> tuple[np.ndarray, np.ndarray]:
    """[m] horizontal distance from base_link to the nearest and farthest ground point the camera sees straight ahead
    (bottom and top edge of the image), level flight, the camera `tilt_deg` below the nose (the scenario's
    kamera.egim_deg; nominal 45 deg): h / tan(tilt +- vfov / 2) + the camera's 0.151 m ahead of base_link. A person's
    feet nearer than the first one are below the image."""
    if camera is None:
        nan = np.full(camera_height.shape, math.nan)
        return nan, nan
    half = math.atan2(camera.height / 2.0, camera.fy)
    tilt = math.radians(tilt_deg)
    near = camera_height / math.tan(tilt + half) + CAMERA_AHEAD_M
    if tilt <= half:  # the top edge looks at or above the horizon: no far limit on the ground
        return near, np.full(camera_height.shape, math.inf)
    return near, camera_height / math.tan(tilt - half) + CAMERA_AHEAD_M


def orbit_turn(t: np.ndarray, angle_deg_: np.ndarray, start: float, end: float, step: float = ORBIT_STEP_S) -> float:
    """[deg] total angle turned (absolute, both directions added up) by a direction sampled at t, from start to end,
    taken every `step` seconds; NaN samples are skipped; NaN if fewer than two samples."""
    grid = np.append(np.arange(start, end, step), end)  # the end itself too, whatever the step
    ok = np.isfinite(angle_deg_)
    if ok.sum() < 2 or grid.size < 2:
        return math.nan
    tt, aa = t[ok], np.unwrap(np.radians(angle_deg_[ok]))
    inside = (grid >= tt[0]) & (grid <= tt[-1])
    if inside.sum() < 2:
        return math.nan
    sampled = np.interp(grid[inside], tt, aa)
    return float(np.degrees(np.abs(np.diff(sampled)).sum()))


def tracking_metrics(
    referee: Sequence[Mapping],
    start: float,
    end: float,
    camera: kamera.Camera | None = None,
    following: bool = True,
    follow_distance: float | None = None,
    near_m: float = NEAR_DISTANCE_M,
    tilt_deg: float = kamera.NOMINAL_TILT_DEG,
) -> tuple[dict, list[dict]]:
    """Distance, frame and behind angle of the window from the referee (Gazebo truth, every camera frame), and the
    orbit turns from the first referee row (the mode was just chosen) on. following: the tracking source follows the
    target (follow_me, tez_los); "yok" hovers, so its behind angle and orbit turns are NaN. follow_distance:
    FLW_TGT_DST [m] in follow_me (yatay_mesafe_hatasi_ort_m), None otherwise. tilt_deg: the camera's tilt below the
    nose (the scenario's kamera.egim_deg) for its near and far ground limit.

    -> (metrics, the near-distance events: [{baslangic_s, bitis_s, en_az_m, en_az_t_s}])."""
    names = ("t", "dron_x", "dron_y", "kamera_z", "hedef_x", "hedef_y", "hedef_yaw", "hedef_hiz", "yatay_mesafe")
    c = _columns(referee, names)
    nan_keys = (
        "en_az_yatay_mesafe_m",
        "en_az_yatay_mesafe_t_s",
        "yakin_mesafe_3m_suresi_s",
        "yakin_mesafe_3m_olay_sayisi",
        "kadraj_yakin_sinir_m",
        "kadraj_yakin_sinir_alti_s",
        "kadraj_uzak_sinir_m",
        "kadraj_uzak_sinir_ustu_s",
        "hedef_kadrajda_orani",
        "ayak_kadrajda_orani",
        "arkada_kalma_hatasi_ort_deg",
        "arkada_kalma_hatasi_p95_deg",
        "arkada_kalma_hatasi_maks_deg",
        "arkada_kalma_kare",
        "arkada_kalma_suresi_s",
        "arkada_kalma_hatasi_90_ustu_s",
        "baslangic_yorunge_donusu_deg",
        "yuruyus_basi_yorunge_donusu_deg",
        "yatay_mesafe_hatasi_ort_m",
    )
    m: dict = dict.fromkeys(nan_keys, math.nan)
    events: list[dict] = []
    if c["t"].size == 0:
        return m, events
    t = c["t"]
    orbit = np.degrees(np.arctan2(c["dron_y"] - c["hedef_y"], c["dron_x"] - c["hedef_x"]))
    orbit[c["yatay_mesafe"] < ORBIT_MIN_DISTANCE_M] = math.nan
    if following:
        m["baslangic_yorunge_donusu_deg"] = orbit_turn(t, orbit, float(t[0]), start) if t[0] < start else math.nan
        m["yuruyus_basi_yorunge_donusu_deg"] = orbit_turn(t, orbit, start, start + YURUYUS_BASI_S)
    win = (t >= start) & (t <= end)
    if not win.any():
        return m, events
    w = {k: v[win] for k, v in c.items()}
    tw, d, dt = w["t"], w["yatay_mesafe"], durations(w["t"])
    i = int(np.nanargmin(d))
    m["en_az_yatay_mesafe_m"], m["en_az_yatay_mesafe_t_s"] = float(d[i]), float(tw[i])
    if follow_distance is not None:
        m["yatay_mesafe_hatasi_ort_m"] = float(np.mean(np.abs(d - follow_distance)))
    near = d < near_m
    m["yakin_mesafe_3m_suresi_s"] = float(dt[near].sum())
    for a, b in intervals(tw, near):
        span = (tw >= a) & (tw <= b)
        j = int(np.argmin(np.where(span, d, np.inf)))
        events.append({"baslangic_s": a, "bitis_s": b, "en_az_m": float(d[j]), "en_az_t_s": float(tw[j])})
    m["yakin_mesafe_3m_olay_sayisi"] = len(events)
    near_limit, far_limit = frame_limits(camera, w["kamera_z"], tilt_deg)
    if camera is not None:
        m["kadraj_yakin_sinir_m"] = float(np.nanmean(near_limit))
        m["kadraj_uzak_sinir_m"] = float(np.nanmean(far_limit))
        m["kadraj_yakin_sinir_alti_s"] = float(dt[d < near_limit].sum())
        m["kadraj_uzak_sinir_ustu_s"] = float(dt[d > far_limit].sum())
    rows = [r for r in referee if _inside(r["t"], start, end)]
    feet = np.array([bool(r.get("ayak_gorunur")) for r in rows])
    head = np.array([bool(r.get("bas_gorunur")) for r in rows])
    m["ayak_kadrajda_orani"] = float(feet.mean())
    m["hedef_kadrajda_orani"] = float((feet & head).mean())
    if following:
        moving = w["hedef_hiz"] >= MOVING_SPEED
        behind = np.degrees(w["hedef_yaw"]) + 180.0  # ENU: the direction from the target back along its motion
        error = np.abs(wrap_deg(orbit[win] - behind))
        ok = moving & np.isfinite(error)
        m |= stats("arkada_kalma_hatasi", error[ok], ("ort", "p95", "maks"), "_deg")
        m["arkada_kalma_kare"] = int(ok.sum())
        m["arkada_kalma_suresi_s"] = float(dt[ok].sum())
        m["arkada_kalma_hatasi_90_ustu_s"] = float(dt[ok & (error > OVERSHOOT_DEG)].sum())
    return m, events


def behind_error_series(referee: Sequence[Mapping]) -> tuple[np.ndarray, np.ndarray]:
    """(t, behind-angle error [deg], NaN while the target stands) of every referee row (for the plots)."""
    c = _columns(referee, ("t", "dron_x", "dron_y", "hedef_x", "hedef_y", "hedef_yaw", "hedef_hiz"))
    orbit = np.degrees(np.arctan2(c["dron_y"] - c["hedef_y"], c["dron_x"] - c["hedef_x"]))
    error = np.abs(wrap_deg(orbit - (np.degrees(c["hedef_yaw"]) + 180.0)))
    error[c["hedef_hiz"] < MOVING_SPEED] = math.nan
    return c["t"], error


# --- ULog ----------------------------------------------------------------------------------------------------------


@dataclass
class Topics:
    """Datasets of some ULog topics over the ULog files of one run (oldest first), concatenated in time; multi
    instance 0 only. data[name] = {field: np.ndarray}; missing topics are absent."""

    data: dict[str, dict[str, np.ndarray]] = field(default_factory=dict)
    error: str | None = None

    @classmethod
    def read(cls, paths: Sequence[Path], names: Sequence[str]) -> "Topics":
        out: dict[str, dict[str, list]] = {}
        try:
            from pyulog import ULog

            for path in paths:
                if path is None or not Path(path).is_file():
                    continue
                for d in ULog(str(path), list(names)).data_list:
                    if d.multi_id != 0:
                        continue
                    for k, v in d.data.items():
                        out.setdefault(d.name, {}).setdefault(k, []).append(np.asarray(v))
        except Exception as e:  # noqa: BLE001 - the report must still be written
            return cls({}, f"{type(e).__name__}: {e}")
        joined = {}
        for name, columns in out.items():
            parts = {k: np.concatenate(v) for k, v in columns.items()}
            order = np.argsort(parts["timestamp"], kind="stable")
            joined[name] = {k: v[order] for k, v in parts.items()}
        return cls(joined)

    def get(self, name: str) -> dict[str, np.ndarray] | None:
        return self.data.get(name)


def debug_names(data: Mapping) -> np.ndarray:
    """The name of every debug_vect sample from pyulog's columns (one int8 column per character, name[0] ...)."""
    chars = np.stack([np.asarray(data[f"name[{i}]"]) for i in range(DEBUG_NAME_CHARS)], axis=1).astype(np.uint8)
    return np.array([bytes(row).split(b"\0", 1)[0].decode("ascii", "replace") for row in chars])


def tez_los_in_ulog(data: Mapping | None, start: float, end: float, sent: Sequence[Mapping] | None = None) -> dict:
    """TEZ_LOS samples PX4 logged (debug_vect, SDLOG_PROFILE 163) in the window start..end [s]: PX4's time stamp is
    the message's arrival (mavlink_receiver), PX4's clock is the sim clock in SITL. Other DEBUG_VECT senders share the
    topic, so only the name TEZ_LOS counts. data None (no debug_vect in the ULog): 0 messages, the rest NaN.

    With `sent` (tez_los.csv rows that went out: t, x, y, z, gonderim_sim) every logged message with a direction is
    matched to the sent one with the same values nearest in time: PX4 arrival - capture is the end-to-end delay as the
    autopilot sees it (PX4 drops time_usec, so the values are the only link; a NaN message is ambiguous)."""
    span = end - start
    m = {"tez_los_px4_sayisi": 0, "tez_los_px4_hizi_hz": 0.0 if span > 0 else math.nan, "tez_los_px4_eslesen": 0}
    m |= stats("uctan_uca_px4_ms", (), ("ort", "p95")) | stats("px4_varis_eksi_gonderim_ms", (), ("ort", "p95", "min"))
    if data is None or len(data["timestamp"]) == 0:
        return m
    t = np.asarray(data["timestamp"], dtype=float) / 1e6
    inside = (t >= start) & (t <= end) & (debug_names(data) == TEZ_LOS_NAME)
    count = int(inside.sum())
    m["tez_los_px4_sayisi"] = count
    m["tez_los_px4_hizi_hz"] = count / span if span > 0 else math.nan
    if sent is None:
        return m
    with_dir = [a for a in sent if not math.isnan(a["x"])]
    vals = np.array([[a["x"], a["y"], a["z"]] for a in with_dir]).reshape(-1, 3)
    sent_t = np.array([a["gonderim_sim"] for a in with_dir])
    captured = np.array([a["t"] for a in with_dir])
    logged = np.stack([np.asarray(data[k], dtype=float) for k in "xyz"], axis=1)
    delays, gaps = [], []
    for i in np.flatnonzero(inside & np.isfinite(logged[:, 0])):
        same = np.all(np.abs(vals - logged[i]) < PX4_MATCH_VALUE, axis=1) & (np.abs(sent_t - t[i]) < PX4_MATCH_S)
        found = np.flatnonzero(same)
        if found.size:
            j = found[np.argmin(np.abs(sent_t[found] - t[i]))]
            delays.append((t[i] - captured[j]) * 1000.0)
            gaps.append((t[i] - sent_t[j]) * 1000.0)
    m["tez_los_px4_eslesen"] = len(delays)
    m |= stats("uctan_uca_px4_ms", delays, ("ort", "p95"))
    return m | stats("px4_varis_eksi_gonderim_ms", gaps, ("ort", "p95", "min"))


def follow_target_in_ulog(
    target: Mapping | None,
    estimator: Mapping | None,
    start: float,
    end: float,
    world: konumlama.WorldGeo | None,
    truth: Callable[[float], tuple[float, float]] | None,
) -> dict:
    """What PX4 made of FOLLOW_TARGET in the window start..end [s] (PX4 time = sim time in SITL): follow_target (what
    arrived; the logger keeps one sample per 500 ms, so this is not the number of messages) and
    follow_target_estimator (every 200 ms): how far its estimate (lat_est / lon_est, the position the Follow Me task
    flies after) was from where the person really was at that time, how often it was valid, and for how long it was
    stale (no FOLLOW_TARGET for 3 s: PX4 keeps the last position and stops moving it)."""
    span = end - start
    m: dict = {"follow_target_px4_sayisi": 0, "follow_target_px4_hizi_hz": 0.0 if span > 0 else math.nan}
    m |= {"px4_kestirim_gecerli_orani": math.nan, "px4_kestirim_bayat_s": math.nan}
    m |= stats("px4_kestirim_hatasi", (), STATS, "_m")
    if target is not None:
        t = np.asarray(target["timestamp"], dtype=float) / 1e6
        count = int(((t >= start) & (t <= end)).sum())
        m["follow_target_px4_sayisi"] = count
        m["follow_target_px4_hizi_hz"] = count / span if span > 0 else math.nan
    if estimator is None:
        return m
    t = np.asarray(estimator["timestamp"], dtype=float) / 1e6
    inside = (t >= start) & (t <= end)
    valid = np.asarray(estimator["valid"]).astype(bool) & inside
    stale = np.asarray(estimator["stale"]).astype(bool)
    steps = np.diff(t, append=t[-1] if t.size else 0.0)
    m["px4_kestirim_gecerli_orani"] = float(valid.sum() / inside.sum()) if inside.any() else math.nan
    m["px4_kestirim_bayat_s"] = float(steps[inside & stale].sum())
    errors = []
    if world is not None and truth is not None:
        lat, lon = np.asarray(estimator["lat_est"], dtype=float), np.asarray(estimator["lon_est"], dtype=float)
        for i in np.flatnonzero(valid & np.isfinite(lat) & np.isfinite(lon)):
            x, y, _ = world.to_local(lat[i], lon[i])
            tx, ty = truth(t[i])
            errors.append(math.hypot(x - tx, y - ty))
    return m | stats("px4_kestirim_hatasi", errors, STATS, "_m")


def follow_status_in_ulog(
    status: Mapping | None,
    start: float,
    end: float,
    truth: Callable[[float], tuple[float, float, float, float, str]] | None = None,
) -> dict:
    """PX4's Follow Target task about itself (follow_target_status, every 400 ms; NED, course 0 = north):
    px4_rota_kuzey_varsayimi_s: from its first sample, how long its target course stayed at the initial 0 (north,
    FlightTaskAutoFollowTarget.hpp _target_course_rad{0.0f}) before the target moved fast enough to update it;
    px4_rota_hatasi: its course against the target's true course while the target moves at least PX4_COURSE_SPEED;
    px4_yorunge_donusu: how far its orbit angle setpoint turned before the target started walking and in the first
    YURUYUS_BASI_S of the walk. NaN without the topic (it is logged only after the logger restart in follow_me)."""
    m = {
        "px4_durum_sayisi": 0,
        "px4_rota_ilk_deg": math.nan,
        "px4_yorunge_acisi_ilk_deg": math.nan,
        "px4_rota_kuzey_varsayimi_s": math.nan,
        "px4_yorunge_donusu_baslangic_deg": math.nan,
        "px4_yorunge_donusu_yuruyus_basi_deg": math.nan,
    } | stats("px4_rota_hatasi", (), ("ort", "p95"), "_deg")
    if status is None or len(status["timestamp"]) == 0:
        return m
    t = np.asarray(status["timestamp"], dtype=float) / 1e6
    course = np.degrees(np.asarray(status["tracked_target_course"], dtype=float))
    orbit = np.degrees(np.asarray(status["orbit_angle_setpoint"], dtype=float))
    m["px4_durum_sayisi"] = int(t.size)
    m["px4_rota_ilk_deg"], m["px4_yorunge_acisi_ilk_deg"] = float(course[0]), float(wrap_deg(orbit[0]))
    changed = np.flatnonzero(course != course[0])
    m["px4_rota_kuzey_varsayimi_s"] = (
        float((t[changed[0]] if changed.size else t[-1]) - t[0]) if course[0] == 0.0 else 0.0
    )
    if t[0] < start:
        m["px4_yorunge_donusu_baslangic_deg"] = orbit_turn(
            t, orbit, float(t[0]), start, step=float(np.median(np.diff(t)))
        )
    m["px4_yorunge_donusu_yuruyus_basi_deg"] = orbit_turn(
        t, orbit, start, start + YURUYUS_BASI_S, step=float(np.median(np.diff(t))) if t.size > 1 else ORBIT_STEP_S
    )
    if truth is not None:
        errors = []
        for ti, ci in zip(t, course, strict=True):
            if not _inside(ti, start, end):
                continue
            _, _, yaw, speed, _ = truth(ti)
            if speed >= PX4_COURSE_SPEED:
                errors.append(abs(wrap_deg(ci - (90.0 - math.degrees(yaw)))))  # ENU yaw -> NED course
        m |= stats("px4_rota_hatasi", errors, ("ort", "p95"), "_deg")
    return m


def follow_start_metrics(
    follow_attempts: Sequence[Mapping],
    referee: Sequence[Mapping],
    switched: float | None,
    start: float,
    estimator: Mapping | None,
    status: Mapping | None,
) -> dict:
    """Why stock Follow Me sways while the person stands (follow start: mode switch -> the person starts walking; the
    second exception to the window, like the orbit turns). The FOLLOW_TARGET positions that went out then: how much
    they spread around the person (std of sent - true, horizontal), how far one is from the next (frame to frame),
    how far they sit towards the drone (the box's error depends on where the drone looks from; it moves as the drone
    orbits) and how often they went. What PX4's estimator made of them (follow_target_estimator.vel_est, every 200 ms
    in the ULog): the person stands, so all of that speed is made up; the share at or above PX4_COURSE_SPEED, where the
    Follow Target task updates the course it assumes, and how often that course (follow_target_status) changed.
    NaN without a mode switch; the PX4 numbers NaN without the follow_target topics in the ULog."""
    m: dict = {
        "follow_target_titresim_baslangic_m": math.nan,
        "follow_target_ardisik_fark_baslangic_p50_m": math.nan,
        "follow_target_drona_dogru_baslangic_m": math.nan,
        "follow_target_hizi_baslangic_hz": math.nan,
        "px4_kestirim_hizi_baslangic_1mps_orani": math.nan,
        "px4_rota_degisimi_baslangic_sayisi": math.nan,
    } | stats("px4_kestirim_hizi_baslangic", (), ("ort", "p95", "maks"), "_mps")
    if switched is None or not start > switched:
        return m
    span = start - switched
    sent = sorted(
        (a for a in follow_attempts if a["sonuc"] == "gonderildi" and switched <= a["gonderim_sim"] < start),
        key=lambda a: a["gonderim_sim"],
    )
    m["follow_target_hizi_baslangic_hz"] = len(sent) / span
    if sent:
        c = _columns(sent, ("t", "x", "y", "gercek_x", "gercek_y"))
        ex, ey = c["x"] - c["gercek_x"], c["y"] - c["gercek_y"]
        m["follow_target_titresim_baslangic_m"] = float(math.hypot(np.nanstd(ex), np.nanstd(ey)))
        if len(sent) > 1:
            m["follow_target_ardisik_fark_baslangic_p50_m"] = float(
                np.nanmedian(np.hypot(np.diff(c["x"]), np.diff(c["y"])))
            )
        r = _columns(referee, ("t", "dron_x", "dron_y"))
        if r["t"].size:
            dx = np.interp(c["t"], r["t"], r["dron_x"]) - c["gercek_x"]
            dy = np.interp(c["t"], r["t"], r["dron_y"]) - c["gercek_y"]
            length = np.hypot(dx, dy)
            ok = length > ORBIT_MIN_DISTANCE_M
            if ok.any():
                toward = (ex[ok] * dx[ok] + ey[ok] * dy[ok]) / length[ok]
                m["follow_target_drona_dogru_baslangic_m"] = float(np.nanmean(toward))
    if estimator is not None and len(estimator["timestamp"]):
        t = np.asarray(estimator["timestamp"], dtype=float) / 1e6
        inside = (t >= switched) & (t < start) & np.asarray(estimator["valid"]).astype(bool)
        speed = np.hypot(np.asarray(estimator["vel_est[0]"], float), np.asarray(estimator["vel_est[1]"], float))
        speed = speed[inside & np.isfinite(speed)]
        m |= stats("px4_kestirim_hizi_baslangic", speed, ("ort", "p95", "maks"), "_mps")
        if speed.size:
            m["px4_kestirim_hizi_baslangic_1mps_orani"] = float(np.mean(speed >= PX4_COURSE_SPEED))
    if status is not None and len(status["timestamp"]):
        t = np.asarray(status["timestamp"], dtype=float) / 1e6
        course = np.asarray(status["tracked_target_course"], dtype=float)[(t >= switched) & (t < start)]
        m["px4_rota_degisimi_baslangic_sayisi"] = int(np.count_nonzero(np.diff(course) != 0)) if course.size else 0
    return m


@dataclass(eq=False)
class Px4Follow:
    """PX4's Follow Target internals of a run from its ULog, in the Gazebo world (x east, y north [m]; angles NED
    [rad], 0 = north). E: follow_target_estimator (lat_est / lon_est, every 200 ms), the estimator's target. F: the
    target position the task places the drone around, the estimate through the task's own second order filter
    (FlightTaskAutoFollowTarget updateTargetPositionVelocityFilter, natural frequency 1 rad/s, damping 0.71, the
    estimated velocity fed forward); not logged, recovered from follow_target_status (every 400 ms) as
    desired_position_raw - FLW_TGT_DST (cos, sin)(course + follow angle). P: trajectory_setpoint (every 200 ms), the
    position setpoint = F + FLW_TGT_DST (cos, sin)(orbit angle setpoint). F, P and the aim (desired_position_raw) are
    NED from the EKF origin (vehicle_local_position ref_lat / ref_lon); without it they are NaN."""

    est_t: np.ndarray
    est_xy: np.ndarray  # (n, 2) E; NaN where the estimate was not valid
    est_vel: np.ndarray  # (n, 2) vel_est north, east [m/s]
    est_stale: np.ndarray  # no FOLLOW_TARGET for 3 s (PX4 keeps the last position)
    st_t: np.ndarray
    course: np.ndarray  # tracked_target_course: the course PX4 assumes for the target
    orbit: np.ndarray  # orbit_angle_setpoint: direction from F to where PX4 wants the drone now
    follow_angle: np.ndarray
    filtered_xy: np.ndarray  # (m, 2) F
    aim_xy: np.ndarray  # (m, 2) desired_position_raw: F + FLW_TGT_DST behind the assumed course
    sp_t: np.ndarray
    setpoint_xy: np.ndarray  # (k, 2) P

    @classmethod
    def from_topics(cls, topics: "Topics", world: konumlama.WorldGeo, distance: float | None) -> "Px4Follow | None":
        """None without follow_target_estimator and follow_target_status (no follow_me, or not logged)."""
        est, st = topics.get("follow_target_estimator"), topics.get("follow_target_status")
        if est is None or st is None or not len(est["timestamp"]) or not len(st["timestamp"]):
            return None
        valid = np.asarray(est["valid"]).astype(bool)
        lat, lon = np.asarray(est["lat_est"], dtype=float), np.asarray(est["lon_est"], dtype=float)
        est_xy = np.full((lat.size, 2), math.nan)
        for i in np.flatnonzero(valid & np.isfinite(lat) & np.isfinite(lon)):
            est_xy[i] = world.to_local(lat[i], lon[i])[:2]
        proj = None
        lp = topics.get("vehicle_local_position")
        if lp is not None and len(lp["timestamp"]):
            ref = float(lp["ref_lat"][-1]), float(lp["ref_lon"][-1])
            if all(math.isfinite(v) for v in ref) and ref != (0.0, 0.0):
                proj = konumlama.MapProjection(*ref)

        def to_world(north: np.ndarray, east: np.ndarray) -> np.ndarray:
            out = np.full((len(north), 2), math.nan)
            if proj is None:
                return out
            for i, (n, e) in enumerate(zip(north, east, strict=True)):
                if math.isfinite(n) and math.isfinite(e):
                    out[i] = world.to_local(*proj.reproject(float(n), float(e)))[:2]
            return out

        course = np.asarray(st["tracked_target_course"], dtype=float)
        follow_angle = np.asarray(st["follow_angle"], dtype=float)
        aim_n = np.asarray(st["desired_position_raw[0]"], dtype=float)
        aim_e = np.asarray(st["desired_position_raw[1]"], dtype=float)
        dst = math.nan if distance is None else float(distance)
        sp = topics.get("trajectory_setpoint")
        sp_t = np.asarray(sp["timestamp"], dtype=float) / 1e6 if sp is not None else np.zeros(0)
        sp_xy = (
            to_world(np.asarray(sp["position[0]"], dtype=float), np.asarray(sp["position[1]"], dtype=float))
            if sp is not None
            else np.zeros((0, 2))
        )
        return cls(
            est_t=np.asarray(est["timestamp"], dtype=float) / 1e6,
            est_xy=est_xy,
            est_vel=np.stack([np.asarray(est["vel_est[0]"], float), np.asarray(est["vel_est[1]"], float)], axis=1),
            est_stale=np.asarray(est["stale"]).astype(bool),
            st_t=np.asarray(st["timestamp"], dtype=float) / 1e6,
            course=course,
            orbit=np.asarray(st["orbit_angle_setpoint"], dtype=float),
            follow_angle=follow_angle,
            filtered_xy=to_world(
                aim_n - dst * np.cos(course + follow_angle), aim_e - dst * np.sin(course + follow_angle)
            ),
            aim_xy=to_world(aim_n, aim_e),
            sp_t=sp_t,
            setpoint_xy=sp_xy,
        )

    @staticmethod
    def _pick(ts: np.ndarray, values: np.ndarray, t: float, hold: bool) -> np.ndarray:
        """values (n,) or (n, k) at t: the last sample at or before t (hold), or linearly between the samples around
        t; NaN outside the samples."""
        shape = values.shape[1:]
        if ts.size == 0:
            return np.full(shape, math.nan)
        if hold:
            i = int(np.searchsorted(ts, t, side="right")) - 1
            return values[i].astype(float) if i >= 0 else np.full(shape, math.nan)
        if values.ndim == 1:
            return np.asarray(np.interp(t, ts, values, left=math.nan, right=math.nan))
        return np.array([np.interp(t, ts, values[:, k], left=math.nan, right=math.nan) for k in range(shape[0])])

    def at(self, t: float, hold: bool = False) -> dict:
        """Everything at sim time t [s]: E, F, P, aim (world x, y), vel (north, east), speed, course, orbit,
        follow_angle (interpolated, angles unwrapped; hold: as last logged, like the video), stale (as last logged)."""
        vel = self._pick(self.est_t, self.est_vel, t, hold)
        stale = self._pick(self.est_t, self.est_stale.astype(float), t, True)
        angles = {
            k: float(self._pick(self.st_t, v if hold else np.unwrap(v), t, hold))
            for k, v in (("course", self.course), ("orbit", self.orbit), ("follow_angle", self.follow_angle))
        }
        return {
            "E": self._pick(self.est_t, self.est_xy, t, hold),
            "F": self._pick(self.st_t, self.filtered_xy, t, hold),
            "P": self._pick(self.sp_t, self.setpoint_xy, t, hold),
            "aim": self._pick(self.st_t, self.aim_xy, t, hold),
            "vel": vel,
            "speed": float(np.hypot(*vel)) if vel.size == 2 else math.nan,
            "stale": bool(stale == 1.0),
            **angles,
        }


# --- (d) tracking: the person's corners and the near passes ----------------------------------------------------------

CLOSE_PASS_M = 6.0  # [m] user's question (13.11): every span of the recording closer than this is explained
DISTANCE_BANDS_M = (4.0, 6.0, 10.0)  # [m] shares of the recording below 4, below 6, 6..10 and above 10 m
LEG_TURN_RATE_DEG_S = 20.0  # [deg/s] slower on a straight leg: the natural sway ~4 deg/s, a 1.3 m arc at 1.4 m/s ~60
LEG_RATE_SPAN_S = 0.5  # [s] the turn rate is taken over this
LEG_MIN_S = 1.0  # [s] a straight stretch at least this long is a leg
LEG_ON_COURSE_DEG = 20.0  # [deg] a leg starts where the person first moves this close to its direction
CORNER_TURN_DEG = 45.0  # [deg] a leg turning at least this much from the one before starts at a corner
STAND_S = 1.0  # [s] standing this long before a leg makes it a start (kalkış)
CATCH_UP_DEG = 30.0  # [deg] PX4's assumed course this close to the new direction: it caught up with the corner
CORNER_WINDOW_S = 6.0  # [s] after a corner: the overshoot is looked for and a near pass is put down to it
SPEED_CHANGE_MPS = 1.0  # [m/s] the person's speed changed this much ...
SPEED_CHANGE_S = 4.0  # [s] ... in this long before the closest moment: it stopped, started or ran
BLIND_S = 1.5  # [s] no measurement this long at the start of the approach: PX4 flew on its prediction (3 fusions)
GAP_FACTOR_S = 1.0  # [s] a gap this long (2 fusions) from STALE_S before the approach to its closest moment: a factor
STALE_S = 3.0  # [s] PX4's stale timeout (TargetEstimator GPS_MESSAGE_STALE_TIMEOUT_MS)
POSITION_SHIFT_M = 0.5  # [m] the sent position's error brought the drone this much closer: konum kayması
NEAR_PASS_CAUSES = ("takip_basi", "kilit_kaybi", "kose", "durma_hizlanma", "konum_kaymasi", "diger", "takip_yok")
DECOMPOSITION_TERMS = ("dron_m", "px4_suzgec_m", "px4_ongoru_m", "konum_hatasi_m", "olcum_yasi_m")


def _spans(mask: np.ndarray) -> list[tuple[int, int]]:
    """[(first, last)] indices of the runs where mask holds."""
    out, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = i
        elif not m and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(mask) - 1))
    return out


def _mean_course(radians: np.ndarray) -> float:
    return float(np.degrees(np.arctan2(np.sin(radians).mean(), np.cos(radians).mean())) % 360.0)


def legs(referee: Sequence[Mapping]) -> list[dict]:
    """The straight legs of the person's path from the referee (Gazebo truth, every camera frame), in time order:
    [{no, baslangic_s, bitis_s, yon_deg, onceki_yon_deg, donus_deg, durus_s, tur}]. A leg is a stretch of at least
    LEG_MIN_S moving (>= MOVING_SPEED) with the course turning slower than LEG_TURN_RATE_DEG_S; legs less than
    CORNER_TURN_DEG apart without a stop between are one leg. baslangic_s: where the person first moves within
    LEG_ON_COURSE_DEG of the leg's direction (yon_deg, NED course, 0 = north) after the leg before; durus_s: standing
    time before it; tur: kalkis (after standing >= STAND_S), donus (a turn while moving) or ilk."""
    c = _columns(referee, ("t", "hedef_hiz", "hedef_yaw"))
    t = c["t"]
    if t.size < 2:
        return []
    moving = c["hedef_hiz"] >= MOVING_SPEED
    yaw = c["hedef_yaw"]
    known = np.isfinite(yaw)
    if not known.any():
        return []
    yaw = yaw[np.maximum.accumulate(np.where(known, np.arange(t.size), np.argmax(known)))]  # NaN: the yaw before it
    course = np.unwrap(math.pi / 2 - yaw)  # ENU yaw -> NED course
    rate = np.degrees(np.abs(course - np.interp(t - LEG_RATE_SPAN_S, t, course))) / LEG_RATE_SPAN_S
    dt = durations(t)
    runs = [(a, b) for a, b in _spans(moving & (rate < LEG_TURN_RATE_DEG_S)) if t[b] - t[a] >= LEG_MIN_S]
    merged: list[list[tuple[int, int]]] = []
    for run in runs:
        if merged:
            leg = merged[-1]
            between = slice(leg[-1][1] + 1, run[0])
            standing = float(dt[between][~moving[between]].sum())
            turn = abs(wrap_deg(_mean_course(course[run[0] : run[1] + 1]) - _mean_course(_steady(course, leg))))
            if turn < CORNER_TURN_DEG and standing < STAND_S:
                leg.append(run)  # a gentle bend: the same leg goes on
                continue
        merged.append([run])
    out = []
    previous_end, previous_dir = -1, None
    course_deg = np.degrees(course) % 360.0
    for k, leg in enumerate(merged):
        direction = _mean_course(_steady(course, leg))
        near = np.abs(wrap_deg(course_deg - direction)) < LEG_ON_COURSE_DEG
        search = np.arange(previous_end + 1, leg[0][0] + 1)
        hits = search[moving[search] & near[search]]
        first = int(hits[0]) if hits.size else leg[0][0]
        before = slice(previous_end + 1, first)
        standing = float(dt[before][~moving[before]].sum())
        turn = abs(wrap_deg(direction - previous_dir)) if previous_dir is not None else math.nan
        kind = "kalkis" if standing >= STAND_S else ("donus" if previous_dir is not None else "ilk")
        out.append(
            {
                "no": k + 1,
                "baslangic_s": float(t[first]),
                "bitis_s": float(t[leg[-1][1]]),
                "yon_deg": direction,
                "onceki_yon_deg": previous_dir,
                "donus_deg": turn,
                "durus_s": standing,
                "tur": kind,
            }
        )
        previous_end, previous_dir = leg[-1][1], direction
    return out


def _steady(values: np.ndarray, leg: Sequence[tuple[int, int]]) -> np.ndarray:
    return np.concatenate([values[a : b + 1] for a, b in leg])


def corner_metrics(
    legs_: Sequence[Mapping], referee: Sequence[Mapping], px4: Px4Follow | None, following: bool
) -> tuple[dict, list[dict]]:
    """How the follow mode took each leg start (the corners of the person's path; legs()): px4_yetisme_s, the time
    until PX4's assumed course (follow_target_status) came within CATCH_UP_DEG of the new direction, searched until
    the next corner (NaN: it did not; NaN without the status); arkada_kalma_maks_deg and arkada_kalma_90_ustu_s, the
    largest behind-angle error and the time the drone was beside or ahead of the person (> OVERSHOOT_DEG) in the
    CORNER_WINDOW_S after the corner, until the next one (NaN without a follow mode). The 9.8 work had these in a
    script outside the repo with the corners of takip_yuruyen written in; here they come from the referee.

    -> (olcutler: the totals and kose_<i>_* of every corner, the corners for ozet.json "koseler")."""
    t_b, error = behind_error_series(referee)
    dt = durations(t_b)
    corners = []
    for k, g in enumerate(legs_):
        t_k = g["baslangic_s"]
        until = legs_[k + 1]["baslangic_s"] if k + 1 < len(legs_) else math.inf
        c = dict(g) | {"px4_yetisme_s": math.nan, "px4_yetisti": None}
        if px4 is not None and px4.st_t.size:
            sel = (px4.st_t >= t_k) & (px4.st_t < until)
            off = np.abs(wrap_deg(np.degrees(px4.course[sel]) - g["yon_deg"]))
            hit = np.flatnonzero(off < CATCH_UP_DEG)
            c["px4_yetisti"] = bool(hit.size)
            c["px4_yetisme_s"] = float(px4.st_t[sel][hit[0]] - t_k) if hit.size else math.nan
        c["arkada_kalma_maks_deg"] = c["arkada_kalma_90_ustu_s"] = math.nan
        if following:
            w = (t_b >= t_k) & (t_b < min(t_k + CORNER_WINDOW_S, until)) & np.isfinite(error)
            c["arkada_kalma_maks_deg"] = float(error[w].max()) if w.any() else math.nan
            c["arkada_kalma_90_ustu_s"] = float(dt[w & (error > OVERSHOOT_DEG)].sum())
        corners.append(c)
    lags = (c["px4_yetisme_s"] for c in corners)
    m: dict = {"kose_sayisi": len(corners)} | stats("kose_px4_yetisme", lags, ("ort", "maks"), "_s")
    known = [c for c in corners if c["px4_yetisti"] is not None]
    m["kose_px4_yetismedi_sayisi"] = sum(not c["px4_yetisti"] for c in known) if known else math.nan
    worst = [c["arkada_kalma_maks_deg"] for c in corners if math.isfinite(c["arkada_kalma_maks_deg"])]
    m["kose_arkada_kalma_maks_deg"] = max(worst) if worst else math.nan
    m["kose_arkada_kalma_90_ustu_s"] = (
        float(sum(c["arkada_kalma_90_ustu_s"] for c in corners)) if following and corners else math.nan
    )
    for i, c in enumerate(corners, start=1):
        for key in ("yon_deg", "px4_yetisme_s", "arkada_kalma_maks_deg", "arkada_kalma_90_ustu_s"):
            m[f"kose_{i}_{key}"] = c[key]
    return m, corners


def _stream(sent: Sequence[Mapping]) -> tuple[np.ndarray, np.ndarray, list[Mapping]]:
    """(send times, newest capture time sent so far, rows) of the measurements that reached PX4, by send time."""
    rows = sorted(sent, key=lambda a: a["gonderim_sim"])
    send = np.array([float(a["gonderim_sim"]) for a in rows])
    capture = np.maximum.accumulate(np.array([float(a["t"]) for a in rows])) if rows else np.zeros(0)
    return send, capture, rows


def _age(x: float, send: np.ndarray, capture: np.ndarray) -> float:
    """[s] how old PX4's newest measurement was at x (from its capture time); inf before the first one."""
    i = int(np.searchsorted(send, x, side="right")) - 1
    return float(x - capture[i]) if i >= 0 else math.inf


def _largest_gap(x0: float, x1: float, send: np.ndarray, capture: np.ndarray) -> float:
    """[s] the largest age of PX4's newest measurement anywhere in x0..x1 (just before each arrival, and at x1)."""
    ages = [_age(x0, send, capture), _age(x1, send, capture)]
    for j in np.flatnonzero((send > x0) & (send <= x1)):
        ages.append(float(send[j] - capture[j - 1]) if j > 0 else math.inf)
    return max(ages)


def decompose(
    target: np.ndarray,
    drone: np.ndarray,
    setpoint: np.ndarray,
    filtered: np.ndarray,
    estimate: np.ndarray,
    sent: np.ndarray,
    sent_truth: np.ndarray,
    orbit: float,
    distance: float | None,
) -> dict:
    """How much closer than FLW_TGT_DST the drone was to the person along n, the direction PX4 wanted it from its
    target (orbit angle setpoint, NED; world x east, y north [m]), split exactly by D - T = (D - P) + (P - F) + (F - E)
    + (E - S) + (S - T_c) + (T_c - T), where P - F is FLW_TGT_DST along n. Each term is how much it brought the drone
    closer (+) or pushed it away (-): dron_m (the drone short of its setpoint P: its momentum, the position
    controller), px4_suzgec_m (the task's filtered target F ahead of the estimate E), px4_ongoru_m (E ahead of the
    last FOLLOW_TARGET S: the estimator's prediction with its velocity and acceleration), konum_hatasi_m (S against
    the person at its frame's capture time T_c: the position from the model's box), olcum_yasi_m (the person moved
    since that frame). kalan_m: what the sum misses (P - F not exactly FLW_TGT_DST along n: topics sampled at other
    times). NaN where an input is missing."""
    n = np.array([math.sin(orbit), math.cos(orbit)]) if math.isfinite(orbit) else np.full(2, math.nan)
    dst = math.nan if distance is None else float(distance)
    parts = {
        "toplam_m": float(dst - (drone - target) @ n),
        "dron_m": float(-(drone - setpoint) @ n),
        "px4_suzgec_m": float(-(filtered - estimate) @ n),
        "px4_ongoru_m": float(-(estimate - sent) @ n),
        "konum_hatasi_m": float(-(sent - sent_truth) @ n),
        "olcum_yasi_m": float(-(sent_truth - target) @ n),
    }
    parts["kalan_m"] = parts["toplam_m"] - sum(parts[k] for k in DECOMPOSITION_TERMS)
    return parts


def near_passes(
    referee: Sequence[Mapping],
    start: float,
    legs_: Sequence[Mapping],
    sent: Sequence[Mapping],
    lock_events: Sequence[Mapping],
    px4: Px4Follow | None,
    distance: float | None,
    source: str,
) -> tuple[dict, list[dict]]:
    """Every span of the recording (the referee's rows: mode switch -> scenario end, what kosu.mp4 shows) with the
    drone closer than CLOSE_PASS_M to the person, why, and the shares of the distance. sent: the measurements that
    reached PX4 (FOLLOW_TARGET in follow_me: t, gonderim_sim, x, y, gercek_x, gercek_y; TEZ_LOS with a target in
    tez_los); px4 and distance (FLW_TGT_DST) give the decomposition at the closest moment (decompose(), follow_me).

    The cause (sebep), the first that holds: takip_yok (source yok: the drone hovers), takip_basi (the person had not
    started walking: the orbit turn of the follow start), kilit_kaybi (at the start of the approach PX4's newest
    measurement was BLIND_S old, or its estimate went stale), kose (a leg turning >= CORNER_TURN_DEG started at most
    CORNER_WINDOW_S before the approach or during it), durma_hizlanma (the person's speed changed >= SPEED_CHANGE_MPS
    in the SPEED_CHANGE_S before the closest moment), konum_kaymasi (the position error term is the largest and
    >= POSITION_SHIFT_M), diger. etkenler: every one of these that holds (olcum_boslugu: a gap >= GAP_FACTOR_S or a
    lock loss from STALE_S before the approach to its closest moment, or a stale estimate: a gap during the approach
    may also be its result, the person below the camera's near limit; the decomposition tells how much it counted).

    -> (olcutler, the events for ozet.json "yakin_gecis")."""
    names = ("t", "yatay_mesafe", "hedef_hiz", "hedef_yaw", "hedef_x", "hedef_y", "dron_x", "dron_y")
    c = _columns(referee, names)
    t, d = c["t"], c["yatay_mesafe"]
    m: dict = {
        "yakin_gecis_6m_olay_sayisi": 0,
        "yakin_gecis_6m_suresi_s": math.nan,
        "yakin_gecis_en_az_m": math.nan,
        **{f"yakin_gecis_{k}_sayisi": 0 for k in NEAR_PASS_CAUSES},
        "mesafe_4m_alti_orani": math.nan,
        "mesafe_6m_alti_orani": math.nan,
        "mesafe_6_10m_orani": math.nan,
        "mesafe_10m_ustu_orani": math.nan,
    }
    if t.size == 0 or not np.isfinite(d).any():
        return m, []
    dt = durations(t)
    total = float(dt.sum())
    low, near_m, high = DISTANCE_BANDS_M
    m |= {
        "yakin_gecis_6m_suresi_s": float(dt[d < CLOSE_PASS_M].sum()),
        "yakin_gecis_en_az_m": float(np.nanmin(d)),
        "mesafe_4m_alti_orani": float(dt[d < low].sum() / total),
        "mesafe_6m_alti_orani": float(dt[d < near_m].sum() / total),
        "mesafe_6_10m_orani": float(dt[(d >= near_m) & (d <= high)].sum() / total),
        "mesafe_10m_ustu_orani": float(dt[d > high].sum() / total),
    }
    send, capture, rows = _stream(sent)
    corners = [g for g in legs_ if g["onceki_yon_deg"] is not None and g["donus_deg"] >= CORNER_TURN_DEG]
    losses = [e["t"] for e in lock_events if e.get("olay") == "kilit_kaybi"]
    course = (90.0 - np.degrees(c["hedef_yaw"])) % 360.0
    events = []
    for a, b in intervals(t, d < CLOSE_PASS_M):
        span = (t >= a) & (t <= b) & (d < CLOSE_PASS_M)
        j = int(np.argmin(np.where(span, d, np.inf)))
        t_min = float(t[j])
        if rows:
            age, gap = _age(a, send, capture), _largest_gap(a - STALE_S, t_min, send, capture)
            age_min = _age(t_min, send, capture)
        elif source == "yok":
            age = gap = age_min = math.nan
        else:  # a follow mode without a single measurement: PX4 never knew where the person was
            age = gap = age_min = math.inf
        stale = False
        if px4 is not None and px4.est_t.size:
            stale = bool(px4.est_stale[(px4.est_t >= a - STALE_S) & (px4.est_t <= t_min)].any())
        recent = [g for g in corners if a - CORNER_WINDOW_S <= g["baslangic_s"] <= t_min]
        window = (t >= t_min - SPEED_CHANGE_S) & (t <= t_min)
        change = float(np.nanmax(c["hedef_hiz"][window]) - np.nanmin(c["hedef_hiz"][window]))
        parts = dict.fromkeys(("toplam_m", *DECOMPOSITION_TERMS, "kalan_m"), math.nan)
        px4_speed = px4_course = math.nan
        if px4 is not None:
            now = px4.at(t_min)
            px4_speed, px4_course = now["speed"], math.degrees(now["course"]) % 360.0
            newest = int(np.searchsorted(send, t_min, side="right")) - 1
            if newest >= 0 and "x" in rows[newest]:
                s = rows[newest]
                parts = decompose(
                    np.array([c["hedef_x"][j], c["hedef_y"][j]]),
                    np.array([c["dron_x"][j], c["dron_y"][j]]),
                    now["P"],
                    now["F"],
                    now["E"],
                    np.array([float(s["x"]), float(s["y"])]),
                    np.array([float(s["gercek_x"]), float(s["gercek_y"])]),
                    now["orbit"],
                    distance,
                )
        finite = {k: parts[k] for k in DECOMPOSITION_TERMS if math.isfinite(parts[k])}
        main = max(finite, key=finite.get) if finite and max(finite.values()) > 0 else None
        shift = bool(parts["konum_hatasi_m"] >= POSITION_SHIFT_M)
        flags = {
            "takip_basi": t_min < start,
            "olcum_boslugu": bool(gap >= GAP_FACTOR_S) or stale or any(a - STALE_S <= x <= t_min for x in losses),
            "kose": bool(recent),
            "durma_hizlanma": change >= SPEED_CHANGE_MPS,
            "konum_kaymasi": shift,
        }
        if source == "yok":
            cause = "takip_yok"
        elif flags["takip_basi"]:
            cause = "takip_basi"
        elif age >= BLIND_S or stale:
            cause = "kilit_kaybi"
        elif flags["kose"]:
            cause = "kose"
        elif flags["durma_hizlanma"]:
            cause = "durma_hizlanma"
        elif shift and main == "konum_hatasi_m":
            cause = "konum_kaymasi"
        else:
            cause = "diger"
        m[f"yakin_gecis_{cause}_sayisi"] += 1
        events.append(
            {
                "baslangic_s": a,
                "bitis_s": b,
                "sure_s": float(dt[span].sum()),
                "en_az_m": float(d[j]),
                "en_az_t_s": t_min,
                "sebep": cause,
                "etkenler": [k for k, v in flags.items() if v] if source != "yok" else [],
                "olcum_yasi_baslangicta_s": age,
                "olcum_yasi_en_azda_s": age_min,
                "en_buyuk_bosluk_s": gap,
                "px4_bayat": stale,
                "kose_s": recent[-1]["baslangic_s"] if recent else None,
                "hiz_degisimi_mps": change,
                "hedef_hizi_mps": float(c["hedef_hiz"][j]),
                "gercek_rota_deg": float(course[j]) if c["hedef_hiz"][j] >= MOVING_SPEED else math.nan,
                "px4_hiz_kestirimi_mps": px4_speed,
                "px4_rota_deg": px4_course,
                "ayristirma": parts,
                "baskin_etken": main,
            }
        )
    m["yakin_gecis_6m_olay_sayisi"] = len(events)
    return m, events


def mode_timeline(status: Mapping | None) -> list[dict]:
    """[{baslangic_s, bitis_s, nav_state, ad}] of PX4's navigation state (vehicle_status) over the run's ULogs."""
    if status is None or len(status["timestamp"]) == 0:
        return []
    t = np.asarray(status["timestamp"], dtype=float) / 1e6
    nav = np.asarray(status["nav_state"]).astype(int)
    spans = []
    begin = 0
    for i in range(1, nav.size + 1):
        if i == nav.size or nav[i] != nav[begin]:
            state = int(nav[begin])
            name = NAV_STATE_NAMES[state] if 0 <= state < len(NAV_STATE_NAMES) else str(state)
            end = float(t[i]) if i < nav.size else float(t[-1])
            spans.append({"baslangic_s": float(t[begin]), "bitis_s": end, "nav_state": state, "ad": name})
            begin = i
    return spans


def mode_kept(timeline: Sequence[Mapping], wanted: int | None, start: float, end: float) -> float:
    """Share of start..end [s] the timeline spends in nav_state `wanted` (NaN if unknown or no overlap)."""
    if wanted is None or end <= start or not timeline:
        return math.nan
    covered = kept = 0.0
    for s in timeline:
        a, b = max(start, s["baslangic_s"]), min(end, s["bitis_s"])
        if b > a:
            covered += b - a
            kept += (b - a) if s["nav_state"] == wanted else 0.0
    return kept / (end - start) if covered > 0 else math.nan


def wanted_nav_state(timeline: Sequence[Mapping], switched_at: float | None) -> int | None:
    """The nav_state PX4 was in right after the run switched to its mode (the heartbeat had already confirmed it)."""
    if switched_at is None:
        return None
    for s in timeline:
        if s["bitis_s"] > switched_at:
            return s["nav_state"]
    return None


def mavlink_mode_kept(changes: Sequence[tuple[float, str]], wanted: str, start: float, end: float) -> float:
    """Same as mode_kept from the run's own heartbeat record [(sim time, mode name)], when there is no ULog."""
    if not changes or end <= start:
        return math.nan
    spans = [
        {"baslangic_s": t, "bitis_s": changes[i + 1][0] if i + 1 < len(changes) else end, "nav_state": int(n == wanted)}
        for i, (t, n) in enumerate(changes)
    ]
    return mode_kept(spans, 1, start, end)


def attitude_in_ulog(att: Mapping | None, truth: Mapping | None, mag: Mapping | None, start: float, end: float) -> dict:
    """EKF yaw (vehicle_attitude) - true yaw (vehicle_attitude_groundtruth, gz_bridge) in the window [deg], and the
    declination of the field PX4's magnetometer measured (sensor_mag rotated into NED with the true attitude; PX4's
    WMM at the world origin: +3.41 deg). Independent of the model (every logged sample)."""
    m = {"ekf_yaw_hatasi_ulog_ort_deg": math.nan, "ekf_yaw_hatasi_ulog_maks_deg": math.nan}
    m["mag_sapma_olculen_deg"] = math.nan
    if att is None or truth is None or len(att["timestamp"]) == 0 or len(truth["timestamp"]) == 0:
        return m
    q = [f"q[{i}]" for i in range(4)]
    tt = np.asarray(truth["timestamp"], dtype=float) / 1e6

    def true_q(at: np.ndarray) -> np.ndarray:
        qs = np.array([np.interp(at, tt, np.asarray(truth[k], dtype=float)) for k in q])
        return qs / np.linalg.norm(qs, axis=0)

    ta = np.asarray(att["timestamp"], dtype=float) / 1e6
    win = (ta >= start) & (ta <= end)
    if win.any():
        error = wrap_deg(_yaw(np.array([np.asarray(att[k], dtype=float) for k in q])[:, win]) - _yaw(true_q(ta[win])))
        m["ekf_yaw_hatasi_ulog_ort_deg"] = float(np.mean(error))
        m["ekf_yaw_hatasi_ulog_maks_deg"] = float(np.max(np.abs(error)))
    if mag is not None and len(mag["timestamp"]):
        tm = np.asarray(mag["timestamp"], dtype=float) / 1e6
        sel = (tm >= start) & (tm <= end)
        if sel.any():
            body = np.array([np.asarray(mag[k], dtype=float)[sel] for k in "xyz"])
            ned = np.einsum("ijn,jn->in", _dcm(true_q(tm[sel])), body)
            m["mag_sapma_olculen_deg"] = float(np.degrees(np.arctan2(np.median(ned[1]), np.median(ned[0]))))
    return m


def _yaw(q: np.ndarray) -> np.ndarray:
    w, x, y, z = q
    return np.degrees(np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))


def _dcm(q: np.ndarray) -> np.ndarray:
    """Body FRD -> NED rotation of each quaternion column (w, x, y, z): (3, 3, n)."""
    w, x, y, z = q
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ]
    )


# --- one run --------------------------------------------------------------------------------------------------------


@dataclass
class RunData:
    """What measure() needs of one run (see the module text); fields left empty make their metrics NaN."""

    start: float  # [s sim] recording window
    end: float
    referee: Sequence[Mapping]  # kayit.Recorder.snapshot()
    source: str  # takip.kaynak: yok | follow_me | tez_los
    detections: Sequence[Mapping] = ()  # algilama.DetectionLog.rows (algilama.csv)
    boxes: Mapping[int, Sequence[Kutu]] = field(default_factory=dict)  # DetectionLog.boxes (kutular.csv)
    skipped: Sequence = ()  # DetectionLog.skipped
    attempts: Sequence[Mapping] = ()  # takip.Tracker.attempts (tez_los.csv)
    follow_attempts: Sequence[Mapping] = ()  # Tracker.follow_attempts (follow_target.csv)
    lock_events: Sequence[Mapping] = ()  # Tracker.events
    camera: kamera.Camera | None = None
    mount: tuple | None = None  # (Recorder.camera_offset, Recorder.camera_dcm)
    world: konumlama.WorldGeo | None = None
    origin: konumlama.GeoPoint | None = None  # EKF origin (GPS_GLOBAL_ORIGIN)
    truth: Callable[[float], tuple] | None = None  # Scenario.truth
    others: int = 0  # other people of the scenario
    same_clothes: frozenset[int] = frozenset()  # the other people dressed like the target (1-based)
    ulogs: Sequence[Path] = ()  # ucus_once.ulg, ucus.ulg (oldest first)
    mode_name: str = ""  # the PX4 mode the run asked for
    mode_switched_s: float | None = None  # [s sim] when PX4's heartbeat reported it
    mode_changes: Sequence[tuple[float, str]] = ()  # [(s sim, mode name)] from the heartbeat while recording
    follow_distance: float | None = None  # FLW_TGT_DST [m] as PX4 holds it (follow_me)
    camera_tilt_deg: float = kamera.NOMINAL_TILT_DEG  # [deg] below the nose: the scenario's kamera.egim_deg


ULOG_TOPICS = (
    "debug_vect",
    "follow_target",
    "follow_target_estimator",
    "follow_target_status",
    "vehicle_status",
    "vehicle_attitude",
    "vehicle_attitude_groundtruth",
    "sensor_mag",
    "trajectory_setpoint",
    "vehicle_local_position",
)


def measure(d: RunData) -> tuple[dict, dict]:
    """Every metric of a run except rapor.metrics' F1 ones and the RTF (senaryo.py); -> (olcutler, more ozet.json
    sections: "mod" (wanted mode, ULog timeline), "yakin_mesafe" (the 3 m events of the window), "koseler" (the
    corners of the person's path and how PX4 took them), "yakin_gecis" (the < 6 m passes of the recording and why))."""
    start, end = d.start, d.end
    following = d.source != "yok"
    m = frame_metrics(d.detections, d.skipped, d.referee, start, end)
    m |= model_metrics(d.detections, d.boxes, d.referee, start, end, d.others, d.same_clothes)
    m |= los_metrics(d.detections, d.referee, start, end)
    m |= stream_metrics(d.attempts, d.lock_events, start, end)
    m |= follow_metrics(d.follow_attempts, d.detections, start, end)
    m |= position_metrics(d.detections, d.referee, start, end, d.camera, d.mount, d.world, d.origin)
    track, near = tracking_metrics(
        d.referee, start, end, d.camera, following, d.follow_distance, tilt_deg=d.camera_tilt_deg
    )
    m |= track
    topics = Topics.read(d.ulogs, ULOG_TOPICS) if d.ulogs else Topics()
    sent = [a for a in d.attempts if a["sonuc"] == "gonderildi"]
    m |= tez_los_in_ulog(topics.get("debug_vect"), start, end, sent)
    sent_count = m["tez_los_gonderilen"]
    m["tez_los_px4_orani"] = m["tez_los_px4_sayisi"] / sent_count if sent_count else math.nan
    truth_xy = (lambda s: d.truth(s)[:2]) if d.truth is not None else None
    m |= follow_target_in_ulog(
        topics.get("follow_target"), topics.get("follow_target_estimator"), start, end, d.world, truth_xy
    )
    m |= follow_status_in_ulog(topics.get("follow_target_status"), start, end, d.truth)
    m |= follow_start_metrics(
        d.follow_attempts,
        d.referee,
        d.mode_switched_s,
        start,
        topics.get("follow_target_estimator"),
        topics.get("follow_target_status"),
    )
    m |= attitude_in_ulog(
        topics.get("vehicle_attitude"), topics.get("vehicle_attitude_groundtruth"), topics.get("sensor_mag"), start, end
    )
    px4 = Px4Follow.from_topics(topics, d.world, d.follow_distance) if d.world is not None else None
    path = legs(d.referee)
    corner_m, corners = corner_metrics(path, d.referee, px4, following)
    if d.source == "follow_me":
        stream = [a for a in d.follow_attempts if a["sonuc"] == "gonderildi"]
    else:  # tez_los: what the mode gets is TEZ_LOS with a target; yok: none
        stream = [a for a in d.attempts if a["sonuc"] == "gonderildi" and a["hedef"]] if following else []
    near_m, passes = near_passes(d.referee, start, path, stream, d.lock_events, px4, d.follow_distance, d.source)
    m |= corner_m | near_m
    timeline = mode_timeline(topics.get("vehicle_status"))
    wanted = wanted_nav_state(timeline, d.mode_switched_s)
    m["mod_korunma_orani"] = mode_kept(timeline, wanted, start, end)
    source = "ulog"
    if math.isnan(m["mod_korunma_orani"]):
        m["mod_korunma_orani"] = mavlink_mode_kept(d.mode_changes, d.mode_name, start, end)
        source = "mavlink" if not math.isnan(m["mod_korunma_orani"]) else None
    sections = {
        "mod": {
            "istenen": d.mode_name,
            "secildi_s": d.mode_switched_s,
            "istenen_nav_state": wanted,
            "korunma_kaynagi": source,
            "mavlink": [list(c) for c in d.mode_changes],
            "ulog": timeline,
        },
        "yakin_mesafe": {"esik_m": NEAR_DISTANCE_M, "olaylar": near},
        "koseler": corners,
        "yakin_gecis": {
            "esik_m": CLOSE_PASS_M,
            "pencere": "kayıt (video): mod seçimi -> senaryo sonu",
            "olaylar": passes,
        },
    }
    if topics.error:
        sections["ulog_hatasi"] = topics.error
    return m, sections
