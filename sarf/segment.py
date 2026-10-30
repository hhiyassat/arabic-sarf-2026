# -*- coding: utf-8 -*-
"""
sarf.segment — المقشِّر: تجزئة الكلمة إلى خانات (slots) لكلٍّ منها نوع، وربط العامل بمعموله.

أنواع الخانات:
    عامل          من فهرس العوامل (يؤثّر فيما بعده)         لا يُقطَّع، ويُعرض «عامل»
    مبني          ما في ملف المبنيات (02_mabniyat) وحده:     لا يُقطَّع، ويُعرض «مبني»
                  كلمةً كاملة، أو حرف عطف، أو ما الكافة، أو ضميراً متصلاً (بصوره: sarf.lexicon)
    أل            أل التعريف: ليست في الملف                 تُقطَّع مع جذعها
    جذع           ما بقي، ومنه الفعل الماضي والأمر           يُقطَّع CV
                  (مبنيان، لكنهما ليسا في الملف)
    لفظ الجلالة   ليس كمثله شيء                              لا يُقطَّع
    ما لم يجده المقشِّر في الملف من حرف عطف أو ضمير (نون الوقاية في «نِي») يصير جذعاً ويُقطَّع.

شرط الفصل بين خانتين: أن تبدأ الثانية بما يُبتدأ به: حرف متحرك، أو همزة وصل تُنطق ابتداءً
كما في أول الكلمة (بِٱلْعَدْلِ = [بِ][ءَلْعَدْلِ]، وَٱمْسَحُوا = [وَ][ءِمْسَحُوا]).
والشدة على الحدّ تُفكّ: نصفها الأول (الساكن) للخانة السابقة، ونصفها الثاني للتالية
(النَّاسِ = [ءَنْ: أل][نَاسِ]). وإن بدأت الثانية بساكن فلا فصل، وتُضمّ الخانتان في وحدة واحدة
(فَلْيَكْتُبْ ← [فَلْ][يَكْتُبْ]).
وتُضمّ الخانات المتجاورة التي تُقطَّع (أل، جذع) في وحدة واحدة. والوحدة التي فيها خانة تُقطَّع
تُقطَّع كلها، وما سواها لا يُقطَّع.

العلاقة: لكل عامل غير مرفوض معمولٌ هو الخانة التالية في كلمته، أو أول خانة في الكلمة التالية
(بعد حرف العطف وأل). وحكم المعمول من مجموعة العامل في الفهرس، ويُقارَن بالعلامة المكتوبة
في الجر والنصب والرفع على الاسم.

ملاحظة: الحروف من خارج «سألتمونيها» جذرية بعد فصل حروف المعاني المتصلة (العطف، والجر،
وأل، والضمائر). وتقشير زوائد البنية (أحرف المضارعة وغيرها) لم يُكتب بعد.
"""
from .chars import (FATHA, DAMMA, KASRA, SUKUN, FATHATAN, DAMMATAN, KASRATAN,
                    MARKS, letters, plain, strip_marks)
from .divine import divine_name
from .match import PRON_SUFFIXES, match_letters, vocal_compatible, vform_match
from . import syllabify as cv
from .affix import stem_info, radical_nun, short_host, ha_kasra_ok
from .status import BLOCKED

AMIL, MABNI, ARTICLE, STEM, DIVINE = 'عامل', 'مبني', 'أل', 'جذع', 'لفظ الجلالة'
CUT_TYPES = {ARTICLE, STEM}                                  # ما يُقطَّع
CUT, FIXED = 'cut', 'fixed'                                  # نوع الوحدة

MOVING = {FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN}
STEM_SUFFIXES = [s for s in PRON_SUFFIXES if s != 'ي']      # ياء المتكلم وحدها ملتبسة بياء المدّ
MIN_STEM = 3                                                # أقلّ حروف الجذع بعد نزع الضمير

