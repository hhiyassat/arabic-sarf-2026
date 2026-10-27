# -*- coding: utf-8 -*-
"""
sarf.align — ربط كل عامل بمقاطع كلمته.
"""
from .chars import SUKUN
from .match import match_letters
from . import syllabify as cv

def syllables_by_word(res):
    by_word = {}
    for rend, pat, verdict, ws in res['rows']:
        key = ws[0] if ws else -1
        by_word.setdefault(key, []).append(dict(syl=rend, cv=pat, verdict=verdict))
    return by_word

def isolated_cv(form):
    """تقطيع العامل منفرداً كما كُتب — لمعرفة بنيته المقطعية الذاتية"""
    r = cv.run(form)
    return [dict(syl=rend, cv=pat) for rend, pat, _, _ in r['rows']]

def align(found, by_word, words):
    for f in found:
        if f['method'] == 'multi_word':
            a, b = f['words_span']
            f['syllables'] = [s for w in range(a, b) for s in by_word.get(w, [])]
            continue
        sy = by_word.get(f['word_index'], [])
        off = f['char_span'][0]
        # بعد عاطفة متحركة (وَ/فَ) يبدأ العامل بالمقطع الثاني، إلا إن كان ساكناً فيُغلق مقطع العاطفة (فَلْ)
        idx = 0
        if off == 1:
            op_marks = match_letters(words[f['word_index']])[1][1]
            idx = 0 if SUKUN in op_marks else 1
        if f['method'].startswith('proclitic'):
            f['syllables'] = sy[idx:idx + 1]       # السابقة = مقدمة مقطع واحد من الكلمة المضيفة
        elif f['method'].startswith('fused_prefix'):
            f['syllables'] = sy[idx:idx + len(isolated_cv(f['operator']))]
        else:
            # كلمة كاملة، أو عامل + لاحقة (تُعرض مقاطع العامل ولاحقته معاً)
            f['syllables'] = sy[idx:]
        f['cv'] = ' '.join(s['cv'] for s in f['syllables'])
        f['isolated'] = isolated_cv(f['operator'])
    for f in found:
        f.setdefault('cv', ' '.join(s['cv'] for s in f['syllables']))
        f.setdefault('isolated', isolated_cv(f['operator']))
    return found
