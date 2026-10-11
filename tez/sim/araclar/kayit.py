"""Ground truth recorder: one row per drone camera frame, stamped with the frame's sim time.

Each row says where the drone, its camera and the target are, where the target appears in that frame (the camera's
own camera_info, distortion included) and the true line of sight to it in the frames of the team's pixel -> LOS chain
(optical, body FRD, NED; see kamera.py). Gazebo publishes poses at 50 Hz and frames at ~30 Hz on different sim
times, so the drone pose is interpolated to each frame time. Sim time is also PX4's time in SITL.
"""

import math
import os
import threading
from collections import deque

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")  # protobuf 7.x in ~/.local
os.environ.setdefault("GZ_IP", "127.0.0.1")  # same as calistir.sh

import numpy as np  # noqa: E402
from gz.msgs10.camera_info_pb2 import CameraInfo  # noqa: E402
from gz.msgs10.pose_v_pb2 import Pose_V  # noqa: E402
from gz.transport13 import Node  # noqa: E402

from hedef import Scenario  # noqa: E402
from kamera import ENU_TO_NED, FLU_TO_FRD, GZ_CAMERA_TO_OPTICAL, Camera, deviation, quat_to_dcm  # noqa: E402

DRONE_MODEL = "x500_tez_0"
CAMERA_LINK = "camera_link"
CAMERA_TOPIC = "/x500_tez/kamera"
# Mingfei actor; the "in view" point and the LOS use the body centre
TARGET_POINTS = (("ayak", 0.0), ("merkez", 0.9), ("bas", 1.75))  # [m] above ground
POSE_HISTORY = 100  # poses kept for interpolation (2 s at 50 Hz)


def nlerp(q0: np.ndarray, q1: np.ndarray, f: float) -> np.ndarray:
    """Quaternion interpolation; over 20 ms the difference to slerp is far below a pixel."""
    if np.dot(q0, q1) < 0:
        q1 = -q1
    q = (1 - f) * q0 + f * q1
    return q / np.linalg.norm(q)


def euler_frd_ned(r_world_flu: np.ndarray) -> tuple[float, float, float]:
    """PX4 roll, pitch, yaw [deg] of a Gazebo model orientation (ENU world, FLU body)."""
    r = ENU_TO_NED @ r_world_flu @ FLU_TO_FRD
    return (
        math.degrees(math.atan2(r[2, 1], r[2, 2])),
        math.degrees(-math.asin(max(-1.0, min(1.0, r[2, 0])))),
        math.degrees(math.atan2(r[1, 0], r[0, 0])),
    )


def camera_to_body_dcm(r_rel: np.ndarray) -> np.ndarray:
    """C_cb (optical -> body FRD) of a camera link with orientation r_rel relative to its FLU model."""
    return FLU_TO_FRD @ r_rel @ GZ_CAMERA_TO_OPTICAL.T


