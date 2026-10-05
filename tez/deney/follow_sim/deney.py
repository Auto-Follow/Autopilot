#!/usr/bin/env python3
"""Headless, repeatable Follow Me experiments.

Starts PX4 SITL + Gazebo (no GUI, no panel) with the camera tilted by --egim, takes off, switches to Follow Me and
runs every scenario of the chosen experiment: the target stands still while the drone settles with the scenario's
parameters, then walks the PARKUR path (follow_core.py) while every 50 ms is logged to <cikti>/<scenario>.csv.

  tez/deney/follow_sim/deney.py --deney kamera --egim 40
  tez/deney/follow_sim/deney.py --deney geolocation --egim 40
  tez/deney/follow_sim/deney.py --deney gecikme --egim 40

Refuses to start while another PX4 / Gazebo is running (e.g. the simulation in your own terminal).
Results are analysed with analiz.py.
"""
import argparse
import csv
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--deney", required=True, choices=sorted(EXPERIMENTS))
    p.add_argument("--egim", type=float, default=40.0, help="camera tilt, degrees down")
    p.add_argument("--cikti", type=Path, help="output directory (default: sonuclar/<deney>_egim<N>)")
    p.add_argument("--settle", type=float, default=20.0, help="seconds the drone settles before each run")
    p.add_argument("--only", help="comma separated scenario names to run")
    return p.parse_args()


# Scenario fields: ht, dst (FLW_TGT_HT/DST), kaynak ("gercek" true GPS / "kamera" geolocation), hiz (send the
# target velocity), ft_delay (s), ft_loss (0-1), ft_burst (mean burst length, messages), kamera_hiz (velocity sent
# with camera fixes: "yok" / "kalman" / "gercek"), hiz_carpan (parkour speed factor), bant (None or (top, bottom)
# image-row fractions: FLW_TGT_DST is moved in flight to keep the target's foot point in that band)
BAND_TILTED = (0.25, 0.75)
BAND_LEVEL = (0.6, 0.9)  # a level camera sees the target steepest near the bottom of the image


def _sc(name, ht, dst, **kw):
    base = {"name": name, "ht": ht, "dst": dst, "kaynak": "gercek", "hiz": False, "ft_delay": 0.0, "ft_loss": 0.0,
            "ft_burst": 1.0, "kamera_hiz": "yok", "hiz_carpan": 1.0, "bant": None}
    base.update(kw)
    return base


EXPERIMENTS = {
    # Open loop (true target position, no velocity, like a Vision system that always sees the target): which
    # geometry keeps the target in view? Visibility for any camera tilt is computed afterwards from the logged poses.
    "kamera": [_sc(f"ht{ht:g}_dst{dst:g}", ht, dst) for ht, dst in
               ((3, 8), (5, 8), (8, 8), (12, 8), (8, 5), (8, 12), (5, 5), (12, 12))],
    # Geolocation accuracy (open loop: drone follows the true position, the camera fix is only measured), then the
    # full chain: FOLLOW_TARGET from the camera fix only.
    "geolocation": [_sc("acik_ht5_dst8", 5, 8), _sc("acik_ht8_dst8", 8, 8), _sc("acik_ht12_dst8", 12, 8),
                    _sc("kapali_ht8_dst8", 8, 8, kaynak="kamera"), _sc("kapali_ht5_dst8", 5, 8, kaynak="kamera")],
    # Latency / loss on the FOLLOW_TARGET path, full camera chain (Vision on the Pi, or ground processing via Wi-Fi)
    "gecikme": [_sc("gecikme0_kayip0", 8, 8, kaynak="kamera"),
                _sc("gecikme200_kayip0", 8, 8, kaynak="kamera", ft_delay=0.2),
                _sc("gecikme500_kayip0", 8, 8, kaynak="kamera", ft_delay=0.5),
                _sc("gecikme1000_kayip0", 8, 8, kaynak="kamera", ft_delay=1.0),
                _sc("gecikme0_kayip30", 8, 8, kaynak="kamera", ft_loss=0.3),
                _sc("gecikme0_kayip60", 8, 8, kaynak="kamera", ft_loss=0.6),
                _sc("gecikme0_kayip30_patlama", 8, 8, kaynak="kamera", ft_loss=0.3, ft_burst=20.0),
                _sc("gecikme500_kayip30", 8, 8, kaynak="kamera", ft_delay=0.5, ft_loss=0.3)],
    # Fast target (parkour speeds x2: walk 3 m/s, run 6 m/s), FOLLOW_TARGET from the camera: no velocity vs. a
    # Kalman filter (position + velocity) vs. the true velocity (upper bound), plus Kalman + distance band.
    # Run with --egim 45.
    "kalman": [_sc("hizli_hizsiz", 8, 8, kaynak="kamera", hiz_carpan=2.0),
               _sc("hizli_kalman", 8, 8, kaynak="kamera", kamera_hiz="kalman", hiz_carpan=2.0),
               _sc("hizli_gercek_hiz", 8, 8, kaynak="kamera", kamera_hiz="gercek", hiz_carpan=2.0),
               _sc("hizli_kalman_bant", 8, 8, kaynak="kamera", kamera_hiz="kalman", hiz_carpan=2.0,
                   bant=BAND_TILTED),
               _sc("normal_kalman", 8, 8, kaynak="kamera", kamera_hiz="kalman")],
    # Level camera kept far enough to see the target (8 m high, 30 m back = 15 deg view), normal speed.
    # Run with --egim 0.
    "duz": [_sc("duz_dst30_hizsiz", 8, 30, kaynak="kamera"),
            _sc("duz_dst30_kalman", 8, 30, kaynak="kamera", kamera_hiz="kalman"),
            _sc("duz_bant_kalman", 8, 30, kaynak="kamera", kamera_hiz="kalman", bant=BAND_LEVEL)],
}


