#!/usr/bin/env bash
# m06 acceptance run, no window (~8-10 minutes): m06_testi.py flies takip_yuruyen (model + stock Follow Me) and
# kalabalik_park (model, Hold), with --mod-adi a third run into that (out-of-tree) mode, and checks the seven
# conditions of spec 2026-11-10-m06-sim-ortami "Test Planı" (see m06_testi.py).
#
#   tez/sim/araclar/m06_kabul.sh [--cikti KLASÖR] [--mod-adi "<ad>" --px4-baslat "<komut>"]
#
# Outputs: tez/sim/sonuclar/<date>_m06_kabul/ (or --cikti): kosu<i>_<scenario>/ and kosu<i>_<scenario>.log.
# Exit code 0 = passed.
set -euo pipefail
SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${TEZ_PYTHON:-$SIM/../../../.venv-tez/bin/python}" "$SIM/araclar/m06_testi.py" "$@"
