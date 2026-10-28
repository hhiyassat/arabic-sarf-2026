# -*- coding: utf-8 -*-
"""
sarf.algebra — الجبر اللساني: هندسة ذات أنواع، تُبنى تكرارياً بالامتداد المرخَّص، وتُغلق بشهادتَي
الإكمال والحدّ، ثم تدخل مكوّناً في المستوى الأعلى (تجربة على الفرع experiment).

المستويات:  خلية ≺ مقطع ≺ وحدة لفظية ≺ جملة ≺ فقرة ≺ موضوع
وفي المصحف: الجملة موضعها الآية، والفقرة السورة، والموضوع المصحف (حدودها ثابتة بالرسم).

التعريفات:
    الخلية   s = ⟨id, C, H, L, O⟩       الصامت، والحركة a/u/i/∅، والطول 1/2، وأثر الرسم
    الوحدة   G⁽ᵏ⁾ = ⟨id, τ, A, B, Θ, Ω, O⟩ والأثر T (سجل العمليات وأدلتها) مستقل
    الدليل   e = سببٌ ثابت + شروطٌ متحققة + موانعُ ثبت انتفاؤها (لا «لم نجد مانعاً»)
    الامتداد G' = Extend_{k,r,e}(G, x)،   Ω(G') = (Ω(G) ∖ D_e) ∪ N_e
    الإغلاق  Ĝ = Close_k(G; e_c, e_b)     لا يكون إلا بشهادتَي الإكمال والحدّ، وΩ خالية من اللازم

والقانون التكراري: G⁽ᵏ⁾ₙ₊₁ = Extend_k(G⁽ᵏ⁾ₙ, Ĝ⁽ᵏ⁻¹⁾ₙ₊₁)، وما لم يُغلق لا يدخل المستوى الأعلى،
بل يبقى معلَّقاً في O['pending'] بسبب تأجيله، فلا يضيع وقوعٌ (المبرهنة الأولى).
"""
from dataclasses import dataclass, field

from .chars import (FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN,
                    MADDA_MARK, DAGGER_ALIF, letters)

# طبقتان على النص نفسه تشتركان في الخلايا:
#   اللغوية: خلية ≺ مقطع ≺ وحدة لفظية ≺ جملة ≺ وحدة خطابية ≺ خطاب السورة — حدودها بالعلاقات وشروط الاكتمال
#   المصحفية: خلية ≺ كلمة ≺ آية ≺ سورة ≺ مصحف — حدودها مثبتة في الرسم
# والآية لا تُغلق الجملة، والجملة لا تُغلق الآية؛ وتربطهما Location(J) = مواضع كلمات J في الآيات
LEVELS = ['خلية', 'مقطع', 'وحدة لفظية', 'جملة', 'وحدة خطابية', 'خطاب']
CELL, SYLLABLE, UNIT, SENTENCE, DISCOURSE, SPEECH = range(6)
PARAGRAPH, TOPIC = DISCOURSE, SPEECH
M_WORD, M_AYAH, M_SURAH, M_MUSHAF = 'كلمة', 'آية', 'سورة', 'مصحف'

H_OF = {FATHA: 'a', DAMMA: 'u', KASRA: 'i', FATHATAN: 'a', DAMMATAN: 'u', KASRATAN: 'i'}
MADD_OF = {'a': 'اى', 'u': 'و', 'i': 'ي'}
HAMZA = {'أ': 'ء', 'إ': 'ء', 'ؤ': 'ء', 'ئ': 'ء', 'ء': 'ء'}


# ---------- الدليل والالتزام ----------
@dataclass
class Evidence:
    """e = ⟨السبب، الشروط، الموانع المنتفية⟩. absent: [(المانع، برهان انتفائه)]"""
    cause: str
    conditions: list = field(default_factory=list)
    absent: list = field(default_factory=list)

    def valid(self):
        return bool(self.cause) and all(c for c in self.conditions) and all(p and proof for p, proof in self.absent)

    def text(self):
        out = 'السبب: ' + self.cause
        if self.conditions:
            out += ' | الشروط: ' + '، '.join(self.conditions)
        if self.absent:
            out += ' | انتفى: ' + '، '.join(f'{p} ({proof})' for p, proof in self.absent)
        return out


@dataclass
class Obligation:
    """التزامٌ في Ω: لازمٌ (required) لا تُغلق الوحدة قبل استيفائه، أو جائز"""
    name: str
    required: bool = True
    met: bool = False
    ev: Evidence = None
    reason: str = ''
    units: list = field(default_factory=list)     # الوحدات التي يخصّها الالتزام (لتعيين جملته)


# ---------- الخلية ----------
@dataclass
class Cell:
    id: str
    C: str            # الصامت (الهمزات موحَّدة ء)
    H: str            # a / u / i / ∅
    L: int = 1        # 2: بعدها حرف مدّ من جنسها
    O: dict = field(default_factory=dict)    # tok: موضع الرسم، glyph، role، silent: [مواضع لا تُنطق]

    def key(self):
        return (self.C, self.H, self.L)

    def show(self):
        return f"⟨{self.C},{self.H}{'ː' if self.L == 2 else ''}⟩"


# ---------- الهندسة ----------
class CloseError(Exception):
    pass


@dataclass
class Geo:
    id: str
    tau: tuple                    # (المستوى، النوع)
    A: list = field(default_factory=list)
    B: list = field(default_factory=list)       # [(العلاقة، من، إلى، الدليل)]
    Theta: dict = field(default_factory=dict)
    Omega: list = field(default_factory=list)
    O: dict = field(default_factory=dict)
    closed: bool = False
    ec: Evidence = None
    eb: Evidence = None

    @property
    def level(self):
        return self.tau[0]

    def open_required(self):
        return [o for o in self.Omega if o.required and not o.met]


class Trace(list):
    """الأثر T: سجل العمليات وأدلتها، مستقل عن الهندسة"""
    def log(self, op, node, **kw):
        self.append(dict(op=op, node=node.id, level=node.level, **kw))


def extend(G, x, rel, ev, T, discharge=(), new=()):
    """G' = Extend_{k,r,e}(G, x): لا امتداد بلا دليل مكتمل؛ ثم Ω(G') = (Ω(G) ∖ D_e) ∪ N_e"""
    if not isinstance(ev, Evidence) or not ev.valid():
        raise CloseError(f'امتداد بلا دليل مكتمل في {G.id}')
    if isinstance(x, Geo) and not x.closed:
        raise CloseError(f'{x.id} غير مغلق: لا يدخل مكوّناً في {G.id}')
    G.A.append(x)
    if rel:
        G.B.append((rel, len(G.A) - 2 if len(G.A) > 1 else None, len(G.A) - 1, ev))
    for name in discharge:
        for o in G.Omega:
            if o.name == name and not o.met:
                o.met, o.ev = True, ev
    G.Omega.extend(new)
    T.log('Extend', G, rel=rel, child=getattr(x, 'id', None), ev=ev.text())
    return G


def close(G, ec, eb, T):
    """Ĝ = Close_k(G; e_c, e_b): شهادتا الإكمال والحدّ لازمتان، ولا التزام لازم مفتوح (المبرهنة الرابعة)"""
    if ec is None or eb is None or not ec.valid() or not eb.valid():
        raise CloseError(f'{G.id}: لا إغلاق بلا شهادتَي الإكمال والحدّ')
    if G.open_required():
        raise CloseError(f'{G.id}: التزام لازم مفتوح: ' + '، '.join(o.name for o in G.open_required()))
    G.closed, G.ec, G.eb = True, ec, eb
    T.log('Close', G, ec=ec.text(), eb=eb.text())
    return G


def defer(G, T, reason):
    T.log('Defer', G, reason=reason)
    G.O['deferred'] = reason
    return G


# ---------- المستوى 0: الخلايا من الرسم ----------
def cells_of(text, base_id, wasl_vowel=None):
    """خلايا الوحدة من رسمها المطبَّع، ومعها كل حرفٍ لا يُنطق في O['silent'] لخليةٍ مجاورة.
    → (الخلايا، رموز الرسم [(الحرف، العلامات)])"""
    toks = letters(text)
    out = []
    pending_silent = []
    for j, (L, m) in enumerate(toks):
        prev = out[-1] if out else None
        nxt = toks[j + 1] if j + 1 < len(toks) else None
        role = None
        # همزة الوصل أول الوحدة: تُنطق ابتداءً (اصطلاح المقطِّع: كل خانة تبدأ بما يُبتدأ به)
        if L == 'ا' and j == 0 and not m and nxt is not None:
            v = wasl_vowel or ('a' if nxt[0] == 'ل' else 'u' if len(toks) > 2 and DAMMA in toks[2][1] else 'i')
            out.append(Cell(f'{base_id}.{len(out)}', 'ء', v, 1, dict(tok=[j], glyph='ا', role='همزة وصل')))
            continue
        if L == 'آ':
            out.append(Cell(f'{base_id}.{len(out)}', 'ء', 'a', 2, dict(tok=[j], glyph=L, role='همزة ومدّة')))
            continue
        # ألف الوصل بعد سابقةٍ من حرف واحد (لَّٱصۡطَفَىٰ، وَّٱسۡتَغۡنَى): لا تُنطق، وما بعدها ساكن
        if L == 'ا' and not m and len(out) == 1 and out[0].C in 'لوفبك' and out[0].H == 'a' and \
                nxt is not None and SUKUN in nxt[1]:
            prev.O.setdefault('silent', []).append((j, 'ألف وصل بعد السابقة')); prev.O['tok'].append(j)
            continue
        # حرف المد: يُطيل حركة ما قبله (الألف بعد الفتح، والواو بعد الضم، والياء بعد الكسر)
        if not m and prev is not None and prev.L == 1 and not prev.O.get('tanwin') and \
                prev.H in MADD_OF and L in MADD_OF[prev.H]:
            prev.L = 2
            prev.O['tok'].append(j); prev.O['madd'] = L
            continue
        # ما لا يُنطق: الألف الفارقة، وألف تنوين النصب، واللام الشمسية العارية قبل المشدَّد
        if not m and (L in 'اى' or L == 'ل' and nxt is not None and SHADDA in nxt[1]):
            why = 'لام شمسية' if L == 'ل' else 'ألف بعد التنوين' if prev is not None and prev.O.get('tanwin') else 'ألف لا تُنطق'
            if prev is not None:
                prev.O.setdefault('silent', []).append((j, why)); prev.O['tok'].append(j)
            else:
                pending_silent.append((j, why))
            continue
        # الواو أو الياء تحمل الخنجرية بلا حركة: كرسيٌّ للألف (ٱلصَّلَوٰةَ = صَلَاة): يُطيل ما قبله ولا يُنطق صامتاً
        if DAGGER_ALIF in m and not m & {FATHA, DAMMA, KASRA, SUKUN, SHADDA} and L in 'وي' and \
                prev is not None and prev.H == 'a':
            prev.L = 2
            prev.O['tok'].append(j); prev.O['madd'] = L + 'ٰ'
            continue
        C = HAMZA.get(L, L)
        H = next((H_OF[x] for x in (FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN) if x in m), '∅')
        tanwin = bool(m & {FATHATAN, DAMMATAN, KASRATAN})
        if SHADDA in m and out:
            out.append(Cell(f'{base_id}.{len(out)}', C, '∅', 1, dict(tok=[j], glyph=L, role='شدة: الأول')))
            role = 'شدة: الثاني'
        elif SHADDA in m:
            role = 'شدة أول الوحدة: لا تُكرَّر'
        c = Cell(f'{base_id}.{len(out)}', C, H, 1, dict(tok=[j], glyph=L, role=role, tanwin=tanwin))
        if DAGGER_ALIF in m:
            c.H, c.L = 'a', 2
            c.O['madd'] = 'ٰ'
        if pending_silent:
            c.O['silent'] = pending_silent; c.O['tok'] = [s for s, _ in pending_silent] + c.O['tok']
            pending_silent = []
        out.append(c)
    if pending_silent:
        # حرفٌ لا يُنطق ولا خلية في وحدته (ى وحدها بعد تنوينٍ في الوحدة السابقة): يُحفظ وقوعاً بلا خلية
        cells_of.orphans = pending_silent
    else:
        cells_of.orphans = []
    return out, toks


def spans(text):
    """مواضع رموز الرسم: [(البداية، النهاية)] لكل حرفٍ بعلاماته كما كُتبت"""
    from .chars import MARKS, TATWEEL
    out = []
    for i, ch in enumerate(text):
        if ch in MARKS or ch == TATWEEL:
            if out:
                out[-1][1] = i + 1
            continue
        out.append([i, i + 1])
    return [tuple(x) for x in out]


def render_cells(cells, text, orphans=()):
    """Render: الرسم من الخلايا بروابط O (ومن الوقوعات التي لا خلية لها): يُنسخ كل موضع رسمٍ كما كُتب،
    مرة واحدة. → (النص، المواضع المغطّاة بترتيبها)"""
    sp = spans(text)
    seen = [j for j, _ in orphans]
    for c in cells:
        for j in c.O['tok']:
            if j not in seen:
                seen.append(j)
    return ''.join(text[sp[j][0]:sp[j][1]] for j in sorted(seen)), seen


