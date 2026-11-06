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


def build(sura, verses, texts=None):
    its, per = [], []
    for v in verses:
        a = analyze(CAT, (texts or {}).get(v) or R[(sura, v)], quran_source.uthmani_mode())
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
      any(e.startswith('PX09_NO_PROMOTION') for e in check_paragraph(bad, LT)), check_paragraph(bad, LT))
bad2 = copy.deepcopy(pc)
bad2['links'][0]['evidence'] = 'دليلٌ مصطنع'
check('P06 إفساد: دليلٌ لا يطابق حدّ الجملة يُكشف', any(e.startswith('PX05_LINK_EVIDENCE') for e in check_paragraph(bad2, LT)))
LT3, c3, r3, pc3 = build(112, [1, 2, 3])
bad3 = copy.deepcopy(pc3)
bad3['boundary']['source_end'] = 'SOURCE:sura_end'
check('P07 نهاية سورةٍ مصطنعة: 112:1–3 ليست آخر السورة، فلا حدّ مصدرٍ «آخر السورة»، وادّعاؤه يكشفه الفاحص',
      pc3['boundary']['source_end'] is None and any(e.startswith('PX10_BOUNDARY') for e in check_paragraph(bad3, LT3)), pc3['boundary'])
st, why = paragraph_status([dict(kind='LINK', id='a', required=True, status='MET'), dict(kind='EXT', id='b', required=False, status='OPEN')])
st2, why2 = paragraph_status([dict(kind='LINK', id='a', required=True, status='MET'), dict(kind='REFERENCE', id='c', required=True, status='OPEN',
                                                                                             reason='مرجعٌ لازم مفقود')])
check('P08 العقد: الامتداد الاختياري الغائب لا يمنع الاكتمال، والاعتماد اللازم المفقود يمنعه ويُسمّى', st == 'COMPLETE' and st2 == 'INCOMPLETE'
      and 'REFERENCE' in why2[0])
LT2, c2, r2, pc2 = build(2, [282])
ks = {k['status'] for k in pc2['links']}
check('P09 آية الدين: فقرةٌ مرشّحة من جملها الست عشرة (بعد تأجيل حدّ «وَأَقۡوَمُ») بروابط مرشّحة (لا مثبتة) أو غير قائمة؛ ولا رابط «مثبت» بلا دليل',
      len(pc2['components']) == 16 and ks <= {'CANDIDATE', 'NOT_ESTABLISHED', 'PROVEN'} and check_paragraph(pc2, LT2) == [], (len(pc2['components']), ks))
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


# ---------- §٨ T14-5: وحدة العدّ منفصلة عن المجموعة والوظيفة والأثر ----------
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import catalog_units as CU
_argv = sys.argv; sys.argv = ['x']
_rep = CU.main(); sys.argv = _argv
miss = {(x['form'], x['group']) for x in _rep['units_without_exact_meaning']}
check('K09 الجرد المئوي (CSV) 100 وحدة بمفتاح (الصيغة، المجموعة)، وملف المعاني 98: وحدتا «إِنَّ» و«أَنَّ» بلا سجلّ معنى، والبقية فروق صيغة',
      _rep['units'] == 100 and _rep['jsonl_units'] == 98 and {('إِنَّ', '2'), ('أَنَّ', '2')} <= miss)
check('K10 معرّف الوحدة منفصلٌ عن المجموعة والوظيفة والأثر، و«إذا» بلا جزمٍ في التنفيذ مع مقترح تصحيح الوصف (لا تعديل للجرد)',
      all(u['unit_id'] and 'teaching_group' in u and 'functions' in u and 'effects' in u for u in _rep['unit_table']) and
      'مقترح' in _rep['idha_effect']['proposal'])

