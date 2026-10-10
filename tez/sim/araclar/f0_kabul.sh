#!/usr/bin/env bash
# F0 acceptance run, no window: start the simulation, run f0_testi.py, shut PX4 down, check nothing is left running.
#
#   tez/sim/araclar/f0_kabul.sh
#
# Logs: build/px4_sitl_tez/tez_kabul/{sim.log,test.log}. Exit code 0 = passed.
set -uo pipefail

SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$SIM/../.." && pwd)"
BUILD="$REPO/build/px4_sitl_tez"
PYTHON="${TEZ_PYTHON:-$REPO/../.venv-tez/bin/python}"
OUT="$BUILD/tez_kabul"
mkdir -p "$OUT"

"$SIM/calistir.sh" --ekransiz < /dev/null > "$OUT/sim.log" 2>&1 &
SIM_PID=$!

registered=0
for _ in $(seq 120); do
	if grep -q "registered as" "$OUT/sim.log"; then
		registered=1
		break
	fi
	kill -0 "$SIM_PID" 2> /dev/null || break
	sleep 1
done

status=1
if [ "$registered" -eq 1 ]; then
	"$PYTHON" "$SIM/araclar/f0_testi.py" 2>&1 | tee "$OUT/test.log"
	status=${PIPESTATUS[0]}
else
	echo "HATA: simülasyon açılmadı veya tez modu kaydolmadı; son satırlar:"
	tail -20 "$OUT/sim.log"
fi

(cd "$BUILD/rootfs" && timeout 20 ../bin/px4-shutdown > /dev/null 2>&1)
for _ in $(seq 30); do
	kill -0 "$SIM_PID" 2> /dev/null || break
	sleep 1
done
if kill -0 "$SIM_PID" 2> /dev/null || pgrep -x px4 > /dev/null || pgrep -f "^gz sim" > /dev/null; then
	echo "HATA: kapanıştan sonra çalışan PX4/Gazebo süreci kaldı"
	status=1
else
	echo "Kapanış temiz: PX4 ve Gazebo kapandı."
fi

if grep -qi "unresponsive" "$OUT/sim.log"; then
	echo "HATA: PX4 tez modunu 'unresponsive' olarak işaretledi (sim.log)"
	status=1
fi
exit "$status"
