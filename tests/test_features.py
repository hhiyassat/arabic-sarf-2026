#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_features.py — مراحل الصرف (sarf/features.py): لكل سمةٍ شاهدٌ يثبتها، وحالةٌ مضادة لا يجوز أن تثبت فيها.
    python3 tests/test_features.py
"""
import os, sys
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
os.chdir(H)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.algebra import Trace, sentence_geo
from sarf.features import unit_features, noun_suffix, PROVEN, CAND, DEFER

bad = 0


def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)


cat = Catalog(['operators_catalog.jsonl', 'operators_catalog_split_vocalized.csv'])
ROWS = {(int(x[0]), int(x[1])): x[2] for x in (l.rstrip('\n').split('\t')
                                                 for l in open('data/quran_hafs.tsv', encoding='utf-8'))}


def feats(ref):
    a = analyze(cat, ROWS[ref])
    _, units = sentence_geo(a, f'Q{ref[0]}:{ref[1]}', Trace())
    F = unit_features(a, units)
    return {units[k].O['text']: v for k, v in sorted(F.items())}, F, units


def st(rec, f):
    return (rec.get(f) or {}).get('st'), (rec.get(f) or {}).get('v')


# ١. اللاحقة المكتوبة بالحروف والحركات معاً
check('ـُونَ جمع مذكر سالم', noun_suffix('خَٰلِدُونَ')[:2] == ('plural', 'sound_masc'))
check('ـَٰت بالألف الخنجرية جمع مؤنث سالم', noun_suffix('جَنَّٰتٍ')[:2] == ('plural', 'sound_fem'))
check('جمع المؤنث لا يُنصب بالفتحة: أَمَاتَ ليس جمعاً', noun_suffix('أَمَاتَ') is None, noun_suffix('أَمَاتَ'))
check('ـَيْنِ مثنى', noun_suffix('رَجُلَيْنِ')[0] == 'dual')

# ٢. آية الدَّين: الفعل وفاعله ووزنه وتعدّيه، والاسم وعدده وجنسه وتعريفه
W, F, U = feats((2, 282))
r = W['تَدَايَنْتُمْ']
check('تَدَايَنْتُمْ: ماضٍ مثبت', st(r, 'tense') == (PROVEN, 'ماضٍ'), r.get('tense'))
check('تَدَايَنْتُمْ: الفاعل أنتم مثبت', st(r, 'subject') == (PROVEN, dict(person=2, number='plural', gender='masc')))
check('تَدَايَنْتُمْ: مزيد على تَفَاعَلَ', r['augmentation']['st'] == PROVEN and r['augmentation']['v']['form'] == 'VI')
r = W['اكْتُبُو']
check('فَاكْتُبُوهُ: متعدٍّ مثبت بضمير المفعول المكتوب', st(r, 'transitivity') == (PROVEN, 'متعدٍّ'), r.get('transitivity'))
r = W['يَكْتُبَ']
check('أَنْ يَكْتُبَ: باب نَصَرَ (a-u) من عين الماضي في HFN وعين المضارع المكتوبة', st(r, 'bab') == (PROVEN, 'a-u'), r.get('bab'))
r = W['كَاتِبٌ']
check('كَاتِبٌ: مفرد مذكر نكرة مثبتة', st(r, 'number') == (PROVEN, 'singular') and st(r, 'gender') == (PROVEN, 'masc')
      and st(r, 'definiteness') == (PROVEN, 'نكرة'), r)
r = W['الْعَدْلِ']
check('الْعَدْلِ: معرفة بأل مثبتة', st(r, 'definiteness') == (PROVEN, 'معرفة'))
check('الْعَدْلِ: المصدر لا يثبت إفراده بالقالب (قد يوافق قالب جمع)', r['number']['st'] != PROVEN, r['number'])

# ٣. التاء المربوطة: علامة تأنيثٍ لفظية لا تثبت الإفراد ولا جنس المسمّى
W, F, U = feats((2, 30))
r = next(v for k, v in W.items() if 'مَلَٰئِكَة' in k)
check('لِلْمَلَٰئِكَةِ: التاء علامةٌ مثبتة', st(r, 'fem_marker') == (PROVEN, True), r)
check('لِلْمَلَٰئِكَةِ: الإفراد غير مثبت (جمع تكسير)', r['number']['st'] != PROVEN, r['number'])
check('لِلْمَلَٰئِكَةِ: الجنس غير مثبت', r['gender']['st'] != PROVEN, r['gender'])
W, F, U = feats((2, 25))
r = W['مُّطَهَّرَةٌ']
check('مُّطَهَّرَةٌ: قالب اسم المفعول وتاء التأنيث: مفردٌ مؤنث مثبت', st(r, 'number') == (PROVEN, 'singular')
      and st(r, 'gender') == (PROVEN, 'fem'), r)
r = W['جَنَّٰتٍ']
check('جَنَّٰتٍ: جمع مؤنث', st(r, 'number')[1] == 'plural' and st(r, 'plural_type')[1] == 'sound_fem', r)
r = W['هُمْ']
check('هُمْ: الغائبون الذكور من ملف المبنيات', st(r, 'person') == (PROVEN, 3) and st(r, 'number') == (PROVEN, 'plural')
      and st(r, 'gender') == (PROVEN, 'masc'), r)
r = W['رُزِقُوا']
check('رُزِقُوا: مجهول مثبت', st(r, 'voice') == (PROVEN, 'مجهول'))

# ٤. الزمن: «وا» يشترك فيه الماضي والأمر والمضارع المحذوف النون
W, F, U = feats((3, 28))
r = W['تَتَّقُوا']
check('أَنْ تَتَّقُوا: الزمن لا يثبت ماضياً («أَنْ» تدخل على الماضي أيضاً، و«وا» مشترك)',
      not (r['tense']['st'] == PROVEN and r['tense']['v'] == 'ماضٍ'), r['tense'])
W, F, U = feats((2, 24))
r = next(v for k, v in W.items() if k.startswith('تَفْعَلُو'))
check('لَمْ تَفْعَلُوا: «لَمْ» لا تدخل إلا على المضارع: مضارع مثبت', st(r, 'tense') == (PROVEN, 'مضارع'), r['tense'])
W, F, U = feats((5, 75))
r = W['يَأْكُلَانِ']
check('يَأْكُلَانِ: المثنى الغائب بالياء مذكر', st(r, 'subject') == (PROVEN, dict(person=3, number='dual', gender='masc')),
      r['subject'])

# ٥. «ءَالِهَة»: قالب فَاعِل يلتبس بأَفْعِلَة بعد اجتماع الهمزتين
W, F, U = feats((6, 19))
r = next((v for k, v in W.items() if 'ءَالِهَة' in k), None)
check('ءَالِهَةً: الإفراد غير مثبت', r is not None and r['number']['st'] != PROVEN, r and r['number'])

# ٦. لا تثبت سمةٌ للاسم إن لم تثبت اسميته
W, F, U = feats((2, 282))
bad_ = [k for k, v in W.items() if v.get('pos', {}).get('st') != PROVEN and v.get('pos', {}).get('alt')
        and any(x.get('st') == PROVEN for f, x in v.items() if f != 'pos')]
check('لا سمة مثبتة لاسمٍ لم تثبت اسميته', not bad_, bad_)
# ٧. كل سمة بحالةٍ من الأربع، ولكل مرشّحٍ أو مؤجَّلٍ دليلٌ أو بدائل
allst = {x['st'] for v in F.values() for x in v.values()}
check('الحالات من الأربع وحدها', allst <= {PROVEN, CAND, DEFER, 'غير منطبق'}, allst)

# ٨. الفعلية بشهادة HFN حيث لا تكفي الكتابة وحدها (sarf/pipeline.py _lexical_verbs)، وحالاتها المضادة
W, F, U = feats((2, 282))
for w in ('يَسْتَطِيعُ', 'تُذَكِّرَ', 'يُعَلِّمُ', 'عَلَّمَ', 'يَأْبَ', 'يُمْلِلِ', 'يَتَّقِ', 'تَرْضَوْنَ'):
    check(f'{w}: فعلٌ مثبت (آية الدَّين)', st(W[w], 'pos') == (PROVEN, 'فعل'), W[w].get('pos'))
for w in ('أَقْسَطُ', 'أَقْوَمُ'):
    check(f'{w}: اسم التفضيل لا يثبت فعلاً (أَفۡعَلُ)', W[w]['pos']['v'] != 'فعل', W[w]['pos'])
check('يُمِلَّ: معلوم (حركة العين المنقولة إلى الفاء في المضعَّف)', st(W['يُمِلَّ'], 'voice') == (PROVEN, 'معلوم'), W['يُمِلَّ']['voice'])
for w in ('رَجُلَيْنِ', 'شَهِيدَيْنِ', 'امْرَأَتَانِ'):
    check(f'{w}: اسمٌ مثنى مثبت', st(W[w], 'pos') == (PROVEN, 'اسم') and st(W[w], 'number') == (PROVEN, 'dual'),
          (W[w].get('pos'), W[w].get('number')))
check('امْرَأَتَانِ: مؤنث مثبت بتاء التأنيث قبل لاحقة التثنية', st(W['امْرَأَتَانِ'], 'gender') == (PROVEN, 'fem'))
check('رَجُلَيْنِ: الجنس بلا علامة مكتوبة لا يثبت (سماعي)', W['رَجُلَيْنِ']['gender']['st'] != PROVEN, W['رَجُلَيْنِ']['gender'])
W, F, U = feats((2, 9))
r = next((v for k, v in W.items() if k.startswith('أَنْفُس')), None)
check('أَنْفُسَ: «أ» في أوله لا تثبت المضارع (أَفۡعُل)', r is not None and r['pos']['v'] != 'فعل', r and r['pos'])
W, F, U = feats((2, 130))
r = next((v for k, v in W.items() if k.startswith('نَفْس')), None)
check('نَفْسَ: لها رخصة اسم، فلا تثبت فعلاً', r is not None and r['pos']['v'] != 'فعل', r and r['pos'])
W, F, U = feats((3, 37))
r = next((v for k, v in W.items() if k.startswith('تَقَبَّلَ')), None)
check('تَقَبَّلَ: ماضٍ (التاء من قالب تَفَعَّلَ)، لا مضارع', r is not None and r['tense']['v'] == 'ماضٍ', r and r.get('tense'))
W, F, U = feats((2, 48))
r = W.get('تَجْزِي')
check('تَجْزِي: الياء لام الجذر، فالفاعل لا يثبت «أنتِ»', r is not None and r['subject']['st'] != PROVEN, r and r.get('subject'))

# ٩. تدقيق آية الدَّين الثاني: «لا» الناهية بالجزم المكتوب، والجذع مع ضميره المفصول، والعوامل الفعلية أفعالاً
from sarf.pipeline import Pipeline as _P
_ctx = _P(cat).run(ROWS[(2, 282)])
_c = {(c['word_index'] + 1, c['operator'], c['group']): c['status'] for c in _ctx.candidates}
check('وَلَا يَبۡخَسۡ: «لا» الناهية مقبولة (الجزم المكتوب ينفي النافية)', _c.get((31, 'لَا', '6')) == 'accepted', _c.get((31, 'لَا', '6')))
check('أَنۡ تَكۡتُبُوهُ: «أن» مقبولة (حذف النون مع الضمير المفصول)', _c.get((80, 'أَنْ', '5')) == 'accepted', _c.get((80, 'أَنْ', '5')))
_g = {g['word_index'] + 1: g for g in _ctx.agreement}
for w in (81, 107):
    check(f'2:282:{w}: «تَكۡتُبُو» مع ضميره فعلٌ فاعله «أنتم»', w in _g and _g[w]['pronouns'] == ['أَنْتُمْ'], _g.get(w))
W, F, U = feats((2, 282))
for w in ('كَانَ', 'لَيْسَ'):
    r = W.get(w)
    check(f'{w}: فعلٌ ماضٍ مثبت بالجرد، بلا جذر', r is not None and st(r, 'pos') == (PROVEN, 'فعل') and st(r, 'tense') == (PROVEN, 'ماضٍ')
          and r['augmentation']['st'] == 'غير منطبق', r)
from sarf.affix import plural_waw_host
check('يَدۡعُو: الناقص لا يُعدّ واو جماعة', not plural_waw_host('يَدْعُو'))
check('تَرُدُّو: المضعَّف بحرفين ثانيهما مشدَّد', plural_waw_host('تَرُدُّو'))
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