# حكم المعمول بمجموعة العامل (الاسم بعد الجار، واسم إنّ، واسم كان؛ والفعل بعد الناصب والجازم)
EXPECTED = {'1': 'جر', '2': 'نصب', '5': 'نصب', '6': 'جزم', '7': 'جزم', '10': 'رفع', '11': 'رفع', '13': 'نصب'}
NO_JAZM = ('لَوْ', 'إِذَا')                                    # في باب الشرط ولا تجزم (الفهرس: «لا يجزم»)
CHECKED = {'1', '2', '10', '11'}                            # يُقارَن بالعلامة المكتوبة على الاسم
VERB_CHECKED = {'1', '5', '6', '7'}                         # ويُقارَن بعلامة المضارع (sarf.affix)
YA_CASE = 'جر أو نصب'                                        # ياء الجمع والمثنى
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

def _opens(tok):
    """هل تبدأ الخانة بما يُبتدأ به: حرف متحرك، أو همزة وصل تُنطق ابتداءً (بِٱلْعَدْلِ = بِ + ءَلْعَدْلِ).
    والمشدَّد خليتان أولاهما ساكنة (حكم صاحب النظرية)، فلا يُبتدأ به: لِلَّهِ وحدةٌ واحدة، ولفظ الجلالة لا يُقطع"""
    if '\u0651' in tok[1]:
        return False
    return _moving(tok) or (tok[0] == 'ا' and not tok[1])


# ---------- الخانات ----------
def _slot(word, offs, a, b, typ, role, **kw):
    s = dict(text=word[offs[a][0]:offs[b - 1][1]], type=typ, role=role, span=(a, b))
    s.update(kw)
    return s

def _host(word, toks, offs, a, b, lex, at_word_start):
    """خانات ما ليس عاملاً: مبني من المعجم كاملاً، أو [أل][جذع][ضمير متصل]"""
    text = word[offs[a][0]:offs[b - 1][1]]
    hits = lex.lookup(text) if lex else []
    if not hits and lex and a > 0 and toks[a - 1][0] == 'ل' and toks[a][0] == 'ل':
        hits = lex.lookup('ا' + text)          # لِلَّذِينَ: ألف «ٱلَّذِينَ» محذوفة خطاً بعد لام الجر
    if not hits and lex and not at_word_start:
        # بقية الكلمة بعد السابقة ضمير متصل بصورته (بِهِمْ، لَهُ): مبني
        e = lex.attested(text)
        if e and e['category'] == 'attached_pronoun':
            hits = [e]
    if hits:
        return [_slot(word, offs, a, b, MABNI, 'lexicon', lexicon=[h['entry_id'] for h in hits],
                      note=hits[0]['category'])]
    slots = []
    if at_word_start and b - a > 2 and toks[a][0] in ('و', 'ف') and toks[a][1] == {FATHA} and \
            toks[a + 1][0] == 'ا' and not toks[a + 1][1]:
        # وَ/فَ قبل همزة الوصل حرف عطف يقيناً: همزة الوصل لا تقع وسط الكلمة (فَٱكْتُبُوهُ)
        slots.append(_slot(word, offs, a, a + 1, MABNI, 'conj', note='حرف عطف'))
        return slots + _host(word, toks, offs, a + 1, b, lex, False)
    if b - a > 2 and toks[a][0] == 'ا' and toks[a + 1][0] == 'ل' and \
            (not toks[a + 1][1] or toks[a + 1][1] == {SUKUN}):
        slots.append(_slot(word, offs, a, a + 2, ARTICLE, 'article', note='أل التعريف: ليست في ملف المبنيات'))
        a += 2
    elif b - a > 2 and a > 0 and toks[a - 1][0] == 'ل' and toks[a][0] == 'ل' and \
            (not toks[a][1] or toks[a][1] == {SUKUN}):
        # بعد لام الجر تُحذف ألف «أل» خطاً وتبقى لامها: لِّلۡمُطَفِّفِينَ، لِلنَّاسِ
        slots.append(_slot(word, offs, a, a + 1, ARTICLE, 'article', note='لام «أل» بعد لام الجر'))
        a += 1
    tail = None
    for suf in sorted(STEM_SUFFIXES, key=lambda s: -len(letters(s))):
        stoks = match_letters(suf)
        k = len(stoks)
        if suf == 'نَا' and b - k - 1 >= a and SUKUN in toks[b - k - 1][1]:
            continue                                # «نَا» بعد ساكن ضمير الفاعل في الماضي (جَعَلۡنَا) لا يُفصل كالتاء
        if (b - k - a < MIN_STEM and not short_host(toks[a:b - k])) or radical_nun(toks[a:b], suf) or \
                toks[b - k][0] == 'ة' or not ha_kasra_ok(toks[a:b], suf):   # التاء المربوطة ليست هاء الضمير (ٱلۡجِنَّةِ)
            continue
        cand = [(L, frozenset(m)) for L, m in toks[b - k:b]]
        if plain(cand, True) == plain(stoks, True) and vocal_compatible(cand, stoks)[0]:
            tail = _slot(word, offs, b - k, b, MABNI, 'enclitic', note='ضمير متصل')
            b -= k
            break
    if b > a:
        slots.append(_slot(word, offs, a, b, STEM, 'stem'))
    if tail:
        slots.append(tail)
    return slots

