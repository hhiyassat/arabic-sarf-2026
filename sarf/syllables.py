# -*- coding: utf-8 -*-
"""
sarf.syllables — المقطع بقوالبه الستة، مبنيّاً من خلايا الجبر بالامتداد المرخَّص: مصدرٌ واحد للمقاطع
في المحلّل (sarf.segment.syllabify_units) وفي الجبر (sarf.algebra.unit_geo).

    M = {CV, CVC, CVV, CVVC, CVVCC, CVCC}، وCVCC وCVVCC في آخر الكلمة وحده (حكم صاحب النظرية)
    Rem_M(u) = {v | uv ∈ M}

ومنه: unit_syllables(text): خلايا الوحدة ومقاطعها وما لم يُبنَ له مقطع، وحركة همزة الوصل في ابتدائها؛
وrender(G): رسم المقطع (الصامت، والحركة أو التنوين، وحرف المد، والسواكن بسكونها).
"""
from collections import Counter

from .chars import FATHA, DAMMA, KASRA, SUKUN, FATHATAN, DAMMATAN, KASRATAN
from .cells import cells_of
from .core import SYLLABLE, Evidence, Obligation, Geo, Trace, extend, close


SYLLABLE_SHAPES = ('CV', 'CVC', 'CVV', 'CVVC', 'CVVCC', 'CVCC')     # M: الأشكال الستة المرخَّصة
WORD_FINAL_ONLY = ('CVCC', 'CVVCC')                                # لا يقعان إلا في آخر الكلمة (حكم صاحب النظرية)


def rem_M(u, word_end=True):
    """Rem_M(u) = {v | uv ∈ M}: البقايا الممكنة للمقطع الجاري u. وإذا لم يكن الموضع آخر الكلمة
    سقط من M ما لا يقع إلا في آخرها (CVCC، CVVCC)"""
    shapes = SYLLABLE_SHAPES if word_end else tuple(x for x in SYLLABLE_SHAPES if x not in WORD_FINAL_ONLY)
    return {m[len(u):] for m in shapes if m.startswith(u)}


def cell_shape(c, first):
    """قراءة الخلية في المقطع: المتحركة صامتٌ ونواة (CV أو CVV)، والساكنة صامتٌ C"""
    if c.H == '∅':
        return 'C'
    return 'CVV' if c.L == 2 else 'CV'


def syllable_next(G):
    """Next_Γ(G) مشتقٌّ من Rem_M: ما يمكن أن يلي المقطع الجاري (بقاياه غير ε)"""
    u = cv(G) if G.A else ''
    return {v for v in rem_M(u) if v}


def cv(G):
    c0 = G.A[0]
    return 'C' + ('VV' if c0.L == 2 else 'V') + 'C' * (len(G.A) - 1)


def syllabify(cells, base_id, T, word_end=True):
    """المقاطع من الخلايا بالامتداد المرخَّص: تُضاف الخلية x إلى المقطع الجاري u إذا كان
    Rem_M(u·x) ≠ ∅ (و CVCC/CVVCC لا تُقبل إلا والخلية آخر الكلمة)؛ ويُغلق المقطع بشهادتَي الإكمال
    (u ∈ M) والحدّ (Rem_M(u·x) = ∅ للخلية التالية x، أو لا خلية بعده).
    → (المقاطع المغلقة، الخلايا التي لم يُبنَ لها مقطع مع السبب)"""
    out, stray = [], []
    i, n = 0, len(cells)
    while i < n:
        G = Geo(f'{base_id}.σ{len(out)}', (SYLLABLE, 'مقطع'),
                Omega=[Obligation('نواة متحركة')])
        c = cells[i]
        x = cell_shape(c, True)
        # الساكنة في أول المقطع: Rem_M(C) يطلب V بعدها، وكل خلية تالية تبدأ بصامت، فلا تبلغ M: لا مقطع
        if x == 'C':
            stray.append((c, 'لا يُبتدأ بساكن'))
            i += 1
            continue
        extend(G, c, None, Evidence('الخلية متحركة', [f'الحركة {c.H}', f'Rem_M({x}) ≠ ∅'],
                                    [('الابتداء بساكن', 'الحركة مكتوبة')]),
               T, discharge=['نواة متحركة'])
        i += 1
        why_end = None
        while i < n:
            u = cv(G)
            x = cell_shape(cells[i], False)
            last = i == n - 1 and word_end
            # الحرف قبل المشدَّد مكتوبٌ بلا حركة، والمشدَّد خليتان (حكم صاحب النظرية: عَ.بَدْتْ.تُمْ):
            # فالخاتمتان داخل الكلمة كما كُتبتا، لا بالأداء
            written_cc = x == 'C' and cells[i].O.get('role') == 'شدة: الأول' and G.A[-1].H == '∅' and len(G.A) > 1
            r = rem_M(u + x, word_end=last or written_cc)
            if x != 'C' or not r:
                why_end = (u, x, last)
                break
            extend(G, cells[i], 'خاتمة', Evidence('الخلية ساكنة', [f'Rem_M({u}·C) = {{{", ".join(sorted(v or "ε" for v in r))}}}']), T)
            i += 1
        u = cv(G)
        ec = Evidence('قالب المقطع', [u, f'{u} ∈ M'], [('مقطع بلا نواة', 'النواة الخلية الأولى')])
        if i == n:
            eb = Evidence('نهاية الوحدة', ['لا خلية بعدها'])
        elif why_end[1] != 'C':
            eb = Evidence('الخلية التالية متحركة', [f'Rem_M({u}·{why_end[1]}) = ∅: المتحرك يبدأ مقطعاً'])
        elif not why_end[2] and rem_M(u + 'C') and why_end[1] == 'C':
            eb = Evidence('CVCC وCVVCC لا يقعان إلا في آخر الكلمة', [f'{u}·C ليس آخر الكلمة'])
        else:
            eb = Evidence('المقطع مشبَع', [f'Rem_M({u}) = {{ε}}'])
        close(G, ec, eb, T)
        out.append(G)
    return out, stray