# ---------- §١٥ «ذَٰلِكُمۡ أَقۡسَطُ … وَأَقۡوَمُ …»: لا قسمةٌ ثابتة مع وجه العطف على المفرد ----------
cq = next(c for c in pc2['components'] if any(tuple(g['location']) == (2, 282, 89) for g in c.get('internal_groupings') or []))
check('T15a الحدّ قبل «وَأَقۡوَمُ» مؤجَّلٌ صراحةً بتجميعين (SPLIT، JOIN) داخل المكوّن، والتزام التجميع مؤجَّل يمنع الاكتمال',
      any(o['kind'] == 'GROUPING' and o['status'] == 'DEFERRED' and o['id'].startswith(cq['sentence']) for o in pc2['obligations']) and
      cq['verdict_by_level']['SENTENCE'] == 'DEFERRED_BOUNDARY', cq)
Jb = {max(J.O['location'])[2]: J for SP in LT2 for D in SP.A + SP.O.get('pending', []) for J in D.A + D.O.get('pending', [])}
check('T15b مقابلة: قبل «وَٱللَّهُ بِكُلِّ شَيۡءٍ عَلِيمࣱ» مرفوعٌ بعده (عَلِيمࣱ) فالجملة الاسمية لازمة، والحدّ مثبت كما كان',
      121 in Jb and Jb[121].O['boundary'].get('J') == 'proven', sorted(Jb))

# ---------- §٧ «إذا»: الضمير قرينةٌ لا حكم ----------
from sarf.algebra import idha_reading, IDHA_SOURCE
a6 = analyze(CAT, 'إِذَا أَنتَ أَكۡرَمۡتَ ٱلۡكَرِيمَ مَلَكۡتَهُۥ', quran_source.uthmani_mode())
f6 = [f for f in a6['operators'] if f['operator'] == 'إِذَا']
r6 = idha_reading(a6, f6[0]) if f6 else None
check('K06 «إذا أنت أكرمت الكريم ملكته»: الضمير قرينةٌ لا حكم؛ يليه ماضٍ يوافقه فوجه الشرط قائم، والقرار ملتبس، ولا يُحذف الشرط',
      r6 and r6['decision'] == 'AMBIGUOUS' and r6['faces'][1]['status'] == 'CONDITIONS_MET' and not idha_fujaiyya(a6, f6[0])[0]
      and clause_start(a6, f6[0]['word_index']), r6)
r1 = idha_reading(a1, f1[0])
check('K07 الفجائية بدليلٍ مسمّى لا بالضمير وحده: في 7:107 الفاء قبل «إذا» وما بعد الضمير ليس ماضياً، ووجه الشرط مستبعدٌ بقاعدةٍ موثّقة (مغني اللبيب)',
      r1['decision'] == 'FUJAIYYA' and 'فاءٌ قبل «إذا»' in r1['evidence'] and r1['faces'][1]['status'] == 'EXCLUDED_BY_RULE'
      and 'مغني اللبيب' in IDHA_SOURCE, r1)
a8 = analyze(CAT, 'إِذَا هُمۡ يَقۡنَطُونَ', quran_source.uthmani_mode())
f8 = [f for f in a8['operators'] if f['operator'] == 'إِذَا']
r8 = idha_reading(a8, f8[0]) if f8 else None
check('K08 «إِذَا هُمۡ يَقۡنَطُونَ» وحدها (بلا فاءٍ ولا أداةٍ قبلها): الفجائية مرشّحة لا محسومة، فيبقى وجه الشرط',
      r8 and r8['decision'] == 'AMBIGUOUS' and r8['faces'][0]['status'] == 'CANDIDATE', r8)

# ---------- §٦ حدود المصدر حتى آخر كلمة ----------
from sarf.algebra import source_boundary_kinds, is_sura_end_word, verse_last_word
lw = verse_last_word(112, 4)
check('S01 آخر السورة آخر كلمةٍ في آخر آياتها: (112،4،آخر) SURA_END؛ وكلمةٌ قبلها في الآية الأخيرة ليست آخر السورة',
      is_sura_end_word((112, 4, lw)) and not is_sura_end_word((112, 4, lw - 1)) and not is_sura_end_word((112, 3, verse_last_word(112, 3))))
