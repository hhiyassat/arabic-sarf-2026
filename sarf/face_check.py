# -*- coding: utf-8 -*-
"""sarf/face_check.py — كواشف سلامة الوجه (AR02، مقوّاة في AR03 §٥). كل كاشفٍ يفحص خاصيةً واحدة ويُسمّى باسمه.

    check_face_record(word, m) → [(الكاشف، الوصف)]   فارغةٌ إن سلم السجل

الترتيب: المخطط أولاً (وجود الحقول وأنواعها بحسب الحالة)، ثم إعادة الاشتقاق من الجذر وقالب HFN والحدث، ثم المقارنة بالمسجَّل.
وما نقص من دليلٍ مطلوب فشلٌ مسمّى، لا تخطٍّ صامت (كان الفاحص في AR02 يتخطّى التحقيق إذا غاب realization أو فرغ hfn_forms).

الكواشف:
  SCHEMA          الحقول المطلوبة بحسب حالة السجل وحالة الوجه موجودةٌ بأنواعها (realization وpatterns وhfn_forms وevidence_ids …)
  EVIDENCE_MISSING  وجهٌ مرخّص أو مختار بلا شاهد، أو بلا قالب HFN
  IDENTITY        هوية الوجه تُعاد من محتواه (الامتداد، الجذر، الوزن، النوع، اللمّة، القالب)
  EVIDENCE_LINK   كل شاهدٍ حدثٌ في HFN بجذر الوجه وبابه ولمّته وقالبه — لا يكفي اتفاق الجذر والباب؛ و ROOT:<جذر> رخصة جذرٍ في HFN
  REALIZATION     التحقيق العكسي يُعاد كاملاً: الصيغة المعادة، والعمليات، والحالة، وmatched متسقٌ مع الحالة
  INFLECTION      حكم الكلمة الداخلة يُعاد بالقاعدة نفسها
  PATTERN         أهداف الوزن تُعاد من الباب والقالب واللمّة؛ ووزن الوقوع هو وزن الوجه المختار، ولا وزن بلا وجهٍ مختار
  SELECTION       وجهٌ مختار واحد على الأكثر، يطابق جذر السجل ووزنه، وحالته «مقبول»، ولا تحقيقَ مغطّى يعارضه (MISMATCH)
  STATUS          الحالات الأربع المستقلة تُعاد من الأوجه (selection_statuses)
  PROTECTION      المحمي بلا جذرٍ ولا وزنٍ ولا أوجه؛ وclass_deferred بلا جذرٍ ولا وزنٍ ولا وجهٍ مختار
  CLASS           الوجه الفعلي وزنه من أبواب الفعل المعلنة
  SEGMENTATION    في سجلّ الآية: جزء القطع وأجزاء المنافسين من الكلمة نفسها، والجذع جزءٌ من الكلمة
"""
from .root import (analysis_key, analysis_id, hfn, WAZN, face_realization, pattern_targets, selection_statuses, _plain_vowels)

VERB_CLASSES = set(WAZN) | {'I'}
FACE_STATUSES = {'GENERATED', 'LICENSED', 'SELECTED', 'SELECTED_ROOT_LICENCE', 'RANKED', 'REJECTED_WITH_BARRIER'}
RECORD_STATUSES = {'accepted', 'ranked', 'deferred', 'rejected', 'class_deferred', 'not_applicable', 'unknown'}
_EVENTS = {}


def _events():
    """event_id → (الحدث، الباب الذي فُهرس فيه)"""
    if not _EVENTS:
        H = hfn()
        for (r, c), evs in H.index.items():
            for e in evs:
                _EVENTS[e['event_id']] = (e, c)
    return _EVENTS


def _types(obj, spec, where, out):
    """spec: {field: (types, required)}"""
    ok = True
    for k, (tp, req) in spec.items():
        if k not in obj:
            if req:
                out.append(('SCHEMA', f'{where}: الحقل «{k}» مفقود'))
                ok = False
        elif not isinstance(obj[k], tp):
            out.append(('SCHEMA', f'{where}: الحقل «{k}» نوعه {type(obj[k]).__name__}'))
            ok = False
    return ok


FACE_SPEC = dict(analysis_id=(str, True), root=(str, True), form_class=(str, True), kind=(str, True), status=(str, True),
                 lemma=((str, type(None)), True), hfn_forms=(list, True), evidence_ids=(list, True))
LEX_FACE_SPEC = dict(realization=(dict, True), patterns=(dict, True))
REAL_SPEC = dict(reconstructed_form=((str, type(None)), True), operations=(list, True), matched=(bool, True), status=(str, True))


