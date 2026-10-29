# -*- coding: utf-8 -*-
"""
sarf.output_schema — السجل الجامع: ناتج التحليل بصيغة schema/morph_analysis.schema.json (1.1).

المبدأ: لا يُكتب حقل لا دليل عليه من الكتابة أو الملف أو الفهرس. فما لم يُحسم نوعه بالكتابة
يُكتب pos = undetermined (1.1) بلا كائن، ولا تُخترع سماتٌ اختيارية (الجذر، الوزن، الباب…).

  الحالة (T09) → status:   مقبول ← selected، مؤجَّل ← candidate، ممنوع ← rejected
  score: درجة الحكم لا احتمال: 0.9 للمرجَّح، و0.5 للمؤجَّل، و0 للممنوع
  التحليل الأول: الخانات كما فصلها المقشِّر، ولكل خانة عامل مرشَّحُها المقبول وإلا أول المؤجَّلين؛
  وبعده تحليلٌ لكل مرشَّح آخر على خانته، ثم الممنوع ومعه سببه في evidence.
"""
from .affix import stem_info
from .chars import (FATHA, DAMMA, KASRA, SUKUN, FATHATAN, DAMMATAN, KASRATAN, letters, strip_marks)
from .match import vform_match
from .lexicon import MabniLexicon
from .normalize import UTHMANI_SIGNS
from .root import soundness, WAZN
from .segment import AMIL, MABNI, ARTICLE, DIVINE
from .status import ACCEPTED, DEFERRED, BLOCKED

SCHEMA_VERSION = '1.1'
STATUS = {ACCEPTED: 'selected', DEFERRED: 'candidate', BLOCKED: 'rejected'}
SCORE = {'selected': 0.9, 'candidate': 0.5, 'rejected': 0.0}
CASE = {'رفع': 'nom', 'نصب': 'acc', 'جر': 'gen'}
MOOD = {'رفع': 'indicative', 'نصب': 'subjunctive', 'جزم': 'jussive'}
MARK_NAME = {DAMMA: 'damma', FATHA: 'fatha', KASRA: 'kasra', SUKUN: 'sukun',
             DAMMATAN: 'dammatan', FATHATAN: 'fathatan', KASRATAN: 'kasratan'}
MARK_CASE = {DAMMA: 'nom', DAMMATAN: 'nom', FATHA: 'acc', FATHATAN: 'acc', KASRA: 'gen', KASRATAN: 'gen'}
MARK_MOOD = {DAMMA: 'indicative', FATHA: 'subjunctive', SUKUN: 'jussive'}
# أثر العامل بمجموعته في الفهرس (particle.effect)
EFFECT = {'1': 'jarr', '2': 'nasb_ism_raf_khabar', '4': 'nasb', '5': 'nasb_verb', '6': 'jazm_one'}
# أفعالٌ في الفهرس (كان وأخواتها، وأفعال المقاربة، والمدح والذم، وأفعال القلوب)
VERB_GROUPS = {'10', '11', '12', '13'}
JAMID = ('لَيْسَ', 'عَسَى', 'نِعْمَ', 'بِئْسَ', 'حَبَّذَا')
# ضمير الفاعل في الماضي بلاحقته: (الشخص، العدد، الجنس)
PAST_SUBJECT = {'وا': (3, 'plural', 'masc'), 'و': (3, 'plural', 'masc'), 'تْ': (3, 'singular', 'fem'),
                'تُمْ': (2, 'plural', 'masc'), 'تُمَا': (2, 'dual', 'common'), 'تُنَّ': (2, 'plural', 'fem'),
                'تُ': (1, 'singular', 'common'), 'تَ': (2, 'singular', 'masc'), 'تِ': (2, 'singular', 'fem'),
                'نَا': (1, 'plural', 'common'), None: (3, 'singular', 'masc')}

_LEX = None


def _lex():
    global _LEX
    if _LEX is None:
        _LEX = MabniLexicon()
    return _LEX


