# -*- coding: utf-8 -*-
"""شواهد AR02 (SARF_ANALYZER_REPAIR_AR02). لا أجوبة مرجعية ولا قوائم استثناء.
  F  المقارنة بين الأوجه بالتحليل الكامل (§٤) — ستة إلزامية
  I  هوية الوجه المستقرة (§٥)
  P  الحماية بتوقّعات صريحة (§١٣)
  M  الإفساد بكواشف مسمّاة (§١٤): لكلٍّ original_valid وvalue_actually_changed وexpected_detector وactual_detector وmutated_rejected
  X  عابرة للطبقات (§١٥)
"""
import copy, json, os, random, sys, unicodedata

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
from sarf.root import morph, face_rivals, analysis_key, analysis_id
from sarf.protected import protected
from sarf.face_check import check_face_record
from sarf.analyze import analyze
from sarf.catalog import Catalog

CAT = Catalog([os.path.join(H, 'operators_catalog.jsonl'), os.path.join(H, 'operators_catalog_split_vocalized.csv')])
FAILS, MUT = [], []


def check(name, ok, info=''):
    print(('ok  ' if ok else 'FAIL') + ' ' + name + (' — ' + str(info)[:300] if not ok else ''))
    if not ok:
        FAILS.append(name)


# ---------- F: المقارنة بالتحليل الكامل ----------
P = dict(span='تَبَرَّ', root='برر', form_class='I', kind='فعل', lemma='بَرَّ')
r, d, sh = face_rivals(P, [dict(span='تَبَرَّكَ', root='برر', form_class='V', kind='فعل', lemma='تَبَرَّرَ')])
check('F1 جذرٌ واحد ووزنٌ مختلف: منافسٌ لا يختفي، والجذر المشترك ثابت', len(r) == 1 and sh == 'برر', (r, sh))
r, d, sh = face_rivals(P, [dict(span='تَبَرَّكَ', root='برر', form_class='I', kind='فعل', lemma='بَرَّ')])
check('F2 جذرٌ ووزنٌ ولمّةٌ واحدة: شاهدٌ مكرّر لا منافس (لا تأجيل زائف)', r == [] and len(d) == 1, (r, d))
r, d, sh = face_rivals(P, [dict(span='تَبَرَّكَ', root='برر', form_class=None, pos='مصدر', kind='مصدر', lemma='تَبَرُّك')])
check('F3 جذرٌ واحد وصنفٌ مختلف (اسم): منافس، والجذر المشترك ثابت', len(r) == 1 and sh == 'برر', (r, sh))
r, d, sh = face_rivals(P, [dict(span='تَبَرَّكَ', root='برك', form_class='V', kind='فعل', lemma='تَبَرَّكَ'),
                           dict(span='تَبَرَّكَ', root='برك', form_class='V', kind='فعل', lemma='تَبَرَّكَ')])
check('F4 تحليلٌ واحد بشاهدين معجميين: منافسٌ واحد لا اثنان', len(r) == 1 and sh is None, (r, sh))
r, d, sh = face_rivals(P, [dict(span='تَبَرَّكَ', root='برك', form_class='V', kind='فعل', lemma='تَبَرَّكَ'),
                           dict(span='تَبَرَّكَ', root='بور', form_class='V', kind='فعل', lemma='تَبَوَّرَ')])
check('F5 جذران مختلفان مرخّصان: يُحفظان، ولا جذر مشترك', len(r) == 2 and sh is None, (r, sh))
r, d, sh = face_rivals(dict(P, span='تَبَرَّ'), [dict(span='تَبَرَّ', root='برر', form_class='I', kind='فعل', lemma='بَرَّ')])
check('F6 التقشير نفسه والتحليل نفسه: لا منافس', r == [])
wf = [dict(span='تَبَرَّكَ', root=x, form_class='V', kind='فعل', lemma=x) for x in ('برك', 'بور', 'برق')]
ids = []
for seed in range(5):
    sh_ = list(wf)
    random.Random(seed).shuffle(sh_)
    ids.append(sorted(x['analysis_id'] for x in face_rivals(P, sh_)[0]))
