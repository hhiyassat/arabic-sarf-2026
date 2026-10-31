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
                    DAGGER_ALIF, letters)
from .cells import (HAMZA, Cell, cells_of, _lex_key, lex_index, _verb_ilal, participle_analyses,
                    sibawayh_analyses)

# طبقتان على النص نفسه تشتركان في الخلايا:
#   اللغوية: خلية ≺ مقطع ≺ وحدة لفظية ≺ جملة ≺ وحدة خطابية ≺ خطاب السورة — حدودها بالعلاقات وشروط الاكتمال
#   المصحفية: خلية ≺ كلمة ≺ آية ≺ سورة ≺ مصحف — حدودها مثبتة في الرسم
# والآية لا تُغلق الجملة، والجملة لا تُغلق الآية؛ وتربطهما Location(J) = مواضع كلمات J في الآيات
LEVELS = ['خلية', 'مقطع', 'وحدة لفظية', 'جملة', 'وحدة خطابية', 'خطاب']
CELL, SYLLABLE, UNIT, SENTENCE, DISCOURSE, SPEECH = range(6)
PARAGRAPH, TOPIC = DISCOURSE, SPEECH
M_WORD, M_AYAH, M_SURAH, M_MUSHAF = 'كلمة', 'آية', 'سورة', 'مصحف'



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
        j = c.O['tok'][-1] if c.O['tok'] else 0          # همزة الابتداء بلا موضع رسم: خانة أول الوحدة
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
    sylls, stray = syllabify(cells, base_id, T, word_end=ui == len(seg['units']) - 1)
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
    # بوابة الحماية الدستورية قبل كل تحليلٍ جذري: العامل والمبني والاسم الذهبي يُغلق بهويته المعجمية بلا جذر ولا وزن
    from .protected import protected_slot as _protected
    prot = _protected(seg) if stem else None
    if prot is not None:
        G.Theta.update(R=None, root_status=prot['root_status'], protected=dict(cls=prot['cls'], identity=prot['identity'],
                                                                              proclitics=prot['proclitics'],
                                                                              enclitic=prot['enclitic']))
        if prot['ambiguous']:
            defer(G, T, f'تعيين الفئة مؤجَّل: {prot["cls"]} «{prot["identity"]}» محمي، أو {prot["alternative"]}')
            G.Omega[0].reason = 'فئة مؤجَّلة'
            return G
        ev = Evidence(f'وحدةٌ محمية دستورياً: {prot["cls"]} «{prot["identity"]}» (root_status = NOT_APPLICABLE)',
                      [f'الهوية من {prot["source"]}'] + ([f'السوابق: {"، ".join(prot["proclitics"])}'] if prot['proclitics'] else []) +
                      ([f'الضمير المتصل: {prot["enclitic"]}'] if prot['enclitic'] else []) +
                      ['لا يُستخرج جذرٌ ولا وزن: حكم تمثيلٍ دستوري (CONSTITUTIONAL_PROTECTED_CLASS)'],
                      [('تحليلٌ جذري للوحدة', 'الوحدة من الفئات المحمية')])
        G.Omega[0].met, G.Omega[0].ev = True, ev
        close(G, ev, Evidence('حدّ الخانة', ['من المقشِّر: ' + '+'.join(sl['type'] for sl in slots)]), T)
        return G
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
        sc = [c for c in cells if c.O['slot'] == 'جذع']
        if noun_proof is None and len(sc) == 3 and sc[0].L == 2 and sc[0].H == 'a' and sc[1].H == 'i' and \
                sc[1].L == 1 and sc[2].H in ('u', 'i'):
            # بناء فاعِل بحركة إعرابٍ على اللام (فَاطِرُ): لا فعل على هذه الصورة؛ فالماضي فَاعَلَ بفتح العين،
            # والأمر فَاعِلۡ بسكون اللام
            noun_proof = 'بناء فاعِل: كسر العين وحركة إعرابٍ على اللام'
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
    sel = m.get('selection') or {}
    ranked = m.get('level') == 'ranked'
    if ranked:
        # مرجَّحٌ لا مثبت: الإغلاق بالقراءة المرجَّحة، والبدائل محفوظة في Θ وفي الشهادة
        G.Theta['ranking'] = dict(status='مرجَّح لا مثبت', decision=sel.get('decision'), alternatives=sel.get('alternatives', []))
    ev = Evidence(f'Realize({" ".join(root)}, {m["form_class"]}, {kind})' + (' — مرجَّح لا مثبت' if ranked else ''),
                  [f'α = ⟨{", ".join(x or "?" for x in alpha)}⟩', 'Flatten(β) = الخلايا نفسها'] + ops +
                  ([f'الترجيح: {sel.get("decision")}', 'البدائل المحفوظة: ' + '، '.join(sel.get('alternatives', []))]
                   if ranked else []),
                  [('خلية زائدة داخل الهيكل', 'كل خلية بين السابقة واللاحقة مقابَلة')])
    G.Omega[0].met, G.Omega[0].ev = True, ev
    close(G, ev, Evidence('حدّ الخانة', ['من المقشِّر: جذع']), T)
    return G


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
    if c == 'جزم':
        return None                                   # لا جزم في الاسم: قراءةٌ خاطئة للسكون
    if is_form(stem[-1]['text'], ('قَبْلُ', 'بَعْدُ')) and c == 'رفع':
        return None                                   # مبنيّان على الضم إذا قُطعا عن الإضافة
    # جمع المؤنث السالم يُنصب بالكسرة: الكسرة بعد «ات» جرٌّ أو نصب (ٱلصَّٰلِحَٰتِ، جَنَّٰتٍ)
    if c == 'جر' and len(st) >= 3 and st[-1][0] == 'ت' and (st[-2][0] == 'ا' or DAGGER_ALIF in st[-2][1]):
        return 'جر أو نصب'                            # والألف قد تُرسم خنجرية (ٱلصَّٰلِحَٰتِ، ءَايَٰتِ)
    # «انِ»: رفعُ المثنى، أو جرُّ ما آخره ألف ونون (ٱلۡفُرۡقَانِ، ءَاذَانِهِمۡ): لا تدلّ
    if c == 'رفع' and len(st) >= 2 and st[-1][0] == 'ن' and KASRA in st[-1][1] and st[-2][0] == 'ا':
        return None
    # تنوين «إذ» في يَوۡمَئِذٍ وحِينَئِذٍ تنوينُ عِوَض، لا علامة جرّ للكلمة
    if len(st) >= 2 and st[-2][0] == 'ئ' and st[-1][0] == 'ذ':
        return None
    if is_form(stem[-1]['text'], ZURUF_V, i3rab=True):
        return None                                   # الظرف: حالته لا تخصّ هذه القواعد
    # الممنوع من الصرف يُجرّ بالفتحة: فتحةٌ بلا تنوين ولا «أل» ولا لاحقة جرٌّ أو نصب (إِسۡرَٰٓءِيلَ، إِبۡرَٰهِيمَ)،
    # إلا أن يكون مضافاً يليه معرَّف (كِتَٰبَ ٱللَّهِ)
    if c == 'نصب' and st and FATHA in st[-1][1] and not st[-1][1] & {FATHATAN} and \
            not any(sl['type'] == 'أل' for sl in seg['slots']) and seg['slots'][-1] is stem[-1]:
        nxt = a['segments'][wi + 1] if wi + 1 < len(a['segments']) else None
        mudaf = nxt is not None and any(sl['type'] in ('أل', 'لفظ الجلالة') or
                                        sl['type'] == 'مبني' and is_form(sl['text'], RELATIVES_V) for sl in nxt['slots'])
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
    # «ال» لم يفصلها المقطِّع قبل اللام (ٱلَّيۡلِ: لامُ التعريف ولامُ الكلمة لامٌ مشدَّدة)، والموصول مستثنى
    if stem:
        t0 = vtoks(stem[0]['text'])
        if len(t0) > 3 and t0[0][0] == 'ا' and not t0[0][1] and t0[1][0] == 'ل' and \
                (SHADDA in t0[1][1] or not t0[1][1] - {SUKUN} and SHADDA in t0[2][1]) and \
                not is_form(stem[0]['text'], RELATIVES_V):
            return True
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
    ism_text = a['segments'][ism_w]['slots'][t['slot']]['text']
    relative = is_form(ism_text, RELATIVES_V + ('مَا', 'مَنْ'))
    n = len(a['segments'])
    from .status import ACCEPTED
    first_pp = None
    w = ism_w + 1
    if _boundary_after(marks, ism_w):
        return None
    clause_w = {f['word_index'] for f in a['operators'] if f['group'] in CLAUSE_OPS and f.get('status') != 'blocked'}
    while w < n:
        if w > ism_w + 1 and (w in clause_w or clause_start(a, w)):
            break                                     # عامل تركيبٍ جديد أو ما له الصدارة: ما بعده لغيره
        seg = a['segments'][w]
        sl0 = seg['slots'][0]['text']
        # اللام المزحلقة على اسمٍ أو فعل، أو على ضمير الفصل المنفصل (لَهُوَ، لَهِيَ)؛ أما «لَكُمۡ، لَهُمۡ، لَهُۥ» فلام جرّ
        nxt_sl = seg['slots'][1] if len(seg['slots']) > 1 else None
        if grp == '2' and sl0 in ('لَ', 'لَّ') and nxt_sl is not None and \
                (nxt_sl['type'] != 'مبني' or is_form(nxt_sl['text'], ('هُوَ', 'هِيَ'))):
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
    if 3 <= len(st) <= 4 and all(m & {FATHA, DAMMA, KASRA} and not m & {SUKUN} for _, m in st) and \
            not any(L in 'اوي' and not m & {FATHA, DAMMA, KASRA} for L, m in st) and FATHA in st[-1][1]:
        return True
    # المضعَّف (مَرَّ، رَدَّ): حرفان آخرهما مشدَّدٌ مفتوح
    if len(st) == 2 and st[0][1] == {FATHA} and st[1][1] == {SHADDA, FATHA}:
        return True
    # الماضي وبعده ضمير مفعول (بَعَثَهُۥ، أَقۡبَرَهُۥ): يُفحص ما قبل الضمير
    from .cells import ENCLITICS_V
    for e in ENCLITICS_V:
        el = letters(e)
        if len(st) > len(el) + 2 and [L for L, _ in st[-len(el):]] == [L for L, _ in el] and \
                [m for _, m in st[-len(el):]] == [m for _, m in el] and FATHA in st[-len(el) - 1][1]:
            core = st[:-len(el)]
            if 3 <= len(core) <= 4 and all(m & {FATHA, DAMMA, KASRA} and not m & {SUKUN} for _, m in core) and \
                    not any(L in 'اوي' for L, _ in core):
                return True
            # أَفۡعَلَ: همزةٌ مفتوحة، فساكن، فمفتوحان (أَقۡبَرَهُۥ، أَنزَلَهُ)
            if len(core) == 4 and core[0][0] == 'أ' and core[0][1] == {FATHA} and SUKUN in core[1][1] and \
                    core[2][1] == {FATHA} and not any(L in 'اوي' for L, _ in core[1:]):
                return True
            break
    return False


def _hollow_madi(text):
    """الأجوف الماضي: فَاعَلَ بلا مقطع ثالث (زَادَ، قَالَ، جَاءَ)، وبعده ضميرٌ متصل أو لا (فَزَادَهُمُ)"""
    from .cells import ENCLITICS_V
    st = letters(text)
    if len(st) > 3 and st[0][0] in 'وف' and set(st[0][1]) == {FATHA}:
        st = st[1:]
    if len(st) > 3 and st[0][0] in 'أ' and set(st[0][1]) == {FATHA} and st[2][0] == 'ا':
        st = st[1:]                                    # أَفَالَ: الأجوف من أَفۡعَلَ (أَمَاتَهُۥ، أَقَامَ)
    # جَآءُوٓ، قَالُوٓا: واو الجماعة بعد الضمّ
    if len(st) >= 4 and set(st[0][1]) == {FATHA} and st[1][0] == 'ا' and not st[1][1] and DAMMA in st[2][1] and \
            ''.join(L for L, _ in st[3:]) in ('و', 'وا'):
        return True
    if len(st) < 3 or not (set(st[0][1]) == {FATHA} and st[1][0] == 'ا' and not st[1][1] and FATHA in st[2][1]):
        return False
    rest = ''.join(L + ''.join(sorted(m)) for L, m in st[3:])
    return not rest or is_form(rest, ENCLITICS_V)


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
        if len(sg['slots']) > 1 and is_form(sg['slots'][0]['text'], ('وَ', 'فَ')) and sg['slots'][0]['type'] != 'جذع':
            break
        time_adv = stem and is_form(stem[-1]['text'], TIME_V, i3rab=True)
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
    # علامات الوقف لا تدخل التحليل (حكم صاحب النظرية): الحدّ يُشتقّ من الخانات، والعلامات للتقييم وحده
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
            rel_ = r.get('role') or r.get('expected') or 'عمل'
            if src is dst:
                # العامل ومعموله في وحدةٍ لفظية واحدة (بِسۡمِ): الطرفان خانتان داخلها بهويتيهما، لا الوحدة نفسها
                ws_ = a['segments'][r['word_index']]['slots']
                a_id, b_id = f'{src.id}.s{r["slot"]}', f'{dst.id}.s{t["slot"]}'
                S.B.append((f'{rel_} (داخل الوحدة: «{ws_[r["slot"]]["text"]}» ← '
                            f'«{a["segments"][t["word_index"]]["slots"][t["slot"]]["text"]}»)', a_id, b_id, ob.ev))
                S.O.setdefault('inner', {})[a_id] = src.id
                S.O['inner'][b_id] = dst.id
            else:
                S.B.append((rel_, src.id, dst.id, ob.ev))
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
                    wsl = a['segments'][w]['slots']
                    # طرف الخبر رأسُ الكلمة (جذعها أو لفظ الجلالة)، لا آخر خاناتها: «لِيُعَذِّبَهُمۡ» رأسها الفعل لا «هُمۡ»
                    kslot = next((x for x in wsl if x['type'] in ('جذع', 'لفظ الجلالة')), wsl[-1])
                    prev_w = a['segments'][r['word_index'] - 1]['word'] if r['word_index'] > 0 else ''
                    if r['operator'] in ('كَانَ',) and len(wsl) > 1 and wsl[0]['type'] == 'عامل' and \
                            is_form(wsl[0]['text'], ('لِ',)) and is_form(prev_w, ('مَا', 'لَمْ'), prefix=True):
                        # لام الجحود بعد «ما كان» و«لم يكن»: اللام والفعل مصدرٌ مؤوَّل متعلّق بخبر «كان» المحذوف
                        # (مُرِيدًا، عند البصريين)، فالطرف الفعل رأسُ المصدر المؤوَّل، لا جملةٌ فعلية هي الخبر
                        kind = 'محذوف يتعلّق به المصدر المؤوَّل (لام الجحود)'
                        why = f'«{prev_w}» + «كان» + «{wsl[0]["text"]}» والمضارع: لام الجحود'
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
RELATIVES_V = ('الَّذِينَ', 'الَّذِي', 'الَّتِي', 'اللَّذَيْنِ', 'اللَّتَيْنِ', 'اللَّاتِي', 'الَّٰتِي', 'اللَّائِي', 'الَّٰٓئِي',
               'الَّذَانِ', 'اللَّذَانِ', 'الَّذَيْنِ')
