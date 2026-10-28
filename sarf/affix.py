# -*- coding: utf-8 -*-
"""
sarf.affix — مقشِّر الزوائد: هل الجذع فعل أم اسم، وما زوائده ولواحقه، وما علامة إعرابه.

القاعدة: الحرف جذري إلا أن يكون من حروف «سألتمونيها» (زوائد البنية) أو من اللواحق
(الضمائر المتصلة وعلامات الفعل). فلا يُقشَّر إلا ما في ZAWAID أو LAWAHIQ:
    حرف المضارعة       أ ن ي ت                  (من سألتمونيها)
    همزة الوصل         ا في أول فعل الأمر       (من سألتمونيها)
    نون الرفع          ـونَ ـينَ ـانِ
    واو الجماعة        ـوا (والألف الفارقة)
    نون التوكيد        ـنَّ (والخفيفة تُرسم تنويناً)
    ياء المخاطبة       ـِي (مع حذف النون في المضارع، وفي الأمر)
    تاء التأنيث        ـَتْ (الساكنة: الماضي)
    ضمير الرفع         ـْتُمْ ـْتُ ـْتَ ـْتِ ـْنَا  (بعد ساكن: الماضي)
    الضمير المتصل      ـهُ ـهِ ـكَ ـكُمْ ـهُمْ …  (لاحقة: يُنزع قبل الحكم)

الدليل القوي وحده يُثبت النوع:
    فعل: همزة وصل في أوله (غير أل والأسماء العشرة)، أو ألف فارقة بعد واو الجماعة،
         أو حرف مضارعة مع نون التوكيد أو نون الرفع أو السكون في آخره،
         أو ضمير رفع متحرك بعد ساكن (الماضي)، أو تاء التأنيث الساكنة (الماضي)،
         أو سكون الآخر بلا حرف مضارعة: فعل أمر بلا همزة وصل (قُلْ، قِفْ، عَلِّمْ)؛
         لأن النص يُقرأ كما كُتب (بلا وقف) فالاسم المعرب لا يُختم بالسكون،
         والمبنيات والعوامل لا تصل إلى المقشِّر لأنها خانات مستقلة
    اسم: تنوين، أو أل، أو تاء مربوطة
وما سوى ذلك لا يُحكم فيه (pos = None)، ويبقى حرف المضارعة وعلامة الآخر معلومة.
"""
from .chars import (FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN,
                    letters, plain)
from .match import PRON_SUFFIXES, ALIF_TO_YA, match_letters, vocal_compatible

ZAWAID = set('سألتمونيها') | {'ء', 'إ', 'آ'}      # حروف الزيادة (والهمزة بصورها)
LAWAHIQ = set('هكنيوامت')                        # حروف اللواحق: الضمائر المتصلة وعلامات الفعل
MUDARI = {'أ', 'ن', 'ي', 'ت'}
TANWIN = {FATHATAN, DAMMATAN, KASRATAN}
WASL_NOUNS = {'اسم', 'ابن', 'ابنة', 'ابنم', 'امرؤ', 'امرئ', 'امرأ', 'امرأة', 'اثنان', 'اثنين',
              'اثنتان', 'اثنتين', 'است', 'امرأت', 'ابنت', 'اثنا', 'اثنت'}   # أسماء تبدأ بهمزة وصل (وصورها قبل الضمير)
OBJ_SUFFIXES = sorted((s for s in PRON_SUFFIXES if s != 'ي'), key=lambda s: -len(letters(s)))
MIN_STEM = 3
MARK_MOOD = {FATHA: 'نصب', DAMMA: 'رفع', SUKUN: 'جزم'}
MADD = set('اويىآ')
PROCLITIC_LETTERS = set('وفلبكءأ')                 # حروف تسبق الكلمة متصلةً بها (والهمزة للاستفهام)
# ضمائر الرفع المنفصلة: صورتها تشبه الماضي مع ضمير (أَنْتَ = أَنْ + تَ) فتُستثنى
RAF_PRONOUNS = {'أنا', 'أنت', 'أنتما', 'أنتم', 'أنتن', 'هو', 'هي', 'هما', 'هم', 'هن', 'نحن'}


