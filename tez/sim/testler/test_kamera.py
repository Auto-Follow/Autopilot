"""Camera model against the worked example of "Pikselden Vektöre Dönüşüm" (H. Uygun, 2026-10-10).

The example camera is the team's calibrated IMX296 (1440x1080), not the Camera Module 3; only the math is checked.
"""

import math

import numpy as np
import pytest

import kamera

IMX296 = kamera.Camera(
    1440, 1080, 1529.93, 1530.40, 747.530, 535.242, (-0.4346, 0.200824, 0.000352666, 0.000935646, -0.0227967)
)
PIXEL = (1010.0, 290.0)  # centre of the 20x20 bbox at x=1000, y=280


def test_normalized_and_undistorted_point() -> None:
    xd, yd = (PIXEL[0] - IMX296.cx) / IMX296.fx, (PIXEL[1] - IMX296.cy) / IMX296.fy
    assert (xd, yd) == pytest.approx((0.17156, -0.16025), abs=1e-5)
    xn, yn = IMX296.undistort(xd, yd)
    assert (xn, yn) == pytest.approx((0.17577, -0.16425), abs=1e-5)
    assert IMX296.distort(xn, yn) == pytest.approx((xd, yd), abs=1e-10)


def test_camera_los_and_angles() -> None:
    los = IMX296.pixel_to_los(*PIXEL)
    assert los == pytest.approx([0.17089, -0.15970, 0.97226], abs=1e-5)
    assert kamera.deviation(los, "optical") == pytest.approx((9.97, -9.33, 13.53), abs=0.01)


def test_body_los_with_30_deg_tilt() -> None:
    body = kamera.camera_to_body(math.radians(30)) @ IMX296.pixel_to_los(*PIXEL)
    assert body == pytest.approx([0.92185, 0.17089, 0.34783], abs=1e-5)
    assert kamera.deviation(body, "body") == pytest.approx((10.50, 20.67, 22.80), abs=0.01)


def test_ned_los() -> None:
    body = np.array([0.92185, 0.17089, 0.34783])
    ned = kamera.body_to_ned(math.radians(8), math.radians(-4), math.radians(60)) @ body
    assert ned == pytest.approx([0.34233, 0.83457, 0.43164], abs=1e-4)


def test_edge_of_image_needs_undistortion() -> None:
    """Last pixel column (u = 1439, 691 px right of the principal point): 24.32 deg without, 26.53 deg with it."""
    u = 1439.0
    assert math.degrees(math.atan((u - IMX296.cx) / IMX296.fx)) == pytest.approx(24.32, abs=0.01)
    assert kamera.deviation(IMX296.pixel_to_los(u, IMX296.cy), "optical")[0] == pytest.approx(26.53, abs=0.01)


@pytest.mark.parametrize("u, v", [(0, 0), (1439, 1079), (720, 540), (1010, 290), (100, 900)])
def test_project_inverts_pixel_to_los(u: float, v: float) -> None:
    assert IMX296.project(IMX296.pixel_to_los(u, v)) == pytest.approx((u, v), abs=1e-6)


def test_gazebo_camera_axes() -> None:
    """A Gazebo camera looks along +x; image right is -y, image down is -z."""
    assert kamera.GZ_CAMERA_TO_OPTICAL @ [1, 0, 0] == pytest.approx([0, 0, 1])
    assert kamera.GZ_CAMERA_TO_OPTICAL @ [0, -1, 0] == pytest.approx([1, 0, 0])
    assert kamera.GZ_CAMERA_TO_OPTICAL @ [0, 0, -1] == pytest.approx([0, 1, 0])


def test_behind_camera_is_not_projected() -> None:
    assert IMX296.project(np.array([0.0, 0.0, -1.0])) is None
