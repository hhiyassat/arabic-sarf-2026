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
a112 = analyze(CAT, verse_text(112, 3), 'auto')
S112, U112 = sentence_geo(a112, 'Q112:3', Trace())
C112_, R112_ = [], []
LT112, _, _ = linguistic_layer([(112, 3, a112, U112, S112)], Trace(), 'test', cond_out=C112_, rel_out=R112_)
o112 = verse_relations(a112, U112, unit_features(a112, U112), '112:3', legacy_cond=C112_, legacy_rel=R112_)
J112 = [J for SP in LT112 for D in SP.A + SP.O.get('pending', []) for J in D.A + D.O.get('pending', [])][0]
c0 = closure_certificate(J112, o112['records'])
rid = next(ob['discharge_relation_id'] for ob in c0['obligations'] if ob.get('discharge_relation_id'))
m = copy.deepcopy(o112['records'])
r_ = next(r for r in m if r['relation_id'] == rid)
r_['status'] = 'DEFERRED'
if (r_.get('frame') or {}).get('subject'):
    r_['frame']['subject']['status'] = 'DEFERRED'          # البنية المستوفية نفسها (فاعل الإطار)، لا رأس السجل وحده
c1 = closure_certificate(J112, m)
check('M23 إفساد: تنزيل العلاقة المستوفية في جملةٍ مغلقة («لَمۡ يَلِدۡ») يُسقط الإغلاق',
      c0['verdict_by_level']['LOCAL_PREDICATION'] == 'CLOSED_IN_FACE' and
      c1['verdict_by_level']['LOCAL_PREDICATION'] not in ('CLOSED_IN_FACE', 'CLOSED_WITH_SHARED_STRUCTURE'),
      (c0['verdict_by_level'], c1['verdict_by_level']))

# أمثلة موجبة ومقابلة خارج آية الدين (كل آيةٍ وحدها)
_, C3 = run(112, 3)
check('G12 موجبة خارج آية الدين: «لَمۡ يَلِدۡ» (112:3) مغلقةٌ في وجهها في مستوى الإسناد المحلي — الفاعل مستترٌ مرخَّص (S01.h) وحدّ الإسناد '
      'المحلي ثابت؛ ولا تُغلق في مستوى الجملة: بعدها عطفٌ محتمل فالاستقلال غير مشهود به (مراجعة 040 ن٤)',
      C3[0]['verdict_by_level']['LOCAL_PREDICATION'] == 'CLOSED_IN_FACE' and C3[0]['verdict_level'] == 'SENTENCE' and
      C3[0]['verdict'] == C3[0]['verdict_by_level']['SENTENCE'] == 'DEFERRED_BOUNDARY' and
      C3[0]['boundary']['independence_status'] == 'NOT_WITNESSED', [c['verdict_by_level'] for c in C3])
_, C1 = run(108, 1)
check('G13 مقابلة: «إِنَّآ أَعۡطَيۡنَٰكَ ٱلۡكَوۡثَرَ» (108:1) لا تُغلق: النواة نقص تغطيةٍ مسمّى (الفعل لم يُعرف)، وحدّ الآية غير مفحوص',
      C1[0]['verdict'] not in ('CLOSED_IN_FACE', 'CLOSED_WITH_SHARED_STRUCTURE') and
      any(ob['requirement_kind'] == 'NUCLEUS' and ob['status'] == 'COVERAGE' for ob in C1[0]['obligations']), [c['verdict'] for c in C1])
check('G14 متعدّدة الأوجه: في 2:282 أحكامٌ مختلفة (اختيارٌ مؤجَّل، ونقص تغطية، وحدٌّ مؤجَّل)، والمحرّك لا يحكم بحكمٍ واحد للجميع',
      {'DEFERRED_ANALYSIS_SELECTION', 'INCOMPLETE_RULE_COVERAGE', 'DEFERRED_BOUNDARY'} <= {c['verdict_by_level']['LOCAL_PREDICATION'] for c in C})

