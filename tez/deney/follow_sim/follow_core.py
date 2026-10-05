"""Core logic for the Follow Me simulation panel.

- TargetMover: moves the `hedef` model in Gazebo (kinematic, via /world/<w>/set_pose).
- VehicleLink: MAVLink link to PX4 SITL: FOLLOW_TARGET, MANUAL_CONTROL, mode/arm commands.
- Geometry: camera image plane, LOS (slant) ray, height line and ground intersections.
- SceneDrawer: draws that geometry in Gazebo with markers.
- Geolocation: target lat/lon from the detected pixel and the PX4 EKF pose (geolocation.py).
- LinkImpairment: delay / loss on the FOLLOW_TARGET path (Wi-Fi or Vision latency study).

Gazebo world frame is ENU (x = East, y = North, z = Up). The gz camera frame is x forward, y left, z up.
"""
import os

# System gz python bindings were generated for an older protobuf than the one in ~/.local.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import json
import math
import multiprocessing
import re
import socket
import threading
import random
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from gz.math7 import Angle, Quaterniond, SphericalCoordinates, Vector3d
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.marker_pb2 import Marker
from gz.msgs10.marker_v_pb2 import Marker_V
from gz.msgs10.pose_pb2 import Pose
from gz.msgs10.pose_v_pb2 import Pose_V
from gz.transport13 import Node, SubscribeOptions
from pymavlink import mavutil

import geolocation as geoloc

HERE = Path(__file__).resolve().parent

WORLD = os.environ.get("PX4_GZ_WORLD", "renkli_duz")
DRONE_MODEL = os.environ.get("FOLLOW_DRONE_MODEL", "x500_mono_cam_0")
TARGET_MODEL = "hedef"
MAVLINK_URL = os.environ.get("FOLLOW_MAVLINK_URL", "udpin:0.0.0.0:14540")

# Camera mount and intrinsics: keep in sync with PX4 models x500_mono_cam and mono_cam (Camera Module 3).
CAMERA_OFFSET = (0.12, 0.03, 0.242)  # camera_link position in base_link [m]
CAMERA_PITCH_DEG = float(os.environ.get("FOLLOW_CAMERA_PITCH_DEG") or 0.0)  # baslat.sh --egim; 0 = x500_mono_cam
CAMERA_PITCH_RAD = math.radians(CAMERA_PITCH_DEG)  # positive = looking down
HFOV_RAD = 1.1519
IMAGE_W, IMAGE_H = 2304, 1296
# x500_base puts base_link (IMU, the point the EKF tracks) 0.24 m above the model frame that Gazebo reports, and
# CAMERA_OFFSET is in the model frame. Geolocation needs the camera relative to base_link, in PX4 body FRD.
BASE_LINK_Z_IN_MODEL = 0.24
CAMERA = geoloc.CameraModel.from_hfov(
    HFOV_RAD, IMAGE_W, IMAGE_H, pitch_down_deg=CAMERA_PITCH_DEG,
    offset_frd=(CAMERA_OFFSET[0], -CAMERA_OFFSET[1], -(CAMERA_OFFSET[2] - BASE_LINK_Z_IN_MODEL)))
IMAGE_PLANE_DIST = 1.2  # where the image plane is drawn in front of the camera [m]

TARGET_START = (8.0, 0.0)  # must match the hedef pose in worlds/renkli_duz.sdf
TARGET_HEIGHT_M = 1.79  # models/hedef: feet at z = 0, top of the head at 1.79 m
AREA_LIMIT = 95.0

# Ground control station and Wi-Fi video link (option A). Must match the yer_istasyonu / menzil_halkasi poses
# in worlds/renkli_duz.sdf. The range is the planning limit, not a radio model.
GCS_POSITION = (-5.0, 0.0, 1.0)  # antenna/laptop position [m]
LINK_RANGE_M = 100.0
LINK_WARN_M = 80.0

# Vision mode: FOLLOW_TARGET only while the camera sees the target.
DETECTION_PORT = 5610  # per-frame detection results from video/goruntu_yayini.py
DETECTION_FRESH_S = 0.5  # older results -> fall back to the geometric visibility check
PX4_TARGET_STALE_S = 3.0  # PX4 TargetEstimator GPS_MESSAGE_STALE_TIMEOUT_MS: extrapolation stops after this
VISION_DEMO_HEIGHT_M = 2.5  # FLW_TGT_HT at which the level camera still sees the target at 8 m (atan(2.5/8) < 20 deg)

# Geolocation: flat ground. The EKF origin is set while the drone stands on the ground, so the ground plane is
# BODY_HEIGHT_LANDED_M below it: base_link height when landed (Gazebo: model z -0.013 m at rest + 0.24 m).
# On the real drone: measure base_link (Pixhawk) height above the ground with the drone on its landing gear.
BODY_HEIGHT_LANDED_M = 0.227
GEO_POSE_MAX_GAP_S = 0.15  # no fix if the EKF pose history does not cover the frame time within this

# Target path for repeatable experiments: (kind, ...) with kind in walk(m, m/s), turn(deg), wait(s), arc(deg, R, m/s)
PARKUR = [("walk", 20.0, 1.5), ("turn", 90.0), ("walk", 20.0, 1.5), ("wait", 5.0), ("walk", 20.0, 3.0),
          ("turn", 180.0), ("walk", 20.0, 1.5), ("arc", 180.0, 10.0, 1.5), ("wait", 5.0)]
TURN_RATE_DEG_S = 90.0

# Fixed follow geometry per camera, chosen by deney.py optimum_egik / optimum_duz (05.10.2026, 2 runs each, camera
# fixes without velocity): tilted (45 deg) 10 m high / 10 m back, level camera 8 m / 30 m. PX4 Follow Me unchanged.
FOLLOW_HT_DST = (10.0, 10.0) if CAMERA_PITCH_DEG >= 20 else (8.0, 30.0)
FOLLOW_DEFAULTS = {"FLW_TGT_DST": FOLLOW_HT_DST[1], "FLW_TGT_HT": FOLLOW_HT_DST[0], "FLW_TGT_FA": 180.0,
                   "FLW_TGT_ALT_M": 0, "FLW_TGT_MAX_VEL": 5.0}  # keep the target on the 200 m colorful area [m]

# PX4 custom modes (main_mode, sub_mode)
MODE_TAKEOFF = (4, 2)
MODE_HOLD = (4, 3)
MODE_RTL = (4, 5)
MODE_LAND = (4, 6)
MODE_FOLLOW = (4, 8)
MAIN_MODE_NAMES = {1: "Manual", 2: "Altitude", 3: "Position", 5: "Acro", 6: "Offboard", 7: "Stabilized"}
AUTO_SUB_MODE_NAMES = {1: "Hazır", 2: "Kalkış", 3: "Bekle (Hold)", 4: "Görev", 5: "Eve dön (RTL)", 6: "İniş",
                       8: "Follow Me", 9: "Hassas iniş"}


