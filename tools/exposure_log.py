#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/exposure_log.py — سجل التعرّض للشواهد (FT12، SARF_COMPREHENSIVE_REPAIR_04 §٩).

يجمع كل آيةٍ ذُكرت (برقمها أو بمداها) في: الشيفرة والاختبارات والأدوات، وملفات الاستخراج والتغطية والجرد، والتقارير والمراجعات
(reports/ وHANDOFF وتسليمات ~/Downloads)، ورسائل المالك إلى الوكيل في سجل الجلسة (إن مُرِّر)؛ ثم يعلّم من المجموعة المحجوبة
السابقة ما تعرّض منها «مكشوفاً» بتاريخه ومصدره، ولا يستبدل به غيره.

    python3 tools/exposure_log.py --out exposure.json [--transcript الجلسة.jsonl] [--downloads ~/Downloads]
"""
import argparse, glob, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = re.compile(r'(?<![\d.:])(\d{1,3}):(\d{1,3})(?:\s*[–-]\s*(\d{1,3}))?(?![\d:])')
AR_DIG = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')


def refs(text, valid):
    out = set()
    for m in REF.finditer(text.translate(AR_DIG)):
        s_, a_, b_ = int(m.group(1)), int(m.group(2)), m.group(3)
        for v_ in range(a_, (int(b_) if b_ and int(b_) >= a_ and int(b_) - a_ < 300 else a_) + 1):
            if (s_, v_) in valid:
                out.add((s_, v_))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--transcript')
    ap.add_argument('--downloads')
    args = ap.parse_args()
    sys.path.insert(0, ROOT)
    from sarf import quran_source
    valid = {(s_, v_) for s_, v_, _ in quran_source.rows()}
    cats = {
        'code': ['sarf/*.py'], 'tests': ['tests/*.py', 'tests/golden/*', 'tests/heldout/*.md'], 'tools': ['tools/*.py', 'tools/**/*.py'],
        'extraction_coverage_inventory': ['coverage/*', 'approved/*', 'data_fixes/*', 'lexicon/*.md', '*.md', 'verses*.txt'],
        'reports_reviews': ['reports/*.html', 'reports/*.md', 'reports/**/*.md', 'reports/**/*.json'],
    }
    exp = {}
    for cat, pats in cats.items():
        for pat in pats:
            for f in glob.glob(os.path.join(ROOT, pat), recursive=True):
                if not os.path.isfile(f) or os.path.getsize(f) > 30_000_000 or f.endswith('witness_provenance.json'):
                    continue
                try:
                    t = open(f, encoding='utf-8', errors='ignore').read()
                except Exception:
                    continue
                for k in refs(t, valid):
                    exp.setdefault(k, set()).add(f'{cat}:{os.path.relpath(f, ROOT)}')
    if args.downloads and os.path.isdir(args.downloads):
        for f in glob.glob(os.path.join(args.downloads, '**', '*'), recursive=True):
            if os.path.isfile(f) and f.endswith(('.md', '.html', '.txt', '.csv')) and os.path.getsize(f) < 30_000_000:
                for k in refs(open(f, encoding='utf-8', errors='ignore').read(), valid):
                    exp.setdefault(k, set()).add(f'deliveries:{os.path.relpath(f, args.downloads)}')
    owner = {}
    if args.transcript and os.path.exists(args.transcript):
        for line in open(args.transcript, encoding='utf-8', errors='ignore'):
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get('type') != 'user':
                continue
            c = (ev.get('message') or {}).get('content')
            txt = c if isinstance(c, str) else ' '.join(x.get('text', '') for x in c or [] if isinstance(x, dict) and x.get('type') == 'text')
            if not txt or txt.startswith('Stop hook') or '<task-notification>' in txt:
                continue
            for k in refs(txt, valid):
                owner.setdefault(k, ev.get('timestamp'))
                exp.setdefault(k, set()).add('owner_notes:session_transcript')
    wp = json.load(open(os.path.join(ROOT, 'tests', 'heldout', 'witness_provenance.json'), encoding='utf-8'))
    held = wp['held_out']['verses']
    status = []
    for x in held:
        k = tuple(int(p_) for p_ in x.split(':'))
        src = sorted(exp.get(k, ()))
        status.append(dict(verse=x, status='EXPOSED' if src else 'HELD_OUT_UNREAD', sources=src, owner_note_time=owner.get(k)))
    rep = dict(method='كل ذكرٍ لرقم آيةٍ أو مداها في المصادر المسمّاة تعرّض؛ والمدى يُفكّ آياتٍ', categories=sorted(cats) + ['deliveries', 'owner_notes'],
               exposed_count=len(exp), exposed=sorted(f'{s_}:{v_}' for s_, v_ in exp),
               by_category={c: sum(1 for v in exp.values() if any(x.startswith(c + ':') for x in v)) for c in list(cats) + ['deliveries', 'owner_notes']},
               held_out_previous=dict(seed=wp['held_out']['seed'], size=len(held), status=status,
                                      exposed=[x['verse'] for x in status if x['status'] == 'EXPOSED'],
                                      note='المكشوف يبقى في القائمة بتاريخ تعرّضه ومصدره، ولا يُستبدل به غيره، ولا يُعاد إعلان استقلال القياس به'),
               sources={f'{s_}:{v_}': sorted(v) for (s_, v_), v in sorted(exp.items())})
    json.dump(rep, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"آياتٌ متعرَّضٌ لها {len(exp)}؛ ومن المحجوبة السابقة ({len(held)}) مكشوفة {len(rep['held_out_previous']['exposed'])}: "
          + '، '.join(rep['held_out_previous']['exposed']))
    return rep


if __name__ == '__main__':
    main()