def sim_already_running():
    out = subprocess.run(["pgrep", "-af", r"bin/px4|gz sim"], capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if "pgrep" not in line]


def wait_for(cond, timeout, what):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if cond():
            return
        time.sleep(0.2)
    raise TimeoutError(f"zaman aşımı: {what}")


class Recorder:
    def __init__(self):
        self.rows = None
        self.scenario = None

    def __call__(self, row):
        if self.rows is not None:
            row["scenario"] = self.scenario
            self.rows.append(row)

    def start(self, name):
        self.scenario, self.rows = name, []

    def stop(self, path):
        rows, self.rows = self.rows, None
        keys = sorted({k for r in rows for k in r})
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)
        return len(rows)


def main():
    args = parse_args()
    running = sim_already_running()
    if running:
        print("Çalışan bir simülasyon var, deney başlatılmadı:\n  " + "\n  ".join(running))
        return 1
    scenarios = EXPERIMENTS[args.deney]
    if args.only:
        wanted = set(args.only.split(","))
        scenarios = [s for s in scenarios if s["name"] in wanted]
    out = args.cikti or HERE / "sonuclar" / f"{args.deney}_egim{args.egim:g}"
    out.mkdir(parents=True, exist_ok=True)

    # follow_core reads the world and the camera tilt at import time
    os.environ["PX4_GZ_WORLD"] = "renkli_duz_egik"  # baslat.sh always generates it (also for 0 deg)
    os.environ["FOLLOW_CAMERA_PITCH_DEG"] = f"{args.egim:g}"
    env = dict(os.environ, HEADLESS="1", FOLLOW_PANEL="0")
    log = open(out / "px4.log", "w")
    cmd = [str(HERE / "baslat.sh"), "--egim", f"{args.egim:g}"]
    # stdin stays an open pipe: on EOF the PX4 shell would spin and flood the log
    px4 = subprocess.Popen(cmd, env=env, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT,
                           start_new_session=True)
    print(f"PX4 + Gazebo başlatıldı (pid {px4.pid}), kamera {args.egim:g}° aşağı. Çıktı: {out}", flush=True)

    sys.path.insert(0, str(HERE))
    import follow_core as fc

    sim = None
    try:
        time.sleep(8)
        sim = fc.FollowSim()
        sim.show_scene = False
        rec = Recorder()
        sim.recorder = rec
        sim.start()
        link = sim.link
        wait_for(lambda: link.state.connected, 120, "PX4 bağlantısı")
        wait_for(lambda: link.ekf_origin is not None and link.home_ned is not None, 120, "EKF orijini / home")
        wait_for(lambda: sim.geometry is not None, 30, "drone pozu (Gazebo)")
        print(f"Bağlandı. EKF orijini {link.ekf_origin}, home {link.home_ned}, "
              f"drone z = {sim.gz.drone_pose()[0].z():.3f} m (yerde), Gazebo zamanı {sim.gz.sim_time():.3f} s, "
              f"PX4 zamanı {link.boot_time:.3f} s", flush=True)
        time.sleep(5)  # let the estimator settle before arming
        for name, value in fc.FOLLOW_DEFAULTS.items():
            link.set_param(name, value)
            time.sleep(0.05)
        for attempt in range(5):
            link.takeoff()
            try:
                wait_for(lambda: link.state.rel_alt > 2.0, 30, "kalkış")
                break
            except TimeoutError:
                print(f"Kalkış denemesi {attempt + 1} olmadı, tekrar: {link.state.messages[-3:]}", flush=True)
        else:
            raise RuntimeError("kalkış başarısız")
        link.set_mode(fc.MODE_FOLLOW)
        wait_for(lambda: link.state.mode == "Follow Me", 20, "Follow Me modu")
        print("Follow Me açık.", flush=True)

        summary = []
        for sc in scenarios:
            sim.target_source = "gercek"
            sim.send_target_velocity = sc["hiz"]
            sim.camera_velocity = "yok"
            sim.band.stop()
            sim.target.parkur_speed_scale = sc["hiz_carpan"]
            sim.ft_link.delay_s = sim.ft_link.loss = 0.0
            sim.target.set_pattern("dur")
            link.set_param("FLW_TGT_HT", float(sc["ht"]))
            time.sleep(0.1)
            link.set_param("FLW_TGT_DST", float(sc["dst"]))
            time.sleep(args.settle)
            if link.state.mode != "Follow Me":
                link.set_mode(fc.MODE_FOLLOW)
                time.sleep(3)
            sim.target_source = sc["kaynak"]
            sim.kalman.reset()
            sim.camera_velocity = sc["kamera_hiz"]
            if sc["bant"]:
                sim.band.v_top, sim.band.v_bottom = sc["bant"]
                sim.band.start(sc["dst"])
            sim.ft_link.delay_s, sim.ft_link.loss, sim.ft_link.burst = sc["ft_delay"], sc["ft_loss"], sc["ft_burst"]
            sim.ft_link.submitted = sim.ft_link.dropped = 0
            rec.start(sc["name"])
            sim.target.set_pattern("parkur")
            t0 = time.monotonic()
            wait_for(lambda: sim.target.parkur_finished, 200, "parkur")
            time.sleep(4)  # catch the drone settling after the last wait
            n = rec.stop(out / f"{sc['name']}.csv")
            sim.band.stop()
            info = dict(sc, rows=n, kf_rejected=sim.kalman.rejected_total, duration_s=round(time.monotonic() - t0, 1), egim=args.egim,
                        ft_submitted=sim.ft_link.submitted, ft_dropped=sim.ft_link.dropped,
                        mode_end=link.state.mode)
            summary.append(info)
            print(f"  {sc['name']}: {n} satır, {info['duration_s']} s, FT gönderilen {info['ft_submitted']}, "
                  f"düşen {info['ft_dropped']}, mod {info['mode_end']}", flush=True)
            if link.state.mode != "Follow Me":
                link.set_mode(fc.MODE_FOLLOW)
        (out / "ozet.json").write_text(json.dumps({"egim": args.egim, "senaryolar": summary,
                                                   "mesajlar": link.state.messages}, indent=1, ensure_ascii=False))
        print("Bitti.", flush=True)
        return 0
    finally:
        if sim is not None:
            sim.stop()
        stop_group(px4)
        log.close()


def stop_group(proc, timeout=30.0):
    """SIGTERM the whole session (PX4, Gazebo server, video stream), wait until it is gone, SIGKILL leftovers."""
    def alive():
        return subprocess.run(["pgrep", "-s", str(proc.pid)], capture_output=True).returncode == 0
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    t0 = time.monotonic()
    while alive() and time.monotonic() - t0 < timeout:
        time.sleep(0.5)
    if alive():
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    proc.wait()


if __name__ == "__main__":
    sys.exit(main())
