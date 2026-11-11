"""engine_dump4.py (V50C01) — engine_dump2 نفسه (البصمة والمقارنة دون تغيير)، والإرفاق بعقد v4 (tools/v50/ajnas_sidecar.py)
مع فحص هوية المحرّك لكل إرفاقٍ داخل التفريغ (V48C03 §٩).
    dump <root> <OUT.jsonl.gz> [--jobs N]  |  cmp <A> <B> <OUT.json>   (cmp هو cmp في engine_dump2)"""
import base64, itertools, json, multiprocessing as mp, os, sys, zlib, gzip
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'v48c2'))
import engine_dump2 as E2
_ROOT = []


def one(items):
    sys.path.insert(0, _ROOT[0]); os.chdir(_ROOT[0])
    sys.path.insert(0, os.path.join(_ROOT[0], 'tools', 'hfn_isolation'))
    sys.path.insert(0, HERE)
    import guard
    ident = guard.assert_identity()
    from sarf.stages import run
    C = run(items, None, E2.TARGETS)
    canon = E2.Canon()
    prods, sents, stab = E2.fingerprint(C, canon)
    out = dict(products=prods, sentences=sents, stability=stab, repr_types=dict(canon.repr_types), hfn=ident)
    import ajnas_sidecar as S
    import sidecar_contract as K
    sc = S.attach(C)
    s = E2.js(E2.Canon()(sc))
    out['ajnas_sidecar'] = dict(sha=E2.sha(s), contract=sc['contract'], z=base64.b64encode(zlib.compress(s.encode(), 6)).decode())
    out['leak_scan'] = S.leak_scan(C, E2.PRODUCTS)
    out['engine_identity_violations'] = K.engine_identity(sc, C)
    prods2, sents2, stab2 = E2.fingerprint(C, E2.Canon())
    out['post_attach_same_context'] = dict(products=all(prods2[p]['sha'] == prods[p]['sha'] for p in E2.PRODUCTS),
                                           sentences=sents2 == sents, stability=stab2 == stab)
    if guard.assert_identity() != ident:
        raise E2.DumpError('HFN_IDENTITY_CHANGED_DURING_RUN')
    return out


def _init(root):
    if not _ROOT:
        _ROOT.append(root)


def dump(root, path, jobs):
    _ROOT.append(os.path.abspath(root)); sys.path.insert(0, _ROOT[0])
    from sarf import quran_source
    groups = [list(g) for _, g in itertools.groupby(quran_source.rows(), key=lambda x: x[0])]
    only = set(filter(None, os.environ.get('SARF_DUMP_SURAHS', '').split(',')))
    if only:
        groups = [g for g in groups if str(g[0][0]) in only]
    with mp.get_context('spawn').Pool(jobs, initializer=_init, initargs=(_ROOT[0],)) as P, gzip.open(path, 'wt', encoding='utf-8') as f:
        for i, r in enumerate(P.imap(one, groups, chunksize=1)):
            f.write(json.dumps(dict(surah=groups[i][0][0], verses=len(groups[i]), **r), ensure_ascii=False) + '\n')
    print('dumped', len(groups), 'surahs', sum(len(g) for g in groups), 'verses')


if __name__ == '__main__':
    if sys.argv[1] == 'dump':
        dump(sys.argv[2], sys.argv[3], int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 1)
    else:
        E2.cmp(sys.argv[2], sys.argv[3], sys.argv[4])
