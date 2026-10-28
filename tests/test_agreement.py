#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار T18: A(m) = { Φ(p) | R(m,p) } — سمات الفعل من توافقه مع الضمير.

    python3 tests/test_agreement.py
"""
import os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from sarf.agreement import agreement, narrow, phi
from sarf.analyze import analyze
from sarf.catalog import Catalog

CAT = Catalog([os.path.join(HERE, 'operators_catalog.jsonl'),
               os.path.join(HERE, 'operators_catalog_split_vocalized.csv')])
bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

# Φ من ملف المبنيات (دليل مستقل): الضمائر المنفصلة للرفع الاثنا عشر
P = phi()
check('Φ: اثنا عشر ضميراً للرفع', len(P) == 12, sorted(P))
check('Φ(أَنْتِ) = مخاطبة مفردة', P['أَنْتِ'] == (2, 'singular', 'fem'))

# R بقواعد التصريف ← A(m)
CASES = [
    ('يَلِدْ', ['هُوَ']), ('تَحْزَنْ', ['أَنْتَ', 'هِيَ']),            # T18: تَكْتُبُ تحليلان
    ('يَعْلَمُونَ', ['هُمْ']), ('قَالُوا', ['هُمْ']), ('كَتَبْتُ', ['أَنَا']), ('رَأَيْتَ', ['أَنْتَ']),
    ('قَالَتْ', ['هِيَ']), ('كُنْتُمْ', ['أَنْتُمْ']), ('جَعَلْنَا', ['نَحْنُ']), ('قُلْ', ['أَنْتَ']),
    ('اسْجُدِي', ['أَنْتِ']), ('يَكْتُبَانِ', ['هُمَا']),
    ('تَكْتُبُ', None),                                              # لم يثبت أنه فعل بالكتابة وحدها
]
for w, want in CASES:
    a = agreement(w)
    got = a and a['pronouns']
    check(f'A({w})', got == want, got)

# القرينة: ضمير منفصل قبله يخصّص، وما لا يوافق يُسجَّل مخالفةً ولا يُخصِّص
a = narrow(agreement('تَحْزَنْ'), 'هِيَ')
check('هِيَ تَحْزَنْ ← {هي}', a['pronouns'] == ['هِيَ'] and a['narrowed_by'] == 'هِيَ', a)
a = narrow(agreement('تَحْزَنْ'), 'هُوَ')
check('هُوَ تَحْزَنْ ← مخالفة، ويبقى التحليلان', a['conflict'] == 'هُوَ' and len(a['pronouns']) == 2, a)
a = narrow(agreement('يَعْلَمُونَ'), 'أَنْتِ')
check('أَنْتِ يَعْلَمُونَ ← مخالفة', a['conflict'] == 'أَنْتِ', a)

# في الآية: صيغة المضارع التي لم يثبت أنها فعل تثبت بالتوافق مع الضمير قبلها، ولا تثبت بغيره (لا دور)
def agr_of(text):
    return analyze(CAT, text)['agreement']
g = agr_of('أَنْتِ تَكْتُبِينَ')
check('أَنْتِ تَكْتُبِينَ: فعل بصيغته (التاء وشكل المضارع ونون الرفع)، ويُخصَّص بالضمير',
      g and not g[0].get('verb_by_agreement') and g[0]['pronouns'] == ['أَنْتِ'], g)
g = agr_of('أَنْتِ تَكْتُبِي')
check('أَنْتِ تَكْتُبِي: فعل بالتوافق', g and g[0].get('verb_by_agreement') and g[0]['pronouns'] == ['أَنْتِ'], g)
check('هُوَ تَكْتُبُ: لا توافق فلا يُحكم بالفعل', agr_of('هُوَ تَكْتُبُ') == [], agr_of('هُوَ تَكْتُبُ'))
check('تَكْتُبُ وحدها: لا حكم', agr_of('تَكْتُبُ') == [])
# المبني للمجهول من الكتابة: الفتح قبل الآخر مع ضمّ حرف المضارعة؛ والألف قبله لا تفصل (يُسَاقُ/يُرَاءُ)
for w, want in [('يُولَدْ', 'passive'), ('قُتِلُوا', 'passive'), ('يُحْبِبْ', 'active'), ('يَلِدْ', 'active'),
                ('يُسَاقُونَ', None), ('يُرَاءُونَ', None)]:
    got = agreement(w)['voice']
    check(f'الجهة: {w}', got == want, got)
check('لَتَرَوُنَّ: جمع مع نون التوكيد', agreement('تَرَوُنَّ')['pronouns'] == ['أَنْتُمْ'])
check('أَلَمْ: ليست مضارعاً', agreement('أَلَمْ') is None)
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
