"""Flat-ground position of the target from its box: what the Pi sends PX4's stock Follow Me as FOLLOW_TARGET.

Spec 2026-11-10-m06-sim-ortami, 6 and "Varsayımlar" 5-6 (temporary: m10 brings the real transform, m05 the interface).

Locator.locate, once per processed frame with a chosen box:
  1. foot point: the bottom middle of the box ((u0 + u1) / 2, v1), pixel edges like the detector's boxes;
  2. the pixel's ray through camera_info (kamera.Camera.pixel_to_los, distortion included) and the nominal mount
     (45 deg below the nose, camera FRD offset (0.151, 0, 0.035) m; the Pi uses its measured one), rotated into NED
     with the EKF attitude of the frame's capture time, from the camera's EKF position;
  3. intersected with the ground: the horizontal plane GROUND_BELOW_HOME_M under the home position (flat ground at
     the take-off point's height; base_link is that high above the landing gear's feet);
  4. the point in PX4's local NED frame -> latitude / longitude with PX4's own projection (lib/geo MapProjection,
     azimuthal equidistant on a 6371 km sphere) about the EKF origin (GPS_GLOBAL_ORIGIN). PX4's target estimator
     projects FOLLOW_TARGET back with the same projection and origin, so the round trip only adds the 1e-7 deg
     integers of the message (<= 0.56 cm). Height: the ground's AMSL height (where the person's feet are).

No position (and no FOLLOW_TARGET) when: no box was chosen (kutu_yok); no camera_info yet (kamera_yok); the box is
closer than EDGE_MARGIN_PX to the left, right or bottom edge: the feet or one side may be cut off, so its bottom middle
is not the foot point (kenar; a head cut off at the top leaves the feet where they are); the pose history does not
hold a sample at most POSE_SPAN_S before and one at most POSE_SPAN_S after the capture time (poz_yok); the EKF origin
or the home position is not known yet (referans_yok); the foot ray is less than asin(MIN_DOWN) = 14.5 deg below the
horizon (ufka_yakin: a far detection, or the nose pitched up; the flat-ground distance grows without bound there).

PoseHistory: the EKF pose PX4 streams on the onboard link (ATTITUDE_QUATERNION 50 Hz, LOCAL_POSITION_NED 30 Hz,
stamped with time_boot_ms) plus GPS_GLOBAL_ORIGIN and HOME_POSITION, filled by the MAVLink link's message hook
(px4_baglanti.pose_hook) and read by the tracking thread. In SITL, PX4's clock is Gazebo's (gz_bridge sets it every
physics step), so a camera frame's capture time is a PX4 time; on the real vehicle the Pi has to map its camera clock
to PX4's (TIMESYNC, m04).

Evaluation only, never used to steer: WorldGeo turns the Gazebo world's ENU metres into WGS84 latitude / longitude
like Gazebo's NavSat sensor (the drone's GPS) does: the world's spherical_coordinates, ENU = gz-math LOCAL2. A position
PX4 got can so be compared with where the person really was.
"""

import bisect
import math
import threading
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

import kamera

# Nominal mount of the drone camera (spec "Kamera parametreleri"; models/x500_tez): the tracking side uses these, not
# what Gazebo reports, like the Pi uses its measured mount; a mount error can be put in on purpose later.
MOUNT_PITCH_DOWN = math.radians(45.0)  # [rad] below the nose
NOMINAL_MOUNT = kamera.camera_to_body(MOUNT_PITCH_DOWN)  # C_cb, optical -> body FRD
NOMINAL_OFFSET_FRD = np.array([0.151, 0.0, 0.035])  # [m] camera optical centre from base_link, body FRD
# [m] base_link above the ground when the drone stands on it: bottom of the x500 skids (base_link_collision_3/4 at
# z -0.2195, 0.015 thick). Home is where it armed, so the flat ground is this far below home. Measured on the vehicle.
GROUND_BELOW_HOME_M = 0.227
EDGE_MARGIN_PX = 8.0  # [px] spec 6: a box closer to the left, right or bottom edge may have its feet cut off
MIN_DOWN = 0.25  # u_D, down component of the unit foot ray in NED (45 deg camera report: the target has 0.55-0.7)
POSE_SPAN_S = 0.15  # [s] the samples around the capture time may be at most this far from it
POSE_KEEP_S = 5.0  # [s] pose samples kept (a model result comes ~0.15 s after its frame)
EARTH_RADIUS_M = 6371000.0  # PX4 lib/geo CONSTANTS_RADIUS_OF_EARTH (a sphere, not WGS84)
WGS84_A = 6378137.0  # [m] Gazebo's EARTH_WGS84 surface
WGS84_E2 = (1.0 / 298.257223563) * (2.0 - 1.0 / 298.257223563)
STATUSES = ("hesaplandi", "kutu_yok", "kamera_yok", "kenar", "poz_yok", "referans_yok", "ufka_yakin")