def _peelable(*letters_):
    """لا يُقشَّر حرف من خارج الزوائد واللواحق"""
    return all(L in ZAWAID or L in LAWAHIQ for L in letters_)

_LEX = None

def _mabni(text):
    """في ملف المبنيات (مَنْ، عَنْ، قَدْ، كُمْ): سكون آخره سكون بناء لا أمر"""
    global _LEX
    if _LEX is None:
        from .lexicon import MabniLexicon
        _LEX = MabniLexicon()
    return bool(_LEX.lookup(text))


def short_host(toks):
    """جذعٌ من حرفين ثانيهما مشدَّد يحمل الضمير (رَبَّهُ، حَقَّهُ، أُمَّهُ): الشدة لا تقع على حرف الضمير"""
    return len(toks) == 2 and SHADDA in toks[1][1] and plain(toks).replace('أ', 'ا') != 'اي'   # أَيُّهَا: «ها» للتنبيه


def raf_mark(text, sukun=False):
    """→ دليل الرفع المكتوب على آخر الكلمة (بعد نزع الضمير المتصل)، أو None:
    الضمة أو تنوينها، أو «ـُونَ» (جمع المذكر والأفعال الخمسة)؛
    ومع sukun=True: سكون الآخر أيضاً (المجرور المعرب لا يُختم بالسكون)، إلا المبني من الملف"""
    toks = [(L, set(m)) for L, m in letters(text)]
    if not toks or _mabni(text) or sukun and _closed(toks):
        return None
    info = stem_info(text)
    if info['pos'] == 'verb' and info['kind'] in ('madi', 'amr'):
        return None                            # حركة آخر الماضي والأمر بناءٌ لا إعراب (زُرْتُمُ)
    obj = info['object']
    if obj:
        toks = toks[:-len(match_letters(obj))]
    elif toks[-1][0] == 'ه' and toks[-1][1] == {DAMMA} and plain(toks) != 'الله':
        return None                            # ضمةُ هاءٍ لم تُنزع: الأغلب ضمير (لَهُ)، فلا يُحكم بها
    if len(toks) >= 3 and toks[-1][0] == 'ن' and FATHA in toks[-1][1] and toks[-2][0] == 'و' and \
            not toks[-2][1] and DAMMA in toks[-3][1]:
        return 'ـُونَ'
    if toks[-1][1] & {DAMMA, DAMMATAN}:
        return 'الضمة' if DAMMA in toks[-1][1] else 'تنوين الضم'
    if sukun and toks[-1][1] == {SUKUN} and toks[-1][0] not in MADD:
        return 'السكون'
    return None


def ha_kasra_ok(toks, suf):
    """هاء الضمير المكسورة (هِ، هِمْ…) لا تقع إلا بعد كسرة أو ياء: فإن سبقها غيرهما فالهاء أصلية (يَنتَهِ)"""
    stoks = match_letters(suf)
    if stoks[0][0] != 'ه' or KASRA not in stoks[0][1] or len(toks) <= len(stoks):
        return True
    L, m = toks[-len(stoks) - 1]
    return KASRA in m or L in ('ي', 'ى')


def _closed(toks):
    """في ملف المبنيات، وحدها أو بعد سابقة من حرف واحد (وَلَقَدۡ، لَئِنۡ ← إِنۡ)"""
    def text_of(ts):
        return ''.join(L + ''.join(sorted(m)) for L, m in ts)
    toks = list(toks)
    if toks[0][0] == 'ئ':
        toks[0] = ('إ', toks[0][1])               # ئِنۡ بعد فصل اللام: «إِنۡ»
    if _mabni(text_of(toks)):
        return True
    if len(toks) > 2 and toks[0][0] in PROCLITIC_LETTERS and toks[0][1] & {FATHA, KASRA}:
        rest = list(toks[1:])
        if rest[0][0] == 'ئ':
            rest[0] = ('إ', rest[0][1])          # لَئِنۡ: همزة «إن» على ياء بعد اللام
        return _mabni(text_of(rest))
    return False