def _pron(person, number, gender, function=None):
    p = dict(person=person, number=number)
    if gender:
        p['gender'] = gender
    if function:
        p['function'] = function
    return p


def _last_mark(text):
    toks = letters(text)
    return set(toks[-1][1]) if toks else set()


def _observed(text):
    """العلامة المكتوبة على آخر الحرف كما هي"""
    return ''.join(sorted(_last_mark(text))) or None


# ---------- الفعل ----------
def _past_suffix(text, suffix):
    """لاحقة الماضي بحركتها الفعلية (المقشِّر يسمّي تُ/تَ/تِ كلها «تُ»)"""
    if suffix in ('تُ', 'تَ', 'تِ'):
        m = _last_mark(text)
        return 'تَ' if FATHA in m else 'تِ' if KASRA in m else 'تُ'
    return suffix


def _verbs(text, info, agr=None):
    """→ [كائن verb] لكل إسنادٍ تحتمله الكتابة. السمات من طبقة التوافق (T18) إن حُسبت:
    A(m) = {Φ(p) | R(m,p)}؛ وإلا من اللاحقة كما هي"""
    toks = letters(text)
    voice = 'passive' if toks and DAMMA in toks[0][1] and info['kind'] == 'madi' else 'active'
    if info['kind'] == 'madi':
        p, n, g = PAST_SUBJECT.get(_past_suffix(text, info['suffix']), PAST_SUBJECT[None])
        subj = [_pron(p, n, g, 'subject')]
        infl = dict(status='mabni')
        tense = 'past'
    elif info['kind'] == 'amr':
        n, g = {'وا': ('plural', 'masc'), 'و': ('plural', 'masc'), 'ي': ('singular', 'fem')}.get(
            info['suffix'], ('singular', 'masc'))
        subj = [_pron(2, n, g, 'subject')]
        infl = dict(status='mabni')
        if info['suffix'] in ('وا', 'و', 'ي'):
            infl['build_mark'] = 'deletion'
        elif _last_mark(text) == {SUKUN}:
            infl['build_mark'] = 'sukun'
        tense = 'imperative'
    else:
        pre, suf = info['prefix'], info['suffix']
        plural = suf in ('وا', 'و', 'نون الرفع')
        if pre == 'أ':
            subj = [_pron(1, 'singular', 'common', 'subject')]
        elif pre == 'ن':
            subj = [_pron(1, 'plural', 'common', 'subject')]
        elif pre == 'ي':
            subj = [_pron(3, 'plural' if plural else 'singular', 'masc', 'subject')]
        elif suf == 'ي':
            subj = [_pron(2, 'singular', 'fem', 'subject')]
        elif plural:
            subj = [_pron(2, 'plural', 'masc', 'subject')]
        else:                                  # تَكْتُبُ: أنتَ أو هي، لا تفصل الكتابة بينهما
            subj = [_pron(2, 'singular', 'masc', 'subject'), _pron(3, 'singular', 'fem', 'subject')]
        if info['mood'] == 'مبني':
            infl = dict(status='mabni')
        else:
            infl = dict(status='murab')
            if info['mood'] in MOOD:
                infl['mood'] = MOOD[info['mood']]
            if info['mood'] == 'حذف النون':
                infl['marker'] = 'nun_deleted'
            elif info['suffix'] == 'نون الرفع':
                infl.update(mood='indicative', marker='nun_retained')
            else:
                m = _last_mark(text) & set(MARK_NAME)
                if m:
                    infl['marker'] = MARK_NAME[next(iter(m))]
            obs = _observed(text)
            if obs:
                infl['observed_mark'] = obs
        tense = 'imperfect'
    if agr and agr.get('features'):
        subj = [_pron(p, n, g, 'subject') for p, n, g in agr['features']]
    voices = [voice]
    if agr and 'voice' in agr:
        voices = [agr['voice']] if agr['voice'] else ['active', 'passive']   # لا تفصل الكتابة: الاحتمالان
    return [dict(tense=tense, voice=vc, subject=s, inflection=dict(infl)) for vc in voices for s in subj]


