#!/usr/bin/env python3
"""m06 acceptance test of the thesis simulation (tez/sim/araclar/m06_kabul.sh runs it; spec 2026-11-10-m06-sim-ortami
"Test Planı"), ~8-10 minutes, no window.

Runs, each one its own senaryo.py process without a window (toplu.command), into <çıktı>/kosu<i>_<scenario>/:
  1. takip_yuruyen: the model's boxes, PX4's stock Follow Me closes the loop (--takip follow_me --los model)
  2. kalabalik_park: the model's boxes, the drone waits in Hold (--takip yok --los model)
  3. only with --mod-adi: takip_yuruyen into that PX4 mode, chosen by name, with TEZ_LOS from the model (--takip
     tez_los), after the --px4-baslat commands; e.g. m15's module built in with tez/sim/derle.sh --harici <folder>
and checks the seven conditions of the spec, one OK / HATA line each. They say that the chain works; they are no
performance thresholds:
  1. tez/pin/verify_pin.sh --worktree passes (once); in every run PX4 holds each start parameter (read back over
     MAVLink before the takeoff: ozet.json "ayarlar.px4_parametreleri"), every line of the two .params files is one
     of them and the ULog says SYS_AUTOSTART 4001 (the F0 checks)
  2. the model loaded and its sha256 is written; in at least one processed frame a box has IoU >= 0.5 with the target
  3. the ULog has debug_vect "TEZ_LOS", as many as were sent in the window within ±5 %
  4. the drone switched to the run's mode by name and kept it through the recording (vehicle_status in the ULog);
     follow_me: the ULog has follow_target
  5. ffprobe reads kosu.mp4: h264, yuv420p, 2000x720, duration within ±1 s of the recording (olcutler.kayit_suresi_s)
  6. ozet.json has every key of spec "Ölçüt Tanımları" (olcum.KEYS; null where it does not apply), rapor.html exists
  7. clean shutdown (no PX4 / Gazebo left); with --px4-baslat no "unresponsive" in sim.log (ozet.json "harici_mod")
A run that did not complete (TAMAMLANMADI, or no ozet.json) fails as well; KALDI would only come from a scenario's
"basari" thresholds, which are not m06 conditions.

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/m06_testi.py [--cikti KLASÖR]
    ... --mod-adi "AUTO FOLLOW" --px4-baslat "<module> start"     the optional third run

Outputs: tez/sim/sonuclar/<date>_m06_kabul/ (or --cikti): kosu<i>_<scenario>/ (senaryo.py's run folder: kosu.mp4,
rapor.html, ozet.json, ucus.ulg, sim.log, CSV files) and kosu<i>_<scenario>.log (senaryo.py's output).
Exit code 0 = passed, 1 = failed, 2 = refused before anything started.
"""

import argparse
import datetime as dt
import json
import math
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import olcum
import parametreler
import toplu
import video
from px4_baglanti import FOLLOW_TARGET_MODE_NAME, HOLD_MODE_NAME
from rapor import MODE_KEPT
from senaryo import TEZ_LOS_ULOG_TOLERANCE
from simulasyon import LEFT_RUNNING, REPO, SIM_DIR, running

AIRFRAME = 4001  # stock 4001_gz_x500 (calistir.sh PX4_SYS_AUTOSTART), as f0_testi.AIRFRAME
PIN_CHECK = REPO / "tez" / "pin" / "verify_pin.sh"
PIN_OK = "KILIT SAGLAM"
VIDEO_CODEC = "h264"
VIDEO_PIX_FMT = "yuv420p"
VIDEO_DURATION_TOLERANCE_S = 1.0  # [s] kosu.mp4 against the referee's recording (spec, condition 5)
HEX_DIGITS = set("0123456789abcdef")
ANSI = re.compile(r"\x1b\[[0-9;]*m")  # verify_pin.sh colours its OK / HATA

Check = tuple[str, bool, str]
results: list[Check] = []


