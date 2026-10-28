#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ترقيم المقطع بالأرقام (تجربة على الفرع experiment): الحروف ء1 … ي28 والألف خارجها،
والفتحة 29 والضمة 30 والكسرة 31 والسكون 0؛ والمد الحركة مكرَّرة، والتنوين الحركة ثم نون ساكنة.

    python3 tests/test_numbering.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarf.numbering import code, LETTER_NO

CASES = [
    ('كَ', '22 29'),
    ('يَكْ', '28 29 22 0'),           # السكون 0
    ('قَا', '21 29 29'),              # الألف فتحتان
    ('لُو', '23 30 30'),              # الواو المدية ضمتان
    ('قِي', '21 31 31'),              # الياء المدية كسرتان
    ('يَوْ', '28 29 27 0'),           # الواو بعد الفتحة حرف
    ('شَيْ', '13 29 28 0'),           # والياء كذلك
    ('نٍ', '25 31 25 0'),             # التنوين: الحركة ثم نون ساكنة
    ('مً', '24 29 25 0'),
    ('ءَلْ', '1 29 23 0'),            # الهمزة 1
    ('أَ', '1 29'),                   # وصورها كلها 1
    ('ةُ', '3 30'),                   # التاء المربوطة تاء
    ('عَٰ', '18 29 29'),              # الألف الخنجرية مدّ
    ('آ', '1 29 29'),                 # همزة ومدّة
    ('رَبِّ', '10 29 2 0 2 31'),      # المشدَّد حرفان أولهما ساكن
]

bad = 0
check_letters = len({n for L, n in LETTER_NO.items() if L in 'ءبتثجحخدذرزسشصضطظعغفقكلمنهوي'}) == 28
print('OK ' if check_letters else 'BAD', 'ثمانية وعشرون حرفاً من الهمزة إلى الياء')
bad += not check_letters
for src, want in CASES:
    got = code(src)
    ok = got == want
    bad += not ok
    print('OK ' if ok else 'BAD', src, '' if ok else f'→ {got} (المتوقَّع {want})')
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
