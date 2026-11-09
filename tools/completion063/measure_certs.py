"""measure_certs.py dump <جذر الشيفرة> <OUT.jsonl.gz> [--jobs N] | cmp <قبل> <بعد> <OUT.json>

dump: لكل جملةٍ في المصحف (شهادة الإغلاق، المرحلة ١٦): الحكم ومستواه، وحالة كل التزام (الاسم، الحالة، الاستيفاء القديم، معرّف التصريف).
cmp:  انتقالات الحكم وحالات الالتزامات بين نسختين، بمواضعها؛ وما انتقل من مستوفى/مغلق إلى غيره يُعدّ منفرداً."""
import sys, os, json, gzip, collections, itertools, multiprocessing as mp

_ROOT = []


def one(items):
    sys.path.insert(0, _ROOT[0])
    os.chdir(_ROOT[0])
    from sarf.stages import run
    C = run(items, None, ['certificates'])
    out = []
    for cid, c in C.get('certificates').items():
        out.append(json.dumps(dict(id=cid, span=[str(x) for x in (c.get('span') or [])], verdict=c.get('verdict'), level=c.get('verdict_level'),
                                   by_level=c.get('verdict_by_level'),
                                   obligations=[dict(id=o.get('obligation_id'), name=o.get('name'), status=o.get('status'), met=o.get('met'),
                                                     legacy=o.get('legacy_met'), rel=o.get('discharge_relation_id'))
                                                for o in c.get('obligations') or []]), ensure_ascii=False))
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
        for i, p in enumerate(parts):
            for line in p:
                d = json.loads(line)
                d['key'] = f'{groups[i][0][0]}|{d["id"]}'
                f.write(json.dumps(d, ensure_ascii=False) + '\n')
    print('dumped', sum(len(p) for p in parts))


def load(p):
    with gzip.open(p, 'rt', encoding='utf-8') as f:
        return {d['key']: d for d in map(json.loads, f)}


def cmp(a, b, out):
    A, B = load(a), load(b)
    vt, ot = collections.Counter(), collections.Counter()
    ex = collections.defaultdict(list)
    lost = []
    for k, x in A.items():
        y = B.get(k)
        if y is None:
            vt[('GONE', x['verdict'], None)] += 1
            continue
        if (x['verdict'], x['level']) != (y['verdict'], y['level']):
            vt[(x['level'], x['verdict'], y['verdict'])] += 1
            ex[f'verdict {x["verdict"]}→{y["verdict"]}'].append(k)
            if str(x['verdict']).startswith('CLOSED') and not str(y['verdict']).startswith('CLOSED'):
                lost.append(dict(sentence=k, before=x['verdict'], after=y['verdict']))
        # المفتاح اسم الالتزام وترتيب وروده باسمه في الجملة: معرّف O<n> يُزاح إذا أُدخل التزامٌ قبله، فلا يُقابَل به
        def keyed(L):
            seen, out_ = collections.Counter(), {}
            for o_ in L:
                seen[o_['name']] += 1
                out_[(o_['name'], seen[o_['name']])] = o_
            return out_
        kx, ob = keyed(x['obligations']), keyed(y['obligations'])
        for kk, o in kx.items():
            o2 = ob.get(kk)
            s2 = o2['status'] if o2 else 'GONE'
            if o['status'] != s2 or bool(o['legacy']) != bool((o2 or {}).get('legacy')):
                ot[(o['status'], s2, bool(o['legacy']), bool((o2 or {}).get('legacy')))] += 1
                ex[f'obligation {o["status"]}→{s2} legacy {bool(o["legacy"])}→{bool((o2 or {}).get("legacy"))}'].append(f'{k} {o["name"]}')
        for oid, o2 in ob.items():
            if oid not in kx:
                ot[('NEW', o2['status'], None, bool(o2['legacy']))] += 1
                ex[f'obligation NEW {o2["status"]}'].append(f'{k} {o2["name"]}')
    new = [k for k in B if k not in A]
    res = dict(sentences_before=len(A), sentences_after=len(B), new_sentences=len(new),
               verdict_transitions=[dict(level=a_, before=b_, after=c_, n=n) for (a_, b_, c_), n in vt.most_common()],
               obligation_transitions=[dict(before=a_, after=b_, legacy_before=c_, legacy_after=d_, n=n) for (a_, b_, c_, d_), n in ot.most_common()],
               closed_lost=lost, examples={k_: v_[:30] for k_, v_ in ex.items()}, example_counts={k_: len(v_) for k_, v_ in ex.items()})
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k_: res[k_] for k_ in ('verdict_transitions', 'obligation_transitions')}, ensure_ascii=False)[:3000],
          'closed_lost', len(lost))


if __name__ == '__main__':
    if sys.argv[1] == 'dump':
        dump(sys.argv[2], sys.argv[3], int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2)
    else:
        cmp(sys.argv[2], sys.argv[3], sys.argv[4])
