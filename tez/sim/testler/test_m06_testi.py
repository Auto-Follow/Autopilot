"""m06 acceptance test (m06_testi.py, tasks.md 13.1): the ozet.json key check and the TEZ_LOS count within ±5 %, from
hand-made summaries; no simulation."""

from pathlib import Path

import m06_testi
import olcum


def summary_with(metrics: dict) -> dict:
    return {"senaryo": "takip_yuruyen", "sonuc": "GEÇTİ", "olcutler": metrics}


def test_ozet_json_has_every_key_of_the_metric_definitions(tmp_path: Path) -> None:
    """Condition 6: every key of spec "Ölçüt Tanımları" (olcum.KEYS) is in ozet.json "olcutler", null allowed (NaN in
    the run, e.g. geolocation in a "yok" run); a missing key is named; rapor.html must be written."""
    report = tmp_path / "rapor.html"
    report.write_text("<html></html>", encoding="utf-8")
    every = dict.fromkeys(olcum.KEYS, 1.0) | {"geolocation_hatasi_ort_m": None, "kose_sayisi": None}
    ok, detail = m06_testi.keys_check(summary_with(every), report)
    assert ok, detail
    assert f"{len(olcum.KEYS)}/{len(olcum.KEYS)}" in detail and "2 tanesi null" in detail
    assert m06_testi.missing_keys(summary_with(every | {"fazla_anahtar": 3})) == []  # more keys are fine

    some_gone = {k: v for k, v in every.items() if k not in ("tez_los_px4_sayisi", "mod_korunma_orani")}
    assert m06_testi.missing_keys(summary_with(some_gone)) == ["tez_los_px4_sayisi", "mod_korunma_orani"]
    ok, detail = m06_testi.keys_check(summary_with(some_gone), report)
    assert not ok and "tez_los_px4_sayisi" in detail and "mod_korunma_orani" in detail

    assert m06_testi.missing_keys({"sonuc": "TAMAMLANMADI"}) == list(olcum.KEYS)  # no "olcutler" at all
    report.unlink()
    ok, detail = m06_testi.keys_check(summary_with(every), report)
    assert not ok and "rapor.html" in detail


def test_tez_los_in_the_ulog_is_the_sent_count_within_five_percent() -> None:
    """Condition 3: PX4 logged (ULog debug_vect "TEZ_LOS") as many as were sent in the window, ±5 % of the sent count;
    none sent or none logged fails, whatever the other number."""
    for sent, logged in [(333, 333), (100, 95), (100, 105), (892, 850)]:
        ok, detail = m06_testi.tez_los_count(sent, logged)
        assert ok, (sent, logged, detail)
        assert f"ULog'da {logged}" in detail and f"gönderilen {sent}" in detail
    for sent, logged in [(100, 94), (100, 106), (333, 316), (892, 0)]:
        ok, detail = m06_testi.tez_los_count(sent, logged)
        assert not ok, (sent, logged, detail)
    assert "TEZ_LOS adlı debug_vect yok" in m06_testi.tez_los_count(892, 0)[1]
    for sent, logged in [(0, 0), (None, 12), (0, 5)]:  # null in ozet.json: the window had no TEZ_LOS
        ok, detail = m06_testi.tez_los_count(sent, logged)
        assert not ok and "gönderilmedi" in detail
    assert not m06_testi.tez_los_count(100, None)[0]

    ok, detail = m06_testi.tez_los_check(summary_with({"tez_los_gonderilen": 387, "tez_los_px4_sayisi": 387}))
    assert ok and "387" in detail
    assert not m06_testi.tez_los_check(summary_with({}))[0]