# ---------- الاسم ----------
def _letter_marker(toks):
    """علامة الإعراب بالحرف: جمع المذكر السالم والمثنى (والنون بعدهما ليست علامة)
    → (marker، الحالة إن عيّنها الحرف وحده، أو None للياء: جر أو نصب)"""
    if len(toks) < 3 or toks[-1][0] != 'ن':
        return None
    L, m = toks[-2]
    pm = toks[-3][1]
    if L == 'و' and not m and DAMMA in pm and FATHA in toks[-1][1]:
        return 'waw', 'nom'                    # ـُونَ
    if L == 'ي' and (not m or m == {SUKUN}) and (KASRA in pm or FATHA in pm):
        return 'ya', None                      # ـِينَ، ـَيْنِ
    if L == 'ا' and not m and KASRA in toks[-1][1]:
        return 'alif', 'nom'                   # ـَانِ
    return None


def _noun(text, info, definite_by=None, case=None):
    infl = dict(status='murab')
    toks = letters(text)
    m = _last_mark(text)
    lm = _letter_marker(toks)
    if lm:
        marker, c = lm
        infl.update(marker=marker, marker_kind='substitute')
        if c or case:
            infl['case'] = c or case
    else:
        for mk, cs in MARK_CASE.items():
            if mk in m:
                infl.update(case=cs, marker=MARK_NAME[mk], marker_kind='original')
                break
        if not m and toks and toks[-1][0] in ('ا', 'ى') and len(toks) > 1 and FATHATAN in toks[-2][1]:
            infl.update(case='acc', marker='fathatan', marker_kind='original')   # خَيۡرًا
    obs = _observed(text)
    if obs:
        infl['observed_mark'] = obs
    n = dict(subtype='common', inflection=infl)
    if definite_by:
        n.update(definiteness='definite', definite_by=definite_by)
    elif m & {FATHATAN, DAMMATAN, KASRATAN} or infl.get('marker') == 'fathatan':
        n['definiteness'] = 'indefinite'
    return n


def _stem_segment(slot, after_article, governor=None, gcase=None, agr=None):
    """الجذع: النوع من الدليل القوي وحده (sarf.affix)، أو من عامله: معمول الجار وإنّ المقبولين
    وافقت علامتُه أثرَهما اسمٌ (الحرف الجار والناسخ لا يعملان إلا في اسم)؛ وإلا undetermined"""
    text = slot['text']
    info = stem_info(text)
    seg = dict(role='stem', form=text)
    ev = [dict(source='rule', id='affix', note=e) for e in info['evidence']]
    if governor and info['pos'] != 'verb':
        ev.append(dict(source='governor', id=governor, note='معمولٌ لجارٍّ أو ناسخٍ مقبول، وعلامته توافق أثره'))
    if after_article or info['pos'] == 'noun' or governor and info['pos'] != 'verb':
        seg.update(pos='noun', noun=_noun(text, info, 'article' if after_article else None, gcase))
        if after_article:
            ev.append(dict(source='rule', id='affix', note='أل قبله'))
        return [seg], ev
    if agr and agr.get('verb_by_agreement'):
        info = dict(info, pos='verb')
        ev.append(dict(source='rule', id='T18', note=f"توافقه مع «{agr['narrowed_by']}» قبله: {agr['rule']}"))
    elif agr:
        ev.append(dict(source='rule', id='T18', note=agr['rule'] +
                       (f"؛ وخصّصه «{agr['narrowed_by']}» قبله" if agr.get('narrowed_by') else '')))
    if info['pos'] == 'verb':
        out = []
        for v in _verbs(text, info, agr):
            out.append(dict(seg, pos='verb', verb=v))
        return out, ev
    seg['pos'] = 'undetermined'
    return [seg], ev


