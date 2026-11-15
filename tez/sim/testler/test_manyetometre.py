"""The drone's magnetometer in the simulation (spec 2026-11-10-m06-sim-ortami "Varsayımlar" 6,
implementation/gorev-grubu-07.md, part A), checked against the locked PX4 v1.17.0 source; no Gazebo or PX4 run.

Gazebo Harmonic's magnetometer system (gz-sim 8.15) computes the field from its own 10 deg tables and writes the NED
components into its ENU world frame; PX4 v1.17.0's gz_bridge maps that with x = -y, y = -x, z = z. Together this
mirrors the east component: at the world origin PX4 measured a declination of -2.57 deg while its EKF expects the
WMM's +3.41 deg. The simulation therefore runs PX4's own sensor_mag_sim instead (the WMM field at the true position,
rotated by the true attitude) and loads no Gazebo magnetometer system.
"""

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

import konumlama
import parametreler

SIM_DIR = Path(__file__).resolve().parent.parent
REPO = SIM_DIR.parent.parent
WMM_TABLES = REPO / "src/lib/world_magnetic_model/geo_magnetic_tables.hpp"
WORLDS = ("duz_alan", "cayir")


def wmm_table(name: str) -> tuple[np.ndarray, float]:
    """One table of PX4's world magnetic model (int16, 10 deg grid from -90 / -180) and its scale."""
    text = WMM_TABLES.read_text(encoding="utf-8")
    body = re.search(rf"{name}_table\[19\]\[37\]\s*\{{(.*?)\}};", text, re.S).group(1)
    body = re.sub(r"/\*.*?\*/|//[^\n]*", "", body, flags=re.S)
    scale = float(re.search(rf"WMM_{name.upper()}_SCALE_TO_\w+\s*=\s*([0-9.eE+-]+)", text).group(1))
    return np.array([int(v) for v in re.findall(r"-?\d+", body)], dtype=float).reshape(19, 37), scale


def wmm(name: str, lat: float, lon: float) -> float:
    """lib/world_magnetic_model/geo_mag_declination.cpp get_table_data: bilinear between the four grid corners."""
    table, scale = wmm_table(name)
    lat0, lon0 = math.floor(lat / 10.0) * 10.0, math.floor(lon / 10.0) * 10.0
    i, j = int((lat0 + 90.0) / 10.0), int((lon0 + 180.0) / 10.0)
    a, b = (lat - lat0) / 10.0, (lon - lon0) / 10.0
    low = b * (table[i, j + 1] - table[i, j]) + table[i, j]
    high = b * (table[i + 1, j + 1] - table[i + 1, j]) + table[i + 1, j]
    return (a * (high - low) + low) * scale


def wmm_field_enu(lat: float, lon: float) -> np.ndarray:
    """PX4's expected earth field [T] in ENU (what an SDF <magnetic_field> holds)."""
    decl = math.radians(wmm("declination", lat, lon))
    incl = math.radians(wmm("inclination", lat, lon))
    h = wmm("totalintensity", lat, lon) * 1e-9 * math.cos(incl)
    return np.array([h * math.sin(decl), h * math.cos(decl), -h * math.tan(incl)])


def test_worlds_hold_px4s_wmm_field_of_their_origin() -> None:
    """<magnetic_field> of every world is PX4's WMM at its <spherical_coordinates> (Zurich, PX4's default home):
    declination +3.41 deg, inclination 63.16 deg, 48 239 nT. No system reads it (server.config loads no Gazebo
    magnetometer system); it is written so that the world file says what the drone's magnetometer measures."""
    for name in WORLDS:
        sdf = SIM_DIR / "worlds" / f"{name}.sdf"
        geo = konumlama.world_geo(sdf)
        field = np.array([float(v) for v in ET.parse(sdf).getroot().findtext("world/magnetic_field").split()])
        expected = wmm_field_enu(geo.lat0, geo.lon0)
        assert field == pytest.approx(expected, abs=2e-10), name
    assert wmm("declination", geo.lat0, geo.lon0) == pytest.approx(3.406, abs=0.001)


def test_the_drone_magnetometer_is_px4s_simulated_one() -> None:
    """sim.params turns on PX4's sensor_mag_sim (px4-rc.gzsim starts it), which uses the true pose that gz_bridge
    publishes; Gazebo's magnetometer system is not loaded, so gz_bridge receives no second, mirrored field."""
    assert parametreler.load()["SENS_EN_MAGSIM"].value == 1
    assert "gz-sim-magnetometer-system" not in "".join(
        ET.tostring(p, encoding="unicode") for p in ET.parse(SIM_DIR / "server.config").getroot().iter("plugin")
    )
    rc = (REPO / "ROMFS/px4fmu_common/init.d-posix/px4-rc.gzsim").read_text(encoding="utf-8")
    assert re.search(r"param compare -s SENS_EN_MAGSIM 1\s*then\s*sensor_mag_sim start", rc)
    sim = (REPO / "src/modules/simulation/sensor_mag_sim/SensorMagSim.hpp").read_text(encoding="utf-8")
    assert "ORB_ID(vehicle_attitude_groundtruth)" in sim and "ORB_ID(vehicle_global_position_groundtruth)" in sim
    assert "197388" in sim  # the device id of rcS's CAL_MAG0_ID: calibrated, priority 50


@pytest.mark.parametrize("yaw_deg", [0.0, 37.0, 90.0, 200.0, -120.0])
def test_gazebo_harmonics_field_reaches_px4_with_the_east_part_mirrored(yaw_deg: float) -> None:
    """Why Gazebo's magnetometer is not used: gz-sim 8 sets the world field to (N, E, D) of its tables in ENU slots
    (Magnetometer.cc, use_earth_frame_ned true), gz-sensors rotates it into the body (FLU), and PX4's gz_bridge maps
    the body field with x = -y, y = -x, z = z (GZBridge.cpp). Rotated to NED with the true attitude, PX4 sees the
    declination with the opposite sign for every heading."""
    bridge = (REPO / "src/modules/simulation/gz_bridge/GZBridge.cpp").read_text(encoding="utf-8")
    assert "report.x = -msg.field_tesla().y();" in bridge and "report.y = -msg.field_tesla().x();" in bridge
    decl, incl, strength = math.radians(2.564), math.radians(63.25), 0.4807  # gz-sim 8.15 tables at the world origin
    h = strength * math.cos(incl)
    world_slots = np.array([h * math.cos(decl), h * math.sin(decl), h * math.tan(incl)])  # (N, E, D) as (x, y, z)
    psi = math.radians(yaw_deg)  # PX4 heading (NED); in Gazebo's ENU the nose is at 90 deg - psi from east
    theta = math.pi / 2 - psi
    r_world_body = np.array(
        [[math.cos(theta), -math.sin(theta), 0.0], [math.sin(theta), math.cos(theta), 0.0], [0, 0, 1]]
    )
    flu = r_world_body.T @ world_slots
    frd = np.array([-flu[1], -flu[0], flu[2]])  # gz_bridge
    r_ned_body = np.array([[math.cos(psi), -math.sin(psi), 0.0], [math.sin(psi), math.cos(psi), 0.0], [0, 0, 1]])
    ned = r_ned_body @ frd
    assert math.degrees(math.atan2(ned[1], ned[0])) == pytest.approx(-2.564, abs=1e-9)
    assert math.degrees(math.atan2(ned[2], math.hypot(ned[0], ned[1]))) == pytest.approx(63.25, abs=1e-9)
