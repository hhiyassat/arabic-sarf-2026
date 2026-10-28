# -*- coding: utf-8 -*-
"""
sarf.affix — مقشِّر الزوائد: هل الجذع فعل أم اسم، وما زوائده ولواحقه، وما علامة إعرابه.

القاعدة: الحرف جذري إلا أن يكون من حروف «سألتمونيها» (زوائد البنية) أو من اللواحق
(الضمائر المتصلة وعلامات الفعل). فلا يُقشَّر إلا ما في ZAWAID أو LAWAHIQ:
    حرف المضارعة       أ ن ي ت                  (من سألتمونيها)
    همزة الوصل         ا في أول فعل الأمر       (من سألتمونيها)
    نون الرفع          ـونَ ـينَ ـانِ
    واو الجماعة        ـوا (والألف الفارقة)
    نون التوكيد        ـنَّ ـنْ
    ضمير الرفع         ـْتُمْ ـْتُ ـْتَ ـْتِ ـْنَا  (بعد ساكن: الماضي)
    الضمير المتصل      ـهُ ـهِ ـكَ ـكُمْ ـهُمْ …  (لاحقة: يُنزع قبل الحكم)

الدليل القوي وحده يُثبت النوع:
    فعل: همزة وصل في أوله (غير أل والأسماء العشرة)، أو ألف فارقة بعد واو الجماعة،
         أو حرف مضارعة مع نون التوكيد أو نون الرفع أو السكون في آخره،
         أو ضمير رفع متحرك بعد ساكن (الماضي)
    اسم: تنوين، أو أل، أو تاء مربوطة
وما سوى ذلك لا يُحكم فيه (pos = None)، ويبقى حرف المضارعة وعلامة الآخر معلومة.
"""
from .chars import (FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN,
                    letters, plain)
from .match import PRON_SUFFIXES, match_letters, vocal_compatible

ZAWAID = set('سألتمونيها') | {'ء', 'إ', 'آ'}      # حروف الزيادة (والهمزة بصورها)
LAWAHIQ = set('هكنيوامت')                        # حروف اللواحق: الضمائر المتصلة وعلامات الفعل
MUDARI = {'أ', 'ن', 'ي', 'ت'}
TANWIN = {FATHATAN, DAMMATAN, KASRATAN}
WASL_NOUNS = {'اسم', 'ابن', 'ابنة', 'ابنم', 'امرؤ', 'امرئ', 'امرأ', 'امرأة', 'اثنان', 'اثنين',
              'اثنتان', 'اثنتين', 'است'}        # أسماء تبدأ بهمزة وصل
OBJ_SUFFIXES = sorted((s for s in PRON_SUFFIXES if s != 'ي'), key=lambda s: -len(letters(s)))
MIN_STEM = 3
MARK_MOOD = {FATHA: 'نصب', DAMMA: 'رفع', SUKUN: 'جزم'}
# ضمائر الرفع المنفصلة: صورتها تشبه الماضي مع ضمير (أَنْتَ = أَنْ + تَ) فتُستثنى
RAF_PRONOUNS = {'أنا', 'أنت', 'أنتما', 'أنتم', 'أنتن', 'هو', 'هي', 'هما', 'هم', 'هن', 'نحن'}


def _peelable(*letters_):
    """لا يُقشَّر حرف من خارج الزوائد واللواحق"""
    return all(L in ZAWAID or L in LAWAHIQ for L in letters_)

