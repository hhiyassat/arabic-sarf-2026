# -*- coding: utf-8 -*-
"""شواهد AR03 (SARF_AR02_AUDIT_REPAIR_01). لا أجوبة مرجعية ولا قوائم استثناء.
  F  هوية التحليل الكاملة في face_rivals (§٢) — أربعة إلزامية
  G  وجهٌ لكل لمّة وقالب في morph_faces (§٣)
  S  الحالات الأربع المستقلة (§٤)
  M  الإفساد التسعة بكواشف مسمّاة (§٥): original_valid وvalue_actually_changed وexpected_detector وactual_detector وmutated_rejected
  D  المثنى (§٦)
  R  التحقيق العكسي: لكل قاعدة شاهدٌ موجب ومقابل والتباس (§٧)
  K  أثر التحقيق في الاختيار (§٨)
  L  اللواحق وسياسة المطابقة (§٩)
  W  مسارات الوجه الاسمي (§١٠)
  X  عابرة للطبقات (§١١)
"""
import copy, json, os, random, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
from sarf.root import (morph, morph_faces, face_rivals, analysis_key, analysis_id, selection_statuses, face_realization, hfn,
                       match_policy, match_transformations, stem_info)
from sarf.face_check import check_face_record
from sarf.analyze import analyze
from sarf.catalog import Catalog

CAT = Catalog([os.path.join(H, 'operators_catalog.jsonl'), os.path.join(H, 'operators_catalog_split_vocalized.csv')])
FAILS, MUT = [], []


def check(name, ok, info=''):
    print(('ok  ' if ok else 'FAIL') + ' ' + name + (' — ' + str(info)[:300] if not ok else ''))
    if not ok:
        FAILS.append(name)


# ---------- F: هوية التحليل الكاملة (§٢) ----------
P = dict(span='تَبَرَّ', root='برر', form_class='I', kind='فعل', lemma='بَرَّ')
r, d, sh = face_rivals(P, [dict(span='تَبَرَّكَ', root='برر', form_class='I', kind='فعل', lemma='بَرَّ', evidence='e1')])
check('F1 الجذر والباب واللمّة واحدة والامتداد مختلف: وجهان (منافسٌ لا شاهدٌ مكرّر)', len(r) == 1 and d == [] and sh == 'برر', (r, d))
r, d, sh = face_rivals(P, [dict(span='تَبَرَّ', root='برر', form_class=None, pos='مصدر', kind='مصدر', lemma='بَرَّ', evidence='e1')])
check('F2 الامتداد واحد والصنف مختلف: وجهان', len(r) == 1 and d == [], (r, d))
r, d, sh = face_rivals(P, [dict(span='تَبَرَّكَ', root='برك', form_class='V', kind='فعل', lemma='تَبَرَّكَ', evidence='e1'),
                           dict(span='تَبَرَّكَ', root='برك', form_class='V', kind='فعل', lemma='تَبَرَّكَ', evidence='e2')])
check('F3 التحليل نفسه بدليلين: وجهٌ واحد يحمل الدليلين', len(r) == 1 and r[0]['evidence'] == ['e1', 'e2'], r)
wf = [dict(span='تَبَرَّكَ', root=x, form_class='V', kind='فعل', lemma=x, evidence=e) for x in ('برك', 'بور', 'برق') for e in ('e1', 'e2')] + \
     [dict(span='تَبَرَّ', root='برر', form_class='I', kind='فعل', lemma='بَرَّ', evidence='e3')]
outs = set()
for seed in range(6):
    sh_ = copy.deepcopy(wf)
    random.Random(seed).shuffle(sh_)
    r, d, sh = face_rivals(P, sh_)
    outs.add(json.dumps([r, d, sh], ensure_ascii=False, sort_keys=True))
check('F4 ترتيب الأدلة والأوجه لا يغيّر النتيجة (المنافسون وهوياتهم وأدلتهم والمكرّر)', len(outs) == 1, len(outs))
r, d, sh = face_rivals(P, [dict(span='تَبَرَّ', root='برر', form_class='I', kind='فعل', lemma='بَرَّ', evidence='e9')])
check('F5 المفتاح كله يطابق وجه القطع: شاهدٌ مكرّر بدليله، لا منافس', r == [] and len(d) == 1 and d[0]['evidence'] == ['e9'], (r, d))

