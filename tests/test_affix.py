#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبارات مقشِّر الزوائد (sarf.affix) ونفي المرشَّح بالكتابة المبني عليه (sarf.evidence).

    python3 tests/test_affix.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarf.affix import stem_info
from sarf.catalog import Catalog
from sarf.pipeline import Pipeline

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPE = Pipeline(Catalog([os.path.join(HERE, 'operators_catalog.jsonl'),
                         os.path.join(HERE, 'operators_catalog_split_vocalized.csv')]))

# (الجذع، النوع، الصيغة، علامة الآخر، اللاحقة)
STEMS = [
    ('يَكْتُبْ', 'verb', 'mudari', 'جزم', None),
    ('يَعْلَمُونَ', 'verb', 'mudari', 'رفع', 'نون الرفع'),
    ('أَكِيدَنَّ', 'verb', 'mudari', 'مبني', 'نون التوكيد'),
    ('تَقُولُوا', 'verb', 'mudari', 'حذف النون', 'وا'),
    ('امْسَحُوا', 'verb', 'amr', None, 'وا'),
    ('قَالُوا', 'verb', 'madi', None, 'وا'),
    ('تَدَايَنْتُمْ', 'verb', 'madi', None, 'تُمْ'),
    ('يُعَذِّبَهُمْ', None, 'mudari', 'نصب', None),          # بلا دليل قاطع على الفعل
    ('نَبِيُّونَ', None, 'mudari', 'رفع', 'نون الرفع'),      # نون الرفع مع النون تلتبس بجمع الاسم
    ('دَيْنٍ', 'noun', None, None, None),
    ('الْعَدْلِ', 'noun', None, None, None),
    ('مَوْتِ', None, None, None, None),                      # التاء بعد ساكن ليست ضمير رفع
    ('أَنْتَ', None, None, None, None),                      # ضمير منفصل
]

# (النص، العامل، المجموعة، الحكم)
REJECT = [
    ('وَٱمْسَحُوا۟', 'وَ', '1', 'rejected'),
    ('وَلَمْ يُولَدْ', 'وَ', '4', 'rejected'),
    ('وَأَنتَ فِيهِمْ', 'وَ', '1', 'rejected'),
    ('وَلْيَكْتُبْ', 'لِ', '6', 'candidate'),                # لام الأمر بعد الواو
    ('وَتَٱللَّهِ', 'تَ', '1', 'candidate'),                  # تاء القسم بعد الواو
    ('لَأَكِيدَنَّ', 'لِ', '1', 'rejected'),                 # اللام المفتوحة قبل الفعل
    ('لَكُمْ', 'لِ', '1', 'candidate'),
    ('لَا يَعْلَمُونَ', 'لَا', '6', 'rejected'),
    ('لَا رَيْبَ', 'لَا', '6', 'rejected'),
    ('لَا تَحْزَنْ', 'لَا', '6', 'candidate'),
    ('كَانُوا۟', 'كَانَ', '10', 'candidate'),                 # كان مع واو الجماعة
]

bad = 0
for text, pos, kind, mood, suf in STEMS:
    i = stem_info(text)
    got = (i['pos'], i['kind'], i['mood'], i['suffix'])
    ok = got == (pos, kind, mood, suf)
    bad += not ok
    print('OK ' if ok else 'BAD', text, got if not ok else '')
for text, op, grp, want in REJECT:
    ops = PIPE.run(text, until='evidence').candidates
    got = next((f['status'] for f in ops if f['operator'] == op and f['group'] == grp), 'absent')
    ok = got == want
    bad += not ok
    print('OK ' if ok else 'BAD', text, op, grp, got if not ok else '')
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
