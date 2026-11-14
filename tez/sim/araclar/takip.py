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
  (i)  model: the chosen box's centre -> Camera.pixel_to_los (camera_info, distortion) -> camera_to_body(tilt), the
       scenario's kamera.egim_deg (default kamera.NOMINAL_TILT_DEG). The nominal mount, like the Pi would use its
       measured one, not the mount Gazebo reports: a mount error can be put in on purpose later.
  (ii) hakem: the referee's los_govde of the frame while the target is visible, NaN while it is not; every camera
       frame (30 Hz), once the referee's row and segmentation frame are both in (that delay is measured too).

Tracker: model results come in ModelProcess' result thread (on_model), the referee's frames from a gz-transport
thread (on_referee -> its own thread). The chosen source's messages go: DelayLine (gecikme.py) -> LosSender (one per
frame, NaN = no target, never an invalid vector; px4_baglanti.py) -> Vehicle.send_los. A model frame becomes an
algilama.csv row once its TEZ_LOS went out (or was refused); every TEZ_LOS attempt is a tez_los.csv row.

follow_me (spec 6): every chosen model box also gets its flat-ground position (konumlama.Locator, the EKF pose of the
frame's capture time from the link's pose history), in every tracking source; with follow=True it goes to PX4 as
FOLLOW_TARGET behind the frame's TEZ_LOS on the same delay line (FollowTargetSender: at most every third camera frame,
none without a position). With the referee as the source (takip.los: hakem) FOLLOW_TARGET carries where the person
really is, only while the camera sees them: a "perfect detector" reference run. Every FOLLOW_TARGET attempt is a
follow_target.csv row. The truth columns (gercek_x/y, hatasi) are evaluation only, from the scenario's path.
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
import konumlama
import px4_baglanti
from algilama import Kutu

GATE_FACTOR = 1.5  # spec 5: centre distance at most 1.5 x the previous box's diagonal
LOST_AFTER = 10  # spec 5: processed frames in a row without a match drop the lock
# A box locks on the target only if it overlaps the referee's box at least this much: the IoU at which the metrics say
# a box belongs to a person at all (spec "Ölçüt Tanımları": yanlış kişi / yanlış pozitif, 0.3). Without it a box far
# off would lock with an IoU of 0.01, where an operator would not have clicked.
LOCK_MIN_IOU = 0.3
MOUNT_PITCH_DOWN = konumlama.MOUNT_PITCH_DOWN  # nominal camera mount (spec "Kamera parametreleri"; the Pi: measured)
NOMINAL_MOUNT = konumlama.NOMINAL_MOUNT  # C_cb, optical -> body FRD
REFEREE_KEEP_S = 3.0  # [s sim] referee frames kept for the lock of a model frame (a model result is ~0.15 s late)
# [ms sim] a referee frame later than this after its capture can miss the model result of the same frame (the result
# is ready ~120-150 ms after the capture: spec "Model dosyası"): an unlocked frame then finds no referee (hakem_yok)
# and the re-lock waits. Normally the referee is ~35 ms late (gorev-grubu-17-on-kamera-acisi.md, "Canlı hakem akışı").
REFEREE_LATE_MS = 100.0
SOURCES = ("model", "hakem")


