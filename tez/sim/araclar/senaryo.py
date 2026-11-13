#!/usr/bin/env python3
"""Run one scenario end to end and write its report.

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/senaryo.py --senaryo yuruyen_insan
    ... --ekransiz          no Gazebo window
    ... --dogrula           overhead camera checks that the rendered target is where the ground truth says
    ... --param AD=DEĞER    one more PX4 start parameter after the scenario's takip.px4_parametreleri (repeatable)
    ... --kamera-egim 30    camera tilt below the nose for this run (kamera.egim_deg; the real mount: 45)
    ... --help              every option: model (--model, --imgsz, --conf, --sinif, --modelsiz), tracking (--takip,
                            --mod-adi, --los, --px4-baslat), delay and video (--gecikme-ms, --qgc, --videosuz,
                            --kareleri-sakla); each replaces the scenario's value

Steps: check the mode name and the model file (sha256), start the model process and wait for the loaded model, write
the scenario world (base world + target), start Gazebo + PX4 (calistir.sh) with the start parameters, read them back
from PX4, take off, switch by name to the mode of the scenario's tracking source (takip.kaynak; "yok" = PX4 "Hold",
"follow_me" = "Follow Target", "tez_los" = takip.mod_adi / --mod-adi), record ground truth while the target walks,
stop the model process and the TEZ_LOS / FOLLOW_TARGET streams, land, shut down, collect the ULog, write the report
to tez/sim/sonuclar/<date>_<scenario>/.
ozet.json "ayarlar" holds every setting of the run (scenario + command line).
The camera tilt (kamera.egim_deg / --kamera-egim, nominal 45 deg) is one setting for everything: a tilt other than
models/x500_tez's own gives the run a tilted copy of the model (hedef.camera_model), LOS (i), the flat-ground position,
the camera's near limit and the video use it, and the tilt Gazebo reports is compared with it after the run.
A setting that a later task group of spec 2026-11-10-m06-sim-ortami wires in, or a mode name PX4 does not offer,
stops the run before anything starts.

The model (algilama.py) runs in its own process on the newest camera frame only, from the moment Gazebo publishes
until the recording ends; frames that arrive while it is busy are skipped and counted. The tracking side (takip.py)
selects the target's box in every processed frame and sends its line of sight to PX4 as DEBUG_VECT "TEZ_LOS" (one
message per processed frame, NaN = no target), or the referee's (--los hakem, every camera frame) - in every tracking
source, "yok" included. algilama.csv has one row per processed frame (times, model_ms, boxes, selection, LOS,
TEZ_LOS), kutular.csv every box, tez_los.csv every TEZ_LOS attempt; all join dogru_cevap.csv on round(t * 1e6).
--modelsiz (algilama.etkin: false) starts no model process at all.

follow_me closes the loop with PX4's stock Follow Me: the chosen box's flat-ground position (konumlama.py, the EKF
pose of the frame) goes to PX4 as FOLLOW_TARGET (at most every third camera frame); with --los hakem the person's
true position, only while they are visible. FLW_TGT_HT is drone.yukseklik_m unless given. follow_target.csv has
every FOLLOW_TARGET attempt; algilama.csv the position of every chosen box (every tracking source).

The numbers (ozet.json "olcutler"): olcum.measure, every key of spec "Ölçüt Tanımları", from the referee's rows, the
model's frames, the TEZ_LOS / FOLLOW_TARGET attempts, the mode the heartbeat reported and PX4's ULog files; the report
(rapor.py) adds the checks and warnings (model on the image, 3 m, the camera's near limit, mode, RTF). Several runs
of one scenario and their spread: toplu.py.

kosu.mp4 (unless --videosuz): a recorder process (goruntu_yayini.py) writes the camera frames of the referee's
recording (15 fps of sim time, 1280x720 JPEG) into kareler/ while the run goes on; after the run video.py puts the
video together from the run's files (camera with the referee's and the model's boxes | top view), then kareler/ goes
(--kareleri-sakla keeps it).
"""

import argparse
import datetime as dt
import importlib.util
import math
import shutil
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

import algilama
import dogrulama
import goruntu
import goruntu_yayini
import hedef
import kamera
import konumlama
import olcum
import parametreler
import rapor
import takip
import video
from kayit import Recorder
from px4_baglanti import FOLLOW_TARGET_MODE_NAME, HOLD_MODE_NAME, STOCK_MODE_NAMES, Vehicle, check_mode_name
from simulasyon import BUILD, SIM_DIR, Simulation, running

