# -*- coding: utf-8 -*-
"""
sarf.align — ربط كل عامل بخانته في كلمته، وبعلاقته بمعموله (sarf.segment).
العوامل لا تُقطَّع، فلا مقاطع لها.
"""
from . import syllabify as cv


def align(found, segs, rels):
    for f in found:
        seg = segs[f['word_index']]
        slot = next((s for s in seg['slots'] if s['type'] == 'عامل'
                     and [f['operator'], f['group']] in [list(o) for o in s['operators']]), None)
        f['slot'] = None if slot is None else dict(index=slot['index'], unit=slot['unit'], text=slot['text'])
        f['relation'] = next((r for r in rels if r['word_index'] == f['word_index'] and
                              r['operator'] == f['operator'] and r['group'] == f['group']), None)
    return found


# ---------- للتوافق ----------
def syllables_by_word(res):
    by_word = {}
    for rend, pat, verdict, ws in res['rows']:
        key = ws[0] if ws else -1
        by_word.setdefault(key, []).append(dict(syl=rend, cv=pat, verdict=verdict))
    return by_word

def isolated_cv(form):
    """تقطيع صيغة منفردة كما كُتبت"""
    r = cv.run(form)
    return [dict(syl=rend, cv=pat) for rend, pat, _, _ in r['rows']]
