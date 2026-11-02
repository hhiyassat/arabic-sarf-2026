# -*- coding: utf-8 -*-
"""سجلٌّ لكل مرشّح عاملٍ في المصحف (jsonl): موضعه وأداته ومجموعته وحكمه، والمتوقَّع والمكتوب، ودليل الحكم.

لا مرجع خارجياً فيه: هو ناتج التحليل وحده، للمقارنة بين نسختين (tools/compare_runs.py).
    python3 tools/dump_operators.py OUT.jsonl [--jobs N]
"""
import sys, os, json, argparse
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
ap = argparse.ArgumentParser()
ap.add_argument('out')
ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
args = ap.parse_args()
ROWS = [(int(x[0]), int(x[1]), x[2]) for x in
        (l.rstrip('\n').split('\t') for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'))]


def job(s):
    from sarf.analyze_cache import analyze_cached
    from sarf.catalog import Catalog
    cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
    out = []
    for s_, v, text in [r for r in ROWS if r[0] == s]:
        a = analyze_cached(cat, text)
        for c in a['operators']:
            r = c.get('relation') or {}
            t = r.get('target') or {}
            j = c.get('judgement') or {}
            out.append(dict(loc=f'{s_}:{v}:{c["word_index"] + 1}', word=c['word'], op=c['operator'], group=c.get('group'),
                            slot=(c.get('slot') or {}).get('index'), st=c['status'],
                            target=f"{t['word_index'] + 1}/{t.get('slot')}" if t else None, target_text=t.get('text'),
                            expected=r.get('expected'), observed=r.get('observed'), consistent=r.get('consistent'),
                            note=r.get('note'), why=(c.get('reject_reason') if c['status'] == 'blocked' else j.get('proof') if c['status'] == 'accepted' else j.get('deferred_because')),
                            rivals=j.get('rivals')))
    return out


if __name__ == '__main__':
    import multiprocessing as mp
    R = []
    with mp.get_context('fork').Pool(args.jobs) as P:
        for o in P.imap_unordered(job, range(1, 115)):
            R += o
    R.sort(key=lambda r: ([int(x) for x in r['loc'].split(':')], r['slot'] if r['slot'] is not None else -1, r['op'], str(r['group'])))
    with open(args.out, 'w', encoding='utf-8') as f:
        for r in R:
            f.write(json.dumps(r, ensure_ascii=False, default=str, sort_keys=True) + '\n')
    print(len(R), 'مرشّح عامل ←', args.out)