# ---------- G: وجهٌ لكل لمّة وقالب (§٣) ----------
LIC = [dict(root='حسب', form_class='I', verb='حَسَبَ', hfn_form='فَعَلَ', event_id='HFN-E-8830469cb3'),
       dict(root='حسب', form_class='I', verb='حَسِبَ', hfn_form='فَعِلَ', event_id='HFN-E-21c3d3ea39'),
       dict(root='حسب', form_class='I', verb='حَسِبَ', hfn_form='فَعِلَ', event_id='HFN-E-e77c876179')]
out = dict(status='accepted', root='حسب', form_class='I', level='event', licensed=LIC, candidates=[('حسب', 'I')])
fs = morph_faces('حسب', out)
check('G1 حَسَبَ/فَعَلَ وحَسِبَ/فَعِلَ وجهان، لكلٍّ قالبه وأدلته؛ ولا وجه بلمّةٍ فارغة', sorted((f['lemma'], tuple(f['hfn_forms']), len(f['evidence_ids'])) for f in fs) ==
      [('حَسَبَ', ('فَعَلَ',), 1), ('حَسِبَ', ('فَعِلَ',), 2)] and all(f['lemma'] for f in fs), fs)
st = selection_statuses(dict(out, faces=fs))
check('G2 المكتوب لا يفصل (حسب بلا حركات): لا وجه مختار، والجذر مثبت، والاختيار الكامل مؤجَّل لتعدّد اللمّات',
      not any(f['status'] == 'SELECTED' for f in fs) and st['root_status'] == 'PROVEN' and st['analysis_selection_status'] == 'DEFERRED_MULTIPLE_LEMMAS'
      and st['pattern_status'] == 'DEFERRED', (st, [f['status'] for f in fs]))
fs = morph_faces('حَسَبْتُ', out)
check('G3 المكتوب يفصل (حَسَبْتُ): حَسَبَ وحده مختارٌ بالكتابة، وحَسِبَ مرخّصٌ غير مختار', [(f['lemma'], f['status']) for f in fs] ==
      [('حَسَبَ', 'SELECTED'), ('حَسِبَ', 'LICENSED')] and fs[0]['selection_basis'] == 'WRITTEN_FORM_UNIQUE', [(f['lemma'], f['status']) for f in fs])
m = morph('حَسَبَ', dict(stem_info('حَسَبَ'), pos='verb', governed=True))
check('G4 morph: حَسَبَ المحكوم بعامل وجهٌ مختار واحد، ووزن الوقوع وزنه هو (فَعَلَ) لا وزن المجموعة', m['status'] == 'accepted' and
      [f['lemma'] for f in m['faces'] if f['status'] == 'SELECTED'] == ['حَسَبَ'] and m['pattern']['lemma_pattern'] == 'فَعَلَ' and
      check_face_record('حَسَبَ', m) == [], (m['statuses'], m.get('pattern')))

# ---------- S: الحالات الأربع (§٤) ----------
for w in ('سَمِنَ', 'حَسِبَ'):
    m = morph(w)
    check(f'S1 {w}: class_deferred بلا وجهٍ مختار ولا وزن ولا جذر، والحالات الأربع مؤجَّلة', m['status'] == 'class_deferred' and
          not any(f['status'] in ('SELECTED', 'SELECTED_ROOT_LICENCE') for f in m['faces']) and m.get('pattern') is None and m.get('root') is None
          and m['statuses'] == dict(root_status='CLASS_DEFERRED', pattern_status='DEFERRED', analysis_selection_status='DEFERRED',
                                    class_status='CLASS_DEFERRED') and check_face_record(w, m) == [], m['statuses'])
m = morph('إِنَّ')
check('S2 المحمي: not_applicable، root_status NOT_APPLICABLE، بلا أوجه', m['status'] == 'not_applicable' and m['root_status'] == 'NOT_APPLICABLE'
      and not m.get('faces') and check_face_record('إِنَّ', m) == [])
for w in ('كَتَبْتُ', 'ادَّخَرَ', 'آمَنَ', 'قَالَ', 'يَكْتُبُ', 'وَقُلْ'):
    m = morph(w)
    check(f'S3 {w}: الحالات المسجّلة تُعاد من الأوجه، والفاحص لا يجد خللاً', m['statuses'] == selection_statuses(m) and check_face_record(w, m) == [],
          (m['statuses'], check_face_record(w, m)))
