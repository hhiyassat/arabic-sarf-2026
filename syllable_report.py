#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تقرير HTML: الكلمات ومقاطعها.

يستورد منطق التقطيع من extract_operators (Catalog / analyze / syllables_by_word)
ولا يكرّره. لكل آية: جدول صفٌّ لكل كلمة (الرقم، الكلمة، المقاطع ملوّنة حسب النوع،
نمط CV، العوامل)، مع ملخّص أنواع المقاطع للآية، وملخّص إجمالي في رأس الصفحة.

النطاق: تحليل نصّي فقط (أنماط CV). لا أحكام تجويد صوتية.

الاستعمال:
  python3 syllable_report.py -f verses.txt verses_inna.txt verses_innama.txt -o syllable_report.html
  python3 syllable_report.py "نص آية" -o out.html [--uthmani auto|on|off]
"""
import sys, os, html, argparse
from collections import Counter, OrderedDict

import extract_operators as E
from cv_syllabifier import SIX

# أنواع المقاطع التي نعدّها/نلوّنها: الستة + OTHER + POISON
TYPES = SIX + ['OTHER', 'POISON']

# أسماء عربية موجزة للعرض في المفتاح والملخّص
TYPE_LABEL = OrderedDict([
    ('CV',    'CV — ساكن+حركة'),
    ('CVV',   'CVV — ساكن+مدّ'),
    ('CVC',   'CVC — مغلق قصير'),
    ('CVVC',  'CVVC — مغلق بمدّ'),
    ('CVCC',  'CVCC — مغلق بساكنين'),
    ('CVVCC', 'CVVCC — مغلق بمدّ وساكنين'),
    ('OTHER', 'OTHER — نمط خارج الستة'),
    ('POISON','POISON — تشكيل ناقص'),
])


def syl_type(cv):
    """نوع المقطع لأغراض العدّ/التلوين: ستّة معروفة، أو POISON، أو OTHER."""
    if cv == 'POISON':
        return 'POISON'
    if cv in SIX:
        return cv
    return 'OTHER'


def esc(s):
    return html.escape('' if s is None else str(s))


CSS = """
:root{
  --bg:#ffffff; --fg:#1a1a1a; --muted:#666; --card:#f6f7f9; --border:#d9dde3;
  --th:#eceff3; --warnbg:#fff3cd; --warnfg:#7a5b00; --poisonbg:#f8d7da; --poisonfg:#842029;
  --c-CV:#1565c0;    --c-CVV:#00838f;   --c-CVC:#6a1b9a;
  --c-CVVC:#ef6c00;  --c-CVCC:#ad1457;  --c-CVVCC:#283593;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#15181d; --fg:#e8eaed; --muted:#9aa0a6; --card:#1e232b; --border:#333a44;
    --th:#242b34; --warnbg:#4a3d00; --warnfg:#ffe08a; --poisonbg:#5a1f24; --poisonfg:#ffb3b8;
    --c-CV:#64b5f6;    --c-CVV:#4dd0e1;   --c-CVC:#ce93d8;
    --c-CVVC:#ffb74d;  --c-CVCC:#f48fb1;  --c-CVVCC:#9fa8da;
  }
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:var(--bg); color:var(--fg);
  font-family:"Noto Naskh Arabic","Geeza Pro","Scheherazade New","Segoe UI",system-ui,sans-serif;
  font-size:20px; line-height:1.9; padding:20px 16px 60px;
}
h1{font-size:28px;margin:0 0 6px}
h2{font-size:23px;margin:34px 0 8px;border-top:2px solid var(--border);padding-top:16px}
.muted{color:var(--muted);font-size:16px;line-height:1.7}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin:12px 0}
.orig{font-size:24px;line-height:2.1}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:20px}
th,td{border:1px solid var(--border);padding:8px 10px;text-align:right;vertical-align:top}
th{background:var(--th);font-size:17px;font-weight:700;white-space:nowrap}
td.num{color:var(--muted);text-align:center;font-size:17px;width:3ch}
td.word{font-size:24px;white-space:nowrap}
td.cv{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:16px;direction:ltr;text-align:left;color:var(--muted)}
.chip{display:inline-block;margin:2px 3px;padding:3px 10px;border-radius:8px;font-size:21px;
  border:1px solid currentColor;line-height:1.6}
