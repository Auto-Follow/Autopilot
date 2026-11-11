"""Person detector of the simulation: the detector interface, the model file and the YOLO detector on the laptop CPU.

The whole interface is Algilayici.algila(kare_rgb) -> list[Kutu]: one drone camera frame in, the boxes of the wanted
class out. Vision's detector (m08/m10) plugs in as another class with the same method; nothing here reads ../Vision
(rule 7). ultralytics and torch are imported only inside YoloAlgilayici, so the unit tests run without them.

Model file: --model > algilama.model (hedef.load already puts the first over the second) > MODEL_DIR/DEFAULT_MODEL.
Model files never go into a repo (rule 9); tez/sim/modeller.yaml records the known ones with their sha256.

In a scenario run the detector works in its own process (ModelProcess, "spawn"): frame reader (goruntu.py) -> camera
defects (kusurlar.py) -> detector, one FrameResult per processed frame to the main process through a FIFO queue.
DetectionLog writes them to algilama.csv / kutular.csv with the round(t * 1e6) key of dogru_cevap.csv.
"""

import atexit
import csv
import functools
import hashlib
import json
import math
import multiprocessing as mp
import os
import queue
import shutil
import signal
import statistics
import sys
import tempfile
import threading
import time
import traceback
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np
import yaml

import goruntu
import kusurlar

SIM_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = Path.home() / "auto-follow-modeller"  # outside every repo; the shared store is not decided yet
DEFAULT_MODEL = "person_detection_model_v0.2.pt"
CATALOG = SIM_DIR / "modeller.yaml"
DEFAULT_CLASS = "person"  # v0.2 calls it "Person", COCO "person"
CATALOG_KEYS = {"ad", "sha256", "boyut_bayt", "kaynak", "alma", "aciklama"}
CATALOG_REQUIRED = {"ad", "sha256", "kaynak", "alma"}
HEX_DIGITS = set("0123456789abcdef")


@dataclass(frozen=True)
class Kutu:
    """One detected box in full-resolution pixels of the frame, as pixel edges (u0 <= u < u1) like the referee's
    boxes (kayit.visible_parts); u right, v down from the top left corner of the image."""

    u0: float  # [px] left edge
    v0: float  # [px] top edge
    u1: float  # [px] right edge
    v1: float  # [px] bottom edge
    guven: float  # [0..1] confidence of the detector
    sinif: int  # class number in the model
    sinif_adi: str  # class name in the model


class Algilayici(Protocol):
    """What the simulation needs from a person detector."""

    def algila(self, kare_rgb: np.ndarray) -> list[Kutu]:
        """Boxes of the wanted class in one frame (RGB uint8, height x width x 3), the most confident first."""
        ...


@dataclass(frozen=True)
class KnownModel:
    """A model file recorded in modeller.yaml."""

    name: str  # file name
    sha256: str | None  # None: not recorded yet
    size: int | None  # [byte]
    source: str  # where the file comes from
    fetch: str  # how to put it into MODEL_DIR


@dataclass(frozen=True)
class ModelFile:
    """The model file of a run: its digest and what modeller.yaml says about it."""

    path: Path
    sha256: str
    size: int  # [byte]
    known: KnownModel | None  # matched by digest, else by file name; None: not in modeller.yaml
    warning: str | None  # the file differs from its record

    def as_dict(self) -> dict:
        return {
            "yol": str(self.path),
            "sha256": self.sha256,
            "boyut_bayt": self.size,
            "kayitli": self.known.name if self.known else None,
            "uyari": self.warning,
        }