class Box(Protocol):
    """A detector box in pixel edges (algilama.Kutu): u0 <= u < u1, v0 <= v < v1 [px]."""

    u0: float
    v0: float
    u1: float
    v1: float


@dataclass(frozen=True)
class GeoPoint:
    lat: float  # [deg] WGS84
    lon: float  # [deg]
    alt: float  # [m] AMSL


@dataclass(frozen=True)
class Pose:
    """EKF pose at one time: attitude body FRD -> NED and position NED (EKF origin)."""

    t: float  # [s] PX4 time (= sim time in SITL)
    q: np.ndarray  # (w, x, y, z), unit
    p: np.ndarray  # [m] (N, E, D)
    before_ms: float = 0.0  # [ms] how old the samples before t were (the older of the two streams)
    after_ms: float = 0.0  # [ms] how much later the samples after t came

    @property
    def c_bn(self) -> np.ndarray:
        return kamera.quat_to_dcm(*self.q)

    def euler_deg(self) -> tuple[float, float, float]:
        """roll, pitch, yaw [deg], 3-2-1 (PX4's)."""
        r = self.c_bn
        return (
            math.degrees(math.atan2(r[2, 1], r[2, 2])),
            math.degrees(-math.asin(max(-1.0, min(1.0, r[2, 0])))),
            math.degrees(math.atan2(r[1, 0], r[0, 0])),
        )


def _bracket(times: list[float], t: float, span: float) -> tuple[int, int, float] | None:
    """Indices of the samples at or before and at or after t, both within `span` [s], and the fraction of t between."""
    i = bisect.bisect_left(times, t)
    if i < len(times) and times[i] == t:
        return i, i, 0.0
    if i == 0 or i == len(times):
        return None
    t0, t1 = times[i - 1], times[i]
    if t - t0 > span or t1 - t > span:
        return None
    return i - 1, i, (t - t0) / (t1 - t0)


class PoseHistory:
    """The EKF pose samples PX4 streams, the EKF origin and the home position; written by one thread (the MAVLink
    reader), read by another (tracking)."""

    def __init__(self, keep_s: float = POSE_KEEP_S) -> None:
        self._keep = keep_s
        self._lock = threading.Lock()
        self._att: deque[tuple[float, np.ndarray]] = deque()
        self._pos: deque[tuple[float, np.ndarray]] = deque()
        self._origin: GeoPoint | None = None
        self._home: tuple[np.ndarray, float] | None = None
        self.errors = 0  # malformed messages the MAVLink hook skipped

    def add_attitude(self, t: float, q: np.ndarray) -> None:
        """[s] PX4 time; q (w, x, y, z) body FRD -> NED (normalised here)."""
        q = np.asarray(q, dtype=float)
        self._add(self._att, t, q / np.linalg.norm(q))

    def add_position(self, t: float, p: np.ndarray) -> None:
        """[s] PX4 time; p [m] NED."""
        self._add(self._pos, t, np.asarray(p, dtype=float))

    def _add(self, samples: deque, t: float, value: np.ndarray) -> None:
        with self._lock:
            if samples and t < samples[-1][0]:  # late (UDP keeps the order, but stay correct): put it in its place
                items = list(samples)
                items.insert(bisect.bisect([s[0] for s in items], t), (t, value))
                samples.clear()
                samples.extend(items)
            else:
                samples.append((t, value))
            while samples and samples[-1][0] - samples[0][0] > self._keep:
                samples.popleft()

    def set_origin(self, origin: GeoPoint) -> None:
        with self._lock:
            self._origin = origin

    def set_home(self, ned: np.ndarray, alt: float) -> None:
        """Home position: NED [m] in the EKF frame and its AMSL height [m]."""
        with self._lock:
            self._home = (np.asarray(ned, dtype=float), float(alt))

    @property
    def origin(self) -> GeoPoint | None:
        with self._lock:
            return self._origin

    @property
    def home_ned(self) -> np.ndarray | None:
        with self._lock:
            return None if self._home is None else self._home[0]

    @property
    def home_alt(self) -> float | None:
        with self._lock:
            return None if self._home is None else self._home[1]

    def at(self, t: float, span: float = POSE_SPAN_S) -> Pose | None:
        """EKF pose at PX4 time t [s], interpolated (attitude nlerp, position linear); None if either stream has no
        sample at most `span` [s] before t or none at most `span` after it."""
        with self._lock:
            att, pos = list(self._att), list(self._pos)
        a = _bracket([s[0] for s in att], t, span)
        b = _bracket([s[0] for s in pos], t, span)
        if a is None or b is None:
            return None
        q0, q1 = att[a[0]][1], att[a[1]][1]
        if np.dot(q0, q1) < 0:
            q1 = -q1
        q = (1 - a[2]) * q0 + a[2] * q1
        p = (1 - b[2]) * pos[b[0]][1] + b[2] * pos[b[1]][1]
        before = max(t - att[a[0]][0], t - pos[b[0]][0])
        after = max(att[a[1]][0] - t, pos[b[1]][0] - t)
        return Pose(t, q / np.linalg.norm(q), p, before * 1000.0, after * 1000.0)