# رخصة جذرٍ بلا حدث: لا «مقبول» مع وجهٍ مولَّد يرفضه الفاحص
out = dict(status='accepted', root='كتب', form_class='II', level='root', licensed=[], candidates=[('كتب', 'II')])
fs = morph_faces('كَتَّبَ', out)
check('S4 القبول على مستوى الجذر: الوجه SELECTED_ROOT_LICENCE بشاهد ROOT:كتب، والاختيار ROOT_LICENCE_ONLY، والفاحص يقبله',
      [f['status'] for f in fs] == ['SELECTED_ROOT_LICENCE'] and fs[0]['evidence_ids'] == ['ROOT:كتب'] and
      selection_statuses(dict(out, faces=fs))['analysis_selection_status'] == 'ROOT_LICENCE_ONLY' and
      check_face_record('كَتَّبَ', dict(out, faces=fs, pattern=None, statuses=selection_statuses(dict(out, faces=fs)))) == [], fs)


# ---------- M: الإفساد التسعة (§٥) ----------
def mutate(name, word, fn, expected, base=None):
    base = base or morph(word)
    orig_ok = check_face_record(word, base) == []
    mut = copy.deepcopy(base)
    fn(mut)
    changed = json.dumps(mut, ensure_ascii=False, sort_keys=True, default=str) != json.dumps(base, ensure_ascii=False, sort_keys=True, default=str)
    found = check_face_record(word, mut)
    det = sorted({d for d, _ in found})
    rec = dict(mutation=name, word=word, original_valid=orig_ok, value_actually_changed=changed, expected_detector=expected,
               actual_detector=det, mutated_rejected=bool(found), messages=[m_ for _, m_ in found][:4])
    MUT.append(rec)
    check(f'M {name}: الأصل سليم، والقيمة تغيّرت، وكشفها {expected}', orig_ok and changed and expected in det, rec)


def sel(m):
    return next(f for f in m['faces'] if f['status'] == 'SELECTED')


mutate('١ حذف realization', 'كَتَبْتُ', lambda m: sel(m).pop('realization'), 'SCHEMA')
mutate('٢ تفريغ hfn_forms', 'كَتَبْتُ', lambda m: sel(m).__setitem__('hfn_forms', []), 'EVIDENCE_MISSING')
mutate('٣ تفريغ الأدلة', 'كَتَبْتُ', lambda m: sel(m).__setitem__('evidence_ids', []), 'EVIDENCE_MISSING')
mutate('٤أ تزوير وزن الوجه', 'كَتَبْتُ', lambda m: sel(m)['patterns']['lemma_pattern'].__setitem__('value_or_alternatives', ['فَعِلَ']), 'PATTERN')
mutate('٤ب تزوير وزن الوقوع', 'كَتَبْتُ', lambda m: m['pattern'].__setitem__('lemma_pattern', 'فَعِلَ'), 'PATTERN')
mutate('٥ تزوير reconstructed_form', 'كَتَبْتُ', lambda m: sel(m)['realization']['lemma'].__setitem__('reconstructed_form', 'كَذَبَ'), 'REALIZATION')
mutate('٦أ matched يناقض الحالة', 'كَتَبْتُ', lambda m: sel(m)['realization']['lemma'].__setitem__('matched', False), 'REALIZATION')
mutate('٦ب الحالة تناقض التحقيق المعاد', 'كَتَبْتُ', lambda m: sel(m)['realization']['lemma'].update(status='MISMATCH', matched=False), 'REALIZATION')
G4 = morph('حَسَبَ', dict(stem_info('حَسَبَ'), pos='verb', governed=True))
mutate('٧ دليل لمّةٍ أخرى بالجذر والباب نفسيهما', 'حَسَبَ', lambda m: sel(m).__setitem__('evidence_ids', ['HFN-E-21c3d3ea39']), 'EVIDENCE_LINK', base=G4)
mutate('٨أ جذرٌ على وجهٍ محمي', 'إِنَّ', lambda m: m.update(root='ءنن', form_class='I'), 'PROTECTION')
mutate('٨ب وزنٌ على وجهٍ محمي', 'إِنَّ', lambda m: m.update(pattern=dict(lemma_pattern='فَعَلَ')), 'PROTECTION')
mutate('٩ وجهٌ مختار بعد تأجيل الفئة', 'سَمِنَ', lambda m: m['faces'][0].__setitem__('status', 'SELECTED'), 'PROTECTION')
mutate('٩ب الحالات الأربع تناقض الأوجه', 'كَتَبْتُ', lambda m: m['statuses'].__setitem__('analysis_selection_status', 'DEFERRED_MULTIPLE_LEMMAS'), 'STATUS')

