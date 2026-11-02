#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مصدرٌ واحد لمقاطع الوحدات (sarf.syllables): الخلايا ومقاطعها ورسمها، وحركة همزة الوصل، والتطابق مع المقطِّع السابق.

    python3 tests/test_syllables.py
"""
import os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.syllables import unit_syllables, render, cv, wasl_vowel
from sarf import syllabify as legacy
import sarf.algebra as algebra
import sarf.syllables as syllables

bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

def syl(t, end=True):
    _, S, st, _ = unit_syllables(t, word_end=end)
    return [render(G) for G in S], [cv(G) for G in S], st

for n in ('syllabify', 'rem_M', 'cv', 'SYLLABLE_SHAPES'):
    check(f'sarf.algebra.{n} هو sarf.syllables.{n}', getattr(algebra, n) is getattr(syllables, n))
check('فَاكْتُبُوهُ = فَكْ.تُ.بُو.هُ', syl('فَاكْتُبُوهُ')[:2] == (['فَكْ', 'تُ', 'بُو', 'هُ'], ['CVC', 'CV', 'CVV', 'CV']), syl('فَاكْتُبُوهُ'))
check('اكْتُبُو: همزة الوصل تُضمّ ابتداءً (ءُكْ)', syl('اكْتُبُو')[0][0] == 'ءُكْ', syl('اكْتُبُو'))
check('التنوين يُرسم بشكله (مُسَمًّى = مُ.سَمْ.مً)', syl('مُّسَمًّى')[0] == ['مُ', 'سَمْ', 'مً'], syl('مُّسَمًّى'))
check('«ى» الساكنة ياءٌ صامتة (شَىْءٌ = شَيْ.ءٌ)', syl('شَىْءٌ')[0] == ['شَيْ', 'ءٌ'], syl('شَىْءٌ'))
check('«ى» بعد الكسرة ياء مدّ (نِى = نِي)', syl('نِى')[0] == ['نِي'], syl('نِى'))
check('حركة همزة الوصل: الفتح قبل «أل»', wasl_vowel('الْحَقُّ') == 'a')
check('حركة همزة الوصل: الضم إن سكن الأول وضُمّ الثاني ضمةً قصيرة', wasl_vowel('اكْتُبْ') == 'u')
check('حركة همزة الوصل: الكسر في افْتَعَلَ', wasl_vowel('اتَّقُوا') == 'i')
check('مسألةٌ مسجَّلة (S06.04): القاعدة الخطّية تكسر «ادْعُوا»، والصواب الضم', wasl_vowel('ادْعُوا') == 'i')
check('لا وصل في أول الوحدة: None', wasl_vowel('كَتَبَ') is None)
ev = unit_syllables('الرَّحْمَٰنِ')[3]
check('أدوار الخلايا معدودة: همزة وصل، واللام الشمسية لا تُنطق، والشدة خليتان',
      ev['همزة وصل'] == 1 and ev['لا يُنطق: لام شمسية'] == 1 and ev['شدة: الأول'] == 1, dict(ev))
check('CVCC لا يقع داخل الكلمة', syl('قَالْتْ', False)[1] == ['CVVC'], syl('قَالْتْ', False))
for w in ('فَاكْتُبُوهُ', 'الرَّحْمَٰنِ', 'مُّسَمًّى', 'يَسْتَطِيعُ', 'تُدِيرُونَهَا', 'وَامْرَأَتَانِ', 'لِلشَّهَٰدَةِ', 'شَىْءٌ', 'نِى', 'اتَّبِعُو'):
    old = [(r[0], r[1]) for r in legacy.run(w)['rows']]
    new = list(zip(*syl(w)[:2]))
    check(f'يطابق المقطِّع السابق: {w}', old == new, (old, new))
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
