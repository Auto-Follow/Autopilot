"""Report metrics and success thresholds on a synthetic recording."""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import dogrulama
import hedef
import kamera
import olcum
import rapor
import yuruyus


def scenario(success: dict) -> hedef.Scenario:
    """Walks east 10 m from 60 s (ideal motion: exactly 70 s at the end)."""
    sc = hedef.Scenario("t", "", "duz_alan", 10.0, (10.0, 0.0), 60.0, 5.0, success=success)
    sc.track, sc.walk_end = yuruyus.plan(sc.start, 60.0, [("move", (20.0, 0.0), 1.0)], yuruyus.Behaviour(natural=False))
    return sc


def recording() -> pd.DataFrame:
    """30 fps from 50 s to 75 s; the target is out of view between 64 s and 66 s."""
    t = np.arange(50.0, 75.0, 1 / 30)
    seen = ~((t >= 64.0) & (t < 66.0))
    return pd.DataFrame(
        {"t": t, "kadrajda": seen, "yatay_mesafe": 10.0 + 0.1 * (t - 50), "dron_x": 0.0, "dron_y": 0.0, "dron_z": 10.0}
    )


def test_metrics() -> None:
    m = rapor.metrics(scenario({}), recording())
    assert m["kadrajda_kalma"] == pytest.approx(13 / 15, abs=0.01)  # 2 s lost out of 60..75 s
    assert m["en_uzun_kayip_s"] == pytest.approx(2.0, abs=0.05)
    assert m["yatay_mesafe_max_m"] == pytest.approx(12.5, abs=0.01)


def test_success_thresholds() -> None:
    sc = scenario({"kadrajda_kalma_min": 0.9, "en_uzun_kayip_max_s": 3, "yatay_mesafe_max_m": 15})
    result = {k: ok for k, _, _, _, ok in rapor.evaluate(sc, rapor.metrics(sc, recording()))}
    assert result == {"kadrajda_kalma_min": False, "en_uzun_kayip_max_s": True, "yatay_mesafe_max_m": True}


def test_missing_metric_fails_the_threshold() -> None:
    [(_, _, _, value, ok)] = rapor.evaluate(scenario({"en_uzun_kayip_max_s": 3}), {})
    assert math.isnan(value) and not ok


def test_json_has_no_nan() -> None:
    assert rapor._json_safe({"a": math.nan, "b": [1.0, math.nan]}) == {"a": None, "b": [1.0, None]}


def test_overhead_check_verdict() -> None:
    assert dogrulama.passed([]) is None
    assert dogrulama.passed([{"fark": 0.1}, {"fark": 0.2}])
    assert not dogrulama.passed([{"fark": 0.1}, {"fark": math.nan}])
    assert not dogrulama.passed([{"fark": 0.5}])
    # hidden under a tree: skipped, but the target must be seen at half of the check times at least
    hidden = {"fark": math.nan, "ortulu": True}
    assert dogrulama.passed([{"fark": 0.1}, hidden])
    assert not dogrulama.passed([{"fark": 0.1}, hidden, hidden])


def test_checks_warn_below_3_m_and_say_whether_the_model_ran() -> None:
    """Decision 3 (12.11): every time the drone came closer than 3 m to the target is a warning and an event (a
    measurement for m01, not a success threshold); the IoU check of task group 4 says the model ran on the image."""
    near = [
        {"baslangic_s": 70.0, "bitis_s": 71.0, "en_az_m": 2.0, "en_az_t_s": 70.4},
        {"baslangic_s": 80.0, "bitis_s": 80.5, "en_az_m": 0.86, "en_az_t_s": 80.2},
    ]
    m = {"iou05_kare_sayisi": 237, "hedef_gorunur_islenen": 325, "iou_max": 0.94, "yakin_mesafe_3m_suresi_s": 1.5}
    m |= {"kadraj_yakin_sinir_alti_s": 2.3, "kadraj_yakin_sinir_m": 3.87, "mod_korunma_orani": 1.0, "rtf_ort": 0.85}
    checks = {c["ad"]: c for c in rapor.checks(m, {"yakin_mesafe": {"olaylar": near}}, model_ran=True)}
    assert checks["model"]["durum"] == "tamam" and "325 işlenmiş karenin 237" in checks["model"]["metin"]
    warn = checks["yakin_mesafe"]
    assert warn["durum"] == "uyari" and warn["olay"] and "2 kez" in warn["metin"] and "0.86 m (80.2 s)" in warn["metin"]
    assert "başarı eşiği değildir" in warn["metin"]
    assert checks["kadraj_yakin_siniri"]["durum"] == "uyari" and checks["rtf"]["durum"] == "uyari"
    assert "mod" not in checks  # kept the whole window
    none = rapor.checks({"iou05_kare_sayisi": 0, "en_az_yatay_mesafe_m": 7.2}, {}, model_ran=True)
    assert [(c["ad"], c["durum"], c["olay"]) for c in none] == [
        ("model", "hata", True),
        ("yakin_mesafe", "tamam", False),
    ]
    assert rapor.checks({}, {}, model_ran=False) == []


