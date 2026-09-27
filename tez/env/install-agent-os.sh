#!/usr/bin/env bash
# Agent OS'u SABIT v2.1.1 surumuyle ~/agent-os'a kurar.
# NOT: Resmi base-install.sh dosyalari 'main' branch'inden indirir (main = v3) - KULLANMAYIN.
set -euo pipefail

AOS_TAG="v2.1.1"
AOS_COMMIT="6a6495111e9f7f9cdab3c172814a7476e83a8ec9"
AOS_DIR="$HOME/agent-os"

if [ -d "$AOS_DIR" ]; then
  have=$(git -C "$AOS_DIR" rev-parse HEAD 2>/dev/null || echo "git-degil")
  if [ "$have" = "$AOS_COMMIT" ]; then echo "Agent OS ${AOS_TAG} zaten kurulu: $AOS_DIR"; exit 0; fi
  echo "HATA: $AOS_DIR var ama ${AOS_TAG} degil ($have). Once yedekleyip kaldirin." >&2; exit 1
fi

git -c advice.detachedHead=false clone -q --depth 1 --branch "$AOS_TAG" \
  https://github.com/buildermethods/agent-os.git "$AOS_DIR"
have=$(git -C "$AOS_DIR" rev-parse HEAD)
if [ "$have" != "$AOS_COMMIT" ]; then
  echo "HATA: indirilen commit ($have) beklenen ${AOS_TAG} commit'i degil. Kaldiriliyor." >&2
  rm -rf "$AOS_DIR"; exit 1
fi
git -C "$AOS_DIR" remote set-url --push origin no_push
echo "Agent OS ${AOS_TAG} kuruldu: $AOS_DIR ($AOS_COMMIT)"