def load_catalog(path: Path = CATALOG) -> dict[str, KnownModel]:
    """modeller.yaml -> file name -> record; a broken record is refused with its field."""
    d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = d.get("modeller") if isinstance(d, dict) else None
    if not isinstance(entries, list):
        raise ValueError(f"{path.name}: 'modeller:' altında bir liste olmalı")
    known: dict[str, KnownModel] = {}
    for i, e in enumerate(entries):
        where = f"{path.name}: modeller[{i}]"
        if not isinstance(e, dict):
            raise ValueError(f"{where}: {{ad: ..., sha256: ..., kaynak: ..., alma: ...}} olmalı")
        unknown, missing = set(e) - CATALOG_KEYS, CATALOG_REQUIRED - set(e)
        if unknown or missing:
            raise ValueError(f"{where}: bilinmeyen alan(lar) {sorted(unknown)}, eksik alan(lar) {sorted(missing)}")
        name, digest, size = e["ad"], e["sha256"], e.get("boyut_bayt")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{where}.ad: dosya adı olmalı, gelen: {name!r}")
        if name in known:
            raise ValueError(f"{where}.ad: {name} iki kez kayıtlı")
        if digest is not None and not (isinstance(digest, str) and len(digest) == 64 and set(digest) <= HEX_DIGITS):
            raise ValueError(f"{where}.sha256: 64 küçük onaltılık rakam ya da null olmalı, gelen: {digest!r}")
        if size is not None and not (isinstance(size, int) and not isinstance(size, bool) and size > 0):
            raise ValueError(f"{where}.boyut_bayt: pozitif tam sayı ya da null olmalı, gelen: {size!r}")
        known[name] = KnownModel(name, digest, size, str(e["kaynak"]), str(e["alma"]))
    return known


def model_path(chosen: Path | None, folder: Path | None = None) -> Path:
    """The run's model file: the one chosen with --model / algilama.model, else the default file of the folder."""
    return chosen if chosen is not None else (folder or MODEL_DIR) / DEFAULT_MODEL


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_model(path: Path, catalog: Mapping[str, KnownModel]) -> ModelFile:
    """Digest of the model file and its comparison with modeller.yaml.

    Raises FileNotFoundError saying where the file comes from (before anything starts)."""
    if not path.is_file():
        raise FileNotFoundError(_missing_text(path, catalog))
    digest = file_sha256(path)
    by_digest = {m.sha256: m for m in catalog.values() if m.sha256}
    known = by_digest.get(digest) or catalog.get(path.name)
    warning = None
    if known is not None and known.sha256 is not None and known.sha256 != digest:
        warning = (
            f"{path.name}: sha256 {digest}, {CATALOG.name}'daki kayıt {known.sha256}; dosya değişmiş ya da başka bir "
            "model. Bu koşunun sonuçları bu dosyaya aittir"
        )
    return ModelFile(path, digest, path.stat().st_size, known, warning)


def _missing_text(path: Path, catalog: Mapping[str, KnownModel]) -> str:
    known = catalog.get(path.name)
    other = "Başka bir dosya için: --model <yol> (senaryoda algilama.model)."
    if known is not None:
        return (
            f"Model dosyası yok: {path}\n  Kaynak: {known.source}\n  Almak için: {known.fetch}\n  {other} "
            "Model dosyaları repoya girmez (kural 9)."
        )
    names = ", ".join(sorted(catalog)) or "yok"
    return (
        f"Model dosyası yok: {path}\n  Bu ad {CATALOG.name}'da kayıtlı değil; kayıtlı modeller: {names} "
        f"({CATALOG}).\n  Dosyayı {MODEL_DIR}/ altına koyun ya da yolunu --model ile verin."
    )


def resolve_class(names: Mapping[int, str], wanted: str | int | None) -> int:
    """Class number to keep: a name (any case) or number from algilama.sinif / --sinif; None = the "person" class."""
    listing = ", ".join(f"{i}: {n}" for i, n in sorted(names.items()))
    if isinstance(wanted, int):
        if wanted in names:
            return wanted
        raise ValueError(f"algilama.sinif: {wanted} numaralı sınıf modelde yok (--sinif); modelin sınıfları: {listing}")
    target = (wanted if wanted is not None else DEFAULT_CLASS).casefold()
    found = sorted(i for i, n in names.items() if n.casefold() == target)
    if found:
        return found[0]
    if wanted is None:
        raise ValueError(
            f"algilama.sinif: modelde adı '{DEFAULT_CLASS}' olan sınıf yok; --sinif ile ad ya da numara verin. "
            f"Modelin sınıfları: {listing}"
        )
    raise ValueError(f"algilama.sinif: '{wanted}' adlı sınıf modelde yok (--sinif); modelin sınıfları: {listing}")


