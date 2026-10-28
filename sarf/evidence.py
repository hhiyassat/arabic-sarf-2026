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
"""
from .chars import FATHA, DAMMA, DAMMATAN, plain, strip_marks as _strip_marks
from .match import match_letters
from .affix import stem_info, RAF_PRONOUNS
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

def reject_candidates(found, words):
    for f in found:
        f['status'], f['reject_reason'], f['checked'] = DEFERRED, None, []
    for f in found:
        op = _strip_marks(f['operator'])
        tgt = _target_after(f, words)
        if not tgt:
            continue
        info = stem_info(tgt)
        reason = None
        # R1/R2: لام الأمر ولا الناهية — ما بعدها مضارع مجزوم
        if f['group'] == '6' and op in ('ل', 'لا'):
            f['checked'].append('R1/R2 المجزوم بعدها')
            if info['pos'] == 'noun':
                reason = f"ما بعدها اسم ({'، '.join(info['evidence'])})"
            elif info['kind'] != 'mudari':
                reason = 'ما بعدها ليس فعلاً مضارعاً'
            elif info['mood'] in CASE:
                why = 'ثبوت النون' if info['suffix'] == 'نون الرفع' else CASE[info['mood']]
                reason = f'الفعل بعدها غير مجزوم كتابةً ({why})'
        # R3: اسم الفعل الناصب للمفعول — ما بعده مرفوع
        elif f['group'] == '9' and op in ('رويد', 'بله', 'دونك', 'عليك'):
            f['checked'].append('R3 المنصوب بعده')
            last = match_letters(tgt)[-1][1]
            if last & {DAMMA, DAMMATAN}:
                reason = 'ما بعده مرفوع كتابةً، واسم الفعل ينصب مفعوله'
        # R4: واو القسم الجارّة وواو المعية — لا تدخلان على فعل ولا حرف ولا ضمير رفع
        elif op == 'و' and f['group'] in ('1', '4') and f['method'].startswith('proclitic'):
            f['checked'].append('R4 الاسم بعد الواو')
            after = [g for g in found if g is not f and g['word_index'] == f['word_index'] and
                     g['char_span'] and g['char_span'][0] == f['char_span'][1]]
            if plain(match_letters(tgt), True).replace('أ', 'ا') in {p.replace('أ', 'ا') for p in RAF_PRONOUNS}:
                reason = 'بعدها ضمير رفع منفصل: الواو عاطفة أو حالية'
            elif info['pos'] == 'verb':
                reason = f"بعدها فعل ({'، '.join(info['evidence'])}): الواو عاطفة"
            elif after:
                reason = f"بعدها عامل ({after[0]['operator']}): الواو عاطفة"
        # R5: اللام المفتوحة قبل الفعل لام توكيد أو جواب قسم، لا جارّة
        elif op == 'ل' and f['group'] == '1' and f['method'].startswith('proclitic'):
            f['checked'].append('R5 اللام المفتوحة قبل الفعل')
            if FATHA in match_letters(f['word'])[f['char_span'][0]][1] and info['pos'] == 'verb':
                reason = f"اللام المفتوحة قبل الفعل ({'، '.join(info['evidence'])}) لام توكيد أو جواب قسم، لا جارّة"
        if reason:
            f['status'], f['reject_reason'] = BLOCKED, reason
    return found
