# -*- coding: utf-8 -*-
"""
sarf.segment — المقشِّر: تجزئة الكلمة إلى خانات (slots) لكلٍّ منها نوع، وربط العامل بمعموله.

أنواع الخانات:
    عامل          من فهرس العوامل (يؤثّر فيما بعده)        لا يُقطَّع، ويُعرض «عامل»
    مبني          من معجم المبنيات، وأل، والضمير المتصل،  لا يُقطَّع، ويُعرض «مبني»
                  وحرف العطف، وما الكافة
    معرب          ما بقي (الجذع)                            يُقطَّع CV
    لفظ الجلالة   ليس كمثله شيء                             لا يُقطَّع

شرط الفصل بين خانتين: أن تبدأ الثانية بحرف متحرك، فيكون حدّ الخانة حدَّ مقطع.
والشدة على الحدّ تُفكّ: نصفها الأول (الساكن) للخانة السابقة، ونصفها الثاني للتالية
(النَّاسِ = [ءَنْ: أل][نَاسِ]). وإن بدأت الثانية بساكن أو بهمزة وصل فلا فصل، وتُضمّ الخانتان
في وحدة واحدة (وَٱمْسَحُوا، فَلْيَكْتُبْ ← [فَلْ][يَكْتُبْ]).
الوحدة التي فيها خانة معربة تُقطَّع كلها، وما سواها لا يُقطَّع.

العلاقة: لكل عامل غير مرفوض معمولٌ هو الخانة التالية في كلمته، أو أول خانة في الكلمة التالية
(بعد حرف العطف وأل). وحكم المعمول من مجموعة العامل في الفهرس، ويُقارَن بالعلامة المكتوبة
في الجر والنصب والرفع على الاسم.

ملاحظة: الحروف من خارج «سألتمونيها» جذرية بعد فصل حروف المعاني المتصلة (العطف، والجر،
وأل، والضمائر). وتقشير زوائد البنية (أحرف المضارعة وغيرها) لم يُكتب بعد.
"""
from .chars import (FATHA, DAMMA, KASRA, SUKUN, FATHATAN, DAMMATAN, KASRATAN,
                    MARKS, letters, plain)
from .divine import divine_name
from .match import PRON_SUFFIXES, match_letters, vocal_compatible
from . import syllabify as cv

AMIL, MABNI, MURAB, DIVINE = 'عامل', 'مبني', 'معرب', 'لفظ الجلالة'

MOVING = {FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN}
STEM_SUFFIXES = [s for s in PRON_SUFFIXES if s != 'ي']      # ياء المتكلم وحدها ملتبسة بياء المدّ
MIN_STEM = 3                                                # أقلّ حروف الجذع بعد نزع الضمير

# حكم المعمول بمجموعة العامل (الاسم بعد الجار، واسم إنّ، واسم كان؛ والفعل بعد الناصب والجازم)
EXPECTED = {'1': 'جر', '2': 'نصب', '5': 'نصب', '6': 'جزم', '7': 'جزم', '10': 'رفع', '11': 'رفع', '13': 'نصب'}
CHECKED = {'1', '2', '10', '11'}                            # يُقارَن بالعلامة المكتوبة على الاسم
MARK_CASE = {KASRA: 'جر', KASRATAN: 'جر', FATHA: 'نصب', FATHATAN: 'نصب',
             DAMMA: 'رفع', DAMMATAN: 'رفع', SUKUN: 'جزم'}


# ---------- الحروف ومواضعها ----------
def _offsets(word):
    """→ [(بداية، نهاية)] لكل حرف بعلاماته في نص الكلمة"""
    out = []
    for i, ch in enumerate(word):
        if ch in MARKS or ch == 'ـ':
            if out:
                out[-1][1] = i + 1
        else:
            out.append([i, i + 1])
    return out

def _exp_map(word):
    """فهرس حروف match_letters(word, True) ← فهرس الحرف الأصلي (الخنجرية تُمدّ ألفاً)"""
    m = []
    for i, (L, mk) in enumerate(letters(word)):
        m.append(i)
        if 'ٰ' in mk and L not in ('ى', 'ا'):
            m.append(i)
    return m

def _moving(tok):
    return bool(tok[1] & MOVING)


# ---------- الخانات ----------
def _slot(word, offs, a, b, typ, role, **kw):
    s = dict(text=word[offs[a][0]:offs[b - 1][1]], type=typ, role=role, span=(a, b))
    s.update(kw)
    return s

