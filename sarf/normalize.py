# -*- coding: utf-8 -*-
"""
sarf.normalize — التطبيع:
  uthmani_normalize(text)  الرسم العثماني → إملائي يفهمه المقطِّع (مستوى النص)
  normalize(word, ev)      مستوى الكلمة قبل التقطيع: الألف المحذوفة خطاً، والمدّة، وتوحيد الهمزات
"""
import re, unicodedata
from collections import OrderedDict

from .chars import SUKUN, MADDA_MARK, FATHA, letters, tokenize

HAMZA_FORMS = {'أ': 'ء', 'إ': 'ء', 'ؤ': 'ء', 'ئ': 'ء', 'ء': 'ء'}

# قاموس مغلق: ألف محذوفة خطاً (تُدرَج قبل المعالجة)
LEXICAL_MADD = OrderedDict([
    ('ذَلِك', 'ذَالِك'),
    ('هَذَا', 'هَاذَا'),
    ('هَذِه', 'هَاذِه'),
    ('الرَّحْمَن', 'الرَّحْمَان'),
])

# ---------- Stage 0: Uthmani → إملائي يفهمه المقطِّع ----------
UTHMANI_MAP = {
    'ٱ': 'ا',          # ألف الوصل
    'ۡ': SUKUN,        # السكون العثماني (رأس الخاء)
    'ۥ': 'و',          # واو الصلة الصغيرة
    'ۦ': 'ي',          # ياء الصلة الصغيرة
    'ۧ': 'ي',          # الياء الصغيرة (إِبْرَٰهِـۧمَ)
}
UTHMANI_DROP = set(chr(c) for c in range(0x06D6, 0x06EE)) - set(UTHMANI_MAP) | {'۟', 'ـ'}
MADD_AFTER_FATHA = re.compile('(\u064E\u0651?|\u0651\u064E)\u0622')

MADD_LETTERS = set('اويىآ')
UTHMANI_SIGNS = {'ٱ'} | set(chr(c) for c in range(0x06D6, 0x06EE))

def uthmani_normalize(text, implicit_sukun=None):
    """
    implicit_sukun: في الرسم العثماني الحرف العاري (غير المدّي) ساكن مُخفى/مدغم (تَدَايَنتُم).
    None ⇒ يُفعَّل تلقائياً إن ظهرت علامات عثمانية في النص.
    """
    text = unicodedata.normalize('NFC', text)
    # «آ» بعد فتحة = ألف مدّ عليها علامة المدّ العثمانية لا همزة: إِنَّمَآ، جَآءَ (وتبقى همزةً بعد ساكن: ٱلْقُرْآنُ)
    text = MADD_AFTER_FATHA.sub(r'\1ا', text)
    if implicit_sukun is None:
        implicit_sukun = any(ch in UTHMANI_SIGNS for ch in text)
    out = []
    for ch in text:
        if ch in UTHMANI_MAP:
            out.append(UTHMANI_MAP[ch])
        elif ch in UTHMANI_DROP:          # ومنها ۠: تُحذف العلامة وتبقى الألف مدّاً كما رُسمت
            continue
        else:
            out.append(ch)
    text = ' '.join(''.join(out).split())
    if not implicit_sukun:
        return text
    words = []
    for w in text.split():
        toks = letters(w)
        rebuilt = []
        for i, (L, mk) in enumerate(toks):
            mk = set(mk)
            if not mk and L not in MADD_LETTERS and L != 'ة' and 'ء' <= L <= 'ي':
                prev_al = i > 0 and toks[i - 1][0] == 'ا'
                if not (L == 'ل' and prev_al):          # لام التعريف تبقى للمقطِّع
                    mk.add(SUKUN)
            rebuilt.append(L + ''.join(sorted(mk)))
        words.append(''.join(rebuilt))
    return ' '.join(words)

# ---------- Stage 1: Normalize ----------
def normalize(word, ev):
    for k, v in LEXICAL_MADD.items():
        if k in word:
            word = word.replace(k, v)
            ev['LEXICAL_MADD_INSERTION'] += 1
    word = word.replace('آ', 'ء' + FATHA + 'ا')            # المدّة
    if 'آ' in word:
        ev['MADDA_EXPANDED'] += 1
    toks = tokenize(word)
    for t in toks:
        if t[0] in HAMZA_FORMS and t[0] != 'ء':
            t[0] = 'ء'
            ev['HAMZA_UNIFIED'] += 1
        if MADDA_MARK in t[1]:
            t[1].discard(MADDA_MARK)
    return toks

normalize_word = normalize