check('F7 ترتيب الأدلة لا يغيّر المنافسين ولا هوياتهم', all(x == ids[0] for x in ids))

# ---------- I: هوية الوجه ----------
m = morph('كَتَبْتُ')
f = m['faces'][0]
check('I1 الهوية من المحتوى: تُعاد بالمفتاح نفسه', f['analysis_id'] == analysis_id(analysis_key('كَتَبْتُ', f['root'], f['form_class'], 'فعل', f['lemma'])))
check('I2 الهوية لا تتبع ترتيب العرض (لا C1/C2)', not f['analysis_id'].startswith('C') and f['analysis_id'].startswith('A'))
m1, m2 = morph('ادَّخَرَ'), morph('ادَّخَرَ')
check('I3 تشغيلان: الأوجه وهوياتها وحالاتها متطابقة', json.dumps(m1['faces'], ensure_ascii=False) == json.dumps(m2['faces'], ensure_ascii=False))
check('I4 ادَّخَرَ: وجهٌ مختار واحد (ذخر)، والمنافس الدالي مولَّدٌ لا مختار', [x['root'] for x in m1['faces'] if x['status'] == 'SELECTED'] == ['ذخر'] and
      any(x['root'] == 'دخر' and x['status'] == 'GENERATED' for x in m1['faces']))

# ---------- P: الحماية بتوقّعات صريحة ----------
EXP = [('اللَّهُ', 'اسم ذهبي', 'لفظ الجلالة'), ('إِنَّ', 'مبني', 'إِنَّ'), ('الَّذِينَ', 'مبني', 'الَّذِينَ'),
       ('إِبْرَاهِيمَ', 'اسم ذهبي', 'إِبْرَٰهِيم'), ('كَانَ', 'عامل من العوامل المائة', 'كَانَ'), ('لَعَلَّكُمْ', 'عامل من العوامل المائة', 'لَعَلَّ')]
for w, cls, ident in EXP:
    pr, mm = protected(w), morph(w)
    check(f'P1 {w}: الفئة «{cls}» والهوية «{ident}»، ولا جذر ولا وزن ولا أوجه', pr and pr['cls'] == cls and unicodedata.normalize('NFC', pr['identity']) == unicodedata.normalize('NFC', ident) and
          pr['ambiguous'] is False and mm['status'] == 'not_applicable' and mm.get('root') is None and not mm.get('faces'), (pr, mm and mm.get('status')))
mm = morph('سَمِنَ')
check('P2 الالتباس: سَمِنَ class_deferred، والحماية باقية على «مِنْ»، والبديل المعجمي محفوظ بلا جذرٍ مقبول',
      mm['status'] == 'class_deferred' and mm['protected']['identity'] == 'مِنْ' and mm.get('root') is None and
      any(x.get('root') == 'سمن' for x in mm['protected'].get('lexical_rivals') or []))
a = analyze(CAT, 'إِنَّ', 'auto')
check('P3 الحماية لا تمنع النحو: «إِنَّ» في الواجهة عاملٌ بلا مدخلٍ صرفي', not [x for x in a.get('morph') or [] if x.get('root')])

# ---------- M: الإفساد بكواشف مسمّاة ----------
def mutate(name, word, fn, expected):
    base = morph(word)
    orig_ok = check_face_record(word, base) == []
    mut = copy.deepcopy(base)
    fn(mut)
    changed = json.dumps(mut, ensure_ascii=False, sort_keys=True, default=str) != json.dumps(base, ensure_ascii=False, sort_keys=True, default=str)
    found = check_face_record(word, mut)
    det = sorted({d for d, _ in found})
    rec = dict(mutation=name, word=word, original_valid=orig_ok, value_actually_changed=changed, expected_detector=expected,
               actual_detector=det, mutated_rejected=bool(found))
    MUT.append(rec)
    check(f'M {name}: الأصل سليم، والقيمة تغيّرت، وكشفها {expected}', orig_ok and changed and expected in det, rec)