def read_world_origin(world=WORLD):
    """Return (lat_deg, lon_deg, elevation_m) from the world file, falling back to the PX4 default origin."""
    lat, lon, elev = 47.397971057728974, 8.546163739800146, 0.0
    path = HERE / "worlds" / f"{world}.sdf"
    if path.exists():
        text = path.read_text(encoding="utf-8-sig")
        for tag in ("latitude_deg", "longitude_deg", "elevation"):
            m = re.search(rf"<{tag}>\s*([-\d.eE+]+)\s*</{tag}>", text)
            if m:
                value = float(m.group(1))
                lat, lon, elev = ((value, lon, elev) if tag == "latitude_deg" else
                                  (lat, value, elev) if tag == "longitude_deg" else (lat, lon, value))
    return lat, lon, elev


# ----------------------------------------------------------------------------------------------- geometry
def vec(x, y, z):
    return Vector3d(float(x), float(y), float(z))


def camera_pose(drone_pos, drone_rot):
    """World position and rotation of the camera optical center."""
    pos = drone_pos + drone_rot * vec(*CAMERA_OFFSET)
    rot = drone_rot * Quaterniond(0.0, CAMERA_PITCH_RAD, 0.0)
    return pos, rot


@dataclass
class Geometry:
    cam_pos: Vector3d
    height: float  # camera height above the flat ground [m]
    theta_deg: float  # angle between straight down and the LOS ray
    slant: float  # h / cos(theta)
    nadir: Vector3d  # ground intersection of the height line
    ground_hit: Vector3d  # ground intersection of the LOS ray (target foot point)
    plane_corners: list  # image plane corners: top-left, top-right, bottom-right, bottom-left
    pierce: Vector3d = None  # where the LOS ray crosses the image plane (None if behind the camera)
    pixel: tuple = None  # (u, v) in pixels, OpenCV convention (origin top-left)
    in_frame: bool = False
    horizontal_dist: float = 0.0


def compute_geometry(drone_pos, drone_rot, target_xy):
    cam_pos, cam_rot = camera_pose(drone_pos, drone_rot)
    fwd, left, up = cam_rot * vec(1, 0, 0), cam_rot * vec(0, 1, 0), cam_rot * vec(0, 0, 1)

    ground_hit = vec(target_xy[0], target_xy[1], 0.0)
    nadir = vec(cam_pos.x(), cam_pos.y(), 0.0)
    ray = ground_hit - cam_pos
    slant_measured = ray.length()
    height = cam_pos.z()
    cos_theta = (-ray.z() / slant_measured) if slant_measured > 1e-6 else 1.0
    theta_deg = math.degrees(math.acos(max(-1.0, min(1.0, cos_theta))))
    slant = height / cos_theta if cos_theta > 1e-3 else float("inf")

    half_w = IMAGE_PLANE_DIST * math.tan(HFOV_RAD / 2)
    half_h = half_w * IMAGE_H / IMAGE_W
    center = cam_pos + fwd * IMAGE_PLANE_DIST
    corners = [center + left * half_w + up * half_h, center - left * half_w + up * half_h,
               center - left * half_w - up * half_h, center + left * half_w - up * half_h]

    geo = Geometry(cam_pos=cam_pos, height=height, theta_deg=theta_deg, slant=slant, nadir=nadir,
                   ground_hit=ground_hit, plane_corners=corners,
                   horizontal_dist=math.hypot(ray.x(), ray.y()))

    depth = ray.dot(fwd)
    if depth > 1e-6:
        geo.pierce = cam_pos + ray * (IMAGE_PLANE_DIST / depth)
        focal_px = (IMAGE_W / 2) / math.tan(HFOV_RAD / 2)
        u = IMAGE_W / 2 - focal_px * ray.dot(left) / depth
        v = IMAGE_H / 2 - focal_px * ray.dot(up) / depth
        geo.pixel = (u, v)
        geo.in_frame = 0 <= u < IMAGE_W and 0 <= v < IMAGE_H
    return geo


# ----------------------------------------------------------------------------------------------- gazebo
def _pose_listener(world, drone_model, shared, stop):
    """Runs in its own process. gz-transport python deadlocks a blocking request() while subscription
    callbacks keep arriving in the same process, so subscriptions live here and share the latest values.
    shared: [drone x y z qw qx qy qz monotonic_stamp sim_time]"""
    os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
    node = Node()

    def on_poses(msg):
        for p in msg.pose:
            if p.name == drone_model:
                o = p.orientation
                sim_time = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
                with shared.get_lock():
                    shared[0:9] = [p.position.x, p.position.y, p.position.z, o.w, o.x, o.y, o.z, time.monotonic(),
                                   sim_time]
                return

    # dynamic_pose/info arrives at the physics rate; the pure-python protobuf parser cannot keep up, so throttle.
    opts = SubscribeOptions()
    opts.msgs_per_sec = 30
    node.subscribe(Pose_V, f"/world/{world}/dynamic_pose/info", on_poses, opts)
    stop.wait()


class GzWorld:
    """Pose/marker service calls; the drone pose comes from a listener process."""

    def __init__(self, world=WORLD):
        self.world = world
        ctx = multiprocessing.get_context("fork")  # fork before any gz Node exists in this process
        self._shared = ctx.Array("d", 9)
        self._stop = ctx.Event()
        self._listener = ctx.Process(target=_pose_listener, args=(world, DRONE_MODEL, self._shared, self._stop),
                                     daemon=True)
        self._listener.start()
        self.node = Node()

    def close(self):
        self._stop.set()
        self._listener.join(timeout=2)

    def _read(self):
        with self._shared.get_lock():
            return list(self._shared)

    def drone_pose(self):
        d = self._read()
        if d[7] == 0.0 or time.monotonic() - d[7] > 2.0:
            return None
        return vec(d[0], d[1], d[2]), Quaterniond(d[3], d[4], d[5], d[6])

    def sim_time(self):
        """Current Gazebo time, extrapolated from the last pose message (None before the first one)."""
        d = self._read()
        if d[7] == 0.0:
            return None
        return d[8] + (time.monotonic() - d[7])

    def set_model_pose(self, name, x, y, z, yaw):
        req = Pose()
        req.name = name
        req.position.x, req.position.y, req.position.z = x, y, z
        req.orientation.w, req.orientation.z = math.cos(yaw / 2), math.sin(yaw / 2)
        ok, _ = self.node.request(f"/world/{self.world}/set_pose", req, Pose, Boolean, 500)
        return ok

    def set_model_poses(self, poses):
        """poses: {name: (x, y, z, yaw)} in one service call."""
        req = Pose_V()
        for name, (x, y, z, yaw) in poses.items():
            p = req.pose.add()
            p.name = name
            p.position.x, p.position.y, p.position.z = x, y, z
            p.orientation.w, p.orientation.z = math.cos(yaw / 2), math.sin(yaw / 2)
        ok, _ = self.node.request(f"/world/{self.world}/set_pose_vector", req, Pose_V, Boolean, 500)
        return ok

    def send_markers(self, markers):
        req = Marker_V()
        req.marker.extend(markers)
        ok, _ = self.node.request("/marker_array", req, Marker_V, Boolean, 500)
        return ok


