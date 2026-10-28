# -*- coding: utf-8 -*-
"""
sarf.match — مطابقة العوامل في الكلمة بحسب الفهرس:
  1. عامل متعدد الكلمات   2. الكلمة كاملة   3. عامل + لاحقة   3a. ما الكافة   3b. نداء موصول
  4. سابقة حرفية + بقية الكلمة؛ ويُسبَق 2–4 بتقشير وَ/فَ العاطفتين.
"""
from .chars import (FATHA, KASRA, SUKUN, SHADDA, DAGGER_ALIF,
                    letters, plain, vowel, strip_marks as _strip_marks)
from .divine import divine_name

def vocal_compatible(word_toks, op_toks, skip_first_shadda=True):
    """
    هل تشكيل الكلمة لا يناقض تشكيل العامل؟ (الحروف متساوية العدد)
    - حركتان مختلفتان على الحرف نفسه ⇒ تعارض
    - شدة في أحدهما دون الآخر (والآخر مشكول) ⇒ تعارض، إلا شدة الإدغام على الحرف الأول (مِّنْ)
    - غير المشكول لا يناقض شيئاً
    → (compatible, n_checked_letters)
    """
    checked = 0
    for idx, ((_, wm), (_, om)) in enumerate(zip(word_toks, op_toks)):
        if not wm or not om:
            continue
        wv, ov = vowel(wm), vowel(om)
        if wv and ov:
            checked += 1
            if wv != ov:
                return False, checked
        if (SHADDA in wm) != (SHADDA in om):
            if not (idx == 0 and skip_first_shadda):
                # السكون مقابل الشدة/الحركة تعارض صريح؛ غياب الشدة مع حركة متفقة يُتسامح فيه للكلمة غير التامة التشكيل
                if (SHADDA in om and SUKUN in wm) or (SHADDA in wm and SUKUN in om) or (wv and ov):
                    return False, checked
        if (SUKUN in wm) and ov and SHADDA not in om:
            # حرف ساكن في الكلمة متحرك في العامل — يُتسامح في آخر الكلمة (سكون الوقف)
            if idx != len(op_toks) - 1:
                return False, checked
    return True, checked

PRON_SUFFIXES = ['هُو', 'هِي', 'هُمَا', 'كُمَا', 'هُمْ', 'هُنَّ', 'كُمْ', 'كُنَّ', 'هَا', 'نَا', 'نِي', 'هُ', 'هِ', 'كَ', 'كِ', 'ي', 'هِمْ', 'هِمَا', 'هِنَّ']
VERB_SUFFIXES = ['ُوا', 'ُوا۟', 'َتْ', 'َا', 'ُونَ', 'ْتُمْ', 'ْتُ', 'ْتَ', 'ْنَا', 'ْنَ', 'ْتِ']
# العوامل التي تقبل لاحقة: (المجموعة) → قائمة اللواحق
SUFFIX_GROUPS = {'1': 'pron', '2': 'pron', '10': 'both', '11': 'both', '13': 'pron'}
# ى/ا الأخيرة تنقلب ياءً قبل الضمير: عَلَى → عَلَيْهِمْ، إِلَى → إِلَيْهِ
ALIF_TO_YA = {'على', 'إلى', 'لدى', 'حتى'}

# السوابق الحرفية: الحرف → الحركات المقبولة
PROCLITICS = {
    'ب': {KASRA},
    'ل': {KASRA, FATHA, SUKUN},   # لِ الجر/الأمر، لَ التوكيد، لْ الأمر بعد وَ/فَ
    'ك': {FATHA},
    'و': {FATHA},
    'ت': {FATHA},
}
CONJ = {'و', 'ف'}   # عاطفتان تُقشَّران قبل البحث

# ما الكافة بعد إنّ وأخواتها: تكفّها عن العمل (إلا ليت فيجوز فيها الوجهان)
KAFFA_GROUPS = {'2'}
KAFFA_EFFECT = {
    'إن': 'مكفوفة عن العمل؛ أداة حصر وقصر — ما بعدها مبتدأ وخبر أو جملة فعلية',
    'أن': 'مكفوفة عن العمل؛ تفيد الحصر — ما بعدها مبتدأ وخبر أو جملة فعلية',
    'ليت': 'يجوز إعمالها (نصب الاسم ورفع الخبر) وإهمالها',
    None: 'مكفوفة عن العمل — ما بعدها مبتدأ وخبر أو جملة فعلية',
}

