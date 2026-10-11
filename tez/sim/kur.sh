#!/usr/bin/env bash
# One-time setup of the simulation assets that are not kept in git.
#
#   tez/sim/kur.sh
#
# Human target: a MakeHuman person (CC0) animated with CMU motion capture, built by tez/sim/insan/uret.sh
# (downloads pinned by sha256, ~0.7 GB the first time, kept in ~/.cache/auto-follow-insan). Sources and licences:
# tez/sim/models/insan/KAYNAK.md.
set -euo pipefail

SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$SIM/models/insan/meshes"
# Bump when tez/sim/insan changes in a way that needs a rebuild
VERSION="makehuman-cmu-1 $(sha256sum "$SIM/insan/uret.py" | cut -c1-16)"

if [ -f "$DEST/.tamam" ] && [ "$(cat "$DEST/.tamam")" = "$VERSION" ]; then
	echo "İnsan modeli zaten kurulu: $DEST"
	exit 0
fi
rm -rf "$DEST"
"$SIM/insan/uret.sh"
echo "$VERSION" > "$DEST/.tamam"
echo "Kuruldu: $DEST"
