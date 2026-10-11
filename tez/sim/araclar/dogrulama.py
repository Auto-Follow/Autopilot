"""Overhead check (senaryo.py --dogrula): does the rendered target stand where the ground truth says?

Gazebo does not publish the actor's pose, so a static nadir camera high above the path photographs the scene at
chosen sim times and the target is located in the frames. Image up = +x (east), image right = -y. The world is
rendered without shadows for this check (a shadow shifts the measured centroid by ~0.5 m, 2026-10-11 test).
"""

import math
import os
import threading
from pathlib import Path

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")  # protobuf 7.x in ~/.local
os.environ.setdefault("GZ_IP", "127.0.0.1")  # same as calistir.sh

import numpy as np  # noqa: E402
from gz.msgs10.image_pb2 import Image  # noqa: E402
from gz.transport13 import Node  # noqa: E402

from hedef import ACTOR_HIP_HEIGHT, Scenario  # noqa: E402

HFOV = 1.2  # [rad]
SIZE = (1600, 1200)  # [px]
TOPIC = "/dogrulama/image"
MARGIN = 4.0  # [m] around the path
LIMIT = 0.3  # [m] walking body centroid is 0.05-0.19 m ahead of the path (2026-10-11 test)


def camera_pose(sc: Scenario) -> tuple[float, float, float]:
    """Camera position over the middle of the path, high enough to see all of it with the margin."""
    x0, x1, y0, y1 = sc.bounds()
    half_h = math.tan(HFOV / 2)  # horizontal image axis covers y
    half_v = half_h * SIZE[1] / SIZE[0]  # vertical image axis covers x
    height = max(25.0, ((x1 - x0) / 2 + MARGIN) / half_v, ((y1 - y0) / 2 + MARGIN) / half_h)
    return (x0 + x1) / 2, (y0 + y1) / 2, height


def camera_sdf(pos: tuple[float, float, float]) -> str:
    return f"""
    <model name="dogrulama_kamerasi">
      <static>true</static>
      <pose>{pos[0]:.3f} {pos[1]:.3f} {pos[2]:.3f} 0 1.570796 0</pose>
      <link name="link">
        <sensor name="tepe" type="camera">
          <topic>{TOPIC}</topic>
          <always_on>1</always_on>
          <update_rate>10</update_rate>
          <camera>
            <horizontal_fov>{HFOV}</horizontal_fov>
            <image><width>{SIZE[0]}</width><height>{SIZE[1]}</height></image>
            <clip><near>1</near><far>{pos[2] + 20:.0f}</far></clip>
          </camera>
        </sensor>
      </link>
    </model>
"""


def check_times(sc: Scenario) -> list[float]:
    """Before the walk, ~8 times while moving, and at the end [s sim time, 0.1 s steps]."""
    step = max(2.0, (sc.walk_end - sc.start_time) / 8)
    times = [sc.start_time - 5.0, *np.arange(sc.start_time + 1.0, sc.walk_end + 0.01, step), sc.end_time - 1.0]
    return sorted({round(float(t), 1) for t in times})


def locate(img: np.ndarray, cam: tuple[float, float, float], drone: tuple[float, float, float] | None) -> tuple | None:
    """Target centroid on the ground [m]: pixels unlike the grass, the drone masked out."""
    h_px, w_px = img.shape[:2]
    cx, cy, cz = cam
    f = (w_px / 2) / math.tan(HFOV / 2)
    ground = np.median(img.reshape(-1, 3), axis=0)
    ys, xs = np.nonzero(np.abs(img.astype(int) - ground).sum(axis=2) > 60)
    if drone is not None:
        dz = cz - drone[2]
        du = w_px / 2 - (drone[1] - cy) * f / dz
        dv = h_px / 2 - (drone[0] - cx) * f / dz
        keep = np.hypot(xs - du, ys - dv) > 0.8 * f / dz  # drone body ~0.6 m across
        xs, ys = xs[keep], ys[keep]
    if len(xs) < 15:
        return None
    scale = (cz - ACTOR_HIP_HEIGHT * 0.9) / f  # metres per pixel at the body's mean height
    return float(cx + (h_px / 2 - ys.mean()) * scale), float(cy - (xs.mean() - w_px / 2) * scale)


class OverheadCheck:
    """Keeps one overhead frame per check time; results() compares them with the ground truth."""

    def __init__(self, sc: Scenario, pos: tuple[float, float, float]) -> None:
        self.sc = sc
        self.pos = pos
        self.times = check_times(sc)
        self.frames: dict[float, np.ndarray] = {}
        self._lock = threading.Lock()
        self._node = Node()
        self._node.subscribe(Image, TOPIC, self._on_image)

    def _on_image(self, msg: Image) -> None:
        t = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        for want in self.times:
            if want not in self.frames and abs(t - want) < 0.06:
                img = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.width, 3).copy()
                with self._lock:
                    self.frames[want] = img

    def results(self, rows: list[dict], out: Path) -> list[dict]:
        """One row per check time; `rows` (ground truth) gives the drone position to mask out."""
        checks = []
        for want in self.times:
            with self._lock:
                img = self.frames.get(want)
            tx, ty, *_ = self.sc.truth(want)
            check = {"t": want, "hesap_x": tx, "hesap_y": ty, "goruntu_x": math.nan, "goruntu_y": math.nan}
            check["fark"] = math.nan
            if img is not None:
                near = min(rows, key=lambda r: abs(r["t"] - want)) if rows else None
                drone = (near["dron_x"], near["dron_y"], near["dron_z"]) if near else None
                est = locate(img, self.pos, drone)
                if est is not None:
                    check.update(goruntu_x=est[0], goruntu_y=est[1], fark=math.hypot(est[0] - tx, est[1] - ty))
                if want == self.times[len(self.times) // 2]:
                    import cv2

                    cv2.imwrite(str(out / "dogrulama_tepe.png"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            checks.append(check)
        return checks


def passed(checks: list[dict]) -> bool | None:
    """None without checks; otherwise every check located the target within LIMIT."""
    if not checks:
        return None
    return all(not math.isnan(c["fark"]) and c["fark"] <= LIMIT for c in checks)