def test_report_has_every_key_the_new_sections_and_the_warning_event(tmp_path: Path) -> None:
    """ozet.json gets every key of olcum.KEYS (null where it does not apply), the checks and the 3 m event; rapor.html
    shows the checks, the grouped metrics, the settings and the tracking plot."""
    sc = scenario({})
    rows = [
        r
        | {"kamera_z": 8.0, "hedef_x": 10.0, "hedef_y": 0.0, "hedef_yaw": 0.0, "hedef_hiz": 0.0, "ayak_gorunur": True}
        | {"bas_gorunur": True, "gorunur": True, "hedef_piksel": 900.0, "merkez_u": 1152.0, "merkez_v": 648.0}
        for r in recording().to_dict("records")
    ]
    cam = kamera.Camera(2304, 1296, 1773.9, 1773.9, 1152.0, 648.0)
    near = [{"baslangic_s": 64.0, "bitis_s": 65.0, "en_az_m": 2.5, "en_az_t_s": 64.5}]
    settings = {"takip": {"kaynak": "yok", "mod": "Hold", "los": None}, "algilama": {"etkin": False}, "gecikme": {}}
    settings["px4_parametreleri"] = {"FLW_TGT_DST": {"deger": 8, "kaynak": "gercek_dron.params:24", "px4": 8.0}}
    summary = rapor.write(
        tmp_path,
        sc,
        rows,
        ["Dron 25.0 s'de hazır (Hold, 10 m)"],
        True,
        [],
        cam.as_dict(),
        None,
        None,
        settings,
        {"en_az_yatay_mesafe_m": 2.5, "yakin_mesafe_3m_suresi_s": 1.0},
        {"yakin_mesafe": {"esik_m": 3.0, "olaylar": near}},
    )
    saved = json.loads((tmp_path / "ozet.json").read_text(encoding="utf-8"))
    assert set(olcum.KEYS) <= set(saved["olcutler"]) and saved["olcutler"]["algilama_orani"] is None
    assert saved["kontroller"][0]["ad"] == "yakin_mesafe" and any("3 m altına indi" in e for e in saved["olaylar"])
    assert summary["sonuc"] == "GEÇTİ"  # a warning is no threshold
    page = (tmp_path / "rapor.html").read_text(encoding="utf-8")
    for part in (
        "Kontroller ve uyarılar",
        "Takip: mesafe ve kadraj",
        "(a) Model",
        "Ayarlar",
        "FLW_TGT_DST",
        "Takip zaman çizelgesi",
    ):
        assert part in page, part


def test_report_explains_the_near_passes_and_the_corners(tmp_path: Path) -> None:
    """Task group 9: the < 6 m passes of the recording with their cause and decomposition, and the corners with how
    fast PX4 caught up, as tables, a check line and a timeline figure (distance, cause bands, corners)."""
    sc = scenario({})
    rows = [
        r
        | {"kamera_z": 8.0, "hedef_x": 10.0, "hedef_y": 0.0, "hedef_yaw": 0.0, "hedef_hiz": 0.0, "ayak_gorunur": True}
        | {"bas_gorunur": True, "gorunur": True, "hedef_piksel": 900.0, "merkez_u": 1152.0, "merkez_v": 648.0}
        for r in recording().to_dict("records")
    ]
    parts = {"toplam_m": 5.0, "dron_m": 1.5, "px4_suzgec_m": 2.5, "px4_ongoru_m": 1.2, "konum_hatasi_m": -0.3}
    parts |= {"olcum_yasi_m": 0.1, "kalan_m": 0.0}
    event = {"baslangic_s": 64.0, "bitis_s": 65.5, "sure_s": 1.5, "en_az_m": 3.0, "en_az_t_s": 64.8, "sebep": "kose"}
    event |= {"etkenler": ["kose", "durma_hizlanma"], "ayristirma": parts, "baskin_etken": "px4_suzgec_m"}
    event |= {"olcum_yasi_baslangicta_s": 0.2, "en_buyuk_bosluk_s": 0.4, "hedef_hizi_mps": 1.4}
    event |= {"px4_hiz_kestirimi_mps": 2.6, "px4_rota_deg": 355.0, "gercek_rota_deg": 270.0, "kose_s": 63.0}
    corner = {"no": 1, "baslangic_s": 60.3, "bitis_s": 69.0, "yon_deg": 90.0, "onceki_yon_deg": None, "tur": "kalkis"}
    corner |= {"donus_deg": None, "durus_s": 34.0, "px4_yetisme_s": 1.5, "px4_yetisti": True}
    corner |= {"arkada_kalma_maks_deg": 120.0, "arkada_kalma_90_ustu_s": 1.2}
    metrics = {"yakin_gecis_6m_olay_sayisi": 1, "yakin_gecis_6m_suresi_s": 1.5, "yakin_gecis_kose_sayisi": 1}
    metrics |= {"mesafe_6m_alti_orani": 0.06, "kose_sayisi": 1, "kose_px4_yetisme_ort_s": 1.5}
    sections = {"yakin_gecis": {"esik_m": 6.0, "olaylar": [event]}, "koseler": [corner]}
    rapor.write(tmp_path, sc, rows, [], True, [], None, None, None, {}, metrics, sections)
    saved = json.loads((tmp_path / "ozet.json").read_text(encoding="utf-8"))
    check = next(c for c in saved["kontroller"] if c["ad"] == "yakin_gecis")
    assert check["durum"] == "uyari" and "köşe" in check["metin"] and "64.0" in check["metin"]
    page = (tmp_path / "rapor.html").read_text(encoding="utf-8")
    for part in (
        "Yakın geçişler (&lt; 6 m)",
        "köşe / yön değişimi",
        "PX4'ün süzülmüş hedefi",
        "+2.50",
        "Köşeler",
        "kalkış",
        "1.50",
        "Yakın geçişler ve sebepleri",
        "%6.0",
    ):
        assert part in page, part
