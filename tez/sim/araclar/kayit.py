"""Ground truth recorder: one row per drone camera frame, stamped with the frame's sim time.

Each row says where the drone, its camera and the target are (and the other people of the scenario, if any: their
position and body-centre pixel), where the target appears in that frame (the camera's
own camera_info, distortion included) and the true line of sight to it in the frames of the team's pixel -> LOS chain
(optical, body FRD, NED; see kamera.py). Gazebo publishes poses at 50 Hz and frames at ~30 Hz on different sim
times, so the drone pose is interpolated to each frame time. Sim time is also PX4's time in SITL.

Live use (task group 5): Recorder(on_frame=...) hands every camera frame to the tracking side as soon as the referee
knows it: while recording, once both the row and the segmentation frame of that time are there (FrameJoin); outside
the recording (no referee), with no row at all. That is the referee's LOS (ii) and the operator's choice of the target
(first lock) in the run; it comes as late as the referee really is.
"""

import math
import os
import threading
import time
from collections import deque
from collections.abc import Callable

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")  # protobuf 7.x in ~/.local
os.environ.setdefault("GZ_IP", "127.0.0.1")  # same as calistir.sh

import numpy as np  # noqa: E402
from gz.msgs10.camera_info_pb2 import CameraInfo  # noqa: E402
from gz.msgs10.image_pb2 import Image  # noqa: E402
from gz.msgs10.pose_v_pb2 import Pose_V  # noqa: E402
from gz.transport13 import Node  # noqa: E402

from hedef import OTHER_LABEL, TARGET_LABEL, Scenario  # noqa: E402
from kamera import ENU_TO_NED, FLU_TO_FRD, GZ_CAMERA_TO_OPTICAL, Camera, deviation, quat_to_dcm  # noqa: E402

DRONE_MODEL = "x500_tez_0"
CAMERA_LINK = "camera_link"
CAMERA_TOPIC = "/x500_tez/kamera"
# Mingfei actor; the "in view" point and the LOS use the body centre
TARGET_POINTS = (("ayak", 0.0), ("merkez", 0.9), ("bas", 1.75))  # [m] above ground
POSE_HISTORY = 100  # poses kept for interpolation (2 s at 50 Hz)
SEG_TOPIC = "/x500_tez/kamera_seg/labels_map"  # models/x500_tez: segmentation camera, half resolution
SEG_SCALE = 2  # drone camera pixels per segmentation pixel
VISIBLE_PX = 40  # [px of the drone camera] fewer visible pixels of the target = not visible (hidden or too small)
JOIN_KEEP_S = 3.0  # [s sim] a half of a referee frame waits this long for the other half, then it is dropped


def is_visible(parts: dict | None) -> bool:
    """The target is visible in a segmentation frame (visible_parts): enough of it is not hidden."""
    return bool(parts) and parts["hedef_piksel"] >= VISIBLE_PX


class FrameJoin:
    """Joins the two halves of the referee's view of one camera frame: the row (truth_row, made once a later drone
    pose came) and the segmentation frame of the same time; they come in either order. Keys: round(t * 1e6)."""

    def __init__(self, keep_s: float = JOIN_KEEP_S) -> None:
        self._keep_us = round(keep_s * 1e6)
        self._rows: dict[int, dict] = {}
        self._segs: dict[int, dict] = {}
        self._newest = 0
        self.dropped = 0  # halves whose other half never came

    @property
    def pending(self) -> int:
        return len(self._rows) + len(self._segs)

    def add_row(self, key: int, row: dict) -> dict | None:
        """The whole frame (row + its segmentation + gorunur) if its segmentation frame is already there."""
        parts = self._segs.pop(key, None)
        if parts is None:
            self._rows[key] = row
            self._prune(key)
            return None
        return row | parts | {"gorunur": is_visible(parts)}

    def add_seg(self, key: int, parts: dict) -> dict | None:
        row = self._rows.pop(key, None)
        if row is None:
            self._segs[key] = parts
            self._prune(key)
            return None
        return row | parts | {"gorunur": is_visible(parts)}

    def _prune(self, key: int) -> None:
        self._newest = max(self._newest, key)
        for waiting in (self._rows, self._segs):
            old = [k for k in waiting if k < self._newest - self._keep_us]
            for k in old:
                del waiting[k]
            self.dropped += len(old)


def visible_parts(labels: np.ndarray, wanted: dict[int, str]) -> dict:
    """Visible pixel count and bounding box (drone camera pixels) of each labelled person in a segmentation frame.

    labels: (h, w) label per pixel; wanted: label -> column prefix. Box columns are pixel edges: u0 <= u < u1.
    """
    counts = np.bincount(labels.ravel(), minlength=256)
    out = {}
    for label, prefix in wanted.items():
        n = int(counts[label]) if label < len(counts) else 0
        out[f"{prefix}_piksel"] = n * SEG_SCALE * SEG_SCALE
        box = (math.nan,) * 4
        if n:
            mask = labels == label
            cols, rows = np.flatnonzero(mask.any(axis=0)), np.flatnonzero(mask.any(axis=1))
            box = (cols[0] * SEG_SCALE, rows[0] * SEG_SCALE, (cols[-1] + 1) * SEG_SCALE, (rows[-1] + 1) * SEG_SCALE)
        for key, value in zip(("u0", "v0", "u1", "v1"), box, strict=True):
            out[f"{prefix}_kutu_{key}"] = value
    return out


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
    # Other people (distractors): where they are and whether their body centre is in this frame
    seen = 0
    for i, person in enumerate(sc.others, start=1):
        px, py, *_ = person.track.at(t)
        uv = camera.project(GZ_CAMERA_TO_OPTICAL @ r_cam.T @ (np.array([px, py, TARGET_POINTS[1][1]]) - p_cam))
        u, v = uv if uv is not None else (math.nan, math.nan)
        inside = uv is not None and camera.contains(u, v)
        row.update(
            {f"insan{i}_x": px, f"insan{i}_y": py, f"insan{i}_u": u, f"insan{i}_v": v, f"insan{i}_kadrajda": inside}
        )
        seen += inside
    if sc.others:
        row["kadrajdaki_diger_insan"] = seen
    return row


