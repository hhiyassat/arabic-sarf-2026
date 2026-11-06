"""tests/test_paragraph.py — SARF_MAJOR_COMPLETION_TO_PARAGRAPH_03: الفقرة المرشّحة (§٢٠)، وT14-5 (إذا الفجائية)، وحدّ المصدر."""
import copy, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.algebra import (Trace, sentence_geo, linguistic_layer, closure_certificate, paragraph_candidate, check_paragraph,
                          paragraph_status, idha_fujaiyya, clause_start)
from sarf.features import unit_features
from sarf import relations as RL, quran_source
FAIL = []
CAT = Catalog([os.path.join(ROOT, 'operators_catalog.jsonl'), os.path.join(ROOT, 'operators_catalog_split_vocalized.csv')])
R = {(a, b): t for a, b, t in quran_source.rows()}


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {got}'))
    if not cond:
        FAIL.append(name)


def build(sura, verses):
    its, per = [], []
    for v in verses:
        a = analyze(CAT, R[(sura, v)], quran_source.uthmani_mode())
        S_, U = sentence_geo(a, f'Q{sura}:{v}', Trace())
        its.append((sura, v, a, U, S_))
        per.append((sura, v, a, U, unit_features(a, U)))
    C, Rl = [], []
    LT, _, _ = linguistic_layer(its, Trace(), 'p', cond_out=C, rel_out=Rl)
    recs = []
    for s, v, a, U, F in per:
        recs += RL.verse_relations(a, U, F, f'{s}:{v}', legacy_cond=C, legacy_rel=Rl)['records']
    Js = [J for SP in LT for D in SP.A + SP.O.get('pending', []) for J in D.A + D.O.get('pending', [])]
    certs = [closure_certificate(J, recs) for J in Js]
    return LT, certs, recs, paragraph_candidate(LT, certs, recs)


LT, certs, recs, pc = build(112, [1, 2, 3, 4])
check('P01 سورة الإخلاص: فقرةٌ مرشّحة بمكوّناتها (جملٌ بهوياتها وأحكامها بالمستويات) وروابطها بأدلّتها، وحدّاها من المصدر شاهدان، '
      'والحدّ اللغوي غير مثبت، والحكم «غير مكتملة» بأسبابٍ مسمّاة — لا فارغة ولا مكتملة بلا دليل',
      pc['components'] and all(c['verdict_by_level'] for c in pc['components']) and pc['links'] and
      all(k['evidence_id'] and k['evidence'] for k in pc['links'] if k['status'] != 'NOT_ESTABLISHED') and
      pc['boundary']['source_start'] == 'SOURCE:sura_start' and pc['boundary']['source_end'] == 'SOURCE:sura_end' and
      pc['boundary']['linguistic'] == 'NOT_PROVEN' and pc['status'] == 'PARAGRAPH_CANDIDATE_INCOMPLETE' and pc['reasons'], pc['status'])
check('P02 الفاحص المستقل للفقرة لا يجد خطأً في الفقرة المبنية', check_paragraph(pc, LT) == [], check_paragraph(pc, LT))
check('P03 الإحالة: ضمير «يَلِدۡ» و«يُولَدۡ» المستتر الغائب التزامُ مرجعٍ مؤجَّل (تعيين المرجع غير منفَّذ)، لا مرجعٌ مدّعى',
      pc['references'] and all(x['status'] == 'DEFERRED' and x['signature']['person'] == 3 for x in pc['references']) and
      any(o['kind'] == 'REFERENCE' and o['status'] == 'DEFERRED' for o in pc['obligations']), pc['references'])
check('P04 لا علاقة دلالية مدّعاة: السبب والغاية والنتيجة والدليل والتفسير «غير مقيَّمة» حتى تُنفَّذ قواعد الأدوات (لا «غائبة»)',
      all(v_.startswith('NOT_EVALUATED') for k in pc['links'] for v_ in k['semantic'].values()))
# إفساد: رابطٌ «مثبت» بلا دليلٍ وحيد الوجه
bad = copy.deepcopy(pc)
bad['links'][0]['status'] = 'PROVEN'
check('P05 إفساد: ادّعاء ترابطٍ «مثبت» لا تدعمه علاقاته (والحدّ يحتمل عطفاً وحالاً واستئنافاً) يكشفه الفاحص',
      any('مثبت' in e for e in check_paragraph(bad, LT)), check_paragraph(bad, LT))
