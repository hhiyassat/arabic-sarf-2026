#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/import_quran_simple.py — تحويل quran-simple-enhanced.txt (سطرٌ لكل آية، بلا أرقام) إلى data/quran_simple.tsv.

الأحكام (المالك، 3 نوفمبر 2026)، وكلها مسجَّلة في data/quran_simple_ops.json، والمصدر محفوظٌ كما هو في العمود الرابع:
  ١ الترقيم بالترتيب على أعداد آيات السور في رواية حفص (6236)؛ ويُرفض الملف إن خالف العدد.
  ٢ البسملة الملصقة بأول الآية الأولى (غير الفاتحة والتوبة) تُفصل: تُطابَق بحروفها وحركاتها مع البسملة في الآية 1:1،
     أو بصورتها «بِّسْمِ» بالشدّة على الباء (95:1، 97:1)؛ ولا يُفصل غير ذلك.
  ٣ «<sel>» يُخرج من النص المحلَّل، ويُسجَّل موضعه: بعد أيّ كلمة (رقمها في النص المحلَّل).
  لا يُغيَّر حرفٌ ولا حركة في النص غير ذلك.

    python3 tools/import_quran_simple.py [--src data/quran-simple-enhanced.txt]
"""
import argparse, hashlib, json, os, re

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# أعداد آيات السور في رواية حفص (العدّ الكوفي)، 114 سورة، مجموعها 6236
AYAT = [7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128, 111, 110, 98, 135, 112, 78, 118, 64, 77, 227, 93, 88,
        69, 60, 34, 30, 73, 54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60, 49, 62, 55, 78, 96, 29, 22, 24, 13,
        14, 11, 11, 18, 12, 12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29, 19, 36, 25, 22, 17, 19, 26, 30, 20, 15, 21,
        11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6]
SEL = '<sel>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=os.path.join(H, 'data', 'quran-simple-enhanced.txt'))
    ap.add_argument('--out', default=os.path.join(H, 'data', 'quran_simple.tsv'))
    ap.add_argument('--ops', default=os.path.join(H, 'data', 'quran_simple_ops.json'))
    a = ap.parse_args()
    assert len(AYAT) == 114 and sum(AYAT) == 6236
    raw = open(a.src, 'rb').read()
    lines = [l for l in raw.decode('utf-8').split('\n') if l != '']
    if len(lines) != 6236:
        raise SystemExit(f'عدد الأسطر {len(lines)} لا 6236: لا يُرقَّم')
    basmala = lines[0]
    variants = {basmala, basmala.replace('\u0628\u0650', '\u0628\u0651\u0650', 1)}   # «بِّسْمِ»: شدّة الإدغام على الباء (95:1، 97:1)
    ops, out, k = dict(source=dict(path=os.path.relpath(a.src, H), sha256=hashlib.sha256(raw).hexdigest(), lines=len(lines)),
                       rules=['ترقيمٌ بالترتيب على أعداد حفص', 'فصل البسملة الملصقة بالآية الأولى', 'إخراج <sel> مع حفظ موضعه'],
                       basmala=[], sel=[], untouched_first_verses=[]), [], 0
    for s, n in enumerate(AYAT, 1):
        for v in range(1, n + 1):
            src = lines[k]
            k += 1
            t = src
            if v == 1 and s not in (1, 9):
                hit = next((b for b in variants if t.startswith(b + ' ')), None)
                if hit:
                    t = t[len(hit) + 1:]
                    ops['basmala'].append(dict(ref=f'{s}:{v}', prefix=hit))
                else:
                    ops['untouched_first_verses'].append(f'{s}:{v}')
            words, sels = [], []
            for w in t.split(' '):
                if w == SEL:
                    sels.append(len(words))          # بعد الكلمة رقم len(words) (من 1)
                elif w:
                    words.append(w)
            if SEL in ' '.join(words):
                raise SystemExit(f'{s}:{v}: «<sel>» ملتصقٌ بكلمة')
            for after in sels:
                ops['sel'].append(dict(ref=f'{s}:{v}', after_word=after))
            if '\t' in src:
                raise SystemExit(f'{s}:{v}: مسافة جدولة في المصدر')
            out.append(f'{s}\t{v}\t{" ".join(words)}\t{src}')
    open(a.out, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    ops['output'] = dict(path=os.path.relpath(a.out, H), sha256=hashlib.sha256(open(a.out, 'rb').read()).hexdigest(), verses=len(out))
    ops['counts'] = dict(basmala_separated=len(ops['basmala']), sel=len(ops['sel']), untouched_first_verses=len(ops['untouched_first_verses']))
    json.dump(ops, open(a.ops, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(ops['counts'], ops['output'])


if __name__ == '__main__':
    main()