# ---------- المستوى 1: المقطع بقوالبه الستة ----------
def syllable_next(G):
    """Next_Γ(G): ما يرخَّص إضافته إلى المقطع: خلية متحركة إن كان فارغاً، وإلا خلية ساكنة ما دامت
    الخواتم أقل من اثنتين (CV، CVV، CVC، CVVC، CVCC، CVVCC)"""
    if not G.A:
        return 'onset'
    codas = sum(1 for c in G.A[1:])
    return 'coda' if codas < 2 else None


def cv(G):
    c0 = G.A[0]
    return 'C' + ('VV' if c0.L == 2 else 'V') + 'C' * (len(G.A) - 1)


def syllabify(cells, base_id, T):
    """المقاطع من الخلايا بالامتداد المرخَّص، وكل مقطع يُغلق بشهادتَي الإكمال والحدّ.
    → (المقاطع المغلقة، الخلايا التي لم يُبنَ لها مقطع مع السبب)"""
    out, stray = [], []
    i, n = 0, len(cells)
    while i < n:
        G = Geo(f'{base_id}.σ{len(out)}', (SYLLABLE, 'مقطع'),
                Omega=[Obligation('نواة متحركة')])
        c = cells[i]
        if c.H == '∅':
            stray.append((c, 'لا يُبتدأ بساكن'))     # بلا دليل امتداد: لا يُبنى مقطع ولا يُغلق
            i += 1
            continue
        extend(G, c, None, Evidence('الخلية متحركة', [f'الحركة {c.H}'], [('الابتداء بساكن', 'الحركة مكتوبة')]),
               T, discharge=['نواة متحركة'])
        i += 1
        while i < n and syllable_next(G) == 'coda' and cells[i].H == '∅':
            extend(G, cells[i], 'خاتمة', Evidence('الخلية ساكنة', [f'الخواتم {len(G.A) - 1} < 2']), T)
            i += 1
        ec = Evidence('قالب المقطع', [cv(G)], [('مقطع بلا نواة', 'النواة الخلية الأولى')])
        if i == n:
            eb = Evidence('نهاية الوحدة', ['لا خلية بعدها'])
        elif cells[i].H != '∅':
            eb = Evidence('الخلية التالية متحركة', ['المتحرك يبدأ مقطعاً، فلا يكون خاتمة'])
        else:
            eb = Evidence('الخواتم استوفت حدّها', ['خاتمتان'])
        close(G, ec, eb, T)
        out.append(G)
    return out, stray


# ---------- الإسقاطات والمساواة ----------
def flatten(G):
    """Flatten: الخلايا في الترتيب، من أي مستوى"""
    if isinstance(G, Cell):
        return [G]
    out = []
    for x in G.A:
        out += flatten(x)
    for x in G.O.get('pending', []):
        out += flatten(x)
    return out


def proj_root(G):
    return G.Theta.get('R')


def proj_cells(G):
    return [c.key() for c in flatten(G)]


def equal_under(proj, G1, G2):
    """المساواة من جهة: Root(كَتَبَ) = Root(كَاتَبَ)، وCells(كَتَبَ) ≠ Cells(كَاتَبَ)"""
    return proj(G1) == proj(G2)


# ---------- المستوى 2: الوحدة اللفظية، وRealize(R, P, F) ----------
WEAK = 'وىيءا'


def realize_skeleton(root, cls, kind):
    """Realize(R, P): هيكل الصوامت الذي يحققه الجذر في قالب الوزن: [(الصامت، الوسم)].
    R ← الأصل بترتيبه، وX تكرار الأصل السابق (الشدة)، و«ا» في القالب طولٌ لا صامت"""
    from .root import PAST, MUDARI, AMR
    tmpl = {'madi': PAST, 'mudari': MUDARI, 'amr': AMR}[kind].get(cls)
    if tmpl is None:
        return None
    out, k = [], 0
    for t in tmpl:
        if t == 'R':
            out.append((HAMZA.get(root[k], root[k]), f'r{k + 1}'))
            k += 1
        elif t == 'X':
            out.append((out[-1][0], f'r{k}'))
        elif t == 'ا':
            out.append(('ː', 'طول'))
        else:
            out.append((HAMZA.get(t, t), f'زائد:{t}'))
    return out


def align_alpha(cells, root, cls, kind):
    """α: الخلايا ↦ مواقع الجذر والزوائد، بمطابقة هيكل Realize على الخلايا بالترتيب.
    الأصل المعتل (و ي ء) يجوز ألا يقابله صامت: يُسجَّل إعلالاً (حذفاً أو قلباً إلى مدّ)؛
    وما قبل الهيكل سابقة (حرف المضارعة، همزة الوصل)، وما بعده لاحقة.
    → (α، العمليات) أو (None، السبب)"""
    sk = realize_skeleton(root, cls, kind)
    if sk is None:
        return None, f'لا قالب للوزن {cls} في {kind}'
    alpha = [None] * len(cells)
    ops = []
    i = 0
    pre = []
    while i < len(cells) and (cells[i].O.get('role') == 'همزة وصل' or kind == 'mudari' and not pre and i == 0):
        alpha[i] = 'وصل' if cells[i].O.get('role') == 'همزة وصل' else 'سابقة'
        pre.append(i); i += 1
    for C, lab in sk:
        if C == 'ː':
            if i == 0 or cells[i - 1].L != 2:
                return None, f'القالب يقتضي طولاً بعد {lab} ولا مدّ في الخلية'
            ops.append('الألف طول')
            continue
        if i < len(cells) and cells[i].C == C:
            alpha[i] = lab; i += 1
            continue
        if lab.startswith('زائد:ت') and i < len(cells) and cells[i].C in 'طد':
            alpha[i] = lab; ops.append(f'إبدال ت ← {cells[i].C}'); i += 1
            continue
        if lab.startswith('r') and C in WEAK:
            # فاء المثال في افتعل تُقلب تاءً وتُدغم (ٱتَّقَى ← وقي)
            if lab == 'r1' and cls == 'VIII' and i < len(cells) and cells[i].C == 'ت':
                alpha[i] = lab; ops.append('إبدال و ← ت'); i += 1
                continue
            ops.append(f'إعلال {lab} ({C}): ' + ('قلب إلى مدّ' if i and cells[i - 1].L == 2 else 'حذف'))
            continue
        return None, f'لا تقابل خليةٌ {lab} «{C}» في الموضع {i}'
    for k in range(i, len(cells)):
        alpha[k] = 'لاحقة'
    if not any(a and a.startswith('r') for a in alpha):
        return None, 'لا أصل مقابَلاً'
    return alpha, ops


def unit_geo(a, wi, ui, base_id, T, governed_info=None):
    """الوحدة اللفظية: تُبنى من مقاطعها المغلقة (أو من خلاياها إن كانت مدخلاً معجمياً لا يُقطَّع)،
    وتُغلق بشهادة الهوية: مدخلٌ معجمي (عامل، مبني، لفظ الجلالة) أو Realize(R, P, F) مطابقاً للخلايا"""
    from .affix import stem_info
    seg = a['segments'][wi]
    u = seg['units'][ui]
    slots = [seg['slots'][k] for k in u['slots']]
    text = u['text']
    first_vowel = None
    if u['kind'] == 'cut' and u['syllables']:
        c0, _ = cells_of(u['syllables'][0]['syl'], 'tmp')
        first_vowel = c0[0].H if c0 else None
    cells, toks = cells_of(text, base_id, first_vowel)
    orphans = cells_of.orphans
    # كل خلية ↦ خانتها، بمواضع الرسم: الخانات متتالية في نص الوحدة
    bounds, acc = [], 0
    for sl in slots:
        n = len(letters(sl['text']))
        bounds.append((acc, acc + n, sl['type']))
        acc += n
    for c in cells:
        j = c.O['tok'][-1]
        c.O['slot'] = next((t for a0, a1, t in bounds if a0 <= j < a1), slots[-1]['type'])
    lexical = u['kind'] != 'cut'
    G = Geo(base_id, (UNIT, 'معجمية' if lexical else 'مقطَّعة'),
            Omega=[Obligation('هوية اللفظ')],
            O=dict(text=text, slots=[(sl['type'], sl['text']) for sl in slots], word_index=wi, unit=ui))
    G.O['cells'] = cells
    G.O['orphans'] = orphans
    if lexical:
        for c in cells:
            extend(G, c, None, Evidence('خلية من رسم المدخل', [c.show()]), T)
        G.O['pending'] = []
        lab = u['label'] or ''
        ev = Evidence(f'مدخل معجمي: {lab}', [f'«{text}» في ' + ('فهرس العوامل' if 'عامل' in lab else
                                                               'ملف المبنيات' if 'مبني' in lab else
                                                               'المعجم: لفظ الجلالة' if 'الجلالة' in lab else 'المعجم')])
        G.Omega[0].met, G.Omega[0].ev = True, ev
        G.Theta['lex'] = lab
        close(G, ev, Evidence('حدّ الخانة', ['من المقشِّر: ' + ' + '.join(sl['type'] for sl in slots)]), T)
        return G
    sylls, stray = syllabify(cells, base_id, T)
    G.O['pending'] = [c for c, _ in stray]
    for S in sylls:
        extend(G, S, 'تتابع', Evidence('مقطع مغلق', [cv(S)]), T)
    if stray:
        defer(G, T, 'خلية لم يُبنَ لها مقطع: ' + '، '.join(f'{c.show()} {why}' for c, why in stray))
        return G
    # β: تجميع الخلايا في المقاطع، ويُقارَن بمقطِّع الخط
    G.Theta['beta'] = [cv(S) for S in sylls]
    pipe = [x['cv'] for x in u['syllables']]
    G.Theta['beta_agrees'] = (G.Theta['beta'] == pipe)
    # الهوية: Realize(R, P, F) للجذع المقبول جذره
    stem = [sl for sl in slots if sl['type'] == 'جذع']
    m = next((x for x in a.get('morph', []) if x['word_index'] == wi and stem and x['slot'] == stem[0]['index']), None)
    if not stem or len([sl for sl in slots if sl['type'] != 'أل']) != 1:
        types = '+'.join(sl['type'] for sl in slots)
        defer(G, T, f'لا تحليل جذري ووزني لـ{types} بعدُ (اسم)')
        G.Omega[0].reason = 'اسم'
        return G
    if not m:
        # الاسم يثبت بدليل إيجابي: «أل»، أو التنوين، أو التاء المربوطة، أو حرف جرٍّ مقبول عامل فيه
        from .status import ACCEPTED
        st = {(f['word_index'], f['operator'], f['group']): f.get('status') for f in a['operators']}
        jarr = any(r.get('target') and r['target']['word_index'] == wi and r['target']['slot'] == stem[0]['index'] and
                   r.get('expected') == 'جر' and st.get((r['word_index'], r['operator'], r['group'])) == ACCEPTED
                   for r in a.get('relations', []))
        noun_proof = ('أل' if any(sl['type'] == 'أل' for sl in slots) else
                      'التنوين' if any(c.O.get('tanwin') for c in cells) else
                      'التاء المربوطة' if any(c.C == 'ة' for c in cells) else
                      'حرف جر مقبول' if jarr else None)
        if noun_proof is None:
            defer(G, T, 'اسم أو غيره: لم تثبت الاسمية بالكتابة، والجذر والوزن مؤجَّلان')
            G.Omega[0].reason = 'لم تثبت الاسمية'
            return G
        hits = lex_index().get(_lex_key(stem[0]['text']), [])
        stem_cells = [c for c in cells if c.O['slot'] == 'جذع']
        parts = participle_analyses(stem_cells)
        roots = sorted({h[0] for h in hits} | {p[0] for p in parts})
        if len(roots) == 1 and not hits:
            r, cls, kind, alpha, ops, lvl = parts[0]
            classes = sorted({p[1] for p in parts})
            if len(classes) == 1:
                alpha = ['أل'] * (len(cells) - len(stem_cells)) + alpha
                from .root import WAZN
                G.Theta.update(R=r, P=f'اسم {kind} من {WAZN.get(cls, cls)} ({cls})', F=dict(kind='اسم', pos=f'اسم {kind}'),
                               alpha=alpha, ops=ops)
                ev = Evidence(f'Realize({" ".join(r)}, اسم {kind} من {cls})',
                              [f'الاسمية: {noun_proof}',
                               f'حدث ({r}، {cls}) في HFN' if lvl == 'حدث' else f'الجذر {r} في HFN، والوزن بالقالب',
                               f'α = ⟨{", ".join(alpha)}⟩'] + ops,
                              [('قالب آخر مرخَّص', 'قالب واحد')])
                G.Omega[0].met, G.Omega[0].ev = True, ev
                close(G, ev, Evidence('حدّ الخانة', ['من المقشِّر: ' + '+'.join(sl['type'] for sl in slots)]), T)
                return G
        if len(roots) == 1 and hits:
            h = hits[0]
            alpha, ops = align_radicals(stem_cells, roots[0])
            if alpha:
                alpha = ['أل'] * (len(cells) - len(stem_cells)) + alpha
                G.Theta.update(R=roots[0], P=f'{h[1]} ({h[2]})', F=dict(kind='اسم', pos=h[1]), alpha=alpha, ops=ops,
                               lex=h[4])
                ev = Evidence(f'بناء معجمي مرخَّص: {h[1]} «{h[4]}» في HFN ({h[3]})',
                              [f'الاسمية: {noun_proof}', f'الجذر {" ".join(roots[0])}', f'α = ⟨{", ".join(alpha)}⟩'] + ops,
                              [('جذرٌ آخر للمدخل نفسه', 'مدخل واحد الجذر')])
                G.Omega[0].met, G.Omega[0].ev = True, ev
                close(G, ev, Evidence('حدّ الخانة', ['من المقشِّر: ' + '+'.join(sl['type'] for sl in slots)]), T)
                return G
        if not roots:
            sib = sibawayh_analyses(stem_cells)
            sroots = sorted({x[0] for x in sib})
            if len(sroots) == 1:
                x = sib[0]
                pats = sorted({f'{y[3]} ({y[1]}، {y[2]})' for y in sib})
                alpha = ['أل'] * (len(cells) - len(stem_cells)) + x[4]
                G.Theta.update(R=x[0], P='بناء سيبويه: ' + ' أو '.join(pats), F=dict(kind='اسم', pos='بناء'),
                               alpha=alpha, ops=[])
                ev = Evidence(f'Realize({" ".join(x[0])}, {x[3]}): من أبنية الأسماء عند سيبويه',
                              [f'الاسمية: {noun_proof}', f'الكتاب {x[2]} ({x[1]}): {x[3]}، ومن أمثلته {x[5][:40]}',
                               f'الجذر {x[0]} في HFN', f'α = ⟨{", ".join(alpha)}⟩',
                               'الملف غير مصدَّق من صاحب النظرية (owner_ratified=NO)'],
                              [('جذرٌ آخر بقالبٍ آخر', 'جذر واحد في كل الأبنية المطابقة')])
                G.Omega[0].met, G.Omega[0].ev = True, ev
                close(G, ev, Evidence('حدّ الخانة', ['من المقشِّر: ' + '+'.join(sl['type'] for sl in slots)]), T)
                return G
            if len(sroots) > 1:
                roots = sroots
        defer(G, T, 'اسم: ' + ('أكثر من جذر في HFN: ' + '، '.join(roots) if len(roots) > 1 else
                               'لا مدخل له في HFN (مصدر، اسم فاعل، اسم مفعول)'))
        G.Omega[0].reason = 'اسم'
        return G
    if m['status'] != 'accepted':
        why = m.get('reason') or 'لا تحليل'
        defer(G, T, f'الجذر والوزن مؤجَّلان: {why}')
        G.Omega[0].reason = 'جذر مؤجَّل'
        return G
    agr = next((g for g in a.get('agreement', []) if g['word_index'] == wi and g['slot'] == stem[0]['index']), None)
    info = stem_info(stem[0]['text'])
    kinds = [k for k in [(agr or {}).get('kind'), info.get('kind'), 'madi', 'mudari', 'amr'] if k]
    root = m['root']
    alpha, ops, kind = None, None, None
    for k in dict.fromkeys(kinds):
        alpha, ops = align_alpha(cells, root, m['form_class'], k)
        if alpha:
            kind = k
            break
    if not alpha:
        defer(G, T, f'Realize لا يطابق الخلايا: {ops}')
        G.Omega[0].reason = 'Realize'
        return G
    F = dict(kind=kind)
    if agr:
        F.update(subject=agr.get('pronouns'), voice=agr.get('voice'))
    G.Theta.update(R=root, P=m['form_class'], F=F, alpha=alpha, ops=ops)
    wm = wazn_meaning(m['form_class'])
    if wm:
        G.Theta['wazn_meaning'] = dict(wazn=wm[0], meaning=wm[1], sources=wm[2], status=wm[3])
    ev = Evidence(f'Realize({" ".join(root)}, {m["form_class"]}, {kind})',
                  [f'α = ⟨{", ".join(x or "?" for x in alpha)}⟩', 'Flatten(β) = الخلايا نفسها'] + ops,
                  [('خلية زائدة داخل الهيكل', 'كل خلية بين السابقة واللاحقة مقابَلة')])
    G.Omega[0].met, G.Omega[0].ev = True, ev
    close(G, ev, Evidence('حدّ الخانة', ['من المقشِّر: جذع']), T)
    return G