def sel(m):
    return next(f for f in m['faces'] if f['status'] == 'SELECTED')


mutate('الجذر', 'كَتَبْتُ', lambda m: sel(m).__setitem__('root', 'كذب'), 'IDENTITY')
mutate('الوزن', 'كَتَبْتُ', lambda m: sel(m).__setitem__('form_class', 'II'), 'IDENTITY')
mutate('الصنف', 'كَتَبْتُ', lambda m: sel(m).__setitem__('form_class', 'مصدر') or sel(m).__setitem__('analysis_id',
       analysis_id(analysis_key('كَتَبْتُ', sel(m)['root'], 'مصدر', 'فعل', sel(m)['lemma']))), 'CLASS')
mutate('هوية الوجه', 'كَتَبْتُ', lambda m: sel(m).__setitem__('analysis_id', 'A000000000000'), 'IDENTITY')
mutate('ارتباط الدليل', 'كَتَبْتُ', lambda m: sel(m).__setitem__('evidence_ids', ['HFN-E-0000000000']), 'EVIDENCE_LINK')
mutate('حالة الاختيار', 'ادَّخَرَ', lambda m: [f.__setitem__('status', 'SELECTED') for f in m['faces']], 'SELECTION')
mutate('نقل الحماية إلى وجهٍ غير محمي', 'إِنَّ', lambda m: m.update(root='ءنن', form_class='I'), 'PROTECTION')
mutate('جذرٌ مقبول لوجهٍ مؤجَّل الفئة', 'سَمِنَ', lambda m: m.update(root='سمن'), 'PROTECTION')

# ---------- R: التحقيق العكسي (الدفعة ٢) ----------
from sarf.realize import verify, realize_lemma
for root, cls, form, lemma, op in (('ضلل', 'IV', 'أَفْعَلَ', 'أَضَلَّ', 'GEMINATE_MERGE'), ('صفو', 'VIII', 'افْتَعَى (افتعل ناقص)', 'اصْطَفَى', "VIII_TA_TO_TA'"),
                                   ('ءمن', 'IV', 'أَفْعَلَ', 'آمَنَ', 'HAMZA_SEAT'), ('دعو', 'I', 'فَعَلَ (ناقص واوي)', 'دَعَا', 'WEAK_LAM'),
                                   ('ذكر', 'VIII', 'افْتَعَلَ', 'ادَّكَرَ', 'VIII_TA_TO_DAL_ASSIMILATED'), ('وقي', 'VIII', 'افْتَعَى (افتعل ناقص)', 'اتَّقَى', 'VIII_FA_ASSIMILATED_TO_TA')):
    r = verify(root, cls, form, lemma)
    check(f'R1 {lemma}: يُعاد من {root}+{form} بالعملية {op}', r['status'] == 'MATCHED' and op in r['operations'], r)
r = realize_lemma('قول', 'I', 'فَعَلَ')
check('R2 الأجوف غير المعلّم: بديلان (قَوَلَ، قَالَ) لا اختيار', sorted(x['form'] for x in r['alternatives']) == sorted(['قَوَلَ', 'قَالَ']), r)
r = verify('بءر', 'VIII', 'افْتَعَلَ', 'ابْتَءَرَ')
check('R3 همزةٌ بلا كرسيّ في الهدف: حالةٌ مسمّاة لا مطابقة', r['status'] == 'MISMATCH_HAMZA_SEAT_ONLY' and r['matched'] is False, r)
r = verify('كتب', 'I', 'فَعَلَ', 'كَذَبَ')
check('R4 الهدف مختلف: MISMATCH بالموضع، لا إخفاء بتجريد', r['status'] == 'MISMATCH' and r['differences'] and r['differences'][0]['position'] == 1, r)
mm = morph('آمَنَ')
f = next(x for x in mm['faces'] if x['root'] == 'ءمن' and x['form_class'] == 'IV')
check('R5 نجاح التحقيق لا يثبت الاختيار: آمَنَ يتحقق ويبقى مؤجَّلاً (لا دليل فعلية بالكتابة)', f['realization']['lemma']['status'] == 'MATCHED' and
      mm['status'] == 'deferred' and f['status'] == 'LICENSED')