# ---------- Stage 1: Match ----------
def match_letters(word, expand_dagger=True):
    """للمطابقة فقط: الألف الخنجرية = ألف (يَٰ → يَا) أو تُحذف (لَٰكِنَّ → لَكِنَّ)، والمدّة تُهمَل"""
    out = []
    for L, mk in letters(word):
        if DAGGER_ALIF in mk and L not in ('ى', 'ا') and expand_dagger:
            out.append((L, mk - {DAGGER_ALIF})); out.append(('ا', frozenset()))
        else:
            out.append((L, mk - {DAGGER_ALIF, 'ٓ'}))
    return out

HOLLOW_GROUPS = {'10', '11'}                       # كَانَ، صَارَ، بَاتَ، كَادَ
HOLLOW_SUFFIXES = ['تُمْ', 'تُمَا', 'تُنَّ', 'تُ', 'تَ', 'تِ', 'نَا', 'نَ']   # ضمائر الرفع المتحركة

FUSED_GROUPS = {'4'}   # أدوات نداء تُوصَل رسماً بما بعدها: يَٰٓأَيُّهَا

def match_word(cat, word, wi):
    """→ قائمة تطابقات للكلمة wi؛ الخنجرية تُجرَّب ألفاً ثم محذوفة، ويُقدَّم ما وجد عاملاً حرّاً"""
    first = _match_word(cat, word, wi, match_letters(word, True))
    for f in first:
        f['expanded'] = True               # char_span على حروف الكلمة بعد مدّ الخنجرية ألفاً
    if DAGGER_ALIF not in word or any(not f['method'].startswith('proclitic') for f in first):
        return first
    second = _match_word(cat, word, wi, match_letters(word, False))
    for f in second:
        f['expanded'] = False
    if any(not f['method'].startswith('proclitic') for f in second):
        return second
    return first

