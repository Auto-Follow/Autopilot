"""Human motion model: is this how a person would move?"""

import math

import numpy as np
import pytest

import yuruyus

START = (10.0, 0.0)
SQUARE_CORNER = [("move", (20.0, 0.0), 1.4), ("move", (20.0, 10.0), 1.4)]


def moving(tr: yuruyus.Track, t0: float = 60.0) -> dict:
    m = tr.t >= t0
    return {k: getattr(tr, k)[m] for k in ("t", "x", "y", "yaw", "speed")} | {"kind": tr.kind[m]}


def test_accelerates_and_stops_within_human_limits() -> None:
    tr, end = yuruyus.plan(START, 60.0, [("move", (30.0, 0.0), 1.4)], yuruyus.Behaviour(wander_m=0, speed_variation=0))
    m = moving(tr)
    accel = np.diff(m["speed"]) / np.diff(m["t"])
    assert np.abs(accel).max() <= yuruyus.ACCEL["walk"] * 1.05
    assert tr.at(60.0)[3] == 0.0 and tr.at(end)[3] == 0.0
    assert tr.at(60.5)[3] == pytest.approx(1.0, abs=0.05)  # 2 m/s^2 from rest: walking speed within 0.7 s
    assert tr.at(70.0)[3] == pytest.approx(1.4)
    # 20 m at 1.4 m/s takes 14.3 s; starting and stopping add 1.4 / 2 s
    assert end - 60.0 == pytest.approx(20 / 1.4 + 0.7, abs=0.05)
    assert tr.at(end)[:2] == pytest.approx((30.0, 0.0))


def test_corner_is_an_arc_with_radius_from_speed() -> None:
    tr, _ = yuruyus.plan(START, 60.0, SQUARE_CORNER, yuruyus.Behaviour(wander_m=0, speed_variation=0))
    m = moving(tr)
    # Walking 1.4 m/s with 1.5 m/s^2 sideways: radius 1.31 m, the path stays off the corner point by r(sqrt2 - 1)
    radius = 1.4**2 / yuruyus.LATERAL["walk"]
    closest = np.hypot(m["x"] - 20.0, m["y"] - 0.0).min()
    assert closest == pytest.approx(radius * (math.sqrt(2) - 1), abs=0.03)
    turn_rate = np.abs(np.diff(m["yaw"]) / np.diff(m["t"]))
    assert turn_rate.max() == pytest.approx(1.4 / radius, rel=0.1)  # v / r, no instant turn


def tight_arc_speed() -> float:
    return math.sqrt(yuruyus.LATERAL["walk"] * yuruyus.TURN_RADIUS)


def test_sharp_turn_steps_round_on_a_tight_arc() -> None:
    steps = [("move", (20.0, 0.0), 1.4), ("move", (12.0, 0.5), 1.4)]  # almost back
    tr, _ = yuruyus.plan(START, 60.0, steps, yuruyus.Behaviour(wander_m=0, speed_variation=0))
    m = moving(tr)
    near = np.hypot(m["x"] - 20.0, m["y"]) < 2 * yuruyus.TURN_RADIUS + 0.05
    assert np.hypot(m["x"] - 20.0, m["y"]).min() < 0.01  # reaches the point, then turns
    assert m["speed"][near].max() <= 1.4 and m["speed"][near].min() > 0.3  # slows down but keeps stepping
    assert set(m["kind"][near]) == {"walk"}  # never "stand": no turning on the spot
    assert m["x"].max() < 20.0 + yuruyus.TURN_RADIUS + 0.01  # overshoots by at most the turning radius
    turn_rate = np.abs(np.diff(m["yaw"]) / np.diff(m["t"]))
    assert turn_rate.max() <= tight_arc_speed() / yuruyus.TURN_RADIUS * 1.1
    assert tr.at(1e6)[:2] == pytest.approx((12.0, 0.5))


def test_sets_off_in_a_new_direction_with_small_steps() -> None:
    steps = [("move", (20.0, 0.0), 1.4), ("wait", 3.0), ("move", (20.0, 10.0), 1.4)]
    tr, _ = yuruyus.plan(START, 60.0, steps, yuruyus.Behaviour(wander_m=0, speed_variation=0))
    waiting = (tr.t > 60) & (tr.kind == "stand")
    # waits facing east, no rotation on the spot (the last sample is already the first instant of setting off)
    assert np.degrees(np.abs(tr.yaw[waiting][:-1])).max() < 1e-6
    leave = tr.t[waiting][-1]
    turning = (tr.t > leave) & (tr.t < leave + 1.5)
    assert set(tr.kind[turning]) == {"walk"}
    assert math.degrees(tr.at(leave + 2.0)[2]) == pytest.approx(90.0, abs=3)  # heading north after the arc
    assert tr.at(1e6)[:2] == pytest.approx((20.0, 10.0))


def test_running_uses_the_run_animation_and_wider_arcs() -> None:
    tr, _ = yuruyus.plan(START, 60.0, [("move", (30.0, 0.0), 3.0)], yuruyus.Behaviour(wander_m=0, speed_variation=0))
    assert "run" in set(tr.kind) and "walk" not in set(tr.kind)
    assert np.diff(tr.speed).max() / yuruyus.DT <= yuruyus.ACCEL["run"] * 1.05


def test_natural_variation_is_small_and_repeatable() -> None:
    beh = yuruyus.Behaviour(seed=3)
    a, _ = yuruyus.plan(START, 60.0, [("move", (40.0, 0.0), 1.4)], beh)
    b, _ = yuruyus.plan(START, 60.0, [("move", (40.0, 0.0), 1.4)], beh)
    assert np.array_equal(a.x, b.x) and np.array_equal(a.y, b.y)
    m = moving(a)
    cruise = (m["x"] > 15) & (m["x"] < 35)
    assert 0.0 < np.std(m["speed"][cruise] / 1.4) < 0.1
    assert 0.0 < np.abs(m["y"]).max() < 0.4  # wanders a little, but passes the scenario points
    assert np.degrees(np.abs(m["yaw"][cruise])).max() < 6
    assert a.at(1e6)[:2] == pytest.approx((40.0, 0.0))
    c, _ = yuruyus.plan(START, 60.0, [("move", (40.0, 0.0), 1.4)], yuruyus.Behaviour(seed=4))
    assert not np.array_equal(a.y, c.y)


def test_ideal_motion_is_the_old_one() -> None:
    tr, end = yuruyus.plan(START, 60.0, SQUARE_CORNER, yuruyus.Behaviour(natural=False))
    assert end - 60.0 == pytest.approx(20 / 1.4, abs=0.02)
    assert tr.at(65.0)[:2] == pytest.approx((17.0, 0.0), abs=0.01)
    assert tr.at(65.0)[3] == pytest.approx(1.4)


def test_before_the_start_the_target_waits_facing_its_first_direction() -> None:
    tr, _ = yuruyus.plan(START, 60.0, [("move", (10.0, 20.0), 1.4)], yuruyus.Behaviour())
    x, y, yaw, speed, kind = tr.at(30.0)
    assert (x, y, speed, kind) == (10.0, 0.0, 0.0, "stand")
    assert yaw == pytest.approx(math.pi / 2)