# ---------- البناء المعجمي المرخَّص للاسم: المصدر واسم الفاعل واسم المفعول من HFN ----------
_LEX = None
NOUN_POS = ('مصدر', 'اسم فاعل', 'اسم مفعول')


def _lex_key(t):
    """مفتاح المطابقة: الحروف والحركات بلا علامة الإعراب الأخيرة (ولا ألف تنوين النصب)، والهمزات موحَّدة،
    والخنجرية ألف"""
    import re
    t = re.sub('[\u06D6-\u06ED\u0640\u0653]', '', t).replace('\u0670', 'ا')
    toks = letters(t)
    if toks and toks[-1][0] in 'اى' and not toks[-1][1] and len(toks) > 1 and toks[-2][1] & {FATHATAN}:
        toks = toks[:-1]
    out = []
    for i, (L, m) in enumerate(toks):
        m = set(m) - {SUKUN}
        if i == len(toks) - 1:
            m -= {FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN}
        out.append(HAMZA.get(L, L) + ''.join(sorted(m)))
    return ''.join(out)


def lex_index():
    """مفتاح الاسم ← [(الجذر، النوع، الوزن، المعرِّف)] من lexical_units.csv في HFN"""
    global _LEX
    if _LEX is None:
        import csv, os
        from .root import hfn
        _LEX = {}
        H = hfn()
        if H.path and os.path.exists(os.path.join(H.path, 'lexical_units.csv')):
            ev_root = {}
            for e in csv.DictReader(open(os.path.join(H.path, 'events.csv'), encoding='utf-8')):
                ev_root[e['event_id']] = e['root_K']
            for x in csv.DictReader(open(os.path.join(H.path, 'lexical_units.csv'), encoding='utf-8')):
                if x['pos_ar'] in NOUN_POS and x['event_id'] in ev_root:
                    _LEX.setdefault(_lex_key(x['lemma']), []).append(
                        (ev_root[x['event_id']], x['pos_ar'], x['pattern'], x['lu_id'], x['lemma']))
    return _LEX


def align_radicals(cells, root):
    """α للبناء المعجمي: الأصول بترتيبها في الخلايا، والمعتل منها يجوز إعلاله؛ وما سواها زائد"""
    alpha = ['زائد'] * len(cells)
    ops, i = [], 0
    for k, r in enumerate(root):
        r = HAMZA.get(r, r)
        j = next((x for x in range(i, len(cells)) if cells[x].C == r), None)
        if j is None:
            if r in WEAK:
                ops.append(f'إعلال r{k + 1} ({r})')
                continue
            return None, f'الأصل r{k + 1} «{r}» لا تقابله خلية'
        alpha[j] = f'r{k + 1}'
        if j + 1 < len(cells) and cells[j + 1].C == r and cells[j].H == '∅':
            alpha[j + 1] = f'r{k + 1}'          # الشدة: الخليتان للأصل نفسه
            j += 1
        i = j + 1
    return alpha, ops


# ---------- اسما الفاعل والمفعول قياساً: Realize(R, P) مرخَّصاً بحدث (R، الوزن) في HFN ----------
# كل عنصر: (الصامت أو Rk، الحركة أو *، الطول أو *)؛ والأخير حركته حركة الإعراب
def _t(spec):
    out = []
    for x in spec.split():
        C, H, L = x.split(':')
        out.append((C, H, int(L) if L != '*' else '*'))
    return out


PARTICIPLES = {
    ('I', 'فاعل'): _t('R1:a:2 R2:i:1 R3:*:*'),
    ('I', 'مفعول'): _t('م:a:1 R1:∅:1 R2:u:2 R3:*:*'),
    ('II', 'فاعل'): _t('م:u:1 R1:a:1 R2:∅:1 R2:i:1 R3:*:*'),
    ('II', 'مفعول'): _t('م:u:1 R1:a:1 R2:∅:1 R2:a:1 R3:*:*'),
    ('III', 'فاعل'): _t('م:u:1 R1:a:2 R2:i:1 R3:*:*'),
    ('III', 'مفعول'): _t('م:u:1 R1:a:2 R2:a:1 R3:*:*'),
    ('IV', 'فاعل'): _t('م:u:1 R1:∅:1 R2:i:1 R3:*:*'),
    ('IV', 'مفعول'): _t('م:u:1 R1:∅:1 R2:a:1 R3:*:*'),
    ('V', 'فاعل'): _t('م:u:1 ت:a:1 R1:a:1 R2:∅:1 R2:i:1 R3:*:*'),
    ('VI', 'فاعل'): _t('م:u:1 ت:a:1 R1:a:2 R2:i:1 R3:*:*'),
    ('VII', 'فاعل'): _t('م:u:1 ن:∅:1 R1:a:1 R2:i:1 R3:*:*'),
    ('VIII', 'فاعل'): _t('م:u:1 R1:∅:1 ت:a:1 R2:i:1 R3:*:*'),
    ('VIII', 'مفعول'): _t('م:u:1 R1:∅:1 ت:a:1 R2:a:1 R3:*:*'),
    ('X', 'فاعل'): _t('م:u:1 س:∅:1 ت:a:1 R1:∅:1 R2:i:1 R3:*:*'),
    ('X', 'مفعول'): _t('م:u:1 س:∅:1 ت:a:1 R1:∅:1 R2:a:1 R3:*:*'),
}
# لواحق الاسم بعد آخر الأصول: التاء المربوطة، ونون الجمع والمثنى، وتاء جمع المؤنث
NOUN_SUFFIX = ('ة', 'ن', 'ت')


def _match_participle(cells, tmpl):
    """→ (الأصول، α، العمليات) أو None. صحيح الأصول وحده (المعتل يُترك للمدخل المعجمي)"""
    if len(cells) < len(tmpl):
        return None
    rad, alpha, ops = {}, [], []
    for (C, H, L), c in zip(tmpl, cells):
        if C.startswith('R'):
            if c.C in 'وي' and not (C == 'R2' and tmpl[0] == ('R1', 'a', 2) and c.H == 'i') or rad.get(C, c.C) != c.C:
                return None
            rad[C] = c.C
            alpha.append(C.lower())
        else:
            if c.C != C and not (C == 'ت' and c.C in 'طد'):
                return None
            if c.C != C:
                ops.append(f'إبدال ت ← {c.C}')
            alpha.append(f'زائد:{C}')
        if H != '*' and c.H != H or L != '*' and c.L != L:
            return None
    rest = cells[len(tmpl):]
    if len(rest) > 1 or rest and rest[0].C not in NOUN_SUFFIX:
        return None
    alpha += ['لاحقة'] * len(rest)
    return ''.join(rad[k] for k in sorted(rad)), alpha, ops


import os as _os
RANK_BY_ATTESTATION = _os.environ.get('SARF_RANK_ATTESTATION') == '1'


def _verb_ilal(H, root):
    """عين الفعل الثلاثي في HFN: «معلّ» إن جاء ماضيه بألفٍ بعد الفاء (قَامَ، بَاعَ)، و«صحيح» إن ثبتت العين
    واواً أو ياءً متحركة (عَوِرَ)، وإلا None"""
    out = set()
    for e in H.index.get((root, 'I'), []):
        t = letters(e['verb'])
        if len(t) >= 2 and t[1][0] == 'ا':
            out.add('معلّ')
        elif len(t) >= 2 and t[1][0] in 'وي' and t[1][1] & {FATHA, DAMMA, KASRA}:
            out.add('صحيح')
    return 'معلّ' if out == {'معلّ'} else 'صحيح' if out == {'صحيح'} else ('كلاهما' if out else None)


