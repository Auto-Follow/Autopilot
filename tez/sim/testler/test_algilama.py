"""Model file, its sha256 record, the class of a detector, its boxes and one frame through the model stage, without
ultralytics, torch or Gazebo."""

import csv
import hashlib
import math
import re
import sys
from pathlib import Path

import numpy as np
import pytest
from gz.msgs10.image_pb2 import Image

import algilama
import goruntu
import hedef
import kusurlar

SCENARIO = """
ad: model_deneme
takip: {kaynak: yok}
hedef: {baslangic: [10, 0], yol: [{nokta: [20, 0], hiz_mps: 1.0}]}
"""


def catalog(tmp_path: Path, digest: str | None, name: str = algilama.DEFAULT_MODEL) -> dict[str, algilama.KnownModel]:
    path = tmp_path / "modeller.yaml"
    sha = f"'{digest}'" if digest is not None else "null"  # quoted: YAML reads a digits-only digest as a number
    path.write_text(
        f"modeller:\n  - {{ad: {name}, sha256: {sha}, boyut_bayt: 5, kaynak: Vision ebff718, alma: git show}}\n",
        encoding="utf-8",
    )
    return algilama.load_catalog(path)


def test_model_path_priority(tmp_path: Path) -> None:
    """--model > algilama.model > ~/auto-follow-modeller/person_detection_model_v0.2.pt (hedef.load merges the
    first two; algilama.model_path adds the default)."""
    scenario = tmp_path / "s.yaml"
    scenario.write_text(SCENARIO + "algilama: {model: yaml.pt}\n", encoding="utf-8")
    cli = hedef.CommandLine(model=str(tmp_path / "cli.pt"))
    assert algilama.model_path(hedef.load(str(scenario), cli).detection.model) == tmp_path / "cli.pt"
    assert algilama.model_path(hedef.load(str(scenario)).detection.model) == Path.cwd() / "yaml.pt"

    scenario.write_text(SCENARIO, encoding="utf-8")
    assert algilama.model_path(hedef.load(str(scenario)).detection.model) == algilama.MODEL_DIR / algilama.DEFAULT_MODEL
    assert algilama.MODEL_DIR == Path.home() / "auto-follow-modeller"
    assert algilama.model_path(None, tmp_path) == tmp_path / "person_detection_model_v0.2.pt"


def test_missing_model_file_says_where_to_get_it(tmp_path: Path) -> None:
    known = catalog(tmp_path, "0" * 64)
    with pytest.raises(FileNotFoundError) as error:
        algilama.inspect_model(tmp_path / algilama.DEFAULT_MODEL, known)
    text = str(error.value)
    assert str(tmp_path / algilama.DEFAULT_MODEL) in text
    assert "Vision ebff718" in text and "git show" in text and "--model" in text  # source, how to get it, other file

    with pytest.raises(FileNotFoundError, match=re.escape("modeller.yaml'da kayıtlı değil")) as error:
        algilama.inspect_model(tmp_path / "baska.pt", known)
    assert algilama.DEFAULT_MODEL in str(error.value)  # lists the known files


def test_sha256_is_compared_with_the_record(tmp_path: Path) -> None:
    model = tmp_path / algilama.DEFAULT_MODEL
    model.write_bytes(b"model")
    digest = hashlib.sha256(b"model").hexdigest()
    assert algilama.file_sha256(model) == digest

    same = algilama.inspect_model(model, catalog(tmp_path, digest))
    assert (same.sha256, same.size, same.warning) == (digest, 5, None)
    assert same.known is not None and same.known.name == algilama.DEFAULT_MODEL

    other = algilama.inspect_model(model, catalog(tmp_path, "f" * 64))
    assert other.sha256 == digest and other.warning is not None
    assert digest in other.warning and "f" * 64 in other.warning

    renamed = tmp_path / "kopya.pt"  # the same file under another name is still the known model
    renamed.write_bytes(b"model")
    assert algilama.inspect_model(renamed, catalog(tmp_path, digest)).known.name == algilama.DEFAULT_MODEL

    unrecorded = algilama.inspect_model(model, catalog(tmp_path, None))  # yolov8s.pt until task group 13
    assert unrecorded.warning is None and unrecorded.known.sha256 is None