STALL_TIMEOUT = 15.0  # [s wall] sim time not advancing for this long = Gazebo is stuck
RTF_WARNING = rapor.RTF_WARNING  # below this mean real time factor the report warns: the model may take the CPU
RTF_SPAN = 5.0  # [s sim] pieces of the window for the lowest RTF
PROGRESS_EVERY = 10.0  # [s sim] the model's numbers in the log while recording
# PX4 must have logged the TEZ_LOS messages sent in the window (ULog debug_vect) within this share (tasks.md 5.7)
TEZ_LOS_ULOG_TOLERANCE = 0.05
LOCK_EVENTS_LISTED = 12  # lock events written into the report's events one by one
# follow_me: FOLLOW_TARGETs sent before PX4's logger is restarted, so that the follow_target topic exists (see
# simulasyon.restart_logger); ~0.3 s after the first one. The restart must be done before the window starts.
LOGGER_RESTART_AFTER = 3
TILT_TOLERANCE_DEG = 0.05  # [deg] the tilt Gazebo reports must be the scenario's (the copy writes 6 decimals of rad)
# PX4 mode (AVAILABLE_MODES name) of each tracking source; chosen by name, never by number (tez_los: takip.mod_adi)
TRACKING_MODES = {"yok": HOLD_MODE_NAME, "follow_me": FOLLOW_TARGET_MODE_NAME}


def log(text: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {text}", flush=True)


@dataclass
class ModeLog:
    """The PX4 mode of the run as the heartbeat reported it: when the scenario's mode was reached and every change
    after that ([(sim time [s], mode name)]); olcum.measure uses it when the ULog has no vehicle_status."""

    switched_s: float | None = None
    changes: list[tuple[float, str]] = field(default_factory=list)

    def switched(self, t: float, name: str) -> None:
        self.switched_s = t
        self.changes.append((t, name))

    def changed(self, t: float, name: str) -> None:
        self.changes.append((t, name))


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
    restart_logger: Callable[[], tuple[bool, str]] | None = None,
    modes: ModeLog | None = None,
    frames: goruntu_yayini.FrameRecorder | None = None,
) -> bool:
    """restart_logger: Simulation.restart_logger, called once in follow_me (the follow_target topics into the ULog);
    modes: filled with the mode the heartbeat reported; frames: the video's camera frames, kept while recording."""
    v = Vehicle()
    if tracker is not None:  # TEZ_LOS goes out from the moment the link to PX4 exists
        tracker.attach(v)
    recording = _Recording(rec, frames)
    try:
        return _fly(
            v, sc, recording, events, run_settings, model, detections, tracker, restart_logger, modes or ModeLog()
        )
    finally:
        if tracker is not None:
            tracker.detach()
        v.close()


