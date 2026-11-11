"""Model file, its sha256 record and the class of a detector, without ultralytics or torch."""

import hashlib
import re
import sys
from pathlib import Path

import pytest

import algilama
import hedef

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
    assert known["yolov8s.pt"].sha256 is None  # task group 13

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
