#!/usr/bin/env python3
"""Run one scenario end to end and write its report.

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo yuruyen_insan
    ... --ekransiz          no Gazebo window
    ... --dogrula           overhead camera checks that the rendered target is where the ground truth says
    ... --param AD=DEĞER    one more PX4 start parameter after the scenario's takip.px4_parametreleri (repeatable)
    ... --help              every option: model (--model, --imgsz, --conf, --sinif, --modelsiz), tracking (--takip,
                            --mod-adi, --los, --px4-baslat), delay and video (--gecikme-ms, --qgc, --videosuz,
                            --kareleri-sakla); each replaces the scenario's value

Steps: check the mode name and the model file (sha256), start the model process and wait for the loaded model, write
the scenario world (base world + target), start Gazebo + PX4 (calistir.sh) with the start parameters, read them back
from PX4, take off, switch by name to the mode of the scenario's tracking source (takip.kaynak; "yok" = PX4 "Hold",
"tez_los" = takip.mod_adi / --mod-adi), record ground truth while the target walks, stop the model process and the
TEZ_LOS stream, land, shut down, collect the ULog, write the report to tez/sim/sonuclar/<date>_<scenario>/.
ozet.json "ayarlar" holds every setting of the run (scenario + command line). A setting that a later task group of
spec 2026-11-10-m06-sim-ortami wires in, or a mode name PX4 does not offer, stops the run before anything starts.

The model (algilama.py) runs in its own process on the newest camera frame only, from the moment Gazebo publishes
until the recording ends; frames that arrive while it is busy are skipped and counted. The tracking side (takip.py)
selects the target's box in every processed frame and sends its line of sight to PX4 as DEBUG_VECT "TEZ_LOS" (one
message per processed frame, NaN = no target), or the referee's (--los hakem, every camera frame) - in every tracking
source, "yok" included. algilama.csv has one row per processed frame (times, model_ms, boxes, selection, LOS,
TEZ_LOS), kutular.csv every box, tez_los.csv every TEZ_LOS attempt; all join dogru_cevap.csv on round(t * 1e6).
--modelsiz (algilama.etkin: false) starts no model process at all.
"""

import argparse
import datetime as dt
import importlib.util
import math
import shutil
import sys
import time
from collections.abc import Callable
from pathlib import Path

import algilama
import dogrulama
import goruntu
import hedef
import parametreler
import rapor
import takip
from kayit import Recorder
from px4_baglanti import FOLLOW_TARGET_MODE_NAME, HOLD_MODE_NAME, STOCK_MODE_NAMES, Vehicle, check_mode_name
from simulasyon import BUILD, SIM_DIR, Simulation, running

STALL_TIMEOUT = 15.0  # [s wall] sim time not advancing for this long = Gazebo is stuck
RTF_WARNING = 0.9  # below this mean real time factor the report warns: the model may take the CPU from Gazebo
RTF_SPAN = 5.0  # [s sim] pieces of the window for the lowest RTF
PROGRESS_EVERY = 10.0  # [s sim] the model's numbers in the log while recording
# PX4 must have logged the TEZ_LOS messages sent in the window (ULog debug_vect) within this share (tasks.md 5.7)
TEZ_LOS_ULOG_TOLERANCE = 0.05
LOCK_EVENTS_LISTED = 12  # lock events written into the report's events one by one
# PX4 mode (AVAILABLE_MODES name) of each tracking source; chosen by name, never by number (tez_los: takip.mod_adi)
TRACKING_MODES = {"yok": HOLD_MODE_NAME, "follow_me": FOLLOW_TARGET_MODE_NAME}


def log(text: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {text}", flush=True)


def mode_name(sc: hedef.Scenario) -> str:
    """AVAILABLE_MODES name of the mode the tracking source flies in."""
    t = sc.tracking
    return t.mode_name if t.source == "tez_los" else TRACKING_MODES[t.source]


def check_mode(sc: hedef.Scenario) -> None:
    """ValueError before anything starts if PX4 will not offer the mode of the tracking source (by name only)."""
    check_mode_name(mode_name(sc), sc.tracking.px4_start)


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
    tracker: takip.Tracker | None = None,
) -> bool:
    v = Vehicle()
    if tracker is not None:  # TEZ_LOS goes out from the moment the link to PX4 exists
        tracker.attach(v)
    try:
        return _fly(v, sc, rec, events, run_settings, model, detections, tracker)
    finally:
        if tracker is not None:
            tracker.detach()
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


