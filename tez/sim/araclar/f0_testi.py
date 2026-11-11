#!/usr/bin/env python3
"""F0 acceptance test of the thesis simulation (tez/sim/araclar/f0_kabul.sh runs it).

Starts the simulation without a window (or uses one that is already running, --acik-sim) and checks, each reported
as OK / HATA:
  1. The Camera Module 3 stream: 2304x1296, about 30 fps, focal length of a 66 deg lens.
  2. PX4 runs the stock airframe (SYS_AUTOSTART 4001) and every start parameter of tez/sim/parametreler
     (gercek_dron.params, sim.params) has the same value in PX4 (PARAM_REQUEST_READ).
  3. "Hold" and "Follow Target" are in PX4's mode list (MAVLink AVAILABLE_MODES, what QGC shows).
  4. Takeoff to 10 m, switch to Hold, it holds position for 15 s.
  5. Landing and disarm; PX4 and Gazebo shut down cleanly.

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/f0_testi.py [--acik-sim]
"""

import argparse
import math
import os
import sys
import threading
import time

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")  # protobuf 7.x in ~/.local
os.environ.setdefault("GZ_IP", "127.0.0.1")  # same as calistir.sh

from gz.msgs10.camera_info_pb2 import CameraInfo  # noqa: E402
from gz.msgs10.image_pb2 import Image  # noqa: E402
from gz.transport13 import Node  # noqa: E402

import parametreler  # noqa: E402
from kayit import CAMERA_TOPIC  # noqa: E402
from px4_baglanti import FOLLOW_TARGET_MODE_NAME, HOLD_MODE_NAME, Vehicle  # noqa: E402
from simulasyon import BUILD, Simulation  # noqa: E402

OUT = BUILD / "tez_kabul"
AIRFRAME = 4001  # stock 4001_gz_x500, chosen by calistir.sh (PX4_SYS_AUTOSTART)
REQUIRED_MODES = (HOLD_MODE_NAME, FOLLOW_TARGET_MODE_NAME)
CAMERA_SIZE = (2304, 1296)  # [px]
CAMERA_HFOV = math.radians(66.0)  # Camera Module 3 Standard
CAMERA_RATE = 30.0  # [Hz]
TAKEOFF_ALT = 10.0  # [m]
HOLD_TIME = 15.0  # [s]
HOLD_TOLERANCE = 0.5  # [m] horizontal and vertical drift allowed while Hold keeps the position

results: list[tuple[str, bool, str]] = []


def report(name: str, ok: bool, detail: str) -> bool:
    results.append((name, ok, detail))
    print(f"{'OK  ' if ok else 'HATA'} {name}: {detail}", flush=True)
    return ok


def check_camera() -> None:
    """Count camera frames for 4 s and read the calibration message."""
    node = Node()
    lock = threading.Lock()
    frames: list[tuple[int, int, float, float]] = []  # width, height, sim time, wall time
    info: list[CameraInfo] = []

    def on_image(msg: Image) -> None:
        with lock:
            frames.append(
                (msg.width, msg.height, msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9, time.monotonic())
            )

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
    sim_span, wall_span = samples[-1][2] - samples[0][2], samples[-1][3] - samples[0][3]
    rate = (len(samples) - 1) / sim_span
    report(
        "kamera çözünürlüğü", size == CAMERA_SIZE, f"{size[0]}x{size[1]} (beklenen {CAMERA_SIZE[0]}x{CAMERA_SIZE[1]})"
    )
    report(
        "kamera hızı",
        abs(rate - CAMERA_RATE) < 0.1 * CAMERA_RATE,
        f"{rate:.1f} kare / sim saniyesi (beklenen {CAMERA_RATE:.0f}); gerçek zaman oranı {sim_span / wall_span:.2f}",
    )
    if calib is None:
        report("kamera kalibrasyonu", False, f"{CAMERA_TOPIC}/camera_info yayın yapmıyor")
        return
    fx_expected = CAMERA_SIZE[0] / 2 / math.tan(CAMERA_HFOV / 2)
    fx = calib.intrinsics.k[0]
    report("kamera odak uzaklığı", abs(fx - fx_expected) < 2.0, f"fx {fx:.1f} px (66° için {fx_expected:.1f})")


