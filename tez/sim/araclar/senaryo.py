#!/usr/bin/env python3
"""Run one scenario end to end and write its report.

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo yuruyen_insan
    ... --ekransiz          no Gazebo window
    ... --dogrula           overhead camera checks that the rendered target is where the ground truth says

Steps: write the scenario world (base world + target), start Gazebo + PX4 (calistir.sh), take off, switch to the
scenario's mode, record ground truth while the target walks, land, shut down, collect the ULog, write the report
to tez/sim/sonuclar/<date>_<scenario>/.
"""

import argparse
import datetime as dt
import math
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")  # protobuf 7.x in ~/.local

import numpy as np  # noqa: E402
from gz.msgs10.image_pb2 import Image  # noqa: E402
from gz.transport13 import Node  # noqa: E402

import hedef  # noqa: E402
import rapor  # noqa: E402
from kayit import Recorder  # noqa: E402
from px4_baglanti import TEZ_MODE_NAME, Vehicle  # noqa: E402

SIM_DIR = hedef.SIM_DIR
REPO = SIM_DIR.parent.parent
BUILD = REPO / "build" / "px4_sitl_tez"
PX4_HOLD_MODE = (4 << 16) | (3 << 24)  # PX4 custom_mode of Auto/Hold (main mode 4, sub mode 3)


