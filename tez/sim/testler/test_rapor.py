"""Report metrics and success thresholds on a synthetic recording."""

import math

import numpy as np
import pandas as pd
import pytest

import dogrulama
import hedef
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
