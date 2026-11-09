"""tests/test_c063_hfn.py — SARF_COMPLETION_FROM_REPORT_063 §٥: مستهلك HFN للترحيل إلى v47 (خط الأساس v36 باقٍ).
الحدث المسحوب خارج كل فهرس بمرجعه وسببه وإصداره وبصمة ملفه؛ والمعاني كلها محفوظة؛ وهمزة الوصل بتمثيلٍ معلن والمكتوب محفوظ."""
import csv, os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import sarf.root as R
import sarf.cells as CL
FAIL = []


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:300]}'))
    if not ok:
        FAIL.append(name)


EV = ['event_id', 'root_K', 'hfn_root_id', 'layer', 'form', 'verb', 'transitivity', 'masdar', 'source', 'sibawayh_rules', 'n_lex', 'tier',
      'residual', 'rank', 'is_fact', 'licensing_status', 'event_review_v36']
d = tempfile.mkdtemp(prefix='hfn_c063_')
rel = os.path.join(d, 'release_v99')
os.makedirs(rel)
rows = [dict(event_id='E1', root_K='قول', form='فَعَلَ (أجوف)', verb='قَالَ', event_review_v36=''),
        dict(event_id='E2', root_K='قيل', form='فَعَلَ (أجوف)', verb='قَالَ', event_review_v36='WITHDRAWN_v43: A=N: اختبار'),
        dict(event_id='E3', root_K='صبر', form='افْتَعَلَ', verb='ٱصْطَبَرَ', event_review_v36=''),
        dict(event_id='E4', root_K='حقو', form='فَعِلَ', verb='حَقِيَ', event_review_v36='')]
with open(os.path.join(rel, 'events.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, EV)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in EV})
with open(os.path.join(rel, 'form_meanings.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, ['event_id', 'verb', 'form_class', 'concept_id', 'pending_concept', 'meaning', 'method', 'n_lex', 'evidence', 'status', 'rank'])
    w.writeheader()
    for eid, m in (('E1', 'القول'), ('E1', 'الظنّ'), ('E2', 'القيلولة'), ('E3', 'الصبر')):
        w.writerow(dict(event_id=eid, meaning=m))
with open(os.path.join(rel, 'lexical_units.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, ['lu_id', 'event_id', 'lemma', 'pos_ar', 'pattern', 'basis', 'status', 'lemma_pattern'])
    w.writeheader()
    w.writerow(dict(lu_id='E2#M', event_id='E2', lemma='قَيْلُولَة', pos_ar='مصدر', pattern='فَيْعُولَة'))
    w.writerow(dict(lu_id='E3#M', event_id='E3', lemma='ٱصْطِبَار', pos_ar='مصدر', pattern='افْتِعَال'))

H = R.HFN(rel)
live = [e['event_id'] for L in H.index.values() for e in L]
check('H01 الحدث المسحوب خارج فهرس الأحداث', 'E2' not in live and 'E1' in live, live)
check('H02 المسحوب محفوظٌ بمعرّفه وسببه وإصداره وبصمة ملفه',
      H.withdrawn and H.withdrawn[0]['event_id'] == 'E2' and H.withdrawn[0]['reason'].startswith('WITHDRAWN') and
      H.withdrawn[0]['release'] == 'release_v99' and len(H.withdrawn[0]['events_sha256']) == 64, H.withdrawn)
check('H03 معاني المسحوب لا تدخل، ومعاني الحيّ كلها محفوظة بترتيبها (لا يُسقط الثاني)',
      'E2' not in H.meanings_all and [m['meaning'] for m in H.meanings_all['E1']] == ['القول', 'الظنّ'] and H.meanings['E1'] == 'القول',
      dict(H.meanings_all))
e3 = next(e for L in H.index.values() for e in L if e['event_id'] == 'E3')
check('H04 همزة الوصل «ٱ» بالتمثيل المعلن «ا»، والمكتوب في المورد محفوظ', e3['verb'] == 'اصْطَبَرَ' and e3['verb_written'] == 'ٱصْطَبَرَ'
      and H.wasl_converted == 1, e3)
check('H05 التحويل للحرف الأول وحده، ولا يمسّ الحركات', R.hfn_wasl('ٱصْطَبَرَ') == ('اصْطَبَرَ', True) and
      R.hfn_wasl('قَالَ') == ('قَالَ', False) and R.hfn_wasl('بَٱ') == ('بَٱ', False))
old_H, old_L = R._HFN, CL._LEX
try:
    R._HFN, CL._LEX = H, None
    L = CL.lex_index()
    flat = [x for v in L.values() for x in v]
    check('H06 لمّات الحدث المسحوب لا تعود من فهرس الأسماء', not any(x[3] == 'E2#M' for x in flat), flat)
    k = CL._lex_key('اصْطِبَار')
    check('H07 لمّة «ٱصْطِبَار» تُفهرس بالتمثيل المعلن، والمكتوب في آخر الصفّ', k in L and L[k][0][4] == 'ٱصْطِبَار', list(L))
finally:
    R._HFN, CL._LEX = old_H, old_L
# الإفساد: لو قُرئ المسحوب حياً لظهر في الفهرس
orig = R.hfn_withdrawn
try:
    R.hfn_withdrawn = lambda e: False
    Hm = R.HFN(rel)
    check('H08 إفساد: تعطيل الاستبعاد يُدخل المسحوب في الفهرس (فالفحص H01 يكشف)', any(e['event_id'] == 'E2' for L_ in Hm.index.values() for e in L_))
finally:
    R.hfn_withdrawn = orig
# الإصدار المحمَّل: v36 التاريخي بلا مسحوب ولا تحويل؛ والمستهدف مثبَّتٌ ومتحقَّق (MANIFEST وملفاته والمسحوب المصرَّح به)
H0 = R.hfn()
if H0.release == 'release_v36':
    check('H09 التاريخي v36: لا مسحوب ولا تحويل همزة وصل، والإصدار والبصمة مسجّلان',
          not H0.withdrawn and H0.wasl_converted == 0 and len(H0.events_sha256 or '') == 64 and H0.pin['mode'] == 'HISTORICAL',
          (H0.release, len(H0.withdrawn), H0.wasl_converted))
else:
    check('H09 المستهدف: مثبَّتٌ بالتزام HFN وبصمة MANIFEST، وكل ملفٍّ مصرَّح به متحقَّق، والمسحوب = المصرَّح به بلا اختلاف',
          H0.release == R.HFN_TARGET['release'] and H0.pin['mode'] == 'TARGET' and H0.pin['hfn_commit'] == R.HFN_TARGET['hfn_commit']
          and H0.pin['files_verified'] >= 40 and {w['event_id'] for w in H0.withdrawn} == set(H0.pin['withdrawn_declared'])
          and H0.withdrawn_discrepancy is None, (H0.release, H0.pin.get('mode'), len(H0.withdrawn), H0.withdrawn_discrepancy))
v47 = os.environ.get('SARF_HFN_V47', '/home/user/ucr/repro03/pinned/hfn/release/release_v47')
if os.path.exists(os.path.join(v47, 'events.csv')):
    H47 = R.HFN(v47)
    ids = {w['event_id'] for w in H47.withdrawn}
    check('H10 v47 المثبَّت: كل مسحوبٍ خارج الفهرس، وهمزات الوصل محوّلة كلها',
          ids and not ids & {e['event_id'] for L_ in H47.index.values() for e in L_} and
          not any(e['verb'].startswith('ٱ') for L_ in H47.index.values() for e in L_), (len(ids), H47.wasl_converted))
else:
    print('SKIP H10 (v47 غير موجود محلياً)')
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
