"""sidecar_diff.py <dump_C_old (v2)> <dump_C_new (v3)> <OUT.json> <OUT.tsv.gz> — فروق الإرفاق القديم والجديد (V48C03 §٩).
المفتاح: (الوقوع، الحدث، الرابط). لكل إرفاقٍ قديمٍ: باقٍ أو مفقودٌ بسبب قرار الوقوع الجديد؛ ولكل جديدٍ لم يكن: مضافٌ بسببه.
وانتقال قرار كل وقوع (قديم ← جديد) معدود، ولا يبقى انتقالٌ بلا سببٍ مسمّى."""
import base64, gzip, json, sys, zlib
from collections import Counter


def load(p):
    out = {}
    for l in gzip.open(p, 'rt', encoding='utf-8'):
        d = json.loads(l)
        sc = json.loads(zlib.decompress(base64.b64decode(d['ajnas_sidecar']['z'])))
        for occ in sc['sidecar'].values():
            for r in occ:
                out[r['occurrence']] = r
    return out


def dec(es):
    """قرار الوقوع بصيغةٍ واحدة للقديم والجديد: القديم كتب DEFERRED_NO_EVENT_IDENTITY قراراً، والجديد DEFERRED بسببٍ مسمّى"""
    if not es:
        return 'NONE'
    d = es['decision'].split(' ')[0]
    if d == 'DEFERRED_NO_EVENT_IDENTITY':
        return 'DEFERRED_NO_EVENT_IDENTITY'
    if d == 'DEFERRED' and es.get('reason'):
        r = es['reason']
        return 'DEFERRED_NO_EVENT_IDENTITY' if r.startswith('DEFERRED_NO_EVENT_IDENTITY') else r
    return d


def main(po, pn, outj, outt):
    O, N = load(po), load(pn)
    trans = Counter(); rows = []; unexplained = []
    for occ in sorted(set(O) | set(N)):
        a, b = O.get(occ) or {}, N.get(occ) or {}
        ea, eb = a.get('event_side'), b.get('event_side')
        da, db = dec(ea), dec(eb)
        if da != db:
            trans[(da, db)] += 1
        la = {(l['event_id'], l['link_id']) for l in (ea or {}).get('links') or []}
        lb = {(l['event_id'], l['link_id']) for l in (eb or {}).get('links') or []}
        for k in sorted(la - lb):
            why = db if db.startswith('DEFERRED') else ('CONTRACT_EXCLUDED' if (eb or {}).get('excluded_contract') else db)
            rows.append((occ, k[0], k[1], 'REMOVED', why, a.get('analysis_id'), (b or {}).get('analysis_selection_status')))
            if not why.startswith(('DEFERRED_ANALYSIS_NOT_SELECTED', 'DEFERRED_PATTERN_NOT_SELECTED', 'DEFERRED_SELECTED_WITHOUT', 'CONTRACT_EXCLUDED')):
                unexplained.append((occ, k))
        for k in sorted(lb - la):
            rows.append((occ, k[0], k[1], 'ADDED', db, None, (b or {}).get('analysis_selection_status')))
            unexplained.append((occ, k))
        for k in sorted(la & lb):
            rows.append((occ, k[0], k[1], 'KEPT', db, a.get('analysis_id'), (b or {}).get('analysis_selection_status')))
    kinds = Counter((r[3], r[4]) for r in rows)
    old_att = sum(len((r.get('event_side') or {}).get('links') or []) for r in O.values())
    new_att = sum(len((r.get('event_side') or {}).get('links') or []) for r in N.values())
    removed = [r for r in rows if r[3] == 'REMOVED']
    rep = dict(old_attachments=old_att, new_attachments=new_att, kept=sum(1 for r in rows if r[3] == 'KEPT'), removed=len(removed),
               added=sum(1 for r in rows if r[3] == 'ADDED'), by_kind={f'{k[0]}|{k[1]}': v for k, v in kinds.most_common()},
               removed_occurrences=len({r[0] for r in removed}), removed_old_analysis_id_null=sum(1 for r in removed if r[5] is None),
               kept_old_analysis_id_null=sum(1 for r in rows if r[3] == 'KEPT' and r[5] is None),
               occurrence_decision_transitions={f'{k[0]} → {k[1]}': v for k, v in trans.most_common()},
               unexplained=len(unexplained), unexplained_examples=unexplained[:20],
               example_1_5=[r for r in rows if r[0] == '1:5:w1.s0'])
    json.dump(rep, open(outj, 'w'), ensure_ascii=False, indent=1)
    with gzip.open(outt, 'wt', encoding='utf-8') as f:
        f.write('occurrence\tevent_id\tlink_id\ttransition\tnew_decision\told_analysis_id\tnew_analysis_selection_status\n')
        for r in rows:
            f.write('\t'.join('' if x is None else str(x) for x in r) + '\n')
    print(json.dumps({k: v for k, v in rep.items() if k not in ('unexplained_examples',)}, ensure_ascii=False))


if __name__ == '__main__':
    main(*sys.argv[1:5])
