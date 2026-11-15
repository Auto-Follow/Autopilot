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

Segmentation frames are read from their raw bytes (read_image), not parsed by the protobuf module: Gazebo 8's
segmentation camera (gz-sensors 8.2.2) appends one more `frame_id` entry to the header of every frame it publishes and
never clears them (~51 bytes a frame, ~2000 entries after a minute of recording). Parsed whole with the pure Python
protobuf the tools use, a frame took longer and longer and filled the heap; full garbage collections came every
~0.3 s and after ~70 s of recording the gz-transport thread fell behind the 30 Hz frames: the referee's rows reached
the tracking side after the model's results and no re-lock was possible (spec 2026-11-10-m06-sim-ortami,
implementation/gorev-grubu-17-on-kamera-acisi.md, "Canlı hakem akışı"). read_image skips the header's entries unread.
"""

import math
import os
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")  # protobuf 7.x in ~/.local
os.environ.setdefault("GZ_IP", "127.0.0.1")  # same as calistir.sh

import numpy as np  # noqa: E402
from gz.msgs10.camera_info_pb2 import CameraInfo  # noqa: E402
from gz.msgs10.pose_v_pb2 import Pose_V  # noqa: E402
from gz.transport13 import Node, SubscribeOptions  # noqa: E402

from hedef import OTHER_LABEL, TARGET_LABEL, Scenario  # noqa: E402
from kamera import ENU_TO_NED, FLU_TO_FRD, GZ_CAMERA_TO_OPTICAL, Camera, deviation, quat_to_dcm  # noqa: E402

DRONE_MODEL = "x500_tez_0"
CAMERA_LINK = "camera_link"
CAMERA_TOPIC = "/x500_tez/kamera"
# Mingfei actor; the "in view" point and the LOS use the body centre
TARGET_POINTS = (("ayak", 0.0), ("merkez", 0.9), ("bas", 1.75))  # [m] above ground
POSE_HISTORY = 100  # poses kept for interpolation (2 s at 50 Hz)
SEG_TOPIC = "/x500_tez/kamera_seg/labels_map"  # models/x500_tez: segmentation camera, half resolution
IMAGE_TYPE = "gz.msgs.Image"
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


@dataclass(frozen=True)
class ImageFrame:
    """What the referee needs of a gz.msgs.Image, read from its raw bytes (read_image)."""

    t: float  # [s sim] header stamp
    width: int
    height: int
    data: memoryview  # the pixels as sent, not copied


# gz.msgs field numbers: Image {Header header = 1; uint32 width = 2; uint32 height = 3; bytes data = 5; ...},
# Header {Time stamp = 1; repeated Map data = 2}, Time {int64 sec = 1; int32 nsec = 2}
WIRE_VARINT, WIRE_FIXED64, WIRE_LEN, WIRE_FIXED32 = 0, 1, 2, 5


def _varint(buf: memoryview, pos: int, end: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        if pos >= end or shift > 63:
            raise ValueError("gz.msgs.Image kesik ya da bozuk (varint)")
        byte = buf[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, pos
        shift += 7


def _fields(buf: memoryview, pos: int, end: int) -> Iterator[tuple[int, int, int, int]]:
    """(field number, wire type, value, end of the field) of the fields in buf[pos:end]; for a length-delimited field
    value is where its bytes start. Fields this reader does not need are skipped by their wire type."""
    while pos < end:
        tag, pos = _varint(buf, pos, end)
        number, wire = tag >> 3, tag & 7
        if wire == WIRE_VARINT:
            value, pos = _varint(buf, pos, end)
            yield number, wire, value, pos
            continue
        if wire == WIRE_LEN:
            size, start = _varint(buf, pos, end)
            pos = start + size
            value = start
        elif wire == WIRE_FIXED64:
            value, pos = pos, pos + 8
        elif wire == WIRE_FIXED32:
            value, pos = pos, pos + 4
        else:
            raise ValueError(f"gz.msgs.Image bozuk: tel türü {wire}")
        if pos > end:
            raise ValueError("gz.msgs.Image kesik: alan mesajın sonunu aşıyor")
        yield number, wire, value, pos


def _signed(value: int) -> int:
    """int64 / int32 varints carry negative numbers as 64-bit two's complement."""
    return value - (1 << 64) if value >= 1 << 63 else value