# ----------------------------------------------------------------------------------------------- markers
NS = "follow_viz"
COLORS = {
    "plane": (0.25, 0.55, 1.0, 0.35),
    "plane_edge": (0.15, 0.4, 1.0, 1.0),
    "frustum": (0.6, 0.75, 1.0, 1.0),
    "ray": (1.0, 0.55, 0.0, 1.0),
    "height": (0.0, 0.85, 0.3, 1.0),
    "ground": (1.0, 1.0, 1.0, 1.0),
    "hit": (1.0, 0.3, 0.0, 1.0),
    "nadir": (0.0, 0.7, 0.2, 1.0),
    "pierce": (1.0, 0.0, 0.0, 1.0),
}


def _base(mid, mtype, color):
    m = Marker()
    m.ns, m.id, m.action, m.type = NS, mid, Marker.ADD_MODIFY, mtype
    r, g, b, a = COLORS[color]
    for c in (m.material.ambient, m.material.diffuse, m.material.emissive):
        c.r, c.g, c.b, c.a = r, g, b, a
    return m


def _set_point(p, v):
    p.x, p.y, p.z = v.x(), v.y(), v.z()


def segment(mid, a, b, radius, color):
    """Thick line as a cylinder (ogre2 ignores line widths)."""
    m = _base(mid, Marker.CYLINDER, color)
    d = b - a
    length = d.length()
    _set_point(m.pose.position, (a + b) * 0.5)
    q = Quaterniond()
    if length > 1e-6:
        axis = vec(0, 0, 1).cross(d / length)
        angle = math.acos(max(-1.0, min(1.0, (d / length).z())))
        if axis.length() > 1e-9:
            q = Quaterniond(axis.normalized(), angle)
        elif d.z() < 0:
            q = Quaterniond(vec(1, 0, 0), math.pi)
    m.pose.orientation.w, m.pose.orientation.x, m.pose.orientation.y, m.pose.orientation.z = q.w(), q.x(), q.y(), q.z()
    m.scale.x = m.scale.y = 2 * radius
    m.scale.z = max(length, 1e-3)
    return m


def sphere(mid, center, radius, color):
    m = _base(mid, Marker.SPHERE, color)
    _set_point(m.pose.position, center)
    m.pose.orientation.w = 1.0
    m.scale.x = m.scale.y = m.scale.z = 2 * radius
    return m


def quad(mid, corners, color):
    m = _base(mid, Marker.TRIANGLE_LIST, color)
    m.pose.orientation.w = 1.0
    m.scale.x = m.scale.y = m.scale.z = 1.0
    a, b, c, d = corners
    for v in (a, b, c, a, c, d, a, c, b, a, d, c):  # both faces
        _set_point(m.point.add(), v)
    return m


def build_markers(geo):
    cam = geo.cam_pos
    markers = [
        quad(1, geo.plane_corners, "plane"),
        segment(10, geo.plane_corners[0], geo.plane_corners[1], 0.008, "plane_edge"),
        segment(11, geo.plane_corners[1], geo.plane_corners[2], 0.008, "plane_edge"),
        segment(12, geo.plane_corners[2], geo.plane_corners[3], 0.008, "plane_edge"),
        segment(13, geo.plane_corners[3], geo.plane_corners[0], 0.008, "plane_edge"),
        *[segment(20 + i, cam, c, 0.004, "frustum") for i, c in enumerate(geo.plane_corners)],
        segment(30, cam, geo.ground_hit, 0.035, "ray"),
        segment(31, cam, geo.nadir, 0.035, "height"),
        segment(32, geo.nadir, geo.ground_hit, 0.02, "ground"),
        sphere(40, geo.ground_hit, 0.25, "hit"),
        sphere(41, geo.nadir, 0.25, "nadir"),
    ]
    if geo.pierce is not None:
        markers.append(sphere(42, geo.pierce, 0.05, "pierce"))
    else:
        markers.append(sphere(42, cam, 0.001, "pierce"))
    return markers


def delete_all_markers(gz):
    m = Marker()
    m.ns, m.action = NS, Marker.DELETE_ALL
    return gz.send_markers([m])


# ----------------------------------------------------------------------------------------------- target
TARGET_PATTERNS = ("dur", "gidip_gel", "daire", "kare", "klavye", "parkur")