def to_boxes(
    xyxy: np.ndarray, conf: np.ndarray, cls: np.ndarray, names: Mapping[int, str], size: tuple[int, int]
) -> list[Kutu]:
    """Kutu list from a detector's arrays [(n, 4) corners in px, (n,) confidence, (n,) class], clipped to the frame
    (width, height) [px], the most confident first. Ultralytics' corners are pixel edges like ours (a box over the
    last column ends at the width); a box that covers no pixel after clipping is dropped."""
    width, height = size
    corners = np.clip(np.asarray(xyxy, dtype=float).reshape(-1, 4), 0.0, [width, height, width, height])
    found = [
        Kutu(float(u0), float(v0), float(u1), float(v1), float(c), int(k), names.get(int(k), str(int(k))))
        for (u0, v0, u1, v1), c, k in zip(corners, np.asarray(conf).ravel(), np.asarray(cls).ravel(), strict=True)
        if u1 > u0 and v1 > v0
    ]
    return sorted(found, key=lambda b: -b.guven)


def boxes_of(result: object, names: Mapping[int, str], size: tuple[int, int]) -> list[Kutu]:
    """Kutu list of one ultralytics result (Results.boxes on the CPU) in a frame of `size` (width, height) [px]."""
    b = result.boxes
    return to_boxes(b.xyxy.numpy(), b.conf.numpy(), b.cls.numpy(), names, size)


def iou(a: Kutu | tuple, b: Kutu | tuple) -> float:
    """Intersection over union of two pixel-edge boxes (Kutu or (u0, v0, u1, v1)); 0 if either is missing (NaN)."""
    a = (a.u0, a.v0, a.u1, a.v1) if isinstance(a, Kutu) else tuple(a)
    b = (b.u0, b.v0, b.u1, b.v1) if isinstance(b, Kutu) else tuple(b)
    if not all(math.isfinite(v) for v in a + b):
        return 0.0
    inter = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


@functools.cache
def _ultralytics() -> type:
    """ultralytics' YOLO class, imported once per process with every download, the analytics and the settings writes
    kept off. ultralytics reads these switches when it is imported, so nothing may import it earlier."""
    if "ultralytics" in sys.modules:
        raise RuntimeError("ultralytics bu süreçte başka bir yerden önceden açılmış; indirme/analitik kapatılamaz")
    # settings.json goes to a throwaway folder instead of ~/.config/Ultralytics; written before the import so that
    # even ultralytics' first view of the settings has sync (analytics) off and its folders inside it
    folder = Path(tempfile.mkdtemp(prefix="tez-ultralytics-"))
    atexit.register(shutil.rmtree, folder, ignore_errors=True)
    settings = {"sync": False} | {k: str(folder / k) for k in ("datasets_dir", "weights_dir", "runs_dir")}
    (folder / "Ultralytics").mkdir()
    (folder / "Ultralytics" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    os.environ["YOLO_CONFIG_DIR"] = str(folder)
    os.environ["YOLO_OFFLINE"] = "1"  # no internet check (DNS) at import, so no analytics and no downloads
    os.environ["YOLO_AUTOINSTALL"] = "0"  # never pip-install a missing package
    os.environ["YOLO_VERBOSE"] = "0"
    try:
        from ultralytics import YOLO
        from ultralytics.utils import ONLINE, SETTINGS
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            f"{e.name} kurulu değil: model paketleri tez/env/model-requirements.txt ile kurulur (tez/env/VERSIONS.md)"
        ) from e

    if ONLINE or SETTINGS["sync"]:
        raise RuntimeError(f"ultralytics çevrimdışı açılamadı (ONLINE={ONLINE}, sync={SETTINGS['sync']})")
    return YOLO


