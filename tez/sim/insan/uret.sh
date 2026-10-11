#!/usr/bin/env bash
# Build the human target (tez/sim/models/insan/meshes) from open sources; kur.sh runs it.
#
#   tez/sim/insan/uret.sh
#
# Downloads (sha256 checked, ~0.7 GB, kept in ~/.cache/auto-follow-insan so a rebuild needs no download):
#   Blender 4.5 LTS (GPL, tool only), MPFB 2 MakeHuman extension (GPL, tool only), MakeHuman system assets (CC0),
#   three CMU motion capture clips (free for research and commercial use, cgspeed BVH conversion).
# Blender runs with its own user folder there, so a Blender the user may have installed is not touched.
set -euo pipefail

INSAN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM="$(cd "$INSAN/.." && pwd)"
DEST="$SIM/models/insan/meshes"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/auto-follow-insan"

BLENDER_TAR=blender-4.5.14-linux-x64.tar.xz
BLENDER_URL="https://download.blender.org/release/Blender4.5/$BLENDER_TAR"
BLENDER_SHA256=9ba871ff2ecd36526b77432745980b7e6664ecd0c7ca11c48849073dcfe06da3
MPFB_ZIP=add-on-mpfb-v2.0.18.zip
MPFB_SHA256=c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad
MPFB_URL="https://extensions.blender.org/download/sha256:$MPFB_SHA256/$MPFB_ZIP"
ASSETS_ZIP=makehuman_system_assets_cc0.zip
ASSETS_URL="https://files.makehumancommunity.org/asset_packs/makehuman_system_assets/$ASSETS_ZIP"
ASSETS_SHA256=b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107
CMU_URL=https://github.com/Shriinivas/cmubvh/raw/main
CMU=(
	"Sequence-035-039/35/Data/35_01.zip f539094eaad1b619a9fcd1676ec586c130b2adc9e8cf4936492051b29018fd2a"
	"Sequence-035-039/35/Data/35_17.zip def1b93003383df60b083acaa196206573a870d6f6a3f2285deebf5a1f41d3de"
	"Sequence-113-128/113/Data/113_21.zip ee8f714567ae6b55271fcf87276bebd456bdb7de1632b7011546a21e829a7ec0"
)

fetch() { # url sha256 file
	if [ -f "$3" ] && echo "$2  $3" | sha256sum --check --quiet 2> /dev/null; then
		return
	fi
	echo "İndiriliyor: $(basename "$3")"
	curl -fL --retry 3 --progress-bar -o "$3.part" "$1"
	echo "$2  $3.part" | sha256sum --check --quiet || {
		echo "HATA: $(basename "$3") sha256 değeri beklenenden farklı. Gruba bildirin; kendiniz değiştirmeyin." >&2
		exit 1
	}
	mv "$3.part" "$3"
}

mkdir -p "$CACHE/cmu"
fetch "$MPFB_URL" "$MPFB_SHA256" "$CACHE/$MPFB_ZIP"
fetch "$ASSETS_URL" "$ASSETS_SHA256" "$CACHE/$ASSETS_ZIP"
for entry in "${CMU[@]}"; do
	path=${entry% *}
	fetch "$CMU_URL/$path" "${entry#* }" "$CACHE/cmu/$(basename "$path")"
	unzip -q -o "$CACHE/cmu/$(basename "$path")" -d "$CACHE/cmu"
done

BLENDER="$CACHE/blender-4.5/blender"
if [ ! -x "$BLENDER" ]; then
	fetch "$BLENDER_URL" "$BLENDER_SHA256" "$CACHE/$BLENDER_TAR"
	echo "Blender açılıyor..."
	tar -xf "$CACHE/$BLENDER_TAR" -C "$CACHE"
	mv "$CACHE/${BLENDER_TAR%.tar.xz}" "$CACHE/blender-4.5"
	rm "$CACHE/$BLENDER_TAR"
fi
export BLENDER_USER_RESOURCES="$CACHE/blender-kullanici"
if [ ! -d "$BLENDER_USER_RESOURCES/extensions/user_default/mpfb" ]; then
	"$BLENDER" -b --command extension install-file -r user_default -e "$CACHE/$MPFB_ZIP" > /dev/null
fi
DATA="$("$BLENDER" -b --python-expr "from bl_ext.user_default.mpfb.services import LocationService
print('VERI', LocationService.get_user_data())" 2> /dev/null | sed -n 's/^VERI //p')"
if [ ! -d "$DATA/clothes/male_casualsuit03" ]; then
	mkdir -p "$DATA"
	unzip -q -o "$CACHE/$ASSETS_ZIP" -d "$DATA"
fi

echo "İnsan modeli üretiliyor (birkaç dakika)..."
mkdir -p "$DEST"
"$BLENDER" -b --python "$INSAN/uret.py" -- --cikti "$DEST" --cmu "$CACHE/cmu" > "$CACHE/uret.log" 2>&1 || {
	echo "HATA: üretim başarısız, log: $CACHE/uret.log" >&2
	tail -20 "$CACHE/uret.log" >&2
	exit 1
}
grep -E "^(ANIM|TAMAM)" "$CACHE/uret.log"