# ---------- D: المثنى (§٦) ----------
from sarf.cells import number_mark_splits, number_mark_deferrals, noun_template_faces
for w, bad in (('بَيْتَانِ', 'بَيْة'), ('صَوْتَانِ', 'صَوْة')):
    sp = number_mark_splits(w)
    fs = noun_template_faces(w)
    check(f'D1 {w}: التاء أصلية محفوظة، ولا «{bad}» (الساكن قبل التاء يمنع بديل المربوطة)', sp and all(s[0] != bad for s in sp) and
          all(f['segmentation'][0] != bad for f in fs) and any(f['segmentation'][0] == sp[0][0] and sp[0][0].endswith('ت') for f in fs),
          (sp, [f['segmentation'] for f in fs]))
fs = noun_template_faces('امْرَأَتَانِ')
check('D2 امْرَأَتَانِ: وجه التأنيث (امْرَأَة) محفوظٌ بعمليته، ووجه التاء كما كُتبت محفوظ', any(f['segmentation'][0] == 'امْرَأَة' and
      f['split_operations'] == ['TA_MARBUTA_TO_TA_BEFORE_NUMBER_MARK'] for f in fs) and any(f['segmentation'][0] == 'امْرَأَت' for f in fs),
      [(f['segmentation'], f['split_operations']) for f in fs])
fs = noun_template_faces('يَدَانِ')
check('D3 يَدَانِ: لا يُرفض لقصر جذعه؛ يُحلَّل بباب ما حُذفت لامه (يدي)، والعدد مرشّحٌ بالعلامة لا مثبت',
      any(f['root'] == 'يدي' and f['segmentation'] == ['يَد', 'َانِ'] and f['split_operations'] == ['DELETED_LAM_STEM'] and
          f['number_status'] == 'CANDIDATE_BY_ENDING' for f in fs), fs)
dfr = number_mark_deferrals('حِينَ')
check('D4 حِينَ: الجذع القصير بلا قاعدة محذوفٍ مؤجَّلٌ بسببٍ مسمّى، لا رفضٌ صامت', dfr and dfr[0]['reason'] == 'SHORT_STEM_NO_DELETED_RADICAL_RULE', dfr)
fs = noun_template_faces('مِسْكِينَ')
check('D5 مِسْكِينَ: الجمع لا يثبت من الخاتمة وحدها — الوجه المفرد (مِفْعِيل، سكن) محفوظ، والعدد مرشّح', any(not f['number_mark'] and f['root'] == 'سكن'
      for f in fs) and all(f.get('number_status') == 'CANDIDATE_BY_ENDING' for f in fs if f['number_mark']), [(f['root'], f['segmentation']) for f in fs])
fs = noun_template_faces('شَجَرَتَانِ')
check('D6 شَجَرَتَانِ: مفتوحٌ قبل التاء → البديل المربوط يُولَّد، والتاء كما كُتبت محفوظة (التوليد غير الاختيار)',
      {f['segmentation'][0] for f in fs if f['number_mark']} == {'شَجَرَة', 'شَجَرَت'}, [f['segmentation'] for f in fs])

# ---------- R: التحقيق العكسي (§٧) ----------
from sarf.realize import verify, realize_lemma


def V(*a):
    return verify(*a)


for lemma, args, op in (('أَعْطَى', ('عطو', 'IV', 'أَفْعَلَ'), 'WEAK_LAM'), ('سَمَّى', ('سمو', 'II', 'فَعَّلَ'), 'WEAK_LAM'),
                        ('ادَّعَى', ('دعو', 'VIII', 'افْتَعَلَ'), 'WEAK_LAM'), ('أَقَامَ', ('قوم', 'IV', 'أَفْعَلَ'), 'HOLLOW_AYN_DERIVED'),
                        ('اسْتَقَامَ', ('قوم', 'X', 'اسْتَفْعَلَ'), 'HOLLOW_AYN_DERIVED'), ('انْقَادَ', ('قود', 'VII', 'انْفَعَلَ'), 'HOLLOW_AYN_DERIVED'),
                        ('اخْتَارَ', ('خير', 'VIII', 'افْتَعَلَ'), 'HOLLOW_AYN_DERIVED'), ('اتَّخَذَ', ('ءخذ', 'VIII', 'افْتَعَلَ'), 'VIII_HAMZA_FA_ASSIMILATED_TO_TA'),
                        ('خَافَ', ('خوف', 'I', 'فَعِلَ'), 'HOLLOW_AYN'), ('حَسِبَ', ('حسب', 'I', 'فَعَلَ/فَعِلَ'), 'SUBSTITUTE')):
    r = V(*args, lemma)
    check(f'R1 موجب: {lemma} يُعاد من {args[0]}+{args[2]} بالعملية {op}', r['status'] == 'MATCHED' and op in r['operations'], r)