# ---------- ٤ المصدر المؤوَّل بنيةً ----------
ms = {(r['texts']['harf'], r['texts']['verb']): r for r in o['records'] if r['type'] == 'MASDAR'}
check('G15 «أَلَّا» (MERGED) مع «حذف النون»: وجه المصدرية مرخَّصٌ في وجهه (استوفى شروطه)، واختياره مؤجَّل لأن وجه المفسّرة فرضيةٌ غير مفحوصة '
      '(مراجعة 038 ن١: الترخيص غير الاختيار)', all(ms[k_]['status'] == 'LICENSED' and ms[k_]['selection'] == 'DEFERRED'
                                                  for k_ in (('أَلَّا', 'تَرْتَابُوا'), ('أَلَّا', 'تَكْتُبُو'))) and
      any('المفسّرة' in x for x in ms[('أَلَّا', 'تَرْتَابُوا')]['alternatives']))
o64, _ = run(3, 64)
m64 = [r for r in o64['records'] if r['type'] == 'MASDAR' and r['texts']['harf'] == 'أَلَّا']
check('G15b موجبة: «أَلَّا نَعۡبُدَ» (3:64) — الفتحة نصبٌ خالص، فـ«أَنْ» مصدرية والمصدر المؤوَّل مرخَّص', m64 and m64[0]['status'] == 'LICENSED')
e1 = ms[('أَنْ', 'تَكْتُبُو')]['extent']
check('G16 امتداد «أَنۡ تَكۡتُبُوهُ»: المثبت الحرف والفعل والضمير المتصل بهوياتها، وما بعدها مرشّحٌ حدّه غير مثبت',
      e1['proven_text'] == 'أَنْ تَكْتُبُو هُ' and e1['boundary_status'] == 'DEFERRED' and len(e1['proven']) == 3)
e2 = ms[('أَلَّا', 'تَكْتُبُو')]['extent']
check('G17 «أَلَّا تَكۡتُبُوهَا»: لا شيء بعد الأعضاء المرخَّصة، لكن نفاد البحث داخل الإطار لا يثبت حدّ المصدر: حدّ الإطار عاطف '
      'قد يُعطف به فعلٌ داخل المصدر، فالحدّ مؤجَّل بدليله المسمّى (مراجعة 036)', e2['boundary_status'] == 'DEFERRED' and
      e2['proven_text'] == 'أَلَّا تَكْتُبُو هَا' and 'عاطف' in e2['frame_end'])
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

# ---------- مراجعة 036 ----------
cv = {c['sentence']: c for c in C}
# بالموضع لا بالرقم: دمج حدّ «وَأَقۡوَمُ» المؤجَّل (§١٥) يعيد ترقيم الجمل بعده
cw = lambda w: next(c for c in C if f'2:282:{w}' in c['span'])
c13 = cw(116)
check('R01 «وَإِنْ تَفْعَلُوا فَإِنَّهُ فُسُوقٌ بِكُمْ»: تعلّق «بكم» بحثه غير مكتمل (A01)، فلا «مغلقة بالبنية المشتركة» بل نقص تغطية',
      c13['verdict_by_level']['LOCAL_PREDICATION'] == 'INCOMPLETE_RULE_COVERAGE' and any(x['rule'] == 'A01' and x['kind'] == 'COVERAGE' for x in c13['residuals']), c13['verdict'])
check('R01b لا إغلاق (في وجهٍ ولا بالبنية المشتركة) مع باقٍ بحثه غير مكتمل في أي جملةٍ من 2:282',
      all(not (v_ in ('CLOSED_IN_FACE', 'CLOSED_WITH_SHARED_STRUCTURE') and any(x['kind'] == 'COVERAGE' for x in c['residuals']))
          for c in C for v_ in c['verdict_by_level'].values()))
pl6 = next(o_ for o_ in cv['L2.d6.J']['obligations'] if o_['requirement_kind'] == 'PLACEMENT')
check('R02 «فَلْيُمْلِلْ وَلِيُّهُ»: «وليّ» و«هُ» طرفان في S01 وI01 المرخَّصتين، فلا يُعدّان بلا موضع؛ والباقي «هُوَ» وحده (في S01 المؤجَّل)',
      'Q2:282.w49.u0' not in pl6['residual_reason'] and 'Q2:282.w49.u1' not in pl6['residual_reason'] and 'Q2:282.w47.u0' in pl6['residual_reason'],
      pl6['residual_reason'])