class YoloAlgilayici:
    """Ultralytics YOLO on the CPU. Only the given file is loaded; nothing is downloaded or sent anywhere."""

    def __init__(
        self,
        model: Path,
        imgsz: int | None = None,
        conf: float = 0.25,
        sinif: str | int | None = None,
        cekirdek: int = 4,
    ) -> None:
        """model: an existing .pt file (inspect_model first); imgsz [px]: None = the training size stored in the file;
        conf: (0..1] threshold; sinif: name or number, None = "person"; cekirdek: torch threads, the rest of the CPU
        stays with Gazebo and PX4."""
        if not model.is_file():  # ultralytics would look for a missing file on the internet
            raise FileNotFoundError(_missing_text(model, load_catalog()))
        yolo = _ultralytics()
        import cv2
        import torch

        self._torch, self._cv2 = torch, cv2
        self.cekirdek = cekirdek
        self.conf = conf
        self._model = yolo(str(model))
        if self._model.task != "detect":
            raise ValueError(f"{model.name}: algılama (detect) modeli değil, görevi {self._model.task}")
        self.names = {int(k): str(v) for k, v in self._model.names.items()}
        self.sinif = resolve_class(self.names, sinif)
        self.stride = int(self._model.model.stride.max())  # [px] the input size must be a multiple of it
        trained = self._model.overrides.get("imgsz")
        self.trained_imgsz = trained if isinstance(trained, int) else None
        self.imgsz = imgsz if imgsz is not None else self.trained_imgsz
        if self.imgsz is None:
            raise ValueError(f"{model.name}: eğitim imgsz değeri dosyada yok; --imgsz ile verin")
        if self.imgsz % self.stride:
            low = self.imgsz // self.stride * self.stride
            raise ValueError(
                f"algilama.imgsz: modelin adımının ({self.stride} px) katı olmalı (--imgsz), gelen: {self.imgsz}; "
                f"ör. {max(low, self.stride)} ya da {low + self.stride}"
            )
        self.last_model_ms = float("nan")  # [ms] colour conversion + pre-processing + inference + post-processing
        self.last_stages_ms: dict[str, float] = {}  # [ms] ultralytics' own preprocess / inference / postprocess
        # the first call builds the predictor; it also sets torch's threads to ultralytics' own count (CPU count - 1,
        # at most 8, torch_utils.select_device), so the thread count is set after it
        self.warmup_ms = self._timed(np.zeros((self.imgsz, self.imgsz, 3), np.uint8))[1]
        torch.set_num_threads(cekirdek)

    def algila(self, kare_rgb: np.ndarray) -> list[Kutu]:
        if kare_rgb.dtype != np.uint8 or kare_rgb.ndim != 3 or kare_rgb.shape[2] != 3:
            raise ValueError(
                f"kare RGB uint8 (yükseklik, genişlik, 3) olmalı, gelen: {kare_rgb.dtype} {kare_rgb.shape}"
            )
        if self._torch.get_num_threads() != self.cekirdek:
            self._torch.set_num_threads(self.cekirdek)
        found, self.last_model_ms = self._timed(kare_rgb)
        return found

    def _timed(self, kare_rgb: np.ndarray) -> tuple[list[Kutu], float]:
        start = time.perf_counter()
        bgr = self._cv2.cvtColor(kare_rgb, self._cv2.COLOR_RGB2BGR)  # ultralytics reads numpy frames as OpenCV BGR
        result = self._model.predict(
            bgr, imgsz=self.imgsz, conf=self.conf, classes=[self.sinif], device="cpu", verbose=False, save=False
        )[0]
        height, width = kare_rgb.shape[:2]
        found = boxes_of(result, self.names, (width, height))
        self.last_stages_ms = {k: float(v) for k, v in result.speed.items()}
        return found, (time.perf_counter() - start) * 1000.0