for lemma, args, why in (('دَعَا', ('دعو', 'I', 'فَعَلَ'), 'الثلاثي الواوي ألفاً لا ياءً'), ('أَحْيَا', ('حيي', 'IV', 'أَفْعَلَ'), 'بعد الياء ألفاً'),
                         ('اسْتَحْوَذَ', ('حوذ', 'X', 'اسْتَفْعَلَ'), 'الأجوف المزيد الصحيح العين بديلاً'),
                         ('سَوِيَ', ('سوو', 'I', 'فَعِلَ'), 'اللفيف الواوي لا يُدغم ولا يُعَلّ عينه')):
    r = V(*args, lemma)
    check(f'R2 مقابل: {lemma} ({why}) يتحقق بقاعدته لا بقاعدة غيره', r['status'] == 'MATCHED', r)
r = V('كتب', 'I', 'فَعَلَ/فَعِلَ', 'كَذَبَ')
check('R3 مقابل: الهدف المختلف MISMATCH بعد تجربة البديلين كليهما', r['status'] == 'MISMATCH' and sorted(r['alternatives']) == sorted(['كَتَبَ', 'كَتِبَ']), r)
for args, alts in ((('قوم', 'IV', 'أَفْعَلَ'), {'أَقْوَمَ', 'أَقَامَ'}), (('حيي', 'I', 'فَعِلَ'), {'حَيِيَ', 'حَيَّ'}),
                   (('ءخذ', 'VIII', 'افْتَعَلَ'), {'ائْتَخَذَ', 'اتَّخَذَ'}), (('حسب', 'I', 'فَعَلَ/فَعِلَ'), {'حَسَبَ', 'حَسِبَ'})):
    got = {x['form'] for x in realize_lemma(*args)['alternatives']}
    check(f'R4 التباس: {args} يُعطي البدائل كلها {sorted(alts)} بلا اختيار', got == alts, got)
r = V('كتب', 'I', '', 'كَتَبَ')
check('R5 NOT_COVERED حين لا قاعدة (صيغةٌ فارغة)، لا MISMATCH', r['status'] == 'NOT_COVERED' and r['not_covered_reason'], r)
r = V('كتبر', 'I', 'فَعْلَلَ', 'كَتْبَرَ')
check('R6 الرباعي في التغطية: كَتْبَرَ يُعاد', r['status'] == 'MATCHED', r)

# ---------- K: أثر التحقيق في الاختيار (§٨) ----------
H_ = hfn()
ev = H_.index[('كتب', 'I')][0]
old = ev['form']
try:
    ev['form'] = 'فَعِلَ'                     # إفساد قالب الوجه المختار في المورد نفسه (داخل الاختبار وحده)
    m = morph('كَتَبْتُ')
    f = next(x for x in m['faces'] if x['root'] == 'كتب')
    check('K1 قالبٌ مُفسَد للوجه المختار: التعارض مكتشَف (MISMATCH)، والوجه غير مختار، ولا وزن على الوقوع، والاختيار مؤجَّل بسببه',
          f['realization']['lemma']['status'] == 'MISMATCH' and f['status'] != 'SELECTED' and f['selection_blocked_by'] == 'REALIZATION_MISMATCH'
          and m.get('pattern') is None and m['statuses']['analysis_selection_status'] == 'DEFERRED_REALIZATION_CONFLICT' and
          check_face_record('كَتَبْتُ', m) == [], (f['status'], m['statuses']))
    a = analyze(CAT, 'كَتَبْتُ', 'auto')
    x = a['morph'][0]
    check('K2 عابر: الواجهة العامة لا تستهلك الوجه بلا شرط — لا هوية تحليلٍ مختار ولا وزن', x.get('analysis_id') is None and x.get('pattern') is None
          and x['statuses']['analysis_selection_status'] == 'DEFERRED_REALIZATION_CONFLICT', x)
