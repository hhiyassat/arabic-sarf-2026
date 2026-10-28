# -*- coding: utf-8 -*-
"""
sarf.output_text — الناتج النصي وJSON لتحليل الآية.
"""
from . import syllabify as cv
from .segment import unit_view
from .status import STATUS_AR, BLOCKED


def word_irab(a, wi):
    """→ [(نص الخانة، عبارة الإعراب، حالة العامل)] للكلمة wi، من علاقات العوامل غير الممنوعة"""
    status = {(f['word_index'], f['operator'], f['group']): f['status'] for f in a['operators']}
    out = []
    for r in a.get('relations', []):
        st = STATUS_AR.get(status.get((r['word_index'], r['operator'], r['group'])), '')
        if r['word_index'] == wi and r.get('zaida'):
            slot = a['segments'][wi]['slots'][r['slot']]['text']
            out.append((slot, 'حرف جر زائد للتوكيد (ترجيح صاحب النظرية)', st))
        k = r.get('khabar')
        if k and k['word_index'] == wi:
            out.append((k['text'], f"خبر «{r['operator']}» مقدَّم في محلّ نصب", st))
        t = r['target']
        if t and t['word_index'] == wi and r.get('role'):
            out.append((t['text'], r['role'], st))
    return out


def relation_text(r):
    """العامل ← المعمول: الحالة المتوقَّعة والعلامة المكتوبة"""
    if r is None:
        return '—'
    if r['note'] and r['target'] is None:
        return r['note']
    t = r['target']
    if t is None:
        return 'لا معمول في النص'
    out = f"{t['text']} ({t['type']})"
    if r['expected']:
        out += f"  متوقَّع: {r['expected']}"
    if r['observed'] == 'محلاً':
        out += f"  في محلّ {r['expected']}" if r['expected'] else '  مبني'
    elif r['observed']:
        out += f"  مكتوب: {r['observed']}"
    if r['consistent'] is not None:
        out += '  ✓' if r['consistent'] else '  ✗ يخالف العلامة المكتوبة'
    if r['note']:
        out += f"  — {r['note']}"
    return out

def text_report(a):
    out = [f"الآية:    {a['verse']}", f"المُطبَّع: {a['normalized']}"]
    out.append('')
    out.append(f"العوامل المستخرجة: {len(a['operators'])}")
    out.append('-' * 80)
    for f in a['operators']:
        top = f['meanings'][0]
        out.append(f"[{f['word_index']}] {f['word']}  ⟵  {f['operator']}  (مج {f['group']}: {f['operator_class']})")
        out.append(f"     طريقة={f['method']}  ثقة={f['confidence']}  الحكم={STATUS_AR.get(f.get('status'), '')}"
                   + (f"  بقية={f['host_rest']}" if f.get('host_rest') else '')
                   + (f"  ملاحظة: {f['note']}" if f.get('note') else ''))
        if f.get('reject_reason'):
            out.append(f"     سبب المنع: {f['reject_reason']}")
        j = f.get('judgement')
        if j:
            if j['proof']:
                out.append(f"     الأدلة: {' | '.join(j['proof'])}")
            if j['deferred_because']:
                out.append(f"     سبب التأجيل: {' | '.join(j['deferred_because'])}")
        if f.get('slot'):
            out.append(f"     الخانة: [{f['slot']['text']}] عامل — لا يُقطَّع")
        if f.get('status') != BLOCKED:
            out.append(f"     المعمول: {relation_text(f.get('relation'))}")
        out.append(f"     المعاني المرشحة:  " + ' | '.join(
            f"{m['label']} ({m['prior'] if m['prior'] is not None else '—'})" for m in f['meanings']))
        out.append(f"     العمل: {top['effect']}")
        out.append('')
    out.append('=' * 80)
    out.append(cv.report(a['syll']))
    out.append('')
    out.append(unit_view(a['segments']))
    irab = [(w['word'], x) for w in a['segments'] for x in word_irab(a, w['word_index'])]
    if irab:
        out.append('')
        out.append('الإعراب:')
        for word, (slot, role, st) in irab:
            out.append(f"  {word:<16} {slot}: {role}  [{st}]")
    return '\n'.join(out)

def to_json(a):
    d = {k: v for k, v in a.items() if k != 'syll'}
    r = a['syll']
    d['syllable_counts'] = dict(r['counts'])
    d['cv_line'] = r['cv_line']
    d['events'] = dict(r['events'])
    return d
