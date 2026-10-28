#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/eval_algebra.py — صحة ما أغلقه الجبر: جذر كل وحدة مغلقة بـRealize أو بالبناء المعجمي يُقارَن بجذر QAC،
بحسب طريق الإغلاق. يكتب النتيجة في reports/algebra_metrics.json (المفتاح root_vs_qac).
"""
import os, sys, json, re, difflib, collections
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.algebra import sentence_geo, Trace

cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
Q = collections.defaultdict(list)
for l in open(H + 'data/quran-morphology.txt', encoding='utf-8'):
    loc, form, tag, feats = l.rstrip('\n').split('\t')
    s, v, w, k = map(int, loc.split(':'))
    Q[(s, v, w)].append((form, tag, feats.split('|')))
def skel(t):
    t = re.sub('[ً-ٰٟۖ-ࣰۭ-ࣲـ]', '', t)
    return t.translate(str.maketrans('ٱأإآؤئىة', 'اااااييه')).replace('ء', '')
HZ = str.maketrans('أإؤئآ', 'ءءءءء')
C = collections.Counter(); bad = collections.defaultdict(list)
for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'):
    s, v, text = l.rstrip('\n').split('\t'); s, v = int(s), int(v)
    a = analyze(cat, text)
    S, units = sentence_geo(a, 'x', Trace())
    qws = sorted(k[2] for k in Q if k[0] == s and k[1] == v)
    qtext = [skel(''.join(f for f, _, _ in Q[(s, v, w)])) for w in qws]
    otext = [skel(seg['word']) for seg in a['segments']]
    amap = {}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, otext, qtext, autojunk=False).get_opcodes():
        if op in ('equal', 'replace') and i2 - i1 == j2 - j1:
            for k in range(i2 - i1):
                amap[i1 + k] = qws[j1 + k]
    for (wi, ui), G in units.items():
        if not G.closed or not G.Theta.get('R') or wi not in amap:
            continue
        route = ('فعل' if (G.Theta.get('F') or {}).get('kind') != 'اسم' else
                 'اسم فاعل/مفعول قياساً' if str(G.Theta.get('P', '')).startswith('اسم') else
                 'بناء سيبويه' if str(G.Theta.get('P', '')).startswith('بناء سيبويه') else 'مدخل معجمي (مصدر وغيره)')
        roots = [f[5:].translate(HZ) for _, _, fs in Q[(s, v, amap[wi])] for f in fs if f.startswith('ROOT:')]
        C[route] += 1
        if roots and G.Theta['R'] == roots[0]:
            C[route + ' ✓'] += 1
        elif len(bad[route]) < 25:
            bad[route].append(f'{s}:{v} {G.O["text"]} ours={G.Theta["R"]} qac={roots[:1]}')
P = os.environ.get('SARF_ALG_METRICS', H + 'reports/algebra_metrics.json')
M = json.load(open(P, encoding='utf-8'))
M['root_vs_qac'] = dict(C)
M['root_vs_qac_misses'] = dict(bad)
json.dump(M, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for r in ('فعل', 'اسم فاعل/مفعول قياساً', 'مدخل معجمي (مصدر وغيره)', 'بناء سيبويه'):
    print(r, C[r + ' ✓'], '/', C[r], f'{100 * C[r + " ✓"] / max(C[r], 1):.1f}%')
for r, xs in bad.items():
    print('==', r); print('\n'.join(xs[:12]))
