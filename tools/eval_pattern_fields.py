#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/eval_pattern_fields.py — قياس حقول الوزن الجديدة في المحلّل (lemma_pattern / realized_pattern) على dev.
أداةٌ منفصلة عن مقياس الجذر والوزن (tools/root_wazn_bench.py) ولا تعدّله: المحلّل يرى (id، word) وحدهما،
ثم تُقرأ الأجوبة بعد تجميد المخرج.

    PYTHONHASHSEED=0 python3 tools/eval_pattern_fields.py <dev_blind_input.tsv> <testset_all.tsv> <corrections.tsv> <out.json>
"""
import csv, collections, json, os, sys, unicodedata

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
sys.path.insert(0, os.path.join(H, 'tools'))
import root_wazn_bench as B


def main(inp, ref_path, corr_path, out):
    from sarf.root import morph
    rows = B.read_blind_input(inp)
    outs = {}
    for r in rows:                                   # المحلّل أولاً، بلا مرجع
        m = morph(r['word'])
        outs[r['id']] = dict(status=(m or {}).get('status'), root=(m or {}).get('root'), pattern=(m or {}).get('pattern'))
    _, ref = B.read_tsv(ref_path)                    # ثم المرجع
    ref = {x['id']: x for x in ref}
    corr = B.load_corrections(corr_path)
    C = collections.Counter()
    ex = collections.defaultdict(list)
    for i, o in outs.items():
        x = ref[i]
        if o['status'] != 'accepted' or o['root'] != x['root'] or not x['wazn']:
            continue
        if B.denominators_for(i, corr)['wazn'] != 'PROVISIONAL_REFERENCE_MAIN':
            continue
        p = o['pattern'] or {}
        rw = B.wazn_convention(x['wazn'])
        C['proven_with_ref_wazn'] += 1
        if p.get('lemma_pattern_status') == 'SELECTED':
            C['lemma_selected'] += 1
            ok = B.wazn_convention(p['lemma_pattern']) == rw
            C['lemma_selected_agree' if ok else 'lemma_selected_disagree'] += 1
            if not ok:
                ex['lemma_selected_disagree'].append(dict(id=i, word=x['word'], ref=x['wazn'], lemma=p['lemma_pattern'], realized=p.get('realized_pattern')))
        else:
            C['lemma_alternatives'] += 1
            C['ref_in_lemma_alternatives' if rw in {B.wazn_convention(q) for q in p.get('lemma_pattern_alternatives') or []} else 'ref_not_in_alternatives'] += 1
        real = p.get('realized_pattern')
        if real:
            C['realized_agree_with_ref_wazn' if B.wazn_convention(B.hfn_form_wazn(real)) == rw else 'realized_differs_from_ref_wazn'] += 1
    k, n = C['lemma_selected_agree'], C['lemma_selected']
    rep = dict(scope='dev، المقام الرئيسي المؤقت لحقول الوزن؛ صفوف جذرها مثبتٌ موافق ولها وزنٌ مرجعي', counts=dict(C),
               lemma_selected_precision=dict(k=k, n=n, value=round(k / n, 4) if n else None, wilson_low=B.wilson_low(k, n)),
               examples={k: v[:40] for k, v in ex.items()})
    json.dump(rep, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(rep['counts'], ensure_ascii=False), rep['lemma_selected_precision'])


if __name__ == '__main__':
    main(*sys.argv[1:])