COND_STRICT_V = ('أَيَّمَا', 'إِذَا', 'إِنْ', 'لَوْ', 'أَيْنَمَا', 'حَيْثُمَا', 'مَهْمَا', 'كُلَّمَا', 'إِذْمَا', 'مَتَى', 'مَتَىٰ', 'أَيَّانَ')
SADARA_V = ('إِنَّ', 'لَٰكِنَّ', 'لَكِنَّ', 'لَيْتَ', 'لَعَلَّ')   # «إنّ» المكسورة وأخواتها سوى «أنّ» و«كأنّ»
TIME_V = ('يَوْمَ', 'حِينَ', 'سَاعَةَ', 'لَيْلَةَ', 'غَدًا', 'ءَانَ', 'آنَ')
ZURUF_V = ('مَعَ', 'عِنْدَ', 'لَدَى', 'لَدَىٰ', 'لَدُنْ', 'فَوْقَ', 'تَحْتَ', 'بَيْنَ', 'قَبْلَ', 'بَعْدَ', 'أَمَامَ', 'خَلْفَ',
           'وَرَاءَ', 'دُونَ', 'حَوْلَ', 'قُدَّامَ', 'إِزَاءَ', 'تِلْقَاءَ')
VERBAL_OPS = {'10', '11', '12', '13'}            # كان وأخواتها، وأفعال المقاربة، والمدح والذم، وأفعال القلوب: أفعالٌ تبدأ جملة
JARR_V = ('بِ', 'لِ', 'لَ', 'لَّ', 'كَ', 'فِي', 'فِى', 'مِنْ', 'مِّنْ', 'عَلَى', 'عَلَىٰ', 'عَلَيْ', 'إِلَى', 'إِلَىٰ', 'إِلَيْ',
          'عَنْ', 'عِنْدَ', 'لَدَى', 'لَدَىٰ', 'لَدَيْ')
PRON_FREE_V = ('هُوَ', 'هِيَ', 'هُمْ', 'هُمَا', 'هُنَّ', 'أَنْتَ', 'أَنْتِ', 'أَنْتُمْ', 'أَنْتُمَا', 'أَنْتُنَّ', 'أَنَا', 'نَحْنُ')
QAWL_V = ('قَالَ', 'قَالُوا', 'قَالَتْ', 'قَالَتَا', 'قَالَا', 'قُلْنَ', 'قُلْتُ', 'قُلْتَ', 'قُلْتِ', 'قُلْنَا', 'قُلْتُمْ',
          'يَقُولُ', 'يَقُولَ', 'يَقُولُونَ', 'يَقُولُوا', 'يَقُولَا', 'يَقُولَانِ', 'تَقُولُ', 'تَقُولَ', 'تَقُولُونَ', 'تَقُولُوا',
          'نَقُولُ', 'نَقُولَ', 'أَقُولُ', 'أَقُولَ', 'قُلْ', 'قُولُوا', 'قُولِي', 'قِيلَ', 'يُقَالُ', 'يَقُلْ', 'نَادَى', 'نَادَىٰ',
          'نَادَوْا', 'يُنَادِي', 'يُنَادُونَ', 'وَصَّى', 'وَصَّىٰ', 'دَعَا', 'دَعَوْا', 'لَيَقُولُنَّ', 'لَيَقُولَنَّ', 'لَتَقُولُنَّ',
          'فَلْيَقُلْ', 'لِيَقُولُوا', 'لْيَقُولُوا', 'قَٰلَ', 'دَعَوُا', 'دَعَوَا', 'نَادَوْا', 'نَادَوا', 'يُنَادَوْنَ')


def _wasl_start(word):
    """الكلمة تبدأ بهمزة وصل: ألفٌ بلا حركة في أولها (ٱلۡ…)"""
    t = vtoks(word)
    return bool(t) and t[0][0] == 'ا' and not t[0][1]


# أدوات الشرط التي لا تلتبس بالموصول أو الاستفهام في الكتابة (ما ومن تلتبسان فتُترك)
CLAUSE_OPS = ('2', '5', '6', '7', '10')            # النواسخ، والنواصب، والجوازم، والشرط: تفتح تركيباً جديداً


def _bare_w(t):
    """الحروف وحدها، للعرض والمفاتيح فقط؛ ولا تُقارَن بها الكلمات (حكم صاحب النظرية: يُمنع تجريد الكلمة من الحركات)"""
    import re
    return re.sub('[^ء-ي]', '', t.replace('ٱ', 'ا'))


_VMARKS = {FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN, DAGGER_ALIF}
_CASE_MARKS = {FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN}


def vtoks(t):
    """الكلمة مشكولةً للمقارنة: حروفها وحركاتها كما كُتبت (ٱ ألفٌ، وتُترك علامات الضبط القرآني التي ليست حركات)"""
    return [(L, frozenset(m & _VMARKS)) for L, m in letters(t.replace('ٱ', 'ا'))]


