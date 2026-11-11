#!/usr/bin/env python3
"""Run one scenario end to end and write its report.

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo yuruyen_insan
    ... --ekransiz          no Gazebo window
    ... --dogrula           overhead camera checks that the rendered target is where the ground truth says
    ... --param AD=DEĞER    one more PX4 start parameter after the scenario's takip.px4_parametreleri (repeatable)
    ... --help              every option: model (--model, --imgsz, --conf, --sinif, --modelsiz), tracking (--takip,
                            --mod-adi, --los, --px4-baslat), delay and video (--gecikme-ms, --qgc, --videosuz,
                            --kareleri-sakla); each replaces the scenario's value

Steps: check the model file (sha256), start the model process and wait for the loaded model, write the scenario
world (base world + target), start Gazebo + PX4 (calistir.sh) with the start parameters, read them back from PX4,
take off, switch to the mode of the scenario's tracking source (takip.kaynak; "yok" = PX4 "Hold"), record ground
truth while the target walks, stop the model process, land, shut down, collect the ULog, write the report to
tez/sim/sonuclar/<date>_<scenario>/. ozet.json "ayarlar" holds every setting of the run (scenario + command line).
A setting that a later task group of spec 2026-11-10-m06-sim-ortami wires in stops the run before anything starts.

The model (algilama.py) runs in its own process on the newest camera frame only, from the moment Gazebo publishes
until the recording ends; frames that arrive while it is busy are skipped and counted. algilama.csv has one row per
processed frame (times, model_ms, boxes), kutular.csv every box; both join dogru_cevap.csv on round(t * 1e6).
--modelsiz (algilama.etkin: false) starts no model process at all.
"""

import argparse
import datetime as dt
import importlib.util
import shutil
import sys
import time
from pathlib import Path

import algilama
import dogrulama
import goruntu
import hedef
import parametreler
import rapor
from kayit import Recorder
from px4_baglanti import FOLLOW_TARGET_MODE_NAME, HOLD_MODE_NAME, Vehicle
from simulasyon import BUILD, SIM_DIR, Simulation, running

STALL_TIMEOUT = 15.0  # [s wall] sim time not advancing for this long = Gazebo is stuck
RTF_WARNING = 0.9  # below this mean real time factor the report warns: the model may take the CPU from Gazebo
RTF_SPAN = 5.0  # [s sim] pieces of the window for the lowest RTF
PROGRESS_EVERY = 10.0  # [s sim] the model's numbers in the log while recording
# PX4 mode (AVAILABLE_MODES name) of each tracking source; chosen by name, never by number (tez_los: takip.mod_adi)
TRACKING_MODES = {"yok": HOLD_MODE_NAME, "follow_me": FOLLOW_TARGET_MODE_NAME}