class TargetMover:
    """Kinematic walking target. Units: m, s, rad (ENU yaw, 0 = East)."""

    def __init__(self, x=TARGET_START[0], y=TARGET_START[1], yaw=0.0):
        self.x, self.y, self.yaw = x, y, yaw
        self.vx = self.vy = 0.0
        self.speed = 1.5
        self.pattern = "dur"
        self.keys = set()  # "ileri", "geri", "sol", "sag" for the keyboard pattern
        self._leg = 0.0  # distance walked on the current straight leg
        self._seg = 0  # parkur: current segment index
        self._seg_done = 0.0  # parkur: progress in the current segment (m, deg or s)
        self.parkur_finished = False
        self.parkur_speed_scale = 1.0  # deney.py: faster target (walk/run/arc speeds times this)
        self._lock = threading.Lock()

    def set_pattern(self, pattern):
        with self._lock:
            self.pattern = pattern
            self._leg = 0.0
            if pattern == "parkur":  # start towards the area center so repeated runs stay on the colored ground
                self._seg, self._seg_done, self.parkur_finished = 0, 0.0, False
                if math.hypot(self.x, self.y) > 5.0:
                    self.yaw = math.atan2(-self.y, -self.x)

    def step(self, dt):
        with self._lock:
            x0, y0 = self.x, self.y
            v = self.speed
            if self.pattern == "gidip_gel":
                self._walk(v * dt)
                if self._leg >= 30.0:
                    self.yaw, self._leg = self.yaw + math.pi, 0.0
            elif self.pattern == "daire":
                radius = 15.0
                self.yaw += v * dt / radius
                self._walk(v * dt)
            elif self.pattern == "kare":
                self._walk(v * dt)
                if self._leg >= 30.0:
                    self.yaw, self._leg = self.yaw + math.pi / 2, 0.0
            elif self.pattern == "parkur":
                self._parkur_step(dt)
            elif self.pattern == "klavye":
                if "sol" in self.keys:
                    self.yaw += math.radians(60) * dt
                if "sag" in self.keys:
                    self.yaw -= math.radians(60) * dt
                if "ileri" in self.keys:
                    self._walk(v * dt)
                elif "geri" in self.keys:
                    self._walk(-v * dt)
            self.yaw = math.atan2(math.sin(self.yaw), math.cos(self.yaw))
            if abs(self.x) > AREA_LIMIT or abs(self.y) > AREA_LIMIT:  # turn back towards the center
                self.x = max(-AREA_LIMIT, min(AREA_LIMIT, self.x))
                self.y = max(-AREA_LIMIT, min(AREA_LIMIT, self.y))
                self.yaw = math.atan2(-self.y, -self.x)
            self.vx, self.vy = ((self.x - x0) / dt, (self.y - y0) / dt) if dt > 0 else (0.0, 0.0)
            return self.x, self.y, self.yaw

    def _parkur_step(self, dt):
        if self._seg >= len(PARKUR):
            self.pattern, self.parkur_finished = "dur", True
            return
        kind, *a = PARKUR[self._seg]
        if kind == "walk":
            step = min(a[1] * self.parkur_speed_scale * dt, a[0] - self._seg_done)
            self._walk(step)
            total = a[0]
        elif kind == "turn":
            step = min(TURN_RATE_DEG_S * dt, abs(a[0]) - self._seg_done)
            self.yaw += math.copysign(math.radians(step), a[0])
            total = abs(a[0])
        elif kind == "arc":  # left arc: a = (deg, radius, speed)
            step = min(math.degrees(a[2] * self.parkur_speed_scale * dt / a[1]), a[0] - self._seg_done)
            self.yaw += math.radians(step)
            self._walk(math.radians(step) * a[1])
            total = a[0]
        else:  # wait
            step, total = min(dt, a[0] - self._seg_done), a[0]
        self._seg_done += step
        if self._seg_done >= total - 1e-9:
            self._seg, self._seg_done = self._seg + 1, 0.0

    def _walk(self, dist):
        self.x += dist * math.cos(self.yaw)
        self.y += dist * math.sin(self.yaw)
        self._leg += abs(dist)

    def state(self):
        with self._lock:
            return self.x, self.y, self.yaw, self.vx, self.vy


# ----------------------------------------------------------------------------------------------- mavlink
@dataclass
class VehicleState:
    connected: bool = False
    armed: bool = False
    mode: str = "—"
    rel_alt: float = float("nan")
    last_heartbeat: float = 0.0
    messages: list = field(default_factory=list)


