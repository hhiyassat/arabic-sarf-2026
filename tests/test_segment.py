#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبارات المقشِّر (sarf.segment): الخانات وأنواعها، وشرط الفصل، والعامل ← المعمول.
كل حالة هنا قاعدة حسمها صاحب النظرية.

    python3 tests/test_segment.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarf.catalog import Catalog
from sarf.pipeline import Pipeline

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPE = Pipeline(Catalog([os.path.join(HERE, 'operators_catalog.jsonl'),
                         os.path.join(HERE, 'operators_catalog_split_vocalized.csv')]))


def units(text, wi=0):
    """→ [(نص الوحدة، وسمها أو مقاطعها)] للكلمة wi"""
    seg = PIPE.run(text).segments[wi]
    return [(u['text'], ' . '.join(s['syl'] for s in u['syllables']) if u['kind'] == 'معرب' else u['label'])
            for u in seg['units']]

def relation(text, op):
    ctx = PIPE.run(text)
    r = next(r for r in ctx.relations if r['operator'] == op)
    t = r['target']
    return (t['text'] if t else None, r['expected'], r['observed'], r['consistent'])

CASES = [
    # العامل والمبني لا يُقطَّعان، والضمير المتصل خانة مستقلة
    ('فِيهِمْ', [('فِي', 'عامل'), ('هِمْ', 'مبني')]),
    ('عَلَيْهِ', [('عَلَيْ', 'عامل'), ('هِ', 'مبني')]),
    ('إِلَيْنَا', [('إِلَيْ', 'عامل'), ('نَا', 'مبني')]),
    ('لَكُمْ', [('لَ', 'عامل'), ('كُمْ', 'مبني')]),
    ('بِأَنَّهُمْ', [('بِ', 'عامل'), ('أَنَّ', 'عامل'), ('هُمْ', 'مبني')]),
    # المعرب وحده يُقطَّع
    ('بِدَيْنٍ', [('بِ', 'عامل'), ('دَيْنٍ', 'دَيْ . نٍ')]),
    ('بِرُءُوسِكُمْ', [('بِ', 'عامل'), ('رُءُوسِ', 'رُ . ءُو . سِ'), ('كُمْ', 'مبني')]),
    ('لِيُعَذِّبَهُمْ', [('لِ', 'عامل'), ('يُعَذِّبَ', 'يُ . عَذْ . ذِ . بَ'), ('هُمْ', 'مبني')]),
    # لا فصل إذا بدأت الخانة التالية بساكن
    ('فَلْيَكْتُبْ', [('فَلْ', 'مبني+عامل'), ('يَكْتُبْ', 'يَكْ . تُبْ')]),
    ('وَٱمْسَحُوا۟', [('وَامْسَحُوا', 'وَمْ . سَ . حُو')]),
    ('بِٱلْعَدْلِ', [('بِالْ', 'عامل+مبني'), ('عَدْلِ', 'عَدْ . لِ')]),
    # أل خانة مبنية، والشمسية: نصف الشدة الأول لأل
    ('ٱلْعَدْلِ', [('الْ', 'مبني'), ('عَدْلِ', 'عَدْ . لِ')]),
    ('ٱلنَّاسِ', [('ال', 'مبني'), ('نَّاسِ', 'نَا . سِ')]),
    # المبني من المعجم كلمةً كاملة
    ('ٱلَّذِينَ', [('الَّذِينَ', 'مبني')]),
    ('أَنَا۠', [('أَنَا', 'مبني')]),
    # كان مع ضمير الرفع: [كُنْ: عامل][تُمْ: مبني]
    ('كُنْتُمْ', [('كُنْ', 'عامل'), ('تُمْ', 'مبني')]),
    # التنوين علامة إعراب: أَجَلٍ ليس «أَجَلْ» المبنية
    ('أَجَلٍ', [('أَجَلٍ', 'ءَ . جَ . لٍ')]),
    # لفظ الجلالة لا يُقطَّع، والعامل قبله خانة
    ('لِلَّهِ', [('لِ', 'عامل'), ('لَّهِ', 'لفظ الجلالة')]),
]

RELATIONS = [
    ('عَلَيْهِ', 'عَلَى', ('هِ', 'جر', 'محلاً', None)),
    ('بِدَيْنٍ', 'بِ', ('دَيْنٍ', 'جر', 'جر', True)),
    ('كُنْتُمْ', 'كَانَ', ('تُمْ', 'رفع', 'محلاً', None)),
    ('إِنَّ ٱللَّهَ غَفُورٌ', 'إِنَّ', ('اللَّهَ', 'نصب', 'نصب', True)),
    ('إِلَى ٱلْمَوْتِ', 'إِلَى', ('مَوْتِ', 'جر', 'جر', True)),
    ('إِنَّمَا', 'إِنَّ', (None, None, None, None)),               # مكفوفة
]

bad = 0
for text, want in CASES:
    got = units(text)
    ok = got == want
    bad += not ok
    print('OK ' if ok else 'BAD', text, got if not ok else '')
for text, op, want in RELATIONS:
    got = relation(text, op)
    ok = got == want
    bad += not ok
    print('OK ' if ok else 'BAD', text, op, got if not ok else '')
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
