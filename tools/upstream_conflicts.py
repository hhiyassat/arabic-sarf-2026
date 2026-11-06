"""tools/upstream_conflicts.py — تعدّي الوسيط دليلاً على «تعارض الطبقتين» (حكم المالك، 6 نوفمبر، البند ٣).

لكل التزامٍ حاله CONFLICT في شهادة الإغلاق، يُنظر في أدلّة المنبع لفعله المالك (UPSTREAM:…:transitivity_wasit:…)، ويُقابَل
حكم الوسيط بحكم التعدّي في إطار 14أ لذلك الفعل وبدعوى الطبقة القديمة. لا تتغيّر حالةُ أي علاقةٍ ولا أي التزام: الأداة تقيس فقط،
وتتحقّق أن الشهادة بالأدلّة وبدونها متطابقةٌ في كل ما عدا حقل external_evidence.

    PYTHONHASHSEED=0 SARF_HFN=…/release_v36 python3 -s tools/upstream_conflicts.py upstream.jsonl.gz OUT.json [--jobs 2]
"""
import collections, itertools, json, multiprocessing as mp, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.chdir(ROOT)
EV = {}


def _strip(c):
    c = json.loads(json.dumps(c, ensure_ascii=False, default=str))
    c.pop('external_evidence_ids', None)
    for o in c['obligations']:
        o.pop('external_evidence', None)
    return c


def classify(ob, w, tr14):
    """→ (الصنف، الشرح). w: لازم | متعدي (الوسيط)؛ tr14: (القيمة، الحالة) في إطار 14أ"""
    v14, st14 = (tr14 or (None, None))[:2]
    if ob['requirement_kind'] != 'OBJECT':
        return 'NOT_DIRECTLY_RELEVANT', 'التعارض في غير المفعول (فاعل أو غيره): التعدّي لا يشهد له ولا عليه مباشرة'
    w14 = {'متعدٍّ': 'متعدي', 'لازم': 'لازم'}.get(v14)
    if w14 and w14 == w:
        return 'AGREES_WITH_14A_TRANSITIVITY', f'الوسيط «{w}» يوافق تعدّي إطار 14أ («{v14}»، {st14})'
    if w14 and w14 != w:
        return 'CONTRADICTS_14A_TRANSITIVITY', f'الوسيط «{w}» يخالف تعدّي إطار 14أ («{v14}»، {st14})'
    if w == 'متعدي':
        return 'SUPPORTS_LEGACY_OBJECT_CLAIM', 'إطار 14أ مؤجَّل التعدّي؛ والوسيط «متعدٍّ» يوافق دعوى الطبقة القديمة أن للفعل مفعولاً، ولا يعيّن المفعول'
    return 'CONTRADICTS_LEGACY_OBJECT_CLAIM', 'إطار 14أ مؤجَّل التعدّي؛ والوسيط «لازم» يخالف دعوى الطبقة القديمة أن للفعل مفعولاً، ويوافق غيابه في 14أ'


def _surah(items):
    from sarf.catalog import Catalog
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo, linguistic_layer, closure_certificate
    from sarf.features import unit_features
    from sarf.relations import verse_relations
    from sarf import quran_source
    CAT = Catalog([os.path.join(ROOT, 'operators_catalog.jsonl'), os.path.join(ROOT, 'operators_catalog_split_vocalized.csv')])
    its, per = [], []
    for s, v, text in items:
        a = analyze(CAT, text, quran_source.uthmani_mode())
        S_, U = sentence_geo(a, f'Q{s}:{v}', Trace())
        its.append((s, v, a, U, S_))
        per.append((s, v, a, U, unit_features(a, U)))
    C, Rl = [], []
    LT, _, _ = linguistic_layer(its, Trace(), 'upc', cond_out=C, rel_out=Rl)
    RBV = {}
    for s, v, a, U, F in per:
        RBV[(s, v)] = verse_relations(a, U, F, f'{s}:{v}', legacy_cond=C, legacy_rel=Rl)['records']
    out = dict(conflicts=0, touched=0, cls=collections.Counter(), by_kind=collections.Counter(), examples=collections.defaultdict(list),
               identical_without_evidence=0, sentences=0, evidence_on_obligations=0)
    for SP in LT:
        for D in SP.A + SP.O.get('pending', []):
            for Jx in D.A + D.O.get('pending', []):
                vv = sorted({(x[0], x[1]) for x in Jx.O.get('location', [])})
                recs = [r for x in vv for r in RBV.get(x, [])]
                c1 = closure_certificate(Jx, recs, upstream=EV)
                c0 = closure_certificate(Jx, recs)
                out['sentences'] += 1
                out['identical_without_evidence'] += _strip(c1) == _strip(c0)
                fr = {r['heads'].get('verb'): r for r in recs if r['type'] == 'VERB_FRAME'}
                for ob in c1['obligations']:
                    out['evidence_on_obligations'] += bool(ob.get('external_evidence'))
                    if ob['status'] != 'CONFLICT':
                        continue
                    out['conflicts'] += 1
                    out['by_kind'][ob['requirement_kind']] += 1
                    tw = [e for e in (ob.get('external_evidence') or []) if e['feature'] == 'transitivity_wasit']
                    if not tw:
                        continue
                    out['touched'] += 1
                    owner = (ob.get('owner') or '')
                    f_ = (fr.get(owner) or {}).get('frame') or {}
                    for e in tw[:1]:
                        k, why = classify(ob, e['value'], f_.get('transitivity'))
                        out['cls'][f"{ob['requirement_kind']}:{k}"] += 1
                        if len(out['examples'][k]) < 8:
                            out['examples'][k].append(dict(obligation=ob['obligation_id'], name=ob['name'], wasit=e['value'], evidence_id=e['id'],
                                                           tr14=f_.get('transitivity'), why=why, residual=ob['residual_reason']))
    return out


def main():
    global EV
    from upstream_candidates import load_evidence
    EV = load_evidence(sys.argv[1])
    from sarf import quran_source
    V = quran_source.rows()
    if '--verses' in sys.argv:
        want = set(sys.argv[sys.argv.index('--verses') + 1].split(','))
        V = [x for x in V if f'{x[0]}:{x[1]}' in want]
    groups = [list(g) for _, g in itertools.groupby(V, key=lambda x: x[0])]
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2
    with mp.get_context('fork').Pool(jobs) as P:
        parts = P.map(_surah, groups, chunksize=1)
    T = dict(conflicts=0, touched=0, cls=collections.Counter(), by_kind=collections.Counter(), examples=collections.defaultdict(list),
             identical_without_evidence=0, sentences=0, evidence_on_obligations=0)
    for p in parts:
        for k in ('conflicts', 'touched', 'identical_without_evidence', 'sentences', 'evidence_on_obligations'):
            T[k] += p[k]
        T['cls'].update(p['cls'])
        T['by_kind'].update(p['by_kind'])
        for k, v in p['examples'].items():
            T['examples'][k] = (T['examples'][k] + v)[:8]
    T['cls'] = dict(sorted(T['cls'].items()))
    T['by_kind'] = dict(T['by_kind'])
    json.dump(T, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: T[k] for k in ('sentences', 'identical_without_evidence', 'conflicts', 'touched', 'cls')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
