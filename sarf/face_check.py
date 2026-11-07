# -*- coding: utf-8 -*-
"""sarf/face_check.py — كواشف سلامة الوجه (AR02): كل كاشفٍ يفحص خاصيةً واحدة ويُسمّى باسمه، فيُعرف أيّها كشف الإفساد.

    check_face_record(word, m) → [(الكاشف، الوصف)]   فارغةٌ إن سلم السجل

الكواشف:
  IDENTITY        هوية الوجه تساوي هويةً تُعاد من محتواه (لا من ترتيبه)
  EVIDENCE_LINK   كل شاهدٍ للوجه حدثٌ في HFN بجذره ووزنه
  SELECTION       وجهٌ مختار واحد على الأكثر، وهو ما قبله morph بجذره ووزنه؛ ولا مختار مع حالةٍ غير «مقبول»
  PROTECTION      الوجه المحمي (not_applicable) بلا جذرٍ ولا وزنٍ ولا أوجه؛ وclass_deferred بلا جذر
  CLASS           الوجه الفعلي وزنه من أبواب الفعل المعلنة
  REALIZATION     التحقيق العكسي يُعاد: اللمّة من الجذر وصيغة HFN بعملياتها تطابق لمّة الحدث، والعمليات المسجّلة هي المعادة
  INFLECTION      حكم الكلمة الداخلة (MATCHED/MATCHED_STEM/NOT_COVERED) يُعاد بالقاعدة نفسها
  SEGMENTATION    في سجلّ الآية: جزء القطع وأجزاء المنافسين حروفٌ من الكلمة نفسها، والجذع جزءٌ من الكلمة
"""
from .root import analysis_key, analysis_id, hfn, WAZN, face_realization, _plain_vowels

VERB_CLASSES = set(WAZN) | {'I'}


def check_face_record(word, m):
    out = []
    if m is None:
        return out
    st = m.get('status')
    if st == 'not_applicable':
        if m.get('root') or m.get('form_class') or m.get('faces') or m.get('licensed'):
            out.append(('PROTECTION', 'وجهٌ محمي يحمل جذراً أو وزناً أو أوجهاً'))
        return out
    if st == 'class_deferred' and m.get('root'):
        out.append(('PROTECTION', 'class_deferred يحمل جذراً مقبولاً'))
    H = hfn()
    faces = m.get('faces') or []
    for f in faces:
        key = analysis_key(word, f['root'], f['form_class'], f.get('kind'), f.get('lemma'))
        if f.get('analysis_id') != analysis_id(key):
            out.append(('IDENTITY', f"هوية الوجه {f.get('analysis_id')} لا تُعاد من محتواه"))
        if f.get('kind') == 'فعل' and f['form_class'] not in VERB_CLASSES:
            out.append(('CLASS', f"وجهٌ فعلي بوزنٍ غير فعلي: {f['form_class']}"))
        if f.get('realization') and f.get('lemma') and len(f.get('hfn_forms') or []) == 1:
            again = face_realization(word, f['root'], f['form_class'], f['hfn_forms'][0], f['lemma'])
            st_ = f['realization'].get('lemma', {}).get('status')
            if again['lemma']['status'] not in ('MATCHED', 'MISMATCH_HAMZA_SEAT_ONLY') and st_ in ('MATCHED', 'MISMATCH_HAMZA_SEAT_ONLY'):
                out.append(('REALIZATION', f"اللمّة لا تُعاد من الجذر والصيغة: {again['lemma'].get('reconstructed_form')} ≠ {f['lemma']}"))
            elif again['lemma'].get('operations') != f['realization'].get('lemma', {}).get('operations'):
                out.append(('REALIZATION', 'العمليات المسجّلة غير المعادة'))
            if again['word']['status'] != f['realization'].get('word', {}).get('status'):
                out.append(('INFLECTION', f"حكم الكلمة الداخلة {f['realization'].get('word', {}).get('status')} والمعاد {again['word']['status']}"))
        ev_ok = {e['event_id'] for e in H.index.get((f['root'], f['form_class']), [])}
        bad = [e for e in f.get('evidence_ids') or [] if e not in ev_ok]
        if bad:
            out.append(('EVIDENCE_LINK', f'شاهدٌ لا يخصّ الوجه ({f["root"]} {f["form_class"]}): {bad}'))
    sel = [f for f in faces if f.get('status') == 'SELECTED']
    if len(sel) > 1:
        out.append(('SELECTION', f'أكثر من وجهٍ مختار: {len(sel)}'))
    if sel and st != 'accepted':
        out.append(('SELECTION', f'وجهٌ مختار والحالة {st}'))
    if st == 'accepted' and not any(f['root'] == m.get('root') and f['form_class'] == m.get('form_class') and
                                    f.get('status') == 'SELECTED' for f in faces):
        out.append(('SELECTION', 'مقبولٌ بلا وجهٍ مختار يطابق جذره ووزنه'))
    return out


def check_verse_entry(word, entry, slot_text):
    """سجلّ verse_morph لوقوعٍ: أجزاء القطع والمنافسين من الكلمة نفسها (SEGMENTATION)، والمختار له هوية (IDENTITY)"""
    out = []
    w = _plain_vowels(word)
    if slot_text and _plain_vowels(slot_text) not in w:
        out.append(('SEGMENTATION', f'الجذع «{slot_text}» ليس جزءاً من الكلمة'))
    pf = entry.get('peeled_face')
    if pf and (_plain_vowels(pf['span']) not in w or slot_text and _plain_vowels(pf['span']) != _plain_vowels(slot_text)):
        out.append(('SEGMENTATION', f"جزء القطع «{pf['span']}» ليس جذع الخانة «{slot_text}»"))
    for r in entry.get('whole_word_rivals') or []:
        if _plain_vowels(r.get('span') or '') not in w:
            out.append(('SEGMENTATION', f"جزء المنافس «{r.get('span')}» ليس من الكلمة"))
    if entry.get('status') == 'accepted' and not entry.get('analysis_id'):
        out.append(('IDENTITY', 'مقبولٌ بلا هوية تحليل'))
    if entry.get('status') == 'accepted' and entry.get('whole_word_rivals'):
        out.append(('SELECTION', 'مقبولٌ مع منافسٍ حيّ'))
    return out