class VehicleLink:
    """MAVLink to PX4 SITL (offboard port). Sends HEARTBEAT, FOLLOW_TARGET and MANUAL_CONTROL."""

    def __init__(self, url=MAVLINK_URL):
        self.mav = mavutil.mavlink_connection(url, source_system=250, source_component=191, dialect="common")
        self.state = VehicleState()
        self.sticks = {"roll": 0.0, "pitch": 0.0, "throttle": 0.0, "yaw": 0.0}  # all in [-1, 1], 0 = centered
        self._send_lock = threading.Lock()
        self._defaults_applied = False
        # EKF pose history for geolocation, keyed by PX4 time (s): attitude (w, x, y, z) and local NED position
        self.att_hist = deque(maxlen=300)
        self.pos_hist = deque(maxlen=300)
        self.ekf_origin = None  # (lat_deg, lon_deg, alt_m) of the local NED frame (GPS_GLOBAL_ORIGIN)
        self.home_ned = None  # (n, e, d) of the home position in the local frame
        self.boot_time = None  # last PX4 time_boot (s) seen
        self._stop = threading.Event()
        self._rx = threading.Thread(target=self._receive_loop, daemon=True)
        self._rx.start()

    def close(self):
        self._stop.set()

    def _log(self, text):
        self.state.messages.append((time.strftime("%H:%M:%S"), text))
        del self.state.messages[:-50]

    def _receive_loop(self):
        while not self._stop.is_set():
            msg = self.mav.recv_match(blocking=True, timeout=0.5)
            if msg is None:
                if self.state.connected and time.monotonic() - self.state.last_heartbeat > 3.0:
                    self.state.connected = False
                    self._log("PX4 bağlantısı kesildi")
                continue
            if msg.get_srcComponent() != 1:
                continue
            mtype = msg.get_type()
            if mtype == "HEARTBEAT" and msg.type != mavutil.mavlink.MAV_TYPE_GCS:
                if not self.state.connected:
                    self._log("PX4'e bağlanıldı")
                    if not self._defaults_applied:
                        self._defaults_applied = True
                        threading.Thread(target=self.apply_follow_defaults, daemon=True).start()
                self.state.connected = True
                self.state.last_heartbeat = time.monotonic()
                self.state.armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                main, sub = (msg.custom_mode >> 16) & 0xFF, (msg.custom_mode >> 24) & 0xFF
                self.state.mode = (AUTO_SUB_MODE_NAMES.get(sub, f"Auto {sub}") if main == 4
                                   else MAIN_MODE_NAMES.get(main, f"Mod {main}"))
            elif mtype == "GLOBAL_POSITION_INT":
                self.state.rel_alt = msg.relative_alt / 1000.0
            elif mtype == "ATTITUDE_QUATERNION":
                self.boot_time = msg.time_boot_ms / 1000.0
                self.att_hist.append((self.boot_time, (msg.q1, msg.q2, msg.q3, msg.q4)))
            elif mtype == "LOCAL_POSITION_NED":
                self.boot_time = msg.time_boot_ms / 1000.0
                self.pos_hist.append((self.boot_time, (msg.x, msg.y, msg.z)))
            elif mtype == "GPS_GLOBAL_ORIGIN":
                self.ekf_origin = (msg.latitude * 1e-7, msg.longitude * 1e-7, msg.altitude * 1e-3)
            elif mtype == "HOME_POSITION":
                self.home_ned = (msg.x, msg.y, msg.z)
            elif mtype == "STATUSTEXT":
                self._log(f"PX4: {msg.text}")
            elif mtype == "COMMAND_ACK" and msg.result != mavutil.mavlink.MAV_RESULT_ACCEPTED:
                self._log(f"Komut {msg.command} reddedildi (sonuç {msg.result})")

    def _send(self, fn, *args):
        with self._send_lock:
            fn(*args)

    def request_streams(self):
        """High-rate EKF attitude/position for geolocation, plus the EKF origin and home (until received)."""
        for msg_id, hz in ((mavutil.mavlink.MAVLINK_MSG_ID_ATTITUDE_QUATERNION, 50),
                           (mavutil.mavlink.MAVLINK_MSG_ID_LOCAL_POSITION_NED, 50)):
            self.command(mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, msg_id, 1e6 / hz)
        if self.ekf_origin is None:
            self.command(mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE, mavutil.mavlink.MAVLINK_MSG_ID_GPS_GLOBAL_ORIGIN)
        if self.home_ned is None:
            self.command(mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE, mavutil.mavlink.MAVLINK_MSG_ID_HOME_POSITION)

    def pose_at(self, t):
        """EKF (attitude quaternion, NED position) interpolated at PX4 time t [s], or None."""
        q = _interpolate(self.att_hist, t)
        p = _interpolate(self.pos_hist, t)
        if q is None or p is None:
            return None
        n = math.sqrt(sum(c * c for c in q))
        return tuple(c / n for c in q), p

    def send_heartbeat(self):
        self._send(self.mav.mav.heartbeat_send, mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                   0, 0, mavutil.mavlink.MAV_STATE_ACTIVE)

    def send_manual_control(self):
        s = self.sticks
        # MANUAL_CONTROL: x = pitch, y = roll, r = yaw in [-1000, 1000]; z = throttle in [0, 1000] (500 = centered)
        self._send(self.mav.mav.manual_control_send, self.mav.target_system or 1,
                   int(s["pitch"] * 1000), int(s["roll"] * 1000), int(500 + s["throttle"] * 500),
                   int(s["yaw"] * 1000), 0)

    def send_follow_target(self, lat_deg, lon_deg, alt_amsl, v_north=None, v_east=None):
        """Without a velocity (None) the vel field is NaN: PX4 ignores est_capabilities and would fuse a 0 as
        a real "target is standing still" measurement, while NaN makes its estimator derive the velocity
        from successive positions."""
        if v_north is None or v_east is None:
            capabilities, vel = 0b01, [math.nan] * 3  # position only
        else:
            capabilities, vel = 0b11, [v_north, v_east, 0.0]  # position + velocity
        self._send(self.mav.mav.follow_target_send, int(time.monotonic() * 1000) & 0xFFFFFFFFFFFFFFFF,
                   capabilities, int(lat_deg * 1e7), int(lon_deg * 1e7), float(alt_amsl),
                   vel, [0.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0],
                   [0.0, 0.0, 0.0], 0)

    def command(self, cmd, *params):
        p = list(params) + [0.0] * (7 - len(params))
        self._send(self.mav.mav.command_long_send, self.mav.target_system or 1, 1, cmd, 0, *p)

    def set_mode(self, mode):
        main, sub = mode
        self.command(mavutil.mavlink.MAV_CMD_DO_SET_MODE, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                     main, sub)

    def arm(self, arm=True):
        self.command(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1.0 if arm else 0.0)

    def set_param(self, name, value):
        ptype = mavutil.mavlink.MAV_PARAM_TYPE_INT32 if isinstance(value, int) else mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        if ptype == mavutil.mavlink.MAV_PARAM_TYPE_INT32:  # PX4 uses bytewise int encoding in PARAM_SET
            import struct
            value = struct.unpack("<f", struct.pack("<i", value))[0]
        self._send(self.mav.mav.param_set_send, self.mav.target_system or 1, 1, name.encode(), float(value), ptype)

    def apply_follow_defaults(self):
        """PX4 v1.17 Follow Me defaults (docs): 8 m behind, 8 m above home, from directly behind, 2D altitude."""
        for name, value in FOLLOW_DEFAULTS.items():
            self.set_param(name, value)
            time.sleep(0.05)
        self._log(f"Follow Me parametreleri varsayılana ayarlandı (HT={FOLLOW_HT_DST[0]:g} m, "
                  f"DST={FOLLOW_HT_DST[1]:g} m, FA=180°, ALT_M=0)")

    def takeoff(self):
        self.set_mode(MODE_TAKEOFF)
        time.sleep(0.3)
        self.arm(True)


def _interpolate(hist, t):
    """Linear interpolation in a [(time, tuple)] history; quaternions are normalized by the caller."""
    samples = list(hist)
    if not samples or t < samples[0][0] - GEO_POSE_MAX_GAP_S or t > samples[-1][0] + GEO_POSE_MAX_GAP_S:
        return None
    for (t0, a), (t1, b) in zip(reversed(samples[:-1]), reversed(samples[1:])):
        if t0 <= t <= t1:
            if t1 - t0 > GEO_POSE_MAX_GAP_S:
                return None
            w = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            if len(a) == 4 and sum(x * y for x, y in zip(a, b)) < 0:  # same hemisphere for quaternions
                b = tuple(-x for x in b)
            return tuple(x + w * (y - x) for x, y in zip(a, b))
    return samples[-1][1] if t > samples[-1][0] else samples[0][1]


class LinkImpairment:
    """Delay and packet loss on a message path (FOLLOW_TARGET). Loss is a Gilbert-Elliott two-state channel: the
    average loss rate is `loss`, losses come in bursts of `burst` messages on average (1 = independent)."""

    def __init__(self):
        self.delay_s = 0.0
        self.loss = 0.0
        self.burst = 1.0
        self._bad = False
        self._queue = deque()
        self.submitted = self.dropped = 0
        self._lock = threading.Lock()

    def active(self):
        return self.delay_s > 0 or self.loss > 0

    def _lost(self):
        if self.loss <= 0:
            return False
        if self.burst <= 1.0:
            return random.random() < self.loss
        p_bad_to_good = 1.0 / self.burst
        p_good_to_bad = min(1.0, self.loss * p_bad_to_good / max(1e-6, 1.0 - self.loss))
        self._bad = (random.random() >= p_bad_to_good) if self._bad else (random.random() < p_good_to_bad)
        return self._bad

    def submit(self, now, send):
        with self._lock:
            self.submitted += 1
            if self._lost():
                self.dropped += 1
                return
            self._queue.append((now + self.delay_s, send))

    def pump(self, now):
        """Sends what is due; returns how many messages were delivered."""
        due = []
        with self._lock:
            while self._queue and self._queue[0][0] <= now:
                due.append(self._queue.popleft()[1])
        for send in due:
            send()
        return len(due)


class DetectionListener:
    """Latest detection result of video/goruntu_yayini.py ({"seen": bool, "u", "v"}), received as UDP JSON."""

    def __init__(self, port=DETECTION_PORT):
        self.last = None
        self.last_time = 0.0
        self._stop = threading.Event()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self._sock.bind(("127.0.0.1", port))
        except OSError:  # another panel owns the port: only the geometric check is available
            self._sock.close()
            self._sock = None
            return
        self._sock.settimeout(0.5)
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while not self._stop.is_set():
            try:
                data = self._sock.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                self.last = json.loads(data)
                self.last_time = time.monotonic()
            except ValueError:
                pass

    def fresh(self):
        return self.last if self.last is not None and time.monotonic() - self.last_time < DETECTION_FRESH_S else None

    def close(self):
        self._stop.set()
        if self._sock is not None:
            self._sock.close()


