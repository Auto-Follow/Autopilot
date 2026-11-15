#!/usr/bin/env python3
"""Run one scenario several times and summarise the runs: each run on its own and the mean, the lowest and the
highest of every metric (decision 4, 12.11: in task groups 7 and 9 every scenario runs 3 times; the model source and
the stock Follow Me change from run to run, one run says little).

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/toplu.py --senaryo takip_yuruyen --tekrar 3
    ... --senaryo kalabalik_park --tekrar 3 -- --los hakem     everything after -- goes to senaryo.py, every run
    ... --ozet tez/sim/sonuclar/A tez/sim/sonuclar/B           summarise runs that already exist, no simulation

Every run is its own senaryo.py process without a window, in its own folder (kosu_<i>/): a crash or a stuck Gazebo of
one run does not take the others along and no run inherits another's state. A run that never got going (no ozet.json,
or TAMAMLANMADI before the drone was ready, e.g. no heartbeat from PX4) is an infrastructure failure, not a result: it
is tried again, at most --yeniden-dene times per run, and every attempt is listed. A run that flew and then failed
(KALDI, or TAMAMLANMADI later) is a result and counts.

Outputs in tez/sim/sonuclar/<date>_<scenario>_x<N>/ (or --cikti): kosu_<i>/ and kosu_<i>.log per run (a retried one
keeps its first folder as kosu_<i>_deneme<k>/), toplu.json (per metric: every run's value, ort, en_az, en_cok, n = runs
that have a value; the attempts), toplu.csv (one row per metric) and toplu.html (the main metrics, every run as a dot,
and links to every run's rapor.html and kosu.mp4: each senaryo.py run makes its own video, --videosuz does not).
"""

import argparse
import csv
import datetime as dt
import html
import json
import math
import shutil
import statistics
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import rapor  # noqa: E402
from simulasyon import SIM_DIR, running  # noqa: E402

