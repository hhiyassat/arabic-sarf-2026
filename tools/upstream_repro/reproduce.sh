#!/usr/bin/env bash
# reproduce.sh — يعيد SARF_UPSTREAM_CONSUMER_REPAIR_02 كله من نسخٍ نظيفة (Linux وmacOS؛ bash 3.2 فما فوق؛ لا يلزم `timeout` ولا GNU coreutils).
# يحفظ PID كل عمليةٍ خلفية ويفحص خروجها منفردة، ويرفض النتيجة الناقصة أو المكرّرة أو المختلطة الإصدارات، ويعدّ الآيات المنجزة لا الملفات.
#
#   bash reproduce.sh --sarf <arabic-sarf-2026> --data <data> --hfn <HusseinFrameNet> --hfn-base <release_v36> --wazn <wazn-net> \
#        --amln <AMLN> --maq <Maqaiys-roots> --branch <التزام الفرع> --old <التزام المستهلك السابق> --out <مجلد جديد> [--verses 1:1,2:8] [--skip-tests]
# --verses و--skip-tests لاختبار الأداة نفسها وحده (التشغيل المرجعي على الآيات الـ6236 كلها بلا تخطٍّ).
# REPRO_FAULT=bg_fail|missing_result يحقن عطلاً لاختبار الأداة (tools/upstream_repro/test_reproduce.sh)؛ ولا يُعيَّن في التشغيل المرجعي.
set -euo pipefail
BASE=02b136014c9d3b25cc332e9455e331e5fd563e44
VERSES=""; SKIP_TESTS=0; JOBS=3; TMO=7200
while [ $# -gt 0 ]; do
  case "$1" in
    --sarf) SARF="$2";; --data) DATA="$2";; --hfn) HFN="$2";; --hfn-base) V36="$2";; --wazn) WAZN="$2";; --amln) AMLN="$2";; --maq) MAQ="$2";;
    --branch) BR_C="$2";; --old) OLD_C="$2";; --out) OUT="$2";; --verses) VERSES="$2";; --jobs) JOBS="$2";;
    --skip-tests) SKIP_TESTS=1; shift; continue;;
    *) echo "معامل غير معروف: $1" >&2; exit 2;;
  esac; shift 2
done
for v in SARF DATA HFN V36 WAZN AMLN MAQ BR_C OLD_C OUT; do [ -n "${!v:-}" ] || { echo "ناقص: $v" >&2; exit 2; }; done
[ ! -e "$OUT" ] || { echo "OUT موجود: لا يُستبدل تسليمٌ سابق ($OUT)" >&2; exit 2; }
command -v python3 >/dev/null || { echo "يلزم python3" >&2; exit 2; }
python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 13) else 1)' || { echo "يلزم Python 3.13" >&2; exit 2; }
for c in "$BASE" "$BR_C" "$OLD_C"; do git -C "$SARF" cat-file -e "$c^{commit}" || { echo "الالتزام $c غير موجود في $SARF" >&2; exit 2; }; done
for f in "$DATA/quran_hafs.tsv" "$DATA/quran-morphology.txt" "$V36/events.csv" "$V36/MANIFEST.json"; do [ -f "$f" ] || { echo "مفقود: $f" >&2; exit 2; }; done
for r in "$HFN" "$WAZN" "$AMLN" "$MAQ"; do git -C "$r" rev-parse --git-dir >/dev/null || { echo "ليس مستودع git: $r" >&2; exit 2; }; done
mkdir -p "$OUT/m" "$OUT/tests" "$OUT/meta"
export PYTHONHASHSEED=0 SARF_DEP_SALT=upc-2026-11-08-no-cache
LOG="$OUT/reproduce_steps.log"

# مهلةٌ محمولة: بايثون نفسها (subprocess.run(timeout=…))؛ ورمز الخروج 124 عند انقضائها كما في timeout
run_t() { local secs="$1"; shift
  python3 - "$secs" "$@" <<'PY'
import subprocess, sys
try:
    sys.exit(subprocess.run(sys.argv[2:], timeout=float(sys.argv[1])).returncode)
except subprocess.TimeoutExpired:
    print('TIMEOUT', ' '.join(sys.argv[2:])[:200], file=sys.stderr); sys.exit(124)
PY
}
# العمليات الخلفية: PID لكلٍّ وسمه، ويُنتظر كلٌّ منفرداً ويُفحص رمزه
PIDS=(); NAMES=()
bg() { local name="$1"; shift; ( "$@" ) > "$OUT/meta/$name.stdout" 2>&1 & PIDS+=("$!"); NAMES+=("$name"); echo "start $name pid=$!" >> "$LOG"; }
wait_all() { local i rc bad=0
  for i in "${!PIDS[@]}"; do
    if wait "${PIDS[$i]}"; then rc=0; else rc=$?; fi
    echo "exit ${NAMES[$i]} pid=${PIDS[$i]} rc=$rc" >> "$LOG"
    [ "$rc" = 0 ] || { echo "فشلت العملية الخلفية ${NAMES[$i]} (PID ${PIDS[$i]}) بالرمز $rc — $OUT/meta/${NAMES[$i]}.stdout" >&2; bad=1; }
  done
  PIDS=(); NAMES=(); [ "$bad" = 0 ] || exit 3
}
fault() { [ "${REPRO_FAULT:-}" = "$1" ]; }
VARG=(); [ -n "$VERSES" ] && VARG=(--verses "$VERSES")

