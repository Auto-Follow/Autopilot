"""MAVLink connection to PX4 SITL for the simulation tools (acts as the ground station on UDP 14540).

TEZ_LOS (spec 2026-11-10-m06-sim-ortami, "Varsayımlar" 1; not final until the shared ICD, m05): the line of sight to
the target as DEBUG_VECT name "TEZ_LOS", x y z = unit vector in body FRD from the camera, time_usec = the frame's
capture time; x = y = z = NaN means "no target". LosSender keeps the stream's rules (one message per frame, frames
only forwards, at most one per camera frame interval) and Vehicle.send_los checks every vector before it goes out
(two-sided validation: PX4 checks again). Every message of the connection goes through one lock (serialize_sends).

FOLLOW_TARGET (spec 6, "Varsayımlar" 5): the target's flat-ground position for PX4's stock Follow Me ("Follow
Target"), at most every third camera frame (~10 Hz; FollowTargetSender, same stream rules). PX4 v1.17.0 takes lat,
lon, alt and vel only (mavlink_receiver handle_message_follow_target), fuses a position at most every 500 ms and a
velocity only if it is finite (TargetEstimator), so the velocity goes as NaN: a 0 would be fused as "standing still".

Vehicle keeps the autopilot's EKF pose (ATTITUDE_QUATERNION, LOCAL_POSITION_NED), the EKF origin and home in a
konumlama.PoseHistory through pymavlink's message_hooks: the main thread's recv_match loops read the socket as before
and every message they parse passes the hook (pose_hook), so no second reader competes for it.
"""

import math
import socket
import struct
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable

import numpy as np
from pymavlink import mavutil
from pymavlink.dialects.v20 import development as mavlink

import konumlama

# Names PX4 gives its own modes in AVAILABLE_MODES (src/lib/modes/ui.hpp nav_state_names; what QGC shows).
# Modes are always chosen by name: the numbers of external modes depend on the registration order.
HOLD_MODE_NAME = "Hold"
FOLLOW_TARGET_MODE_NAME = "Follow Target"
# Every mode PX4 v1.17.0 offers a multicopter for selection, before any external mode registers: the internal nav
# states of mode_util::getValidNavStates() without Termination (ModeManagement::getModeStatus: not settable), named
# by nav_state_names. Used to refuse a wrong takip.mod_adi before the simulation starts; in the run the names PX4
# reports (AVAILABLE_MODES) decide. PX4 is locked, the list cannot drift (test_mesajlar checks it against the source).
STOCK_MODE_NAMES = (
    "Manual",
    "Altitude",
    "Position",
    "Mission",
    HOLD_MODE_NAME,
    "Return",
    "Position Slow",
    "Altitude Cruise",
    "Acro",
    "Offboard",
    "Stabilized",
    "Takeoff",
    "Land",
    FOLLOW_TARGET_MODE_NAME,
    "Precision Landing",
    "Orbit",
    "VTOL Takeoff",
)
# AVAILABLE_MODES leaves mode_name empty for MAVLink standard modes (AVAILABLE_MODES.hpp send_single_mode); they get
# PX4's own name of the nav state behind them on a multicopter (lib/modes/standard_modes.hpp)
STANDARD_MODE_NAMES = {
    mavlink.MAV_STANDARD_MODE_POSITION_HOLD: "Position",
    mavlink.MAV_STANDARD_MODE_ORBIT: "Orbit",
    mavlink.MAV_STANDARD_MODE_ALTITUDE_HOLD: "Altitude",
    mavlink.MAV_STANDARD_MODE_SAFE_RECOVERY: "Return",
    mavlink.MAV_STANDARD_MODE_MISSION: "Mission",
    mavlink.MAV_STANDARD_MODE_LAND: "Land",
    mavlink.MAV_STANDARD_MODE_TAKEOFF: "Takeoff",
}