# Model process ("spawn"): frame reader -> camera defects -> detector, apart from the main process so that torch does
# not compete with it for the GIL and gz-transport is never used across a fork.

READY_TIMEOUT = 180.0  # [s] for the model to load and warm up (~5 s alone; more while Gazebo starts)
STOP_TIMEOUT = 15.0  # [s] for the model process to finish its frame and send its books
TAKE_TIMEOUT = 0.2  # [s] the model process looks at the stop request this often while no frame comes
MESSAGE_TIMEOUT = 1.0  # [s] the main process checks that the model process is alive this often


class ModelError(RuntimeError):
    """The model process did not come up: it refused a setting (imgsz, class...) or did not load."""


@dataclass(frozen=True)
class ModelSettings:
    """Everything the model process needs; picklable, it crosses into a spawned process."""

    model: Path  # an existing file (inspect_model first)
    imgsz: int | None  # [px] None: the training size stored in the file
    conf: float
    sinif: str | int | None
    cekirdek: int  # torch threads
    kusurlar: dict = field(default_factory=dict)  # the scenario's camera defects (off in Faz A)
    topic: str = goruntu.CAMERA_TOPIC


@dataclass(frozen=True)
class FrameResult:
    """One processed frame, model process -> main process. Wall times are time.monotonic [s]."""

    t: float  # [s, sim] capture (Gazebo header stamp)
    sira: int  # the reader's frame counter
    varis: float  # arrival at the reader
    basla: float  # the model process took the frame from the slot
    bitis: float  # the boxes were ready
    cozme_ms: float  # [ms] decoding the message
    kusur_ms: float  # [ms] camera defects stage
    model_ms: float  # [ms] the detector's algila(): colour conversion, pre-processing, inference, post-processing
    kutular: tuple[Kutu, ...]
    atlanan: tuple[goruntu.Skipped, ...]  # frames replaced while the model worked on the previous frame


def process(
    raw: bytes,
    arrival: goruntu.Arrival,
    replaced: list[goruntu.Arrival],
    defects: kusurlar.KameraKusurlari,
    detector: Algilayici,
    basla: float,
) -> FrameResult:
    """One frame taken from the slot at monotonic time `basla`: decode, camera defects, detector; each step timed."""
    start = time.perf_counter()
    frame = goruntu.decode(raw, arrival)
    decoded = time.perf_counter()
    image = defects.uygula(frame.rgb, frame.t)
    staged = time.perf_counter()
    boxes = detector.algila(image)
    done = time.perf_counter()
    return FrameResult(
        t=frame.t,
        sira=frame.sira,
        varis=frame.varis,
        basla=basla,
        bitis=time.monotonic(),
        cozme_ms=(decoded - start) * 1000.0,
        kusur_ms=(staged - decoded) * 1000.0,
        model_ms=(done - staged) * 1000.0,
        kutular=tuple(boxes),
        atlanan=tuple(goruntu.Skipped(a.sira, goruntu.stamp(a.head), a.varis) for a in replaced),
    )


def _error_text(e: BaseException) -> str:
    """A setting the model refuses reads like a scenario error; anything else keeps its type."""
    return str(e) if isinstance(e, ValueError | FileNotFoundError) else f"{type(e).__name__}: {e}"