def participle_analyses(cells):
    """→ [(الجذر، الوزن، فاعل/مفعول، α، العمليات، المستوى)] مرخَّصة بحدثٍ في HFN بالجذر والوزن،
    أو بالجذر وحده إن لم يُرخَّص بحدثٍ شيء (كما في الفعل)"""
    from .root import hfn
    H = hfn()
    matched = []
    for (cls, kind), tmpl in PARTICIPLES.items():
        m = _match_participle(cells, tmpl)
        if m:
            root, alpha, ops = m
            matched.append((root, cls, kind, alpha, ops))
            # الأجوف: «اسم الفاعل يعتلّ باعتلال فعله» (ابن يعيش، شرح المفصل ج5 ص448): قَامَ ← قَائِم، بَاعَ ← بَائِع.
            # فهمزة فاعل بعد الطول بدلٌ من العين بشرط أن يكون الفعل نفسه مُعَلَّ العين (في ماضيه ألف: قَامَ)؛
            # فإن صحّت عينه في الفعل (عَوِرَ) صحّت في اسم الفاعل (عَاوِر) ولم تُهمز
            if cls == 'I' and kind == 'فاعل' and root[1] == 'ء':
                for w in 'وي':
                    r2 = root[0] + w + root[2]
                    if _verb_ilal(H, r2) in ('معلّ', 'كلاهما'):
                        matched.append((r2, cls, kind, alpha, ops + [f'إبدال العين {w} ← ء: الفعل معلّ العين']))
            # المثال والمهموز في افتعل: الفاء تاء مدغمة (مُتَّخِذ ← ءخذ)
            if cls == 'VIII' and root[0] == 'ت':
                for w in 'ءوي':
                    matched.append((w + root[1:], cls, kind, alpha, ops + [f'إبدال الفاء {w} ← ت']))
        # الناقص: اللام محذوفة، فالعين آخر الأصول بكسرٍ طويل قبل نون الجمع أو بتنوين (مُعۡتَدِينَ، مُعۡتَدٍ)
        if tmpl[-1][0] == 'R3' and len(cells) >= len(tmpl) - 1:
            short = tmpl[:-1]
            head = cells[:len(short)]
            last = head[-1] if head else None
            if last is not None and last.H == 'i' and (last.L == 2 or last.O.get('tanwin')):
                m = _match_participle(head, short[:-1] + [(short[-1][0], 'i', '*')]) if \
                    len(cells) - len(short) <= 1 else None
                if m and (len(cells) == len(short) or cells[-1].C == 'ن'):
                    for w in 'وي':
                        matched.append((m[0] + w, cls, kind, m[1] + ['لاحقة'] * (len(cells) - len(short)),
                                        m[2] + [f'حذف اللام {w}']))
    # وعينٌ واو أو ياء صحيحة في فاعل (عَاوِر) لا تكون إلا من فعلٍ صحيح العين (عَوِرَ)
    matched = [x for x in matched if not (x[1] == 'I' and x[2] == 'فاعل' and x[0][1] in 'وي' and
                                          'إبدال العين' not in ' '.join(x[4]) and _verb_ilal(H, x[0]) not in ('صحيح', 'كلاهما'))]
    ev = [x + ('حدث',) for x in matched if (x[0], x[1]) in H.index]
    if RANK_BY_ATTESTATION and len({x[0] for x in ev}) > 1:
        # الترجيح بقوة الشهادة في HFN (A أقوى من B … E)، إن تفاضلت؛ وإلا بقي الاحتمال (تجربة تنتظر الإقرار)
        rank = {x[0]: min((e['tier'][:1] or 'Z') for e in H.index[(x[0], x[1])]) for x in ev}
        best = min(rank.values())
        if sum(1 for r in set(rank) if rank[r] == best) == 1:
            ev = [x + () for x in ev if rank[x[0]] == best]
    return ev or [x + ('جذر',) for x in matched if x[0] in H.roots]


# ---------- معاني صيغ الأفعال (ملف أوزان الأفعال بمصادره، غير مصدَّق من صاحب النظرية) ----------
_WMEAN = None


def wazn_meaning(cls):
    """الوزن I…X ← (المعنى، المصادر، حالة الإقرار) من data/patterns/awzaan_af3aal_all.csv؛
    والثلاثي المجرد يتوقف على بابه (حركة عين المضارع)، فلا يُسنَد إليه معنى هنا"""
    global _WMEAN
    if _WMEAN is None:
        import csv, os
        _WMEAN = {}
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'data', 'patterns', 'awzaan_af3aal_all.csv')
        if os.path.exists(path):
            for x in csv.DictReader(open(path, encoding='utf-8-sig')):
                code = x['wazn_code'].strip()
                if code and code != 'I' and code not in _WMEAN:
                    _WMEAN[code] = (x['wazn'], x['wazn_meaning'] or x['meaning'],
                                    ' | '.join(u for u in (x['source_shadha'], x['source_sibawayh'], x['source_radi']) if u),
                                    'مُقَرّ' if x['owner_ratified'] == 'YES' else 'غير مُقَرّ')
    return _WMEAN.get(cls)


# ---------- أبنية الأسماء عند سيبويه (الكتاب ج4 ص242 وما بعدها): قوالب للاسم ----------
_SIB = None
SIB_PATHS = ['data/patterns/awzan_sibawayh_308.csv']


def sibawayh_patterns():
    """→ [(المعرِّف، الصفحة، البناء، القالب، الأمثلة)] من ملف أبنية سيبويه: الموجود والنادر المعيَّن الضبط،
    والقالب بخلايا البناء: ف ع ل ↦ R1 R2 R3 (والرباعي والخماسي لاماته R3…R5)، وآخر خلية حركتها حركة الإعراب"""
    global _SIB
    if _SIB is not None:
        return _SIB
    import csv, os
    H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = next((os.path.join(H, x) for x in SIB_PATHS if os.path.exists(os.path.join(H, x))), None)
    _SIB = []
    if not path:
        return _SIB
    for x in csv.DictReader(open(path, encoding='utf-8-sig')):
        pat = x['pattern_vocalized']
        if x['status'] not in ('EXISTS', 'RARE') or x['vocalization_basis'] == 'UNDETERMINED' or '?' in pat:
            continue
        cs, _ = cells_of(pat, 'p')
        if not cs:
            continue
        quad = x['section'].startswith(('رباعي', 'خماسي'))
        seen, tmpl = {}, []
        lams = 0
        for c in cs:
            if c.C in 'فع':
                C = 'R1' if c.C == 'ف' else 'R2'
            elif c.C == 'ل':
                if quad and not (c.H == 'a' and False):
                    # الرباعي والخماسي: كل لامٍ أصلٌ جديد، إلا الشدة (اللام الثانية من خليتي الشدة)
                    if c.O.get('role') == 'شدة: الثاني':
                        C = f'R{2 + lams}'
                    else:
                        lams += 1
                        C = f'R{2 + lams}'
                else:
                    C = 'R3'
            else:
                C = c.C
            tmpl.append((C, c.H, c.L))
        last = len(tmpl) - 1
        if pat[-1] in '\u064C\u064F':                # الحركة الأخيرة إعراب
            C, H_, L = tmpl[last]
            tmpl[last] = (C, '*', '*' if L == 1 else L)
        _SIB.append((x['id'], x['page'], pat, tmpl, x['examples']))
    return _SIB


def sibawayh_analyses(cells):
    """→ [(الجذر، المعرِّف، الصفحة، البناء، α، الأمثلة)] لكل بناءٍ يطابق الخلايا وجذرُه في HFN"""
    from .root import hfn
    H = hfn()
    out = []
    for sid, page, pat, tmpl, ex in sibawayh_patterns():
        if len(cells) < len(tmpl):
            continue
        rad, alpha, ok = {}, [], True
        for (C, Hh, L), c in zip(tmpl, cells):
            if C.startswith('R'):
                if rad.get(C, c.C) != c.C or (c.C in 'وي' and c.H == '∅' and False):
                    ok = False; break
                rad[C] = c.C
                alpha.append(C.lower())
            elif c.C != C:
                ok = False; break
            else:
                alpha.append(f'زائد:{C}')
            if Hh != '*' and c.H != Hh or L != '*' and c.L != L:
                ok = False; break
        if not ok:
            continue
        rest = cells[len(tmpl):]
        if len(rest) > 1 or rest and rest[0].C not in NOUN_SUFFIX:
            continue
        root = ''.join(rad[k] for k in sorted(rad))
        if root in H.roots:
            out.append((root, sid, page, pat, alpha + ['لاحقة'] * len(rest), ex))
    return out


# ---------- المستوى 3: الجملة (الآية) ----------
# ---------- الحالة المكتوبة، والخبر، والمفعول ----------
def word_case(a, wi, verbs=()):
    """الحالة المكتوبة على آخر جذع الكلمة wi: رفع، أو نصب، أو جر، أو «جر أو نصب» (الياء)؛ وNone لما لا تدلّ عليه
    علامته، وللفعل، ولما ليس فيه جذع"""
    from .segment import _observed
    if wi in verbs or wi >= len(a['segments']):
        return None
    seg = a['segments'][wi]
    stem = [sl for sl in seg['slots'] if sl['type'] in ('جذع', 'لفظ الجلالة')]
    if not stem:
        return None
    if 'toks' not in seg:
        seg = dict(seg, toks=[(L, set(m)) for L, m in letters(seg['word'])])
    try:
        c = _observed(seg, stem[-1])
    except (IndexError, KeyError):
        return None
    st = letters(stem[-1]['text'])
    bare = _bare_w(stem[-1]['text'])
    if c == 'جزم':
        return None                                   # لا جزم في الاسم: قراءةٌ خاطئة للسكون
    if bare in ('قبل', 'بعد') and c == 'رفع':
        return None                                   # مبنيّان على الضم إذا قُطعا عن الإضافة
    # جمع المؤنث السالم يُنصب بالكسرة: الكسرة بعد «ات» جرٌّ أو نصب (ٱلصَّٰلِحَٰتِ، جَنَّٰتٍ)
    if c == 'جر' and len(st) >= 3 and st[-1][0] == 'ت' and (st[-2][0] == 'ا' or DAGGER_ALIF in st[-2][1]):
        return 'جر أو نصب'                            # والألف قد تُرسم خنجرية (ٱلصَّٰلِحَٰتِ، ءَايَٰتِ)
    # «انِ»: رفعُ المثنى، أو جرُّ ما آخره ألف ونون (ٱلۡفُرۡقَانِ، ءَاذَانِهِمۡ): لا تدلّ
    if c == 'رفع' and len(st) >= 2 and st[-1][0] == 'ن' and KASRA in st[-1][1] and st[-2][0] == 'ا':
        return None
    # تنوين «إذ» في يَوۡمَئِذٍ وحِينَئِذٍ تنوينُ عِوَض، لا علامة جرّ للكلمة
    if bare.endswith('ئذ'):
        return None
    from .segment import ZURUF
    if bare in ZURUF:
        return None                                   # الظرف: حالته لا تخصّ هذه القواعد
    # الممنوع من الصرف يُجرّ بالفتحة: فتحةٌ بلا تنوين ولا «أل» ولا لاحقة جرٌّ أو نصب (إِسۡرَٰٓءِيلَ، إِبۡرَٰهِيمَ)،
    # إلا أن يكون مضافاً يليه معرَّف (كِتَٰبَ ٱللَّهِ)
    if c == 'نصب' and st and FATHA in st[-1][1] and not st[-1][1] & {FATHATAN} and \
            not any(sl['type'] == 'أل' for sl in seg['slots']) and seg['slots'][-1] is stem[-1]:
        nxt = a['segments'][wi + 1] if wi + 1 < len(a['segments']) else None
        mudaf = nxt is not None and any(sl['type'] in ('أل', 'لفظ الجلالة') or
                                        sl['type'] == 'مبني' and _bare_w(sl['text']).startswith('ال') for sl in nxt['slots'])
        if not mudaf:
            return 'نصب أو جر'
    return c


def noun_evidence(seg, next_wasl=False):
    """دليلٌ مكتوب على اسمية الكلمة: تنوين، أو «أل»، أو لفظ الجلالة، أو تاء مربوطة، أو «ات» في آخرها.
    بلا واحدٍ منها لا تُقرأ حركة الآخر حالةً إعرابية: فتحة الماضي (عَلَّمَ، تَبَٰرَكَ)، وكسرة التقاء الساكنين
    (أَقِمِ، غُلِبَتِ)، وكسرة المنادى المضاف إلى الياء (يَٰقَوۡمِ) تشتبه بالنصب والجر"""
    if any(sl['type'] in ('أل', 'لفظ الجلالة') for sl in seg['slots']):
        return True
    stem = [sl for sl in seg['slots'] if sl['type'] == 'جذع']
    if not stem:
        return False
    st = letters(stem[-1]['text'])
    if not st:
        return False
    if st[-1][1] & {FATHATAN, DAMMATAN, KASRATAN} or st[-1][0] == 'ة' or \
            len(st) >= 2 and st[-1][0] == 'ت' and (st[-2][0] == 'ا' or DAGGER_ALIF in st[-2][1]):
        return True
    # تنوين النصب على ألفٍ بعد الحرف (عَيۡنًا): العلامة على ما قبل الألف
    if len(st) >= 2 and st[-1][0] == 'ا' and FATHATAN in st[-2][1]:
        return True
    # بناءان لا يكونان فعلاً: فاعِل (مَٰلِكِ) وفِعَال (صِرَٰطَ). والكسرة قبل همزة وصلٍ قد تكون كسرة التقاء
    # الساكنين في أمر فاعَلَ (قَٰتِلِ ٱلۡ…)، فلا تُعدّ
    if next_wasl and KASRA in st[-1][1]:
        return False
    alif_after = lambda i: DAGGER_ALIF in st[i][1] or i + 1 < len(st) and st[i + 1][0] == 'ا' and FATHA in st[i][1]
    core = [x for x in st if x[0] != 'ا']
    if len(core) == 3 and alif_after(0) and KASRA in core[1][1] and st[0][0] not in 'اأإ':
        return True                                   # فاعِل
    if len(core) == 3 and KASRA in st[0][1] and alif_after(1):
        return True                                   # فِعَال
    return False


