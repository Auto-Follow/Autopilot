#!/usr/bin/env bash
# F0 acceptance run, no window (~2 minutes): f0_testi.py starts the simulation, checks it and shuts it down.
#
#   tez/sim/araclar/f0_kabul.sh
#
# Logs: build/px4_sitl_tez/tez_kabul/sim.log. Exit code 0 = passed.
set -euo pipefail
SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${TEZ_PYTHON:-$SIM/../../../.venv-tez/bin/python}" "$SIM/araclar/f0_testi.py" "$@"
