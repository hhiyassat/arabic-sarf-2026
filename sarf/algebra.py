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
        ok = r.get('consistent') is not False and src is not None and dst is not None and src.closed and dst.closed
        ob = Obligation(name, met=bool(ok), units=[x.id for x in (src, dst) if x is not None])
        if ok:
            ob.ev = Evidence(f'«{r["operator"]}» عاملٌ مقبول', proof or ['مطابقة'],
                             [('مخالفة العلامة', f'المكتوب {r.get("observed")}')] if r.get('observed') else [])
            S.B.append((r.get('role') or r.get('expected') or 'عمل', src.id, dst.id, ob.ev))
        else:
            ob.reason = 'المعمول أو العامل غير مغلق'
        S.Omega.append(ob)
        if r['group'] in ('2', '10') and not r.get('khabar'):
            S.Omega.append(Obligation(f'خبر «{r["operator"]}»', reason='الخبر لم يُحلَّل بعد (T05)',
                                      units=[src.id] if src is not None else []))
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


def boundary_record(p, words, pos_of, bonds, obls, nuclei, du_start, mark, ayah_end, surah_end, sources, a_id, q):
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
    L_checked = not ayah_end
    L = [f'{b[0]}: {words_text(words, pos_of[b[1]])} ↔ {words_text(words, pos_of[b[2]])}' for b in cross]
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
    elif not L_checked:
        cat = ('تام' if M == [] else 'كافٍ' if M else 'غير محسوم: حدّ الآية غير مفحوص لفظاً')
    elif F.startswith('تام'):
        cat = 'تام' if M == [] else 'كافٍ' if M else 'تام أو كافٍ (التعلّق المعنوي غير مسجَّل)'
    else:
        cat = 'غير محسوم'
    I = ('لا يُبتدأ بما بعده استقلالاً' if L else 'يُبتدأ بما بعده' if cat in ('تام', 'كافٍ') or cat.startswith('تام أو')
         else 'غير محسوم')
    return dict(location=loc, F=F, L=L, L_checked=L_checked, M=M, W=W, I=I, E=E, category=cat, a=a_id, q=q,
                mark=mark, ayah_end=ayah_end)


def words_text(words, p):
    return f'{words[p][0]}:{words[p][1]}:{words[p][2]}'


def linguistic_layer(items, T, a_id='', q='حفص عن عاصم (مصحف المجمّع)'):
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
        n = len(words)
        segs, du_start = [], 0
        for p in range(n):
            last = p == n - 1
            if marks[p] or ay_end[p] or last:
                rec = boundary_record(p, words, pos_of, bonds, obls, nuclei, du_start, marks[p], ay_end[p], last,
                                      sources, a_id, q)
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
