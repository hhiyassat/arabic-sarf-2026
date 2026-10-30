#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/reconcile_roots.py — مصالحة جذور الأفعال بين نسختين بهويات الوقوعات (مراجعة التقرير الرابعة ١):
ما انتقل من التأجيل إلى القبول، وما انتقل من القبول إلى التأجيل، وما تغيّر جذره أو وزنه، مع الجذر والوزن
ودليل الاختيار قبل التعديل وبعده، وجذر QAC.

    SARF_ROOT_DUMP=old.jsonl python3 tools/eval_root.py   # في نسخة قبل التعديل
    SARF_ROOT_DUMP=new.jsonl python3 tools/eval_root.py   # في النسخة الحالية
    python3 tools/reconcile_roots.py old.jsonl new.jsonl  # → reports/root_reconciliation.json
"""
import sys, json, os, collections

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'


def load(path):
    out, occ = {}, collections.Counter()
    for line in open(path, encoding='utf-8'):
        r = json.loads(line)
        k = (r['loc'], r['text'])
        occ[k] += 1
        out[k + (occ[k],)] = r
    return out


def brief(r):
    sel = r.get('selection') or {}
    return dict(status=r['status'], root=r.get('root'), form=r.get('form'), level=r.get('level'),
                reason=(r.get('reason') or '')[:120], decision=sel.get('decision'),
                candidates=[f"{c['root']}/{c['form']} ({c['tier']}{'، مطابق' if c.get('exact') else ''})"
                            for c in sel.get('candidates', [])][:6])


old, new = load(sys.argv[1]), load(sys.argv[2])
C = collections.Counter()
rows = collections.defaultdict(list)
for k in sorted(set(old) | set(new)):
    a, b = old.get(k), new.get(k)
    if a is None or b is None:
        C['غير مقابَل'] += 1
        continue
    gold = b.get('gold')
    if a['status'] == b['status'] and a.get('root') == b.get('root') and a.get('form') == b.get('form'):
        C['لم يتغيّر'] += 1
        continue
    if a['status'] != 'accepted' and b['status'] == 'accepted':
        kind = 'من التأجيل إلى القبول: ' + ('صحيح' if b.get('root') == gold else 'مخالف لـQAC')
    elif a['status'] == 'accepted' and b['status'] != 'accepted':
        kind = 'من القبول إلى التأجيل: ' + ('كان صحيحاً' if a.get('root') == gold else 'كان مخالفاً لـQAC')
    elif a['status'] == 'accepted':
        kind = 'تغيّر التحليل المقبول: ' + ('صار صحيحاً' if b.get('root') == gold else
                                            'صار مخالفاً' if a.get('root') == gold else 'مخالف قبل وبعد')
    else:
        kind = 'مؤجَّل قبل وبعد بسببٍ آخر'
    C[kind] += 1
    rows[kind].append(dict(loc=k[0], text=k[1], gold=f"{gold}/{b.get('gold_form')}", before=brief(a), after=brief(b)))
out = dict(counts=dict(C), rows={k: v[:40] for k, v in rows.items()}, totals={k: len(v) for k, v in rows.items()})
json.dump(out, open(H + 'reports/root_reconciliation.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, v in sorted(C.items(), key=lambda x: -x[1]):
    print(k, v)
