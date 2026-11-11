"""Tracking side of the simulation: which box is the target, its line of sight and the TEZ_LOS stream to PX4.

Spec 2026-11-10-m06-sim-ortami, 5. All of it is temporary: m11 brings the real target selection and invalid-data
handling, m10 the real pixel -> body transform, m05 the interface (TEZ_LOS is an assumption, spec "Varsayımlar" 1).

Selection (Selection.step, once per processed model frame):
  - no lock: the referee stands in for the operator who picks the target on the ground station: the box with the
    highest IoU with the target's referee box locks (target visible, IoU at least LOCK_MIN_IOU).
  - locked: the box whose centre is nearest to the previous choice, at most GATE_FACTOR x the previous box's diagonal
    away; the referee is not asked. LOST_AFTER processed frames in a row without such a box drop the lock, and the
    next processed frame tries the referee again (re-lock, counted).

Line of sight, from the camera to the target in body FRD (x nose, y right, z down), unit vectors:
  (i)  model: the chosen box's centre -> Camera.pixel_to_los (camera_info, distortion) -> camera_to_body(45 deg).
       The nominal mount, like the Pi would use its measured one, not the mount Gazebo reports: a mount error can be
       put in on purpose later.
  (ii) hakem: the referee's los_govde of the frame while the target is visible, NaN while it is not; every camera
       frame (30 Hz), once the referee's row and segmentation frame are both in (that delay is measured too).

Tracker: model results come in ModelProcess' result thread (on_model), the referee's frames from a gz-transport
thread (on_referee -> its own thread). The chosen source's messages go: DelayLine (gecikme.py) -> LosSender (one per
frame, NaN = no target, never an invalid vector; px4_baglanti.py) -> Vehicle.send_los. A model frame becomes an
algilama.csv row once its TEZ_LOS went out (or was refused); every TEZ_LOS attempt is a tez_los.csv row.
"""

import csv
import math
import queue
import statistics
import threading
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import algilama
import gecikme
import goruntu
import kamera
import px4_baglanti
from algilama import Kutu

GATE_FACTOR = 1.5  # spec 5: centre distance at most 1.5 x the previous box's diagonal
LOST_AFTER = 10  # spec 5: processed frames in a row without a match drop the lock
# A box locks on the target only if it overlaps the referee's box at least this much: the IoU at which the metrics say
# a box belongs to a person at all (spec "Ölçüt Tanımları": yanlış kişi / yanlış pozitif, 0.3). Without it a box far
# off would lock with an IoU of 0.01, where an operator would not have clicked.
LOCK_MIN_IOU = 0.3
MOUNT_PITCH_DOWN = math.radians(
    45.0
)  # nominal camera mount (spec "Kamera parametreleri"; the Pi uses its measured one)
NOMINAL_MOUNT = kamera.camera_to_body(MOUNT_PITCH_DOWN)  # C_cb, optical -> body FRD
REFEREE_KEEP_S = 3.0  # [s sim] referee frames kept for the lock of a model frame (a model result is ~0.15 s late)
MATCH_IOU = algilama.IOU_MATCH  # the chosen box is the target (spec "Ölçüt Tanımları": seçim doğru)
SOURCES = ("model", "hakem")


@dataclass(frozen=True)
class Referee:
    """What the referee knows about the target in one camera frame."""

    t: float  # [s sim] capture
    box: tuple[float, float, float, float]  # its visible pixels' box, pixel edges (NaN when nothing is visible)
    visible: bool  # enough of it is not hidden (kayit.VISIBLE_PX)
    los_body: tuple[float, float, float]  # los_govde: camera -> body centre, body FRD, unit
    ready: float  # [s monotonic] row and segmentation frame were both in

    @classmethod
    def from_row(cls, row: dict, ready: float) -> "Referee":
        box = tuple(float(row.get(f"hedef_kutu_{k}", math.nan)) for k in ("u0", "v0", "u1", "v1"))
        los = tuple(float(row[f"los_govde_{k}"]) for k in "xyz")
        return cls(float(row["t"]), box, bool(row.get("gorunur")), los, ready)


