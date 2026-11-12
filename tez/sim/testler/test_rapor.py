"""Report metrics and success thresholds on a synthetic recording."""

import math

import numpy as np
import pandas as pd
import pytest

import dogrulama
import hedef
import konumlama
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


def test_tez_los_messages_that_reached_px4_are_counted_from_the_ulog_columns() -> None:
    """debug_vect in the ULog (pyulog: one int8 column per character of the name); only TEZ_LOS counts, other
    DEBUG_VECT senders share the topic (spec "Varsayımlar" 1)."""
    names = ["TEZ_LOS", "TEZ_LOS", "BASKA", "TEZ_LOS", "TEZ_LOS"]
    data = {"timestamp": np.array([59.99e6, 60.0e6, 60.01e6, 61.5e6, 62.01e6])}
    for i in range(10):
        data[f"name[{i}]"] = np.array([ord(n[i]) if i < len(n) else 0 for n in names], dtype=np.int8)
    assert list(rapor.debug_names(data)) == names
    for k, v in zip("xyz", ([0.6, 0.6, 0.0, math.nan, 0.8], [0.0] * 5, [0.8, 0.8, 1.0, math.nan, 0.6]), strict=True):
        data[k] = np.array(v, dtype=np.float32)
    m = rapor.tez_los_in_ulog(data, 60.0, 62.0)
    assert (m["tez_los_px4_sayisi"], m["tez_los_px4_hizi_hz"]) == (2, pytest.approx(1.0))
    # the logged ones are matched to the sent ones by their values (PX4 drops time_usec): PX4 arrival - capture
    sent = [
        {"t": 59.88, "x": 0.6, "y": 0.0, "z": 0.8, "gonderim_sim": 59.998},
        {"t": 61.38, "x": math.nan, "y": math.nan, "z": math.nan, "gonderim_sim": 61.498},  # NaN: ambiguous, skipped
        {"t": 61.89, "x": 0.8, "y": 0.0, "z": 0.6, "gonderim_sim": 62.007},
    ]
    m = rapor.tez_los_in_ulog(data, 60.0, 62.5, sent)
    assert m["tez_los_px4_sayisi"] == 3 and m["tez_los_px4_eslesen"] == 2  # the NaN one at 61.5 s is not matched
    assert m["uctan_uca_px4_ms_ort"] == pytest.approx(120.0, abs=0.01)
    assert m["px4_varis_eksi_gonderim_ms_ort"] == pytest.approx(2.5, abs=0.01)  # arrived 2 and 3 ms after the send


def test_follow_target_in_the_ulog_and_where_px4_thought_the_target_was() -> None:
    """follow_target (the logger keeps one sample per 500 ms) and follow_target_estimator (every 200 ms): its estimate
    against where the target really was at the same PX4 time (= sim time in SITL), and how long it was stale (no
    FOLLOW_TARGET for 3 s: PX4 keeps the last position and stops moving it)."""
    world = konumlama.WorldGeo(47.397971057728974, 8.546163739800146, 0.0)
    target = {"timestamp": np.array([59.5e6, 60.0e6, 60.5e6, 61.0e6, 62.9e6])}
    t = np.round(np.arange(60.0, 63.001, 0.2), 6)
    geo = [world.to_geodetic(10.0 + (s - 60.0) - 0.3, 2.0) for s in t]  # 0.3 m behind a target walking east at 1 m/s
    estimator = {
        "timestamp": t * 1e6,
        "valid": np.array([0] + [1] * (len(t) - 1), dtype=np.uint8),  # the first one before any fusion
        "stale": (t >= 62.0).astype(np.uint8),
        "lat_est": np.array([math.nan] + [g[0] for g in geo[1:]]),
        "lon_est": np.array([math.nan] + [g[1] for g in geo[1:]]),
    }
    m = rapor.follow_target_in_ulog(target, estimator, 60.0, 63.0, world, lambda s: (10.0 + (s - 60.0), 2.0))
    assert (m["follow_target_px4_sayisi"], m["follow_target_px4_hizi_hz"]) == (4, pytest.approx(4 / 3))
    assert m["px4_kestirim_hatasi_ort_m"] == pytest.approx(0.3, abs=1e-6)
    assert m["px4_kestirim_hatasi_maks_m"] == pytest.approx(0.3, abs=1e-6)
    assert m["px4_kestirim_gecerli_orani"] == pytest.approx(15 / 16)
    assert m["px4_kestirim_bayat_s"] == pytest.approx(1.0)  # 62.0 -> 63.0 s
    assert rapor.follow_target_in_ulog(None, None, 60.0, 63.0, world, None)["follow_target_px4_sayisi"] == 0