def _check_face(word, f, out):
    where = f"الوجه {f.get('analysis_id')}"
    if not _types(f, FACE_SPEC, where, out):
        return
    if f['status'] not in FACE_STATUSES:
        out.append(('SCHEMA', f"{where}: حالةٌ غير معرّفة {f['status']}"))
    form = f['hfn_forms'][0] if f['hfn_forms'] else None
    if len(f['hfn_forms']) > 1:
        out.append(('SCHEMA', f'{where}: أكثر من قالبٍ في وجهٍ واحد (الوجه تحليلٌ واحد)'))
    if f['analysis_id'] != analysis_id(analysis_key(word, f['root'], f['form_class'], f['kind'], f['lemma'], form)):
        out.append(('IDENTITY', f"{where}: الهوية لا تُعاد من محتواه"))
    if f['kind'] == 'فعل' and f['form_class'] not in VERB_CLASSES:
        out.append(('CLASS', f"{where}: وجهٌ فعلي بوزنٍ غير فعلي: {f['form_class']}"))
    lexical = f['status'] not in ('GENERATED', 'SELECTED_ROOT_LICENCE')
    if f['status'] == 'SELECTED_ROOT_LICENCE':
        H = hfn()
        if f['evidence_ids'] != [f"ROOT:{f['root']}"] or f['root'] not in H.roots:
            out.append(('EVIDENCE_LINK', f'{where}: رخصة الجذر ليست ROOT:{f["root"]} من جذور HFN'))
        if f['lemma'] or f['hfn_forms']:
            out.append(('SCHEMA', f'{where}: رخصة جذرٍ بلا حدث تحمل لمّةً أو قالباً'))
        return
    if f['status'] == 'GENERATED':
        if f['evidence_ids'] or f['lemma'] or f.get('realization'):
            out.append(('SCHEMA', f'{where}: وجهٌ مولَّد بلا رخصة يحمل شاهداً أو لمّةً أو تحقيقاً'))
        return
    # وجهٌ معجمي (مرخّص أو مختار أو مرجّح أو مرفوض بمانع): الشاهد والقالب واللمّة والتحقيق والأوزان مطلوبة
    if not f['evidence_ids']:
        out.append(('EVIDENCE_MISSING', f'{where}: وجهٌ {f["status"]} بلا شاهد'))
    if not form:
        out.append(('EVIDENCE_MISSING', f'{where}: وجهٌ {f["status"]} بلا قالب HFN'))
    if not f['lemma']:
        out.append(('EVIDENCE_MISSING', f'{where}: وجهٌ {f["status"]} بلا لمّة'))
    if not _types(f, LEX_FACE_SPEC, where, out):
        return
    EV = _events()
    for e in f['evidence_ids']:
        ev, cls = EV.get(e, (None, None))
        if ev is None:
            out.append(('EVIDENCE_LINK', f'{where}: الشاهد {e} ليس حدثاً في HFN'))
        elif (ev['root_K'], cls) != (f['root'], f['form_class']) or _plain_vowels(ev['verb']) != _plain_vowels(f['lemma'] or '') \
                or (form and ev['form'] != form):
            out.append(('EVIDENCE_LINK', f"{where}: الشاهد {e} للّمّة «{ev['verb']}» بقالب «{ev['form']}»، لا للوجه «{f['lemma']}» «{form}»"))
    if not form or not f['lemma']:
        return
    rz = f['realization']
    if not isinstance(rz.get('lemma'), dict) or not isinstance(rz.get('word'), dict):
        out.append(('SCHEMA', f'{where}: التحقيق بلا lemma أو word'))
        return
    if not _types(rz['lemma'], REAL_SPEC, where + ' realization.lemma', out):
        return
    again = face_realization(word, f['root'], f['form_class'], form, f['lemma'])
    la, lr = again['lemma'], rz['lemma']
    if lr['matched'] != (lr['status'] == 'MATCHED'):
        out.append(('REALIZATION', f"{where}: matched={lr['matched']} يناقض الحالة {lr['status']}"))
    for k in ('reconstructed_form', 'status', 'matched', 'operations'):
        if la.get(k) != lr.get(k):
            out.append(('REALIZATION', f"{where}: {k} المسجّل «{lr.get(k)}» والمعاد «{la.get(k)}»"))
    if again['word'].get('status') != rz['word'].get('status'):
        out.append(('INFLECTION', f"{where}: حكم الكلمة الداخلة {rz['word'].get('status')} والمعاد {again['word']['status']}"))
    pt = pattern_targets(word, f['form_class'], form, f['lemma'], f['evidence_ids'])
    for k, v in pt.items():
        r = (f['patterns'] or {}).get(k)
        if not isinstance(r, dict):
            out.append(('SCHEMA', f'{where}: هدف الوزن «{k}» مفقود'))
        elif r.get('value_or_alternatives') != v['value_or_alternatives'] or r.get('status') != v['status']:
            out.append(('PATTERN', f"{where}: {k} المسجّل {r.get('value_or_alternatives')} ({r.get('status')}) والمعاد "
                                   f"{v['value_or_alternatives']} ({v['status']})"))
    if f['status'] == 'SELECTED' and la['status'] == 'MISMATCH':
        out.append(('SELECTION', f'{where}: مختارٌ وتحقيقه المغطّى MISMATCH'))


