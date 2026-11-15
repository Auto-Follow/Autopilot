"""Camera defects stage between the frame reader and the model: KameraKusurlari.uygula(kare, t) -> kare.

The scenario's `kusurlar:` block sets it. In Faz A of spec 2026-11-10-m06-sim-ortami every defect is off and the frame
passes unchanged (the same array, bit for bit). The Faz B fields are reserved (PHASE_B: noise, motion blur, rolling
shutter, exposure); giving one now stops the run before anything starts instead of being silently ignored. The time the
stage takes (kusur_ms) is measured on every frame, so a Faz B stage shows its cost in algilama.csv.
"""

import time
from collections.abc import Mapping

import numpy as np

# Reserved for Faz B (task group 15): noise, motion blur, rolling shutter, exposure/brightness
PHASE_B = ("gurultu", "bulaniklik", "rolling_shutter", "pozlama")


def check(settings: Mapping) -> None:
    """Raise ValueError for every field of a `kusurlar:` block that Faz A cannot apply, with the field's name."""
    unknown = sorted(set(settings) - set(PHASE_B))
    if unknown:
        raise ValueError(
            f"kusurlar: bilinmeyen alan(lar) {unknown}; ayrılmış alanlar (Faz B'de uygulanacak): {list(PHASE_B)}"
        )
    for field in PHASE_B:
        if field in settings:
            raise ValueError(
                f"kusurlar.{field}: Faz B'de uygulanacak (spec 2026-11-10-m06-sim-ortami, Görev grubu 15); "
                "Faz A'da kamera kusurları kapalıdır, alanı silin ya da kusurlar: {} yazın"
            )


class KameraKusurlari:
    """The camera defects of a run; off in Faz A."""

    def __init__(self, settings: Mapping) -> None:
        check(settings)
        self.etkin = False  # no defect is on in Faz A
        self.kusur_ms = 0.0  # [ms] time of the last uygula()

    def uygula(self, kare: np.ndarray, t: float) -> np.ndarray:
        """The frame (RGB uint8, height x width x 3) as the camera with its defects would have taken it at sim time
        t [s]. Faz A: the same array, never changed in place."""
        start = time.perf_counter()
        out = kare
        self.kusur_ms = (time.perf_counter() - start) * 1000.0
        return out
