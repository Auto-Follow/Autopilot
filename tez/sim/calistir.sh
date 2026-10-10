#!/usr/bin/env bash
# Start the thesis simulation: Gazebo with a tez world (drone x500_tez_0 inside it) + PX4 SITL with the thesis
# modules (build/px4_sitl_tez, see derle.sh) attached to that drone through airframe 4030_gz_x500_tez.
#
#   tez/sim/calistir.sh                    # Gazebo window + PX4 shell (pxh>) in this terminal
#   tez/sim/calistir.sh --ekransiz         # no Gazebo window (automatic tests)
#   tez/sim/calistir.sh --dunya duz_alan   # world from tez/sim/worlds (default: duz_alan)
#
# QGroundControl connects by itself (UDP 14550). Ctrl+C or `shutdown` in pxh> stops PX4 and Gazebo;
# without a terminal (--ekransiz from a script) use: (cd build/px4_sitl_tez/rootfs && ../bin/px4-shutdown)
# Every start uses fresh parameters (team standard: tests do not inherit parameters).
set -euo pipefail

SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SIM/../.." && pwd)"
BUILD="$REPO/build/px4_sitl_tez"

DUNYA=duz_alan
EKRANSIZ=0
while [ $# -gt 0 ]; do
	case "$1" in
	--dunya) DUNYA="$2"; shift 2 ;;
	--ekransiz) EKRANSIZ=1; shift ;;
	-h | --help) sed -n '2,10p' "$0"; exit 0 ;;
	*) echo "Bilinmeyen seçenek: $1 (yardım: --help)" >&2; exit 2 ;;
	esac
done

WORLD_FILE="$SIM/worlds/$DUNYA.sdf"
[ -f "$WORLD_FILE" ] || { echo "Dünya yok: $WORLD_FILE" >&2; exit 2; }
[ -x "$BUILD/bin/px4" ] || { echo "PX4 derlenmemiş. Önce: tez/sim/derle.sh" >&2; exit 2; }
if pgrep -x px4 > /dev/null || pgrep -f "^gz sim" > /dev/null; then
	echo "Zaten çalışan bir PX4 veya Gazebo var (ps -ef | grep -E 'px4|gz sim'). Önce onu kapatın." >&2
	exit 2
fi

# Models: thesis models first, then PX4's own (x500_tez includes model://x500).
export GZ_SIM_RESOURCE_PATH="$SIM/models:$SIM/worlds:$REPO/Tools/simulation/gz/models${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
export GZ_SIM_SYSTEM_PLUGIN_PATH="$BUILD/src/modules/simulation/gz_plugins${GZ_SIM_SYSTEM_PLUGIN_PATH:+:$GZ_SIM_SYSTEM_PLUGIN_PATH}"
export GZ_SIM_SERVER_CONFIG_PATH="$SIM/server.config"
export GZ_IP=127.0.0.1

GZ_PIDS=()
cleanup() {
	trap - EXIT INT TERM
	for pid in "${GZ_PIDS[@]}"; do
		kill -INT "$pid" 2> /dev/null || true
	done
	for pid in "${GZ_PIDS[@]}"; do
		for _ in $(seq 50); do kill -0 "$pid" 2> /dev/null || break; sleep 0.1; done
		kill -KILL "$pid" 2> /dev/null || true
	done
}
trap cleanup EXIT INT TERM

gz sim --verbose=1 -r -s "$WORLD_FILE" &
GZ_PIDS+=($!)
if [ "$EKRANSIZ" -eq 0 ]; then
	gz sim -g > /dev/null 2>&1 &
	GZ_PIDS+=($!)
fi

# PX4 must find this world already running; otherwise its startup script would launch a second Gazebo.
for _ in $(seq 60); do
	gz topic -l 2> /dev/null | grep -q "^/world/$DUNYA/clock" && break
	sleep 1
done
gz topic -l 2> /dev/null | grep -q "^/world/$DUNYA/clock" || { echo "Gazebo dünyası açılmadı: $DUNYA" >&2; exit 1; }

cd "$BUILD/rootfs"
rm -f parameters*.bson dataman

export PX4_SIM_MODEL=gz_x500_tez
export PX4_GZ_WORLD="$DUNYA"
if [ -t 0 ]; then
	"$BUILD/bin/px4"
else
	# No terminal (scripts, tests): daemon mode without the pxh shell. A shell on a closed or idle stdin
	# either loops and fills the log or never notices `shutdown`. Stop it with build/px4_sitl_tez/bin/px4-shutdown.
	"$BUILD/bin/px4" -d
fi
