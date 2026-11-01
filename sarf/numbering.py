# -*- coding: utf-8 -*-
"""
sarf.numbering — ترقيم المقطع بالأرقام بدل CV (حكم صاحب النظرية، 29 أكتوبر).

الخلية ⟨حرف، حالة⟩ رقمٌ واحد من 1 إلى 116 (29 حرفاً × 4 حالات):
    Code(c_i, h_j) = 4(i − 1) + j + 1
- i: ا1 ب2 ت3 ث4 ج5 ح6 خ7 د8 ذ9 ر10 ز11 س12 ش13 ص14 ض15 ط16 ظ17 ع18 غ19 ف20 ق21 ك22 ل23 م24 ن25 ه26 و27 ي28 ء29
- j: السكون (أو غياب الحركة) 0، الفتحة 1، الكسرة 2، الضمة 3  (h0 = ∅، h1 = a، h2 = i، h3 = o)
فالرقم يعرّف محتوى الخلية، ويُسترجع منه الحرف والحالة: i = ⌊(Code − 1)/4⌋ + 1، j = (Code − 1) mod 4.

- حرف المدّ خليةٌ بلا حركة: الألف ⟨ا، ∅⟩ = 1 (قَا = 82 1، والخنجرية ألف)، والواو ⟨و، ∅⟩ = 105، والياء ⟨ي، ∅⟩ = 109.
- التنوين حالةُ حركته موسومةً بـ«ن»، بلا نون (بٌ = 8ن).
- المشدَّد خليتان أولاهما ساكنة (رَبِّ = 38 5 7).
- صور الهمزة كلها ء (29)، والتاء المربوطة تاء (3)، والألف المقصورة بعد الفتح ألف.
"""
from .chars import FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN, DAGGER_ALIF, letters

ALPHABET = 'ابتثجحخدذرزسشصضطظعغفقكلمنهويء'
LETTER_NO = {L: i for i, L in enumerate(ALPHABET, 1)}
HAMZA_NO = LETTER_NO['ء']
LETTER_NO.update({'أ': HAMZA_NO, 'إ': HAMZA_NO, 'ؤ': HAMZA_NO, 'ئ': HAMZA_NO, 'ة': 3})
STATE_NO = {None: 0, FATHA: 1, KASRA: 2, DAMMA: 3}           # h0 = ∅، h1 = a، h2 = i، h3 = o
TANWIN_MARK = 'ن'
TANWIN = {FATHATAN: FATHA, DAMMATAN: DAMMA, KASRATAN: KASRA}
MADD_OF = {'ا': FATHA, 'ى': FATHA, 'و': DAMMA, 'ي': KASRA}


def cell_code(i, vowel=None):
    """Code(c_i, h_j) = 4(i − 1) + j + 1"""
    return 4 * (i - 1) + STATE_NO[vowel] + 1


def decode(code_):
    """الرقم ← (الحرف، الحالة): i = ⌊(Code − 1)/4⌋ + 1، j = (Code − 1) mod 4"""
    n = int(str(code_).rstrip(TANWIN_MARK))
    i, j = (n - 1) // 4 + 1, (n - 1) % 4
    return ALPHABET[i - 1], ('∅', 'a', 'i', 'o')[j]


ALIF = cell_code(LETTER_NO['ا'])                              # 1


def encode(text):
    """→ [أرقام الخلايا] لنصٍّ مشكول (مقطع أو كلمة)"""
    out = []
    last_vowel = None
    for L, marks in letters(text):
        if L == 'آ':                                   # همزة ومدّة: ءَا
            out += [cell_code(HAMZA_NO, FATHA), ALIF]
            last_vowel = None
            continue
        if L in MADD_OF and not marks and last_vowel == MADD_OF[L]:
            out.append(ALIF if L in 'اى' else cell_code(LETTER_NO[L]))   # حرف المدّ خليةٌ بلا حركة
            last_vowel = None
            continue
        if L == 'ا':                                   # ألف بلا حركة في غير موضع المد: لا تُنطق
            continue
        n = LETTER_NO.get(L)
        if n is None:
            continue
        vowel = next((m for m in (FATHA, DAMMA, KASRA) if m in marks), None)
        tanwin = next((TANWIN[m] for m in TANWIN if m in marks), None)
        if SHADDA in marks:
            out.append(cell_code(n))                   # المشدَّد خليتان: الأولى ساكنة
        if tanwin:
            out.append(f'{cell_code(n, tanwin)}{TANWIN_MARK}')   # التنوين: الحالة موسومةً، بلا نون
            last_vowel = tanwin
        else:
            out.append(cell_code(n, vowel))
            last_vowel = vowel
            if DAGGER_ALIF in marks and vowel == FATHA:
                out.append(ALIF)                       # الألف الخنجرية ألفُ مدّ
                last_vowel = None
    return out


def code(text):
    """الأرقام نصّاً: «82 1»"""
    return ' '.join(str(n) for n in encode(text))


def syllables_code(sylls):
    """مقاطع الوحدة: «82 1 . 92 105»"""
    return ' . '.join(code(s['syl']) for s in sylls)
