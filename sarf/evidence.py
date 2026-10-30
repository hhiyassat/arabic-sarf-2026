# -*- coding: utf-8 -*-
"""
sarf.evidence — نفي المرشَّح بالكتابة (القرار 7 في المخطط: العامل يُتحقَّق منه بالكتابة).
يضيف لكل مرشَّح status/reject_reason بحالات T09 (sarf.status): الممنوع يبقى في القائمة ومعه سببه،
وما لم يُمنع مؤجَّل حتى يحكم له sarf.judge بالقبول.
نوع ما بعد العامل (فعل أو اسم) وعلامته من مقشِّر الزوائد (sarf.affix).

R1/R2  لام الأمر ولا الناهية: ما بعدها مضارع مجزوم، فتُرفضان إن كان اسماً، أو غير مضارع،
       أو مضارعاً مرفوعاً (أو بثبوت النون) أو منصوباً
R3     اسم الفعل الناصب: يُرفض إن كان ما بعده مرفوعاً
R4     وَ الجارّة (القسم) وواو المعية: تُرفضان إن كان بعدها فعل، أو عامل، أو ضمير رفع منفصل
R5     اللام المفتوحة الجارّة: تُرفض إن كان بعدها فعل (هي لام التوكيد أو جواب القسم)
R6     حرف الجر وواو المعية: يُمنعان إن كان ما بعدهما مرفوعاً كتابةً (ضمة، أو تنوين ضم، أو ـُونَ)،
       أو ساكن الآخر وليس مبنياً من الملف (وَلَقَدۡ، وَلَهُمۡ)
R8     السابقة: تُمنع إن بدأت بقية الكلمة بساكن أو مشدَّد (غير اللام وهمزة الوصل وبِسۡمِ)
R9     بِ وكَ وتَ الجارّة المتصلة: تُمنع إن كان بعدها فعل
R10    السابقة ذات الحرف الواحد (و ف ك ل ب): لا تُفصل بلا رخصةٍ للبقية؛ فإن رُخِّصت الكلمة كلها ببنائها
       أو معجمها ولم تُرخَّص البقية، فالحرف من أصل الكلمة (كَبِيرًا، وَلِيُّهُۥ، لِقَآءَ، فَرِهَٰنٌ ← بل ف + رِهَٰن)
R7     اسم الشرط الجازم (مج 7): يُمنع إن كان ما بعده مرفوعاً كتابةً أو ضمير رفع منفصلاً
       (مَا تَفْعَلُونَ، مَا يَوْمُ ٱلدِّينِ)؛ ولا يشمل لَوْ وإِذَا لأنهما لا تجزمان
"""
from .chars import letters, FATHATAN, KASRATAN, FATHA, KASRA, DAMMA, DAMMATAN, SUKUN, SHADDA, plain, strip_marks as _strip_marks
from .match import match_letters, PRON_SUFFIXES, vform_match
from .affix import stem_info, raf_mark, RAF_PRONOUNS
from .status import DEFERRED, BLOCKED

CASE = {'رفع': 'مرفوع', 'نصب': 'منصوب'}


def _text(toks):
    return ''.join(L + ''.join(sorted(m)) for L, m in toks)

def _target_after(f, words):
    """نص المعمول: بقيّة الكلمة بعد السابقة (proclitic)، أو الكلمة التالية."""
    if f['method'].startswith('proclitic'):
        return _text(match_letters(f['word'], f.get('expanded', True))[f['char_span'][1]:])
    nxt = f['word_index'] + 1
    return words[nxt] if nxt < len(words) else None

HAMZA_LETTERS = 'ءأإآؤئ'
# حرف الجر مدغماً في «ما» أو «مَن» الاستفهامية أو الموصولة: بنيةٌ معروفة بعد السابقة (وَمِمَّا، وَعَمَّا، وَفِيمَا)
MERGED_V = ('مِمَّا', 'مِمَّنْ', 'عَمَّا', 'عَمَّنْ', 'فِيمَا', 'فِيمَ', 'بِمَا', 'بِمَ', 'لِمَا', 'لِمَ', 'كَمَا', 'مِمَّ',
            'عَمَّ', 'إِلَامَ',
            # أسماءٌ مبنية أو ملازمة للإضافة تقع بعد السابقة (وَلِذِي، لَمَعَكُمۡ)
            'ذِي', 'ذُو', 'ذَا', 'ذَاتِ', 'ذَوَاتَيْ', 'أُولِي', 'أُولُو', 'مَعَ', 'مَعَكُمْ', 'مَعَهُ', 'مَعَهُمْ', 'مَعَنَا', 'مَعِيَ')
