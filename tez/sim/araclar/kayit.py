"""Ground truth recorder: drone and camera poses from Gazebo, target from the scenario, at a fixed sim-time rate.

Each row says where the drone, its camera and the target are, and where the target appears in the drone camera
image (pinhole model with the camera's own camera_info). Rows are stamped with Gazebo sim time, which is also
PX4's time in SITL.
"""

import math
import os
import threading

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")  # protobuf 7.x in ~/.local

import numpy as np  # noqa: E402
from gz.msgs10.camera_info_pb2 import CameraInfo  # noqa: E402
from gz.msgs10.pose_v_pb2 import Pose_V  # noqa: E402
from gz.transport13 import Node  # noqa: E402

from hedef import Scenario  # noqa: E402

DRONE_MODEL = "x500_tez_0"
CAMERA_LINK = "camera_link"
CAMERA_TOPIC = "/x500_tez/kamera"
TARGET_HEIGHT = 1.75  # [m] head of the human target above ground
TARGET_CENTER = 0.9  # [m] body centre used for "in view"


def rotation(qw: float, qx: float, qy: float, qz: float) -> np.ndarray:
    """Rotation matrix (body -> world) of a unit quaternion."""
    return np.array(
        [
            [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
            [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
            [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
        ]
    )


class Recorder:
    def __init__(self, scenario: Scenario, world: str, rate_hz: float = 20.0) -> None:
        self.sc = scenario
        self.world = world
        self.period = 1.0 / rate_hz
        self.rows: list[dict] = []
        self.sim_time = 0.0
        self.camera: dict | None = None  # intrinsics from camera_info
        self.camera_offset: tuple[float, float, float] | None = None  # camera link relative to the model [m]
        self._lock = threading.Lock()
        self._next = 0.0
        self._recording = False
        self._node = Node()
        self._node.subscribe(Pose_V, f"/world/{world}/dynamic_pose/info", self._on_pose)
        self._node.subscribe(CameraInfo, f"{CAMERA_TOPIC}/camera_info", self._on_info)

    def start(self) -> None:
        self._recording = True

    def stop(self) -> None:
        self._recording = False

    def snapshot(self) -> list[dict]:
        with self._lock:
            return list(self.rows)

    def _on_info(self, msg: CameraInfo) -> None:
        if self.camera is None:
            k = msg.intrinsics.k
            self.camera = {"fx": k[0], "fy": k[4], "cx": k[2], "cy": k[5], "w": msg.width, "h": msg.height}

    def _on_pose(self, msg: Pose_V) -> None:
        t = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        self.sim_time = t
        if not self._recording or t < self._next or self.camera is None:
            return
        poses = {p.name: p for p in msg.pose}
        if DRONE_MODEL not in poses or CAMERA_LINK not in poses:
            return
        self._next = t + self.period
        row = self._row(t, poses[DRONE_MODEL], poses[CAMERA_LINK])
        with self._lock:
            self.rows.append(row)

    def _row(self, t: float, model: object, cam_rel: object) -> dict:
        # Link poses in dynamic_pose/info are relative to their model
        r_model = rotation(model.orientation.w, model.orientation.x, model.orientation.y, model.orientation.z)
        p_model = np.array([model.position.x, model.position.y, model.position.z])
        r_rel = rotation(cam_rel.orientation.w, cam_rel.orientation.x, cam_rel.orientation.y, cam_rel.orientation.z)
        p_rel = np.array([cam_rel.position.x, cam_rel.position.y, cam_rel.position.z])
        if self.camera_offset is None:
            self.camera_offset = tuple(float(v) for v in p_rel)
        r_cam = r_model @ r_rel
        p_cam = p_model + r_model @ p_rel

        tx, ty, tyaw, tspeed, tkind = self.sc.truth(t)
        row = {
            "t": t,
            "dron_x": p_model[0],
            "dron_y": p_model[1],
            "dron_z": p_model[2],
            "dron_qw": model.orientation.w,
            "dron_qx": model.orientation.x,
            "dron_qy": model.orientation.y,
            "dron_qz": model.orientation.z,
            "kamera_x": p_cam[0],
            "kamera_y": p_cam[1],
            "kamera_z": p_cam[2],
            "hedef_x": tx,
            "hedef_y": ty,
            "hedef_yaw": tyaw,
            "hedef_hiz": tspeed,
            "hedef_animasyon": tkind,
            "yatay_mesafe": math.hypot(tx - p_model[0], ty - p_model[1]),
        }
        for label, height in (("ayak", 0.0), ("merkez", TARGET_CENTER), ("bas", TARGET_HEIGHT)):
            u, v, visible = self._project(np.array([tx, ty, height]), r_cam, p_cam)
            row[f"{label}_u"], row[f"{label}_v"], row[f"{label}_gorunur"] = u, v, visible
        row["kadrajda"] = row["merkez_gorunur"]
        return row

    def _project(self, point: np.ndarray, r_cam: np.ndarray, p_cam: np.ndarray) -> tuple[float, float, bool]:
        """Pixel (u, v) of a world point in the drone image. Gazebo camera frame: x forward, y left, z up."""
        d = r_cam.T @ (point - p_cam)
        if d[0] <= 0.05:
            return math.nan, math.nan, False
        c = self.camera
        u = c["cx"] - c["fx"] * d[1] / d[0]
        v = c["cy"] - c["fy"] * d[2] / d[0]
        return u, v, bool(0 <= u < c["w"] and 0 <= v < c["h"])
