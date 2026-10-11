#!/usr/bin/env bash
# F1 acceptance run, no window (~6 minutes): the walking-human scenario twice, compared (see f1_testi.py).
#
#   tez/sim/araclar/f1_kabul.sh
#
# Outputs: build/px4_sitl_tez/tez_kabul/f1_kosu{1,2}/. Exit code 0 = passed.
set -euo pipefail
SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${TEZ_PYTHON:-$SIM/../../../.venv-tez/bin/python}" "$SIM/araclar/f1_testi.py" "$@"