class _Recording:
    """The referee's recording and the video's camera frames start and stop together (one window in sim time)."""

    def __init__(self, rec: Recorder, frames: goruntu_yayini.FrameRecorder | None) -> None:
        self.rec, self.frames = rec, frames

    @property
    def sim_time(self) -> float:
        return self.rec.sim_time

    def start(self) -> None:
        if self.frames is not None:
            self.frames.begin(self.rec.sim_time)
        self.rec.start()

    def stop(self) -> None:
        self.rec.stop()
        if self.frames is not None:
            self.frames.end(self.rec.sim_time)


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
    rec: "_Recording",
    events: list[str],
    run_settings: dict,
    model: algilama.ModelProcess | None,
    detections: algilama.DetectionLog | None,
    tracker: takip.Tracker | None,
    restart_logger: Callable[[], tuple[bool, str]] | None,
    modes: ModeLog,
) -> bool:
    if not check_start_params(v, run_settings["px4_parametreleri"], events):
        return False
    available = v.modes()  # name -> custom_mode of the modes PX4 offers now; the number is only ever taken from here
    run_settings["takip"]["px4_modlari"] = sorted(available)
    missing = sorted(set(STOCK_MODE_NAMES) - set(available))
    if missing:  # the list checked before the start differs from PX4's: the run goes on, PX4's list decides
        events.append(f"PX4'ün mod listesinde beklenen stok modlar yok: {', '.join(missing)}")
    name = run_settings["takip"]["mod"]
    if name not in available:
        events.append(
            f"'{name}' PX4'ün mod listesinde yok (takip.mod_adi / --mod-adi); PX4'ün seçilebilir modları: "
            f"{', '.join(sorted(available))}"
        )
        return False
    mode = available[name]
    names = {number: n for n, number in available.items()}
    log(f"Kalkış: {sc.altitude:.0f} m")
    if not v.takeoff(sc.altitude):
        events.append("Kalkış başarısız")
        return False
    if tracker is not None and not v.wait_references():  # home is valid once armed
        events.append("EKF kökeni (GPS_GLOBAL_ORIGIN) ya da ev noktası alınamadı: kutuların konumu hesaplanamaz")
    time.sleep(3)  # let the takeoff mode settle into its hover
    if not v.switch_mode(mode):
        events.append(f"'{name}' moduna geçilemedi")
        return False
    modes.switched(rec.sim_time, name)
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
    logger = _LoggerRestart(restart_logger if tracker is not None and tracker.follow else None, events)
    while rec.sim_time < sc.end_time:
        logger.poll(tracker, rec.sim_time, sc.start_time)
        current = v.current_mode(timeout=1.0)
        if current is not None and current != mode:
            events.append(f"{rec.sim_time:.1f} s: dron senaryo modundan çıktı")
            modes.changed(rec.sim_time, names.get(current, f"custom_mode {current:#x}"))
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
    if tracker is not None:  # like the Pi's model: the TEZ_LOS / FOLLOW_TARGET streams end with the recording
        tracker.close()
        sent = tracker.sender.counts["gonderildi"]
        follow = f", FOLLOW_TARGET {tracker.follow_sender.counts['gonderildi']}" if tracker.follow else ""
        log(f"TEZ_LOS akışı kapandı: {sent} mesaj gönderildi{follow}")
    log("Senaryo bitti, iniş")
    if not v.land():
        events.append("İniş/disarm tamamlanamadı")
    return True


class _LoggerRestart:
    """follow_me: restart PX4's logger once FOLLOW_TARGET flows (in its own thread: the main thread keeps reading
    MAVLink, the pose history must not stall), before the window starts."""

    def __init__(self, restart: Callable[[], tuple[bool, str]] | None, events: list[str]) -> None:
        self._restart, self._events = restart, events
        self._thread: threading.Thread | None = None
        self._gave_up = False

    def poll(self, tracker: takip.Tracker | None, now: float, window_start: float) -> None:
        if self._restart is None or self._thread is not None or self._gave_up:
            return
        if tracker.follow_sender.counts["gonderildi"] >= LOGGER_RESTART_AFTER:
            self._thread = threading.Thread(target=self._run, args=(now,), name="tez-logger", daemon=True)
            self._thread.start()
        elif now >= window_start - 1.0:
            self._gave_up = True
            self._events.append(
                "PX4 kaydedicisi yeniden başlatılmadı (kayıt penceresinden önce FOLLOW_TARGET gitmedi): ULog'da "
                "follow_target konuları yok"
            )

    def _run(self, now: float) -> None:
        ok, text = self._restart()
        log(f"PX4 kaydedicisi yeniden başlatıldı ({now:.1f} s): follow_target konuları ULog'a girsin diye")
        if not ok:
            self._events.append(f"PX4 kaydedicisi yeniden başlatılamadı: {text}")


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
        f"Model ölçütleri: hedef görünürken algılama %{100 * m['algilama_orani']:.0f} (IoU >= 0.5 kutu, "
        f"{m['iou05_kare_sayisi']}/{m['hedef_gorunur_islenen']} kare, IoU ort. {m['iou_ort']:.2f}), seçim doğru "
        f"%{100 * m['secim_dogru_orani']:.0f}, yanlış kişi %{100 * m['yanlis_kisi_orani']:.1f} (aynı kıyafet "
        f"%{100 * m['yanlis_kisi_ayni_kiyafet_orani']:.1f}), yanlış pozitif {m['yanlis_pozitif_kare_basi']:.2f}/kare"
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
            f"görünürken doğru kutu %{100 * m['secim_dogru_orani']:.0f}; LOS açı hatası (i)-(ii) ort. "
            f"{m['los_aci_hatasi_ort_deg']:.2f}°, p95 {m['los_aci_hatasi_p95_deg']:.2f}°, en çok "
            f"{m['los_aci_hatasi_maks_deg']:.2f}° ({m['los_aci_kare']} kare)"
        )


