#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/eval_inflection.py — قياس محور البناء والإعراب (sarf.relations._inflection) على المصحف كله.

لكل وحدة: البناء، والعامل، والحالة، والعلامة، والعبارة، وحالة الاتفاق بين الثلاثة (قدرة العامل، والعلامة المقروءة بالصنف،
والعبارة المولَّدة): AGREE، أو CONFLICT، أو UNVERIFIED، أو UNGOVERNED، أو MABNI، أو N/A.
ويُشغَّل الفاحص المستقل check_inflection على كل آية. ويُكتب JSON فيه الهوية والأعداد وكل تعارضٍ بموضعه.

    PYTHONHASHSEED=0 python3 tools/eval_inflection.py [--jobs N] [--out reports/<dir>]
"""
import argparse, collections, json, os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
_CAT = []


def _one(t):
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo
    from sarf.features import unit_features
    from sarf.relations import verse_relations, check_inflection
    s, v, text = t
    from sarf import quran_source
    a = analyze(_CAT[0], text, quran_source.uthmani_mode())
    _, U = sentence_geo(a, f'Q{s}:{v}', Trace())
    out = verse_relations(a, U, unit_features(a, U), f'{s}:{v}')
    rows = []
    for uid, loc, tx in out['tokens']:
        inf = out['axes'][uid]['inflection']
        g = inf.get('governor') or {}
        rows.append(dict(loc=loc, text=tx, build=inf['build'][0], agreement=inf['agreement'], statement=inf['statement'],
                         state=inf['state'][0], mark=inf['mark'] and inf['mark'][0], governor=g.get('operator') or g.get('kind'),
                         expected=g.get('expected'), conflicts=inf['conflicts'], word_class=out['axes'][uid]['word_class'][0],
                         relation=g.get('relation'), effect=inf.get('effect'), mark_dims=inf.get('mark_dims'),
                         conflict_nature=inf.get('conflict_nature'), uid=uid, notes=inf.get('notes') or [],
                         capacity_source=g.get('capacity_source')))
    return dict(verse=f'{s}:{v}', rows=rows, check=check_inflection(out['axes']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--out', default=os.path.join(H, 'reports', 'inflection_axis_01'))
    a = ap.parse_args()
    import multiprocessing as mp
    from sarf.catalog import Catalog
    sys.path.insert(0, os.path.join(H, 'tools'))
    import provenance
    _CAT.append(Catalog([os.path.join(H, 'operators_catalog.jsonl'), os.path.join(H, 'operators_catalog_split_vocalized.csv')]))
    from sarf import quran_source
    V = quran_source.rows()
    with mp.get_context('fork').Pool(a.jobs) as P:
        res = P.map(_one, V, chunksize=20)
    C, K, conf, chk, verbs_jarr = collections.Counter(), collections.Counter(), [], [], 0
    REL, EFF, DIM, SRC = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    noted, unlicensed = [], []
    for r in res:
        chk += [f"{r['verse']}: {e}" for e in r['check']]
        for x in r['rows']:
            C[x['agreement']] += 1
            if x['agreement'] == 'AGREE':
                K[f"{x['word_class']}|{x['expected']}|{x['mark']}"] += 1
                REL[str(x['relation'])] += 1
                SRC[str(x['capacity_source'])] += 1
                if x['notes']:
                    noted.append(dict(loc=x['loc'], text=x['text'], uid=x['uid'], governor=x['governor'], notes=x['notes']))
                e = x['effect'] or {}
                EFF['لفظي' if e.get('lafzi') else 'تقديري' if e.get('taqdiri') else 'محلّي' if e.get('mahalli') else '—'] += 1
                d = x['mark_dims'] or {}
                DIM[f"{d.get('carrier')}|{d.get('visibility')}|{d.get('originality')}"] += 1
            if x['agreement'] == 'UNVERIFIED' and x['relation'] == 'غير مرخَّص في الجرد':
                unlicensed.append(dict(loc=x['loc'], text=x['text'], governor=x['governor'], expected=x['expected']))
            if x['agreement'] == 'CONFLICT':
                conf.append(x)
            if x['word_class'] == 'فعل' and (x['state'] == 'جر' or 'مجرور' in (x['statement'] or '')):
                verbs_jarr += 1
    os.makedirs(a.out, exist_ok=True)
    rep = dict(identity=provenance.identity('\n'.join(t[2] for t in V), 'محور البناء والإعراب v1'), verses=len(res), by_agreement=dict(C.most_common()),
               agree_by_class_state_mark=dict(K.most_common()), agree_by_relation=dict(REL.most_common()),
               agree_by_effect=dict(EFF.most_common()), agree_by_capacity_source=dict(SRC.most_common()),
               agree_with_internal_note=noted, unverified_capacity_not_in_inventory=unlicensed, agree_by_mark_dims=dict(DIM.most_common()), verbs_with_jarr=verbs_jarr, checker_errors=chk,
               conflicts=conf)
    json.dump(rep, open(os.path.join(a.out, 'inflection_measurement.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('verses', len(res), dict(C.most_common()))
    print('relation', dict(REL.most_common()), '| effect', dict(EFF.most_common()))
    print('mark dims', dict(DIM.most_common()))
    print('capacity source', dict(SRC.most_common()), '| AGREE with internal note', len(noted))
    print('verbs with jarr', verbs_jarr, '| checker errors', len(chk), '| conflicts', len(conf))
    for k, n in K.most_common(30):
        print(' ', n, k)


if __name__ == '__main__':
    main()
