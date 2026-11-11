"""model_dene.py (trying the detector on pictures) with a fake detector: no ultralytics, torch or Gazebo."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import algilama
import hedef
import model_dene


class FakeDetector:
    """Finds one box where the picture is pure red (R=255, G=B=0), so it also tells RGB from BGR."""

    def __init__(self) -> None:
        self.frames: list[np.ndarray] = []

    def algila(self, kare_rgb: np.ndarray) -> list[algilama.Kutu]:
        self.frames.append(kare_rgb)
        rows, cols = np.nonzero((kare_rgb[:, :, 0] == 255) & (kare_rgb[:, :, 2] == 0))
        if not len(rows):
            return []
        u0, v0, u1, v1 = int(cols.min()), int(rows.min()), int(cols.max()) + 1, int(rows.max()) + 1
        return [algilama.Kutu(u0, v0, u1, v1, 0.9, 0, "Person")]


def test_options_follow_the_algilama_rules() -> None:
    def settings(*argv: str) -> hedef.Detection:
        return model_dene.detection_settings(model_dene.parser().parse_args(["--kare", "a.png", *argv]))

    assert settings() == hedef.Detection()
    chosen = settings("--model", "m.pt", "--imgsz", "960", "--conf", "0.5", "--sinif", "0", "--cekirdek", "2")
    assert (chosen.model, chosen.imgsz, chosen.conf, chosen.class_name, chosen.cores) == (
        Path.cwd() / "m.pt",
        960,
        0.5,
        0,
        2,
    )
    with pytest.raises(ValueError, match="algilama.conf"):
        settings("--conf", "1.5")
    with pytest.raises(ValueError, match="algilama.cekirdek"):
        settings("--cekirdek", "0")


def test_pictures_go_through_the_detector_and_get_their_boxes_drawn(tmp_path: Path) -> None:
    picture = np.zeros((120, 200, 3), np.uint8)
    picture[30:70, 50:80] = (255, 0, 0)  # a red "person": columns 50..79, rows 30..69
    path = tmp_path / "kare.png"
    Image.fromarray(picture).save(path)
    fake = FakeDetector()

    [r] = model_dene.run_pictures([path], fake, lambda r: ["satır"], None, repeat=3)
    assert len(fake.frames) == 3 and fake.frames[0].shape == (120, 200, 3)  # RGB uint8, as Algilayici expects
    assert r.boxes == [algilama.Kutu(50, 30, 80, 70, 0.9, 0, "Person")] and len(r.times_ms) == 3
    assert r.output == tmp_path / "kare_model.jpg" and r.output.is_file()
    assert "1 kutu (Person 0.90)" in model_dene.summary(r) and "3 çalıştırma" in model_dene.summary(r)

    out = model_dene.draw(np.zeros((120, 200, 3), np.uint8), r.boxes, [])
    assert out.shape == (120, 200, 3)
    assert tuple(out[50, 50]) == model_dene.MODEL_BOX and tuple(out[50, 79]) == model_dene.MODEL_BOX  # edges
    assert tuple(out[50, 65]) == (0, 0, 0)  # inside the box nothing is drawn

    other = tmp_path / "cikti"
    [r] = model_dene.run_pictures([path], fake, lambda r: [], other, repeat=1)
    assert r.output == other / "kare_model.jpg" and r.output.is_file()