@dataclass(frozen=True)
class Choice:
    """The selection's answer for one processed frame."""

    state: str  # ilk_kilit | yeniden_kilit | izleme | eslesmedi | kilit_kaybi | kilitsiz
    box: Kutu | None = None
    index: int | None = None  # in the frame's box list (kutular.csv "kutu")
    lock_no: int = 0  # 1 = the run's first lock; 0 = not locked in this frame
    misses: int = 0  # processed frames in a row without a match while locked
    reason: str = ""  # kilitsiz: hakem_yok | hedef_gorunmuyor | kutu_eslesmedi
    lock_iou: float = math.nan  # IoU of the locking box with the referee's box
    gate: tuple[float, float, float] | None = None  # (u, v) centre and radius [px] of the gate while locked
    distance: float = math.nan  # [px] centre of the nearest box to the gate centre


def box_centre(box: Kutu) -> tuple[float, float]:
    """Centre of a pixel-edge box [px]. Continuous image coordinates: pixel u covers [u, u + 1), as in
    Camera.project (Gazebo's principal point W/2 = 1152 is the edge between the two middle pixels)."""
    return (box.u0 + box.u1) / 2.0, (box.v0 + box.v1) / 2.0


def box_diagonal(box: Kutu) -> float:
    return math.hypot(box.u1 - box.u0, box.v1 - box.v0)


def los_of_box(camera: kamera.Camera, box: Kutu, mount: np.ndarray = NOMINAL_MOUNT) -> np.ndarray:
    """LOS (i): unit vector camera -> the box's centre in body FRD (camera_info intrinsics and distortion, mount)."""
    return mount @ camera.pixel_to_los(*box_centre(box))


