"""MAVLink messages of the simulation without PX4: TEZ_LOS as DEBUG_VECT, the rules of the TEZ_LOS stream, the one
send lock and the PX4 mode names (AVAILABLE_MODES)."""

import math
import re
import threading
import time
from pathlib import Path

import numpy as np
import pytest
from pymavlink.dialects.v20 import development as mavlink

import px4_baglanti

REPO = Path(__file__).resolve().parents[3]


def decoded(msg: object) -> object:
    """A message as PX4's MAVLink parser would see it: packed into bytes, parsed back."""
    return mavlink.MAVLink(None).parse_char(msg.pack(mavlink.MAVLink(None)))


def test_tez_los_is_a_debug_vect_with_a_unit_vector_or_nan() -> None:
    mav = mavlink.MAVLink(None)
    unit = np.array([0.6, -0.48, 0.64])
    back = decoded(px4_baglanti.los_message(mav, 61_032_000, unit))
    assert back.get_type() == "DEBUG_VECT" and back.name == "TEZ_LOS" and back.time_usec == 61_032_000
    assert (back.x, back.y, back.z) == pytest.approx(tuple(unit), abs=1e-7)  # float32 on the wire
    assert math.hypot(back.x, back.y, back.z) == pytest.approx(1.0, abs=1e-6)
    assert len(px4_baglanti.TEZ_LOS_NAME) <= 9  # PX4 keeps 9 characters of the name (debug_vect.name is char[10])

    none = decoded(px4_baglanti.los_message(mav, 61_065_000, None))  # hedef yok
    assert none.name == "TEZ_LOS" and all(math.isnan(v) for v in (none.x, none.y, none.z))

    for bad in ([math.nan, 0.0, 1.0], [0.6, 0.0, 0.81], [0.0, 0.0, 0.0], [math.inf, 0.0, 0.0]):
        assert px4_baglanti.check_los(np.array(bad)) is not None
        with pytest.raises(ValueError):
            px4_baglanti.los_message(mav, 1, np.array(bad))
    assert px4_baglanti.check_los(np.array([0.6, 0.0, 0.8004])) is None  # |norm - 1| = 3.2e-4 < 1e-3
    assert px4_baglanti.check_los(None) is None


class FakeLink:
    def __init__(self) -> None:
        self.sent: list[tuple[int, tuple | None]] = []

    def send_los(self, time_usec: int, vec: np.ndarray | None) -> None:
        self.sent.append((time_usec, None if vec is None else tuple(vec)))


def test_only_valid_new_frames_go_to_px4_and_everything_else_is_counted() -> None:
    """One message per frame, frames only forwards in time, at most one per camera frame interval (30 Hz), never a
    vector PX4 would have to throw away (two-sided validation)."""
    s = px4_baglanti.LosSender()
    unit = np.array([0.6, 0.0, 0.8])
    assert s.send(59.968, unit)[0] == "baglanti_yok"  # before the MAVLink link exists
    link = FakeLink()
    s.attach(link)
    assert s.send(60.000, unit)[0] == "gonderildi"
    assert s.send(60.000, unit)[0] == "ayni_kare"
    assert s.send(59.968, unit)[0] == "eski_kare"
    assert s.send(60.020, unit)[0] == "hiz_siniri"  # 20 ms after the last one: faster than the camera
    assert s.send(60.032, None)[0] == "gonderildi"  # next camera frame (32 ms with the 4 ms physics step): hedef yok
    for bad in ([math.nan, 0.0, 1.0], [0.6, 0.0, 0.81], [1.0, math.nan, 0.0]):
        assert s.send(60.068, np.array(bad))[0] == "gecersiz"
    assert s.send(60.068, unit)[0] == "gonderildi"
    s.detach()
    assert s.send(60.100, unit)[0] == "baglanti_yok"

    assert link.sent == [(60_000_000, (0.6, 0.0, 0.8)), (60_032_000, None), (60_068_000, (0.6, 0.0, 0.8))]
    assert s.counts == {
        "gonderildi": 3,
        "baglanti_yok": 2,
        "ayni_kare": 1,
        "eski_kare": 1,
        "hiz_siniri": 1,
        "gecersiz": 3,
    }