ob5 = next(o_ for o_ in cv['L2.d5.J']['obligations'] if o_['name'].startswith('مفعول «يَبْخَسْ'))
check('R03 مفعول «يبخس»: 14أ لا تسجّل مفعولاً («شيئاً» مرشّحٌ غير مربوط)، فلا يُعلن مستوفى بنصّ «مفعول به» القديم: تعارض طبقتين',
      ob5['status'] == 'CONFLICT' and not ob5['met'] and 'UNLINKED_CANDIDATE' in ob5['residual_reason'], ob5)
check('R03b كل مستوفى بالطبقة القديمة يحمل معرّف دليلٍ قابلاً للتتبّع (المصدر والالتزام والوحدات والرتبة)',
      all(o_['discharge_evidence_id'] and (o_['discharge_relation_id'] or str(o_['discharge_evidence_id']).startswith('LEGACY:') and
          all(x.get('rank') and 'units' in x for x in o_['satisfied_by'] if x['status'] == 'LEGACY'))
          for c in C for o_ in c['obligations'] if o_['met']))
b16 = cw(128)['boundary']
check('R04 نهاية 2:282 ليست «آخر السورة»: حدّ المصدر «نهاية المدخل المحلَّل»، والحدّ اللغوي غير مثبت (الاستقلال لفظاً غير مفحوص)',
      not b16['proven'] and 'نهاية المدخل' in str(b16['source']) and 'آخر السورة' != b16['source'], b16)
a_ = ms[('أَلَّا', 'تَرْتَابُوا')]
check('R05 «أَلَّا» مع حذف النون: المقدّمة «حذف النون متحقّق ولا يحسم النصب أو الجزم» (لا «النصب مكتوب»)، ووجه المصدرية استوفى شروطه، '
      'ووجه المفسّرة فرضيةٌ غير مفحوصة لا وجهٌ مكافئ', 'لا يحسم' in a_['premises'][1] and 'النصب مكتوب' not in a_['premises'][1] and
      [f_['status'] for f_ in a_['faces']] == ['CONDITIONS_MET', 'HYPOTHESIS_UNCHECKED'])

# ---------- مراجعة 038 ----------
from sarf.algebra import certificate_unmet
check('R06 ن١ «أَلَّا تَرۡتَابُوا»: مرخَّصٌ في وجهه، والاختيار مؤجَّل، والشرط الناقص مسمّى (فحص المفسّرة)؛ والشهادة تعدّه نقص تغطية لا إغلاقاً',
      a_['status'] == 'LICENSED' and a_['selection'] == 'DEFERRED' and a_['search_status'] == 'SEARCH_INCOMPLETE' and
      any('المفسّرة' in x for x in a_['search_scope']['outside_coverage']) and
      any(x['rule'] == 'M02' and x['kind'] == 'COVERAGE' for x in cw(95)['residuals']) and
      cw(95)['verdict'] not in ('CLOSED_IN_FACE', 'CLOSED_WITH_SHARED_STRUCTURE'))
pb = [c['boundary'] for c in C if c['boundary']['levels']['LOCAL_PREDICATION'] == 'PROVEN']
check('R07 ن٢ كل حدٍّ محلي مثبت يحمل القاعدة ومعرّف الدليل والمستوى وثباته المفحوص؛ والاستقلال لا يُدّعى مع عطفٍ محتمل',
      pb and all(b_.get('rule_id') and b_.get('evidence_id') and b_.get('level') and b_.get('stable_across_alternatives') and b_.get('independence')
                 and b_['stability']['status'] == 'PROVEN' and b_['stability']['checked_relations'] > 0 for b_ in pb) and
      all(b_['independence_status'] != 'PROVEN' for b_ in pb if 'عطف' in (b_.get('linguistic_evidence') or '')),
      [b_ for b_ in pb if not b_.get('rule_id')][:1])
