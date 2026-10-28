#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
الجبر اللساني: التعريفات والمبرهنات على أمثلة بعينها (تجربة على الفرع experiment).

    python3 tests/test_algebra.py
"""
import os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.algebra import (Trace, Geo, Evidence, Obligation, CloseError, extend, close, cells_of, render_cells,
                          syllabify, cv, align_alpha, flatten, equal_under, proj_root, proj_cells, sentence_geo,
                          render_sentence, SENTENCE, UNIT)
from sarf.root import hfn

bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

T = Trace()

# الخلايا وβ: كَتَّبَ = ⟨ك,a⟩⟨ت,∅⟩⟨ت,a⟩⟨ب,a⟩، والمقاطع كَتْ.تَ.بَ
cells, _ = cells_of('كَتَّبَ', 'k')
check('Cells(كَتَّبَ)', [c.key() for c in cells] == [('ك', 'a', 1), ('ت', '∅', 1), ('ت', 'a', 1), ('ب', 'a', 1)],
      [c.show() for c in cells])
S, stray = syllabify(cells, 'k', T)
check('β(كَتَّبَ) = كَتْ.تَ.بَ', [cv(x) for x in S] == ['CVC', 'CV', 'CV'] and not stray, [cv(x) for x in S])
check('Flatten(β) = الخلايا', [c for x in S for c in x.A] == cells)
check('خليتا الشدة وقوعان مختلفان من موضع رسم واحد',
      cells[1].id != cells[2].id and cells[1].O['tok'] == cells[2].O['tok'])
# α: ⟨r1, r2, r2, r3⟩
alpha, ops = align_alpha(cells, 'كتب', 'II', 'madi')
check('α(كَتَّبَ) = ⟨r1, r2, r2, r3⟩', alpha == ['r1', 'r2', 'r2', 'r3'], alpha)
# كَاتَبَ: الألف طول في القالب
c2, _ = cells_of('كَاتَبَ', 'k2')
alpha2, _ = align_alpha(c2, 'كتب', 'III', 'madi')
check('α(كَاتَبَ) = ⟨r1, r2, r3⟩ والألف طولُ r1', alpha2 == ['r1', 'r2', 'r3'] and c2[0].L == 2, alpha2)
check('كَتَبَ لا يطابق قالب فَاعَلَ (لا طول)', align_alpha(cells_of('كَتَبَ', 'k3')[0], 'كتب', 'III', 'madi')[0] is None)

# المساواة من جهة: Root(كَتَبَ) = Root(كَاتَبَ)، والخلايا مختلفة
g1 = Geo('a', (UNIT, 't'), A=cells_of('كَتَبَ', 'a')[0], Theta=dict(R='كتب'))
g2 = Geo('b', (UNIT, 't'), A=c2, Theta=dict(R='كتب'))
check('Root(كَتَبَ) = Root(كَاتَبَ)', equal_under(proj_root, g1, g2))
check('Cells(كَتَبَ) ≠ Cells(كَاتَبَ)', not equal_under(proj_cells, g1, g2))

# المبرهنة الرابعة: لا إغلاق بلا شهادتين، ولا مع التزام لازم مفتوح، ولا امتداد بلا دليل
G = Geo('g', (UNIT, 't'), Omega=[Obligation('هوية اللفظ')])
for name, fn in [('إغلاق بلا شهادة حدّ', lambda: close(G, Evidence('x', ['y']), None, T)),
                 ('إغلاق مع التزام لازم مفتوح', lambda: close(G, Evidence('x', ['y']), Evidence('z', ['w']), T)),
                 ('امتداد بلا سبب', lambda: extend(G, cells[0], None, Evidence(''), T)),
                 ('امتداد بوحدة غير مغلقة', lambda: extend(G, Geo('h', (UNIT, 't')), 'r', Evidence('x', ['y']), T))]:
    try:
        fn()
        check(name + ': مرفوض', False, 'قُبل')
    except CloseError:
        check(name + ': مرفوض', True)

# Render: الرسم يعود كما كان، والحرف الذي لا يُنطق يحفظه O
for w in ['ٱلصَّلَوٰةَ', 'قَالُوا', 'يُسْرًا', 'مُّسَمًّى', 'السَّمِيعُ']:
    from sarf.normalize import uthmani_normalize
    t = uthmani_normalize(w)
    cs, _ = cells_of(t, 'r')
    check(f'Render(Cells({t})) = {t}', render_cells(cs, t)[0] == t, render_cells(cs, t)[0])
check('ٱلصَّلَوٰةَ: الواو كرسيّ ألف، فاللام طويلة',
      [c.show() for c in cells_of(uthmani_normalize('ٱلصَّلَوٰةَ'), 'r')[0]][3] == '⟨ل,aː⟩')

# في الآية: لَمۡ يَلِدۡ وَلَمۡ يُولَدۡ تُغلق جملةً، وRender يعيدها
if hfn():
    from sarf.analyze import analyze
    from sarf.catalog import Catalog
    cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
    a = analyze(cat, 'لَمْ يَلِدْ وَلَمْ يُولَدْ')
    Sg, units = sentence_geo(a, 'Q112:3', Trace())
    check('لَمۡ يَلِدۡ وَلَمۡ يُولَدۡ: الجملة مغلقة', Sg.closed and Sg.level == SENTENCE,
          [o.name for o in Sg.open_required()])
    check('Render(الآية) = النص', render_sentence(Sg, units) == a['normalized'])
    rel = sorted(b[0] for b in Sg.B)
    check('علاقاتها: جزمان وإسنادان', rel.count('إسناد') == 2 and sum('مجزوم' in r for r in rel) == 2, rel)
    a = analyze(cat, 'فَلْيَكْتُبْ بَّيْنَكُمْ كَاتِبٌۢ بِٱلْعَدْلِ')
    Sg, units = sentence_geo(a, 'v', Trace())
    k = next(G for G in units.values() if G.O['text'] == 'كَاتِبٌ')
    check('كَاتِبٌ = Realize(ك ت ب، اسم فاعل من فَعَلَ)', k.closed and k.Theta['R'] == 'كتب' and 'فاعل' in k.Theta['P'],
          k.O.get('deferred'))
    check('ما لم يُغلق محفوظ: كل خلية يبلغها البناء',
          {c.id for c in flatten(Sg)} == {c.id for G in units.values() for c in G.O['cells']})
    check('والجملة غير المكتملة مؤجَّلة لا مغلقة', not Sg.closed and Sg.open_required())
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