def _wasl_kind(toks, suffix):
    """ما بعد همزة الوصل → 'amr' أو 'madi' أو None (مصدر أو غير محسوم):
    الأمر: سكون الآخر (ٱذۡهَبۡ)، أو ياء المخاطبة، أو واو الجماعة بعد صيغة الأمر: حرفان بعد الهمزة (ٱتَّقُوا، ٱدۡعُوا)،
           أو ثلاثة أولها ساكن غير مشدد (ٱعۡلَمُوا)، أو كسرٌ قبل الآخر (ٱسۡتَغۡفِرُوا، ٱتَّبِعُوا)
    الماضي: واو الجماعة في غير ذلك (ٱنقَلَبُوا، ٱتَّبَعُوا)، أو آخره فتح أو ألف مقصورة بعد فتح (ٱتَّخَذَ، ٱبۡتَلَىٰ)،
           وما سواه لا يُحكم فيه (ٱبۡتِغَآءَ: مصدر)"""
    body, last, pen = toks[1:], toks[-1], toks[-2]
    if suffix == 'ي':
        return 'amr'
    if suffix in ('وا', 'و'):
        if len(body) <= 2 or len(body) == 3 and SUKUN in body[0][1] and SHADDA not in body[0][1] or \
                KASRA in pen[1]:
            return 'amr'
        return 'madi'
    if last[0] == 'ت' and last[1] == {SUKUN} and FATHA in pen[1]:
        return 'madi'                                    # ٱنكَدَرَتۡ: تاء التأنيث
    if last[1] == {SUKUN} and last[0] not in MADD:
        return 'amr'
    if (FATHA in last[1] or last[0] in ('ى', 'ا') and not last[1]) and FATHA in pen[1]:
        return 'madi'
    return None


def radical_nun(toks, suf):
    """نون «نِي» جذرية لا نون وقاية (تَحْزَنِى): بعد حرف المضارعة يلزم ثلاثة أحرف قبل «نِي»،
    إلا أن يُختم ما قبلها بحرف علّة (تَرَىٰنِى)"""
    k = len(match_letters(suf))
    return suf == 'نِي' and len(toks) > k and toks[0][0] in MUDARI and set(toks[0][1]) & {FATHA, DAMMA} and \
        len(toks) - k - 1 < 3 and toks[-k - 1][0] not in MADD


