# -*- coding: utf-8 -*-
"""
sarf.normalize — التطبيع:
  uthmani_normalize(text)  الرسم العثماني → إملائي يفهمه المقطِّع (مستوى النص)
  normalize(word, ev)      مستوى الكلمة قبل التقطيع: الألف المحذوفة خطاً، والمدّة، وتوحيد الهمزات
"""
import re, unicodedata
from collections import OrderedDict

from .chars import SUKUN, SHADDA, MADDA_MARK, FATHA, letters, tokenize

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
    'ۧ': 'ي',          # الياء الصغيرة (إِبْرَٰهِـۧمَ)
}
# رموز الأداء تُحذف: واو الصلة وياؤها الصغيرتان (ۥ ۦ: الصلة الصغرى والكبرى)، وعلامة المدّ (ٓ)،
# والألف الخنجرية على الألف المقصورة (مُوسَىٰ ← مُوسَى). وهي داخلة في UTHMANI_DROP إلا الخنجرية.
DAGGER_ON_MAQSURA = re.compile('(ى[\u064B-\u0652]*)\u0670')
UTHMANI_DROP = set(chr(c) for c in range(0x06D6, 0x06EE)) - set(UTHMANI_MAP) | {'۟', 'ـ', '\u0653'}
MADD_AFTER_FATHA = re.compile('(\u064E\u0651?|\u0651\u064E)\u0622')

LONE_ALIF = re.compile('([\u064B\u08F0][\u0651\u06D6-\u06ED]*)\\s+(ا[\u06D6-\u06ED]*)(?=\\s|$)')
KFGQPC_MAP = {0x08F0: 0x064B, 0x08F1: 0x064C, 0x08F2: 0x064D, 0x200F: None, 0x065C: None}
# الهمزة المنفصلة عن كرسيّها بحركة: على المطّة ← ء (مَـَٔابًا)، وعلى الياء غير المنقوطة ← ئ (لِقَاۤىِٕ)،
# وعلى الواو ← ؤ (ٱللُّؤۡلُوِٕ)، وعلى الألف الخنجرية ← أ (فَٱدَّٰرَٰٔتُمۡ)؛ والحركة بينهما تبقى
ZERO = '\u06DF'                                       # الصفر المستدير (حرف زائد)
ALIF_ZERO = re.compile('ا' + SUKUN)
HAMZA_SEAT = {'\u0640': 'ء', '\u0649': 'ئ', '\u064A': 'ئ', '\u0648': 'ؤ', '\u0670': 'أ'}
HAMZA_ON_TATWEEL = re.compile('([\u0640\u0649\u064A\u0648])([\u064B-\u0652\u0670]*)[\u0654\u0655]|(\u0670)()\u0654')

MADD_LETTERS = set('اويىآ')
UTHMANI_SIGNS = {'ٱ', '\u0653', '\u0670'} | set(chr(c) for c in range(0x06D6, 0x06EE))   # والمدّة والخنجرية

def drop_zero_letters(text):
    """الصفر المستدير (۟) فوق حرف علّة يدل على زيادته فلا يُنطق وصلاً ولا وقفاً (اصطلاح ضبط المصحف):
    يُحذف الحرف (جِا۟ىٓءَ ← جِىٓءَ، أُو۟لَٰٓئِكَ ← أُلَٰٓئِكَ)، إلا الألف بعد الواو، فهي الألف الفارقة
    بعد واو الجماعة، ويحتاجها المقشِّر دليلاً على الفعل (كَفَرُوا۟)؛ وتُحذف علامتها وحدها."""
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if i + 1 < len(text) and text[i + 1] == ZERO and ch in 'اويى':
            k = len(out)
            while k and ('\u064B' <= out[k - 1] <= '\u0655' or out[k - 1] == '\u0670' or '\u06D6' <= out[k - 1] <= '\u06ED'):
                k -= 1
            prev = out[k - 1] if k else ''
            # واو الجماعة لا حركة عليها (كَفَرُوا۟)؛ أما ٱلرِّبَوٰا۟ فواوها مفتوحة
            prev_marks = [c for c in out[k:] if '\u064B' <= c <= '\u0652' or c == '\u0670']
            if ch == 'ا' and prev == 'و' and not prev_marks:
                out.append(ch)
            i += 2
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def uthmani_normalize(text, implicit_sukun=None):
    """
    implicit_sukun: في الرسم العثماني الحرف العاري (غير المدّي) ساكن مُخفى/مدغم (تَدَايَنتُم).
    None ⇒ يُفعَّل تلقائياً إن ظهرت علامات عثمانية في النص.
    """
    # ألفُ تنوين النصب مفصولةً بمسافة (عيبٌ في بعض نسخ مصحف المجمّع الرقمية: صَفࣰّ اۖ): لا كلمة هي ألف وحدها
    text = LONE_ALIF.sub(r'\1\2', text)
    if implicit_sukun is None:                         # يُكشف قبل أي تعديل (ومنه NFC الذي يدمج ٓ في آ)
        implicit_sukun = any(ch in UTHMANI_SIGNS or ord(ch) in KFGQPC_MAP or ch in '\u06E1\u0654\u0655' for ch in text)
    text = unicodedata.normalize('NFC', text)
    # ترميز مصحف المجمّع (KFGQPC): التنوين «المفتوح» صورةٌ للتنوين نفسه (إخفاء/إدغام)،
    # والهمزة فوق المطّة همزةٌ على السطر (مَـَٔابًا ← مَءَابًا)؛ وعلامة الاتجاه تُحذف
    text = text.translate(KFGQPC_MAP)
    # السكون ْ في مصحف المجمّع صفرٌ مستدير على الحرف الزائد (كَفَرُواْ، أُوْلَٰٓئِكَ)، وسكونه ۡ:
    # فإن وُجد ۡ في النص فكل ْ صفر؛ وعلى الألف صفرٌ في كل حال (الألف لا تحمل سكوناً)
    text = text.replace('أٓ', 'آ')                     # الهمزة والمدّة: ٱلۡأٓخِرَةِ
    if '\u06E1' in text:
        text = text.replace(SUKUN, ZERO)
    else:
        text = ALIF_ZERO.sub('ا' + ZERO, text)
    text = drop_zero_letters(text)
    text = HAMZA_ON_TATWEEL.sub(lambda m: HAMZA_SEAT[m.group(1) or m.group(3)] + (m.group(2) or ''), text)
    text = unicodedata.normalize('NFC', text)          # الهمزة فوق الحرف بعد حركته: يُـِٔ ← ئِ
    # «آ» بعد فتحة = ألف مدّ عليها علامة المدّ العثمانية لا همزة: إِنَّمَآ، جَآءَ (وتبقى همزةً بعد ساكن: ٱلْقُرْآنُ)
    text = MADD_AFTER_FATHA.sub(r'\1ا', text)
    text = DAGGER_ON_MAQSURA.sub(r'\1', text)
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
                # الحرف العاري قبل حرفٍ مشدَّد مدغمٌ فيه إدغاماً كاملاً (اصطلاح ضبط المصحف):
                # يبقى عارياً ليحذفه المقطِّع (لِّلنَّاسِ، عَٰهَدتَّ، يُدۡرِككُّمُ)؛ ولام التعريف بعد الألف كذلك
                mudgham = i + 1 < len(toks) and SHADDA in toks[i + 1][1]
                if not (L == 'ل' and prev_al) and not mudgham:
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
