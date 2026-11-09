"""tests/test_fa01.py — SARF_FINAL_COMPLETION_AND_ACCEPTANCE_01: اختبارات الإصلاحات المستقلة في هذه الجولة (§٣، §٧، §٨)."""
import copy, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from sarf.stages import run_ref, _sentences
from sarf.algebra import closure_certificate
FAIL = []


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:400]}'))
    if not ok:
        FAIL.append(name)


# §٨ الموضع من 14أ لا من روابط الطبقة القديمة
C = run_ref('2:278')
recs = [r for v in C.get('records').values() for r in v['records']]
Js = _sentences(C.get('sentences')['LT'])
J0 = next(J for J in Js if any('اتَّقُوا' in str(o.name) for o in J.Omega))
c0 = closure_certificate(J0, recs)
pl = [o for o in c0['obligations'] if o['name'] == 'موضع كل كلمة (14أ)']
check('P01 «اتقوا الله» (2:278): «اللَّهَ» يضعه الرابط القديم وحده و14أ لا ترخّصه ← التزام الموضع من 14أ «تعارض طبقتين»، والإسناد المحلي غير مغلق',
      pl and pl[0]['status'] == 'CONFLICT' and 'اللَّهَ' in pl[0]['residual_reason']
      and not str(c0['verdict_by_level']['LOCAL_PREDICATION']).startswith('CLOSED'), (pl, c0['verdict_by_level']))
J1 = copy.copy(J0)
J1.O = dict(J0.O, placed_by_legacy_bond_only=[])
c1 = closure_certificate(J1, recs)
check('P02 إفساد: بمحو سجلّ «الوضع بالرابط القديم وحده» يختفي التزام الموضع من 14أ (فالفحص P01 هو ما يكشفه)',
      not any(o['name'] == 'موضع كل كلمة (14أ)' for o in c1['obligations']))
check('P03 الالتزام يسمّي مقياسه: تغطية أدوارٍ محلية في 14أ مستقلةً عن الطبقة القديمة', pl and 'مستقلةً عن روابط الطبقة القديمة' in pl[0]['measure'])
lic_place = [x for J in Js for x in (J.O.get('placed_by_legacy_bond_only') or [])]
check('P04 كل وقوعٍ وُضع بالرابط القديم وحده مسجَّلٌ بموضعه ووحداته ونوع رابطه', lic_place and all(x['units'] and x['bonds'] and x['location'] for x in lic_place),
      lic_place[:2])
# §٧ حدّ الإطار عند همزة الاستفهام قبل حرف جرّ (14:10 «قَالَتۡ رُسُلُهُمۡ أَفِي ٱللَّهِ شَكٌّ»)
from sarf.algebra import clause_start
from sarf.analyze import analyze
from sarf.catalog import Catalog
C14 = run_ref('14:10')
a14 = C14.get('analysis')['14:10']
R14 = C14.get('records')['14:10']['records']
check('P05 «أَفِي» تبدأ كلاماً له الصدارة (استفهام)', (clause_start(a14, 2) or (None,))[0] == 'استفهام', clause_start(a14, 2))
s14 = [r for r in R14 if r['type'] == 'SUBJECT' and r['texts'].get('verb') == 'قَالَتْ']
check('P06 فاعل «قَالَتْ» «رُسُلُ» مرخَّص، و«شَكٌّ» (في جملة الاستفهام) لا ينافسه', s14 and s14[0]['status'] == 'LICENSED'
      and 'شَكٌّ' not in str(s14[0]['texts']), [(r['status'], r['texts']) for r in s14])
CAT = Catalog([os.path.join(ROOT, 'operators_catalog.jsonl'), os.path.join(ROOT, 'operators_catalog_split_vocalized.csv')])
for w in ('أَمِنَ', 'أَبِ'):
    check(f'P07 مقابل: «{w}» لا يُعدّ استفهاماً بهذه القاعدة (فعلٌ بحركته، أو حرفٌ واحد خارج الجرد المعتمد)',
          clause_start(analyze(CAT, w), 0) is None, clause_start(analyze(CAT, w), 0))
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