def _match_word(cat, word, wi, toks):
    results = []

    def emit(op, span, method, checked, conf, host_rest=None, note=None):
        results.append(dict(word_index=wi, word=word, method=method, operator=op['form'],
                            group=op['group'], operator_class=op['cls'], char_span=span,
                            confidence=conf, vocal_checks=checked, host_rest=host_rest, note=note,
                            meanings=[dict(id=m['operator_id'], label=m['meaning_label'],
                                           prior=m['detection_probabilistic'].get('prior'),
                                           effect=m['grammatical_effect'])
                                      for m in op['meanings']]))

    def conf_of(checked, n_letters):
        if checked == 0:
            return 'low'          # بلا تشكيل: مطابقة رسمية فقط
        return 'high' if checked >= max(1, n_letters - 1) else 'medium'

    def lexical(off, t, tag=None):
        """2/3/3b: عامل حرّ (كلمة كاملة، أو + لاحقة، أو نداء موصول) → هل وُجد؟"""
        if tag is None:
            tag = '' if off == 0 else '+conj'
        hit = False
        g9_whole = False
        # 2. الكلمة كاملة
        for op, n, how in cat.by_plain(t, cat.single):
            if op['plain'] in ALIF_TO_YA and SHADDA in t[-1][1]:
                emit(op, (off, len(toks) - 1), 'operator+suffix' + tag, n, conf_of(n, len(t)),
                     host_rest='ي', note='ياء المتكلم مدغمة في ياء الحرف')
            else:
                emit(op, (off, len(toks)), 'whole_word' + tag, n, conf_of(n, len(t)),
                     note=None if how == 'strict' else 'مطابقة مرنة للهمزات')
                if op['group'] == '9':
                    g9_whole = True       # اسم فعل: لا نكتفِ بالمطابقة الكاملة، بل نجرّب «عامل + لاحقة» أيضاً
            hit = True
        if hit and not g9_whole:
            return True
        # 3. عامل + لاحقة  (ويُجرَّب أيضاً بعد مطابقة اسم فعل كاملة: عَلَيْكَ ← عَلَى + كَ)
        for op in cat.single:
            mode = SUFFIX_GROUPS.get(op['group'])
            if not mode:
                continue
            otoks = list(op['toks'])
            if op['plain'] in ALIF_TO_YA:
                otoks = otoks[:-1] + [('ي', frozenset({SUKUN}))]
            k = len(otoks)
            if len(t) <= k or plain(t[:k], True) != plain(otoks, True):
                continue
            rest = plain(t[k:])
            sufs = (PRON_SUFFIXES if mode in ('pron', 'both') else []) + \
                   (VERB_SUFFIXES if mode in ('verb', 'both') else [])
            if not any(_strip_marks(s) == rest for s in sufs):
                continue
            vsuf = any(_strip_marks(s) == rest for s in VERB_SUFFIXES) and mode in ('verb', 'both')
            if vsuf:
                otoks = otoks[:-1] + [(otoks[-1][0], frozenset())]   # كَانَ + ـُوا = كَانُوا: حركة الآخر للاحقة
            ok, n = vocal_compatible(t[:k], otoks)
            if ok:
                emit(op, (off, off + k), 'operator+suffix' + tag, n, conf_of(n, k), host_rest=rest)
                hit = True
        # 3c. الأجوف من كان وأخواتها مع ضمير الرفع المتحرك: تُحذف عينه (كَانَ ← كُنْتُمْ، صَارَ ← صِرْنَا)
        for op in cat.single:
            if op['group'] not in HOLLOW_GROUPS or len(op['toks']) != 3 or op['toks'][1][0] != 'ا':
                continue
            if len(t) <= 2 or plain(t[:2]) != op['toks'][0][0] + op['toks'][2][0] or SUKUN not in t[1][1]:
                continue
            rest = t[2:]
            if any(plain(rest) == _strip_marks(s) for s in HOLLOW_SUFFIXES):
                emit(op, (off, off + 2), 'operator+suffix' + tag, 0, 'medium', host_rest=plain(rest),
                     note='أجوف: حُذفت عينه مع ضمير الرفع المتحرك')
                hit = True
        # اجتماع تحليلي اسم الفعل: مطابقة كاملة + مطابقة مع لاحقة ⇒ ثقة كليهما medium
        if g9_whole and any(r['method'].startswith('operator+suffix') for r in results):
            for r in results:
                if r['method'].startswith(('whole_word', 'operator+suffix')):
                    r['confidence'] = 'medium'
        if hit:
            return True
        # 3a. إنّ وأخواتها + ما الكافة (إِنَّمَا، أَنَّمَا، كَأَنَّمَا، لَكِنَّمَا، لَيْتَمَا، لَعَلَّمَا)
        for op in cat.single:
            if op['group'] not in KAFFA_GROUPS:
                continue
            k = len(op['toks'])
            if len(t) != k + 2 or plain(t[:k], True) != plain(op['toks'], True) or plain(t[k:]) != 'ما':
                continue
            ok, n = vocal_compatible(t[:k], op['toks'])
            if not ok or vowel(t[k][1]) not in (FATHA, None):
                continue
            emit(op, (off, off + k), 'operator+kaffa' + tag, n, conf_of(n, k), host_rest='ما',
                 note='مكفوفة بـ«ما» الكافة: تدخل على الجملتين الاسمية والفعلية')
            effect = KAFFA_EFFECT.get(op['plain'], KAFFA_EFFECT[None])
            results[-1]['kaffa'] = 'مَا'
            for m in results[-1]['meanings']:
                m['effect'] = effect
            hit = True
        if hit:
            return True
        # 3b. أداة نداء موصولة رسماً (يَا + أَيُّهَا)
        for op in cat.single:
            if op['group'] not in FUSED_GROUPS:
                continue
            k = len(op['toks'])
            if len(t) > k + 1 and plain(t[:k], True) == plain(op['toks'], True) and t[k][0] in ('أ', 'ء'):
                ok, n = vocal_compatible(t[:k], op['toks'])
                if ok:
                    emit(op, (off, off + k), 'fused_prefix' + tag, n, conf_of(n, k), host_rest=plain(t[k:]))
                    hit = True
        return hit

    def proclitic(off, t, lexical_rest=False):
        """4. سابقة حرفية في الموضع off"""
        if len(t) < 2 or t[0][0] not in PROCLITICS:
            return False
        L, mk = t[0]
        v = vowel(mk) or (SUKUN if SUKUN in mk else None)
        if v is not None and v not in PROCLITICS[L]:
            return False
        rest = plain(t[1:], True)
        if L == 'ت' and not rest.startswith('الله'):
            return False                          # تاء القسم مع لفظ الجلالة فقط
        if L == 'و' and off == 1:
            return False
        if t[1][0] == 'ا' and len(t) > 2 and t[2][0] != 'ل' and SUKUN not in t[2][1] and vowel(t[2][1]):
            return False                          # كَاتِب: ألف مدّ بعد الحرف ⇒ الحرف من الأصل (لا تُمدّ حركة السابقة)
        strong = lexical_rest or rest.startswith('ال') or (L == 'ل' and v == SUKUN) or \
                 any(_strip_marks(s) == rest for s in PRON_SUFFIXES)
        hit = False
        for op in cat.clitic:
            if op['plain'] != L:
                continue
            # لام الأمر الساكنة لا تكون جارّة؛ لام مفتوحة = التوكيد فقط
            if L == 'ل' and v == SUKUN and op['group'] != '6':
                continue
            if L == 'ل' and lexical_rest and op['group'] == '6':
                continue                          # لام الأمر لا تدخل إلا على مضارع، لا على أداة (لِأَنَّ، لِمَا)
            if L == 'ل' and v == FATHA:
                op = dict(op, meanings=[m for m in op['meanings'] if 'التوكيد' in m['meaning_label']])
                if not op['meanings']:
                    continue
            conf = 'low' if v is None else ('high' if strong else 'medium')
            if L == 'و':
                note = 'قد تكون واو العطف (غير مفهرسة)'
            elif not strong and v is not None:
                note = 'قد يكون الحرف من أصل الكلمة'
            else:
                note = None
            emit(op, (off, off + 1), 'proclitic' + ('' if off == 0 else '+conj'),
                 1 if v else 0, conf, host_rest=plain(t[1:]), note=note)
            hit = True
        return hit

    if lexical(0, toks):
        return results
    conj = len(toks) > 2 and toks[0][0] in CONJ and vowel(toks[0][1]) in (FATHA, None)
    if conj and lexical(1, toks[1:]):
        proclitic(0, toks, lexical_rest=True)     # وَ نفسها مفهرسة (قسم/معية/رُبّ)
        return results
    # عامل حرّ بعد حرف جر متصل: بِأَنَّهُمْ، لِأَنَّ، كَأَنْ …
    inner = len(toks) > 2 and toks[0][0] in ('ب', 'ل', 'ك') and lexical(1, toks[1:], tag='+proclitic')
    divine = divine_name(word) is not None     # ما بعد السابقة لفظ الجلالة: السابقة حرف يقيناً (لا أمر ولا أصل)
    if not proclitic(0, toks, lexical_rest=inner or divine) and conj:
        proclitic(1, toks[1:], lexical_rest=divine)   # فَلْيَكْتُبْ، فَبِمَا، فَلِلَّهِ
    elif conj and toks[0][0] == 'و' and len(toks) > 3 and \
            ((toks[1][0] == 'ل' and SUKUN in toks[1][1]) or (toks[1][0] == 'ب' and KASRA in toks[1][1]) or
             (toks[1][0] == 'ت' and divine)):
        proclitic(1, toks[1:], lexical_rest=divine)   # وَلْيَكْتُبْ، وَبِٱلْآخِرَةِ، وَتَٱللَّهِ: الواو عاطفة محتملة
    return results

