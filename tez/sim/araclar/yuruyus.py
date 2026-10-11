"""Human motion model: the scenario's waypoints and speeds -> a time track the actor follows and the referee uses.

A person does not move like the waypoint list: they speed up and slow down over about a second, take corners on an
arc (wider when faster), stop and turn on the spot for sharp turns, turn towards the next direction before setting
off after a pause, and neither keep an exact speed nor an exact straight line. With `natural=False` the old ideal
motion is kept (straight lines, constant speed, instant turns) for debugging.

The limits below are typical values for adults (assumptions until measured with real targets); the random parts are
seeded, so a scenario walks the same way in every run.
"""

import math
from dataclasses import dataclass

import numpy as np

DT = 0.02  # [s] track resolution
DS = 0.02  # [m] planning resolution along the path
RUN_SPEED = 2.0  # [m/s] faster legs use the run animation
ACCEL = {"walk": 1.0, "run": 2.5}  # [m/s^2] speeding up and slowing down (steady gait after ~2 steps)
LATERAL = {"walk": 1.5, "run": 3.0}  # [m/s^2] centripetal acceleration in turns: radius = v^2 / a
PIVOT_RATE = math.radians(180)  # [rad/s] turning on the spot
SHARP_TURN = math.radians(135)  # sharper corners: stop, turn on the spot, go on
MIN_ARC_TURN = math.radians(2)  # smaller direction changes need no arc
TAPER = 2.0  # [m] the path wander fades out this close to every scenario point
SPEED_WAVELENGTH = (4.0, 12.0)  # [m] speed fluctuation: ~3-8 s at walking speed
WANDER_WAVELENGTH = (8.0, 20.0)  # [m] lateral wander of the walking line: heading off by ~2-3 deg


@dataclass(frozen=True)
class Behaviour:
    natural: bool = True
    seed: int = 0
    speed_variation: float = 0.05  # relative standard deviation of the speed
    wander_m: float = 0.08  # standard deviation of the sideways deviation from the straight line [m]


@dataclass
class Track:
    """Target state on a DT grid; before the first and after the last sample it stands still."""

    t: np.ndarray
    x: np.ndarray
    y: np.ndarray
    yaw: np.ndarray  # [rad] unwrapped heading, world frame (0 = east)
    speed: np.ndarray  # [m/s]
    kind: np.ndarray  # Gazebo animation per sample: stand | walk | run

    def at(self, t: float) -> tuple[float, float, float, float, str]:
        """(x, y, yaw, speed, animation) at time t."""
        if t <= self.t[0]:
            i = 0
        elif t >= self.t[-1]:
            return float(self.x[-1]), float(self.y[-1]), _wrap(self.yaw[-1]), 0.0, "stand"
        else:
            i = int(np.searchsorted(self.t, t, side="right")) - 1
        f = 0.0 if i == 0 and t <= self.t[0] else (t - self.t[i]) / (self.t[i + 1] - self.t[i])

        def lerp(a: np.ndarray) -> float:
            return float(a[i] + f * (a[i + 1] - a[i])) if f else float(a[i])

        return lerp(self.x), lerp(self.y), _wrap(lerp(self.yaw)), lerp(self.speed), str(self.kind[i])

    def length(self) -> float:
        return float(np.hypot(np.diff(self.x), np.diff(self.y)).sum())


def _wrap(a: float) -> float:
    return float((a + math.pi) % (2 * math.pi) - math.pi)


def _smooth_noise(s: np.ndarray, rng: np.random.Generator, wavelengths: tuple[float, float], k: int = 4) -> np.ndarray:
    """Smooth random signal of unit standard deviation along s: a sum of k sines with random wavelengths/phases."""
    lam = rng.uniform(*wavelengths, k)
    phase = rng.uniform(0, 2 * math.pi, k)
    return np.sqrt(2 / k) * np.sin(2 * math.pi * s[:, None] / lam + phase).sum(axis=1)


def _kind(speed: float) -> str:
    return "run" if speed > RUN_SPEED else "walk"