check('S02 الأنواع منفصلة: آخر 112:3 AYAH_END لا SURA_END، وآخر المدخل INPUT_END وحده إن لم يكن آخر آية',
      source_boundary_kinds((112, 3, verse_last_word(112, 3))) == ['AYAH_END'] and
      source_boundary_kinds((112, 4, 1), (112, 4, 1)) == ['INPUT_END'])
pre = ' '.join(R[(112, 4)].split()[:3])
LTp, cp_, rp_, pcp = build(112, [1, 2, 3, 4], texts={4: pre})
check('S03 مقدّمة الآية الأخيرة مع حذف بقية كلماتها: لا حدّ مصدرٍ «آخر السورة» في الجملة ولا في الفقرة',
      pcp['boundary']['source_end'] is None and not any((c['boundary'].get('rule_id') == 'SOURCE:sura_end') for c in cp_) and
      'INPUT_END' in pcp['boundary']['source_end_kinds'], pcp['boundary'])
check('S04 السورة كاملة: حدّ المصدر آخر السورة في الفقرة، وحدّ الجملة الأخيرة SURA_END؛ ولا يستوفي وحده التزاماً لغوياً (الحدّ اللغوي غير مثبت)',
      pc['boundary']['source_end'] == 'SOURCE:sura_end' and 'SURA_END' in pc['boundary']['source_end_kinds'] and
      pc['boundary']['linguistic'] == 'NOT_PROVEN', pc['boundary'])
check('S05 جزء الكلمة الأخيرة: التمثيل لا يقسم الكلمة موضعاً (الكلمة أصغر وحدة موضع)، وموضعٌ بعد آخر كلمة ليس آخر السورة',
      not is_sura_end_word((112, 4, lw + 1)))
Jfake = next(J for SP in LT3 for D in SP.A + SP.O.get('pending', []) for J in D.A + D.O.get('pending', []) if max(J.O['location'])[1] == 3)
Jfake.O.setdefault('boundary', {})['J_why'] = 'آخر السورة: ادّعاءٌ مصطنع'
Jfake.O['boundary']['location'] = max(Jfake.O['location'])
cf = closure_certificate(Jfake, r3)
check('S06 حقل سببٍ يزعم «آخر السورة» في 112:3: يُرفض ويُسجَّل، ولا يرقّي الحدّ', cf['boundary']['sura_end_claim_rejected'] and
      cf['boundary']['rule_id'] != 'SOURCE:sura_end', cf['boundary'])

# ---------- §٥ الفاحص مدقّقٌ للشهادة: الإفسادات الاثنا عشر على نسخ ----------
from sarf.algebra import _pc_fingerprint, paragraph_candidates, PARAGRAPH_CHECKS
base_err = check_paragraph(pc2, LT2, c2, r2)
check('M00 الفقرة المبنية لآية الدين تجتاز الفحوص كلها بإعادة التوليد (لا خطأ)', base_err == [], base_err)
MUT = []
def mut(name, fn, want, pc_=pc2, LT_=LT2, certs_=c2, recs_=r2, refresh=True):
    x = copy.deepcopy(pc_)
    before = json.dumps(x, ensure_ascii=False, sort_keys=True, default=str)
    fn(x)
    if refresh:
        x['fingerprint'] = _pc_fingerprint(x)
    changed = json.dumps(x, ensure_ascii=False, sort_keys=True, default=str) != before
    e = check_paragraph(x, LT_, certs_, recs_)
    hit = sorted({y.split(':')[0] for y in e})
    MUT.append(dict(mutation=name, changed=changed, detected_by=hit, expected=want, ok=changed and want in hit))
    check(f'{name} → {want}', changed and want in hit, (changed, e[:3]))
