"""Camera model and frame conventions shared by the ground truth recorder and the tests.

Follows the team's pixel -> line-of-sight chain ("Pikselden Vektöre Dönüşüm", H. Uygun, 2026-10-10):
pixel (u, v) -> normalized (x_d, y_d) = K^-1 (u, v, 1) -> undistorted (x_n, y_n) (Brown-Conrady, k1 k2 p1 p2 k3)
-> unit vector in the camera optical frame -> body FRD (permutation P, then mount/gimbal pitch) -> NED (attitude).

Frames (all right handed):
  optical  x right, y down, z forward (along the lens axis)          -- what the vision code works in
  body     FRD: x nose, y right wing, z down                         -- PX4
  NED      x north, y east, z down                                   -- PX4 local frame
  Gazebo   world ENU (x east, y north, z up); models FLU; a camera sensor looks along its link's +x, image right = -y,
           image down = -z
"""

import math
from dataclasses import dataclass

import numpy as np

# [deg] camera below the nose on the real mount (X500 V2 Depth Camera Mount position) and in models/x500_tez
# (camera_link pitch 0.785398; test_kamera_egimi checks the SDF). A scenario may fly another tilt (hedef.py
# kamera.egim_deg, --kamera-egim): its run then gets a tilted copy of the model and every computation uses that tilt.
NOMINAL_TILT_DEG = 45.0

# Fixed axis changes (rows: new axes in old coordinates)
GZ_CAMERA_TO_OPTICAL = np.array([[0.0, -1.0, 0.0], [0.0, 0.0, -1.0], [1.0, 0.0, 0.0]])
FLU_TO_FRD = np.diag([1.0, -1.0, -1.0])
ENU_TO_NED = np.array([[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, -1.0]])
# Optical axes renamed to body axes for a camera looking along the nose (forward = z_c, right = x_c, down = y_c)
OPTICAL_TO_BODY_P = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])


def rot_x(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def rot_y(a: float) -> np.ndarray:
    """Rotation about y; in FRD a positive angle raises the nose (aviation convention)."""
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def rot_z(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def quat_to_dcm(qw: float, qx: float, qy: float, qz: float) -> np.ndarray:
    """Rotation matrix (child -> parent) of a unit quaternion."""
    return np.array(
        [
            [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
            [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
            [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
        ]
    )


def body_to_ned(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """C_bn = Rz(yaw) Ry(pitch) Rx(roll), 3-2-1 Euler angles [rad]."""
    return rot_z(yaw) @ rot_y(pitch) @ rot_x(roll)


def camera_to_body(pitch_down: float) -> np.ndarray:
    """C_cb for a camera fixed on the body, tilted `pitch_down` [rad] below the nose (no roll/yaw mount offset)."""
    return rot_y(-pitch_down) @ OPTICAL_TO_BODY_P


def tilt_of_mount(c_cb: np.ndarray) -> float:
    """[deg] how far below the nose the optical axis of a mount C_cb (optical -> body FRD) points (FRD z is down)."""
    axis = np.asarray(c_cb, dtype=float)[:, 2]
    return math.degrees(math.atan2(axis[2], math.hypot(axis[0], axis[1])))


def angle_deg(a: np.ndarray, b: np.ndarray) -> float:
    """Angle between two directions [deg]; atan2 keeps it exact for the small angles that matter here."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return math.degrees(math.atan2(float(np.linalg.norm(np.cross(a, b))), float(np.dot(a, b))))


def deviation(los: np.ndarray, frame: str) -> tuple[float, float, float]:
    """(horizontal, vertical, total) angle [deg] of a unit LOS from the boresight: right, down positive.

    frame "body": boresight x (nose); frame "optical": boresight z (lens axis).
    """
    if frame == "body":
        fwd, right, down = los[0], los[1], los[2]
    elif frame == "optical":
        fwd, right, down = los[2], los[0], los[1]
    else:
        raise ValueError(f"frame: 'body' or 'optical', got {frame!r}")
    return (
        math.degrees(math.atan2(right, fwd)),
        math.degrees(math.atan2(down, fwd)),
        math.degrees(math.acos(max(-1.0, min(1.0, fwd)))),
    )


@dataclass(frozen=True)
class Camera:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    dist: tuple[float, float, float, float, float] = (0.0, 0.0, 0.0, 0.0, 0.0)  # k1, k2, p1, p2, k3 (OpenCV order)

    @classmethod
    def from_camera_info(cls, msg: object) -> "Camera":
        """From a gz.msgs.CameraInfo (Gazebo fills it from the sensor's SDF, including <distortion>)."""
        k = msg.intrinsics.k
        d = list(msg.distortion.k)[:5]
        d += [0.0] * (5 - len(d))
        return cls(int(msg.width), int(msg.height), k[0], k[4], k[2], k[5], tuple(float(v) for v in d))

    def as_dict(self) -> dict:
        return {
            "w": self.width,
            "h": self.height,
            "fx": self.fx,
            "fy": self.fy,
            "cx": self.cx,
            "cy": self.cy,
            "dist": list(self.dist),
        }

    def distort(self, xn: float, yn: float) -> tuple[float, float]:
        """Brown-Conrady forward model: ideal normalized point -> distorted normalized point."""
        k1, k2, p1, p2, k3 = self.dist
        r2 = xn * xn + yn * yn
        radial = 1 + k1 * r2 + k2 * r2 * r2 + k3 * r2 * r2 * r2
        xd = xn * radial + 2 * p1 * xn * yn + p2 * (r2 + 2 * xn * xn)
        yd = yn * radial + p1 * (r2 + 2 * yn * yn) + 2 * p2 * xn * yn
        return xd, yd

    def undistort(self, xd: float, yd: float, iterations: int = 20) -> tuple[float, float]:
        """Inverse of distort() by Newton iteration (the model has no closed-form inverse)."""
        if not any(self.dist):
            return xd, yd
        xn, yn = xd, yd
        h = 1e-7
        for _ in range(iterations):
            fx, fy = self.distort(xn, yn)
            ex, ey = fx - xd, fy - yd
            if abs(ex) < 1e-12 and abs(ey) < 1e-12:
                break
            # Numerical Jacobian of distort() at (xn, yn)
            ax, ay = self.distort(xn + h, yn)
            bx, by = self.distort(xn, yn + h)
            j11, j12, j21, j22 = (ax - fx) / h, (bx - fx) / h, (ay - fy) / h, (by - fy) / h
            det = j11 * j22 - j12 * j21
            xn -= (j22 * ex - j12 * ey) / det
            yn -= (-j21 * ex + j11 * ey) / det
        return xn, yn

    def project(self, ray: np.ndarray) -> tuple[float, float] | None:
        """Pixel (u, v) of a direction in the optical frame; None if it points behind the camera."""
        if ray[2] <= 1e-6:
            return None
        xd, yd = self.distort(ray[0] / ray[2], ray[1] / ray[2])
        return self.cx + self.fx * xd, self.cy + self.fy * yd

    def pixel_to_los(self, u: float, v: float) -> np.ndarray:
        """Unit line-of-sight vector in the optical frame for pixel (u, v)."""
        xn, yn = self.undistort((u - self.cx) / self.fx, (v - self.cy) / self.fy)
        r = np.array([xn, yn, 1.0])
        return r / np.linalg.norm(r)

    def contains(self, u: float, v: float) -> bool:
        return 0 <= u < self.width and 0 <= v < self.height
