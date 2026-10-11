#!/usr/bin/env bash
# One-time setup of the simulation assets that are not kept in git (large binary meshes).
#
#   tez/sim/kur.sh
#
# Human target: "actor" by Mingfei on Gazebo Fuel, CC BY 4.0 (see tez/sim/models/insan/KAYNAK.md).
# The archive is pinned by sha256 like the other downloads in tez/env/VERSIONS.md.
set -euo pipefail

SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ACTOR_URL="https://fuel.gazebosim.org/1.0/Mingfei/models/actor/1/actor.zip"
ACTOR_SHA256="edd48c4e609c32e88ab63dc770c1fd0a6c7847d28340a3ce88b65f01ae04e5b4"
ACTOR_FILES=(walk.dae stand.dae run.dae)
DEST="$SIM/models/insan/meshes"
# Walk/run copies that do not glide (araclar/animasyon.py): start where the feet pass each other (hip travel from the
# first frame) and move the hips as far as the legs really step (side camera: planted toe still at 0.91; the run uses
# the same skeleton factor, its slip could not be measured reliably)
WALK_START_M=0.37
RUN_START_M=0.24
STRIDE_SCALE=0.91
INSTALLED="$ACTOR_SHA256 animasyon-2"

make_copies() {
	python3 "$SIM/araclar/animasyon.py" "$DEST/walk.dae" "$DEST/walk_tez.dae" "$WALK_START_M" "$STRIDE_SCALE"
	python3 "$SIM/araclar/animasyon.py" "$DEST/run.dae" "$DEST/run_tez.dae" "$RUN_START_M" "$STRIDE_SCALE"
	echo "$INSTALLED" > "$DEST/.tamam"
}

if [ -f "$DEST/.tamam" ]; then
	case "$(cat "$DEST/.tamam")" in
	"$INSTALLED")
		echo "İnsan modeli zaten kurulu: $DEST"
		exit 0
		;;
	"$ACTOR_SHA256"*)
		make_copies
		echo "Animasyon kopyaları güncellendi: $DEST (walk_tez.dae, run_tez.dae)"
		exit 0
		;;
	esac
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "İnsan modeli indiriliyor (~11 MB)..."
curl -fsSL --retry 3 -o "$TMP/actor.zip" "$ACTOR_URL"
echo "$ACTOR_SHA256  $TMP/actor.zip" | sha256sum --check --quiet || {
	echo "HATA: indirilen dosyanın sha256 değeri beklenenden farklı. Gruba bildirin; kendiniz değiştirmeyin." >&2
	exit 1
}
mkdir -p "$TMP/zip" "$DEST"
unzip -q "$TMP/actor.zip" -d "$TMP/zip"
for f in "${ACTOR_FILES[@]}"; do
	cp "$TMP/zip/meshes/$f" "$DEST/$f"
done
make_copies
echo "Kuruldu: $DEST (${ACTOR_FILES[*]} + walk_tez.dae, run_tez.dae)"