# ---------- العامل والمبني ----------
def _operator_ids(cat, op, group):
    u = cat.ops.get((op, group)) if cat else None
    return [m['operator_id'] for m in (u['meanings'] if u else []) if m.get('operator_id')]


def _clitic_type(op, group):
    """العامل بصيغته المشكولة من الفهرس (لا يُجرَّد)"""
    if group == '1':
        return 'oath' if vform_match(op, ('وَ', 'تَ')) else 'preposition'
    if group == '6' and vform_match(op, ['لِ']):
        return 'imperative_lam'
    if group == '4':
        return 'vocative' if vform_match(op, ('يَا', 'أَ', 'أَيْ')) else 'conjunction'
    return 'conjunction'


# نوع العامل من مجموعته في الفهرس، لا من أول مدخلٍ في المعجم (مَا: نافية في 3، وشرطية في 7)
NOUN_CATEGORY = {'7': 'conditional_noun', '8': 'kinaya', '9': 'verb_name'}
NOUN_SUBTYPE = {'7': 'conditional', '8': 'number', '9': 'ism_fiil'}
KINAYA = ('كَمْ', 'كَأَيِّنْ', 'كَذَا', 'كَيْتَ')
PARTICLES_IN_7 = ('لَوْ',)                                # في باب الشرط وهي حرف


def _noun_object(op, group):
    """كائن noun للعامل الاسمي: من المعجم بفئة بابه إن وُجد، وإلا الحدّ الأدنى المعلوم"""
    cat_name = NOUN_CATEGORY.get(group)
    if group == '8' and vform_match(op, KINAYA):
        cat_name = 'kinaya'
    for e in _lex().forms.get(op, []) + _lex().lookup(op):
        if e['pos'] == 'noun' and e['category'] == cat_name:
            return dict(e['noun'])
    subtype = 'kinaya' if cat_name == 'kinaya' else NOUN_SUBTYPE[group]
    if vform_match(op, ['إِذَا']):
        subtype = 'adverbial'
    status = 'murab' if subtype in ('number', 'common') else 'mabni'
    return dict(subtype=subtype, inflection=dict(status=status))


def _operator_segment(cand, slot, cat, role):
    op, group = cand['operator'], cand['group']
    seg = dict(role=role, form=slot['text'])
    if role == 'proclitic':
        seg['clitic_type'] = _clitic_type(op, group)
    ids = _operator_ids(cat, op, group)
    if group in VERB_GROUPS:
        v = dict(tense='past', voice='active', subject=_pron(3, 'singular', 'masc', 'subject'),
                 inflection=dict(status='mabni'), conjugability='jamid' if vform_match(op, JAMID) else 'mutasarrif')
        if group in ('10', '11'):
            v['completeness'] = 'naqis'
        seg.update(pos='verb', verb=v)
    elif group in NOUN_CATEGORY and not vform_match(op, PARTICLES_IN_7) and not (group == '8' and vform_match(op, ['ذُو'])):
        seg.update(pos='noun', noun=_noun_object(op, group))
    elif group == '8' and vform_match(op, ['ذُو']):
        seg.update(pos='noun', noun=dict(subtype='common', five_nouns=True, inflection=dict(status='murab')))
    else:
        p = dict(governing=not vform_match(op, PARTICLES_IN_7), operator_ids=ids, catalog_group=group)
        eff = EFFECT.get(group, 'none')
        if group == '6' and vform_match(op, ['إِنْ']):
            eff = 'jazm_two'
        if group == '3':
            eff = 'raf_ism_nasb_khabar' if vform_match(op, ['مَا']) else 'nasb_ism_raf_khabar'
        if vform_match(op, PARTICLES_IN_7):
            eff = 'none'
        p['effect'] = eff
        if cand.get('kaffa'):
            p.update(kaffa=True, governing=False, effect='none')
        seg.update(pos='particle', particle=p)
    return seg, ids


