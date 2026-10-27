# -*- coding: utf-8 -*-
"""
sarf.evidence — نفي المرشَّح بالكتابة (القرار 7 في المخطط: العامل يُتحقَّق منه بالكتابة).
يضيف لكل مرشَّح status/reject_reason، والمرفوض يبقى في القائمة ومعه سببه.
"""
from .chars import FATHA, DAMMA, KASRA, SUKUN, FATHATAN, DAMMATAN, KASRATAN, plain, strip_marks as _strip_marks
from .match import PRON_SUFFIXES, match_letters

RAF_PREFIX = set('يتأن')   # حروف المضارعة لثبوت نون الرفع

def _last_haraka(toks):
    """الحركة الأخيرة لمعمولٍ فعليّ، بعد نزع ضميرٍ متصل (الأطول أولاً، وبقاء حرفين)، أو None."""
    toks = list(toks)
    for suf in sorted(PRON_SUFFIXES, key=lambda s: len(_strip_marks(s)), reverse=True):
        sl = len(_strip_marks(suf))
        if len(toks) - sl >= 2 and plain(toks[-sl:]) == _strip_marks(suf):
            toks = toks[:-sl]
            break
    if not toks:
        return None
    mk = toks[-1][1]
    for h in (FATHATAN, DAMMATAN, KASRATAN, FATHA, DAMMA, KASRA, SUKUN):
        if h in mk:
            return h
    return None

def _noon_raf(toks):
    """ثبوت نون الرفع: تبدأ بحرف مضارعة، وتنتهي بـ ونَ/ينَ (نون مفتوحة) أو انِ (نون مكسورة)."""
    if len(toks) < 3 or toks[0][0] not in RAF_PREFIX:
        return False
    (l2, _), (l1, m1) = toks[-2], toks[-1]
    if l1 != 'ن':
        return False
    return (l2 in ('و', 'ي') and FATHA in m1) or (l2 == 'ا' and KASRA in m1)

def _target_after(f, words):
    """رموز المعمول: بقيّة الكلمة بعد السابقة (proclitic)، أو الكلمة التالية."""
    if f['method'].startswith('proclitic'):
        return match_letters(f['word'], True)[f['char_span'][1]:]
    nxt = f['word_index'] + 1
    return match_letters(words[nxt], True) if nxt < len(words) else None

def reject_candidates(found, words):
    """يضيف status/reject_reason لكل مرشَّح؛ والمرفوض يبقى في القائمة ومعه سببه (مبدأ المخطط)."""
    CASE = {FATHA: 'منصوب', DAMMA: 'مرفوع'}
    for f in found:
        f['status'], f['reject_reason'] = 'candidate', None
    for f in found:
        op = _strip_marks(f['operator'])
        tgt = _target_after(f, words)
        if not tgt:
            continue
        h = _last_haraka(tgt)
        # R1/R2: لام الأمر ولا الناهية (المجموعة 6) — تُرفض إن كان الفعل بعدها غير مجزوم كتابةً
        if f['group'] == '6' and op in ('ل', 'لا'):
            reason = CASE.get(h) or ('ثبوت النون' if _noon_raf(tgt) else None)
            if reason:
                f['status'] = 'rejected'
                f['reject_reason'] = f'الفعل بعدها غير مجزوم كتابةً ({reason})'
        # R3: اسم الفعل الناصب للمفعول (المجموعة 9) — تُرفض إن كان ما بعده مرفوعاً كتابةً
        elif f['group'] == '9' and op in ('رويد', 'بله', 'دونك', 'عليك'):
            if h in (DAMMA, DAMMATAN):
                f['status'] = 'rejected'
                f['reject_reason'] = 'ما بعده مرفوع كتابةً، واسم الفعل ينصب مفعوله'
    return found