def _follow_log_lines(m: dict, follow: dict) -> None:
    if follow["etkin"]:
        log(
            f"FOLLOW_TARGET ({follow['kaynak']}): kayıt penceresinde {m['follow_target_gonderilen']} gönderildi "
            f"({m['follow_target_hizi_hz']:.1f} mesaj/sim-s), konumsuz kare {m['follow_target_konumsuz_kare']}; "
            f"gönderilen konumun hatası ort. {m['geolocation_hatasi_ort_m']:.2f} m (p95 "
            f"{m['geolocation_hatasi_p95_m']:.2f}, en çok {m['geolocation_hatasi_maks_m']:.2f}; gönderim anına göre "
            f"{m['geolocation_hatasi_gonderimde_ort_m']:.2f}); bütün koşuda {follow['sonuclar']}"
        )
        log(
            f"PX4: ULog'da {m['follow_target_px4_sayisi']} follow_target (kaydedici 500 ms'de bir); hedef "
            f"kestirimi gerçek konumdan ort. {m['px4_kestirim_hatasi_ort_m']:.2f} m (p95 "
            f"{m['px4_kestirim_hatasi_p95_m']:.2f}), bayat {m['px4_kestirim_bayat_s']:.1f} s; PX4 hedef rotasını "
            f"{m['px4_rota_kuzey_varsayimi_s']:.1f} s kuzey (0°) varsaydı, rota hatası ort. "
            f"{m['px4_rota_hatasi_ort_deg']:.0f}°"
        )
    if m.get("konum_hesaplanan"):
        log(
            f"Konum (model kutusu, düz zemin): kayıt penceresinde {m['konum_hesaplanan']} kare, durumlar "
            f"{m['konum_durumlari']}; kutu hedefken hata ort. {m['konum_hatasi_ort_m']:.2f} m (p95 "
            f"{m['konum_hatasi_p95_m']:.2f}, en çok {m['konum_hatasi_maks_m']:.2f}; {m['konum_kare']} kare), gerçek "
            f"pozla {m['konum_hatasi_gercek_pozla_ort_m']:.2f} m; EKF yaw hatası ort. "
            f"{m['ekf_yaw_hatasi_ort_deg']:+.2f}°, EKF yatay konum hatası ort. "
            f"{m['ekf_yatay_konum_hatasi_ort_m']:.2f} m"
        )


def _geometry_log_lines(m: dict, source: str, follow_distance: float | None) -> None:
    target = (
        f"; FLW_TGT_DST {follow_distance:g}, |mesafe - FLW_TGT_DST| ort. {m['yatay_mesafe_hatasi_ort_m']:.2f} m"
        if follow_distance is not None
        else ""
    )
    log(
        f"Takip ({source}): dron-hedef yatay mesafe ort. {m['yatay_mesafe_ort_m']:.2f} m (en az "
        f"{m['en_az_yatay_mesafe_m']:.2f} m, {m['en_az_yatay_mesafe_t_s']:.1f} s'de; en çok "
        f"{m['yatay_mesafe_max_m']:.2f})"
        + target
        + f"; 3 m altında {m['yakin_mesafe_3m_suresi_s']:.1f} s ({m['yakin_mesafe_3m_olay_sayisi']} kez); kameranın "
        f"yakın görüş sınırı {m['kadraj_yakin_sinir_m']:.1f} m, altında {m['kadraj_yakin_sinir_alti_s']:.1f} s; "
        f"hedefin tamamı kadrajda %{100 * m['hedef_kadrajda_orani']:.0f}, merkezi %{100 * m['kadrajda_kalma']:.0f}"
    )
    if source != "yok":
        log(
            f"Takip ({source}): arkada kalma açısı hatası ort. {m['arkada_kalma_hatasi_ort_deg']:.0f}° (p95 "
            f"{m['arkada_kalma_hatasi_p95_deg']:.0f}°, > 90° {m['arkada_kalma_hatasi_90_ustu_s']:.1f} s); hedef "
            f"dururken dron etrafında {m['baslangic_yorunge_donusu_deg']:.0f}° döndü, yürüyüşün ilk "
            f"{olcum.YURUYUS_BASI_S:.0f} s'sinde {m['yuruyus_basi_yorunge_donusu_deg']:.0f}°; istenen modda "
            f"%{100 * m['mod_korunma_orani']:.0f}"
        )


