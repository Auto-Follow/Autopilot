#!/usr/bin/env bash
# Build PX4 SITL (px4_sitl_default) and its Gazebo plugins for the thesis simulation into build/px4_sitl_tez, so the
# plain `make px4_sitl` build in build/px4_sitl_default is not affected. PX4 sources stay untouched.
#
#   tez/sim/derle.sh                          # build (configures on first run)
#   tez/sim/derle.sh --harici <klasör>        # with the out-of-tree PX4 modules of <klasör> (has src/CMakeLists.txt)
#   tez/sim/derle.sh --temiz                  # delete build/px4_sitl_tez first (combines with --harici)
#
# Out-of-tree PX4 modules (EXTERNAL_MODULES_LOCATION): the folder of --harici; without it tez/px4 if
# tez/px4/src/CMakeLists.txt exists; otherwise none, the stock SITL. The output is build/px4_sitl_tez in every case.
# When that choice differs from the one in the CMake cache, CMake is configured again, so a build without --harici
# after one with it is the stock SITL again. A module's command (bin/px4-<command>, see calistir.sh --px4-baslat)
# that is no longer in the build is removed after the build.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD="$REPO/build/px4_sitl_tez"

TEMIZ=0
HARICI=""
while [ $# -gt 0 ]; do
	case "$1" in
	--temiz) TEMIZ=1; shift ;;
	--harici)
		if [ $# -lt 2 ] || [ -z "$2" ]; then
			echo "--harici bir klasör ister (yardım: --help)" >&2
			exit 2
		fi
		HARICI="$2"
		shift 2
		;;
	-h | --help) sed -n '2,13p' "$0"; exit 0 ;;
	*) echo "Bilinmeyen seçenek: $1 (yardım: --help)" >&2; exit 2 ;;
	esac
done

EXTERNAL=""
if [ -n "$HARICI" ]; then
	if [ ! -f "$HARICI/src/CMakeLists.txt" ]; then
		echo "--harici $HARICI: içinde src/CMakeLists.txt olan klasör olmalı (PX4 EXTERNAL_MODULES_LOCATION;" \
			"ör. <dal>/tez/px4, src/ klasörünün kendisi değil)" >&2
		exit 2
	fi
	# absolute, so that it compares with the cache and does not depend on the folder derle.sh was started from
	EXTERNAL="$(realpath "$HARICI")"
elif [ -f "$REPO/tez/px4/src/CMakeLists.txt" ]; then
	EXTERNAL="$REPO/tez/px4"
fi
if [ -n "$EXTERNAL" ] && ! grep -q "PARENT_SCOPE" "$EXTERNAL/src/CMakeLists.txt"; then
	# PX4 reads the module list from the parent scope (CMakeLists.txt, add_subdirectory of <klasör>/src)
	echo "UYARI: $EXTERNAL/src/CMakeLists.txt'de PARENT_SCOPE yok: config_module_list_external PX4'e geçmez," \
		"harici modül derlenmez (tez/sim/README.md, \"C. Kendi PX4 modülünü takmak\")" >&2
fi

if [ "$TEMIZ" -eq 1 ]; then
	rm -rf "$BUILD"
fi

CONFIGURED=""
if [ -f "$BUILD/CMakeCache.txt" ]; then
	CONFIGURED="$(sed -n 's/^EXTERNAL_MODULES_LOCATION:[A-Z]*=//p' "$BUILD/CMakeCache.txt")"
fi

echo "Harici modüller: ${EXTERNAL:-yok (stok PX4 SITL)}"
if [ ! -f "$BUILD/build.ninja" ] || [ "$CONFIGURED" != "$EXTERNAL" ]; then
	echo "CMake yapılandırması (önbellekteki: ${CONFIGURED:-yok})"
	cmake -S "$REPO" -B "$BUILD" -G Ninja \
		-DCONFIG=px4_sitl_default \
		-DEXTERNAL_MODULES_LOCATION="$EXTERNAL"
fi

cmake --build "$BUILD"
cmake --build "$BUILD" --target px4_gz_plugins

# The build makes bin/px4-<command> for the modules it has but never removes one: drop those of modules that left
# the build (px4-alias.sh is written at configure time from the current module list).
COMMANDS="$(sed -n "s/^alias \([^=]*\)=.*/\1/p" "$BUILD/bin/px4-alias.sh")"
for link in "$BUILD"/bin/px4-*; do
	[ -L "$link" ] || continue
	name="${link##*/px4-}"
	if ! grep -qxF "$name" <<< "$COMMANDS"; then
		rm -f "$link"
		echo "Derlemede olmayan modülün komutu silindi: bin/px4-$name"
	fi
done

echo "Derleme tamam: $BUILD/bin/px4 (harici modüller: ${EXTERNAL:-yok})"
