"""tests/test_c063_morph.py — SARF_COMPLETION_FROM_REPORT_063 §٤–٥: إصلاحات صرفية بقواعد مكتوبة لا بقوائم كلمات.
- الضمة على فاء الثلاثي الأجوف مع الضمير المتحرك لا تكون إلا في الواوي (قُلْنَا ← قول، لا قيل)، والكسرة تبقى غير معيِّنة.
- المضعَّف: الشدة حرفان، أولهما العين وثانيهما اللام (حَقّ ← ح ق ق).
- التحقيق الأمامي: الجذر معتلّ اللام لا يحقّق كلمةً آخرها عينٌ مشدَّدة (حَقّ ← حقو ممنوع)، إلا أن تكون اللام هي العين (حَيّ ← حيي).
- مداخل الجذر نفسه بأحداثٍ مختلفة تُعرض كلها، لا أولها."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from sarf.algebra import align_radicals, _weak_lam_barred
FAIL = []


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:300]}'))
    if not ok:
        FAIL.append(name)


class _C:                                     # خليةٌ بالحرف والحركة كما يقرؤها align_radicals (C وH)
    def __init__(self, C, H):
        self.C, self.H = C, H


haqq = [_C('ح', 'a'), _C('ق', '∅'), _C('ق', 'u')]
hayy = [_C('ح', 'a'), _C('ي', '∅'), _C('ي', 'u')]
check('M01 حَقّ ← ح ق ق: الشدة عينٌ ولام', align_radicals(haqq, 'حقق')[0] == ['r1', 'r2', 'r3'], align_radicals(haqq, 'حقق'))
check('M02 حَقّ لا يحقّق حقو (اللام المعتلّة لا تُدغم في القاف)', _weak_lam_barred(haqq, 'حقو') and not _weak_lam_barred(haqq, 'حقق'))
check('M03 حَيّ يحقّق حيي (اللام هي العين): لا منع', not _weak_lam_barred(hayy, 'حيي'), align_radicals(hayy, 'حيي'))
qadin = [_C('ق', 'a'), _C('ا', '∅'), _C('ض', 'i')]
check('M04 قَاضٍ (لا شدة): حذف اللام المعتلّة جائز، ولا منع', not _weak_lam_barred(qadin, 'قضي'))
from sarf.stages import run_ref
C = run_ref('2:282')
U = C.get('units')['2:282']['units']
g = U[(26, 0)]
check('M05 «الْحَقُّ» (2:282:27) مغلقة على حقق، وبديلا الحدث معروضان، والممنوع مسمّىً في الدليل',
      g.closed and g.Theta.get('R') == 'حقق' and ' أو ' in g.Theta.get('P', '') and len(g.Theta.get('lex_entries') or []) == 2,
      (g.closed, g.Theta.get('R'), g.Theta.get('P'), g.O.get('deferred')))
ev = str(getattr(g.Omega[0], 'ev', ''))
check('M06 الدليل يسمّي الجذر الممنوع وسببه المكتوب (لا يُحذف بلا أثر)', 'حقو' in ev and 'ممنوعٌ بالتحقيق المكتوب' in ev, ev[:300])
C2 = run_ref('2:34')
q = C2.get('units')['2:34']['units'][(1, 0)]
check('M07 «قُلْنَا» (2:34) مغلقة على قول', q.closed and q.Theta.get('R') == 'قول', (q.Theta.get('R'), q.O.get('deferred')))
# الأجوف بالضمة في v47 (حيث «قيل» فعلٌ في المورد): الضمة تمنع قيل، والفتحة في «قَالُوا» تبقى ملتبسة
from sarf.root import hfn as _hfn
_H = _hfn()
v47 = _H.path if _H.release == 'release_v47' else os.environ.get('SARF_HFN_V47', '')   # المحمَّل إن كان المستهدف، لا مسار بيئةٍ بعينها
if v47 and os.path.exists(os.path.join(v47, 'events.csv')):
    import subprocess, json
    env = {k: v for k, v in os.environ.items() if k not in ('SARF_HFN_TARGET_CONFIG', 'SARF_HFN_EXPERIMENTAL_OK')}   # V48C02: لا يرث الطفل إعداد v48 التجريبي
    env.update(SARF_HFN=v47, SARF_HFN_RELEASE_OK='release_v47', PYTHONHASHSEED='0')
    code = (f"import sys,json\nsys.path.insert(0,{ROOT!r})\nfrom sarf.stages import run_ref\nout={{}}\nfor ref,k in (('2:34',(1,0)),('2:11',(7,0))):\n"
            "    G=run_ref(ref).get('units')[ref]['units'][k]; out[ref]=[G.closed, G.Theta.get('R'), G.O.get('deferred')]\nprint(json.dumps(out,ensure_ascii=False))")
    r = subprocess.run([sys.executable, '-P', '-s', '-c', code], env=env, capture_output=True, text=True, cwd=ROOT)
    o = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {}
    check('M08 v47: «قُلْنَا» قول وحده (الضمة)، و«قَالُوا» ملتبسةٌ بين قول وقيل (لا يُختار بلا دليل)',
          o.get('2:34', [None, None])[1] == 'قول' and o.get('2:11', [True])[0] is False and 'قيل' in str(o.get('2:11')), (o, r.stderr[-300:]))
else:
    print('SKIP M08 (v47 غير محمَّل ولا SARF_HFN_V47 معيَّن) — تخطٍّ لا نجاح')
import sarf.root as R
src = open(R.__file__, encoding='utf-8').read()
check('M09 القاعدة مكتوبةٌ بشرطها (الماضي، الثلاثي، الضمة بلا كسرة)، لا بقائمة كلمات',
      "kind == 'madi' and cls == 'I' and DAMMA in before and KASRA not in before" in src)
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