def _near_pass_log_lines(m: dict, sections: dict) -> None:
    """The < 6 m passes of the recording with their cause (olcum.near_passes) and the corners (olcum.corner_metrics)."""
    passes = sections.get("yakin_gecis", {}).get("olaylar", [])
    spans = "; ".join(
        f"{e['baslangic_s']:.1f}–{e['bitis_s']:.1f} s en az {e['en_az_m']:.2f} m "
        f"({rapor.NEAR_PASS_TEXT.get(e['sebep'], e['sebep'])})"
        for e in passes
    )
    log(
        f"Kayıtta {olcum.CLOSE_PASS_M:g} m'den yakın geçiş: {len(passes)} kez"
        + (f": {spans}" if spans else "")
        + f"; mesafe < 4 m %{100 * m['mesafe_4m_alti_orani']:.0f}, < 6 m %{100 * m['mesafe_6m_alti_orani']:.0f}, "
        f"6–10 m %{100 * m['mesafe_6_10m_orani']:.0f}, > 10 m %{100 * m['mesafe_10m_ustu_orani']:.0f}"
    )
    corners = sections.get("koseler", [])
    if corners:
        log(
            f"Köşeler ({len(corners)}): "
            + "; ".join(
                f"{c['baslangic_s']:.1f} s → {c['yon_deg']:.0f}°: PX4 yetişme {c['px4_yetisme_s']:.1f} s, arkada kalma "
                f"en çok {c['arkada_kalma_maks_deg']:.0f}°"
                for c in corners
            )
        )


