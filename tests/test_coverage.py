#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فحص السجل يمسك ما يُخفي النقص: كل مرتبةٍ بلا ما يثبتها، وكل إشارةٍ إلى ما لا يوجد، وكل بابٍ غائب.

    python3 tests/test_coverage.py
"""
import copy, os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H + 'tools')
import check_coverage as cc

bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

rows, cl = cc.load(cc.REG), __import__('json').load(open(cc.CHK, encoding='utf-8'))
errs, _, _ = cc.check(rows, cl)
check('السجل الحالي سليم', not errs, errs[:5])

def caught(name, mutate, want):
    R, C = copy.deepcopy(rows), copy.deepcopy(cl)
    mutate(R, C)
    e, _, _ = cc.check(R, C)
    check(name, any(want in x for x in e), e[:3])

first = lambda R, st: next(r for r in R if r['status'] == st)
caught('«مختبَر» بلا اختبار', lambda R, C: first(R, 'tested').pop('tests'), 'بلا «tests»')
caught('«مختبَر» بلا نطاق', lambda R, C: first(R, 'tested').pop('scope'), 'بلا «scope»')
caught('نصّ فحصٍ غير موجود في ملفه', lambda R, C: first(R, 'tested').__setitem__('tests', ['tests/test_core.py::فحصٌ لا وجود له']), 'غير موجود في')
caught('ملف اختبارٍ غير موجود', lambda R, C: first(R, 'tested').__setitem__('tests', ['tests/لا_وجود.py']), 'ملف الاختبار غير موجود')
caught('«القرآن كله» بلا قياس', lambda R, C: (lambda r: (r.__setitem__('scope', 'القرآن كله'), r.pop('measurement', None)))(first(R, 'tested')),
       'بلا قياسٍ مسجَّل')
caught('مفتاح قياسٍ غير موجود', lambda R, C: first(R, 'tested').__setitem__('measurement', ['reports/algebra_metrics.json#counts.لا_وجود']), 'غير موجود في')
caught('«منفَّذ» برمزٍ غير معرَّف', lambda R, C: first(R, 'implemented').__setitem__('code', ['sarf/core.py:لا_وجود']), 'غير معرَّف')
caught('«منفَّذ» بلا شيفرة', lambda R, C: first(R, 'implemented').pop('code'), 'بلا «code»')
caught('«غير ممثَّل» ومعه شيفرة', lambda R, C: first(R, 'unrepresented').__setitem__('code', ['sarf/core.py']), 'ومعه «code»')
caught('«منفَّذ» ومعه اختبار: المرتبة أعلى من المعلنة', lambda R, C: first(R, 'implemented').__setitem__('tests', ['tests/test_core.py']), 'ومعه «tests»')
caught('«قاعدة غير منفَّذة» بلا قاعدة', lambda R, C: first(R, 'rule_written').pop('rule'), 'بلا «rule»')
caught('«ممثَّل» بلا تمثيل', lambda R, C: first(R, 'represented').pop('representation'), 'بلا «representation»')
caught('حذف بابٍ من السجل وهو في قائمة الحصر', lambda R, C: R.remove(next(r for r in R if r['topic'] == 'اسم التفضيل')), 'غائبٌ عن السجل')
caught('مرحلةٌ بلا أي سطر', lambda R, C: [R.remove(r) for r in [r for r in R if r['stage'] == 25]], 'بلا أي سطر')
caught('معرّفٌ مكرَّر', lambda R, C: R.append(copy.deepcopy(R[0])), 'مكرَّر')
caught('حالةٌ غير معروفة', lambda R, C: R[0].__setitem__('status', 'شبه منجز'), 'حالةٌ غير معروفة')
caught('حقلٌ غير معروف', lambda R, C: R[0].__setitem__('done', True), 'حقولٌ غير معروفة')
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