def check_parameters(v: Vehicle) -> None:
    """The stock airframe runs and PX4 holds every value of the .params files (after the PX4_PARAM_* start)."""
    autostart = v.get_param("SYS_AUTOSTART")
    report("airframe", autostart == AIRFRAME, f"SYS_AUTOSTART {autostart} (beklenen {AIRFRAME}, stok 4001_gz_x500)")

    expected = parametreler.load()  # the same files calistir.sh loaded; --param is not used by this test
    wrong = []
    for name, p in expected.items():
        actual = v.get_param(name)
        if not parametreler.matches(p.value, actual):
            wrong.append(f"{name} PX4'te {actual} ({p.source}: {parametreler.format_value(p.value)})")
    report(
        "başlangıç parametreleri",
        not wrong,
        f"{len(expected) - len(wrong)}/{len(expected)} parametre PX4'te dosyadaki değerde"
        + (f"; farklı: {'; '.join(wrong)}" if wrong else ""),
    )


def flight(v: Vehicle, hold_mode: int) -> None:
    climbed = v.takeoff(TAKEOFF_ALT)
    if not report("kalkış", climbed, f"{TAKEOFF_ALT:.0f} m'ye kalktı" if climbed else "kalkılamadı"):
        return
    time.sleep(3)  # let the takeoff mode settle into its hover

    if not report("Hold'a geçiş", v.switch_mode(hold_mode), f"HEARTBEAT '{HOLD_MODE_NAME}' gösteriyor"):
        return

    start = v.wait(["LOCAL_POSITION_NED"], lambda _: True, 5)
    max_xy = max_z = 0.0
    t_end = time.monotonic() + HOLD_TIME
    while time.monotonic() < t_end:
        p = v.wait(["LOCAL_POSITION_NED"], lambda _: True, 2)
        if p is not None and start is not None:
            max_xy = max(max_xy, math.hypot(p.x - start.x, p.y - start.y))
            max_z = max(max_z, abs(p.z - start.z))
    still = v.current_mode() == hold_mode
    report("mod korundu", still, f"{HOLD_TIME:.0f} s boyunca Hold'da kaldı" if still else "mod başka moda düştü")
    report(
        "konum tutma",
        max_xy < HOLD_TOLERANCE and max_z < HOLD_TOLERANCE,
        f"en büyük sapma yatay {max_xy:.2f} m, dikey {max_z:.2f} m (sınır {HOLD_TOLERANCE} m)",
    )

    report("iniş ve disarm", v.land(), "yere indi, motorlar durdu")


def checks() -> None:
    check_camera()
    v = Vehicle()
    try:
        check_parameters(v)
        modes = v.modes()
        missing = [name for name in REQUIRED_MODES if name not in modes]
        listed = " ve ".join(f"'{name}'" for name in REQUIRED_MODES)
        detail = f"{listed} QGC'nin göreceği listede"
        if missing:
            detail = f"eksik: {', '.join(missing)}; PX4'ün listesi: {', '.join(sorted(modes))}"
        if report("mod listesi", not missing, detail):
            flight(v, modes[HOLD_MODE_NAME])
    finally:
        v.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--acik-sim", action="store_true", help="çalışan bir simülasyonu kullan (calistir.sh)")
    args = ap.parse_args()

    if args.acik_sim:
        checks()
    else:
        sim = Simulation(OUT)
        with sim:
            if report("simülasyon açıldı", sim.wait_ready(), f"PX4 + Gazebo, rcS bitti (log: {sim.log_path})"):
                checks()
        problems = sim.problems()
        for problem in problems:
            report("temiz kapanış", False, problem)
        if not problems:
            report("temiz kapanış", True, "PX4 ve Gazebo kapandı")

    failed = [name for name, ok, _ in results if not ok]
    print("\nSONUÇ:", "GEÇTİ" if not failed else f"KALDI ({', '.join(failed)})", flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
