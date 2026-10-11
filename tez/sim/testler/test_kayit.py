"""Ground truth rows without Gazebo: a drone pose, the x500_tez camera mount and a scenario target."""

import math

import numpy as np
import pytest

import hedef
import kamera
import kayit
import yuruyus

CM3 = kamera.Camera(2304, 1296, 1773.9, 1773.9, 1152.0, 648.0)
TILT = math.radians(45)
# camera_link in models/x500_tez/model.sdf: 0.151 m forward, 0.035 m down, pitched 45 deg (Gazebo FLU, +pitch = down)
CAM_POS = np.array([0.151, 0.0, -0.035])
CAM_R = np.array([[math.cos(TILT), 0, math.sin(TILT)], [0, 1, 0], [-math.sin(TILT), 0, math.cos(TILT)]])
LEVEL_EAST = np.array([1.0, 0.0, 0.0, 0.0])  # Gazebo model facing east, level


def scenario(start: tuple[float, float]) -> hedef.Scenario:
    """A target standing at `start` the whole time."""
    sc = hedef.Scenario("t", "", "duz_alan", 10.0, "tez", start, 60.0, 5.0)
    sc.track, sc.walk_end = yuruyus.plan(start, 60.0, [("wait", 1.0)], yuruyus.Behaviour())
    return sc


def test_mount_matches_the_pdf_chain() -> None:
    assert kayit.camera_to_body_dcm(CAM_R) == pytest.approx(kamera.camera_to_body(TILT))


def test_target_on_the_optical_axis_is_in_the_image_centre() -> None:
    # Camera 10 m up (at its own height) looking 45 deg down: the axis meets the body-centre height 9.1 m ahead.
    p_model = np.array([0.0, 0.0, 10.0])
    cam_z = 10.0 - 0.035
    ahead = 0.151 + (cam_z - 0.9)
    row = kayit.truth_row(70.0, scenario((ahead, 0.0)), CM3, p_model, LEVEL_EAST, CAM_POS, CAM_R)
    assert (row["merkez_u"], row["merkez_v"]) == pytest.approx((1152.0, 648.0), abs=1e-6)
    assert row["kadrajda"]
    assert [row["los_kamera_x"], row["los_kamera_y"], row["los_kamera_z"]] == pytest.approx([0, 0, 1], abs=1e-9)
    assert row["sapma_dikey_deg"] == pytest.approx(45.0)
    assert row["sapma_yatay_deg"] == pytest.approx(0.0, abs=1e-9)
    assert row["dron_yaw_deg"] == pytest.approx(90.0)  # facing east in PX4's NED
    # LOS in NED: east and down, 45 deg
    assert [row["los_ned_x"], row["los_ned_y"], row["los_ned_z"]] == pytest.approx([0, 0.70711, 0.70711], abs=1e-5)


def test_target_to_the_left_and_behind() -> None:
    p_model = np.array([0.0, 0.0, 10.0])
    left = kayit.truth_row(70.0, scenario((9.0, 3.0)), CM3, p_model, LEVEL_EAST, CAM_POS, CAM_R)
    assert left["merkez_u"] < 1152.0 and left["sapma_yatay_deg"] < 0  # north is left when facing east
    behind = kayit.truth_row(70.0, scenario((-10.0, 0.0)), CM3, p_model, LEVEL_EAST, CAM_POS, CAM_R)
    assert not behind["kadrajda"] and math.isnan(behind["merkez_u"])


def test_euler_of_a_yawed_model() -> None:
    # Gazebo yaw +30 deg (towards north from east) is PX4 yaw 60 deg (from north towards east)
    q = np.array([math.cos(math.radians(15)), 0, 0, math.sin(math.radians(15))])
    assert kayit.euler_frd_ned(kamera.quat_to_dcm(*q)) == pytest.approx((0.0, 0.0, 60.0), abs=1e-9)


def test_nlerp_halfway() -> None:
    q0 = np.array([1.0, 0, 0, 0])
    q1 = np.array([math.cos(0.1), 0, 0, math.sin(0.1)])
    assert kayit.nlerp(q0, q1, 0.5) == pytest.approx([math.cos(0.05), 0, 0, math.sin(0.05)], abs=1e-6)
