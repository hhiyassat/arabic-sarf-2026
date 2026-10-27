#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_operators.py — واجهة سطر الأوامر لاستخراج العوامل (الكود في sarf/).
    UthmaniNorm ∘ Match(catalog) ∘ Evidence ∘ Syllabify(verse) ∘ Align(operator → syllables)
يُبقي الأسماء القديمة للتوافق: eo.Catalog، eo.analyze، eo.uthmani_normalize، eo.letters، eo.LOOSE، eo.cv …

الاستعمال:
    python3 extract_operators.py "وَٱمْسَحُوا۟ بِرُءُوسِكُمْ"
    python3 extract_operators.py -f verse.txt [--catalog operators_catalog.jsonl operators_catalog_split_vocalized.csv] [--json]
"""
import sys, os, json, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sarf import syllabify as cv                           # noqa: F401
from sarf.chars import *                                   # noqa: F401,F403
from sarf.normalize import uthmani_normalize               # noqa: F401
from sarf.match import *                                   # noqa: F401,F403
from sarf.catalog import Catalog
from sarf.evidence import reject_candidates                # noqa: F401
from sarf.align import syllables_by_word, isolated_cv, align   # noqa: F401
from sarf.analyze import analyze
from sarf.output_text import text_report, to_json

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description='استخراج العوامل من الآية + التقطيع المقطعي')
    ap.add_argument('verse', nargs='*', help='نص الآية (أو استعمل -f)')
    ap.add_argument('-f', '--file', help='ملف يحوي آية في كل سطر')
    ap.add_argument('--catalog', nargs='+',
                    default=[p for p in (os.path.join(here, 'operators_catalog.jsonl'),
                                         os.path.join(here, 'operators_catalog_split_vocalized.csv'))
                             if os.path.exists(p)],
                    help='ملف أو أكثر (.jsonl/.csv)؛ الأول أساس وما بعده يضيف العوامل الغائبة فقط')
    ap.add_argument('--uthmani', default='auto', choices=['auto', 'on', 'off'],
                    help='المعاملة العثمانية (السكون الضمني): auto=تلقائي بوجود علامة عثمانية، on=دائماً، off=أبداً')
    ap.add_argument('--json', action='store_true', help='إخراج JSON Lines')
    args = ap.parse_args()

    cat = Catalog(args.catalog)
    if args.file:
        verses = [l.strip() for l in open(args.file, encoding='utf-8') if l.strip()]
    elif args.verse:
        verses = [' '.join(args.verse)]
    else:
        verses = [l.strip() for l in sys.stdin if l.strip()]

    for v in verses:
        a = analyze(cat, v, uthmani=args.uthmani)
        if args.json:
            print(json.dumps(to_json(a), ensure_ascii=False))
        else:
            print(text_report(a))
            print('\n' + '#' * 80 + '\n')