def model_process(settings: ModelSettings, results: "mp.Queue", stop: "mp.synchronize.Event") -> None:
    """Entry of the model process. Messages to the main process, in this order through the FIFO `results`:
    ("hazir", info) or ("hata", text); then ("kare", FrameResult) per processed frame; then ("hata", text) if a
    frame failed and ("bitti", books) when `stop` is set."""
    # Ctrl+C in the terminal reaches the whole process group: the main process stops this one through `stop`, so the
    # books still come
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        defects = kusurlar.KameraKusurlari(settings.kusurlar)
        detector = YoloAlgilayici(settings.model, settings.imgsz, settings.conf, settings.sinif, settings.cekirdek)
        reader = goruntu.FrameReader(settings.topic)
    except Exception as e:  # noqa: BLE001 - the main process reports it and starts nothing
        results.put(("hata", _error_text(e)))
        return
    info = {
        "siniflar": detector.names,
        "sinif": detector.sinif,
        "sinif_adi": detector.names[detector.sinif],
        "imgsz": detector.imgsz,
        "egitim_imgsz": detector.trained_imgsz,
        "adim": detector.stride,
        "conf": detector.conf,
        "cekirdek": detector.cekirdek,
        "isinma_ms": detector.warmup_ms,
        "kusurlar_etkin": defects.etkin,
        "konu": settings.topic,
        "pid": os.getpid(),
    }
    results.put(("hazir", info))
    processed = 0
    try:
        while not stop.is_set():
            taken = reader.take(TAKE_TIMEOUT)
            if taken is None:
                continue
            basla = time.monotonic()
            results.put(("kare", process(*taken, defects, detector, basla)))
            processed += 1
    except Exception:  # noqa: BLE001 - reported with the books; the main process marks the run
        results.put(("hata", "model süreci bir karede durdu:\n" + traceback.format_exc()))
    reader.close()
    results.put(("bitti", reader.slot.counts() | {"islenen": processed}))


