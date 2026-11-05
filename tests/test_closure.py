#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_closure.py — SARF_MAJOR_CLOSURE_01: بوابة E02/E03، وهوية المرشّح الصرفي، وشهادة الإغلاق v2، وامتداد المصدر المؤوَّل.
موجبةٌ ومقابلةٌ وإفساديةٌ عابرةٌ للطبقات. والمدخل مصحف المجمّع، ولا تُمرَّر القيم المتوقعة.

    PYTHONHASHSEED=0 python3 -P -s tests/test_closure.py
"""
import copy, os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
os.environ.setdefault('SARF_QURAN', 'hafs_kfgqpc')
from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.algebra import Trace, sentence_geo, linguistic_layer, closure_certificate, CLOSURE_AR
from sarf.features import unit_features, host_case_vowel_proof, initial_hamza_kasra_proof, E_RULES
from sarf.relations import verse_relations, check_records, check_cross, check_inflection

CAT = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
FAIL = []


def verse_text(s, v):
    for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 3 and p[0] == str(s) and p[1] == str(v):
            return p[2]


def run(s, v):
    a = analyze(CAT, verse_text(s, v), 'auto')
    S, U = sentence_geo(a, f'Q{s}:{v}', Trace())
    C, Rl = [], []
    LT, _, _ = linguistic_layer([(s, v, a, U, S)], Trace(), 'test', cond_out=C, rel_out=Rl)
    o = verse_relations(a, U, unit_features(a, U), f'{s}:{v}', legacy_cond=C, legacy_rel=Rl)
    Js = [J for SP in LT for D in SP.A + SP.O.get('pending', []) for J in D.A + D.O.get('pending', [])]
    return o, [closure_certificate(J, o['records']) for J in Js]


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {got}'))
    if not cond:
        FAIL.append(name)


# ---------- ١ بوابة E02 وE03 ----------
check('G01 E02 v2: «رُدُّهُ» و«مُدُّهُ» (الأمر المضعّف) لا تُعدّ أسماءً، و«وَلِيُّهُ» اسمٌ بالقاعدة المصحَّحة',
      not host_case_vowel_proof('رُدُّ', 'هُ') and not host_case_vowel_proof('مُدُّ', 'هُ') and bool(host_case_vowel_proof('وَلِيُّ', 'هُ')))
check('G02 سجلّ E02 وE03: الإصدار، والمجال، والمقدّمات، والموانع، والأمثلة المقابلة، والمصدر، والاختبارات، والنتائج التابعة، وعيب v1',
      all(set(E_RULES[k]) >= {'version', 'scope', 'positive_premises', 'barriers', 'counterexamples', 'source', 'tests', 'dependent_outputs',
                              'v1_defect'} for k in ('E02', 'E03')))
check('G03 E03 v2 معطَّلة حتى يُعتمد P1: لا اسميةٍ بها لـ«إِحۡدَى» ولا لـ«إِخَالُ»', initial_hamza_kasra_proof('إِحْدَى') is None and
      initial_hamza_kasra_proof('إِخَالُ') is None)

o, C = run(2, 282)
u68 = next(u for u, l, t in o['tokens'] if l == '2:282:68' and t == 'إِحْدَى')
check('G04 النتائج التابعة لـE03 مؤجَّلة لا مثبتة: «إحدى» بلا صنف، ولا إضافة مرخَّصة «إحدى ← هما»',
      o['axes'][u68]['word_class'][0] is None and not any(r['type'] == 'IDAFA' and r['status'] == 'LICENSED' and r['heads'].get('mudaf') == u68
                                                          for r in o['records']))

# ---------- ٢ هوية المرشّح الصرفي ----------
fr = {r['texts']['verb']: r for r in o['records'] if r['type'] == 'VERB_FRAME'}
yb = fr['يَبْخَسْ']
check('G05 «يبخس»: المرشّح الكامل بهويته، وزمنه القائم وحده (مضارع)، والممنوعان بسببيهما (ماضٍ، أمر)، ومحوره يحمل الهوية نفسها',
      yb['frame']['candidate']['tense_live'] == ['مضارع'] and set(yb['frame']['candidate']['tense_rejected']) == {'ماضٍ', 'أمر'} and
      o['axes'][yb['heads']['verb']]['identity']['morph_candidate'] == yb['frame']['candidate']['id'])
m = copy.deepcopy(o)
f_ = next(r for r in m['records'] if r['relation_id'] == yb['relation_id'])
f_['frame']['tense'] = ('أمر',) + tuple(f_['frame']['tense'][1:])
check('M20 إفساد الزمن إلى مرشّحٍ ممنوع من الوحدة نفسها (يبخس: أمر) يكشفه الفاحص (القاعدة ١٠)',
      any('وجهٌ ممنوع' in e or 'غير زمن مرشّحه' in e for e in check_cross(m['records'], m['axes'])))
m = copy.deepcopy(o)
m['axes'][yb['heads']['verb']]['identity']['morph_candidate'] = yb['frame']['candidate']['id'].replace('T=مضارع', 'T=أمر')
check('M21 إفساد هوية المرشّح في المحور (مرشّحٌ آخر للوحدة نفسها) يكشفه الفاحص دون الاعتماد على الموضع',
      any('هوية المرشّح في المحور' in e for e in check_cross(m['records'], m['axes'])))
m = copy.deepcopy(o)
f_ = next(r for r in m['records'] if r['relation_id'] == yb['relation_id'])
f_['frame']['candidate']['tense'] = 'ماضٍ'
check('M22 إفساد زمن المرشّح خارج أزمنته القائمة يكشفه الفاحص',
      any('ليس من أزمنته القائمة' in e or 'غير زمن مرشّحه' in e for e in check_cross(m['records'], m['axes'])))

# ---------- ٣ شهادة الإغلاق v2 ----------
ids = {r['relation_id']: r for r in o['records']}
TYPE_OF = {'SUBJECT': {'SUBJECT', 'VERB_FRAME'}, 'AGENT_PASSIVE': {'SUBJECT', 'VERB_FRAME'}, 'SUBJECT_OR_PASSIVE_AGENT': {'SUBJECT', 'VERB_FRAME'},
           'NASIKH_ISM': {'NASIKH'}, 'OBJECT': {'OBJECT'}, 'KHABAR': {'NASIKH'}, 'GOVERNED': {'PP', 'MASDAR', 'NASIKH'},
           'NUCLEUS': {'PREDICATION', 'PREDICATIVE_PP', 'VERB_FRAME', 'NASIKH'}}
obs = [ob for c in C for ob in c['obligations']]
bad = [ob['obligation_id'] for ob in obs if ob.get('discharge_relation_id') and ob['requirement_kind'] in TYPE_OF and
       ids[ob['discharge_relation_id']]['type'] not in TYPE_OF[ob['requirement_kind']]]
check('G06 لا يُستوفى التزامٌ بعلاقةٍ من غير نوعه، وكل مستوفى بعلاقةٍ يسمّي معرّفها ودليلها', not bad and all(
    ob['discharge_evidence_id'] for ob in obs if ob.get('discharge_relation_id')), bad)
check('G07 لكل التزامٍ سجلّه: المعرّف، والمالك، والوجه، والنوع، ودليل اللزوم، واللزوم، والحالة، والعلاقة المستوفية ودليلها، والباقي',
      all(set(ob) >= {'obligation_id', 'owner', 'face_id', 'requirement_kind', 'requirement_evidence', 'required', 'status',
                      'discharge_relation_id', 'discharge_evidence_id', 'residual_reason'} for ob in obs))
w = next(ob for ob in obs if ob['name'] in ('فاعل «يُمْلِلِ»', 'فاعل «وَلْيُمْلِلِ»'))
check('G08 «وليملل الذي»: جدول الإسناد القديم لا يُلغي تأجيل 14أ — الالتزام غير مستوفى (تعارض)، والحكم ليس «مغلقة»',
      w['status'] == 'CONFLICT' and not w['met'] and 'جدول الإسناد' not in str(w.get('discharge_evidence_id')))
check('G09 «فاعل أو نائب فاعل» لا يُختزل في «فاعل»: لا يكون مستوفى إلا «في كل الأوجه»',
      all(ob['status'] != 'MET' for ob in obs if ob['requirement_kind'] == 'SUBJECT_OR_PASSIVE_AGENT'))
check('G10 صيغة «كان» غير المحسومة (يكونا، تكون): طرف إسنادها ليس «فاعلاً مستوفى»، بل اختيارٌ بين الناقص والتامّ',
      all(ob['status'] == 'SELECTION' for ob in obs if ob['requirement_kind'] == 'NASIKH_ISM_OR_SUBJECT'))
check('G11 الأحكام من القائمة المحدّدة، والمؤجَّل في المدى مصنَّف (اختيار، حدّ، تغطية، لازم) لا التزامٌ لازمٌ تلقائياً',
      all(c['verdict'] in CLOSURE_AR for c in C) and all(x['kind'] in ('SELECTION', 'BOUNDARY', 'COVERAGE', 'REQUIRED') for c in C for x in c['residuals']))
m = copy.deepcopy(o['records'])
c13 = next(c for c in C if c['verdict'] == 'CLOSED_WITH_SHARED_STRUCTURE')
rid = next(ob['discharge_relation_id'] for ob in c13['obligations'] if ob.get('discharge_relation_id'))
next(r for r in m if r['relation_id'] == rid)['status'] = 'DEFERRED'
Jx = None
a = analyze(CAT, verse_text(2, 282), 'auto')
S_, U_ = sentence_geo(a, 'Q2:282', Trace())
LT, _, _ = linguistic_layer([(2, 282, a, U_, S_)], Trace(), 'test', cond_out=[], rel_out=[])
Jx = next(J for SP in LT for D in SP.A + SP.O.get('pending', []) for J in D.A + D.O.get('pending', []) if J.id == c13['sentence'])
c1 = closure_certificate(Jx, m)
check('M23 إفساد: تنزيل العلاقة المستوفية في جملةٍ مغلقة يُسقط الإغلاق', c1['verdict'] not in ('CLOSED_IN_FACE', 'CLOSED_WITH_SHARED_STRUCTURE'),
      c1['verdict'])

# أمثلة موجبة ومقابلة خارج آية الدين (كل آيةٍ وحدها)
_, C3 = run(112, 3)
check('G12 موجبة خارج آية الدين: «لَمۡ يَلِدۡ» (112:3) مغلقة في وجهها — الفاعل مستترٌ مرخَّص (S01.h) والحدّ مثبت',
      C3[0]['verdict'] == 'CLOSED_IN_FACE', [c['verdict'] for c in C3])
_, C1 = run(108, 1)
check('G13 مقابلة: «إِنَّآ أَعۡطَيۡنَٰكَ ٱلۡكَوۡثَرَ» (108:1) لا تُغلق: النواة نقص تغطيةٍ مسمّى (الفعل لم يُعرف)، وحدّ الآية غير مفحوص',
      C1[0]['verdict'] not in ('CLOSED_IN_FACE', 'CLOSED_WITH_SHARED_STRUCTURE') and
      any(ob['requirement_kind'] == 'NUCLEUS' and ob['status'] == 'COVERAGE' for ob in C1[0]['obligations']), [c['verdict'] for c in C1])
check('G14 متعدّدة الأوجه: في 2:282 جملٌ «اختيارٌ مؤجَّل» و«مغلقة بالبنية المشتركة»، والمحرّك لا يؤجّل الجميع ولا يغلق الجميع',
      {'DEFERRED_ANALYSIS_SELECTION', 'CLOSED_WITH_SHARED_STRUCTURE'} <= {c['verdict'] for c in C} and
      len({c['verdict'] for c in C}) >= 3)

# ---------- ٤ المصدر المؤوَّل بنيةً ----------
ms = {(r['texts']['harf'], r['texts']['verb']): r for r in o['records'] if r['type'] == 'MASDAR'}
check('G15 «أَلَّا» (MERGED) مع «حذف النون» (نصبٌ أو جزم): «أَلَّا تَرۡتَابُوا» و«أَلَّا تَكۡتُبُوهَا» مؤجَّلان بوجهي المصدرية والتفسير',
      ms[('أَلَّا', 'تَرْتَابُوا')]['status'] == 'DEFERRED' and ms[('أَلَّا', 'تَكْتُبُو')]['status'] == 'DEFERRED' and
      any('المفسّرة' in x for x in ms[('أَلَّا', 'تَرْتَابُوا')]['alternatives']))
o64, _ = run(3, 64)
m64 = [r for r in o64['records'] if r['type'] == 'MASDAR' and r['texts']['harf'] == 'أَلَّا']
check('G15b موجبة: «أَلَّا نَعۡبُدَ» (3:64) — الفتحة نصبٌ خالص، فـ«أَنْ» مصدرية والمصدر المؤوَّل مرخَّص', m64 and m64[0]['status'] == 'LICENSED')
e1 = ms[('أَنْ', 'تَكْتُبُو')]['extent']
check('G16 امتداد «أَنۡ تَكۡتُبُوهُ»: المثبت الحرف والفعل والضمير المتصل بهوياتها، وما بعدها مرشّحٌ حدّه غير مثبت',
      e1['proven_text'] == 'أَنْ تَكْتُبُو هُ' and e1['boundary_status'] == 'DEFERRED' and len(e1['proven']) == 3)
e2 = ms[('أَلَّا', 'تَكْتُبُو')]['extent']
check('G17 «أَلَّا تَكۡتُبُوهَا»: لا شيء بعد الأعضاء المرخَّصة في الإطار، فالحدّ مثبت', e2['boundary_status'] == 'LICENSED' and
      e2['proven_text'] == 'أَلَّا تَكْتُبُو هَا')
e3 = ms[('أَنْ', 'يُمِلَّ')]['extent']
check('G18 «أَن يُمِلَّ هُوَ»: «هو» مرشّح فاعلٍ مؤجَّل، فهو في الامتداد المرشّح لا المثبت', 'هُوَ' in e3['candidate_text'] and
      'هُوَ' not in e3['proven_text'])
check('G19 وظيفة المصدر لا تُحصر: مؤجَّلةٌ بأبوابٍ للفحص لا أوجهٍ ثبت جوازها', all(
    r['function']['status'] == 'DEFERRED' and 'لا أوجهٌ ثبت جوازها' in r['function']['text'] for r in ms.values()))
check('G20 الفواحص الثلاثة بلا خلل على 2:282', not check_records(o['records'], o['tokens'], o.get('parts')) and
      not check_cross(o['records'], o['axes']) and not check_inflection(o['axes']))

# ---------- ٥ حدّ بحث الفاعل: لا «لا منافس» بلا دليل صنف المنافس المحتمل ----------
o7, _ = run(7, 89)
s7 = next(r for r in o7['records'] if r['type'] == 'SUBJECT' and r['texts'].get('verb') == 'يَشَاءَ')
o11, _ = run(11, 123)
s11 = next(r for r in o11['records'] if r['type'] == 'SUBJECT' and r['texts'].get('verb') == 'يُرْجَعُ')
check('G21 «يَشَآءَ ٱللَّهُ رَبُّنَا» و«يُرۡجَعُ ٱلۡأَمۡرُ كُلُّهُۥ»: بعد المرشّح مرفوعٌ كتابةً صنفه غير محسوم، فلا يُرخَّص الفاعل بدعوى «لا منافس» '
      '(النتيجة لا تُبنى على غياب دليل الصنف)', s7['status'] == 'DEFERRED' and 'صنفه غير محسوم' in s7['reason'] and
      s11['status'] == 'DEFERRED' and 'كُلُّ' in s11['reason'], (s7['reason'][:80], s11['reason'][:80]))
o3, _ = run(112, 3)
f3 = [r['frame']['subject'] for r in o3['records'] if r['type'] == 'VERB_FRAME']
check('G22 S01.h: «لَمۡ يَلِدۡ وَلَمۡ يُولَدۡ» — لا اسم ظاهر، والبحث بلغ حدّ الإطار: الفاعل مستترٌ مرخَّص، ومرجعه غير معيَّن',
      len(f3) == 2 and all(x['status'] == 'LICENSED' and 'مستتر' in x['kind'] for x in f3), f3)
check('G23 مقابلة S01.h: «فعلٌ محتمل» (صنفٌ غير محسوم) لا يُعدّ حدّاً مثبتاً للبحث، فلا يُرخَّص مستترٌ عنده',
      'S01.h' not in s11['reason'])

o48, _ = run(2, 48)
s48 = [r for r in o48['records'] if r['type'] == 'SUBJECT' and r['texts'].get('verb') == 'يُقْبَلُ']
check('G24 «لَا يُقۡبَلُ مِنۡهَا شَفَٰعَةٌ» (2:48): شبه الجملة بين المجهول والمرفوع قد تكون نائب الفاعل — يبقى مؤجَّلاً (حراسة سلسلة القواعد)',
      s48 and all(r['status'] == 'DEFERRED' and 'شبه جملة' in r['reason'] for r in s48), [(r['status'], r['reason'][:60]) for r in s48])

print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