def _governed_words(a):
    """الكلمات التي يعمل فيها عاملٌ مقبول في آيتها (فحالتها مفسَّرة بعاملها)"""
    from .status import ACCEPTED
    st = {(f['word_index'], f['operator'], f['group']): f.get('status') for f in a['operators']}
    return {r['target']['word_index'] for r in a.get('relations', []) if r.get('target') and
            st.get((r['word_index'], r['operator'], r['group'])) == ACCEPTED}


def _boundary_after(marks, w):
    return 0 <= w < len(marks) and marks[w] in BOUNDARY_WAQF


def find_khabar(a, r, verbs, governed, marks):
    """خبر الناسخ (إنّ وأخواتها مج 2، وكان وأخواتها مج 10) في آيته، إلى أول حدٍّ أو عاملِ تركيبٍ آخر:
    - ما بين الناسخ واسمه المؤخَّر (فَإِنَّ مَعَ ٱلۡعُسۡرِ يُسۡرًا): خبرٌ مقدَّم شبه جملة
    - اللام المزحلقة على كلمةٍ بعد اسم «إنّ»: خبرها
    - أول اسمٍ بعد الاسم علامته المكتوبة حالةُ الخبر (رفعٌ لإنّ، ونصبٌ لكان)، ولا عامل فيه غيره
    - فعلٌ يلي الاسم مباشرةً (والاسم ليس موصولاً تليه صلته): جملة فعلية
    - وإلا شبه جملة تلي الاسم، ولا مرفوع/منصوب بعدها إلى الحدّ
    → (رقم الكلمة، النوع، الدليل) أو None"""
    t = r.get('target')
    if t is None:
        return None
    op_w, ism_w = r['word_index'], t['word_index']
    grp = r['group']
    want = 'رفع' if grp == '2' else 'نصب'
    if ism_w > op_w + 1:
        return (op_w + 1, 'شبه جملة مقدَّم', 'ما بين الناسخ واسمه المؤخَّر')
    ism_text = _bare_w(a['segments'][ism_w]['slots'][t['slot']]['text'])
    relative = ism_text in RELATIVES or ism_text in ('ما', 'من')
    n = len(a['segments'])
    from .status import ACCEPTED
    first_pp = None
    w = ism_w + 1
    if _boundary_after(marks, ism_w):
        return None
    while w < n:
        seg = a['segments'][w]
        sl0 = seg['slots'][0]['text']
        # اللام المزحلقة على اسمٍ أو فعل، أو على ضمير الفصل المنفصل (لَهُوَ، لَهِيَ)؛ أما «لَكُمۡ، لَهُمۡ، لَهُۥ» فلام جرّ
        nxt_sl = seg['slots'][1] if len(seg['slots']) > 1 else None
        if grp == '2' and sl0 in ('لَ', 'لَّ') and nxt_sl is not None and \
                (nxt_sl['type'] != 'مبني' or _bare_w(nxt_sl['text']) in ('هو', 'هي')):
            return (w, 'خبر باللام المزحلقة', 'اللام المزحلقة لا تدخل إلا على خبر «إنّ»')
        if w == ism_w + 1 and not relative and w not in verbs and any(
                f['word_index'] == w and f['group'] == '10' and f.get('status') == ACCEPTED for f in a['operators']):
            return (w, 'جملة فعلية (كان وأخواتها)', 'ناسخٌ فعليٌّ مقبول يلي اسم «إنّ» مباشرةً')
        if w in verbs:
            if w == ism_w + 1 and not relative:
                return (w, 'جملة فعلية', 'فعلٌ يلي اسم الناسخ مباشرةً')
            if not relative:
                break
        c = word_case(a, w, verbs)
        if c == want and w not in governed:
            from .affix import stem_info
            stem_t = [sl['text'] for sl in seg['slots'] if sl['type'] == 'جذع']
            mud = stem_t and stem_info(stem_t[-1]).get('kind') == 'mudari'
            kind = 'مرفوع (اسم أو مضارع لم تثبت فعليته)' if mud and want == 'رفع' else 'مفرد'
            return (w, kind, f'العلامة المكتوبة {want}، ولا عامل فيه غير الناسخ')
        if first_pp is None and w in governed and c == 'جر':
            first_pp = w
        if _boundary_after(marks, w):
            break
        w += 1
    if first_pp is not None and first_pp == ism_w + 1:
        return (first_pp, 'شبه جملة', f'شبه جملة تلي الاسم، ولا {want} بعدها إلى الحدّ')
    return None


def _madi_like(text):
    """صورة الماضي قبل الضمير: حروفٌ متحركة كلها بلا مدّ ولا سكون (أَكَلَ، جَعَلَ، بعد واوٍ أو فاء)،
    أو آخرها ضمير رفعٍ بعد ساكن (رَفَعۡنَٰ، قُلۡتُ)"""
    st = letters(text)
    if len(st) >= 2 and st[0][0] in 'وف' and FATHA in st[0][1] and len(st) > 3:
        st = st[1:]
    if len(st) >= 3 and (st[-1][0] == 'ت' or ''.join(L for L, _ in st[-2:]) == 'نا' or
                         st[-1][0] == 'ن' and DAGGER_ALIF in st[-1][1]):
        k = -2 if st[-1][0] == 'ت' or DAGGER_ALIF in st[-1][1] else -3
        if SUKUN in st[k][1]:
            return True
    return 3 <= len(st) <= 4 and all(m & {FATHA, DAMMA, KASRA} and not m & {SUKUN} for _, m in st) and \
        not any(L in 'اوي' and not m & {FATHA, DAMMA, KASRA} for L, m in st) and FATHA in st[-1][1]


def find_object(a, g, verbs, governed, marks, units, unit_of):
    """المفعول به لفعلٍ متعدٍّ: الضمير المتصل بعده في كلمته، أو أول منصوبٍ بعده (يُتجاوز مرفوعٌ واحد هو الفاعل)
    إلى أول حدٍّ أو فعلٍ آخر، ولا عامل فيه غيره. → (رقم الوحدة، الدليل) أو None"""
    wi, si = g['word_index'], g['slot']
    seg = a['segments'][wi]
    for sl in seg['slots'][si + 1:]:
        if sl['type'] == 'مبني':
            return (units[unit_of[(wi, sl['index'])]].id, 'ضمير متصل بالفعل')
    skipped_subject = False
    w = wi + 1
    if _boundary_after(marks, wi):
        return None
    clause_w = {f['word_index'] for f in a['operators'] if f['group'] in CLAUSE_OPS and f.get('status') != 'blocked'}
    while w < len(a['segments']):
        if w in verbs or w in clause_w:
            break                                     # فعلٌ آخر أو عامل تركيبٍ جديد (أنّ، كان، الشرط): ما بعده لغيره
        sg = a['segments'][w]
        stem = [sl for sl in sg['slots'] if sl['type'] in ('جذع', 'لفظ الجلالة')]
        c = word_case(a, w, verbs)
        # المعطوف بالواو أو الفاء معطوفٌ على ما قبله، لا مفعولٌ أول (لِتَسۡكُنُواْ فِيهِ وَٱلنَّهَارَ)
        if len(sg['slots']) > 1 and _bare_w(sg['slots'][0]['text']) in ('و', 'ف') and sg['slots'][0]['type'] != 'جذع':
            break
        time_adv = stem and _bare_w(stem[-1]['text']) in ('يوم', 'حين', 'ساعة', 'ليلة', 'غدا')
        # المنصوب اسمٌ بدليلٍ مكتوب، أو جذعٌ بعده ضمير (أَبۡنَآءَهُمۡ)؛ وفتحة المضارع المؤكَّد (لَيَعۡلَمَنَّ) ليست نصباً
        nounish = noun_evidence(sg) or (stem and sg['slots'][-1]['type'] == 'مبني' and not _madi_like(stem[-1]['text']))
        if c == 'رفع' and not skipped_subject:
            skipped_subject = True
        elif w not in governed and not time_adv and nounish and stem and \
                (c == 'نصب' or c == 'جر أو نصب' and w == wi + 1):
            k = (w, stem[-1].get('unit', 0))
            return (units[k].id if k in units else None, 'أول منصوب بعد الفعل ولا عامل فيه غيره')
        if _boundary_after(marks, w):
            break
        w += 1
    return None


def sentence_geo(a, vid, T):
    """الآية: تمتدّ بالوحدات المغلقة وحدها، بعلاقاتها المقبولة (العامل ← المعمول، والإسناد)؛
    وتُغلق إن استُوفيت التزاماتها اللازمة وثبت حدّها برقم الآية"""
    S = Geo(vid, (SENTENCE, 'مادة الآية'), O=dict(text=a['normalized'], pending=[]))
    units = {}
    for seg in a['segments']:
        wi = seg['word_index']
        for ui in range(len(seg['units'])):
            G = unit_geo(a, wi, ui, f'{vid}.w{wi}.u{ui}', T)
            units[(wi, ui)] = G
            if G.closed:
                extend(S, G, 'تجاور', Evidence('وحدة مغلقة تلي سابقتها', [f'الكلمة {wi}']), T)
            else:
                S.O['pending'].append(G)
                S.Omega.append(Obligation(f'إغلاق «{G.O["text"]}»', reason=G.O.get('deferred', ''), units=[G.id]))
    # عمليات المقشِّر على الرسم: فكّ الشدة على حدّ الخانتين (كُنَّ ← كُنْ + نَ) تُسجَّل ليُعكس في Render
    S.O['ops'] = []
    for seg in a['segments']:
        us = seg['units']
        for ui in range(1, len(us)):
            if merge_split_shadda(us[ui - 1]['text'], us[ui]['text']) is not None and \
                    ''.join(x['text'] for x in us) != seg['word']:
                S.O['ops'].append(('فكّ الشدة', seg['word_index'], ui))
    unit_of = {}
    for seg in a['segments']:
        for sl in seg['slots']:
            unit_of[(seg['word_index'], sl['index'])] = (seg['word_index'], sl.get('unit', 0))
    status = {(f['word_index'], f['operator'], f['group']): f for f in a['operators']}
    from .status import ACCEPTED
    verbs = {g['word_index'] for g in a.get('agreement', [])}
    governed = _governed_words(a)
    marks = waqf_of(a['verse']) if 'verse' in a else []
    if len(marks) != len(a['segments']):
        marks = [None] * len(a['segments'])
    for r in a.get('relations', []):
        f = status.get((r['word_index'], r['operator'], r['group']))
        if not f or f.get('status') != ACCEPTED:
            continue
        t = r.get('target')
        name = f'معمول «{r["operator"]}»'
        if t is None:
            if r.get('note'):        # المكفوفة: لا معمول، والكفّ ثابت بالكتابة
                S.B.append(('كفّ', unit_of.get((r['word_index'], r['slot'])), None,
                            Evidence(r['note'], (f.get('judgement') or {}).get('proof', []))))
            continue
        src = units.get(unit_of.get((r['word_index'], r['slot'])))
        dst = units.get(unit_of.get((t['word_index'], t['slot'])))
        proof = (f.get('judgement') or {}).get('proof', [])
        # العلاقة النحوية ثابتة بالعامل المقبول ومعموله وعلامته؛ وإغلاق الوحدتين بالجذر والوزن التزامٌ آخر («إغلاق»)
        ok = r.get('consistent') is not False and src is not None and dst is not None
        ob = Obligation(name, met=bool(ok), units=[x.id for x in (src, dst) if x is not None])
        if ok:
            ob.ev = Evidence(f'«{r["operator"]}» عاملٌ مقبول', proof or ['مطابقة'],
                             [('مخالفة العلامة', f'المكتوب {r.get("observed")}')] if r.get('observed') else [])
            S.B.append((r.get('role') or r.get('expected') or 'عمل', src.id, dst.id, ob.ev))
        else:
            ob.reason = 'العلامة المكتوبة تخالف أثر العامل' if r.get('consistent') is False else 'لا معمول في الآية'
        S.Omega.append(ob)
        if r['group'] in ('2', '10'):
            ob = Obligation(f'خبر «{r["operator"]}»', units=[src.id] if src is not None else [])
            kh = r.get('khabar')
            if kh or 'خبر' in (r.get('role') or ''):
                ob.met, ob.ev = True, Evidence('الخبر من المقشِّر', [str((kh or {}).get('text') or r.get('role'))])
            else:
                found = find_khabar(a, r, verbs, governed, marks)
                if found:
                    w, kind, why = found
                    kslot = a['segments'][w]['slots'][-1]
                    dstk = units.get((w, kslot.get('unit', 0)))
                    ob.met, ob.ev = True, Evidence(f'خبر «{r["operator"]}» {kind}', [why])
                    if dstk is not None and src is not None:
                        S.B.append((f'خبر «{r["operator"]}» ({kind})', src.id, dstk.id, ob.ev))
                    ob.units = [x for x in [src.id if src is not None else None, dstk.id if dstk is not None else None] if x]
                else:
                    ob.reason = 'لم يوجد الخبر في آيته بالعلامة المكتوبة'
            S.Omega.append(ob)
            S.O.setdefault('nuclei', []).append((src.id if src is not None else None, f'ناسخ «{r["operator"]}»'))
    for g in a.get('agreement', []):
        G = units.get(unit_of.get((g['word_index'], g['slot'])))
        if G is None:
            continue
        # الإسناد ثابت بالتوافق (T18) وإن لم يُغلق جذر الفعل: فهو نواة جملة
        S.O.setdefault('nuclei', []).append((G.id, f'إسناد «{G.O["text"]}»'))
        if not G.closed:
            continue
        prons = g.get('pronouns') or []
        ob = Obligation(f'فاعل «{G.O["text"]}»', met=bool(prons), units=[G.id])
        if prons:
            ob.ev = Evidence('جدول الإسناد R(m, p)', [g.get('rule') or '', 'Φ(p): ' + ' أو '.join(prons)])
            S.B.append(('إسناد', G.id, ' أو '.join(prons), ob.ev))
        S.Omega.append(ob)
        # المفعول به: التزامٌ جائز (يُحذف المفعول)، لا لازم؛ والتعدّي من HFN
        # «قال» ومعموله مقول القول جملةً محكيّة، لا مفعولٌ منصوب: فلا يُفتح له التزام المفعول
        if G.Theta.get('R') and G.Theta.get('P') and g.get('voice') != 'passive' and G.Theta['R'] != 'قول':
            from .root import hfn
            tr = {e.get('transitivity') for e in hfn().index.get((G.Theta['R'], G.Theta['P']), [])}
            wm = wazn_meaning(G.Theta['P']) or ('', '', '', '')
            by_wazn = not tr - {''} and 'التعدية' in (wm[1] or '') + ('التعدية' if G.Theta['P'] in ('II', 'IV') else '')
            if tr & {'متعدي', 'مشترك'} or by_wazn:
                why_tr = 'الفعل متعدٍّ في HFN' if tr & {'متعدي', 'مشترك'} else \
                    f'التعدية غالبةٌ في وزن {wm[0] or G.Theta["P"]} (ملف أوزان الأفعال، غير مُقَرّ)'
                oo = Obligation(f'مفعول «{G.O["text"]}»', required=False, units=[G.id])
                found = find_object(a, g, verbs, governed, marks, units, unit_of)
                if found and found[0]:
                    oo.met, oo.ev = True, Evidence('مفعول به', [found[1], why_tr])
                    S.B.append(('مفعول به', G.id, found[0], oo.ev))
                    oo.units = [G.id, found[0]]
                else:
                    oo.reason = 'لم يُذكر أو لم يُكشف (قد يُحذف المفعول)'
                S.Omega.append(oo)
    if S.open_required():
        defer(S, T, f'{len(S.open_required())} التزاماً مفتوحاً')
        return S, units
    close(S, Evidence('استُوفيت التزامات الآية', [f'{len(S.Omega)} التزاماً']),
          Evidence('حدّ الآية', ['رقم الآية في المصحف']), T)
    return S, units