TEZ_LOS_NAME = "TEZ_LOS"  # DEBUG_VECT.name; PX4 keeps 9 characters (debug_vect.name is char[10])
LOS_NORM_TOLERANCE = 1e-3  # |norm - 1| below this: a unit vector (spec 5)
# [s, sim] least spacing of the capture times of two TEZ_LOS messages: one per camera frame at most (spec 5: "en çok
# 30 Hz"). The 30 Hz camera's frames come 32 or 36 ms apart in sim (4 ms physics step), so the limit sits below 32 ms
# and still stops anything faster than one message per frame. Capture times, not send times: the wall-clock spacing
# of two sends jitters with the threads and would drop good frames.
LOS_MIN_SPACING_S = 0.030
# [s, sim] least spacing of the capture times of two FOLLOW_TARGET messages (spec 6: "en çok 10 Hz"): every third
# camera frame at most, which is 96 or 100 ms after (frames 32, 32, 32, 36 ms apart); a 100 ms limit would take every
# fourth one (7.6 Hz). PX4 fuses a position at most every 500 ms (MINIMUM_TIME_BETWEEN_POS_FUSIONS_MS) and calls the
# target lost after 3 s without one (GPS_MESSAGE_STALE_TIMEOUT_MS).
FOLLOW_MIN_SPACING_S = 0.096
FOLLOW_POSITION_ONLY = 1  # FOLLOW_TARGET.est_capabilities: bit 0 POS (PX4 v1.17.0 does not read it)
AUTOPILOT_COMPONENT = 1  # MAV_COMP_ID_AUTOPILOT1: whose pose messages count
# [Hz] EKF pose streams for the frames' positions: PX4's own rates on an onboard link (mavlink_main.cpp
# MAVLINK_MODE_ONBOARD), which a Pi on TELEM2 in onboard mode would get if the link has the bandwidth (m04)
POSE_STREAMS = {"ATTITUDE_QUATERNION": 50, "LOCAL_POSITION_NED": 30}
# PX4 sends GPS_GLOBAL_ORIGIN only when the EKF origin is set or changes, or when asked (streams/GPS_GLOBAL_ORIGIN.hpp
# _force_next_send): set before this link was up, it never comes by itself. HOME_POSITION comes every 2 s once valid.
REFERENCE_MESSAGES = ("GPS_GLOBAL_ORIGIN", "HOME_POSITION")
REFERENCE_ASK_EVERY_S = 1.0  # [s] while waiting for them


def check_los(vec: np.ndarray | None) -> str | None:
    """Why a TEZ_LOS vector may not be sent, None if it may: finite, unit length; None (no target) always may."""
    if vec is None:
        return None
    v = np.asarray(vec, dtype=float)
    if v.shape != (3,):
        return f"3 bileşen olmalı, gelen {v.shape}"
    if not np.all(np.isfinite(v)):
        return "sonlu olmayan bileşen"
    norm = float(np.linalg.norm(v))
    if abs(norm - 1.0) >= LOS_NORM_TOLERANCE:
        return f"birim değil (norm {norm:.6f})"
    return None


def los_message(mav: object, time_usec: int, vec: np.ndarray | None) -> object:
    """DEBUG_VECT "TEZ_LOS" of one frame (pymavlink message of `mav`); vec None = NaN = no target. ValueError if
    the vector may not be sent (check_los)."""
    reason = check_los(vec)
    if reason is not None:
        raise ValueError(f"{TEZ_LOS_NAME}: {reason}")
    x, y, z = (math.nan,) * 3 if vec is None else (float(c) for c in vec)
    return mav.debug_vect_encode(TEZ_LOS_NAME.encode(), int(time_usec), x, y, z)


def check_follow_target(point: konumlama.GeoPoint) -> str | None:
    """Why a FOLLOW_TARGET position may not be sent, None if it may: finite, a latitude / longitude on the Earth."""
    if not all(math.isfinite(v) for v in (point.lat, point.lon, point.alt)):
        return "sonlu olmayan alan"
    if abs(point.lat) > 90.0 or abs(point.lon) > 180.0:
        return f"enlem/boylam aralık dışında ({point.lat}, {point.lon})"
    return None


def follow_target_message(mav: object, timestamp_ms: int, point: konumlama.GeoPoint) -> object:
    """FOLLOW_TARGET of one frame: timestamp [ms] = its capture time (PX4's clock; PX4 does not use it), position only.
    The velocity is NaN, not MAVLink's "0 for unknown": PX4 v1.17.0 ignores est_capabilities and would fuse a 0;
    acceleration, attitude and rates are MAVLink's unknown (0) and unused by PX4. ValueError if it may not be sent."""
    reason = check_follow_target(point)
    if reason is not None:
        raise ValueError(f"FOLLOW_TARGET: {reason}")
    nan = math.nan
    return mav.follow_target_encode(
        int(timestamp_ms),
        FOLLOW_POSITION_ONLY,
        round(point.lat * 1e7),
        round(point.lon * 1e7),
        float(point.alt),
        [nan, nan, nan],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        [nan, nan, nan],
        0,
    )