class MapProjection:
    """PX4 lib/geo MapProjection: azimuthal equidistant projection about a reference point on a sphere of
    EARTH_RADIUS_M; local x north, y east [m]. PX4's EKF and its follow-target estimator use it."""

    def __init__(self, lat0: float, lon0: float) -> None:
        self._lat0, self._lon0 = math.radians(lat0), math.radians(lon0)
        self._sin0, self._cos0 = math.sin(self._lat0), math.cos(self._lat0)

    def project(self, lat: float, lon: float) -> tuple[float, float]:
        """[deg] -> (north, east) [m]."""
        la, lo = math.radians(lat), math.radians(lon)
        sin_lat, cos_lat, cos_d = math.sin(la), math.cos(la), math.cos(lo - self._lon0)
        c = math.acos(max(-1.0, min(1.0, self._sin0 * sin_lat + self._cos0 * cos_lat * cos_d)))
        k = c / math.sin(c) if c != 0 else 1.0
        north = k * (self._cos0 * sin_lat - self._sin0 * cos_lat * cos_d) * EARTH_RADIUS_M
        east = k * cos_lat * math.sin(lo - self._lon0) * EARTH_RADIUS_M
        return north, east

    def reproject(self, north: float, east: float) -> tuple[float, float]:
        """(north, east) [m] -> (lat, lon) [deg]."""
        x, y = north / EARTH_RADIUS_M, east / EARTH_RADIUS_M
        c = math.hypot(x, y)
        if c == 0:
            return math.degrees(self._lat0), math.degrees(self._lon0)
        sin_c, cos_c = math.sin(c), math.cos(c)
        lat = math.asin(cos_c * self._sin0 + x * sin_c * self._cos0 / c)
        lon = self._lon0 + math.atan2(y * sin_c, c * self._cos0 * cos_c - x * self._sin0 * sin_c)
        return math.degrees(lat), math.degrees(lon)


def _ecef(lat: float, lon: float, h: float) -> np.ndarray:
    la, lo = math.radians(lat), math.radians(lon)
    n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * math.sin(la) ** 2)
    return np.array(
        [
            (n + h) * math.cos(la) * math.cos(lo),
            (n + h) * math.cos(la) * math.sin(lo),
            (n * (1 - WGS84_E2) + h) * math.sin(la),
        ]
    )


def _geodetic(xyz: np.ndarray) -> tuple[float, float, float]:
    """ECEF [m] -> (lat [deg], lon [deg], h [m]) on WGS84 (iterated to well below a micrometre)."""
    x, y, z = xyz
    p = math.hypot(x, y)
    lon = math.atan2(y, x)
    lat = math.atan2(z, p * (1 - WGS84_E2))
    h = 0.0
    for _ in range(8):
        n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * math.sin(lat) ** 2)
        h = p / math.cos(lat) - n
        lat = math.atan2(z, p * (1 - WGS84_E2 * n / (n + h)))
    return math.degrees(lat), math.degrees(lon), h


