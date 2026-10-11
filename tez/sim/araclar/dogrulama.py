"""Overhead check (senaryo.py --dogrula): does the rendered target stand where the ground truth says?

Gazebo does not publish the actor's pose, so a static nadir segmentation camera high above the path labels every
pixel at chosen sim times and the target (label hedef.TARGET_LABEL) is located in the frames. Image up = +x (east),
image right = -y. Labels ignore ground texture, shadows, trees' colours and the other people; a target hidden under a
tree crown at a check time is reported as hidden, not as a failure.
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

from hedef import OTHER_LABEL, TARGET_LABEL, Scenario  # noqa: E402

HFOV = 1.2  # [rad]
SIZE = (800, 600)  # [px] 3-5 cm per pixel on the ground: enough for the 0.3 m limit, light to receive
TOPIC = "/dogrulama"
LABELS_TOPIC = TOPIC + "/labels_map"
MARGIN = 4.0  # [m] around the path
BODY_CENTRE = 0.9  # [m] mean height of the target pixels seen from above
LIMIT = 0.3  # [m] walking body centroid is 0.05-0.19 m ahead of the path (2026-10-11 test)
MIN_PIXELS = 15  # fewer target pixels: hidden (e.g. under a tree)
MIN_SEEN = 0.5  # share of the check times at which the target must be visible for the check to count


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
        <sensor name="tepe" type="segmentation">
          <topic>{TOPIC}</topic>
          <always_on>1</always_on>
          <update_rate>10</update_rate>
          <camera>
            <segmentation_type>instance</segmentation_type>
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


def locate(labels: np.ndarray, cam: tuple[float, float, float]) -> tuple | None:
    """Target centroid on the ground [m] from a label image; None if (almost) no target pixel is visible."""
    h_px, w_px = labels.shape
    cx, cy, cz = cam
    f = (w_px / 2) / math.tan(HFOV / 2)
    ys, xs = np.nonzero(labels == TARGET_LABEL)
    if len(xs) < MIN_PIXELS:
        return None
    scale = (cz - BODY_CENTRE) / f  # metres per pixel at the body's mean height
    return float(cx + (h_px / 2 - ys.mean()) * scale), float(cy - (xs.mean() - w_px / 2) * scale)


def picture(labels: np.ndarray) -> np.ndarray:
    """Label image for people: grey background, target blue, other people orange (report palette)."""
    img = np.full((*labels.shape, 3), 236, np.uint8)
    img[labels >= OTHER_LABEL] = (235, 104, 52)
    img[labels == TARGET_LABEL] = (42, 120, 214)
    return img


class OverheadCheck:
    """Keeps one overhead frame per check time; results() compares them with the ground truth."""

    def __init__(self, sc: Scenario, pos: tuple[float, float, float]) -> None:
        self.sc = sc
        self.pos = pos
        self.times = check_times(sc)
        self.frames: dict[float, np.ndarray] = {}
        self._lock = threading.Lock()
        self._node = Node()
        self._node.subscribe(Image, LABELS_TOPIC, self._on_image)

    def _on_image(self, msg: Image) -> None:
        t = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        for want in self.times:
            if want not in self.frames and abs(t - want) < 0.06:
                # instance segmentation: label in the third channel
                img = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.width, 3)[:, :, 2].copy()
                with self._lock:
                    self.frames[want] = img

    def results(self, out: Path) -> list[dict]:
        """One row per check time: computed and seen position, their difference; `ortulu` if the target was hidden."""
        checks = []
        for want in self.times:
            with self._lock:
                img = self.frames.get(want)
            tx, ty, *_ = self.sc.truth(want)
            check = {"t": want, "hesap_x": tx, "hesap_y": ty, "goruntu_x": math.nan, "goruntu_y": math.nan}
            check.update(fark=math.nan, ortulu=False)
            if img is not None:
                est = locate(img, self.pos)
                if est is None:
                    check["ortulu"] = True
                else:
                    check.update(goruntu_x=est[0], goruntu_y=est[1], fark=math.hypot(est[0] - tx, est[1] - ty))
                if want == self.times[len(self.times) // 2]:
                    import cv2

                    cv2.imwrite(str(out / "dogrulama_tepe.png"), cv2.cvtColor(picture(img), cv2.COLOR_RGB2BGR))
            checks.append(check)
        return checks


def passed(checks: list[dict]) -> bool | None:
    """None without checks; otherwise the target was seen at enough check times and always within LIMIT there.

    A frame that never arrived counts as a failure; a target hidden under a tree does not.
    """
    if not checks:
        return None
    seen = [c for c in checks if not c.get("ortulu")]
    if len(seen) < MIN_SEEN * len(checks):
        return False
    return all(not math.isnan(c["fark"]) and c["fark"] <= LIMIT for c in seen)
