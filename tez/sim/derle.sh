#!/usr/bin/env bash
# Build PX4 SITL together with the thesis modules in tez/px4 (out-of-tree modules, PX4 sources stay untouched).
# Output goes to build/px4_sitl_tez, so the plain `make px4_sitl` build in build/px4_sitl_default is not affected.
#
#   tez/sim/derle.sh            # build (configures on first run)
#   tez/sim/derle.sh --temiz    # delete build/px4_sitl_tez first
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD="$REPO/build/px4_sitl_tez"

if [ "${1:-}" = "--temiz" ]; then
	rm -rf "$BUILD"
fi

if [ ! -f "$BUILD/build.ninja" ]; then
	cmake -S "$REPO" -B "$BUILD" -G Ninja \
		-DCONFIG=px4_sitl_default \
		-DEXTERNAL_MODULES_LOCATION="$REPO/tez/px4"
fi

cmake --build "$BUILD"
cmake --build "$BUILD" --target px4_gz_plugins

echo "Derleme tamam: $BUILD/bin/px4"