SCENARIO_TOOL = Path(__file__).resolve().parent / "senaryo.py"
VIDEO = "kosu.mp4"  # every run's video (senaryo.py, video.py), linked from toplu.html
WAIT_FOR_EXIT_S = 120.0  # [s] for the previous run's PX4 and Gazebo to be gone
READY_EVENT = ("Dron ", "hazır")  # senaryo.py's event once the drone is in the scenario's mode
OWN_FLAGS = ("--cikti", "--ekransiz", "--senaryo")  # toplu.py sets these for every run
# The main table and the dots, in this order (labels from the report); every other numeric metric is in toplu.json
MAIN_KEYS = (
    "yatay_mesafe_ort_m",
    "en_az_yatay_mesafe_m",
    "yatay_mesafe_max_m",
    "yatay_mesafe_hatasi_ort_m",
    "yakin_mesafe_3m_suresi_s",
    "yakin_mesafe_3m_olay_sayisi",
    "kadraj_yakin_sinir_alti_s",
    "yakin_gecis_en_az_m",
    "mesafe_4m_alti_orani",
    "mesafe_6m_alti_orani",
    "mesafe_6_10m_orani",
    "mesafe_10m_ustu_orani",
    "yakin_gecis_6m_olay_sayisi",
    "yakin_gecis_6m_suresi_s",
    "yakin_gecis_takip_basi_sayisi",
    "yakin_gecis_kilit_kaybi_sayisi",
    "yakin_gecis_kose_sayisi",
    "yakin_gecis_durma_hizlanma_sayisi",
    "yakin_gecis_konum_kaymasi_sayisi",
    "yakin_gecis_diger_sayisi",
    "kose_px4_yetisme_ort_s",
    "kose_px4_yetisme_maks_s",
    "kose_px4_yetismedi_sayisi",
    "kose_arkada_kalma_maks_deg",
    "kose_arkada_kalma_90_ustu_s",
    "arkada_kalma_hatasi_ort_deg",
    "arkada_kalma_hatasi_p95_deg",
    "arkada_kalma_hatasi_90_ustu_s",
    "baslangic_yorunge_donusu_deg",
    "yuruyus_basi_yorunge_donusu_deg",
    "px4_rota_kuzey_varsayimi_s",
    "px4_rota_hatasi_ort_deg",
    "follow_target_titresim_baslangic_m",
    "px4_kestirim_hizi_baslangic_ort_mps",
    "px4_kestirim_hizi_baslangic_1mps_orani",
    "px4_rota_degisimi_baslangic_sayisi",
    "kadrajda_kalma",
    "hedef_kadrajda_orani",
    "gorunur_kalma",
    "en_uzun_kayip_s",
    "algilama_orani",
    "secim_dogru_orani",
    "yanlis_kisi_orani",
    "yanlis_kisi_ayni_kiyafet_orani",
    "yanlis_pozitif_kare_basi",
    "kilit_kaybi_sayisi",
    "yeniden_kilit_sayisi",
    "los_aci_hatasi_ort_deg",
    "konum_hatasi_ort_m",
    "konum_hatasi_gercek_pozla_ort_m",
    "geolocation_hatasi_ort_m",
    "px4_kestirim_hatasi_ort_m",
    "px4_kestirim_bayat_s",
    "ekf_yaw_hatasi_ulog_ort_deg",
    "ekf_yaw_hatasi_ulog_maks_deg",
    "uctan_uca_ms_ort",
    "model_ms_ort",
    "islenen_kare_hizi_hz",
    "rtf_ort",
    "mod_korunma_orani",
)
DOT_KEYS = (
    "yatay_mesafe_ort_m",
    "en_az_yatay_mesafe_m",
    "mesafe_6m_alti_orani",
    "kose_px4_yetisme_ort_s",
    "yakin_mesafe_3m_suresi_s",
    "arkada_kalma_hatasi_ort_deg",
    "baslangic_yorunge_donusu_deg",
    "hedef_kadrajda_orani",
    "kadrajda_kalma",
    "algilama_orani",
    "kilit_kaybi_sayisi",
    "konum_hatasi_ort_m",
    "ekf_yaw_hatasi_ulog_ort_deg",
    "rtf_ort",
)
LABELS = {k: label for _, rows in rapor.METRIC_GROUPS for k, label in rows}
CORNER_ROWS = (  # kose_<i>_<key> of every corner (olcum.corner_metrics), one table row each
    ("px4_yetisme_s", "PX4'ün rotasının yeni yönün 30° içine girmesi [s] (– yetişmedi)"),
    ("arkada_kalma_maks_deg", "Köşeden sonraki 6 s'de arkada kalma hatası, en çok [°]"),
    ("arkada_kalma_90_ustu_s", "Dron yanında/önünde (> 90°, aşma) [s]"),
)