PROCLITIC_ONE = ('وَ', 'فَ', 'كَ', 'لِ', 'لَ', 'بِ')


def _strip_enclitic(t):
    """البقية بلا الضمير المتصل في آخرها (مَعَكُمۡ ← مَعَ)"""
    from .cells import ENCLITICS_V
    toks = match_letters(t)
    for suf in ENCLITICS_V:
        k = len(match_letters(suf))
        if len(toks) > k + 1 and vform_match(toks[-k:], [suf]):
            return _text(toks[:-k])
    return t


def _licence(f, tgt, found, lex):
    """R10: سببُ منع الفصل إن رُخِّصت الكلمة كلها ولم تُرخَّص البقية، وإلا None.
    رخصة البقية: جذعٌ مرخَّص (sarf.cells.stem_licence)، أو ضمير متصل، أو مبني في الملف، أو «أل» أو همزة وصل
    يليها ساكن، أو همزة، أو عاملٌ آخر يبدأ بعدها. والرخصتان تُحفظان في المرشَّح للبيان"""
    from .cells import stem_licence, licence_strength
    op = f['operator']
    if not vform_match(op, PROCLITIC_ONE):
        return None
    toks = match_letters(tgt)
    if not toks:
        return None
    L0, m0 = toks[0]
    nxt = toks[1] if len(toks) > 1 else None
    bare = _strip_enclitic(tgt)
    # البقية كما كُتبت (بالخنجرية): ذَٰلِكَ في الملف لا «ذَالِكَ»
    raw = ''.join(L + ''.join(sorted(m)) for L, m in letters(f['word'])[1:]) if len(f['operator']) <= 2 else tgt
    # البقية بنيةٌ يعرفها المقشِّر (قوة 3): همزة، ضمير متصل، همزة وصل يليها ساكن، لام «أل» بعد لام الجر، مبنيٌّ في
    # الملف، حرفٌ وضمير أو مبني (لَهُۥ، لِذِي)، أو عاملٌ آخر يبدأ بعدها
    structural = L0 in HAMZA_LETTERS or vform_match(tgt, PRON_SUFFIXES) or vform_match(tgt, MERGED_V) or \
        L0 == 'ا' and nxt is not None and (not nxt[1] or SUKUN in nxt[1] or SHADDA in nxt[1] or nxt[0] == 'ل') or \
        vform_match(op, ('لِ',)) and L0 == 'ل' and (not m0 or SUKUN in m0) or \
        bool(lex and any(lex.lookup(t) or lex.attested(t) for t in {tgt, bare, raw, _strip_enclitic(raw)})) or \
        L0 in 'لبك' and len(toks) > 1 and m0 & {FATHA, KASRA} and \
        (not any(m & {SHADDA, DAMMATAN, KASRATAN, FATHATAN} for _, m in toks[1:]) and
         vform_match(toks[1:], PRON_SUFFIXES) or bool(lex and lex.lookup(_strip_enclitic(_text(toks[1:]))))) or \
        any(g is not f and g['word_index'] == f['word_index'] and g.get('char_span') and
            g['char_span'][0] >= f['char_span'][1] for g in found)
    word = _text(match_letters(f['word'], f.get('expanded', True)))
    whole = stem_licence(word)
    rest = () if structural else stem_licence(tgt)
    # الفعل بعد السابقة: لا يدخل الجارّ على الفعل (بِ، كَ)، ولا لام الجر على الماضي (لِقَآءَ ليس لِ + قَاءَ)؛
    # والبقية التي عليها دليل الاسم (تنوين، أل، تاء مربوطة) ليست فعلاً
    ri = stem_info(tgt)
    verb_ok = vform_match(op, ('وَ', 'فَ', 'لَ')) or vform_match(op, ('لِ',)) and ri['kind'] == 'mudari'
    if not verb_ok or ri['pos'] == 'noun':
        rest = tuple(x for x in rest if x[0] not in ('فعل', 'فعل محتمل', 'فعل بالكتابة'))
    s_whole = licence_strength(whole)
    s_rest = 3 if structural else max(licence_strength(rest), 1 if ri['pos'] == 'verb' and verb_ok else 0)
    # قراءتا فعلٍ متنافستان (وَجِئۡتُ: «وجء» أو وَ + «جِئۡتُ»): لا تُقدَّم الكلمة كلها على البقية بمرتبة الدليل
    verbish = ('فعل', 'فعل محتمل', 'فعل بالكتابة')
    # ودليل الفعلية المكتوب في آخر الكلمة (ضمير رفعٍ بعد ساكن) تشترك فيه الكلمة كلها وبقيتها، فلا يرجّح إحداهما
    if any(x[0] in verbish for x in whole) and verb_ok and \
            (any(x[0] in verbish for x in rest) or ri['pos'] == 'verb' or stem_info(word)['pos'] == 'verb'):
        s_whole = min(s_whole, s_rest)
    if 0 < s_whole <= s_rest < 3:
        f['alternative'] = 'الحرف أصليٌّ في «' + word + '» (' + '، '.join(f'{k}: {r}' for k, r, _ in whole[:2]) + ')'
    f['licence'] = dict(whole=[list(x) for x in whole[:2]], whole_strength=s_whole,
                        rest='بنيةٌ معروفة' if structural else [list(x) for x in rest[:2]], rest_strength=s_rest)
    if s_whole > s_rest:
        k, root, what = whole[0]
        return (f'الكلمة كلها مرخَّصة ({k}: {root}، {what}؛ قوة {s_whole})، والبقية «{tgt}» ' +
                (f'أضعف رخصة (قوة {s_rest})' if s_rest else 'لا رخصة لها') + ': الحرف من أصل الكلمة')
    return None