class Recorder:
    def __init__(
        self,
        scenario: Scenario,
        world: str,
        on_frame: Callable[[float, dict | None, float], None] | None = None,
    ) -> None:
        """on_frame(t, row, ready): every camera frame for the tracking side, `row` = the referee's row joined with
        its segmentation frame (None outside the recording), `ready` = monotonic time it became known. Runs in a
        gz-transport thread: it must return quickly."""
        self.sc = scenario
        self._on_frame = on_frame
        self._join = FrameJoin()
        self.errors: list[str] = []  # on_frame failures (the transport thread must not die)
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
        self._seg: dict[int, dict] = {}  # frame time [us] -> visible_parts()
        self._labels = {TARGET_LABEL: "hedef"} | {OTHER_LABEL + i: f"insan{i + 1}" for i in range(len(scenario.others))}
        self._node = Node()
        self._node.subscribe(Pose_V, f"/world/{world}/dynamic_pose/info", self._on_pose)
        self._node.subscribe(CameraInfo, f"{CAMERA_TOPIC}/camera_info", self._on_info)

    @property
    def join_dropped(self) -> int:
        """Halves of referee frames whose other half never came (so on_frame never got that frame)."""
        with self._lock:
            return self._join.dropped

    def start(self) -> None:
        # segmentation frames only from now on: parsing them in Python all the time slowed the MAVLink tools
        self._node.subscribe(Image, SEG_TOPIC, self._on_seg)
        self._recording = True

    def stop(self) -> None:
        self._recording = False
        self._node.unsubscribe(SEG_TOPIC)

    def snapshot(self) -> list[dict]:
        """Rows so far, each joined with the segmentation frame of the same time (NaN where none arrived)."""
        with self._lock:
            rows, seg = list(self.rows), dict(self._seg)
        empty = dict.fromkeys(visible_parts(np.zeros((1, 1), np.uint8), self._labels), math.nan)
        out = []
        for r in rows:
            parts = seg.get(round(r["t"] * 1e6))
            r = r | (parts or empty)
            r["gorunur"] = is_visible(parts)
            out.append(r)
        return out

    def _emit(self, frames: list[tuple[float, dict | None]]) -> None:
        """Hand frames to on_frame, outside the lock (the tracking side may take its own locks)."""
        if self._on_frame is None or not frames:
            return
        ready = time.monotonic()
        for t, row in frames:
            try:
                self._on_frame(t, row, ready)
            except Exception as e:  # noqa: BLE001 - the transport thread keeps running; the run reports it
                if len(self.errors) < 20:
                    self.errors.append(f"{type(e).__name__}: {e}")

    def _on_seg(self, msg: Image) -> None:
        if not self._recording:
            return
        t = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        # instance segmentation: the label is in the third channel (the first two encode the instance)
        labels = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.width, 3)[:, :, 2]
        parts = visible_parts(labels, self._labels)
        key = round(t * 1e6)
        with self._lock:
            self._seg[key] = parts
            done = self._join.add_seg(key, parts) if self._on_frame is not None else None
        self._emit([(done["t"], done)] if done is not None else [])

    def _on_info(self, msg: CameraInfo) -> None:
        # camera_info is published with every image and carries the image's time stamp
        t = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        done: list[tuple[float, dict | None]] = []
        with self._lock:
            if self.camera is None:
                self.camera = Camera.from_camera_info(msg)
            if self._recording:
                self._frames.append(t)
                done = self._flush()
            else:
                done = [(t, None)]  # no referee outside the recording: the frame exists, nothing is known about it
        self._emit(done)

    def _on_pose(self, msg: Pose_V) -> None:
        t = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        model = cam = None
        for p in msg.pose:
            if p.name == DRONE_MODEL:
                model = p
            elif p.name == CAMERA_LINK:
                cam = p
        done: list[tuple[float, dict | None]] = []
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
                done = self._flush()
        self._emit(done)

    def _flush(self) -> list[tuple[float, dict]]:
        """Turn every waiting frame time that now lies between two poses into a row (lock held); returns the frames
        whose segmentation frame is there too (for on_frame)."""
        done: list[tuple[float, dict]] = []
        if self.camera is None or self._rel is None:
            return done
        while self._frames and self._poses and self._frames[0] <= self._poses[-1][0]:
            t = self._frames.popleft()
            pose = self._pose_at(t)
            if pose is not None:
                row = truth_row(t, self.sc, self.camera, *pose, *self._rel)
                self.rows.append(row)
                if self._on_frame is not None:
                    whole = self._join.add_row(round(t * 1e6), row)
                    if whole is not None:
                        done.append((t, whole))
        return done

    def _pose_at(self, t: float) -> tuple[np.ndarray, np.ndarray] | None:
        poses = list(self._poses)
        for i in range(len(poses) - 1, 0, -1):  # newest first: frames wait for at most a few poses
            (t0, p0, q0), (t1, p1, q1) = poses[i - 1], poses[i]
            if t0 <= t <= t1:
                f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                return p0 + f * (p1 - p0), nlerp(q0, q1, f)
        return None
