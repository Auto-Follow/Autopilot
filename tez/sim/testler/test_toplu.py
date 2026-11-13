"""Several runs of one scenario (toplu.py, decision 4 of 12.11): the spread of every metric, which runs are tried
again, and the senaryo.py command; no simulation."""

import json
import math
from pathlib import Path

import pytest

import toplu


def summary(sonuc: str, events: list[str], **metrics: object) -> dict:
    return {"senaryo": "takip_yuruyen", "sonuc": sonuc, "olaylar": events, "olcutler": metrics}


READY = "Dron 25.0 s'de hazır (Follow Target, 8 m)"


def test_spread_of_every_metric_over_the_runs() -> None:
    """Per metric: every run's value, the mean, the lowest and the highest of the runs that have one (null = NaN in
    ozet.json); counts, dicts and text are not averaged."""
    runs = [
        summary("GEÇTİ", [READY], yatay_mesafe_ort_m=7.6, en_az_yatay_mesafe_m=0.86, algilama_orani=None, kilit=3),
        summary("GEÇTİ", [READY], yatay_mesafe_ort_m=8.2, en_az_yatay_mesafe_m=4.46, algilama_orani=0.7, kilit=1),
        summary("KALDI", [READY], yatay_mesafe_ort_m=7.0, en_az_yatay_mesafe_m=2.40, algilama_orani=0.5, kilit=2),
    ]
    runs[0]["olcutler"]["konum_durumlari"] = {"hesaplandi": 3}
    agg = toplu.aggregate(runs)
    d = agg["yatay_mesafe_ort_m"]
    assert d["kosular"] == [7.6, 8.2, 7.0] and d["n"] == 3
    assert (d["ort"], d["en_az"], d["en_cok"]) == (pytest.approx(7.6), 7.0, 8.2)
    a = agg["algilama_orani"]
    assert a["kosular"][0] is None and a["n"] == 2 and a["ort"] == pytest.approx(0.6)
    assert agg["kilit"]["ort"] == pytest.approx(2.0)
    assert "konum_durumlari" not in agg
    nothing = toplu.aggregate([summary("GEÇTİ", [READY], x=None)])["x"]
    assert nothing["n"] == 0 and math.isnan(nothing["ort"])


def test_only_a_run_that_never_got_going_is_tried_again() -> None:
    """No ozet.json, or TAMAMLANMADI before the drone was ready (e.g. no heartbeat from PX4): infrastructure, tried
    again. A run that flew and then failed is a result and counts."""
    assert not toplu.started(None)
    assert not toplu.started(summary("TAMAMLANMADI", ["Beklenmeyen hata: RuntimeError: PX4'ten heartbeat gelmedi"]))
    assert toplu.started(summary("TAMAMLANMADI", [READY, "80.0 s: model süreci durdu: ..."]))
    assert toplu.started(summary("KALDI", [READY])) and toplu.started(summary("GEÇTİ", [READY]))


def test_senaryo_command_runs_without_a_window_into_the_run_folder(tmp_path: Path) -> None:
    cmd = toplu.command("takip_yuruyen", tmp_path / "kosu_1", ["--los", "hakem", "--param", "FLW_TGT_RS=0.2"])
    assert cmd[1].endswith("senaryo.py") and cmd[2:4] == ["--senaryo", "takip_yuruyen"]
    assert "--ekransiz" in cmd and cmd[cmd.index("--cikti") + 1] == str(tmp_path / "kosu_1")
    assert cmd[-4:] == ["--los", "hakem", "--param", "FLW_TGT_RS=0.2"]
    for own in (["--cikti", "x"], ["--ekransiz"]):
        with pytest.raises(ValueError):
            toplu.command("takip_yuruyen", tmp_path, own)


def test_summary_files_of_the_runs(tmp_path: Path) -> None:
    """toplu.json (every metric's spread and the attempts), toplu.csv (one row per metric) and toplu.html with the
    main table and a link to every run's kosu.mp4 (task group 8); the run folders' ozet.json are read back (--ozet)."""
    for i, value in enumerate((7.6, 8.2, 7.0), start=1):
        folder = tmp_path / f"kosu_{i}"
        folder.mkdir()
        s = summary("GEÇTİ", [READY], yatay_mesafe_ort_m=value, en_az_yatay_mesafe_m=value - 5, rtf_ort=0.9)
        (folder / "ozet.json").write_text(json.dumps(s), encoding="utf-8")
        if i < 3:  # the third run made no video (--videosuz)
            (folder / "kosu.mp4").write_bytes(b"mp4")
    runs = toplu.read_runs([tmp_path / f"kosu_{i}" for i in (1, 2, 3)])
    attempts = [{"kosu": i, "deneme": 1, "klasor": f"kosu_{i}", "sonuc": "GEÇTİ"} for i in (1, 2, 3)]
    toplu.write(tmp_path, "takip_yuruyen", runs, attempts, [])
    saved = json.loads((tmp_path / "toplu.json").read_text(encoding="utf-8"))
    assert saved["kosu_sayisi"] == 3 and saved["olcutler"]["yatay_mesafe_ort_m"]["en_cok"] == 8.2
    assert saved["denemeler"] == attempts
    csv_text = (tmp_path / "toplu.csv").read_text(encoding="utf-8").splitlines()
    assert csv_text[0].startswith("anahtar,") and any(line.startswith("yatay_mesafe_ort_m,") for line in csv_text)
    page = (tmp_path / "toplu.html").read_text(encoding="utf-8")
    assert "Dron–hedef yatay mesafe, ortalama [m]" in page and "8.20" in page and "data:image/png;base64" in page
    assert 'href="kosu_1/kosu.mp4"' in page and 'href="kosu_2/kosu.mp4"' in page and "kosu_3/kosu.mp4" not in page
