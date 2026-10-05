#!/usr/bin/env bash
# Undo kur.sh: remove the PX4 hook and the model/world symlinks (and an old ~/.bashrc block, if any).
set -uo pipefail
SIM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PX4_DIR="${PX4_DIR:-$(cd "$SIM_DIR/../../.." && pwd)}"
GZ_DIR="$PX4_DIR/Tools/simulation/gz"
rm -f "$PX4_DIR/build/px4_sitl_default/etc/init.d-posix/airframes/4010_gz_x500_mono_cam.post"
for m in "$SIM_DIR"/models/*/; do rm -f "$GZ_DIR/models/$(basename "$m")"; done
for w in "$SIM_DIR"/worlds/*.sdf; do rm -f "$GZ_DIR/worlds/$(basename "$w")"; done
sed -i '/# >>> follow_sim >>>/,/# <<< follow_sim <<</d' "$HOME/.bashrc"
echo "Kaldırıldı. PX4 yine varsayılan hâliyle çalışır."
