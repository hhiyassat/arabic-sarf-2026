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


def mudgham(toks, i):
    """حرفٌ في الرسم لا خلية له قبل المشدَّد: الياء الزائدة رسماً قبل الياء المشدَّدة (بِأَييِّكُمُ)، كالمرسوم عليه
    الصفر المستدير (D21؛ حكم صاحب النظرية). أما سائر العاري قبل المشدَّد (عَبَدتُّمۡ، يُوَجِّههُّ) فخليةٌ ساكنة
    كما كُتب، والمشدَّد بعده خليتان (حكم صاحب النظرية: النص لا الأداء). واللام الشمسية لها حكمها (D22)."""
    if i + 1 >= len(toks):
        return False
    L, m = toks[i]
    return L == 'ي' and not (m & (MARKS - {MADDA_MARK, SUKUN})) and toks[i + 1][0] == 'ي' and SHADDA in toks[i + 1][1] \
        and i > 0 and vowel(toks[i - 1][1]) != KASRA
