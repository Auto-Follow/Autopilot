"""Capture -> PX4 delay line (spec 4): part 1 (task group 5) keeps the order and stamps every message's release; part 2
(task group 12) adds the artificial delay in sim time, its seeded jitter and the clock model of the sent time_usec."""

import csv
import statistics
import threading
import time
from pathlib import Path

import numpy as np
import pytest

import algilama
import gecikme
import goruntu
import takip


def test_messages_leave_in_order_no_earlier_than_their_delay() -> None:
    out: list[tuple[str, float, str]] = []
    line = gecikme.DelayLine(lambda item, serbest: out.append((item, serbest, threading.current_thread().name)))

    now = time.monotonic()
    line.put("a", now)  # no delay and nothing waiting: leaves at once, in the caller's thread
    assert out == [("a", pytest.approx(now, abs=0.05), threading.current_thread().name)]

    start = time.monotonic()
    line.put("b", start, extra_ms=60.0)
    line.put("c", start, extra_ms=0.0)  # ready earlier than "b" but must not overtake it
    line.put("d", start + 0.07, extra_ms=10.0)
    line.close()
    assert [item for item, *_ in out] == ["a", "b", "c", "d"]
    released = {item: serbest for item, serbest, _ in out}
    assert released["b"] >= start + 0.060 and released["c"] >= released["b"]
    assert released["d"] >= start + 0.080
    assert line.pending == 0
    with pytest.raises(RuntimeError):
        line.put("e", time.monotonic())


def test_jitter_is_uniform_round_the_extra_delay_seeded_and_never_negative() -> None:
    """gecikme.titresim_ms: extra_ms + U(-jitter, +jitter) (netem's convention), at least 0; the same seed draws the
    same delays in the same order, another seed others; without jitter every message gets extra_ms exactly."""
    draws = [gecikme.LinkDelay(200.0, 30.0).draw_ms() for _ in range(3)]
    assert len(set(draws)) == 1  # a new line with the default seed starts the same sequence

    delay = gecikme.LinkDelay(200.0, 30.0)
    values = np.array([delay.draw_ms() for _ in range(4000)])
    assert values.min() >= 170.0 and values.max() <= 230.0
    assert values.mean() == pytest.approx(200.0, abs=1.0)
    thirds = np.histogram(values, bins=3, range=(170.0, 230.0))[0] / len(values)
    assert thirds == pytest.approx([1 / 3] * 3, abs=0.04)  # uniform, not bunched in the middle
    again = gecikme.LinkDelay(200.0, 30.0, seed=gecikme.JITTER_SEED)
    assert [again.draw_ms() for _ in range(4000)] == values.tolist()
    other = gecikme.LinkDelay(200.0, 30.0, seed=1)
    assert [other.draw_ms() for _ in range(50)] != values[:50].tolist()

    fixed = gecikme.LinkDelay(200.0)
    assert {fixed.draw_ms() for _ in range(10)} == {200.0}
    low = gecikme.LinkDelay(10.0, 30.0)
    small = [low.draw_ms() for _ in range(500)]
    assert min(small) == 0.0 and max(small) <= 40.0  # the part below 0 is cut, never a negative delay
    for bad in ((-1.0, 0.0), (0.0, -5.0), (float("nan"), 0.0)):
        with pytest.raises(ValueError, match="gecikme"):
            gecikme.LinkDelay(*bad)


def test_delay_counts_in_the_lines_clock_even_when_it_runs_slower_than_the_wall() -> None:
    """The tracking side gives the line the sim clock: at RTF 0.5 a message delayed 100 ms leaves 100 sim ms (200 wall
    ms) after it was ready, a shorter draw behind it does not overtake it, and a message without delay leaves at once
    even if the converted clock reads a hair behind its ready time (never stamped before it)."""
    t0 = time.monotonic()

    def sim() -> float:  # a sim clock at half the wall rate
        return 60.0 + 0.5 * (time.monotonic() - t0)

    out: list[tuple[str, float, float]] = []
    line = gecikme.DelayLine(lambda item, released: out.append((item, released, time.monotonic())), clock=sim)
    ready = sim()
    line.put("a", ready, extra_ms=100.0)
    line.put("b", ready, extra_ms=20.0)
    line.close()
    (a, sim_a, wall_a), (b, sim_b, _) = out
    assert (a, b) == ("a", "b")
    assert ready + 0.100 <= sim_a < ready + 0.100 + 0.010  # not overshot by sleeping in wall seconds
    assert wall_a - (t0 + 2 * (ready - 60.0)) >= 0.200 - 0.002
    assert sim_b >= sim_a

    caller = threading.current_thread().name
    seen: list[tuple[str, float, str]] = []
    behind = gecikme.DelayLine(lambda item, released: seen.append((item, released, caller)), clock=lambda: 9.999)
    behind.put("x", 10.0)
    assert seen == [("x", 10.0, caller)] and behind.pending == 0


