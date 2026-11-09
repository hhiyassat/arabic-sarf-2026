"""measure_reconciliation.py <OUT.json> [--jobs N]: المصالحة على المصحف كله (stages.run حتى face_reconciliation لكل سورة):
كل تغيير في السمات النهائية عن مخرج المرحلة ١٣ بوقوعه وسمته وقيمتيه وسببه، وأخطاء check_consistency."""
import sys, os, json, collections, itertools, multiprocessing as mp
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT); os.chdir(ROOT)


def one(items):
    from sarf.stages import run
    C = run(items, None, ['face_reconciliation'])
    R = C.get('reconciliation')
    return [dict(verse=k, **x) for k, L in R['log'].items() for x in L], [dict(verse=k, err=list(map(str, e))) for k, E in R['errors'].items() for e in E]


def main():
    from sarf import quran_source
    out = sys.argv[1]
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 3
    V = quran_source.rows()
    if '--verses' in sys.argv:
        w = set(sys.argv[sys.argv.index('--verses') + 1].split(','))
        V = [x for x in V if f'{x[0]}:{x[1]}' in w]
    groups = [list(g) for _, g in itertools.groupby(V, key=lambda x: x[0])]
    with mp.get_context('fork').Pool(jobs) as P:
        parts = P.map(one, groups, chunksize=1)
    log = [x for p in parts for x in p[0]]
    errs = [x for p in parts for x in p[1]]
    C = collections.Counter((x['feature'], json.dumps(x['before'], ensure_ascii=False), json.dumps(x['after'], ensure_ascii=False)) for x in log)
    json.dump(dict(verses=len(V), units_changed=len({(x['verse'], tuple(x['unit'])) for x in log}), feature_changes=len(log), consistency_errors=len(errs),
                   errors=errs[:50], transitions=[dict(feature=a, before=json.loads(b), after=json.loads(c), n=n) for (a, b, c), n in C.most_common()],
                   changes=log), open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    print(len(V), 'units changed', len({(x['verse'], tuple(x['unit'])) for x in log}), 'feature changes', len(log), 'errors', len(errs))


if __name__ == '__main__':
    main()
