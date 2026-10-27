# -*- coding: utf-8 -*-
"""
sarf.output_text — الناتج النصي وJSON لتحليل الآية.
"""
from . import syllabify as cv

def text_report(a):
    out = [f"الآية:    {a['verse']}", f"المُطبَّع: {a['normalized']}"]
    out.append('')
    out.append(f"العوامل المستخرجة: {len(a['operators'])}")
    out.append('-' * 80)
    for f in a['operators']:
        top = f['meanings'][0]
        out.append(f"[{f['word_index']}] {f['word']}  ⟵  {f['operator']}  (مج {f['group']}: {f['operator_class']})")
        out.append(f"     طريقة={f['method']}  ثقة={f['confidence']}  الحكم={f.get('status', 'candidate')}"
                   + (f"  بقية={f['host_rest']}" if f.get('host_rest') else '')
                   + (f"  ملاحظة: {f['note']}" if f.get('note') else ''))
        if f.get('reject_reason'):
            out.append(f"     سبب الرفض: {f['reject_reason']}")
        out.append(f"     المقاطع في السياق: {' . '.join(s['syl'] for s in f['syllables'])}   [{f['cv']}]")
        out.append(f"     العامل منفرداً:    {' . '.join(s['syl'] for s in f['isolated'])}   "
                   f"[{' '.join(s['cv'] for s in f['isolated'])}]")
        out.append(f"     المعاني المرشحة:  " + ' | '.join(
            f"{m['label']} ({m['prior'] if m['prior'] is not None else '—'})" for m in f['meanings']))
        out.append(f"     العمل: {top['effect']}")
        out.append('')
    out.append('=' * 80)
    out.append(cv.report(a['syll']))
    out.append('')
    out.append(cv.word_view(a['syll']))
    return '\n'.join(out)

def to_json(a):
    d = {k: v for k, v in a.items() if k != 'syll'}
    r = a['syll']
    d['syllable_counts'] = dict(r['counts'])
    d['cv_line'] = r['cv_line']
    d['events'] = dict(r['events'])
    return d