def _progress(
    model: algilama.ModelProcess | None,
    detections: algilama.DetectionLog | None,
    tracker: takip.Tracker | None,
    now: float,
) -> None:
    """Log lines with what the model and the TEZ_LOS stream did over the last PROGRESS_EVERY sim seconds."""
    last = model.last if model is not None else None
    if last is not None and detections is not None:
        recent = [r for r in detections.rows[-1000:] if r["t"] > last.t - PROGRESS_EVERY]
        processed, skipped = len(recent), sum(r["onceki_atlanan"] for r in recent)
        log(
            f"  t = {last.t:.0f} s: model {model.results} kare işledi; son {PROGRESS_EVERY:.0f} s'de "
            f"{processed / PROGRESS_EVERY:.1f} kare/s, %{100 * skipped / max(1, processed + skipped):.0f} kare "
            f"atlandı; son kare {len(last.kutular)} kutu, model_ms {last.model_ms:.0f} ms"
        )
    if tracker is not None:
        log(f"  t = {now:.0f} s: son {PROGRESS_EVERY:.0f} s'de {tracker.recent(now - PROGRESS_EVERY)}")


def _fly(
    v: Vehicle,
    sc: hedef.Scenario,
    rec: Recorder,
    events: list[str],
    run_settings: dict,
    model: algilama.ModelProcess | None,
    detections: algilama.DetectionLog | None,
    tracker: takip.Tracker | None,
) -> bool:
    if not check_start_params(v, run_settings["px4_parametreleri"], events):
        return False
    modes = v.modes()  # name -> custom_mode of the modes PX4 offers now; the number is only ever taken from here
    run_settings["takip"]["px4_modlari"] = sorted(modes)
    missing = sorted(set(STOCK_MODE_NAMES) - set(modes))
    if missing:  # the list checked before the start differs from PX4's: the run goes on, PX4's list decides
        events.append(f"PX4'ün mod listesinde beklenen stok modlar yok: {', '.join(missing)}")
    name = run_settings["takip"]["mod"]
    if name not in modes:
        events.append(
            f"'{name}' PX4'ün mod listesinde yok (takip.mod_adi / --mod-adi); PX4'ün seçilebilir modları: "
            f"{', '.join(sorted(modes))}"
        )
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
            _progress(model, detections, tracker, rec.sim_time)
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
    if tracker is not None:  # like the Pi's model: the TEZ_LOS stream ends with the recording
        tracker.close()
        sent = tracker.sender.counts["gonderildi"]
        log(f"TEZ_LOS akışı kapandı: {sent} mesaj gönderildi")
    log("Senaryo bitti, iniş")
    if not v.land():
        events.append("İniş/disarm tamamlanamadı")
    return True


def start_model(
    sc: hedef.Scenario,
    model_file: algilama.ModelFile,
    run_settings: dict,
    on_result: Callable[[algilama.FrameResult, float], None],
) -> algilama.ModelProcess:
    """Start the model process and wait until the model is loaded; every result goes to on_result (the tracking
    thread, which writes algilama.csv / kutular.csv)."""
    model = algilama.ModelProcess(model_settings(sc, model_file), on_result)
    d = sc.detection
    log(f"Model süreci açılıyor: {model_file.path.name}, CPU, {d.cores} çekirdek (indirme ve analitik kapalı)...")
    info = model.start()
    run_settings["algilama"]["model_bilgisi"] = info
    log(
        f"Model hazır: sınıf {info['sinif']} ({info['sinif_adi']}), imgsz {info['imgsz']} (adım {info['adim']}), "
        f"conf {info['conf']}, ilk çağrı {info['isinma_ms']:.0f} ms; kamera kusurları kapalı"
    )
    return model


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