bad2 = copy.deepcopy(pc)
bad2['links'][0]['evidence'] = 'دليلٌ مصطنع'
check('P06 إفساد: دليلٌ لا يطابق حدّ الجملة يُكشف', any('لا يطابق' in e for e in check_paragraph(bad2, LT)))
LT3, c3, r3, pc3 = build(112, [1, 2, 3])
bad3 = copy.deepcopy(pc3)
bad3['boundary']['source_end'] = 'SOURCE:sura_end'
check('P07 نهاية سورةٍ مصطنعة: 112:1–3 ليست آخر السورة، فلا حدّ مصدرٍ «آخر السورة»، وادّعاؤه يكشفه الفاحص',
      pc3['boundary']['source_end'] is None and any('آخر السورة' in e for e in check_paragraph(bad3, LT3)), pc3['boundary'])
st, why = paragraph_status([dict(kind='LINK', id='a', required=True, status='MET'), dict(kind='EXT', id='b', required=False, status='OPEN')])
st2, why2 = paragraph_status([dict(kind='LINK', id='a', required=True, status='MET'), dict(kind='REFERENCE', id='c', required=True, status='OPEN',
                                                                                             reason='مرجعٌ لازم مفقود')])
check('P08 العقد: الامتداد الاختياري الغائب لا يمنع الاكتمال، والاعتماد اللازم المفقود يمنعه ويُسمّى', st == 'COMPLETE' and st2 == 'INCOMPLETE'
      and 'REFERENCE' in why2[0])
LT2, c2, r2, pc2 = build(2, [282])
ks = {k['status'] for k in pc2['links']}
check('P09 آية الدين: فقرةٌ مرشّحة من جملها السبع عشرة بروابط مرشّحة (لا مثبتة) أو غير قائمة؛ ولا رابط «مثبت» بلا دليل',
      len(pc2['components']) == 17 and ks <= {'CANDIDATE', 'NOT_ESTABLISHED', 'PROVEN'} and check_paragraph(pc2, LT2) == [], (len(pc2['components']), ks))
ne = [k for k in pc2['links'] if k['status'] == 'NOT_ESTABLISHED']
check('P10 جملتان متتاليتان بلا دليل حدٍّ يربطهما: رابطٌ «غير قائم» يمنع الاكتمال (التزامٌ مفتوح)، ولا يُستنتج ترابطٌ من التتابع وحده',
      all(any(o['kind'] == 'LINK' and o['id'] == k['link_id'] and o['status'] == 'OPEN' for o in pc2['obligations']) for k in ne),
      [k['link_id'] for k in ne])

# ---------- T14-5: «إذا» الفجائية و«لو» و«إذا» الشرطيتان غير الجازمتين ----------
def ops(s, v):
    a = analyze(CAT, R[(s, v)], quran_source.uthmani_mode())
    return a, [f for f in a['operators'] if f['operator'] == 'إِذَا']
a1, f1 = ops(7, 107)
a2, f2 = ops(84, 1)
a3, f3 = ops(30, 36)
check('K01 «فَإِذَا هِيَ ثُعۡبَانٌ» (7:107): «إذا» الفجائية لا تفتح شرطاً (لا صدارة شرطٍ ولا جواب)', f1 and idha_fujaiyya(a1, f1[0])[0] and
      clause_start(a1, f1[0]['word_index']) is None)
check('K02 مقابلة: «إِذَا ٱلسَّمَآءُ ٱنشَقَّتۡ» (84:1) شرطية', f2 and not idha_fujaiyya(a2, f2[0])[0] and clause_start(a2, f2[0]['word_index']))
check('K03 في 30:36 «إذا» الأولى شرطية والثانية فجائية («إِذَا هُمۡ يَقۡنَطُونَ»)', len(f3) == 2 and not idha_fujaiyya(a3, f3[0])[0]
      and idha_fujaiyya(a3, f3[1])[0])
L = [json.loads(l) for l in open(os.path.join(ROOT, 'operators_catalog.jsonl'), encoding='utf-8') if l.strip()]
U = {(x['vocalized_form'], x['group_number']) for x in L}
check('K04 هوية الوحدات المعدودة محفوظة: الفهرس لم يُعدَّل (98 وحدة بمفتاح الصيغة والمجموعة، و140 معنى)، و«لو» و«إذا» في مجموعتهما',
      len(U) == 98 and len(L) == 140 and ('لَوْ', '7') in U and ('إِذَا', '7') in U)
from sarf.segment import NO_JAZM
check('K05 لا يُستنتج الجزم من رقم المجموعة: «لو» و«إذا» في المجموعة 7 بلا جزمٍ متوقَّع', set(NO_JAZM) == {'لَوْ', 'إِذَا'})

print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
