"""Scenario report: metrics, pass/fail against the scenario's success thresholds, plots, one self-contained HTML.

Outputs in the scenario folder: rapor.html, ozet.json (metrics, machine readable), dogru_cevap.csv (ground truth).
"""

import base64
import datetime as dt
import html
import io
import json
import math
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import dunya  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import dogrulama  # noqa: E402
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


def _git_commit() -> str:
    try:
        git = ["git", "-C", str(SIM_DIR)]
        out = subprocess.run([*git, "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
        dirty = subprocess.run([*git, "status", "--porcelain", "--", ".."], capture_output=True, text=True).stdout
        return out.stdout.strip() + (" (+ commit'lenmemiş değişiklik)" if dirty.strip() else "")
    except (OSError, subprocess.CalledProcessError):
        return "?"


def _fmt(value: float | None, key: str = "") -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "–"
    if key.startswith(("kadrajda", "gorunur", "segmentasyon", "atlanan_kare")):
        return f"%{100 * value:.1f}"
    if isinstance(value, int):
        return str(value)
    return f"{value:.2f}"


METRIC_LABELS = {
    "hedef_yol_m": "Hedefin yolu [m]",
    "hedef_hareket_suresi_s": "Hedefin hareket süresi [s]",
    "yatay_mesafe_min_m": "Yatay mesafe, en az [m]",
    "yatay_mesafe_ort_m": "Yatay mesafe, ortalama [m]",
    "yatay_mesafe_max_m": "Yatay mesafe, en fazla [m]",
    "kadrajda_kalma": "Hedefin kadrajda kaldığı süre",
    "en_uzun_kayip_s": "En uzun kadraj dışı aralık [s]",
    "gorunur_kalma": "Hedefin gerçekten göründüğü süre (ağaç arkası hariç)",
    "kadrajda_ortulu": "Hedef kadrajda ama örtülü (ör. ağaç arkasında)",
    "diger_insan_kadrajda_ort": "Kadrajdaki diğer insan sayısı, ortalama",
    "dron_yukseklik_ort_m": "Dron yüksekliği, ortalama [m]",
    "dron_yatay_hareket_max_m": "Dronun kalkış noktasından en büyük yatay uzaklığı [m]",
    "egim_max_deg": "Dronun en büyük eğimi (ULog) [°]",
    "kayit_suresi_s": "Kayıt süresi [s]",
    "rtf_ort": "Gerçek zaman oranı (RTF), kayıt penceresi ortalaması",
    "rtf_min_5s": "RTF, en yavaş 5 s'lik dilim",
    "uretilen": "Model sürecine ulaşan kamera karesi (kayıt penceresi)",
    "islenen": "Modelin işlediği kare",
    "atlanan": "Model meşgulken atlanan kare",
    "atlanan_kare_orani": "Atlanan kare oranı",
    "islenen_kare_hizi_hz": "İşlenen kare hızı [kare/sim-s]",
    "okuyucuya_ulasmayan": "Kameranın üretip model sürecine hiç ulaşmayan kare",
    "model_ms_ort": "Model süresi (model_ms), ortalama [ms]",
    "model_ms_p95": "Model süresi, p95 [ms]",
    "ulasma_ms_ort": "Karenin model sürecine ulaşma gecikmesi, ortalama [sim ms]",
    "bekleme_ms_ort": "Karenin modeli bekleme süresi, ortalama [ms]",
    "islem_ms_ort": "Kare başına toplam işlem (çözme + kusur + model), ortalama [ms]",
    "iou05_kare_sayisi": "Hedefle IoU ≥ 0.5 model kutusu bulunan işlenmiş kare (geçici kontrol)",
    "iou_max": "Hedefle en iyi IoU",
}


def _json_safe(value: object) -> object:
    """NaN is not valid JSON: write null instead."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(v) for v in value]
    return value


def write(
    out: Path,
    sc: Scenario,
    rows: list[dict],
    events: list[str],
    completed: bool,
    checks: list[dict],
    camera: dict | None,
    camera_mount: dict | None,
    ulog: Path | None,
    settings: dict | None = None,
    more_metrics: dict | None = None,
    sections: dict | None = None,
) -> dict:
    """Write dogru_cevap.csv, ozet.json and rapor.html; `settings` is the run's "ayarlar" (senaryo.settings),
    `more_metrics` go into "olcutler" (model, frame and RTF numbers, task group 4), `sections` are more top level
    parts of ozet.json (e.g. "kare_defteri")."""
    df = pd.DataFrame(rows)
    if not df.empty:
        df.to_csv(out / "dogru_cevap.csv", index=False, float_format="%.4f")
    m = metrics(sc, df) if not df.empty else {}
    m.update(ulog_summary(ulog))
    m.update(more_metrics or {})
    success = evaluate(sc, m)
    verify_ok = dogrulama.passed(checks)
    if checks:
        diffs = [c["fark"] for c in checks if not math.isnan(c["fark"])]
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
        **(sections or {}),
        "basari": [{"alan": k, "esik": th, "deger": v, "gecti": ok} for k, _, th, v, ok in success],
        "dogrulama": checks,
        "olaylar": events,
        "kamera": camera,
        "kamera_montaji": camera_mount,
    }
    summary = _json_safe(summary)
    (out / "ozet.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    figures = []
    if not df.empty:
        figures.append(("Üstten görünüm", plot_map(sc, df)))
        figures.append(("Mesafe", plot_distance(sc, df)))
        figures.append(("Hedefin hızı", plot_target_speed(sc, df)))
        if camera is not None:
            figures.append(("Kamera görüntüsündeki yol", plot_image_track(df, camera)))
    (out / "rapor.html").write_text(_html(sc, summary, success, figures, out), encoding="utf-8")
    return summary


def _html(sc: Scenario, s: dict, success: list, figures: list[tuple[str, str]], out: Path) -> str:
    e = html.escape
    badge = {"GEÇTİ": ("✓", "#1a7f37"), "KALDI": ("✗", "#c62828"), "TAMAMLANMADI": ("!", "#9a6700")}[s["sonuc"]]
    m = s["olcutler"]
    metric_rows = "".join(
        f"<tr><td>{e(label)}</td><td class=num>{_fmt(m[k], k)}</td></tr>"
        for k, label in METRIC_LABELS.items()
        if k in m
    )
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
    figs = "".join(f'<figure><img alt="{e(t)}" src="data:image/png;base64,{b}"></figure>' for t, b in figures)
    files = ", ".join(f"<code>{p.name}</code>" for p in sorted(out.iterdir()) if p.is_file())
    return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(sc.name)} — senaryo raporu</title>
<style>
:root {{ --surface:{SURFACE}; --text:{TEXT}; --text-2:{TEXT_2}; --rule:{GRID}; }}
body {{ background:var(--surface); color:var(--text); font:15px/1.5 system-ui, sans-serif; margin:0 auto;
  max-width:860px; padding:24px 16px; }}
h1 {{ font-size:22px; margin:0 0 4px; }} h2 {{ font-size:17px; margin:28px 0 8px; }}
.muted, figcaption {{ color:var(--text-2); }}
.badge {{ display:inline-block; padding:4px 12px; border-radius:6px; color:#fff; font-weight:600; }}
table {{ border-collapse:collapse; width:100%; font-size:14px; }}
th, td {{ border-bottom:1px solid var(--rule); padding:6px 8px; text-align:left; vertical-align:top; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
figure {{ margin:16px 0; }} img {{ max-width:100%; height:auto; }}
code {{ font-size:13px; }}
</style></head><body>
<h1>{e(sc.name)}</h1>
<p class=muted>{e(sc.description)}</p>
<p><span class=badge style="background:{badge[1]}">{badge[0]} {e(s["sonuc"])}</span>
<span class=muted>&nbsp;{e(s["tarih"])} · commit {e(s["commit"])} · takip kaynağı <code>{e(sc.tracking_source)}</code>,
{sc.altitude:.0f} m</span></p>
<h2>Başarı ölçütleri</h2>{success_html}
<h2>Ölçümler</h2><table>{metric_rows}</table>
<h2>Grafikler</h2>{figs}
{verify_html}
<h2>Olaylar</h2><ul>{events}</ul>
<h2>Dosyalar</h2><p>{files}</p>
<p class=muted>Koordinatlar: Gazebo dünyası, x doğu, y kuzey; dron (0, 0)'dan kalkar. Doğru cevap
(<code>dogru_cevap.csv</code>) senaryodaki yoldan hesaplanır; dron ve kamera konumu Gazebo'dan okunur.</p>
</body></html>
"""
