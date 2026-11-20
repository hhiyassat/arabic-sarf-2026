#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
قوالب أبنية سيبويه: الملاحظة بين قوسين و«/» لا تدخل خلايا القالب (إصلاح 2026-11-21).
كان sibawayh_patterns يأخذ pattern_vocalized كما هو، فدخلت حروف «(رباعي)» و«(جمع)» و«/» خلايا 25 قالباً.

    python3 tests/test_sibawayh_template_notes.py
"""
import os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.cells import cells_of, sibawayh_patterns, sibawayh_analyses, template_variants

bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

P = sibawayh_patterns()
check('298 قالباً (295 سجلاً، وثلاثة منها ببديلين)', len(P) == 298, len(P))
check('لا خلية قالبٍ من حروف الملاحظة ولا «/» ولا فراغ',
      not [p[0] for p in P if any(t[0] in '()/ ' for t in p[3])])
check('template_variants: الملاحظة تُحذف', template_variants('فُعْلُولٌ (رباعي)') == ['فُعْلُولٌ'])
check('template_variants: البديلان يُفصلان', template_variants('مَفَاعِلُ/مَفَاعِيلُ') == ['مَفَاعِلُ', 'مَفَاعِيلُ'])
check('template_variants: القالب النظيف كما هو', template_variants('فَعْلٌ') == ['فَعْلٌ'])
ids = {}
for p in P:
    ids.setdefault(p[0], []).append(p[2])
check('S060 قالبان: مَفَاعِلُ ومَفَاعِيلُ', ids.get('S060') == ['مَفَاعِلُ', 'مَفَاعِيلُ'], ids.get('S060'))
check('S344 فُعْلُولٌ بلا «(رباعي)»', ids.get('S344') == ['فُعْلُولٌ'], ids.get('S344'))


def sib(w):
    cs, _ = cells_of(w, 't')
    return {(a[1], a[0]) for a in sibawayh_analyses(cs)}


# كلماتٌ لم يكن يطابقها قالبها قبل الإصلاح
check('مَصَابِيحُ ← S060 مَفَاعِيلُ (صبح)', ('S060', 'صبح') in sib('مَصَابِيحُ'), sib('مَصَابِيحُ'))
check('مَسَاجِدُ ← S060 مَفَاعِلُ (سجد)', ('S060', 'سجد') in sib('مَسَاجِدُ'), sib('مَسَاجِدُ'))
check('عُصْفُورٌ ← S344 فُعْلُولٌ (عصفر)', ('S344', 'عصفر') in sib('عُصْفُورٌ'), sib('عُصْفُورٌ'))
check('أَصْدِقَاءُ ← S044 أَفْعِلَاءُ (صدق)', ('S044', 'صدق') in sib('أَصْدِقَاءُ'), sib('أَصْدِقَاءُ'))
# الألف المقصورة في القالب لا تطابق ألف المدّ
check('مَوْتَى ← S095 فَعْلَى (موت)', ('S095', 'موت') in sib('مَوْتَى'), sib('مَوْتَى'))
check('جَنَّٰتٍ لا تطابق فَعْلَى (ألف مدٍّ لا مقصورة)', not {s for s, _ in sib('جَنَّٰتٍ')} & {'S095', 'S098'},
      sib('جَنَّٰتٍ'))
check('كل خلية «ى» في القالب ألفٌ مقصورة', all(t[3] in (None, 'ى') for p in P for t in p[3]))
# قالبٌ نظيف لم يتغيّر
check('عَنَاكِبُ ← S084 كما كان', ('S084', 'عكب') in sib('عَنَاكِبُ'), sib('عَنَاكِبُ'))

print('FAIL' if bad else 'PASS', bad)
sys.exit(1 if bad else 0)
