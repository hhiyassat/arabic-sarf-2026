# -*- coding: utf-8 -*-
"""
sarf.chars — الحروف والعلامات: الثوابت، وتفكيك الكلمة إلى (حرف، علامات)، وأدوات الحروف.
لا يعتمد على أي وحدة أخرى.
"""
FATHA, DAMMA, KASRA = 'َ', 'ُ', 'ِ'
SUKUN, SHADDA = 'ْ', 'ّ'
FATHATAN, DAMMATAN, KASRATAN = 'ً', 'ٌ', 'ٍ'
MADDA_MARK, DAGGER_ALIF, TATWEEL = 'ٓ', 'ٰ', 'ـ'
MARKS = {FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN, MADDA_MARK, DAGGER_ALIF}

VOWELS = {FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN}

# ---------- Stage 0: tokenize ----------
def tokenize(word):
    """→ [(letter, set(marks))]"""
    out = []
    for ch in word:
        if ch == TATWEEL:
            continue
        if ch in MARKS:
            if out:
                out[-1][1].add(ch)
        else:
            out.append([ch, set()])
    return out

def letters(word):
    """→ [(letter, frozenset(marks))] مع حذف التطويل"""
    out = []
    for ch in word:
        if ch == TATWEEL:
            continue
        if ch in MARKS:
            if out:
                out[-1][1].add(ch)
        else:
            out.append([ch, set()])
    return [(l, frozenset(m)) for l, m in out]

LOOSE = str.maketrans({'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ى': 'ي', 'ة': 'ه'})

def plain(toks, loose=False):
    s = ''.join(l for l, _ in toks)
    return s.translate(LOOSE) if loose else s

def vowel(marks):
    for m in marks:
        if m in VOWELS:
            return m
    return None

def vowel_of(marks):
    for m in (FATHA, DAMMA, KASRA):
        if m in marks:
            return m
    return None

def tanwin_of(marks):
    for m in (FATHATAN, DAMMATAN, KASRATAN):
        if m in marks:
            return m
    return None

def strip_marks(s):
    return ''.join(ch for ch in s if ch not in MARKS)

_strip_marks = strip_marks