def _mabni_segment(slot, prev_seg):
    """مبني من الملف: يُنسخ كائنه كما هو؛ والضمير المتصل enclitic بوظيفته من مضيفه"""
    text = slot['text']
    e = None
    if slot.get('lexicon'):
        e = next((x for x in _lex().entries if x['entry_id'] == slot['lexicon'][0]), None)
    e = e or _lex().attested(text)
    if slot['role'] in ('conj', 'proclitic'):
        from .match import vform_match
        ct = 'resumption_fa' if vform_match(text, ['فَ']) else 'emphasis_lam' if vform_match(text, ['لَ']) else 'conjunction'
        seg = dict(role='proclitic', form=text, clitic_type=ct, pos='particle',
                   particle=dict(governing=False, effect='none'))
        return seg, e
    if slot['role'] == 'kaffa':
        return dict(role='suffix', form=text, suffix_type='other', pos='particle',
                    particle=dict(governing=False, effect='none')), e
    if slot['role'] == 'muqattaat':
        return dict(role='stem', form=text, pos='undetermined'), None
    if e and e['category'] == 'attached_pronoun' and prev_seg is not None:
        pr = dict(e.get('pronoun') or {})
        if prev_seg.get('pos') == 'particle':
            pr['function'] = 'governed_by_particle'
        elif prev_seg.get('pos') == 'verb':
            pr['function'] = 'object'
        elif prev_seg.get('pos') == 'noun':
            pr['function'] = 'possessive'
        seg = dict(role='enclitic', form=text, pronoun=pr) if 'person' in pr else \
            dict(role='stem', form=text, pos='noun', noun=dict(e['noun']))
        if seg['role'] == 'enclitic':
            seg.update(pos='noun', noun=dict(e['noun']))
        return seg, e
    if e:
        seg = dict(role='stem', form=text, pos=e['pos'])
        seg[e['pos']] = dict(e[e['pos']])
        return seg, e
    return dict(role='stem', form=text, pos='undetermined'), None


def _divine_segment(slot):
    infl = dict(status='murab')
    m = _last_mark(slot['text'])
    for mk, case in MARK_CASE.items():
        if mk in m:
            infl.update(case=case, marker=MARK_NAME[mk], marker_kind='original')
            break
    obs = _observed(slot['text'])
    if obs:
        infl['observed_mark'] = obs
    return dict(role='stem', form=slot['text'], pos='noun',
                noun=dict(subtype='proper', derivation=dict(**{'class': 'jamid'}), definiteness='definite',
                          definite_by='proper', inflection=infl))


# ---------- الكلمة ----------
def _syllables(seg):
    out, spans = [], {}
    for u in seg['units']:
        a = len(out)
        for x in u.get('syllables') or []:
            out.append(dict(text=x['syl'], cv=x['cv'], verdict=x['verdict']))
        for si in u['slots']:
            if len(out) > a:
                spans[si] = [a, len(out)]
    return out, spans


