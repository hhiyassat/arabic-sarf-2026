#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/dump_certs.py — تفريغ شهادات الجمل والفقرة لكل سورةٍ بهوياتٍ مستقرة، لمقارنة الانتقالات بالهوية لا بالأعداد
(SARF_COMPREHENSIVE_REPAIR_04 §١٩–٢٠). يعمل على شيفرة الجذر الممرَّر (نسخة عملٍ مجمَّدة)، فيُقارن الأساس بالجديد بالأداة نفسها.

هوية الجملة: (أول موضع، آخر موضع)؛ وهوية الالتزام: (مالكه، اسمه)؛ وهوية العلاقة: relation_id.

    PYTHONHASHSEED=0 python3 tools/dump_certs.py <جذر الشيفرة> <out.jsonl.gz> [--jobs N]
    python3 tools/dump_certs.py cmp <base.jsonl.gz> <new.jsonl.gz> --json out.json
"""
import collections, gzip, json, os, sys
from concurrent.futures import ProcessPoolExecutor


def _h(x):
    import hashlib
    def canon(v, d=0):
        if d > 30:
            return '…'
        if isinstance(v, dict):
            return {str(k): canon(w, d + 1) for k, w in sorted(v.items(), key=lambda kv: str(kv[0]))}
        if isinstance(v, (list, tuple)):
            return [canon(w, d + 1) for w in v]
        if isinstance(v, (set, frozenset)):
            return sorted(repr(canon(w, d + 1)) for w in v)
        if isinstance(v, (str, int, float, bool)) or v is None:
            return v
        return type(v).__name__
    return hashlib.sha256(json.dumps(canon(x), ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]


def _work(args):
    root, s, items = args
    sys.path.insert(0, root)
    os.chdir(root)
    from sarf.catalog import Catalog
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo, linguistic_layer, closure_certificate
    from sarf import algebra as AL
    from sarf.features import unit_features
    from sarf import relations as RL, quran_source
    CAT = Catalog([os.path.join(root, 'operators_catalog.jsonl'), os.path.join(root, 'operators_catalog_split_vocalized.csv')])
    its, per = [], []
    for s_, v_, t in items:
        a = analyze(CAT, t, quran_source.uthmani_mode())
        S_, U = sentence_geo(a, f'Q{s_}:{v_}', Trace())
        its.append((s_, v_, a, U, S_))
        per.append((s_, v_, a, U, unit_features(a, U)))
    C, Rl = [], []
    LT, _, _ = linguistic_layer(its, Trace(), 'dc', cond_out=C, rel_out=Rl)
    recs = []
    for s_, v_, a, U, F in per:
        recs += RL.verse_relations(a, U, F, f'{s_}:{v_}', legacy_cond=C, legacy_rel=Rl)['records']
    Js = [J for SP in LT for D in SP.A + SP.O.get('pending', []) for J in D.A + D.O.get('pending', [])]
    certs = [closure_certificate(J, recs) for J in Js]
    sents = []
    for J, c in zip(Js, certs):
        L = J.O.get('location') or []
        sents.append(dict(key=f'{min(L)}..{max(L)}' if L else J.id, verdict=c['verdict'], by_level=c.get('verdict_by_level'),
                          boundary_rule=(c.get('boundary') or {}).get('rule_id'), source_kinds=(c.get('boundary') or {}).get('source_kinds'),
                          internal_deferred=bool(J.O.get('deferred_boundaries')),
                          h=_h(c),
                          obligations=[dict(key=f"{o.get('owner')}|{o['name']}", status=o['status'], face_id=o.get('face_id'),
                                            kind=o.get('requirement_kind'), h=_h(o), residual=str(o.get('residual_reason') or '')[:200])
                                       for o in c['obligations']]))
    rels = [dict(id=r['relation_id'], type=r['type'], status=r['status'], h=_h(r), reason=str(r.get('reason') or '')[:200]) for r in recs]
    para = None
    if hasattr(AL, 'paragraph_candidates'):
        pcs = AL.paragraph_candidates(LT, certs, recs)
        para = [dict(id=p['paragraph_id'], status=p['status'], n_comp=len(p['components']), n_obl=len(p['obligations']),
                     kinds=dict(collections.Counter(f"{o['kind']}:{o['status']}" for o in p['obligations'])),
                     boundary=p['boundary'].get('linguistic'), conditions=p['boundary'].get('conditions'), h=_h(p),
                     check=AL.check_paragraph(p, LT, certs, recs)) for p in pcs]
    elif hasattr(AL, 'paragraph_candidate'):
        p = AL.paragraph_candidate(LT, certs, recs)
        para = [dict(id=p['paragraph_id'], status=p['status'], n_comp=len(p['components']), n_obl=len(p['obligations']),
                     kinds=dict(collections.Counter(f"{o['kind']}:{o['status']}" for o in p['obligations'])),
                     boundary=p['boundary'].get('linguistic'), check=AL.check_paragraph(p, LT))]
    return dict(sura=s, sentences=sents, relations=rels, paragraphs=para)


def dump(root, out, jobs):
    sys.path.insert(0, root)
    from sarf import quran_source
    by = collections.defaultdict(list)
    for s, v, t in quran_source.rows(root):
        by[s].append((s, v, t))
    with ProcessPoolExecutor(jobs) as ex, gzip.open(out, 'wt', encoding='utf-8') as f:
        for r in ex.map(_work, [(root, s, by[s]) for s in sorted(by)]):
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def cmp(a, b, out):
    A = {r['sura']: r for r in map(json.loads, gzip.open(a, 'rt', encoding='utf-8'))}
    B = {r['sura']: r for r in map(json.loads, gzip.open(b, 'rt', encoding='utf-8'))}
    rep = collections.Counter()
    trans = collections.Counter()
    ex = collections.defaultdict(list)
    for s in sorted(A):
        sa = {x['key']: x for x in A[s]['sentences']}
        sb = {x['key']: x for x in B[s]['sentences']}
        rep['sent_base'] += len(sa); rep['sent_new'] += len(sb)
        rep['sent_same_span'] += len(set(sa) & set(sb)); rep['sent_removed'] += len(set(sa) - set(sb)); rep['sent_added'] += len(set(sb) - set(sa))
        for k in set(sa) - set(sb):
            ex['sentence_span_removed'].append(f'{s}:{k}')
        for k in set(sa) & set(sb):
            for lv in ('LOCAL_PREDICATION', 'SENTENCE', 'DISCOURSE_UNIT'):
                x, y = (sa[k]['by_level'] or {}).get(lv), (sb[k]['by_level'] or {}).get(lv)
                if x != y:
                    trans[f'verdict:{lv}:{x}→{y}'] += 1
                    if len(ex[f'verdict:{lv}:{x}→{y}']) < 12:
                        ex[f'verdict:{lv}:{x}→{y}'].append(f'{s}:{k}')
        # المالك جملةٌ (L…) يُستبدل به مدى الجملة: ترقيم الجمل يتغيّر بدمج حدٍّ مؤجَّل، والمدى هويةٌ مستقرة
        okey = lambda x, o: o['key'] if o['key'].startswith('Q') else x['key'] + '|' + o['key'].split('|', 1)[1]
        oa = {okey(x, o): o for x in A[s]['sentences'] for o in x['obligations']}
        ob = {okey(x, o): o for x in B[s]['sentences'] for o in x['obligations']}
        for k in set(oa) | set(ob):
            x, y = (oa.get(k) or {}).get('status'), (ob.get(k) or {}).get('status')
            if x != y:
                trans[f'obligation:{x}→{y}'] += 1
                ex[f'obligation:{x}→{y}'].append(dict(key=f'{s}|{k}', before=oa.get(k), after=ob.get(k)))
            elif x is not None and oa[k].get('h') and ob[k].get('h') and oa[k]['h'] != ob[k]['h']:
                trans[f'obligation_content:{x}'] += 1
                ex[f'obligation_content:{x}'].append(dict(key=f'{s}|{k}', before=oa.get(k), after=ob.get(k)))
        ra = {r['id']: r for r in A[s]['relations']}
        rb = {r['id']: r for r in B[s]['relations']}
        for k in set(ra) | set(rb):
            x, y = (ra.get(k) or {}).get('status'), (rb.get(k) or {}).get('status')
            t = (ra.get(k) or rb.get(k))['type']
            if x != y:
                trans[f'relation:{t}:{x}→{y}'] += 1
                ex[f'relation:{t}:{x}→{y}'].append(dict(key=k, before=ra.get(k), after=rb.get(k)))
            elif x is not None and ra[k].get('h') and rb[k].get('h') and ra[k]['h'] != rb[k]['h']:
                trans[f'relation_content:{t}:{x}'] += 1
                ex[f'relation_content:{t}:{x}'].append(dict(key=k, before=ra.get(k), after=rb.get(k)))
        pa = {p['id']: p for p in A[s]['paragraphs'] or []}
        for p in B[s]['paragraphs'] or []:
            q = pa.get(p['id'])
            if q is not None and q.get('boundary') != p.get('boundary'):
                trans[f"paragraph_boundary:{q.get('boundary')}→{p.get('boundary')}"] += 1
                ex[f"paragraph_boundary:{q.get('boundary')}→{p.get('boundary')}"].append(p['id'])
            rep['para_new'] += 1
            rep['para_new_' + p['status']] += 1
            rep['para_check_errors'] += len(p['check'])
        for p in A[s]['paragraphs'] or []:
            rep['para_base'] += 1
            rep['para_base_' + p['status']] += 1
    res = dict(summary=dict(rep), transitions=dict(sorted(trans.items())), examples=dict(ex))
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(res['summary'], ensure_ascii=False))
    for k, v in sorted(trans.items()):
        print(f'{v:6d}  {k}')


if __name__ == '__main__':
    if sys.argv[1] == 'cmp':
        cmp(sys.argv[2], sys.argv[3], sys.argv[sys.argv.index('--json') + 1])
    else:
        dump(os.path.abspath(sys.argv[1]), sys.argv[2], int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2)
