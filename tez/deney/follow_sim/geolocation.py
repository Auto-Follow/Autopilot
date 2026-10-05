"""Target geolocation from a single camera pixel (flat ground model).

pixel (u, v) + camera intrinsics + camera mount + vehicle attitude/position (PX4 EKF) -> target position on the
ground -> latitude / longitude for FOLLOW_TARGET.

Frames (PX4 convention):
  NED   local North-East-Down, origin = EKF origin
  FRD   body Forward-Right-Down, attitude quaternion q rotates FRD -> NED (ATTITUDE_QUATERNION)
  OPT   camera optical frame (OpenCV): x right, y down, z forward (along the optical axis)

Only numpy; meant to run unchanged on the Raspberry Pi (pose from MAVLink, pixel from the Vision detector).
"""
import math
from dataclasses import dataclass

import numpy as np

EARTH_RADIUS_M = 6378137.0


@dataclass
class CameraModel:
    """Pinhole intrinsics (pixels) and the mount on the vehicle."""
    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int
    offset_frd: tuple = (0.0, 0.0, 0.0)  # camera center in the body frame [m]
    pitch_down_deg: float = 0.0  # mount tilt, positive = looking down

    @classmethod
    def from_hfov(cls, hfov_rad, width, height, **mount):
        f = (width / 2) / math.tan(hfov_rad / 2)
        return cls(f, f, width / 2, height / 2, width, height, **mount)

    def r_body_opt(self):
        """Rotation OPT -> FRD: level camera (z_opt = x_frd, x_opt = y_frd, y_opt = z_frd), then tilted down."""
        level = np.array([[0.0, 0.0, 1.0],
                          [1.0, 0.0, 0.0],
                          [0.0, 1.0, 0.0]])
        p = math.radians(self.pitch_down_deg)
        # nose-down rotation about the body y axis (FRD pitch of -p)
        tilt = np.array([[math.cos(p), 0.0, -math.sin(p)],
                         [0.0, 1.0, 0.0],
                         [math.sin(p), 0.0, math.cos(p)]])
        return tilt @ level


def quat_to_dcm(q):
    """(w, x, y, z) -> 3x3 rotation matrix (body -> NED for PX4 attitude)."""
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def euler_to_quat(roll, pitch, yaw):
    """Aerospace ZYX Euler angles [rad] -> (w, x, y, z)."""
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
    return (cr * cp * cy + sr * sp * sy, sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy)


@dataclass
class GroundFix:
    north: float  # target position in the local NED frame [m]
    east: float
    slant: float  # camera -> target distance [m]
    depression_deg: float  # angle of the ray below the horizon
    height: float  # camera height above the ground plane [m]


def pixel_to_ground(cam, u, v, q_body_ned, pos_ned, ground_down=0.0):
    """Intersect the pixel ray with the horizontal plane D = ground_down.

    pos_ned: vehicle (body origin) position in NED [m]. Returns None if the ray does not hit the ground in front
    of the camera (at or above the horizon)."""
    ray_opt = np.array([(u - cam.cx) / cam.fx, (v - cam.cy) / cam.fy, 1.0])
    r_ned_body = quat_to_dcm(q_body_ned)
    ray = r_ned_body @ (cam.r_body_opt() @ ray_opt)
    origin = np.asarray(pos_ned, dtype=float) + r_ned_body @ np.asarray(cam.offset_frd, dtype=float)
    height = ground_down - origin[2]  # D grows downwards
    if ray[2] <= 1e-6 or height <= 0.0:
        return None
    s = height / ray[2]
    hit = origin + s * ray
    slant = s * float(np.linalg.norm(ray))
    depression = math.degrees(math.asin(ray[2] / np.linalg.norm(ray)))
    return GroundFix(float(hit[0]), float(hit[1]), slant, depression, float(height))


def point_to_pixel(cam, point_ned, q_body_ned, pos_ned):
    """Projects a NED point into the image: (u, v, depth), depth <= 0 means behind the camera."""
    r_ned_body = quat_to_dcm(q_body_ned)
    origin = np.asarray(pos_ned, dtype=float) + r_ned_body @ np.asarray(cam.offset_frd, dtype=float)
    p_opt = cam.r_body_opt().T @ (r_ned_body.T @ (np.asarray(point_ned, dtype=float) - origin))
    if p_opt[2] <= 1e-9:
        return float("nan"), float("nan"), float(p_opt[2])
    return (float(cam.cx + cam.fx * p_opt[0] / p_opt[2]), float(cam.cy + cam.fy * p_opt[1] / p_opt[2]),
            float(p_opt[2]))


def ned_to_geodetic(north, east, ref_lat_deg, ref_lon_deg):
    """Local tangent plane offset -> lat/lon (equirectangular; error < 1 cm within a few hundred meters)."""
    lat = ref_lat_deg + math.degrees(north / EARTH_RADIUS_M)
    lon = ref_lon_deg + math.degrees(east / (EARTH_RADIUS_M * math.cos(math.radians(ref_lat_deg))))
    return lat, lon


def geodetic_to_ned(lat_deg, lon_deg, ref_lat_deg, ref_lon_deg):
    north = math.radians(lat_deg - ref_lat_deg) * EARTH_RADIUS_M
    east = math.radians(lon_deg - ref_lon_deg) * EARTH_RADIUS_M * math.cos(math.radians(ref_lat_deg))
    return north, east


def ground_error_sensitivity(height, depression_deg):
    """First-order horizontal error of the ground point [m] per 1 deg of depression-angle error and per 1 m of
    height error. Ground range r = h / tan(d): dr/dd = h / sin^2(d), dr/dh = 1 / tan(d)."""
    d = math.radians(depression_deg)
    return height / math.sin(d) ** 2 * math.radians(1.0), 1.0 / math.tan(d)