.chip small{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;opacity:.75;direction:ltr;margin-right:5px}
.t-CV{color:var(--c-CV)}    .t-CVV{color:var(--c-CVV)}   .t-CVC{color:var(--c-CVC)}
.t-CVVC{color:var(--c-CVVC)}.t-CVCC{color:var(--c-CVCC)} .t-CVVCC{color:var(--c-CVVCC)}
.t-OTHER{color:var(--warnfg);background:var(--warnbg);border-color:var(--warnfg)}
.t-POISON{color:var(--poisonfg);background:var(--poisonbg);border-color:var(--poisonfg);font-weight:700}
.op{display:block;font-size:16px;line-height:1.7;margin:2px 0;padding-right:8px;border-right:3px solid var(--border)}
.op b{font-size:19px}
.op .meta{color:var(--muted)}
.summary{font-size:16px;margin:8px 0;display:flex;flex-wrap:wrap;gap:6px}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;border:1px solid var(--border)}
.pill b{font-family:ui-monospace,Menlo,Consolas,monospace}
.key{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.total{font-size:18px}
.total .pill{font-size:17px;padding:4px 12px}
"""


def chips_html(sylls):
    """شارات المقاطع ملوّنة حسب النوع."""
    out = []
    for s in sylls:
        t = syl_type(s['cv'])
        out.append(
            f'<span class="chip t-{esc(t)}" title="{esc(s["cv"])}">'
            f'{esc(s["syl"])}<small>{esc(s["cv"])}</small></span>'
        )
    return ''.join(out) if out else '<span class="muted">—</span>'


def ops_html(ops):
    if not ops:
        return '<span class="muted">—</span>'
    out = []
    for f in ops:
        bits = [f'<b>{esc(f["operator"])}</b>']
        bits.append(f'<span class="meta">مج {esc(f["group"])}: {esc(f["operator_class"])}</span>')
        meth = esc(f['method'])
        if f.get('host_rest'):
            meth += f' · بقية={esc(f["host_rest"])}'
        bits.append(f'<span class="meta">{meth}</span>')
        out.append('<span class="op">' + ' — '.join(bits) + '</span>')
    return ''.join(out)


def summary_pills(counter, extra_class=''):
    out = []
    for t in TYPES:
        n = counter.get(t, 0)
        if n == 0 and t in ('OTHER', 'POISON'):
            continue
        cls = f't-{t}' if t in ('OTHER', 'POISON') and n else ''
        out.append(f'<span class="pill {cls}"><b>{esc(t)}</b>: {n}</span>')
    return f'<div class="summary {extra_class}">' + ''.join(out) + '</div>'


def verse_counter(by_word):
    c = Counter()
    for wi in by_word:
        for s in by_word[wi]:
            c[syl_type(s['cv'])] += 1
    return c


def verse_html(a, idx):
    by_word = E.syllables_by_word(a['syll'])
    n_words = a['syll']['n_words']
    raw_words = a['syll']['raw_words']
    words = a['words']

    # عوامل مفهرسة بحسب رقم الكلمة
    ops_by_word = {}
    for f in a['operators']:
        ops_by_word.setdefault(f['word_index'], []).append(f)

    rows = []
    for wi in range(n_words):
        word = words[wi] if wi < len(words) else raw_words[wi]
        sylls = by_word.get(wi, [])
        cvpat = ' '.join(s['cv'] for s in sylls)
        rows.append(
            '<tr>'
            f'<td class="num">{wi}</td>'
            f'<td class="word">{esc(word)}</td>'
            f'<td>{chips_html(sylls)}</td>'
            f'<td class="cv">{esc(cvpat)}</td>'
            f'<td>{ops_html(ops_by_word.get(wi, []))}</td>'
            '</tr>'
        )

    head = [f'<h2>الآية {idx}</h2>',
            f'<div class="card"><div class="orig">{esc(a["verse"])}</div>']
    head.append(f'<div class="muted">المُطبَّع: {esc(a["normalized"])}</div>')
    if a['syllabified_text'] != a['normalized']:
        head.append(f'<div class="muted">للتقطيع: {esc(a["syllabified_text"])}</div>')
    head.append('</div>')

    table = (
        '<table><thead><tr>'
        '<th>#</th><th>الكلمة</th><th>المقاطع</th><th>نمط CV</th><th>العوامل</th>'
        '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
    )

    c = verse_counter(by_word)
    total = sum(c.values())
    summ = (f'<div class="muted">مجموع المقاطع: {total}'
            f' (SYLLABLES={a["syll"]["n_syll"]})</div>' + summary_pills(c))
    return '\n'.join(head) + table + summ, c


def build_html(analyses):
    body = []
    grand = Counter()
    sections = []
    for i, a in enumerate(analyses, 1):
        s, c = verse_html(a, i)
        grand += c
        sections.append(s)


    # مفتاح الألوان
    key = ['<div class="key">']
    for t in TYPES:
        cls = f't-{t}'
        key.append(f'<span class="chip {cls}">{esc(t)}<small>{esc(TYPE_LABEL[t].split(" — ")[-1])}</small></span>')
    key.append('</div>')

    header = [
        '<h1>تقرير الكلمات ومقاطعها</h1>',
        '<div class="muted">النص كما هو: كل كلمة تُقطَّع مستقلّة بحركاتها المكتوبة، بلا وصل ولا وقف؛ والتنوين حركة واحدة من جنسه.</div>',
        f'<div class="muted">عدد الآيات: {len(analyses)} — النطاق: أنماط CV فقط (بلا أحكام تجويد صوتية).</div>',
        '<div class="card">',
        '<div class="muted">الملخّص الإجمالي:</div>',
        summary_pills(grand, 'total'),
        '<div class="muted" style="margin-top:6px">مفتاح الألوان:</div>',
        ''.join(key),
        '</div>',
    ]

    doc = [
        '<!doctype html>',
        '<html lang="ar" dir="rtl"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>تقرير الكلمات ومقاطعها</title>',
        f'<style>{CSS}</style></head><body>',
        '\n'.join(header),
        '\n'.join(sections),
        '</body></html>',
    ]
    return '\n'.join(doc), grand


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

    cat = E.Catalog(args.catalog)
    analyses = [E.analyze(cat, v, uthmani=args.uthmani) for v in verses]
    doc, grand = build_html(analyses)

    with open(args.out, 'w', encoding='utf-8') as fh:
        fh.write(doc)

    tot = sum(grand.values())
    print(f'كُتب {args.out}: {len(analyses)} آية، مجموع المقاطع = {tot}')
    print('الملخّص الإجمالي: ' + '  '.join(f'{t}={grand.get(t,0)}' for t in TYPES if grand.get(t,0)))


if __name__ == '__main__':
    main()