# ---------- رسم المقطع، وحركة همزة الوصل، ومقاطع الوحدة ----------
AR_V = {'a': FATHA, 'u': DAMMA, 'i': KASRA}
AR_TANWIN = {'a': FATHATAN, 'u': DAMMATAN, 'i': KASRATAN}
AR_MADD = {'a': 'ا', 'u': 'و', 'i': 'ي'}


def render(G):
    """رسم المقطع من خلاياه: الصامت الأول بحركته (أو تنوينه) وحرف مدّه، ثم الخواتم بسكونها"""
    c0 = G.A[0]
    r = c0.C + (AR_TANWIN if c0.O.get('tanwin') else AR_V)[c0.H] + (AR_MADD[c0.H] if c0.L == 2 else '')
    return r + ''.join(c.C + SUKUN for c in G.A[1:])


def wasl_vowel(text):
    """حركة همزة الوصل في ابتداء الوحدة، بقاعدة المقطِّع السابق نفسها (sarf.syllabify.resolve):
    الفتح قبل لام «أل» (القمرية والشمسية)، والضم إن سكن الأول وضُمّ الثاني ضمةً قصيرة (اُكْتُبْ)، وإلا الكسر.
    → None إن لم تبدأ الوحدة بهمزة وصل.
    والقاعدة خطّية لا صرفية، فتخطئ حيث الضمة عارضة أو طويلة (اِدْعُوا والصواب اُدْعُوا): مسألةٌ مسجَّلة (S06.04)"""
    cells, toks = cells_of(text, 'w', 'a')
    if not cells or cells[0].O.get('role') != 'همزة وصل':
        return None
    if len(toks) > 1 and toks[1][0] == 'ل':
        return 'a'
    if len(cells) > 2 and cells[1].H == '∅' and cells[2].H == 'u' and cells[2].L == 1 and not cells[2].O.get('tanwin'):
        return 'u'
    return 'i'


def cell_events(cells, orphans=()):
    """أدوار الخلايا معدودةً بأسمائها: ما يجري على الرسم في بناء الخلايا (همزة الوصل، والشدة، والمد، والتنوين،
    وما لا يُنطق بسببه)"""
    ev = Counter()
    for c in cells:
        if c.O.get('role'):
            ev[c.O['role']] += 1
        if c.O.get('madd'):
            ev['مدّ: ' + c.O['madd']] += 1
        if c.O.get('tanwin'):
            ev['تنوين'] += 1
        for _, why in c.O.get('silent') or []:
            ev['لا يُنطق: ' + why] += 1
    for _, why in orphans:
        ev['لا يُنطق بلا خلية: ' + why] += 1
    return ev


def unit_syllables(text, base_id='u', T=None, word_end=True):
    """→ (الخلايا، المقاطع المغلقة، الخلايا التي لم يُبنَ لها مقطع مع السبب، الأحداث)"""
    T = T if T is not None else Trace()
    cells, _ = cells_of(text, base_id, wasl_vowel(text))
    orphans = list(cells_of.orphans)
    sylls, stray = syllabify(cells, base_id, T, word_end=word_end)
    return cells, sylls, stray, cell_events(cells, orphans)
