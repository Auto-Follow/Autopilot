"""MAVLink connection to PX4 SITL for the simulation tools (acts as the ground station on UDP 14540)."""

import math
import socket
import struct
import threading
import time
from collections.abc import Callable

from pymavlink import mavutil

# Names PX4 gives its own modes in AVAILABLE_MODES (src/lib/modes/ui.hpp nav_state_names; what QGC shows).
# Modes are always chosen by name: the numbers of external modes depend on the registration order.
HOLD_MODE_NAME = "Hold"
FOLLOW_TARGET_MODE_NAME = "Follow Target"


def decode_param_value(value: float, param_type: int) -> int | float:
    """PARAM_VALUE.param_value as the parameter's own type.

    PX4 copies INT32 parameters bit for bit into the float field (MAV_PROTOCOL_CAPABILITY_PARAM_ENCODE_BYTEWISE,
    mavlink_parameters.cpp send_param), so 4001 arrives as the float 5.6e-42 and has to be reinterpreted.
    """
    if param_type == mavutil.mavlink.MAV_PARAM_TYPE_INT32:
        return struct.unpack("<i", struct.pack("<f", value))[0]
    return value


class Vehicle:
    def __init__(self, timeout: float = 60.0, verbose: bool = True) -> None:
        self.verbose = verbose
        self.m = mavutil.mavlink_connection("udpin:127.0.0.1:14540", dialect="development")
        # PX4 streams up to 4 MB/s on this link; while the tools are busy (camera frames) the default 208 KB socket
        # buffer overflowed and a COMMAND_ACK was lost (F1 run, 2026-10-11). Linux caps it at net.core.rmem_max.
        self.m.port.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        if self.m.wait_heartbeat(timeout=timeout) is None:
            raise RuntimeError("PX4'ten heartbeat gelmedi (calistir.sh çalışıyor mu?)")
        # The x500 airframe refuses to arm without a ground station (NAV_DLL_ACT 2): act as one.
        self._closed = threading.Event()
        threading.Thread(target=self._send_gcs_heartbeat, daemon=True).start()
        for name, rate_hz in (("LOCAL_POSITION_NED", 10), ("EXTENDED_SYS_STATE", 2)):
            msg_id = getattr(mavutil.mavlink, f"MAVLINK_MSG_ID_{name}")
            self.command(mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, msg_id, 1e6 / rate_hz, quiet=True)

    def close(self) -> None:
        self._closed.set()
        self.m.close()

    def _send_gcs_heartbeat(self) -> None:
        while not self._closed.wait(1.0):
            self.m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)

    def log(self, text: str) -> None:
        if self.verbose:
            print(f"     {text}", flush=True)

    def command(self, cmd: int, *params: float, quiet: bool = False) -> bool:
        p = list(params) + [0.0] * (7 - len(params))
        self.m.mav.command_long_send(self.m.target_system, self.m.target_component, cmd, 0, *p)
        ack = self.m.recv_match(type="COMMAND_ACK", condition=f"COMMAND_ACK.command=={cmd}", blocking=True, timeout=5)
        accepted = ack is not None and ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED
        if not accepted and not quiet:
            self.log(f"komut {cmd} reddedildi: {ack.result if ack else 'cevap yok'}")
        return accepted

    def wait(self, types: list[str], pred: Callable, timeout: float) -> object | None:
        """Return the first message of the given types that satisfies pred; print PX4 status texts meanwhile."""
        t_end = time.monotonic() + timeout
        while time.monotonic() < t_end:
            msg = self.m.recv_match(type=[*types, "STATUSTEXT"], blocking=True, timeout=1)
            if msg is None:
                continue
            if msg.get_type() == "STATUSTEXT":
                self.log(f"PX4: {msg.text.strip()}")
            elif pred(msg):
                return msg
        return None

    def modes(self, timeout: float = 15.0) -> dict[str, int]:
        """{mode name: custom_mode} of every mode PX4 offers (AVAILABLE_MODES, what QGC shows)."""
        # Index 0 asks for all modes. PX4 sends them before the COMMAND_ACK, so do not wait for the ack
        # (command() would drop them).
        self.m.mav.command_long_send(
            self.m.target_system,
            self.m.target_component,
            mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,
            0,
            mavutil.mavlink.MAVLINK_MSG_ID_AVAILABLE_MODES,
            *[0] * 6,
        )
        found: dict[str, int] = {}
        indices: set[int] = set()  # names are not unique (unavailable modes all come as "(Mode not available)")
        total = None
        t_end = time.monotonic() + timeout
        while time.monotonic() < t_end and len(indices) != total:
            msg = self.m.recv_match(type="AVAILABLE_MODES", blocking=True, timeout=1)
            if msg is not None:
                found[msg.mode_name] = msg.custom_mode
                indices.add(msg.mode_index)
                total = msg.number_modes
        if len(indices) != total:
            self.log(f"mod listesi eksik geldi ({len(indices)}/{total}): {sorted(found)}")
        return found

    def switch_mode(self, custom_mode: int, timeout: float = 5.0) -> bool:
        """Ask for a mode and wait until PX4's heartbeat reports it (the heartbeat decides, not the ack)."""
        # PX4 packs main mode into byte 2 and sub mode into byte 3 of custom_mode
        main_mode, sub_mode = (custom_mode >> 16) & 0xFF, (custom_mode >> 24) & 0xFF
        for _ in range(2):
            self.command(
                mavutil.mavlink.MAV_CMD_DO_SET_MODE,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                main_mode,
                sub_mode,
            )
            if self.current_mode(timeout, want=custom_mode) == custom_mode:
                return True
        return False

    def current_mode(self, timeout: float = 3.0, want: int | None = None) -> int | None:
        """custom_mode in the next autopilot heartbeat (or the first one equal to `want`)."""
        hb = self.wait(
            ["HEARTBEAT"],
            lambda h: h.get_srcComponent() == 1 and (want is None or h.custom_mode == want),
            timeout,
        )
        return hb.custom_mode if hb is not None else None

    def get_param(self, name: str, timeout: float = 6.0) -> int | float | None:
        """Current value of a PX4 parameter (PARAM_REQUEST_READ); None if PX4 does not answer (unknown name)."""
        tries = 3  # UDP: a request or its answer can get lost while PX4 streams telemetry
        for _ in range(tries):
            self.m.mav.param_request_read_send(self.m.target_system, self.m.target_component, name.encode(), -1)
            msg = self.m.recv_match(
                type="PARAM_VALUE", condition=f"PARAM_VALUE.param_id=='{name}'", blocking=True, timeout=timeout / tries
            )
            if msg is not None:
                return decode_param_value(msg.param_value, msg.param_type)
        return None

    def set_param(self, name: str, value: float) -> None:
        self.m.mav.param_set_send(
            self.m.target_system, self.m.target_component, name.encode(), value, mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        )
        self.m.recv_match(type="PARAM_VALUE", condition=f"PARAM_VALUE.param_id=='{name}'", blocking=True, timeout=5)

    def takeoff(self, altitude: float, timeout: float = 120.0) -> bool:
        """Take off to `altitude` [m] above home and wait until it is reached. Retries arming while the estimator
        is still converging, like a pilot would."""
        nan = math.nan
        if self.wait(["LOCAL_POSITION_NED"], lambda _: True, 60) is None:
            self.log("LOCAL_POSITION_NED gelmedi")
            return False
        self.set_param("MIS_TAKEOFF_ALT", altitude)
        t_end = time.monotonic() + timeout
        armed = False
        while time.monotonic() < t_end and not armed:
            armed = self.command(
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, -1, 0, 0, nan, nan, nan, nan, quiet=True
            ) and self.command(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1, quiet=True)
            if not armed:
                time.sleep(2)
        if not armed:
            self.log("arm edilemedi")
            return False
        remaining = max(1.0, t_end - time.monotonic())
        return self.wait(["LOCAL_POSITION_NED"], lambda p: -p.z > altitude - 0.5, remaining) is not None

    def land(self, timeout: float = 90.0) -> bool:
        """Land at the current position and wait for disarm."""
        nan = math.nan
        self.command(mavutil.mavlink.MAV_CMD_NAV_LAND, 0, 0, 0, nan, nan, nan, nan)
        landed = self.wait(
            ["EXTENDED_SYS_STATE"], lambda s: s.landed_state == mavutil.mavlink.MAV_LANDED_STATE_ON_GROUND, timeout
        )
        disarmed = self.wait(
            ["HEARTBEAT"],
            lambda h: h.get_srcComponent() == 1 and not (h.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED),
            20,
        )
        return landed is not None and disarmed is not None
