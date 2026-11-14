#!/usr/bin/env python3
"""Put runs side by side: the metrics (ozet.json "olcutler") and the settings ("ayarlar") of several runs in one table
(spec 2026-11-10-m06-sim-ortami, 6.; tasks.md 12.3).

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/karsilastir.py <klasör A> <klasör B> ...
    ... --hepsi             every numeric metric and every setting (default: the main metrics, the settings that
                            differ and the delay / tracking settings)
    ... --html K.html       the same tables in one HTML file, with links to every run's rapor.html and kosu.mp4

A folder is either one run (it holds ozet.json: senaryo.py --cikti, or a kosu_<i>/ of toplu.py) or a toplu.py folder
(it holds toplu.json): its column is the mean of its runs, the lowest and the highest in brackets (toplu.aggregate),
and its settings are those of its runs ("farklı: ..." where they differ). Every column after the first also gets its
difference to the first (Δ; ratios in percentage points). Values are measurements, there is no pass threshold (m01).
"""

import argparse
import html
import json
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import rapor
import toplu

# Shown first: the capture -> PX4 latency (task group 12's question: does the measured delay follow the setting?)
TIME_KEYS = (
    "uctan_uca_ms_ort",
    "uctan_uca_ms_p50",
    "uctan_uca_ms_p95",
    "uctan_uca_ms_maks",
    "ek_gecikme_ms_ort",
    "ek_gecikme_ms_maks",
    "hazir_ms_ort",
    "uctan_uca_px4_ms_ort",
    "uctan_uca_px4_ms_p95",
    "follow_target_uctan_uca_ms_ort",
)
MAIN_KEYS = TIME_KEYS + tuple(k for k in toplu.MAIN_KEYS if k not in TIME_KEYS)
# Settings shown even when every column has the same value: the ones a comparison is usually about
ALWAYS_SETTINGS = (
    "takip.kaynak",
    "takip.los",
    "takip.yeniden_kilit_bekleme_s",
    "gecikme.ek_ms",
    "gecikme.titresim_ms",
    "gecikme.saat_ofset_ms",
    "gecikme.saat_kayma_ppm",
    "kamera.egim_deg",
    "algilama.model_dosyasi.sha256",
)
# Not settings but numbers of the run (they differ between two runs of the same settings) or run-specific paths
SKIP_SETTINGS = (
    "algilama.model_bilgisi.isinma_ms",
    "algilama.model_bilgisi.pid",
    "kamera.gazebo_modeli",
)
TEXT_WIDTH = 40  # [characters] longer setting values are cut in the terminal table (the HTML keeps them whole)


@dataclass
class Column:
    """One column of the table: one run, or the runs of one toplu.py folder."""

    folder: Path
    run_folders: list[Path]  # the folder of every run (the column's folder itself for one run)
    runs: list[dict]  # ozet.json of every run, in the order of run_folders
    metrics: dict  # toplu.aggregate: {key: {kosular, ort, en_az, en_cok, n}}
    settings: dict[str, str]  # flattened "ayarlar" (block.key -> text), "farklı: ..." where the runs differ

    @property
    def name(self) -> str:
        return self.folder.name

    @property
    def grouped(self) -> bool:
        return len(self.runs) > 1


def flatten(settings: dict, prefix: str = "") -> dict[str, str]:
    """ozet.json "ayarlar" -> {"takip.kaynak": "follow_me", ...}: nested blocks joined with dots, lists joined with
    commas, a PX4 start parameter as its value (px4_parametreleri.<NAME>), SKIP_SETTINGS left out."""
    out: dict[str, str] = {}
    for key, value in settings.items():
        name = f"{prefix}{key}"
        if name in SKIP_SETTINGS:
            continue
        if prefix == "px4_parametreleri." and isinstance(value, dict):
            out[name] = _text(value.get("deger"))
        elif isinstance(value, dict) and value:
            out |= flatten(value, f"{name}.")
        else:
            out[name] = _text(value)
    return out


def _text(value: object) -> str:
    if value is None:
        return "–"
    if isinstance(value, list | tuple):
        return ", ".join(_text(v) for v in value) or "–"
    if isinstance(value, dict):
        return "–"  # an empty block (kusurlar: {})
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _merge(runs: Sequence[dict]) -> dict[str, str]:
    """The settings of the runs of one column: one value where they agree, 'farklı: a / b' where they do not."""
    flat = [flatten(r.get("ayarlar") or {}) for r in runs]
    keys: list[str] = []
    for f in flat:
        keys += [k for k in f if k not in keys]
    merged = {}
    for key in keys:
        values = [f.get(key, "–") for f in flat]
        distinct = list(dict.fromkeys(values))
        merged[key] = distinct[0] if len(distinct) == 1 else "farklı: " + " / ".join(distinct)
    return merged