@dataclass(frozen=True)
class Referee:
    """What the referee knows about the target in one camera frame."""

    t: float  # [s sim] capture
    box: tuple[float, float, float, float]  # its visible pixels' box, pixel edges (NaN when nothing is visible)
    visible: bool  # enough of it is not hidden (kayit.VISIBLE_PX)
    los_body: tuple[float, float, float]  # los_govde: camera -> body centre, body FRD, unit
    ready: float  # [s monotonic] row and segmentation frame were both in
    position: tuple[float, float] = (math.nan, math.nan)  # [m] where the target is: Gazebo world x east, y north

    @classmethod
    def from_row(cls, row: dict, ready: float) -> "Referee":
        box = tuple(float(row.get(f"hedef_kutu_{k}", math.nan)) for k in ("u0", "v0", "u1", "v1"))
        los = tuple(float(row[f"los_govde_{k}"]) for k in "xyz")
        position = (float(row.get("hedef_x", math.nan)), float(row.get("hedef_y", math.nan)))
        return cls(float(row["t"]), box, bool(row.get("gorunur")), los, ready, position)


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
    # flat-ground position of the chosen box (konumlama.py), every tracking source
    "konum",  # konumlama.STATUSES: hesaplandi | kutu_yok | kamera_yok | kenar | poz_yok | referans_yok | ufka_yakin
    "ayak_u",  # [px] foot point: bottom middle of the chosen box
    "ayak_v",
    "isin_asagi",  # u_D, down component of the unit foot ray in NED
    "poz_once_ms",  # [ms] EKF samples around the capture time: the older one before, the later one after
    "poz_sonra_ms",
    "ekf_n",  # [m] EKF position (NED, EKF origin) and attitude [deg] of the capture time, interpolated
    "ekf_e",
    "ekf_d",
    "ekf_roll_deg",
    "ekf_pitch_deg",
    "ekf_yaw_deg",
    "konum_n",  # [m] ground point, EKF local NED
    "konum_e",
    "konum_d",
    "konum_lat",  # [deg] what FOLLOW_TARGET carries, and its AMSL height [m]
    "konum_lon",
    "konum_alt",
    "konum_menzil_m",  # [m] camera -> ground point
    "konum_yatay_m",  # [m] drone -> ground point, horizontal
    "konum_x",  # [m] the same point in the Gazebo world (x east, y north; evaluation)
    "konum_y",
    "gercek_x",  # [m] where the target really was at the capture time (scenario path; evaluation only)
    "gercek_y",
    "konum_hatasi_m",  # [m] horizontal distance konum - gercek
    "ft_sonuc",  # FOLLOW_TARGET of this frame (follow_me, LOS model): FollowTargetSender result, konum_yok, or empty
    "ft_gonderim_sim",
    "ft_uctan_uca_ms",  # [ms sim] FOLLOW_TARGET send - capture
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
# follow_target.csv: every FOLLOW_TARGET attempt (follow_me); t_us joins the other files
FOLLOW_COLUMNS = (
    "t_us",
    "t",  # [s sim] capture of the frame the position is from
    "kaynak",  # model (flat-ground position of the chosen box) | hakem (the true position)
    "lat",  # [deg], [m AMSL]: as sent
    "lon",
    "alt",
    "x",  # [m] the sent point in the Gazebo world (x east, y north)
    "y",
    "gercek_x",  # [m] the target at the capture time (evaluation)
    "gercek_y",
    "hata_m",  # [m] horizontal, sent - true at the capture time
    "hata_gonderimde_m",  # [m] sent - true at the send time (the target walked on meanwhile)
    "sonuc",  # FollowTargetSender: gonderildi | gecersiz | baglanti_yok | ayni_kare | eski_kare | hiz_siniri | hata
    "kaynak_hazir",
    "hazir",
    "serbest",
    "gonderim",
    "gonderim_sim",
    "uctan_uca_ms",
)