def _tracking_log_lines(m: dict, summary: dict) -> None:
    lock = summary["kilit"]
    log(
        f"TEZ_LOS ({summary['kaynak']}): kayıt penceresinde {m['tez_los_gonderilen']} gönderildi "
        f"({m['tez_los_hedef_yok']} hedef yok, {m['tez_los_hizi_hz']:.1f} mesaj/sim-s), "
        f"{m['tez_los_gecersiz']} geçersiz; "
        f"uçtan uca ort. {m['uctan_uca_ms_ort']:.0f} ms (p50 {m['uctan_uca_ms_p50']:.0f}, p95 "
        f"{m['uctan_uca_ms_p95']:.0f}, en çok {m['uctan_uca_ms_maks']:.0f}); bütün koşuda {summary['sonuclar']}"
    )
    if "tez_los_px4_sayisi" in m:
        log(
            f"PX4'ün ULog'unda kayıt penceresinde {m['tez_los_px4_sayisi']} TEZ_LOS (debug_vect); yönlü olanlardan "
            f"{m['tez_los_px4_eslesen']} gönderilenle eşleşti, PX4'ün varış damgasıyla uçtan uca ort. "
            f"{m['uctan_uca_px4_ms_ort']:.0f} ms (p95 {m['uctan_uca_px4_ms_p95']:.0f}); PX4 varışı - gönderim ort. "
            f"{m['px4_varis_eksi_gonderim_ms_ort']:.1f} ms"
        )
    if not math.isnan(m["secili_kare_orani"]):  # the model's frames were selected (not without a model)
        log(
            f"Hedef seçimi: {lock['kilit_sayisi']} kilit, {lock['kilit_kaybi']} kilit kaybı, {lock['yeniden_kilit']} "
            f"yeniden kilit (bütün koşu); kayıt penceresinde seçili kare %{100 * m['secili_kare_orani']:.0f}, hedef "
            f"görünürken doğru kutu %{100 * m['secim_dogru_orani']:.0f}; LOS (i)-(ii) farkı ort. "
            f"{m['los_i_ii_fark_ort_deg']:.2f}°, p95 {m['los_i_ii_fark_p95_deg']:.2f}°, en çok "
            f"{m['los_i_ii_fark_maks_deg']:.2f}° ({m['los_i_ii_kare']} kare)"
        )


def tracking_results(
    tracker: takip.Tracker,
    sc: hedef.Scenario,
    detections: algilama.DetectionLog | None,
    rows: list[dict],
    ulog: Path | None,
    events: list[str],
) -> tuple[dict, dict]:
    """The TEZ_LOS stream's and the selection's numbers in the window (olcutler) and the whole run (ozet.json
    "tez_los"); events for the lock changes and a ULog count off by more than TEZ_LOS_ULOG_TOLERANCE."""
    m = tracker.metrics(sc.start_time, sc.end_time, detections.rows if detections is not None else [], rows)
    sent = [a for a in tracker.attempts if a["sonuc"] == "gonderildi"]
    m |= rapor.ulog_tez_los(ulog, sc.start_time, sc.end_time, sent)
    if "tez_los_px4_sayisi" in m:
        sent = m["tez_los_gonderilen"]
        m["tez_los_px4_orani"] = m["tez_los_px4_sayisi"] / sent if sent else float("nan")
        if not sent or abs(m["tez_los_px4_orani"] - 1.0) > TEZ_LOS_ULOG_TOLERANCE:
            events.append(
                f"TEZ_LOS: PX4'ün ULog'unda {m['tez_los_px4_sayisi']} kayıt, gönderilen {sent} (kayıt penceresi; "
                f"izin verilen fark %{100 * TEZ_LOS_ULOG_TOLERANCE:.0f})"
            )
    summary = tracker.summary()
    lock_events = summary["kilit"]["olaylar"]
    names = {"ilk_kilit": "ilk kilit", "yeniden_kilit": "yeniden kilit", "kilit_kaybi": "kilit kaybı"}
    for e in lock_events[:LOCK_EVENTS_LISTED]:
        detail = f"IoU {e['kilit_iou']:.2f}" if "kilit_iou" in e else f"{e['ardisik_kacirma']} karede eşleşme yok"
        events.append(f"{e['t']:.2f} s: {names[e['olay']]} (kilit {e['kilit_no']}, {detail})")
    if len(lock_events) > LOCK_EVENTS_LISTED:
        events.append(f"... {len(lock_events) - LOCK_EVENTS_LISTED} kilit olayı daha (ozet.json tez_los.kilit)")
    events += [f"Takip: {e}" for e in summary["hatalar"]]
    _tracking_log_lines(m, summary)
    return m, summary


