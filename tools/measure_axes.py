"""tools/measure_axes.py — تفريغ المحاور والعلاقات لكل وحدةٍ في المصحف بالجسرين كما في صفحة التتبّع (مقارنة النسخ بالوحدة والعلاقة).

    PYTHONHASHSEED=0 python3 tools/measure_axes.py <جذر الشيفرة> <ملف.jsonl.gz> [--jobs N]
"""
import sys, os, json, gzip, itertools, multiprocessing as mp
ROOT = os.path.abspath(sys.argv[1]); OUT = sys.argv[2]
JOBS = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2
sys.path.insert(0, ROOT); os.chdir(ROOT)
from sarf.catalog import Catalog
CAT = Catalog([os.path.join(ROOT, 'operators_catalog.jsonl'), os.path.join(ROOT, 'operators_catalog_split_vocalized.csv')])
def surah(items):
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo, linguistic_layer
    from sarf.features import unit_features
    from sarf import relations as RL, quran_source
    its, per = [], []
    for s, v, text in items:
        a = analyze(CAT, text, quran_source.uthmani_mode())
        S_, U = sentence_geo(a, f'Q{s}:{v}', Trace())
        its.append((s, v, a, U, S_)); per.append((s, v, a, U, unit_features(a, U)))
    C, Rl = [], []
    linguistic_layer(its, Trace(), 'axb', cond_out=C, rel_out=Rl)
    res = []
    for s, v, a, U, F in per:
        o = RL.verse_relations(a, U, F, f'{s}:{v}', legacy_cond=C, legacy_rel=Rl)
        rows = []
        for uid, loc, tx in o['tokens']:
            ax = o['axes'][uid]; inf = ax['inflection']; g = inf.get('governor') or {}
            rows.append(dict(uid=uid, loc=loc, text=tx, agreement=inf['agreement'], statement=inf['statement'],
                             wc=ax['word_class'][0], wc_ev=ax['word_class'][1], build=inf['build'][0], role=(ax.get('role') or [None])[0],
                             gov=g.get('operator') or g.get('kind'), mark=inf['mark'] and inf['mark'][0], state=inf['state'][0]))
        rels = [dict(id=r['relation_id'], type=r['type'], rule=r['rule_id'], status=r['status'], reason=r['reason'], oreq=((r.get('frame') or {}).get('object_requirement') or {}).get('kind'),
                     premises=[str(p) for p in r['premises']]) for r in o['records']]
        chk = RL.check_inflection(o['axes'], o['tokens']) + RL.check_cross(o['records'], o['axes']) + RL.check_records(o['records'], o['tokens'])
        res.append(dict(verse=f'{s}:{v}', rows=rows, rels=rels, check=chk))
    return res
if __name__ == '__main__':
    from sarf import quran_source
    V = quran_source.rows()
    groups = [list(g) for _, g in itertools.groupby(V, key=lambda x: x[0])]
    with mp.get_context('fork').Pool(JOBS) as P:
        res = P.map(surah, groups, chunksize=1)
    n = 0
    with gzip.open(OUT, 'wt', encoding='utf-8') as f:
        for rr in res:
            for r in rr:
                f.write(json.dumps(r, ensure_ascii=False) + '\n'); n += 1
    print('dumped', n, 'check errors', sum(len(r['check']) for rr in res for r in rr))