# الحروف المقطّعة في أوائل السور: تُقرأ بأسماء حروفها (ألِفْ لامْ ميمْ)، فلا تُقطَّع كلماتٍ
MUQATTAAT = {'الم', 'المص', 'الر', 'المر', 'كهيعص', 'طه', 'طسم', 'طس', 'يس', 'ص', 'حم', 'عسق', 'ق', 'ن'}

def _muqattaat(toks):
    """أوّل كلمة في الآية من الحروف المقطّعة: صورتها في القائمة، ولا حركة على حروفها"""
    return plain(toks) in MUQATTAAT and not any(m & MOVING for _, m in toks)

def segment_word(word, wi, cands, lex):
    toks = [(L, set(m)) for L, m in letters(word)]
    offs = _offsets(word)
    n = len(toks)
    if wi == 0 and _muqattaat(toks):
        sl = _slot(word, offs, 0, n, MABNI, 'muqattaat', note='حروف مقطّعة: تُقرأ بأسماء حروفها')
        sl.update(index=0, unit=0)
        return dict(word_index=wi, word=word, toks=toks, slots=[sl],
                    units=[dict(text=word, kind=FIXED, label='حروف مقطّعة', slots=[0], syllables=[])])
    emap = _exp_map(word)
    # 1. خانات العوامل (غير المرفوضة) بمواضعها في الحروف الأصلية
    by_span = {}
    for c in cands:
        if c.get('status') == BLOCKED:
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
    # 1b. السابقة المرفوضة عاملاً حرفٌ مبني إن كانت في الملف (وَ العاطفة، لَ التوكيد): تبقى خانة لا تُقطَّع
    taken = [o['span'] for o in op_slots]
    for c in cands:
        if c.get('status') != BLOCKED or not c['method'].startswith('proclitic') or c.get('radical'):
            continue                                   # الحرف الأصلي (كَيۡفَ، كَذَّبَتۡ) لا يُفصل
        a, b = c['char_span']
        if c.get('expanded', True):
            a, b = emap[a], emap[b - 1] + 1
        if any(x < b and a < y for x, y in taken):
            continue
        sl = _slot(word, offs, a, b, MABNI, 'proclitic', note='حرف ليس عاملاً هنا', cands=[])
        if lex and lex.attested(sl['text']):
            op_slots.append(sl)
            taken.append((a, b))
    op_slots.sort(key=lambda o: o['span'])
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
            elif prev and prev['type'] == AMIL and any(c.get('kaffa') for c in prev.get('cands', [])):
                slots.append(_slot(word, offs, pos, end, MABNI, 'kaffa', note='ما الكافة'))
            elif prev and prev['type'] == AMIL and any(c['method'].startswith('operator+suffix')
                                                       for c in prev.get('cands', [])):
                slots.append(_slot(word, offs, pos, end, MABNI, 'enclitic', note='ضمير متصل'))
            else:
                slots += _host(word, toks, offs, pos, end, lex, pos == 0)
        if op:
            slots.append(op)
            pos = op['span'][1]
    # الحرف المدغم في الضمير: نصف الشدة الأول للعامل، والثاني للضمير
    #   إِلَىَّ = [إِلَيْ][يَ]، كُنَّا = [كُنْ][نَا]
    for i, s in enumerate(slots):
        notes = [c.get('note') or '' for c in s.get('cands', [])] if s['type'] == AMIL else []
        if any('ياء المتكلم مدغمة' in n for n in notes) and i + 1 < len(slots):
            s['text'] += 'يْ'
            slots[i + 1]['text'] = 'يَ'
        elif any('نون الفعل مدغمة' in n for n in notes):
            a, b = s['span']
            tail = word[offs[b - 1][1]:]
            s['text'] = word[offs[a][0]:offs[b - 1][0]] + 'نْ'
            pron = _slot(word, offs, b - 1, n, MABNI, 'enclitic', note='ضمير متصل')
            pron['text'] = 'نَ' + tail
            pron['span'] = (b, n) if b < n else (b - 1, n)
            if i + 1 < len(slots) and slots[i + 1]['role'] == 'enclitic':
                slots[i + 1] = pron
            else:
                slots.insert(i + 1, pron)
    # 3. المبني لا يكون إلا ما في الملف: ما لم يُوجد فيه من حرف عطف أو كافة أو ضمير يصير جذعاً
    for s in slots:
        if s['type'] == MABNI and s['role'] in ('conj', 'kaffa', 'enclitic'):
            e = lex.attested(s['text']) if lex else None
            if e:
                s['lexicon'] = [e['entry_id']]
            else:
                s['type'] = STEM
                s['note'] = (s.get('note') or '') + ': ليس في ملف المبنيات'
    # 4. الوحدات: تُضمّ الخانة إلى سابقتها إن بدأت بساكن، أو كانتا كلتاهما مما يُقطَّع
    units = []
    for i, s in enumerate(slots):
        s['index'] = i
        if units and (not _opens(toks[s['span'][0]]) or
                      (s['type'] in CUT_TYPES and units[-1][-1]['type'] in CUT_TYPES)):
            units[-1].append(s)
        else:
            units.append([s])
    out_units = []
    for j, us in enumerate(units):
        a, b = us[0]['span'][0], us[-1]['span'][1]
        types = [s['type'] for s in us]
        if DIVINE in types:
            kind, label = DIVINE, '+'.join(dict.fromkeys(types))
        elif CUT_TYPES & set(types):
            kind, label = CUT, None
        else:
            kind = FIXED
            label = '+'.join(dict.fromkeys(types))
        for s in us:
            s['unit'] = j
        text = word[offs[a][0]:offs[b - 1][1]] if kind == CUT else ''.join(s['text'] for s in us)
        out_units.append(dict(text=text, kind=kind, label=label,
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
    if L == 'ا' and not mk and b - a > 1 and FATHATAN in toks[b - 2][1]:
        return 'نصب'                                   # يُسْرًا: ألف تنوين النصب
    if L == 'ن' and b - a > 2:
        # العلامة بالحرف (جمع المذكر السالم والمثنى): الواو والألف رفع، والياء جر أو نصب
        W, wm = toks[b - 2]
        pm = toks[b - 3][1]
        if W == 'و' and not wm and DAMMA in pm and FATHA in mk:
            return 'رفع'
        if W == 'ا' and not wm and KASRA in mk:
            return 'رفع'
        if W == 'ي' and (not wm or wm == {SUKUN}) and (KASRA in pm and FATHA in mk or FATHA in pm and KASRA in mk):
            return YA_CASE
        if W in ('و', 'ي') and FATHA in mk:
            return None
    for m, case in MARK_CASE.items():
        if m in mk:
            return case
    return None

# الاسم المؤخَّر: إنّ وأخواتها وكان وأخواتها قد يليها خبرٌ شبه جملة مقدَّم (فَإِنَّ مَعَ ٱلْعُسْرِ يُسْرًا،
# لَيْسَ كَمِثْلِهِۦ شَىْءٌ)، فيُتجاوَز الظرف أو الجار مع ما بعده إلى الاسم
DEFERRED_NAME = {'2', '10', '11'}
# مشكولةً، وآخرها بلا حركة: حركة الإعراب فيه غير محدَّدة (قَبْلَ، قَبْلِ، قَبْلُ)؛ فلا يُعدّ «قِبَلَ» ولا «خِلَٰفٍ» ظرفاً
ZURUF = ('مَع', 'عِنْد', 'لَدَى', 'لَدَىٰ', 'لَدُن', 'فَوْق', 'تَحْت', 'بَيْن', 'قَبْل', 'بَعْد', 'أَمَام', 'خَلْف', 'وَرَاء',
         'دُون', 'حَوْل', 'قُدَّام', 'إِزَاء', 'تِلْقَاء')

def _tawkid_lam(slot):
    """اللام المفتوحة قبل الاسم الظاهر لام توكيد (مزحلقة) لا جارّة: إِنَّ فِى ذَٰلِكَ لَءَايَةً"""
    return slot['type'] == AMIL and slot['text'] == 'ل' + FATHA

def _kaf_zaida(seg, si):
    """كاف التشبيه الداخلة على «مثل» زائدة للتوكيد (لَيْسَ كَمِثْلِهِۦ شَىْءٌ): ترجيح صاحب النظرية"""
    slots = seg['slots']
    return (slots[si]['type'] == AMIL and vform_match(slots[si]['text'], ['كَ']) and si + 1 < len(slots)
            and slots[si + 1]['text'].startswith('م' + KASRA + 'ث' + SUKUN + 'ل'))   # مِثْل لا مَثَل (كَمَثَلِ تشبيه)

def _first_content(seg):
    return next((t['index'] for t in seg['slots']
                 if t['role'] not in ('conj', 'article', 'proclitic') and not _tawkid_lam(t)), None)

def _skip_semi_clause(segs, tg):
    """الهدف ظرف أو جار → الكلمة بعد مجروره أو المضاف إليه؛ وإلا الهدف نفسه"""
    wi, si = tg
    seg, slot = segs[wi], segs[wi]['slots'][si]
    is_jar = slot['type'] == AMIL and all(g == '1' for _, g in slot['operators'])
    with_pron = slot['type'] == STEM and any(vform_match(slot['text'], [z + p]) for z in ZURUF for p in PRON_SUFFIXES)
    is_zarf = slot['type'] == STEM and (vform_match(slot['text'], ZURUF) or with_pron)       # مَعَ، مَعَهُۥ
    if not (is_jar or is_zarf):
        return tg
    rest_in_word = with_pron or any(t['index'] > si for t in seg['slots'])   # مجرور أو مضاف إليه في الكلمة
    nxt = wi + 1 if rest_in_word else wi + 2
    if nxt < len(segs):
        fc = _first_content(segs[nxt])
        if fc is not None:
            return nxt, fc
    return tg

def _after_article(seg, si):
    return si > 0 and seg['slots'][si - 1]['role'] == 'article'

def _target(segs, wi, si):
    """المعمول: الخانة التالية في الكلمة، أو أول خانة في الكلمة التالية؛ وأل لا تكون معمولاً
    بل الجذع بعدها (بِٱلْعَدْلِ: بِ ← عَدْلِ)، ولا حرف العطف في أول الكلمة التالية"""
    for t in segs[wi]['slots'][si + 1:]:
        if t['role'] != 'article':
            return wi, t['index']
    if wi + 1 < len(segs):
        for t in segs[wi + 1]['slots']:
            if t['role'] not in ('conj', 'article', 'proclitic'):
                return wi + 1, t['index']
    return None

def relate(segs, cands):
    rels = []
    for c in cands:
        if c.get('status') == BLOCKED:
            continue
        seg = segs[c['word_index']]
        si = next((s['index'] for s in seg['slots']
                   if s['type'] == AMIL and (c['operator'], c['group']) in s['operators']), None)
        if si is None:
            continue
        r = dict(operator=c['operator'], group=c['group'], word_index=c['word_index'], slot=si,
                 target=None, expected=EXPECTED.get(c['group']), observed=None, consistent=None, note=None)
        if c['group'] == '7' and vform_match(c['operator'], NO_JAZM):
            r.update(expected=None, note='لا تجزم (الفهرس)')
        if c.get('kaffa'):
            r.update(expected=None, note='مكفوفة بما: لا تعمل')
            rels.append(r)
            continue
        tg = _target(segs, c['word_index'], si)
        slot = seg['slots'][si]
        if slot['type'] == AMIL and _kaf_zaida(seg, si):
            ts = seg['slots'][si + 1]
            r.update(expected='جر', note='الكاف زائدة للتوكيد قبل «مثل»: جرٌّ لفظي (ترجيح صاحب النظرية)',
                     target=dict(word_index=c['word_index'], slot=si + 1, text=ts['text'], type=ts['type']))
            obs = _observed(seg, ts)
            r.update(observed=obs, consistent=(obs == 'جر') if obs else None, zaida=True)
            rels.append(r)
            continue
        if tg and _tawkid_lam(slot) and segs[tg[0]]['slots'][tg[1]]['type'] != MABNI:
            ts = segs[tg[0]]['slots'][tg[1]]
            r.update(expected=None, note='اللام المفتوحة قبل الاسم الظاهر لام توكيد: لا تعمل',
                     target=dict(word_index=tg[0], slot=tg[1], text=ts['text'], type=ts['type']))
            rels.append(r)
            continue
        if tg and _kaf_zaida(segs[tg[0]], tg[1]) and c['group'] in DEFERRED_NAME:
            # لَيْسَ كَمِثْلِهِۦ شَىْءٌ: الكاف زائدة، و«مِثْل» خبر ليس مقدَّم، والاسم مؤخَّر
            khabar = segs[tg[0]]['slots'][tg[1] + 1]['text']
            r['khabar'] = dict(word_index=tg[0], slot=tg[1] + 1, text=khabar)
            tg = _skip_semi_clause(segs, tg)
            r['note'] = f'الكاف زائدة للتوكيد، و«{khabar}» خبر مقدَّم في محلّ نصب، والاسم مؤخَّر (ترجيح صاحب النظرية)'
        elif tg and c['group'] in DEFERRED_NAME:
            tg2 = _skip_semi_clause(segs, tg)
            if tg2 != tg:
                tg = tg2
                r['note'] = 'شبه جملة مقدَّمة، والاسم مؤخَّر بعدها'
        if tg and tg[0] == c['word_index'] and segs[tg[0]]['slots'][tg[1]]['text'] == 'تْ':
            tg = _target(segs, tg[0], tg[1])    # فَكَانَتْ: تاء التأنيث ليست المعمول
        if tg:
            ts = segs[tg[0]]['slots'][tg[1]]
            r['target'] = dict(word_index=tg[0], slot=tg[1], text=ts['text'], type=ts['type'])
            if ts['type'] == MABNI and r['expected'] == 'جزم':
                r['note'] = 'المعمول مبنيٌّ ليس فعلاً: لا يُجزم'   # إِنۡ هُوَ: الضمير لا يكون في محلّ جزم
            elif ts['type'] == MABNI:
                r['observed'] = 'محلاً'
            elif ts['type'] == AMIL:
                r['note'] = 'المعمول يبدأ بعامل: جملة أو مصدر مؤوَّل'
            elif ts['type'] == STEM and not _after_article(segs[tg[0]], tg[1]) and \
                    ((m := stem_info(ts['text']))['pos'] == 'verb' or
                     (m['kind'] == 'mudari' and (c['group'] in ('5', '6', '7') or
                                                 vform_match(c['operator'], ('حَتَّى', 'لِ'))))):   # حتى ولام التعليل قبل المضارع
                r['target'].update(pos='verb', kind=m['kind'])
                if c['group'] == '1':
                    r.update(expected='نصب', note='الجار قبل المضارع: النصب بأن مضمرة')
                if m['kind'] == 'mudari' and c['group'] in VERB_CHECKED and r['expected']:
                    r['observed'] = m['mood']
                    if m['mood'] == 'حذف النون':
                        r['consistent'] = r['expected'] in ('نصب', 'جزم')
                    elif m['mood'] in ('رفع', 'نصب', 'جزم'):
                        r['consistent'] = m['mood'] == r['expected']
                elif m['kind'] in ('madi', 'amr'):
                    r['note'] = 'المعمول فعل ماضٍ' if m['kind'] == 'madi' else 'المعمول فعل أمر'
            elif r['expected'] and c['group'] in CHECKED:
                obs = _observed(segs[tg[0]], ts)
                r['observed'] = obs
                if c['group'] == '10' and r['expected'] == 'رفع' and obs == 'نصب':
                    # كَانَ مِيقَٰتًا: المنصوب بعدها خبرها، واسمها مستتر أو مؤخَّر
                    r.update(expected='نصب', consistent=True, khabar_only=True,
                             note='المنصوب بعدها خبرها، واسمها ضمير مستتر أو مؤخَّر')
                elif obs == r['expected'] or obs == YA_CASE and r['expected'] in ('جر', 'نصب'):
                    r['consistent'] = True
                elif obs and not ((r['expected'], obs) in (('جر', 'نصب'), ('نصب', 'جر'))):
                    r['consistent'] = False      # الجر بالفتحة (الممنوع من الصرف) والنصب بالكسرة (جمع المؤنث) لا يُحكم فيهما
        rels.append(r)
    for r in rels:
        r['role'] = _role(r)
    return rels


# ---------- الإعراب: دور المعمول بعبارة النحاة ----------
NAME_OF = {'2': 'اسم', '10': 'اسم', '11': 'اسم'}

def _role(r):
    """→ عبارة إعراب المعمول، أو None إن لم يكن للعامل أثر إعرابي معيَّن"""
    t, op, exp = r['target'], r['operator'], r['expected']
    if t is None or exp is None or t['type'] == AMIL:
        return None
    mahall = r['observed'] == 'محلاً'
    if t.get('pos') == 'verb':
        if r['group'] == '1':
            text = f'مضارع منصوب بأن مضمرة بعد «{op}»'
        else:
            verb = {'نصب': 'منصوب', 'جزم': 'مجزوم'}.get(exp, exp)
            if r['observed'] is not None:
                text = f'مضارع {verb} بـ«{op}»'
            elif t.get('kind') == 'madi':
                text = f'في محلّ {exp} بـ«{op}»'
            else:
                # ماضٍ مبني في محلّه، أو مضارع بعلامة مقدَّرة أو محذوفة (يَخْشَىٰ، يَنتَهِ): لا تُميِّز الكتابة بينهما
                text = f'أثر «{op}» فيه {exp}، ولا علامة ظاهرة في الكتابة'
    elif r['group'] == '1':
        if r.get('zaida'):
            text = 'مجرور لفظاً بالكاف الزائدة'
        else:
            text = f'في محلّ جر بـ«{op}»' if mahall else f'مجرور بـ«{op}»'
    elif r.get('khabar_only'):
        text = f'خبر «{op}» منصوب، واسمها ضمير مستتر أو مؤخَّر'
    elif r['group'] in NAME_OF:
        case = {'نصب': 'منصوب', 'رفع': 'مرفوع'}[exp]
        text = f'في محلّ {exp} اسم «{op}»' if mahall else f'اسم «{op}» {case}'
        if r.get('khabar'):
            text += ' مؤخَّر'
    else:
        return None
    if r['observed'] == 'حذف النون':
        text += f" وعلامة {'جزمه' if exp == 'جزم' else 'نصبه'} حذف النون"
    if r['consistent'] is False:
        text += ' (العلامة المكتوبة تخالف)'
    return text


# ---------- التقطيع على الوحدات التي تُقطَّع ----------
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
    """تقطيع الوحدات التي تُقطَّع وحدها → ناتج بصيغة cv.run (counts، rows، events …)"""
    from collections import Counter
    events, counts = cv.Events(), Counter()
    rows, others, cv_line = [], [], []
    divine_words = []
    for seg in segs:
        wi = seg['word_index']
        if any(u['kind'] == DIVINE for u in seg['units']):
            divine_words.append(wi)
        for u in seg['units']:
            if u['kind'] != CUT:
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
    """كل كلمة بوحداتها: ما يُقطَّع بمقاطعه، وما سواه بوسمه"""
    lines = []
    for seg in segs:
        parts, pats = [], []
        for u in seg['units']:
            if u['kind'] == CUT:
                parts.append(' . '.join(s['syl'] for s in u['syllables']))
                pats += [s['cv'] for s in u['syllables']]
            else:
                parts.append(f"[{u['text']}: {u['label']}]")
        lines.append(f"{seg['word']:<16} {' | '.join(parts):<44} {' '.join(pats)}")
    return '\n'.join(lines)
