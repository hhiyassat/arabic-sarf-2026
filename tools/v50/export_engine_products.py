"""export_engine_products.py <SARF_ROOT> <OUT.jsonl.gz> [--jobs N] — يصدّر منتجي المحرّك analysis وfeatures_final بصورتهما القانونية لكل آية
(V50C01 R3: جردٌ مستقل للوقوعات يُقابَل به الإرفاق في المدقّق).

لكل سورة سطر: {surah, analysis: {آية: قانوني}, features_final: {آية: قانوني}, keys: {analysis: {آية: sha}, features_final: {آية: sha}}}
والقانوني والبصمة بدوالّ engine_dump2 نفسها (Canon وjs وsha)، فبصمة كل آيةٍ تُقابَل ببصمة مفتاحها المسجّلة في تفريغ التشغيل (C/D):
إن تطابقت فالمصدَّر هو مخرج المحرّك نفسه الذي قيس، لا تشغيلٌ جديد مختلف. يُشغَّل بالبيئة والشيفرة المجمّدتين للتشغيل نفسه."""
import gzip, itertools, json, multiprocessing as mp, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = []
PRODUCTS = ('analysis', 'features_final')


def one(items):
    sys.path.insert(0, _ROOT[0]); os.chdir(_ROOT[0])
    sys.path.insert(0, os.path.join(_ROOT[0], 'tools', 'v48c2'))
    sys.path.insert(0, os.path.join(_ROOT[0], 'tools', 'hfn_isolation'))
    import engine_dump2 as E
    import guard
    ident = guard.assert_identity()
    from sarf.stages import run
    C = run(items, None, E.TARGETS)
    out = dict(hfn=ident, keys={})
    for p in PRODUCTS:
        cv = E.Canon()(C.get(p))
        out[p] = cv
        out['keys'][p] = {k: E.sha(E.js(x)) for k, x in cv.items()}
    return out


def _init(root):
    if not _ROOT:
        _ROOT.append(root)


def main(root, path, jobs):
    _ROOT.append(os.path.abspath(root)); sys.path.insert(0, _ROOT[0])
    from sarf import quran_source
    groups = [list(g) for _, g in itertools.groupby(quran_source.rows(), key=lambda x: x[0])]
    with mp.get_context('spawn').Pool(jobs, initializer=_init, initargs=(_ROOT[0],)) as P, gzip.open(path, 'wt', encoding='utf-8') as f:
        for i, r in enumerate(P.imap(one, groups, chunksize=1)):
            f.write(json.dumps(dict(surah=groups[i][0][0], **r), ensure_ascii=False) + '\n')
    print('exported', len(groups), 'surahs')


if __name__ == '__main__':
    a = sys.argv[1:]
    j = int(a[a.index('--jobs') + 1]) if '--jobs' in a else 2
    main(a[0], a[1], j)
