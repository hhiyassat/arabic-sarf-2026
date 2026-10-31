#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار بوابة الحماية الدستورية (CLAUDE.md §١): لا جذر للعوامل المائة ولا للمبنيات ولا للأسماء الذهبية،
بصيغها وسوابقها وضمائرها، قبل توليد مرشّحات الجذر؛ والملتبس يُحفظ بديله وتُؤجَّل فئته.

    python3 tests/test_protected.py
"""
import os, sys
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
os.chdir(H)
from sarf.protected import protected, NOT_APPLICABLE, REASON
from sarf.root import morph
from sarf.chars import letters


def same(a, b):
    return [(L, frozenset(m)) for L, m in letters(a or '')] == [(L, frozenset(m)) for L, m in letters(b or '')]

bad = 0


def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)


def ident(w):
    p = protected(w)
    return p and (p['identity'], p['proclitics'], p['enclitic'], p['ambiguous'])


# العوامل الفعلية بتصريفها وسوابقها
for w, idn in [('وَلَسْتُمْ', 'لَيْسَ'), ('لَسْتُنَّ', 'لَيْسَ'), ('لَيْسَتِ', 'لَيْسَ'), ('كُنْتُمْ', 'كَانَ'), ('فَكَانُوا', 'كَانَ'),
               ('لَكَانُوا', 'كَانَ'), ('وَّكَانُوا', 'كَانَ'), ('تَكُونَنَّ', 'كَانَ'), ('يَكُ', 'كَانَ'), ('يَكَادُ', 'كَادَ'),
               ('عَسَى', 'عَسَى'), ('نِعْمَ', 'نِعْمَ')]:
    p = protected(w)
    check(f'«{w}» عاملٌ محمي «{idn}»', p and same(p['identity'], idn) and not p['ambiguous'], ident(w))
# أفعال القلوب: الحماية مرشّحة والفئة مؤجَّلة
for w in ('عَلِمَ', 'يَعْلَمُونَ', 'أَفَرَأَيْتُمْ', 'وَجَدْتُّمُوهُمْ'):
    p = protected(w)
    check(f'«{w}» فعلٌ قلبيّ: محمي مرشّح، والفئة مؤجَّلة', p and p['ambiguous'], ident(w))
# الأسماء الذهبية بحركات الإعراب والنداء والسوابق
for w in ('إِبْرَٰهِيمُ', 'إِبْرَٰهِيمَ', 'يَٰٓإِبْرَٰهِيمُ', 'لِإِبْرَٰهِيمَ', 'وَإِسْحَٰقَ', 'دَاوُۥدُ', 'يَٰدَاوُۥدُ', 'مُحَمَّدٌ', 'ٱللَّهُ', 'وَلِلَّهِ'):
    p = protected(w)
    check(f'«{w}» اسمٌ ذهبي', p and p['cls'] == 'اسم ذهبي', ident(w))
# المبنيات والأدوات بضمائرها
for w, idn in [('إِنَّا', 'إِنَّ'), ('إِنِّي', 'إِنَّ'), ('لَعَلَّكُمْ', 'لَعَلَّ'), ('عَلَيْهِمْ', 'عَلَى'), ('فِيهِنَّ', 'فِي'),
               ('مِّنِّي', 'مِنْ'), ('مِمَّا', 'مِمَّا'), ('لَقَدْ', 'لَقَدْ'), ('فَقَدْ', 'قَدْ'), ('أَوَلَمْ', 'لَمْ'),
               ('أَيُّهَا', 'أَيُّهَا'), ('وَهُوَ', 'هُوَ'), ('أُلَٰئِكَ', 'أُولَاءِكَ')]:
    p = protected(w)
    check(f'«{w}» محمي بهويته «{idn}»', p and same(p['identity'], idn), ident(w))
# لا حماية لما ليس منها (الحركات معاً: لا تجريد)
for w in ('كَتَبَ', 'قَالَ', 'فَقَعُوا', 'تَهِنُوا', 'نَصِيرًا', 'لَعَنَّا', 'أَمِنَ', 'نِعْمَتَ', 'ابْتَلَى', 'ءَامَنَّا', 'كَلَٰمَ',
          'وَأَمْنًا', 'سَأَلَكَ'):
    check(f'«{w}» ليس وحدةً محمية', protected(w) is None, ident(w))
# البوابة قبل مرشّحات الجذر
m = morph('وَلَسْتُمْ')
check('morph(وَلَسۡتُمۡ): NOT_APPLICABLE بلا مرشّحات جذرية', m['status'] == 'not_applicable' and
      m['root_status'] == NOT_APPLICABLE and m['reason'] == REASON and not m['candidates'], m)
m = morph('عَلِمَ')
check('morph(عَلِمَ): class_deferred، والبديل محفوظ ولا جذر مقبول', m['status'] == 'class_deferred' and m['root'] is None
      and m.get('alternative'), m.get('status'))
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
