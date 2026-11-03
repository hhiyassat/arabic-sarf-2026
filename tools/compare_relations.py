#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/compare_relations.py — مقارنة سجلات العلاقات (sarf.relations) بين نسختين على مستوى العلاقة والموضع.

  dump: لكل آية سجلاتها (المعرّف، النوع، القاعدة، الحالة، الرؤوس، الأعضاء بمواضعها، السبب، المقدّمات، البدائل)
  cmp:  لكل علاقة: مضافة، أو محذوفة، أو تغيّرت حالتها، أو أعضاؤها، أو سببها؛ بمواضعها. ويُكتب JSON وجدولٌ مقروء.

    PYTHONHASHSEED=0 python3 tools/compare_relations.py dump <جذر الشيفرة> <ملف.jsonl.gz> [--jobs N]
    python3 tools/compare_relations.py cmp <قبل.jsonl.gz> <بعد.jsonl.gz> --json <تقرير.json> [--md <جدول.md>]
"""
import argparse, collections, gzip, json, os, sys


def _one(t):
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo
    from sarf.features import unit_features
    from sarf.relations import verse_relations
    s, v, text = t
    a = analyze(_CAT[0], text)
    _, U = sentence_geo(a, f'Q{s}:{v}', Trace())
    out = verse_relations(a, U, unit_features(a, U), f'{s}:{v}')
    keep = ('relation_id', 'type', 'rule_id', 'rule_version', 'status', 'heads', 'positions', 'texts', 'reason', 'premises',
            'alternatives', 'container_id', 'search_status', 'nucleus_complete')
    return json.dumps(dict(verse=f'{s}:{v}', records=[{k: r.get(k) for k in keep} for r in out['records']]), ensure_ascii=False)


_CAT = []


def dump(root, path, jobs):
    import multiprocessing as mp
    sys.path.insert(0, root)
    from sarf.catalog import Catalog
    _CAT.append(Catalog([os.path.join(root, 'operators_catalog.jsonl'), os.path.join(root, 'operators_catalog_split_vocalized.csv')]))
    V = [(int(p[0]), int(p[1]), p[2]) for p in (l.rstrip('\n').split('\t') for l in open(os.path.join(root, 'data', 'quran_hafs.tsv'),
                                                                                        encoding='utf-8')) if len(p) >= 3 and p[0].isdigit()]
    with mp.get_context('fork').Pool(jobs) as P:
        lines = P.map(_one, V, chunksize=20)
    with gzip.open(path, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    return len(lines)


def load(path):
    out = {}
    for l in gzip.open(path, 'rt', encoding='utf-8'):
        if l.strip():
            d = json.loads(l)
            for r in d['records']:
                out[r['relation_id']] = r
    return out


TANWIN = set('\u064b\u064c\u064d')
CAUSES = {
    'A02': 'تعلّقٌ موجب جديد (A02)، ويحلّ محلّ A01 المؤجَّل للموضع نفسه',
    'E01': 'إثبات أَفْعَل بنفي البدائل (E01، مقترحة)',
    'T19': 'الاسمية من شكل التنوين وحده لا ترخّص (العقد T19)',
    'T19_HOST': 'مضيفٌ محتمل أُسقط من بدائل A01: اسميته من التنوين وحده (T19)',
    'COORD': 'منافس العطف (إصلاح الإسناد الزائف داخل العطف)',
    'T19_CASCADE': 'تابعٌ لتغيّرٍ بـT19 في الآية نفسها يشاركه موضعاً (حاويةٌ أو شبه جملةٍ أُجِّلت فسقط ما بُني عليها)',
    'UNHIDE': 'مرشّح تعلّقٍ (A01) كان محجوباً بإسنادٍ مؤجَّل (N02) فظهر: المؤجَّل لا يحجب الوجه الآخر',
    'ID': 'تغيّر المعرّف وحده بتغيّر الأعضاء: انظر سبب السجل المقابل',
    'OTHER': 'غير مصنَّف آلياً: يُراجع يدوياً',
}


def _has(r, mark):
    return r is not None and mark in json.dumps({k: r.get(k) for k in ('reason', 'premises', 'alternatives', 'rule_id')}, ensure_ascii=False)


def cause(a, b, B):
    """سبب التغيّر بعلاماتٍ معلنة في السجلين، لا بتخمين: القاعدة، أو نصّ المقدّمة والسبب والبدائل"""
    if b is not None and b['rule_id'] == 'A02' or a is not None and b is None and a['type'] == 'ATTACH' and \
            any(x['rule_id'] == 'A02' and x['positions'].get('oblique') == a['positions'].get('oblique') for x in B.values()):
        return 'A02'
    if a is None and b['type'] == 'ATTACH' and b['rule_id'] == 'A01' and \
            any(x['type'] == 'PREDICATIVE_PP' and x['status'] != 'LICENSED' and
                set(x['positions'].get('predicate_pp', [])) & set(b['positions'].get('oblique', [])) for x in B.values()):
        return 'UNHIDE'
    for mark, c in (('E01', 'E01'), ('T19', 'T19'), ('منافس العطف', 'COORD'), ('معطوفٌ على «', 'COORD')):
        if _has(a, mark) != _has(b, mark):
            return c
    if a is not None and b is not None and a['type'] == 'ATTACH':
        ha = {h['host_text'] for h in a.get('alternatives') or [] if isinstance(h, dict)}
        hb = {h['host_text'] for h in b.get('alternatives') or [] if isinstance(h, dict)}
        if ha - hb and all(set(t) & TANWIN for t in ha - hb) and not hb - ha:
            return 'T19_HOST'
    return 'OTHER'


def compare(A, B):
    rows = []
    for rid in sorted(set(A) | set(B)):
        a, b = A.get(rid), B.get(rid)
        if a is None:
            rows.append(dict(change='مضافة', relation_id=rid, type=b['type'], rule=b['rule_id'], positions=b['positions'], texts=b['texts'],
                             before=None, after=b['status'], reason_after=b['reason']))
        elif b is None:
            rows.append(dict(change='محذوفة', relation_id=rid, type=a['type'], rule=a['rule_id'], positions=a['positions'], texts=a['texts'],
                             before=a['status'], after=None, reason_before=a['reason']))
        else:
            ch = [k for k in ('status', 'positions', 'texts', 'reason', 'alternatives', 'premises', 'search_status') if a.get(k) != b.get(k)]
            if ch:
                rows.append(dict(change='تغيّرت: ' + '، '.join(ch), relation_id=rid, type=b['type'], rule=b['rule_id'], positions=b['positions'],
                                 texts=b['texts'], before=a['status'], after=b['status'], reason_before=a['reason'], reason_after=b['reason']))
    for r in rows:
        r['cause'] = cause(A.get(r['relation_id']), B.get(r['relation_id']), B)
    # المعرّف المستبدل: محذوفٌ ومضافٌ من نوعٍ واحد في آيةٍ واحدة يشتركان في رأسٍ بموضعه، فسببهما سبب المضاف
    added = [r for r in rows if r['before'] is None]
    for r in rows:
        if r['after'] is None and r['cause'] in ('OTHER',):
            v = r['relation_id'].split(':')[:2]
            for x in added:
                if x['relation_id'].split(':')[:2] == v and x['type'] == r['type'] and \
                        any(set(r['positions'].get(k, [])) & set(x['positions'].get(k, [])) for k in r['positions']):
                    r['cause'], r['replaced_by'] = 'ID', x['relation_id']
                    x.setdefault('replaces', r['relation_id'])
                    break
    pos = lambda r: {p for ps in r['positions'].values() for p in ps}
    t19 = [r for r in rows if r['cause'] == 'T19']
    for r in rows:
        if r['cause'] == 'OTHER':
            v = r['relation_id'].split(':')[:2]
            src = next((x for x in t19 if x['relation_id'].split(':')[:2] == v and pos(x) & pos(r)), None)
            if src:
                r['cause'], r['cascade_of'] = 'T19_CASCADE', src['relation_id']
    C = collections.Counter(f"{r['type']}|{r['before']}→{r['after']}" for r in rows)
    return rows, C


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=('dump', 'cmp'))
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--json')
    ap.add_argument('--md')
    a = ap.parse_args()
    if a.mode == 'dump':
        print('dumped', dump(os.path.abspath(a.a), a.b, a.jobs))
        sys.exit(0)
    rows, C = compare(load(a.a), load(a.b))
    if a.json:
        K = collections.Counter(f"{r['cause']}|{r['type']}|{r['before']}→{r['after']}" for r in rows)
        json.dump(dict(changes=len(rows), causes=CAUSES, by_cause=dict(collections.Counter(r['cause'] for r in rows).most_common()),
                       by_cause_type_status=dict(sorted(K.items())), by_type_status=dict(C.most_common()), rows=rows),
                  open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if a.md:
        L = ['| السبب | التغيّر | النوع/القاعدة | الموضع | الأطراف | قبلُ | بعدُ | السبب بعدُ |', '|---|---|---|---|---|---|---|---|']
        for r in sorted(rows, key=lambda r: (list(CAUSES).index(r['cause']), r['type'], r['relation_id'])):
            pos = '، '.join(p for ps in r['positions'].values() for p in ps[:1])
            tx = ' / '.join(f'{k}=«{v}»' for k, v in r['texts'].items())
            L.append(f"| {r['cause']} | {r['change']} | {r['type']} {r['rule']} | {pos} | {tx} | {r['before'] or '—'} | {r['after'] or '—'} | "
                     f"{(r.get('reason_after') or '—')[:110]} |")
        open(a.md, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    try:
        print('changes', len(rows), dict(collections.Counter(r['cause'] for r in rows).most_common()))
        for k, n in C.most_common():
            print(' ', n, k)
    except BrokenPipeError:
        pass