class Tracker:
    """The tracking threads of a run (see the module text). source: what TEZ_LOS (and in follow_me FOLLOW_TARGET)
    carries, "model" (LOS (i), the box's ground point) or "hakem" (LOS (ii), the true position); the model's frames
    are selected and located either way, for algilama.csv and the metrics."""

    def __init__(
        self,
        source: str,
        clock: goruntu.SimClock,
        out: Path,
        detections: algilama.DetectionLog | None,
        camera: Callable[[], kamera.Camera | None],
        extra_ms: float = 0.0,
        now: Callable[[], float] = time.monotonic,
        follow: bool = False,
        locator: konumlama.Locator | None = None,
        world: konumlama.WorldGeo | None = None,
        truth: Callable[[float], tuple[float, float]] | None = None,
        mount: np.ndarray = NOMINAL_MOUNT,
    ) -> None:
        """clock: sim <-> wall; out: run folder (tez_los.csv, follow_target.csv); detections: algilama.csv (None
        without a model); camera: the drone camera's camera_info once known (Recorder.camera); extra_ms [ms]:
        artificial delay (0 until task group 12); now: monotonic clock [s]; follow: send FOLLOW_TARGET (follow_me);
        locator: flat-ground positions of the model's boxes (None: none); world: the Gazebo world's geodetic origin
        (evaluation columns; the referee's FOLLOW_TARGET); truth: the target's true (x, y) [m] at a sim time
        (evaluation only); mount: C_cb (optical -> body FRD) of LOS (i), kamera.camera_to_body(the scenario's tilt)."""
        if source not in SOURCES:
            raise ValueError(f"takip.los: {list(SOURCES)} olmalı, gelen: {source!r}")
        if follow and source == "hakem" and world is None:
            raise ValueError("follow_me + hakem: gerçek konumu enlem/boylama çevirmek için dünyanın kökeni gerekir")
        self.source = source
        self.follow = follow
        self._clock = clock
        self._out = out
        self._detections = detections
        self._camera = camera
        self._now = now
        self._locator = locator
        self._world = world
        self._truth = truth
        self.mount = np.asarray(mount, dtype=float)
        self._poses: konumlama.PoseHistory | None = None
        self.poses: konumlama.PoseHistory | None = None  # the last link's history, kept after detach (metrics)
        self.selection = Selection()
        self.sender = px4_baglanti.LosSender(now)
        self.follow_sender = px4_baglanti.FollowTargetSender(now)
        self.fixes: Counter[str] = Counter()  # Locator results of the whole run
        self.follow_attempts: list[dict] = []  # follow_target.csv rows
        self._ft_file = None
        self._ft_writer = None
        self._line = gecikme.DelayLine(self._deliver, extra_ms, now, name="tez-gecikme-hatti")
        self._lock = threading.Lock()
        self._referees: dict[int, Referee] = {}
        self._newest_referee = 0
        self._referee_late_ms: list[float] = []  # [ms sim] capture -> the referee's frame known, every recorded frame
        self._referee_keys: set[int] = set()  # every referee frame of the run (time_key)
        self._no_referee: list[int] = []  # model frames that found no referee to lock with (hakem_yok)
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
        """The MAVLink link (Vehicle) TEZ_LOS and FOLLOW_TARGET go out on, once it exists; its pose history (poses)
        gives the EKF pose of the frames."""
        self.sender.attach(link)
        self.follow_sender.attach(link)
        self._poses = self.poses = getattr(link, "poses", None)

    def detach(self) -> None:
        self.sender.detach()
        self.follow_sender.detach()
        self._poses = None

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
        if choice.reason == "hakem_yok":
            with self._lock:
                self._no_referee.append(key)
        camera = self._camera()
        los = los_of_box(camera, choice.box, self.mount) if choice.box is not None and camera is not None else None
        self._note(choice, r.t)
        extra = _choice_columns(choice, los)
        fix = None
        if self._locator is not None:
            fix = self._locator.locate(choice.box, r.t, camera, self._poses)
            with self._lock:
                self.fixes[fix.status] += 1
            extra |= self._fix_columns(fix, r.t)
        hazir = self._now()
        extra |= {"hazir": hazir, "hazir_sim": self._clock.to_sim(hazir), "takip_ms": (hazir - alinma) * 1000.0}
        if self.source == "model" and not self._closed:
            self._line.put(("model", r, alinma, extra, los, fix, hazir), hazir)
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
                    late = (self._clock.to_sim(ready) - t) * 1000.0
                    with self._lock:
                        self._referee_late_ms.append(late)
                if self.source == "hakem" and not self._closed:
                    seen = referee is not None and referee.visible
                    los = np.array(referee.los_body) if seen else None
                    point = None
                    if self.follow and seen and all(math.isfinite(c) for c in referee.position):
                        point = konumlama.GeoPoint(*self._world.to_geodetic(*referee.position))  # a perfect GPS
                    hazir = self._now()
                    self._line.put(("hakem", t, los, point, ready, hazir), hazir)
            except Exception as e:  # noqa: BLE001 - the thread keeps going; the run reports it
                self._error(f"hakem karesi işlenemedi: {type(e).__name__}: {e}")
            finally:
                self._queue.task_done()

    def _keep(self, referee: Referee) -> None:
        key = algilama.time_key(referee.t)
        with self._lock:
            self._referees[key] = referee
            self._referee_keys.add(key)
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
                _, r, alinma, extra, los, fix, hazir = item
                result, at = self.sender.send(r.t, los)
                sent = self._attempt(r.t, "model", los, result, alinma, hazir, serbest, at)
                extra |= {f"tez_los_{k}": v for k, v in zip("xyz", _vector(los), strict=True)}
                extra |= {"tez_los_sonuc": result, "serbest": serbest, "serbest_sim": self._clock.to_sim(serbest)}
                extra |= {"ek_gecikme_ms": sent["ek_gecikme_ms"], "gonderim": sent["gonderim"]}
                extra |= {"gonderim_sim": sent["gonderim_sim"], "uctan_uca_ms": sent["uctan_uca_ms"]}
                if self.follow:
                    extra |= self._follow(
                        r.t, "model", fix.geo if fix is not None and fix.ok else None, alinma, hazir, serbest
                    )
                self._write_row(r, alinma, extra)
            else:
                _, t, los, point, ready, hazir = item
                result, at = self.sender.send(t, los)
                self._attempt(t, "hakem", los, result, ready, hazir, serbest, at)
                if self.follow and point is not None:
                    self._follow(t, "hakem", point, ready, hazir, serbest)
        except Exception as e:  # noqa: BLE001 - one message lost is reported; the line must keep going
            self._error(f"TEZ_LOS / FOLLOW_TARGET gönderilemedi: {type(e).__name__}: {e}")

    def _follow(
        self, t: float, source: str, point: konumlama.GeoPoint | None, origin: float, hazir: float, serbest: float
    ) -> dict:
        """FOLLOW_TARGET of the frame captured at t (behind its TEZ_LOS); -> its algilama.csv columns."""
        if point is None:
            return {"ft_sonuc": "konum_yok"}
        result, at = self.follow_sender.send(t, point)
        to_sim = self._clock.to_sim
        sent = result == "gonderildi"
        gonderim_sim = to_sim(at) if sent else math.nan
        x, y = self._world_xy(point)
        tx, ty = self._true_xy(t)
        sx, sy = self._true_xy(gonderim_sim) if sent else (math.nan, math.nan)
        row = {
            "t_us": algilama.time_key(t),
            "t": t,
            "kaynak": source,
            "lat": point.lat,
            "lon": point.lon,
            "alt": point.alt,
            "x": x,
            "y": y,
            "gercek_x": tx,
            "gercek_y": ty,
            "hata_m": math.hypot(x - tx, y - ty),
            "hata_gonderimde_m": math.hypot(x - sx, y - sy),
            "sonuc": result,
            "kaynak_hazir": origin,
            "hazir": hazir,
            "serbest": serbest,
            "gonderim": at if sent else math.nan,
            "gonderim_sim": gonderim_sim,
            "uctan_uca_ms": (gonderim_sim - t) * 1000.0,
        }
        with self._lock:
            if self._ft_writer is None:
                self._ft_file = (self._out / "follow_target.csv").open("w", newline="", encoding="utf-8")
                self._ft_writer = csv.writer(self._ft_file)
                self._ft_writer.writerow(FOLLOW_COLUMNS)
            self._ft_writer.writerow([algilama.csv_cell(row[c]) for c in FOLLOW_COLUMNS])
            self._ft_file.flush()
            self.follow_attempts.append(row)
        return {"ft_sonuc": result, "ft_gonderim_sim": gonderim_sim, "ft_uctan_uca_ms": row["uctan_uca_ms"]}

    def _world_xy(self, point: konumlama.GeoPoint | None) -> tuple[float, float]:
        if point is None or self._world is None:
            return math.nan, math.nan
        x, y, _ = self._world.to_local(point.lat, point.lon, point.alt)
        return x, y

    def _true_xy(self, t: float) -> tuple[float, float]:
        if self._truth is None or not math.isfinite(t):
            return math.nan, math.nan
        return self._truth(t)

    def _fix_columns(self, fix: konumlama.Fix, t: float) -> dict:
        nan = math.nan
        pose = fix.pose
        roll, pitch, yaw = pose.euler_deg() if pose is not None else (nan, nan, nan)
        p = pose.p if pose is not None else (nan, nan, nan)
        ned = fix.ned if fix.ned is not None else (nan, nan, nan)
        geo = fix.geo
        x, y = self._world_xy(geo)
        tx, ty = self._true_xy(t) if fix.ok else (nan, nan)
        foot = fix.foot or (nan, nan)
        return {
            "konum": fix.status,
            "ayak_u": foot[0],
            "ayak_v": foot[1],
            "isin_asagi": fix.down,
            "poz_once_ms": pose.before_ms if pose is not None else nan,
            "poz_sonra_ms": pose.after_ms if pose is not None else nan,
            "ekf_n": p[0],
            "ekf_e": p[1],
            "ekf_d": p[2],
            "ekf_roll_deg": roll,
            "ekf_pitch_deg": pitch,
            "ekf_yaw_deg": yaw,
            "konum_n": ned[0],
            "konum_e": ned[1],
            "konum_d": ned[2],
            "konum_lat": geo.lat if geo else nan,
            "konum_lon": geo.lon if geo else nan,
            "konum_alt": geo.alt if geo else nan,
            "konum_menzil_m": fix.range_m,
            "konum_yatay_m": fix.horizontal_m,
            "konum_x": x,
            "konum_y": y,
            "gercek_x": tx,
            "gercek_y": ty,
            "konum_hatasi_m": math.hypot(x - tx, y - ty),
        }

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
            for name in ("_file", "_ft_file"):
                if getattr(self, name) is not None:
                    getattr(self, name).close()
                    setattr(self, name, None)

    # --- numbers ------------------------------------------------------------------------------------------------

    def summary(self) -> dict:
        """ozet.json "tez_los": the whole run (not only the window); "follow_target": FOLLOW_TARGET and the box
        positions of the whole run. The window's numbers: olcum.py (attempts, follow_attempts, events)."""
        with self._lock:
            attempts, events, errors = list(self.attempts), list(self.events), list(self.errors)
            follow, fixes = list(self.follow_attempts), dict(self.fixes)
            late = [v for v in self._referee_late_ms if math.isfinite(v)]
            missed = list(self._no_referee)
            came_later = sum(1 for k in missed if k in self._referee_keys)
        sent = [a for a in attempts if a["sonuc"] == "gonderildi"]
        ft_sent = [a for a in follow if a["sonuc"] == "gonderildi"]
        poses = self.poses
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
            "hakem_akisi": referee_stream(late)
            | {"hakem_yok_kare": len(missed), "hakem_sonradan_gelen_kare": came_later},
            "follow_target": {
                "etkin": self.follow,
                "kaynak": self.source if self.follow else None,
                "sonuclar": dict(Counter(a["sonuc"] for a in follow)),
                "ilk_gonderim_sim_s": ft_sent[0]["gonderim_sim"] if ft_sent else math.nan,
                "son_gonderim_sim_s": ft_sent[-1]["gonderim_sim"] if ft_sent else math.nan,
                "konum": fixes,  # Locator results of every processed model frame
                "ekf_kokeni": None if poses is None or poses.origin is None else vars(poses.origin),
                "ev_ned": None if poses is None or poses.home_ned is None else poses.home_ned.tolist(),
                "poz_kancasi_hatalari": poses.errors if poses is not None else 0,
            },
        }

    def recent(self, t_from: float) -> str:
        """One log line about TEZ_LOS since sim time t_from [s]."""
        with self._lock:
            sent = [a for a in self.attempts if a["sonuc"] == "gonderildi" and a["t"] >= t_from]
            follow = [a for a in self.follow_attempts if a["sonuc"] == "gonderildi" and a["t"] >= t_from]
        target = sum(a["hedef"] for a in sent)
        state = "kilitli" if self.selection.locked else "kilit yok"
        text = f"TEZ_LOS ({self.source}): {len(sent)} gönderildi ({target} hedefli, {len(sent) - target} hedef yok); "
        if self.follow:
            errors = [a["hata_m"] for a in follow if math.isfinite(a["hata_m"])]
            mean = f", konum hatası ort. {statistics.fmean(errors):.2f} m" if errors else ""
            text += f"FOLLOW_TARGET: {len(follow)} gönderildi{mean}; "
        return text + state


def referee_stream(late_ms: Sequence[float]) -> dict:
    """ozet.json "tez_los" "hakem_akisi": how late the referee's frames reached the tracking side [ms sim after the
    capture]: frames, p50, p95, max and how many were later than REFEREE_LATE_MS. Tracker.summary adds the model
    frames that found no referee to lock with (hakem_yok_kare; before the recording there is none) and how many of
    those got their referee frame later (hakem_sonradan_gelen_kare: the referee was late, not missing)."""
    values = np.asarray(late_ms, dtype=float)
    if values.size == 0:
        stats = dict.fromkeys(("gecikme_ms_p50", "gecikme_ms_p95", "gecikme_ms_maks"), math.nan)
    else:
        p50, p95 = np.percentile(values, [50, 95])
        stats = {"gecikme_ms_p50": float(p50), "gecikme_ms_p95": float(p95), "gecikme_ms_maks": float(values.max())}
    return {
        "kare": int(values.size),
        **stats,
        "gec_kare": int((values > REFEREE_LATE_MS).sum()),
        "gec_esik_ms": REFEREE_LATE_MS,
    }


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
