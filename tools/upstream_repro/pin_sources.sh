#!/usr/bin/env bash
# pin_sources.sh — نسخٌ مثبتة معزولة من المصادر الأربع بـgit archive عند الالتزام المطلوب (لا تبديل فرع، ولا سحب، ولا كتابة في مستودعات المالك).
# الاستعمال: bash pin_sources.sh <HFN_REPO> <WAZN_REPO> <AMLN_REPO> <MAQ_REPO> <OUT_DIR>
set -euo pipefail
HFN="$1" WAZN="$2" AMLN="$3" MAQ="$4" OUT="$5"
[ ! -e "$OUT" ] || { echo "OUT موجود: $OUT" >&2; exit 2; }
mkdir -p "$OUT"
pin() {  # repo commit name [paths...]
  local repo=$1 c=$2 name=$3; shift 3
  local full; full=$(git -C "$repo" rev-parse --verify "$c^{commit}") || { echo "الالتزام $c غير موجود في $repo (اجلبه أولاً: git fetch)" >&2; exit 2; }
  mkdir -p "$OUT/$name"
  git -C "$repo" archive "$full" -- "$@" | tar -x -C "$OUT/$name"
  echo "$full" > "$OUT/$name/.pinned_commit"
  echo "$name $full"
}
# ملفات 06_handoff العليا (لفاحص الإصدار): مصفوفةٌ بلا تقسيم نصّي (أسماء بمسافات أو أحرف عربية)؛ متوافقٌ مع bash 3.2 (macOS)
HANDOFF=()
while IFS= read -r p; do
  [ "$(git -c core.quotepath=off -C "$HFN" cat-file -t "22dcb06:$p")" = blob ] && HANDOFF+=("$p")
done < <(git -c core.quotepath=off -C "$HFN" ls-tree --name-only 22dcb06 06_handoff/)
pin "$HFN" 22dcb06 hfn release/release_v36 release/release_v37 release/release_v46 release/release_v47 02_roots tools api scripts 00_governance "${HANDOFF[@]}"
pin "$WAZN" 0f647e5 wazn .
pin "$AMLN" 8da48f7 amln .
pin "$MAQ" 6c2c58f maq .
# المصادر للقراءة وحدها: يُمنع كل كتابةٍ فيها من البداية
chmod -R a-w "$OUT"
