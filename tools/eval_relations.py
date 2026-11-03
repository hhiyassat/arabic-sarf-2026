#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/eval_relations.py — عقد النواة الاسمية والتعلّق (v1) على المصحف كله: سجلات العلاقات بأنواعها وحالاتها،
وفحصها البنيوي (sarf.relations.check_records)، وعيّنات؛ وصفحة HTML لآيةٍ بمواضعها.

    PYTHONHASHSEED=0 python3 tools/eval_relations.py [--jobs N] [--verse 2:282] [--out reports/nominal_nucleus_01]
"""
import argparse, collections, html, json, os, sys, multiprocessing as mp

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
sys.path.insert(0, os.path.join(H, 'tools'))
from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.algebra import Trace, sentence_geo
from sarf.features import unit_features
from sarf.relations import verse_relations, check_records

CAT = Catalog([os.path.join(H, 'operators_catalog.jsonl'), os.path.join(H, 'operators_catalog_split_vocalized.csv')])


def verses():
    for l in open(os.path.join(H, 'data', 'quran_hafs.tsv'), encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 3 and p[0].isdigit():
            yield int(p[0]), int(p[1]), p[2]


def rel_of(t):
    s, v, text = t
    a = analyze(CAT, text)
    _, U = sentence_geo(a, f'Q{s}:{v}', Trace())
    out = verse_relations(a, U, unit_features(a, U), f'{s}:{v}')
    return f'{s}:{v}', out, check_records(out['records'], out['tokens'])


def one(t):
    k, out, errs = rel_of(t)
    C, ex = collections.Counter(), {}
    for r in out['records']:
        key = f"{r['type']}|{r['rule_id']}|{r['status']}"
        C[key] += 1
        ex.setdefault(key, f"{k}: {' / '.join(f'{x}=«{y}»' for x, y in r['texts'].items())} — {r['reason'][:100]}")
        if r['type'] == 'ATTACH':
            C['ATTACH:hosts'] += len(r['alternatives'])
            C['ATTACH:search_incomplete'] += r.get('search_status') == 'SEARCH_INCOMPLETE'
    return C, ex, [f'{k}: {e}' for e in errs]


def page(ref, out, errs, ident):
    rows = []
    for r in out['records']:
        rows.append('<tr><td>{}</td><td>{} {}</td><td class="st {}">{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td><code>{}</code></td></tr>'.format(
            html.escape(r['type']), r['rule_id'], r['rule_version'], r['status'].lower(), r['status'],
            '<br>'.join(f"{html.escape(k)}: <span class='ar'>{html.escape(v)}</span> <small>({'، '.join(r['positions'][k])})</small>"
                        for k, v in r['texts'].items()),
            html.escape(r['reason']), '<br>'.join(html.escape(str(p))[:160] for p in r['premises']),
            '<br>'.join(html.escape(a if isinstance(a, str) else f"{a['host_kind']}: «{a['host_text']}» ({a['host_position']}) — {a['status']}")
                        for a in r['alternatives']) or '—',
            html.escape(r['relation_id'])))
    flags = 'nucleus_complete / clause_complete / boundary_proven / sentence_closed مستقلةٌ عن حالة العلاقة'
    return f'''<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>علاقات {ref}</title><style>body{{font-family:system-ui,"Noto Naskh Arabic",sans-serif;margin:16px;line-height:1.7;background:#fff;color:#222}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:4px 6px;vertical-align:top;font-size:14px}}th{{background:#f2f2f2}}
.ar{{font-size:17px}}.st.licensed{{background:#e6f4ea}}.st.deferred{{background:#fff7e0}}.st.rejected{{background:#fde8e8}}.st.conflict{{background:#efe6fb}}
code{{font-size:11px;direction:ltr;unicode-bidi:embed}}</style>
<h1>عقد النواة الاسمية والتعلّق (v1): {ref}</h1>
<p>هوية التشغيل: <code>{html.escape(json.dumps(ident, ensure_ascii=False))}</code></p>
<p>الفحص البنيوي: {'سليم' if not errs else html.escape('؛ '.join(errs))}. {flags}. وكل حالة «مرخّصة» علاقةٌ محلية في وجهها، لا اختيارٌ نهائي ولا إغلاق جملة.</p>
<table><tr><th>النوع</th><th>القاعدة</th><th>الحالة</th><th>الأطراف (بمواضعها)</th><th>السبب</th><th>المقدّمات</th><th>البدائل والمضيفون</th><th>المعرّف</th></tr>
{''.join(rows)}</table></html>'''


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--verse', default='2:282')
    ap.add_argument('--out', default=os.path.join(H, 'reports', 'nominal_nucleus_01'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    import provenance
    V = list(verses())
    with mp.get_context('fork').Pool(a.jobs) as P:
        R = P.map(one, V, chunksize=20)
    C, ex, errs = collections.Counter(), {}, []
    for c, e, er in R:
        C.update(c); errs += er
        for k, x in e.items():
            ex.setdefault(k, x)
    s, v = map(int, a.verse.split(':'))
    vt = next(t for t in V if t[0] == s and t[1] == v)
    ident = provenance.identity(vt[2], 'عقد النواة الاسمية والتعلّق v1')
    k, out, verrs = rel_of(vt)
    json.dump(dict(identity=ident, verses=len(V), counts=dict(sorted(C.items())), examples=ex, check_errors=errs[:200],
                   check_error_count=len(errs), verse=dict(ref=k, records=out['records'], tokens=out['tokens'], check=verrs)),
              open(os.path.join(a.out, 'measurement.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(a.out, f'index.html'), 'w', encoding='utf-8').write(page(k, out, verrs, {x: ident[x] for x in ('run_id', 'commit', 'dirty', 'hfn_path', 'hfn_sha', 'code_sha')}))
    for key, n in sorted(C.items()):
        print(n, key)
    print('check errors:', len(errs), errs[:5])