@dataclass(frozen=True)
class WorldGeo:
    """The Gazebo world's geodetic origin (<spherical_coordinates>, WGS84, ENU, heading 0): world x east, y north,
    z up [m] <-> latitude / longitude / height, like Gazebo's NavSat sensor (gz-math LOCAL2)."""

    lat0: float  # [deg]
    lon0: float  # [deg]
    elevation: float  # [m]
    _origin: np.ndarray = field(init=False, repr=False, compare=False)
    _enu: np.ndarray = field(init=False, repr=False, compare=False)  # rows: east, north, up in ECEF

    def __post_init__(self) -> None:
        la, lo = math.radians(self.lat0), math.radians(self.lon0)
        enu = np.array(
            [
                [-math.sin(lo), math.cos(lo), 0.0],
                [-math.sin(la) * math.cos(lo), -math.sin(la) * math.sin(lo), math.cos(la)],
                [math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)],
            ]
        )
        object.__setattr__(self, "_origin", _ecef(self.lat0, self.lon0, self.elevation))
        object.__setattr__(self, "_enu", enu)

    def to_geodetic(self, x: float, y: float, z: float = 0.0) -> tuple[float, float, float]:
        """World (east, north, up) [m] -> (lat [deg], lon [deg], height [m])."""
        return _geodetic(self._origin + self._enu.T @ np.array([x, y, z]))

    def to_local(self, lat: float, lon: float, h: float = 0.0) -> tuple[float, float, float]:
        """(lat [deg], lon [deg], height [m]) -> world (east, north, up) [m]."""
        x, y, z = self._enu @ (_ecef(lat, lon, h) - self._origin)
        return float(x), float(y), float(z)


def world_geo(path: Path) -> WorldGeo:
    """The <spherical_coordinates> of a world SDF (tez/sim/worlds); only ENU worlds with heading 0 are supported."""
    sc = ET.parse(path).getroot().find("world/spherical_coordinates")
    if sc is None:
        raise ValueError(f"{path.name}: <spherical_coordinates> yok")
    orientation = sc.findtext("world_frame_orientation", "ENU").strip()
    heading = float(sc.findtext("heading_deg", "0"))
    if orientation != "ENU" or heading != 0.0 or sc.findtext("surface_model", "EARTH_WGS84").strip() != "EARTH_WGS84":
        raise ValueError(f"{path.name}: yalnız EARTH_WGS84, ENU ve heading_deg 0 destekleniyor")
    return WorldGeo(
        float(sc.findtext("latitude_deg")), float(sc.findtext("longitude_deg")), float(sc.findtext("elevation", "0"))
    )


@dataclass(frozen=True)
class Fix:
    """The target's position from one frame's box, or why there is none (status, STATUSES)."""

    status: str
    foot: tuple[float, float] | None = None  # [px] bottom middle of the box
    down: float = math.nan  # u_D of the foot ray (NED, unit)
    pose: Pose | None = None  # EKF pose of the capture time
    ned: np.ndarray | None = None  # [m] ground point, EKF local NED
    geo: GeoPoint | None = None  # what FOLLOW_TARGET carries
    range_m: float = math.nan  # [m] camera -> ground point
    horizontal_m: float = math.nan  # [m] drone (EKF) -> ground point, horizontal

    @property
    def ok(self) -> bool:
        return self.status == "hesaplandi"


def foot_pixel(box: Box) -> tuple[float, float]:
    """Bottom middle of a pixel-edge box: the foot point nearest to the camera (spec "Varsayımlar" 5)."""
    return (box.u0 + box.u1) / 2.0, float(box.v1)


def at_edge(box: Box, camera: kamera.Camera, margin: float = EDGE_MARGIN_PX) -> bool:
    """The box reaches closer than `margin` [px] to the left, right or bottom edge of the image."""
    return box.u0 < margin or box.u1 > camera.width - margin or box.v1 > camera.height - margin