def check_face_record(word, m):
    out = []
    if m is None:
        return out
    if not _types(m, dict(status=(str, True), faces=(list, False)), 'السجل', out):
        return out
    st = m['status']
    if st not in RECORD_STATUSES:
        out.append(('SCHEMA', f'حالة السجل غير معرّفة: {st}'))
    if st == 'not_applicable':
        if m.get('root') or m.get('form_class') or m.get('faces') or m.get('licensed') or m.get('pattern'):
            out.append(('PROTECTION', 'وجهٌ محمي يحمل جذراً أو وزناً أو أوجهاً'))
        if m.get('root_status') != 'NOT_APPLICABLE':
            out.append(('PROTECTION', f"المحمي root_status={m.get('root_status')}"))
        return out
    faces = m.get('faces') or []
    if st == 'class_deferred':
        if m.get('root') or m.get('form_class') or m.get('pattern'):
            out.append(('PROTECTION', 'class_deferred يحمل جذراً أو وزناً مقبولاً'))
        if any(f.get('status') in ('SELECTED', 'SELECTED_ROOT_LICENCE') for f in faces):
            out.append(('PROTECTION', 'class_deferred وفيه وجهٌ مختار'))
    if 'statuses' not in m:
        out.append(('SCHEMA', 'السجل بلا الحالات الأربع (statuses)'))
    elif m['statuses'] != selection_statuses(m):
        out.append(('STATUS', f"الحالات المسجّلة {m['statuses']} والمعادة {selection_statuses(m)}"))
    for f in faces:
        if isinstance(f, dict):
            _check_face(word, f, out)
        else:
            out.append(('SCHEMA', 'وجهٌ ليس سجلاً'))
    sel = [f for f in faces if isinstance(f, dict) and f.get('status') in ('SELECTED', 'SELECTED_ROOT_LICENCE')]
    if len(sel) > 1:
        out.append(('SELECTION', f'أكثر من وجهٍ مختار: {len(sel)}'))
    if sel and st != 'accepted':
        out.append(('SELECTION', f'وجهٌ مختار والحالة {st}'))
    if any((f.get('root'), f.get('form_class')) != (m.get('root'), m.get('form_class')) for f in sel):
        out.append(('SELECTION', 'الوجه المختار لا يطابق جذر السجل ووزنه'))
    if st == 'accepted' and not any(f.get('root') == m.get('root') and f.get('form_class') == m.get('form_class') for f in faces):
        out.append(('SELECTION', 'مقبولٌ بلا وجهٍ يطابق جذره ووزنه'))
    full = [f for f in sel if f.get('status') == 'SELECTED']
    pat = m.get('pattern')
    if pat and not full:
        out.append(('PATTERN', 'وزنٌ على الوقوع بلا وجهٍ مختار'))
    elif pat and full:
        lp = (full[0].get('patterns') or {}).get('lemma_pattern', {}).get('value_or_alternatives') or []
        got = ([pat.get('lemma_pattern')] if pat.get('lemma_pattern') else pat.get('lemma_pattern_alternatives')) if isinstance(pat, dict) else None
        if got != lp or \
                pat.get('realized_pattern') != (full[0].get('hfn_forms') or [None])[0]:
            out.append(('PATTERN', f"وزن الوقوع {pat.get('lemma_pattern') if isinstance(pat, dict) else pat} لا يطابق وزن الوجه المختار {lp}"))
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
    if entry.get('status') == 'accepted' and entry.get('whole_word_rivals'):
        out.append(('SELECTION', 'مقبولٌ مع منافسٍ حيّ'))
    st = entry.get('statuses') or {}
    if entry.get('status') == 'accepted' and st.get('analysis_selection_status') == 'SELECTED' and not entry.get('analysis_id'):
        out.append(('IDENTITY', 'مختارٌ بلا هوية تحليل'))
    if entry.get('analysis_id') and st.get('analysis_selection_status') != 'SELECTED':
        out.append(('SELECTION', 'هوية تحليلٍ مختار مع اختيارٍ غير مثبت'))
    if entry.get('pattern') and st.get('analysis_selection_status') != 'SELECTED':
        out.append(('PATTERN', 'وزنٌ على الوقوع واختيار التحليل غير مثبت'))
    return out
