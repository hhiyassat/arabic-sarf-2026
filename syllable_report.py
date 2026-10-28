#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
syllable_report.py — واجهة سطر الأوامر لتقرير HTML (الكود في sarf/output_html.py وsarf/mood.py).

النطاق: تحليل نصّي فقط (أنماط CV). لا أحكام تجويد صوتية.

الاستعمال:
  python3 syllable_report.py -f verses.txt verses_inna.txt verses_innama.txt -o syllable_report.html
  python3 syllable_report.py "نص آية" -o out.html [--uthmani auto|on|off]
"""
import sys, os, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.mood import MOOD, op_mood, has_inshai_operator   # noqa: F401
from sarf.output_html import TYPES, build_html


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description='تقرير HTML: الكلمات ومقاطعها')
    ap.add_argument('verse', nargs='*', help='نص الآية (أو استعمل -f)')
    ap.add_argument('-f', '--file', nargs='+', help='ملف أو أكثر، آية في كل سطر')
    ap.add_argument('-o', '--out', default='syllable_report.html', help='ملف HTML الناتج')
    ap.add_argument('--uthmani', default='auto', choices=['auto', 'on', 'off'],
                    help='المعاملة العثمانية: auto/on/off (كما في extract_operators.py)')
    ap.add_argument('--catalog', nargs='+',
                    default=[p for p in (os.path.join(here, 'operators_catalog.jsonl'),
                                         os.path.join(here, 'operators_catalog_split_vocalized.csv'))
                             if os.path.exists(p)])
    args = ap.parse_args()

    verses = []
    if args.file:
        for path in args.file:
            with open(path, encoding='utf-8') as fh:
                verses += [l.strip() for l in fh if l.strip()]
    elif args.verse:
        verses = [' '.join(args.verse)]
    else:
        verses = [l.strip() for l in sys.stdin if l.strip()]

    if not verses:
        sys.exit('لا آيات للمعالجة.')

    cat = Catalog(args.catalog)
    analyses = [analyze(cat, v, uthmani=args.uthmani) for v in verses]
    doc, grand = build_html(analyses, cat)

    with open(args.out, 'w', encoding='utf-8') as fh:
        fh.write(doc)

    tot = sum(grand.values())
    print(f'كُتب {args.out}: {len(analyses)} آية، مجموع المقاطع = {tot}')
    print('الملخّص الإجمالي: ' + '  '.join(f'{t}={grand.get(t,0)}' for t in TYPES if grand.get(t,0)))


if __name__ == '__main__':
    main()
