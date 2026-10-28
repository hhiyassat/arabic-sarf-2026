#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
corpus_audit.py — فحص المحلل على نصٍّ لم يُضبط عليه (FT12، Q04): المصحف برواية حفص (مصحف المجمّع).

    python3 corpus_audit.py                      # جزء عمّ (78–114)
    python3 corpus_audit.py --surahs 1-114       # المصحف كله
    python3 corpus_audit.py -o reports/corpus_audit.md

يُنزَّل النص مرة واحدة إلى data/quran_hafs.tsv (المجلد غير متتبَّع) من
github.com/fawazahmed0/quran-api (ara-quranuthmanihaf، مصدره qurancomplex.gov.sa).
يعدّ: الانهيار، والمقاطع المرفوضة، وحالات الحكم، والعلاقات المخالفة لعلامتها، ويسرد أمثلتها.
"""
import argparse, collections, json, os, sys, time, traceback, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.output_text import word_irab

URL = 'https://raw.githubusercontent.com/fawazahmed0/quran-api/1/editions/ara-quranuthmanihaf.json'
DATA = os.path.join(HERE, 'data', 'quran_hafs.tsv')


def load():
    if not os.path.exists(DATA):
        os.makedirs(os.path.dirname(DATA), exist_ok=True)
        with urllib.request.urlopen(URL, timeout=120) as r:
            d = json.load(r)['quran']
        with open(DATA, 'w', encoding='utf-8') as f:
            for x in d:
                f.write(f"{x['chapter']}\t{x['verse']}\t{x['text'].strip()}\n")
    return [(int(a), int(b), t) for a, b, t in (l.rstrip('\n').split('\t') for l in open(DATA, encoding='utf-8'))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--surahs', default='78-114')
    ap.add_argument('-o', '--out', default=os.path.join(HERE, 'reports', 'corpus_audit.md'))
    ap.add_argument('--examples', type=int, default=15)
    args = ap.parse_args()
    lo, hi = (int(x) for x in args.surahs.split('-')) if '-' in args.surahs else (int(args.surahs),) * 2
    verses = [(s, v, t) for s, v, t in load() if lo <= s <= hi]
    cat = Catalog([os.path.join(HERE, 'operators_catalog.jsonl'),
                   os.path.join(HERE, 'operators_catalog_split_vocalized.csv')])
    C = collections.Counter()
    ex = collections.defaultdict(list)
    t0 = time.time()
    for s, v, text in verses:
        ref = f'{s}:{v}'
        try:
            a = analyze(cat, text)
        except Exception as e:                                   # noqa: BLE001
            C['انهيار'] += 1
            ex['انهيار'].append(f'{ref} {e!r} {traceback.format_exc(limit=1).strip()[-120:]}')
            continue
        for k, n in a['syll']['counts'].items():
            C['مقطع ' + k] += n
        for f in a['operators']:
            C['حالة ' + f['status']] += 1
            if f['status'] == 'accepted':
                ex[f"مقبول {f['operator']} (مج {f['group']})"].append(f"{ref} {a['segments'][f['word_index']]['word']}")
        for r in a['relations']:
            if r['consistent'] is False:
                C['علاقة تخالف علامتها'] += 1
                ex['علاقة تخالف علامتها'].append(
                    f"{ref} {r['operator']} (مج {r['group']}) ← {r['target']['text']}: متوقَّع {r['expected']}، مكتوب {r['observed']}")
        for seg in a['segments']:
            for u in seg['units']:
                for x in u.get('syllables') or []:
                    if x['verdict'] != 'OK':
                        C['مقطع مرفوض'] += 1
                        ex['مقطع مرفوض'].append(f"{ref} {seg['word']}: {x['syl']} {x['cv']} {x['verdict']}")
            for wi in [seg['word_index']]:
                for _, role, st in word_irab(a, wi):
                    C['سطر إعراب'] += 1
    L = [f'# فحص المحلل على المصحف (السور {lo}–{hi})', '',
         f'- الآيات: {len(verses)}، الزمن: {time.time() - t0:.0f} ث',
         f'- النص: مصحف المجمّع برواية حفص، من `{URL}`', '', '## الأعداد', '', '| البند | العدد |', '|---|---|']
    L += [f'| {k} | {n} |' for k, n in sorted(C.items())]
    for k in ('انهيار', 'مقطع مرفوض', 'علاقة تخالف علامتها'):
        if ex[k]:
            L += ['', f'## {k} ({len(ex[k])})', ''] + [f'- {e}' for e in ex[k][:200]]
    L += ['', '## أمثلة المقبول بحسب العامل', '']
    for k in sorted((k for k in ex if k.startswith('مقبول')), key=lambda k: -len(ex[k])):
        L.append(f"- **{k[6:]}** ({len(ex[k])}): " + '، '.join(ex[k][:args.examples]))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print(f'كُتب {args.out}: {len(verses)} آية، انهيار {C["انهيار"]}، مقاطع مرفوضة {C["مقطع مرفوض"]}')
    sys.exit(1 if C['انهيار'] else 0)


if __name__ == '__main__':
    main()
