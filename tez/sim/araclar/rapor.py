"""Scenario report: metrics, checks and warnings, pass/fail against the scenario's success thresholds, plots, one
self-contained HTML.

Outputs in the scenario folder: rapor.html, ozet.json (metrics, machine readable), dogru_cevap.csv (ground truth).
The metrics come from olcum.py (spec "Ölçüt Tanımları": every key, NaN where it does not apply) and from metrics()
below (the F1 numbers of the referee rows). checks() turns some of them into the report's checks and warnings: the
model really ran on the image (IoU, task group 4), the 3 m distance warning (decision 3, 12.11), the camera's near
limit, the mode, the RTF; none of them is a success threshold (m01 sets those).
"""

import base64
import datetime as dt
import html
import io
import json
import math
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import dunya  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import dogrulama  # noqa: E402
import kamera  # noqa: E402
import olcum  # noqa: E402
from hedef import SIM_DIR, SUCCESS_KEYS, Scenario  # noqa: E402

# Reference palette (dataviz skill): categorical slots 1-2, light surface, text and grid tokens
TARGET_COLOR = "#2a78d6"
DRONE_COLOR = "#eb6834"
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
OUT_OF_VIEW = "#ecebe7"
OTHERS_COLOR = "#8b8a86"  # other people: neutral, they are context, not a series to compare
TREE_COLOR = "#5f8f4e"
WARNING_COLOR = "#c62828"
PX4_COLOR = "#7b3fa0"  # what PX4's Follow Target task assumes (course, orbit angle setpoint)
RTF_WARNING = 0.9  # below this mean real time factor the model may take the CPU from Gazebo (senaryo.py)
# Success key -> (metric, the metric must be at least (True) or at most (False) the threshold)
SUCCESS_RULES = {
    "kadrajda_kalma_min": ("kadrajda_kalma", True),
    "gorunur_kalma_min": ("gorunur_kalma", True),
    "en_uzun_kayip_max_s": ("en_uzun_kayip_s", False),
    "yatay_mesafe_max_m": ("yatay_mesafe_max_m", False),
}


def _style(ax: plt.Axes) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(TEXT_2)
    ax.tick_params(colors=TEXT_2, labelsize=9)
    ax.xaxis.label.set_color(TEXT_2)
    ax.yaxis.label.set_color(TEXT_2)


