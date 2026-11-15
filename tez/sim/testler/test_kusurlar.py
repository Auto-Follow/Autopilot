"""Camera defects stage between the frame reader and the model: off in Faz A, Faz B fields reserved."""

import re
from pathlib import Path

import numpy as np
import pytest

import hedef
import kusurlar

SCENARIO = """
ad: kusur_deneme
takip: {kaynak: yok}
hedef: {baslangic: [10, 0], yol: [{nokta: [20, 0], hiz_mps: 1.0}]}
"""


def test_empty_settings_pass_the_frame_bit_for_bit() -> None:
    frame = np.random.default_rng(6).integers(0, 256, (1296, 2304, 3), dtype=np.uint8)
    frame.setflags(write=False)  # the reader hands out a read-only view of the message
    before = frame.tobytes()
    stage = kusurlar.KameraKusurlari({})
    out = stage.uygula(frame, 61.032)
    assert out.dtype == np.uint8 and out.shape == (1296, 2304, 3)
    assert out.tobytes() == before and frame.tobytes() == before
    assert not stage.etkin
    assert 0.0 <= stage.kusur_ms < 50.0  # measured every frame (spec 2.)


def test_phase_b_fields_are_reserved_and_unknown_fields_refused(tmp_path: Path) -> None:
    for field in kusurlar.PHASE_B:
        with pytest.raises(ValueError, match=re.escape(f"kusurlar.{field}: Faz B'de uygulanacak")):
            kusurlar.KameraKusurlari({field: {"sigma": 2}})
    with pytest.raises(ValueError, match="bilinmeyen alan") as error:
        kusurlar.KameraKusurlari({"bulanik": 1})
    assert all(name in str(error.value) for name in kusurlar.PHASE_B)  # lists the reserved names

    # the scenario is checked when it is loaded, before anything starts
    path = tmp_path / "s.yaml"
    path.write_text(SCENARIO + "kusurlar: {gurultu: {sigma: 2}}\n", encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape("kusurlar.gurultu: Faz B'de uygulanacak")):
        hedef.load(str(path))
    path.write_text(SCENARIO + "kusurlar: {}\n", encoding="utf-8")
    assert hedef.load(str(path)).defects == {}
