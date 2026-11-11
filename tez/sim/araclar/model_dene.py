#!/usr/bin/env python3
"""Try the person detector on pictures, or on frames of a scenario rendered in Gazebo, and look at its boxes. No PX4.

    P=~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python
    $P tez/sim/araclar/model_dene.py --kare foto.jpg                         # any PNG/JPG; repeat --kare for more
    $P tez/sim/araclar/model_dene.py --senaryo kalabalik_park --zaman 66,73   # renders the scenario first (~1 min)
    ... --kamera 0,0,10,45,0      with --senaryo: camera x, y, z [m], pitch down [deg], yaw [deg] (as onizleme.py)
    ... --model YOL --imgsz PX --conf 0.25 --sinif AD|NO --cekirdek 4      the algilama settings of a scenario
    ... --tekrar N                run the model N times on every frame (model_ms: mean, min, max)
    ... --cikti KLASOR

Red: the model's boxes with their confidence. With --senaryo also the referee's boxes of the same moment
(segmentation camera): target blue, other people orange. Prints the model file and its sha256, the classes, the
input size and model_ms per frame. The scenario's own algilama block is not used here, only these options.
Output: --kare -> <name>_model.jpg next to the picture (or in --cikti); --senaryo -> the frames (kare_<t>.png) and
kare_<t>_model.jpg in tez/sim/sonuclar/<date>_model_<scenario>/ (or --cikti).
"""

import argparse
import datetime as dt
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import algilama
import hedef

MODEL_BOX = (230, 25, 25)  # red; the referee's boxes are blue (target) and orange (others), as in onizleme.py
TEXT_SIZE = 34  # [px] on the 2304 x 1296 frames
# Ubuntu's fonts-dejavu-core; PIL's built-in font has no Turkish letters (ç, ğ, ı, ş, ü came out as boxes)
FONT_FILE = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
JPEG_QUALITY = 90


@dataclass
class Result:
    """One frame through the detector."""

    name: str
    boxes: list[algilama.Kutu]
    times_ms: list[float]  # [ms] one per run, measured around algila()
    stages_ms: dict[str, float]  # [ms] the detector's own split of its last run, if it reports one
    output: Path | None = None


def detection_settings(args: argparse.Namespace) -> hedef.Detection:
    """The options checked with the rules of a scenario's algilama block (hedef.read_detection)."""
    given = {"model": args.model, "imgsz": args.imgsz, "conf": args.conf, "sinif": args.sinif}
    given["cekirdek"] = args.cekirdek
    return hedef.read_detection({k: v for k, v in given.items() if v is not None})


def detect(detector: algilama.Algilayici, frame: np.ndarray, name: str, repeat: int = 1) -> Result:
    times, boxes = [], []
    for _ in range(repeat):
        start = time.perf_counter()
        boxes = detector.algila(frame)
        times.append((time.perf_counter() - start) * 1000.0)
    return Result(name, boxes, times, dict(getattr(detector, "last_stages_ms", {})))


def draw(img: np.ndarray, boxes: list[algilama.Kutu], lines: list[str]) -> np.ndarray:
    """The frame with the model's boxes (confidence under each box) and the text lines at the bottom left."""
    pil = Image.fromarray(img)
    d = ImageDraw.Draw(pil)
    font = ImageFont.truetype(FONT_FILE, TEXT_SIZE) if FONT_FILE.is_file() else ImageFont.load_default(size=TEXT_SIZE)
    text = {"font": font, "stroke_width": 3, "stroke_fill": (0, 0, 0)}
    for b in boxes:
        # pixel edges u0 <= u < u1 -> PIL's inclusive corners
        d.rectangle([b.u0, b.v0, max(b.u0, b.u1 - 1), max(b.v0, b.v1 - 1)], outline=MODEL_BOX, width=4)
        below = min(b.v1 + 4, img.shape[0] - TEXT_SIZE - 4)
        d.text((b.u0, below), f"{b.sinif_adi} {b.guven:.2f}", fill=MODEL_BOX, **text)
    for i, line in enumerate(reversed(lines)):  # above the "t = ..." line of onizleme.Frames.annotate
        d.text((40, img.shape[0] - 130 - i * (TEXT_SIZE + 16)), line, fill=(255, 255, 255), **text)
    return np.asarray(pil)


