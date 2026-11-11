#!/usr/bin/env bash
# Start the thesis simulation: Gazebo with a tez world (drone x500_tez_0 inside it) + PX4 SITL (build/px4_sitl_tez,
# see derle.sh) with the stock airframe 4001_gz_x500 attached to that drone and the real vehicle's settings loaded.
#
#   tez/sim/calistir.sh                          # Gazebo window + PX4 shell (pxh>) in this terminal
#   tez/sim/calistir.sh --ekransiz               # no Gazebo window (automatic tests)
#   tez/sim/calistir.sh --dunya duz_alan         # world from tez/sim/worlds (default: duz_alan)
#   tez/sim/calistir.sh --dunya yol/dunya.sdf    # any world file (scenario worlds written by araclar/senaryo.py)
#   tez/sim/calistir.sh --param FLW_TGT_DST=10   # one more start parameter (repeatable; the last one wins)
#
# QGroundControl connects by itself (UDP 14550). Ctrl+C or `shutdown` in pxh> stops PX4 and Gazebo;
# without a terminal (--ekransiz from a script) use: (cd build/px4_sitl_tez/rootfs && ../bin/px4-shutdown)
# Every start uses fresh parameters (team standard: tests do not inherit parameters).
#
# No PX4 file is changed ((b) path, spec 2026-11-10-m06-sim-ortami): PX4_SYS_AUTOSTART=4001 selects the stock
# airframe, PX4_GZ_MODEL_NAME attaches PX4 to the drone in the world, and the start parameters
# (tez/sim/parametreler/gercek_dron.params -> sim.params -> --param) go in as PX4_PARAM_<NAME>, which the stock
# posix rcS sets after `param reset_all` and before the airframe file. Python: $TEZ_PYTHON or the team venv.
set -euo pipefail

SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SIM/../.." && pwd)"
BUILD="$REPO/build/px4_sitl_tez"
PY="${TEZ_PYTHON:-$SIM/../../../.venv-tez/bin/python}"

DUNYA=duz_alan
EKRANSIZ=0
PARAM_ARGS=()
while [ $# -gt 0 ]; do
	case "$1" in
	--dunya) DUNYA="$2"; shift 2 ;;
	--ekransiz) EKRANSIZ=1; shift ;;
	--param) PARAM_ARGS+=(--param "$2"); shift 2 ;;
	-h | --help) sed -n '2,18p' "$0"; exit 0 ;;
	*) echo "Bilinmeyen seçenek: $1 (yardım: --help)" >&2; exit 2 ;;
	esac
done

if [[ "$DUNYA" == *.sdf ]]; then
	WORLD_FILE="$(realpath "$DUNYA")"
	[ -f "$WORLD_FILE" ] || { echo "Dünya dosyası yok: $DUNYA" >&2; exit 2; }
	# PX4 and the clock topic use the <world name>, not the file name
	DUNYA="$(sed -n 's/.*<world name="\([^"]*\)".*/\1/p' "$WORLD_FILE" | head -1)"
	[ -n "$DUNYA" ] || { echo "Dünya dosyasında <world name=...> yok: $WORLD_FILE" >&2; exit 2; }
else
	WORLD_FILE="$SIM/worlds/$DUNYA.sdf"
	[ -f "$WORLD_FILE" ] || { echo "Dünya yok: $WORLD_FILE" >&2; exit 2; }
fi
[ -x "$BUILD/bin/px4" ] || { echo "PX4 derlenmemiş. Önce: tez/sim/derle.sh" >&2; exit 2; }
[ -x "$PY" ] || { echo "Python yok: $PY (ekip venv'i, bkz. tez/env/VERSIONS.md; başkası için TEZ_PYTHON)" >&2; exit 2; }
if pgrep -x px4 > /dev/null || pgrep -f "^gz sim" > /dev/null; then
	echo "Zaten çalışan bir PX4 veya Gazebo var (ps -ef | grep -E 'px4|gz sim'). Önce onu kapatın." >&2
	exit 2
fi

# Start parameters, checked before anything starts (a bad line stops here with its file, line and name).
# Variables inherited from the caller's shell would bypass the load order, so only ours reach PX4.
PARAM_LINES="$("$PY" "$SIM/araclar/parametreler.py" "${PARAM_ARGS[@]}")"
while IFS= read -r name; do
	unset "$name"
done < <(compgen -e | grep '^PX4_PARAM_' || true)
echo "Başlangıç parametreleri (PX4_PARAM_*, tez/sim/parametreler + --param):"
while IFS= read -r line; do
	[ -n "$line" ] || continue
	export "${line?}"  # NAME=VALUE (the ? quiets shellcheck SC2163)
	echo "  $line"
done <<< "$PARAM_LINES"

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

export PX4_SYS_AUTOSTART=4001        # stock 4001_gz_x500; rcS takes it before any lookup by model name
export PX4_GZ_MODEL_NAME=x500_tez_0  # attach to the drone that is already in the world (px4-rc.gzsim)
export PX4_GZ_WORLD="$DUNYA"
export PX4_SIM_MODEL=x500_tez        # informational only; alone it would make rcS look for a <no>_x500_tez airframe
if [ -t 0 ]; then
	"$BUILD/bin/px4"
else
	# No terminal (scripts, tests): daemon mode without the pxh shell. A shell on a closed or idle stdin
	# either loops and fills the log or never notices `shutdown`. Stop it with build/px4_sitl_tez/bin/px4-shutdown.
	"$BUILD/bin/px4" -d
fi
