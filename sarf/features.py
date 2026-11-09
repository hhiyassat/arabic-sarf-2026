# -*- coding: utf-8 -*-
"""
sarf/features.py — مراحل الصرف بعد الجذر والوزن: السمات الصرفية لكل وحدةٍ لفظية، كلٌّ بحالته ودليله.

  الفعل: الزمن، والبناء للمعلوم أو للمجهول، والفاعل (الشخص والعدد والجنس)، والتجرّد والزيادة وحروفها،
         واللزوم والتعدّي، والباب (للثلاثي المجرد)، والدالّ والمدلول (الحدث في HFN، ومعنى الوزن)
  الاسم: العدد (مفرد، مثنى، جمع ونوعه)، والجنس (علامة التأنيث)، والتعريف والتنكير، والاشتقاق ونوعه
  المبني والضمير: الشخص والعدد والجنس من ملف المبنيات المعتمد

  الحالة لكل سمة (لا يُقبل ترجيحٌ إثباتاً، ويُحفظ المنافس):
    مثبت      بدليلٍ مكتوب أو معجميٍّ معتمد يعيّن قيمةً واحدة
    مرشّح     قيمةٌ لها دليلٌ غير كافٍ (صورةٌ مكتوبة بلا رخصةٍ للبقية، أو مدخلٌ في HFN غير مقرّ)؛ لا تدخل الاستدلال
    مؤجَّل    لا دليل، أو تعدّدت القيم؛ والقيم المحتملة في alt
    غير منطبق السمة لا تنطبق (لا جذر للمحمي، ولا باب لغير الثلاثي المجرد…)

  النص لا الصوت: كل حكمٍ هنا من الكتابة (الحروف والحركات معاً) أو من معجمٍ مسمّى؛ ولا تجريد للحركات.
"""
from .chars import letters, FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN, DAGGER_ALIF

PROVEN, CAND, DEFER, NA = 'مثبت', 'مرشّح', 'مؤجَّل', 'غير منطبق'
TANWIN = {FATHATAN, DAMMATAN, KASRATAN}
CASE_V = {FATHA, DAMMA, KASRA} | TANWIN
ROMAN = ('I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X')
# حروف الزيادة في أوزان الثلاثي المزيد (الوزن بحروفه، لا بمعناه)
AUGMENT = {'II': ('فَعَّلَ', 'تضعيف العين'), 'III': ('فَاعَلَ', 'ألفٌ بعد الفاء'), 'IV': ('أَفْعَلَ', 'همزة القطع'),
           'V': ('تَفَعَّلَ', 'التاء وتضعيف العين'), 'VI': ('تَفَاعَلَ', 'التاء والألف'),
           'VII': ('انْفَعَلَ', 'همزة الوصل والنون'), 'VIII': ('افْتَعَلَ', 'همزة الوصل والتاء'),
           'IX': ('افْعَلَّ', 'همزة الوصل وتضعيف اللام'), 'X': ('اسْتَفْعَلَ', 'همزة الوصل والسين والتاء')}
TENSE = {'madi': 'ماضٍ', 'mudari': 'مضارع', 'amr': 'أمر'}
NUM_AR = {'singular': 'مفرد', 'dual': 'مثنى', 'plural': 'جمع'}
GEN_AR = {'masc': 'مذكر', 'fem': 'مؤنث', 'common': 'مشترك'}


def feat(value, status, evidence='', alt=None):
    r = dict(v=value, st=status, ev=evidence)
    if alt:
        r['alt'] = alt
    return r


# ---------- الاسم: العدد والجنس من اللاحقة المكتوبة ----------
def _m(tok, *vs):
    return any(v in tok[1] for v in vs)


def noun_suffix(stem):
    """→ (العدد، نوع الجمع، الجنس، اللاحقة، طول اللاحقة بالحروف) من آخر الجذع المكتوب، أو None.
    الحروف والحركات معاً: «ـَانِ/ـَيْنِ» مثنى، «ـُونَ/ـِينَ» جمع مذكر سالم، «ـَاتٌ…» جمع مؤنث سالم، «ـَة» مفردٌ مؤنث"""
    t = letters(stem)
    n = len(t)
    if n >= 4 and t[-1][0] == 'ن':
        a, b = t[-2], t[-3]
        if _m(t[-1], KASRA) and a[0] == 'ا' and not a[1] and _m(b, FATHA):
            return ('dual', None, 'fem' if b[0] == 'ت' and n >= 5 else None, 'ـَانِ', 2)
        if _m(t[-1], KASRA) and a[0] == 'ي' and _m(a, SUKUN) and _m(b, FATHA):
            return ('dual', None, 'fem' if b[0] == 'ت' and n >= 5 else None, 'ـَيْنِ', 2)
        if _m(t[-1], FATHA) and a[0] == 'و' and not (a[1] - {SUKUN}) and _m(b, DAMMA):
            return ('plural', 'sound_masc', 'masc', 'ـُونَ', 2)
        if _m(t[-1], FATHA) and a[0] == 'ي' and not (a[1] - {SUKUN}) and _m(b, KASRA):
            return ('plural', 'sound_masc', 'masc', 'ـِينَ', 2)
    # جمع المؤنث السالم لا يُنصب بالفتحة: آخره ضمٌّ أو كسرٌ أو تنوينهما (أَمَاتَ فعل)
    FPL = {DAMMA, KASRA, DAMMATAN, KASRATAN}
    if n >= 4 and t[-1][0] == 'ت' and (t[-1][1] & FPL) and t[-2][0] == 'ا' and not t[-2][1] and _m(t[-3], FATHA):
        return ('plural', 'sound_fem', 'fem', 'ـَات', 2)
    if n >= 3 and t[-1][0] == 'ت' and (t[-1][1] & FPL) and DAGGER_ALIF in t[-2][1]:
        return ('plural', 'sound_fem', 'fem', 'ـَٰت', 1)      # الألف الخنجرية: الجمع بالرسم العثماني (جَنَّٰتٍ)
    if n >= 2 and t[-1][0] == 'ة':
        return ('singular', None, 'fem', 'ـَة', 1)
    return None


def _tanwin(t):
    """التنوين على الآخر، أو على ما قبل ألفٍ أو ياءٍ (ألف المقصور) لا حركة لها: شَيۡـًٔا، هُدًى"""
    if not t:
        return False
    if t[-1][1] & TANWIN:
        return True
    return len(t) > 1 and t[-1][0] in ('ا', 'ى') and not (t[-1][1] - {SUKUN}) and bool(t[-2][1] & TANWIN)


def _alif_hamza_start(stem):
    """أوله همزةٌ بعدها ألف (ءَا، آ): قالب فَاعِل يلتبس بأَفْعِلَة وأَفْعَال بعد اجتماع الهمزتين (ءَالِهَة)"""
    t = letters(stem)
    i = 0
    if t and t[0][0] == 'ا' and len(t) > 1 and t[1][0] == 'ل':
        i = 2                                                     # بعد «ال»
    return len(t) > i + 1 and ((t[i][0] == 'ء' and t[i + 1][0] == 'ا') or t[i][0] == 'آ' or 'ٓ' in t[i][1] and t[i][0] == 'ا')


def _rest(stem, k):
    """الجذع دون آخر k حروف (بحركاتها)، للحكم على البقية"""
    from .chars import MARKS, TATWEEL
    starts = [i for i, ch in enumerate(stem) if ch not in MARKS and ch != TATWEEL]
    return stem[:starts[-k]] if len(starts) > k else ''


# ---------- المبني من ملف المبنيات ----------
_LEX = None


def _lex():
    global _LEX
    if _LEX is None:
        from .lexicon import MabniLexicon
        _LEX = MabniLexicon()
    return _LEX


def mabni_features(text):
    """الشخص والعدد والجنس من مداخل ملف المبنيات (حرفاً وحركة)؛ وما تعدّدت مداخله بقيمٍ مختلفة يُؤجَّل"""
    hits = _lex().lookup(text) or [e for e in [_lex().attested(text)] if e]
    vals = []
    for e in hits:
        x = e.get('extra') or {}
        if x.get('number') or x.get('gender') or x.get('person'):
            vals.append((x.get('person'), x.get('number'), x.get('gender'), e['entry_id'], e['category']))
    if not vals:
        return {}
    keys = {v[:3] for v in vals}
    src = '، '.join(f'{v[3]} ({v[4]})' for v in vals[:3])
    if len(keys) == 1:
        p, n, g = vals[0][:3]
        out = {}
        if p:
            out['person'] = feat(p, PROVEN, 'ملف المبنيات: ' + src)
        if n:
            out['number'] = feat(n, PROVEN, 'ملف المبنيات: ' + src)
        if g:
            out['gender'] = feat(g, PROVEN, 'ملف المبنيات: ' + src)
        return out
    return {'number': feat(None, DEFER, 'مداخل متعدّدة بقيمٍ مختلفة: ' + src, alt=sorted({str(k) for k in keys}))}