def _host(word, toks, offs, a, b, lex, at_word_start):
    """خانات ما ليس عاملاً: مبني من المعجم كاملاً، أو [أل][جذع معرب][ضمير متصل]"""
    text = word[offs[a][0]:offs[b - 1][1]]
    hits = lex.lookup(text) if lex else []
    if hits:
        return [_slot(word, offs, a, b, MABNI, 'lexicon', lexicon=[h['entry_id'] for h in hits],
                      note=hits[0]['category'])]
    slots = []
    if b - a > 2 and toks[a][0] == 'ا' and toks[a + 1][0] == 'ل' and \
            (not toks[a + 1][1] or toks[a + 1][1] == {SUKUN}):
        slots.append(_slot(word, offs, a, a + 2, MABNI, 'article', note='أل التعريف'))
        a += 2
    tail = None
    for suf in sorted(STEM_SUFFIXES, key=lambda s: -len(letters(s))):
        stoks = match_letters(suf)
        k = len(stoks)
        if b - k - a < MIN_STEM:
            continue
        cand = [(L, frozenset(m)) for L, m in toks[b - k:b]]
        if plain(cand, True) == plain(stoks, True) and vocal_compatible(cand, stoks)[0]:
            tail = _slot(word, offs, b - k, b, MABNI, 'enclitic', note='ضمير متصل')
            b -= k
            break
    if b > a:
        slots.append(_slot(word, offs, a, b, MURAB, 'stem'))
    if tail:
        slots.append(tail)
    return slots

def segment_word(word, wi, cands, lex):
    toks = [(L, set(m)) for L, m in letters(word)]
    offs = _offsets(word)
    n = len(toks)
    emap = _exp_map(word)
    # 1. خانات العوامل (غير المرفوضة) بمواضعها في الحروف الأصلية
    by_span = {}
    for c in cands:
        if c.get('status') == 'rejected':
            continue
        if c['method'] == 'multi_word':
            span = (0, n)
        else:
            a, b = c['char_span']
            if c.get('expanded', True):
                a, b = emap[a], emap[b - 1] + 1
            span = (a, b)
        by_span.setdefault(span, []).append(c)
    op_slots, last = [], 0
    for span in sorted(by_span, key=lambda s: (s[0], -s[1])):
        if span[0] < last:
            continue                                   # تداخل: يبقى الأسبق
        cs = by_span[span]
        op_slots.append(_slot(word, offs, span[0], span[1], AMIL, 'operator',
                              operators=[(c['operator'], c['group']) for c in cs], cands=cs))
        last = span[1]
    # 2. ما بين العوامل وبعدها
    slots, pos = [], 0
    divine = divine_name(word) is not None
    for k, op in enumerate(op_slots + [None]):
        end = op['span'][0] if op else n
        if end > pos:
            prev = slots[-1] if slots else None
            if pos == 0 and end == 1 and toks[0][0] in ('و', 'ف') and op:
                slots.append(_slot(word, offs, 0, 1, MABNI, 'conj', note='حرف عطف'))
            elif divine and op is None:
                slots.append(_slot(word, offs, pos, end, DIVINE, 'divine'))
            elif prev and prev['type'] == AMIL and any(c.get('kaffa') for c in prev['cands']):
                slots.append(_slot(word, offs, pos, end, MABNI, 'kaffa', note='ما الكافة'))
            elif prev and prev['type'] == AMIL and any(c['method'].startswith('operator+suffix')
                                                       for c in prev['cands']):
                slots.append(_slot(word, offs, pos, end, MABNI, 'enclitic', note='ضمير متصل'))
            else:
                slots += _host(word, toks, offs, pos, end, lex, pos == 0)
        if op:
            slots.append(op)
            pos = op['span'][1]
    # 3. الوحدات: تُضمّ الخانة إلى سابقتها إن بدأت بغير متحرك
    units = []
    for i, s in enumerate(slots):
        s['index'] = i
        if units and not _moving(toks[s['span'][0]]):
            units[-1].append(s)
        else:
            units.append([s])
    out_units = []
    for j, us in enumerate(units):
        a, b = us[0]['span'][0], us[-1]['span'][1]
        types = [s['type'] for s in us]
        if DIVINE in types:
            kind, label = DIVINE, DIVINE
        elif MURAB in types:
            kind, label = MURAB, None
        else:
            kind = 'fixed'
            label = '+'.join(dict.fromkeys(types))
        for s in us:
            s['unit'] = j
        out_units.append(dict(text=word[offs[a][0]:offs[b - 1][1]], kind=kind, label=label,
                              slots=[s['index'] for s in us], syllables=[]))
    for s in slots:
        s.pop('cands', None)
    return dict(word_index=wi, word=word, slots=slots, units=out_units, toks=toks)