@dataclass(frozen=True)
class Run:
    number: int
    scenario: str
    source: str  # takip.kaynak the run flies with
    mode: str  # AVAILABLE_MODES name of the mode PX4 must fly
    flags: tuple[str, ...]  # senaryo.py flags after --senaryo / --ekransiz / --cikti

    @property
    def name(self) -> str:
        return f"kosu{self.number}_{self.scenario}"

    @property
    def label(self) -> str:
        return f"koşu {self.number} ({self.scenario}, {self.source})"

    @property
    def external(self) -> bool:
        """Started with --px4-baslat: the run is looked at for "unresponsive" (an out-of-tree mode)."""
        return "--px4-baslat" in self.flags


def plan(mode_name: str | None = None, px4_start: Sequence[str] = ()) -> list[Run]:
    """The runs of the acceptance test: the two fixed ones, the third only with a mode name."""
    runs = [
        Run(1, "takip_yuruyen", "follow_me", FOLLOW_TARGET_MODE_NAME, ("--takip", "follow_me", "--los", "model")),
        Run(2, "kalabalik_park", "yok", HOLD_MODE_NAME, ("--takip", "yok", "--los", "model")),
    ]
    if mode_name is not None:
        flags = ["--takip", "tez_los", "--mod-adi", mode_name, "--los", "model"]
        for text in px4_start:
            flags += ["--px4-baslat", text]
        runs.append(Run(3, "takip_yuruyen", "tez_los", mode_name, tuple(flags)))
    return runs