pl8 = next(o_ for o_ in cv['L2.d8.J']['obligations'] if o_['requirement_kind'] == 'PLACEMENT')
import re as _re
ids8 = _re.findall(r'Q2:282\.w\d+\.u\d+', pl8['residual_reason'].split('؛')[0])
check('R08 ن٣ لا بتر في السجل: باقي الموضع في L2.d8 يعدّد 8 من 8 بهوياتها كاملة، ولا هويةٌ مقطوعة',
      pl8['residual_reason'].startswith('8 ') and len(ids8) == 8 and '…' not in pl8['residual_reason'], ids8)
un5 = certificate_unmet(cv['L2.d5.J'])
check('R09 ن٤ ملخّص غير المستوفى مولَّدٌ من الحالة الآلية: يشمل تعارض مفعول «يبخس» الجائز، ويطابق عدّ الحالات غير المستوفاة',
      any(u['status'] == 'CONFLICT' and not u['required'] and 'يَبْخَسْ' in u['name'] for u in un5) and
      all(len(certificate_unmet(c)) == sum(o_['status'] in ('OPEN', 'CONFLICT', 'SELECTION', 'COVERAGE', 'BOUNDARY') for o_ in c['obligations']) for c in C))
check('R10 ن٧ مقياس الموضع مسمّى: تغطية أدوارٍ محلية، لا اتصالٌ بالبنية الأعلى ولا اكتمال الجملة وحدّها',
      all('تغطية الأدوار المحلية' in o_['measure'] and 'البنية الأعلى' in o_['measure'] for c in C for o_ in c['obligations']
          if o_['requirement_kind'] == 'PLACEMENT'))

# ---------- مراجعة 040: مستوى الشهادة، ومضمون الحدّ لا وجود حقوله، وهوية الوجه ----------
from sarf.algebra import CLOSURE_LEVELS, _locs


def run_j(s, v):
    a = analyze(CAT, verse_text(s, v), 'auto')
    S_, U_ = sentence_geo(a, f'Q{s}:{v}', Trace())
    C_, R_ = [], []
    LT_, _, _ = linguistic_layer([(s, v, a, U_, S_)], Trace(), 'test', cond_out=C_, rel_out=R_)
    o_ = verse_relations(a, U_, unit_features(a, U_), f'{s}:{v}', legacy_cond=C_, legacy_rel=R_)
    return o_, [J for SP in LT_ for D in SP.A + SP.O.get('pending', []) for J in D.A + D.O.get('pending', [])]


check('L01 ن٤ لكل شهادةٍ حكمٌ في كل مستوى (الإسناد المحلي، والجملة، والوحدة الخطابية)، والحكم الرئيس موسومٌ بمستواه ومطابقٌ لحكم ذلك المستوى؛ '
      'ولا حكمٌ أعلى أقوى من الأدنى', all(set(c['verdict_by_level']) == set(CLOSURE_LEVELS) and c['verdict'] == c['verdict_by_level'][c['verdict_level']]
                                          and set(c['boundary']['levels']) == set(CLOSURE_LEVELS) and
                                          not (c['boundary']['levels']['SENTENCE'] == 'PROVEN' and c['boundary']['levels']['LOCAL_PREDICATION'] != 'PROVEN')
                                          for c in C + C3))
CLOSED_ = ('CLOSED_IN_FACE', 'CLOSED_WITH_SHARED_STRUCTURE')
check('L02 ن٤ لا ينتقل حكمٌ محلي إلى الجملة: كل جملةٍ مغلقةٍ في مستوى الجملة حدُّها مثبتٌ في ذلك المستوى (استقلالٌ مشهود)، ولا تُغلق الجملة '
      'وحدّها محليٌّ وحده', all(c['boundary']['levels'][lv] == 'PROVEN' and (lv == 'LOCAL_PREDICATION' or c['boundary']['independence_status'] == 'PROVEN')
                                for c in C + C3 for lv in CLOSURE_LEVELS if c['verdict_by_level'][lv] in CLOSED_))
