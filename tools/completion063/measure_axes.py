"""measure_axes.py dump <جذر الشيفرة> <OUT.jsonl.gz> [--jobs N] | cmp <قبل> <بعد> <OUT.json>

dump: لكل وحدةٍ في المصحف: محور الإعراب (agreement، ungoverned_kind، العلامة)، والدور، ومتطلَّب المفعول في إطار الفعل، وسجلات OBJECT.
cmp:  انتقالات agreement وungoverned_kind ومتطلَّب المفعول وسجلات المفعول بين نسختين، بمواضعها؛ وما انتقل من مرخَّص إلى غيره."""
import sys, os, json, gzip, collections, itertools, multiprocessing as mp

_ROOT = []


def one(items):
    sys.path.insert(0, _ROOT[0])
    os.chdir(_ROOT[0])
    from sarf.stages import run
    C = run(items, None, ['relations'])
    out = []
    for k, V in C.get('records').items():
        tok = {u: (loc, t) for u, loc, t in V['tokens']}
        units = {}
        for u, a_ in V['axes'].items():
            inf = a_.get('inflection') or {}
            units[u] = dict(loc=tok[u][0], text=tok[u][1], agreement=inf.get('agreement'), kind=inf.get('ungoverned_kind'),
                            role=str(a_.get('role'))[:120])
        frames = {r['heads']['verb']: (r['frame'].get('object_requirement') or {}).get('kind')
                  for r in V['records'] if r['type'] == 'VERB_FRAME' and r.get('frame')}
        objs = {r['relation_id']: dict(rule=r['rule_id'], status=r['status'], texts=r['texts'])
                for r in V['records'] if r['type'] == 'OBJECT'}
        out.append(json.dumps(dict(verse=k, units=units, frames=frames, objects=objs), ensure_ascii=False))
    return out


def dump(root, path, jobs):
    _ROOT.append(os.path.abspath(root))
    sys.path.insert(0, _ROOT[0])
    from sarf import quran_source
    V = quran_source.rows()
    groups = [list(g) for _, g in itertools.groupby(V, key=lambda x: x[0])]
    with mp.get_context('fork').Pool(jobs) as P:
        parts = P.map(one, groups, chunksize=1)
    with gzip.open(path, 'wt', encoding='utf-8') as f:
        for p in parts:
            for line in p:
                f.write(line + '\n')
    print('dumped', sum(len(p) for p in parts))


def load(p):
    with gzip.open(p, 'rt', encoding='utf-8') as f:
        return {d['verse']: d for d in map(json.loads, f)}


def cmp(a, b, out):
    A, B = load(a), load(b)
    ag, kd, fr, ob = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    ex = collections.defaultdict(list)
    kinds_after, ag_before, ag_after = collections.Counter(), collections.Counter(), collections.Counter()
    lic_lost = []
    for v in A:
        x, y = A[v], B[v]
        for u, ua in x['units'].items():
            ub = y['units'].get(u)
            ag_before[ua['agreement']] += 1
            if ub is None:
                continue
            ag_after[ub['agreement']] += 1
            if ub['agreement'] == 'UNGOVERNED':
                kinds_after[ub['kind']] += 1
            if ua['agreement'] != ub['agreement']:
                ag[(ua['agreement'], ub['agreement'])] += 1
                ex[f'agreement {ua["agreement"]}→{ub["agreement"]}'].append((ua['loc'], ua['text']))
            if ua['role'] != ub['role']:
                kd[('role', ua['role'][:40], ub['role'][:40])] += 1
                ex['role'].append((ua['loc'], ua['text'], ua['role'][:60], ub['role'][:60]))
        for vb, k in x['frames'].items():
            k2 = y['frames'].get(vb)
            if k != k2:
                fr[(k, k2)] += 1
                ex[f'object_requirement {k}→{k2}'].append(v + ' ' + vb)
        for rid, o in x['objects'].items():
            o2 = y['objects'].get(rid)
            if o2 is None or o2['status'] != o['status']:
                ob[(o['rule'], o['status'], (o2 or {}).get('status'))] += 1
                if o['status'] == 'LICENSED':
                    lic_lost.append((v, rid, (o2 or {}).get('status')))
        for rid, o2 in y['objects'].items():
            if rid not in x['objects']:
                ob[('NEW', o2['rule'], o2['status'])] += 1
                ex[f'new OBJECT {o2["rule"]} {o2["status"]}'].append((v, o2['texts']))
    res = dict(verses=len(A), agreement_before=dict(ag_before), agreement_after=dict(ag_after), ungoverned_kind_after=dict(kinds_after),
               agreement_transitions=[dict(before=a_, after=b_, n=n) for (a_, b_), n in ag.most_common()],
               role_changes=sum(n for k_, n in kd.items()),
               object_requirement_transitions=[dict(before=a_, after=b_, n=n) for (a_, b_), n in fr.most_common()],
               object_record_transitions=[dict(key=list(k_), n=n) for k_, n in ob.most_common()],
               licensed_lost=lic_lost, examples={k_: v_[:25] for k_, v_ in ex.items()}, example_counts={k_: len(v_) for k_, v_ in ex.items()})
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k_: res[k_] for k_ in ('agreement_transitions', 'ungoverned_kind_after', 'role_changes', 'object_record_transitions')},
                     ensure_ascii=False)[:3000], 'licensed_lost', len(lic_lost))


if __name__ == '__main__':
    if sys.argv[1] == 'dump':
        dump(sys.argv[2], sys.argv[3], int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2)
    else:
        cmp(sys.argv[2], sys.argv[3], sys.argv[4])