# ١ تثبيت المصادر، وإعداد 6 نوفمبر من التزاماته المسجّلة
TOOLS="$(cd "$(dirname "$0")" && pwd)"
bash "$TOOLS/pin_sources.sh" "$HFN" "$WAZN" "$AMLN" "$MAQ" "$OUT/pinned" >> "$LOG"
# ٢ نسخٌ مجمّدة: الأساس، والمستهلك السابق، والفرع
frz() { mkdir -p "$2"; git -C "$SARF" archive "$1" | tar -x -C "$2"; ln -s "$DATA" "$2/data"; echo "$1" > "$2/.frozen_commit"; }
frz "$BASE" "$OUT/frozen_base"; frz "$OLD_C" "$OUT/frozen_old"; frz "$BR_C" "$OUT/frozen_branch"
B="$OUT/frozen_branch"
python3 "$TOOLS/make_pins.py" "$OUT/pinned" "$OUT/meta/pins_regenerated.json" >> "$LOG"
python3 - "$OUT/meta/pins_regenerated.json" "$B/tools/upstream/pins_2026_11_08.json" <<'PY'
import sys, json
a, b = (json.load(open(p)) for p in sys.argv[1:3])
assert a == b, 'سجلّ التثبيت المولَّد يخالف المحفوظ: ' + str({k for k in a if a[k] != b.get(k)})
PY
V47="$OUT/pinned/hfn/release/release_v47"
# بيئة الاستهلاك: مصفوفة (لا سلسلة تُقسَّم)، فالمسارات بمسافات سليمة
UPENV=(SARF_HFN="$V36" SARF_UP_PINS="$B/tools/upstream/pins_2026_11_08.json" SARF_UP_HFN="$OUT/pinned/hfn" SARF_UP_WAZN="$OUT/pinned/wazn"
       SARF_UP_AMLN="$OUT/pinned/amln" SARF_UP_MAQ="$OUT/pinned/maq")
OLDENV=(SARF_HFN="$V36" SARF_UP_PINS="$OUT/frozen_old/tools/upstream/pins_2026_11_08.json" SARF_UP_HFN="$OUT/pinned/hfn" SARF_UP_WAZN="$OUT/pinned/wazn"
        SARF_UP_AMLN="$OUT/pinned/amln" SARF_UP_MAQ="$OUT/pinned/maq")