def merge_split_shadda(left, right):
    """عكس «فكّ الشدة على الحدّ» في المقشِّر: «كُنْ» + «نَ» ← «كُنَّ». → النص المدموج أو None"""
    if not left or not right:
        return None
    tl, tr = letters(left), letters(right)
    if not tl or not tr or tl[-1][0] != tr[0][0] or SUKUN not in tl[-1][1] or SHADDA in tr[0][1]:
        return None
    sp = spans(left)
    head = left[:sp[-1][0]]
    L = tl[-1][0]
    sr = spans(right)
    marks = right[sr[0][0] + 1:sr[0][1]]
    import unicodedata
    return unicodedata.normalize('NFC', head + L + SHADDA + marks + right[sr[0][1]:])


def render_sentence(S, units):
    """Render(الآية): الكلمات من وحداتها، والوحدات من خلاياها؛ وعمليات المقشِّر المسجَّلة تُعكس"""
    words = {}
    for (wi, ui), G in sorted(units.items()):
        txt, _ = render_cells(G.O['cells'], G.O['text'], G.O.get('orphans', ()))
        if wi in words and ('فكّ الشدة', wi, ui) in S.O.get('ops', []):
            words[wi] = merge_split_shadda(words[wi], txt)
        else:
            words[wi] = words.get(wi, '') + txt
    return ' '.join(words[k] for k in sorted(words))


def build(geo_level, kind, children, gid, T, boundary):
    """Build_k(x₁…xₙ; e) = Close_k(FoldExtend_k(G₀; x₁…xₙ); e_c, e_b): المغلق يمتدّ به، وغيره يُعلَّق"""
    G = Geo(gid, (geo_level, kind), O=dict(pending=[]))
    for x in children:
        if x.closed:
            extend(G, x, 'تتابع', Evidence(f'{x.tau[1]} مغلقة', [x.id]), T)
        else:
            G.O['pending'].append(x)
            G.Omega.append(Obligation(f'إغلاق {x.id}'))
    if G.open_required():
        defer(G, T, f'{len(G.open_required())} مكوّناً غير مغلق')
    else:
        close(G, Evidence('مكوّناته كلها مغلقة', [str(len(G.A))]), Evidence(boundary, ['من بنية المصحف']), T)
    return G



# ---------- الطبقتان: المصحفية واللغوية، وLocation ----------
# علامات الوقف في مصحف المجمّع: حكم لجنة المصحف في تمام المعنى عندها
WAQF = {'ۘ': 'م', 'ۗ': 'قلى', 'ۚ': 'ج', 'ۖ': 'صلى', 'ۛ': '∴', 'ۜ': 'س'}
WAQF_NAME = {'م': 'الوقف لازم', 'قلى': 'الوقف أولى', 'ج': 'الوقف جائز', 'صلى': 'الوصل أولى مع جواز الوقف',
             '∴': 'معانقة: الوقف في أحد الموضعين', 'س': 'سكتة'}
# الحدّ المثبت: ما جاز الوقف عنده لتمام المعنى؛ والمعانقة لا تعيّن موضعها، والسكتة ليست وقفاً
BOUNDARY_WAQF = ('م', 'قلى', 'ج', 'صلى')


def waqf_of(verse_text):
    """علامة الوقف بعد كل كلمة من الآية في رسم المصحف (أو None)"""
    from .normalize import LONE_ALIF
    return [next((WAQF[ch] for ch in w if ch in WAQF), None) for w in LONE_ALIF.sub(r'\1\2', verse_text).split()]


def mushaf_layer(items, T):
    """الطبقة المصحفية: كلمة ← آية ← سورة ← مصحف، من الخلايا نفسها؛ حدودها في الرسم فتُغلق بالحفظ وحده.
    items: [(السورة، الآية، التحليل، الوحدات)] → المصحف"""
    surahs = {}
    for s, v, a, units in items:
        ay = Geo(f'M{s}:{v}', (3, M_AYAH), O=dict(layer='مصحف', text=a['normalized']))
        for wi, seg in enumerate(a['segments']):
            W = Geo(f'M{s}:{v}:{wi}', (2, M_WORD), O=dict(layer='مصحف', text=seg['word']))
            for ui in range(len(seg['units'])):
                for c in units[(wi, ui)].O['cells']:
                    extend(W, c, None, Evidence('خلية من رسم الكلمة', [c.id]), T)
            close(W, Evidence('خلايا الكلمة كلها', [str(len(W.A))]), Evidence('حدّ الكلمة في الرسم', ['مسافة']), T)
            extend(ay, W, 'تتابع', Evidence('كلمة مغلقة', [W.id]), T)
        close(ay, Evidence('كلمات الآية كلها', [str(len(ay.A))]), Evidence('رقم الآية في المصحف', [f'{s}:{v}']), T)
        surahs.setdefault(s, []).append(ay)
    sur = []
    for s in sorted(surahs):
        G = Geo(f'M{s}', (4, M_SURAH), O=dict(layer='مصحف'))
        for ay in surahs[s]:
            extend(G, ay, 'تتابع', Evidence('آية مغلقة', [ay.id]), T)
        close(G, Evidence('آيات السورة كلها', [str(len(G.A))]), Evidence('حدّ السورة في المصحف', [str(s)]), T)
        sur.append(G)
    M = Geo('M', (5, M_MUSHAF), O=dict(layer='مصحف'))
    for G in sur:
        extend(M, G, 'تتابع', Evidence('سورة مغلقة', [G.id]), T)
    close(M, Evidence('سور المصحف كلها', [str(len(M.A))]), Evidence('حدّ المصحف', ['آخر سورة الناس']), T)
    return M


# ---------- الروابط عبر حدّ الآية ----------
RELATIVES = ('الذين', 'الذي', 'التي', 'اللذين', 'اللتين', 'اللاتي', 'اللائي', 'الذين')
# أدوات الشرط التي لا تلتبس بالموصول أو الاستفهام في الكتابة (ما ومن تلتبسان فتُترك)
COND_STRICT = ('إذا', 'إن', 'لو', 'أينما', 'حيثما', 'مهما', 'كلما', 'إذما', 'متى', 'أيان')
CLAUSE_OPS = ('2', '5', '6', '7', '10')            # النواسخ، والنواصب، والجوازم، والشرط: تفتح تركيباً جديداً


def _bare_w(t):
    import re
    return re.sub('[^ء-ي]', '', t.replace('ٱ', 'ا'))


def _unit_of_slot(a, wi, slot):
    return (wi, a['segments'][wi]['slots'][slot].get('unit', 0))


def find_attachment(prev):
    """المتعلَّق في الآية السابقة لشبه جملةٍ أو مستثنى بعد حدّها، من الأقرب إلى الحدّ:
    فعلٌ ثابت (T18)، ثم شبه فعلٍ مغلق (اسم فاعل، أو اسم مفعول، أو مصدر)، ثم كلمةٌ بصيغة الفعل لم تثبت فعليتها.
    → (معرِّف الوحدة، النوع، ثابت؟) أو None"""
    from .affix import stem_info
    pa, units = prev['a'], prev['units']
    verbs = sorted(((g['word_index'], g['slot']) for g in pa.get('agreement', [])), reverse=True)
    if verbs:
        wi, sl = verbs[0]
        return (units[_unit_of_slot(pa, wi, sl)].id, 'فعل', True)
    for k in sorted(units, reverse=True):
        G = units[k]
        pos = (G.Theta.get('F') or {}).get('pos', '')
        if G.closed and (pos in ('اسم فاعل', 'اسم مفعول', 'مصدر') or str(G.Theta.get('P', '')).startswith('اسم')):
            return (G.id, f'شبه فعل ({pos or G.Theta.get("P")})', True)
    for k in sorted(units, reverse=True):
        G = units[k]
        if G.tau[1] == 'مقطَّعة' and stem_info(G.O['text']).get('kind') in ('madi', 'mudari', 'amr'):
            return (G.id, 'كلمة بصيغة الفعل (لم تثبت فعليتها)', False)
    return None


ZURUF_TIME = ('اليوم', 'الآن')