def _png(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _runs(t: np.ndarray, mask: np.ndarray) -> list[tuple[float, float]]:
    """Contiguous [start, end] intervals where mask is true."""
    spans, start = [], None
    for ti, m in zip(t, mask, strict=True):
        if m and start is None:
            start = ti
        elif not m and start is not None:
            spans.append((start, ti))
            start = None
    if start is not None:
        spans.append((start, t[-1]))
    return spans


def metrics(sc: Scenario, df: pd.DataFrame) -> dict:
    walk = df[(df.t >= sc.start_time) & (df.t <= sc.end_time)]
    if walk.empty:
        return {}
    lost = _runs(walk.t.to_numpy(), ~walk.kadrajda.to_numpy(dtype=bool))
    first = df.iloc[0]
    return {
        "kayit_suresi_s": float(df.t.iloc[-1] - df.t.iloc[0]),
        "hedef_yol_m": sc.path_length(),
        "hedef_hareket_suresi_s": sc.walk_end - sc.start_time,
        "yatay_mesafe_min_m": float(walk.yatay_mesafe.min()),
        "yatay_mesafe_ort_m": float(walk.yatay_mesafe.mean()),
        "yatay_mesafe_max_m": float(walk.yatay_mesafe.max()),
        "kadrajda_kalma": float(walk.kadrajda.mean()),
        "en_uzun_kayip_s": max((b - a for a, b in lost), default=0.0),
        "dron_yukseklik_ort_m": float(walk.dron_z.mean()),
        "dron_yatay_hareket_max_m": float(np.hypot(df.dron_x - first.dron_x, df.dron_y - first.dron_y).max()),
    } | _visibility(walk)


def _visibility(walk: pd.DataFrame) -> dict:
    """From the segmentation camera: how often the target was really visible, and how often hidden while in view."""
    if "gorunur" not in walk or walk.hedef_piksel.isna().all():
        return {}
    seen = walk.gorunur.to_numpy(dtype=bool)
    m = {
        "gorunur_kalma": float(seen.mean()),
        "kadrajda_ortulu": float((walk.kadrajda.to_numpy(dtype=bool) & ~seen).mean()),
        "segmentasyon_kare_orani": float(walk.hedef_piksel.notna().mean()),
    }
    others = [c[: -len("_kadrajda")] for c in walk.columns if c.startswith("insan") and c.endswith("_kadrajda")]
    if others:
        m["diger_insan_kadrajda_ort"] = float(walk.kadrajdaki_diger_insan.mean())
    return m


def ulog_summary(path: Path | None) -> dict:
    if path is None or not path.is_file():
        return {}
    try:
        from pyulog import ULog

        ulog = ULog(str(path), ["vehicle_attitude"])
        att = ulog.get_dataset("vehicle_attitude").data
        qw, qx, qy, qz = (att[f"q[{i}]"] for i in range(4))
        tilt = np.degrees(np.arccos(np.clip(1 - 2 * (qx**2 + qy**2), -1, 1)))
        return {
            "ulog_suresi_s": float((ulog.last_timestamp - ulog.start_timestamp) / 1e6),
            "egim_max_deg": float(tilt.max()),
        }
    except Exception as e:  # noqa: BLE001 - the report must still be written
        return {"ulog_hatasi": f"{type(e).__name__}: {e}"}


def evaluate(sc: Scenario, m: dict) -> list[tuple[str, str, float, float, bool]]:
    """(key, description, threshold, value, passed) for every success threshold in the scenario."""
    checks = []
    for key, threshold in sc.success.items():
        metric, at_least = SUCCESS_RULES[key]
        value = m.get(metric, math.nan)
        ok = not math.isnan(value) and (value >= threshold if at_least else value <= threshold)
        checks.append((key, SUCCESS_KEYS[key], threshold, value, ok))
    return checks


def plot_map(sc: Scenario, df: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    _style(ax)
    spec = dunya.load(sc.world)
    for i, t in enumerate(spec.trees if spec else []):
        r = dunya.TREE_KINDS[t.kind].crown_radii[0] * t.scale
        ax.add_patch(
            plt.Circle((t.x, t.y), r, color=TREE_COLOR, alpha=0.25, linewidth=0, label="Ağaç tacı" if i == 0 else None)
        )
    for i in range(1, len(sc.others) + 1):
        if f"insan{i}_x" in df:
            ax.plot(
                df[f"insan{i}_x"],
                df[f"insan{i}_y"],
                color=OTHERS_COLOR,
                linewidth=1.2,
                label="Diğer insanlar" if i == 1 else None,
            )
    ax.plot(df.hedef_x, df.hedef_y, color=TARGET_COLOR, linewidth=2, label="Hedef")
    ax.plot(df.dron_x, df.dron_y, color=DRONE_COLOR, linewidth=2, label="Dron")
    for xs, ys, color in ((df.hedef_x, df.hedef_y, TARGET_COLOR), (df.dron_x, df.dron_y, DRONE_COLOR)):
        ax.plot(xs.iloc[0], ys.iloc[0], "o", color=color, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.plot(xs.iloc[-1], ys.iloc[-1], "s", color=color, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel("Doğu x [m]")
    ax.set_ylabel("Kuzey y [m]")
    ax.legend(frameon=False, labelcolor=TEXT, loc="best", fontsize=9)
    ax.set_title("Üstten görünüm (● başlangıç, ■ bitiş)", color=TEXT, fontsize=11, loc="left")
    return _png(fig)


def plot_distance(sc: Scenario, df: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    _style(ax)
    t = df.t.to_numpy()
    for a, b in _runs(t, ~df.kadrajda.to_numpy(dtype=bool)):
        ax.axvspan(a, b, color=OUT_OF_VIEW, linewidth=0)
    ax.plot(t, df.yatay_mesafe, color=TARGET_COLOR, linewidth=2)
    ax.axvline(sc.start_time, color=TEXT_2, linewidth=0.8, linestyle="--")
    ax.text(sc.start_time, ax.get_ylim()[1], " hedef yürümeye başlar", color=TEXT_2, fontsize=8, va="top")
    ax.set_xlabel("Simülasyon zamanı [s]")
    ax.set_ylabel("Yatay mesafe [m]")
    ax.set_title("Dron–hedef yatay mesafesi (gri: hedef kadraj dışında)", color=TEXT, fontsize=11, loc="left")
    return _png(fig)


def plot_target_speed(sc: Scenario, df: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    _style(ax)
    ax.plot(df.t, df.hedef_hiz, color=TARGET_COLOR, linewidth=2)
    ax.axvline(sc.start_time, color=TEXT_2, linewidth=0.8, linestyle="--")
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Simülasyon zamanı [s]")
    ax.set_ylabel("Hız [m/s]")
    ax.set_title("Hedefin hızı (hızlanma, dönüş ve duraklamalar dahil)", color=TEXT, fontsize=11, loc="left")
    return _png(fig)


def plot_image_track(df: pd.DataFrame, camera: dict) -> str:
    fig, ax = plt.subplots(figsize=(7.2, 7.2 * camera["h"] / camera["w"] + 0.6))
    _style(ax)
    ax.add_patch(plt.Rectangle((0, 0), camera["w"], camera["h"], fill=False, edgecolor=TEXT_2, linewidth=1))
    seen = df[df.kadrajda]
    ax.plot(seen.merkez_u, seen.merkez_v, ".", color=TARGET_COLOR, markersize=3)
    ax.set_xlim(-0.05 * camera["w"], 1.05 * camera["w"])
    ax.set_ylim(1.05 * camera["h"], -0.05 * camera["h"])
    ax.set_aspect("equal")
    ax.set_xlabel("u [piksel]")
    ax.set_ylabel("v [piksel]")
    ax.set_title(
        f"Hedef merkezinin dron kamerasındaki yeri ({camera['w']}×{camera['h']}, kadrajdaki anlar)",
        color=TEXT,
        fontsize=11,
        loc="left",
    )
    return _png(fig)


def plot_tracking(
    sc: Scenario, df: pd.DataFrame, camera: kamera.Camera | None, following: bool, follow_distance: float | None
) -> str:
    """Over time: drone-target horizontal distance against the 3 m warning, the camera's near and far ground limit
    and FLW_TGT_DST; the behind-angle error (following sources); where the referee sees the target in the image."""
    ratios = [2.2, 1.4, 1.0] if following else [2.2, 1.0]
    fig, axes = plt.subplots(len(ratios), 1, figsize=(7.6, 1.7 * sum(ratios) + 0.6), sharex=True, height_ratios=ratios)
    t = df.t.to_numpy()
    ax = axes[0]
    _style(ax)
    for a, b in _runs(t, ~df.kadrajda.to_numpy(dtype=bool)):
        ax.axvspan(a, b, color=OUT_OF_VIEW, linewidth=0)
    ax.plot(t, df.yatay_mesafe, color=TARGET_COLOR, linewidth=1.8, label="yatay mesafe")
    ax.axhline(olcum.NEAR_DISTANCE_M, color=WARNING_COLOR, linewidth=1.0, linestyle="--", label="3 m (uyarı)")
    if camera is not None and "kamera_z" in df:
        near, far = olcum.frame_limits(camera, df.kamera_z.to_numpy(dtype=float))
        ax.plot(t, near, color=TEXT_2, linewidth=1.0, linestyle=(0, (4, 2)), label="kameranın yakın görüş sınırı")
        ax.plot(t, far, color=TEXT_2, linewidth=1.0, linestyle=":", label="uzak sınır")
    if follow_distance is not None:
        ax.axhline(
            follow_distance, color=DRONE_COLOR, linewidth=0.8, alpha=0.7, label=f"FLW_TGT_DST {follow_distance:g} m"
        )
    ax.axvline(sc.start_time, color=TEXT_2, linewidth=0.8)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Mesafe [m]")
    # above the plot: inside it the legend covers the far limit line
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="lower left", bbox_to_anchor=(0.0, 1.0), labelcolor=TEXT)
    ax.set_title(
        "Takip zaman çizelgesi (gri: hedef kadraj dışında; dikey çizgi: hedef yürümeye başlar)",
        color=TEXT,
        fontsize=11,
        loc="left",
        pad=34,
    )
    if following:
        ax = axes[1]
        _style(ax)
        tb, error = olcum.behind_error_series(df.to_dict("records"))
        ax.plot(tb, error, color=DRONE_COLOR, linewidth=1.4)
        ax.axhline(olcum.OVERSHOOT_DEG, color=WARNING_COLOR, linewidth=0.8, linestyle="--")
        ax.text(
            t[0], olcum.OVERSHOOT_DEG, " 90°: dron hedefin yanında/önünde", color=WARNING_COLOR, fontsize=7, va="bottom"
        )
        ax.set_ylim(0, 180)
        ax.set_yticks([0, 45, 90, 135, 180])
        ax.set_ylabel("Arkada kalma\nhatası [°]")
    ax = axes[-1]
    _style(ax)
    lanes = (
        (
            "tamamı kadrajda",
            df.ayak_gorunur.to_numpy(dtype=bool) & df.bas_gorunur.to_numpy(dtype=bool)
            if "ayak_gorunur" in df
            else None,
        ),
        ("merkezi kadrajda", df.kadrajda.to_numpy(dtype=bool)),
        ("görünür (örtülü değil)", df.gorunur.to_numpy(dtype=bool) if "gorunur" in df else None),
    )
    for y, (_, mask) in enumerate(reversed(lanes)):
        if mask is None:
            continue
        spans = [(a, b - a) for a, b in _runs(t, mask)]
        ax.broken_barh(spans, (y - 0.35, 0.7), color=TARGET_COLOR, alpha=0.75)
    ax.set_yticks(range(len(lanes)), [label for label, _ in reversed(lanes)], fontsize=8)
    ax.set_ylim(-0.6, len(lanes) - 0.4)
    ax.grid(False)
    ax.axvline(sc.start_time, color=TEXT_2, linewidth=0.8)
    ax.set_xlabel("Simülasyon zamanı [s]")
    fig.align_ylabels(axes)
    return _png(fig)


def plot_px4_follow(sc: Scenario, status: Mapping, df: pd.DataFrame) -> str:
    """PX4's Follow Target task against the truth (NED, 0 = north, 90 = east): the target course it assumes (starts at
    0, updated only above 1 m/s) and its orbit angle setpoint (where around the target it sends the drone) against
    the drone's real orbit angle and the ideal "behind" (true course + 180 deg)."""
    fig, axes = plt.subplots(2, 1, figsize=(7.6, 5.0), sharex=True)
    ts = np.asarray(status["timestamp"], dtype=float) / 1e6
    course = olcum.wrap_deg(np.degrees(np.asarray(status["tracked_target_course"], dtype=float)))
    orbit = olcum.wrap_deg(np.degrees(np.asarray(status["orbit_angle_setpoint"], dtype=float)))
    t = df.t.to_numpy()
    moving = df.hedef_hiz.to_numpy(dtype=float) >= olcum.MOVING_SPEED
    true_course = olcum.wrap_deg(90.0 - np.degrees(df.hedef_yaw.to_numpy(dtype=float)))  # ENU yaw -> NED course
    actual = np.degrees(np.arctan2(df.dron_x - df.hedef_x, df.dron_y - df.hedef_y).to_numpy(dtype=float))
    ax = axes[0]
    _style(ax)
    ax.plot(
        t[moving], true_course[moving], ".", color=TARGET_COLOR, markersize=2, label="hedefin gerçek rotası (yürürken)"
    )
    ax.plot(ts, course, ".", color=PX4_COLOR, markersize=4, label="PX4'ün varsaydığı rota")
    ax.set_ylabel("Rota [°]")
    ax.set_ylim(-185, 185)
    ax.set_yticks([-180, -90, 0, 90, 180])
    ax.legend(frameon=False, fontsize=8, loc="upper left", labelcolor=TEXT)
    ax.set_title(
        "PX4 Follow Target: hedefin rotası ve yörünge açısı (NED, 0° kuzey, 90° doğu)",
        color=TEXT,
        fontsize=11,
        loc="left",
    )
    ax = axes[1]
    _style(ax)
    behind = olcum.wrap_deg(true_course + 180.0)
    ax.plot(t[moving], behind[moving], ".", color=TARGET_COLOR, markersize=2, label="olması gereken: hedefin arkası")
    ax.plot(t, actual, ".", color=DRONE_COLOR, markersize=2, label="dronun gerçek yörünge açısı")
    ax.plot(ts, orbit, ".", color=PX4_COLOR, markersize=4, label="PX4'ün yörünge açısı hedefi")
    ax.set_ylabel("Yörünge açısı [°]")
    ax.set_ylim(-185, 185)
    ax.set_yticks([-180, -90, 0, 90, 180])
    ax.legend(frameon=False, fontsize=8, loc="upper left", labelcolor=TEXT)
    for a in axes:
        a.axvline(sc.start_time, color=TEXT_2, linewidth=0.8)
    axes[-1].set_xlabel("Simülasyon zamanı [s]")
    return _png(fig)


def _git_commit() -> str:
    try:
        git = ["git", "-C", str(SIM_DIR)]
        out = subprocess.run([*git, "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
        dirty = subprocess.run([*git, "status", "--porcelain", "--", ".."], capture_output=True, text=True).stdout
        return out.stdout.strip() + (" (+ commit'lenmemiş değişiklik)" if dirty.strip() else "")
    except (OSError, subprocess.CalledProcessError):
        return "?"


PERCENT_KEYS = {
    "kadrajda_kalma",
    "kadrajda_ortulu",
    "gorunur_kalma",
    "segmentasyon_kare_orani",
    "hedef_kadrajda_orani",
    "ayak_kadrajda_orani",
    "atlanan_kare_orani",
    "secili_kare_orani",
    "secim_dogru_orani",
    "algilama_orani",
    "kacirma_orani",
    "yanlis_kisi_orani",
    "yanlis_kisi_ayni_kiyafet_orani",
    "tez_los_px4_orani",
    "px4_kestirim_gecerli_orani",
    "mod_korunma_orani",
}


def _fmt(value: object, key: str = "") -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "–"
    if isinstance(value, dict):
        return ", ".join(f"{k} {v}" for k, v in value.items()) or "–"
    if key in PERCENT_KEYS:
        return f"%{100 * value:.1f}"
    if isinstance(value, bool | int):
        return str(int(value))
    return f"{value:.2f}"


# Report tables: (title, [(key, label)]), in the order of the report; every key of olcum.KEYS is in one of them.
METRIC_GROUPS = (
    (
        "Takip: mesafe ve kadraj (hakeme göre, kayıt penceresi)",
        (
            ("yatay_mesafe_ort_m", "Dron–hedef yatay mesafe, ortalama [m]"),
            ("en_az_yatay_mesafe_m", "Yatay mesafe, en az [m]"),
            ("en_az_yatay_mesafe_t_s", "En az mesafenin anı [s]"),
            ("yatay_mesafe_max_m", "Yatay mesafe, en fazla [m]"),
            ("yatay_mesafe_hatasi_ort_m", "Follow Me: |yatay mesafe − FLW_TGT_DST|, ortalama [m]"),
            ("yakin_mesafe_3m_suresi_s", "Yatay mesafenin 3 m altında kaldığı süre [s] (uyarı, eşik değil)"),
            ("yakin_mesafe_3m_olay_sayisi", "3 m altına iniş sayısı"),
            ("kadraj_yakin_sinir_m", "Kameranın yakın görüş sınırı: yerde görülen en yakın nokta, ortalama [m]"),
            (
                "kadraj_yakin_sinir_alti_s",
                "Dronun bu sınırdan yakın kaldığı süre (kişinin ayakları kadraj altında) [s]",
            ),
            ("kadraj_uzak_sinir_m", "Kameranın uzak sınırı: yerde görülen en uzak nokta, ortalama [m]"),
            ("kadraj_uzak_sinir_ustu_s", "Hedefin bu sınırdan uzak kaldığı süre [s]"),
            ("kadrajda_kalma", "Hedefin gövde merkezi kadrajda"),
            ("hedef_kadrajda_orani", "Hedefin tamamı (ayak ve baş) kadrajda"),
            ("ayak_kadrajda_orani", "Hedefin ayakları kadrajda (konum hesabının noktası)"),
            ("gorunur_kalma", "Hedef gerçekten görünüyor (ağaç arkası hariç)"),
            ("kadrajda_ortulu", "Hedef kadrajda ama örtülü (ör. ağaç arkasında)"),
            ("en_uzun_kayip_s", "En uzun kadraj dışı aralık [s]"),
            ("dron_yukseklik_ort_m", "Dron yüksekliği, ortalama [m]"),
            ("egim_max_deg", "Dronun en büyük eğimi (ULog) [°]"),
            ("dron_yatay_hareket_max_m", "Dronun kalkış noktasından en büyük yatay uzaklığı [m]"),
            ("diger_insan_kadrajda_ort", "Kadrajdaki diğer insan sayısı, ortalama"),
        ),
    ),
    (
        "Takip: hedefin arkasında kalma ve yörünge (stok Follow Me davranışı)",
        (
            ("arkada_kalma_hatasi_ort_deg", "Arkada kalma açısı hatası, ortalama [°] (hedef ≥ 0.5 m/s iken)"),
            ("arkada_kalma_hatasi_p95_deg", "Arkada kalma açısı hatası, p95 [°]"),
            ("arkada_kalma_hatasi_maks_deg", "Arkada kalma açısı hatası, en çok [°]"),
            ("arkada_kalma_hatasi_90_ustu_s", "Dron hedefin yanında ya da önünde (hata > 90°) [s]"),
            ("arkada_kalma_suresi_s", "Hedefin yürüdüğü süre (açının tanımlı olduğu) [s]"),
            ("baslangic_yorunge_donusu_deg", "Takip başı: hedef dururken dronun etrafında döndüğü açı [°]"),
            ("yuruyus_basi_yorunge_donusu_deg", "Yürüyüşün ilk 10 s'si: dronun hedef etrafında döndüğü açı [°]"),
            ("px4_rota_kuzey_varsayimi_s", "PX4'ün hedef rotasını kuzey (0°) varsaydığı süre [s]"),
            ("px4_rota_hatasi_ort_deg", "PX4'ün hedef rotası − gerçek rota, ortalama [°] (hedef ≥ 1 m/s)"),
            ("px4_rota_hatasi_p95_deg", "PX4'ün hedef rotası hatası, p95 [°]"),
            ("px4_yorunge_donusu_baslangic_deg", "PX4'ün yörünge açısı hedefinin dönüşü, hedef dururken [°]"),
            ("px4_yorunge_donusu_yuruyus_basi_deg", "PX4'ün yörünge açısı hedefinin dönüşü, yürüyüşün ilk 10 s'si [°]"),
            ("px4_yorunge_acisi_ilk_deg", "PX4'ün ilk yörünge açısı hedefi [°] (0 = hedefin kuzeyi)"),
            ("px4_durum_sayisi", "ULog'daki follow_target_status kaydı (400 ms'de bir)"),
            ("mod_korunma_orani", "İstenen PX4 modunda geçen süre / kayıt penceresi"),
        ),
    ),
    (
        "Takip: konum ve FOLLOW_TARGET",
        (
            ("follow_target_gonderilen", "Gönderilen FOLLOW_TARGET (gönderim anı kayıt penceresinde)"),
            ("follow_target_hizi_hz", "FOLLOW_TARGET hızı [mesaj/sim-s]"),
            ("follow_target_konumsuz_kare", "Konumu hesaplanamadığı için FOLLOW_TARGET gitmeyen işlenmiş kare"),
            (
                "follow_target_uctan_uca_ms_ort",
                "FOLLOW_TARGET uçtan uca gecikme (yakalama → gönderim), ortalama [sim ms]",
            ),
            ("follow_target_uctan_uca_ms_p95", "FOLLOW_TARGET uçtan uca gecikme, p95 [sim ms]"),
            ("follow_target_uctan_uca_ms_maks", "FOLLOW_TARGET uçtan uca gecikme, en çok [sim ms]"),
            ("geolocation_hatasi_ort_m", "Gönderilen hedef konumu − karenin anındaki gerçek konum, ortalama [m]"),
            ("geolocation_hatasi_p50_m", "Gönderilen hedef konumu hatası, p50 [m]"),
            ("geolocation_hatasi_p95_m", "Gönderilen hedef konumu hatası, p95 [m]"),
            ("geolocation_hatasi_maks_m", "Gönderilen hedef konumu hatası, en çok [m]"),
            ("geolocation_hatasi_gonderimde_ort_m", "Gönderilen konum − gönderim anındaki gerçek konum, ortalama [m]"),
            ("geolocation_hatasi_gonderimde_p95_m", "Gönderilen konum − gönderim anındaki gerçek konum, p95 [m]"),
            ("konum_hesaplanan", "Konumu hesaplanan işlenmiş kare (kutunun alt ortası → düz zemin)"),
            ("konum_durumlari", "Konum durumları"),
            ("konum_kare", "Konum hatasının ölçüldüğü kare (seçilen kutu hedefken)"),
            ("konum_hatasi_ort_m", "Model kutusunun konumu − gerçek konum (EKF pozuyla), ortalama [m]"),
            ("konum_hatasi_p50_m", "Model kutusunun konum hatası, p50 [m]"),
            ("konum_hatasi_p95_m", "Model kutusunun konum hatası, p95 [m]"),
            ("konum_hatasi_maks_m", "Model kutusunun konum hatası, en çok [m]"),
            ("konum_hatasi_gercek_pozla_ort_m", "Aynı kutular dronun gerçek pozuyla, ortalama [m] (kutunun payı)"),
            ("konum_hatasi_gercek_pozla_p95_m", "Aynı kutular dronun gerçek pozuyla, p95 [m]"),
            ("ekf_yaw_hatasi_ort_deg", "EKF yaw − gerçek yaw, model kareleri, ortalama [°]"),
            ("ekf_yaw_hatasi_maks_deg", "EKF yaw − gerçek yaw, model kareleri, en çok |·| [°]"),
            ("ekf_yaw_hatasi_ulog_ort_deg", "EKF yaw − gerçek yaw, ULog (her örnek), ortalama [°]"),
            ("ekf_yaw_hatasi_ulog_maks_deg", "EKF yaw − gerçek yaw, ULog, en çok |·| [°]"),
            ("mag_sapma_olculen_deg", "Manyetometrenin ölçtüğü alanın sapması (declination) [°]; PX4 WMM: +3.41°"),
            ("ekf_yatay_konum_hatasi_ort_m", "EKF yatay konumu − gerçek konum, ortalama [m]"),
            ("ekf_yatay_konum_hatasi_maks_m", "EKF yatay konumu − gerçek konum, en çok [m]"),
        ),
    ),
    (
        "PX4'ün hedef kestirimi (ULog)",
        (
            ("follow_target_px4_sayisi", "PX4'ün ULog'a yazdığı follow_target (kaydedici en çok 500 ms'de bir yazar)"),
            (
                "px4_kestirim_hatasi_ort_m",
                "PX4'ün hedef kestirimi (follow_target_estimator) − gerçek konum, ortalama [m]",
            ),
            ("px4_kestirim_hatasi_p50_m", "PX4'ün hedef kestirimi hatası, p50 [m]"),
            ("px4_kestirim_hatasi_p95_m", "PX4'ün hedef kestirimi hatası, p95 [m]"),
            ("px4_kestirim_hatasi_maks_m", "PX4'ün hedef kestirimi hatası, en çok [m]"),
            ("px4_kestirim_gecerli_orani", "PX4'ün hedef kestiriminin geçerli olduğu süre"),
            ("px4_kestirim_bayat_s", "PX4'ün hedefi 'bayat' saydığı süre (3 s FOLLOW_TARGET yok) [s]"),
        ),
    ),
    (
        "(a) Model",
        (
            ("model_kare", "Hakemi olan işlenmiş kare (kayıt penceresi)"),
            ("hedef_gorunur_islenen", "Hedefin göründüğü işlenmiş kare"),
            ("algilama_orani", "Algılama oranı: hedef görünürken hedefle IoU ≥ 0.5 kutu bulunan kare"),
            ("kacirma_orani", "Kaçırma oranı (1 − algılama)"),
            ("iou_ort", "Bulunan karelerde en iyi kutunun IoU'su, ortalama"),
            ("iou_p50", "Bulunan karelerde en iyi kutunun IoU'su, p50"),
            ("iou_max", "Hedefle en iyi IoU"),
            ("secili_kare_orani", "Bir kutunun hedef seçildiği işlenmiş kare"),
            ("secim_dogru_orani", "Hedef görünürken seçilen kutunun hedef olduğu kare (IoU ≥ 0.5)"),
            ("yanlis_kisi_orani", "Seçilen kutu başka bir insanın (IoU ≥ 0.3, hedefinkinden büyük)"),
            ("yanlis_kisi_ayni_kiyafet_orani", "… hedefle aynı kıyafetli bir insanın"),
            ("yanlis_pozitif_kare_basi", "Yanlış pozitif kutu / işlenmiş kare (hiçbir insanla IoU ≥ 0.3 değil)"),
            ("kilit_kaybi_sayisi", "Kilit kaybı (10 işlenmiş karede eşleşme yok)"),
            ("yeniden_kilit_sayisi", "Hakemle yeniden kilit"),
        ),
    ),
    (
        "(b) Görüş vektörü (LOS)",
        (
            ("los_aci_kare", "Ölçülen kare (seçilen kutu hedefken)"),
            ("los_aci_hatasi_ort_deg", "LOS (i) model − LOS (ii) hakem açısı, ortalama [°]"),
            ("los_aci_hatasi_p50_deg", "LOS açı hatası, p50 [°]"),
            ("los_aci_hatasi_p95_deg", "LOS açı hatası, p95 [°]"),
            ("los_aci_hatasi_maks_deg", "LOS açı hatası, en çok [°]"),
            ("los_sapma_farki_yatay_ort_deg", "Sistematik fark, yatay (sağa +), ortalama [°]"),
            ("los_sapma_farki_dikey_ort_deg", "Sistematik fark, dikey (aşağı +), ortalama [°]"),
        ),
    ),
    (
        "(c) Zaman, kareler ve TEZ_LOS",
        (
            ("rtf_ort", "Gerçek zaman oranı (RTF), kayıt penceresi ortalaması"),
            ("rtf_min_5s", "RTF, en yavaş 5 s'lik dilim"),
            ("uretilen", "Model sürecine ulaşan kamera karesi"),
            ("islenen", "Modelin işlediği kare"),
            ("atlanan", "Model meşgulken atlanan kare"),
            ("atlanan_kare_orani", "Atlanan kare oranı"),
            ("islenen_kare_hizi_hz", "İşlenen kare hızı [kare/sim-s]"),
            ("okuyucuya_ulasmayan", "Kameranın üretip model sürecine hiç ulaşmayan kare"),
            ("model_ms_ort", "Model süresi (model_ms), ortalama [ms]"),
            ("model_ms_p95", "Model süresi, p95 [ms]"),
            ("ulasma_ms_ort", "Karenin model sürecine ulaşma gecikmesi, ortalama [sim ms]"),
            ("bekleme_ms_ort", "Karenin modeli bekleme süresi, ortalama [ms]"),
            ("islem_ms_ort", "Kare başına toplam işlem (çözme + kusur + model), ortalama [ms]"),
            ("uctan_uca_ms_ort", "Uçtan uca gecikme (yakalama → gönderim), ortalama [sim ms]"),
            ("uctan_uca_ms_p50", "Uçtan uca gecikme, p50 [sim ms]"),
            ("uctan_uca_ms_p95", "Uçtan uca gecikme, p95 [sim ms]"),
            ("uctan_uca_ms_maks", "Uçtan uca gecikme, en çok [sim ms]"),
            ("uctan_uca_px4_ms_ort", "Uçtan uca gecikme, PX4'ün varış damgasıyla (yakalama → PX4), ortalama [sim ms]"),
            ("uctan_uca_px4_ms_p95", "Uçtan uca gecikme, PX4'ün varış damgasıyla, p95 [sim ms]"),
            ("px4_varis_eksi_gonderim_ms_ort", "PX4'ün varış damgası − gönderim, ortalama [ms]"),
            ("tez_los_gonderilen", "Gönderilen TEZ_LOS (gönderim anı kayıt penceresinde)"),
            ("tez_los_hedef_yok", "Bunlardan 'hedef yok' (NaN)"),
            ("tez_los_gecersiz", "Geçersiz olduğu için gönderilmeyen TEZ_LOS"),
            ("tez_los_reddedilen", "Akış kurallarına takılan TEZ_LOS (aynı / eski kare, hız sınırı)"),
            ("tez_los_hizi_hz", "TEZ_LOS hızı [mesaj/sim-s]"),
            ("tez_los_px4_sayisi", "PX4'ün ULog'a yazdığı TEZ_LOS (debug_vect)"),
            ("tez_los_px4_eslesen", "Değeriyle gönderilenle eşleşen ULog kaydı"),
            ("tez_los_px4_orani", "PX4'e ulaşan / gönderilen TEZ_LOS"),
        ),
    ),
    (
        "Senaryo",
        (
            ("hedef_yol_m", "Hedefin yolu [m]"),
            ("hedef_hareket_suresi_s", "Hedefin hareket süresi [s]"),
            ("kayit_suresi_s", "Kayıt süresi [s]"),
        ),
    ),
)


def _json_safe(value: object) -> object:
    """NaN is not valid JSON: write null instead."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(v) for v in value]
    return value


def _value(m: Mapping, key: str) -> float:
    v = m.get(key)
    return math.nan if v is None else float(v)


def checks(m: Mapping, sections: Mapping, model_ran: bool) -> list[dict]:
    """The report's checks and warnings, [{ad, durum (tamam | uyari | hata), metin, olay}]: olay = the text also goes
    to the events (the RTF and mode events come from senaryo.py already). Measurements, not success thresholds."""
    out = []
    if model_ran:
        found, seen, best = _value(m, "iou05_kare_sayisi"), _value(m, "hedef_gorunur_islenen"), _value(m, "iou_max")
        ok = found > 0
        text = (
            f"Model görüntüde çalışıyor: hedefin göründüğü {seen:.0f} işlenmiş karenin {found:.0f} tanesinde bir model "
            f"kutusu hedefle IoU ≥ {olcum.IOU_MATCH} (en iyi {_fmt(best)})"
            if ok
            else "Model kontrolü: hiçbir işlenmiş karede model kutusu hedefle IoU ≥ 0.5 değil (model görüntüde "
            "çalışmıyor olabilir)"
        )
        out.append({"ad": "model", "durum": "tamam" if ok else "hata", "metin": text, "olay": not ok})
    near = sections.get("yakin_mesafe", {}).get("olaylar", [])
    if near:
        worst = min(near, key=lambda e: e["en_az_m"])
        spans = "; ".join(f"{e['baslangic_s']:.1f}–{e['bitis_s']:.1f} s (en az {e['en_az_m']:.2f} m)" for e in near[:6])
        more = f"; … {len(near) - 6} kez daha" if len(near) > 6 else ""
        out.append(
            {
                "ad": "yakin_mesafe",
                "durum": "uyari",
                "metin": f"Dron–hedef yatay mesafe {olcum.NEAR_DISTANCE_M:g} m altına indi: {len(near)} kez, toplam "
                f"{_value(m, 'yakin_mesafe_3m_suresi_s'):.1f} s, en az {worst['en_az_m']:.2f} m "
                f"({worst['en_az_t_s']:.1f} s): "
                f"{spans}{more}. Eşik m01'e önerilecek bir ölçüm eşiğidir, başarı eşiği değildir.",
                "olay": True,
            }
        )
    elif not math.isnan(_value(m, "en_az_yatay_mesafe_m")):
        out.append(
            {
                "ad": "yakin_mesafe",
                "durum": "tamam",
                "metin": f"Dron–hedef yatay mesafe {olcum.NEAR_DISTANCE_M:g} m altına inmedi (en az "
                f"{_value(m, 'en_az_yatay_mesafe_m'):.2f} m)",
                "olay": False,
            }
        )
    below = _value(m, "kadraj_yakin_sinir_alti_s")
    if below > 0:
        out.append(
            {
                "ad": "kadraj_yakin_siniri",
                "durum": "uyari",
                "metin": f"Dron kameranın yakın görüş sınırından ({_value(m, 'kadraj_yakin_sinir_m'):.1f} m) yakına "
                f"{below:.1f} s girdi: o sırada kişinin ayakları kadrajın altındadır (konum hesabı ayak noktasını "
                "kullanır)",
                "olay": False,
            }
        )
    kept = _value(m, "mod_korunma_orani")
    if not math.isnan(kept) and kept < 0.999:
        out.append(
            {
                "ad": "mod",
                "durum": "uyari",
                "metin": f"Dron kayıt penceresinin %{100 * (1 - kept):.1f}'inde senaryonun modunda değildi "
                f"('{sections.get('mod', {}).get('istenen', '')}')",
                "olay": False,
            }
        )
    rtf = _value(m, "rtf_ort")
    if not math.isnan(rtf) and rtf < RTF_WARNING:
        out.append(
            {
                "ad": "rtf",
                "durum": "uyari",
                "metin": f"RTF {rtf:.2f} (< {RTF_WARNING}): simülasyon gerçek zamandan yavaş aktı; model CPU'yu "
                "Gazebo'dan alıyor olabilir (sim saatiyle ölçülen süreler etkilenmez, model sim saatine göre hızlı "
                "görünür)",
                "olay": False,
            }
        )
    return out


def write(
    out: Path,
    sc: Scenario,
    rows: list[dict],
    events: list[str],
    completed: bool,
    checks_: list[dict],
    camera: dict | None,
    camera_mount: dict | None,
    ulog: Path | None,
    settings: dict | None = None,
    more_metrics: dict | None = None,
    sections: dict | None = None,
    video: Callable[[Path], dict] | None = None,
) -> dict:
    """Write dogru_cevap.csv, ozet.json and rapor.html; `settings` is the run's "ayarlar" (senaryo.settings),
    `more_metrics` go into "olcutler" (olcum.measure and the RTF), `sections` are more top level parts of ozet.json
    (e.g. "kare_defteri", "mod", "yakin_mesafe"). checks_: the overhead verification (dogrulama.py). Every key of
    olcum.KEYS is written (NaN = null where it does not apply); the checks go to "kontroller", failed ones and the
    3 m warning to "olaylar" too. `video` (video.make of the run): called once ozet.json and the CSV files are there
    (it reads them), its answer becomes ozet.json "video"; a failed video is an event, not a failed run."""
    sections = dict(sections or {})
    df = pd.DataFrame(rows)
    if not df.empty:
        df.to_csv(out / "dogru_cevap.csv", index=False, float_format="%.4f")
    m = metrics(sc, df) if not df.empty else {}
    m.update(ulog_summary(ulog))
    m.update(more_metrics or {})
    for key in olcum.KEYS:
        m.setdefault(key, math.nan)
    model_ran = bool(settings and settings.get("algilama", {}).get("model_bilgisi"))
    report_checks = checks(m, sections, model_ran)
    events = list(events) + [c["metin"] for c in report_checks if c["olay"]]
    success = evaluate(sc, m)
    verify_ok = dogrulama.passed(checks_)
    if checks_:
        diffs = [c["fark"] for c in checks_ if not math.isnan(c["fark"])]
        m["dogrulama_fark_max_m"] = max(diffs) if diffs else math.nan
    if not completed or df.empty:
        result = "TAMAMLANMADI"
    elif all(ok for *_, ok in success) and verify_ok is not False:
        result = "GEÇTİ"
    else:
        result = "KALDI"

    summary = {
        "senaryo": sc.name,
        "sonuc": result,
        "tarih": dt.datetime.now().isoformat(timespec="seconds"),
        "commit": _git_commit(),
        "ayarlar": settings or {},
        "olcutler": m,
        "kontroller": report_checks,
        **sections,
        "basari": [{"alan": k, "esik": th, "deger": v, "gecti": ok} for k, _, th, v, ok in success],
        "dogrulama": checks_,
        "olaylar": events,
        "kamera": camera,
        "kamera_montaji": camera_mount,
    }
    summary = _json_safe(summary)
    (out / "ozet.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    if video is not None:
        try:
            info = video(out)
        except Exception as e:  # noqa: BLE001 - the report must still be written
            info = {"hata": f"{type(e).__name__}: {e}"}
        if "hata" in info:
            summary["olaylar"].append(f"Video yapılamadı: {info['hata']}")
        summary["video"] = _json_safe(info)
        text = json.dumps(summary, indent=2, ensure_ascii=False, default=float)
        (out / "ozet.json").write_text(text, encoding="utf-8")

    figures = []
    if not df.empty:
        cam = camera_of(camera)
        following = sc.tracking_source != "yok"
        distance = _follow_distance(settings) if sc.tracking_source == "follow_me" else None
        figures.append(("Takip zaman çizelgesi", plot_tracking(sc, df, cam, following, distance)))
        status = olcum.Topics.read([ulog], ["follow_target_status"]).get("follow_target_status") if ulog else None
        if status is not None and len(status["timestamp"]):
            figures.append(("PX4 Follow Target", plot_px4_follow(sc, status, df)))
        figures.append(("Üstten görünüm", plot_map(sc, df)))
        figures.append(("Mesafe", plot_distance(sc, df)))
        figures.append(("Hedefin hızı", plot_target_speed(sc, df)))
        if camera is not None:
            figures.append(("Kamera görüntüsündeki yol", plot_image_track(df, camera)))
    (out / "rapor.html").write_text(_html(sc, summary, success, figures, out), encoding="utf-8")
    return summary


def camera_of(camera: Mapping | None) -> kamera.Camera | None:
    """The camera back from its ozet.json form (kamera.Camera.as_dict)."""
    if camera is None:
        return None
    return kamera.Camera(
        int(camera["w"]),
        int(camera["h"]),
        camera["fx"],
        camera["fy"],
        camera["cx"],
        camera["cy"],
        tuple(camera["dist"]),
    )


def _follow_distance(settings: Mapping | None) -> float | None:
    """FLW_TGT_DST as PX4 held it (read back before takeoff), else as asked."""
    entry = (settings or {}).get("px4_parametreleri", {}).get("FLW_TGT_DST")
    if not entry:
        return None
    value = entry.get("px4") if entry.get("px4") is not None else entry.get("deger")
    return float(value) if value is not None else None


CHECK_MARK = {"tamam": ("✓", "#1a7f37"), "uyari": ("!", "#9a6700"), "hata": ("✗", WARNING_COLOR)}


def _metric_tables(m: Mapping) -> str:
    e = html.escape
    parts = []
    for title, rows in METRIC_GROUPS:
        present = [(k, label) for k, label in rows if k in m]
        if not present:
            continue
        body = "".join(
            f"<tr><td>{e(label)}<br><code>{e(k)}</code></td><td class=num>{e(_fmt(m[k], k))}</td></tr>"
            for k, label in present
        )
        empty = all(_fmt(m[k], k) == "–" for k, _ in present)
        note = "<p class=muted>Bu koşuda uygulanmaz (değerler NaN).</p>" if empty else ""
        parts.append(f"<h3>{e(title)}</h3>{note}<table>{body}</table>")
    return "".join(parts)


def _settings_html(settings: Mapping) -> str:
    e = html.escape
    if not settings:
        return "<p class=muted>Ayar yok.</p>"
    t = settings.get("takip", {})
    d = settings.get("algilama", {})
    f = d.get("model_dosyasi") or {}
    info = d.get("model_bilgisi") or {}
    lines = [
        ("Takip kaynağı / PX4 modu", f"{t.get('kaynak')} / {t.get('mod')}"),
        ("TEZ_LOS kaynağı (takip.los)", str(t.get("los"))),
        ("PX4'ün seçilebilir modları", ", ".join(t.get("px4_modlari") or []) or "–"),
        ("PX4 başlatma komutları", ", ".join(t.get("px4_baslat") or []) or "–"),
        ("Algılama", "açık" if d.get("etkin") else "kapalı (--modelsiz)"),
    ]
    if d.get("etkin"):
        known = f"modeller.yaml'da {f.get('kayitli')}" if f.get("kayitli") else "modeller.yaml'da kayıtlı değil"
        lines += [
            ("Model dosyası", f"{f.get('yol', d.get('model'))} ({f.get('boyut_bayt')} bayt)"),
            ("Model sha256", f"{f.get('sha256')} ({known})" + (f"; UYARI: {f.get('uyari')}" if f.get("uyari") else "")),
            (
                "Model ayarları",
                f"sınıf {info.get('sinif')} ({info.get('sinif_adi')}), imgsz {info.get('imgsz')} "
                f"(adım {info.get('adim')}), "
                f"conf {info.get('conf')}, {info.get('cekirdek')} çekirdek, ilk çağrı {_fmt(info.get('isinma_ms'))} ms",
            ),
        ]
    g = settings.get("gecikme", {})
    lines.append(("Gecikme", ", ".join(f"{k} {v}" for k, v in g.items()) or "–"))
    lines.append(("Kamera kusurları", ", ".join(settings.get("kusurlar") or {}) or "kapalı"))
    waiting = settings.get("henuz_bagli_degil") or {}
    if waiting:
        lines.append(
            ("Henüz bağlanmamış (varsayılanı etkin değil)", ", ".join(f"{k} (grup {v})" for k, v in waiting.items()))
        )
    table = "".join(f"<tr><td>{e(k)}</td><td>{e(str(v))}</td></tr>" for k, v in lines)
    params = settings.get("px4_parametreleri") or {}
    prow = "".join(
        f"<tr><td><code>{e(name)}</code></td><td class=num>{e(str(p.get('deger')))}</td>"
        f"<td class=num>{e(_fmt(p.get('px4')) if isinstance(p.get('px4'), float) else str(p.get('px4')))}</td>"
        f"<td class=muted>{e(str(p.get('kaynak')))}</td></tr>"
        for name, p in params.items()
    )
    ptable = (
        f"<h3>PX4 başlangıç parametreleri ({len(params)})</h3>"
        "<table><tr><th>Ad</th><th>İstenen</th><th>PX4'ten okunan</th>"
        f"<th>Kaynak</th></tr>{prow}</table>"
        if params
        else ""
    )
    return f"<table>{table}</table>{ptable}"


def _mode_html(mode: Mapping | None) -> str:
    e = html.escape
    if not mode:
        return ""
    spans = mode.get("ulog") or []
    rows = "".join(
        f"<tr><td class=num>{s['baslangic_s']:.1f}</td><td class=num>{s['bitis_s']:.1f}</td>"
        f"<td>{e(s['ad'])} <span class=muted>({s['nav_state']})</span></td></tr>"
        for s in spans
    )
    kept = mode.get("korunma_kaynagi")
    head = (
        f"<p>İstenen mod <b>{e(str(mode.get('istenen')))}</b>, seçildiği an {_fmt(mode.get('secildi_s'))} s"
        f" (PX4 nav_state {mode.get('istenen_nav_state')}); korunma oranının kaynağı: {e(str(kept))}.</p>"
    )
    table = (
        "<table><tr><th>Başlangıç [s]</th><th>Bitiş [s]</th><th>PX4 modu (vehicle_status.nav_state)</th></tr>"
        f"{rows}</table>"
        if rows
        else "<p class=muted>ULog'da vehicle_status yok.</p>"
    )
    return f"<h2>Mod zaman çizelgesi (ULog)</h2>{head}{table}"


def _html(sc: Scenario, s: dict, success: list, figures: list[tuple[str, str]], out: Path) -> str:
    e = html.escape
    badge = {"GEÇTİ": ("✓", "#1a7f37"), "KALDI": ("✗", "#c62828"), "TAMAMLANMADI": ("!", "#9a6700")}[s["sonuc"]]
    m = s["olcutler"]
    m = {k: (math.nan if v is None else v) for k, v in m.items()}
    if success:
        success_rows = "".join(
            f"<tr><td>{e(desc)}<br><code>{e(k)}</code></td><td class=num>{_fmt(th, k)}</td>"
            f"<td class=num>{_fmt(v, k)}</td><td>{'✓ geçti' if ok else '✗ kaldı'}</td></tr>"
            for k, desc, th, v, ok in success
        )
        success_html = (
            "<table><tr><th>Ölçüt</th><th>Eşik</th><th>Ölçülen</th><th>Sonuç</th></tr>" + success_rows + "</table>"
        )
    else:
        success_html = "<p class=muted>Bu senaryoda başarı eşiği tanımlı değil (<code>basari</code> boş).</p>"
    check_items = "".join(
        f'<li class="{c["durum"]}"><span class=mark style="color:{CHECK_MARK[c["durum"]][1]}">'
        f"{CHECK_MARK[c['durum']][0]}</span> {e(c['metin'])}</li>"
        for c in s.get("kontroller", [])
    )
    checks_html = f"<ul class=checks>{check_items}</ul>" if check_items else "<p class=muted>Kontrol yok.</p>"
    verify_html = ""
    if s["dogrulama"]:
        rows = "".join(
            f"<tr><td class=num>{c['t']:.1f}</td><td class=num>{_fmt(c['hesap_x'])}, {_fmt(c['hesap_y'])}</td>"
            f"<td class=num>{_fmt(c['goruntu_x'])}, {_fmt(c['goruntu_y'])}</td>"
            f"<td class=num>{'ağaç altında, görünmüyor' if c.get('ortulu') else _fmt(c['fark'])}</td></tr>"
            for c in s["dogrulama"]
        )
        img = ""
        if (out / "dogrulama_tepe.png").is_file():
            img = "<p class=muted>Örnek tepe kamerası karesi: <code>dogrulama_tepe.png</code></p>"
        verify_html = f"""<h2>Hedef konumu doğrulaması</h2>
<p>Hakemin hesapladığı hedef konumu ile tepe segmentasyon kamerasında görülen konum (gövde merkezi). Sınır
{dogrulama.LIMIT} m: yürürken gövde merkezi yolun 0.05–0.19 m önündedir (öne eğik duruş ve adım döngüsü). Ağaç tacı
altında kalan anlar sayılmaz; hedef kontrol anlarının en az yarısında görünmelidir.</p>
<table><tr><th>Zaman [s]</th><th>Hesap x, y [m]</th><th>Görüntü x, y [m]</th><th>Fark [m]</th></tr>
{rows}</table>{img}"""
    events = "".join(f"<li>{e(x)}</li>" for x in s["olaylar"]) or "<li>Olay yok</li>"
    figs = "".join(
        f'<figure><img alt="{e(t)}" src="data:image/png;base64,{b}"><figcaption>{e(t)}</figcaption></figure>'
        for t, b in figures
    )
    files = ", ".join(f"<code>{p.name}</code>" for p in sorted(out.iterdir()) if p.is_file())
    v = s.get("video") or {}
    if v.get("dosya"):
        video_html = (
            f'<p>Video: <a href="{e(v["dosya"])}">{e(v["dosya"])}</a> ({v["kare_sayisi"]} kare, {v["sure_s"]:.1f} s, '
            f"{v['baslangic_s']:.1f} → {v['bitis_s']:.1f} s; kamera karesi olmayan an {v['eksik_kare']}). VLC ile "
            f"açın: <code>vlc {e(str(out / v['dosya']))}</code></p>"
        )
    elif v.get("hata"):
        video_html = f"<p class=muted>Video yapılamadı: {e(str(v['hata']))}</p>"
    else:
        video_html = "<p class=muted>Video yok (--videosuz).</p>"
    return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(sc.name)} — senaryo raporu</title>
<style>
:root {{ --surface:{SURFACE}; --text:{TEXT}; --text-2:{TEXT_2}; --rule:{GRID}; }}
body {{ background:var(--surface); color:var(--text); font:15px/1.5 system-ui, sans-serif; margin:0 auto;
  max-width:900px; padding:24px 16px; }}
h1 {{ font-size:22px; margin:0 0 4px; }} h2 {{ font-size:17px; margin:28px 0 8px; }}
h3 {{ font-size:15px; margin:18px 0 6px; }}
.muted, figcaption {{ color:var(--text-2); }}
.badge {{ display:inline-block; padding:4px 12px; border-radius:6px; color:#fff; font-weight:600; }}
table {{ border-collapse:collapse; width:100%; font-size:14px; }}
th, td {{ border-bottom:1px solid var(--rule); padding:6px 8px; text-align:left; vertical-align:top; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
td code {{ color:var(--text-2); font-size:12px; }}
ul.checks {{ list-style:none; padding:0; }} ul.checks li {{ padding:6px 10px; margin:4px 0; border-radius:6px;
  background:#f3f2ee; }} ul.checks li.uyari {{ background:#fff4d6; }} ul.checks li.hata {{ background:#fde2e1; }}
.mark {{ font-weight:700; margin-right:4px; }}
figure {{ margin:16px 0; }} img {{ max-width:100%; height:auto; }}
code {{ font-size:13px; }}
</style></head><body>
<h1>{e(sc.name)}</h1>
<p class=muted>{e(sc.description)}</p>
<p><span class=badge style="background:{badge[1]}">{badge[0]} {e(s["sonuc"])}</span>
<span class=muted>&nbsp;{e(s["tarih"])} · commit {e(s["commit"])} · takip kaynağı <code>{e(sc.tracking_source)}</code>,
{sc.altitude:.0f} m</span></p>
{video_html}
<h2>Kontroller ve uyarılar</h2>{checks_html}
<p class=muted>Bunlar ölçümdür, başarı eşiği değildir (eşikleri m01 belirler).</p>
<h2>Başarı ölçütleri</h2>{success_html}
<h2>Ölçümler</h2>
<p class=muted>Yalnız kayıt penceresi ({sc.start_time:.0f} s → {sc.end_time:.1f} s); "takip başı" ölçütleri mod
seçiminden hedefin yürümeye başlamasına kadardır. Tanımlar: spec "Ölçüt Tanımları". "–" = bu koşuda uygulanmaz.</p>
{_metric_tables(m)}
<h2>Grafikler</h2>{figs}
{_mode_html(s.get("mod"))}
<h2>Ayarlar</h2>{_settings_html(s.get("ayarlar") or {})}
{verify_html}
<h2>Olaylar</h2><ul>{events}</ul>
<h2>Dosyalar</h2><p>{files}</p>
<p class=muted>Koordinatlar: Gazebo dünyası, x doğu, y kuzey; dron (0, 0)'dan kalkar. Doğru cevap
(<code>dogru_cevap.csv</code>) senaryodaki yoldan hesaplanır; dron ve kamera konumu Gazebo'dan okunur.</p>
</body></html>
"""
