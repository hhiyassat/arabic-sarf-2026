#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار القسمة على الوحدات المائة بمعيار القسمة المعتمد (Q01، T12، T14a):
18 إنشائية، و80 خبرية، و2 مؤجَّلتان (لَوْ، كَمْ). العدد ناتج الأحكام لا شرطٌ لها (T14).

    python3 tests/test_mood.py
"""
import os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarf.catalog import Catalog
from sarf.mood import op_mood, MOOD, MOOD_DEFERRED, _nfc

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = Catalog([os.path.join(HERE, 'operators_catalog.jsonl'),
               os.path.join(HERE, 'operators_catalog_split_vocalized.csv')])

bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

units = {k: op_mood(dict(operator=k[0], group=k[1])) for k in CAT.ops}
n = Counter(units.values())
check('عدد الوحدات 100', len(units) == 100, len(units))
check('إنشائي 18', n['إنشائي'] == 18, n)
check('خبري 80', n['خبري'] == 80, n)
check('مؤجَّل 2', n['مؤجَّل'] == 2, n)
# كل مفتاح في الجدولين وحدةٌ في الفهرس (لا خطأ في الصيغة أو المجموعة)
KEYS = {(_nfc(f), g) for f, g in CAT.ops}                 # ترتيب الشدة والحركة يختلف بين الفهرس والكود
check('مفاتيح الإنشائي في الفهرس', set(MOOD) <= KEYS, set(MOOD) - KEYS)
check('مفاتيح المؤجَّل في الفهرس', set(MOOD_DEFERRED) <= KEYS, set(MOOD_DEFERRED) - KEYS)
# أحكام بعينها
for form, group, want in [('نِعْمَ', '12', 'إنشائي'), ('لَيْتَ', '2', 'إنشائي'), ('لَا', '6', 'إنشائي'),
                          ('لَا', '3', 'خبري'), ('وَ', '1', 'خبري'), ('تَ', '1', 'خبري'),
                          ('لَعَلَّ', '2', 'خبري'), ('عَسَى', '11', 'خبري'), ('رُبَّ', '1', 'خبري'),
                          ('هَيْهَاتَ', '9', 'خبري'), ('لَوْ', '7', 'مؤجَّل'), ('كَمْ', '8', 'مؤجَّل')]:
    got = op_mood(dict(operator=form, group=group))
    check(f'{form} (مج {group}) {want}', got == want, got)
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
