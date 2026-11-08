#!/usr/bin/env bash
# pin_historical.sh — إعادة تركيب إعداد المستهلك السابق (تشغيل 6 نوفمبر R2) من التزاماته المسجّلة في أثره (upstream.json → provenance):
#   AMLN 1cadaa3، wazn b8a4672 (mutawaa_v3 وتعدّي الوسيط v1)، HFN 41dbbeb (release_v36)، HFN a4cac9a (release_v37 سمةً)، Maqaiys 6c2c58f
# الاستعمال: bash pin_historical.sh <HFN_REPO> <WAZN_REPO> <AMLN_REPO> <MAQ_REPO> <OUT_DIR>
set -euo pipefail
HFN="$1" WAZN="$2" AMLN="$3" MAQ="$4" OUT="$5"
[ ! -e "$OUT" ] || { echo "OUT موجود: $OUT" >&2; exit 2; }
mkdir -p "$OUT"
pin() { local repo=$1 c=$2 name=$3; shift 3
  local full; full=$(git -C "$repo" rev-parse --verify "$c^{commit}") || { echo "الالتزام $c غير موجود في $repo" >&2; exit 2; }
  mkdir -p "$OUT/$name"; git -C "$repo" archive "$full" -- "$@" | tar -x -C "$OUT/$name"; echo "$full" > "$OUT/$name/.pinned_commit"; echo "$name $full"; }
pin "$AMLN" 1cadaa3 amln .
pin "$WAZN" b8a4672 wazn .
pin "$HFN" 41dbbeb hfn release/release_v36 tools api
pin "$HFN" a4cac9a hfn37 release/release_v37
pin "$MAQ" 6c2c58f maq .
chmod -R a-w "$OUT"