def stem_info(text):
    """→ dict(pos, kind, mood, prefix, suffix, object, evidence)
    pos: 'verb' | 'noun' | None؛ kind: 'mudari' | 'amr' | 'madi' | None
    mood: علامة آخر الفعل المضارع (رفع، نصب، جزم، أو «حذف النون»)، أو None"""
    toks = [(L, set(m)) for L, m in letters(text)]
    info = dict(pos=None, kind=None, mood=None, prefix=None, suffix=None, object=None, evidence=[])
    if not toks:
        return info
    ev = info['evidence']
    if plain(toks) in RAF_PRONOUNS or len(toks) > 2 and toks[0][0] in PROCLITIC_LETTERS and \
            FATHA in toks[0][1] and plain(toks[1:]) in RAF_PRONOUNS:
        ev.append('ضمير رفع منفصل')             # وبعد سابقة: فَأَنتَ، ءَأَنتُمۡ
        return info
    # اسم: تنوين، أو أل، أو تاء مربوطة
    if toks[-1][1] & TANWIN or len(toks) > 1 and toks[-1][0] in ('ا', 'ى') and not toks[-1][1] and \
            FATHATAN in toks[-2][1]:
        info['pos'] = 'noun'; ev.append('تنوين')            # وتنوين النصب قبل الألف: خَيۡرًا، هُدًى
        return info
    if len(toks) > 2 and toks[0][0] == 'ا' and toks[1][0] == 'ل' and (not toks[1][1] or toks[1][1] == {SUKUN}):
        info['pos'] = 'noun'; ev.append('أل')
        return info
    if toks[-1][0] == 'ة':
        info['pos'] = 'noun'; ev.append('تاء مربوطة')
        return info
    # الماضي مع «نَا» الفاعلين بعد ساكن (بَنَيْنَا، أَنذَرْنَا) قبل نزع «نا» مفعولاً (أَنذَرَنَا):
    # إلا «نا» على حرف جرّ تنقلب ألفه ياءً (عَلَيْنَا، إِلَيْنَا، لَدَيْنَا)
    if len(toks) >= 4 and toks[-1][0] == 'ا' and not toks[-1][1] and toks[-2][0] == 'ن' and \
            toks[-2][1] == {FATHA} and SUKUN in toks[-3][1] and \
            plain(toks[:-3] + [('ى', frozenset())]) not in ALIF_TO_YA:
        info.update(pos='verb', kind='madi', suffix='نَا'); ev.append('ضمير الرفع «نَا» بعد ساكن')
        return info
    # لاحقة: الضمير المتصل (مفعول به) يُنزع قبل الحكم
    for suf in OBJ_SUFFIXES:
        stoks = match_letters(suf)
        k = len(stoks)
        if len(toks) - k < MIN_STEM and not short_host(toks[:-k]):
            continue
        if radical_nun(toks, suf) or not ha_kasra_ok(toks, suf):
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
    elif (info['object'] or toks[0][0] == 'ا' and not toks[0][1]) and \
            last_L == 'و' and not last_m and n >= 2 and DAMMA in toks[-2][1]:
        # وبلا ضمير مع همزة الوصل: الخانة بعد فصل الضمير المتصل (اكْتُبُو | هُ)
        info['suffix'] = 'و'                   # واو الجماعة قبل الضمير، أو واو الأسماء الخمسة (أَبُوهُ): لا يُحكم بها وحدها
        toks = toks[:-1]
    elif n >= 4 and last_L in ('ي', 'ى') and (not last_m or last_m == {SUKUN}) and KASRA in toks[-2][1] and \
            toks[-2][0] not in MADD and not info['object'] and \
            (toks[0][0] == 'ت' and toks[0][1] & {FATHA, DAMMA} or toks[0][0] == 'ا' and not toks[0][1]):
        # ياء المخاطبة: لا تُقشَّر إلا بعد تاء المضارعة أو همزة الوصل؛
        # وفي غيرهما تلتبس بياء المتكلم على الاسم (نَفْسِى) فلا يُحكم (كُلِى، قَرِّى)
        info['suffix'] = 'ي'
        toks = toks[:-1]
    # ما أوّله همزة وصل (غير أل والأسماء العشرة): أمرٌ، أو ماضي انفعل وافتعل واستفعل، أو مصدرها
    first_L, first_m = toks[0]
    if first_L == 'ا' and not first_m and len(toks) > 2 and toks[1][0] != 'ل' and \
            plain(toks).translate(str.maketrans('', '', 'ـ')) not in WASL_NOUNS:   # مطابقةً بعد نزع الضمير، لا «يبدأ بـ»: ٱسۡتَغۡفِرُوا، ٱسۡمَعُوا
        kind = _wasl_kind(toks, info['suffix'])
        if kind:
            info.update(pos='verb', kind=kind, prefix='ا' if kind == 'amr' else None)
            ev.append('همزة وصل في أول فعل الأمر' if kind == 'amr' else 'همزة وصل في أول الماضي (انفعل، افتعل، استفعل)')
            if kind == 'madi' and toks[-1][0] == 'ت' and toks[-1][1] == {SUKUN} and info['suffix'] is None:
                info['suffix'] = 'تْ'
            if info['suffix'] == 'ي':
                ev.append('ياء المخاطبة')
        return info
    # الماضي: تاء التأنيث الساكنة بعد فتح (قَالَتْ، تَبَّتْ)
    if info['suffix'] is None and len(toks) >= 3 and toks[-1][0] == 'ت' and toks[-1][1] == {SUKUN} and \
            FATHA in toks[-2][1]:
        info.update(pos='verb', kind='madi', suffix='تْ'); ev.append('تاء التأنيث الساكنة')
        return info
    # الماضي: ضمير رفع متحرك بعد ساكن
    for suf in ('تُمْ', 'تُمَا', 'تُنَّ', 'تُ', 'تَ', 'تِ', 'نَا'):
        stoks = match_letters(suf)
        k = len(stoks)
        m_ = len(toks)
        # تُ تَ تِ وحدها تلتبس بتاء الاسم الساكن ما قبلها (مَوْتِ، بَيْتِ، وَقْتِ): يُشترط ثلاثة أحرف قبلها
        if m_ - k >= (3 if k == 1 else 2) and SUKUN in toks[m_ - k - 1][1] and \
                not plain(toks).endswith('ليت') and \
                plain([(L, frozenset(m)) for L, m in toks[m_ - k:]]) == plain(stoks):
            info.update(pos='verb', kind='madi', suffix=suf); ev.append(f'ضمير الرفع «{suf}» بعد ساكن')
            return info
    # المضارع: حرف المضارعة متحركاً بفتح أو ضم
    if first_L in MUDARI and (first_m & {FATHA, DAMMA}) and len(toks) >= 3 and _peelable(first_L) and \
            not _closed(toks):                         # أَلَمۡ: همزة الاستفهام مع «لَمۡ»، لا مضارع
        info.update(kind='mudari', prefix=first_L)
        L, m = toks[-1]
        if info['suffix'] in ('وا', 'و'):
            info['mood'] = 'حذف النون'
        elif info['suffix'] == 'ي':
            # ياء المخاطبة بلا نون: حذف النون؛ ولا يُحكم بالفعل إلا مع تاء المضارعة (تَكْتُبِي)
            # تلتبس بياء المتكلم على اسم أوله تاء (تَوْفِيقِى): لا يُحكم بالفعل، ويشهد له العامل
            info['mood'] = 'حذف النون'
        elif L == 'ن' and SHADDA in m:
            # الخفيفة تُرسم في المصحف تنويناً (لَنَسۡفَعَۢا)، فالنون الساكنة بعد فتح أصلية (تَحۡزَنۡ، يَأۡذَنۡ)
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
        # الأمر بلا همزة وصل: الأجوف (قُولُوا، كُونُوا) وما بقي منه حرفان (كُلُوا، خُذُوا)؛
        # وغيرهما ماضٍ (قَالُوا، قُتِلُوا)
        core = toks
        if len(toks) > 2 and toks[0][0] in ('و', 'ف') and toks[0][1] == {FATHA}:
            core = toks[1:]                    # فَقُولُوا: الفاء والواو المفتوحتان لا تقعان أول الأمر الأجوف
        c_m = core[0][1]
        if DAMMA in c_m and not (c_m & {SHADDA}) and (
                len(core) == 3 and core[1][0] == 'و' and not core[1][1] or
                len(core) == 2 and SHADDA not in core[1][1]):
            info['kind'] = 'amr'; ev.append('أمر بلا همزة وصل مع واو الجماعة')
        else:
            info['kind'] = 'madi'
        return info
    # فعل الأمر بلا همزة وصل: سكون الآخر على حرف غير مدّ، بلا لاحقة ولا حرف مضارعة
    if info['suffix'] is None and len(toks) >= 2 and \
            toks[-1][1] == {SUKUN} and toks[-1][0] not in MADD and not _closed(toks) and \
            toks[-1][0] != 'ه' and not (toks[-1][0] == 'م' and toks[-2][0] in 'هكت'):
        # ويُستثنى: هاء السكت (هِيَهۡ، مَالِيَهۡ)، والضمير الساكن الآخر (لَهُمۡ، كَيۡدَهُمۡ، عَلَيۡكُمۡ)
        info.update(pos='verb', kind='amr'); ev.append('سكون الآخر بلا حرف مضارعة (أمر مبني على السكون)')
    return info
