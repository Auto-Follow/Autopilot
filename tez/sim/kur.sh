#!/usr/bin/env bash
# One-time setup of the simulation assets that are not kept in git (large binary meshes and textures).
#
#   tez/sim/kur.sh
#
# Human target: "actor" by Mingfei on Gazebo Fuel, CC BY 4.0 (see tez/sim/models/insan/KAYNAK.md).
# Ground textures (ambientCG, Poly Haven) and trees (Gazebo Fuel OpenRobotics), all CC0: models/dokular/KAYNAK.md.
# Every download is pinned by sha256 like the other downloads in tez/env/VERSIONS.md. Running it again only does
# what is missing or out of date.
# At the end it checks the model folder (~/auto-follow-modeller/) against tez/sim/modeller.yaml and prints each
# file's sha256 (araclar/algilama.py with TEZ_PYTHON or the team venv). Model files are never downloaded here: a
# missing one is a warning with where to get it, the setup is still done.
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

fetch() { # url sha256 output
	curl -fsSL --retry 3 -o "$3" "$1"
	echo "$2  $3" | sha256sum --check --quiet || {
		echo "HATA: $1 dosyasının sha256 değeri beklenenden farklı. Gruba bildirin; kendiniz değiştirmeyin." >&2
		exit 1
	}
}

install_human() {
	if [ -f "$DEST/.tamam" ]; then
		case "$(cat "$DEST/.tamam")" in
		"$INSTALLED")
			echo "İnsan modeli zaten kurulu: $DEST"
			return
			;;
		"$ACTOR_SHA256"*)
			make_copies
			echo "Animasyon kopyaları güncellendi: $DEST (walk_tez.dae, run_tez.dae)"
			return
			;;
		esac
	fi
	echo "İnsan modeli indiriliyor (~11 MB)..."
	fetch "$ACTOR_URL" "$ACTOR_SHA256" "$TMP/actor.zip"
	mkdir -p "$TMP/zip" "$DEST"
	unzip -q "$TMP/actor.zip" -d "$TMP/zip"
	for f in "${ACTOR_FILES[@]}"; do
		cp "$TMP/zip/meshes/$f" "$DEST/$f"
	done
	make_copies
	echo "Kuruldu: $DEST (${ACTOR_FILES[*]} + walk_tez.dae, run_tez.dae)"
}

# Ground textures: colour maps only (1K is enough: dunya.py bakes them at ~1.2 cm/px)
TEX="$SIM/models/dokular"
AMBIENTCG=( # asset sha256-of-zip
	"Grass001 902f447a64171c8099589642d5bf2d1d6e52c40e94d957eb78eae722084b0cfb"
	"Grass004 4b63495f459db8481f4d5144e4e9069345c81cf898cc71f2216f5dd3bb344469"
	"Ground037 4e69db2b7251b1736fa70fe6fe4ab80d64bd220117dd5dd4c7caaead51c2574e"
)
POLYHAVEN=( # asset sha256-of-jpg
	"forrest_ground_01 3dd6875cb3908e022a3c45ebbffa5e84c670ff2691fbbb6dc9ea4bff88523800"
	"dry_mud_field_001 fa527aa4eb6151c7dab4f0a7b31722d0aa180f728af694594439d106e76f6c6d"
)

install_textures() {
	mkdir -p "$TEX"
	local entry name sha
	for entry in "${AMBIENTCG[@]}"; do
		read -r name sha <<<"$entry"
		[ -f "$TEX/${name}_1K-JPG_Color.jpg" ] && continue
		echo "Doku indiriliyor: ambientCG $name"
		fetch "https://ambientcg.com/get?file=${name}_1K-JPG.zip" "$sha" "$TMP/$name.zip"
		unzip -q -o -j "$TMP/$name.zip" "${name}_1K-JPG_Color.jpg" -d "$TEX"
	done
	for entry in "${POLYHAVEN[@]}"; do
		read -r name sha <<<"$entry"
		[ -f "$TEX/${name}_diff_1k.jpg" ] && continue
		echo "Doku indiriliyor: Poly Haven $name"
		fetch "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/$name/${name}_diff_1k.jpg" "$sha" "$TMP/${name}_diff_1k.jpg"
		mv "$TMP/${name}_diff_1k.jpg" "$TEX/"
	done
	echo "Zemin dokuları kurulu: $TEX"
}

# Trees: Gazebo Fuel OpenRobotics models; the meshes and textures are used, the model.sdf is written by dunya.py
TREES="$SIM/models/agaclar"
TREE_LIST=( # folder fuel-name version sha256
	"mese Oak%20tree 7 ae128176f707b571d2a2a47a1ab6b80596e81d96402501a64f4f28a49543daa5"
	"cam Pine%20Tree 6 d436a44229321314e79e4c2ba709dc926e833a5b5d90d16c5d085c2a74576e25"
)

install_trees() {
	local entry dir name ver sha
	for entry in "${TREE_LIST[@]}"; do
		read -r dir name ver sha <<<"$entry"
		[ "$(cat "$TREES/$dir/.tamam" 2>/dev/null)" = "$sha" ] && continue
		echo "Ağaç modeli indiriliyor: $dir"
		fetch "https://fuel.gazebosim.org/1.0/OpenRobotics/models/$name/$ver/$name.zip" "$sha" "$TMP/$dir.zip"
		rm -rf "${TREES:?}/$dir"
		mkdir -p "$TREES/$dir"
		unzip -q "$TMP/$dir.zip" 'meshes/*' 'materials/textures/*' -d "$TREES/$dir"
		echo "$sha" >"$TREES/$dir/.tamam"
	done
	echo "Ağaç modelleri kurulu: $TREES"
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
install_human
install_textures
install_trees
# Worlds with a description file get their ground and trees generated (only when something changed)
for spec in "$SIM"/worlds/*.yaml; do
	[ -e "$spec" ] || continue
	python3 "$SIM/araclar/dunya.py" "$(basename "$spec" .yaml)"
done
# Model files (spec "Model dosyası", rule 9: outside every repo): checked, never downloaded
PY="${TEZ_PYTHON:-$SIM/../../../.venv-tez/bin/python}"
if [ -x "$PY" ]; then
	"$PY" "$SIM/araclar/algilama.py"
else
	echo "UYARI: Python ortamı yok ($PY): model dosyaları denetlenmedi; ekip venv'i tez/env/VERSIONS.md'de (ya da TEZ_PYTHON)" >&2
fi
