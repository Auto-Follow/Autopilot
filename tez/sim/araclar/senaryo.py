#!/usr/bin/env python3
"""Run one scenario end to end and write its report.

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo yuruyen_insan
    ... --ekransiz          no Gazebo window
    ... --dogrula           overhead camera checks that the rendered target is where the ground truth says
    ... --param AD=DEĞER    one more PX4 start parameter after the scenario's takip.px4_parametreleri (repeatable)
    ... --help              every option: model (--model, --imgsz, --conf, --sinif, --modelsiz), tracking (--takip,
                            --mod-adi, --los, --px4-baslat), delay and video (--gecikme-ms, --qgc, --videosuz,
                            --kareleri-sakla); each replaces the scenario's value

Steps: write the scenario world (base world + target), start Gazebo + PX4 (calistir.sh) with the start parameters,
read them back from PX4, take off, switch to the mode of the scenario's tracking source (takip.kaynak; "yok" = PX4
"Hold"), record ground truth while the target walks, land, shut down, collect the ULog, write the report to
tez/sim/sonuclar/<date>_<scenario>/. ozet.json "ayarlar" holds every setting of the run (scenario + command line).
A setting that a later task group of spec 2026-11-10-m06-sim-ortami wires in stops the run before anything starts.
"""

import argparse
import datetime as dt
import shutil
import sys
import time
from pathlib import Path

import dogrulama
import hedef
import parametreler
import rapor
from kayit import Recorder
from px4_baglanti import FOLLOW_TARGET_MODE_NAME, HOLD_MODE_NAME, Vehicle
from simulasyon import BUILD, SIM_DIR, Simulation

STALL_TIMEOUT = 15.0  # [s wall] sim time not advancing for this long = Gazebo is stuck
# PX4 mode (AVAILABLE_MODES name) of each tracking source; chosen by name, never by number (tez_los: takip.mod_adi)
TRACKING_MODES = {"yok": HOLD_MODE_NAME, "follow_me": FOLLOW_TARGET_MODE_NAME}


