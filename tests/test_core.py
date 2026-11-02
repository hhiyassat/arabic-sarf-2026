#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نواة الجبر المشتركة (sarf.core): الأنواع والعمليات واحدة في المشروع كله، والمحلّل يحمل أثراً واحداً.

    python3 tests/test_core.py
"""
import os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
import sarf.core as core
import sarf.algebra as algebra
from sarf.core import Trace, Geo, Evidence, Obligation, CloseError, extend, close, defer, UNIT
from sarf.catalog import Catalog
from sarf.pipeline import Pipeline, STAGES

bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

# ١. تعريفٌ واحد: ما تستورده الطبقة اللغوية هو نفسه ما في النواة، لا نسخةٌ منه
for n in ('LEVELS', 'Evidence', 'Obligation', 'CloseError', 'Geo', 'Trace', 'extend', 'close', 'defer'):
    check(f'sarf.algebra.{n} هو sarf.core.{n}', getattr(algebra, n) is getattr(core, n))

# ٢. قوانين العمليات كما هي
T = Trace()
G = Geo('g', (UNIT, 'اختبار'), Omega=[Obligation('معمول')])
try:
    extend(G, 'x', 'r', Evidence(''), T)
    check('لا امتداد بلا دليل مكتمل', False)
except CloseError:
    check('لا امتداد بلا دليل مكتمل', True)
e = Evidence('سبب', ['شرط'], [('مانع', 'برهان انتفائه')])
try:
    close(G, e, e, T)
    check('لا إغلاق والتزامٌ لازم مفتوح', False)
except CloseError:
    check('لا إغلاق والتزامٌ لازم مفتوح', True)
extend(G, 'x', 'r', e, T, discharge=['معمول'])
close(G, e, e, T)
check('الامتداد يستوفي الالتزام، ثم يصحّ الإغلاق', G.closed and not G.open_required())
defer(Geo('h', (UNIT, 'اختبار')), T, 'سبب التأجيل')
check('الأثر يسجّل Extend ثم Close ثم Defer بالترتيب', [r['op'] for r in T] == ['Extend', 'Close', 'Defer'], [r['op'] for r in T])

# ٣. المحلّل يحمل أثراً واحداً من sarf.core، وفيه كل مرحلةٍ بترتيبها
cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
ctx = Pipeline(cat).run('بِسۡمِ ٱللَّهِ ٱلرَّحۡمَٰنِ ٱلرَّحِيمِ', until='match')
check('الأثر من نوع sarf.core.Trace', type(ctx.trace) is Trace)
check('until: الأثر يقف حيث وقف التشغيل', [r['stage'] for r in ctx.trace] == ['normalize', 'match'], list(ctx.trace))
ctx = Pipeline(cat).run('بِسۡمِ ٱللَّهِ ٱلرَّحۡمَٰنِ ٱلرَّحِيمِ', skip=('syllabify',))
check('كل مرحلة في الأثر بترتيبها، والمتجاوَزة معلَنة',
      [r['stage'] for r in ctx.trace] == [s.name for s in STAGES] and
      [r['summary'] for r in ctx.trace if r['stage'] == 'syllabify'] == ['تُجووزت'], list(ctx.trace))
check('ملخّص كل مرحلة في الأثر هو ملخّصها في السجل', [(r['stage'], r['summary']) for r in ctx.trace] == ctx.log)
check('الأثر لا يدخل ناتج analyze (الناتج كما كان)',
      'trace' not in Pipeline(cat).run('بِسۡمِ ٱللَّهِ ٱلرَّحۡمَٰنِ ٱلرَّحِيمِ').result())
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
