#!/usr/bin/env bash
# reproduce.sh — يعيد قياس SARF_COMPLETION_FROM_REPORT_063 من نسختين نظيفتين (git archive) للأساس والالتزام النهائي.
# Linux وmacOS؛ bash 3.2 فما فوق؛ Python 3.13. لا يكتب في المستودع ولا يستبدل مجلداً موجوداً.
#
#   bash reproduce.sh --sarf <arabic-sarf-2026> --data <data> --hfn-v36 <release_v36> [--hfn-v47 <release_v47>] \
#        --final <الالتزام النهائي> --out <مجلد جديد> [--jobs 3] [--skip-tests]
# --data: المجلد الذي فيه quran_hafs.tsv وquran-morphology.txt (QAC للقياس وحده). وبلا --hfn-v47 تُتخطّى قياسات v47 وتُعلَن NOT_RUN.
set -euo pipefail
BASE=67a4df885fbd4d8e9ae8295d34f6c68f4b7a29e0          # التزام صفحة 063 (BASE_REPORT_COMMIT 56936fe… في سجلّ الصفحات؛ وهذا رأس فرعها)
V36_SHA=941d1cf7bdc3                                     # بادئة بصمة events.csv في v36 (sha256)
V47_SHA=c62e7232638e                                     # بادئة بصمة events.csv في v47 المثبَّت (HFN 22dcb06)
JOBS=3; SKIP_TESTS=0; V47=""
while [ $# -gt 0 ]; do
  case "$1" in
    --sarf) SARF="$2";; --data) DATA="$2";; --hfn-v36) V36="$2";; --hfn-v47) V47="$2";; --final) FINAL="$2";; --out) OUT="$2";;
    --jobs) JOBS="$2";; --skip-tests) SKIP_TESTS=1; shift; continue;;
    *) echo "معامل غير معروف: $1" >&2; exit 2;;
  esac; shift 2