def stem_info(text):
    """→ dict(pos, kind, mood, prefix, suffix, object, evidence)
    pos: 'verb' | 'noun' | None؛ kind: 'mudari' | 'amr' | 'madi' | None
    mood: علامة آخر الفعل المضارع (رفع، نصب، جزم، أو «حذف النون»)، أو None"""
    toks = [(L, set(m)) for L, m in letters(text)]
    info = dict(pos=None, kind=None, mood=None, prefix=None, suffix=None, object=None, evidence=[])
    if not toks:
        return info
    ev = info['evidence']
    if plain(toks) in RAF_PRONOUNS:
        ev.append('ضمير رفع منفصل')
        return info
    # اسم: تنوين، أو أل، أو تاء مربوطة
    if toks[-1][1] & TANWIN:
        info['pos'] = 'noun'; ev.append('تنوين')
        return info
    if len(toks) > 2 and toks[0][0] == 'ا' and toks[1][0] == 'ل' and (not toks[1][1] or toks[1][1] == {SUKUN}):
        info['pos'] = 'noun'; ev.append('أل')
        return info
    if toks[-1][0] == 'ة':
        info['pos'] = 'noun'; ev.append('تاء مربوطة')
        return info
    # لاحقة: الضمير المتصل (مفعول به) يُنزع قبل الحكم
    for suf in OBJ_SUFFIXES:
        stoks = match_letters(suf)
        k = len(stoks)
        if len(toks) - k < MIN_STEM:
            continue
        cand = [(L, frozenset(m)) for L, m in toks[-k:]]
        if plain(cand, True) == plain(stoks, True) and vocal_compatible(cand, stoks)[0]:
            info['object'] = suf
            toks = toks[:-k]
            break
    n = len(toks)
    last_L, last_m = toks[-1]
    # واو الجماعة بالألف الفارقة (أو قبل الضمير بلا ألف: فَٱكْتُبُوهُ)
    if n >= 3 and last_L == 'ا' and not last_m and toks[-2][0] == 'و' and not toks[-2][1] and DAMMA in toks[-3][1]:
        info.update(pos='verb', suffix='وا'); ev.append('واو الجماعة والألف الفارقة')
        toks = toks[:-2]
    elif info['object'] and last_L == 'و' and not last_m and n >= 2 and DAMMA in toks[-2][1]:
        info['suffix'] = 'و'                   # واو الجماعة قبل الضمير، أو واو الأسماء الخمسة (أَبُوهُ): لا يُحكم بها وحدها
        toks = toks[:-1]
    # فعل الأمر بهمزة الوصل
    first_L, first_m = toks[0]
    if first_L == 'ا' and not first_m and len(toks) > 2 and toks[1][0] != 'ل' and \
            plain(toks).translate(str.maketrans('', '', 'ـ')) not in WASL_NOUNS and \
            not any(plain(toks).startswith(w) for w in WASL_NOUNS):
        info.update(pos='verb', kind='amr', prefix='ا'); ev.append('همزة وصل في أول فعل الأمر')
        return info
    # الماضي: ضمير رفع متحرك بعد ساكن
    for suf in ('تُمْ', 'تُمَا', 'تُنَّ', 'تُ', 'تَ', 'تِ', 'نَا'):
        stoks = match_letters(suf)
        k = len(stoks)
        m_ = len(toks)
        # تُ تَ تِ وحدها تلتبس بتاء الاسم الساكن ما قبلها (مَوْتِ، بَيْتِ، وَقْتِ): يُشترط ثلاثة أحرف قبلها
        if m_ - k >= (3 if k == 1 else 2) and SUKUN in toks[m_ - k - 1][1] and \
                plain([(L, frozenset(m)) for L, m in toks[m_ - k:]]) == plain(stoks):
            info.update(pos='verb', kind='madi', suffix=suf); ev.append(f'ضمير الرفع «{suf}» بعد ساكن')
            return info
    # المضارع: حرف المضارعة متحركاً بفتح أو ضم
    if first_L in MUDARI and (first_m & {FATHA, DAMMA}) and len(toks) >= 3 and _peelable(first_L):
        info.update(kind='mudari', prefix=first_L)
        L, m = toks[-1]
        if info['suffix'] in ('وا', 'و'):
            info['mood'] = 'حذف النون'
        elif L == 'ن' and SHADDA in m or (L == 'ن' and SUKUN in m and FATHA in toks[-2][1]):
            info.update(pos='verb', suffix='نون التوكيد', mood='مبني'); ev.append('نون التوكيد')
        elif (L == 'ن' and FATHA in m and toks[-2][0] in ('و', 'ي') and not toks[-2][1] or
              L == 'ن' and KASRA in m and toks[-2][0] == 'ا') and len(toks) > 3:
            # نون الرفع؛ ومع غير الياء تلتبس بجمع الاسم (نَبِيُّونَ، تَابِعُونَ) فلا يُحكم بالفعل
            info.update(suffix='نون الرفع', mood='رفع'); ev.append('نون الرفع')
            if first_L == 'ي':
                info['pos'] = 'verb'
        else:
            for mk, mood in MARK_MOOD.items():
                if mk in m:
                    info['mood'] = mood
            if info['mood'] == 'جزم':
                info['pos'] = 'verb'; ev.append('حرف المضارعة والسكون في الآخر')
        if info['pos'] == 'verb':
            ev.insert(0, f'حرف المضارعة «{first_L}»')
        return info
    if info['suffix'] == 'وا':
        info['kind'] = 'madi'                  # واو الجماعة بلا حرف مضارعة ولا همزة وصل: قَالُوا
    return info