def log(text: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {text}", flush=True)


def mode_name(sc: hedef.Scenario) -> str:
    """AVAILABLE_MODES name of the mode the tracking source flies in."""
    t = sc.tracking
    return t.mode_name if t.source == "tez_los" else TRACKING_MODES[t.source]


def settings(sc: hedef.Scenario, model: algilama.ModelFile | None = None) -> dict:
    """ozet.json "ayarlar": hedef.settings + the PX4 mode + the model file (path, sha256, modeller.yaml record);
    fly() adds what PX4 reports for each start parameter, run() what the loaded model reports."""
    s = hedef.settings(sc)
    s["takip"] = {"kaynak": s["takip"]["kaynak"], "mod": mode_name(sc)} | s["takip"]
    if model is not None:
        s["algilama"]["model"] = str(model.path)
        s["algilama"]["model_dosyasi"] = model.as_dict()
    return s


def check_model(sc: hedef.Scenario) -> algilama.ModelFile | None:
    """The run's model file and its sha256, before anything starts; None without a model (--modelsiz).

    FileNotFoundError says where the file comes from; ModuleNotFoundError if the model packages are missing."""
    if not sc.detection.enabled:
        return None
    model = algilama.inspect_model(algilama.model_path(sc.detection.model), algilama.load_catalog())
    if importlib.util.find_spec("ultralytics") is None:  # not imported here: only the model process opens it
        raise ModuleNotFoundError(
            "ultralytics kurulu değil: model paketleri tez/env/model-requirements.txt ile kurulur (tez/env/VERSIONS.md)"
            "; modelsiz koşmak için --modelsiz"
        )
    return model


def model_settings(sc: hedef.Scenario, model: algilama.ModelFile) -> algilama.ModelSettings:
    d = sc.detection
    return algilama.ModelSettings(model.path, d.imgsz, d.conf, d.class_name, d.cores, dict(sc.defects))


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


def fly(
    sc: hedef.Scenario,
    rec: Recorder,
    events: list[str],
    run_settings: dict,
    model: algilama.ModelProcess | None = None,
    detections: algilama.DetectionLog | None = None,
) -> bool:
    v = Vehicle()
    try:
        return _fly(v, sc, rec, events, run_settings, model, detections)
    finally:
        v.close()


def _model_ok(model: algilama.ModelProcess | None, events: list[str]) -> bool:
    """The model process is still running and has processed frames (it works on the camera since Gazebo started)."""
    if model is None:
        return True
    if not model.running:
        events.append("Model süreci kayıttan önce durdu: " + ("; ".join(model.errors) or "nedeni bilinmiyor"))
        return False
    if model.results == 0:
        events.append(f"Model süreci hiç kare işlemedi ({goruntu.CAMERA_TOPIC} konusundan kare gelmedi)")
        return False
    return True


def _progress(model: algilama.ModelProcess | None, detections: algilama.DetectionLog | None) -> None:
    """One log line with what the model did over the last PROGRESS_EVERY sim seconds."""
    last = model.last if model is not None else None
    if last is None or detections is None:
        return
    recent = [r for r in detections.rows[-1000:] if r["t"] > last.t - PROGRESS_EVERY]
    processed, skipped = len(recent), sum(r["onceki_atlanan"] for r in recent)
    log(
        f"  t = {last.t:.0f} s: model {model.results} kare işledi; son {PROGRESS_EVERY:.0f} s'de "
        f"{processed / PROGRESS_EVERY:.1f} kare/s, %{100 * skipped / max(1, processed + skipped):.0f} kare atlandı; "
        f"son kare {len(last.kutular)} kutu, model_ms {last.model_ms:.0f} ms"
    )


def _fly(
    v: Vehicle,
    sc: hedef.Scenario,
    rec: Recorder,
    events: list[str],
    run_settings: dict,
    model: algilama.ModelProcess | None,
    detections: algilama.DetectionLog | None,
) -> bool:
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
    if not _model_ok(model, events):
        return False
    rec.start()
    log(f"Kayıt başladı; hedef {sc.start_time:.0f} s'de yürümeye başlayacak, senaryo {sc.end_time:.0f} s'de bitecek")
    last_t, last_change = rec.sim_time, time.monotonic()
    next_progress = sc.start_time
    while rec.sim_time < sc.end_time:
        current = v.current_mode(timeout=1.0)
        if current is not None and current != mode:
            events.append(f"{rec.sim_time:.1f} s: dron senaryo modundan çıktı")
            mode = current
        if model is not None and not model.running:
            rec.stop()
            events.append(f"{rec.sim_time:.1f} s: model süreci durdu: " + ("; ".join(model.errors) or "?"))
            return False
        if rec.sim_time >= next_progress:
            _progress(model, detections)
            next_progress += PROGRESS_EVERY
        if rec.sim_time != last_t:
            last_t, last_change = rec.sim_time, time.monotonic()
        elif time.monotonic() - last_change > STALL_TIMEOUT:
            rec.stop()
            events.append(f"Simülasyon zamanı {last_t:.1f} s'de durdu (Gazebo takıldı)")
            return False
    rec.stop()
    if model is not None:  # the recording is over: the CPU goes back to Gazebo and PX4 for the landing
        model.stop()
        log(f"Model süreci kapandı: {model.results} kare işlendi")
    log("Senaryo bitti, iniş")
    if not v.land():
        events.append("İniş/disarm tamamlanamadı")
    return True


def start_model(
    sc: hedef.Scenario, model_file: algilama.ModelFile, out: Path, clock: goruntu.SimClock, run_settings: dict
) -> tuple[algilama.ModelProcess, algilama.DetectionLog]:
    """Start the model process and wait until the model is loaded; its results go to algilama.csv / kutular.csv."""
    detections = algilama.DetectionLog(out, clock)
    model = algilama.ModelProcess(model_settings(sc, model_file), detections.add)
    d = sc.detection
    log(f"Model süreci açılıyor: {model_file.path.name}, CPU, {d.cores} çekirdek (indirme ve analitik kapalı)...")
    try:
        info = model.start()
    except algilama.ModelError:
        detections.close()
        raise
    run_settings["algilama"]["model_bilgisi"] = info
    log(
        f"Model hazır: sınıf {info['sinif']} ({info['sinif_adi']}), imgsz {info['imgsz']} (adım {info['adim']}), "
        f"conf {info['conf']}, ilk çağrı {info['isinma_ms']:.0f} ms; kamera kusurları kapalı"
    )
    return model, detections


def frame_books(model: algilama.ModelProcess, detections: algilama.DetectionLog, events: list[str]) -> dict:
    """ozet.json "kare_defteri": every frame that reached the model process is processed, skipped or still waiting,
    and every processed frame reached the main process and algilama.csv (whole model process, not only the window)."""
    books = dict(model.books or {})
    books["ana_surece_ulasan"] = model.results
    books["algilama_csv_satiri"] = len(detections.rows)
    if model.books is None:
        books["tutarli"] = False
        events.append("Model sürecinin kare defteri gelmedi (süreç düzgün kapanmadı)")
        return books
    books["tutarli"] = books["uretilen"] == books["verilen"] + books["atlanan"] + books["bekleyen"] and books[
        "verilen"
    ] == books["islenen"] == model.results == len(detections.rows)
    if not books["tutarli"]:
        events.append(f"Kare defteri tutmuyor: {books}")
    return books


def _detection_log_lines(m: dict) -> None:
    log(
        f"Model: kayıt penceresinde {m['islenen']} kare işlendi ({m['islenen_kare_hizi_hz']:.1f} kare/sim-s), "
        f"{m['atlanan']} kare atlandı (%{100 * m['atlanan_kare_orani']:.0f}; okuyucuya ulaşan {m['uretilen']}, "
        f"kameranın ürettiği {m['kamera_karesi']}); model_ms ort. {m['model_ms_ort']:.0f} ms (p95 "
        f"{m['model_ms_p95']:.0f}), ulaşma {m['ulasma_ms_ort']:.0f} ms, bekleme {m['bekleme_ms_ort']:.0f} ms"
    )
    log(
        f"IoU kontrolü (geçici): {m['iou05_kare_sayisi']} işlenmiş karede bir model kutusu hedefin hakem kutusuyla "
        f"IoU >= 0.5 (en iyi {m['iou_max']:.2f}; hedefin göründüğü işlenmiş kare {m['hedef_gorunur_islenen']})"
    )


def run(
    sc: hedef.Scenario, out: Path, headless: bool, verify: bool, model_file: algilama.ModelFile | None = None
) -> dict:
    """Fly the scenario once and write the report into `out`; returns the summary (ozet.json).

    Before anything starts it raises ValueError if the scenario asks for a setting that is not wired yet,
    FileNotFoundError / ModuleNotFoundError if the model file or the model packages are missing (check_model) and
    algilama.ModelError if the model refuses a setting (imgsz, class) when it loads.
    """
    hedef.check_wired(sc)
    if model_file is None:
        model_file = check_model(sc)
    run_settings = settings(sc, model_file)
    log(f"Senaryo '{sc.name}': hedef yolu {sc.path_length():.1f} m, {sc.walk_end - sc.start_time:.1f} s; çıktı {out}")
    t = sc.tracking
    log(f"Takip kaynağı {t.source} (PX4 modu '{run_settings['takip']['mod']}'), LOS {t.los or 'yok'}")
    waiting = run_settings["henuz_bagli_degil"]
    if waiting:
        log("Henüz bağlanmamış varsayılanlar, bu koşuda etkin değil: " + ", ".join(waiting))

    events: list[str] = []
    clock = goruntu.SimClock()
    clock.subscribe(sc.world)
    model = detections = None
    if model_file is not None:  # loaded before anything is written or started: a refused setting stops here
        known = f"modeller.yaml'da {model_file.known.name}" if model_file.known else "modeller.yaml'da kayıtlı değil"
        log(f"Model dosyası {model_file.path} ({model_file.size} bayt), sha256 {model_file.sha256} ({known})")
        if model_file.warning:
            log(f"UYARI: {model_file.warning}")
            events.append(f"Model dosyası uyarısı: {model_file.warning}")
        model, detections = start_model(sc, model_file, out, clock, run_settings)
    else:
        log("Model yok (--modelsiz / algilama.etkin: false): model süreci açılmaz")
    try:
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy(sc.source, out / "senaryo.yaml")
        check_pos = dogrulama.camera_pose(sc) if verify else None
        world_file = hedef.write_world(sc, out, dogrulama.camera_sdf(check_pos) if verify else "")
        rec = Recorder(sc, sc.world)
        check = dogrulama.OverheadCheck(sc, check_pos) if verify else None
    except BaseException:
        if model is not None:  # never leave the model process behind
            model.stop()
        raise
    # scenario's takip.px4_parametreleri, then --param: calistir.sh loads them after the .params files
    sim = Simulation(out, world_file, headless, params={p.name: p.value for p in t.px4_params})
    completed = False
    try:
        with sim:
            if not sim.wait_ready():
                events.append("Simülasyon açılmadı (sim.log'a bakın)")
            else:
                log("PX4 ve Gazebo hazır")
                completed = fly(sc, rec, events, run_settings, model, detections)
            log("Simülasyon kapatılıyor")
    except KeyboardInterrupt:
        events.append("Kullanıcı durdurdu (Ctrl+C)")
    except Exception as e:  # noqa: BLE001 - the report must still be written
        events.append(f"Beklenmeyen hata: {type(e).__name__}: {e}")
    finally:
        if model is not None:
            model.stop()
            detections.close()
    events += sim.problems()

    ulog = sim.newest_ulog()
    if ulog is not None:
        shutil.copy(ulog, out / "ucus.ulg")
    rows = rec.snapshot()
    checks = check.results(out) if check is not None else []
    # sim seconds per wall second in the scenario window (Gazebo does not wait for the model)
    more = {"rtf_ort": clock.rtf(sc.start_time, sc.end_time), "rtf_min_5s": clock.rtf_min(sc.start_time, sc.end_time)}
    if more["rtf_ort"] < RTF_WARNING:
        events.append(
            f"RTF {more['rtf_ort']:.2f} (< {RTF_WARNING}): simülasyon gerçek zamandan yavaş aktı; model CPU'yu "
            "Gazebo'dan alıyor olabilir"
        )
    log(f"RTF (kayıt penceresi): ort. {more['rtf_ort']:.3f}, en düşük {more['rtf_min_5s']:.3f} ({RTF_SPAN:.0f} s'lik)")
    sections = {}
    if model is not None:
        more |= detections.metrics(sc.start_time, sc.end_time, rows)
        sections["kare_defteri"] = frame_books(model, detections, events)
        events += [f"Model süreci: {e}" for e in model.errors]
        completed &= not model.errors
        if more["islenen"] == 0:
            events.append("Kayıt penceresinde işlenmiş kare yok: model ölçütleri hesaplanamadı")
        else:
            if more["iou05_kare_sayisi"] == 0:
                events.append("Geçici IoU kontrolü: hiçbir işlenmiş karede model kutusu hedefle IoU >= 0.5 değil")
            _detection_log_lines(more)
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
        more,
        sections,
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
        model_file = check_model(sc)
    except (ValueError, FileNotFoundError, ModuleNotFoundError) as e:
        print(f"Senaryo hatası: {e}", file=sys.stderr)
        return 2
    if not (SIM_DIR / "models" / "insan" / "meshes" / ".tamam").is_file():
        print("İnsan modeli kurulu değil veya eski. Önce: tez/sim/kur.sh", file=sys.stderr)
        return 2
    if not (BUILD / "bin" / "px4").is_file():
        print("PX4 derlenmemiş. Önce: tez/sim/derle.sh", file=sys.stderr)
        return 2
    if running():  # before the model loads for nothing
        print("Zaten çalışan bir PX4 veya Gazebo var; önce onu kapatın (ya da bitmesini bekleyin)", file=sys.stderr)
        return 2

    out = args.cikti or SIM_DIR / "sonuclar" / f"{dt.datetime.now():%Y%m%d_%H%M%S}_{sc.name}"
    try:
        summary = run(sc, out, args.ekransiz, args.dogrula, model_file)
    except algilama.ModelError as e:
        print(f"Model hatası, simülasyon açılmadı: {e}", file=sys.stderr)
        return 2
    log(f"Rapor: {out / 'rapor.html'}")
    log(f"SONUÇ: {summary['sonuc']}")
    return 0 if summary["sonuc"] == "GEÇTİ" else 1


if __name__ == "__main__":
    sys.exit(main())