def _cause(x): x['links'][0]['candidates'] = ['CAUSE']; x['links'][0]['semantic']['CAUSE'] = 'PROVEN'
mut('M01 تغيير نوع الرابط إلى CAUSE بلا دليل', _cause, 'PX09_NO_PROMOTION')
mut('M02 evidence_id مصطنع', lambda x: x['links'][1].update(evidence_id='FAKE#boundary@(0, 0, 0)'), 'PX05_LINK_EVIDENCE')
mut('M03 الحكم «مكتملة» مع التزاماتٍ مفتوحة', lambda x: x.update(status='PARAGRAPH_CANDIDATE_COMPLETE'), 'PX08_VERDICT')
mut('M04 حذف مكوّن', lambda x: x['components'].pop(3), 'PX02_OCCURRENCES')
mut('M05 حذف التزام', lambda x: x['obligations'].pop(0), 'PX06_OBLIGATIONS_GENERATED')
mut('M06 حذف إحالةٍ لازمة من سجلٍّ حقيقي', lambda x: x['references'].pop(0), 'PX11_REFERENCES')
mut('M07 تزوير بداية السورة', lambda x: x['boundary'].update(source_start='SOURCE:sura_start'), 'PX10_BOUNDARY')
mut('M08 تزوير نهاية السورة', lambda x: x['boundary'].update(source_end='SOURCE:sura_end'), 'PX10_BOUNDARY')
mut('M09 تزوير الحدّ اللغوي', lambda x: x['boundary'].update(linguistic='PROVEN'), 'PX10_BOUNDARY')
def _swap(x): k = x['links'][2]; k['src'], k['dst'] = k['dst'], k['src']
mut('M10 تبديل طرفي الرابط', _swap, 'PX04_LINK_ENDS')
mut('M10b تبديل وجه الرابط', lambda x: x['links'][2].update(faces=['X→Y#RESUMPTION']), 'PX04_LINK_ENDS')
def _other(x):
    c = next(c for c in x['components'] if c['faces'])
    c['faces'] = sorted(c['faces'][:-1] + [c['faces'][-1].replace('#T=', '#C9|T=') if '#T=' in c['faces'][-1] else c['faces'][-1] + '#C9'])
mut('M11 إدخال علاقةٍ صحيحة لمرشّحٍ آخر (وجهٌ لمرشّحٍ صرفيٍّ غير مرشّح الشهادة)', _other, 'PX03_FACES')
def _data(x): x['obligations'][0]['status'] = 'MET'
mut('M12 تغيير بياناتٍ ثم تحديث بصمتها: البصمة سليمة والفحص الدلالي يكشف', _data, 'PX07_OBLIGATION_STATUS')
check('M12b والبصمة وحدها تكشف التغيير بلا تحديثها (تكامل)', any(e.startswith('PX12_FINGERPRINT') for e in
      check_paragraph(dict(pc2, status='X'), LT2, c2, r2)))
check('M13 الفحوص المسمّاة كلها معرَّفة، وكل إفسادٍ غيّر القيمة فعلاً', all(m['changed'] for m in MUT) and
      all(m['expected'] in PARAGRAPH_CHECKS for m in MUT))
# الحدّ اللغوي ليس ثابتاً «مؤجَّلاً»: شروط PB-L1 كلها مستوفاة → PROVEN بلا خطأ، وشرطٌ غير مفحوص → يُكشف ادّعاء PROVEN
okb = copy.deepcopy(pc)
okb['boundary']['conditions'] = {s_: {k_: 'MET: اصطناع اختباري' for k_ in 'abc'} for s_ in ('start', 'end')}
okb['boundary']['linguistic'] = 'PROVEN'
check('B01 PB-L1 ليست ثابتاً: شروطها كلها مستوفاة → الحدّ اللغوي PROVEN مقبولٌ عند الفاحص (PX10)',
      not any(e.startswith('PX10') for e in check_paragraph(okb, LT)))
pcs = paragraph_candidates(LT2, c2, r2, vocative_starts={J.id for J in [] })
check('B02 المرشّحات تُبنى بنقاط البدء المعلنة (A1): لآية الدين مرشّحٌ واحد لأن لا نقطة بدءٍ داخلها', len(pcs) == 1)
json.dump(MUT, open(os.environ.get('SARF_MUT_OUT', os.devnull), 'w'), ensure_ascii=False, indent=1)

print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
