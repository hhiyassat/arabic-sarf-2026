# -*- coding: utf-8 -*-
"""
sarf.numbering — ترقيم المقطع بالأرقام بدل CV (تجربة صاحب النظرية).

الحروف تسعة وعشرون (حكم صاحب النظرية): الألف إلى الياء ثم الهمزة:
    ا1 ب2 ت3 ث4 ج5 ح6 خ7 د8 ذ9 ر10 ز11 س12 ش13 ص14 ض15 ط16 ظ17 ع18 غ19 ف20 ق21 ك22 ل23 م24 ن25 ه26 و27 ي28 ء29
والحركات بعدها لئلا تختلط بها: الفتحة 30، والضمة 31، والكسرة 32؛ والسكون 0 (السكون أو غياب الحركة).

- حروف المد الثلاثة ليست حروفاً: المد هو الحركة مكرَّرة. فالألف فتحتان (قَا = 21 30 30)،
  والواو بعد الضمة ضمتان (لُو = 23 31 31)، والياء بعد الكسرة كسرتان (قِي = 21 32 32).
  والواو والياء بعد الفتحة حرفان (يَوْ = 28 30 27 0).
- التنوين حركةٌ يُشار إليها بعلامة «ن» (بٌ = 2 31ن)؛ فالنص لا يكتب نوناً، ونون التنوين صوتٌ لا رسم.
- صور الهمزة كلها 29، والتاء المربوطة 3، والمشدَّد حرفان أولهما ساكن.
- الألف (1) لا تقع خليةً في المرسوم: هي مدٌّ أو وصلٌ أو كرسيّ همزة أو زائدة.
"""
from .chars import FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN, DAGGER_ALIF, letters

ALPHABET = 'ابتثجحخدذرزسشصضطظعغفقكلمنهويء'
LETTER_NO = {L: i for i, L in enumerate(ALPHABET, 1)}
HAMZA_NO = LETTER_NO['ء']
LETTER_NO.update({'أ': HAMZA_NO, 'إ': HAMZA_NO, 'ؤ': HAMZA_NO, 'ئ': HAMZA_NO, 'ة': 3})
VOWEL_NO = {FATHA: 30, DAMMA: 31, KASRA: 32}
TANWIN_MARK = 'ن'
SUKUN_NO = 0
TANWIN = {FATHATAN: FATHA, DAMMATAN: DAMMA, KASRATAN: KASRA}
MADD_OF = {'ا': FATHA, 'ى': FATHA, 'و': DAMMA, 'ي': KASRA}


def encode(text):
    """→ [أرقام] لنصٍّ مشكول (مقطع أو كلمة)"""
    out = []
    last_vowel = None
    for L, marks in letters(text):
        if L == 'آ':                                   # همزة ومدّة: ءَا
            out += [HAMZA_NO, VOWEL_NO[FATHA], VOWEL_NO[FATHA]]
            last_vowel = FATHA
            continue
        if L in MADD_OF and not marks and last_vowel == MADD_OF[L]:
            out.append(VOWEL_NO[last_vowel])           # حرف المد: الحركة مكرَّرة
            last_vowel = None
            continue
        if L == 'ا':                                   # ألف بلا حركة في غير موضع المد: لا تُنطق
            continue
        n = LETTER_NO.get(L)
        if n is None:
            continue
        if SHADDA in marks:
            out += [n, SUKUN_NO]                       # المشدَّد حرفان: الأول ساكن
        out.append(n)
        vowel = next((m for m in (FATHA, DAMMA, KASRA) if m in marks), None)
        tanwin = next((TANWIN[m] for m in TANWIN if m in marks), None)
        if tanwin:
            out.append(f'{VOWEL_NO[tanwin]}{TANWIN_MARK}')   # التنوين: الحركة موسومةً، بلا نون
            last_vowel = tanwin
        elif vowel:
            out.append(VOWEL_NO[vowel])
            last_vowel = vowel
            if DAGGER_ALIF in marks and vowel == FATHA:
                out.append(VOWEL_NO[FATHA])            # الألف الخنجرية مدٌّ: فتحتان
                last_vowel = None
        else:
            out.append(SUKUN_NO)                       # السكون أو غياب الحركة
            last_vowel = None
    return out


def code(text):
    """الأرقام نصّاً: «21 30 30»"""
    return ' '.join(str(n) for n in encode(text))


def syllables_code(sylls):
    """مقاطع الوحدة: «21 30 30 . 23 31 31»"""
    return ' . '.join(code(s['syl']) for s in sylls)