def is_form(t, forms, i3rab=False, prefix=False):
    """هل الكلمة t إحدى الصيغ المشكولة forms، حرفاً وحركة؟ لا تجريد. ويُقبل في الحرف الأخير وحده:
    - حركة التقاء الساكنين المكتوبة مكان السكون في الصيغة (هُمُ، مَنِ، قُلِ، عَنِ)
    - وحركة الإعراب أيّاً كانت إن كانت الصيغة معربة (i3rab: الظروف)
    prefix: تُقبل الواو أو الفاء المفتوحة قبلها (وَمَن، فَقَدۡ)"""
    tt = vtoks(t)
    # الشدّة على أول الكلمة علامةُ إدغامٍ من الكلمة قبلها (نَّحۡنُ، وَّقَالُواْ): مكتوبةٌ على الحدّ لا من حركات الكلمة
    if tt and SHADDA in tt[0][1]:
        tt = [(tt[0][0], tt[0][1] - {SHADDA})] + tt[1:]
    cands = [tt]
    if prefix and len(tt) > 1 and tt[0][0] in 'وف' and tt[0][1] == {FATHA}:
        cands.append(tt[1:])
    for f in forms:
        ff = vtoks(f)
        for c in cands:
            if len(c) != len(ff) or any(a != b for a, b in zip(c[:-1], ff[:-1])) or c[-1][0] != ff[-1][0]:
                continue
            lm, fm = c[-1][1], ff[-1][1]
            if lm == fm or fm == {SUKUN} and len(lm) == 1 and lm <= {FATHA, DAMMA, KASRA} or \
                    i3rab and (lm - _CASE_MARKS) == (fm - _CASE_MARKS):
                return True
    return False


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
    # مدى بداية الآية التالية: إلى ما قبل أول كلمةٍ لها الصدارة (فلا يعمل ما بعدها فيما قبلها)، أو آخرها.
    # (علامات الوقف لا تدخل التحليل)
    first_b = next((i - 1 for i in range(1, len(na['segments'])) if clause_start(na, i)), len(na['segments']) - 1)
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
    kaf = jar0 is not None and is_form(jar0['operator'], ('كَ',))
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
    w0 = na['segments'][0]['word']
    tgt = (pid(last_nuc['word_index'], last_nuc['slot']) if last_nuc else prev['units'][max(prev['units'])].id)
    if is_form(w0, ('إِلَّا',)):
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
    c0 = word_case(na, 0, verbs_n) if 0 not in gov_n and noun_evidence(seg0, len(na['segments']) > 1 and _wasl_start(na['segments'][1]['word'])) and not voc else None
    # الواو والفاء في أول الكلمة، مبنيّاً كان في المقشِّر أو عاملاً مؤجَّلاً (واو القسم)
    conj = len(na['segments'][0]['slots']) > 1 and is_form(na['segments'][0]['slots'][0]['text'], ('وَ', 'فَ'))
    if c0:
        verbs_p = {g['word_index'] for g in pa.get('agreement', [])}
        AMB = ('جر أو نصب', 'نصب أو جر')
        same = next((w for w in range(n1 - 1, -1, -1) if noun_evidence(pa['segments'][w], w + 1 < n1 and _wasl_start(pa['segments'][w + 1]['word'])) and (
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
        time_adv = is_form(seg0['slots'][-1]['text'], TIME_V, i3rab=True)
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
    if is_form(w0, RELATIVES_V):
        out.append(dict(src=prev['units'][max(prev['units'])].id, dst=nid(0, 0), rel='نعت أو بدل أو ابتداء',
                        proven=False, rule='اسم موصول في أول الآية: قد يكون تابعاً لما قبله، وقد يكون مبتدأ'))
    # شرطٌ لا جواب له في آيته
    for f in pa['operators']:
        if f['group'] == '7' and f.get('status') != 'blocked' and is_form(f['operator'], COND_STRICT_V):
            after = [g for g in pa.get('agreement', []) if g['word_index'] > f['word_index']]
            later_b = any(clause_start(pa, w) for w in range(f['word_index'] + 1, n1))
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


READINGS = ('حفص عن عاصم (مصحف المجمّع)',)


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
    if not isinstance(q, str) or q not in READINGS:
        raise ValueError(f'قراءةٌ غير معرَّفة في سجل الحدّ: {q!r}')   # فاحص المخطط: q من القراءات المعرَّفة
    return dict(location=loc, F=F, L=L, Lp=Lp, L_checked=L_checked, M=M, W=W, I=I, E=E, category=cat, a=a_id, q=q,
                mark=mark, ayah_end=ayah_end)


def clause_start(a, wi):
    """ما يبدأ به الكلام في أول الكلمة wi وله الصدارة، فلا يعمل فيه ما قبله ولا يكون من جملةٍ قبله إلا معطوفاً:
    → (النوع، بعد حرف عطف؟) أو None. الأنواع: ناسخ، استفهام، نداء، شرط، تنبيه.
    - «إِنَّ» وكأنّ ولكنّ وليت ولعلّ عاملاً مقبولاً في أول الكلمة (لا «أَنَّ»)
    - الاستفهام: هَلۡ، والهمزة المفتوحة قبل فاء أو واو مفتوحتين (أَفَلَا، أَوَلَمۡ)، أو قبل «لَمۡ» (أَلَمۡ)، أو قبل همزة (أَءِنَّكُمۡ)
    - النداء: ياءٌ بعدها ألف أو خنجرية في أول الكلمة (يَٰقَوۡمِ، يَٰٓأَيُّهَا)
    - الشرط الذي لا يلتبس بالموصول (COND_STRICT_V)
    - التنبيه: أَلَا"""
    from .status import ACCEPTED
    seg = a['segments'][wi]
    word = seg['word']
    toks = letters(word)
    conj = len(seg['slots']) > 1 and seg['slots'][0]['type'] != 'جذع' and is_form(seg['slots'][0]['text'], ('وَ', 'فَ'))
    rest = word
    if conj:
        toks = toks[1:]
        rest = word[len(seg['slots'][0]['text']):]
    ops = [f for f in a['operators'] if f['word_index'] == wi and f.get('status') != 'blocked']
    for f in ops:
        if f['group'] == '2' and f.get('status') == ACCEPTED and is_form(f['operator'], SADARA_V):
            return ('ناسخ له الصدارة', conj)
        if f['group'] in ('6', '7') and is_form(f['operator'], COND_STRICT_V):
            return ('شرط', conj)                      # «إِنْ» الشرطية في باب الجزم (6)، وسائر الأدوات في باب الشرط (7)
    if not toks:
        return None
    L0, m0 = toks[0]
    if is_form(rest, ('هَلْ',)) or len(toks) > 2 and toks[0][0] == 'ه' and toks[0][1] == {FATHA} and toks[1][0] == 'ل' \
            and toks[1][1] == {SUKUN} and len(seg['slots']) > 1:
        return ('استفهام', conj)
    if is_form(rest, ('لَئِنْ',)):
        return ('شرط', conj)                          # اللام الموطِّئة للقسم و«إنْ»
    if L0 in 'أء' and FATHA in m0 and len(toks) > 2:
        L1, m1 = toks[1]
        if L1 == 'آ':
            return ('استفهام', conj)                  # ءَآللَّهُ، ءَآلۡـَٰٔنَ: همزة الاستفهام قبل همزة الوصل الممدودة
        madd_verb = len(toks) > 3 and toks[2][0] == 'ا' and not toks[2][1] and toks[3][1] & {FATHA, DAMMA, KASRA}
        if L1 in 'فو' and FATHA in m1 and SHADDA not in m1 and not madd_verb or L1 in 'ءأإ' or \
                L1 == 'ل' and toks[2][0] == 'م' and len(toks) == 3 and SUKUN in toks[2][1]:
            return ('استفهام', conj)
        if L1 == 'ل' and FATHA in m1 and SHADDA not in m1 and toks[2][0] == 'ا' and len(toks) <= 4:
            return ('تنبيه', conj)
    if L0 == 'ي' and len(toks) > 2 and (DAGGER_ALIF in m0 or toks[1][0] == 'ا'):
        return ('نداء', conj)
    return None


def _maqsur(st):
    """آخره ألفٌ مقصورة (ضُحَى، وفي «ضُحَىٰهَا» آخر الجذع قبل الضمير): لا تظهر عليه حركة الإعراب"""
    return bool(st) and (st[-1][0] == 'ى' or st[-1][0] == 'ا' and not st[-1][1] and len(st) > 2 and FATHA in st[-2][1]
                         and not st[-2][1] & {FATHATAN})


def word_feats(a):
    from .affix import stem_info
    """سمات الكلمة المكتوبة اللازمة لعلاقات الجملة التالية R(G, Q, c) (حكم صاحب النظرية في الصفة والحال والاستئناف):
    conj حرف عطف (و، ف) في أولها مقطَّعاً؛ nakira اسمٌ عليه تنوين بلا «أل»؛ verb نوع الفعل (madi، mudari، amr) وشخصه؛
    qad «قد»؛ rel اسم موصول؛ case الحالة المكتوبة"""
    verbs = {g['word_index']: g for g in a.get('agreement', [])}
    out = []
    for wi, seg in enumerate(a['segments']):
        sl = seg['slots']
        conj = len(sl) > 1 and sl[0]['type'] != 'جذع' and is_form(sl[0]['text'], ('وَ', 'فَ'))
        st = letters(seg['word'])
        w_ = seg['word']
        tanwin = any(m & {FATHATAN, DAMMATAN, KASRATAN} for _, m in st)
        has_al = any(x['type'] in ('أل', 'لفظ الجلالة') for x in sl)
        g = verbs.get(wi)
        standalone = 'أو' if is_form(w_, ('أَوْ',)) else 'ثم' if is_form(w_, ('ثُمَّ',)) else \
            'أم' if is_form(w_, ('أَمْ',)) else None
        if standalone and not conj:
            conj = True                               # «أَوۡ» و«ثُمَّ» كلمتان مستقلتان، و«ثُمَّ» كالفاء (حكم صاحب النظرية)
        # واوٌ أو فاء ملتصقة بضمير رفعٍ منفصل (فَهِيَ، وَهُمۡ): الضمير لا يبدأ بهما، فهما عاطفتان
        if not conj and len(st) > 2 and st[0][0] in 'وف' and set(st[0][1]) == {FATHA} and is_form(w_[2:], PRON_FREE_V):
            conj, sl0 = True, st[0][0]
        else:
            sl0 = None
        out.append(dict(
            conj=conj, conj_letter=(standalone or sl0 or sl[0]['text'][:1]) if conj else None,
            # «مَن» و«ما» تكونان شرطاً فتطلبان جواباً بالفاء (وَمَن شَآءَ فَلۡيَكۡفُرۡ)، أو موصولاً أو غيره
            cond_amb=is_form(w_, ('مَنْ', 'مَا', 'مَهْمَا'), prefix=True),
            neg=is_form(w_, ('مَا', 'لَا', 'لَمْ', 'لَنْ', 'لَمَّا'), prefix=True),
            ops=[f['group'] for f in a['operators'] if f['word_index'] == wi and f.get('status') != 'blocked'],
            # أول المعطوف: فعل، أو مرفوع، أو ضمير منفصل، أو شبه جملة (جارٌّ في أوله بعد العاطف): بداية جملة
            head=('pron' if is_form(w_, PRON_FREE_V, prefix=True) else
                  'pp' if any(x['type'] == 'عامل' and is_form(x['text'], JARR_V)
                              for x in sl[1 if conj and len(sl) > 1 else 0:2]) else None),
            first=st[0][0] if st else '', first_fatha=bool(st) and FATHA in st[0][1],
            nakira=tanwin and not has_al and noun_evidence(seg), noun=noun_evidence(seg),
            verb=g['kind'] if g else None, person=(g['features'][0][0] if g and g.get('features') else None),
            qad=is_form(w_, ('قَدْ', 'لَقَدْ'), prefix=True), rel=is_form(w_, RELATIVES_V, prefix=True),
            case=word_case(a, wi, set(verbs)) if not g else None,
            text=w_, agr=[tuple(x) for x in g['features']] if g and g.get('features') else [],
            prons=[x['text'] for x in sl[1:] if x['type'] == 'مبني'],
            rel_agr=next((v for k, v in RELATIVE_AGR.items() if is_form(w_, (k,), prefix=True)), None),
            zarf=any(x['type'] == 'جذع' and is_form(x['text'], ZURUF_V, i3rab=True) for x in sl),
            mood=(stem_info(next((x['text'] for x in sl if x['type'] == 'جذع'), w_)).get('mood') if g and g['kind'] == 'mudari' else None),
            lam_fatha=len(sl) > 1 and is_form(sl[0]['text'], ('لَ',)),
            amma=is_form(w_, ('أَمَّا', 'إِمَّا'), prefix=True),
            an=is_form(w_, ('أَنْ',), prefix=True),
            # صورة الفعل بالمقشِّر (يَهۡدِي، يَشۡعُرُونَ) وإن لم تثبت فعليته بالإسناد: تكفي دليلاً على جملةٍ بعد النفي والشرط
            vshape=(stem_info(next((x['text'] for x in sl if x['type'] == 'جذع'), w_).replace(DAGGER_ALIF, 'ا')).get('kind')
                    if not g else g['kind']),
            # آخره ألفٌ مقصورة: لا تظهر عليه حركة الإعراب، فيوافق كل حالة
            maqsur=_maqsur(st) or _maqsur(letters(next((x['text'] for x in sl if x['type'] == 'جذع'), ''))),
            al=has_al, segs=[(x['type'], x['text']) for x in sl],
            demo=is_form(w_, ('أُولَٰئِكَ', 'أُولَئِكَ', 'أُلَٰئِكَ', 'أُلَئِكَ', 'ذَٰلِكَ', 'ذَلِكَ', 'تِلْكَ', 'هَٰذَا', 'هَذَا', 'هَٰذِهِ', 'هَٰؤُلَاءِ'), prefix=True)))
    return out


# الموصول الاسمي ← (العدد، النوع) لمطابقة العائد
RELATIVE_AGR = {'الَّذِي': ('singular', 'masc'), 'الَّتِي': ('singular', 'fem'), 'الَّذِينَ': ('plural', 'masc'),
                'اللَّذَانِ': ('dual', 'masc'), 'اللَّذَيْنِ': ('dual', 'masc'), 'الَّذَانِ': ('dual', 'masc'),
                'الَّذَيْنِ': ('dual', 'masc'), 'اللَّتَانِ': ('dual', 'fem'), 'اللَّتَيْنِ': ('dual', 'fem'),
                'اللَّاتِي': ('plural', 'fem'), 'الَّٰتِي': ('plural', 'fem'), 'اللَّائِي': ('plural', 'fem'), 'الَّٰٓئِي': ('plural', 'fem')}
# ضمير الغائب المتصل ← (العدد، النوع): العائد في الصلة
PRON_AGR = {'هُ': ('singular', 'masc'), 'هِ': ('singular', 'masc'), 'هُو': ('singular', 'masc'), 'هِي': ('singular', 'masc'),
            'هَا': ('singular', 'fem'), 'هُمْ': ('plural', 'masc'), 'هِمْ': ('plural', 'masc'), 'هُمَا': ('dual', None),
            'هِمَا': ('dual', None), 'هُنَّ': ('plural', 'fem'), 'هِنَّ': ('plural', 'fem')}
PRON_FREE_AGR = {'هُوَ': ('singular', 'masc'), 'هِيَ': ('singular', 'fem'), 'هُمْ': ('plural', 'masc'), 'هُمَا': ('dual', None),
                 'هُنَّ': ('plural', 'fem')}


def _agrees(want, got):
    """(العدد، النوع) للموصول مطابقٌ لما في العائد؛ والنوع غير المعيَّن لا يعارض"""
    return want[0] == got[0] and (got[1] is None or want[1] is None or want[1] == got[1])


def relative_structs(feats, nuc_pos, starts):
    """N = Relative_e(M, Q, ρ) لكل موصولٍ اسمي (حكم صاحب النظرية؛ الأصول من ابن عقيل):
    - الموصول الاسمي (الذي، التي، الذين، اللذان، اللاتي…) يفتح التزامين لازمين: «الصلة» و«العائد»؛ و«مَن» و«ما»
      لا يُفتح لهما شيء حتى يثبت أنهما موصولتان (قد تكونان شرطيتين أو استفهاميتين)
    - الصلة: جملةٌ فعلية خبرية (فعلٌ غير أمر)، أو اسمية (ضمير منفصل أو مرفوع أوّلها)، أو شبه جملة (جارّ أو ظرف)
    - نطاقها: من بعد الموصول إلى أول ما له الصدارة، أو عاطفٍ يبدأ جملة بعد نواة الصلة، أو نواةٍ ثانية بلا عاطف
    - العائد: فاعل الفعل للغائب مطابقاً للموصول عدداً ونوعاً، أو ضميرٌ متصل في الصلة مطابق، أو ضميرٌ منفصل
      مطابق في الاسمية؛ وفي شبه الجملة مستترٌ في متعلَّقها؛ وإن كان الفعل متعدياً لم يُذكر مفعوله فالعائد المنصوب
      محذوفٌ بقاعدة (حذف العائد المنصوب بفعلٍ تام)، وإلا بقي العائد مفتوحاً، ولا يُجعل الغياب شهادةَ حذف
    → [dict(kind, head, start, end, obligations=[(الاسم، مستوفى؟، الدليل)])]؛ end أول كلمة بعد الصلة"""
    out = []
    n = len(feats)
    for m in range(n - 1):
        want = feats[m].get('rel_agr')
        if not want:
            continue
        q = m + 1
        g = feats[q]
        # نطاق الصلة
        first_nuc = next((k for k in range(q, n) if k in nuc_pos or feats[k]['verb']), None)
        end = q + 1
        while end < n and end - q < 12:
            f = feats[end]
            # الصلة تنتهي عند موصولٍ آخر، أو ما له الصدارة، أو فاء، أو عاطفٍ لا يليه اسمٌ بدليله المكتوب (المعطوف المفرد
            # داخل الصلة: بِٱلَّيۡلِ وَٱلنَّهَارِ)، أو نواةٍ ثانية بلا عاطف
            if f.get('rel_agr') or starts[end] or f['conj'] and (f['conj_letter'] != 'و' or not f.get('noun')) or \
                    (end in nuc_pos or f['verb']) and first_nuc is not None and end > first_nuc and not f['conj']:
                break
            end += 1
        span = range(q, end)
        obl = []
        kind = None
        if g['verb'] and g['verb'] != 'amr' or q in nuc_pos:
            kind = 'جملة فعلية'
        elif g.get('head') == 'pron' or g['case'] == 'رفع' and not g['conj']:
            kind = 'جملة اسمية'
        elif g.get('head') == 'pp' or g.get('zarf'):
            kind = 'شبه جملة'
        elif g.get('neg') or g.get('qad'):
            kind = 'جملة فعلية' if any(feats[k]['verb'] for k in span) else None
        obl.append(('صلة', kind is not None, f'{kind} بعد الموصول' if kind else 'لم يُكشف ما يصلح صلةً'))
        rho = None
        if kind == 'جملة فعلية':
            v = next((k for k in span if feats[k]['verb'] or k in nuc_pos), None)
            if v is not None and any(x[0] == 3 and _agrees(want, (x[1], x[2])) for x in feats[v]['agr']):
                rho = f'فاعل «{feats[v]["text"]}» المستتر أو المتصل للغائب، مطابقٌ للموصول'
        if rho is None and kind in ('جملة فعلية', 'جملة اسمية'):
            for k in span:
                for pr in feats[k]['prons']:
                    got = next((v for f_, v in PRON_AGR.items() if is_form(pr, (f_,))), None)
                    if got and _agrees(want, got):
                        rho = f'الضمير «{pr}» في «{feats[k]["text"]}» مطابقٌ للموصول'
                        break
                if rho:
                    break
                got = next((v for f_, v in PRON_FREE_AGR.items() if is_form(feats[k]['text'], (f_,), prefix=True)), None)
                if got and _agrees(want, got):
                    rho = f'الضمير المنفصل «{feats[k]["text"]}» مطابقٌ للموصول'
                    break
        if rho is None and kind == 'شبه جملة':
            rho = 'مستترٌ في متعلَّق شبه الجملة (استقرّ)'
        if rho is None and kind == 'جملة فعلية':
            v = next((k for k in span if feats[k]['verb']), None)
            if v is not None and feats[v]['verb'] != 'amr' and not feats[v]['prons'] and \
                    not any(feats[k]['case'] == 'نصب' and feats[k].get('noun') for k in span if k > v):
                rho = f'عائدٌ منصوب محذوف بعد «{feats[v]["text"]}» (حذف العائد المنصوب بفعلٍ تام)'
        obl.append(('عائد', rho is not None, rho or 'لم يُكشف العائد، ولا قاعدة حذفٍ منطبقة'))
        out.append(dict(kind='صلة', head=m, start=q, end=end, silah=kind, obligations=obl))
    return out


COND_JAZM = ('إِنْ', 'مَنْ', 'مَا', 'مَهْمَا', 'أَيْنَمَا', 'حَيْثُمَا', 'مَتَى', 'مَتَىٰ', 'أَيَّانَ', 'أَيَّمَا', 'إِذْمَا')
COND_NONJAZM = ('إِذَا', 'لَوْ', 'لَمَّا', 'كُلَّمَا', 'لَئِنْ')


def _lam_madi(word):
    """لامٌ مفتوحة على ماضٍ (لَذَهَبَ، لَٱتَّبَعۡنَٰكُمۡ): جواب «لو» — اللام مكتوبةٌ بفتحتها، وما بعدها على صورة الماضي"""
    from .affix import stem_info
    t = letters(word)
    if len(t) < 4 or t[0][0] != 'ل' or set(t[0][1]) != {FATHA}:
        return False
    rest = word[2:] if word[1:2] == FATHA else word[1:]
    for suf in ('هُمْ', 'هُمُ', 'كُمْ', 'كُمُ', 'هَا', 'نَا', 'هُ', 'كَ'):
        if rest.endswith(suf) and len(letters(rest)) - len(letters(suf)) >= 3:
            rest = rest[:-len(suf)]                    # لَجَعَلَهُۥ: الضمير المتصل مفعول
            break
    return stem_info(rest).get('kind') == 'madi' or _madi_like(rest)


def cond_structs(feats, nuc_pos, starts, ay_end=None):
    """G = Cond_t,e(S, Q) لكل أداة شرط (حكم صاحب النظرية؛ الأصول من ابن عقيل):
    - الأداة: ما له صدارة الشرط (إِنْ، إِذَا، لَوْ، لَئِنْ، أَيْنَمَا…)، و«لَمَّا» يليها ماضٍ، و«مَن، ما، مهما» يليها فعل
      (وهذه تبقى بقراءتيها: شرطية أو موصولة/استفهامية)
    - تفتح التزامين: «فعل الشرط» (أول فعلٍ بعدها) و«الجواب»
    - الجواب: كلمةٌ بفاءٍ رابطة بعد جملة الشرط (فاء الجواب لا عاطفة)؛ أو مع «لَوْ» لامٌ مفتوحة على فعل (لَذَهَبَ)؛
      أو مع الجازمة مضارعٌ مجزوم بلا عاطف. وما سوى ذلك (نواةٌ بلا دليل الربط) جوابٌ محتمل لا مستوفى
    - لا يُحكم بحذف الجواب لغيابه؛ وإن سبقت الأداةَ جملةٌ تامّة فقد يكون ما قبلها دليلَ الجواب، وهي قراءةٌ محفوظة
    → [dict(kind='شرط', head, tool, s_pos, q_pos, q_kind, obligations)]"""
    out = []
    n = len(feats)
    for t in range(n - 1):
        f = feats[t]
        text = f['text']
        strict = starts[t] and starts[t][0] == 'شرط'
        lamma = is_form(text, ('لَمَّا',), prefix=True) and feats[t + 1]['verb'] == 'madi'
        amb = f.get('cond_amb') and (feats[t + 1]['verb'] or t + 1 in nuc_pos)
        if not (strict or lamma or amb):
            continue
        jazm = is_form(text, COND_JAZM, prefix=True)
        tool = next((x for x in COND_JAZM + COND_NONJAZM if is_form(text, (x,), prefix=True)), text)
        # رأس جملة الشرط: الكلمة التي تلي الأداة (بعد «ما» الزائدة: إِذَا مَا دُعُواْ)، فعلاً ثبتت فعليته أو بصورته
        # (وَإِذَا قِيلَ: «قِيلَ» رأسها وإن لم تثبت فعليته بالإسناد، فلا يُتخطّى إلى «لَا تُفۡسِدُواْ» داخل المقول).
        # فإن كان اسماً بدليله (إِذَا ٱلسَّمَآءُ ٱنشَقَّتۡ) فالفعل بعده، ولا يُتجاوز نفيٌ أو ما له الصدارة
        h1 = t + 2 if t + 2 < n and is_form(feats[t + 1]['text'], ('مَا',)) and tool in ('إِذَا', 'إِنْ', 'أَيْنَمَا') else t + 1
        g1 = feats[h1]
        neg_s = None
        if is_form(g1['text'], ('لَمْ', 'لَا', 'مَا', 'لَنْ'), prefix=True) and h1 + 1 < n:
            # جملة الشرط منفيّة (فَإِن لَّمۡ تَفۡعَلُواْ): S = Negation(لم، الجملة الفعلية)، ورأسها الفعل بعد النفي
            neg_s, h1 = g1['text'], h1 + 1
            g1 = feats[h1]
        if g1.get('noun') and not g1['verb'] and h1 not in nuc_pos:
            s_pos = next((k for k in range(h1 + 1, min(n, h1 + 4)) if feats[k]['verb'] or k in nuc_pos), None)
            if s_pos is not None and any(starts[j] or feats[j].get('neg') for j in range(h1 + 1, s_pos)):
                s_pos = None
        else:
            s_pos = h1
        # الجازمة يليها مضارعٌ مرفوع أو منصوب كتابةً (ثبوت النون، الضمة): ليست شرطية هنا (وَمَا يَخۡدَعُونَ: نافية)
        if jazm and s_pos is not None:
            from .affix import stem_info as _si
            sx = _si(feats[s_pos]['text'])
            mood = feats[s_pos].get('mood') or sx.get('mood')
            if (feats[s_pos]['verb'] == 'mudari' or sx.get('kind') == 'mudari') and \
                    (mood in ('رفع', 'نصب') or sx.get('suffix') == 'نون الرفع'):
                continue
        # الفعلية تثبت بدليلٍ موجب (الإسناد، أو النواة، أو صورة الفعل الصرفية)، لا بغياب دليل الاسمية: فما يلي الأداة
        # بلا دليلٍ موجب مرشَّحٌ تفتحه البيئة النحوية (الأداة تطلب فعلاً)، ونوعه غير محسوم (مراجعة التقرير الثالثة ٢)
        s_verb = s_pos is not None and bool(feats[s_pos]['verb'] or s_pos in nuc_pos or feats[s_pos].get('vshape'))
        obl = [('فعل الشرط', bool(s_verb),
                (f'منفيٌّ بـ«{neg_s}»: ' if neg_s else '') +
                f'«{feats[s_pos]["text"]}»' + ('' if feats[s_pos]['verb'] or s_pos in nuc_pos else ' (بصورة الفعل الصرفية)' if feats[s_pos].get('vshape') else
                 ' مرشَّحٌ يلي الأداة، ولم تثبت فعليته بدليلٍ موجب')
                if s_pos is not None else 'لم يُكشف فعل الشرط')]
        q_pos, q_kind = None, None
        if True:
            # يُبحث عن دليل ربط الجواب ولو لم يُكشف فعل الشرط (وَلَوۡ شَآءَ ٱللَّهُ لَذَهَبَ)
            # ملكية الجواب (مراجعة التقرير الثانية ٥): لا يُستوفى الجواب بفاءٍ لاحقة إلا إن كانت لهذا الشرط: فالفاء
            # الداخلة على شرطٍ جديد (فَإِن لَّمۡ تَفۡعَلُواْ) ليست جوابه، وأداةُ شرطٍ قبل الجواب جوابُها أولى بما بعدها؛
            # و«ما/مَن» المحتملة لا يُتجاوز بجوابها آخرُ الآية ولا جملةٌ معطوفة
            for k in range((s_pos if s_pos is not None else t) + 1, min(n, t + 30)):
                g = feats[k]
                if starts[k] and starts[k][0] == 'شرط':
                    break                              # شرطٌ جديد (ولو بفاء): ليس جواب هذا
                if starts[k] and not (g['conj'] and g['conj_letter'] == 'ف'):
                    break                              # ما له الصدارة: الجواب لم يأتِ قبله
                if tool in ('إِذَا', 'لَمَّا') and s_pos is not None and k > s_pos + 1 and not g['conj'] and \
                        (g['verb'] == 'madi' or g.get('vshape') == 'madi' and not g.get('noun') or
                         not g['verb'] and not g.get('noun') and _madi_like(g['text'])):
                    q_pos, q_kind = k, f'ماضٍ بعد جملة الشرط في جواب «{tool}»'
                    break                              # فَلَمَّآ أَضَآءَتۡ … ذَهَبَ: قبل أي فاءٍ بعده
                if g['conj'] and g['conj_letter'] == 'ف':
                    q_pos, q_kind = k, 'فاءٌ رابطة للجواب'
                    break
                if amb and not strict and (ay_end and ay_end[k - 1] or
                                           g['conj'] and g['conj_letter'] in ('و', 'ثم') and clause_word(feats, k, nuc_pos)):
                    break
                if tool == 'لَوْ' and (g.get('lam_fatha') and (g['verb'] or k in nuc_pos) or _lam_madi(g['text'])):
                    q_pos, q_kind = k, 'لامٌ مفتوحة على الفعل في جواب «لو»'
                    break
                if jazm and g['verb'] == 'mudari' and g.get('mood') == 'جزم' and not g['conj']:
                    q_pos, q_kind = k, 'مضارعٌ مجزوم في جواب الجازمة'
                    break
                if g['conj'] and g['conj_letter'] in ('و', 'ثم', 'أو'):
                    continue                           # معطوفٌ على فعل الشرط
            # جواب «إِذَا» ماضٍ بعد جملة الشرط بلا عاطف (حكم صاحب النظرية: وَإِذَا قِيلَ لَهُمۡ … قَالُوٓاْ)
            if q_pos is None and tool == 'إِذَا' and s_pos is not None:
                k = next((k for k in range(s_pos + 1, min(n, s_pos + 30))
                          if feats[k]['verb'] == 'madi' and not feats[k]['conj'] and not starts[k]), None)
                if k is not None and not any(starts[j] for j in range(s_pos + 1, k)):
                    q_pos, q_kind = k, 'ماضٍ بعد جملة الشرط في جواب «إذا»'
            cand = None
            if q_pos is None and s_pos is not None:
                cand = next((k for k in range(s_pos + 1, min(n, s_pos + 30))
                             if (feats[k]['verb'] or k in nuc_pos) and not feats[k]['conj']), None)
                if cand is not None:
                    q_kind = f'جوابٌ محتمل: «{feats[cand]["text"]}» (نواةٌ بلا دليل ربط)'
        if amb and not strict and q_pos is None:
            continue                                   # «ما/مَن» بلا جوابٍ مملوك: لا قراءة شرطية (فَمَا رَبِحَت: نافية)
        if q_pos is None and t > 0 and any(k in nuc_pos for k in range(max(0, t - 6), t)) and \
                (t + 1 >= n or any(starts[k] and starts[k][0] == 'شرط' for k in range((s_pos or t) + 1, min(n, (s_pos or t) + 6)))
                 or ay_end and s_pos is not None and any(ay_end[k] for k in range(s_pos, min(n, s_pos + 4)))):
            # بعد جملةٍ تامّة، ولا جواب قبل شرطٍ جديد أو آخر الآية (إِن كُنتُمۡ صَٰدِقِينَ): جوابٌ محذوف يدلّ عليه ما قبله،
            # قراءةٌ مرشَّحة لا مستوفاة (لا يُحكم بالحذف إلا بدليل، والدليل هنا ما قبل الأداة)
            q_kind = 'جوابٌ محذوف مرشَّح يدلّ عليه ما قبل الأداة'
        if q_pos is not None and not s_verb:
            # صلاحية الكلمة جواباً غير ثبوت أنها جوابٌ لهذا الشرط: ورأس الشرط نفسه مؤجَّل (مراجعة التقرير الرابعة ١)
            obl.append(('الجواب', False, f'مرشَّح: {q_kind}، مشروطٌ بثبوت فعل الشرط'))
        else:
            obl.append(('الجواب', q_pos is not None, q_kind or 'لم يُكشف الجواب، ولا يُحكم بحذفه بلا دليل'))
        # نطاق الحدّ المحتمل حين لم يُستوفَ الجواب: إلى الجواب المحتمل، أو أول ما له الصدارة، أو ثماني كلمات
        nxt_start = next((k for k in range((s_pos or t) + 1, min(n, t + 8)) if starts[k]), min(n, t + 8))
        stop = min(cand, nxt_start) if cand is not None else nxt_start
        out.append(dict(kind='شرط', head=t, tool=tool, s_pos=s_pos, q_pos=q_pos, q_kind=q_kind, open_to=stop,
                        amb=bool(amb and not strict),
                        obligations=obl))
    return out


# شواهد مواصفة حدود العطف: تُحفظ سجلاتها كاملةً في كل تشغيل
COORD_WATCH = {'55:5', '80:32', '80:21', '2:4', '2:6', '2:259', '91:1', '91:2', '12:16', '2:25', '2:9'}
COORD_EFFECT = {'و': 'مطلق الجمع (لا يثبت به ترتيب)', 'ف': 'الترتيب والتعقيب', 'ثم': 'الترتيب والتراخي',
                'أم': 'المعادلة بعد همزة التسوية أو الاستفهام (أَمۡ المتصلة)',
                'أو': 'التخيير أو الإباحة أو الشك، بحسب السياق'}
CASE_COMPAT = {'رفع': {'رفع'}, 'نصب': {'نصب', 'جر أو نصب', 'نصب أو جر'}, 'جر': {'جر', 'جر أو نصب', 'نصب أو جر'},
               'جر أو نصب': {'جر', 'نصب', 'جر أو نصب', 'نصب أو جر'}, 'نصب أو جر': {'جر', 'نصب', 'جر أو نصب', 'نصب أو جر'}}


# شبه جملةٍ في كلمة واحدة: جارٌّ وضميرٌ متصل (لَهُمۡ، عَلَيۡهِمۡ)، أو جارٌّ مدغمٌ في «ما» (مِمَّا، عَمَّا)
PP_WORD_V = tuple(b + p for b in ('لَ', 'لِ', 'بِ', 'عَلَيْ', 'إِلَيْ', 'عَنْ', 'مِنْ', 'فِي', 'لَدَيْ', 'عِنْدَ', 'مَعَ')
                  for p in ('هُ', 'هِ', 'هَا', 'هُمْ', 'هِمْ', 'هُمَا', 'هِمَا', 'هُنَّ', 'هِنَّ', 'كَ', 'كِ', 'كُمْ', 'كُمَا',
                            'كُنَّ', 'نَا')) + ('لِي', 'بِي', 'مِنِّي', 'عَنِّي', 'مِمَّا', 'عَمَّا', 'فِيمَا', 'بِمَا', 'لِمَا', 'مِمَّنْ')
ISTIDRAK_V = ('لَٰكِنْ', 'لَكِنْ', 'لَٰكِنَّ', 'لَكِنَّ', 'بَلْ')


def _pp_like(g):
    """شبه جملةٍ في كلمة: جارٌّ مقطَّع، أو جارٌّ وضمير، أو جذعٌ أوله لامٌ أو باءٌ مكسورة ومجرورٌ (وَلِأَنۡعَٰمِكُمۡ)"""
    if g.get('head') == 'pp' or is_form(g['text'], PP_WORD_V, prefix=True):
        return True
    stem = next((x[1] for x in (g.get('segs') or []) if x[0] == 'جذع'), '')
    st = letters(stem)
    return g['case'] == 'جر' and len(st) > 3 and st[0][0] in 'لب' and st[0][1] == {KASRA}


def clause_word(feats, h, nuc_pos):
    """أول المعطوف يبدأ جملةً بنفسه: فعلٌ (ثابت أو بصورته)، أو ما له الصدارة أو ناسخ، أو «أَمَّا»، أو نفيٌ أو شرطٌ
    يليه فعل، أو ضمير أو شبه جملة يليهما ما يتمّ به الكلام (وَلَهُمۡ عَذَابٌ، وَإِيَّاكَ نَسۡتَعِينُ)"""
    g = feats[h]
    nxt = feats[h + 1] if h + 1 < len(feats) else None
    nv = bool(nxt) and (nxt['verb'] or h + 1 in nuc_pos or nxt.get('vshape'))
    if g['verb'] or h in nuc_pos or g.get('vshape') and not g.get('noun') or g.get('amma') or \
            not g.get('noun') and (_madi_like(g['text']) or _hollow_madi(g['text'])) or \
            _verb_enclitic(g) or \
            set(g.get('ops', [])) & VERBAL_OPS:
        return True
    if is_form(g['text'], ISTIDRAK_V, prefix=True):
        return True
    if (g.get('neg') or g.get('cond_amb')) and (nv or nxt and nxt.get('head') in ('pron', 'pp')) and not g.get('rel'):
        return True
    if g.get('head') == 'pron':
        return bool(nxt) and not nxt['conj']
    pp = g.get('head') == 'pp' or is_form(g['text'], PP_WORD_V, prefix=True)
    return pp and _pp_clause(feats, h, nuc_pos)


def _verb_enclitic(g):
    """صورة الماضي قبل ضمير المفعول بعد العاطف (فَأَمَاتَهُۥ، ثُمَّ بَعَثَهُۥ): الاسم قبل الضمير لا يأتي على هذه الصورة
    إلا منصوباً، فيُقصر على الأجوف من أَفۡعَلَ وعلى ما ليس ظرفاً"""
    from .cells import ENCLITICS_V
    t = g['text']
    if g.get('zarf') or not any(x[0] == 'مبني' and is_form(x[1], ENCLITICS_V) for x in (g.get('segs') or [])[1:]):
        return False
    st = letters(t)
    if st and st[0][0] in 'وف' and st[0][1] == {FATHA}:
        st = st[1:]
    return len(st) > 3 and st[0][0] == 'أ' and st[0][1] == {FATHA} and st[2][0] == 'ا' and _hollow_madi(t)


def _pp_clause(feats, h, nuc_pos):
    """شبه الجملة بعد العاطف يبدأ جملةً إن تلاه ما يتمّ به الكلام: مرفوعٌ (خبرٌ مقدَّم ومبتدأ مؤخَّر: وَلَهُمۡ عَذَابٌ)،
    أو فعل، أو ضمير؛ فإن تلاه مجرورٌ أو منصوب (وَبِٱلۡيَوۡمِ ٱلۡأٓخِرِ) فهو مفردٌ معطوف"""
    nxt = feats[h + 1] if h + 1 < len(feats) else None
    q = h + 1
    # شبه جملةٍ ثانية قبل المرفوع (وَلَهُمۡ فِيهَآ أَزۡوَٰجٌ): تُتخطّى
    while nxt is not None and q < h + 3 and not nxt['conj'] and (nxt.get('head') == 'pp' or
                                                                is_form(nxt['text'], PP_WORD_V, prefix=True)) and \
            not is_form(nxt['text'], JARR_V) and q + 1 < len(feats):
        q += 1
        nxt = feats[q]
    if nxt is not None and is_form(feats[h]['text'], JARR_V) and nxt['case'] in ('جر', 'جر أو نصب', 'نصب أو جر', None) \
            and h + 2 < len(feats):
        nxt = feats[h + 2]                              # فِي قُلُوبِهِم مَّرَضٌ: الجارّ كلمة، ومجروره بعده، ثم المرفوع
    return bool(nxt) and not nxt['conj'] and (nxt['case'] == 'رفع' or nxt['verb'] or h + 1 in nuc_pos or
                                              nxt.get('head') == 'pron' or nxt.get('demo') or nxt.get('vshape') and
                                              not nxt.get('noun'))


def coord_structs(feats, nuc_pos, starts, not_conj, is_clause, ay_end=None):
    """G = Coord_h,e(A, B) لكل حرف عطف (حكم صاحب النظرية؛ الأصول من ابن عقيل):
    - الحرف عاطفٌ هنا ما لم يثبت غيره: فاء الجواب الرابطة، وفاء خبر الموصول المبتدأ ليستا عاطفتين (not_conj)
    - المستوى: جملةٌ (المعطوف فعلٌ أو ما له الصدارة أو جملة اسمية من أكثر من كلمة) أو مفرد
    - المعطوف عليه في المفرد: اسمٌ قبله في الجملة الجارية يوافقه في الحالة المكتوبة وعليه دليل الاسمية؛ وليس بالضرورة
      أقربَ كلمة، فإن صلح أكثر من واحد حُفظت البدائل؛ وفي الجملة: الجملة قبله، والعلاقة عطفٌ أو حال أو استئناف
    - الأثر: الواو لمطلق الجمع، والفاء للترتيب والتعقيب، وثُمَّ للترتيب والتراخي
    → [dict(kind='عطف', pos, letter, level, B, A=[مرشحات]، effect)]"""
    out = []
    n = len(feats)
    for k in range(1, n):
        f = feats[k]
        if not f['conj'] or k in not_conj:
            continue
        letter = f['conj_letter']
        h = k + 1 if letter in ('أو', 'ثم', 'أم') else k
        if h >= n:
            continue
        # «وَمَآ أُنزِلَ» بعد «بِمَآ أُنزِلَ»: «ما» موصولةٌ معطوفة على «ما» قبلها، لا نافية تبدأ جملة
        prev_ma = next((j for j in range(k - 1, max(-1, k - 8), -1)
                        if is_form(feats[j]['text'], ('بِمَا', 'مِمَّا', 'لِمَا', 'عَمَّا', 'فِيمَا'), prefix=True)), None)
        if prev_ma is not None and is_form(g_text := feats[h]['text'], ('مَا',), prefix=True) and h + 1 < n and \
                (feats[h + 1]['verb'] or h + 1 in nuc_pos or _madi_like(feats[h + 1]['text']) or
                 feats[h + 1].get('vshape') and not feats[h + 1].get('noun')):
            out.append(dict(kind='عطف', pos=k, letter=letter, level='مفرد', B=h, A=[prev_ma],
                            effect=COORD_EFFECT.get(letter, ''), note=f'«{g_text}» موصولة معطوفة على نظيرتها'))
            continue
        g = feats[h]
        # مرفوعٌ بعد مرفوعٍ هو أول جملته (ٱلشَّمۡسُ وَٱلۡقَمَرُ بِحُسۡبَانٍ): اسمان متعاطفان، وما بعدهما مشتركٌ خارجهما
        a_ = k - 1
        if a_ > 0 and feats[a_]['case'] in ('جر', 'جر أو نصب') and feats[a_ - 1]['case'] == 'رفع' and feats[a_ - 1].get('noun'):
            a_ -= 1                                     # المضاف إليه بعد الأول
        first_of_clause = a_ >= 0 and (a_ == 0 or starts[a_] or (ay_end and ay_end[a_ - 1]) or feats[a_ - 1]['verb'] or
                                       a_ - 1 in nuc_pos or feats[a_ - 1]['conj'])
        if g.get('noun') and g['case'] == 'رفع' and a_ >= 0 and feats[a_].get('noun') and feats[a_]['case'] == 'رفع' and \
                first_of_clause and letter in ('و', 'ف', 'ثم', 'أو') and not g.get('demo'):
            out.append(dict(kind='عطف', pos=k, letter=letter, level='مفرد', B=h, A=[a_],
                            effect=COORD_EFFECT.get(letter, ''), note='مرفوعان متعاطفان أولُهما أول جملته'))
            continue
        if is_clause(k - 1) or clause_word(feats, h, nuc_pos):
            out.append(dict(kind='عطف', pos=k, letter=letter, level='جملة', B=h, A=['الجملة قبله'],
                            effect=COORD_EFFECT.get(letter, '')))
            continue
        # شبه جملةٍ معطوفة على شبه جملة (مَتَٰعًا لَّكُمۡ وَلِأَنۡعَٰمِكُمۡ): الطرفان جارٌّ ومجرور، ويُقدَّم الجارّ نفسه
        pp_b = _pp_like(g)
        if pp_b:
            def _is_pp(j):
                return _pp_like(feats[j]) or is_form(feats[j]['text'], JARR_V)
            def _jl(f_):
                lb = letters(f_['text'])
                return lb[1][0] if f_['conj'] and len(lb) > 1 else lb[0][0] if lb else ''
            ppc = []
            for j in range(k - 1, max(-1, k - 10), -1):
                if starts[j] and j < k - 1 or ay_end and ay_end[j] and j < k - 1:
                    break
                if _is_pp(j):
                    ppc.append(j)
            same = [j for j in ppc if _jl(feats[j]) == _jl(g)]
            if ppc:
                out.append(dict(kind='عطف', pos=k, letter=letter, level='شبه جملة', B=h, A=(same or ppc)[:3],
                                effect=COORD_EFFECT.get(letter, ''), note='جارٌّ ومجرور معطوفٌ على جارٍّ ومجرور'))
                continue
        c = g['case']
        cands = []
        # المعطوف المفرد: اسمٌ بدليله، أو موصولٌ (وَٱلَّذِينَ ءَامَنُواْ)، أو مصدرٌ مؤوَّل بـ«أَنْ» والفعل (وَأَن تَقُولُواْ)؛
        # والمقصور والمبني والمؤوَّل لا تظهر حالته، فيوافق كل حالة
        single = g.get('noun') or g.get('rel') or g.get('an')
        any_case = g.get('maqsur') or g.get('rel') or g.get('an')
        if single and (any_case or c in CASE_COMPAT):
            # الظاهر الحالة: في الجملة الجارية؛ وما لا تظهر حالته يُبحث له أبعد، متخطّياً ما له الصدارة،
            # ويُقدَّم ما يماثله: الموصول على الموصول، والمؤوَّل على المؤوَّل
            for j in range(k - 1, max(-1, k - (20 if any_case else 12)), -1):
                if starts[j] and j < k - 1 and not any_case:
                    break
                fj = feats[j]
                if g.get('rel') and fj.get('rel') or g.get('an') and fj.get('an'):
                    cands = [j]
                    break
                if fj.get('noun') and not fj.get('rel') and (any_case or fj['case'] in CASE_COMPAT[c] or fj.get('maqsur')):
                    cands.append(j)
        out.append(dict(kind='عطف', pos=k, letter=letter, level='مفرد', B=h, A=cands,
                        effect=COORD_EFFECT.get(letter, '')))
    return out


def relative_khabar(feats, nuc_pos, starts, st_):
    """خبر الموصول المبتدأ (الَّذِي كَتَبَ الدَّرْسَ …): بعد الصلة، إن لم تُعطف عليها صلةٌ أخرى:
    فاءٌ داخلة على الخبر (ٱلَّذِينَ يُنفِقُونَ … فَلَهُمۡ)، أو نواةٌ بلا عاطف، أو مرفوعٌ أو ضمير منفصل أو اسم إشارة
    أو شبه جملة → (موضع الخبر، الدليل) أو (None، السبب)"""
    k = st_['end']
    n = len(feats)
    while k < n:
        f = feats[k]
        # صلةٌ معطوفة على الصلة (وَيُقِيمُونَ ٱلصَّلَوٰةَ): تُتخطّى إلى آخرها
        if f['conj'] and f['conj_letter'] == 'و' and (f['verb'] or k in nuc_pos):
            k += 1
            while k < n and not feats[k]['conj'] and not starts[k] and not (k in nuc_pos or feats[k]['verb']):
                k += 1
            continue
        if f['conj'] and f['conj_letter'] == 'ف':
            return k, 'فاءٌ داخلة على خبر الموصول المبتدأ'
        if f['conj']:
            return None, 'عاطفٌ بعد الصلة لا يُعيَّن خبراً'
        if k in nuc_pos or f['verb']:
            return k, 'جملةٌ فعلية بعد الصلة'
        if f.get('demo') or f.get('head') in ('pron', 'pp') or f['case'] == 'رفع':
            return k, 'مرفوعٌ أو ضمير أو إشارة أو شبه جملة بعد الصلة'
        return None, 'لم يُكشف الخبر بعد الصلة'
    return None, 'انتهى النص قبل الخبر'


def sentence_boundary(p, js, n, spans, cspans, nuc_pos, qawl_pos, starts, obls, pos_of, feats=None, chain=False,
                      block=None):
    """Boundary(J | W) بين الكلمة p والتي بعدها، والجملة الجارية J تبدأ عند js (هندسة الخانات، لا علامات الوقف):
    Boundary ⟺ Complete(J) ∧ BlockedExtension(J, W)
    - Complete(J): في J نواة إسناد، ولا التزامٌ نحوي لازم مفتوح فيها (فهو يطلب ما بعده)
    - BlockedExtension: لا رابطٌ ثابت يعبر الموضع، وليست W مقولَ قولٍ لنواةٍ قبلها، وW تبدأ بما له الصدارة
      (فلا يعمل فيه ما قبله): ناسخ مكسور، أو استفهام، أو نداء، أو شرط، أو تنبيه
    → ('proven', السبب) أو ('possible', السبب) حين يحتمل الموضع الحدّ والامتداد معاً، أو None"""
    # التزامات البنى (الصلة، والشرط): داخل المكوّن الداخلي لا حدّ، والمكوّن الأعلى المفتوح يجعل الحدّ محتملاً
    if block is not None:
        return None if block[0] == 'inner' else ('possible', block[1])
    # J تامّة بنواتها، أو هي معطوفةٌ بواوٍ أو فاء على جملةٍ تامّة قبلها (تشاركها في التمام: وَيَهۡدِيَكُمۡ … وَيَتُوبَ عَلَيۡكُمۡ)
    if not any(js <= x <= p for x in nuc_pos) and not chain:
        return None
    # التزامٌ لازم مفتوح (خبرٌ لم يُكشف): J غير تامّة في التحليل، فلا يثبت الحدّ؛ لكن قد يملؤه ما بعد الموضع
    # أو يكون التحليل قاصراً عنه، فيبقى الحدّ محتملاً ولا يُغلق الباب على ما بعده
    open_ = next((o.name for o in obls if o.required and not o.met and o.name.startswith(SYNTACTIC_OBL) and
                  any(js <= pos_of.get(u, -1) <= p for u in o.units)), None)
    d = _boundary_kind(p, js, spans, cspans, nuc_pos, qawl_pos, starts, feats)
    if d and open_:
        return ('possible', f'التزامٌ مفتوح ({open_}): قد يملؤه ما بعد الموضع')
    return d




def is_qawl(word):
    """فعل القول (وما في معناه: نادى، وصّى، دعا) بصيغته المشكولة، وبعد واو أو فاء: معموله مقول القول"""
    return is_form(word, QAWL_V, prefix=True)


def _boundary_kind(p, js, spans, cspans, nuc_pos, qawl_pos, starts, feats=None):
    if any(min(a, b) <= p < max(a, b) for a, b in spans):
        return None
    q = [x for x in qawl_pos if js <= x <= p]
    if q and feats:
        # يمتنع الحدّ قبل بداية المقول وحدها: بعد «قال» فاعلُه المرفوع وشبهُ الجملة (قَالَ مُوسَىٰ لِقَوۡمِهِۦٓ)، ثم يبدأ المقول؛
        # وداخل المقول تقع الحدود كما تقع في غيره
        k = max(q) + 1
        while k < len(feats) and not starts[k] and k not in nuc_pos and \
                (feats[k]['case'] == 'رفع' and feats[k].get('noun') or feats[k].get('head') == 'pp'):
            k += 1
        if p < k:
            return None
    elif q and not any(starts[k] or k in nuc_pos for k in range(max(q) + 1, p + 1)):
        return None                                   # ما بعد «قال» مقولُه: معمولٌ له لا جملة مستقلة
    if starts[p] and starts[p][0] in ('تنبيه', 'استفهام', 'نداء', 'شرط') or feats and feats[p].get('cond_amb'):
        return None                                   # ما له الصدارة، وأداة الشرط، تطلب كلامها بعدها (أَلَآ إِنَّهُمۡ، فَمَنِ ٱهۡتَدَىٰ)
    w = starts[p + 1]
    if any(min(a, b) <= p < max(a, b) for a, b in cspans):
        return ('possible', 'رابط محتمل يعبر الموضع')
    # نهاية الجملة قبل الواو أو الفاء (حكم صاحب النظرية): الجملة التامّة قبلها جملةٌ صحيحة، وما بعدها عطفٌ أو حال
    # أو معيّة أو استئناف، تُحفظ بدائله ولا يُختار منها اعتباطاً
    f = feats[p + 1] if feats else None
    if f and f['conj']:
        if f['conj_letter'] == 'أم':
            return None                                  # «أَمۡ» المتصلة تعادل همزة التسوية: لا يُبتدأ بها
        name = {'و': 'الواو', 'ف': 'الفاء', 'ثم': '«ثُمَّ»'}.get(f['conj_letter'], '«أو»')
        # فاء الجواب: «مَن» أو «ما» في J قبلها قد تكون شرطاً، فما بعد الفاء جوابه لا جملة مستقلة
        if f['conj_letter'] == 'ف' and any(feats[k].get('cond_amb') for k in range(js, p + 1)):
            return ('possible', 'فاءٌ قد تكون جوابَ شرطٍ بـ«مَن» أو «ما» قبلها')
        # يُقصر الحكم على الجملة (حكم صاحب النظرية): المعطوف فعلٌ، أو ما له الصدارة، أو جملةٌ اسمية أولها مرفوع
        # أو ضمير منفصل أو شبه جملة، وهي أكثر من كلمة؛ أما الاسم المعطوف على مفرد فليس جملة (عِظَٰمًا ‖ وَرُفَٰتًا)
        # «أَوۡ» و«ثُمَّ» كلمتان: المعطوف يبدأ بما بعدهما
        h = p + 2 if f['conj_letter'] in ('أو', 'ثم', 'أم') else p + 1
        if h >= len(feats):
            return None
        g = feats[h]
        span = next((k for k in range(h + 1, len(feats)) if feats[k]['conj'] or starts[k]), len(feats)) - h
        nxt_v = h + 1 < len(feats) and (feats[h + 1]['verb'] or h + 1 in nuc_pos or feats[h + 1].get('vshape') or
                                         set(feats[h + 1].get('ops', [])) & VERBAL_OPS)
        clause = (g['verb'] or starts[h] or h in nuc_pos) and not (h > p + 1 and g['conj']) or \
            set(g.get('ops', [])) & VERBAL_OPS or g.get('amma') or \
            (set(g.get('ops', [])) & {'6', '7'} or g.get('neg') or g.get('cond_amb')) and nxt_v and not g.get('an') or \
            (g['case'] == 'رفع' or g.get('head') == 'pron' or g.get('head') == 'pp' and _pp_clause(feats, h, nuc_pos)) and \
            span > 1
        if clause:
            return ('proven', f'نهاية جملة قبل {name}: وما بعدها {relations_after(feats, p)}')
        return None
    # الشرط بعد جملة تامّة قد يكون ما قبله دليلَ جوابه (وَلَا يَأۡبَ ٱلشُّهَدَآءُ إِذَا مَا دُعُواْ): فلا يثبت به الحدّ
    if w and not w[1] and w[0] != 'شرط':
        return ('proven', f'{w[0]}: له الصدارة بعد جملة تامّة، ولا رابط يعبر الموضع')
    if w and w[0] == 'شرط':
        return ('possible', 'شرطٌ بعد جملة تامّة: يبدأ جملة، أو ما قبله دليل جوابه')
    if w:
        return ('possible', f'{w[0]} بعد حرف عطف: جملةٌ معطوفة أو حالية')
    if p + 1 in nuc_pos:
        return ('possible', 'نواةٌ بعد جملة تامّة: ' + (relations_after(feats, p) if feats else 'استئناف، أو حال، أو صفة، أو خبر'))
    return None


def relations_after(feats, p):
    """R(G, Q, c): العلاقات المرخَّصة بين البناء السابق والجملة التالية Q (أولها الكلمة p + 1)، بشروطها المكتوبة؛
    وما ثبت مانعه يُستبعد وحده، والباقي بدائل محفوظة (حكم صاحب النظرية):
    - صفة: قبلها نكرة، والجملة خبرية (ليست أمراً)، وفيها رابطٌ يعود على المنعوت (فعلٌ للغائب)
    - حال: بالواو مع جملة اسمية أو «قد» والماضي؛ وبلا واو مضارعٌ مثبت للغائب. والواو مع المضارع المثبت لا تُعتمد حالاً مباشرةً
    - عطف (بالواو أو الفاء)، ومعيّة (واوٌ بعدها منصوب)، واستئناف
    والتنكير وحده لا يحسم الصفة، ولا الواو وحدها الحال، ولا فشلُ غيرهما الاستئناف"""
    q, prev = feats[p + 1], feats[p]
    R = []
    if q['conj']:
        R.append('عطف')
    if q['verb'] and not q['conj'] and prev['nakira'] and q['verb'] != 'amr' and q['person'] == 3:
        R.append('صفة')
    if q['conj'] and q['conj_letter'] == 'و':
        if q['qad'] or not q['verb']:
            R.append('حال')
        if q['case'] == 'نصب' and q.get('noun') and not q['verb']:
            R.append('معيّة')
    elif not q['conj'] and q['verb'] == 'mudari' and q['person'] == 3:
        R.append('حال')
    if q['verb'] or q['conj'] or q['qad']:
        R.append('استئناف')
    return 'أو '.join(x + '، ' for x in R).rstrip('، ') if R else 'علاقته غير معيَّنة'


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
    rel_samples, cond_samples, coord_samples, coord_records = [], [], [], []
    failures = collections.defaultdict(list)
    sources = waqf_sources()
    by_surah = collections.OrderedDict()
    for it in items:
        by_surah.setdefault(it[0], []).append(it)
    for s, its in by_surah.items():
        words, wunits, marks, ay_end, starts, wtext, feats = [], [], [], [], [], [], []
        khabar_done, pending_open = set(), []
        pos_of, qawl = {}, set()
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
                    if G.Theta.get('R') == 'قول':
                        qawl.add(G.id)
                words.append((s, v, wi)); wunits.append(us); marks.append(mk[wi]); wtext.append(seg['word'])
                ay_end.append(wi == len(a['segments']) - 1)
                starts.append(a['starts'][wi] if 'starts' in a else clause_start(a, wi))
                fv = (a['feats'] if 'feats' in a else word_feats(a))[wi] if wi == 0 or 'feats' in a else fv_all[wi]
                if wi == 0 and 'feats' not in a:
                    fv_all = word_feats(a)
                    fv = fv_all[0]
                fv = dict(fv)
                # فاء أو واو ملتصقة لم يقطعها المقطِّع (فَأَرَادُواْ، فَجَعَلۡنَٰهُمُ): عاطفةٌ إن لم تكن فاءَ الجذر أو واوَه:
                # جذرُ الوحدة المغلقة لا يبدأ بها، أو ما بعدها فعلٌ بدليله المكتوب (ضمير رفعٍ متصل)
                if not fv['conj'] and fv['first'] in 'وف' and fv['first_fatha'] and len(letters(seg['word'])) >= 4:
                    R_ = next((G.Theta.get('R') for G in us if G.Theta.get('R')), None)
                    from .affix import stem_info as _si
                    rest = seg['word'][seg['word'].index(fv['first']) + 1:].lstrip(FATHA).replace(DAGGER_ALIF, 'ا')
                    if R_ and R_[0] != fv['first'] or not R_ and _si(rest).get('pos') == 'verb':
                        fv['conj'], fv['conj_letter'] = True, fv['first']
                        if not fv['verb'] and not R_:
                            fv['verb'] = _si(rest).get('kind')
                elif fv['conj'] and not fv['verb'] and fv['conj_letter'] in ('و', 'ف') and 'slots' in seg:
                    # فصلها المقشِّر برخصة البقية (فَ + جَعَلۡنَٰهُمُ): فعليّة البقية بدليلها المكتوب كما في الملتصقة
                    from .affix import stem_info as _si
                    stem = next((x['text'] for x in seg['slots'] if x['type'] == 'جذع'), '')
                    rest = (stem + ''.join(x['text'] for x in seg['slots'][[x['type'] for x in seg['slots']].index('جذع') + 1:])
                            if stem else '').replace(DAGGER_ALIF, 'ا')
                    if rest and _si(rest).get('pos') == 'verb':
                        fv['verb'] = _si(rest).get('kind')
                feats.append(fv)
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
        spans = [(pos_of[b[1]], pos_of[b[2]]) for b in bonds if b[1] in pos_of and b[2] in pos_of]
        cspans = [(pos_of[c['src']], pos_of[c['dst']]) for c in cand]
        nuc_pos = sorted({pos_of[x[0]] for x in nuclei if x[0] in pos_of})
        qawl_pos = {pos_of[x[0]] for x in nuclei if x[0] in qawl} | {p for p, w in enumerate(wtext) if is_qawl(w)}
        js = 0                                        # أول الجملة الجارية بقراءة القطع عند آخر حدٍّ مسجَّل (ثابتٍ أو محتمل)
        chain = False                                 # الجملة الجارية معطوفة على جملةٍ تامّة قبلها
        # البنى والتزاماتها: الصلة (ثم الشرط والعطف)
        rels = relative_structs(feats, set(nuc_pos), starts)
        inner = {}
        for r in rels:
            for k in range(r['head'], r['end'] - 1):
                inner.setdefault(k, ('inner', 'داخل الصلة'))
            st['rel'] += 1
            for name, met, _ in r['obligations']:
                st[f'rel:{name}'] += 1
                st[f'rel:{name}:met'] += bool(met)
            st[f'rel:نوع:{r["silah"]}'] += 1
            if len(rel_samples) < 40:
                rel_samples.append(dict(location=words_text(words, r['head']), text=' '.join(wtext[r['head']:r['end']]),
                                        silah=r['silah'], obligations=[list(o) for o in r['obligations']]))
        rel_at = {r['head']: r for r in rels}
        silah_pos = {k for r in rels for k in range(r['head'] + 1, r['end'])}
        # موضع كل كلمة في البناء (مراجعة التقرير ١٠): الموضع ← الدور المرخَّص؛ والتتابع وحده لا يجعل للكلمة موضعاً
        roles = {}
        for r in rels:
            roles.setdefault(r['head'], f'موصول ({r["silah"] or "صلته غير مكشوفة"})')
        # النوى المرتبطة ببنيةٍ أعلى (مراجعة التقرير ٦): تعدّد النوى طبيعيٌّ في الخبر الجملي والصلة والشرط والمقول
        # والمعطوف؛ والسؤال: هل بقيت نواةٌ غير مرتبطة؟ → الموضع ← سبب الارتباط
        nset = set(nuc_pos)
        bound = {}
        # حالة كل علاقةٍ تربط نواةً (مراجعة ملفات الجمل ٦): مرخّصة بقاعدةٍ ودليل، أو مرجّحة، أو مرشّحة؛
        # والنواة المربوطة بعلاقةٍ غير مرخّصة لا تُعدّ مرتبطة في إغلاق الجملة
        bound_status = {}
        for r in rels:
            for k in range(r['head'] + 1, r['end']):
                if k in nset:
                    bound.setdefault(k, f'صلة «{wtext[r["head"]]}»')
        for b in bonds:
            if b[0].startswith('خبر «') and b[2] in pos_of:
                bound.setdefault(pos_of[b[2]], b[0])
        for qp in qawl_pos:
            k = next((k for k in range(qp + 1, min(n, qp + 6)) if k in nset), None)
            if k is not None and not any(starts[j] and starts[j][0] != 'نداء' for j in range(qp + 1, k)):
                bound.setdefault(k, f'مقول «{wtext[qp]}»')
        not_conj, not_conj_why, cond_spans = set(), {}, []
        for c_ in cond_structs(feats, set(nuc_pos), starts, ay_end):
            st['cond'] += 1
            st['cond:ambiguous'] += c_['amb']
            for name, met, _ in c_['obligations']:
                st[f'cond:{name}'] += 1
                st[f'cond:{name}:met'] += bool(met)
            if c_['q_pos'] is not None:
                st['cond:ربط:' + c_['q_kind'].split(':')[0]] += 1
                # الشرط وجوابه مكوّنٌ واحد: لا حدّ بين الأداة وأول الجواب، والفاء الرابطة ليست عاطفة
                for k in range(c_['head'], c_['q_pos']):
                    inner.setdefault(k, ('inner', 'بين الشرط وجوابه'))
            elif not c_['amb']:
                # بلا جوابٍ مستوفى لا يُجزم بنطاق جملة الشرط (فعلُ الشرط قد لا يُعرف: وَإِذَآ أَظۡلَمَ … قَامُواْ):
                # يُمنع الحدّ بعد الأداة وحدها، وما بعدها إلى الجواب المحتمل حدٌّ محتمل
                inner.setdefault(c_['head'], ('inner', 'بعد أداة الشرط'))
                for k in range(c_['head'] + 1, min(n - 1, c_['open_to'])):
                    inner.setdefault(k, ('open', f'جواب «{c_["tool"]}» غير مستوفى' + (f' ({c_["q_kind"]})' if c_['q_kind'] else '')))
            if c_['q_pos'] is not None and feats[c_['q_pos']]['conj'] and feats[c_['q_pos']]['conj_letter'] == 'ف':
                not_conj.add(c_['q_pos'])
                not_conj_why[c_['q_pos']] = dict(tool=c_['tool'], head=c_['head'], amb=bool(c_['amb']),
                                                 s_deferred=any('مشروط' in str(o_[2]) for o_ in c_['obligations']))
            cond_spans.append((c_['head'], c_['q_pos'], c_['tool'],
                               not c_['amb'] and all(o_[1] and 'مرشَّح' not in str(o_[2]) and 'محتمل' not in str(o_[2])
                                                     for o_ in c_['obligations'])))
            roles.setdefault(c_['head'], f'أداة شرط «{c_["tool"]}»')
            for k, why in ((c_['s_pos'], 'فعل الشرط'), (c_['q_pos'], 'جواب الشرط')):
                if k is not None:
                    kk = next((j for j in range(k, min(n, k + 4)) if j in nset), None)
                    if kk is not None:
                        bound.setdefault(kk, f'{why} «{c_["tool"]}»')
                        cand_ = c_['amb'] or any(not o_[1] or 'مرشَّح' in str(o_[2]) or 'محتمل' in str(o_[2])
                                                 for o_ in c_['obligations'])
                        if cand_ and bound[kk].startswith(why):
                            bound_status[kk] = 'مرشّحة'
            if len(cond_samples) < 40:
                cond_samples.append(dict(location=words_text(words, c_['head']),
                                         text=' '.join(wtext[c_['head']:(c_['q_pos'] or c_['head']) + 4]),
                                         tool=c_['tool'], amb=c_['amb'], obligations=[list(o) for o in c_['obligations']]))
        def _is_clause(p_):
            d_ = _boundary_kind(p_, 0, [], [], nuc_pos, set(), starts, feats)
            return bool(d_) and d_[1].startswith('نهاية جملة قبل')
        coords = list(coord_structs(feats, set(nuc_pos), starts, not_conj, _is_clause, ay_end))
        single_B = {c['B'] for c in coords if c['level'] != 'جملة'} | {c['pos'] for c in coords if c['level'] != 'جملة'}
        # نهاية الصلة الفعلية: تمتدّ بما يُعطف عليها داخلها (صلةٌ معطوفة، أو مفردٌ معطوف في الصلة: وَمَآ أُنزِلَ)
        eff_end = {r['head']: r['end'] for r in rels}
        def _next_stop(j):
            # تنتهي الصلة المعطوفة عند عاطفٍ آخر، أو ما له الصدارة، أو رأس جملةٍ جديدة بلا عاطف (اسم إشارة، ضمير منفصل،
            # نواةٌ ثانية بعد نواة المعطوف)، أو آخر الآية
            seen_nuc = False
            for p_ in range(j + 1, n):
                f_ = feats[p_]
                if f_['conj'] or starts[p_] or f_.get('demo') or f_.get('head') == 'pron' and not f_['conj']:
                    return p_
                if p_ in nset:
                    if seen_nuc:
                        return p_
                    seen_nuc = True
                if ay_end[p_]:
                    return p_ + 1
            return n
        def _b_stop(j):
            # نطاق المعطوف B: لا يُقطع قبل اكتماله؛ فالضمير أو اسم الإشارة بعد شبه جملةٍ في أوله مبتدؤه، والنواة بعده خبره
            # (وَبِٱلۡأٓخِرَةِ هُمۡ يُوقِنُونَ). ويقف عند عاطفٍ آخر، أو ما له الصدارة، أو آخر الآية، أو رأس جملةٍ بعد نواته
            # والمبتدأ ضميرٌ في أول المعطوف (وَهِيَ خَاوِيَةٌ): خبره المرفوع يتمّ به، فالنواة بعده رأس جملةٍ جديدة؛
            # والنفي بعد اكتمال النواة يبدأ جملة (أَمۡ لَمۡ تُنذِرۡهُمۡ ‖ لَا يُؤۡمِنُونَ)
            f0 = feats[j]
            subj = bool(f0.get('demo') or f0.get('head') == 'pron')
            nuc_seen = bool(j in nset or f0['verb'])
            pred = False
            for p_ in range(j + 1, n):
                f_ = feats[p_]
                if f_['conj'] or starts[p_]:
                    return p_
                if (f_.get('demo') or f_.get('head') == 'pron') and not f_['conj']:
                    if subj or nuc_seen:
                        return p_
                    subj = True
                elif p_ in nset or f_['verb'] or _madi_like(f_['text']) and not f_.get('noun') or \
                        _hollow_madi(f_['text']) and not f_.get('noun'):
                    if nuc_seen or pred:
                        return p_
                    nuc_seen = True
                elif f_.get('neg') and nuc_seen and p_ + 1 < n and (feats[p_ + 1]['verb'] or p_ + 1 in nset or
                                                                     feats[p_ + 1].get('vshape')):
                    return p_
                elif subj and not nuc_seen and f_.get('noun') and f_['case'] == 'رفع':
                    pred = True
                if ay_end[p_]:
                    return p_ + 1
            return n
        def _b_relations(b0, stop_):
            """علاقات المعطوف الجملة الداخلية: شبه جملة متقدّمة متعلّقة بالفعل، ومبتدأ ضمير، وخبر جملة فعلية"""
            rel_ = []
            ws = list(range(b0, stop_))
            pr = next((p_ for p_ in ws if (feats[p_].get('head') == 'pron' or feats[p_].get('demo')) and p_ != b0), None)
            vb = next((p_ for p_ in ws if (p_ in nset or feats[p_]['verb']) and p_ != b0), None)
            ppb = feats[b0].get('head') == 'pp' or is_form(feats[b0]['text'], JARR_V)
            if pr is not None and vb is not None and pr < vb:
                rel_.append(f'مبتدأ «{wtext[pr]}»، وخبره جملة فعلية رأسها «{wtext[vb]}»')
                if ppb:
                    rel_.append(f'«{wtext[b0]}» شبه جملة مقدَّمة، متعلّقة بـ«{wtext[vb]}»')
            elif vb is not None and ppb:
                rel_.append(f'«{wtext[b0]}» شبه جملة متعلّقة بـ«{wtext[vb]}»')
            return rel_
        from .coord import Ctx, site_record, extra_sites, nest, DECISIONS as DECISIONS_
        CX = Ctx(feats=feats, wtext=wtext, words=words, ay_end=ay_end, starts=starts, nset=nset, rel_at=rel_at,
                 eff_end=eff_end, rels=rels, not_conj_why=not_conj_why, cond_spans=cond_spans, q=q,
                 surah_start=bool(words) and words[0][1] == 1 and words[0][2] == 0, next_stop=_next_stop,
                 wunits=wunits, b_stop=_b_stop,
                 rel_khabar=lambda h_: relative_khabar(feats, set(nuc_pos), starts, rel_at[h_]))
        crecs = []

        def _b_verb_head(k0):
            # أول فعلٍ بصورته من أول المعطوف (بعد «أو» و«ثم» و«أم» ونفيٍ أو «قد»)، قبل أي اسمٍ مرفوع أو ضمير
            for j in range(k0, min(n, k0 + 3)):
                f_ = feats[j]
                if j > k0 and (f_['conj'] or starts[j]):
                    return None
                verbish = j in nset or bool(f_['verb']) or not f_.get('noun') and (
                    _madi_like(f_['text']) or _hollow_madi(f_['text'])) or _verb_enclitic(f_)
                if verbish and not (j == k0 and f_['conj_letter'] in ('أو', 'ثم', 'أم') and not f_['verb']):
                    return j
                if not (f_.get('neg') or f_.get('qad') or j == k0 and f_['conj_letter'] in ('أو', 'ثم', 'أم')):
                    return None
            return None

        def _clause_head(j):
            if j in silah_pos or j in single_B or bound.get(j, '').startswith('مقول'):
                return False
            f_ = feats[j]
            demo_head = bool(f_.get('demo')) and not (j > 0 and (j - 1 in nset or feats[j - 1]['verb'] or
                                                                 feats[j - 1].get('vshape')))
            return j in nset or bool(f_['verb']) or not f_.get('noun') and (_madi_like(f_['text']) or
                                                                            _hollow_madi(f_['text'])) or \
                _verb_enclitic(f_) or demo_head or f_.get('head') == 'pron' or bool(starts[j]) or j in rel_at or \
                f_['conj'] and clause_word(feats, j, nset) or \
                (f_.get('head') == 'pp' or is_form(f_['text'], JARR_V)) and _pp_clause(feats, j, nset)
        for c_ in coords:
            k0 = c_['pos']
            host = next((r for r in sorted(rels, key=lambda r: -r['head']) if r['head'] < k0 <= eff_end[r['head']] and
                         eff_end[r['head']] >= k0), None)
            if c_['level'] in ('مفرد', 'شبه جملة') and host is not None and eff_end[host['head']] == k0 and c_['A'] and \
                    all(host['head'] < a_ < k0 for a_ in c_['A']):
                eff_end[host['head']] = _next_stop(k0)      # المفرد المعطوف على ما في الصلة جزءٌ منها
            # الموصول حجّةٌ في جملةٍ أوسع (يُخَٰدِعُونَ ٱللَّهَ وَٱلَّذِينَ ءَامَنُواْ): الجملة الخارجية أولى، والصلة بديل
            def _governed(h_):
                for j in range(h_ - 1, max(-1, h_ - 7), -1):
                    if ay_end[j]:
                        return False                   # الموصول أول آيته: رأسُ عبارته
                    if (j in nset or feats[j]['verb']) and not any(r['head'] < j < eff_end[r['head']] for r in rels):
                        return True
                return False
            governed = host is not None and _governed(host['head'])
            if c_['level'] == 'جملة' and host is not None and eff_end[host['head']] == k0 and not governed:
                # صلةٌ معطوفة على الصلة (ٱلَّذِينَ يُؤۡمِنُونَ بِٱلۡغَيۡبِ وَيُقِيمُونَ): A الصلة، والموصول حاويها
                h0 = host['head']
                sv = next((j for j in range(h0 + 1, k0) if j in nset or feats[j]['verb']), h0 + 1)
                c_['A'] = [dict(id=words_text(words, h0 + 1), type='صلة', head=wtext[sv], span=(h0 + 1, k0 - 1),
                                text=' '.join(wtext[h0 + 1:k0]), container=f'الموصول «{wtext[h0]}» ({words_text(words, h0)})',
                                evidence='العاطف يلي الصلة مباشرة، والمعطوف جملة: صلةٌ معطوفة على الصلة داخل الموصول نفسه')]
                b_n = next((j for j in range(k0, min(n, k0 + 4)) if j in nset), k0)
                c_['B_scope'] = dict(nucleus=wtext[b_n], start=k0, container=c_['A'][0]['container'])
                bound.setdefault(b_n, f'صلةٌ معطوفة على صلة «{wtext[h0]}»')
                c_['b_n'] = b_n
                eff_end[h0] = _next_stop(k0)
            elif c_['level'] == 'جملة':
                # الطرفان بهويتيهما ونطاقيهما (مراجعة التقرير ٧): A الجملة التي تنتهي قبل العاطف (من نواتها السابقة)،
                # وB الجملة التي تبدأ به (إلى نواتها). وبلا نواةٍ قبلها فالطرف A غير معيَّن، ولا يُعدّ العطف عطفَ جملة مثبتاً
                k0 = c_['pos']
                _head = _clause_head
                # رأس الجملة السابقة: أول رأسٍ يُلقى رجوعاً من العاطف (فعلٌ، أو نواة، أو اسم إشارة أو ضمير يبدأ جملة اسمية،
                # أو ما له الصدارة)، ولا يُعبر إلى جملةٍ قبله: «أُوْلَٰٓئِكَ عَلَىٰ هُدࣰى» لا «يُوقِنُونَ … أُوْلَٰٓئِكَ»
                a_n = next((j for j in range(k0 - 1, max(-1, k0 - 15), -1) if _head(j)), None)
                head0 = a_n
                while a_n is not None and a_n > 0 and a_n - 1 not in single_B and \
                        (feats[a_n - 1].get('neg') or feats[a_n - 1].get('qad')) and a_n - 1 < k0:
                    a_n -= 1                           # النفي أو «قد» قبل الرأس من الجملة نفسها (وَمَا يَخۡدَعُونَ)
                # رأس المعطوف الجملة: أول فعلٍ من أوله (وَجَآءُوٓ أَبَاهُمۡ عِشَآءࣰ يَبۡكُونَ: الرأس «جاءوا»، و«يبكون» في
                # داخله حالٌ أو غيرها)؛ فإن لم يكن الرأس نواةً محلَّلة لم تُربط نواةٌ داخلية به
                hb = _b_verb_head(k0)
                if hb is not None:
                    b_n = hb if hb in nset else None
                    c_['b_head'] = hb
                else:
                    b_n = next((j for j in range(k0, min(n, k0 + 4)) if j in nset), None)
                    if b_n is None and _head(k0):
                        b_n = k0
                c_['b_n'] = b_n
                if a_n is not None:
                    fa = feats[head0]
                    typ = ('ما له الصدارة' if starts[head0] else
                           'جملة اسمية' if fa.get('demo') or fa.get('head') in ('pron', 'pp') or head0 in rel_at or
                           is_form(fa['text'], JARR_V) else
                           'جملة فعلية' if head0 in nset or fa['verb'] or not fa.get('noun') and
                           (_madi_like(fa['text']) or _hollow_madi(fa['text'])) else 'جملة اسمية')
                    c_['A'] = [dict(id=words_text(words, a_n), type=typ, head=wtext[head0], span=(a_n, k0 - 1),
                                    text=' '.join(wtext[a_n:k0]), container=None,
                                    evidence='أول رأس جملةٍ رجوعاً من العاطف، لا يُعبر إليه صلةٌ ولا مقولٌ ولا معطوفٌ مفرد')]
                else:
                    c_['A'] = []
                if governed and eff_end[host['head']] == k0:
                    h0 = host['head']
                    c_['A'].append(dict(id=words_text(words, h0 + 1), type='صلة (بديل)', head=wtext[h0 + 1],
                                        span=(h0 + 1, k0 - 1), text=' '.join(wtext[h0 + 1:k0]),
                                        container=f'الموصول «{wtext[h0]}» ({words_text(words, h0)})',
                                        evidence='يجوز عطفه على الصلة، والموصول حجّةٌ في جملةٍ أوسع فالخارجية أولى'))
                c_['B_scope'] = dict(nucleus=wtext[b_n] if b_n is not None else None, start=k0)
                if a_n is not None and b_n is not None:
                    bound.setdefault(b_n, f'معطوفٌ على جملة «{wtext[a_n]}»')
                else:
                    st['coord:جملة:طرفٌ غير معيَّن'] += 1
            # الطرف B بهويته ونوعه ونطاقه ورأسه وحاويه (مراجعة التقرير الرابعة ٣)، وحالة المعطوف عليه في المفرد
            if c_['level'] == 'جملة':
                b0 = c_['B']
                stop_ = _b_stop(b0)
                bh = c_.get('b_head') if c_.get('b_head') is not None else \
                    next((j for j in range(b0, stop_) if j in nset or feats[j]['verb']), b0)
                fb = feats[bh]
                c_['B_full'] = dict(id=words_text(words, k0), span=(k0, stop_ - 1), text=' '.join(wtext[k0:stop_]),
                                    head=wtext[bh], relations=_b_relations(b0, stop_),
                                    type='جملة فعلية' if bh in nset or fb['verb'] else
                                         'جملة اسمية' if fb.get('demo') or fb.get('head') in ('pron', 'pp') or
                                         is_form(fb['text'], JARR_V) or _pp_clause(feats, b0, nset) else 'جملة',
                                    container=(c_.get('B_scope') or {}).get('container'),
                                    evidence='من العاطف إلى أول عاطفٍ آخر أو ما له الصدارة أو رأس جملةٍ جديدة أو آخر الآية')
                if any(r_.startswith('مبتدأ') for r_ in c_['B_full']['relations']):
                    c_['B_full']['type'] = 'جملة اسمية (مبتدأ وخبرٌ جملي)'
                # لا حدّ داخل المعطوف الجملة قبل اكتماله (وَبِٱلۡأٓخِرَةِ ‖ هُمۡ ‖ يُوقِنُونَ)
                for k_ in range(k0, stop_ - 1):
                    inner.setdefault(k_, ('inner', 'داخل المعطوف الجملة'))
                c_['A_status'] = 'معيَّن' if len(c_['A']) == 1 else 'بدائل معلَّقة' if c_['A'] else 'غير معيَّن'
            else:
                c_['B_full'] = dict(id=words_text(words, c_['B']), span=(c_['B'], c_['B']), text=wtext[c_['B']],
                                    head=wtext[c_['B']], type='مفرد', container=None, evidence='كلمة المعطوف')
                c_['A_status'] = ('معيَّن' if len(c_['A']) == 1 else
                                  'بدائل معلَّقة (لم يُعتمد أحدها)' if c_['A'] else 'غير معيَّن')
            if c_['level'] == 'جملة' and c_['A'] or c_['level'] != 'جملة' and len(c_['A']) == 1:
                roles.setdefault(c_['pos'], f'حرف عطف «{c_["letter"]}»')
                if c_['level'] != 'جملة':
                    roles.setdefault(c_['B'], f'معطوفٌ على «{wtext[c_["A"][0]]}»')
            st['coord'] += 1
            st[f'coord:{c_["level"]}'] += 1
            st[f'coord:{c_["letter"]}'] += 1
            if c_['level'] == 'مفرد':
                st['coord:مفرد:' + ('معيَّن' if len(c_['A']) == 1 else 'بدائل' if c_['A'] else 'غير معيَّن')] += 1
            if len(coord_samples) < 60:
                coord_samples.append(dict(location=words_text(words, c_['pos']), letter=c_['letter'], level=c_['level'],
                                          B=wtext[c_['B']], A=[wtext[j] for j in c_['A']][:4] if c_['level'] != 'جملة' else
                                          [f'«{x["text"]}» ({x["type"]}، رأسها «{x["head"]}»' +
                                           (f'، في {x["container"]}' if x.get('container') else '') + ')' for x in c_['A']],
                                          effect=c_['effect'], A_status=c_.get('A_status'),
                                          A_full=[{k: (list(v) if isinstance(v, tuple) else v) for k, v in x.items()}
                                                  for x in c_['A']] if c_['level'] == 'جملة' else [],
                                          B_full={k: (list(v) if isinstance(v, tuple) else v)
                                                  for k, v in (c_.get('B_full') or {}).items()}))
        # سجلّ المرشّحات بعد اكتمال الامتدادات كلها (الصلة قد تمتدّ بعطفٍ لاحق)
        CX.clause_head = _clause_head
        CX.src = {}
        for c_ in coords:
            rec = site_record(c_, CX)
            crecs.append(rec)
            CX.src[rec['letter_unit']] = c_
            k0 = c_['pos']
            # حدّ الموضع يختلف باختلاف المرشّحات الباقية (حالٌ أو صلةٌ أو مفرد، أو جملةٌ مستقلة): يبقى الحدّ محتملاً
            live = [x for x in rec['candidates'] if x['status'] in ('مستوفٍ', 'مؤجَّل')]
            sep = {x['level'] == 'جملة' and not x['container'] and x['function'] in ('عطف', 'استئناف') for x in live}
            if not rec['UniqueWithin'] and len(sep) > 1 and k0 > 0:
                inner.setdefault(k0 - 1, ('open', 'حدّ العطف مؤجَّل: ' + rec['reason']))
            b_n = c_.get('b_n')
            if b_n is not None and b_n in bound and (bound[b_n].startswith('معطوفٌ على') or
                                                     bound[b_n].startswith('صلةٌ معطوفة')):
                # مرخّصة: العطف وحده مستوفٍ (ثابتٌ ضمن النطاق، أو مرخَّصٌ ومنافسه مؤجَّلٌ بلا قاعدةٍ إيجابية)؛
                # ومرجّحة أو مرشّحة: أكثر من وجهٍ مستوفٍ (عطفٌ وحال، أو مفردٌ وجملة، أو رؤوسٌ متعدّدة)
                ok_ = [x for x in rec['candidates'] if x['status'] == 'مستوفٍ']
                fn_ = {x['function'] for x in ok_}
                lv_ = {x['level'] for x in ok_}
                lic = bool(ok_) and all(f_.startswith('عطف') for f_ in fn_) and lv_ == {'جملة'}
                if lic and rec['decision'] == DECISIONS_[1]:
                    # الربط عطفاً ثابتٌ في كل الأوجه المستوفاة، والخلاف في المعطوف عليه وحده (D2): يُحفظ مؤجَّلاً
                    bound[b_n] += ' (والمعطوف عليه مؤجَّلٌ بين ' + '، '.join(f'«{x["A"]["head"]}»' for x in ok_ if x['A']) + ')'
                bound_status[b_n] = ('مرخّصة' if lic else 'مرجّحة' if rec['preferred'] else 'مرشّحة')
            if not rec['UniqueWithin']:
                for p_ in (k0, c_['B']):
                    if p_ in roles and (roles[p_].startswith('حرف عطف') or roles[p_].startswith('معطوفٌ على')) and \
                            not roles[p_].endswith(')'):
                        roles[p_] += ' (مرشَّح، القرار مؤجَّل)'
        crecs += extra_sites(CX, {c_['pos'] for c_ in coords})
        nest(crecs, CX)
        from .coord import check_coord, mutations
        for rec in crecs:
            pr_ = check_coord(rec, CX)
            st['coordcheck:' + ('سليم' if not pr_ else 'مرفوض')] += 1
            if pr_ and len(failures['coordcheck']) < 30:
                failures['coordcheck'].append(f'{rec["letter_unit"]}: {pr_[:3]}')
            if not pr_ and st['coordmut:حالات'] < 400:
                for name_, r_ in mutations(rec, CX):
                    st['coordmut:حالات'] += 1
                    pr2 = check_coord(r_, CX)
                    caught = bool(pr2)
                    st['coordmut:' + ('كُشف' if caught else 'فات')] += 1
                    st[f'coordmut:{name_}:' + ('كُشف' if caught else 'فات')] += 1
                    if not caught and len(failures['coordmut']) < 30:
                        failures['coordmut'].append(f'{rec["letter_unit"]}: {name_}')
                    # قبل/بعد: ما تغيّر، والحكم المتوقع (الرفض) وسببه كما أعاده الفاحص
                    if len(failures['coordmut_examples']) < 24 and name_ not in {x['name'] for x in failures['coordmut_examples']
                                                                               if x['unit'] != rec['letter_unit']}:
                        c0 = next((x for x in rec['candidates'] if x['A'] and x['B']), None)
                        c1 = next((x for x in r_['candidates'] if x['id'] == (c0 or {}).get('id')), None)
                        if c0 and c1:
                            failures['coordmut_examples'].append(dict(
                                unit=rec['letter_unit'], name=name_,
                                before=dict(A=c0['A']['head_id'], A_words=c0['A']['words'], B_words=c0['B']['words'],
                                            status=c0['status'], decision=rec['decision'], rules=c0['rules']),
                                after=dict(A=c1['A']['head_id'], A_words=c1['A']['words'], B_words=c1['B']['words'],
                                           status=c1['status'], decision=r_['decision'], rules=c1['rules']),
                                expected='مرفوض: الشهادة لا تخصّ البنية المعدَّلة', caught=caught, why=pr2[:2]))
            st['coordrec'] += 1
            st[f'coordrec:قرار:{rec["decision"]}'] += 1
            for d_ in rec['decision_codes']:
                st[f'coordrec:تأجيل:{d_}'] += 1
            st['coordrec:مرشّحات'] += len(rec['candidates'])
            for x in rec['candidates']:
                st[f'coordrec:مرشّح:{x["status"]}'] += 1
                for b_ in x['barriers']:
                    st[f'coordrec:مانع:{b_[0]}'] += 1
            acc = next((x for x in rec['candidates'] if x['status'] == 'مستوفٍ'), None)
            if rec['UniqueWithin'] and acc:
                st[f'coordrec:مقبول:{acc["function"]}'] += 1
            st['coordrec:داخل طرف'] += 'inside' in rec
            st['coordrec:سلسلة'] += 'chain' in rec
            if len(coord_records) < 60 or rec['text_id']['verse'] in COORD_WATCH:
                coord_records.append(rec)
        pending = {}                                  # موضع الحدّ ← (inner | open، السبب) لخبر الموصول المبتدأ
        for p in range(n):
            last = p == n - 1
            # الموصول في أول الجملة الجارية مبتدأٌ ينتظر خبره بعد صلته
            if p == js and p in rel_at and p not in khabar_done:
                khabar_done.add(p)
                r = rel_at[p]
                k, why = relative_khabar(feats, set(nuc_pos), starts, r)
                st['rel:خبر'] += 1
                st['rel:خبر:met'] += k is not None
                if k is not None:
                    for g_ in range(r['end'] - 1, k):
                        pending[g_] = ('inner', 'الموصول المبتدأ ينتظر خبره')
                else:
                    pending_open.append((r['end'] - 1, f'خبر الموصول «{wtext[p]}» غير مستوفى: {why}'))
            blk = inner.get(p) or pending.get(p)
            dec = None if last else sentence_boundary(p, js, n, spans, cspans, nuc_pos, qawl_pos, starts,
                                                      obls, pos_of, feats, chain, blk)
            # خبر الموصول المبتدأ غير المستوفى: أول حدٍّ مرشَّح بعد الصلة قد يكون موضع الخبر، فيُجعل محتملاً، ثم يُترك
            if dec and pending_open and p >= pending_open[-1][0]:
                dec = ('possible', pending_open[-1][1])
                pending_open.clear()
            if dec:
                js = p + 1
                if dec[0] == 'proven':
                    chain = dec[1].startswith('نهاية جملة قبل')
                elif dec[1].startswith('حدّ العطف مؤجَّل'):
                    chain = True                      # الحدّ المؤجَّل قبل جملةٍ معطوفة أو حالية: تشارك ما قبلها التمام
            if marks[p] or ay_end[p] or last or dec:
                rec = boundary_record(p, words, pos_of, bonds, obls, nuclei, du_start, marks[p], ay_end[p], last,
                                      sources, a_id, q, cand, checked_ends)
                rec['J'] = ('proven' if last else dec[0]) if (dec or last) else None
                rec['J_why'] = 'آخر السورة' if last else dec[1] if dec else ''
                records.append(rec)
                st['b_candidates'] += 1
                st['b_cat:' + rec['category'].split(':')[0].split(' (')[0]] += 1
                if rec['mark'] in BOUNDARY_WAQF and rec['L']:
                    st['b_mark_with_L'] += 1          # جواز الوقف مع تعلّق لفظي عابر (حسن، أو خطأ في التحليل)
                if rec['J'] and not last:
                    st[f'Jb_{rec["J"]}'] += 1
                    st[f'Jb_{rec["J"]}:' + rec['J_why'].split(':')[0]] += 1
                    # موضع كل حدٍّ مرةً واحدة، للمصالحة: مجموع المواضع = عدد الحدود
                    place = ('عند علامة معتمدة' if rec['mark'] in BOUNDARY_WAQF else 'عند المعانقة' if rec['mark'] == '∴' else
                             f'عند علامة غير معتمدة ({rec["mark"]})' if rec['mark'] else
                             'بلا علامة معتمدة: رأس آية' if rec['ayah_end'] else 'بلا علامة معتمدة: داخل الآية')
                    st[f'Jb_place:{rec["J"]}:{place}'] += 1
                if last or rec['J'] == 'proven':
                    segs.append((du_start, p, rec))
                    du_start = p + 1
        # التقييم بتقسيم مصحف المجمّع (العلامات مرجعٌ لا مدخل): كل علامةٍ حدٌّ في المرجع، والمعانقة حدٌّ في أحد موضعيها
        srec = [r for r in records if r['location'][0] == s]
        muan = []
        for r in srec:
            if r['mark'] == '∴':
                muan.append(r)
            elif r['mark'] in BOUNDARY_WAQF:
                st[f'eval:{r["mark"]}'] += 1
                st[f'eval:{r["mark"]}:{r["J"] or "none"}'] += 1
                if r['J'] == 'proven' and r['J_why'].startswith('نهاية جملة قبل'):
                    st[f'eval:{r["mark"]}:proven:عطف'] += 1
            elif r['J'] == 'proven' and r['location'] != words[-1]:
                st['eval:بلا علامة:proven' + (':رأس آية' if r['ayah_end'] else '')] += 1
            elif r['J'] == 'possible' and not r['mark']:
                st['eval:بلا علامة:possible'] += 1
        for k in range(0, len(muan) - 1, 2):
            pair = muan[k:k + 2]
            st['eval:∴'] += 1
            best = 'proven' if any(r['J'] == 'proven' for r in pair) else \
                'possible' if any(r['J'] == 'possible' for r in pair) else 'none'
            st[f'eval:∴:{best}'] += 1
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
            # كل كلمة موضعها مرخَّص: طرفُ رابطٍ ثابت، أو دورٌ في بنية (صلة، شرط، عطف)، أو نواةٌ، أو نفيٌ/«قد» قبل فعل
            placed_ids = {x for b in my_bonds for x in (b[1], b[2]) if isinstance(x, str)}
            unplaced = []
            for p in range(p0, p1 + 1):
                ids_p = {G.id for G in wunits[p]}
                ok_p = any(i in placed_ids or any(x.startswith(i + '.s') for x in placed_ids) for i in ids_p) or \
                    p in roles or p in bound or p in nset or starts[p] or \
                    any(G.Theta.get('lex') == 'حروف مقطّعة' for G in wunits[p]) or \
                    (feats[p].get('neg') or feats[p].get('qad')) and p + 1 < n and (feats[p + 1]['verb'] or p + 1 in nset)
                if not ok_p:
                    # الوقوع بهويته لا بصيغته (تساوي المحتوى لا يعني تساوي الوقوع): الموضع، والوحدة، والنص، والناقص
                    # جهتان منفصلتان (مراجعة ملفات الجمل ٨): الموضع النحوي (دورٌ في بنية، أو نواة، أو معمولٌ لعاملٍ مقبول)،
                    # وكون الوقوع طرفاً في علاقة؛ والناقص هنا الأولى، والثانية تُذكر بحالها
                    unplaced.append(f'{words_text(words, p)} [{"، ".join(sorted(ids_p))}] «{wtext[p]}»: '
                                    'الموضع النحوي غير مرخَّص (لا دورَ في بنية، ولا نواة، ولا معمولَ عاملٍ مقبول)؛ '
                                    'وليس طرفاً في علاقةٍ مسجَّلة')
            J.O['unplaced'] = unplaced
            if unplaced:
                J.Omega.append(Obligation('موضع كل كلمة', reason=f'{len(unplaced)} وقوعاً بلا موضعٍ مرخَّص في البناء '
                                          '(التتابع وحده لا يكفي)؛ وهي بهوياتها في عمود «وقوعات بلا موضع»'))
                st['J_unplaced'] += 1
                for w_ in unplaced:
                    st['unplaced_words'] += 1
            if len(my_nuc) == 0:
                pass
            else:
                free = [x for x in my_nuc if pos_of.get(x[0]) not in bound]
                J.O['bound'] = [(x[1], bound[pos_of[x[0]]], bound_status.get(pos_of[x[0]], 'مرخّصة'))
                                for x in my_nuc if pos_of.get(x[0]) in bound]
                undecided = [b_ for b_ in J.O['bound'] if b_[2] != 'مرخّصة']
                if undecided:
                    J.Omega.append(Obligation('علاقة غير محسومة', reason='؛ '.join(f'{a_} ← {b_} ({c_})'
                                                                                    for a_, b_, c_ in undecided[:3])))
                    st['J_undecided_relation'] += 1
                if len(free) > 1:
                    J.Omega.append(Obligation('نوى غير مرتبطة', reason=f'{len(free)} نوى لم تثبت علاقتها ببنيةٍ أعلى: ' +
                                              '، '.join(x[1] for x in free[:3])))
                    st['J_free_nuclei'] += 1
                else:
                    st['J_bound_nuclei' if len(my_nuc) > 1 else 'J_one_nucleus'] += 1
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
                # ثلاثة أحكام لا يستلزم أولها ثالثها (مراجعة التقرير الثالثة ٥): LocalComplete(J)، وClosed_k(J) في مستوى
                # الجملة، وNoExternalDependency(J). والثالث لا يثبت بغياب رابطٍ مسجَّل حين لم تُنفَّذ قواعد الحال والفقرة
                why_ = rec.get('J_why') or ''
                ext = ('مثبت: آخر السورة' if why_ == 'آخر السورة' else
                       'غير مثبت: بعده ' + why_.split('وما بعدها ', 1)[1] + ' — الحال والعطف والاستئناف مرشّحاتٌ في سجل العطف، ولا يثبت بها الاستقلال'
                       if 'وما بعدها ' in why_ else
                       'غير مثبت: بعده ما له الصدارة فلا يعمل فيه ما قبله لفظاً، وقد يبقى تعلّقٌ معنوي' if why_ else
                       'غير مثبت')
                J.O['closure'] = dict(local='مكتملة محلياً', level='جملة (لا فقرة)', external=ext)
                close(J, Evidence('استُوفيت التزامات الجملة', [f'النواة: {my_nuc[0][1]}', f'{len(J.Omega)} التزاماً',
                                                              'الإغلاق محلي: Closed_k في مستوى الجملة']),
                      Evidence('حدّ الجملة ثابتٌ في مستواها', [f'W = {rec["W"]}', f'F = {rec["F"]}',
                                                              'لا رابط لفظي مسجَّل يعبر الحدّ (L = ∅ في القواعد المنفَّذة)',
                                                              f'الخلوّ من التعلّق الخارجي: {ext}']), T)
                st['J_closed'] += 1
                st['J_closed:external ' + ext.split(':')[0]] += 1
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
    linguistic_layer.samples = dict(rel=rel_samples, cond=cond_samples, coord=coord_samples, coord_records=coord_records,
                                    coord_failures=dict(failures))
    return out, st, records


def render_layer(G):
    """Render على أي طبقة: نصّ الوحدات/الكلمات بالترتيب (المصحفية: الكلمة نصّها؛ اللغوية: من الخلايا)"""
    return [c for c in flatten(G)]