def log(text: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {text}", flush=True)


def mode_name(sc: hedef.Scenario) -> str:
    """AVAILABLE_MODES name of the mode the tracking source flies in."""
    t = sc.tracking
    return t.mode_name if t.source == "tez_los" else TRACKING_MODES[t.source]


def settings(sc: hedef.Scenario) -> dict:
    """ozet.json "ayarlar": hedef.settings + the PX4 mode; fly() adds what PX4 reports for each start parameter."""
    s = hedef.settings(sc)
    s["takip"] = {"kaynak": s["takip"]["kaynak"], "mod": mode_name(sc)} | s["takip"]
    return s


def check_start_params(v: Vehicle, params: dict[str, dict], events: list[str]) -> bool:
    """Read every start parameter back from PX4 into params[name]["px4"]; a value PX4 does not hold stops the run.

    calistir.sh hands them to PX4 as PX4_PARAM_*, which rcS sets with `param set`. That skips a value equal to the
    current default, and a later `param set-default` of the airframe can still change it (spec 1.): only the value
    read back says what the run flies with.
    """
    wrong = []
    for name, entry in params.items():
        entry["px4"] = v.get_param(name)
        if not parametreler.matches(entry["deger"], entry["px4"]):
            # PX4 keeps floats as float32: 7 significant digits show it (0.6, not 0.600000024)
            got = "okunamadı" if entry["px4"] is None else f"{entry['px4']:.7g}"
            wanted = parametreler.format_value(entry["deger"])
            wrong.append(f"{name} PX4'te {got}, istenen {wanted} ({entry['kaynak']})")
    if wrong:
        events.append("Başlangıç parametresi PX4'te istenen değerde değil, koşu durduruldu: " + "; ".join(wrong))
        return False
    log(f"Başlangıç parametreleri PX4'ten geri okundu: {len(params)}/{len(params)} istenen değerde")
    return True


def fly(sc: hedef.Scenario, rec: Recorder, events: list[str], run_settings: dict) -> bool:
    v = Vehicle()
    try:
        return _fly(v, sc, rec, events, run_settings)
    finally:
        v.close()


def _fly(v: Vehicle, sc: hedef.Scenario, rec: Recorder, events: list[str], run_settings: dict) -> bool:
    if not check_start_params(v, run_settings["px4_parametreleri"], events):
        return False
    modes = v.modes()
    name = run_settings["takip"]["mod"]
    if name not in modes:
        events.append(f"'{name}' PX4'ün mod listesinde yok; mevcut modlar: {', '.join(sorted(modes))}")
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
    """Fly the scenario once and write the report into `out`; returns the summary (ozet.json).

    Raises ValueError before anything starts if the scenario asks for a setting that is not wired yet.
    """
    hedef.check_wired(sc)
    run_settings = settings(sc)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(sc.source, out / "senaryo.yaml")
    check_pos = dogrulama.camera_pose(sc) if verify else None
    world_file = hedef.write_world(sc, out, dogrulama.camera_sdf(check_pos) if verify else "")
    log(f"Senaryo '{sc.name}': hedef yolu {sc.path_length():.1f} m, {sc.walk_end - sc.start_time:.1f} s; çıktı {out}")
    t = sc.tracking
    log(f"Takip kaynağı {t.source} (PX4 modu '{run_settings['takip']['mod']}'), LOS {t.los or 'yok'}")
    waiting = run_settings["henuz_bagli_degil"]
    if waiting:
        log("Henüz bağlanmamış varsayılanlar, bu koşuda etkin değil: " + ", ".join(waiting))

    events: list[str] = []
    rec = Recorder(sc, sc.world)
    check = dogrulama.OverheadCheck(sc, check_pos) if verify else None
    # scenario's takip.px4_parametreleri, then --param: calistir.sh loads them after the .params files
    sim = Simulation(out, world_file, headless, params={p.name: p.value for p in t.px4_params})
    completed = False
    try:
        with sim:
            if not sim.wait_ready():
                events.append("Simülasyon açılmadı (sim.log'a bakın)")
            else:
                log("PX4 ve Gazebo hazır")
                completed = fly(sc, rec, events, run_settings)
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
    checks = check.results(out) if check is not None else []
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
        run_settings,
    )


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--senaryo", required=True, help="tez/sim/senaryolar/<ad>.yaml adı veya bir .yaml yolu")
    ap.add_argument("--ekransiz", action="store_true", help="Gazebo penceresi açılmaz")
    ap.add_argument("--dogrula", action="store_true", help="tepe kamerasıyla hedefin konumunu doğrula")
    ap.add_argument("--cikti", type=Path, help="çıktı klasörü (varsayılan tez/sim/sonuclar/<tarih>_<ad>)")
    g = ap.add_argument_group("algılama (senaryodaki algilama bloğunu ezer)")
    g.add_argument("--model", metavar="YOL", help="model dosyası, .pt (algilama.model)")
    g.add_argument("--imgsz", type=int, metavar="PX", help="model giriş boyutu; varsayılan .pt'deki eğitim değeri")
    g.add_argument("--conf", type=float, help="güven eşiği (0..1]; varsayılan 0.25 (algilama.conf)")
    g.add_argument("--sinif", metavar="AD|NO", help="sınıf adı veya numarası; varsayılan adı 'person' olan")
    g.add_argument("--modelsiz", action="store_true", help="model süreci açılmaz (algilama.etkin: false)")
    g = ap.add_argument_group("takip (senaryodaki takip bloğunu ezer)")
    g.add_argument("--takip", metavar="KAYNAK", help="yok | follow_me | tez_los (takip.kaynak)")
    g.add_argument("--mod-adi", metavar="AD", help="tez_los'ta seçilecek PX4 modunun adı (takip.mod_adi)")
    g.add_argument("--los", metavar="KAYNAK", help="TEZ_LOS'un kaynağı: model | hakem (takip.los)")
    g.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="AD=DEĞER",
        help="PX4 başlangıç parametresi, takip.px4_parametreleri'nden sonra yüklenir (birden çok; sonuncu kazanır)",
    )
    g.add_argument(
        "--px4-baslat",
        action="append",
        default=[],
        metavar="KOMUT",
        help="PX4 açıldıktan sonra çalışacak komut, takip.px4_baslat'tan sonra (birden çok)",
    )
    g = ap.add_argument_group("gecikme ve video")
    g.add_argument("--gecikme-ms", type=float, metavar="MS", help="yakalama -> PX4 yoluna ek gecikme (gecikme.ek_ms)")
    g.add_argument("--qgc", action="store_true", help="QGroundControl'e canlı video (video.qgc: true)")
    g.add_argument("--videosuz", action="store_true", help="kosu.mp4 üretilmez (video.mp4: false)")
    g.add_argument("--kareleri-sakla", action="store_true", help="MP4'ün kareleri (kareler/) silinmez")
    return ap


def command_line(args: argparse.Namespace) -> hedef.CommandLine:
    return hedef.CommandLine(
        model=args.model,
        imgsz=args.imgsz,
        conf=args.conf,
        class_name=args.sinif,
        no_model=args.modelsiz,
        source=args.takip,
        mode_name=args.mod_adi,
        los=args.los,
        params=tuple(args.param),
        px4_start=tuple(args.px4_baslat),
        delay_ms=args.gecikme_ms,
        qgc=args.qgc,
        no_video=args.videosuz,
        keep_frames=args.kareleri_sakla,
    )


def main() -> int:
    args = parser().parse_args()
    try:
        sc = hedef.load(args.senaryo, command_line(args))
        hedef.check_wired(sc)
    except (ValueError, FileNotFoundError) as e:
        print(f"Senaryo hatası: {e}", file=sys.stderr)
        return 2
    if not (SIM_DIR / "models" / "insan" / "meshes" / ".tamam").is_file():
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