def test_every_message_of_the_connection_goes_through_one_lock() -> None:
    """The GCS heartbeat thread, the main thread (commands) and the tracking thread (TEZ_LOS) share one MAVLink
    connection: pymavlink's send is not thread safe (sequence number, buffer)."""

    class SlowMav:
        def __init__(self) -> None:
            self.inside = 0
            self.overlapped = False
            self.count = 0

        def send(self, _msg: object, force_mavlink1: bool = False) -> None:
            self.inside += 1
            self.overlapped |= self.inside > 1
            time.sleep(0.0005)
            self.count += 1
            self.inside -= 1

    mav = SlowMav()
    px4_baglanti.serialize_sends(mav, threading.Lock())
    threads = [threading.Thread(target=lambda: [mav.send(None) for _ in range(25)]) for _ in range(4)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert mav.count == 100 and not mav.overlapped


def available_mode(standard: int, custom: int, properties: int, name: bytes) -> object:
    return decoded(mavlink.MAVLink(None).available_modes_encode(26, 1, standard, custom, properties, name))


def test_modes_are_chosen_by_name_and_a_wrong_name_stops_the_run_with_the_choices() -> None:
    """AVAILABLE_MODES gives PX4's own modes by name, the standard ones (Position, Return...) without one, and
    the unregistered external slots as not selectable; a mode is never chosen by its number."""
    selectable, hidden = 0, mavlink.MAV_MODE_PROPERTY_NOT_USER_SELECTABLE
    assert px4_baglanti.mode_entry(available_mode(0, 0x4030000, selectable, b"Hold")) == ("Hold", 0x4030000)
    position = available_mode(mavlink.MAV_STANDARD_MODE_POSITION_HOLD, 0x30000, selectable, b"")
    assert px4_baglanti.mode_entry(position) == ("Position", 0x30000)
    assert px4_baglanti.mode_entry(available_mode(0, 0x1C0000, hidden, b"(Mode not available)")) is None
    assert px4_baglanti.mode_entry(available_mode(0, 0xD0000, hidden, b"Termination")) is None
    ext = available_mode(0, 0x170000, selectable, b"AUTO FOLLOW")  # a registered external mode (m15)
    assert px4_baglanti.mode_entry(ext) == ("AUTO FOLLOW", 0x170000)

    px4_baglanti.check_mode_name("Hold")
    px4_baglanti.check_mode_name("Follow Target")
    with pytest.raises(ValueError) as error:
        px4_baglanti.check_mode_name("Yok Boyle Mod")
    text = str(error.value)
    assert "'Yok Boyle Mod'" in text and "--mod-adi" in text and "--px4-baslat" in text
    assert all(name in text for name in px4_baglanti.STOCK_MODE_NAMES)
    # an external mode registers after PX4 starts: with a start command its name is looked up in the run
    px4_baglanti.check_mode_name("AUTO FOLLOW", px4_start=("auto_follow start",))


def test_stock_mode_names_are_the_ones_px4_v1_17_builds() -> None:
    """The list checked before the simulation starts = PX4's: the internal nav states of getValidNavStates() without
    Termination (ModeManagement::getModeStatus), named by nav_state_names (src/lib/modes/ui.hpp)."""
    ui = (REPO / "src/lib/modes/ui.hpp").read_text(encoding="utf-8")
    names = re.findall(r'"([^"]+)"', ui.split("nav_state_names[")[1].split("};")[0])
    valid = re.findall(r"NAVIGATION_STATE_(\w+)\)", ui.split("getValidNavStates()")[1].split(";")[0])
    status = (REPO / "msg/versioned/VehicleStatus.msg").read_text(encoding="utf-8")
    number = {k: int(v) for k, v in re.findall(r"uint8 NAVIGATION_STATE_(\w+) = (\d+)", status)}
    expected = {names[number[v]] for v in valid if v != "TERMINATION"}
    assert set(px4_baglanti.STOCK_MODE_NAMES) == expected and len(expected) == 17
    standard = {names[number[v]] for v in ("POSCTL", "ALTCTL", "AUTO_RTL", "AUTO_MISSION", "AUTO_LAND")}
    standard |= {names[number[v]] for v in ("AUTO_TAKEOFF", "ORBIT")}
    assert set(px4_baglanti.STANDARD_MODE_NAMES.values()) == standard