def log(text: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {text}", flush=True)


def _number(value: object) -> float | None:
    """A metric value as a float, None for null / NaN; None for anything that is not a number (text, dicts)."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return None if math.isnan(value) else float(value)


def aggregate(summaries: Sequence[dict]) -> dict:
    """{metric: {kosular: [value or None per run], ort, en_az, en_cok, n}} over the runs' "olcutler"; only metrics
    that are numbers (or null) in every run, NaN where no run has a value."""
    keys: list[str] = []
    for s in summaries:
        keys += [k for k in s["olcutler"] if k not in keys]
    out = {}
    for key in keys:
        raw = [s["olcutler"].get(key) for s in summaries]
        if any(v is not None and _number(v) is None for v in raw):
            continue  # text or a dict (e.g. konum_durumlari): not averaged
        values = [_number(v) for v in raw]
        have = [v for v in values if v is not None]
        out[key] = {
            "kosular": values,
            "ort": statistics.fmean(have) if have else math.nan,
            "en_az": min(have) if have else math.nan,
            "en_cok": max(have) if have else math.nan,
            "n": len(have),
        }
    return out


def started(summary: dict | None) -> bool:
    """False for a run that never got going: no ozet.json, or TAMAMLANMADI before the drone was in its mode."""
    if summary is None:
        return False
    if summary.get("sonuc") != "TAMAMLANMADI":
        return True
    return any(e.startswith(READY_EVENT[0]) and READY_EVENT[1] in e for e in summary.get("olaylar", []))


def command(scenario: str, out: Path, extra: Sequence[str]) -> list[str]:
    """senaryo.py for one run: no window, into `out`, the caller's flags last. ValueError for a flag toplu.py sets."""
    own = [f for f in extra if f.split("=", 1)[0] in OWN_FLAGS]
    if own:
        raise ValueError(f"{', '.join(own)}: toplu.py bunları her koşu için kendisi verir")
    return [sys.executable, str(SCENARIO_TOOL), "--senaryo", scenario, "--ekransiz", "--cikti", str(out), *extra]


def read_summary(folder: Path) -> dict | None:
    path = folder / "ozet.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def read_runs(folders: Sequence[Path]) -> list[dict]:
    """The ozet.json of each run folder, with its folder ("klasor"); a folder without one is left out."""
    runs = []
    for folder in folders:
        s = read_summary(folder)
        if s is None:
            log(f"UYARI: {folder}/ozet.json okunamadı, özete girmedi")
            continue
        runs.append(s | {"klasor": str(folder)})
    return runs


def wait_until_closed(timeout_s: float = WAIT_FOR_EXIT_S) -> bool:
    """True once no PX4 or Gazebo runs (the previous run shut down), False if one is still there after timeout_s."""
    t_end = time.monotonic() + timeout_s
    while running():
        if time.monotonic() > t_end:
            return False
        time.sleep(2.0)
    return True


def run_all(scenario: str, repeat: int, retries: int, out: Path, extra: Sequence[str]) -> tuple[list[dict], list]:
    """Run the scenario `repeat` times (each tried again at most `retries` times if it never got going).
    -> (the runs' ozet.json, every attempt). Stops at a setting senaryo.py refuses (exit code 2: every run would)."""
    runs, attempts = [], []
    for i in range(1, repeat + 1):
        for attempt in range(1, retries + 2):
            if not wait_until_closed():
                raise RuntimeError(f"{WAIT_FOR_EXIT_S:.0f} s sonra hâlâ çalışan bir PX4 ya da Gazebo var")
            folder = out / f"kosu_{i}"
            if folder.exists():  # an earlier attempt of this run: keep it, listed under its new name
                shutil.move(str(folder), str(out / f"kosu_{i}_deneme{attempt - 1}"))
                for a in attempts:
                    if a["klasor"] == folder.name:
                        a["klasor"] = f"kosu_{i}_deneme{attempt - 1}"
            log(f"Koşu {i}/{repeat}, deneme {attempt}: {scenario} -> {folder}")
            with (out / f"kosu_{i}.log").open("a", encoding="utf-8") as f:
                code = subprocess.run(command(scenario, folder, extra), stdout=f, stderr=subprocess.STDOUT).returncode
            s = read_summary(folder)
            result = s["sonuc"] if s is not None else f"ozet yok (çıkış {code})"
            attempts.append({"kosu": i, "deneme": attempt, "klasor": folder.name, "sonuc": result, "cikis": code})
            log(f"Koşu {i}: {result}")
            if code == 2:
                raise ValueError(f"senaryo.py ayarı reddetti (çıkış 2), ayrıntı: {out / f'kosu_{i}.log'}")
            if started(s):
                runs.append(s | {"klasor": str(folder)})
                break
            log(f"Koşu {i} başlayamadı (altyapı hatası), yeniden deneniyor")
    return runs, attempts


def _fmt(value: float | None, key: str) -> str:
    return rapor._fmt(math.nan if value is None else value, key)


def plot_dots(agg: dict, runs: int) -> str:
    """Small multiples: every run as a dot, the mean as a line, for the DOT_KEYS that have values."""
    keys = [k for k in DOT_KEYS if k in agg and agg[k]["n"]]
    cols = 3
    rows = max(1, math.ceil(len(keys) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(10.5, 2.1 * rows), squeeze=False)
    colors = ("#2a78d6", "#eb6834", "#5f8f4e", "#7b3fa0", "#8b8a86")
    for ax, key in zip(axes.flat, keys, strict=False):
        rapor._style(ax)
        d = agg[key]
        scale = 100.0 if key in rapor.PERCENT_KEYS else 1.0
        for i, v in enumerate(d["kosular"]):
            if v is not None:
                ax.plot(v * scale, 0, "o", color=colors[i % len(colors)], markersize=9, alpha=0.85)
        ax.axvline(d["ort"] * scale, color=rapor.TEXT, linewidth=1.2)
        ax.set_yticks([])
        unit = " [%]" if scale == 100.0 else ""
        ax.set_title(LABELS.get(key, key)[:58] + unit, fontsize=8, loc="left", color=rapor.TEXT)
        lo, hi = d["en_az"] * scale, d["en_cok"] * scale
        pad = max(abs(hi - lo) * 0.25, abs(hi) * 0.05, 0.05)
        ax.set_xlim(lo - pad, hi + pad)
    for ax in list(axes.flat)[len(keys) :]:
        ax.axis("off")
    handles = [
        plt.Line2D([], [], marker="o", linestyle="", color=colors[i % 5], label=f"koşu {i + 1}") for i in range(runs)
    ]
    handles.append(plt.Line2D([], [], color=rapor.TEXT, label="ortalama"))
    fig.legend(handles=handles, loc="lower center", ncol=runs + 1, frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    return rapor._png(fig)


def write(out: Path, scenario: str, runs: list[dict], attempts: list[dict], extra: Sequence[str]) -> dict:
    """toplu.json, toplu.csv and toplu.html of the runs."""
    agg = aggregate(runs)
    summary = {
        "senaryo": scenario,
        "tarih": dt.datetime.now().isoformat(timespec="seconds"),
        "kosu_sayisi": len(runs),
        "bayraklar": list(extra),
        "kosular": [{"klasor": r["klasor"], "sonuc": r["sonuc"], "commit": r.get("commit")} for r in runs],
        "denemeler": attempts,
        "olcutler": agg,
    }
    (out / "toplu.json").write_text(
        json.dumps(rapor._json_safe(summary), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (out / "toplu.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["anahtar", *(f"kosu_{i}" for i in range(1, len(runs) + 1)), "ort", "en_az", "en_cok", "n"])
        for key, d in agg.items():
            w.writerow(
                [key, *("" if v is None else v for v in d["kosular"]), d["ort"], d["en_az"], d["en_cok"], d["n"]]
            )
    dots = plot_dots(agg, len(runs)) if runs else ""
    (out / "toplu.html").write_text(_html(scenario, summary, agg, dots, runs), "utf-8")
    return summary


def _corners_html(runs: Sequence[dict], agg: dict, row: Callable[[str, str], str], table: str) -> str:
    """The corners side by side: the person walks the same path in every run, so corner i is the same corner."""
    corners = next((r.get("koseler") for r in runs if r.get("koseler")), None)
    if not corners:
        return ""
    body = []
    for i, c in enumerate(corners, start=1):
        kind = rapor.CORNER_KIND.get(c.get("tur"), c.get("tur"))
        body.append(
            f"<tr><th colspan=99>Köşe {i}: {c['baslangic_s']:.1f} s, {html.escape(str(kind))}, yeni yön "
            f"{c['yon_deg']:.0f}° (0 = kuzey)</th></tr>"
        )
        body += [row(f"kose_{i}_{key}", label) for key, label in CORNER_ROWS if f"kose_{i}_{key}" in agg]
    return (
        "<h2>Köşeler (PX4'ün yeni yöne yetişmesi ve aşma)</h2><p class=muted>Köşe anı ilk koşudan; tanım spec "
        f'"Ölçüt Tanımları".</p><table>{table}{"".join(body)}</table>'
    )


def _near_passes_html(runs: Sequence[dict]) -> str:
    """Every run's < 6 m passes: a short list, the whole table (rapor.near_pass_rows) folded."""
    if not any("yakin_gecis" in r for r in runs):
        return ""
    e = html.escape
    items, rows = [], []
    for r in runs:
        name = e(Path(r["klasor"]).name)
        events = (r.get("yakin_gecis") or {}).get("olaylar", [])
        spans = "; ".join(
            f"{x['baslangic_s']:.1f}–{x['bitis_s']:.1f} s {e(rapor.NEAR_PASS_TEXT.get(x['sebep'], x['sebep']))} "
            f"(en az {x['en_az_m']:.2f} m)"
            for x in events
        )
        items.append(f"<li>{name}: {spans or 'yok'}</li>")
        rows.append(f"<tr><th colspan=99>{name}</th></tr>{rapor.near_pass_rows(events)}")
    return (
        f"<h2>Yakın geçişler (&lt; {rapor.olcum.CLOSE_PASS_M:g} m)</h2><p class=muted>Kayıt (video) penceresi: mod "
        'seçimi → senaryo sonu; sebep, sırayla ilk tutan kural (spec "Ölçüt Tanımları").</p>'
        f"<ul>{''.join(items)}</ul>"
        f"<details><summary>Ayrıştırmalarıyla</summary><table>{rapor.NEAR_PASS_HEAD}{''.join(rows)}</table>"
        f"{rapor.NEAR_PASS_NOTE}</details>"
    )


def _html(scenario: str, s: dict, agg: dict, dots: str, summaries: Sequence[dict] = ()) -> str:
    e = html.escape
    n = s["kosu_sayisi"]
    head = "".join(f"<th>koşu {i}</th>" for i in range(1, n + 1))

    def row(key: str, label: str | None = None) -> str:
        d = agg[key]
        cells = "".join(f"<td class=num>{e(_fmt(v, key))}</td>" for v in d["kosular"])
        spread = "".join(f"<td class=num><b>{e(_fmt(d[k], key))}</b></td>" for k in ("ort", "en_az", "en_cok"))
        return f"<tr><td>{e(label or LABELS.get(key, key))}<br><code>{e(key)}</code></td>{cells}{spread}</tr>"

    main = "".join(row(k) for k in MAIN_KEYS if k in agg)
    rest = "".join(row(k) for k in sorted(agg) if k not in MAIN_KEYS)
    table = f"<tr><th>Ölçüt</th>{head}<th>ort.</th><th>en az</th><th>en çok</th></tr>"
    runs = "".join(
        f"<li>{e(Path(r['klasor']).name)}: {e(r['sonuc'])} <span class=muted>({e(str(r.get('commit')))})</span> · "
        f'<a href="{e(Path(r["klasor"]).name)}/rapor.html">rapor.html</a>'
        + (
            f' · <a href="{e(Path(r["klasor"]).name)}/{VIDEO}">{VIDEO}</a>'
            if (Path(r["klasor"]) / VIDEO).is_file()
            else ""
        )
        + "</li>"
        for r in s["kosular"]
    )
    tries = "".join(
        f"<li>koşu {a['kosu']}, deneme {a['deneme']} ({e(a['klasor'])}): {e(str(a['sonuc']))}</li>"
        for a in s["denemeler"]
    )
    flags = " ".join(s["bayraklar"]) or "yok"
    img = f'<img alt="koşuların dağılımı" src="data:image/png;base64,{dots}">' if dots else ""
    return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>{e(scenario)} — {n} koşu</title>
<style>
body {{ background:{rapor.SURFACE}; color:{rapor.TEXT}; font:15px/1.5 system-ui, sans-serif; margin:0 auto;
  max-width:1000px; padding:24px 16px; }}
h1 {{ font-size:22px; }} h2 {{ font-size:17px; margin:28px 0 8px; }} .muted {{ color:{rapor.TEXT_2}; }}
table {{ border-collapse:collapse; width:100%; font-size:14px; }}
th, td {{ border-bottom:1px solid {rapor.GRID}; padding:5px 8px; text-align:left; vertical-align:top; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }} td code {{ color:{rapor.TEXT_2};
  font-size:12px; }} img {{ max-width:100%; }}
</style></head><body>
<h1>{e(scenario)} — {n} koşunun dağılımı</h1>
<p class=muted>{e(s["tarih"])} · senaryo.py bayrakları: <code>{e(flags)}</code> · her koşu kendi
<code>rapor.html</code>'inde. Değerler ölçümdür, başarı eşiği yoktur (m01).</p>
<h2>Koşular</h2><ul>{runs}</ul>
<h2>Ana ölçütler</h2><table>{table}{main}</table>
{_corners_html(summaries, agg, row, table)}
{_near_passes_html(summaries)}
<h2>Koşu koşu (nokta: koşu, çizgi: ortalama)</h2>{img}
<h2>Denemeler</h2><ul>{tries}</ul>
<details><summary>Bütün sayısal ölçütler</summary><table>{table}{rest}</table></details>
</body></html>
"""


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--senaryo", help="tez/sim/senaryolar/<ad>.yaml adı veya bir .yaml yolu")
    ap.add_argument("--tekrar", type=int, default=3, help="koşu sayısı (varsayılan 3)")
    ap.add_argument(
        "--yeniden-dene", type=int, default=2, help="başlayamayan bir koşunun en çok kaç kez yeniden denenir"
    )
    ap.add_argument("--cikti", type=Path, help="çıktı klasörü (varsayılan tez/sim/sonuclar/<tarih>_<ad>_x<N>)")
    ap.add_argument(
        "--ozet", type=Path, nargs="+", metavar="KLASÖR", help="koşmadan, var olan koşu klasörlerini özetle"
    )
    ap.add_argument("senaryo_bayraklari", nargs="*", help="-- işaretinden sonra: her koşuda senaryo.py'ye verilir")
    return ap


def main() -> int:
    args = parser().parse_args()
    if args.ozet:
        runs = read_runs(args.ozet)
        if not runs:
            print("Okunabilen ozet.json yok", file=sys.stderr)
            return 2
        out = args.cikti or SIM_DIR / "sonuclar" / f"{dt.datetime.now():%Y%m%d_%H%M%S}_toplu_ozet"
        out.mkdir(parents=True, exist_ok=True)
        write(out, runs[0]["senaryo"], runs, [], [])
        log(f"Özet: {out / 'toplu.html'}")
        return 0
    if not args.senaryo or args.tekrar < 1:
        print("--senaryo ve --tekrar >= 1 gerekli (ya da --ozet)", file=sys.stderr)
        return 2
    extra = list(args.senaryo_bayraklari)
    try:
        command(args.senaryo, Path("."), extra)
    except ValueError as e:
        print(f"Bayrak hatası: {e}", file=sys.stderr)
        return 2
    name = Path(args.senaryo).stem
    out = args.cikti or SIM_DIR / "sonuclar" / f"{dt.datetime.now():%Y%m%d_%H%M%S}_{name}_x{args.tekrar}"
    out.mkdir(parents=True, exist_ok=True)
    try:
        runs, attempts = run_all(args.senaryo, args.tekrar, args.yeniden_dene, out, extra)
    except (ValueError, RuntimeError) as e:
        print(f"Durdu: {e}", file=sys.stderr)
        return 2
    summary = write(out, name, runs, attempts, extra)
    for key in ("yatay_mesafe_ort_m", "en_az_yatay_mesafe_m", "arkada_kalma_hatasi_ort_deg", "rtf_ort"):
        d = summary["olcutler"].get(key)
        if d:
            log(f"{key}: ort. {d['ort']:.2f}, en az {d['en_az']:.2f}, en çok {d['en_cok']:.2f} ({d['n']} koşu)")
    log(f"{len(runs)}/{args.tekrar} koşu tamamlandı ({len(attempts)} deneme); özet: {out / 'toplu.html'}")
    return 0 if len(runs) == args.tekrar else 1


if __name__ == "__main__":
    sys.exit(main())
