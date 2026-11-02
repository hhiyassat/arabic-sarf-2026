#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبارات سلوكٍ قائم لأبوابٍ كانت «منفَّذة غير مختبَرة» في سجل التغطية: تثبت ما يفعله المحلّل الآن، ولا تغيّره.

    PYTHONHASHSEED=0 python3 tests/test_behaviour.py
"""
import os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
sys.path.insert(0, H + 'tools')
from sarf.root import hfn

bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

# S06.03 مقاطع الدرج (المقطِّع السابق): همزة الوصل لا تُنطق بعد السابقة
from sarf import syllabify as legacy
check('الدرج: فَاكْتُبُوهُ = فَكْ.تُ.بُو.هُ (الوصل يسقط بعد السابقة)', [r[0] for r in legacy.run('فَاكْتُبُوهُ')['rows']] == ['فَكْ', 'تُ', 'بُو', 'هُ'])
check('الدرج: الأحداث تعدّ سقوط الوصل بعد السابقة', legacy.run('فَاكْتُبُوهُ')['events']['WASL_INTERNAL_AFTER_PROCLITIC'] == 1)

# S09.03 فئات المبنيات من الملف
from sarf.lexicon import MabniLexicon
L = MabniLexicon()
check('فئة المبني من الملف: الَّذِينَ موصول', {e['category'] for e in L.lookup('الَّذِينَ')} == {'relative'})
check('فئة المبني من الملف: هُوَ ضمير منفصل', {e['category'] for e in L.lookup('هُوَ')} == {'separate_pronoun'})

# S12.05 معاني العوامل المحتملة
from sarf.catalog import Catalog
cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
check('معاني العامل «بِ» (مج 1) محفوظةٌ كلها بلا حسم', len(cat.ops[('بِ', '1')]['meanings']) >= 2, len(cat.ops[('بِ', '1')]['meanings']))

# S20.09 المطابقة في الصلة
from sarf.algebra import _agrees, _pp_like
check('المطابقة: العدد والنوع متّفقان', _agrees(('plural', 'masc'), ('plural', 'masc')))
check('المطابقة: النوع غير المعيَّن لا يعارض', _agrees(('plural', 'masc'), ('plural', None)))
check('المطابقة: العدد المختلف يعارض', not _agrees(('plural', 'masc'), ('singular', 'masc')))
# S19.03 شبه الجملة
check('شبه الجملة: الرأس جارّ', _pp_like({'head': 'pp', 'text': 'x', 'segs': [], 'case': None}))
check('شبه الجملة: ليس الاسم المرفوع', not _pp_like({'head': None, 'text': 'كَاتِبٌ', 'segs': [('جذع', 'كَاتِبٌ')], 'case': 'رفع'}))

# S01.01 وS01.02 هوية التشغيل
import provenance
rec = provenance.identity('نص', 'سياسة')
check('هوية التشغيل: الالتزام وبصمة الشيفرة والبيانات والمدخل ومعرّف التشغيل',
      all(rec.get(k) for k in ('commit', 'code_sha', 'data_sha', 'input_sha', 'run_id')), rec)
check('هوية التشغيل: معرّف التشغيل يتغيّر بتغيّر المدخل', provenance.identity('نص آخر', 'سياسة')['run_id'] != rec['run_id'])

if hfn():
    from sarf.cells import stem_licence, cells_of, participle_analyses, _resolve_root
    # S07.07 المداخل المعجمية من HFN
    check('رخصة «دَيْن»: مدخلٌ معجمي (مصدر) في HFN', ('معجم', 'دين', 'مصدر «دَيْن»') in stem_licence('دَيْن'), stem_licence('دَيْن'))
    # S11.01 القراءة على أصلٍ معتل
    check('«وَلِيُّ»: الياء المشدَّدة ياءُ فعيل مدغمة، فالجذر ولي', any(r[1] == 'ولي' for r in stem_licence('وَلِيُّ')), stem_licence('وَلِيُّ'))
    check('«لِقَاء»: الهمزة بعد الألف بدلٌ من اللام، فالجذر لقي', _resolve_root('لقء', hfn(), False) == 'لقي')
    # S13.11 اسم المفعول
    check('مَكْتُوبٌ: اسم مفعول من كتب (I)', ('كتب', 'I', 'مفعول') in [p[:3] for p in participle_analyses(cells_of('مَكْتُوبٌ', 'q')[0])])
    from sarf.analyze import analyze
    # S13.22 المعرب والمبني: المبني معمولٌ في المحلّ
    a = analyze(cat, 'ٱلَّذِي عَلَيۡهِ ٱلۡحَقُّ')
    r = next(o['relation'] for o in a['operators'] if o['operator'] == 'عَلَى')
    check('المبني بعد الجار: في محلّ جر، لا علامة ظاهرة', r['observed'] == 'محلاً' and r['role'] == 'في محلّ جر بـ«عَلَى»', r)
    # S20.08 المفعول معه: «وَ» (مج 4) تُمنع بالرفع المكتوب بعدها
    a = analyze(cat, 'وَأَقۡوَمُ لِلشَّهَٰدَةِ')
    w4 = next(o for o in a['operators'] if o['operator'] == 'وَ' and str(o['group']) == '4')
    check('«وَ» (مج 4) تنصب المفعول معه، فالمرفوع بعدها يمنعها', w4['status'] == 'blocked' and 'المفعول معه' in w4['reject_reason'], w4)
    # S14.05 الباب
    from sarf.algebra import Trace, sentence_geo
    from sarf.features import unit_features
    a = analyze(cat, 'وَلۡيَكۡتُب بَّيۡنَكُمۡ كَاتِبُۢ بِٱلۡعَدۡلِۚ')
    _, U = sentence_geo(a, 't', Trace())
    F = unit_features(a, U)
    b = next(v['bab'] for k, v in F.items() if U[k].O['text'] == 'يَكْتُبْ')
    check('الباب: يَكْتُبْ من فَعَلَ يَفْعُلُ (a-u)', b['v'] == 'a-u' and b['st'] == 'مثبت', b)
    # S13.03 نوع المعرفة للمبني من الملف
    a = analyze(cat, 'ٱلَّذِينَ ءَامَنُواْ')
    _, U = sentence_geo(a, 't', Trace())
    F = unit_features(a, U)
    d = next(v.get('definiteness_kind') for k, v in F.items() if U[k].O['text'] == 'الَّذِينَ')
    check('نوع المعرفة للمبني: الَّذِينَ اسم موصول (ملف المبنيات)', d and d['v'] == 'معرفة: اسم موصول', d)
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
