"""karsilastir.py (tasks.md 12.3): the ozet.json of runs (and of toplu.py folders) side by side, metrics and settings,
from hand-made files; no simulation."""

import json
from pathlib import Path

import pytest

import karsilastir


def run_folder(folder: Path, delay_ms: float, end_to_end_ms: float, **more: object) -> Path:
    """A run folder with a small ozet.json (the keys senaryo.py writes, a few metrics)."""
    folder.mkdir(parents=True)
    summary = {
        "senaryo": "takip_yuruyen",
        "sonuc": more.pop("sonuc", "GEÇTİ"),
        "tarih": "2026-11-15T10:00:00",
        "commit": "29bdb0d8d3",
        "ayarlar": {
            "takip": {"kaynak": "follow_me", "mod": "Follow Target", "los": "model", "px4_modlari": ["Hold", "Land"]}
            | {"yeniden_kilit_bekleme_s": more.pop("relock_s", 0.0)},
            "algilama": {"etkin": True, "model_bilgisi": {"imgsz": 640, "isinma_ms": 1000.0 + end_to_end_ms}},
            "gecikme": {"ek_ms": delay_ms, "titresim_ms": 0.0, "saat_ofset_ms": 0.0, "saat_kayma_ppm": 0.0},
            "kusurlar": {},
            "kamera": {"egim_deg": 35.0, "gazebo_modeli": f"{folder}/x500_tez/model.sdf"},
            "px4_parametreleri": {"FLW_TGT_DST": {"deger": 12.9, "kaynak": "senaryo", "px4": 12.9}},
        },
        "olcutler": {
            "uctan_uca_ms_ort": end_to_end_ms,
            "ek_gecikme_ms_ort": delay_ms + 0.02,
            "algilama_orani": more.pop("found", 0.62),
            "kilit_kaybi_sayisi": 2,
            "rtf_ort": None,
            "konum_durumlari": {"hesaplandi": 10},
        },
    }
    (folder / "ozet.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    return folder


def row(text: str, key: str) -> list[str]:
    """The cells of one row of the terminal table (split on two or more spaces)."""
    line = next(t for t in text.splitlines() if t.split("  ")[0].strip() == key)
    return [c.strip() for c in line.split("  ") if c.strip()]


def test_two_runs_and_a_toplu_folder_side_by_side(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Every column's value, its difference to the first (ratios in points), the settings that differ (and the delay
    settings always), a toplu.py folder as the mean of its runs with their range; numbers of the run that are not
    settings (the model's warm-up, the run's own model path) are not listed as settings."""
    a = run_folder(tmp_path / "gecikme0", 0.0, 120.0)
    (a / "rapor.html").write_text("<html></html>", encoding="utf-8")
    b = run_folder(tmp_path / "gecikme200", 200.0, 321.5, found=0.55)
    group = tmp_path / "eski_x2"
    run_folder(group / "kosu_1", 0.0, 130.0, relock_s=0.0)
    run_folder(group / "kosu_2", 0.0, 140.0, relock_s=1.5, sonuc="KALDI")
    listed = [{"klasor": f"tez/sim/sonuclar/eski_x2/kosu_{i}", "sonuc": "GEÇTİ"} for i in (1, 2)]
    (group / "toplu.json").write_text(json.dumps({"kosular": listed}), encoding="utf-8")

    html_file = tmp_path / "k" / "karsilastirma.html"
    assert karsilastir.main([str(a), str(b), str(group), "--html", str(html_file)]) == 0
    text = capsys.readouterr().out
    assert row(text, "")[:3] == ["gecikme0", "gecikme200", "eski_x2 (ort. 2 koşu)"]
    assert row(text, "uctan_uca_ms_ort") == ["uctan_uca_ms_ort", "120.00", "321.50", "135.00 (130.00–140.00)"] + [
        "+201.50",
        "+15.00",
    ]
    assert row(text, "algilama_orani")[1:] == ["%62.0", "%55.0", "%62.0", "-7.0 puan", "+0.0 puan"]
    assert row(text, "sonuc")[1:] == ["GEÇTİ", "GEÇTİ", "GEÇTİ 1/2 (GEÇTİ, KALDI)"]
    assert row(text, "gecikme.ek_ms")[1:] == ["0", "200", "0"]
    assert row(text, "takip.yeniden_kilit_bekleme_s")[1:] == ["0", "0", "farklı: 0 / 1.5"]
    assert "rtf_ort" not in text  # no column has a value
    assert "isinma_ms" not in text and "gazebo_modeli" not in text  # numbers of the run, not settings
    assert "px4_parametreleri.FLW_TGT_DST" not in text  # the same everywhere: only with --hepsi

    page = html_file.read_text(encoding="utf-8")
    assert "Uçtan uca gecikme (yakalama → gönderim), ortalama [sim ms]" in page and "+201.50" in page
    assert (a / "rapor.html").resolve().as_uri() in page and "kosu_2: KALDI" in page

    assert karsilastir.main([str(a), str(b), "--hepsi"]) == 0
    everything = capsys.readouterr().out
    assert row(everything, "px4_parametreleri.FLW_TGT_DST")[1:] == ["12.9", "12.9"]
    assert row(everything, "kilit_kaybi_sayisi")[1:] == ["2.00", "2.00", "+0.00"]

    empty = tmp_path / "bos"
    empty.mkdir()
    assert karsilastir.main([str(a), str(empty)]) == 2
    assert "ozet.json (tek koşu) ya da toplu.json (toplu.py) yok" in capsys.readouterr().err