def angle_deg(a: Sequence[float], b: Sequence[float]) -> float:
    """Angle between two directions [deg]; atan2 keeps it exact for the small angles that matter here."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return math.degrees(math.atan2(float(np.linalg.norm(np.cross(a, b))), float(np.dot(a, b))))


class Selection:
    """Temporary target selection of spec 5 (m11 brings the real one); one step() per processed frame."""

    def __init__(
        self, gate_factor: float = GATE_FACTOR, lost_after: int = LOST_AFTER, lock_min_iou: float = LOCK_MIN_IOU
    ) -> None:
        self.gate_factor = gate_factor
        self.lost_after = lost_after
        self.lock_min_iou = lock_min_iou
        self._last: Kutu | None = None  # the last chosen box while locked
        self._misses = 0
        self.locks = 0  # first lock + re-locks
        self.losses = 0

    @property
    def locked(self) -> bool:
        return self._last is not None

    @property
    def relocks(self) -> int:
        return max(0, self.locks - 1)

    def step(self, boxes: Sequence[Kutu], referee: Referee | None) -> Choice:
        """The target's box in this frame's boxes; `referee` is used only to lock (None: no referee for it)."""
        if self._last is not None:
            return self._follow(boxes)
        if referee is None:
            return Choice("kilitsiz", reason="hakem_yok")
        if not referee.visible:
            return Choice("kilitsiz", reason="hedef_gorunmuyor")
        scores = [algilama.iou(b, referee.box) for b in boxes]
        best = int(np.argmax(scores)) if scores else -1
        if best < 0 or scores[best] < self.lock_min_iou:
            return Choice("kilitsiz", reason="kutu_eslesmedi")
        self.locks += 1
        self._last, self._misses = boxes[best], 0
        state = "ilk_kilit" if self.locks == 1 else "yeniden_kilit"
        return Choice(state, boxes[best], best, self.locks, lock_iou=scores[best])

    def _follow(self, boxes: Sequence[Kutu]) -> Choice:
        cu, cv = box_centre(self._last)
        gate = (cu, cv, self.gate_factor * box_diagonal(self._last))
        distances = [math.hypot(box_centre(b)[0] - cu, box_centre(b)[1] - cv) for b in boxes]
        nearest = int(np.argmin(distances)) if distances else -1
        distance = distances[nearest] if nearest >= 0 else math.nan
        if nearest >= 0 and distance <= gate[2]:
            self._last, self._misses = boxes[nearest], 0
            return Choice("izleme", boxes[nearest], nearest, self.locks, gate=gate, distance=distance)
        self._misses += 1
        if self._misses >= self.lost_after:
            self._last = None
            self.losses += 1
            return Choice("kilit_kaybi", lock_no=self.locks, misses=self._misses, gate=gate, distance=distance)
        return Choice("eslesmedi", lock_no=self.locks, misses=self._misses, gate=gate, distance=distance)


# algilama.csv columns after DetectionLog's own (one row per processed model frame). Wall times: monotonic [s];
# *_sim: sim seconds (SimClock). tez_los_*: the vector of this frame's TEZ_LOS (empty = NaN = no target) and what
# became of it; the send columns stay empty when TEZ_LOS comes from the referee (takip.los: hakem).
ROW_COLUMNS = (
    "secim",  # Choice.state
    "kilitsiz_neden",
    "kilit_no",
    "ardisik_kacirma",
    "secilen_kutu",  # index in kutular.csv (0 = most confident)
    "secilen_u0",
    "secilen_v0",
    "secilen_u1",
    "secilen_v1",
    "secilen_guven",
    "kilit_iou",
    "kapi_u",  # [px] gate centre (the previous choice) and radius while locked
    "kapi_v",
    "kapi_px",
    "merkez_mesafe_px",  # [px] nearest box centre to the gate centre
    "los_i_x",  # LOS (i) of the chosen box, body FRD
    "los_i_y",
    "los_i_z",
    "tez_los_x",
    "tez_los_y",
    "tez_los_z",
    "tez_los_sonuc",  # LosSender: gonderildi | gecersiz | baglanti_yok | ayni_kare | eski_kare | hiz_siniri | hata
    "hazir",  # selection and LOS done, the message enters the delay line
    "serbest",  # it left the delay line
    "gonderim",  # it was written to the MAVLink socket (sent messages only)
    "hazir_sim",
    "serbest_sim",
    "gonderim_sim",
    "takip_ms",  # [ms] hazir - alinma: selection + LOS in the tracking thread
    "ek_gecikme_ms",  # [ms] serbest - hazir: time in the delay line (no artificial delay before task group 12)
    "uctan_uca_ms",  # [ms sim] gonderim - capture
)
# tez_los.csv: every TEZ_LOS attempt of the run, whichever source; t_us joins algilama.csv / dogru_cevap.csv
LOS_COLUMNS = (
    "t_us",
    "t",  # [s sim] capture of the frame the message is about
    "kaynak",  # model | hakem
    "hedef",  # 1 = a direction, 0 = NaN (no target)
    "x",
    "y",
    "z",
    "time_usec",  # DEBUG_VECT.time_usec as sent: capture time (no clock model before task group 12)
    "sonuc",
    "kaynak_hazir",  # [s monotonic] model: the result reached the main process; hakem: row + segmentation were in
    "hazir",
    "serbest",
    "gonderim",
    "gonderim_sim",
    "kaynak_ms",  # [ms sim] kaynak_hazir - capture
    "hazir_ms",  # [ms sim] hazir - capture
    "ek_gecikme_ms",
    "uctan_uca_ms",
)


class Tracker:
    """The tracking threads of a run (see the module text). source: what TEZ_LOS carries, "model" (LOS (i)) or
    "hakem" (LOS (ii)); the model's frames are selected either way, for algilama.csv and the metrics."""

    def __init__(
        self,
        source: str,
        clock: goruntu.SimClock,
        out: Path,
        detections: algilama.DetectionLog | None,
        camera: Callable[[], kamera.Camera | None],
        extra_ms: float = 0.0,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        """clock: sim <-> wall; out: run folder (tez_los.csv); detections: algilama.csv (None without a model);
        camera: the drone camera's camera_info once known (Recorder.camera); extra_ms [ms]: artificial delay (0 until
        task group 12); now: monotonic clock [s]."""
        if source not in SOURCES:
            raise ValueError(f"takip.los: {list(SOURCES)} olmalı, gelen: {source!r}")
        self.source = source
        self._clock = clock
        self._out = out
        self._detections = detections
        self._camera = camera
        self._now = now
        self.selection = Selection()
        self.sender = px4_baglanti.LosSender(now)
        self._line = gecikme.DelayLine(self._deliver, extra_ms, now, name="tez-gecikme-hatti")
        self._lock = threading.Lock()
        self._referees: dict[int, Referee] = {}
        self._newest_referee = 0
        self._file = None
        self._writer = None
        self.attempts: list[dict] = []  # tez_los.csv rows
        self.events: list[dict] = []  # lock events
        self.errors: list[str] = []
        self._closed = False
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._referee_loop, name="tez-hakem-los", daemon=True)
        self._thread.start()

    # --- inputs -------------------------------------------------------------------------------------------------

    def attach(self, link: object) -> None:
        """The MAVLink link (Vehicle) TEZ_LOS goes out on, once it exists."""
        self.sender.attach(link)

    def detach(self) -> None:
        self.sender.detach()

    def on_referee(self, t: float, row: dict | None, ready: float) -> None:
        """kayit.Recorder on_frame: one camera frame, the referee's row (None outside the recording). Returns at once
        (gz-transport thread); the work is done in the referee thread."""
        if not self._closed:
            self._queue.put((t, row, ready))

    def wait_idle(self) -> None:
        """Until the referee thread has handled every frame given so far."""
        self._queue.join()

    def on_model(self, r: algilama.FrameResult, alinma: float) -> None:
        """ModelProcess on_result: select, LOS (i), and with the model source send; then the algilama.csv row."""
        key = algilama.time_key(r.t)
        with self._lock:
            referee = self._referees.get(key)
        choice = self.selection.step(r.kutular, referee)
        camera = self._camera()
        los = los_of_box(camera, choice.box) if choice.box is not None and camera is not None else None
        self._note(choice, r.t)
        extra = _choice_columns(choice, los)
        hazir = self._now()
        extra |= {"hazir": hazir, "hazir_sim": self._clock.to_sim(hazir), "takip_ms": (hazir - alinma) * 1000.0}
        if self.source == "model" and not self._closed:
            self._line.put(("model", r, alinma, extra, los, hazir), hazir)
        else:
            self._write_row(r, alinma, extra)

    def _referee_loop(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    return
                t, row, ready = item
                referee = Referee.from_row(row, ready) if row is not None else None
                if referee is not None:
                    self._keep(referee)
                if self.source == "hakem" and not self._closed:
                    los = np.array(referee.los_body) if referee is not None and referee.visible else None
                    hazir = self._now()
                    self._line.put(("hakem", t, los, ready, hazir), hazir)
            except Exception as e:  # noqa: BLE001 - the thread keeps going; the run reports it
                self._error(f"hakem karesi işlenemedi: {type(e).__name__}: {e}")
            finally:
                self._queue.task_done()

    def _keep(self, referee: Referee) -> None:
        key = algilama.time_key(referee.t)
        with self._lock:
            self._referees[key] = referee
            self._newest_referee = max(self._newest_referee, key)
            oldest = self._newest_referee - round(REFEREE_KEEP_S * 1e6)
            for k in [k for k in self._referees if k < oldest]:
                del self._referees[k]

    def _note(self, choice: Choice, t: float) -> None:
        if choice.state in ("ilk_kilit", "yeniden_kilit", "kilit_kaybi"):
            event = {"t": t, "olay": choice.state, "kilit_no": choice.lock_no}
            if choice.state == "kilit_kaybi":
                event["ardisik_kacirma"] = choice.misses
            else:
                event["kilit_iou"] = choice.lock_iou
            with self._lock:
                self.events.append(event)

    # --- output -------------------------------------------------------------------------------------------------

    def _deliver(self, item: tuple, serbest: float) -> None:
        """DelayLine: one message leaves the line -> LosSender -> rows. Runs in the producer's or the line's thread."""
        try:
            if item[0] == "model":
                _, r, alinma, extra, los, hazir = item
                result, at = self.sender.send(r.t, los)
                sent = self._attempt(r.t, "model", los, result, alinma, hazir, serbest, at)
                extra |= {f"tez_los_{k}": v for k, v in zip("xyz", _vector(los), strict=True)}
                extra |= {"tez_los_sonuc": result, "serbest": serbest, "serbest_sim": self._clock.to_sim(serbest)}
                extra |= {"ek_gecikme_ms": sent["ek_gecikme_ms"], "gonderim": sent["gonderim"]}
                extra |= {"gonderim_sim": sent["gonderim_sim"], "uctan_uca_ms": sent["uctan_uca_ms"]}
                self._write_row(r, alinma, extra)
            else:
                _, t, los, ready, hazir = item
                result, at = self.sender.send(t, los)
                self._attempt(t, "hakem", los, result, ready, hazir, serbest, at)
        except Exception as e:  # noqa: BLE001 - one message lost is reported; the line must keep going
            self._error(f"TEZ_LOS gönderilemedi: {type(e).__name__}: {e}")

    def _attempt(
        self,
        t: float,
        source: str,
        los: np.ndarray | None,
        result: str,
        origin: float,
        hazir: float,
        serbest: float,
        at: float,
    ) -> dict:
        to_sim = self._clock.to_sim
        sent = result == "gonderildi"
        gonderim_sim = to_sim(at) if sent else math.nan
        x, y, z = _vector(los)
        row = {
            "t_us": algilama.time_key(t),
            "t": t,
            "kaynak": source,
            "hedef": int(los is not None),
            "x": x,
            "y": y,
            "z": z,
            "time_usec": algilama.time_key(t),
            "sonuc": result,
            "kaynak_hazir": origin,
            "hazir": hazir,
            "serbest": serbest,
            "gonderim": at if sent else math.nan,
            "gonderim_sim": gonderim_sim,
            "kaynak_ms": (to_sim(origin) - t) * 1000.0,
            "hazir_ms": (to_sim(hazir) - t) * 1000.0,
            "ek_gecikme_ms": (serbest - hazir) * 1000.0,
            "uctan_uca_ms": (gonderim_sim - t) * 1000.0,
        }
        with self._lock:
            if self._writer is None:
                self._file = (self._out / "tez_los.csv").open("w", newline="", encoding="utf-8")
                self._writer = csv.writer(self._file)
                self._writer.writerow(LOS_COLUMNS)
            self._writer.writerow([algilama.csv_cell(row[c]) for c in LOS_COLUMNS])
            self._file.flush()
            self.attempts.append(row)
        return row

    def _write_row(self, r: algilama.FrameResult, alinma: float, extra: dict) -> None:
        if self._detections is not None:
            self._detections.add(r, alinma, extra)

    def _error(self, text: str) -> None:
        with self._lock:
            if len(self.errors) < 20:
                self.errors.append(text)

    def close(self) -> None:
        """End of the stream: the referee thread and the delay line finish what they hold, tez_los.csv is closed.
        Call after the model process stopped (no more on_model). Repeatable."""
        if not self._closed:
            self._closed = True
            self._queue.put(None)
            self._thread.join(gecikme.CLOSE_TIMEOUT)
        self._line.close()
        with self._lock:
            if self._file is not None:
                self._file.close()
                self._file = None

    # --- numbers ------------------------------------------------------------------------------------------------

    def summary(self) -> dict:
        """ozet.json "tez_los": the whole run (not only the window)."""
        with self._lock:
            attempts, events, errors = list(self.attempts), list(self.events), list(self.errors)
        sent = [a for a in attempts if a["sonuc"] == "gonderildi"]
        return {
            "kaynak": self.source,
            "sonuclar": dict(Counter(a["sonuc"] for a in attempts)),
            "gonderilen_hedef_yok": sum(1 for a in sent if not a["hedef"]),
            "ilk_gonderim_sim_s": sent[0]["gonderim_sim"] if sent else math.nan,
            "son_gonderim_sim_s": sent[-1]["gonderim_sim"] if sent else math.nan,
            "kilit": {
                "kilit_sayisi": self.selection.locks,
                "kilit_kaybi": self.selection.losses,
                "yeniden_kilit": self.selection.relocks,
                "olaylar": events,
            },
            "hatalar": errors,
        }

    def recent(self, t_from: float) -> str:
        """One log line about TEZ_LOS since sim time t_from [s]."""
        with self._lock:
            sent = [a for a in self.attempts if a["sonuc"] == "gonderildi" and a["t"] >= t_from]
        target = sum(a["hedef"] for a in sent)
        state = "kilitli" if self.selection.locked else "kilit yok"
        return (
            f"TEZ_LOS ({self.source}): {len(sent)} gönderildi ({target} hedefli, {len(sent) - target} hedef yok); "
            f"{state}"
        )

    def metrics(self, start: float, end: float, detection_rows: list[dict], referee_rows: list[dict]) -> dict:
        """Numbers of the window start..end [s sim] for ozet.json "olcutler" (temporary, task group 7 moves them to
        olcum.py). TEZ_LOS by send time (what PX4 can log in the window), selection and LOS (i) by frame time."""
        with self._lock:
            attempts, events = list(self.attempts), list(self.events)
        span = end - start
        sent = [a for a in attempts if a["sonuc"] == "gonderildi" and start <= a["gonderim_sim"] <= end]
        tried = [a for a in attempts if start <= a["t"] <= end]
        latency = [a["uctan_uca_ms"] for a in sent]
        m = {
            "tez_los_gonderilen": len(sent),
            "tez_los_hedef_yok": sum(1 for a in sent if not a["hedef"]),
            "tez_los_gecersiz": sum(1 for a in tried if a["sonuc"] == "gecersiz"),
            "tez_los_reddedilen": sum(1 for a in tried if a["sonuc"] in ("ayni_kare", "eski_kare", "hiz_siniri")),
            "tez_los_hizi_hz": len(sent) / span if span > 0 else math.nan,
        } | _stats("uctan_uca_ms", latency)
        m |= _stats("ek_gecikme_ms", [a["ek_gecikme_ms"] for a in sent], ("ort", "maks"))
        m |= _stats("hazir_ms", [a["hazir_ms"] for a in sent], ("ort", "p95"))
        inside = [e for e in events if start <= e["t"] <= end]
        m["kilit_kaybi_sayisi"] = sum(1 for e in inside if e["olay"] == "kilit_kaybi")
        m["yeniden_kilit_sayisi"] = sum(1 for e in inside if e["olay"] == "yeniden_kilit")
        return m | _selection_metrics(start, end, detection_rows, referee_rows)


def _selection_metrics(start: float, end: float, rows: list[dict], referee_rows: list[dict]) -> dict:
    """Processed frames of the window: how often a box was chosen, how often it was the target while the target was
    visible, and LOS (i) against the referee's LOS (ii) of the same frame while the chosen box is the target."""
    frames = [r for r in rows if start <= r["t"] <= end and "secim" in r]
    referee = {algilama.time_key(x["t"]): x for x in referee_rows}
    chosen = right = visible = 0
    angles: list[float] = []
    for r in frames:
        has_box = r.get("secilen_kutu") is not None
        chosen += has_box
        ref = referee.get(r["t_us"])
        if ref is None or not ref.get("gorunur"):
            continue
        visible += 1
        target = tuple(float(ref.get(f"hedef_kutu_{k}", math.nan)) for k in ("u0", "v0", "u1", "v1"))
        box = tuple(r[f"secilen_{k}"] for k in ("u0", "v0", "u1", "v1")) if has_box else (math.nan,) * 4
        if algilama.iou(box, target) >= MATCH_IOU:
            right += 1
            angles.append(angle_deg([r[f"los_i_{k}"] for k in "xyz"], [ref[f"los_govde_{k}"] for k in "xyz"]))
    m = {
        "secili_kare_orani": chosen / len(frames) if frames else math.nan,
        "secim_dogru_orani": right / visible if visible else math.nan,
        "los_i_ii_kare": len(angles),
    }
    return m | _stats("los_i_ii_fark", angles, ("ort", "p50", "p95", "maks"), unit="_deg")


def _stats(
    name: str, values: list[float], kinds: tuple[str, ...] = ("ort", "p50", "p95", "maks"), unit: str = ""
) -> dict:
    values = [v for v in values if not math.isnan(v)]
    out = {}
    for kind in kinds:
        if not values:
            out[f"{name}_{kind}{unit}"] = math.nan
        elif kind == "ort":
            out[f"{name}_{kind}{unit}"] = statistics.fmean(values)
        elif kind == "maks":
            out[f"{name}_{kind}{unit}"] = max(values)
        else:
            out[f"{name}_{kind}{unit}"] = float(np.percentile(values, float(kind[1:])))
    return out


def _vector(los: np.ndarray | None) -> tuple[float, float, float]:
    return (math.nan,) * 3 if los is None else tuple(float(c) for c in los)


def _choice_columns(c: Choice, los: np.ndarray | None) -> dict:
    b = c.box
    gate = c.gate or (math.nan,) * 3
    x, y, z = _vector(los)
    return {
        "secim": c.state,
        "kilitsiz_neden": c.reason,
        "kilit_no": c.lock_no if c.state != "kilitsiz" else 0,
        "ardisik_kacirma": c.misses,
        "secilen_kutu": c.index,
        "secilen_u0": b.u0 if b else math.nan,
        "secilen_v0": b.v0 if b else math.nan,
        "secilen_u1": b.u1 if b else math.nan,
        "secilen_v1": b.v1 if b else math.nan,
        "secilen_guven": b.guven if b else math.nan,
        "kilit_iou": c.lock_iou,
        "kapi_u": gate[0],
        "kapi_v": gate[1],
        "kapi_px": gate[2],
        "merkez_mesafe_px": c.distance,
        "los_i_x": x,
        "los_i_y": y,
        "los_i_z": z,
    }
