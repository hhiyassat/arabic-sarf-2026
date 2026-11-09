"""tests/test_c063_objects.py — SARF_COMPLETION_FROM_REPORT_063 §٦ و§١: المفعول المرشّح بتعدٍّ مرشّح (O03)، ونصب لفظ الجلالة المكتوب،
وأنواع «بلا عامل» (وسمٌ يفصل الأسباب ولا يغيّر الحكم)."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from sarf.stages import run_ref
from sarf.relations import LICENSED, DEFERRED
FAIL = []


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:400]}'))
    if not ok:
        FAIL.append(name)


C = run_ref('2:282')
V = C.get('records')['2:282']
R = V['records']
tok = {u: (loc, t) for u, loc, t in V['tokens']}
objs = [r for r in R if r['type'] == 'OBJECT']
o3 = {r['texts']['verb']: r for r in objs if r['rule_id'] == 'O03'}
check('K01 «وليتق الله» و«واتقوا الله»: لفظ الجلالة مفعولٌ مرشّح في سجلّ O03، لا بلا دور',
      {'يَتَّقِ', 'اتَّقُوا'} <= set(o3) and all(o3[v]['texts']['object'] == 'اللَّهَ' for v in ('يَتَّقِ', 'اتَّقُوا')), sorted(o3))
check('K02 O03 مؤجَّلٌ دائماً (التعدّي مرشّح غير مثبت): لا ترخيص ولا حافّة في الشبكة',
      all(r['status'] == DEFERRED and not r['edges'] for r in o3.values()), [(r['status'], r['edges']) for r in o3.values()])
check('K03 مقدّمات O03 تسمّي دليل التعدّي غير المقرّ (is_fact=False) والعلامة المكتوبة',
      all(any('is_fact=False' in p for p in r['premises']) and any('النصب مكتوب' in p for p in r['premises']) for r in o3.values()))
check('K04 المعرفة («اللَّهَ») بلا بدائل حال/تمييز (مانع التعريف)، والنكرة («شيئاً») تحفظ بدائلها',
      not o3['يَتَّقِ']['alternatives'] and set(o3['يَبْخَسْ']['alternatives']) == {'حال', 'تمييز', 'مفعول مطلق'})
ax = V['axes']
g28 = next(u for u, (loc, t) in tok.items() if loc == '2:282:29')
check('K05 لا دور مرخَّص للمؤجَّل: محور «اللَّهَ» بلا عامل، ونوعه ROLE_DEFERRED يحيل إلى سجلّ O03',
      ax[g28]['inflection']['agreement'] == 'UNGOVERNED' and ax[g28]['inflection'].get('ungoverned_kind') == 'ROLE_DEFERRED'
      and o3['يَتَّقِ']['relation_id'] in ax[g28]['inflection'].get('pending_relations', []), ax[g28]['inflection'])
fr = {r['texts']['verb']: r for r in R if r['type'] == 'VERB_FRAME'}
check('K06 متطلَّب المفعول في إطار «يتق»: مرشّحٌ مؤجَّل بمعرّف سجلّه، لا «ليس منصوباً» ولا «لازم» ولا «محذوف»',
      fr['يَتَّقِ']['frame']['object_requirement']['kind'] == 'OBJECT_CANDIDATE_DEFERRED'
      and fr['يَتَّقِ']['frame']['object_requirement']['relation_id'] == o3['يَتَّقِ']['relation_id'], fr['يَتَّقِ']['frame']['object_requirement'])
# علامة لفظ الجلالة: الفتحة نصبٌ وحده (اللام مكتوبةٌ في خانته)، والكسرة جرّ
from sarf.algebra import word_case
A = C.get('analysis')['2:282'] if isinstance(C.get('analysis'), dict) and '2:282' in C.get('analysis') else None
if A is not None:
    check('K07 «اللَّهَ» (2:282:29) نصبٌ لا «نصب أو جر»', word_case(A, 28) == 'نصب', word_case(A, 28))
    check('K08 «اللَّهُ» (2:282:22) رفع، و«اللَّهِ» (2:282:90، عند الله) جرّ: القاعدة لا تمسّ غير الفتحة',
          word_case(A, 21) == 'رفع' and word_case(A, 89) == 'جر', (word_case(A, 21), word_case(A, 89)))
kinds = {}
for u, a_ in ax.items():
    inf = a_.get('inflection') or {}
    if inf.get('agreement') == 'UNGOVERNED':
        kinds[inf.get('ungoverned_kind')] = kinds.get(inf.get('ungoverned_kind'), 0) + 1
check('K09 كل «بلا عامل» يحمل نوعه: NO_MAHALL للحرف، وROLE_DEFERRED، وMAHALL_UNRESOLVED، وROLE_RULE_NOT_IMPLEMENTED',
      None not in kinds and kinds.get('NO_MAHALL', 0) > 0 and set(kinds) <= {'NO_MAHALL', 'ROLE_DEFERRED', 'MAHALL_UNRESOLVED',
                                                                         'ROLE_RULE_NOT_IMPLEMENTED', 'EVIDENCE_NOT_ADOPTED',
                                                                         'LEXICAL_ENTRY_MISSING'}, kinds)
check('K10 الوسم لا يغيّر الحكم: لا علاقة مرخَّصة جديدة من O03، ولا دور «مفعول به» على مؤجَّل',
      not any(r['status'] == LICENSED and r['rule_id'] == 'O03' for r in R)
      and not any(a_.get('role') and 'مفعول به' in str(a_.get('role')) for u, a_ in ax.items() if u == g28), ax[g28].get('role'))
# انتقالٌ خاطئ كشفه قياس B3 (7:70): إصلاح علامة لفظ الجلالة كشف بحث O02 من وراء فعلٍ آخر
C7 = run_ref('7:70')
R7 = C7.get('records')['7:70']['records']
fr7 = {r['texts']['verb']: r for r in R7 if r['type'] == 'VERB_FRAME'}
check('K11 «أَجِئۡتَنَا لِنَعۡبُدَ ٱللَّهَ»: «ٱللَّهَ» ليس مفعولاً لـ«جئت» (لا O02 ولا O03 ولا مرشّح متطلَّبه) — بينهما فعلٌ مكتوب',
      not any(r['type'] == 'OBJECT' and r['texts'].get('verb') == 'أَجِئْتَ' and r['texts'].get('object') == 'اللَّهَ' for r in R7)
      and 'اللَّهَ' not in str(fr7['أَجِئْتَ']['frame'].get('object_requirement')), [r['texts'] for r in R7 if r['type'] == 'OBJECT'])
check('K12 «نَعۡبُدَ ٱللَّهَ»: المرشّح عند الفعل الأقرب، وتعدّيه مؤجَّل في المورد فلا ترخيص', 
      fr7['نَعْبُدَ']['frame']['object_requirement']['kind'] == 'UNLINKED_CANDIDATE' and 'اللَّهَ' in fr7['نَعْبُدَ']['frame']['object_requirement']['note'])
# انتقالٌ ثانٍ كشفه قياس B3 (الشهادات): 8 جمل أُغلق إسنادها المحلي ومفعولها «تعارض طبقتين» (القديمة تضعه بربطها، و14أ تؤجّله)
C8 = run_ref('2:278')
cf = [c for c in C8.get('certificates').values() if any(o['status'] == 'CONFLICT' for o in c['obligations'])]
check('K13 «اتقوا الله» (2:278): التزامٌ في تعارض الطبقتين يمنع إغلاق الإسناد المحلي ولو كان اختيارياً (لا إغلاق بمرشّح)',
      cf and all(not str(c['verdict_by_level']['LOCAL_PREDICATION']).startswith('CLOSED') for c in cf),
      [(c['sentence'], c['verdict_by_level']) for c in cf])
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
