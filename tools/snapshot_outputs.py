#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/snapshot_outputs.py — ثبات الناتج بين نسختين: تفريغٌ كامل لكل آية، ومقارنة «الاحتواء».

  dump: لكل آية ناتج analyze() والوحدات الجبرية (النوع، Θ، الإغلاق، سبب التأجيل) والجمل والأثر والسمات، مضغوطاً.
  cmp:  كل قيمةٍ في الأساس موجودةٌ بعينها في الجديد (مخالفة = قيمةٌ تغيّرت أو حُذفت أو تغيّر طول قائمة)،
        والحقول الجديدة تُعدّ بمساراتها إضافةً معلنة. ويخرج بغير الصفر إن وُجدت مخالفة.

    PYTHONHASHSEED=0 python3 tools/snapshot_outputs.py dump <جذر الشيفرة> <ملف.pkl.gz> [--jobs N] [--verses 2:282,1:1]
    python3 tools/snapshot_outputs.py cmp <الأساس.pkl.gz> <الجديد.pkl.gz> [--json تقرير.json]

يحتاج PYTHONHASHSEED=0 (لا تُستعمل -I، فهي تتجاهله فيتغيّر ترتيب المجموعات بين تشغيلين).
"""
import argparse, collections, gzip, json, os, pickle, sys


def canon(x):
    if isinstance(x, dict):
        return {k if isinstance(k, str) else repr(k): canon(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [canon(v) for v in x]
    if isinstance(x, (set, frozenset)):
        return sorted(repr(canon(v)) for v in x)
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    return repr(x)


def _verses(root, only):
    out = []
    for l in open(os.path.join(root, 'data', 'quran_hafs.tsv'), encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 3 and p[0].isdigit() and (not only or f'{p[0]}:{p[1]}' in only):
            out.append((int(p[0]), int(p[1]), p[2]))
    return out


_CTX = {}


def _one(t):
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo
    from sarf.features import unit_features
    s, v, text = t
    a = analyze(_CTX['cat'], text)
    T = Trace()
    S, units = sentence_geo(a, f'Q{s}:{v}', T)
    F = unit_features(a, units)
    U = {k: dict(tau=G.tau, Theta=G.Theta, closed=G.closed, deferred=G.O.get('deferred'), text=G.O.get('text'))
         for k, G in units.items()}
    return f'{s}:{v}', canon(dict(a=a, F=F, units=U, S=repr(S), trace=list(T)))


def dump(root, out, jobs=4, only=None):
    import multiprocessing as mp
    sys.path.insert(0, root)
    from sarf.catalog import Catalog
    _CTX['cat'] = Catalog([os.path.join(root, 'operators_catalog.jsonl'),
                           os.path.join(root, 'operators_catalog_split_vocalized.csv')])
    V = _verses(root, only)
    if jobs > 1:
        with mp.get_context('fork').Pool(jobs) as P:
            R = dict(P.map(_one, V, chunksize=20))
    else:
        R = dict(map(_one, V))
    pickle.dump(R, gzip.open(out, 'wb'))
    return len(R)


def compare(A, B):
    """→ (المخالفات [(المسار، الوصف)]، الحقول المضافة {المسار بلا أرقام: العدد})"""
    viol, added = [], collections.Counter()

    def walk(x, y, p):
        if isinstance(x, dict):
            if not isinstance(y, dict):
                viol.append((p, 'تغيّر النوع')); return
            for k in x:
                if k not in y:
                    viol.append((p + [k], 'حُذف')); continue
                walk(x[k], y[k], p + [k])
            for k in y:
                if k not in x:
                    added['/'.join(str(q) for q in p[1:] if not isinstance(q, int)) + '/' + k] += 1
        elif isinstance(x, list):
            if not isinstance(y, list) or len(x) != len(y):
                viol.append((p, f'تغيّر الطول {len(x)} ← {len(y) if isinstance(y, list) else "?"}')); return
            for i, (u, w) in enumerate(zip(x, y)):
                walk(u, w, p + [i])
        elif x != y:
            viol.append((p, f'{str(x)[:80]} ← {str(y)[:80]}'))
    for k in A:
        if k not in B:
            viol.append(([k], 'الآية غائبة'))
        else:
            walk(A[k], B[k], [k])
    return viol, added


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=('dump', 'cmp'))
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--verses')
    ap.add_argument('--json')
    a = ap.parse_args()
    if a.mode == 'dump':
        print('dumped', dump(os.path.abspath(a.a), a.b, a.jobs, set(a.verses.split(',')) if a.verses else None))
        sys.exit(0)
    A, B = pickle.load(gzip.open(a.a)), pickle.load(gzip.open(a.b))
    viol, added = compare(A, B)
    agg = collections.Counter()
    for k, n in added.items():
        agg[k.split('/')[-1] if k.startswith('F/') else k] += n
    if a.json:      # يُكتب قبل الطباعة، فلا يضيع إن انقطع الإخراج
        json.dump(dict(verses=len(A), violations=len(viol), examples=[('/'.join(map(str, p)), d) for p, d in viol[:200]],
                       added=dict(agg)), open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'الآيات {len(A)}، المخالفات {len(viol)}')
    for p, d in viol[:20]:
        print('  مخالفة:', '/'.join(map(str, p)), d)
    for k, n in agg.most_common():
        print('  مضاف:', k, n)
    sys.exit(1 if viol else 0)
