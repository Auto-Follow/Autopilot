#!/usr/bin/env bash
# F1 acceptance: run the walking-human scenario twice (no window, with the overhead check) and compare the runs.
#
#   tez/sim/araclar/f1_kabul.sh
#
# Passes when both runs complete, the rendered target is within 0.3 m of the ground truth in each run, and the two
# runs see the target at the same place (within 0.15 m) at the same sim times. ~6 minutes.
set -uo pipefail

SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$SIM/../.." && pwd)"
PYTHON="${TEZ_PYTHON:-$REPO/../.venv-tez/bin/python}"
OUT="$REPO/build/px4_sitl_tez/tez_kabul"
mkdir -p "$OUT"

status=0
for i in 1 2; do
	rm -rf "$OUT/f1_kosu$i"
	echo "=== Koşu $i ==="
	"$PYTHON" "$SIM/araclar/senaryo.py" --senaryo yuruyen_insan --ekransiz --dogrula --cikti "$OUT/f1_kosu$i" || status=1
done

"$PYTHON" - "$OUT/f1_kosu1/ozet.json" "$OUT/f1_kosu2/ozet.json" <<'PY' || status=1
import json, math, sys

a, b = (json.load(open(p)) for p in sys.argv[1:3])
ok = True
for run, s in (("1", a), ("2", b)):
    worst = s["olcutler"].get("dogrulama_fark_max_m", math.nan)
    good = s["sonuc"] == "GEÇTİ" and worst <= 0.3
    ok &= good
    print(f"{'OK  ' if good else 'HATA'} koşu {run}: {s['sonuc']}, hedef doğrulama farkı en fazla {worst:.2f} m (sınır 0.30)")
pairs = [(x, y) for x in a["dogrulama"] for y in b["dogrulama"] if abs(x["t"] - y["t"]) < 1e-6]
diffs = [math.hypot(x["goruntu_x"] - y["goruntu_x"], x["goruntu_y"] - y["goruntu_y"]) for x, y in pairs]
same = len(diffs) == len(a["dogrulama"]) > 0 and max(diffs) <= 0.15
ok &= same
print(f"{'OK  ' if same else 'HATA'} iki koşu aynı yolu izledi: {len(diffs)} ortak anda en büyük fark "
      f"{max(diffs) if diffs else float('nan'):.3f} m (sınır 0.15)")
print("\nSONUÇ:", "GEÇTİ" if ok else "KALDI")
sys.exit(0 if ok else 1)
PY
if pgrep -x px4 > /dev/null || pgrep -f "^gz sim" > /dev/null; then
	echo "HATA: kapanıştan sonra çalışan PX4/Gazebo süreci kaldı"
	status=1
fi
exit "$status"