def _leg_geometry(points: list[tuple[float, float]], speeds: list[float], natural: bool) -> dict:
    """Path through `points` sampled every ~DS: corners become arcs (natural). Per sample: x, y, heading, the speed
    limit, the animation, and the distance to the nearest scenario point (for the wander taper)."""
    xs, ys, hs, vmax, kinds = [], [], [], [], []
    p = np.array(points, dtype=float)
    d = np.diff(p, axis=0)
    seg_len = np.hypot(d[:, 0], d[:, 1])
    u = d / seg_len[:, None]
    # Tangent length cut from both sides of every interior corner, and the arc there
    cut = np.zeros(len(points))
    arcs = {}
    for k in range(1, len(points) - 1):
        cross = u[k - 1, 0] * u[k, 1] - u[k - 1, 1] * u[k, 0]
        theta = math.acos(max(-1.0, min(1.0, float(u[k - 1] @ u[k]))))
        if not natural or theta < MIN_ARC_TURN:
            continue
        v_c = min(speeds[k - 1], speeds[k])
        kind = _kind(v_c)
        radius = v_c**2 / LATERAL[kind]
        length = radius * math.tan(theta / 2)
        limit = 0.45 * min(seg_len[k - 1], seg_len[k])
        if length > limit:  # the legs are too short for a comfortable arc: tighter and slower
            length = limit
            radius = length / math.tan(theta / 2)
        cut[k] = length
        arcs[k] = (radius, theta, math.copysign(1.0, cross), min(v_c, math.sqrt(LATERAL[kind] * radius)), kind)

    def add(x: float, y: float, h: float, v: float, kind: str) -> None:
        xs.append(x)
        ys.append(y)
        hs.append(h)
        vmax.append(v)
        kinds.append(kind)

    for k in range(len(points) - 1):
        a = p[k] + u[k] * cut[k]
        b = p[k + 1] - u[k] * cut[k + 1]
        h = math.atan2(u[k, 1], u[k, 0])
        for f in np.linspace(0, 1, max(1, math.ceil(math.dist(a, b) / DS)), endpoint=False):
            q = a + f * (b - a)
            add(q[0], q[1], h, speeds[k], _kind(speeds[k]))
        if k + 1 in arcs:
            radius, theta, turn, v_arc, kind = arcs[k + 1]
            center = b + turn * radius * np.array([-math.sin(h), math.cos(h)])
            for f in np.linspace(0, 1, max(2, math.ceil(radius * theta / DS)), endpoint=False):
                hh = h + turn * theta * f
                q = center + turn * radius * np.array([math.sin(hh), -math.cos(hh)])
                add(q[0], q[1], hh, v_arc, kind)
    add(p[-1, 0], p[-1, 1], h, speeds[-1], _kind(speeds[-1]))
    x, y = np.array(xs), np.array(ys)
    s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
    # Distance along the path to the nearest scenario point (corners at the middle of their arcs)
    corner_s = [0.0, s[-1]]
    corner_s += [s[int(np.argmin(np.hypot(x - p[k, 0], y - p[k, 1])))] for k in range(1, len(points) - 1)]
    to_point = np.min(np.abs(s[:, None] - np.array(corner_s)[None, :]), axis=1)
    return {
        "s": s,
        "x": x,
        "y": y,
        "h": np.unwrap(np.array(hs)),
        "vmax": np.array(vmax),
        "kind": kinds,
        "to_point": to_point,
    }


def _leg(points: list[tuple[float, float]], speeds: list[float], beh: Behaviour, rng: np.random.Generator) -> dict:
    """Motion along one leg that starts and ends at rest (natural) -> arrays over time from 0."""
    g = _leg_geometry(points, speeds, beh.natural)
    s, x, y = g["s"], g["x"], g["y"]
    vmax = g["vmax"].copy()
    if beh.natural:
        vmax *= np.clip(1 + beh.speed_variation * _smooth_noise(s, rng, SPEED_WAVELENGTH), 0.5, 1.5)
        accel = np.array([ACCEL[k] for k in g["kind"]])
        v = vmax.copy()
        v[0] = 0.0
        ds = np.diff(s)
        for i in range(1, len(v)):
            v[i] = min(v[i], math.sqrt(v[i - 1] ** 2 + 2 * accel[i] * ds[i - 1]))
        v[-1] = 0.0
        for i in range(len(v) - 2, -1, -1):
            v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * accel[i] * ds[i]))
        if beh.wander_m > 0:
            taper = np.clip(g["to_point"] / TAPER, 0, 1)
            offset = beh.wander_m * _smooth_noise(s, rng, WANDER_WAVELENGTH) * taper**2 * (3 - 2 * taper)
            x = x - np.sin(g["h"]) * offset
            y = y + np.cos(g["h"]) * offset
    else:
        v = vmax
    step = np.hypot(np.diff(x), np.diff(y))
    t = np.concatenate([[0.0], np.cumsum(2 * step / (v[:-1] + v[1:]))])
    heading = np.arctan2(np.diff(y), np.diff(x))
    heading = np.unwrap(np.append(heading, heading[-1]))
    return {"t": t, "x": x, "y": y, "yaw": heading, "speed": v, "kind": g["kind"]}


