# -*- coding: utf-8 -*-
"""
sarf.analyze — تحليل آية: تطبيع ← مطابقة ← نفي بالكتابة ← تقطيع ← ربط.
"""
from .normalize import uthmani_normalize
from .match import extract
from .evidence import reject_candidates
from .align import syllables_by_word, align
from . import syllabify as cv

def analyze(cat, verse, uthmani='auto'):
    """النص كما هو: التقطيع على النص المطبَّع نفسه، كل كلمة مستقلة، بلا وصل ولا وقف"""
    isk = {'auto': None, 'on': True, 'off': False}[uthmani]   # auto←None (تلقائي) / on←True / off←False
    text = uthmani_normalize(verse, implicit_sukun=isk)
    words, found = extract(cat, text)
    found = reject_candidates(found, words)
    res = cv.run(text)
    found = align(found, syllables_by_word(res), words)
    return dict(verse=verse, normalized=text, syllabified_text=text,
                words=words, operators=found, syll=res)