def summary(r: Result) -> str:
    found = ", ".join(f"{b.sinif_adi} {b.guven:.2f}" for b in r.boxes) or "kutu yok"
    ms = f"model_ms {r.times_ms[-1]:.0f} ms"
    if len(r.times_ms) > 1:
        ms = (
            f"model_ms ort. {statistics.fmean(r.times_ms):.0f} ms (en az {min(r.times_ms):.0f}, en çok "
            f"{max(r.times_ms):.0f}, {len(r.times_ms)} çalıştırma)"
        )
    split = r.stages_ms
    if {"preprocess", "inference", "postprocess"} <= set(split):
        ms += (
            f" [ön işleme {split['preprocess']:.1f} + çıkarım {split['inference']:.1f} + son işleme "
            f"{split['postprocess']:.1f} ms]"
        )
    return f"{r.name}: {len(r.boxes)} kutu ({found}) · {ms}"


def header(model: algilama.ModelFile, det: hedef.Detection, imgsz: int, r: Result, referee: bool) -> list[str]:
    """Text drawn on the output: model, settings, time; which colour is what."""
    legend = "kırmızı: model (güven)" + (" · mavi: hakem hedef · turuncu: hakem diğer insanlar" if referee else "")
    return [
        f"{model.path.name} · imgsz {imgsz} · conf {det.conf} · {det.cores} çekirdek · CPU · "
        f"model_ms {statistics.fmean(r.times_ms):.0f} ms · {len(r.boxes)} kutu",
        legend,
    ]


def output_path(picture: Path, out: Path | None) -> Path:
    return (out or picture.parent) / f"{picture.stem}_model.jpg"


def save(img: np.ndarray, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img).save(path, quality=JPEG_QUALITY)
    return path


Lines = Callable[[Result], list[str]]


def run_pictures(
    paths: list[Path], detector: algilama.Algilayici, lines: Lines, out: Path | None, repeat: int
) -> list[Result]:
    """--kare: every picture through the detector; `lines(result)` gives the text drawn on its copy."""
    results = []
    for path in paths:
        frame = np.asarray(Image.open(path).convert("RGB"))
        r = detect(detector, frame, path.name, repeat)
        r.output = save(draw(frame, r.boxes, lines(r)), output_path(path, out))
        results.append(r)
    return results


def numbers(text: str, flag: str, count: int | None = None) -> list[float]:
    """'0,0,10,45,0' -> [0.0, 0.0, 10.0, 45.0, 0.0]; a wrong form is refused with the flag."""
    try:
        values = [float(v) for v in text.split(",")]
    except ValueError:
        values = []
    if not values or (count is not None and len(values) != count):
        how = f"{count} sayı" if count else "en az bir sayı"
        raise ValueError(f"{flag}: virgülle ayrılmış {how} olmalı, gelen: {text!r}")
    return values