finally:
    ev['form'] = old
m = morph('كَتَبْتُ')
check('K3 بعد الإصلاح: يعود الوجه مختاراً (لا نتيجة قديمة بعد تغيّر الوجه)', sel(m)['lemma'] == 'كَتَبَ' and m['pattern']['lemma_pattern'] == 'فَعَلَ')
m = morph('آمَنَ')
f = next(x for x in m['faces'] if x['root'] == 'ءمن' and x['form_class'] == 'IV')
check('K4 نجاح التحقيق ليس إثباتاً للصنف: آمَنَ يتحقق ويبقى مؤجَّلاً', f['realization']['lemma']['status'] == 'MATCHED' and m['status'] == 'deferred'
      and f['status'] == 'LICENSED')

# ---------- L: اللواحق وسياسة المطابقة (§٩) ----------
R = lambda w: face_realization(w, 'كتب', 'I', 'فَعَلَ', 'كَتَبَ')['word']
w = R('كَتَبَ')
check('L1 حرفيّ: كَتَبَ MATCHED بسياسة NFC_LITERAL ولا تحويل', w['status'] == 'MATCHED' and w['comparison_policy'] == 'NFC_LITERAL' and w['transformations'] == [])
w = R('كَتَبَتْهُ')
check('L2 لاحقة إسنادٍ ثم مفعول: كَتَبَتْهُ = كَتَبَ + تْ + هُ، والحكم لا يدّعي تصريف الكلمة كلها', w['status'] == 'MATCHED_STEM_AND_LICENSED_SUFFIX' and
      w['spans'] == dict(stem='كَتَبَ', subject_suffix='تْ', object_suffix='هُ') and 'خارج هذا الحكم' in w['note'], w)
w = R('كَتَبۡنَا')
check('L3 تحويلٌ مرخّص مسمّى: كَتَبۡنَا بالسكون العثماني، والسياسة NAMED_TRANSFORMATIONS لا NFC_LITERAL', w['status'] == 'MATCHED_STEM_AND_LICENSED_SUFFIX' and
      w['comparison_policy'] == 'NAMED_TRANSFORMATIONS' and w['transformations'] == ['UTHMANI_SUKUN_AS_SUKUN'], w)
w = R('كَتَبَتَتَ')
check('L4 مخالفة: كَتَبَتَتَ SUFFIX_NOT_LICENSED (لا MATCHED_STEM)', w['status'] == 'SUFFIX_NOT_LICENSED' and w['spans']['rest'] == 'تَتَ', w)
w = R('كَتَبَهُتْ')
check('L5 الترتيب: المفعول قبل الفاعل (كَتَبَهُتْ) مرفوض', w['status'] == 'SUFFIX_NOT_LICENSED', w)
w = R('يَكْتُبُ')
check('L6 غير مغطّى: المضارع NOT_COVERED لا MISMATCH', w['status'] == 'NOT_COVERED', w)
check('L7 NFC_LITERAL تعني NFC وحده؛ والتطويل والعلامات تحويلٌ مسمّى', match_policy('كَتَبَ', 'كَتَبَ') == 'NFC_LITERAL' and
      match_transformations('كَتـَبَ', 'كَتَبَ') == ['UTHMANI_MARKS_AND_TATWEEL_REMOVED'] and match_policy('كَتـَبَ', 'كَتَبَ') != 'NFC_LITERAL' and
      match_transformations('اسْتَهْنَءَ', 'اسْتَهْنَأَ') == ['HAMZA_SEAT_UNIFIED'] and match_transformations('كَتَبَ', 'كَذَبَ') is None)
m = morph('كَتَبَتَتَ', dict(stem_info('كَتَبَتَتَ'), pos='verb', governed=True))
fk = [f for f in (m or {}).get('faces') or [] if f.get('lemma') == 'كَتَبَ']
check('L8 عابر: إن رُخّص «كَتَبَ» لكَتَبَتَتَ فلا يُختار (اللاحقة غير مرخّصة تمنع الاختيار)', m is None or not fk or
      all(f['status'] != 'SELECTED' and f.get('selection_blocked_by') == 'SUFFIX_NOT_LICENSED' for f in fk), fk)