def test_clock_model_stamps_time_usec_with_offset_and_drift() -> None:
    """time_usec = capture + saat_ofset_ms + saat_kayma_ppm x elapsed (sim time since the start); with both 0 exactly
    the capture time the sim sent before task group 12 (round(t * 1e6), the files' t_us)."""
    plain = gecikme.ClockModel()
    for t in (0.0, 27.46, 61.0331, 99.999999, 1234.5678901):
        assert plain.time_usec(t) == round(t * 1e6) == algilama.time_key(t)
    assert gecikme.ClockModel(12.5, 200.0).time_usec(61.0) == 61_000_000 + 12_500 + 12_200
    assert gecikme.ClockModel(-5.0, -50.0).time_usec(100.0) == 100_000_000 - 5_000 - 5_000
    assert gecikme.ClockModel(-1500.0).time_usec(1.0) == 0  # an unsigned field: a clock behind 0 stamps 0
    with pytest.raises(ValueError, match="gecikme"):
        gecikme.ClockModel(float("inf"))


class FakeLink:
    def __init__(self) -> None:
        self.sent: list[tuple[int, tuple | None]] = []

    def send_los(self, time_usec: int, vec: np.ndarray | None) -> None:
        self.sent.append((time_usec, None if vec is None else tuple(vec)))


def test_tracker_delays_every_tez_los_in_sim_time_and_sends_the_clock_models_time_usec(tmp_path: Path) -> None:
    """takip.Tracker with gecikme.ek_ms 80 and a clock 12.5 ms ahead and 200 ppm fast, the sim at RTF 0.5: every
    TEZ_LOS leaves the delay line 80 sim ms after it was ready (ek_gecikme_ms, in algilama.csv and tez_los.csv), the
    end-to-end delay grows by as much, and the time_usec PX4 gets is the one tez_los.csv logs."""
    t0 = time.monotonic()
    clock = goruntu.SimClock()
    for k in range(1001):  # RTF 0.5 for the next 10 s
        clock.add(sim=61.0 + 0.005 * k, wall=t0 + 0.01 * k)
    detections = algilama.DetectionLog(tmp_path, clock, takip.ROW_COLUMNS)
    stamp = gecikme.ClockModel(12.5, 200.0)
    tr = takip.Tracker(
        "model", clock, tmp_path, detections, camera=lambda: None, delay=gecikme.LinkDelay(80.0), stamp=stamp
    )
    link = FakeLink()
    tr.attach(link)
    captures = []
    for _ in range(3):
        now = time.monotonic()
        t = round(clock.to_sim(now) - 0.120, 4)  # the model result comes 120 sim ms after the capture
        captures.append(t)
        tr.on_model(
            algilama.FrameResult(t, round(t * 30), now - 0.1, now - 0.08, now - 0.01, 1.0, 0.0, 70.0, (), ()), now
        )
        time.sleep(0.1)  # 50 sim ms between frames: above the stream's 1/30 s rate limit
    tr.close()
    detections.close()

    assert [ts for ts, _ in link.sent] == [stamp.time_usec(t) for t in captures]
    with (tmp_path / "tez_los.csv").open(encoding="utf-8") as f:
        attempts = list(csv.DictReader(f))
    assert [int(a["time_usec"]) for a in attempts] == [stamp.time_usec(t) for t in captures]
    assert [a["sonuc"] for a in attempts] == ["gonderildi"] * 3
    delays = [float(a["ek_gecikme_ms"]) for a in attempts]
    assert all(80.0 <= d < 80.0 + 10.0 for d in delays), delays
    assert statistics.fmean(float(a["uctan_uca_ms"]) for a in attempts) == pytest.approx(200.0, abs=10.0)
    with (tmp_path / "algilama.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [float(r["ek_gecikme_ms"]) for r in rows] == pytest.approx(delays)
    assert all(float(r["serbest_sim"]) - float(r["hazir_sim"]) >= 0.080 for r in rows)