class ModelProcess:
    """The model process seen from the main process. start() waits until the detector is loaded; a thread then hands
    every FrameResult to on_result(result, alinma) in order (alinma: monotonic time it reached the main process)."""

    def __init__(self, settings: ModelSettings, on_result: Callable[[FrameResult, float], None]) -> None:
        ctx = mp.get_context("spawn")
        self._queue = ctx.Queue()
        self._stop = ctx.Event()
        self._proc = ctx.Process(
            target=model_process, args=(settings, self._queue, self._stop), name="tez-model", daemon=True
        )
        self._on_result = on_result
        self._thread: threading.Thread | None = None
        self.info: dict | None = None  # the "hazir" message
        self.books: dict | None = None  # the "bitti" message (goruntu.LatestFrame.counts + islenen)
        self.errors: list[str] = []
        self.results = 0  # FrameResults handed to on_result
        self.last: FrameResult | None = None

    def start(self, timeout: float = READY_TIMEOUT) -> dict:
        """Start the process and wait for the loaded detector; ModelError with the model's own message if it refused a
        setting or did not come up."""
        self._proc.start()
        t_end = time.monotonic() + timeout
        while self.info is None:
            try:
                kind, payload = self._queue.get(timeout=MESSAGE_TIMEOUT)
            except queue.Empty:
                if not self._proc.is_alive():
                    raise ModelError(f"model süreci açılırken kapandı (çıkış kodu {self._proc.exitcode})") from None
                if time.monotonic() > t_end:
                    self._stop.set()
                    self._end()
                    raise ModelError(f"model süreci {timeout:.0f} s içinde hazır olmadı") from None
                continue
            if kind == "hata":
                self._end()
                raise ModelError(payload)
            self.info = payload
        self._thread = threading.Thread(target=self._drain, name="tez-model-sonuclari", daemon=True)
        self._thread.start()
        return self.info

    def _drain(self) -> None:
        while True:
            try:
                kind, payload = self._queue.get(timeout=MESSAGE_TIMEOUT)
            except queue.Empty:
                if not self._proc.is_alive():
                    self.errors.append(f"model süreci beklenmedik biçimde kapandı (çıkış kodu {self._proc.exitcode})")
                    return
                continue
            received = time.monotonic()
            if kind == "kare":
                self.results += 1
                self.last = payload
                try:
                    self._on_result(payload, received)
                except Exception as e:  # noqa: BLE001 - a writing error must not stop the books
                    self.errors.append(f"model sonucu yazılamadı: {type(e).__name__}: {e}")
            elif kind == "hata":
                self.errors.append(payload)
            elif kind == "bitti":
                self.books = payload
                return

    @property
    def running(self) -> bool:
        return self._proc.is_alive() and self.books is None

    def stop(self, timeout: float = STOP_TIMEOUT) -> dict | None:
        """Ask the model process to finish its frame and wait for its books (None if they never came). Repeatable."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
        self._end()
        return self.books

    def _end(self) -> None:
        if self._proc.pid is None:
            return
        self._proc.join(STOP_TIMEOUT)
        if self._proc.is_alive():
            self.errors.append("model süreci kapanmadı, sonlandırıldı")
            self._proc.terminate()
            self._proc.join(5)
            if self._proc.is_alive():
                self._proc.kill()
                self._proc.join(5)


# algilama.csv: one row per processed frame; kutular.csv: every box. t_us = round(t * 1e6) is the key of
# dogru_cevap.csv (kayit.py). Wall times: monotonic [s]; *_sim: the same moments in sim time (SimClock).
ROW_COLUMNS = (
    "t_us",
    "t",  # [s sim] capture
    "sira",
    "onceki_atlanan",  # frames replaced while the model worked on the previous one
    "varis",
    "basla",
    "bitis",
    "alinma",  # the result reached the main process
    "varis_sim",
    "basla_sim",
    "bitis_sim",
    "ulasma_ms",  # [ms sim] varis - t
    "bekleme_ms",  # [ms] basla - varis
    "cozme_ms",
    "kusur_ms",
    "model_ms",
    "islem_ms",  # [ms] bitis - basla
    "teslim_ms",  # [ms] alinma - bitis: time in the FIFO; stays small when nothing piles up
    "kutu_sayisi",
)
BOX_COLUMNS = ("t_us", "t", "sira", "kutu", "u0", "v0", "u1", "v1", "guven", "sinif", "sinif_adi")
IOU_MATCH = 0.5  # a model box with this IoU to the target's referee box found the target (spec "Ölçüt Tanımları")


def time_key(t: float) -> int:
    """Row key shared with dogru_cevap.csv: the frame's sim time in microseconds."""
    return round(t * 1e6)


def _cell(value: object) -> object:
    if isinstance(value, float):
        return "" if math.isnan(value) else f"{value:.6f}"
    return value


