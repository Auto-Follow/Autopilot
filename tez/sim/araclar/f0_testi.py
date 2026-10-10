#!/usr/bin/env python3
"""F0 acceptance test of the thesis simulation (run while tez/sim/calistir.sh is running).

Checks, each reported as OK / HATA:
  1. The Camera Module 3 stream: 2304x1296, about 30 fps, focal length of a 66 deg lens.
  2. "Tez Auto Follow" is in PX4's mode list (MAVLink AVAILABLE_MODES).
  3. Takeoff to 10 m, switch to the thesis mode, it holds position for 15 s.
  4. Landing and disarm.

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/f0_testi.py
"""

import math
import os
import sys
import threading
import time
from collections.abc import Callable

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")  # protobuf 7.x in ~/.local

from gz.msgs10.camera_info_pb2 import CameraInfo  # noqa: E402
from gz.msgs10.image_pb2 import Image  # noqa: E402
from gz.transport13 import Node  # noqa: E402
from pymavlink import mavutil  # noqa: E402

MODE_NAME = "Tez Auto Follow"
CAMERA_TOPIC = "/x500_tez/kamera"
CAMERA_SIZE = (2304, 1296)  # [px]
CAMERA_HFOV = math.radians(66.0)  # Camera Module 3 Standard
CAMERA_RATE = 30.0  # [Hz]
TAKEOFF_ALT = 10.0  # [m]
HOLD_TIME = 15.0  # [s]
HOLD_TOLERANCE = 0.5  # [m] horizontal and vertical drift allowed while the skeleton mode holds

results: list[tuple[str, bool, str]] = []


def report(name: str, ok: bool, detail: str) -> bool:
    results.append((name, ok, detail))
    print(f"{'OK  ' if ok else 'HATA'} {name}: {detail}", flush=True)
    return ok


def check_camera() -> None:
    """Count camera frames for 3 s (sim time runs at real time) and read the calibration message."""
    node = Node()
    lock = threading.Lock()
    frames: list[tuple[int, int, float]] = []
    info: list[CameraInfo] = []

    def on_image(msg: Image) -> None:
        with lock:
            frames.append((msg.width, msg.height, time.monotonic()))

    def on_info(msg: CameraInfo) -> None:
        with lock:
            if not info:
                info.append(msg)

    node.subscribe(Image, f"{CAMERA_TOPIC}/image", on_image)
    node.subscribe(CameraInfo, f"{CAMERA_TOPIC}/camera_info", on_info)
    time.sleep(4.0)
    with lock:
        samples = list(frames)
        calib = info[0] if info else None

    if len(samples) < 2:
        report("kamera", False, f"{CAMERA_TOPIC}/image yayın yapmıyor")
        return
    size = (samples[-1][0], samples[-1][1])
    rate = (len(samples) - 1) / (samples[-1][2] - samples[0][2])
    report(
        "kamera çözünürlüğü", size == CAMERA_SIZE, f"{size[0]}x{size[1]} (beklenen {CAMERA_SIZE[0]}x{CAMERA_SIZE[1]})"
    )
    report("kamera hızı", rate > 0.8 * CAMERA_RATE, f"{rate:.1f} fps (beklenen ~{CAMERA_RATE:.0f})")
    if calib is None:
        report("kamera kalibrasyonu", False, f"{CAMERA_TOPIC}/camera_info yayın yapmıyor")
        return
    fx_expected = CAMERA_SIZE[0] / 2 / math.tan(CAMERA_HFOV / 2)
    fx = calib.intrinsics.k[0]
    report("kamera odak uzaklığı", abs(fx - fx_expected) < 2.0, f"fx {fx:.1f} px (66° için {fx_expected:.1f})")


class Vehicle:
    def __init__(self) -> None:
        self.m = mavutil.mavlink_connection("udpin:127.0.0.1:14540", dialect="development")
        if self.m.wait_heartbeat(timeout=60) is None:
            sys.exit("HATA: PX4'ten heartbeat gelmedi (calistir.sh çalışıyor mu?)")
        # The x500 airframe refuses to arm without a ground station (NAV_DLL_ACT 2): act as one.
        threading.Thread(target=self._send_gcs_heartbeat, daemon=True).start()
        for name, rate_hz in (("LOCAL_POSITION_NED", 10), ("EXTENDED_SYS_STATE", 2)):
            msg_id = getattr(mavutil.mavlink, f"MAVLINK_MSG_ID_{name}")
            self.command(mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, msg_id, 1e6 / rate_hz, quiet=True)

    def _send_gcs_heartbeat(self) -> None:
        while True:
            self.m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
            time.sleep(1.0)

    def command(self, cmd: int, *params: float, quiet: bool = False) -> bool:
        p = list(params) + [0.0] * (7 - len(params))
        self.m.mav.command_long_send(self.m.target_system, self.m.target_component, cmd, 0, *p)
        ack = self.m.recv_match(type="COMMAND_ACK", condition=f"COMMAND_ACK.command=={cmd}", blocking=True, timeout=5)
        accepted = ack is not None and ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED
        if not accepted and not quiet:
            print(f"     komut {cmd} reddedildi: {ack.result if ack else 'cevap yok'}", flush=True)
        return accepted

    def wait(self, types: list[str], pred: Callable, timeout: float) -> object | None:
        """Return the first message of the given types that satisfies pred; print PX4 status texts meanwhile."""
        t_end = time.monotonic() + timeout
        while time.monotonic() < t_end:
            msg = self.m.recv_match(type=[*types, "STATUSTEXT"], blocking=True, timeout=1)
            if msg is None:
                continue
            if msg.get_type() == "STATUSTEXT":
                print(f"     PX4: {msg.text}", flush=True)
            elif pred(msg):
                return msg
        return None

    def find_mode(self, name: str) -> int | None:
        """custom_mode of the mode called `name`, from AVAILABLE_MODES (index 0 asks for all modes)."""
        # PX4 sends the modes before the COMMAND_ACK, so do not wait for the ack (command() would drop them).
        self.m.mav.command_long_send(
            self.m.target_system,
            self.m.target_component,
            mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,
            0,
            mavutil.mavlink.MAVLINK_MSG_ID_AVAILABLE_MODES,
            0,
            0,
            0,
            0,
            0,
            0,
        )
        seen: set[str] = set()
        t_end = time.monotonic() + 15
        while time.monotonic() < t_end:
            msg = self.m.recv_match(type="AVAILABLE_MODES", blocking=True, timeout=1)
            if msg is None:
                continue
            seen.add(msg.mode_name)
            if msg.mode_name == name:
                return msg.custom_mode
        print(f"     görülen modlar: {sorted(seen)}", flush=True)
        return None

    def set_custom_mode(self, custom_mode: int) -> bool:
        # PX4 packs main mode into byte 2 and sub mode into byte 3 of custom_mode
        main_mode, sub_mode = (custom_mode >> 16) & 0xFF, (custom_mode >> 24) & 0xFF
        return self.command(
            mavutil.mavlink.MAV_CMD_DO_SET_MODE, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, main_mode, sub_mode
        )

    def set_param(self, name: str, value: float) -> None:
        self.m.mav.param_set_send(
            self.m.target_system, self.m.target_component, name.encode(), value, mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        )
        self.m.recv_match(type="PARAM_VALUE", condition=f"PARAM_VALUE.param_id=='{name}'", blocking=True, timeout=5)