def tracking_sections(tracker: takip.Tracker, m: dict, events: list[str]) -> tuple[dict, dict]:
    """ozet.json "tez_los" and "follow_target" (the whole run) and the events of the window's numbers (olcum.measure):
    the lock changes, a ULog count of TEZ_LOS off by more than TEZ_LOS_ULOG_TOLERANCE, no FOLLOW_TARGET at all."""
    sent = m["tez_los_gonderilen"]
    if not sent or abs(m["tez_los_px4_orani"] - 1.0) > TEZ_LOS_ULOG_TOLERANCE:
        events.append(
            f"TEZ_LOS: PX4'ün ULog'unda {m['tez_los_px4_sayisi']} kayıt, gönderilen {sent} (kayıt penceresi; "
            f"izin verilen fark %{100 * TEZ_LOS_ULOG_TOLERANCE:.0f})"
        )
    summary = tracker.summary()
    follow = summary.pop("follow_target")
    if follow["etkin"] and m["follow_target_gonderilen"] == 0:
        events.append("FOLLOW_TARGET: kayıt penceresinde hiç gönderilmedi (Follow Me'nin hedefi yok)")
    lock_events = summary["kilit"]["olaylar"]
    names = {"ilk_kilit": "ilk kilit", "yeniden_kilit": "yeniden kilit", "kilit_kaybi": "kilit kaybı"}
    for e in lock_events[:LOCK_EVENTS_LISTED]:
        detail = f"IoU {e['kilit_iou']:.2f}" if "kilit_iou" in e else f"{e['ardisik_kacirma']} karede eşleşme yok"
        events.append(f"{e['t']:.2f} s: {names[e['olay']]} (kilit {e['kilit_no']}, {detail})")
    if len(lock_events) > LOCK_EVENTS_LISTED:
        events.append(f"... {len(lock_events) - LOCK_EVENTS_LISTED} kilit olayı daha (ozet.json tez_los.kilit)")
    events += [f"Takip: {e}" for e in summary["hatalar"]]
    _tracking_log_lines(m, summary)
    _follow_log_lines(m, follow)
    return summary, follow


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
    world = konumlama.world_geo(hedef.SIM_DIR / "worlds" / f"{sc.world}.sdf")  # the drone's GPS comes from it
    mount = kamera.camera_to_body(math.radians(sc.camera.tilt_deg))  # C_cb of LOS (i) and the flat-ground position
    log(f"Kamera eğimi {sc.camera.tilt_deg:g}° (kamera.egim_deg; gerçek montaj {kamera.NOMINAL_TILT_DEG:g}°)")
    if t.los is not None:  # the tracking threads: selection, LOS, position, delay line, TEZ_LOS (+ FOLLOW_TARGET)
        tracker = takip.Tracker(
            t.los,
            clock,
            out,
            detections,
            lambda: rec.camera if rec is not None else None,
            sc.delay.extra_ms,
            follow=t.source == "follow_me",
            locator=konumlama.Locator(mount=mount) if model_file is not None else None,
            world=world,
            truth=lambda s: sc.truth(s)[:2],
            mount=mount,
        )
    model = None
    frames = None
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
        if sc.video.mp4:  # like the model: listening to the camera before Gazebo starts
            frames = goruntu_yayini.FrameRecorder(out / goruntu_yayini.FRAMES_DIR)
            frames.start()
            log(
                f"Video kare kaydedicisi hazır: kayıt boyunca {goruntu_yayini.FPS} kare/sim-s, "
                f"{goruntu_yayini.FRAME_SIZE[0]}x{goruntu_yayini.FRAME_SIZE[1]} JPEG -> {goruntu_yayini.FRAMES_DIR}/"
            )
        shutil.copy(sc.source, out / "senaryo.yaml")
        check_pos = dogrulama.camera_pose(sc) if verify else None
        world_file = hedef.write_world(sc, out, dogrulama.camera_sdf(check_pos) if verify else "")
        tilted = hedef.camera_model(sc, out)
        run_settings["kamera"]["gazebo_modeli"] = str(tilted / "model.sdf") if tilted else "models/x500_tez/model.sdf"
        rec = Recorder(sc, sc.world, tracker.on_referee if tracker is not None else None)
        check = dogrulama.OverheadCheck(sc, check_pos) if verify else None
    except BaseException:
        if model is not None:  # never leave the model process behind
            model.stop()
        if frames is not None:
            frames.stop()
        if tracker is not None:
            tracker.close()
        if detections is not None:
            detections.close()
        raise
    # scenario's takip.px4_parametreleri, then --param: calistir.sh loads them after the .params files
    sim = Simulation(out, world_file, headless, params={p.name: p.value for p in t.px4_params})
    completed = False
    modes = ModeLog()
    try:
        with sim:
            if not sim.wait_ready():
                events.append("Simülasyon açılmadı (sim.log'a bakın)")
            else:
                log("PX4 ve Gazebo hazır")
                completed = fly(
                    sc, rec, events, run_settings, model, detections, tracker, sim.restart_logger, modes, frames
                )
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
        video_books = frames.stop() if frames is not None else None
    events += sim.problems()
    if video_books is not None:
        _frame_log_line(video_books, events)

    ulogs = sim.ulogs()
    ulog = ulogs[-1] if ulogs else None
    if ulog is not None:
        shutil.copy(ulog, out / "ucus.ulg")
    copies = []
    for i, earlier in enumerate(ulogs[:-1]):  # follow_me: before PX4's logger was restarted
        copies.append(out / ("ucus_once.ulg" if i == len(ulogs) - 2 else f"ucus_once_{i}.ulg"))
        shutil.copy(earlier, copies[-1])
    if ulog is not None:
        copies.append(out / "ucus.ulg")
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
    gazebo_tilt = kamera.tilt_of_mount(rec.camera_dcm) if rec.camera_dcm is not None else math.nan
    if not abs(gazebo_tilt - sc.camera.tilt_deg) <= TILT_TOLERANCE_DEG:
        events.append(
            f"Kamera eğimi: Gazebo'daki model {gazebo_tilt:.2f}°, senaryo {sc.camera.tilt_deg:g}° (en çok "
            f"{TILT_TOLERANCE_DEG}° fark olabilir); ölçütler senaryonun eğimiyle hesaplandı"
        )
        completed = False
    distance = run_settings["px4_parametreleri"].get("FLW_TGT_DST", {}).get("px4") if t.source == "follow_me" else None
    data = olcum.RunData(
        start=sc.start_time,
        end=sc.end_time,
        referee=rows,
        source=t.source,
        detections=detections.rows if detections is not None else (),
        boxes=detections.boxes if detections is not None else {},
        skipped=detections.skipped if detections is not None else (),
        attempts=tracker.attempts if tracker is not None else (),
        follow_attempts=tracker.follow_attempts if tracker is not None else (),
        lock_events=tracker.events if tracker is not None else (),
        camera=rec.camera,
        mount=(rec.camera_offset, rec.camera_dcm),
        world=world,
        origin=tracker.poses.origin if tracker is not None and tracker.poses is not None else None,
        truth=sc.truth,
        others=len(sc.others),
        same_clothes=frozenset(i for i, o in enumerate(sc.others, start=1) if o.clothes == sc.clothes),
        ulogs=tuple(copies),
        mode_name=run_settings["takip"]["mod"],
        mode_switched_s=modes.switched_s,
        mode_changes=tuple(modes.changes),
        follow_distance=distance,
        camera_tilt_deg=sc.camera.tilt_deg,
    )
    measured, sections = olcum.measure(data)
    more |= measured
    if sections.get("ulog_hatasi"):
        events.append(f"ULog okunamadı: {sections['ulog_hatasi']}")
    if tracker is not None:
        sections["tez_los"], sections["follow_target"] = tracking_sections(tracker, more, events)
        sections["tez_los"]["hakem_eksik_kare"] = rec.join_dropped
        events += [f"Hakem akışı: {e}" for e in rec.errors]
        completed &= not sections["tez_los"]["hatalar"] and not rec.errors  # a broken TEZ_LOS stream is no result
    if model is not None:
        sections["kare_defteri"] = frame_books(model, detections, events)
        events += [f"Model süreci: {e}" for e in model.errors]
        completed &= not model.errors
        if more["islenen"] == 0:
            events.append("Kayıt penceresinde işlenmiş kare yok: model ölçütleri hesaplanamadı")
        else:
            _detection_log_lines(more)
    if rows:
        _geometry_log_lines(more | rapor.metrics(sc, pd.DataFrame(rows)), t.source, distance)
        _near_pass_log_lines(more, sections)
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
            "egim_deg": gazebo_tilt if math.isfinite(gazebo_tilt) else None,
        },
        (out / "ucus.ulg") if ulog else None,
        run_settings,
        more,
        sections,
        video=_video_maker(video_books, sc.video.keep_frames) if frames is not None else None,
    )