def reject_candidates(found, words, lex=None):
    for f in found:
        f['status'], f['reject_reason'], f['checked'] = DEFERRED, None, []
    for f in found:
        op = f['operator']                    # العامل بصيغته المشكولة من الفهرس (لا يُجرَّد)
        tgt = _target_after(f, words)
        if not tgt:
            continue
        info = stem_info(tgt)
        reason = None
        # R8: السابقة لا يليها ساكن ولا مشدَّد في أول البقية، فالحرف أصليّ (كَيۡدَهُمۡ، كَذَّبَتۡ، وَيۡلٌ)؛
        # إلا اللام (فَلۡيَنظُرِ، لِلَّهِ) وهمزة الوصل، و«بِسۡمِ» (حُذفت ألف «اسم» خطاً)
        if f['method'].startswith('proclitic'):
            first_L, first_m = match_letters(tgt)[0]
            # اللام المشدَّدة أول البقية لا تكون لام «أل» إلا بعد لام الجر (لِلَّهِ، لِلَّذِينَ: حُذفت الألف خطاً)؛
            # وبعد غيرها فالشدة من أصل الكلمة (كَلَّا، كَلَّمَ، وَلَّىٰ)
            shadda_lam = first_L == 'ل' and SHADDA in first_m and not vform_match(op, ('لِ', 'لَ'))
            lic = _licence(f, tgt, found, lex)
            if lic:
                f['checked'].append('R10 رخصة البقية')
                reason = lic
                f['radical'] = True
            elif shadda_lam:
                f['checked'].append('R8 أول البقية لامٌ مشدَّدة')
                reason = 'أول ما بعدها لامٌ مشدَّدة بلا لام جرٍّ قبلها: الشدة من أصل الكلمة'
                f['radical'] = True
            elif (SUKUN in first_m or SHADDA in first_m) and first_L not in ('ل', 'ا') and \
                    not (len(match_letters(tgt)) > 1 and match_letters(tgt)[0][0] == 'س' and
                         SUKUN in match_letters(tgt)[0][1] and match_letters(tgt)[1][0] == 'م'):   # بِسۡمِ
                f['checked'].append('R8 أول البقية ساكن')
                reason = f"أول ما بعدها {'ساكن' if SUKUN in first_m else 'مشدَّد'}: الحرف من أصل الكلمة لا سابقة"
                f['radical'] = True
            # R9: حرف الجر المتصل (بِ، كَ، تَ) لا يدخل على الفعل
            elif vform_match(op, ('بِ', 'كَ', 'تَ')) and f['group'] == '1' and info['pos'] == 'verb':
                f['checked'].append('R9 الفعل بعد حرف الجر')
                reason = f"بعدها فعل ({'، '.join(info['evidence'])}): ليست جارّة"
                f['radical'] = vform_match(op, ['كَ'])            # كَفَرُوا: الكاف أصلية؛ والباء والتاء قد تكونان سابقتين غير جارّتين
        # R1/R2: لام الأمر ولا الناهية — ما بعدها مضارع مجزوم
        if reason:
            pass
        elif f['group'] == '6' and vform_match(op, ('لِ', 'لَا')):
            f['checked'].append('R1/R2 المجزوم بعدها')
            if info['pos'] == 'noun':
                reason = f"ما بعدها اسم ({'، '.join(info['evidence'])})"
            elif info['kind'] != 'mudari':
                reason = 'ما بعدها ليس فعلاً مضارعاً'
            elif info['mood'] in CASE:
                why = 'ثبوت النون' if info['suffix'] == 'نون الرفع' else CASE[info['mood']]
                reason = f'الفعل بعدها غير مجزوم كتابةً ({why})'
        # R3: اسم الفعل الناصب للمفعول — ما بعده مرفوع
        elif f['group'] == '9' and vform_match(op, ('رُوَيْدَ', 'بَلْهَ', 'دُونَكَ', 'عَلَيْكَ')):
            f['checked'].append('R3 المنصوب بعده')
            last = match_letters(tgt)[-1][1]
            if last & {DAMMA, DAMMATAN}:
                reason = 'ما بعده مرفوع كتابةً، واسم الفعل ينصب مفعوله'
        # R4: واو القسم الجارّة وواو المعية — لا تدخلان على فعل ولا حرف ولا ضمير رفع
        elif vform_match(op, ['وَ']) and f['group'] in ('1', '4') and f['method'].startswith('proclitic'):
            f['checked'].append('R4 الاسم بعد الواو')
            after = [g for g in found if g is not f and g['word_index'] == f['word_index'] and
                     g['char_span'] and g['char_span'][0] == f['char_span'][1]]
            if vform_match(tgt, RAF_PRONOUNS, loose=True):
                reason = 'بعدها ضمير رفع منفصل: الواو عاطفة أو حالية'
            elif info['pos'] == 'verb':
                reason = f"بعدها فعل ({'، '.join(info['evidence'])}): الواو عاطفة"
            elif after:
                reason = f"بعدها عامل ({after[0]['operator']}): الواو عاطفة"
        # R5: اللام المفتوحة قبل الفعل لام توكيد أو جواب قسم، لا جارّة
        elif vform_match(op, ['لِ']) and f['group'] == '1' and f['method'].startswith('proclitic'):
            f['checked'].append('R5 اللام المفتوحة قبل الفعل')
            if FATHA in match_letters(f['word'])[f['char_span'][0]][1] and info['pos'] == 'verb':
                reason = f"اللام المفتوحة قبل الفعل ({'، '.join(info['evidence'])}) لام توكيد أو جواب قسم، لا جارّة"
        # المعمول ضمير متصل بالعامل (عَلَيْكَ، لَهُ): مبني، فلا تدلّ حركته على الإعراب
        on_pronoun = f['method'] == 'operator+suffix' or \
            f['method'].startswith('proclitic') and vform_match(tgt, PRON_SUFFIXES)
        if not reason and not on_pronoun and (f['group'] == '1' or vform_match(op, ['وَ']) and f['group'] == '4'):
            f['checked'].append('R6 المرفوع بعد الجار')
            mark = raf_mark(tgt, sukun=True)
            if mark:
                what = 'تجرّ' if f['group'] == '1' else 'تنصب المفعول معه'
                state = 'ساكن الآخر' if mark == 'السكون' else f'مرفوع كتابةً ({mark})'
                reason = f'ما بعدها {state}، و«{f["operator"]}» {what}'
        # وإِنۡ لا تُمنع بما بعدها: يليها الاسم المرفوع أو الضمير، والفعل مقدَّر يفسّره المذكور
        # (وَإِنۡ أَحَدࣱ مِّنَ ٱلۡمُشۡرِكِينَ ٱسۡتَجَارَكَ، إِنۡ أَنتُمۡ ضَرَبۡتُمۡ)، كما في كتب النحو
        if not reason and not on_pronoun and f['group'] == '7' and not vform_match(op, ('لَوْ', 'إِذَا')):
            f['checked'].append('R7 المرفوع بعد أداة الشرط')
            mark = raf_mark(tgt)
            if vform_match(tgt, RAF_PRONOUNS, loose=True):
                reason = 'بعدها ضمير رفع منفصل، وأداة الشرط يليها فعل: ليست شرطية هنا'   # إِنۡ هُوَ إِلَّا ذِكۡرٌ
            elif mark:
                reason = f'ما بعدها مرفوع كتابةً ({mark})، وأداة الشرط تجزم: ليست شرطية هنا'
        if reason:
            f['status'], f['reject_reason'] = BLOCKED, reason
    return found
