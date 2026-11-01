#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ترقيم الخلية ⟨حرف، حالة⟩ برقمٍ واحد من 1 إلى 116 (حكم صاحب النظرية): Code = 4(i − 1) + j + 1،
الحروف ا1 … ي28 ء29، والحالة: السكون 0، الفتحة 1، الكسرة 2، الضمة 3؛ وحرف المدّ خليةٌ بلا حركة.

    python3 tests/test_numbering.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarf.numbering import code, LETTER_NO, decode, cell_code

CASES = [
    ('كَ', '86'),
    ('يَكْ', '110 85'),               # السكون حالةٌ (j = 0)
    ('قَا', '82 1'),                  # الألف خليةٌ بلا حركة ⟨ا، ∅⟩ = 1
    ('لُو', '92 105'),                # الواو المدية ⟨و، ∅⟩
    ('قِي', '83 109'),                # الياء المدية ⟨ي، ∅⟩
    ('يَوْ', '110 105'),
    ('شَيْ', '50 109'),
    ('نٍ', '99ن'),                    # التنوين: الحالة موسومةً، بلا نون
    ('مً', '94ن'),
    ('ءَلْ', '114 89'),               # الهمزة 29
    ('أَ', '114'),                    # وصورها كلها 29
    ('ةُ', '12'),                     # التاء المربوطة تاء
    ('عَٰ', '70 1'),                  # الألف الخنجرية ألف
    ('آ', '114 1'),                   # همزة ومدّة
    ('رَبِّ', '38 5 7'),              # المشدَّد خليتان أولاهما ساكنة
]

bad = 0
check_letters = len({n for L, n in LETTER_NO.items() if L in 'ابتثجحخدذرزسشصضطظعغفقكلمنهويء'}) == 29
print('OK ' if check_letters else 'BAD', 'تسعة وعشرون حرفاً: الألف إلى الياء ثم الهمزة')
bad += not check_letters
codes = {cell_code(i, v) for i in range(1, 30) for v in (None, 'َ', 'ِ', 'ُ')}
ok116 = codes == set(range(1, 117)) and all(decode(c) == (decode(c)[0], decode(c)[1]) for c in codes)
print('OK ' if ok116 else 'BAD', '116 رقماً متباينة، من 1 إلى 116، ويُسترجع منها الحرف والحالة')
bad += not ok116
for src, want in CASES:
    got = code(src)
    ok = got == want
    bad += not ok
    print('OK ' if ok else 'BAD', src, '' if ok else f'→ {got} (المتوقَّع {want})')
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