def flight(v: Vehicle, custom_mode: int) -> None:
    nan = math.nan
    if v.wait(["LOCAL_POSITION_NED"], lambda _: True, 60) is None:
        report("konum kestirimi", False, "LOCAL_POSITION_NED gelmedi")
        return
    v.set_param("MIS_TAKEOFF_ALT", TAKEOFF_ALT)
    report(
        "tez modunda arm reddi",
        not v.set_custom_mode(custom_mode)
        or not v.command(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1, quiet=True),
        "yerde tez moduna geçilip arm edilemez",
    )
    time.sleep(1)

    # PX4 rejects arming until the estimator is ready; retry for up to a minute like a pilot would.
    t_end = time.monotonic() + 60
    armed = False
    while time.monotonic() < t_end and not armed:
        armed = v.command(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, -1, 0, 0, nan, nan, nan, nan, quiet=True) and v.command(
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1, quiet=True
        )
        if not armed:
            time.sleep(2)
    if not report("kalkış", armed, "kalkış komutu ve arm kabul edildi" if armed else "60 s içinde arm edilemedi"):
        return
    climbed = v.wait(["LOCAL_POSITION_NED"], lambda p: -p.z > TAKEOFF_ALT - 0.5, 60)
    if not report("kalkış yüksekliği", climbed is not None, f"{TAKEOFF_ALT:.0f} m"):
        return
    time.sleep(3)  # let the takeoff mode settle into its hover

    if not report("tez moduna geçiş", v.set_custom_mode(custom_mode), MODE_NAME):
        return
    hb = v.wait(["HEARTBEAT"], lambda h: h.get_srcComponent() == 1 and h.custom_mode == custom_mode, 5)
    report("aktif mod", hb is not None, "HEARTBEAT tez modunu gösteriyor" if hb else "mod değişmedi")

    start = v.wait(["LOCAL_POSITION_NED"], lambda _: True, 5)
    max_xy = max_z = 0.0
    t_end = time.monotonic() + HOLD_TIME
    while time.monotonic() < t_end:
        p = v.wait(["LOCAL_POSITION_NED"], lambda _: True, 2)
        if p is not None and start is not None:
            max_xy = max(max_xy, math.hypot(p.x - start.x, p.y - start.y))
            max_z = max(max_z, abs(p.z - start.z))
    hb = v.m.recv_match(type="HEARTBEAT", condition="HEARTBEAT.get_srcComponent()==1", blocking=True, timeout=3)
    still = hb is not None and hb.custom_mode == custom_mode
    report("mod korundu", still, f"{HOLD_TIME:.0f} s boyunca tez modunda kaldı" if still else "mod başka moda düştü")
    report(
        "konum tutma",
        max_xy < HOLD_TOLERANCE and max_z < HOLD_TOLERANCE,
        f"en büyük sapma yatay {max_xy:.2f} m, dikey {max_z:.2f} m (sınır {HOLD_TOLERANCE} m)",
    )

    v.command(mavutil.mavlink.MAV_CMD_NAV_LAND, 0, 0, 0, nan, nan, nan, nan)
    landed = v.wait(["EXTENDED_SYS_STATE"], lambda s: s.landed_state == mavutil.mavlink.MAV_LANDED_STATE_ON_GROUND, 90)
    report("iniş", landed is not None, "yere indi")
    disarmed = v.wait(
        ["HEARTBEAT"],
        lambda h: h.get_srcComponent() == 1 and not (h.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED),
        20,
    )
    report("disarm", disarmed is not None, "motorlar durdu")


def main() -> int:
    check_camera()
    v = Vehicle()
    custom_mode = v.find_mode(MODE_NAME)
    if report("mod listesi", custom_mode is not None, f"'{MODE_NAME}' QGC'nin göreceği listede"):
        flight(v, custom_mode)
    failed = [name for name, ok, _ in results if not ok]
    print("\nSONUÇ:", "GEÇTİ" if not failed else f"KALDI ({', '.join(failed)})", flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