def match_multi(cat, words):
    res = []
    toks_list = [match_letters(w) for w in words]
    for op in cat.multi:
        parts = [letters(p) for p in op['form'].split()]
        n = len(parts)
        for i in range(len(words) - n + 1):
            ok_all, checked = True, 0
            for j, p in enumerate(parts):
                wt = toks_list[i + j]
                if plain(wt, True) != plain(p, True):
                    ok_all = False; break
                ok, c = vocal_compatible(wt, p)
                if not ok:
                    ok_all = False; break
                checked += c
            if ok_all:
                res.append(dict(word_index=i, word=' '.join(words[i:i + n]), method='multi_word',
                                operator=op['form'], group=op['group'], operator_class=op['cls'],
                                char_span=None, words_span=(i, i + n), confidence='high' if checked else 'low',
                                vocal_checks=checked, host_rest=None, note=None,
                                meanings=[dict(id=m['operator_id'], label=m['meaning_label'],
                                               prior=m['detection_probabilistic'].get('prior'),
                                               effect=m['grammatical_effect']) for m in op['meanings']]))
    return res

def extract(cat, text):
    words = text.split()
    found = match_multi(cat, words)
    covered = set()
    for f in found:
        covered.update(range(*f['words_span']))
    for wi, w in enumerate(words):
        if wi in covered:
            continue
        found += match_word(cat, w, wi)
    found.sort(key=lambda f: (f['word_index'], f['char_span'][0] if f['char_span'] else -1))
    return words, found