def truth_row(
    t: float,
    sc: Scenario,
    camera: Camera,
    p_model: np.ndarray,
    q_model: np.ndarray,
    p_rel: np.ndarray,
    r_rel: np.ndarray,
) -> dict:
    """Ground truth at sim time t for a drone pose (world ENU) and the camera pose relative to the drone."""
    r_model = quat_to_dcm(*q_model)
    r_cam = r_model @ r_rel
    p_cam = p_model + r_model @ p_rel
    tx, ty, tyaw, tspeed, tkind = sc.truth(t)
    roll, pitch, yaw = euler_frd_ned(r_model)
    row = {
        "t": t,
        "dron_x": p_model[0],
        "dron_y": p_model[1],
        "dron_z": p_model[2],
        "dron_qw": q_model[0],
        "dron_qx": q_model[1],
        "dron_qy": q_model[2],
        "dron_qz": q_model[3],
        "dron_roll_deg": roll,
        "dron_pitch_deg": pitch,
        "dron_yaw_deg": yaw,
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
    for label, height in TARGET_POINTS:
        ray = GZ_CAMERA_TO_OPTICAL @ r_cam.T @ (np.array([tx, ty, height]) - p_cam)
        uv = camera.project(ray)
        u, v = uv if uv is not None else (math.nan, math.nan)
        row[f"{label}_u"], row[f"{label}_v"], row[f"{label}_gorunur"] = u, v, uv is not None and camera.contains(u, v)
        if label == "merkez":
            d_world = np.array([tx, ty, height]) - p_cam
            row["menzil_m"] = float(np.linalg.norm(d_world))
            los = {
                "kamera": ray / np.linalg.norm(ray),  # optical
                "govde": FLU_TO_FRD @ r_model.T @ d_world / row["menzil_m"],  # body FRD, from the camera
                "ned": ENU_TO_NED @ d_world / row["menzil_m"],
            }
            for frame, vec in los.items():
                row[f"los_{frame}_x"], row[f"los_{frame}_y"], row[f"los_{frame}_z"] = vec
            row["sapma_yatay_deg"], row["sapma_dikey_deg"], _ = deviation(los["govde"], "body")
    row["kadrajda"] = row["merkez_gorunur"]
    return row


class Recorder:
    def __init__(self, scenario: Scenario, world: str) -> None:
        self.sc = scenario
        self.rows: list[dict] = []
        self.sim_time = 0.0
        self.camera: Camera | None = None
        self.camera_offset: tuple[float, float, float] | None = None  # camera link relative to the model [m]
        self.camera_dcm: np.ndarray | None = None  # C_cb, optical -> body FRD
        self._lock = threading.Lock()
        self._recording = False
        self._poses: deque[tuple[float, np.ndarray, np.ndarray]] = deque(maxlen=POSE_HISTORY)
        self._frames: deque[float] = deque()  # frame times waiting for a later pose
        self._rel: tuple[np.ndarray, np.ndarray] | None = None
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
        # camera_info is published with every image and carries the image's time stamp
        t = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        with self._lock:
            if self.camera is None:
                self.camera = Camera.from_camera_info(msg)
            if self._recording:
                self._frames.append(t)
                self._flush()

    def _on_pose(self, msg: Pose_V) -> None:
        t = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        model = cam = None
        for p in msg.pose:
            if p.name == DRONE_MODEL:
                model = p
            elif p.name == CAMERA_LINK:
                cam = p
        with self._lock:
            self.sim_time = t
            if cam is not None and self._rel is None:
                o = cam.orientation
                self._rel = (
                    np.array([cam.position.x, cam.position.y, cam.position.z]),
                    quat_to_dcm(o.w, o.x, o.y, o.z),
                )
                self.camera_offset = tuple(float(v) for v in self._rel[0])
                self.camera_dcm = camera_to_body_dcm(self._rel[1])
            if model is not None:
                o = model.orientation
                self._poses.append(
                    (
                        t,
                        np.array([model.position.x, model.position.y, model.position.z]),
                        np.array([o.w, o.x, o.y, o.z]),
                    )
                )
                self._flush()

    def _flush(self) -> None:
        """Turn every waiting frame time that now lies between two poses into a row (lock held)."""
        if self.camera is None or self._rel is None:
            return
        while self._frames and self._poses and self._frames[0] <= self._poses[-1][0]:
            t = self._frames.popleft()
            pose = self._pose_at(t)
            if pose is not None:
                self.rows.append(truth_row(t, self.sc, self.camera, *pose, *self._rel))

    def _pose_at(self, t: float) -> tuple[np.ndarray, np.ndarray] | None:
        poses = list(self._poses)
        for i in range(len(poses) - 1, 0, -1):  # newest first: frames wait for at most a few poses
            (t0, p0, q0), (t1, p1, q1) = poses[i - 1], poses[i]
            if t0 <= t <= t1:
                f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                return p0 + f * (p1 - p0), nlerp(q0, q1, f)
        return None