done
for v in SARF DATA V36 FINAL OUT; do [ -n "${!v:-}" ] || { echo "ناقص: --$v" >&2; exit 2; }; done
[ ! -e "$OUT" ] || { echo "OUT موجود: لا يُستبدل ($OUT)" >&2; exit 2; }
python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 13) else 1)' || { echo "يلزم Python 3.13" >&2; exit 2; }
for c in "$BASE" "$FINAL"; do git -C "$SARF" cat-file -e "$c^{commit}" || { echo "الالتزام $c غير موجود في $SARF" >&2; exit 2; }; done
for f in "$DATA/quran_hafs.tsv" "$DATA/quran-morphology.txt" "$V36/events.csv"; do [ -f "$f" ] || { echo "مفقود: $f" >&2; exit 2; }; done
sha() { python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$1"; }
s36=$(sha "$V36/events.csv"); [ "${s36:0:12}" = "$V36_SHA" ] || { echo "بصمة v36 لا تطابق: $s36" >&2; exit 2; }
if [ -n "$V47" ]; then s47=$(sha "$V47/events.csv"); [ "${s47:0:12}" = "$V47_SHA" ] || { echo "بصمة v47 لا تطابق: $s47" >&2; exit 2; }; fi
mkdir -p "$OUT/m" "$OUT/tests"
LOG="$OUT/reproduce_steps.log"; : > "$LOG"
export PYTHONHASHSEED=0 SARF_DEP_SALT=c063-repro-no-cache
FINAL_FULL=$(git -C "$SARF" rev-parse "$FINAL")
echo "base $BASE final $FINAL_FULL v36 $s36 v47 ${s47:-NOT_RUN}" >> "$LOG"
# ١ نسختان نظيفتان من git (لا worktree ولا ملفات غير ملتزم بها)
for n in base final; do
  c=$BASE; [ $n = final ] && c=$FINAL_FULL
  mkdir -p "$OUT/$n"; git -C "$SARF" archive "$c" | tar -x -C "$OUT/$n"; ln -s "$(cd "$DATA" && pwd)" "$OUT/$n/data"
done
T="$OUT/final/tools/completion063"
step() { local name="$1"; shift; echo "start $name" >> "$LOG"; if "$@" > "$OUT/m/$name.stdout" 2>&1; then echo "exit $name rc=0" >> "$LOG";
         else rc=$?; echo "exit $name rc=$rc" >> "$LOG"; echo "فشلت الخطوة $name ($rc): $OUT/m/$name.stdout" >&2; exit 3; fi; }
in36() { local d="$1"; shift; (cd "$OUT/$d" && SARF_HFN="$V36" "$@"); }
in47() { local d="$1"; shift; (cd "$OUT/$d" && SARF_HFN="$V47" SARF_HFN_RELEASE_OK=release_v47 "$@"); }
# ٢ الاختبارات كلها في النسخة النهائية (كلٌّ بـ python3 -P -s، ورمزه وزمنه)
if [ "$SKIP_TESTS" = 0 ]; then
  : > "$OUT/tests/results.tsv"
  for t in "$OUT"/final/tests/*.py; do
    s=$(date +%s); if in36 final env SARF_HFN_V47="${V47:-/nonexistent}" python3 -P -s "$t" > "$OUT/tests/$(basename "$t").log" 2>&1; then rc=0; else rc=$?; fi
    printf '%s\t%s\t%s\n' "$(basename "$t")" "$rc" "$(( $(date +%s) - s ))" >> "$OUT/tests/results.tsv"
  done
fi
# ٣ المصحف كله: لقطة التحليل، والمحاور، والشهادات — للأساس والنهائي على v36
for n in base final; do
  step snap_$n in36 $n python3 -s "$OUT/final/tools/snapshot_outputs.py" dump . "$OUT/m/snap_$n.pkl.gz" --jobs "$JOBS"
  step axes_$n in36 $n python3 -s "$T/measure_axes.py" dump . "$OUT/m/axes_$n.jsonl.gz" --jobs "$JOBS"
  step certs_$n in36 $n python3 -s "$T/measure_certs.py" dump . "$OUT/m/certs_$n.jsonl.gz" --jobs "$JOBS"
  step evalroot_$n in36 $n env SARF_ROOT_DUMP="$OUT/m/rootdump_$n.jsonl" python3 -s tools/eval_root.py
done
step recon_final in36 final python3 -s "$T/measure_reconciliation.py" "$OUT/m/recon_final.json" --jobs "$JOBS"
step cmp_snap python3 -s "$OUT/final/tools/snapshot_outputs.py" cmp "$OUT/m/snap_base.pkl.gz" "$OUT/m/snap_final.pkl.gz" --json "$OUT/m/cmp_snap.json" || true
step cmp_axes python3 -s "$T/measure_axes.py" cmp "$OUT/m/axes_base.jsonl.gz" "$OUT/m/axes_final.jsonl.gz" "$OUT/m/cmp_axes.json"
step cmp_certs python3 -s "$T/measure_certs.py" cmp "$OUT/m/certs_base.jsonl.gz" "$OUT/m/certs_final.jsonl.gz" "$OUT/m/cmp_certs.json"
step cmp_roots python3 -s "$T/compare_rootdumps.py" "$OUT/m/rootdump_base.jsonl" "$OUT/m/rootdump_final.jsonl" "$OUT/m/cmp_roots.json"
step cmp_units python3 -s "$T/compare_units.py" "$OUT/m/snap_base.pkl.gz" "$OUT/m/snap_final.pkl.gz" "$DATA/quran-morphology.txt" "$OUT/m/cmp_units.json"
# ٤ سجلّ القضايا ومصفوفة المراحل (2:282)
step reg_base in36 final python3 -s "$T/issue_registry.py" "$OUT/base" "$OUT/m/registry_base.json"
step reg_final in36 final python3 -s "$T/issue_registry.py" "$OUT/final" "$OUT/m/registry_final.json"
step issue_log python3 -s "$T/issue_log.py" "$OUT/m/registry_base.json" "$OUT/m/registry_final.json" "$OUT/m/issue_log.json" --md "$OUT/m/issue_log.md"
step matrix in36 final python3 -s "$T/stage_matrix.py" . "$OUT/m/stage_matrix.json" --md "$OUT/m/stage_matrix.md"
# ٥ v47 (الإصدار الافتراضي باقٍ v36): أثر الانتقال بالشيفرة النهائية نفسها
if [ -n "$V47" ]; then
  step snap_final_v47 in47 final python3 -s "$OUT/final/tools/snapshot_outputs.py" dump . "$OUT/m/snap_final_v47.pkl.gz" --jobs "$JOBS"
  step evalroot_final_v47 in47 final env SARF_ROOT_DUMP="$OUT/m/rootdump_final_v47.jsonl" python3 -s tools/eval_root.py
  step cmp_snap_v47 python3 -s "$OUT/final/tools/snapshot_outputs.py" cmp "$OUT/m/snap_final.pkl.gz" "$OUT/m/snap_final_v47.pkl.gz" --json "$OUT/m/cmp_snap_v47.json" || true
  step cmp_roots_v47 python3 -s "$T/compare_rootdumps.py" "$OUT/m/rootdump_final.jsonl" "$OUT/m/rootdump_final_v47.jsonl" "$OUT/m/cmp_roots_v47.json"
  step cmp_units_v47 python3 -s "$T/compare_units.py" "$OUT/m/snap_final.pkl.gz" "$OUT/m/snap_final_v47.pkl.gz" "$DATA/quran-morphology.txt" "$OUT/m/cmp_units_v47.json"
else echo "v47 NOT_RUN: --hfn-v47 غير معطى" >> "$LOG"; fi
touch "$OUT/REPRODUCED"; echo "تمّ: $OUT"
