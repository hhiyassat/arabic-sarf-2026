#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/eval_idha.py — قياس قرار «إذا» الفجائية (idha_reading) بمدوّنة QAC مرجعاً للقياس وحده (وسم SUR)، لا مدخلاً.

لكل «إِذَا» يليها ضميرٌ منفصل في المصحف: قرار المحلّل (FUJAIYYA/AMBIGUOUS)، ووسم QAC في موضعها؛ ولكل «إِذَا» موسومةٍ SUR في QAC
هل ولّد المحلّل مرشّحها (القرينة) أصلاً. → الدقة والاستدعاء بحدّ ويلسون الأدنى 95%.

    PYTHONHASHSEED=0 python3 tools/eval_idha.py [--json out.json]
"""
import argparse, json, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def wilson_low(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json')
    args = ap.parse_args()
    from sarf.catalog import Catalog
    from sarf.analyze import analyze
    from sarf import quran_source
    from sarf.algebra import idha_reading
    CAT = Catalog([os.path.join(ROOT, 'operators_catalog.jsonl'), os.path.join(ROOT, 'operators_catalog_split_vocalized.csv')])
    sur = {}
    for l in open(os.path.join(ROOT, 'data', 'quran-morphology.txt'), encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) > 3 and p[3].startswith('SUR'):
            s_, v_, w_, _ = (int(x) for x in p[0].split(':'))
            sur.setdefault((s_, v_), []).append(w_)
    rows, R = [], {(a, b): t for a, b, t in quran_source.rows()}
    for (s_, v_), t in R.items():
        if 'ذَا' not in t and 'ذَآ' not in t:
            continue
        a = analyze(CAT, t, quran_source.uthmani_mode())
        for f in a['operators']:
            r = idha_reading(a, f)
            if r:
                rows.append(dict(loc=f'{s_}:{v_}', word=f['word_index'] + 1, decision=r['decision'], evidence=r['evidence'],
                                 after=r['after_pronoun'], madi_after=r['madi_after'],
                                 qac_sur=(f['word_index'] + 1) in sur.get((s_, v_), [])))
    ours = {(x['loc'], x['word']) for x in rows}
    fuj = [x for x in rows if x['decision'] == 'FUJAIYYA']
    tp = sum(1 for x in fuj if x['qac_sur'])
    qac_all = [(f'{s_}:{v_}', w_) for (s_, v_), ws in sur.items() for w_ in ws]
    missed = [q for q in qac_all if q not in ours]
    found = [q for q in qac_all if q in {(x['loc'], x['word']) for x in fuj}]
    rep = dict(reference='QAC v0.4 وسم SUR (للقياس وحده)', cue_occurrences=len(rows), fujaiyya=len(fuj),
               ambiguous=sum(1 for x in rows if x['decision'] == 'AMBIGUOUS'),
               precision=dict(k=tp, n=len(fuj), wilson_low=wilson_low(tp, len(fuj))),
               recall=dict(k=len(found), n=len(qac_all), wilson_low=wilson_low(len(found), len(qac_all))),
               qac_sur_without_cue=missed, false_positive=[x for x in fuj if not x['qac_sur']], rows=rows,
               note='الاستدعاء يقيس القرينة (الضمير بعد «إذا») مع القرار؛ وما وسمته QAC فجائيةً بلا ضميرٍ بعدها خارج القرينة أصلاً')
    if args.json:
        json.dump(rep, open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"القرينة {len(rows)}، والفجائية {len(fuj)}، والملتبس {rep['ambiguous']}؛ الدقة {tp}/{len(fuj)} (ويلسون {rep['precision']['wilson_low']:.3f})؛ "
          f"الاستدعاء {len(found)}/{len(qac_all)} (ويلسون {rep['recall']['wilson_low']:.3f})؛ وسم SUR بلا قرينة: {missed}")
    return rep


if __name__ == '__main__':
    main()