def _word(a, seg, cat, governed):
    wi = seg['word_index']
    cands = [f for f in a['operators'] if f['word_index'] == wi]
    sylls, sspans = _syllables(seg)
    # التحليل الأول
    segs, ev, choice, open_ = [], [], {}, False
    alts = []
    stem_variants = None
    prev = None
    for s in seg['slots']:
        if s['type'] == AMIL:
            ops = [c for c in cands if (c['operator'], c['group']) in [tuple(o) for o in s['operators']]]
            ops.sort(key=lambda c: c['status'] != ACCEPTED)
            c = ops[0]
            choice[s['index']] = c
            role = 'proclitic' if c['method'].startswith('proclitic') and s['index'] < len(seg['slots']) - 1 \
                else 'stem'
            sg, ids = _operator_segment(c, s, cat, role)
            ev += [dict(source='catalog', id=i) for i in ids[:1]]
            ev += [dict(source='rule', id='T09', note=p) for p in c.get('judgement', {}).get('proof', [])]
            ev += [dict(source='rule', id='T09', note='مؤجَّل: ' + w) for w in c.get('judgement', {}).get('deferred_because', [])]
            if c['status'] != ACCEPTED:
                open_ = True
            for other in ops[1:]:
                alts.append((s['index'], other, role))
        elif s['type'] == MABNI:
            sg, e = _mabni_segment(s, prev)
            if e:
                ev.append(dict(source='lexicon', id=e['entry_id']))
        elif s['type'] == ARTICLE:
            sg = dict(role='proclitic', form=s['text'], clitic_type='definite_article')
        elif s['type'] == DIVINE:
            sg = _divine_segment(s)
        else:
            after_article = s['index'] > 0 and seg['slots'][s['index'] - 1]['type'] == ARTICLE
            gov = governed.get((wi, s['index']))
            agr = next((x for x in a.get('agreement', []) if x['word_index'] == wi and x['slot'] == s['index']), None)
            variants, sev = _stem_segment(s, after_article, gov[0] if gov else None, gov[1] if gov else None, agr)
            mo = next((x for x in a.get('morph', []) if x['word_index'] == wi and x['slot'] == s['index']
                       and x['status'] == 'accepted'), None)
            if mo and variants[0].get('pos') == 'verb':
                # T19c: الجذر والصيغة المرخَّصان، وشاهدهما من HFN
                rt = dict(radicals=list(mo['root']))
                snd = soundness(mo['root'])
                if snd:
                    rt['soundness'] = snd
                pat = dict(wazn=(mo['event'] or {}).get('hfn_form') or WAZN.get(mo['form_class'], mo['form_class']),
                           augmented=mo['form_class'] not in ('I', 'QI'))
                variants = [dict(v, root=rt, pattern=pat) for v in variants]
                if mo['event']:
                    sev.append(dict(source='lexicon', id=mo['event']['event_id'],
                                    note=f"HFN: {mo['event']['verb']} ({mo['event']['source']})"))
                else:
                    sev.append(dict(source='lexicon', id='HFN-root:' + mo['root'],
                                    note='الجذر مسجَّل في HFN، والوزن بالقالب؛ لا حدث مسجَّل'))
            ev += sev
            sg = variants[0]
            if len(variants) > 1:
                stem_variants = (len(segs), variants[1:])
            if sg.get('pos') == 'undetermined':
                open_ = True
        sg['char_span'] = list(s['span'])
        if s['index'] in sspans:
            sg['syllable_span'] = sspans[s['index']]
        segs.append(sg)
        prev = sg
    status = 'candidate' if open_ else 'selected'
    analyses = [dict(score=SCORE[status], status=status, segments=segs, evidence=ev)]
    # تحليلات بديلة: إسنادٌ آخر للفعل، ومرشَّح آخر على الخانة نفسها
    if stem_variants:
        k, vs = stem_variants
        for v in vs:
            alt = [dict(x) for x in segs]
            alt[k] = dict(v, char_span=segs[k]['char_span'], **({'syllable_span': segs[k]['syllable_span']}
                                                                if 'syllable_span' in segs[k] else {}))
            analyses.append(dict(score=SCORE['candidate'], status='candidate', segments=alt,
                                 evidence=[dict(source='rule', id='affix', note='إسنادٌ آخر تحتمله الكتابة')]))
    for si, c, role in alts:
        alt = [dict(x) for x in segs]
        s = seg['slots'][si]
        sg, ids = _operator_segment(c, s, cat, role)
        sg['char_span'] = list(s['span'])
        alt[si] = sg
        st = STATUS[c['status']]
        analyses.append(dict(score=SCORE[st], status=st, segments=alt,
                             evidence=[dict(source='catalog', id=i) for i in ids[:1]] +
                             [dict(source='rule', id='T09', note=w) for w in c.get('judgement', {}).get('deferred_because', [])]))
    # الممنوع: يُحفظ ومعه سببه
    for c in cands:
        if c['status'] != BLOCKED:
            continue
        b_ = c['char_span'][1]
        form = c['operator']
        if c['method'].startswith('proclitic'):
            rest = ''.join(L + ''.join(sorted(m)) for L, m in letters(seg['word'])[b_:]) or seg['word']
            sgs = [_operator_segment(c, dict(text=form), cat, 'proclitic')[0],
                   dict(role='stem', form=rest, pos='undetermined')]
        else:
            sgs = [_operator_segment(c, dict(text=seg['word']), cat, 'stem')[0]]
        analyses.append(dict(score=0.0, status='rejected', segments=sgs,
                             evidence=[dict(source='rule', id='evidence', note=c.get('reject_reason') or 'ممنوع')]))
    analyses.sort(key=lambda x: -x['score'])
    tok = dict(index=wi, surface=seg['word'], normalized=seg['word'], analyses=analyses)
    if any(s['type'] == DIVINE for s in seg['slots']):
        tok['fixed_lexeme'] = dict(lexeme_id='ALLAH', kind='divine_name')
    elif any(s['role'] == 'muqattaat' for s in seg['slots']):
        tok['fixed_lexeme'] = dict(lexeme_id='MUQATTAAT', kind='closed_class', note='حروف مقطّعة: تُقرأ بأسماء حروفها')
        tok['syllables'] = sylls
    else:
        tok['syllables'] = sylls
    return tok, choice