o3j, J3 = run_j(112, 3)
cl0 = closure_certificate(J3[0], o3j['records'])
# إفساد المضمون: علاقة عملٍ مرخَّصة يمتدّ عضوها وراء الحدّ (مفعولٌ في الآية التالية)، والحقول كلها باقيةٌ ممتلئة
mx = copy.deepcopy(o3j['records'])
fake = copy.deepcopy(next(r for r in mx if r['type'] == 'VERB_FRAME'))
fake.update(type='OBJECT', relation_id='MUT:OBJECT:cross', rule_id='MUT', status='LICENSED')
fake['heads'] = dict(verb=fake['heads']['verb'], object='Q112:4.w2.u0')
fake['members'] = dict(verb=[fake['heads']['verb']], object=['Q112:4.w2.u0'])
fake['positions'] = dict(verb=sorted(_locs(fake))[:1], object=['112:4:2'])
mx.append(fake)
cl1 = closure_certificate(J3[0], mx)
check('L03 ن٥ إفساد مضمون الحدّ: علاقة عملٍ مرخَّصة تعبر الحدّ تُسقط ثباته والإغلاق المحلي، مع بقاء القاعدة ومعرّف الدليل والمستوى ممتلئة',
      cl0['verdict_by_level']['LOCAL_PREDICATION'] == 'CLOSED_IN_FACE' and cl1['boundary']['rule_id'] and cl1['boundary']['evidence_id'] and
      cl1['boundary']['level'] and cl1['boundary']['stability']['status'] == 'NOT_PROVEN' and
      'MUT:OBJECT:cross' in cl1['boundary']['stability']['crossing_local'] and
      cl1['verdict_by_level']['LOCAL_PREDICATION'] == 'DEFERRED_BOUNDARY', (cl1['boundary']['stability'], cl1['verdict_by_level']))
my = copy.deepcopy(o3j['records'])
link = copy.deepcopy(fake)
link.update(type='CONDITION', relation_id='MUT:CONDITION:link', status='LICENSED')
my.append(link)
cl2 = closure_certificate(J3[0], my)
check('L04 ن٥ رابطٌ مرخَّص بين الجمل يعبر الحدّ لا يمدّ الإسناد المحلي (يبقى مغلقاً محلياً) لكنه ينفي الاستقلال: فلا يثبت حدّ الجملة',
      cl2['verdict_by_level']['LOCAL_PREDICATION'] == 'CLOSED_IN_FACE' and cl2['boundary']['independence_status'] == 'DISPROVEN' and
      cl2['boundary']['levels']['SENTENCE'] != 'PROVEN' and cl2['verdict_by_level']['SENTENCE'] == 'DEFERRED_BOUNDARY',
      (cl2['boundary']['independence_status'], cl2['verdict_by_level']))
# إفساد المستوى (مراجعة 046/§١٨ من التكليف 03): ادّعاء «آخر السورة» في حقل السبب لا يرفع الحدّ ما لم يوافقه موضعٌ في المصدر
J3m = copy.deepcopy(J3[0])
J3m.O['boundary'] = dict(J3m.O['boundary'], J_why='آخر السورة', J='proven')
cl3 = closure_certificate(J3m, o3j['records'])
o4j, J4 = run_j(112, 4)
cl4 = closure_certificate(J4[-1], o4j['records'])
check('L05 ادّعاء «آخر السورة» المصطنع (112:3 ليست آخر السورة) يُرفض من المصدر ولا يرفع مستوى الحدّ؛ وآخر السورة الحقيقي (112:4) '
      'يُقبل من المصحف المعتمد في مستوى الجملة والوحدة الخطابية — فالحكم يتبع موضع المصدر لا العبارة',
      cl3['boundary'].get('sura_end_claim_rejected') and cl3['boundary']['levels']['SENTENCE'] != 'PROVEN' and
      cl3['verdict_by_level']['SENTENCE'] == 'DEFERRED_BOUNDARY' and cl4['boundary']['rule_id'] == 'SOURCE:sura_end' and
      cl4['boundary']['levels']['SENTENCE'] == 'PROVEN' and cl4['boundary']['levels']['DISCOURSE_UNIT'] == 'PROVEN',
      (cl3['boundary'].get('sura_end_claim_rejected'), cl3['boundary']['levels'], cl4['boundary']['levels'], cl4['boundary'].get('rule_id')))

