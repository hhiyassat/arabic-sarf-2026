"""tools/morph_engine_export.py <SARF_ROOT> <OUT.jsonl.gz> [--jobs N] — مخرج المحرّك النهائي لكل خانة، عبر الواجهة العامة run()
(MORPH_COMPLETION_01: مصالحة الجرد وقياس P1 قبل وبعد).

لكل خانةٍ في كل آية سطر: الآية، والكلمة، والخانة (نوعها ونصّها ودورها)، وسجلّ morph للمحرّك (الحالة، والمستوى، والجذر، والوزن، والسبب،
وهوية التحليل، وحالات الاختيار، والحدث)، ووحدة الإغلاق (units: الهوية، والإغلاق، وTheta: R الجذر وP البناء وF الصنف وalpha)،
والسمات النهائية (features_final) كاملةً. فهذا ما يخرجه النظام فعلاً للفعل والاسم معاً، لا استدعاء morph() منفرداً."""
import gzip, itertools, json, multiprocessing as mp, os, sys
_ROOT = []


def one(items):
    sys.path.insert(0, _ROOT[0]); os.chdir(_ROOT[0])
    sys.path.insert(0, os.path.join(_ROOT[0], 'tools', 'v48c2'))
    import engine_dump2 as E
    from sarf.stages import run
    C = run(items, None, E.TARGETS)
    can = E.Canon()
    an, U, FF = can(C.get('analysis')), can(C.get('units')), can(C.get('features_final'))
    out = []
    for vk, a in an.items():
        M = {(m.get('word_index'), m.get('slot')): m for m in a.get('morph') or []}
        UU = (U.get(vk) or {}).get('units') or {}
        F = FF.get(vk) or {}
        for seg in a['segments']:
            wi = seg['word_index']
            for sl in seg['slots']:
                k = (wi, sl['index'])
                m = M.get(k) or {}
                u = UU.get(repr(k)) or {}
                th = u.get('Theta') or {}
                out.append(dict(verse=vk, wi=wi, si=sl['index'], word=seg['word'], type=sl['type'], role=sl.get('role'), text=sl['text'],
                                lexicon=sl.get('lexicon'),
                                morph=dict(status=m.get('status'), level=m.get('level'), root=m.get('root'), form=m.get('form_class'),
                                           reason=m.get('reason'), analysis_id=m.get('analysis_id'), statuses=m.get('statuses'),
                                           event=(m.get('event') or {}).get('event_id'), n_candidates=m.get('n_candidates')) if m else None,
                                unit=dict(id=u.get('id'), closed=u.get('closed'), R=th.get('R'), P=th.get('P'), F=th.get('F'), alpha=th.get('alpha')) if u else None,
                                features=F.get(repr(k))))
    return out


def _init(root):
    if not _ROOT:
        _ROOT.append(root)


def main(root, path, jobs):
    _ROOT.append(os.path.abspath(root)); sys.path.insert(0, _ROOT[0])
    from sarf import quran_source
    groups = [list(g) for _, g in itertools.groupby(quran_source.rows(), key=lambda x: x[0])]
    n = 0
    with mp.get_context('spawn').Pool(jobs, initializer=_init, initargs=(_ROOT[0],)) as P, gzip.open(path, 'wt', encoding='utf-8') as f:
        for r in P.imap(one, groups, chunksize=1):
            for x in r:
                f.write(json.dumps(x, ensure_ascii=False) + '\n'); n += 1
    print('slots', n)


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], int(a[a.index('--jobs') + 1]) if '--jobs' in a else 2)
