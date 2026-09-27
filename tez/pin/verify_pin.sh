#!/usr/bin/env bash
# PX4 v1.17.0 surum kilidini dogrular.
#   tez/pin/verify_pin.sh             -> commit gecmisi + submodule kayitlari (CI bunu calistirir)
#   tez/pin/verify_pin.sh --worktree  -> ek olarak yerel submodule checkout'larini da kontrol eder
set -uo pipefail

EXPECTED_TAG="v1.17.0"
EXPECTED_BASE="d6f12ad1c4f70ad3230afd7d86e971421e02fef4"

cd "$(git rev-parse --show-toplevel)" || exit 2
LOCK="tez/pin/v1.17.0.lock"
ALLOW="tez/pin/allowed-paths.txt"
fail=0
ok()  { printf '  \033[32mOK\033[0m   %s\n' "$1"; }
err() { printf '  \033[31mHATA\033[0m %s\n' "$1"; fail=1; }

echo "PX4 surum kilidi kontrolu (${EXPECTED_TAG})"

# 1) Kilit dosyasi script ile tutarli mi
lock_base=$(awk '$1=="base_commit"{print $2}' "$LOCK")
[ "$lock_base" = "$EXPECTED_BASE" ] && ok "kilit dosyasi tabani ${EXPECTED_TAG}" \
  || err "kilit dosyasindaki taban ($lock_base) beklenen ${EXPECTED_TAG} commit'i degil"

# 2) HEAD, v1.17.0 commit'inden turemis mi
if git cat-file -e "${EXPECTED_BASE}^{commit}" 2>/dev/null && git merge-base --is-ancestor "$EXPECTED_BASE" HEAD; then
  ok "HEAD ${EXPECTED_TAG} uzerine kurulu"
else
  err "HEAD ${EXPECTED_TAG} (${EXPECTED_BASE:0:12}) uzerine kurulu degil"
fi

# 3) v1.17.0'dan beri sadece izinli yollar degismis mi (upstream merge'u burada yakalanir)
mapfile -t patterns < <(grep -vE '^\s*(#|$)' "$ALLOW")
bad=()
while IFS= read -r f; do
  allowed=0
  for p in "${patterns[@]}"; do [[ "$f" == $p ]] && { allowed=1; break; }; done
  [ "$allowed" = 1 ] || bad+=("$f")
done < <(git diff --name-only "$EXPECTED_BASE" HEAD 2>/dev/null)
if [ "${#bad[@]}" -eq 0 ]; then
  ok "v1.17.0 disi PX4 dosyasi degismemis"
else
  err "${#bad[@]} PX4 dosyasi izinsiz degismis (ilk 20):"
  printf '         %s\n' "${bad[@]:0:20}"
fi

# 4) .gitmodules kilitli haliyle ayni mi (branch takibi kapali)
exp_gm=$(awk '$1=="gitmodules_sha256"{print $2}' "$LOCK")
[ "$(sha256sum .gitmodules | cut -d' ' -f1)" = "$exp_gm" ] && ok ".gitmodules kilitli" \
  || err ".gitmodules degismis (branch takibi eklenmis olabilir)"
grep -qE '^\s*branch\s*=' .gitmodules && err ".gitmodules icinde 'branch =' satiri var"

# 5) Submodule commit kayitlari kilitle birebir ayni mi
expected=$(awk '$1=="submodule"{print $2, $3}' "$LOCK" | sort)
actual=$(git ls-tree -r HEAD | awk '$2=="commit"{print $3, $4}' | sort)
if [ "$expected" = "$actual" ]; then
  ok "$(echo "$expected" | wc -l) submodule kilitli commit'lerde"
else
  err "submodule kayitlari kilitten farkli:"
  diff <(echo "$expected") <(echo "$actual") | sed 's/^/         /'
fi

# 6) (yerel) checkout edilmis submodule'lar kayitli commit'lerde mi
if [ "${1:-}" = "--worktree" ]; then
  drift=$(git submodule status --recursive | grep -E '^[-+U]' || true)
  [ -z "$drift" ] && ok "yerel submodule checkout'lari dogru" \
    || { err "yerel submodule'lar kayitli commit'te degil (duzeltmek: git submodule update --init --recursive):"; echo "$drift" | sed 's/^/         /'; }
fi

if [ "$fail" = 0 ]; then echo "Sonuc: KILIT SAGLAM (${EXPECTED_TAG})"; else echo "Sonuc: KILIT BOZULMUS"; fi
exit "$fail"