def load(folder: Path) -> Column:
    """The column of a run folder (ozet.json) or of a toplu.py folder (toplu.json and its runs' ozet.json).
    ValueError if the folder holds neither or none of its runs can be read."""
    if (folder / "ozet.json").is_file():
        summary = toplu.read_summary(folder)
        if summary is None:
            raise ValueError(f"{folder}/ozet.json okunamadı")
        folders, runs = [folder], [summary]
    elif (folder / "toplu.json").is_file():
        try:
            listed = json.loads((folder / "toplu.json").read_text(encoding="utf-8"))["kosular"]
        except (OSError, ValueError, KeyError) as e:
            raise ValueError(f"{folder}/toplu.json okunamadı: {e}") from e
        # toplu.py writes the run folders as it was given them; the runs are its subfolders of the same name
        found = [(f, toplu.read_summary(f)) for f in (folder / Path(r["klasor"]).name for r in listed)]
        folders, runs = [f for f, s in found if s is not None], [s for _, s in found if s is not None]
        if not runs:
            raise ValueError(f"{folder}: toplu.json'daki koşuların hiçbirinin ozet.json'u okunamadı")
    else:
        raise ValueError(f"{folder}: ozet.json (tek koşu) ya da toplu.json (toplu.py) yok")
    return Column(folder, folders, runs, toplu.aggregate(runs), _merge(runs))


def metric_keys(columns: Sequence[Column], everything: bool) -> list[str]:
    """The metric rows: MAIN_KEYS that any column has; with `everything` also every other numeric one, sorted."""
    have = {k for c in columns for k, d in c.metrics.items() if d["n"]}
    keys = [k for k in MAIN_KEYS if k in have]
    if everything:
        keys += sorted(have - set(keys))
    return keys


def setting_keys(columns: Sequence[Column], everything: bool) -> list[str]:
    """The settings rows: ALWAYS_SETTINGS, then the ones whose value differs between the columns (or every one)."""
    keys: list[str] = []
    for c in columns:
        keys += [k for k in c.settings if k not in keys]
    shown = [k for k in ALWAYS_SETTINGS if k in keys]
    for key in keys:
        if key in shown:
            continue
        values = {c.settings.get(key, "–") for c in columns}
        if everything or len(values) > 1 or any(v.startswith("farklı: ") for v in values):
            shown.append(key)
    return shown


def cell(column: Column, key: str) -> str:
    """A metric of a column: the run's value, or the mean of the runs with the lowest and the highest."""
    d = column.metrics.get(key)
    if d is None or not d["n"]:
        return "–"
    text = rapor._fmt(d["ort"], key)
    if column.grouped and d["en_az"] != d["en_cok"]:
        text += f" ({rapor._fmt(d['en_az'], key)}–{rapor._fmt(d['en_cok'], key)})"
    return text


def difference(column: Column, first: Column, key: str) -> str:
    """column − first of a metric's means; ratios in percentage points."""
    a, b = first.metrics.get(key), column.metrics.get(key)
    if a is None or b is None or not a["n"] or not b["n"]:
        return "–"
    delta = b["ort"] - a["ort"]
    if not math.isfinite(delta):
        return "–"
    return f"{100 * delta:+.1f} puan" if key in rapor.PERCENT_KEYS else f"{delta:+.2f}"


def header(column: Column) -> str:
    return f"{column.name} (ort. {len(column.runs)} koşu)" if column.grouped else column.name


def identity(column: Column) -> dict[str, str]:
    """The rows above the settings: scenario, result, commit, date of the column's runs."""
    runs = column.runs
    results = [str(r.get("sonuc")) for r in runs]
    result = results[0]
    if len(runs) > 1:
        passed = results.count("GEÇTİ")
        result = f"GEÇTİ {passed}/{len(runs)}" + ("" if passed == len(runs) else f" ({', '.join(results)})")
    return {
        "senaryo": " / ".join(dict.fromkeys(str(r.get("senaryo")) for r in runs)),
        "sonuc": result,
        "commit": " / ".join(dict.fromkeys(str(r.get("commit")) for r in runs)),
        "tarih": " … ".join(dict.fromkeys(str(r.get("tarih")) for r in (runs[0], runs[-1]))),
        "kosu_sayisi": str(len(runs)),
    }


def rows(columns: Sequence[Column], everything: bool) -> tuple[list[list[str]], list[list[str]], list[list[str]]]:
    """(identity, settings, metrics) rows: [key, value of every column, Δ of every column after the first]."""
    first = columns[0]
    ident = [[k, *(identity(c)[k] for c in columns)] for k in identity(first)]
    settings = [[k, *(c.settings.get(k, "–") for c in columns)] for k in setting_keys(columns, everything)]
    metrics = [
        [k, *(cell(c, k) for c in columns), *(difference(c, first, k) for c in columns[1:])]
        for k in metric_keys(columns, everything)
    ]
    return ident, settings, metrics


