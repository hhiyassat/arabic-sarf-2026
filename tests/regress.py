#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار الانحدار: سطر لكل كلمة (الخانات، والعوامل وحالاتها، والإعراب، والمقاطع)
يُقارَن بالنسخة المحفوظة في tests/golden/. كل سطر تغيّر يُعرض ليُفحص ويُعلَّل.

    python3 tests/regress.py              # قارن
    python3 tests/regress.py --update     # احفظ الناتج الحالي بعد فحص الفروق
    python3 tests/regress.py -f ملف.txt   # ملفات آيات أخرى (الافتراضي: verses*.txt)
"""
import argparse, difflib, glob, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.output_text import word_irab
from sarf.mood import op_mood

CAT = Catalog([os.path.join(HERE, 'operators_catalog.jsonl'),
               os.path.join(HERE, 'operators_catalog_split_vocalized.csv')])


def lines(verse):
    a = analyze(CAT, verse)
    out = [f'# {verse}']
    ops = {}
    for f in a['operators']:
        ops.setdefault(f['word_index'], []).append(
            f"{f['operator']}/{f['group']}:{f['status']}:{op_mood(f)}")
    for seg in a['segments']:
        wi = seg['word_index']
        slots = ' '.join(f"{s['text']}<{s['type']}>" for s in seg['slots'])
        irab = ' ; '.join(f'{t}: {r} [{st}]' for t, r, st in word_irab(a, wi))
        units = ' | '.join('.'.join(f"{x['syl']}={x['cv']}" for x in u.get('syllables') or []) or
                           f"{u['text']}={u['label']}" for u in seg['units'])
        out.append(f"{wi}\t{seg['word']}\t{slots}\t{' '.join(ops.get(wi, []))}\t{units}\t{irab}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-f', '--files', nargs='*')
    ap.add_argument('--update', action='store_true')
    args = ap.parse_args()
    files = args.files or sorted(glob.glob(os.path.join(HERE, 'verses*.txt')))
    changed = 0
    for fn in files:
        name = os.path.splitext(os.path.basename(fn))[0]
        gold = os.path.join(HERE, 'tests', 'golden', name + '.tsv')
        now = []
        for v in open(fn, encoding='utf-8'):
            if v.strip():
                now += lines(v.strip())
        if args.update or not os.path.exists(gold):
            open(gold, 'w', encoding='utf-8').write('\n'.join(now) + '\n')
            print(f'حُفظ {gold}')
            continue
        old = open(gold, encoding='utf-8').read().splitlines()
        diff = list(difflib.unified_diff(old, now, name + ' (المحفوظ)', name + ' (الحالي)', n=0, lineterm=''))
        if diff:
            changed += 1
            print('\n'.join(diff))
    print('لا فرق' if not changed else f'تغيّر {changed} ملف')
    sys.exit(1 if changed else 0)


if __name__ == '__main__':
    main()
