"""tests/test_fa02_tools.py — أداة مقارنة الشهادات بالمدى (FA02 §٥): التغطية التامة للتقسيم، ورفض المفتاح المكرّر، ومقارنة دليل الاستيفاء."""
import gzip, json, os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'fa02'))
import certs as T
FAIL = []
NP = [0]


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:300]}'))
    NP[0] += bool(ok)
    if not ok:
        FAIL.append(name)


def c(id_, span, lv='OPEN', obs=()):
    return dict(key=f'2|{id_}', id=id_, span=span, verdict=lv, by_level={'LOCAL_PREDICATION': lv}, obligations=list(obs))


def write(rows):
    f = tempfile.NamedTemporaryFile(suffix='.jsonl.gz', delete=False)
    f.close()
    with gzip.open(f.name, 'wt', encoding='utf-8') as g:
        for r in rows:
            g.write(json.dumps(r, ensure_ascii=False) + '\n')
    return f.name


W = [f'2:1:{i}' for i in range(1, 7)]
A = T.load(write([c('J0', W)]))
r = T.compare(A, T.load(write([c('J0', W[:3]), c('J1', W[3:])])))
check('T01 تقسيمٌ تامّ (الجزءان يغطّيان المدى بلا تداخل) ← SPLIT', r['structural_counts']['SPLIT'] == 1 and r['structural_counts']['PARTIAL'] == 0, r['structural'])
r = T.compare(A, T.load(write([c('J0', W[:2]), c('J1', W[3:])])))
check('T02 تقسيمٌ ناقص (كلمةٌ من المدى بلا جملة) ← PARTIAL بما نقص، لا SPLIT', r['structural_counts']['SPLIT'] == 0
      and r['structural_counts']['PARTIAL'] == 1 and r['structural'][0]['missing'] == ['2:1:3'], r['structural'])
r = T.compare(A, T.load(write([c('J0', W[:4]), c('J1', W[3:])])))
check('T03 جزءان متداخلان ← PARTIAL بالمتداخل', r['structural_counts']['PARTIAL'] == 1 and r['structural'][0]['overlap'] == ['2:1:4'], r['structural'])
try:
    T.load(write([c('J0', W), c('J9', W)]))
    check('T04 مفتاحٌ مكرّر (مدى واحد لجملتين) ← رفضٌ صريح', False)
except T.DuplicateSpan:
    check('T04 مفتاحٌ مكرّر (مدى واحد لجملتين) ← رفضٌ صريح', True)
r = T.compare(T.load(write([c('J0', W[:3]), c('J1', W[3:])])), A)
check('T05 دمجٌ تامّ ← MERGE', r['structural_counts']['MERGE'] == 1, r['structural'])
o1 = dict(name='موضع كل وقوع (14أ)', owner='u1', status='MET', rel='R1', ev='PLACEMENT_14A:u1←R1', sat=['u1←R1'], unplaced=None)
o2 = dict(o1, rel='R2', ev='PLACEMENT_14A:u1←R2', sat=['u1←R2'])
r = T.compare(T.load(write([c('J0', W, obs=[o1])])), T.load(write([c('J0', W, obs=[o2])])))
check('T06 الحالة واحدة (MET) والدليل تغيّر (R1←R2) ← يُعدّ تغيّر دليلٍ لا تطابقاً', r['evidence_only_changes'] == 1 and not r['obligation_status_transitions'], r)
r = T.compare(T.load(write([c('J0', W, obs=[o1])])), T.load(write([c('J0', W, obs=[o1])])))
check('T07 الحالة والدليل متطابقان ← لا تغيّر', r['evidence_only_changes'] == 0 and r['common_changed'] == 0)
print(f'SUMMARY pass={NP[0]} fail={len(FAIL)} skip=0')
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