def test_catalog_in_the_repo_and_its_checks(tmp_path: Path) -> None:
    known = algilama.load_catalog()
    v02 = known[algilama.DEFAULT_MODEL]
    assert v02.sha256 == "c5f6838be50c2c09ca788e97381b68567f0df3f20e430905142ce88f8abaa440"
    assert v02.size == 22_525_930 and "ebff718" in v02.source
    coco = known["yolov8s.pt"]  # the comparison model: its address is known, its digest once fetched (tasks.md 13.4)
    assert coco.sha256 is None and coco.size is None
    assert "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s.pt" in coco.fetch

    bad = tmp_path / "modeller.yaml"
    entry = "  - {ad: a.pt, sha256: null, kaynak: x, alma: y}\n"
    for text, message in [
        ("  - {ad: a.pt, sha256: 12, boyut_bayt: 1, kaynak: x, alma: y}\n", "sha256"),
        ("  - {ad: a.pt, sha256: null, kaynak: x, alma: y, renk: mavi}\n", "renk"),
        ("  - {ad: a.pt, sha256: null, kaynak: x}\n", "alma"),
        (entry + entry, "iki kez"),
    ]:
        bad.write_text("modeller:\n" + text, encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            algilama.load_catalog(bad)


def test_model_folder_check_of_kur_sh(tmp_path: Path) -> None:
    """kur.sh ends with algilama.py: every file modeller.yaml records, as found in the model folder (same sha256 and
    size, another file, no digest recorded yet, missing: with where to get it), then the folder's unrecorded .pt
    files; nothing is fetched and a missing model is a warning, not an error (exit code 0)."""
    folder = tmp_path / "modeller"
    folder.mkdir()
    (folder / "a.pt").write_bytes(b"model")
    (folder / "b.pt").write_bytes(b"other")
    (folder / "c.pt").write_bytes(b"coco")
    (folder / "x.pt").write_bytes(b"model")  # an unrecorded copy of a.pt
    path = tmp_path / "modeller.yaml"
    digest = hashlib.sha256(b"model").hexdigest()
    path.write_text(
        "modeller:\n"
        f"  - {{ad: a.pt, sha256: '{digest}', boyut_bayt: 5, kaynak: Vision ebff718, alma: git show a}}\n"
        f"  - {{ad: b.pt, sha256: '{'e' * 64}', boyut_bayt: 5, kaynak: Vision, alma: git show b}}\n"
        "  - {ad: c.pt, sha256: null, kaynak: GitHub, alma: curl c}\n"
        "  - {ad: d.pt, sha256: null, kaynak: GitHub v8.4.0, alma: curl -fL -o d.pt https://example.org/d.pt}\n",
        encoding="utf-8",
    )
    catalog = algilama.load_catalog(path)
    entries = algilama.check_folder(folder, catalog)
    assert [(e.name, e.state) for e in entries] == [
        ("a.pt", "tamam"),
        ("b.pt", "farkli"),
        ("c.pt", "ozetsiz"),
        ("d.pt", "eksik"),
        ("x.pt", "kayitsiz"),
    ]
    assert entries[2].sha256 == hashlib.sha256(b"coco").hexdigest() and entries[2].size == 4
    text = "\n".join(algilama.folder_lines(entries, folder))
    assert "TAMAM" in text and "FARKLI" in text and "EKSİK" in text and "KAYITSIZ" in text
    assert entries[2].sha256 in text  # the digest to write into modeller.yaml
    assert "curl -fL -o d.pt https://example.org/d.pt" in text and "GitHub v8.4.0" in text  # where to get it
    assert "a.pt'nin kopyası" in text and "1 tamam" in text and "1 eksik" in text

    nothing = algilama.check_folder(tmp_path / "yok", catalog)  # no folder yet: every recorded file is missing
    assert {e.state for e in nothing} == {"eksik"}
    assert "mkdir -p" in "\n".join(algilama.folder_lines(nothing, tmp_path / "yok"))
    assert algilama.main(["--klasor", str(folder)]) == 0


def test_class_is_resolved_from_the_model_names() -> None:
    v02, coco = {0: "Person"}, {0: "person", 1: "bicycle", 2: "car"}
    assert algilama.resolve_class(v02, None) == 0  # default: the class named "person", any case
    assert algilama.resolve_class(coco, None) == 0
    assert algilama.resolve_class(v02, "person") == 0 and algilama.resolve_class(coco, "Person") == 0
    assert algilama.resolve_class(coco, "car") == 2 and algilama.resolve_class(coco, 1) == 1
    with pytest.raises(ValueError, match=re.escape("'kedi'")) as error:
        algilama.resolve_class(coco, "kedi")
    assert "0: person, 1: bicycle, 2: car" in str(error.value) and "--sinif" in str(error.value)
    with pytest.raises(ValueError, match="5 numaralı"):
        algilama.resolve_class(v02, 5)
    with pytest.raises(ValueError, match="'person'"):
        algilama.resolve_class({0: "car"}, None)


def test_the_module_does_not_need_ultralytics_or_torch() -> None:
    assert "ultralytics" not in sys.modules and "torch" not in sys.modules
    assert isinstance(algilama.YoloAlgilayici, type)  # importing it alone loads neither


class Tensor:
    """What ultralytics' Boxes fields offer on the CPU: .numpy()."""

    def __init__(self, values: list) -> None:
        self.values = np.asarray(values, dtype=np.float32)

    def numpy(self) -> np.ndarray:
        return self.values


class Boxes:
    def __init__(self, xyxy: list, conf: list, cls: list) -> None:
        self.xyxy, self.conf, self.cls = Tensor(xyxy), Tensor(conf), Tensor(cls)


class Result:
    """A stand-in for ultralytics.engine.results.Results of one frame."""

    def __init__(self, *boxes: list) -> None:
        self.boxes = Boxes(*boxes)


def test_ultralytics_result_becomes_boxes_clipped_to_the_frame() -> None:
    names, size = {0: "Person"}, (2304, 1296)
    result = Result(
        [[10, 20, 110, 220], [-5, -3, 50, 40], [2300.5, 1200, 2400, 1400], [2400, 10, 2500, 20]],
        [0.5, 0.9, 0.7, 0.3],
        [0, 0, 0, 0],
    )
    boxes = algilama.boxes_of(result, names, size)
    assert [b.guven for b in boxes] == pytest.approx([0.9, 0.7, 0.5])  # most confident first
    assert (boxes[0].u0, boxes[0].v0, boxes[0].u1, boxes[0].v1) == (0.0, 0.0, 50.0, 40.0)  # clipped top left
    # pixel edges (u0 <= u < u1): a box over the last column ends at the width, not at width - 1
    assert (boxes[1].u0, boxes[1].u1, boxes[1].v1) == (2300.5, 2304.0, 1296.0)
    assert (boxes[2].u0, boxes[2].v0, boxes[2].u1, boxes[2].v1) == (10.0, 20.0, 110.0, 220.0)
    assert all(b.sinif == 0 and b.sinif_adi == "Person" for b in boxes)
    assert len(boxes) == 3  # the box completely outside the frame covers no pixel and is dropped
    assert algilama.boxes_of(Result(np.zeros((0, 4)), [], []), names, size) == []

    a = algilama.Kutu(0, 0, 10, 10, 1.0, 0, "Person")
    assert algilama.iou(a, a) == pytest.approx(1.0)
    assert algilama.iou(a, algilama.Kutu(5, 0, 15, 10, 1.0, 0, "Person")) == pytest.approx(50 / 150)
    assert algilama.iou(a, algilama.Kutu(10, 0, 20, 10, 1.0, 0, "Person")) == 0.0  # touching edges share no pixel
    assert algilama.iou(a, (math.nan,) * 4) == 0.0  # referee box of a target that is not visible


def image_bytes(t: float, width: int = 4, height: int = 2) -> bytes:
    msg = Image(width=width, height=height, step=3 * width, pixel_format_type=3)
    msg.header.stamp.sec, msg.header.stamp.nsec = int(t), round((t - int(t)) * 1e9)
    msg.data = np.arange(3 * width * height, dtype=np.uint8).tobytes()
    return msg.SerializeToString()


class FakeDetector:
    """Any detector with algila(): Vision's (m08/m10) plugs in the same way."""

    def __init__(self) -> None:
        self.seen: list[np.ndarray] = []

    def algila(self, kare_rgb: np.ndarray) -> list[algilama.Kutu]:
        self.seen.append(kare_rgb)
        return [algilama.Kutu(1, 0, 3, 2, 0.8, 0, "Person")]


def test_one_frame_through_the_defects_stage_and_a_detector() -> None:
    raw = image_bytes(61.032)
    skipped = [goruntu.Arrival(1, 99.95, image_bytes(60.996)[: goruntu.HEAD_BYTES])]
    detector = FakeDetector()
    r = algilama.process(
        raw, goruntu.Arrival(2, 100.0, raw[:256]), skipped, kusurlar.KameraKusurlari({}), detector, 100.01
    )
    assert detector.seen[0].tobytes() == np.arange(24, dtype=np.uint8).tobytes()  # the frame, unchanged
    assert (r.t, r.sira, r.varis, r.basla) == (pytest.approx(61.032), 2, 100.0, 100.01)
    assert r.kutular == (algilama.Kutu(1, 0, 3, 2, 0.8, 0, "Person"),)
    assert [(s.sira, s.t) for s in r.atlanan] == [(1, pytest.approx(60.996))]
    assert r.bitis >= r.basla and min(r.cozme_ms, r.kusur_ms, r.model_ms) >= 0.0


def test_detection_log_rows_boxes_and_books(tmp_path: Path) -> None:
    clock = goruntu.SimClock()
    for k in range(2001):  # real time: wall 1000 s = sim 50 s
        clock.add(sim=50.0 + k * 0.01, wall=1000.0 + k * 0.01)
    log = algilama.DetectionLog(tmp_path, clock)
    box = algilama.Kutu(100, 200, 140, 300, 0.9, 0, "Person")
    frames = [59.86, 59.90, 59.94, 59.98, 60.02, 60.06, 60.10, 60.14, 60.18]  # [s sim] camera frames, sira 1..9
    for j in (2, 5, 8):  # every third frame is processed, the two before it were replaced while the model worked
        t = frames[j]
        skipped = tuple(goruntu.Skipped(k + 1, frames[k], 0.0) for k in (j - 2, j - 1))
        varis = 1000.0 + (t - 50.0) + 0.020  # arrives 20 ms after capture, waits 5 ms, 65 ms of work
        r = algilama.FrameResult(t, j + 1, varis, varis + 0.005, varis + 0.070, 2.0, 0.0, 60.0, (box,), skipped)
        log.add(r, alinma=r.bitis + 0.001)
    log.close()

    with (tmp_path / "algilama.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [int(r["t_us"]) for r in rows] == [59_940_000, 60_060_000, 60_180_000]  # the key of dogru_cevap.csv
    assert [r["sira"] for r in rows] == ["3", "6", "9"] and rows[1]["onceki_atlanan"] == "2"
    assert float(rows[1]["ulasma_ms"]) == pytest.approx(20.0, abs=0.01)  # sim ms, through the clock
    assert float(rows[1]["bekleme_ms"]) == pytest.approx(5.0, abs=0.01)
    assert float(rows[1]["teslim_ms"]) == pytest.approx(1.0, abs=0.01)
    assert (rows[1]["kutu_sayisi"], float(rows[1]["model_ms"])) == ("1", 60.0)
    with (tmp_path / "kutular.csv").open(encoding="utf-8") as f:
        boxes = list(csv.DictReader(f))
    assert [b["t_us"] for b in boxes] == ["59940000", "60060000", "60180000"] and float(boxes[0]["u1"]) == 140.0

    # the window's frame and time numbers of these rows: olcum.frame_metrics (test_olcum)
    assert [len(s) for s in (log.rows, log.skipped)] == [3, 6] and log.boxes[60_060_000] == (box,)