def pose_hook(history: konumlama.PoseHistory, system: int) -> Callable[[object, object], None]:
    """pymavlink message hook (mavfile.message_hooks, called for every parsed message in the reading thread) that
    keeps the autopilot's EKF pose, EKF origin and home position in `history`. Never raises: the reader must go on."""

    def hook(_conn: object, msg: object) -> None:
        try:
            if msg.get_srcSystem() != system or msg.get_srcComponent() != AUTOPILOT_COMPONENT:
                return
            kind = msg.get_type()
            if kind == "ATTITUDE_QUATERNION":
                history.add_attitude(msg.time_boot_ms / 1000.0, np.array([msg.q1, msg.q2, msg.q3, msg.q4]))
            elif kind == "LOCAL_POSITION_NED":
                history.add_position(msg.time_boot_ms / 1000.0, np.array([msg.x, msg.y, msg.z]))
            elif kind == "GPS_GLOBAL_ORIGIN":
                history.set_origin(konumlama.GeoPoint(msg.latitude * 1e-7, msg.longitude * 1e-7, msg.altitude * 1e-3))
            elif kind == "HOME_POSITION":
                history.set_home(np.array([msg.x, msg.y, msg.z]), msg.altitude * 1e-3)
        except (AttributeError, ValueError, ZeroDivisionError):  # a malformed message: skipped, the reader goes on
            history.errors += 1

    return hook


def serialize_sends(mav: object, lock: threading.Lock) -> None:
    """Make every send of a pymavlink MAVLink object hold `lock`: its send() is not thread safe (sequence number,
    buffer), and the heartbeat, command and TEZ_LOS threads share the connection."""
    unlocked = mav.send

    def send(mavmsg: object, force_mavlink1: bool = False) -> None:
        with lock:
            unlocked(mavmsg, force_mavlink1=force_mavlink1)

    mav.send = send  # every *_send() of pymavlink calls self.send


def mode_entry(msg: object) -> tuple[str, int] | None:
    """(name, custom_mode) of a mode in an AVAILABLE_MODES message; None if it cannot be selected (an unregistered
    external slot, Termination)."""
    if msg.properties & mavlink.MAV_MODE_PROPERTY_NOT_USER_SELECTABLE:
        return None
    name = msg.mode_name.strip() or STANDARD_MODE_NAMES.get(msg.standard_mode, "")
    return (name, msg.custom_mode) if name else None


def check_mode_name(name: str, px4_start: Iterable[str] = ()) -> None:
    """Refuse a mode name PX4 will not offer, before the simulation starts (ValueError listing the choices).

    Without start commands only PX4's own modes exist. An external mode (m15) registers after PX4 starts
    (takip.px4_baslat / --px4-baslat): its name is then looked up in the run, in what PX4 reports."""
    if name in STOCK_MODE_NAMES or any(c.strip() for c in px4_start):
        return
    raise ValueError(
        f"takip.mod_adi: '{name}' PX4'ün seçilebilir modları arasında yok (--mod-adi). PX4 v1.17.0'ın modları: "
        f"{', '.join(sorted(STOCK_MODE_NAMES))}. Harici bir mod (ör. m15'in modu) PX4 açıldıktan sonra kaydolur: "
        "modülü takip.px4_baslat / --px4-baslat ile başlatın; adı o zaman PX4'ün listesinde aranır"
    )