meta() { python3 - "$1" "$2" "$3" <<'PY'
import sys, json, hashlib
name, hp, rel = sys.argv[1:4]
json.dump(dict(run=name, sarf_hfn=hp, release_dir=hp.rstrip('/').split('/')[-1], manifest_sha256=hashlib.sha256(open(hp + '/MANIFEST.json', 'rb').read()).hexdigest(),
               release_ok=rel or None), open(f"{name}.meta.json", 'w'))
PY
}
snap() { local dir="$1" hp="$2" rel="$3" out="$4"
  (cd "$OUT/meta" && meta "$(basename "$out")" "$hp" "$rel")
  # run_t دالّةٌ في الصدفة: تُصدَّر المتغيّرات في صدفةٍ فرعية (لا env، فهو لا يستدعي الدوال)
  if [ -n "$rel" ]; then (cd "$dir" && export SARF_HFN="$hp" SARF_HFN_RELEASE_OK="$rel" && run_t "$TMO" python3 -s tools/snapshot_outputs.py dump . "$out" --jobs 2 "${VARG[@]}")
  else (cd "$dir" && unset SARF_HFN_RELEASE_OK && export SARF_HFN="$hp" && run_t "$TMO" python3 -s tools/snapshot_outputs.py dump . "$out" --jobs 2 "${VARG[@]}"); fi
  fault bg_fail && [ "$(basename "$out")" = snap_v47.pkl.gz ] && { echo "REPRO_FAULT bg_fail" >&2; return 7; }
  return 0
}
# ٣ الوضع أ (الأساس والفرع)، والوضع ج (الشيفرة نفسها على v47)
bg snap_base snap "$OUT/frozen_base" "$V36" "" "$OUT/m/snap_base.pkl.gz"
bg snap_branch snap "$B" "$V36" "" "$OUT/m/snap_branch.pkl.gz"
bg snap_v47 snap "$OUT/frozen_base" "$V47" release_v47 "$OUT/m/snap_v47.pkl.gz"
wait_all
(cd "$B" && python3 -s tools/snapshot_outputs.py cmp "$OUT/m/snap_base.pkl.gz" "$OUT/m/snap_branch.pkl.gz" --json "$OUT/m/cmp_base_branch.json") >> "$LOG"
(cd "$B" && env SARF_HFN="$V36" python3 -s tools/upstream_shadow_diff.py "$OUT/m/snap_base.pkl.gz" "$OUT/m/snap_v47.pkl.gz" "$V36" "$V47" "$OUT/m/shadow_v47" \
  && env SARF_HFN="$V36" python3 -s tools/upstream_shadow_attribution.py "$OUT/m/shadow_v47.jsonl.gz" "$OUT/m/snap_base.pkl.gz" "$OUT/m/snap_v47.pkl.gz" "$V36" "$V47" \
     "$OUT/m/shadow_attribution") >> "$LOG"
# ٤ الوضع ب: المستهلك السابق (72e17c4) والمصلَح على المصادر نفسها، ثم الشهادات بالأدلّة وبدونها
in_dir() { local d="$1"; shift; (cd "$d" && env "$@"); }
bg cand_old in_dir "$OUT/frozen_old" "${OLDENV[@]}" python3 -s tools/upstream_candidates.py "$OUT/m/cand_old.jsonl.gz" "$OUT/m/cand_old.json" --jobs 2 "${VARG[@]}"
bg cand_new in_dir "$B" "${UPENV[@]}" python3 -s tools/upstream_candidates.py "$OUT/m/cand.jsonl.gz" "$OUT/m/cand.json" --jobs 2 "${VARG[@]}"
wait_all
fault missing_result && rm -f "$OUT/m/cand_old.json"
(cd "$B" && export SARF_HFN="$V36" && run_t "$TMO" python3 -s tools/upstream_conflicts.py "$OUT/m/cand.jsonl.gz" "$OUT/m/cert_check.json" --jobs "$JOBS" "${VARG[@]}") >> "$LOG"
for f in cand_old.json cand.json cand_old.jsonl.gz cand.jsonl.gz cert_check.json; do [ -s "$OUT/m/$f" ] || { echo "نتيجةٌ ناقصة: $OUT/m/$f" >&2; exit 4; }; done
(cd "$B" && python3 -s tools/upstream_repair_measure.py "$OUT/m/cand_old.jsonl.gz" "$OUT/m/cand.jsonl.gz" "$V47" "$OUT/pinned/wazn" "$OUT/m/repair" "$OUT/m/cert_check.json") >> "$LOG"
# ٥ الاختبارات على نسخة الفرع (كل ملفٍّ عمليةٌ مستقلة بمهلةٍ محمولة)، مع عدّ الفحوص المنفّذة لا الملفات
if [ "$SKIP_TESTS" = 0 ]; then
  TL=(); while IFS= read -r t; do TL+=("$t"); done < <(cd "$B" && ls tests/test_*.py)
  for t in "${TL[@]}"; do
    n="$(basename "$t" .py)"
    # رمز خروج الاختبار نفسه في ملفّه؛ والعملية الخلفية تفشل إن لم يُكتب
    ( cd "$B" && export "${UPENV[@]}" && if run_t 3000 python3 -P -s "$t" > "$OUT/tests/$n.out" 2>&1; then echo 0; else echo $?; fi > "$OUT/tests/$n.exit" ) &
    PIDS+=("$!"); NAMES+=("test_$n")
    while [ "$(jobs -rp | wc -l | tr -d ' ')" -ge "$JOBS" ]; do sleep 2; done
  done
  wait_all