def run_scenario(args: argparse.Namespace, detector: algilama.Algilayici, lines: Lines, out: Path) -> list[Result]:
    """--senaryo: render the scenario's frames with onizleme.py's camera (Gazebo, no PX4), then the detector on
    each; the referee's boxes are drawn from the segmentation frame of the same moment."""
    import onizleme  # Gazebo's Python bindings, only needed here
    from simulasyon import running

    if running():
        raise RuntimeError("Zaten çalışan bir PX4 veya Gazebo var; önce onu kapatın (ya da bitmesini bekleyin)")
    cam, wanted = numbers(args.kamera, "--kamera", 5), numbers(args.zaman, "--zaman")
    out.mkdir(parents=True, exist_ok=True)
    world, _ = onizleme.world_text(args.senaryo, None, onizleme.camera_sdf(*cam, 20, True), out)
    frames = onizleme.Frames(wanted, None, onizleme.people_of(args.senaryo))
    if not onizleme.capture(world, frames, out):
        raise RuntimeError(f"Gazebo kareleri gelmedi (bkz. {out / 'sim.log'})")
    results = []
    for t, frame in sorted(frames.photos.items()):
        name = f"kare_{t:07.2f}"
        save_raw = out / f"{name}.png"
        Image.fromarray(frame).save(save_raw)  # the frame as the model saw it: --kare can run it again
        r = detect(detector, frame, save_raw.name, args.tekrar)
        r.output = save(draw(frames.annotate(t, frame), r.boxes, lines(r)), out / f"{name}_model.jpg")
        results.append(r)
    return results


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--kare", action="append", type=Path, metavar="RESİM", help="PNG/JPG dosyası (birden çok)")
    src.add_argument("--senaryo", help="senaryo adı veya .yaml yolu: kareleri Gazebo'da çekilir (PX4 yok)")
    ap.add_argument("--zaman", default="3", help="--senaryo: kare zamanları [s], virgülle (varsayılan 3)")
    ap.add_argument("--kamera", default="0,0,10,45,0", help="--senaryo: x,y,z,eğim_derece,yön_derece (onizleme.py)")
    g = ap.add_argument_group("algılama (senaryodaki algilama bloğunun kurallarıyla)")
    g.add_argument(
        "--model", metavar="YOL", help="model dosyası, .pt; varsayılan ~/auto-follow-modeller/ içindeki v0.2"
    )
    g.add_argument("--imgsz", type=int, metavar="PX", help="model giriş boyutu; varsayılan .pt'deki eğitim değeri")
    g.add_argument("--conf", type=float, help="güven eşiği (0..1]; varsayılan 0.25")
    g.add_argument("--sinif", metavar="AD|NO", help="sınıf adı veya numarası; varsayılan adı 'person' olan")
    g.add_argument("--cekirdek", type=int, metavar="N", help="torch iş parçacığı sayısı; varsayılan 4")
    ap.add_argument("--tekrar", type=int, default=1, metavar="N", help="her karede modeli N kez çalıştır (süre için)")
    ap.add_argument("--cikti", type=Path, help="çıktı klasörü")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.tekrar < 1:
            raise ValueError(f"--tekrar en az 1 olmalı, gelen: {args.tekrar}")
        det = detection_settings(args)
        missing = [p for p in args.kare or [] if not p.is_file()]
        if missing:
            raise FileNotFoundError(f"resim yok: {', '.join(map(str, missing))}")
        if args.senaryo:  # a broken scenario or option is reported before the model loads
            hedef.load(args.senaryo)
            numbers(args.kamera, "--kamera", 5)
            numbers(args.zaman, "--zaman")
        model = algilama.inspect_model(algilama.model_path(det.model), algilama.load_catalog())
    except (ValueError, FileNotFoundError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2

    known = f"modeller.yaml'da {model.known.name}" if model.known else "modeller.yaml'da kayıtlı değil"
    print(f"Model: {model.path} ({model.size} bayt)\n  sha256 {model.sha256} ({known})", flush=True)
    if model.warning:
        print(f"  UYARI: {model.warning}", flush=True)
    print("  Model yükleniyor (ultralytics, CPU; indirme ve analitik kapalı)...", flush=True)
    try:
        detector = algilama.YoloAlgilayici(model.path, det.imgsz, det.conf, det.class_name, det.cores)
    except (ValueError, ImportError, RuntimeError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 2
    print(
        f"  sınıflar {detector.names} -> {detector.sinif} ({detector.names[detector.sinif]}) · imgsz {detector.imgsz} "
        f"(eğitim {detector.trained_imgsz}, adım {detector.stride}) · conf {det.conf} · {det.cores} çekirdek · "
        f"ilk çağrı (hazırlık) {detector.warmup_ms:.0f} ms",
        flush=True,
    )

    def lines(r: Result) -> list[str]:
        return header(model, det, detector.imgsz, r, referee=args.senaryo is not None)

    try:
        if args.kare:
            results = run_pictures(args.kare, detector, lines, args.cikti, args.tekrar)
        else:
            name = Path(args.senaryo).stem
            out = args.cikti or algilama.SIM_DIR / "sonuclar" / f"{dt.datetime.now():%Y%m%d_%H%M%S}_model_{name}"
            results = run_scenario(args, detector, lines, out)
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"Hata: {e}", file=sys.stderr)
        return 1
    for r in results:
        print(summary(r))
        print(f"  -> {r.output}")
    every = [ms for r in results for ms in r.times_ms]
    print(f"Ortalama model_ms: {statistics.fmean(every):.0f} ms ({len(every)} çalıştırma, {len(results)} kare)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
