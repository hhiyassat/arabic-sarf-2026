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
C = collections.Counter(); bad = collections.defaultdict(list); excluded = []
WEAK = set('ويءا')
ROMAN = {str(i): r for i, r in enumerate(['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII'])}
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
        if not G.closed or not G.Theta.get('R'):
            continue
        route = ('فعل' if (G.Theta.get('F') or {}).get('kind') != 'اسم' else
                 'اسم فاعل/مفعول قياساً' if str(G.Theta.get('P', '')).startswith('اسم') else
                 'بناء سيبويه' if str(G.Theta.get('P', '')).startswith('بناء سيبويه') else 'مدخل معجمي (مصدر وغيره)')
        if route == 'فعل':
            C['فعل: مغلق'] += 1
        if wi not in amap:
            C['غير مقارن: الكلمة لا تقابل كلمةً في QAC'] += 1
            if route == 'فعل':
                C['فعل: الوزن غير مقارن: الكلمة لا تقابل كلمةً في QAC'] += 1
            excluded.append(f'{s}:{v} {G.O["text"]} (الكلمة لا تقابل كلمةً في QAC)')
            continue
        qsegs = Q[(s, v, amap[wi])]
        roots = [f[5:].translate(HZ) for _, _, fs in qsegs for f in fs if f.startswith('ROOT:')]
        if not roots:
            # لا جذر في QAC (علمٌ أعجمي، أو مبني): لا يُعدّ خلافاً ولا وفاقاً
            C['غير مقارن: لا جذر للكلمة في QAC'] += 1
            if route == 'فعل':
                C['فعل: الوزن غير مقارن: لا جذر في QAC'] += 1
            excluded.append(f'{s}:{v} {G.O["text"]} (لا جذر في QAC)')
            continue
        C[route] += 1
        ours = G.Theta['R']
        if ours == roots[0]:
            C[route + ' ✓'] += 1
            # الوزن أيضاً (للفعل): وزن QAC (VF) مقابل وزن الجبر؛ فالجذر وحده لا يثبت صحة الوزن
            vf = next((f[3:] for _, t, fs in qsegs if t == 'V' for f in fs if f.startswith('VF:')), None)
            if route == 'فعل' and not vf:
                C['فعل: الوزن غير مقارن: لا وزن (VF) في QAC'] += 1
            if route == 'فعل' and vf:
                C['فعل: الوزن مقارن'] += 1
                ours_f = str(G.Theta.get('P'))
                if ROMAN.get(vf) == ours_f:
                    C['فعل: الوزن موافق'] += 1
                elif len(bad['فعل: الوزن مخالف']) < 25:
                    bad['فعل: الوزن مخالف'].append(f'{s}:{v} {G.O["text"]} ours={ours_f} qac={ROMAN.get(vf, vf)}')
            continue
        g = roots[0]
        kind = ('حرف علة أو همزة (الجذر نفسه بإبدال المعتلّ)' if len(ours) == len(g) and
                all(x == y or x in WEAK and y in WEAK for x, y in zip(ours, g)) else
                'حرفٌ زائد أو سابقة عُدّ أصلاً' if len(set(ours) - set(g)) == 1 and len(set(g) - set(ours)) == 1 and
                ours[1:] == g[:-1] else
                'مضعَّفٌ أو مكرَّر' if len(set(ours)) < len(ours) or len(set(g)) < len(g) else 'جذرٌ آخر')
        C[route + ' ✗'] += 1
        if route == 'فعل':
            C['فعل: الوزن غير مقارن: الجذر مخالف'] += 1
        C['الخلاف: ' + kind] += 1
        if len(bad[route]) < 25:
            bad[route].append(f'{s}:{v} {G.O["text"]} ours={ours} qac={g} [{kind}]')
P = os.environ.get('SARF_ALG_METRICS', H + 'reports/algebra_metrics.json')
M = json.load(open(P, encoding='utf-8'))
M['root_vs_qac'] = dict(C)
M['root_vs_qac_misses'] = dict(bad)
M['root_vs_qac_excluded'] = excluded[:40]
json.dump(M, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for r in ('فعل', 'اسم فاعل/مفعول قياساً', 'مدخل معجمي (مصدر وغيره)', 'بناء سيبويه'):
    print(r, C[r + ' ✓'], '/', C[r], f'{100 * C[r + " ✓"] / max(C[r], 1):.1f}%')
for r, xs in bad.items():
    print('==', r); print('\n'.join(xs[:12]))