class FrameStream:
    """Rules of a per-frame message stream to PX4: one message per frame, frames only forwards in time, at most one per
    `min_spacing_s` of capture time, none without a link and none that may not be sent. Every attempt is counted."""

    def __init__(self, min_spacing_s: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.min_spacing_s = min_spacing_s
        self._clock = clock
        self._lock = threading.Lock()
        self._link: object | None = None  # Vehicle
        self._last_t: float | None = None  # [s, sim] capture time of the last message sent
        self.counts: Counter[str] = Counter()

    def attach(self, link: object) -> None:
        with self._lock:
            self._link = link

    def detach(self) -> None:
        with self._lock:
            self._link = None

    def send(self, t: float, payload: object) -> tuple[str, float]:
        """The message of the frame captured at `t` [s, sim]. -> (result, monotonic time of the send or of the
        decision): gonderildi, gecersiz, baglanti_yok, ayni_kare, eski_kare, hiz_siniri, hata."""
        with self._lock:
            result, at = self._send(t, payload)
            self.counts[result] += 1
            return result, at

    def check(self, payload: object) -> str | None:
        """Why `payload` may not be sent, None if it may."""
        raise NotImplementedError

    def write(self, link: object, t: float, payload: object) -> None:
        raise NotImplementedError

    def _send(self, t: float, payload: object) -> tuple[str, float]:
        if self.check(payload) is not None:
            return "gecersiz", self._clock()
        if self._link is None:
            return "baglanti_yok", self._clock()
        if self._last_t is not None:
            if t == self._last_t:
                return "ayni_kare", self._clock()
            if t < self._last_t:
                return "eski_kare", self._clock()
            if t - self._last_t < self.min_spacing_s - 1e-9:
                return "hiz_siniri", self._clock()
        # the send time is read just before the write: after it, the thread waits for the GIL (and on a loaded CPU for
        # the scheduler) and a later reading came out up to ~70 ms late against PX4's own arrival stamp (task group 5)
        at = self._clock()
        try:
            self.write(self._link, t, payload)
        except OSError:  # the UDP socket went away (PX4 shutting down): counted, the stream goes on
            return "hata", at
        self._last_t = t
        return "gonderildi", at


class LosSender(FrameStream):
    """The TEZ_LOS stream: payload = unit LOS in body FRD or None (no target); at most one per camera frame."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        super().__init__(LOS_MIN_SPACING_S, clock)

    def check(self, payload: object) -> str | None:
        return check_los(payload)

    def write(self, link: object, t: float, payload: object) -> None:
        link.send_los(round(t * 1e6), payload)


class FollowTargetSender(FrameStream):
    """The FOLLOW_TARGET stream of follow_me: payload = konumlama.GeoPoint; at most every third camera frame."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        super().__init__(FOLLOW_MIN_SPACING_S, clock)

    def check(self, payload: object) -> str | None:
        if not isinstance(payload, konumlama.GeoPoint):
            return f"konum yok ({type(payload).__name__})"
        return check_follow_target(payload)

    def write(self, link: object, t: float, payload: object) -> None:
        link.send_follow_target(round(t * 1000.0), payload)


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
        # one lock for every message of the connection: GCS heartbeat thread, commands, TEZ_LOS (tracking thread)
        serialize_sends(self.m.mav, threading.Lock())
        # PX4 streams up to 4 MB/s on this link; while the tools are busy (camera frames) the default 208 KB socket
        # buffer overflowed and a COMMAND_ACK was lost (F1 run, 2026-10-11). Linux caps it at net.core.rmem_max.
        self.m.port.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        if self.m.wait_heartbeat(timeout=timeout) is None:
            raise RuntimeError("PX4'ten heartbeat gelmedi (calistir.sh çalışıyor mu?)")
        # the EKF pose of every frame's capture time (follow_me), from now on, in whatever thread reads the link
        self.poses = konumlama.PoseHistory()
        self.m.message_hooks.append(pose_hook(self.poses, self.m.target_system))
        self.request_message("GPS_GLOBAL_ORIGIN")
        # The x500 airframe refuses to arm without a ground station (NAV_DLL_ACT 2): act as one.
        self._closed = threading.Event()
        threading.Thread(target=self._send_gcs_heartbeat, daemon=True).start()
        for name, rate_hz in (*POSE_STREAMS.items(), ("EXTENDED_SYS_STATE", 2)):
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

    def send_los(self, time_usec: int, vec: np.ndarray | None) -> None:
        """One TEZ_LOS (DEBUG_VECT) to PX4; vec None = no target. ValueError if the vector may not be sent."""
        self.m.mav.send(los_message(self.m.mav, time_usec, vec))

    def request_message(self, name: str) -> None:
        """MAV_CMD_REQUEST_MESSAGE for one message; the ack is not awaited (the message may come before it, and the
        hooks see it either way)."""
        msg_id = getattr(mavutil.mavlink, f"MAVLINK_MSG_ID_{name}")
        self.m.mav.command_long_send(
            self.m.target_system,
            self.m.target_component,
            mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,
            0,
            msg_id,
            *[0] * 6,
        )

    def wait_references(self, timeout: float = 10.0) -> bool:
        """Until the pose history holds the EKF origin and the home position (the box positions need both), asking for
        them every REFERENCE_ASK_EVERY_S; reading the link meanwhile lets the hooks see them. Home is valid once
        armed."""
        t_end = time.monotonic() + timeout
        asked = -math.inf
        while time.monotonic() < t_end:
            if self.poses.origin is not None and self.poses.home_ned is not None:
                return True
            if time.monotonic() - asked >= REFERENCE_ASK_EVERY_S:
                for name in REFERENCE_MESSAGES:
                    self.request_message(name)
                asked = time.monotonic()
            self.m.recv_match(blocking=True, timeout=0.2)
        return self.poses.origin is not None and self.poses.home_ned is not None

    def send_follow_target(self, timestamp_ms: int, point: konumlama.GeoPoint) -> None:
        """One FOLLOW_TARGET to PX4. ValueError if the position may not be sent."""
        self.m.mav.send(follow_target_message(self.m.mav, timestamp_ms, point))

    def modes(self, timeout: float = 15.0) -> dict[str, int]:
        """{mode name: custom_mode} of every mode PX4 offers for selection (AVAILABLE_MODES, what QGC shows)."""
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
        indices: set[int] = set()  # the unselectable ones are skipped, but every index counts for completeness
        total = None
        t_end = time.monotonic() + timeout
        while time.monotonic() < t_end and len(indices) != total:
            msg = self.m.recv_match(type="AVAILABLE_MODES", blocking=True, timeout=1)
            if msg is not None:
                entry = mode_entry(msg)
                if entry is not None:
                    found[entry[0]] = entry[1]
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
