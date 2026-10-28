#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/algebra_quran.py — الجبر اللساني على المصحف كله: يبني المستويات الستة لكل آية
(خلية ≺ مقطع ≺ وحدة لفظية ≺ جملة/آية ≺ فقرة/سورة ≺ موضوع/مصحف)، ويفحص المبرهنات الخمس آليّاً
على كل وقوع، ويكتب reports/algebra_metrics.json وreports/algebra_report.html.

يحتاج data/quran_hafs.tsv، وHFN (SARF_HFN أو مساره المعتاد).
الاستعمال: python3 tools/algebra_quran.py [--limit N]
"""
import os, sys, json, argparse, collections, html

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.algebra import (Trace, sentence_geo, mushaf_layer, linguistic_layer, SENTENCE, DISCOURSE, render_sentence, render_cells, spans, flatten, build, cv,
                          Geo, Cell, LEVELS, PARAGRAPH, TOPIC)

ap = argparse.ArgumentParser()
ap.add_argument('--limit', type=int, default=0)
ap.add_argument('--reanalyze-every', type=int, default=20, help='كل كم آية يُفحص Analyze(Render(a)) ∋ a')
args = ap.parse_args()

cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
rows = [l.rstrip('\n').split('\t') for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8')]
if args.limit:
    rows = rows[:args.limit]

C = collections.Counter()
unit_reason = collections.Counter()
open_kind = collections.Counter()
close_route = collections.Counter()
fail = collections.defaultdict(list)
by_surah = collections.defaultdict(list)
samples = {}
SAMPLE_REFS = {(37, 137), (37, 138), (112, 1), (112, 2), (112, 4), (2, 282), (5, 6), (18, 60), (8, 33), (2, 283), (42, 11), (2, 173), (2, 194),
               (1, 2), (21, 57), (3, 26), (10, 59), (6, 32), (49, 10), (35, 28), (18, 110), (47, 20)}


def unit_expr(G):
    cells = G.O['cells']
    cs = ''.join(c.show() for c in cells)
    if G.Theta.get('lex') and not G.Theta.get('R'):
        return f'{G.O["text"]} = Lex[{G.Theta["lex"]}]({cs})'
    if G.closed and G.Theta.get('R'):
        sy = ' ⊕ '.join(''.join(c.show() for c in S.A) for S in G.A)
        F = G.Theta.get('F') or {}
        f = '، '.join(f'{k}={v}' for k, v in F.items() if v)
        return (f'{G.O["text"]} = Realize({" ".join(G.Theta["R"])}, {G.Theta["P"]}{"; " + f if f else ""}) = {sy}'
                f'   α=⟨{", ".join(G.Theta["alpha"])}⟩   β=⟨{" ".join(G.Theta.get("beta", []))}⟩')
    return f'{G.O["text"]} = {cs}   ⟂ معلّق: {G.O.get("deferred", "")}'


def check_verse(s, v, a, S, units, T):
    ok = {}
    # المبرهنة الأولى: حفظ الوقوعات — كل موضع رسمٍ مغطّى مرةً، وكل خلية بلغها البناء
    t1 = True
    all_ids = set()
    for G in units.values():
        txt, seen = render_cells(G.O['cells'], G.O['text'], G.O.get('orphans', ()))
        if sorted(seen) != list(range(len(spans(G.O['text'])))) or len(seen) != len(set(seen)):
            t1 = False
            fail['T1'].append(f'{s}:{v} {G.O["text"]}')
        all_ids |= {c.id for c in G.O['cells']}
    reach = {c.id for c in flatten(S)}
    if reach != all_ids:
        t1 = False
        fail['T1'].append(f'{s}:{v} خلايا لم يبلغها البناء: {len(all_ids - reach)}')
    ok['T1'] = t1
    # المبرهنة الثانية: اتساق الجذر والوزن والتقطيع في الوحدة المغلقة
    t2 = True
    for G in units.values():
        if G.tau[1] != 'مقطَّعة':
            continue
        if G.A and all(isinstance(x, Geo) for x in G.A):
            flat = [c for X in G.A for c in X.A]
            whole = not G.O.get('pending')
            C['cut_units_syllabified'] += whole
            if whole:
                C['beta_agrees'] += bool(G.Theta.get('beta_agrees'))
                if not G.Theta.get('beta_agrees') and len(fail['beta']) < 60:
                    fail['beta'].append(f'{s}:{v} {G.O["text"]} الجبر={G.Theta.get("beta")} المقطِّع={[x["cv"] for x in a["segments"][G.O["word_index"]]["units"][G.O["unit"]]["syllables"]]}')
        if G.closed:
            alpha = G.Theta.get('alpha') or []
            good = flat == G.O['cells'] and len(alpha) == len(flat) and None not in alpha
            if not good:
                t2 = False
                fail['T2'].append(f'{s}:{v} {G.O["text"]}')
    ok['T2'] = t2
    # المبرهنة الثالثة والرابعة: كل مغلقٍ بشهادتين صالحتين ولا التزام لازم مفتوح فيه
    t34 = True
    stack = [S]
    while stack:
        X = stack.pop()
        if isinstance(X, Cell):
            continue
        if X.closed and (X.ec is None or X.eb is None or not X.ec.valid() or not X.eb.valid() or X.open_required()):
            t34 = False
            fail['T3'].append(f'{s}:{v} {X.id}')
        stack.extend(X.A)
        stack.extend(x for x in X.O.get('pending', []) if isinstance(x, (Geo, Cell)))
    ok['T3'] = ok['T4'] = t34
    C['trace_ops'] += len(T)
    C['trace_extend'] += sum(1 for t in T if t['op'] == 'Extend')
    C['trace_close'] += sum(1 for t in T if t['op'] == 'Close')
    C['trace_defer'] += sum(1 for t in T if t['op'] == 'Defer')
    # المبرهنة الخامسة: Render(Analyze(x)) = x
    r = render_sentence(S, units)
    ok['T5'] = r == a['normalized']
    if not ok['T5']:
        fail['T5'].append(f'{s}:{v}')
    return ok, r


verses = []
for n, (s, v, text) in enumerate(rows):
    s, v = int(s), int(v)
    a = analyze(cat, text)
    T = Trace()
    S, units = sentence_geo(a, f'Q{s}:{v}', T)
    ok, rendered = check_verse(s, v, a, S, units, T)
    for k, x in ok.items():
        C[f'{k}_pass'] += x
    C['verses'] += 1
    for G in units.values():
        C['units'] += 1
        C['cells'] += len(G.O['cells'])
        C['syllables'] += sum(1 for X in G.A if isinstance(X, Geo))
        C['syllables_closed'] += sum(1 for X in G.A if isinstance(X, Geo) and X.closed)
        if G.closed:
            C['units_closed'] += 1
            route = ('Lex' if not G.Theta.get('R') else
                     'Realize: فعل' if (G.Theta.get('F') or {}).get('kind') != 'اسم' else
                     'Realize: اسم فاعل/مفعول' if 'اسم' in str(G.Theta.get('P', ''))[:4] else
                     'Realize: بناء سيبويه' if str(G.Theta.get('P', '')).startswith('بناء سيبويه') else 'بناء معجمي: مصدر وغيره')
            close_route[route] += 1
        else:
            unit_reason[G.O.get('deferred', '').split(':')[0]] += 1
    # Analyze(Render(a)) ∋ a على عيّنة: إعادة التحليل من النص المستخرَج تعطي الخلايا والإغلاق أنفسهما
    if args.reanalyze_every and n % args.reanalyze_every == 0:
        a2 = analyze(cat, rendered)
        S2, units2 = sentence_geo(a2, f'Q{s}:{v}', Trace())
        same = ({k: ([c.key() for c in G.O['cells']], G.closed) for k, G in units.items()} ==
                {k: ([c.key() for c in G.O['cells']], G.closed) for k, G in units2.items()})
        C['reanalyze'] += 1
        C['reanalyze_same'] += same
        if not same:
            fail['T5b'].append(f'{s}:{v}')
    lite = dict(verse=a['verse'], normalized=a['normalized'], segments=[dict(word=g['word'], units=g['units']) for g in a['segments']])
    by_surah[s].append((s, v, lite, units, S))
    if (s, v) in SAMPLE_REFS:
        samples[(s, v)] = dict(text=a['normalized'], units={G.id: unit_expr(G) for G in units.values()})
    if n % 500 == 0:
        print(n, dict(C), file=sys.stderr)

# الطبقتان على النص كله: المصحفية (كلمة ← آية ← سورة ← مصحف) واللغوية (جملة ← وحدة خطابية ← خطاب السورة)
T = Trace()
items = [x for s in sorted(by_surah) for x in by_surah[s]]
MU = mushaf_layer([(s, v, a, units) for s, v, a, units, S in items], T)
LT, st = linguistic_layer(items, T)
for k, x in st.items():
    C[k] = x
C['mushaf_closed'] = int(MU.closed)
C['mushaf_ayahs_closed'] = sum(1 for su in MU.A for ay in su.A if ay.closed)
C['speech'] = len(LT)
C['speech_closed'] = sum(1 for x in LT if x.closed)
# المبرهنة الأولى على الطبقتين: الخلايا نفسها تبلغها الطبقتان كلتاهما، ولا تزيد ولا تنقص
all_cells = {c.id for s, v, a, units, S in items for G in units.values() for c in G.O['cells']}
cm = {c.id for c in flatten(MU)}
cl = {c.id for x in LT for c in flatten(x)}
C['T1_layers'] = int(cm == all_cells == cl)
# Location: كل كلمة في المصحف تقع في وحدة خطابية واحدة بالضبط
locs = collections.Counter(loc for x in LT for D in x.A + x.O['pending'] for loc in D.O['location'])
C['T_location'] = int(all(n == 1 for n in locs.values()) and len(locs) == sum(len(a['segments']) for s, v, a, u, S in items))
for x in LT:
    for D in x.A + x.O['pending']:
        J = (D.A + D.O['pending'])[0]
        for o in J.open_required():
            open_kind[o.name.split(' ')[0]] += 1
        ay = set(D.O['ayahs'])
        if ay & set(SAMPLE_REFS):
            units = [u for u in J.A + J.O['pending']]
            ex = {}
            for (s_, v_) in ay:
                ex.update(samples.get((s_, v_), {}).get('units', {}))
            samples.setdefault('du', []).append(dict(
                id=D.id, location=[f'{l[0]}:{l[1]}:{l[2]}' for l in D.O['location']], ayahs=[f'{a}:{b}' for a, b in D.O['ayahs']],
                closed=D.closed, sentence_closed=J.closed, nuclei=J.O.get('nuclei', []),
                boundary=(D.eb.text() if D.eb else ''), units=[ex.get(u.id, u.O['text']) for u in units],
                bonds=[f'{b[1]} →[{b[0]}] {b[2]}' for b in J.B],
                open=[o.name + (f' ({o.reason})' if o.reason else '') for o in J.open_required()]))
M = dict(counts=dict(C), unit_deferred=dict(unit_reason.most_common()), sentence_open=dict(open_kind.most_common()),
         unit_closed_by=dict(close_route.most_common()), failures={k: v[:40] for k, v in fail.items()},
         samples=samples.get('du', []))
json.dump(M, open(os.environ.get('SARF_ALG_METRICS', H + 'reports/algebra_metrics.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(M['counts'], ensure_ascii=False, indent=1))
print('unit_deferred', M['unit_deferred'])
print('sentence_open', M['sentence_open'])
print('closed_by', M['unit_closed_by'])
print({k: len(v) for k, v in fail.items()})
