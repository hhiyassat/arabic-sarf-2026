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
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