# ---------- العلاقة: العامل ← المعمول ----------
def _observed(seg, slot):
    """العلامة المكتوبة على آخر حرف في الخانة → الحالة، أو None إن لم تدلّ عليها"""
    a, b = slot['span']
    toks = seg['toks']
    L, mk = toks[b - 1]
    if L == 'ن' and FATHA in mk and b - a > 2 and toks[b - 2][0] in ('و', 'ي'):
        return None                                    # ـونَ/ـينَ: علامة بالحرف
    for m, case in MARK_CASE.items():
        if m in mk:
            return case
    return None

def _target(segs, wi, si):
    seg = segs[wi]
    if si + 1 < len(seg['slots']):
        return wi, si + 1
    if wi + 1 < len(segs):
        for t in segs[wi + 1]['slots']:
            if t['role'] not in ('conj', 'article'):
                return wi + 1, t['index']
    return None

def relate(segs, cands):
    rels = []
    for c in cands:
        if c.get('status') == 'rejected':
            continue
        seg = segs[c['word_index']]
        si = next((s['index'] for s in seg['slots']
                   if s['type'] == AMIL and (c['operator'], c['group']) in s['operators']), None)
        if si is None:
            continue
        r = dict(operator=c['operator'], group=c['group'], word_index=c['word_index'], slot=si,
                 target=None, expected=EXPECTED.get(c['group']), observed=None, consistent=None, note=None)
        if c.get('kaffa'):
            r.update(expected=None, note='مكفوفة بما: لا تعمل')
            rels.append(r)
            continue
        tg = _target(segs, c['word_index'], si)
        if tg:
            ts = segs[tg[0]]['slots'][tg[1]]
            r['target'] = dict(word_index=tg[0], slot=tg[1], text=ts['text'], type=ts['type'])
            if ts['type'] == MABNI:
                r['observed'] = 'محلاً'
            elif ts['type'] == AMIL:
                r['note'] = 'المعمول يبدأ بعامل: جملة أو مصدر مؤوَّل'
            elif r['expected'] and c['group'] in CHECKED:
                obs = _observed(segs[tg[0]], ts)
                r['observed'] = obs
                if obs == r['expected']:
                    r['consistent'] = True
                elif obs and not ((r['expected'], obs) in (('جر', 'نصب'), ('نصب', 'جر'))):
                    r['consistent'] = False      # الجر بالفتحة (الممنوع من الصرف) والنصب بالكسرة (جمع المؤنث) لا يُحكم فيهما
        rels.append(r)
    return rels


# ---------- التقطيع على الوحدات المعربة ----------
def segment(words, cands, lex):
    segs = [segment_word(w, wi, [c for c in cands if c['word_index'] == wi or
                                 (c['method'] == 'multi_word' and c['words_span'][0] <= wi < c['words_span'][1])],
                         lex)
            for wi, w in enumerate(words)]
    rels = relate(segs, cands)
    for seg in segs:
        del seg['toks']
    return segs, rels

def syllabify_units(segs):
    """تقطيع الوحدات المعربة وحدها → ناتج بصيغة cv.run (counts، rows، events …)"""
    from collections import Counter
    events, counts = cv.Events(), Counter()
    rows, others, cv_line = [], [], []
    divine_words = []
    for seg in segs:
        wi = seg['word_index']
        if any(u['kind'] == DIVINE for u in seg['units']):
            divine_words.append(wi)
        for u in seg['units']:
            if u['kind'] != MURAB:
                continue
            r = cv.run(u['text'])
            events.update(r['events'])
            for rend, pat, verdict, _ in r['rows']:
                rows.append((rend, pat, verdict, [wi]))
                counts[pat] += 1
                cv_line.append(pat)
                u['syllables'].append(dict(syl=rend, cv=pat, verdict=verdict))
                if verdict != 'OK':
                    others.append((rend, pat, verdict, [seg['word']]))
    events['DIVINE_NAME'] = len(divine_words)
    return dict(counts=counts, rows=rows, others=others, events=events, divine_words=divine_words,
                cv_line=cv_line, n_words=len(segs), n_syll=len(rows), raw_words=[s['word'] for s in segs])

def unit_view(segs):
    """كل كلمة بوحداتها: المعرب بمقاطعه، وما سواه بوسمه"""
    lines = []
    for seg in segs:
        parts, pats = [], []
        for u in seg['units']:
            if u['kind'] == MURAB:
                parts.append(' . '.join(s['syl'] for s in u['syllables']))
                pats += [s['cv'] for s in u['syllables']]
            else:
                parts.append(f"[{u['text']}: {u['label']}]")
        lines.append(f"{seg['word']:<16} {' | '.join(parts):<44} {' '.join(pats)}")
    return '\n'.join(lines)
