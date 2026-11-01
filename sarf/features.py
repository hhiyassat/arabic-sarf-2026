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
    if governor:
        out['tense'] = feat('مضارع', PROVEN, f'العامل «{governor[0]}» قبله يقتضي {governor[1]}، ولا يُنصب ولا يُجزم إلا المضارع')
        if kind != 'mudari':
            out['tense']['ev'] += f'؛ وخالفه صنف الإسناد ({TENSE.get(kind)})'
            kind = 'mudari'
    elif tense_ambig:
        out['tense'] = feat(TENSE.get(kind), CAND, why_amb, alt=['ماضٍ', 'أمر', 'مضارع'])
    else:
        out['tense'] = feat(TENSE.get(kind), PROVEN if kind in TENSE else DEFER, 'صنف الإسناد: ' + sig)
    vo = agr.get('voice')
    out['voice'] = feat({'active': 'معلوم', 'passive': 'مجهول'}.get(vo), PROVEN if vo in ('active', 'passive') else DEFER,
                        'حركات الفعل المكتوبة' if vo else 'لم تعيّنه الحركات المكتوبة', alt=None if vo else ['معلوم', 'مجهول'])
    fs = agr.get('features') or []
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
    if tl and tl[-1][1] & TANWIN:
        marks.append('التنوين')
    if sfx0 and sfx0[3] == 'ـَة':
        marks.append('التاء المربوطة')
    elif sfx0 and sfx0[3] in ('ـَات', 'ـَٰت'):
        from .cells import stem_licence, licence_strength
        r_ = _rest(stem, sfx0[4])
        if r_ and licence_strength(list(stem_licence(r_))) >= 1:
            marks.append(f'اللاحقة «{sfx0[3]}» ورخصة البقية «{r_}»')
    if marks:
        out = {'pos': feat('اسم', PROVEN, '، '.join(marks))}
    else:
        out = {'pos': feat(None, DEFER, 'لا علامة اسمٍ مكتوبة، ولم يكشفه التوافق فعلاً', alt=['اسم', 'فعل'])}
    P = G.Theta.get('P') or ''
    pos = (G.Theta.get('F') or {}).get('pos')
    if pos:
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
                out['gender'] = feat('masc', st, why + '؛ ولا علامة تأنيث قبل لاحقة التثنية')
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
    elif last[1] & TANWIN:
        out['definiteness'] = feat('نكرة', PROVEN, 'التنوين مكتوب')
    else:
        out['definiteness'] = feat(None, DEFER, 'لا أل ولا تنوين ولا ضمير: قد يكون مضافاً إلى ظاهر أو ممنوعاً من الصرف',
                                   alt=['معرفة', 'نكرة'])
    if out['pos']['st'] != PROVEN:
        # الصنف غير مثبت: لا تثبت سمةٌ للاسم
        for k, r in out.items():
            if k != 'pos' and r['st'] == PROVEN:
                r['st'], r['ev'] = CAND, r['ev'] + '؛ والاسمية غير مثبتة'
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
            elif stem is not None and not prot and lexk not in ('عامل', 'مبني', 'لفظ الجلالة'):
                rec = noun_features(G, seg, stem, any(s['type'] == 'أل' for s in slots), encl)
            elif lexk in ('مبني',) or (stem is None and lexk):
                rec = {'pos': feat(lexk, PROVEN, 'خانة ' + lexk)}
                rec.update(mabni_features(G.O['text']))
            elif prot:
                rec = {'pos': feat(prot.get('cls'), PROVEN, 'وحدة محمية دستورياً: لا جذر ولا وزن'),
                       'augmentation': feat(None, NA, 'وحدة محمية'), 'transitivity': feat(None, NA, 'وحدة محمية')}
            else:
                rec = {'pos': feat(None, DEFER, 'لم يتعيّن صنف الوحدة')}
            out[(wi, ui)] = rec
    return out