# ---------- الفعل ----------
def _radical_vowel(word, R, k):
    """حركة الحرف الأصلي رقم k (0، 1، 2) في المكتوب: يُطلب الحرف الأول ثم ما بعده بالترتيب (الهمزة بصورها واحدة)"""
    norm = lambda c: 'ء' if c in 'ءأإآؤئ' else c
    t = letters(word)
    i = 0
    for r in range(k + 1):
        while i < len(t) and norm(t[i][0]) != norm(R[r]):
            i += 1
        if i >= len(t):
            return None
        if r < k:
            i += 1
    if k == 1 and len(R) == 3 and R[1] == R[2] and SHADDA in t[i][1] and i > 0:
        i -= 1                    # المضعَّف المدغم: حركة العين نُقلت إلى الفاء (يُمِلُّ ← يُمۡلِلُ)، والتي على اللام علامة إعراب
    v = t[i][1] & {FATHA, DAMMA, KASRA}
    return {FATHA: 'a', DAMMA: 'u', KASRA: 'i'}.get(next(iter(v))) if len(v) == 1 else None


def tense_realization(text, R, P, closed):
    """F03 (مقترحة، تنتظر اعتماد صاحب النظرية): تحقيق كل بديلٍ زمني للمكتوب حرفاً وحركة، في الصحيح غير المضعَّف ذي الجذر المقبول
    والوزن المعروف (I–X)؛ ولا يُرجَّح بديلٌ بترتيب، بل يُمنع ما لا يحقّق المكتوب بمانعٍ مثبت:
      المضارع: أوله حرف مضارعة (أ ن ي ت) مفتوحٌ أو مضموم ليس من قالب الوزن ولا فاء الجذر — وإلا مُنع؛
      الأمر في II وIII وIV وVII وVIII وX: عينه مكسورة — فإن فُتحت مُنع؛ وفي الثلاثي المجرد: فاؤه ساكنة بعد همزة وصل —
           فإن فُتحت الفاء مُنع؛
      الماضي في II وIII وIV وVII وVIII وX: عينه مفتوحة في المعلوم، وأوله مضموم في المجهول — فإن كُسرت العين ولم يُضمّ أوله مُنع.
    → {البديل: (الحالة، السبب)} أو None خارج المجال"""
    if not closed or not R or len(R) != 3 or set(R) & set('وي') or R[1] == R[2] or P not in ('I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'X'):
        return None
    t = letters(text)
    if len(t) < 3:
        return None
    norm = lambda c: 'ء' if c in 'ءأإآؤئ' else c
    f0, m0 = t[0]
    # مواضع امتناع الحكم، لأن الكتابة لا تفصل فيها:
    #  الهمزة في أوله: همزة استفهامٍ قبل الفعل (أَقَتَلۡتَ، أَشَهِدُوا)، أو همزة المتكلم (أُفۡرِغۡ)، أو همزة أَفۡعَلَ
    #  حرف مضارعةٍ محتمل يليه مثله من الجذر أو القالب (تَتَّبِعُوا، نَنۡسَخۡ، نُنَزِّلۡ، تَتَفَكَّرُوا)
    #  تاء تَفَعَّلَ وتَفَاعَلَ في أوله: قد تكون تاء المضارعة وحُذفت الأخرى (تَصَدَّقُوا = تَتَصَدَّقُوا، تَفَرَّقُوا)
    if norm(f0) == 'ء':
        return None
    if f0 in 'نيت' and m0 & {FATHA, DAMMA} and (f0 == R[0] or f0 == 'ت' and P in ('V', 'VI', 'VIII')) and \
            t[1][0] in (R[0], 'ت', 'ن', 'س'):
        return None
    if f0 == 'ت' and P in ('V', 'VI'):
        return None
    ain = _radical_vowel(text, R, 1)
    fa = _radical_vowel(text, R, 0)
    if ain is None:
        return None
    out = {}
    pref = f0 in 'أنيت' and m0 & {FATHA, DAMMA} and not (norm(f0) == norm(R[0]) or f0 == 'ت' and P in ('V', 'VI') or
                                                         f0 == 'أ' and P == 'IV')
    out['مضارع'] = ('LICENSED', f'أوله حرف مضارعة «{f0}» ليس من قالب الوزن {P}') if pref else \
        ('REJECTED', f'لا حرف مضارعة في أوله («{f0}» من قالب الوزن {P} أو من الجذر «{R}»): لا يكون مضارعاً')
    v_ain = {'a': 'مفتوحة', 'i': 'مكسورة', 'u': 'مضمومة'}[ain]
    if P in ('II', 'III', 'IV', 'VII', 'VIII', 'X'):
        out['أمر'] = ('LICENSED', f'عينه مكسورة كأمر الوزن {P}') if ain == 'i' else \
            ('REJECTED', f'عين الجذر «{R[1]}» {v_ain}، وأمر الوزن {P} مكسور العين')
        passive = DAMMA in m0
        out['ماضٍ'] = ('LICENSED', f'عينه مفتوحة كماضي الوزن {P} المعلوم' if ain == 'a' else f'أوله مضموم: ماضٍ مجهول') \
            if ain == 'a' or passive else ('REJECTED', f'عين الجذر «{R[1]}» {v_ain} وأوله غير مضموم، وماضي الوزن {P} مفتوح العين في المعلوم')
    elif P == 'I' and fa == 'a' and not set(R) & set('ءأ'):
        out['أمر'] = ('REJECTED', f'فاء الجذر «{R[0]}» مفتوحة، وأمر الثلاثي الصحيح ساكن الفاء بعد همزة وصل')
    elif P == 'I' and f0 in 'اٱ' and not m0 & {FATHA, DAMMA, KASRA} and fa is None and not set(R) & set('ءأ'):
        out['ماضٍ'] = ('REJECTED', 'أوله همزة وصل، وماضي الثلاثي المجرد لا يبدأ بها')
    if pref:
        out['ماضٍ'] = ('REJECTED', f'في أوله حرف مضارعة «{f0}» ليس من قالب الوزن {P} ولا من الجذر')
        out['أمر'] = ('REJECTED', f'في أوله حرف مضارعة «{f0}» ليس من قالب الوزن {P}')
    return out


def _bab(R, written, kind, past_verb):
    """باب الثلاثي المجرد: حركة عين الماضي (من فعل HFN المطابق) وحركة عين المضارع (من النص المكتوب)"""
    if not R or len(R) != 3 or set(R) & set('ويءأؤئى') or R[1] == R[2]:
        return feat(None, DEFER, 'الباب للصحيح السالم غير المضعَّف هنا؛ والمعتلّ والمهموز والمضعَّف مؤجَّلة')
    def ain_vowel(word, after_prefix):
        t = letters(word)
        i = 1 if after_prefix else 0
        # الفاء ثم العين: أول حرفٍ يساوي R[0] ثم الذي يليه يساوي R[1]
        for j in range(i, len(t) - 1):
            if t[j][0] == R[0] and t[j + 1][0] == R[1]:
                v = t[j + 1][1] & {FATHA, DAMMA, KASRA}
                return {FATHA: 'a', DAMMA: 'u', KASRA: 'i'}.get(next(iter(v))) if len(v) == 1 else None
        return None
    past = ain_vowel(past_verb, False) if past_verb else None
    pres = ain_vowel(written, True) if kind == 'mudari' else None
    if past and pres:
        return feat(f'{past}-{pres}', PROVEN, f'عين الماضي من HFN «{past_verb}»، وعين المضارع من المكتوب «{written}»')
    if past:
        return feat(None, DEFER, f'عين الماضي «{past}» من HFN «{past_verb}»، وحركة عين المضارع غير مكتوبة هنا',
                    alt=[f'{past}-a', f'{past}-i', f'{past}-u'])
    return feat(None, DEFER, 'لا فعل مطابق في HFN يعيّن عين الماضي')


# صنف الإسناد الذي تشترك فيه الأزمنة كتابةً: «وا» (كَتَبُوا، اكْتُبُوا، لَمْ يَكْتُبُوا) وصنف «ون» إذا حُذفت نونه
AMBIG_SIG = {'وا', 'ون', 'و'}
# عواملُ لا تدخل إلا على المضارع: لَمْ، لَنْ، كَيْ، ولام الأمر والتعليل (فَلْيَكْتُبْ، لِيَكْتُبَ)
MUDARI_ONLY = {'لَمْ', 'لَنْ', 'كَيْ', 'لِكَيْ', 'لِ', 'لْ'}


_ELATIVE = {}


def elative_evidence(text):
    """E01 v1 (مقترحة، مشتركة بين السمات والعلاقات — FA02، مراجعة 18:34 «أَكْثَرُ»: كانت العلاقات تثبت الاسم بها والسمات تثبت الفعل):
    «أَفْعَلُ» مختومٌ بضمة أو كسرة بلا تنوين ولا «أل» اسمٌ بنفي البدائل الثلاثة في مجالٍ معلن: الماضي (الآخر غير مفتوح)، ومضارع
    المتكلم من أَفْعَلَ (الهمزة مفتوحة لا مضمومة)، ومضارع المتكلم من الثلاثي: فَعَلَ لا يكون مضارعه يَفْعَلُ إلا وعينه أو لامه حرف حلق
    (سيبويه)، وفَعُلَ يُضمّ مضارعه، والأجوف لا يُكتب هكذا؛ والماضي من HFN. → نصّ الدليل أو None"""
    if text in _ELATIVE:
        return _ELATIVE[text]
    _ELATIVE[text] = out = _elative_evidence(text)
    return out


def _elative_evidence(text):
    t = letters(text)
    if len(t) != 4 or t[0][0] != 'أ' or FATHA not in t[0][1] or SUKUN not in t[1][1] or FATHA not in t[2][1] or \
            DAGGER_ALIF in t[2][1]:
        return None                                 # والخنجرية بعد العين مدٌّ: أَفۡعَال (أَيۡمَٰن)، لا أَفۡعَل
    last = t[3][1]
    if last & {FATHATAN, DAMMATAN, KASRATAN} or not last & {DAMMA, KASRA}:
        return None
    R = ''.join('ء' if c in 'أإؤئ' else c for c in (t[1][0], t[2][0], t[3][0]))
    from .root import hfn
    H = hfn()
    if H is None or R not in H.roots:
        return None
    pasts = [e['verb'] for e in H.index.get((R, 'I'), [])]
    if R[1] in 'وي':
        why = 'الأجوف لا يأتي مضارعه على أَفْعَلُ بعينٍ مفتوحة بعد ساكن'
    else:
        vs = set()
        for pv in pasts:
            pt = letters(pv)
            if len(pt) >= 2:
                vs |= {x for x in (FATHA, DAMMA, KASRA) if x in pt[1][1]}
        if not vs or KASRA in vs or (FATHA in vs and set(R[1:]) & set('ءهعحغخ')):
            return None                             # فَعِلَ يَفْعَلُ، أو حرف حلق، أو لا ماضٍ في HFN: مضارع المتكلم باقٍ
        why = 'ماضيه في HFN «' + '، '.join(pasts) + '» فَعَلَ أو فَعُلَ، ولا حرف حلق في عينه ولامه: فلا يكون مضارعه أَفْعَلُ'
    return f'E01 (مقترحة): «{text}» آخره غير مفتوح فلا يكون ماضياً، وهمزته مفتوحة فلا يكون مضارع أَفْعَلَ، و{why}'


def _afalu_contested(text, agr, governor):
    """صورة «أَفْعَلُ»: همزةٌ مفتوحة، فأصلٌ ساكن، فأصلٌ مفتوح، فأصلٌ عليه ضمة أو كسرة، ولا لاحقة إسناد،
    ولا عامل مكتوب يحكمه (لَمْ، لَنْ…)، ولا ضمير متصل مكتوب في الوحدة. وهي صورة مضارع المتكلم وصورة أفعل التفضيل معاً"""
    if governor or (agr or {}).get('kind') != 'mudari' or (agr or {}).get('signature'):
        return False
    t = letters(text)
    # مجال E01 نفسه (آخرٌ مضموم أو مكسور). والمفتوح الآخر (أَنْ أَعْمَلَ، لَأَسْمَعَهُمْ) خارج هذه القاعدة: كان فعلاً صحيحاً في 7 مواضع
    # (قياس FA02)، وتأجيله إتلافٌ للصحيح؛ وبقاؤه بدليل التوافق وحده نقصٌ معلن (لا ينفي أفعل التفضيل الممنوع من الصرف بالكتابة)
    return len(t) == 4 and t[0][0] in 'أ' and t[0][1] == {FATHA} and t[1][1] == {SUKUN} and t[2][1] == {FATHA} \
        and bool(set(t[3][1]) & {DAMMA, KASRA}) and not set(t[3][1]) & {FATHATAN, DAMMATAN, KASRATAN, SHADDA}


def verb_features(G, agr, morph, obj_pron, governor=None):
    """سمات الفعل: agr سجلّ التوافق (T18)، وmorph سجلّ الجذر، وobj_pron الضمير المتصل بعد الفعل في كلمته،
    وgovernor عاملٌ مكتوب قبله يقتضي النصب أو الجزم (فلا يكون إلا مضارعاً)"""
    out = {'pos': feat('فعل', PROVEN, agr.get('rule') or 'التوافق (T18)')}
    kind = agr.get('kind')
    sig = agr.get('signature') or ''
    written_nun = G.O['text'].rstrip('ًٌٍَُِّْ').endswith('ن')
    tense_ambig = sig in AMBIG_SIG and not (sig == 'ون' and written_nun)
    tl = letters(G.O['text'])
    why_amb = f'صنف الإسناد «{sig}» يشترك فيه الماضي والأمر والمضارع المحذوف النون كتابةً'
    if sig == 'أفعل' or (not sig and tl and SUKUN in tl[-1][1]):
        # أَفۡعِلۡ: أمر الواحد أو مضارع المتكلم المجزوم؛ والمختوم بالسكون بلا لاحقة: أمرٌ أو مضارعٌ مجزوم
        tense_ambig, why_amb = True, 'آخره ساكنٌ بلا لاحقة: أمرٌ أو مضارعٌ مجزوم (أو مضارع المتكلم في أَفۡعِلۡ)'
    R0, P0 = G.Theta.get('R'), G.Theta.get('P')
    if kind == 'madi' and tl and tl[0][0] == 'ا' and not tl[0][1] and P0 not in ('VII', 'VIII', 'IX', 'X'):
        # همزة الوصل في أوله: ماضي انفعل وافتعل وافعلّ واستفعل، أو أمرٌ (ائْتِ، اخْرُجْ)
        tense_ambig = True
        why_amb = 'في أوله همزة وصل، ولم يثبت وزنٌ ماضيه بها (VII–X): قد يكون أمراً'
    if kind == 'madi' and tl and tl[0][0] in 'يتنأ' and tl[0][1] & {FATHA, DAMMA}:
        # حرفٌ من أحرف المضارعة في أوله: لا يكون ماضياً إلا أن يكون فاءَ الجذر، أو تاء تَفَعَّلَ وتَفَاعَلَ، أو همزة أَفۡعَلَ
        f0 = tl[0][0]
        part_of_pattern = bool(R0) and (R0[0] in (f0, 'ء' if f0 == 'أ' else f0) or (f0 == 'ت' and P0 in ('V', 'VI'))
                                        or (f0 == 'أ' and P0 == 'IV'))
        if not part_of_pattern and (R0 or f0 == 'ي' or sig in ('تُمْ', 'نَا', 'تَ', 'تِ', 'تُ', 'تُمَا', 'تُنَّ')):
            tense_ambig = True
            why_amb = f'صنف الإسناد ماضٍ («{sig}»)، وفي أوله «{f0}» من أحرف المضارعة ليس من قالب الماضي' + \
                (f' (الجذر «{R0}»، الوزن {P0})' if R0 else '') + ': فاللاحقة قد تكون من الجذر أو ضمير مفعول'
    R_g, P_g = G.Theta.get('R'), G.Theta.get('P')
    pref_ind = bool(tl) and tl[0][0] in 'أنيت' and bool(tl[0][1] & {FATHA, DAMMA}) and bool(R_g) and \
        tl[0][0] != ('ء' if R_g[0] in 'ءأ' else R_g[0]) and not (tl[0][0] == 'ت' and P_g in ('V', 'VI')) and \
        not (tl[0][0] == 'أ' and P_g == 'IV') and not (len(tl) > 1 and tl[1][0] == tl[0][0])
    if governor and (kind == 'mudari' or pref_ind):
        out['tense'] = feat('مضارع', PROVEN, f'العامل «{governor[0]}» قبله يقتضي {governor[1]}، ولا يُنصب ولا يُجزم إلا المضارع؛ '
                                               'وفي أوله حرف مضارعةٍ مكتوب ليس من الجذر ولا من قالب الوزن (أصلٌ مستقلٌّ عن العامل)' +
                                               ('' if kind == 'mudari' else f'؛ وخالفه صنف الإسناد ({TENSE.get(kind)}) فلم يُعتمد'))
        kind = 'mudari'
    elif governor:
        # قبول العامل قام على أثره المتوقَّع في هذا المعمول، فلا يُثبت به زمن المعمول نفسه (منع الدور): يبقى الزمن مرشّحاً بالتعارض
        out['tense'] = feat(TENSE.get(kind), CAND, f'العامل «{governor[0]}» يقتضي المضارع، وصنف الإسناد {TENSE.get(kind)}: تعارضٌ '
                                                    'لا يُحسم بالعامل وحده، لأن قبوله قام على أثره في هذا المعمول',
                            alt=sorted({TENSE.get(kind), 'مضارع'} - {None}))
    elif tense_ambig:
        out['tense'] = feat(TENSE.get(kind), CAND, why_amb, alt=['ماضٍ', 'أمر', 'مضارع'])
        tr_ = tense_realization(G.O['text'], R0, P0, G.closed)
        if tr_:
            live = [x for x in ('ماضٍ', 'أمر', 'مضارع') if tr_.get(x, ('LICENSED',))[0] != 'REJECTED']
            rej = '؛ '.join(f'{x} ممنوع: {tr_[x][1]}' for x in ('ماضٍ', 'أمر', 'مضارع') if tr_.get(x, ('',))[0] == 'REJECTED')
            rejected_ = {x: tr_[x][1] for x in ('ماضٍ', 'أمر', 'مضارع') if tr_.get(x, ('',))[0] == 'REJECTED'}
            if len(live) == 1 and live[0] == TENSE.get(kind):
                # يثبت الزمن إذا وافق الباقي صنفَ الإسناد الذي بُني عليه ضمير الصيغة؛ وإن خالفه بقي مرشّحاً (لا يُجمع زمنٌ من وجهٍ
                # وضميرٌ من آخر)
                out['tense'] = feat(live[0], PROVEN, f'F03 (مقترحة): {why_amb}؛ و{rej}؛ فبقي {live[0]}' +
                                    (f' ({tr_[live[0]][1]})' if live[0] in tr_ else ''))
                out['tense']['rejected'] = rejected_
                out['tense']['realization'] = tr_.get(live[0], ('LICENSED', 'لم يُمنع'))[1]
            elif rej:
                out['tense'] = feat(TENSE.get(kind) if TENSE.get(kind) in live else live[0], CAND, why_amb + f'؛ F03 (مقترحة): {rej}',
                                    alt=live)
                out['tense']['rejected'] = rejected_
    else:
        out['tense'] = feat(TENSE.get(kind), PROVEN if kind in TENSE else DEFER, 'صنف الإسناد: ' + sig)
    vo = agr.get('voice')
    out['voice'] = feat({'active': 'معلوم', 'passive': 'مجهول'}.get(vo), PROVEN if vo in ('active', 'passive') else DEFER,
                        'حركات الفعل المكتوبة' if vo else 'لم تعيّنه الحركات المكتوبة', alt=None if vo else ['معلوم', 'مجهول'])
    if vo == 'active' and out['tense']['st'] != PROVEN and tl and DAMMA in tl[0][1] and tl[0][0] not in 'يتنأ':
        # ضمّ أوله بلا حرف مضارعة، والزمن غير مثبت: أمرُ الأجوف (قُولُوا، تُوبُوا) معلوم، أو ماضٍ مبني للمجهول
        # (دُعُوا، قُتِلُوا)؛ فالبناء يتبع الزمن ولا يثبت قبله
        out['voice'] = feat('معلوم', CAND, 'أوله مضموم بلا حرف مضارعة، والزمن غير مثبت: قد يكون ماضياً مبنياً للمجهول',
                            alt=['معلوم', 'مجهول'])
    R1, P1 = G.Theta.get('R'), G.Theta.get('P')
    if vo in ('active', 'passive') and kind == 'mudari' and G.closed and R1 and P1 in ('II', 'III', 'IV') and tl and DAMMA in tl[0][1]:
        # يُفَعِّلُ ويُفَاعِلُ ويُفۡعِلُ: ضمّ حرف المضارعة للمعلوم والمجهول معاً؛ والفارق حركة العين: الكسر للمعلوم والفتح للمجهول
        v_ = _radical_vowel(G.O['text'], R1, 1)
        if v_ in ('i', 'a'):
            out['voice'] = feat('معلوم' if v_ == 'i' else 'مجهول', PROVEN,
                                f'حركة العين في قالب {P1}: {"الكسر (معلوم)" if v_ == "i" else "الفتح (مجهول)"}')
    fs = agr.get('features') or []
    if kind == 'mudari' and sig == 'ين' and not written_nun and R1 and R1[-1] in 'يو' and tl and tl[-1][0] == 'ي':
        # الناقص اليائي: الياء لامُ الفعل لا ياء المخاطبة (تَجۡزِي، تَأۡتِي): فالفاعل «هي» أو «أنتَ»
        fs = []
        out['subject'] = feat(None, DEFER, f'الياء في آخره لامُ الجذر «{R1}» لا ياء المخاطبة', alt=[
            dict(person=3, number='singular', gender='fem'), dict(person=2, number='singular', gender='masc')])
    elif not sig and len(tl) > 2 and tl[-1][0] == 'و' and not tl[-1][1] and DAMMA in tl[-2][1]:
        # واو الجماعة قبل ضمير المفعول بلا ألفٍ فارقة (يَأۡتُوكُم): الصنف لم يُعرف، والجمع ظاهر
        fs = []
        out['subject'] = feat(None, DEFER, 'واو الجماعة في آخره قبل ضمير المفعول، ولم يعيّنها صنف الإسناد',
                              alt=[dict(person=q, number='plural', gender='masc') for q in (2, 3)])
    if len(fs) == 1 and out['tense']['st'] != PROVEN:
        p, n, g = fs[0]
        out['subject'] = feat(dict(person=p, number=n, gender=g), CAND, (agr.get('rule') or '') + '؛ والزمن غير مثبت، فالشخص يتبعه',
                              alt=[dict(person=q, number=n, gender=g) for q in (2, 3) if q != p])
    elif len(fs) == 1:
        p, n, g = fs[0]
        why = agr.get('rule') or ''
        if p == 3 and n == 'dual' and g == 'common':
            # الضمير «هُمَا» مشترك، والصيغة تعيّن: يَفْعَلَانِ وفَعَلَا للمذكرين، وتَفْعَلَانِ وفَعَلَتَا للمؤنثتين
            if (kind == 'mudari' and tl and tl[0][0] == 'ي') or (kind == 'madi' and sig == 'ا'):
                g, why = 'masc', why + '؛ والصيغة للمذكرين (الياء في المضارع، والألف بلا تاء في الماضي)'
            elif (kind == 'madi' and sig in ('تَا',)):
                g, why = 'fem', why + '؛ والصيغة للمؤنثتين (تاء التأنيث قبل الألف)'
        out['subject'] = feat(dict(person=p, number=n, gender=g), PROVEN, why)
    elif fs:
        out['subject'] = feat(None, DEFER, 'الصيغة المكتوبة تحتمل أكثر من فاعل: ' + (agr.get('rule') or ''),
                              alt=[dict(person=p, number=n, gender=g) for p, n, g in fs])
    R, P = G.Theta.get('R'), G.Theta.get('P')
    if G.closed and R and P in ROMAN:
        if P == 'I':
            out['augmentation'] = feat(dict(type='مجرد', radicals=len(R)), PROVEN, f'الوزن فَعَلَ والجذر «{R}» مقبول')
        else:
            out['augmentation'] = feat(dict(type='مزيد', form=P, wazn=AUGMENT[P][0], letters=AUGMENT[P][1], radicals=len(R)),
                                       PROVEN, f'الوزن {AUGMENT[P][0]} والجذر «{R}» مقبول')
    else:
        out['augmentation'] = feat(None, DEFER, 'الجذر أو الوزن غير مقبول')
    # اللزوم والتعدّي: الاستعمال المكتوب (ضمير مفعول متصل) يثبت التعدّي في هذا الموضع؛ وHFN مرشّح (is_fact=False)
    tr_hfn = set()
    if R and P in ROMAN:
        from .root import hfn
        tr_hfn = {e.get('transitivity') for e in hfn().index.get((R, P), [])} - {''}
    if obj_pron and vo != 'passive':
        ev = f'ضمير المفعول المتصل «{obj_pron}» مكتوبٌ بعد الفعل'
        if 'لازم' in tr_hfn and not tr_hfn & {'متعدي', 'مشترك'}:
            out['transitivity'] = feat(None, DEFER, ev + '؛ وHFN يسجّله لازماً: تعارض', alt=['متعدٍّ', 'لازم'])
        else:
            out['transitivity'] = feat('متعدٍّ', PROVEN, ev)
    elif tr_hfn == {'لازم'}:
        out['transitivity'] = feat('لازم', CAND, 'HFN: لازم (مدخلٌ غير مقرّ، is_fact=False)')
    elif tr_hfn == {'متعدي'}:
        out['transitivity'] = feat('متعدٍّ', CAND, 'HFN: متعدٍّ (مدخلٌ غير مقرّ، is_fact=False)')
    elif tr_hfn:
        out['transitivity'] = feat(None, DEFER, 'HFN: ' + '، '.join(sorted(tr_hfn)), alt=['لازم', 'متعدٍّ'])
    else:
        out['transitivity'] = feat(None, DEFER, 'لا دليل مكتوب ولا مدخل في HFN')
    # الباب والدالّ والمدلول
    mev = (morph or {}).get('event') or {}
    ev_id = mev.get('event_id') if isinstance(mev, dict) else mev
    events = {}
    if R and P in ROMAN:
        from .root import hfn
        events = {e['event_id']: e for e in hfn().index.get((R, P), [])}
    e = events.get(ev_id)
    if P == 'I' and G.closed:
        out['bab'] = _bab(R, G.O['text'], kind, e['verb'] if e else None)
    else:
        out['bab'] = feat(None, NA, 'الباب للثلاثي المجرد وحده')
    if e:
        out['signified'] = feat(dict(event=ev_id, verb=e['verb'], masdar=e.get('masdar')), PROVEN,
                                'الفعل يطابق حدث HFN حرفاً وحركة (مستوى الحدث في مرشِّح الجذر)')
    elif R and G.closed:
        out['signified'] = feat(None, DEFER, 'الجذر مقبول ولا حدث مسجَّل بهذا الوزن يطابق المكتوب',
                                alt=sorted(events)[:5] or None)
    wm = G.Theta.get('wazn_meaning')
    if wm:
        out['form_meaning'] = feat(wm.get('meaning'), CAND, f'معنى الوزن {wm.get("wazn")} في ملف الأوزان (غير مقرّ)')
    return out


# ---------- E02 وE03 (مقترحتان، تنتظران اعتماد صاحب النظرية): الاسمية بنفي صيغ الفعل المكتوبة ----------
ATTACHED_PRONOUNS = ('هُ', 'هِ', 'هَا', 'هُمَا', 'هِمَا', 'هُمْ', 'هِمْ', 'هُمُ', 'هِمُ', 'هُنَّ', 'هِنَّ', 'كَ', 'كِ', 'كُمْ', 'كُمُ',
                     'كُمَا', 'كُنَّ', 'نَا', 'ي', 'يَ')


def _peel_verbal_proclitics(t):
    """ما بقي في الجذع من «فَـ/وَـ» وهمزة الاستفهام قبل حرف مضارعة و«سَـ» (سَنُدۡخِلُهُمۡ، فَسَيَحۡشُرُهُمۡ، أَيَأۡمُرُكُم):
    يُنزع قبل فحص أول الصيغة"""
    i = 0
    if len(t) > 3 and t[0][0] in 'وف' and t[0][1] == {FATHA}:
        i = 1
    if len(t) > i + 3 and t[i][0] == 'أ' and t[i][1] == {FATHA} and t[i + 1][0] in 'أنيت' and t[i + 1][1] & {FATHA, DAMMA}:
        i += 1                    # همزة الاستفهام قبل حرف مضارعة متحرّك (أَيَأۡمُرُكُم)
    if len(t) > i + 3 and t[i][0] == 'س' and t[i][1] == {FATHA}:
        i += 1
    return t[i:]


# سجلّ القاعدتين بعد تدقيق 032 (SARF_MAJOR_CLOSURE_01 §3): المجال، والمقدّمات، والموانع، والأمثلة المقابلة، والمصدر
E_RULES = {
    'E02': dict(version='v2', status='مقترحة', scope='جذعٌ غير محمي متصلٌ به ضميرٌ متصل من الضمائر المسمّاة (ATTACHED_PRONOUNS)، '
                                                 'وآخر الجذع ضمةٌ أو كسرة بلا تنوين، وفي الجذع بعد نزع السوابق ثلاثة أحرفٍ مكتوبة فأكثر',
                positive_premises=['الفعل قبل الضمير المتصل: ماضٍ آخره فتحة أو ضمير رفع، أو مضارعٌ أوله حرف مضارعة، أو أمرٌ',
                                   'الأمر من الثلاثي يبدأ بهمزة وصل، أو يبقى حرفين (المضعّف رُدَّ، واللفيف قِ)، ومن المزيد بهمزة أَفۡعِلۡ أو همزة وصل، '
                                   'أو على فَعِّ وفَاعِ وتَفَعَّلۡ'],
                barriers=['حرف مضارعة (أ ن ي ت) مفتوح أو مضموم بعد نزع «فَـ/وَـ» و«سَـ» وهمزة الاستفهام', 'همزة وصل في أوله',
                          'همزة في أوله (أ ء آ)', 'ضمير رفع تُ أو تِ بعد ساكن', 'حرفان مكتوبان أو أقل (رُدُّ، مُدُّ، فِرِّ، وَلِّ، قِ)',
                          'فَاعِ (ألفٌ ثانيةٌ وآخره مكسور: نَادِ)', 'فُوعِلَ (ضمّ الأول ومدٌّ بعده: بُورِكَ)', 'تنوين على الآخر'],
                counterexamples=['رُدُّهُ', 'مُدُّهُ', 'قِهِمُ', 'وَلِّهِ', 'نَادِهِ', 'ٱدۡعُهُ', 'أَلۡقِهِ', 'سَنُدۡخِلُهُمۡ', 'أَيَأۡمُرُكُم', 'كَتَبۡتُهُ', 'بُورِكَ'],
                source='صيغ الفعل المكتوبة قبل الضمير المتصل في أبواب التصريف؛ وقيست على QAC للقياس وحده',
                tests=['tests/test_batch_b.py::B01', 'tests/test_batch_b.py::B02', 'tests/test_closure.py::G01'],
                dependent_outputs=['word_class (14ب)', 'IDAFA I01', 'SUBJECT S01', 'inflection AGREE', 'closure certificate'],
                v1_defect='v1 عدّ الجذع ذا الحرفين المشدَّد الآخر (رُدُّهُ، مُدُّهُ) اسماً: الأمر المضعّف من الثلاثي يُضمّ آخره قبل «هُ»'),
    'E03': dict(version='v2', status='معطَّلة: مقدّمة نطاقٍ تنتظر حكم المالك', scope='المدخل المعتمد (hafs_kfgqpc) وحده',
                positive_premises=['P1 (غير مثبتة في المشروع): رواية حفص لا تكسر حرف المضارعة (لا تلتلة)',
                                   'الماضي والأمر من أَفۡعَلَ بهمزةٍ مفتوحة، والمجهول بمضمومة، وهمزة الوصل تُكتب «ٱ»'],
                barriers=['التلتلة: مضارع المتكلم بهمزةٍ مكسورة (إِخَالُ) في غير حفص', 'الأدوات المبدوءة بـ«إِ» (محمية قبل الجذر)'],
                counterexamples=['إِخَالُ'],
                source='لا مصدر في المشروع للمقدّمة P1؛ ومسح المدخل بالمحلّل نفسه لم يجد مضارعاً بحرف مضارعة مكسور (اتّساقٌ لا إثبات)',
                tests=['tests/test_batch_b.py::B04'],
                dependent_outputs=['word_class «إِحۡدَى»', 'IDAFA «إِحۡدَى ← هُمَا»', 'كاشف المكمّل CASE_NOT_WRITTEN', 'مرشّح الفاعل في وجه الغائبة'],
                v1_defect='v1 جعل «لا يبدأ فعلٌ بـإِ» قاعدةً عامة، وتنقضها التلتلة (إِخَالُ)'),
}
# المقدّمة P1 لـE03 لا تُعدّ مثبتة إلا بحكم المالك؛ ومع تعطيلها لا تُثبت E03 اسميةً، فتؤجَّل نتائجها التابعة
E03_PREMISE_P1_APPROVED = False


def host_case_vowel_proof(stem, enclitic):
    """E02 v2 (مقترحة): الاسمية قبل الضمير المتصل بنفي صيغ الفعل المكتوبة، بالمجال والموانع المسمّاة في E_RULES['E02'].
    → نصّ الدليل أو None"""
    if not enclitic or enclitic not in ATTACHED_PRONOUNS:
        return None
    t = _peel_verbal_proclitics(letters(stem))
    if len(t) < 3:
        return None                                             # حرفان أو أقل: رُدُّ، مُدُّ، فِرِّ، وَلِّ، قِ (أمرٌ ممكن)
    f0, m0 = t[0]
    if f0 in 'اٱ' and not m0 & {FATHA, DAMMA, KASRA}:
        return None
    if f0 in 'أءآ' or f0 in 'نيت' and m0 & {FATHA, DAMMA}:
        return None
    if DAMMA in m0 and t[1][0] in 'وي' and not t[1][1]:
        return None
    L, m = t[-1]
    if L == 'ت' and SUKUN in t[-2][1]:
        return None
    if len(t) == 3 and KASRA in m and t[1][0] == 'ا':
        return None                                             # فَاعِ من الناقص (نَادِ)
    if not m & {DAMMA, KASRA} or m & {FATHATAN, DAMMATAN, KASRATAN}:
        return None
    v = 'الضمة' if DAMMA in m else 'الكسرة'
    return (f'E02 v2 (مقترحة): آخر الجذع {v} قبل الضمير المتصل «{enclitic}»، وفيه ثلاثة أحرفٍ فأكثر، ولا يبدأ بحرف مضارعةٍ '
            f'ولا همزةٍ ولا همزة وصل، ولا يُختم بضمير رفع، وليس على فَاعِ ولا فُوعِلَ: فلا يكون فعلاً قبل ضمير')


def initial_hamza_kasra_proof(stem):
    """E03 v2: لا تُثبت اسميةً ما دامت مقدّمتها P1 (لا تلتلة في حفص) غير مثبتة في المشروع (E03_PREMISE_P1_APPROVED).
    ومع اعتمادها تعمل في المدخل المعتمد وحده. → نصّ الدليل أو None"""
    if not E03_PREMISE_P1_APPROVED:
        return None
    from . import quran_source
    if quran_source.name() != 'hafs_kfgqpc':
        return None
    t = _peel_verbal_proclitics(letters(stem))
    if len(t) >= 3 and t[0][0] == 'إ' and KASRA in t[0][1]:
        return 'E03 v2 (مقترحة، بمقدّمة P1 المعتمدة): همزة قطعٍ مكسورة مكتوبة في أول الجذع، ولا تلتلة في رواية حفص'
    return None


# ---------- الاسم ----------
def noun_features(G, seg, stem_slot, has_al, enclitic):
    """الاسمية تثبت بعلامةٍ مكتوبة لا يقبلها الفعل: قالب الاسم المغلق، أو «أل»، أو التنوين، أو تاء التأنيث المربوطة،
    أو ألف جمع المؤنث وتاؤه. وإلا فالصنف مؤجَّل (اسم أو فعلٌ لم يكشفه التوافق)، وسمات الاسم مرشّحةٌ لا مثبتة"""
    stem = stem_slot['text'] if stem_slot else G.O['text']
    tl = letters(stem)
    sfx0 = noun_suffix(stem)
    marks = []
    if (G.Theta.get('F') or {}).get('kind') == 'اسم' and G.closed:
        marks.append('قالب الاسم: ' + (G.Theta.get('P') or ''))
    if has_al:
        marks.append('«أل»')
    if _tanwin(tl):
        marks.append('التنوين')
    if sfx0 and sfx0[3] == 'ـَة':
        marks.append('التاء المربوطة')
    elif sfx0 and sfx0[0] == 'dual' and len(letters(_rest(stem, 2))) >= 3 and \
            (sfx0[3] == 'ـَيْنِ' or not (tl[0][0] in 'يتنأ' and tl[0][1] & {FATHA, DAMMA})):
        # «ـَيۡنِ» لا يُختم به فعل؛ و«ـَانِ» لا يُختم به إلا مضارعٌ بحرف مضارعة (يَفۡعَلَانِ): فهما علامة اسم بعد ثلاثة أحرف
        marks.append(f'لاحقة التثنية «{sfx0[3]}» بعد ثلاثة أحرفٍ فأكثر')
    elif sfx0 and sfx0[3] in ('ـَات', 'ـَٰت'):
        from .cells import stem_licence, licence_strength
        r_ = _rest(stem, sfx0[4])
        if r_ and licence_strength(list(stem_licence(r_))) >= 1:
            marks.append(f'اللاحقة «{sfx0[3]}» ورخصة البقية «{r_}»')
    if not marks:
        e = host_case_vowel_proof(stem, enclitic) or initial_hamza_kasra_proof(stem) or (None if enclitic or has_al else elative_evidence(stem))
        if e:
            marks.append(e)
    if marks:
        out = {'pos': feat('اسم', PROVEN, '، '.join(marks))}
    else:
        out = {'pos': feat(None, DEFER, 'لا علامة اسمٍ مكتوبة، ولم يكشفه التوافق فعلاً', alt=['اسم', 'فعل'])}
    P = G.Theta.get('P') or ''
    pos = (G.Theta.get('F') or {}).get('pos')
    if pos:
        if pos == 'بناء':
            # البناء اسمُ قالبٍ من أبنية سيبويه، لا نوعُ اشتقاق: يُعرض القالب، والجمود والاشتقاق غير محسومين به
            out['pattern'] = feat(P.replace('بناء سيبويه: ', ''), PROVEN, 'أبنية الأسماء عند سيبويه (data/patterns)')
            out['derivation'] = feat(None, DEFER, 'القالب وحده لا يعيّن الجمود والاشتقاق', alt=['جامد', 'مشتق'])
        else:
            out['derivation'] = feat(pos, PROVEN, f'القالب: {P}')
    sfx = noun_suffix(stem)
    t = letters(stem)
    if sfx:
        num, ptype, gen, shape, k = sfx
        rest = _rest(stem, k)
        from .cells import stem_licence, licence_strength
        lic = licence_strength(list(stem_licence(rest))) if rest else 0
        # إثبات اللاحقة: الوحدة مغلقةٌ بقالبٍ للمفرد، أو للبقية رخصةٌ معجمية
        if shape == 'ـَة':
            # التاء المربوطة علامة تأنيثٍ لفظية تثبت بالكتابة؛ ولا تثبت الإفراد (المَلَٰئِكَة، أَذِلَّة جموع تكسير)
            # ولا جنس المسمّى (خَلِيفَة)، إلا على قالب اسم الفاعل أو المفعول: فهي مؤنّثه المفرد (مُطَهَّرَةٌ)
            out['fem_marker'] = feat(True, PROVEN, 'التاء المربوطة مكتوبة')
            if G.closed and pos in ('اسم فاعل', 'اسم مفعول') and not _alif_hamza_start(stem):
                out['number'] = feat('singular', PROVEN, f'قالب {pos} المفرد ({P}) وتاء التأنيث')
                out['gender'] = feat('fem', PROVEN, f'مؤنّث {pos}: قالبه وتاء التأنيث')
            else:
                out['number'] = feat('singular', CAND, 'التاء المربوطة بلا قالبٍ يعيّن الإفراد: قد يكون جمع تكسير',
                                     alt=['singular', 'plural'])
                out['gender'] = feat('fem', CAND, 'علامة التأنيث اللفظية؛ وجنس المسمّى قد يخالفها', alt=['fem', 'masc'])
    if sfx and sfx[3] == 'ـَة':
        pass                                                   # حُكم أعلاه
    elif sfx:
        num, ptype, gen, shape, k = sfx
        rest = _rest(stem, k)
        from .cells import stem_licence, licence_strength
        lic = licence_strength(list(stem_licence(rest))) if rest else 0
        proven = (G.closed and pos in ('اسم فاعل', 'اسم مفعول', 'مصدر') and num != 'singular') or lic >= 2
        rl_ = letters(rest)
        if num == 'dual' and len(rl_) >= 3 and (shape == 'ـَيْنِ' or (rl_ and rl_[-1][0] == 'ت')):
            # «ـَيۡنِ» بعد ثلاثة أحرف (رَجُلَيۡنِ، شَهِيدَيۡنِ)، و«ـَتَانِ» تثنية المختوم بالتاء (امۡرَأَتَانِ): التثنية مكتوبة؛
            # لا «ـَانِ» وحدها (إِنۡسَان، سُلۡطَان مفردان)، ولا ما قبله أقلّ من ثلاثة (عَيۡن، دَيۡن)
            proven = True
        why = f'اللاحقة «{shape}»' + ('' if num == 'singular' else
                                     ('، والوحدة مغلقةٌ بقالب ' + P if G.closed and pos else f'، ورخصة البقية «{rest}» = {lic}'))
        st = PROVEN if proven else CAND
        out['number'] = feat(num, st, why)
        if ptype:
            out['plural_type'] = feat(ptype, st, why)
        if gen:
            out['gender'] = feat(gen, st, why + ('؛ علامة التأنيث المكتوبة (الجنس الصرفي، لا الحقيقي)' if gen == 'fem' else ''))
        elif num == 'dual':
            rl = letters(rest)
            if rl and rl[-1][0] in ('ي', 'و') and FATHA in rl[-1][1]:
                out['gender'] = feat(None, DEFER, why + '؛ وقبل لاحقة التثنية ياءٌ أو واوٌ مفتوحة (ألفٌ قد تكون للتأنيث: حُسْنَيَيْنِ)',
                                     alt=['fem', 'masc'])
            else:
                # لا علامة تأنيثٍ مكتوبة: والجنس سماعيٌّ لا يُعرف بالكتابة (عَيۡنَانِ مؤنثة)، إلا على قالب اسم الفاعل أو المفعول
                if G.closed and pos in ('اسم فاعل', 'اسم مفعول'):
                    out['gender'] = feat('masc', st, why + f'؛ وقالب {pos} بلا تاء التأنيث')
                else:
                    out['gender'] = feat(None, DEFER, why + '؛ ولا علامة تأنيث مكتوبة، وجنس المسمّى سماعي (عَيۡنَانِ مؤنثة)',
                                         alt=['masc', 'fem'])
    elif G.closed and pos in ('اسم فاعل', 'اسم مفعول'):
        if t and t[-1][1] & CASE_V and not _alif_hamza_start(stem):
            out['number'] = feat('singular', PROVEN, f'قالب {pos} المفرد ({P}) بلا لاحقة تثنيةٍ أو جمع، وحركة إعرابه مكتوبة')
            out['gender'] = feat('masc', PROVEN, f'قالب {pos} بلا علامة تأنيث')
        else:
            # بلا حركة إعرابٍ على آخره: قد يكون جمعاً أو مثنى حُذفت نونه للإضافة (حَاضِرِي، بَنُو)
            out['number'] = feat('singular', CAND, f'قالب {pos} بلا حركة إعرابٍ مكتوبة على آخره: قد تكون نونه حُذفت للإضافة',
                                 alt=['singular', 'plural', 'dual'])
            out['gender'] = feat('masc', CAND, f'قالب {pos} بلا علامة تأنيث، والعدد غير مثبت')
    elif G.closed and pos == 'مصدر':
        # قوالب المصدر تشارك قوالب جمع التكسير (فُعُول، فِعَال، فُعْل): قُلُوب، دِيَار، قِيَام؛ فلا يثبت الإفراد بالقالب
        out['number'] = feat('singular', CAND, f'قالب المصدر ({P}) قد يوافق قالب جمع تكسير', alt=['singular', 'plural'])
        out['gender'] = feat(None, DEFER, 'المصدر بلا علامة تأنيث: جنسه من السماع لا من الكتابة')
    else:
        out['number'] = feat(None, DEFER, 'لا لاحقة مكتوبة ولا قالبٌ يعيّن العدد (قد يكون جمع تكسير)',
                             alt=['singular', 'plural'])
        last = t[-1] if t else ('', set())
        if last[0] in ('ى', 'ا') or (last[0] == 'ء' and len(t) > 1 and t[-2][0] == 'ا'):
            out['gender'] = feat(None, DEFER, 'ألفٌ مقصورة أو ممدودة: قد تكون للتأنيث أو أصلية', alt=['fem', 'masc'])
        else:
            out['gender'] = feat(None, DEFER, 'لا علامة تأنيث مكتوبة، والتأنيث المعنوي لا يُعرف بالكتابة', alt=['masc', 'fem'])
    # التعريف والتنكير
    last = t[-1] if t else ('', frozenset())
    if has_al:
        out['definiteness'] = feat('معرفة', PROVEN, '«أل» مكتوبة')
    elif enclitic:
        out['definiteness'] = feat('معرفة', PROVEN, f'مضافٌ إلى الضمير المتصل «{enclitic}»')
    elif _tanwin(t):
        out['definiteness'] = feat('نكرة', PROVEN, 'التنوين مكتوب')
    else:
        out['definiteness'] = feat(None, DEFER, 'لا أل ولا تنوين ولا ضمير: قد يكون مضافاً إلى ظاهر أو ممنوعاً من الصرف',
                                   alt=['معرفة', 'نكرة'])
    if out['pos']['st'] != PROVEN:
        # الصنف غير مثبت: لا تثبت سمةٌ للاسم؛ والتعريف بالضمير المتصل لا يُرشَّح أصلاً (قد يكون فعلاً ومفعوله: عَلَّمَهُ)
        if enclitic and out.get('definiteness', {}).get('ev', '').startswith('مضافٌ إلى الضمير'):
            out['definiteness'] = feat(None, DEFER, f'بعده الضمير المتصل «{enclitic}»، والاسمية غير مثبتة: قد يكون فعلاً ومفعوله',
                                       alt=['معرفة', 'نكرة'])
        for k, r in out.items():
            if k != 'pos' and r['st'] == PROVEN:
                r['st'], r['ev'] = CAND, r['ev'] + '؛ والاسمية غير مثبتة'
    return out


# ---------- العوامل الفعلية (كان وأخواتها، وكاد، وليس…) ----------
SUBJ_PRON = ('تُمْ', 'تُمَا', 'تُنَّ', 'تُ', 'تَ', 'تِ', 'نَا', 'وا', 'نَ', 'ا', 'تْ', 'تَا')


def _with_subject(text, su, ui, seg):
    """الوحدة وما يليها من ضمير رفعٍ متصل فصله التقشير (كُنۡ + تُمۡ)، إن كان التالي ضميراً من صور ضمائر الرفع"""
    if ui + 1 < len(su):
        ns = [seg['slots'][i] for i in su[ui + 1].get('slots', [])]
        if ns and all(x['type'] == 'مبني' for x in ns):
            nxt = ''.join(x['text'] for x in ns)
            if nxt in SUBJ_PRON:
                return text + nxt
    return text

def _verbal_operator(text):
    """→ هوية العامل الفعلي إن كان المكتوب صيغةً من صيغه في الجرد المعتمد (sarf/protected.py VERBAL)، أو None"""
    from .protected import VERBAL
    from .chars import letters as _l
    key = [(L, frozenset(m)) for L, m in _l(text)]
    t = _l(text)
    if len(t) >= 3 and t[0][0] == 'أ' and FATHA in t[0][1] and SUKUN in t[1][1] and FATHA in t[2][1]:
        return None                       # أَفۡعَلُ: مضارع المتكلم أو اسم التفضيل (أَعۡلَمُ)
    for ident, (forms, amb) in VERBAL.items():
        if amb:
            continue                      # الملتبس بفعلٍ تامّ أو باسمٍ (ظَنَّ، عَلِمَ): لا يثبت بالجرد وحده
        for f in forms:
            if [(L, frozenset(m)) for L, m in _l(f)] == key:
                return ident
    return None


def _verbal_operator_features(text, agr=None):
    """العامل الفعلي فعلٌ بالجرد المعتمد، ولا جذر له ولا وزن بحكم الدستور؛ وزمنه من صيغته المكتوبة"""
    from .affix import stem_info
    from .agreement import agreement
    ident = _verbal_operator(text)
    src = f'صيغةٌ من صيغ العامل الفعلي «{ident}» في الجرد المعتمد (sarf/protected.py VERBAL)'
    out = {'pos': feat('فعل', PROVEN, src), 'operator': feat('ناسخٌ أو عاملٌ فعلي', PROVEN, src),
           'augmentation': feat(None, NA, 'وحدة محمية: لا جذر ولا وزن'), 'transitivity': feat(None, NA, 'عاملٌ ناسخ')}
    info = stem_info(text)
    kind = info['kind']
    if kind is None and text == ident:
        kind = 'madi'                                    # الصيغة نفسها مدخلُ الجرد: الماضي (كَانَ، لَيْسَ)
    if kind in TENSE:
        out['tense'] = feat(TENSE[kind], PROVEN, src + '، وصيغته المكتوبة')
    else:
        out['tense'] = feat(None, DEFER, 'لم تعيّن الصيغة المكتوبة زمنه', alt=list(TENSE.values()))
    g = agr or (agreement(text, dict(info, pos='verb', kind=kind)) if kind else None)
    fs = (g or {}).get('features') or []
    if len(fs) == 1:
        p_, n_, gg = fs[0]
        out['subject'] = feat(dict(person=p_, number=n_, gender=gg), PROVEN, (g or {}).get('rule') or '')
    elif fs:
        out['subject'] = feat(None, DEFER, (g or {}).get('rule') or '', alt=[dict(person=a, number=b, gender=c) for a, b, c in fs])
    return out


# ---------- الوحدات ----------
def unit_features(a, units):
    """→ {(wi, ui): {السمة: سجل}} لكل وحدة لفظية"""
    agr = {(g['word_index'], g['slot']): g for g in a.get('agreement', [])}
    gov = {}
    segs_ = {sg['word_index']: sg for sg in a['segments']}
    for r in a.get('relations', []):
        t_ = r.get('target') or {}
        try:
            wtxt = segs_[r['word_index']]['slots'][r['slot']]['text']     # العامل بصورته المكتوبة لا باسمه في الفهرس
        except (KeyError, IndexError, TypeError):
            wtxt = None
        # العامل الذي لا يدخل إلا على المضارع؛ لا «أَنْ» ولا «لَمَّا» ولا أدوات الشرط (تدخل على الماضي)
        if r.get('expected') in ('نصب', 'جزم') and t_.get('type') == 'جذع' and wtxt in MUDARI_ONLY:
            gov[(t_['word_index'], t_['slot'])] = (wtxt, r['expected'])
    morph = {(m['word_index'], m['slot']): m for m in a.get('morph', [])}
    out = {}
    for seg in a['segments']:
        wi = seg['word_index']
        su = seg['units']
        for ui, u in enumerate(su):
            G = units.get((wi, ui))
            if G is None:
                continue
            slots = [seg['slots'][i] for i in u.get('slots', [])]
            stem = next((s for s in slots if s['type'] == 'جذع'), None)
            stem_i = next((i for i in u.get('slots', []) if seg['slots'][i]['type'] == 'جذع'), None)
            nxt = su[ui + 1] if ui + 1 < len(su) else None
            encl = None
            if nxt:
                ns = [seg['slots'][i] for i in nxt.get('slots', [])]
                if ns and all(s['type'] == 'مبني' and s.get('role') == 'enclitic' for s in ns):
                    encl = ''.join(s['text'] for s in ns)
            lexk = G.Theta.get('lex')
            prot = G.Theta.get('protected')
            if stem_i is not None and (wi, stem_i) in agr:
                rec = verb_features(G, agr[(wi, stem_i)], morph.get((wi, stem_i)), encl, gov.get((wi, stem_i)))
                mrec = morph.get((wi, stem_i)) or {}
                if _afalu_contested(G.O['text'], agr[(wi, stem_i)], gov.get((wi, stem_i))) and elative_evidence(G.O['text']):
                    # FA02 (المالك، مراجعة 18:34 «أَكْثَرُ»): الكتابة تنفي الفعل (E01: عين الماضي في HFN وحركة العين المكتوبة)، فالصنف
                    # اسمٌ بدليله في السمات كما في العلاقات — طبقةٌ واحدة للصنف، لا فعلٌ هنا واسمٌ هناك
                    rec = noun_features(G, seg, stem, False, encl)
                elif _afalu_contested(G.O['text'], agr[(wi, stem_i)], gov.get((wi, stem_i))):
                    # «أَفْعَلُ» بحركة إعرابٍ في الآخر، بلا لاحقةٍ ولا عاملٍ يحكمه، ولا ينفي E01 الفعل (حرف حلق، أو فَعِلَ، أو آخرٌ مفتوح):
                    # صورةُ مضارع المتكلم وصورةُ أفعل التفضيل معاً (أَعْلَمُ: أنا أعلم، أو أكثر علماً). فالصنف مؤجَّل بالوجهين، لا مثبتٌ
                    # من حرف المضارعة وحده؛ ولا تُبنى على وجه الفعل سماتٌ مثبتة (V-RAF1 تطلب الصنف مثبتاً)
                    rec = {'pos': feat(None, DEFER, '«أَفْعَلُ» بحركة إعرابٍ بلا لاحقة ولا عامل: مضارع المتكلم أو أفعل التفضيل، '
                                                   'والكتابة لا تفرّق بينهما', alt=['فعل', 'اسم'])}
                elif mrec.get('noun_template_rivals'):
                    # AR02 §١٥: وجهٌ اسمي حيّ ينازع الفعل (§٨): لا تبقى سمات الوجه الفعلي مختارةً على الوقوع
                    rec = {'pos': feat(None, DEFER, 'فعلٌ أو اسم: بناءٌ اسمي (' + '، '.join(
                        f"{r['root']} {r['pattern']}" for r in mrec['noun_template_rivals'][:2]) + ') ينازع دليل الفعل (حرف المضارعة وسكون الآخر)')}
            elif stem is not None and not prot and lexk not in ('عامل', 'مبني', 'لفظ الجلالة'):
                rec = noun_features(G, seg, stem, any(s['type'] == 'أل' for s in slots), encl)
            elif _verbal_operator(_with_subject(G.O['text'], su, ui, seg)):
                # الصيغة مع ضمير الرفع المتصل بها إن فصله التقشير (كُنۡ | تُمۡ ← كُنۡتُمۡ)
                rec = _verbal_operator_features(_with_subject(G.O['text'], su, ui, seg),
                                                agr.get((wi, stem_i)) if stem_i is not None else None)
            elif lexk in ('مبني',) or (stem is None and lexk):
                rec = {'pos': feat(lexk, PROVEN, 'خانة ' + lexk)}
                rec.update(mabni_features(G.O['text']))
            elif prot:
                rec = {'pos': feat(prot.get('cls'), PROVEN, 'وحدة محمية دستورياً: لا جذر ولا وزن'),
                       'augmentation': feat(None, NA, 'وحدة محمية'), 'transitivity': feat(None, NA, 'وحدة محمية')}
            else:
                rec = {'pos': feat(None, DEFER, 'لم يتعيّن صنف الوحدة')}
            # سماتٌ مضافة من سجل التغطية (sarf.features_ext): لا تُضاف إلا الأسماء الغائبة، فلا تتغيّر سمةٌ قائمة
            from .features_ext import extra_features
            vi = _verbal_operator(_with_subject(G.O['text'], su, ui, seg)) if 'operator' in rec else None
            host = out.get((wi, ui - 1)) if ui and slots and all(s['type'] == 'مبني' and s.get('role') == 'enclitic'
                                                               for s in slots) else None
            for k_, v_ in extra_features(G, rec, any(s['type'] == 'أل' for s in slots), encl, prot, lexk, vi, host).items():
                rec.setdefault(k_, v_)
            out[(wi, ui)] = rec
    from .features_ext import post_features
    post_features(a, units, out)
    return out
