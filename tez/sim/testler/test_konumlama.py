"""Flat-ground position of the target (follow_me's FOLLOW_TARGET) without Gazebo or PX4: a known EKF pose and a known
ground point -> pixel -> back to the point; the refusals (horizon, image edge, pose history); the latitude / longitude
projections of PX4 and of Gazebo's world."""

import math
from pathlib import Path

import numpy as np
import pytest

import algilama
import kamera
import konumlama

CM3 = kamera.Camera(2304, 1296, 1773.9, 1773.9, 1152.0, 648.0)  # models/x500_tez, ideal pinhole
DISTORTED = kamera.Camera(2304, 1296, 1500.0, 1502.0, 1160.0, 640.0, (-0.30, 0.10, 0.001, -0.0005, -0.02))
ORIGIN = konumlama.GeoPoint(47.3979711, 8.5461637, 488.27)  # EKF origin as GPS_GLOBAL_ORIGIN gives it (1e-7 deg)
HOME_D = -0.031  # [m] home position D in the EKF frame (the vehicle armed a little above the origin)
GROUND_D = HOME_D + konumlama.GROUND_BELOW_HOME_M
WORLDS = Path(__file__).resolve().parents[1] / "worlds"


def quat(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """(w, x, y, z) of body FRD -> NED for 3-2-1 Euler angles [deg] (what ATTITUDE_QUATERNION carries)."""
    r, p, y = (math.radians(a) / 2 for a in (roll, pitch, yaw))
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return np.array(
        [
            cr * cp * cy + sr * sp * sy,
            sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
        ]
    )


def history(t: float, q: np.ndarray, p: np.ndarray, before: float = 0.02, after: float = 0.02) -> konumlama.PoseHistory:
    """A pose history that holds the pose `q`, `p` from t - before to t + after, with the origin and home known."""
    h = konumlama.PoseHistory()
    for dt in (-before, 0.0, after):
        h.add_attitude(t + dt, q)
        h.add_position(t + dt, p)
    h.set_origin(ORIGIN)
    h.set_home(np.array([0.4, -0.2, HOME_D]), ORIGIN.alt - HOME_D)
    return h


def pixel_of(camera: kamera.Camera, point: np.ndarray, q: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    """Where a NED point appears in the image of the nominally mounted camera of a drone at pose (q, p)."""
    c_bn = kamera.quat_to_dcm(*q)
    cam = p + c_bn @ konumlama.NOMINAL_OFFSET_FRD
    uv = camera.project(konumlama.NOMINAL_MOUNT.T @ c_bn.T @ (point - cam))
    assert uv is not None
    return uv


def standing_on(foot: tuple[float, float], height: float = 190.0) -> algilama.Kutu:
    """A person's box whose bottom middle is the pixel `foot` (pixel edges, like the detector's)."""
    u, v = foot
    return algilama.Kutu(u - 30.0, v - height, u + 30.0, v, 0.9, 0, "Person")


@pytest.mark.parametrize("camera", [CM3, DISTORTED], ids=["cm3", "bozulmali"])
@pytest.mark.parametrize(
    "attitude, ahead, left",
    [((0, 0, 0), 8.0, 0.0), ((4, -11, 35), 9.5, 2.5), ((-7, 12, 210), 10.0, -2.0), ((2, -20, -60), 5.0, 1.0)],
)
def test_a_ground_point_seen_from_a_known_pose_comes_back_within_a_centimetre(
    camera: kamera.Camera, attitude: tuple[float, float, float], ahead: float, left: float
) -> None:
    """Known EKF pose and ground point -> the pixel the point appears at -> a box standing on that pixel -> foot ray
    -> ground plane -> the same point, in NED and through PX4's latitude / longitude projection."""
    t = 71.3
    q, p = quat(*attitude), np.array([3.0, -2.0, -8.0])
    heading = math.radians(attitude[2])
    ground = np.array(
        [
            p[0] + ahead * math.cos(heading) - left * math.sin(heading),
            p[1] + ahead * math.sin(heading) + left * math.cos(heading),
            GROUND_D,
        ]
    )
    foot = pixel_of(camera, ground, q, p)
    assert camera.contains(*foot)
    box = standing_on(foot)
    fix = konumlama.Locator().locate(box, t, camera, history(t, q, p))
    assert fix.status == "hesaplandi" and fix.ok
    assert np.linalg.norm(fix.ned - ground) < 0.01
    assert fix.foot == pytest.approx(((box.u0 + box.u1) / 2, box.v1))
    assert 0.25 <= fix.down <= 1.0
    north, east = konumlama.MapProjection(ORIGIN.lat, ORIGIN.lon).project(fix.geo.lat, fix.geo.lon)
    assert math.hypot(north - ground[0], east - ground[1]) < 0.01
    assert fix.geo.alt == pytest.approx(ORIGIN.alt - GROUND_D)  # the ground's AMSL height: where the feet are
    assert fix.horizontal_m == pytest.approx(math.hypot(ground[0] - p[0], ground[1] - p[1]), abs=0.01)


def test_rays_close_to_the_horizon_are_refused() -> None:
    """u_D < 0.25: a ray 14.5 deg or less below the horizon (a far detection, or the nose pitched up); the flat-ground
    distance grows without bound there."""
    t, q, p = 80.0, quat(0, 15, 90), np.array([0.0, 0.0, -8.0])  # nose 15 deg up: the image top is ~10 deg down
    poses = history(t, q, p)
    c_bn = kamera.quat_to_dcm(*q)
    cam = p + c_bn @ konumlama.NOMINAL_OFFSET_FRD
    found = {}
    for down in (0.24, 0.26):
        ray = np.array([0.0, math.sqrt(1 - down * down), down])  # due east, `down` below the horizon
        uv = CM3.project(konumlama.NOMINAL_MOUNT.T @ c_bn.T @ ray)
        assert uv is not None and CM3.contains(*uv)
        found[down] = konumlama.Locator().locate(standing_on(uv, 60.0), t, CM3, poses)
    assert found[0.24].status == "ufka_yakin" and found[0.24].ned is None
    assert found[0.24].down == pytest.approx(0.24, abs=1e-6)
    assert found[0.26].status == "hesaplandi"
    assert found[0.26].ned[2] == pytest.approx(GROUND_D) and found[0.26].ned[1] > 25.0  # ~29 m ahead
    assert cam[2] < GROUND_D


def test_boxes_at_the_left_right_or_bottom_edge_of_the_image_are_refused() -> None:
    """Closer than 8 px to the left, right or bottom edge the feet (or one side of the person) may be cut off: the
    bottom middle is not the foot point. A head cut off at the top leaves the feet where they are."""
    t, q, p = 70.0, quat(0, 0, 0), np.array([0.0, 0.0, -8.0])
    poses = history(t, q, p)
    locate = konumlama.Locator().locate
    w, h = CM3.width, CM3.height
    for box, status in (
        ((7.0, 300.0, 70.0, 700.0), "kenar"),
        ((8.0, 300.0, 70.0, 700.0), "hesaplandi"),
        ((2200.0, 300.0, w - 7.0, 700.0), "kenar"),
        ((2200.0, 300.0, w - 8.0, 700.0), "hesaplandi"),
        ((1100.0, 900.0, 1160.0, h - 7.0), "kenar"),
        ((1100.0, 900.0, 1160.0, h - 8.0), "hesaplandi"),
        ((1100.0, 0.0, 1160.0, 300.0), "hesaplandi"),  # touches the top: the feet are visible
    ):
        fix = locate(algilama.Kutu(*box, 0.9, 0, "Person"), t, CM3, poses)
        assert fix.status == status, box
    assert locate(None, t, CM3, poses).status == "kutu_yok"
    assert locate(standing_on((1152.0, 900.0)), t, None, poses).status == "kamera_yok"


def test_the_pose_history_must_cover_the_capture_time() -> None:
    """The EKF pose of the frame's capture time is interpolated between the samples before and after it (attitude
    nlerp, position linear); both must be at most 0.15 s away, else there is no position."""
    t = 65.0
    h = konumlama.PoseHistory()
    for k in range(-50, 0):  # 50 Hz up to 20 ms before the frame, nothing after it yet
        h.add_attitude(t + 0.02 * k, quat(0, 0, 0))
        h.add_position(t + 0.02 * k, np.zeros(3))
    assert h.at(t) is None

    h = konumlama.PoseHistory()
    h.add_attitude(t - 0.14, quat(0, 0, 0))
    h.add_attitude(t + 0.14, quat(0, 0, 10))
    h.add_position(t - 0.10, np.array([0.0, 0.0, -8.0]))
    h.add_position(t + 0.02, np.array([1.2, 0.0, -8.0]))
    pose = h.at(t)
    assert pose is not None
    assert pose.euler_deg() == pytest.approx((0.0, 0.0, 5.0), abs=1e-6)  # halfway in time between 0 and 10 deg
    assert pose.p == pytest.approx([1.0, 0.0, -8.0])  # 100 ms of 120 ms between the two positions
    assert (pose.before_ms, pose.after_ms) == pytest.approx((140.0, 140.0))

    h.add_attitude(t - 0.16, quat(0, 0, 0))  # late and older: the nearest sample before the frame still counts
    assert h.at(t).euler_deg() == pytest.approx((0.0, 0.0, 5.0), abs=1e-6)
    gap = konumlama.PoseHistory()
    gap.add_attitude(t - 0.16, quat(0, 0, 0))
    gap.add_attitude(t + 0.01, quat(0, 0, 0))
    gap.add_position(t - 0.01, np.zeros(3))
    gap.add_position(t + 0.01, np.zeros(3))
    assert gap.at(t) is None  # the attitude before the frame is 0.16 s old

    box = standing_on((1152.0, 900.0))
    assert konumlama.Locator().locate(box, t, CM3, gap).status == "poz_yok"
    known = history(t, quat(0, 0, 0), np.array([0.0, 0.0, -8.0]))
    blind = konumlama.PoseHistory()
    for dt in (-0.02, 0.02):
        blind.add_attitude(t + dt, quat(0, 0, 0))
        blind.add_position(t + dt, np.array([0.0, 0.0, -8.0]))
    assert konumlama.Locator().locate(box, t, CM3, blind).status == "referans_yok"  # no origin / home yet
    assert konumlama.Locator().locate(box, t, CM3, known).status == "hesaplandi"


def test_latitude_longitude_like_px4_and_like_gazebo() -> None:
    """PX4 turns FOLLOW_TARGET's latitude / longitude into its NED frame with lib/geo MapProjection (azimuthal
    equidistant, sphere of 6371 km) about the EKF origin; Gazebo's NavSat gives the drone's GPS from the world's
    spherical_coordinates on WGS84 (gz-math LOCAL2 = ENU). Both directions of both, and the values of each."""
    px4 = konumlama.MapProjection(ORIGIN.lat, ORIGIN.lon)
    for north, east in ((10.0, 0.0), (0.0, 10.0), (-35.5, 120.25), (150.0, -150.0)):
        lat, lon = px4.reproject(north, east)
        assert px4.project(lat, lon) == pytest.approx((north, east), abs=1e-6)
    lat, _ = px4.reproject(10.0, 0.0)
    assert lat - ORIGIN.lat == pytest.approx(math.degrees(10.0 / 6371000.0), rel=1e-9)
    _, lon = px4.reproject(0.0, 10.0)
    assert (lon - ORIGIN.lon) * math.cos(math.radians(ORIGIN.lat)) == pytest.approx(
        math.degrees(10.0 / 6371000.0), rel=1e-6
    )

    world = konumlama.world_geo(WORLDS / "duz_alan.sdf")
    assert (world.lat0, world.lon0, world.elevation) == (47.397971057728974, 8.546163739800146, 0.0)
    assert konumlama.world_geo(WORLDS / "cayir.sdf") == world
    # gz.math7 SphericalCoordinates.position_transform(LOCAL2 -> SPHERICAL) of this origin (gz-math 7.7.0): the
    # positions Gazebo's NavSat would report
    for local, gazebo in (
        ((10.0, 0.0), (47.39797105765246, 8.546296208701765, 7.82497227191925e-06)),
        ((0.0, 10.0), (47.398061003094845, 8.546163739800145, 7.848255336284637e-06)),
    ):
        lat, lon, h = world.to_geodetic(*local)
        assert (lat, lon) == pytest.approx(gazebo[:2], abs=1e-12)  # 1e-12 deg = 0.1 micrometre
        assert h == pytest.approx(gazebo[2], abs=1e-8)  # the ENU plane rises above the ellipsoid by d^2 / 2R
    for x, y in ((10.0, 0.0), (-20.0, 35.0), (120.0, -80.0)):
        assert world.to_local(*world.to_geodetic(x, y)) == pytest.approx((x, y, 0.0), abs=1e-6)