def run(
    sc: hedef.Scenario, out: Path, headless: bool, verify: bool, model_file: algilama.ModelFile | None = None
) -> dict:
    """Fly the scenario once and write the report into `out`; returns the summary (ozet.json).

    Before anything starts it raises ValueError if the scenario asks for a setting that is not wired yet or for a mode
    PX4 does not offer, FileNotFoundError / ModuleNotFoundError if the model file or the model packages are missing
    (check_model) and algilama.ModelError if the model refuses a setting (imgsz, class) when it loads.
    """
    hedef.check_wired(sc)
    check_mode(sc)
    if model_file is None:
        model_file = check_model(sc)
    run_settings = settings(sc, model_file)
    log(f"Senaryo '{sc.name}': hedef yolu {sc.path_length():.1f} m, {sc.walk_end - sc.start_time:.1f} s; çıktı {out}")
    t = sc.tracking
    los_text = {"model": "model kutusu, LOS (i)", "hakem": "hakem, LOS (ii)", None: "yok, TEZ_LOS gönderilmez"}[t.los]
    log(f"Takip kaynağı {t.source} (PX4 modu '{run_settings['takip']['mod']}'), TEZ_LOS kaynağı {los_text}")
    waiting = run_settings["henuz_bagli_degil"]
    if waiting:
        log("Henüz bağlanmamış varsayılanlar, bu koşuda etkin değil: " + ", ".join(waiting))

    events: list[str] = []
    clock = goruntu.SimClock()
    clock.subscribe(sc.world)
    rec: Recorder | None = None
    detections = algilama.DetectionLog(out, clock, takip.ROW_COLUMNS) if model_file is not None else None
    tracker = None
    if t.los is not None:  # the tracking threads: selection, LOS, delay line, TEZ_LOS
        tracker = takip.Tracker(
            t.los, clock, out, detections, lambda: rec.camera if rec is not None else None, sc.delay.extra_ms
        )
    model = None
    try:
        if model_file is not None:  # loaded before anything is written or started: a refused setting stops here
            known = (
                f"modeller.yaml'da {model_file.known.name}" if model_file.known else "modeller.yaml'da kayıtlı değil"
            )
            log(f"Model dosyası {model_file.path} ({model_file.size} bayt), sha256 {model_file.sha256} ({known})")
            if model_file.warning:
                log(f"UYARI: {model_file.warning}")
                events.append(f"Model dosyası uyarısı: {model_file.warning}")
            model = start_model(sc, model_file, run_settings, tracker.on_model if tracker else detections.add)
        else:
            log("Model yok (--modelsiz / algilama.etkin: false): model süreci açılmaz")
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy(sc.source, out / "senaryo.yaml")
        check_pos = dogrulama.camera_pose(sc) if verify else None
        world_file = hedef.write_world(sc, out, dogrulama.camera_sdf(check_pos) if verify else "")
        rec = Recorder(sc, sc.world, tracker.on_referee if tracker is not None else None)
        check = dogrulama.OverheadCheck(sc, check_pos) if verify else None
    except BaseException:
        if model is not None:  # never leave the model process behind
            model.stop()
        if tracker is not None:
            tracker.close()
        if detections is not None:
            detections.close()
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
                completed = fly(sc, rec, events, run_settings, model, detections, tracker)
            log("Simülasyon kapatılıyor")
    except KeyboardInterrupt:
        events.append("Kullanıcı durdurdu (Ctrl+C)")
    except Exception as e:  # noqa: BLE001 - the report must still be written
        events.append(f"Beklenmeyen hata: {type(e).__name__}: {e}")
    finally:
        if model is not None:
            model.stop()
        if tracker is not None:  # after the model: its last results still go out or are refused, then rows
            tracker.close()
        if detections is not None:
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
    if tracker is not None:
        tracking, sections["tez_los"] = tracking_results(
            tracker, sc, detections, rows, (out / "ucus.ulg") if ulog else None, events
        )
        sections["tez_los"]["hakem_eksik_kare"] = rec.join_dropped
        events += [f"Hakem akışı: {e}" for e in rec.errors]
        completed &= not sections["tez_los"]["hatalar"] and not rec.errors  # a broken TEZ_LOS stream is no result
        more |= tracking
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
        check_mode(sc)
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
