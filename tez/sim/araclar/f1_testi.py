#!/usr/bin/env python3
"""F1 acceptance test: run the walking-human scenario twice (no window, overhead check) and compare the runs.

Passes when both runs complete, the rendered target is within dogrulama.LIMIT (0.3 m) of the ground truth in each
run, and the two runs see the target at the same place (within 0.15 m) at the same sim times. ~4 minutes.
The runs are without the model (--modelsiz): F1 checks the world and the target, not the detector.

    ~/Desktop/Projects/Auto-Follow/.venv-tez/bin/python tez/sim/araclar/f1_testi.py   (or f1_kabul.sh)
"""

import math
import shutil
import sys

import dogrulama
import hedef
import senaryo
from simulasyon import BUILD

SCENARIO = "yuruyen_insan"
SAME_RUN_LIMIT = 0.15  # [m]


def main() -> int:
    sc = hedef.load(SCENARIO, hedef.CommandLine(no_model=True))  # --modelsiz: no model process
    runs = []
    for i in (1, 2):
        print(f"=== Koşu {i} ===", flush=True)
        out = BUILD / "tez_kabul" / f"f1_kosu{i}"
        shutil.rmtree(out, ignore_errors=True)  # never compare with an older run's files
        runs.append(senaryo.run(sc, out, headless=True, verify=True))

    ok = True
    for i, s in enumerate(runs, 1):
        worst = s["olcutler"].get("dogrulama_fark_max_m")
        good = s["sonuc"] == "GEÇTİ" and worst is not None and worst <= dogrulama.LIMIT
        ok &= good
        worst_text = f"{worst:.2f} m" if worst is not None else "ölçülemedi"
        print(
            f"{'OK  ' if good else 'HATA'} koşu {i}: {s['sonuc']}, hedef doğrulama farkı en fazla {worst_text} "
            f"(sınır {dogrulama.LIMIT:.2f})"
        )

    a, b = (s["dogrulama"] for s in runs)
    diffs = [
        math.hypot(x["goruntu_x"] - y["goruntu_x"], x["goruntu_y"] - y["goruntu_y"])
        for x, y in zip(a, b, strict=False)
        if x["t"] == y["t"] and x["goruntu_x"] is not None and y["goruntu_x"] is not None
    ]
    same = len(diffs) == len(a) > 0 and max(diffs) <= SAME_RUN_LIMIT
    ok &= same
    print(
        f"{'OK  ' if same else 'HATA'} iki koşu aynı yolu izledi: {len(diffs)} ortak anda en büyük fark "
        f"{max(diffs) if diffs else math.nan:.3f} m (sınır {SAME_RUN_LIMIT})"
    )
    print("\nSONUÇ:", "GEÇTİ" if ok else "KALDI", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