class DetectionLog:
    """Writes every FrameResult to algilama.csv and kutular.csv as it comes, and keeps them for the run's numbers.
    The files are created with the first result (a run whose model never saw a frame leaves none)."""

    def __init__(self, out: Path, clock: goruntu.SimClock) -> None:
        self._out = out
        self._clock = clock
        self._files: list = []
        self._rows = self._boxes = None
        self._lock = threading.Lock()
        self.rows: list[dict] = []
        self.boxes: dict[int, tuple[Kutu, ...]] = {}
        self.skipped: list[goruntu.Skipped] = []

    def _open(self) -> None:
        self._files = [(self._out / n).open("w", newline="", encoding="utf-8") for n in ("algilama.csv", "kutular.csv")]
        self._rows, self._boxes = (csv.writer(f) for f in self._files)
        self._rows.writerow(ROW_COLUMNS)
        self._boxes.writerow(BOX_COLUMNS)

    def add(self, r: FrameResult, alinma: float) -> None:
        to_sim = self._clock.to_sim
        varis_sim = to_sim(r.varis)
        row = {
            "t_us": time_key(r.t),
            "t": r.t,
            "sira": r.sira,
            "onceki_atlanan": len(r.atlanan),
            "varis": r.varis,
            "basla": r.basla,
            "bitis": r.bitis,
            "alinma": alinma,
            "varis_sim": varis_sim,
            "basla_sim": to_sim(r.basla),
            "bitis_sim": to_sim(r.bitis),
            "ulasma_ms": (varis_sim - r.t) * 1000.0,
            "bekleme_ms": (r.basla - r.varis) * 1000.0,
            "cozme_ms": r.cozme_ms,
            "kusur_ms": r.kusur_ms,
            "model_ms": r.model_ms,
            "islem_ms": (r.bitis - r.basla) * 1000.0,
            "teslim_ms": (alinma - r.bitis) * 1000.0,
            "kutu_sayisi": len(r.kutular),
        }
        with self._lock:
            if not self._files:
                self._open()
            self.rows.append(row)
            self.boxes[row["t_us"]] = r.kutular
            self.skipped.extend(r.atlanan)
            self._rows.writerow([_cell(row[c]) for c in ROW_COLUMNS])
            for i, b in enumerate(r.kutular):
                values = asdict(b)
                self._boxes.writerow([_cell(v) for v in (row["t_us"], r.t, r.sira, i, *values.values())])
            for f in self._files:
                f.flush()

    def close(self) -> None:
        with self._lock:
            for f in self._files:
                f.close()

    def metrics(self, start: float, end: float, referee: list[dict]) -> dict:
        """The run's frame and time numbers in the sim window start..end [s] (temporary; olcum.py in task group 7).

        uretilen: frames that reached the reader in the window (processed + replaced); kamera_karesi: camera frames
        of the referee (camera_info) in the window, okuyucuya_ulasmayan: those the reader never got. The IoU check
        (task group 4): processed frames with a box of IoU >= 0.5 to the target's referee box."""

        def inside(t: float) -> bool:
            return start <= t <= end

        with self._lock:
            rows = [r for r in self.rows if inside(r["t"])]
            skipped = [s for s in self.skipped if inside(s.t)]  # NaN (header not read) is never inside
            unknown = sum(math.isnan(s.t) for s in self.skipped)
            boxes = dict(self.boxes)
        received = {r["t_us"] for r in rows} | {time_key(s.t) for s in skipped}
        frames = {time_key(x["t"]): x for x in referee if inside(x["t"])}
        produced = len(rows) + len(skipped)
        m = {
            "uretilen": produced,
            "islenen": len(rows),
            "atlanan": len(skipped),
            "atlanan_kare_orani": 1.0 - len(rows) / produced if produced else math.nan,
            "islenen_kare_hizi_hz": len(rows) / (end - start) if end > start else math.nan,
            "kamera_karesi": len(frames),
            "okuyucuya_ulasmayan": len(set(frames) - received),
            "zamani_okunamayan_atlanan": unknown,
        }
        for name in ("model_ms", "cozme_ms", "kusur_ms", "ulasma_ms", "bekleme_ms", "islem_ms", "teslim_ms"):
            values = [r[name] for r in rows if not math.isnan(r[name])]
            m[f"{name}_ort"] = statistics.fmean(values) if values else math.nan
            if name in ("model_ms", "ulasma_ms", "islem_ms"):
                m[f"{name}_p95"] = float(np.percentile(values, 95)) if values else math.nan
            if name in ("model_ms", "teslim_ms"):
                m[f"{name}_max"] = max(values) if values else math.nan
        visible = matched = 0
        best = math.nan
        for r in rows:
            ref = frames.get(r["t_us"])
            if ref is None:
                continue
            target = tuple(float(ref.get(f"hedef_kutu_{k}", math.nan)) for k in ("u0", "v0", "u1", "v1"))
            visible += bool(ref.get("gorunur"))
            score = max((iou(b, target) for b in boxes.get(r["t_us"], ())), default=0.0)
            best = score if math.isnan(best) else max(best, score)
            matched += score >= IOU_MATCH
        m |= {"hedef_gorunur_islenen": visible, "iou05_kare_sayisi": matched, "iou_max": best}
        return m