fi
# ٦ الثوابت: عدد الآيات المنجزة، ولا تكرار، ولا خلط إصدارات، والحماية، والاختبارات بعدّ فحوصها
python3 - "$OUT" "$VERSES" "$SKIP_TESTS" "$V36" "$V47" <<'PY'
import sys, json, glob, os, gzip, pickle, re, hashlib
O, VS, SKIP, V36, V47 = sys.argv[1], sys.argv[2], sys.argv[3] == '1', sys.argv[4], sys.argv[5]
J = lambda p: json.load(open(os.path.join(O, p), encoding='utf-8'))
sys.path.insert(0, os.path.join(O, 'frozen_branch'))
from sarf import quran_source
want = [f'{s}:{v}' for s, v, _ in quran_source.rows()] if not VS else VS.split(',')
for n in ('snap_base', 'snap_branch', 'snap_v47'):
    S = pickle.load(gzip.open(os.path.join(O, 'm', n + '.pkl.gz')))
    assert sorted(S) == sorted(set(want)) and len(S) == len(want), (n, 'عدد الآيات المنجزة', len(S), 'المتوقَّع', len(want))
    m = json.load(open(os.path.join(O, 'meta', n + '.pkl.gz.meta.json')))
    exp = V47 if n == 'snap_v47' else V36
    assert m['sarf_hfn'] == exp and m['manifest_sha256'] == hashlib.sha256(open(exp + '/MANIFEST.json', 'rb').read()).hexdigest(), (n, 'إصدارٌ مختلط', m)
c = J('m/cmp_base_branch.json'); assert c['violations'] == 0 and c['verses'] == len(want), ('الأساس ≠ الفرع', c['violations'])
for n in ('cand', 'cand_old'):
    s = J(f'm/{n}.json')
    assert {x: s['provenance'][x]['commit'] for x in ('hfn', 'wazn', 'amln', 'maq')} == s['pins']['commits'], (n, 'التزامٌ غير المثبت')
    assert all(not v for v in s['isolation']['resource_writes'].values()), (n, 'كتابةٌ في المصادر')
    R = [json.loads(l) for l in gzip.open(os.path.join(O, 'm', n + '.jsonl.gz'), 'rt', encoding='utf-8')]
    keys = [(r['verse'], r['relation_id']) for r in R]
    assert len(keys) == len(set(keys)), (n, 'سجلّ وقوعٍ مكرّر')
    assert set(r['verse'] for r in R) <= set(want), (n, 'آيةٌ خارج المطلوب')
k = J('m/cert_check.json'); assert k['identical_without_evidence'] == k['sentences'] and k['sentences'] > 0, ('شهادةٌ تغيّرت بالأدلّة', k['sentences'])
r = J('m/repair.json')
assert r['identity_root_mismatch_rows']['after_match_with_identity_not_ok'] == 0 and not r['identity_root_mismatch_rows']['after'], ('تعارض هوية مرفق', r['identity_root_mismatch_rows'])
assert r['evidence_ids']['after']['ids_with_different_content'] == 0 and not r['evidence_ids']['after']['registry_errors'], 'تصادم معرّفات'
assert r['evidence_ids']['after']['certificate_refs']['orphan'] in (0, None), 'مرجعٌ يتيم'
T = {}
if not SKIP:
    for p in glob.glob(os.path.join(O, 'tests', '*.exit')):
        n = os.path.basename(p)[:-5]
        out = open(os.path.join(O, 'tests', n + '.out'), encoding='utf-8', errors='replace').read()
        T[n] = dict(exit=open(p).read().strip(), checks=len(re.findall(r'^(?:PASS|FAIL|CAUGHT|MISSED)\b', out, re.M)),
                    failed=len(re.findall(r'^(?:FAIL|MISSED)\b', out, re.M)))
    files = glob.glob(os.path.join(O, 'frozen_branch', 'tests', 'test_*.py'))
    assert len(T) == len(files), ('ملف اختبارٍ بلا نتيجة', len(T), len(files))
    assert all(t['exit'] == '0' and t['failed'] == 0 for t in T.values()), {k: v for k, v in T.items() if v['exit'] != '0' or v['failed']}
json.dump(dict(verses=len(want), tests=T, test_files=len(T), test_files_exit0=sum(t['exit'] == '0' for t in T.values()),
               test_files_with_checks=sum(t['checks'] > 0 for t in T.values()), checks_executed=sum(t['checks'] for t in T.values()),
               helper_files_without_checks=sorted(k for k, t in T.items() if t['checks'] == 0)),
          open(os.path.join(O, 'm', 'invariants.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('OK: آيات', len(want), '؛ الأساس = الفرع؛ لا خلط إصدارات؛ لا تكرار؛ الشهادات مستقلة؛ لا تعارض هوية مرفق؛ لا تصادم معرّفات؛ الاختبارات',
      len(T), 'ملفاً بفحوص', sum(t['checks'] for t in T.values()))
PY
touch "$OUT/REPRODUCED"
