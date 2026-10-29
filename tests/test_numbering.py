#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ترقيم المقطع بالأرقام (تجربة على الفرع experiment): الحروف ا1 … ي28 ثم ء29،
والفتحة 30 والضمة 31 والكسرة 32 والسكون 0؛ والمد الحركة مكرَّرة، والتنوين الحركة موسومةً بـ«ن».

    python3 tests/test_numbering.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarf.numbering import code, LETTER_NO

CASES = [
    ('كَ', '22 30'),
    ('يَكْ', '28 30 22 0'),           # السكون 0
    ('قَا', '21 30 30'),              # الألف فتحتان
    ('لُو', '23 31 31'),              # الواو المدية ضمتان
    ('قِي', '21 32 32'),              # الياء المدية كسرتان
    ('يَوْ', '28 30 27 0'),           # الواو بعد الفتحة حرف
    ('شَيْ', '13 30 28 0'),           # والياء كذلك
    ('نٍ', '25 32ن'),                 # التنوين: الحركة موسومةً، بلا نون
    ('مً', '24 30ن'),
    ('ءَلْ', '29 30 23 0'),           # الهمزة 29
    ('أَ', '29 30'),                  # وصورها كلها 29
    ('ةُ', '3 31'),                   # التاء المربوطة تاء
    ('عَٰ', '18 30 30'),              # الألف الخنجرية مدّ
    ('آ', '29 30 30'),                # همزة ومدّة
    ('رَبِّ', '10 30 2 0 2 32'),      # المشدَّد حرفان أولهما ساكن
]

bad = 0
check_letters = len({n for L, n in LETTER_NO.items() if L in 'ابتثجحخدذرزسشصضطظعغفقكلمنهويء'}) == 29
print('OK ' if check_letters else 'BAD', 'تسعة وعشرون حرفاً: الألف إلى الياء ثم الهمزة')
bad += not check_letters
for src, want in CASES:
    got = code(src)
    ok = got == want
    bad += not ok
    print('OK ' if ok else 'BAD', src, '' if ok else f'→ {got} (المتوقَّع {want})')
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