def cross_ayah_links(analyze_fn, prev, nxt):
    """الروابط بين آيتين متتاليتين من سورة واحدة. prev/nxt: dict(s, v, text، a، units).
    أ. التحليل المشترك: تُحلَّل الآيتان تياراً واحداً، فكل علاقةٍ مقبولة عاملُها في الأولى ومعمولها في الثانية رابطٌ ثابت.
    ب. قواعد بداية الآية التالية:
       - ثابت: شبه جملة (جارٌّ مقبول) في أولها، ولا نواة ولا عامل تركيبٍ بينه وبين أول حدٍّ فيها، فمتعلَّقه قبله (وَبِٱلَّيۡلِ ← تَمُرُّونَ)
       - ثابت: «إِلَّا» في أولها: استثناءٌ من شيءٍ قبله
       - محتمل: اسم موصول في أولها (نعت أو بدل لما قبله، أو مبتدأ)
       - محتمل: شرطٌ في الأولى لا جواب له فيها؛ وناسخٌ في الأولى لم يُستوفَ خبره فيها
    → [dict(src, dst, rel, proven, rule)] بمعرِّفات الوحدات"""
    from .status import ACCEPTED
    from .affix import stem_info
    out = []
    pa, na = prev['a'], nxt['a']
    n1 = len(pa['segments'])
    pid = lambda wi, slot: prev['units'][_unit_of_slot(pa, wi, slot)].id
    nid = lambda wi, slot: nxt['units'][_unit_of_slot(na, wi, slot)].id
    # أ. التحليل المشترك
    try:
        aj = analyze_fn(prev['text'] + ' ' + nxt['text'])
    except Exception:
        aj = None
    if aj and len(aj['segments']) == n1 + len(na['segments']):
        st = {(f['word_index'], f['operator'], f['group']): f.get('status') for f in aj['operators']}
        for r in aj.get('relations', []):
            t = r.get('target')
            # العامل آخرُ كلمة في آيته، فلا معمول له فيها: معموله بعد الحدّ ضرورةً. وما سوى ذلك (كان وخبرها شبه جملة
            # في آيتها، ثم يلتقط المحلل منصوباً بعد الحدّ) لا يُقبل عبوراً
            if t and r['word_index'] == n1 - 1 and t['word_index'] >= n1 and \
                    st.get((r['word_index'], r['operator'], r['group'])) == ACCEPTED:
                try:
                    out.append(dict(src=pid(r['word_index'], r['slot']), dst=nid(t['word_index'] - n1, t['slot']),
                                    rel=r.get('role') or r.get('expected') or 'عمل', proven=True,
                                    rule='التحليل المشترك للآيتين: عاملٌ مقبول ومعموله بعد حدّ الآية'))
                except (KeyError, IndexError):
                    pass
    nuc_prev = [g for g in pa.get('agreement', [])]
    last_nuc = nuc_prev[-1] if nuc_prev else None
    # أول حدٍّ في الآية التالية: علامة وقف مثبتة أو آخرها
    marks = waqf_of(na['verse'])
    first_b = next((i for i, m in enumerate(marks) if m in BOUNDARY_WAQF), len(na['segments']) - 1)
    span = range(0, first_b + 1)
    nst = {(f['word_index'], f['operator'], f['group']): f.get('status') for f in na['operators']}
    jar0 = next((r for r in na.get('relations', []) if r['word_index'] == 0 and r.get('expected') == 'جر' and
                 nst.get((r['word_index'], r['operator'], r['group'])) == ACCEPTED), None)
    nuc_span = [g for g in na.get('agreement', []) if g['word_index'] in span]
    clause_ops = [f for f in na['operators'] if f['word_index'] in span and f['group'] in CLAUSE_OPS and
                  f.get('status') != 'blocked']
    # المدى إلى أول حدٍّ لا يحوي إلا شبه الجملة نفسها (الجارّ ومجروره): لا إسناد فيه يُتمّ كلاماً
    pp_alone = jar0 is not None and jar0.get('target') is not None and first_b <= jar0['target']['word_index']
    # «كَذَٰلِكَ» وحدها: قد تتعلق بما قبلها، وقد تكون خبر مبتدأ محذوف (الأمرُ كذلك)؛ فعبورها محتمل لا ثابت
    kaf = jar0 is not None and _bare_w(jar0['operator']) == 'ك'
    att = find_attachment(prev)
    if jar0 and pp_alone and not nuc_span and not clause_ops and not kaf:
        if att:
            out.append(dict(src=att[0], dst=nid(0, jar0['slot']), rel=f'تعلّق شبه الجملة بـ{att[1]}', proven=True,
                            rule='شبه جملة في أول الآية وحدها إلى أول حدٍّ فيها: متعلَّقها قبل حدّ الآية',
                            attach_proven=att[2]))
            jar0 = None                                   # لا تُكرَّر بالقاعدة القديمة
    if jar0 and pp_alone and not nuc_span and not clause_ops and kaf:
        out.append(dict(src=prev['units'][max(prev['units'])].id, dst=nid(0, jar0['slot']), rel='تعلّق «كذلك» بما قبلها',
                        proven=False, rule='«كَذَٰلِكَ» في أول الآية: متعلقة بما قبلها أو خبرٌ لمحذوف'))
    elif jar0 and pp_alone and not nuc_span and not clause_ops:
        if last_nuc:
            out.append(dict(src=pid(last_nuc['word_index'], last_nuc['slot']), dst=nid(0, jar0['slot']),
                            rel='تعلّق شبه الجملة', proven=True,
                            rule='شبه جملة في أول الآية وحدها إلى أول حدٍّ فيها: متعلَّقها قبل حدّ الآية'))
        else:
            # العبور ثابت (شبه الجملة وحدها لا تستقل)، والمتعلَّق بعينه غير معيَّن في التحليل
            out.append(dict(src=prev['units'][max(prev['units'])].id, dst=nid(0, jar0['slot']),
                            rel='تعلّق شبه الجملة بما قبل الحدّ (المتعلَّق غير معيَّن)', proven=True,
                            rule='شبه جملة في أول الآية وحدها إلى أول حدٍّ فيها: متعلَّقها قبل حدّ الآية'))
    w0 = _bare_w(na['segments'][0]['word'])
    tgt = (pid(last_nuc['word_index'], last_nuc['slot']) if last_nuc else prev['units'][max(prev['units'])].id)
    if w0 in ('إلا', 'الا'):
        out.append(dict(src=tgt, dst=nid(0, 0), rel='استثناء', proven=True,
                        rule='«إِلَّا» في أول الآية: المستثنى منه قبل حدّ الآية'))
    # التابع عبر الحدّ بالمطابقة الإعرابية: كلمةٌ أولَ الآية لا عامل فيها في آيتها، وعلامتها المكتوبة:
    #  - جرٌّ بلا حرف عطف: لا يُبتدأ بمجرور، فعامله (جارٌّ أو مضاف) أو متبوعه قبل الحدّ — ثابت (مَٰلِكِ يَوۡمِ ٱلدِّينِ)
    #  - جرٌّ بعد واو أو فاء: عطفٌ على مجرورٍ قبله، أو واو قسم — محتمل
    #  - نصبٌ ولا نواة ولا عامل تركيبٍ إلى أول حدٍّ: عامله قبل الحدّ — ثابت؛ وإلا فبدلٌ أو نعتٌ أو حال محتمل إن وافق ما قبله
    verbs_n = {g['word_index'] for g in na.get('agreement', [])}
    gov_n = _governed_words(na)
    seg0 = na['segments'][0]
    # يا النداء في أول الكلمة (يَٰقَوۡمِ، يَٰصَٰحِبَيِ): منادى لا تابع
    l0 = letters(seg0['word'])
    voc = len(l0) > 2 and l0[0][0] == 'ي' and (DAGGER_ALIF in l0[0][1] or l0[1][0] == 'ا')
    c0 = word_case(na, 0, verbs_n) if 0 not in gov_n and noun_evidence(seg0, len(na['segments']) > 1 and _bare_w(na['segments'][1]['word'])[:1] == 'ا') and not voc else None
    # الواو والفاء في أول الكلمة، مبنيّاً كان في المقشِّر أو عاملاً مؤجَّلاً (واو القسم)
    conj = len(na['segments'][0]['slots']) > 1 and _bare_w(na['segments'][0]['slots'][0]['text']) in ('و', 'ف')
    if c0:
        verbs_p = {g['word_index'] for g in pa.get('agreement', [])}
        AMB = ('جر أو نصب', 'نصب أو جر')
        same = next((w for w in range(n1 - 1, -1, -1) if noun_evidence(pa['segments'][w], w + 1 < n1 and _bare_w(pa['segments'][w + 1]['word'])[:1] == 'ا') and (
                     word_case(pa, w, verbs_p) in (c0,) + AMB or
                     c0 in AMB and word_case(pa, w, verbs_p) in ('جر', 'نصب'))), None)
        src = pid(same, len(pa['segments'][same]['slots']) - 1) if same is not None else prev['units'][max(prev['units'])].id
        stem0 = len(na['segments'][0]['slots']) - 1
        if c0 == 'جر' and not conj:
            out.append(dict(src=src, dst=nid(0, stem0), rel='تابعٌ أو معمولٌ لما قبل الحدّ (جرّ)', proven=True,
                            rule='مجرورٌ في أول الآية بلا جارٍّ ولا مضافٍ في آيتها: عامله أو متبوعه قبل الحدّ'))
        elif c0 == 'جر' and conj:
            out.append(dict(src=src, dst=nid(0, stem0), rel='عطفٌ على مجرور أو قسم', proven=False,
                            rule='مجرورٌ بعد واو أو فاء في أول الآية: معطوفٌ على ما قبله، أو واو قسم'))
        # ظرف الزمان المنصوب أولَ الآية (ٱلۡيَوۡمَ أُحِلَّ) عامله ما بعده غالباً؛ ومنصوبٌ يليه مضارعٌ لم تثبت فعليته
        # (كُلࣰّا نُّمِدُّ) قد يكون مفعولاً مقدَّماً له: فلا يثبت العبور في الحالين
        stem0_bare = _bare_w(seg0['slots'][-1]['text'])
        time_adv = stem0_bare in ('يوم', 'حين', 'ساعة', 'ليلة', 'غدا') or stem0_bare in ZURUF_TIME
        seg1 = na['segments'][1] if len(na['segments']) > 1 else None
        fronted = seg1 is not None and 1 not in verbs_n and len(seg1['slots']) == 1 and \
            seg1['slots'][0]['type'] == 'جذع' and not noun_evidence(seg1) and \
            (stem_info(seg1['slots'][0]['text']) or {}).get('kind') == 'mudari'
        if c0 == 'نصب' and not conj and (time_adv or fronted):
            out.append(dict(src=src, dst=nid(0, stem0), rel='منصوبٌ عامله قبل الحدّ أو بعده', proven=False,
                            rule='ظرف زمان أو منصوبٌ يليه مضارع لم تثبت فعليته: قد يعمل فيه ما بعده'))
        elif c0 == 'نصب' and not conj and not nuc_span and not clause_ops:
            out.append(dict(src=src, dst=nid(0, stem0), rel='منصوبٌ بعاملٍ قبل الحدّ', proven=True,
                            rule='منصوبٌ في أول الآية ولا نواة ولا عامل إلى أول حدٍّ فيها: عامله قبل الحدّ'))
        elif c0 in ('نصب', 'جر أو نصب', 'نصب أو جر') and same is not None and not conj:
            out.append(dict(src=src, dst=nid(0, stem0), rel='بدلٌ أو نعتٌ أو حال', proven=False,
                            rule='منصوبٌ في أول الآية يوافق ما قبله في الإعراب: تابعٌ له، أو مفعولٌ مقدَّم لما بعده'))
    if w0.lstrip('وف') in RELATIVES and w0[:1] not in 'وف':
        out.append(dict(src=prev['units'][max(prev['units'])].id, dst=nid(0, 0), rel='نعت أو بدل أو ابتداء',
                        proven=False, rule='اسم موصول في أول الآية: قد يكون تابعاً لما قبله، وقد يكون مبتدأ'))
    # شرطٌ لا جواب له في آيته
    pmarks = waqf_of(pa['verse'])
    for f in pa['operators']:
        if f['group'] == '7' and f.get('status') != 'blocked' and _bare_w(f['operator']) in COND_STRICT:
            after = [g for g in pa.get('agreement', []) if g['word_index'] > f['word_index']]
            later_b = any(m in BOUNDARY_WAQF for m in pmarks[f['word_index']:-1]) if len(pmarks) == n1 else True
            if len(after) <= 1 and not later_b:
                out.append(dict(src=pid(f['word_index'], 0) if False else prev['units'][(f['word_index'], 0)].id,
                                dst=nid(0, 0), rel='جواب الشرط بعدُ', proven=False,
                                rule=f'«{f["operator"]}» في الآية السابقة بلا جوابٍ محلَّل فيها'))
                break
    for o in prev['S'].Omega:
        if o.name.startswith('خبر') and not o.met and o.units:
            out.append(dict(src=o.units[0], dst=nid(0, 0), rel=o.name, proven=False,
                            rule='ناسخٌ لم يُستوفَ خبره في آيته'))
            break
    return out


def waqf_sources():
    """سجل أقوال العلماء في الوقف (sources/waqf.csv): (السورة، الآية، الكلمة) ← [القول]"""
    import csv, os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sources', 'waqf.csv')
    out = {}
    if os.path.exists(path):
        for x in csv.DictReader(open(path, encoding='utf-8')):
            out.setdefault((int(x['surah']), int(x['ayah']), int(x['word_index'])), []).append(x)
    return out


WAQF_W = {'م': 'وقف لازم', 'قلى': 'الوقف أولى', 'ج': 'وقف جائز', 'صلى': 'الوصل أولى مع جواز الوقف',
          '∴': 'معانقة (الوقف في أحد الموضعين)', 'س': 'سكت (انقطاع بلا تنفس، ليس وقفاً)'}
SYNTACTIC_OBL = ('معمول', 'خبر', 'فاعل')


