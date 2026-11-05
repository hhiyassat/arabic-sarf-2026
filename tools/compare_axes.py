#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/compare_axes.py — مقارنة تفريغين من tools/measure_axes.py بالوحدة والعلاقة: انتقالات الاتفاق والدور والصنف والبناء،
وتغيّر حالة العلاقات (المضاف والمحذوف بالمعرّف)، وتغيّر النص وحده، وخلايا الصنف بلا دليل، وتسرّب الإنجليزية وتمثيل بايثون.

    python3 tools/compare_axes.py <قبل.jsonl.gz> <بعد.jsonl.gz> --json <تقرير.json>
"""
import argparse, collections, gzip, json, re

LEAK = re.compile(r"\b(singular|dual|plural|masc|fem|common)\b|\{'|\['|ملف المبنيات: [a-z_]+(?! \()")


def load(p):
    U, R, chk, oreq = {}, {}, 0, collections.Counter()
    for l in gzip.open(p, 'rt', encoding='utf-8'):
        r = json.loads(l)
        chk += len(r['check'])
        for u in r['rows']:
            U[u['uid']] = u
        for x in r['rels']:
            R[x['id']] = x
            if x['type'] == 'VERB_FRAME':
                oreq[x.get('oreq')] += 1
    return U, R, chk, oreq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--json', required=True)
    a = ap.parse_args()
    UA, RA, ca, oa = load(a.a)
    UB, RB, cb, ob = load(a.b)
    out = dict(checker=(ca, cb), units=(len(UA), len(UB)), rels=(len(RA), len(RB)),
               agreement=(dict(collections.Counter(u['agreement'] for u in UA.values())),
                          dict(collections.Counter(u['agreement'] for u in UB.values()))),
               object_requirement=(dict(oa), dict(ob)))
    tr, moves = collections.Counter(), []
    for k, x in UA.items():
        y = UB.get(k)
        if y is None:
            tr['missing'] += 1
            continue
        if x['agreement'] != y['agreement'] or x['role'] != y['role'] or x['wc'] != y['wc'] or x['build'] != y['build']:
            tr[f"{x['agreement']}→{y['agreement']}"] += 1
            moves.append(dict(loc=x['loc'], text=x['text'], before=[x['agreement'], x['role'], x['statement']],
                              after=[y['agreement'], y['role'], y['statement']], wc=(x['wc'], y['wc']), build=(x['build'], y['build'])))
    tr['added'] = sum(1 for k in UB if k not in UA)
    out['unit_transitions'] = dict(tr)
    out['unit_moves'] = moves
    rs, rm = collections.Counter(), []
    for k, x in RA.items():
        y = RB.get(k)
        if y is None:
            rs[f"{x['type']}|removed"] += 1
            continue
        if x['status'] != y['status']:
            rs[f"{x['type']}|{x['rule']}|{x['status']}→{y['status']}"] += 1
            rm.append(dict(id=k, type=x['type'], before=x['status'], after=y['status'], reason=y['reason'][:300]))
    for k in RB:
        if k not in RA:
            rs[f"{RB[k]['type']}|added"] += 1
    out['relation_status_changes'] = dict(rs)
    out['relation_moves'] = rm
    out['relation_text_only'] = sum(1 for k, x in RA.items() if k in RB and x['status'] == RB[k]['status'] and
                                    (x['reason'] != RB[k]['reason'] or x['premises'] != RB[k]['premises']))
    out['empty_class_evidence'] = (sum(1 for u in UA.values() if u['wc'] and not u.get('wc_ev')),
                                   sum(1 for u in UB.values() if u['wc'] and not u.get('wc_ev')))
    lk = lambda R: sum(1 for x in R.values() for p in x['premises'] + [x['reason']] if LEAK.search(p))
    out['english_or_python_leaks'] = (lk(RA), lk(RB))
    json.dump(out, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for k in ('checker', 'units', 'rels', 'unit_transitions', 'relation_status_changes', 'relation_text_only', 'empty_class_evidence',
              'english_or_python_leaks', 'object_requirement'):
        print(k, out[k])


if __name__ == '__main__':
    main()