def to_schema(a, cat=None, ref=None, original=None):
    """تحليل الآية (sarf.analyze) → كائن بصيغة morph_analysis.schema.json"""
    tokens, choices = [], {}
    surfaces = (original or a['verse']).split()
    status = {(f['word_index'], f['operator'], f['group']): f['status'] for f in a['operators']}
    governed = {}
    for r in a.get('relations', []):
        t = r.get('target')
        if t and r['consistent'] is True and t.get('pos') != 'verb' and r['group'] in ('1', '2') and \
                status.get((r['word_index'], r['operator'], r['group'])) == ACCEPTED:
            ids = _operator_ids(cat, r['operator'], r['group'])
            governed[(t['word_index'], t['slot'])] = (ids[0] if ids else r['operator'], CASE[r['expected']])
    for seg in a['segments']:
        tok, choice = _word(a, seg, cat, governed)
        if len(surfaces) == len(a['segments']):
            tok['surface'] = surfaces[seg['word_index']]
        tokens.append(tok)
        choices[seg['word_index']] = choice
    deps = []
    for r in a.get('relations', []):
        t = r.get('target')
        if not t or r['slot'] not in choices.get(r['word_index'], {}):
            continue
        c = choices[r['word_index']][r['slot']]
        if (c['operator'], c['group']) != (r['operator'], r['group']) or r['expected'] is None:
            continue
        is_verb = t.get('pos') == 'verb'
        key, table = ('mood', MOOD) if is_verb else ('case', CASE)
        if r['expected'] not in table:
            continue
        d = dict(governor=dict(token=r['word_index'], analysis=0, segment=r['slot']),
                 dependent=dict(token=t['word_index'], analysis=0, segment=t['slot']),
                 expected={key: table[r['expected']]})
        ids = _operator_ids(cat, r['operator'], r['group'])
        if ids:
            d['operator_id'] = ids[0]
        if r['observed'] in table:
            d['observed'] = {key: table[r['observed']]}
            mk = _observed(t['text'])
            if mk:
                d['observed']['mark'] = mk
        if r['consistent'] is not None:
            d['consistent'] = r['consistent']
        deps.append(d)
    src = original or a['verse']
    script = 'uthmani' if any(ch in UTHMANI_SIGNS or ch == '\u06E1' for ch in src) else 'unknown'
    text = dict(original=src, normalized=a['normalized'], script=script)
    if ref:
        text['ref'] = dict(surah=ref[0], ayah=ref[1])
    out = dict(schema_version=SCHEMA_VERSION, text=text, tokens=tokens)
    if deps:
        out['dependencies'] = deps
    return out
