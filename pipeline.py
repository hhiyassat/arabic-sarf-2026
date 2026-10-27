#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline.py — تشغيل مراحل المحلل وفحص ناتج كل مرحلة (الكود في sarf/pipeline.py).

الاستعمال:
    python3 pipeline.py --stages                          # المراحل: ما تحتاجه وما تضيفه
    python3 pipeline.py "نص آية"                           # كل المراحل، وسجل كل مرحلة
    python3 pipeline.py -f verses.txt --until match       # توقّف بعد المطابقة
    python3 pipeline.py "نص آية" --skip evidence          # تجاوز مرحلة
    python3 pipeline.py "نص آية" --dump match             # ناتج مرحلة بعينها JSON
"""
import sys, os, json, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sarf.catalog import Catalog
from sarf.pipeline import Pipeline, STAGES


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description='تشغيل مراحل المحلل وفحص ناتجها')
    ap.add_argument('verse', nargs='*', help='نص الآية (أو استعمل -f)')
    ap.add_argument('-f', '--file', nargs='+', help='ملف أو أكثر، آية في كل سطر')
    ap.add_argument('--stages', action='store_true', help='اعرض المراحل وما تحتاجه وما تضيفه')
    ap.add_argument('--until', help='آخر مرحلة تُنفَّذ')
    ap.add_argument('--skip', nargs='+', default=[], help='مراحل تُتجاوز')
    ap.add_argument('--dump', help='اطبع حقول هذه المرحلة JSON بعد التشغيل')
    ap.add_argument('--uthmani', default='auto', choices=['auto', 'on', 'off'])
    ap.add_argument('--catalog', nargs='+',
                    default=[p for p in (os.path.join(here, 'operators_catalog.jsonl'),
                                         os.path.join(here, 'operators_catalog_split_vocalized.csv'))
                             if os.path.exists(p)])
    args = ap.parse_args()

    if args.stages:
        for st in STAGES:
            print(f"{st!r:<55} {st.doc}")
        return

    verses = []
    if args.file:
        for path in args.file:
            with open(path, encoding='utf-8') as fh:
                verses += [l.strip() for l in fh if l.strip()]
    elif args.verse:
        verses = [' '.join(args.verse)]
    else:
        verses = [l.strip() for l in sys.stdin if l.strip()]

    pipe = Pipeline(Catalog(args.catalog))
    dump = {st.name: st for st in STAGES}.get(args.dump)
    if args.dump and dump is None:
        sys.exit(f"مرحلة غير معروفة: {args.dump}")
    for v in verses:
        try:
            ctx = pipe.run(v, args.uthmani, until=args.until, skip=args.skip)
        except (ValueError, RuntimeError) as e:
            sys.exit(str(e))
        print(f"الآية: {v}")
        for name, summary in ctx.log:
            print(f"  {name:<10} {summary}")
        if dump is not None:
            fields = dump.provides or ('candidates',)      # evidence تعدّل candidates في مكانها
            out = {f: getattr(ctx, f, None) for f in fields}
            print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
        print()


if __name__ == '__main__':
    main()
