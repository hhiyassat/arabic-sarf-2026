#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/eval_case.py — صحة الحالة المكتوبة (word_case) التي تُبنى عليها قواعد الخبر والمفعول والتابع عبر الحدّ:
تُقارَن بحالة الاسم في مدوّنة QAC (NOM/ACC/GEN) على المصحف كله.
"""
import os, sys, re, difflib, collections, json
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.algebra import word_case

cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
Q = collections.defaultdict(list)
for l in open(H + 'data/quran-morphology.txt', encoding='utf-8'):
    loc, form, tag, feats = l.rstrip('\n').split('\t')
    s, v, w, k = map(int, loc.split(':'))
    Q[(s, v, w)].append((form, tag, feats.split('|')))
def skel(t):
    t = re.sub('[ً-ٰٟۖ-ࣰۭ-ࣲـ]', '', t)
    return t.translate(str.maketrans('ٱأإآؤئىة', 'اااااييه')).replace('ء', '')
MAP = {'NOM': 'رفع', 'ACC': 'نصب', 'GEN': 'جر'}
C = collections.Counter(); bad = []
for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'):
    s, v, text = l.rstrip('\n').split('\t'); s, v = int(s), int(v)
    a = analyze(cat, text)
    qws = sorted(k[2] for k in Q if k[0] == s and k[1] == v)
    qtext = [skel(''.join(f for f, _, _ in Q[(s, v, w)])) for w in qws]
    otext = [skel(seg['word']) for seg in a['segments']]
    amap = {}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, otext, qtext, autojunk=False).get_opcodes():
        if op in ('equal', 'replace') and i2 - i1 == j2 - j1:
            for k in range(i2 - i1):
                amap[i1 + k] = qws[j1 + k]
    verbs = {g['word_index'] for g in a.get('agreement', [])}
    for wi in range(len(a['segments'])):
        c = word_case(a, wi, verbs)
        if not c or wi not in amap:
            continue
        gold = [MAP[f] for _, tag, fs in Q[(s, v, amap[wi])] if tag == 'N' for f in fs if f in MAP]
        if not gold:
            C['no_gold'] += 1
            continue
        C['n'] += 1
        ok = gold[-1] == c or c == 'جر أو نصب' and gold[-1] in ('جر', 'نصب')
        C['ok'] += ok
        if not ok and len(bad) < 40:
            bad.append(f'{s}:{v} {a["segments"][wi]["word"]} ours={c} qac={gold[-1]}')
print(dict(C), f'{100 * C["ok"] / max(C["n"], 1):.2f}%')
print('\n'.join(bad))
P = H + 'reports/quran_metrics.json'
M = json.load(open(P, encoding='utf-8')) if os.path.exists(P) else {}
M['case'] = dict(C)
json.dump(M, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
