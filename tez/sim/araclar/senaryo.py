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
import shutil
import sys
import time
from pathlib import Path

import dogrulama
import hedef
import rapor
from kayit import Recorder
from px4_baglanti import HOLD_MODE_NAME, TEZ_MODE_NAME, Vehicle
from simulasyon import BUILD, SIM_DIR, Simulation

STALL_TIMEOUT = 15.0  # [s wall] sim time not advancing for this long = Gazebo is stuck


def log(text: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {text}", flush=True)


def fly(sc: hedef.Scenario, rec: Recorder, events: list[str]) -> bool:
    v = Vehicle()
    try:
        return _fly(v, sc, rec, events)
    finally:
        v.close()


def _fly(v: Vehicle, sc: hedef.Scenario, rec: Recorder, events: list[str]) -> bool:
    modes = v.modes()
    name = TEZ_MODE_NAME if sc.drone_mode == "tez" else HOLD_MODE_NAME
    if name not in modes:
        events.append(f"'{name}' PX4'ün mod listesinde yok")
        return False
    mode = modes[name]
    log(f"Kalkış: {sc.altitude:.0f} m")
    if not v.takeoff(sc.altitude):
        events.append("Kalkış başarısız")
        return False
    time.sleep(3)  # let the takeoff mode settle into its hover
    if not v.switch_mode(mode):
        events.append(f"'{name}' moduna geçilemedi")
        return False
    events.append(f"Dron {rec.sim_time:.1f} s'de hazır ({name}, {sc.altitude:.0f} m)")
    if rec.sim_time > sc.start_time - 1:
        events.append(
            f"Dron hedef yürümeye başlamadan hazır olamadı ({rec.sim_time:.0f} s > {sc.start_time:.0f} s): "
            "zamanlama.baslama_s değerini büyütün"
        )
        return False
    rec.start()
    log(f"Kayıt başladı; hedef {sc.start_time:.0f} s'de yürümeye başlayacak, senaryo {sc.end_time:.0f} s'de bitecek")
    last_t, last_change = rec.sim_time, time.monotonic()
    while rec.sim_time < sc.end_time:
        current = v.current_mode(timeout=1.0)
        if current is not None and current != mode:
            events.append(f"{rec.sim_time:.1f} s: dron senaryo modundan çıktı")
            mode = current
        if rec.sim_time != last_t:
            last_t, last_change = rec.sim_time, time.monotonic()
        elif time.monotonic() - last_change > STALL_TIMEOUT:
            rec.stop()
            events.append(f"Simülasyon zamanı {last_t:.1f} s'de durdu (Gazebo takıldı)")
            return False
    rec.stop()
    log("Senaryo bitti, iniş")
    if not v.land():
        events.append("İniş/disarm tamamlanamadı")
    return True


def run(sc: hedef.Scenario, out: Path, headless: bool, verify: bool) -> dict:
    """Fly the scenario once and write the report into `out`; returns the summary (ozet.json)."""
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(sc.source, out / "senaryo.yaml")
    check_pos = dogrulama.camera_pose(sc) if verify else None
    world_file = hedef.write_world(sc, out, dogrulama.camera_sdf(check_pos) if verify else "", shadows=not verify)
    log(f"Senaryo '{sc.name}': hedef yolu {sc.path_length():.1f} m, {sc.walk_end - sc.start_time:.1f} s; çıktı {out}")

    events: list[str] = []
    rec = Recorder(sc, sc.world)
    check = dogrulama.OverheadCheck(sc, check_pos) if verify else None
    sim = Simulation(out, world_file, headless)
    completed = False
    try:
        with sim:
            if not sim.wait_ready():
                events.append("Simülasyon açılmadı (sim.log'a bakın)")
            else:
                log("PX4 ve Gazebo hazır")
                completed = fly(sc, rec, events)
            log("Simülasyon kapatılıyor")
    except KeyboardInterrupt:
        events.append("Kullanıcı durdurdu (Ctrl+C)")
    except Exception as e:  # noqa: BLE001 - the report must still be written
        events.append(f"Beklenmeyen hata: {type(e).__name__}: {e}")
    events += sim.problems()

    ulog = sim.newest_ulog()
    if ulog is not None:
        shutil.copy(ulog, out / "ucus.ulg")
    rows = rec.snapshot()
    checks = check.results(rows, out) if check is not None else []
    return rapor.write(
        out,
        sc,
        rows,
        events,
        completed,
        checks,
        rec.camera.as_dict() if rec.camera else None,
        {
            "ofset_m": rec.camera_offset,
            "dcm_optik_govde": rec.camera_dcm.tolist() if rec.camera_dcm is not None else None,
        },
        (out / "ucus.ulg") if ulog else None,
    )


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
    if not (SIM_DIR / "models" / "insan" / "meshes" / "walk_tez.dae").is_file():
        print("İnsan modeli kurulu değil veya eski. Önce: tez/sim/kur.sh", file=sys.stderr)
        return 2
    if not (BUILD / "bin" / "px4").is_file():
        print("PX4 derlenmemiş. Önce: tez/sim/derle.sh", file=sys.stderr)
        return 2

    out = args.cikti or SIM_DIR / "sonuclar" / f"{dt.datetime.now():%Y%m%d_%H%M%S}_{sc.name}"
    summary = run(sc, out, args.ekransiz, args.dogrula)
    log(f"Rapor: {out / 'rapor.html'}")
    log(f"SONUÇ: {summary['sonuc']}")
    return 0 if summary["sonuc"] == "GEÇTİ" else 1


if __name__ == "__main__":
    sys.exit(main())