def ground_hit(
    camera: kamera.Camera,
    uv: tuple[float, float],
    c_bn: np.ndarray,
    cam_ned: np.ndarray,
    ground_d: float,
    mount: np.ndarray = NOMINAL_MOUNT,
) -> tuple[np.ndarray, np.ndarray]:
    """Unit ray of pixel `uv` in NED (C_bn body -> NED, `mount` C_cb optical -> body) and where it meets the plane
    D = ground_d [m] from the camera at `cam_ned` (point NaN if it never does)."""
    ray = c_bn @ mount @ camera.pixel_to_los(*uv)
    if ray[2] <= 1e-9 or ground_d <= cam_ned[2]:
        return np.full(3, math.nan), ray
    return cam_ned + (ground_d - cam_ned[2]) / ray[2] * ray, ray


class Locator:
    """Spec 6: chosen box + EKF pose of its frame -> flat-ground position (see the module text)."""

    def __init__(
        self,
        mount: np.ndarray = NOMINAL_MOUNT,
        offset_frd: np.ndarray = NOMINAL_OFFSET_FRD,
        ground_below_home: float = GROUND_BELOW_HOME_M,
        margin: float = EDGE_MARGIN_PX,
        min_down: float = MIN_DOWN,
        span: float = POSE_SPAN_S,
    ) -> None:
        self.mount, self.offset = mount, np.asarray(offset_frd, dtype=float)
        self.ground_below_home, self.margin, self.min_down, self.span = ground_below_home, margin, min_down, span

    def locate(self, box: Box | None, t: float, camera: kamera.Camera | None, poses: PoseHistory | None) -> Fix:
        """Position of the person standing in `box` in the frame captured at t [s, PX4 time]."""
        if box is None:
            return Fix("kutu_yok")
        if camera is None:
            return Fix("kamera_yok")
        foot = foot_pixel(box)
        if at_edge(box, camera, self.margin):
            return Fix("kenar", foot)
        pose = poses.at(t, self.span) if poses is not None else None
        if pose is None:
            return Fix("poz_yok", foot)
        origin, home, home_alt = poses.origin, poses.home_ned, poses.home_alt
        c_bn = pose.c_bn
        cam = pose.p + c_bn @ self.offset
        if origin is None or home is None or home_alt is None:
            return Fix("referans_yok", foot, pose=pose)
        ground_d = home[2] + self.ground_below_home
        point, ray = ground_hit(camera, foot, c_bn, cam, ground_d, self.mount)
        if ray[2] < self.min_down:
            return Fix("ufka_yakin", foot, float(ray[2]), pose)
        lat, lon = MapProjection(origin.lat, origin.lon).reproject(point[0], point[1])
        geo = GeoPoint(lat, lon, origin.alt - ground_d)  # NED D grows downwards from the origin's height
        return Fix(
            "hesaplandi",
            foot,
            float(ray[2]),
            pose,
            point,
            geo,
            float(np.linalg.norm(point - cam)),
            float(math.hypot(point[0] - pose.p[0], point[1] - pose.p[1])),
        )


def true_pose_hit(
    camera: kamera.Camera,
    uv: tuple[float, float],
    row: dict,
    offset_flu: tuple[float, float, float],
    c_cb: np.ndarray,
) -> tuple[float, float]:
    """Evaluation: where the foot ray of pixel `uv` meets the world's ground (z = 0) with the drone's true pose of
    that frame (dogru_cevap.csv row) and the true camera mount Gazebo reports (kayit.Recorder.camera_offset /
    camera_dcm). World (x east, y north) [m]; NaN if it never does. Against the EKF pose this splits the position
    error into the box's part and the estimator's part."""
    r_model = kamera.quat_to_dcm(row["dron_qw"], row["dron_qx"], row["dron_qy"], row["dron_qz"])  # FLU -> ENU
    c_bn = kamera.ENU_TO_NED @ r_model @ kamera.FLU_TO_FRD
    p_cam = np.array([row["dron_x"], row["dron_y"], row["dron_z"]]) + r_model @ np.asarray(offset_flu, dtype=float)
    point, _ = ground_hit(camera, uv, c_bn, kamera.ENU_TO_NED @ p_cam, 0.0, c_cb)
    return float(point[1]), float(point[0])  # NED of the world origin: east = x, north = y