def boundary_record(p, words, pos_of, bonds, obls, nuclei, du_start, mark, ayah_end, surah_end, sources, a_id, q,
                    cand=(), checked_ends=frozenset()):
    """B(b | a, q, c) = ⟨F, L, M, W, I, E⟩ للحدّ المحتمل b بعد الكلمة p (اقتراح صاحب النظرية في النمذجة):
    F تمام الكلام في التحليل، L التعلّقات اللفظية العابرة، M المعنوية، W حكم الوقف، I حكم الابتداء، E القول ودليله.
    والتصنيف المشتق بتعريفات ابن الجزري (النشر، باب الوقوف): تامّ، كافٍ، حسن، أو لم يتمّ"""
    loc = words[p]
    span = range(du_start, p + 1)
    # F: نواة في المدى، ولا التزامٌ نحوي مفتوح فيه
    nuc = [n for n in nuclei if pos_of.get(n[0]) in span]
    open_ = [o for o in obls if o.required and not o.met and o.name.startswith(SYNTACTIC_OBL) and
             any(pos_of.get(u) in span for u in o.units)]
    F = 'غير محسوم: لا نواة محلَّلة' if not nuc else ('ناقص: ' + '، '.join(o.name for o in open_[:2])) if open_ else 'تام في التحليل'
    # L: الروابط اللفظية العابرة للحدّ؛ والمحلل يبحث داخل الآية، فحدّ الآية غير مفحوص
    cross = [b for b in bonds if b[1] in pos_of and b[2] in pos_of and
             min(pos_of[b[1]], pos_of[b[2]]) <= p < max(pos_of[b[1]], pos_of[b[2]])]
    # حدّ الآية مفحوصٌ إن فُحصت الآيتان بقواعد العبور (التحليل المشترك وقواعد البداية)؛ وحدّ السورة غير مفحوص
    L_checked = not ayah_end or (words[p][:2] in checked_ends and not surah_end)
    L = [f'{b[0]}: {words_text(words, pos_of[b[1]])} ↔ {words_text(words, pos_of[b[2]])}' for b in cross]
    Lp = [f'{c["rel"]}: {words_text(words, pos_of[c["src"]])} ↔ {words_text(words, pos_of[c["dst"]])} ({c["rule"]})'
          for c in cand if c['src'] in pos_of and c['dst'] in pos_of and
          min(pos_of[c['src']], pos_of[c['dst']]) <= p < max(pos_of[c['src']], pos_of[c['dst']])]
    # E وM: أقوال العلماء المسجَّلة في هذا الموضع
    E = [dict(scholar='لجنة مصحف المجمّع', book='المصحف (رواية حفص)', judgement=WAQF_W[mark])] if mark else []
    M = None
    src_L = None
    for x in sources.get(loc, []):
        E.append(dict(scholar=x['scholar'], book=x['book'], section=x['section'], judgement=x['category'],
                      url=x['url'], note=x['note']))
        if x['category'] == 'تام':
            M = []
        elif x['category'] in ('كاف', 'كافٍ'):
            M = [f'تعلّق معنوي بنصّ {x["scholar"]}']
        elif x['category'] in ('متصل', 'حسن'):
            src_L = f'تعلّق بما بعده بنصّ {x["scholar"]} ({x["book"]})'
    if src_L:
        L = L + [src_L]
    W = WAQF_W.get(mark) if mark else ('آخر السورة: قطع ممكن' if surah_end else
                                        'رأس آية: الوقف عليه مختار عند أكثر أهل الأداء' if ayah_end else None)
    # التصنيف المشتق
    if F.startswith('ناقص'):
        cat = 'لم يتمّ في التحليل'
    elif L:
        cat = 'حسن' if F.startswith('تام') else 'تعلّق لفظي عابر'
    elif Lp:
        cat = 'غير محسوم: تعلّق محتمل'
    elif not L_checked:
        cat = ('تام' if M == [] else 'كافٍ' if M else 'غير محسوم: حدّ الآية غير مفحوص لفظاً')
    elif F.startswith('تام'):
        cat = 'تام' if M == [] else 'كافٍ' if M else 'تام أو كافٍ (التعلّق المعنوي غير مسجَّل)'
    else:
        cat = 'غير محسوم'
    I = ('لا يُبتدأ بما بعده استقلالاً' if L else 'يُبتدأ بما بعده' if cat in ('تام', 'كافٍ') or cat.startswith('تام أو')
         else 'غير محسوم')
    return dict(location=loc, F=F, L=L, Lp=Lp, L_checked=L_checked, M=M, W=W, I=I, E=E, category=cat, a=a_id, q=q,
                mark=mark, ayah_end=ayah_end)


def words_text(words, p):
    return f'{words[p][0]}:{words[p][1]}:{words[p][2]}'


def linguistic_layer(items, T, a_id='', q='حفص عن عاصم (مصحف المجمّع)', cross=(), checked_ends=frozenset()):
    """الطبقة اللغوية على تيار الوحدات المتصل عبر حدود الآيات.
    - عند كل حدٍّ محتمل (علامة وقف، أو رأس آية، أو آخر سورة) يُسجَّل B(b | a, q, c) = ⟨F, L, M, W, I, E⟩
    - الوحدة الخطابية: ما بين حدّين أجاز الوقفَ عندهما دليلٌ (م، قلى، ج، صلى) أو آخرُ السورة؛ ورأس الآية وحده ليس حدّاً
    - الجملة: نواة إسنادٍ واحدة في وحدتها، والتزاماتها مستوفاة، وعند حدّها F تامّ وL خالٍ مفحوص: جوازُ الوقف وحده
      لا يُغلقها (قد يجوز الوقف والعلاقة النحوية ممتدة)
    - ما عبر الحدّ من تعلّق لفظي يُحفظ رابطاً في الهندسة الأعلى (خطاب السورة)، ولا تُغلق الوحدة الأعلى لاكتمال جملة
    items: [(السورة، الآية، التحليل، الوحدات، مادة الآية S)] → ([خطاب كل سورة]، الإحصاءات، سجلات الحدود)"""
    import collections
    st = collections.Counter()
    out, records = [], []
    sources = waqf_sources()
    by_surah = collections.OrderedDict()
    for it in items:
        by_surah.setdefault(it[0], []).append(it)
    for s, its in by_surah.items():
        words, wunits, marks, ay_end = [], [], [], []
        pos_of = {}
        bonds, obls, nuclei = [], [], []
        for s_, v, a, units, S in its:
            mk = waqf_of(a['verse'])
            if len(mk) != len(a['segments']):
                mk = [None] * len(a['segments'])
                st['waqf_misaligned'] += 1
            for wi, seg in enumerate(a['segments']):
                us = [units[(wi, ui)] for ui in range(len(seg['units']))]
                for G in us:
                    pos_of[G.id] = len(words)
                words.append((s, v, wi)); wunits.append(us); marks.append(mk[wi])
                ay_end.append(wi == len(a['segments']) - 1)
            bonds += [b for b in S.B if isinstance(b[1], str) and b[0] != 'تجاور']
            obls += list(S.Omega)
            nuclei += [n for n in S.O.get('nuclei', []) if n[0]]
        # الروابط عبر حدّ الآية: الثابت منها رابطٌ كسائر الروابط، والمحتمل يُسجَّل في سجل الحدّ
        cand = []
        for c in cross:
            if c['src'] in pos_of and c['dst'] in pos_of:
                if c['proven']:
                    bonds.append((c['rel'], c['src'], c['dst'], Evidence(c['rule'], ['عبر حدّ الآية'])))
                    st['cross_proven'] += 1
                    st['cross_rule:' + c['rule'].split(':')[0][:40]] += 1
                else:
                    cand.append(c)
                    st['cross_candidate'] += 1
        n = len(words)
        segs, du_start = [], 0
        for p in range(n):
            last = p == n - 1
            if marks[p] or ay_end[p] or last:
                rec = boundary_record(p, words, pos_of, bonds, obls, nuclei, du_start, marks[p], ay_end[p], last,
                                      sources, a_id, q, cand, checked_ends)
                records.append(rec)
                st['b_candidates'] += 1
                st['b_cat:' + rec['category'].split(':')[0].split(' (')[0]] += 1
                if rec['mark'] in BOUNDARY_WAQF and rec['L']:
                    st['b_mark_with_L'] += 1          # جواز الوقف مع تعلّق لفظي عابر (حسن، أو خطأ في التحليل)
                if rec['mark'] in BOUNDARY_WAQF or last:
                    segs.append((du_start, p, rec))
                    du_start = p + 1
        disc = []
        for k, (p0, p1, rec) in enumerate(segs):
            ids = {G.id for p in range(p0, p1 + 1) for G in wunits[p]}
            locs = words[p0:p1 + 1]
            ayahs = sorted({(x[0], x[1]) for x in locs})
            st['du'] += 1
            st['du_cross_ayah'] += len(ayahs) > 1
            eb = Evidence(f'B(b): W = {rec["W"]}', [f'F = {rec["F"]}', f'الصنف المشتق: {rec["category"]}'])
            D = Geo(f'L{s}.d{k}', (DISCOURSE, 'وحدة خطابية'),
                    O=dict(layer='لغة', pending=[], location=locs, ayahs=ayahs, boundary=rec))
            my_bonds = [b for b in bonds if b[1] in ids]
            st['bond_cross_du'] += sum(1 for b in my_bonds if b[2] in pos_of and b[2] not in ids)
            my_obls = [o for o in obls if o.units and all(u in ids for u in o.units)]
            my_nuc = [x for x in nuclei if x[0] in ids]
            J = Geo(f'L{s}.d{k}.J', (SENTENCE, 'جملة'), B=my_bonds,
                    Omega=[Obligation(o.name, o.required, o.met, o.ev, o.reason, o.units) for o in my_obls],
                    O=dict(layer='لغة', pending=[], location=locs, nuclei=[x[1] for x in my_nuc], boundary=rec))
            for p in range(p0, p1 + 1):
                for G in wunits[p]:
                    if G.closed:
                        extend(J, G, 'تتابع', Evidence('وحدة مغلقة', [G.id]), T)
                    else:
                        J.O['pending'].append(G)
            if len(my_nuc) == 0:
                J.Omega.append(Obligation('نواة الجملة', reason='لا نواة إسنادٍ محلَّلة (الجملة الاسمية لم تُحلَّل بعد)'))
                st['J_no_nucleus'] += 1
            elif len(my_nuc) > 1:
                J.Omega.append(Obligation('حدود الجمل', reason=f'{len(my_nuc)} نوى في وحدة خطابية واحدة، وحدّ ما بينها غير مثبت'))
                st['J_multi_nucleus'] += 1
            else:
                st['J_one_nucleus'] += 1
            # جواز الوقف لا يُغلق الجملة: يلزم عند حدّها تمامٌ وخلوٌّ مفحوص من التعلّق اللفظي العابر
            if rec['L'] or not rec['L_checked']:
                J.Omega.append(Obligation('استقلال الحدّ لفظاً',
                                          reason='تعلّق لفظي عابر: ' + '؛ '.join(rec['L'][:2]) if rec['L'] else
                                          'حدّ الآية أو السورة غير مفحوص لفظاً'))
                st['J_boundary_not_independent'] += 1
            st['J'] += 1
            if J.open_required():
                defer(J, T, '، '.join(o.name for o in J.open_required()[:3]))
            else:
                close(J, Evidence('استُوفيت التزامات الجملة', [f'النواة: {my_nuc[0][1]}', f'{len(J.Omega)} التزاماً']),
                      Evidence('حدّ الجملة مستقلّ لفظاً وجاز الوقف عنده', [f'W = {rec["W"]}', f'F = {rec["F"]}', 'L = ∅ مفحوص']), T)
                st['J_closed'] += 1
            if J.closed:
                extend(D, J, 'تتابع', Evidence('جملة مغلقة', [J.id]), T)
                close(D, Evidence('جملها مغلقة', ['1']), eb, T)
                st['du_closed'] += 1
            else:
                D.O['pending'].append(J)
                D.Omega.append(Obligation(f'إغلاق {J.id}', reason=J.O.get('deferred', '')))
                defer(D, T, 'جملة غير مغلقة')
            disc.append(D)
        sp = build(SPEECH, 'خطاب السورة', disc, f'L{s}', T, 'حدّ السورة')
        # ما عبر حدّ الوحدة الخطابية من تعلّق لفظي أو معنوي يُحفظ رابطاً في الهندسة الأعلى
        du_at = {}
        for k, (p0, p1, _) in enumerate(segs):
            for p in range(p0, p1 + 1):
                du_at[p] = disc[k].id
        du_of = {uid: du_at[p] for uid, p in pos_of.items()}
        for b in bonds:
            if b[2] in du_of and du_of.get(b[1]) != du_of.get(b[2]):
                sp.B.append(('تعلّق لفظي عابر: ' + b[0], du_of.get(b[1]), du_of.get(b[2]), b[3]))
        for D in disc:
            if D.O['boundary'].get('M'):
                sp.B.append(('تعلّق معنوي عابر', D.id, None, Evidence(D.O['boundary']['M'][0], ['من سجل الوقف'])))
        out.append(sp)
    return out, st, records


def render_layer(G):
    """Render على أي طبقة: نصّ الوحدات/الكلمات بالترتيب (المصحفية: الكلمة نصّها؛ اللغوية: من الخلايا)"""
    return [c for c in flatten(G)]