f = sel(morph('كَتَبْتُ'))
check('W1 أهداف الوزن: الميزان مختار، والمتحقق صيغة لمّة، ووزن الكلمة غير مغطّى، والعائلة ليست وزناً مختاراً',
      f['patterns']['lemma_pattern']['status'] == 'SELECTED' and f['patterns']['lemma_realized_pattern']['status'] == 'RETRIEVED' and
      f['patterns']['word_pattern']['status'] == 'NOT_COVERED' and f['patterns']['form_family']['status'] == 'FAMILY_NOT_A_SELECTED_WAZN')
mutate('القالب (صيغة HFN)', 'كَتَبْتُ', lambda m: sel(m).__setitem__('hfn_forms', ['فَعَّلَ']), 'REALIZATION')
mutate('العملية الصرفية', 'ادَّخَرَ', lambda m: sel(m)['realization']['lemma'].__setitem__('operations', ['SUBSTITUTE']), 'REALIZATION')
mutate('علامة التصريف (حكم الكلمة الداخلة)', 'كَتَبْتُ', lambda m: sel(m)['realization']['word'].__setitem__('status', 'MATCHED'), 'INFLECTION')
# (دخر + افتعل يُعاد هو أيضاً «ادَّخَرَ»: التباسٌ حقيقي لا يكشفه التحقيق، فالمُفسِد جذرٌ يُعاد بغير الكلمة)
mutate('الجذر (بالتحقيق)', 'ادَّخَرَ', lambda m: sel(m).__setitem__('root', 'ذكر'), 'REALIZATION')
from sarf.face_check import check_verse_entry
a = analyze(CAT, 'تَبَرَّكَ', 'auto')
e = a['morph'][0]
ok0 = check_verse_entry('تَبَرَّكَ', e, 'تَبَرَّ') == []
e2 = copy.deepcopy(e)
e2['peeled_face']['span'] = 'بَرَّكَ'
det = sorted({d for d, _ in check_verse_entry('تَبَرَّكَ', e2, 'تَبَرَّ')})
rec = dict(mutation='حدود التقشير', word='تَبَرَّكَ', original_valid=ok0, value_actually_changed=e2 != e, expected_detector='SEGMENTATION',
           actual_detector=det, mutated_rejected=bool(det))
MUT.append(rec)
check('M حدود التقشير: الأصل سليم، وتغيّر الجزء، وكشفه SEGMENTATION', ok0 and 'SEGMENTATION' in det, rec)

# ---------- X: عابرة للطبقات ----------
a = analyze(CAT, 'تَبَرَّكَ', 'auto')
x = a['morph'][0]
check('X1 analyze: تَبَرَّكَ مؤجَّل، ووجه القطع محفوظاً «مرخَّصاً غير مختار»، والمنافس بهويته', x['status'] == 'deferred' and
      x['peeled_face']['status'] == 'LICENSED_NOT_SELECTED' and x['whole_word_rivals'][0]['analysis_id'].startswith('A') and x.get('analysis_id') is None)
a = analyze(CAT, 'وَقَالَتْ', 'auto')
x = a['morph'][0]
check('X2 analyze: وَقَالَتْ مقبول بوجهٍ واحد ذي هوية، بلا منافس', x['status'] == 'accepted' and x['analysis_id'] and not x.get('whole_word_rivals'))

json.dump(MUT, open(os.environ.get('AR02_MUTATIONS_OUT', '/dev/null'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('نجح' if not FAILS else f'فشل {len(FAILS)}: {FAILS}')
sys.exit(1 if FAILS else 0)