# ----------------------------------------------------------------------------------------------- runner
@dataclass
class GeoFix:
    """Target position computed from one camera frame."""
    stamp: float  # monotonic time the fix was computed
    sim_time: float  # camera frame time (= PX4 time in SITL lockstep)
    lat: float
    lon: float
    north: float  # EKF local NED [m]
    east: float
    slant: float
    depression_deg: float
    height: float
    pixel: tuple
    error_m: float = float("nan")  # horizontal distance to the true target position at the frame time
    error_ne: tuple = (float("nan"), float("nan"))


class TargetKalman:
    """Constant-velocity Kalman filter of the camera fixes in the EKF local frame (north, east): gives FOLLOW_TARGET
    a smoothed position and a velocity, which the camera itself cannot measure.

    The fix error is dominated by the ray-angle error (attitude, timing, pixel). Along the line of sight it grows
    with shallow viewing angles (h / sin^2(depression) per rad), across it with the slant range, so the measurement
    covariance is built in that frame. Fixes far outside the prediction (chi-square gate) are rejected."""

    ANGLE_SIGMA_RAD = math.radians(1.0)
    POS_SIGMA_FLOOR_M = 0.5  # measured fix error in SITL: median 0.33-0.46 m (EKF yaw bias included)
    ACCEL_PSD = 2.0  # white-acceleration process noise [m^2/s^3]
    GATE_CHI2 = 13.8  # 2 dof, p = 0.001
    MAX_GAP_S = 3.0  # no fix for this long -> start over
    MAX_REJECTS = 5  # this many gated fixes in a row -> start over at the newest one

    def __init__(self):
        self.reset()

    def reset(self):
        self.x = None  # [n, e, vn, ve]
        self.P = None
        self.t = None
        self.rejects = 0
        self.rejected_total = 0

    def _measurement_cov(self, fix, drone_ne):
        dn, de = fix.north - drone_ne[0], fix.east - drone_ne[1]
        rng = math.hypot(dn, de)
        u = np.array([dn / rng, de / rng]) if rng > 0.1 else np.array([1.0, 0.0])
        s = math.sin(math.radians(max(fix.depression_deg, 1.0)))
        sig_along = max(self.POS_SIGMA_FLOOR_M, self.ANGLE_SIGMA_RAD * fix.height / s ** 2)
        sig_cross = max(self.POS_SIGMA_FLOOR_M, self.ANGLE_SIGMA_RAD * fix.slant)
        cross = np.array([-u[1], u[0]])
        return sig_along ** 2 * np.outer(u, u) + sig_cross ** 2 * np.outer(cross, cross)

    def _predicted(self, t):
        dt = t - self.t
        F = np.eye(4)
        F[0, 2] = F[1, 3] = dt
        q = self.ACCEL_PSD
        Q1 = np.array([[dt ** 3 / 3, dt ** 2 / 2], [dt ** 2 / 2, dt]]) * q
        Q = np.zeros((4, 4))
        Q[np.ix_([0, 2], [0, 2])] = Q1
        Q[np.ix_([1, 3], [1, 3])] = Q1
        return F @ self.x, F @ self.P @ F.T + Q

    def update(self, t, fix, drone_ne):
        """Fuses one camera fix taken at sim time t. Returns False if the fix was rejected."""
        z = np.array([fix.north, fix.east])
        R = self._measurement_cov(fix, drone_ne)
        if self.x is None or t - self.t > self.MAX_GAP_S or self.rejects >= self.MAX_REJECTS:
            self.x = np.array([z[0], z[1], 0.0, 0.0])
            self.P = np.diag([R[0, 0], R[1, 1], 4.0, 4.0])  # velocity unknown: 2 m/s 1-sigma
            self.t, self.rejects = t, 0
            return True
        if t <= self.t:
            return False
        x, P = self._predicted(t)
        H = np.zeros((2, 4))
        H[0, 0] = H[1, 1] = 1.0
        y = z - H @ x
        S = H @ P @ H.T + R
        if float(y @ np.linalg.solve(S, y)) > self.GATE_CHI2:
            self.rejects += 1
            self.rejected_total += 1
            return False
        K = P @ H.T @ np.linalg.inv(S)
        self.x, self.P, self.t, self.rejects = x + K @ y, (np.eye(4) - K @ H) @ P, t, 0
        return True

    def estimate(self, t):
        """(north, east, v_north, v_east) predicted to sim time t, or None."""
        if self.x is None or t is None or t - self.t > self.MAX_GAP_S:
            return None
        x, _ = self._predicted(max(t, self.t))
        return tuple(float(v) for v in x)


class DistanceBand:
    """Keeps the target's foot point between two image rows by moving FLW_TGT_DST in flight (PX4 Follow Me applies
    a changed FLW_TGT_DST immediately). Inside the band the distance is left alone; when the target is above the
    band (far, shallow view) the drone is brought closer, below it (near, steep) it is sent further away.

    The new distance puts the target back just inside the band edge: with the flat-ground geometry the horizontal
    distance for a depression angle a is h / tan(a)."""

    UPDATE_S = 0.5
    MAX_STEP_M = 2.0  # per update -> at most 4 m/s change of the follow distance
    INNER_MARGIN = 0.1  # aim this fraction of the band height inside the edge

    def __init__(self, link, camera, v_top=0.25, v_bottom=0.75, d_min=5.0, d_max=60.0):
        self.link, self.cam = link, camera
        self.v_top, self.v_bottom = v_top, v_bottom  # fractions of the image height (0 = top)
        self.d_min, self.d_max = d_min, d_max
        self.enabled = False
        self.dst = None  # current FLW_TGT_DST commanded by the band
        self._last = 0.0

    def start(self, dst):
        self.enabled, self.dst, self._last = True, float(dst), 0.0

    def stop(self):
        self.enabled = False

    def _depression_at_row(self, v):
        return self.cam.pitch_down_deg + math.degrees(math.atan((v - self.cam.cy) / self.cam.fy))

    def update(self, now, fix):
        if not self.enabled or fix is None or now - self._last < self.UPDATE_S:
            return
        self._last = now
        img_h = self.cam.height
        v = fix.pixel[1] / img_h
        if self.v_top <= v <= self.v_bottom:
            return
        band = self.v_bottom - self.v_top
        goal_v = (self.v_top + self.INNER_MARGIN * band) if v < self.v_top else (self.v_bottom - self.INNER_MARGIN * band)
        goal_dep = self._depression_at_row(goal_v * img_h)
        if goal_dep <= 1.0:
            return
        goal = fix.height / math.tan(math.radians(goal_dep))
        step = max(-self.MAX_STEP_M, min(self.MAX_STEP_M, goal - self.dst))
        self.dst = max(self.d_min, min(self.d_max, self.dst + step))
        self.link.set_param("FLW_TGT_DST", float(self.dst))


