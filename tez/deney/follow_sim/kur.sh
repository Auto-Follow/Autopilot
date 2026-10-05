#!/usr/bin/env bash
# One-time setup for the Follow Me experiment simulation (start it with baslat.sh):
#   - models/worlds symlinked into Tools/simulation/gz (hidden from git status, PX4 files unchanged)
#   - PX4 airframe hook 4010_gz_x500_mono_cam.post -> px4_hook.post (panel + video, only for renkli_duz* worlds)
#   - .venv with OpenCV for the video stream
# Safe to run again (e.g. after `make clean`). Undo with kaldir.sh.
set -euo pipefail

SIM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PX4_DIR="${PX4_DIR:-$(cd "$SIM_DIR/../../.." && pwd)}"   # this folder lives in <Autopilot>/tez/deney/
GZ_DIR="$PX4_DIR/Tools/simulation/gz"
HOOK="$PX4_DIR/build/px4_sitl_default/etc/init.d-posix/airframes/4010_gz_x500_mono_cam.post"

exclude_file="$(git -C "$GZ_DIR" rev-parse --git-path info/exclude)"
[[ "$exclude_file" = /* ]] || exclude_file="$GZ_DIR/$exclude_file"
link() {  # link <source> <relative target inside GZ_DIR>
  ln -sfn "$1" "$GZ_DIR/$2"
  grep -qxF "$2" "$exclude_file" 2>/dev/null || echo "$2" >> "$exclude_file"
}
for m in "$SIM_DIR"/models/*/; do link "${m%/}" "models/$(basename "$m")"; done
for w in "$SIM_DIR"/worlds/*.sdf; do link "$w" "worlds/$(basename "$w")"; done
echo "Modeller ve dünya bağlandı: $GZ_DIR"

# Older versions wrote a ~/.bashrc block (WSL); it is no longer needed
sed -i '/# >>> follow_sim >>>/,/# <<< follow_sim <<</d' "$HOME/.bashrc"

if [[ ! -x "$SIM_DIR/.venv/bin/python" ]]; then
  python3 -m venv --system-site-packages "$SIM_DIR/.venv"
  "$SIM_DIR/.venv/bin/pip" install -q -r "$SIM_DIR/requirements.txt"
  echo "Python ortamı kuruldu: $SIM_DIR/.venv"
fi

if [[ ! -d "$(dirname "$HOOK")" ]]; then
  echo "PX4 SITL derlenmemiş; derleniyor..."
  make -C "$PX4_DIR" px4_sitl >/dev/null
fi
ln -sfn "$SIM_DIR/px4_hook.post" "$HOOK"
echo "PX4 kancası kuruldu: $HOOK"
echo "Hazır. Başlatmak için: $SIM_DIR/baslat.sh   (eğik kamera: --egim 40)"