def _stand(duration: float, pos: tuple[float, float], yaw0: float, yaw1: float | None = None) -> dict:
    """Standing, optionally turning on the spot from yaw0 to yaw1 (shortest way) over `duration`."""
    n = max(2, math.ceil(duration / DT) + 1)
    yaw1 = yaw0 if yaw1 is None else yaw0 + _wrap(yaw1 - yaw0)
    return {
        "t": np.linspace(0, duration, n),
        "x": np.full(n, pos[0]),
        "y": np.full(n, pos[1]),
        "yaw": np.linspace(yaw0, yaw1, n),
        "speed": np.zeros(n),
        "kind": ["stand"] * n,
    }


def plan(start: tuple[float, float], start_time: float, steps: list[tuple], beh: Behaviour) -> tuple[Track, float]:
    """Track for steps [("move", (x, y), speed) | ("wait", seconds)], starting to move at start_time.

    Returns the track and the time the last step ends.
    """
    rng = np.random.default_rng(beh.seed)
    moves = [s for s in steps if s[0] == "move"]
    yaw = math.atan2(moves[0][1][1] - start[1], moves[0][1][0] - start[0]) if moves else 0.0
    pieces = [(0.0, _stand(start_time, start, yaw))]
    t, pos = start_time, start

    # Group consecutive moves into legs; a sharp corner splits a leg (stop, turn, go on)
    items: list[tuple] = []
    leg: list[tuple[tuple[float, float], float]] = []
    here, prev_dir = start, None
    for step in steps:
        if step[0] == "wait":
            if leg:
                items.append(("leg", leg))
                leg = []
            items.append(step)
            prev_dir = None
            continue
        direction = math.atan2(step[1][1] - here[1], step[1][0] - here[0])
        if leg and beh.natural and prev_dir is not None and abs(_wrap(direction - prev_dir)) > SHARP_TURN:
            items.append(("leg", leg))
            leg = []
        leg.append((step[1], step[2]))
        here, prev_dir = step[1], direction
    if leg:
        items.append(("leg", leg))

    for item in items:
        if item[0] == "wait":
            pieces.append((t, _stand(item[1], pos, yaw)))
            t += item[1]
            continue
        points = [pos] + [p for p, _ in item[1]]
        direction = math.atan2(points[1][1] - pos[1], points[1][0] - pos[0])
        turn = abs(_wrap(direction - yaw))
        if beh.natural and turn > math.radians(1):
            duration = turn / PIVOT_RATE
            pieces.append((t, _stand(duration, pos, yaw, direction)))
            t += duration
        motion = _leg(points, [v for _, v in item[1]], beh, rng)
        pieces.append((t, motion))
        t += motion["t"][-1]
        pos, yaw = points[-1], float(motion["yaw"][-1])
    return _assemble(pieces), t


def _assemble(pieces: list[tuple[float, dict]]) -> Track:
    """Concatenate pieces (start time, arrays) and resample on a common DT grid."""
    t = np.concatenate([t0 + p["t"] for t0, p in pieces])
    cols = {k: np.concatenate([np.asarray(p[k], dtype=float) for _, p in pieces]) for k in ("x", "y", "speed")}
    yaw = np.unwrap(np.concatenate([np.asarray(p["yaw"], dtype=float) for _, p in pieces]))
    kind = np.concatenate([np.asarray(p["kind"]) for _, p in pieces])
    keep = np.append(np.diff(t) > 1e-9, True)  # pieces share their boundary instant: the later piece's sample wins
    t, yaw, kind = t[keep], yaw[keep], kind[keep]
    cols = {k: v[keep] for k, v in cols.items()}
    grid = np.concatenate([np.arange(t[0], t[-1], DT), [t[-1]]])
    idx = np.clip(np.searchsorted(t, grid, side="right") - 1, 0, len(t) - 1)
    return Track(
        grid,
        np.interp(grid, t, cols["x"]),
        np.interp(grid, t, cols["y"]),
        np.interp(grid, t, yaw),
        np.interp(grid, t, cols["speed"]),
        kind[idx],
    )
