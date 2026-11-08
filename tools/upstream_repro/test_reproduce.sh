#!/usr/bin/env bash
# test_reproduce.sh <نفس معاملات reproduce.sh عدا --out> : يختبر أداة الإعادة نفسها على آيتين (سريعاً):
#   ١ تشغيلٌ سليم في مسارٍ فيه مسافات ← REPRODUCED      ٢ فشل عاملٍ خلفي ← خروجٌ بغير الصفر باسمه ورمزه
#   ٣ فقد ملف نتيجة ← خروجٌ بغير الصفر «نتيجةٌ ناقصة»
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(mktemp -d)/repro dir with spaces"; mkdir -p "$ROOT"; FAIL=0
run() { bash "$HERE/reproduce.sh" "$@" --verses 1:1,2:8 --skip-tests; }
run "$@" --out "$ROOT/ok" > "$ROOT/ok.log" 2>&1; rc=$?
if [ $rc = 0 ] && [ -e "$ROOT/ok/REPRODUCED" ]; then echo "PASS R1 تشغيلٌ سليم في مسارٍ بمسافات"; else echo "FAIL R1 rc=$rc"; tail -5 "$ROOT/ok.log"; FAIL=1; fi
REPRO_FAULT=bg_fail run "$@" --out "$ROOT/bg" > "$ROOT/bg.log" 2>&1; rc=$?
if [ $rc != 0 ] && grep -q "فشلت العملية الخلفية snap_v47" "$ROOT/bg.log" && [ ! -e "$ROOT/bg/REPRODUCED" ]; then echo "PASS R2 فشل عاملٍ خلفي يُكشف باسمه (rc=$rc)"; else echo "FAIL R2 rc=$rc"; tail -5 "$ROOT/bg.log"; FAIL=1; fi
REPRO_FAULT=missing_result run "$@" --out "$ROOT/miss" > "$ROOT/miss.log" 2>&1; rc=$?
if [ $rc != 0 ] && grep -q "نتيجةٌ ناقصة" "$ROOT/miss.log" && [ ! -e "$ROOT/miss/REPRODUCED" ]; then echo "PASS R3 فقد ملف نتيجة يُكشف (rc=$rc)"; else echo "FAIL R3 rc=$rc"; tail -5 "$ROOT/miss.log"; FAIL=1; fi
[ $FAIL = 0 ] && echo "ALL OK" || echo "FAILED"
exit $FAIL