def _short(text: str) -> str:
    return text if len(text) <= TEXT_WIDTH else text[: TEXT_WIDTH - 1] + "…"


def text_table(columns: Sequence[Column], everything: bool = False) -> str:
    """The terminal table."""
    ident, settings, metrics = rows(columns, everything)
    deltas = [f"Δ {i + 1}−1" for i in range(1, len(columns))]
    head = ["", *(header(c) for c in columns), *deltas]
    sections = [("Koşu", ident), ("Ayarlar (ayarlar)", settings), ("Ölçütler (olcutler)", metrics)]
    body = [[_short(v) for v in r] for _, part in sections for r in part]
    widths = [max(len(r[i]) if i < len(r) else 0 for r in [head, *body]) for i in range(len(head))]

    def line(values: Sequence[str]) -> str:
        cells = [values[0].ljust(widths[0])]
        cells += [v.rjust(widths[i + 1]) for i, v in enumerate(values[1:])]
        return "  ".join(cells).rstrip()

    out = [line(head)]
    for title, part in sections:
        out.append("")
        out.append(f"— {title}")
        out += [line([_short(v) for v in r]) for r in part]
    return "\n".join(out)


def html_page(columns: Sequence[Column], everything: bool = False) -> str:
    """The same tables as one self-contained HTML page (the style of toplu.html)."""
    e = html.escape
    ident, settings, metrics = rows(columns, everything)
    deltas = "".join(f"<th>Δ {i + 1}−1</th>" for i in range(1, len(columns)))
    head = "".join(f"<th>{e(header(c))}</th>" for c in columns)

    def body(part: list[list[str]], labels: bool) -> str:
        out = []
        for key, *values in part:
            label = f"<code>{e(key)}</code>"
            if labels and key in toplu.LABELS:
                label = f"{e(toplu.LABELS[key])}<br>{label}"
            out.append(f"<tr><td>{label}</td>" + "".join(f"<td class=num>{e(v)}</td>" for v in values) + "</tr>")
        return "".join(out)

    links = []
    for i, c in enumerate(columns, start=1):
        items = []
        for folder, run in zip(c.run_folders, c.runs, strict=True):
            files = [
                f'<a href="{(folder / name).resolve().as_uri()}">{name}</a>'
                for name in ("rapor.html", toplu.VIDEO)
                if (folder / name).is_file()
            ]
            items.append(f"<li>{e(folder.name)}: {e(str(run.get('sonuc')))} · {' · '.join(files) or '–'}</li>")
        title = f"<b>{i}. {e(header(c))}</b> <span class=muted>({e(str(c.folder))})</span>"
        links.append(f"<li>{title}<ul>{''.join(items)}</ul></li>")
    table = f"<tr><th></th>{head}{deltas}</tr>"
    return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>Koşuların karşılaştırması</title>
<style>
body {{ background:{rapor.SURFACE}; color:{rapor.TEXT}; font:15px/1.5 system-ui, sans-serif; margin:0 auto;
  max-width:1200px; padding:24px 16px; }}
h1 {{ font-size:22px; }} h2 {{ font-size:17px; margin:28px 0 8px; }} .muted {{ color:{rapor.TEXT_2}; }}
table {{ border-collapse:collapse; width:100%; font-size:14px; }}
th, td {{ border-bottom:1px solid {rapor.GRID}; padding:5px 8px; text-align:left; vertical-align:top; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; }} td code {{ color:{rapor.TEXT_2}; font-size:12px; }}
</style></head><body>
<h1>Koşuların karşılaştırması ({len(columns)} sütun)</h1>
<p class=muted>Toplu sütunlarda değer koşuların ortalaması, parantezde en az–en çok. Δ: sütunun ilk sütundan farkı
(oranlarda yüzde puan). Değerler ölçümdür, başarı eşiği yoktur (m01).</p>
<h2>Koşular</h2><ul>{"".join(links)}</ul>
<h2>Koşu</h2><table>{table}{body(ident, False)}</table>
<h2>Ayarlar</h2><table>{table}{body(settings, False)}</table>
<h2>Ölçütler</h2><table>{table}{body(metrics, True)}</table>
</body></html>
"""


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("klasorler", type=Path, nargs="+", metavar="KLASÖR", help="koşu ya da toplu.py klasörü")
    ap.add_argument("--hepsi", action="store_true", help="bütün sayısal ölçütler ve bütün ayarlar")
    ap.add_argument("--html", type=Path, metavar="DOSYA", help="tabloları bu HTML dosyasına da yaz")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        columns = [load(folder) for folder in args.klasorler]
    except ValueError as e:
        print(f"Karşılaştırılamadı: {e}", file=sys.stderr)
        return 2
    print(text_table(columns, args.hepsi))
    if args.html is not None:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(html_page(columns, args.hepsi), encoding="utf-8")
        print(f"\nHTML: {args.html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