def log(text: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {text}", flush=True)


class Simulation:
    """calistir.sh in the background; always shut down, even after an error."""

    def __init__(self, world_file: Path, out: Path, headless: bool) -> None:
        self.log_path = out / "sim.log"
        args = [str(SIM_DIR / "calistir.sh"), "--dunya", str(world_file)] + (["--ekransiz"] if headless else [])
        self.started = time.time()
        self.proc = subprocess.Popen(
            args, stdin=subprocess.DEVNULL, stdout=self.log_path.open("w"), stderr=subprocess.STDOUT
        )

    def wait_ready(self, timeout: float = 150.0) -> bool:
        t_end = time.monotonic() + timeout
        while time.monotonic() < t_end:
            if self.proc.poll() is not None:
                return False
            if "registered as" in self.log_path.read_text(errors="replace"):
                return True
            time.sleep(1)
        return False

    def stop(self) -> None:
        if self.proc.poll() is None:
            subprocess.run(
                [str(BUILD / "bin" / "px4-shutdown")],
                cwd=BUILD / "rootfs",
                capture_output=True,
                timeout=20,
                check=False,
            )
            try:
                self.proc.wait(40)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                self.proc.wait(10)

    def newest_ulog(self) -> Path | None:
        logs = [p for p in (BUILD / "rootfs" / "log").rglob("*.ulg") if p.stat().st_mtime >= self.started]
        return max(logs, key=lambda p: p.stat().st_mtime) if logs else None


class OverheadCheck:
    """Grab overhead frames at chosen sim times and locate the target in them (see hedef.overhead_camera)."""

    def __init__(self, sc: hedef.Scenario, camera_pos: tuple[float, float, float], times: list[float]) -> None:
        self.sc = sc
        self.pos = camera_pos
        self.times = times
        self.frames: dict[float, np.ndarray] = {}
        self._lock = threading.Lock()
        self._node = Node()
        self._node.subscribe(Image, "/dogrulama/image", self._on_image)

    def _on_image(self, msg: Image) -> None:
        t = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        for want in self.times:
            if want not in self.frames and abs(t - want) < 0.06:
                img = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.width, 3).copy()
                with self._lock:
                    self.frames[want] = img

    def results(self, drone_at: dict[float, tuple[float, float, float]], out: Path) -> list[dict]:
        rows = []
        for want in self.times:
            with self._lock:
                img = self.frames.get(want)
            tx, ty, *_ = self.sc.truth(want)
            row = {
                "t": want,
                "hesap_x": tx,
                "hesap_y": ty,
                "goruntu_x": math.nan,
                "goruntu_y": math.nan,
                "fark": math.nan,
            }
            if img is not None:
                est = self._locate(img, drone_at.get(want))
                if est is not None:
                    row.update(goruntu_x=est[0], goruntu_y=est[1], fark=math.hypot(est[0] - tx, est[1] - ty))
                if want == self.times[len(self.times) // 2]:
                    import cv2

                    cv2.imwrite(str(out / "dogrulama_tepe.png"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            rows.append(row)
        return rows

    def _locate(self, img: np.ndarray, drone: tuple[float, float, float] | None) -> tuple[float, float] | None:
        """Target centroid on the ground [m]: pixels unlike the grass, drone excluded. Image up = +x, right = -y."""
        h_px, w_px = img.shape[:2]
        cx, cy, cz = self.pos
        f = (w_px / 2) / math.tan(hedef.OVERHEAD_HFOV / 2)
        ground = np.median(img.reshape(-1, 3), axis=0)
        diff = np.abs(img.astype(int) - ground).sum(axis=2)
        ys, xs = np.nonzero(diff > 60)
        if drone is not None:
            dz = cz - drone[2]
            du = w_px / 2 - (drone[1] - cy) * f / dz
            dv = h_px / 2 - (drone[0] - cx) * f / dz
            keep = np.hypot(xs - du, ys - dv) > 0.8 * f / dz  # drone body ~0.6 m across
            xs, ys = xs[keep], ys[keep]
        if len(xs) < 15:
            return None
        scale = (cz - hedef.ACTOR_HIP_HEIGHT * 0.9) / f  # metres per pixel at the body's mean height
        return float(cx + (h_px / 2 - ys.mean()) * scale), float(cy - (xs.mean() - w_px / 2) * scale)


def fly(sc: hedef.Scenario, rec: Recorder, events: list[str]) -> bool:
    v = Vehicle()
    tez_mode = v.find_mode(TEZ_MODE_NAME)
    if tez_mode is None:
        events.append("Tez modu PX4'ün mod listesinde yok")
        return False
    log(f"Kalkış: {sc.altitude:.0f} m")
    if not v.takeoff(sc.altitude):
        events.append("Kalkış başarısız")
        return False
    time.sleep(3)
    mode = tez_mode if sc.drone_mode == "tez" else PX4_HOLD_MODE
    if not (v.set_custom_mode(mode) and v.in_mode(mode)):
        events.append(f"'{sc.drone_mode}' moduna geçilemedi")
        return False
    events.append(f"Dron {rec.sim_time:.1f} s'de hazır ({sc.drone_mode} modunda, {sc.altitude:.0f} m)")
    if rec.sim_time > sc.start_time - 1:
        events.append(
            f"Dron hedef yürümeye başlamadan hazır olamadı ({rec.sim_time:.0f} s > {sc.start_time:.0f} s): "
            "zamanlama.baslama_s değerini büyütün"
        )
        return False
    rec.start()
    log(f"Kayıt başladı; hedef {sc.start_time:.0f} s'de yürümeye başlayacak, senaryo {sc.end_time:.0f} s'de bitecek")
    while rec.sim_time < sc.end_time:
        hb = v.m.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
        if hb is not None and hb.get_srcComponent() == 1 and hb.custom_mode != mode:
            events.append(f"{rec.sim_time:.1f} s: dron senaryo modundan çıktı")
            mode = hb.custom_mode
    rec.stop()
    log("Senaryo bitti, iniş")
    if not v.land():
        events.append("İniş/disarm tamamlanamadı")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--senaryo", required=True, help="tez/sim/senaryolar/<ad>.yaml adı veya bir .yaml yolu")
    ap.add_argument("--ekransiz", action="store_true", help="Gazebo penceresi açılmaz")
    ap.add_argument("--dogrula", action="store_true", help="tepe kamerasıyla hedefin konumunu doğrula (gölgesiz)")
    ap.add_argument("--cikti", type=Path, help="çıktı klasörü (varsayılan tez/sim/sonuclar/<tarih>_<ad>)")
    args = ap.parse_args()

    try:
        sc = hedef.load(args.senaryo)
    except (ValueError, FileNotFoundError) as e:
        print(f"Senaryo hatası: {e}", file=sys.stderr)
        return 2
    if not (SIM_DIR / "models" / "insan" / "meshes" / ".tamam").is_file():
        print("İnsan modeli kurulu değil. Önce: tez/sim/kur.sh", file=sys.stderr)
        return 2
    if not (BUILD / "bin" / "px4").is_file():
        print("PX4 derlenmemiş. Önce: tez/sim/derle.sh", file=sys.stderr)
        return 2

    out = args.cikti or SIM_DIR / "sonuclar" / f"{dt.datetime.now():%Y%m%d_%H%M%S}_{sc.name}"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(sc.source, out / "senaryo.yaml")
    world_file, camera_pos = hedef.write_world(sc, out, args.dogrula)
    log(f"Senaryo '{sc.name}': hedef yolu {sc.path_length():.1f} m, {sc.walk_end - sc.start_time:.1f} s; çıktı {out}")

    events: list[str] = []
    rec = Recorder(sc, sc.world)
    check = None
    if args.dogrula:
        step = max(2.0, (sc.walk_end - sc.start_time) / 8)
        times = [round(sc.start_time - 5.0, 1)] + [
            round(t, 1) for t in np.arange(sc.start_time + 1.0, sc.walk_end + 0.01, step)
        ]
        times.append(round(sc.end_time - 1.0, 1))
        check = OverheadCheck(sc, camera_pos, sorted(set(times)))

    sim = Simulation(world_file, out, args.ekransiz)
    completed = False
    try:
        if not sim.wait_ready():
            events.append("Simülasyon açılmadı (sim.log'a bakın)")
        else:
            log("PX4 ve Gazebo hazır")
            completed = fly(sc, rec, events)
    except KeyboardInterrupt:
        events.append("Kullanıcı durdurdu (Ctrl+C)")
    except Exception as e:  # noqa: BLE001 - any failure must still shut the simulation down and be reported
        events.append(f"Beklenmeyen hata: {type(e).__name__}: {e}")
    finally:
        log("Simülasyon kapatılıyor")
        sim.stop()

    ulog = sim.newest_ulog()
    if ulog is not None:
        shutil.copy(ulog, out / "ucus.ulg")
    rows = rec.snapshot()
    checks = []
    if check is not None and rows:
        drone_at = {}
        for want in check.times:
            nearest = min(rows, key=lambda r: abs(r["t"] - want))
            drone_at[want] = (nearest["dron_x"], nearest["dron_y"], nearest["dron_z"])
        checks = check.results(drone_at, out)

    summary = rapor.write(
        out,
        sc,
        rows,
        events,
        completed,
        checks,
        rec.camera,
        rec.camera_offset,
        (out / "ucus.ulg") if ulog else None,
    )
    log(f"Rapor: {out / 'rapor.html'}")
    log(f"SONUÇ: {summary['sonuc']}")
    return 0 if summary["sonuc"] == "GEÇTİ" else 1


if __name__ == "__main__":
    sys.exit(main())
