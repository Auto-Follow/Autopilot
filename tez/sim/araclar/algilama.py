"""Person detector of the simulation: the detector interface, the model file and the YOLO detector on the laptop CPU.

The whole interface is Algilayici.algila(kare_rgb) -> list[Kutu]: one drone camera frame in, the boxes of the wanted
class out. Vision's detector (m08/m10) plugs in as another class with the same method; nothing here reads ../Vision
(rule 7). ultralytics and torch are imported only inside YoloAlgilayici, so the unit tests run without them.

Model file: --model > algilama.model (hedef.load already puts the first over the second) > MODEL_DIR/DEFAULT_MODEL.
Model files never go into a repo (rule 9); tez/sim/modeller.yaml records the known ones with their sha256.
"""

import atexit
import functools
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
import yaml

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
    (width, height) [px], the most confident first."""
    width, height = size
    corners = np.clip(np.asarray(xyxy, dtype=float).reshape(-1, 4), 0.0, [width, height, width, height])
    found = [
        Kutu(float(u0), float(v0), float(u1), float(v1), float(c), int(k), names.get(int(k), str(int(k))))
        for (u0, v0, u1, v1), c, k in zip(corners, np.asarray(conf), np.asarray(cls), strict=True)
    ]
    return sorted(found, key=lambda b: -b.guven)


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
        b = result.boxes
        height, width = kare_rgb.shape[:2]
        found = to_boxes(b.xyxy.numpy(), b.conf.numpy(), b.cls.numpy(), self.names, (width, height))
        self.last_stages_ms = {k: float(v) for k, v in result.speed.items()}
        return found, (time.perf_counter() - start) * 1000.0
