#!/usr/bin/env bash
# التشغيل الكامل بأقصر زمن: التحليل متوازٍ على السور (--jobs)، ثم أدوات القياس متوازيةً تقرأ خبيئة التحليل
# (sarf/analyze_cache.py) بدل إعادة تحليل المصحف كلٌّ على حدة، ثم التقرير.
#   tools/run_full.sh [سجلّ]      (SARF_SENTENCES_BASE=<إصدار> لبيان التغيّر مقابل إصدارٍ مدقَّق)
set -e
export PYTHONHASHSEED=${PYTHONHASHSEED:-0}           # ترتيبٌ حتمي: التشغيل المتوازي يطابق التتابعي بايتاً ببايت
cd "$(dirname "$0")/.."
LOG=${1:-/tmp/sarf_full}
mkdir -p "$LOG"
t0=$(date +%s)
python3 tools/algebra_quran.py --jobs "${SARF_JOBS:-$(nproc)}" > "$LOG/algebra.log" 2>&1
t1=$(date +%s)
python3 tools/eval_algebra.py > "$LOG/eval_algebra.log" 2>&1 &
python3 tools/eval_case.py > "$LOG/eval_case.log" 2>&1 &
python3 tools/eval_root.py > "$LOG/eval_root.log" 2>&1 &
python3 tools/eval_protected.py > "$LOG/eval_protected.log" 2>&1 &
wait
python3 tools/audit_protected.py > "$LOG/audit_protected.log" 2>&1
python3 tools/algebra_report.py >> "$LOG/algebra.log" 2>&1
t2=$(date +%s)
echo "التحليل $((t1 - t0))ث، والقياس والتقرير $((t2 - t1))ث، والمجموع $((t2 - t0))ث" | tee "$LOG/timing.txt"
