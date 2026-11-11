#!/usr/bin/env bash
# Build PX4 SITL (px4_sitl_default) and its Gazebo plugins for the thesis simulation into build/px4_sitl_tez, so the
# plain `make px4_sitl` build in build/px4_sitl_default is not affected. PX4 sources stay untouched.
#
#   tez/sim/derle.sh            # build (configures on first run)
#   tez/sim/derle.sh --temiz    # delete build/px4_sitl_tez first
#
# Out-of-tree PX4 modules: if tez/px4/src/CMakeLists.txt exists it is built in (EXTERNAL_MODULES_LOCATION);
# otherwise this is the stock SITL. When that choice differs from the configured build, CMake is configured again.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD="$REPO/build/px4_sitl_tez"

if [ "${1:-}" = "--temiz" ]; then
	rm -rf "$BUILD"
fi

EXTERNAL=""
if [ -f "$REPO/tez/px4/src/CMakeLists.txt" ]; then
	EXTERNAL="$REPO/tez/px4"
fi
CONFIGURED=""
if [ -f "$BUILD/CMakeCache.txt" ]; then
	CONFIGURED="$(sed -n 's/^EXTERNAL_MODULES_LOCATION:[A-Z]*=//p' "$BUILD/CMakeCache.txt")"
fi

if [ ! -f "$BUILD/build.ninja" ] || [ "$CONFIGURED" != "$EXTERNAL" ]; then
	echo "CMake yapılandırması: harici modüller ${EXTERNAL:-yok (stok PX4 SITL)}"
	cmake -S "$REPO" -B "$BUILD" -G Ninja \
		-DCONFIG=px4_sitl_default \
		-DEXTERNAL_MODULES_LOCATION="$EXTERNAL"
fi

cmake --build "$BUILD"
cmake --build "$BUILD" --target px4_gz_plugins

echo "Derleme tamam: $BUILD/bin/px4"
