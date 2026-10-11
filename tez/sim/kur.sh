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

if [ -f "$DEST/.tamam" ] && [ "$(cat "$DEST/.tamam")" = "$ACTOR_SHA256" ]; then
	echo "İnsan modeli zaten kurulu: $DEST"
	exit 0
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
echo "$ACTOR_SHA256" > "$DEST/.tamam"
echo "Kuruldu: $DEST (${ACTOR_FILES[*]})"