class FollowSim:
    """Ties everything together; runs the 20 Hz update loop in a background thread."""

    RATE_HZ = 20.0
    VIDEO_CONTROL_ADDR = ("127.0.0.1", 5611)  # video/goruntu_yayini.py: Wi-Fi impairment of the video stream

    def __init__(self):
        lat, lon, self.elevation = read_world_origin()
        self.sc = SphericalCoordinates(SphericalCoordinates.EARTH_WGS84, Angle(math.radians(lat)),
                                       Angle(math.radians(lon)), self.elevation, Angle(0))
        self.gz = GzWorld()
        self.link = VehicleLink()
        self.target = TargetMover()
        self.broadcast_target = True
        self.send_target_velocity = True  # False = position only, like a camera-based (Vision) target
        self.show_scene = True
        self.geometry = None
        self.target_gps = None
        self.gcs_distance = None  # drone <-> ground station [m]
        self._out_of_range = False
        self.detections = DetectionListener()
        self.vision_mode = False  # True: FOLLOW_TARGET only while the target is visible
        self.target_seen = False
        self.visibility_source = None  # "kamera" (detector in the video stream) or "geometri" (pinhole check)
        self.lost_since = None  # monotonic time the target was last lost, None while visible
        self.last_target_sent = None  # monotonic time of the last FOLLOW_TARGET
        # Geolocation and the FOLLOW_TARGET source: "gercek" = true target GPS, "kamera" = computed from the image
        self.target_source = "gercek"
        self.geo_fix = None
        # Velocity sent with camera fixes: "yok" (NaN, PX4 estimates it), "kalman" (TargetKalman), "gercek" (true
        # target velocity: the upper bound a perfect filter could reach)
        self.camera_velocity = "yok"
        self.kalman = TargetKalman()
        self.band = DistanceBand(self.link, CAMERA)
        self._sim_now = None
        self._last_det_stamp = None
        self._target_hist = deque(maxlen=200)  # (sim_time, x, y) of the true target
        self.ft_link = LinkImpairment()  # FOLLOW_TARGET path
        self.video_impairment = {"delay_ms": 0, "loss": 0.0}
        self._video_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recorder = None  # callable(row: dict), called every tick (deney.py)
        self.tick_info = {}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)
        try:
            delete_all_markers(self.gz)
        except Exception:
            pass
        self.gz.close()
        self.detections.close()
        self.link.close()

    def target_geodetic(self, x, y):
        r = self.sc.position_transform(vec(x, y, 0.0), SphericalCoordinates.LOCAL2, SphericalCoordinates.SPHERICAL)
        return math.degrees(r.x()), math.degrees(r.y()), r.z()

    def set_video_impairment(self, delay_ms, loss):
        """Wi-Fi model for the video stream (applied to the RTP packets by goruntu_yayini.py)."""
        self.video_impairment = {"delay_ms": int(delay_ms), "loss": float(loss)}
        try:
            self._video_sock.sendto(json.dumps(self.video_impairment).encode(), self.VIDEO_CONTROL_ADDR)
        except OSError:
            pass

    def _update_link(self, drone_pos):
        self.gcs_distance = d = (drone_pos - vec(*GCS_POSITION)).length()
        if not self._out_of_range and d > LINK_RANGE_M:
            self._out_of_range = True
            self.link._log(f"UYARI: drone yer istasyonundan {d:.0f} m uzakta (Wi-Fi video menzili {LINK_RANGE_M:.0f} m)")
        elif self._out_of_range and d < LINK_RANGE_M - 5.0:  # hysteresis: no message spam at the border
            self._out_of_range = False
            self.link._log("Drone tekrar Wi-Fi video menzili içinde")

    def _update_visibility(self, now):
        det = self.detections.fresh()
        if det is not None:
            seen, source = bool(det.get("seen")), "kamera"
        elif self.geometry is not None:
            seen, source = self.geometry.in_frame, "geometri"
        else:
            seen, source = False, None
        self.visibility_source = source
        vision = self.vision_mode or self.target_source == "kamera"  # FOLLOW_TARGET depends on the camera
        if seen and not self.target_seen and self.lost_since is not None and vision:
            self.link._log(f"Hedef tekrar görüldü ({now - self.lost_since:.1f} s sonra), FOLLOW_TARGET yeniden gönderiliyor")
        elif not seen and self.target_seen and vision:
            self.link._log("HEDEF KAYBOLDU: FOLLOW_TARGET kesildi. PX4 3 s son hızla tahmin eder, sonra drone bekler")
        if not seen and self.target_seen:
            self.lost_since = now
        elif seen:
            self.lost_since = None
        self.target_seen = seen

    def _true_target_at(self, sim_time):
        hist = list(self._target_hist)
        for (t0, x0, y0), (t1, x1, y1) in zip(reversed(hist[:-1]), reversed(hist[1:])):
            if t0 <= sim_time <= t1:
                w = (sim_time - t0) / (t1 - t0) if t1 > t0 else 0.0
                return x0 + w * (x1 - x0), y0 + w * (y1 - y0)
        return None

    def _update_geolocation(self, now):
        """New detection -> pixel ray through the EKF pose at the frame time -> ground point -> lat/lon."""
        det = self.detections.fresh()
        if det is None or not det.get("seen") or det.get("clipped") or det.get("stamp") == self._last_det_stamp:
            return
        self._last_det_stamp = det.get("stamp")
        origin = self.link.ekf_origin
        pose = self.link.pose_at(det["sim_time"])  # SITL lockstep: PX4 time_boot == Gazebo sim time
        if origin is None or pose is None:
            return
        q, ned = pose
        fix = geoloc.pixel_to_ground(CAMERA, det["u"], det["v"], q, ned, self._ground_down())
        if fix is None:
            return
        lat, lon = geoloc.ned_to_geodetic(fix.north, fix.east, origin[0], origin[1])
        gf = GeoFix(now, det["sim_time"], lat, lon, fix.north, fix.east, fix.slant, fix.depression_deg, fix.height,
                    (det["u"], det["v"]))
        self.kalman.update(det["sim_time"], gf, (ned[0], ned[1]))
        self.band.update(now, gf)
        truth = self._true_target_at(det["sim_time"])
        if truth is not None:
            t_lat, t_lon, _ = self.target_geodetic(*truth)
            t_n, t_e = geoloc.geodetic_to_ned(t_lat, t_lon, origin[0], origin[1])
            gf.error_ne = (fix.north - t_n, fix.east - t_e)
            gf.error_m = math.hypot(*gf.error_ne)
        self.geo_fix = gf

    def _ground_down(self):
        """D coordinate of the (flat) ground in the EKF local frame."""
        return (self.link.home_ned[2] if self.link.home_ned else 0.0) + BODY_HEIGHT_LANDED_M

    def _fresh_fix(self, now):
        f = self.geo_fix
        return f if f is not None and now - f.stamp < DETECTION_FRESH_S else None

    def _send_target(self, now, vx, vy):
        """Builds this tick's FOLLOW_TARGET (true GPS or camera fix) and hands it to the impaired link."""
        if self.target_source == "kamera":
            fix = self._fresh_fix(now)
            if fix is None:
                return False
            alt = self.link.ekf_origin[2] - self._ground_down()  # ground AMSL (unused with FLW_TGT_ALT_M = 0)
            msg = (fix.lat, fix.lon, alt, None, None)  # the camera gives no velocity: PX4 estimates it
            if self.camera_velocity == "kalman":
                est = self.kalman.estimate(self._sim_now)
                if est is not None:
                    origin = self.link.ekf_origin
                    k_lat, k_lon = geoloc.ned_to_geodetic(est[0], est[1], origin[0], origin[1])
                    msg = (k_lat, k_lon, alt, est[2], est[3])
            elif self.camera_velocity == "gercek":
                msg = (fix.lat, fix.lon, alt, vy, vx)  # ENU -> NED
        else:
            if not (self.target_seen or not self.vision_mode):
                return False
            lat, lon, alt = self.target_gps
            msg = (lat, lon, alt, vy, vx) if self.send_target_velocity else (lat, lon, alt, None, None)  # ENU -> NED
        self.ft_link.submit(now, lambda m=msg: self.link.send_follow_target(*m))
        self.last_target_sent = now
        return True

    def _loop(self):
        period = 1.0 / self.RATE_HZ
        last = time.monotonic()
        tick = 0
        markers_were_shown = False
        markers_paused_until = 0.0  # no Gazebo GUI (HEADLESS=1): the marker service times out after 500 ms
        while not self._stop.is_set():
            now = time.monotonic()
            dt, last = now - last, now
            tick += 1
            try:
                x, y, yaw = self.target.step(dt)
                poses = {TARGET_MODEL: (x, y, 0.0, yaw)}
                _, _, _, vx, vy = self.target.state()
                self.target_gps = self.target_geodetic(x, y)
                sim_time = self.gz.sim_time()
                if sim_time is not None:
                    self._target_hist.append((sim_time, x, y))
                    self._sim_now = sim_time

                pose = self.gz.drone_pose()
                self.geometry = compute_geometry(pose[0], pose[1], (x, y)) if pose is not None else None
                if pose is not None:
                    self._update_link(pose[0])
                self._update_visibility(now)
                self._update_geolocation(now)

                self.link.send_manual_control()
                sent = False
                if tick % 2 == 0 and self.broadcast_target:  # 10 Hz
                    sent = self._send_target(now, vx, vy)
                delivered = self.ft_link.pump(now)
                if tick % int(self.RATE_HZ) == 0:  # 1 Hz
                    self.link.send_heartbeat()
                if tick % (5 * int(self.RATE_HZ)) == 1:  # every 5 s until answered
                    self.link.request_streams()
                draw = self.show_scene and self.geometry is not None and now >= markers_paused_until
                if draw and tick % 2 == 0:  # 10 Hz
                    if self.gz.send_markers(build_markers(self.geometry)):
                        markers_were_shown = True
                    else:  # do not stall the 20 Hz loop; retry later
                        markers_paused_until = time.monotonic() + 10.0
                elif not draw and markers_were_shown:
                    delete_all_markers(self.gz)
                    markers_were_shown = False
                self.gz.set_model_poses(poses)
                if self.recorder is not None:
                    self.recorder(self._row(now, sim_time, pose, (x, y, yaw, vx, vy), sent, delivered))
            except Exception as exc:  # keep the loop alive; show the problem in the panel log
                self.link._log(f"Hata: {exc}")
                time.sleep(0.5)
            self._stop.wait(max(0.0, period - (time.monotonic() - now)))

    def _row(self, now, sim_time, pose, target, sent, delivered):
        """One log line for deney.py (true drone pose from Gazebo, so any camera tilt can be evaluated later)."""
        nan = float("nan")
        row = {"t": now, "sim_t": sim_time if sim_time is not None else nan, "mode": self.link.state.mode,
               "tx": target[0], "ty": target[1], "tyaw": target[2], "tvx": target[3], "tvy": target[4],
               "ft_sent": int(sent), "ft_delivered": delivered}
        if pose is not None:
            p, q = pose
            row.update(dx=p.x(), dy=p.y(), dz=p.z(), qw=q.w(), qx=q.x(), qy=q.y(), qz=q.z())
        g = self.geometry
        if g is not None and g.pixel is not None:
            row.update(pu=g.pixel[0], pv=g.pixel[1], p_in=int(g.in_frame))
        det = self.detections.fresh()
        if det is not None:
            row.update(det_seen=int(bool(det.get("seen"))), det_u=det.get("u", nan), det_v=det.get("v", nan),
                       det_sim_t=det.get("sim_time", nan), det_clip=int(bool(det.get("clipped"))))
        ekf = self.link.pose_at(self.link.boot_time) if self.link.boot_time is not None else None
        if ekf is not None:
            (ew, ex, ey, ez), (en, ee, ed) = ekf
            row.update(ekf_t=self.link.boot_time, ekf_qw=ew, ekf_qx=ex, ekf_qy=ey, ekf_qz=ez, ekf_n=en, ekf_e=ee,
                       ekf_d=ed)
        f = self._fresh_fix(now)
        if f is not None:
            row.update(fix_n=f.north, fix_e=f.east, fix_err=f.error_m, fix_err_n=f.error_ne[0],
                       fix_err_e=f.error_ne[1], fix_age=now - f.stamp, fix_sim_t=f.sim_time, fix_h=f.height,
                       fix_dep=f.depression_deg)
        est = self.kalman.estimate(sim_time)
        if est is not None:
            row.update(kf_n=est[0], kf_e=est[1], kf_vn=est[2], kf_ve=est[3])
        row.update(kf_rejected=self.kalman.rejected_total, cam_vel=self.camera_velocity,
                   band_dst=self.band.dst if self.band.enabled else nan)
        return row