# هوية الوجه
subj_met = [o_ for c in C for o_ in c['obligations'] if o_['requirement_kind'].startswith(('SUBJECT', 'AGENT', 'NASIKH')) and o_['met']
            and o_.get('discharge_relation_id')]
check('F01 ن٦ كل فاعلٍ مستوفى بعلاقةٍ في 14أ يحمل معرّف وجهٍ آلياً منفصلاً عن وصفه، ومعرّف المرشّح الصرفي، وخريطة اشتراكٍ كل وجهٍ فيها مستوفى',
      subj_met and all(str(o_['face_id']).startswith(('FACE:', 'SHARED:')) and o_['face_label'] and o_['morph_candidate_id'] and
                       '#' in o_['morph_candidate_id'] and o_['face_map'] and all(x['relations'] for x in o_['face_map']) for o_ in subj_met),
      [(o_['name'], o_['face_id'], o_['morph_candidate_id']) for o_ in subj_met if not str(o_['face_id']).startswith(('FACE:', 'SHARED:'))][:3])
ob_d = next(o_ for c in C for o_ in c['obligations'] if 'يُضَارَّ' in o_['name'] and o_['requirement_kind'] == 'SUBJECT_OR_PASSIVE_AGENT')
check('F02 ن٦ «لَا يُضَآرَّ كَاتِبٞ»: البناء مؤجَّل، فالاستيفاء في كل الأوجه بخريطةٍ صريحة: وجه المعلوم ووجه المجهول، ولكلٍّ علاقته',
      ob_d['status'] == 'MET_IN_ALL_FACES' and ob_d['face_id'].startswith('SHARED:') and
      sorted(x['face_id'].split('|V=')[1].split('|')[0] for x in ob_d['face_map']) == ['مجهول', 'معلوم'] and all(x['relations'] for x in ob_d['face_map']), ob_d)
o2j, J2 = run_j(2, 282)
JA = next(J for J in J2 if any(o_.name == 'فاعل «يُمْلِلْ»' for o_ in J.Omega))
ca0 = closure_certificate(JA, o2j['records'])
oa0 = next(o_ for o_ in ca0['obligations'] if o_['name'] == 'فاعل «يُمْلِلْ»')
mz = copy.deepcopy(o2j['records'])
next(r for r in mz if r['type'] == 'SUBJECT' and r['texts'].get('verb') == 'يُمْلِلْ')['role_name'] = 'نائب فاعل'
oa1 = next(o_ for o_ in closure_certificate(JA, mz)['obligations'] if o_['obligation_id'] == oa0['obligation_id'])
check('F03 ن٦ إفساد الوجه: علاقة فاعل «فَلْيُمْلِلْ وَلِيُّهُ» المرخَّصة يُغيَّر دورها إلى «نائب فاعل» والإطار معلوم — لا تستوفي الالتزام (خلط أوجه)، بمعرّفٍ لا بوصف',
      oa0['status'] == 'MET' and oa1['status'] == 'CONFLICT' and not oa1['met'] and oa1['residual_reason'].startswith('FACE_MISMATCH'),
      (oa0['status'], oa1['status'], oa1['residual_reason'][:80]))
mw = copy.deepcopy(o2j['records'])
fa = next(r for r in mw if r['type'] == 'VERB_FRAME' and r['heads']['verb'] == oa0['owner'])
fa['frame']['voice'] = ('مجهول', 'مثبت', None)
fa['frame']['candidate']['voice'] = 'مجهول'
oa2 = next(o_ for o_ in closure_certificate(JA, mw)['obligations'] if o_['obligation_id'] == oa0['obligation_id'])
check('F04 ن٦ إفساد المرشّح: تحويل بناء إطار «يُمْلِلْ» إلى المجهول مع فاعلٍ معلوم الدور — الوجه بلا علاقةٍ تقع فيه، فلا استيفاء',
      oa2['status'] == 'CONFLICT' and 'V=مجهول' in oa2['face_id'], (oa2['status'], oa2['face_id']))

print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