def log(text: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {text}", flush=True)


def report(name: str, ok: bool, detail: str) -> bool:
    results.append((name, ok, detail))
    print(f"{'OK  ' if ok else 'HATA'} {name}: {detail}", flush=True)
    return ok


def _number(value: object) -> float | None:
    """A value of ozet.json as a float; None for null, NaN and anything that is not a number."""
    if isinstance(value, bool) or not isinstance(value, int | float) or math.isnan(value):
        return None
    return float(value)


# --- condition 1: the lock and the start parameters ---------------------------------------------------------------


def pin_check() -> tuple[bool, str]:
    """tez/pin/verify_pin.sh --worktree: PX4 v1.17.0, no PX4 file changed, every submodule at its locked commit."""
    try:
        done = subprocess.run(
            [str(PIN_CHECK), "--worktree"], capture_output=True, text=True, timeout=120, check=False, cwd=REPO
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"{PIN_CHECK.name} çalışmadı: {e}"
    lines = [ANSI.sub("", line).strip() for line in (done.stdout + done.stderr).splitlines() if line.strip()]
    last = lines[-1] if lines else "çıktı yok"
    if done.returncode == 0 and PIN_OK in last:
        return True, last
    wrong = [line for line in lines if line.startswith("HATA")]
    return False, f"{last} (çıkış {done.returncode}); " + "; ".join(wrong[:3])


def ulog_parameter(path: Path, name: str) -> tuple[float | None, str | None]:
    """A parameter's value in the header of a ULog -> (value, None) or (None, why not)."""
    if not path.is_file():
        return None, f"{path.name} yok"
    try:
        from pyulog import ULog

        value = ULog(str(path), [], parse_header_only=True).initial_parameters.get(name)
    except Exception as e:  # noqa: BLE001 - the check reports it instead of stopping the test
        return None, f"{path.name} okunamadı: {type(e).__name__}: {e}"
    return (value, None) if value is not None else (None, f"{path.name}'de {name} yok")


def param_check(summary: Mapping, autostart: float | None, files: Mapping[str, parametreler.Param]) -> tuple[bool, str]:
    """Every start parameter of the run holds its value in PX4, the .params files are all among them, 4001 runs."""
    params = summary.get("ayarlar", {}).get("px4_parametreleri") or {}
    wrong = []
    for name, entry in params.items():
        wanted, got = _number(entry.get("deger")), _number(entry.get("px4"))
        if wanted is None or not parametreler.matches(wanted, got):
            wrong.append(f"{name} PX4'te {entry.get('px4')}, istenen {entry.get('deger')} ({entry.get('kaynak')})")
    missing = [name for name in files if name not in params]
    airframe_ok = autostart is not None and int(autostart) == AIRFRAME
    detail = (
        f"{len(params) - len(wrong)}/{len(params)} başlangıç parametresi PX4'te istenen değerde (kalkıştan önce "
        f"PARAM_REQUEST_READ); dosyalardaki {len(files) - len(missing)}/{len(files)} parametre yüklendi; ULog'da "
        f"SYS_AUTOSTART {autostart if autostart is None else int(autostart)} (beklenen {AIRFRAME})"
    )
    if wrong:
        detail += "; farklı: " + "; ".join(wrong[:5])
    if missing:
        detail += "; yüklenmeyen: " + ", ".join(missing)
    return bool(params) and not wrong and not missing and airframe_ok, detail


# --- condition 2: the model ---------------------------------------------------------------------------------------


def model_check(summary: Mapping) -> tuple[bool, str]:
    """The model loaded (its own answer is in ayarlar.algilama.model_bilgisi), its sha256 is written, and in at least
    one processed frame one of its boxes has IoU >= 0.5 with the target's referee box."""
    detection = summary.get("ayarlar", {}).get("algilama", {})
    file = detection.get("model_dosyasi") or {}
    digest = file.get("sha256")
    digest_ok = isinstance(digest, str) and len(digest) == 64 and set(digest) <= HEX_DIGITS
    loaded = bool(detection.get("model_bilgisi"))
    m = summary.get("olcutler") or {}
    found = _number(m.get("iou05_kare_sayisi")) or 0.0
    seen = _number(m.get("hedef_gorunur_islenen")) or 0.0
    best = _number(m.get("iou_max"))
    known = f"modeller.yaml'da {file['kayitli']}" if file.get("kayitli") else "modeller.yaml'da kayıtlı değil"
    if file.get("uyari"):
        known += f"; UYARI: {file['uyari']}"
    detail = (
        f"{Path(str(file.get('yol', '?'))).name} {'yüklendi' if loaded else 'yüklenmedi'}, sha256 {digest} ({known}); "
        f"hedefin göründüğü {seen:.0f} işlenmiş karenin {found:.0f} tanesinde bir model kutusu hedefle IoU ≥ "
        f"{olcum.IOU_MATCH} (en iyi {'–' if best is None else f'{best:.2f}'})"
    )
    return loaded and digest_ok and found >= 1, detail


# --- condition 3: TEZ_LOS in the ULog -----------------------------------------------------------------------------


def tez_los_count(
    sent: float | None, logged: float | None, tolerance: float = TEZ_LOS_ULOG_TOLERANCE
) -> tuple[bool, str]:
    """PX4 logged (ULog debug_vect "TEZ_LOS") as many messages as were sent in the window, within ±tolerance of the
    sent count; nothing sent or nothing logged fails."""
    sent, logged = _number(sent), _number(logged)
    if not sent:
        return False, "kayıt penceresinde hiç TEZ_LOS gönderilmedi"
    if not logged:
        return False, f"{sent:.0f} gönderildi, ULog'da TEZ_LOS adlı debug_vect yok"
    diff = logged - sent
    detail = (
        f"ULog'da {logged:.0f}, gönderilen {sent:.0f} (fark {diff:+.0f}, %{100 * diff / sent:+.1f}; sınır "
        f"±%{100 * tolerance:g})"
    )
    return abs(diff) <= tolerance * sent, detail


def tez_los_check(summary: Mapping) -> tuple[bool, str]:
    m = summary.get("olcutler") or {}
    return tez_los_count(m.get("tez_los_gonderilen"), m.get("tez_los_px4_sayisi"))


# --- condition 4: the mode ----------------------------------------------------------------------------------------


def mode_check(run: Run, summary: Mapping) -> tuple[bool, str]:
    """The heartbeat showed the run's mode (chosen by name) and the ULog's vehicle_status kept it through the
    recording; follow_me: PX4 logged follow_target (after the logger restart, senaryo.py)."""
    mode = summary.get("mod") or {}
    m = summary.get("olcutler") or {}
    switched_s = _number(mode.get("secildi_s"))
    switched = mode.get("istenen") == run.mode and switched_s is not None
    kept = _number(m.get("mod_korunma_orani"))
    kept_ok = kept is not None and kept >= MODE_KEPT
    if switched:
        detail = f"'{run.mode}' {switched_s:.1f} s'de adıyla seçildi"
    else:
        detail = f"'{run.mode}' seçilmedi (ozet.json mod: {mode.get('istenen')}, {mode.get('secildi_s')})"
    detail += (
        f"; kayıt penceresinin %{100 * kept:.1f}'i bu modda (kaynak: {mode.get('korunma_kaynagi')})"
        if kept is not None
        else "; modda kalma ölçülemedi"
    )
    ok = switched and kept_ok
    if run.source == "follow_me":
        follow = _number(m.get("follow_target_px4_sayisi")) or 0.0
        ok &= follow > 0
        detail += f"; ULog'da follow_target {follow:.0f} kayıt"
    return ok, detail


# --- condition 5: the video ---------------------------------------------------------------------------------------


def probe_video(path: Path) -> dict | str:
    """ffprobe's view of the video's first stream and its duration, or why it cannot be read."""
    if not path.is_file():
        return f"{path.name} yok"
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,pix_fmt,width,height,nb_frames:format=duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"ffprobe çalışmadı: {type(e).__name__}: {e}"
    if done.returncode != 0:
        return f"ffprobe okuyamadı (çıkış {done.returncode}): {done.stderr.strip()[:200]}"
    try:
        data = json.loads(done.stdout)
        streams = data.get("streams") or []
        duration = _number(float(data.get("format", {}).get("duration", "nan")))
    except (ValueError, AttributeError) as e:
        return f"ffprobe'un çıktısı okunamadı: {type(e).__name__}: {e}"
    if not streams:
        return "videoda görüntü akışı yok"
    s = streams[0]
    return {
        "codec": s.get("codec_name"),
        "pix_fmt": s.get("pix_fmt"),
        "size": (s.get("width"), s.get("height")),
        "frames": s.get("nb_frames"),
        "duration_s": duration,
    }


def video_check(probe: dict | str, recording_s: float | None) -> tuple[bool, str]:
    """kosu.mp4 is H.264 / yuv420p / 2000x720 and as long as the referee's recording (±1 s)."""
    if isinstance(probe, str):
        return False, probe
    recording_s, duration = _number(recording_s), probe["duration_s"]
    form_ok = (probe["codec"], probe["pix_fmt"], tuple(probe["size"])) == (VIDEO_CODEC, VIDEO_PIX_FMT, video.SIZE)
    length_ok = (
        recording_s is not None and duration is not None and abs(duration - recording_s) <= VIDEO_DURATION_TOLERANCE_S
    )
    width, height = probe["size"]
    detail = (
        f"{probe['codec']}, {probe['pix_fmt']}, {width}×{height}, {probe['frames']} kare, "
        f"{'?' if duration is None else f'{duration:.2f}'} s; kayıt penceresi "
        f"{'?' if recording_s is None else f'{recording_s:.2f}'} s (beklenen {VIDEO_CODEC}, {VIDEO_PIX_FMT}, "
        f"{video.SIZE[0]}×{video.SIZE[1]}, ±{VIDEO_DURATION_TOLERANCE_S:g} s)"
    )
    return form_ok and length_ok, detail


# --- condition 6: the keys of ozet.json ---------------------------------------------------------------------------


def missing_keys(summary: Mapping) -> list[str]:
    """Keys of spec "Ölçüt Tanımları" (olcum.KEYS) that ozet.json "olcutler" lacks, in the spec's order."""
    metrics = summary.get("olcutler")
    if not isinstance(metrics, Mapping):
        return list(olcum.KEYS)
    return [key for key in olcum.KEYS if key not in metrics]


def keys_check(summary: Mapping, report_file: Path) -> tuple[bool, str]:
    """Every key is there (its value may be null: NaN, the metric does not apply to the run) and rapor.html exists."""
    missing = missing_keys(summary)
    metrics = summary.get("olcutler") if isinstance(summary.get("olcutler"), Mapping) else {}
    nulls = sum(1 for key in olcum.KEYS if key in metrics and metrics[key] is None)
    has_report = report_file.is_file() and report_file.stat().st_size > 0
    detail = f"{len(olcum.KEYS) - len(missing)}/{len(olcum.KEYS)} ölçüt anahtarı var ({nulls} tanesi null)"
    if missing:
        detail += f"; eksik: {', '.join(missing[:10])}" + (f" … ({len(missing)} eksik)" if len(missing) > 10 else "")
    detail += f"; {report_file.name} {'yazıldı' if has_report else 'yok'}"
    return not missing and has_report, detail


# --- condition 7: the shutdown ------------------------------------------------------------------------------------


def shutdown_check(run: Run, summary: Mapping, left_running: bool) -> tuple[bool, str]:
    """No PX4 / Gazebo left after the run (senaryo.py's own check and one more look after it ended); a run with
    --px4-baslat: the commander never flagged the mode "unresponsive" (ozet.json "harici_mod")."""
    events = summary.get("olaylar") or []
    left = left_running or any(str(e).startswith(LEFT_RUNNING) for e in events)
    ok = not left
    detail = "PX4 ve Gazebo kapandı" if not left else "kapanıştan sonra çalışan PX4/Gazebo süreci kaldı"
    if not run.external:
        return ok, detail + "; harici mod yok ('unresponsive' aranmaz)"
    external = summary.get("harici_mod")
    if not isinstance(external, Mapping):
        return False, detail + "; ozet.json'da harici_mod yok"
    lines = external.get("unresponsive") or []
    starts = ", ".join(f"'{s.get('komut')}' çıkış {s.get('cikis_kodu')}" for s in external.get("baslatma") or [])
    detail += f"; sim.log'da 'unresponsive' {len(lines)} satır" + (f" (ilki: {lines[0]})" if lines else "")
    detail += f"; başlatma: {starts or 'yok'}"
    return ok and not lines, detail


def completed_check(summary: Mapping | None, code: int) -> tuple[bool, str]:
    """The run wrote its ozet.json and did not end TAMAMLANMADI."""
    if summary is None:
        why = "; senaryo.py ayarı reddetti, simülasyon açılmadı" if code == 2 else ""
        return False, f"ozet.json yazılmadı (senaryo.py çıkış kodu {code}{why})"
    result = summary.get("sonuc")
    detail = f"senaryo.py sonucu {result} (çıkış kodu {code})"
    if result == "TAMAMLANMADI":
        detail += "; olaylar: " + " | ".join(str(e) for e in (summary.get("olaylar") or [])[:3])
    return result != "TAMAMLANMADI", detail


# --- the runs -----------------------------------------------------------------------------------------------------


def fly(run: Run, out: Path) -> tuple[dict | None, int]:
    """senaryo.py for the run, its output on the console and in <out>/<run>.log -> (its ozet.json, exit code)."""
    folder = out / run.name
    command = toplu.command(run.scenario, folder, run.flags)
    log(f"=== {run.label}: senaryo.py {' '.join(command[2:])}")
    with (out / f"{run.name}.log").open("w", encoding="utf-8") as f:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as proc:
            for line in proc.stdout:
                sys.stdout.write(line)
                f.write(line)
            code = proc.wait()
    sys.stdout.flush()
    return toplu.read_summary(folder), code


def check_run(run: Run, folder: Path, summary: dict | None, code: int, files: Mapping[str, parametreler.Param]) -> None:
    """The seven conditions of one run (condition 1's lock check is done once, before the runs)."""
    left_running = running()  # senaryo.py waited for the shutdown itself; anything still here is left over
    if not report(f"{run.label}: koşu tamamlandı", *completed_check(summary, code)) and summary is None:
        return
    autostart, why = ulog_parameter(folder / "ucus.ulg", "SYS_AUTOSTART")
    ok, detail = param_check(summary, autostart, files)
    report(f"{run.label}: 1. parametreler", ok, detail + (f" ({why})" if why else ""))
    report(f"{run.label}: 2. model", *model_check(summary))
    report(f"{run.label}: 3. TEZ_LOS ULog'da", *tez_los_check(summary))
    report(f"{run.label}: 4. mod", *mode_check(run, summary))
    recording_s = (summary.get("olcutler") or {}).get("kayit_suresi_s")
    report(f"{run.label}: 5. video", *video_check(probe_video(folder / video.VIDEO_NAME), recording_s))
    report(f"{run.label}: 6. ozet.json ve rapor", *keys_check(summary, folder / "rapor.html"))
    report(f"{run.label}: 7. temiz kapanış", *shutdown_check(run, summary, left_running))


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cikti", type=Path, help="çıktı klasörü (varsayılan tez/sim/sonuclar/<tarih>_m06_kabul)")
    ap.add_argument("--mod-adi", metavar="AD", help="isteğe bağlı 3. koşu: tez_los ile seçilecek PX4 modunun adı")
    ap.add_argument(
        "--px4-baslat",
        action="append",
        default=[],
        metavar="KOMUT",
        help="3. koşuda PX4 açıldıktan sonra çalışacak komut (birden çok; --mod-adi ile)",
    )
    return ap


def main() -> int:
    args = parser().parse_args()
    if args.px4_baslat and args.mod_adi is None:
        print("--px4-baslat yalnız 3. koşu içindir: --mod-adi ile birlikte verin", file=sys.stderr)
        return 2
    out = (args.cikti or SIM_DIR / "sonuclar" / f"{dt.datetime.now():%Y%m%d_%H%M%S}_m06_kabul").resolve()
    if out.exists() and any(out.iterdir()):
        print(f"Çıktı klasörü boş değil: {out}; başka bir --cikti verin (eski koşularla karışmasın)", file=sys.stderr)
        return 2
    if running():
        print("Zaten çalışan bir PX4 veya Gazebo var; önce onu kapatın (ya da bitmesini bekleyin)", file=sys.stderr)
        return 2
    try:
        files = parametreler.load()  # the .params files calistir.sh loads in every run
    except (OSError, ValueError) as e:
        print(f"Parametre dosyası hatası: {e}", file=sys.stderr)
        return 2
    runs = plan(args.mod_adi, args.px4_baslat)
    out.mkdir(parents=True, exist_ok=True)
    log(f"m06 kabul testi: {len(runs)} koşu -> {out}")
    report("1. kilit (verify_pin.sh --worktree)", *pin_check())

    for run in runs:
        if not toplu.wait_until_closed():
            report(f"{run.label}: başlatılamadı", False, "önceki koşudan kalan PX4/Gazebo 120 s'de kapanmadı")
            break
        summary, code = fly(run, out)
        log(f"=== {run.label}: kontroller")
        check_run(run, out / run.name, summary, code, files)

    print("\n=== m06 kabul testi: özet ===")
    for name, ok, detail in results:
        print(f"{'OK  ' if ok else 'HATA'} {name}: {detail}")
    print(f"Çıktılar: {out} (" + ", ".join(f"{r.name}/" for r in runs) + "; her birinde kosu.mp4, rapor.html)")
    failed = [name for name, ok, _ in results if not ok]
    print("\nSONUÇ:", "GEÇTİ" if not failed else f"KALDI ({', '.join(failed)})", flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