def _stamp(buf: memoryview, pos: int, end: int) -> float | None:
    """[s] header.stamp of a Header's bytes, None if it has none. Gazebo (C++) writes the stamp before the data
    entries: the entries after it are never looked at."""
    for number, wire, value, field_end in _fields(buf, pos, end):
        if number == 1 and wire == WIRE_LEN:
            sec = nsec = 0
            for n, w, v, _ in _fields(buf, value, field_end):
                if w == WIRE_VARINT and n == 1:
                    sec = _signed(v)
                elif w == WIRE_VARINT and n == 2:
                    nsec = _signed(v)
            return sec + nsec * 1e-9
    return None


def read_image(raw: bytes | memoryview) -> ImageFrame:
    """The header stamp, size and pixels of a serialized gz.msgs.Image without the protobuf module; the header's
    data entries are skipped unread (Gazebo's segmentation camera piles them up, see the module text). ValueError
    if the bytes are cut short or not protobuf."""
    buf = memoryview(raw).cast("B")
    t, width, height, data = 0.0, 0, 0, memoryview(b"")
    for number, wire, value, end in _fields(buf, 0, len(buf)):
        if number == 1 and wire == WIRE_LEN:
            stamp = _stamp(buf, value, end)
            t = stamp if stamp is not None else t
        elif number == 2 and wire == WIRE_VARINT:
            width = value
        elif number == 3 and wire == WIRE_VARINT:
            height = value
        elif number == 5 and wire == WIRE_LEN:
            data = buf[value:end]
    return ImageFrame(t, width, height, data)


def label_channel(frame: ImageFrame) -> np.ndarray:
    """(h, w) label per pixel of an instance segmentation frame: the label is in the third channel (the first two
    encode the instance). ValueError if the pixels do not fill width x height x 3."""
    if len(frame.data) != frame.width * frame.height * 3:
        raise ValueError(f"segmentasyon karesi boyutu tutmuyor: {len(frame.data)} bayt, {frame.width}x{frame.height}x3")
    return np.frombuffer(frame.data, np.uint8).reshape(frame.height, frame.width, 3)[:, :, 2]


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
        node: object | None = None,
    ) -> None:
        """on_frame(t, row, ready): every camera frame for the tracking side, `row` = the referee's row joined with
        its segmentation frame (None outside the recording), `ready` = monotonic time it became known. Runs in a
        gz-transport thread: it must return quickly. node: the gz-transport Node (a stand-in in tests)."""
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
        self._node = node if node is not None else Node()
        self._node.subscribe(Pose_V, f"/world/{world}/dynamic_pose/info", self._on_pose)
        self._node.subscribe(CameraInfo, f"{CAMERA_TOPIC}/camera_info", self._on_info)

    @property
    def join_dropped(self) -> int:
        """Halves of referee frames whose other half never came (so on_frame never got that frame)."""
        with self._lock:
            return self._join.dropped

    def start(self) -> None:
        # segmentation frames only from now on (Gazebo renders them only while someone listens), raw: read_image
        self._node.subscribe_raw(SEG_TOPIC, self._on_seg, IMAGE_TYPE, SubscribeOptions())
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

    def _on_seg(self, raw: bytes, _info: object) -> None:
        if not self._recording:
            return
        try:
            frame = read_image(raw)
            labels = label_channel(frame)
        except ValueError as e:  # the transport thread keeps running; the run reports it
            if len(self.errors) < 20:
                self.errors.append(f"segmentasyon karesi okunamadı: {e}")
            return
        t = frame.t
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