def _frame_log_line(books: dict, events: list[str]) -> None:
    """What the video's recorder kept; a dropped frame is shown as the one before in kosu.mp4."""
    if "hata" in books:
        events.append(f"Video kare kaydedicisi: {books['hata']}")
        log(f"UYARI: video kare kaydedicisi: {books['hata']}")
        return
    log(
        f"Video kareleri: {books['yazilan']} yazıldı ({books['secilen']} seçildi, {books['dusen']} kuyruk dolu "
        f"olduğu için düştü, {books['hatali']} hatalı; kameradan {books['kamera_karesi']} kare geldi), kare başına "
        f"ort. {books['yazma_ms_ort']:.1f} ms (en çok {books['yazma_ms_maks']:.0f})"
    )
    if books["dusen"] or books["hatali"]:
        events.append(
            f"Video kareleri: {books['dusen']} kare düştü, {books['hatali']} hatalı (videoda önceki kare gösterilir)"
        )
    events += [f"Video kare kaydedicisi: {e}" for e in books.get("hatalar", [])]


def _video_maker(books: dict | None, keep_frames: bool) -> Callable[[Path], dict]:
    def make(folder: Path) -> dict:
        log("Video birleştiriliyor (kosu.mp4, çevrimdışı)...")
        info = video.make(folder, books, keep_frames)
        if "hata" not in info:
            log(
                f"Video: {folder / info['dosya']} ({info['kare_sayisi']} kare, {info['sure_s']:.1f} s; kamera karesi "
                f"olmayan an {info['eksik_kare']}; {info['uretim_s']:.0f} s'de; kareler {info['kareler']})"
            )
        return info

    return make


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
    g = ap.add_argument_group("kamera (senaryodaki kamera bloğunu ezer)")
    g.add_argument(
        "--kamera-egim",
        type=float,
        metavar="DERECE",
        help=f"kameranın burnun altındaki eğimi (kamera.egim_deg); varsayılan montaj {kamera.NOMINAL_TILT_DEG:g}",
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
        camera_tilt_deg=args.kamera_egim,
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