w = R('كَتَبُو')
check('L9 الامتداد يقف قبل ضمير المفعول (كَتَبُو|هُ): NOT_COVERED بسببٍ مسمّى، لا SUFFIX_NOT_LICENSED', w['status'] == 'NOT_COVERED' and
      w['reason'] == 'SUFFIX_REQUIRES_OBJECT_OUTSIDE_SPAN', w)
w = face_realization('وَعَدْتُّمْ', 'وعد', 'I', 'فَعَلَ', 'وَعَدَ')['word']
check('L10 تاء الفاعل المدغمة بعد الدال (وَعَدْتُّمْ): مرخّصة بتحويلٍ مسمّى', w['status'] == 'MATCHED_STEM_AND_LICENSED_SUFFIX' and
      'TA_ASSIMILATED_AFTER_DAL_TA' in w['transformations'], w)
w = face_realization('كَتَبْتُّمْ', 'كتب', 'I', 'فَعَلَ', 'كَتَبَ')['word']
check('L11 مقابل: التاء المشدّدة بعد غير الدال والطاء والتاء (كَتَبْتُّمْ) غير مرخّصة', w['status'] == 'SUFFIX_NOT_LICENSED', w)

# ---------- W: مسارات الوجه الاسمي (§١٠) ----------
from sarf.cells import _noun_template_faces_whole
fs = _noun_template_faces_whole('حَصِين')
paths = {(f['root'], f['pattern']): f['operation_paths'] for f in fs}
check('W1 حَصِين: مساران (الخلايا كما هي → حصن فَعِيل، والياء عينٌ ساكنة → حصي) محفوظان معاً، لا الأول المثمر وحده',
      ('حصن', 'فَعِيلٌ') in paths and any(r == 'حصي' for r, _ in paths) and all(f['search_status'] == 'COMPLETE' for f in fs), paths)
check('W2 لا تكرار حقيقي: كل (جذر، بناء، معرّف) مرة واحدة', len({(f['root'], f['pattern'], f['sid']) for f in fs}) == len(fs))

# ---------- X: عابرة للطبقات (§١١) ----------
from sarf.algebra import sentence_geo, Trace
from sarf.features import unit_features


def layers(w):
    a = analyze(CAT, w, 'auto')
    S_, U = sentence_geo(a, 'B', Trace())
    return a, U, unit_features(a, U)


a, U, F = layers('وَقَالَتْ')
x = a['morph'][0]
th = U[(0, 1)].Theta.get('analysis_selection') or {}
check('X1 وَقَالَتْ: هوية التحليل المختار نفسها في morph والإغلاق، والوزن من الوجه المختار', x['statuses']['analysis_selection_status'] == 'SELECTED'
      and x['analysis_id'] and th.get('analysis_id') == x['analysis_id'] and th.get('status') == 'SELECTED' and x['pattern']['lemma_pattern'] == 'فَعَلَ', (x, th))
a, U, F = layers('تَبَرَّكَ')
x = a['morph'][0]
check('X2 تَبَرَّكَ: مؤجَّل، ولا هوية مختارة ولا وزن ولا إغلاق بجذر', x['status'] == 'deferred' and x.get('analysis_id') is None and
      x.get('pattern') is None and not U[(0, 0)].closed)
a, U, F = layers('حَسِبْتُمْ')
x = a['morph'][0]
check('X3 حَسِبْتُمْ (فعل قلبٍ محتمل): class_deferred في الواجهة، بلا هوية ولا وزن، والوحدة غير مغلقة بجذر', x['status'] == 'class_deferred' and
      x.get('analysis_id') is None and x.get('pattern') is None and not U[(0, 0)].closed, x)
from sarf.face_check import check_verse_entry
for w in ('وَقَالَتْ', 'تَبَرَّكَ', 'لَمْ يَكْتُبْ', 'فَتَبَرَّكَ'):
    a = analyze(CAT, w, 'auto')
    bad = [check_verse_entry(w.split()[x['word_index']] if ' ' in w else w, x, None) for x in a['morph']]
    check(f'X4 {w}: سجلّات الواجهة متسقة (لا هوية مختارة ولا وزن بلا اختيار)', not any(bad), bad)

json.dump(MUT, open(os.environ.get('AR03_MUTATIONS_OUT', '/dev/null'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('نجح' if not FAILS else f'فشل {len(FAILS)}: {FAILS}')
sys.exit(1 if FAILS else 0)
