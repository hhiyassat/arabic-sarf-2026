# -*- coding: utf-8 -*-
"""
sarf.engine — المحرّك الواحد من المصدر إلى الفقرة، قائماً على الاعتمادات (SARF_DEPENDENCY_PIPELINE_AND_COMPLETION_05).

يمتدّ بمعمار sarf.pipeline (Stage بما تحتاجه وما تضيفه) من الآية إلى المدخل كله، ولا يُنشئ محرّكاً موازياً:
  - كل مرحلةٍ منتِجةٌ (EngineStage) بمدخلاتٍ معلنة (requires، ولكلٍّ إصدارٌ اختياري) ومخرجاتٍ معلنة (provides) ومخطّط تحقّقٍ لكل مخرج،
    وتقابلها مراحل المصفوفة الوظيفية العشرين (functional) التي تنفّذها فعلاً.
  - الجدولة بالاعتماد (ترتيبٌ طوبولوجي مع كشف الدورات)، لا برقم المرحلة: هندسة الوحدات (من ١٧) تسبق السمات (٩) لأن السمات تحتاج الوحدات.
  - لكل مخرجٍ خانةٌ (Slot) ببصمة محتواه وإصدار منتِجه وبصمات مقدّماته؛ والأثر (OperationTrace) سجلّ كل تنفيذ بسببه.
  - حالة التنفيذ منفصلة عن الحكم اللغوي: EXECUTED، NOT_IMPLEMENTED، BLOCKED_DEPENDENCY، FAILED، DEFERRED_SEARCH_LIMIT؛
    ولا يُخفى بها حكمٌ لغوي مؤجَّل ولا تُخفي هي مرحلةً غير منفّذة.
  - المراجعة الراجعة (revise): دليلٌ لاحق يغيّر خانة → تُحفظ القيمة السابقة وسببها، ويُعاد حساب المستهلكين المتأثرين وحدهم بترتيبهم،
    وتُبطل الشهادات المبنية على مقدّماتٍ تغيّرت؛ ولا يُعاد ما لم يتأثر (التطبيع وقراءة المصدر).
  - منع الدوران: دورات المقدّمات بين العلاقات (A مقدّمته B ومقدّمة B هي A) تُكشف، وما استوفاه دليلٌ في دورةٍ غير مسندة لا يُعدّ مستوفى؛
    وللمراجعة حدٌّ تقني ينتج تأجيلاً مسمّى لا انفراداً ولا إغلاقاً.

    from sarf.engine import run
    ctx = run([(2, 282, نص)])          # أو run_ref('2:282')
    ctx.get('paragraphs'), ctx.status, ctx.trace
"""
import copy, hashlib, json, time

EXECUTED, NOT_IMPLEMENTED, BLOCKED, FAILED, SEARCH_LIMIT = ('EXECUTED', 'NOT_IMPLEMENTED', 'BLOCKED_DEPENDENCY', 'FAILED',
                                                             'DEFERRED_SEARCH_LIMIT')
ENGINE_VERSION = 'E05.1'


# ---------- البصمة ----------
def _canon(x, memo=None, _active=None):
    """الصورة القانونية للبصمة — بالمحتوى كاملاً (FA02 §٤، مراجعة المالك: كان الكائن ذو المعرّف يُختصر إلى «OBJ:معرّفه» فلا يدخل
    محتواه البصمة، فتغيّر محتواه بالمعرّف نفسه لا يغيّرها، ولا تكشفه المراجعة). فالكائن يُمثَّل بنوعه ومعرّفه وكل حقوله؛ والمشترك بين
    مواضع يُحسب مرةً (memo)؛ والدورة تُسمّى بمعرّف موضعها «CYCLE:…» لا تُقطع بصمت؛ ولا حدّ عمقٍ يحذف المحتوى"""
    memo = {} if memo is None else memo
    _active = set() if _active is None else _active
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    if isinstance(x, dict):
        return {str(k): _canon(v, memo, _active) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
    if isinstance(x, (list, tuple)):
        return [_canon(v, memo, _active) for v in x]
    if isinstance(x, (set, frozenset)):
        return sorted((json.dumps(_canon(v, memo, _active), ensure_ascii=False, sort_keys=True) for v in x))
    k = id(x)
    label = getattr(x, 'id', None) if isinstance(getattr(x, 'id', None), str) else getattr(x, 'uid', None)
    if k in memo:
        return memo[k]
    if k in _active:
        return f'CYCLE:{type(x).__name__}:{label}'
    _active.add(k)
    fields = {}
    if hasattr(x, '__dict__'):
        fields.update(vars(x))
    for cls in type(x).__mro__:
        for sl in getattr(cls, '__slots__', ()) or ():
            if sl not in fields and hasattr(x, sl):
                fields[sl] = getattr(x, sl)
    if not fields and not callable(x):
        fields = {'repr': repr(x)}
    out = {'__type__': type(x).__name__, '__id__': None if label is None else str(label),
           'fields': {str(f): _canon(v, memo, _active) for f, v in sorted(fields.items()) if not callable(v)}}
    _active.discard(k)
    memo[k] = out
    return out


def fingerprint(x):
    return hashlib.sha256(json.dumps(_canon(x), ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


# ---------- السياق والخانات ----------
class Slot:
    __slots__ = ('name', 'value', 'producer', 'producer_version', 'fp', 'deps', 'history', 'stale')

    def __init__(self, name, value, producer, producer_version, deps):
        self.name, self.value, self.producer, self.producer_version = name, value, producer, producer_version
        self.fp = fingerprint(value)
        self.deps = dict(deps)          # خانة المقدّمة → بصمتها وقت الإنتاج
        self.history = []               # القيم السابقة: (البصمة، السبب، الوقت)
        self.stale = False


class Context:
    """سياق التشغيل الواحد: الخانات، وحالة كل مرحلة، والأثر، وهوية التشغيل"""

    def __init__(self, verses, options=None):
        self.options = dict(options or {})
        self.slots = {}
        self.status = {}                # المرحلة → (الحالة، السبب)
        self.trace = []                 # OperationTrace: كل تنفيذ بمدخلاته ومخرجاته وسببه
        self.revisions = []
        self.input = list(verses)
        self.run_id = fingerprint([ENGINE_VERSION, self.input, sorted(self.options.items(), key=str)])

    def get(self, name):
        s = self.slots.get(name)
        if s is None:
            raise KeyError(f'خانةٌ غير منتَجة: {name}')
        return s.value

    def has(self, name):
        return name in self.slots and not self.slots[name].stale


# ---------- المراحل ----------
class EngineStage:
    def __init__(self, name, fn, requires, provides, functional, schema=None, version='1', implemented=True, doc='',
                 producers=(), linguistic_scope='', known_gaps=()):
        self.name, self.fn, self.functional, self.version, self.implemented, self.doc = name, fn, tuple(functional), version, implemented, doc
        # المدخل: «خانة» أو «خانة@إصدار المنتِج»
        self.requires = tuple(r.split('@')[0] for r in requires)
        self.requires_version = {r.split('@')[0]: r.split('@')[1] for r in requires if '@' in r}
        self.provides = tuple(provides)
        self.schema = dict(schema or {})
        self.producers = tuple(producers)
        self.linguistic_scope = linguistic_scope
        self.known_gaps = tuple(known_gaps)


class Engine:
    def __init__(self, stages, max_revision_steps=200):
        self.stages = {s.name: s for s in stages}
        self.producer_of = {}
        for s in stages:
            for p in s.provides:
                if p in self.producer_of:
                    raise ValueError(f'خانة {p} يعلنها منتِجان: {self.producer_of[p]} و{s.name}')
                self.producer_of[p] = s.name
        self.order = self._topo()
        self.max_revision_steps = max_revision_steps

    def _topo(self):
        """ترتيبٌ طوبولوجي من الاعتمادات؛ والدورة بين المراحل خطأٌ معماري يُرفع"""
        deps = {n: {self.producer_of[r] for r in s.requires if r in self.producer_of} for n, s in self.stages.items()}
        order, temp, done = [], set(), set()

        def visit(n, path):
            if n in done:
                return
            if n in temp:
                raise ValueError('دورة بين المراحل: ' + ' → '.join(path + [n]))
            temp.add(n)
            for d in sorted(deps[n]):
                visit(d, path + [n])
            temp.discard(n)
            done.add(n)
            order.append(n)
        for n in self.stages:
            visit(n, [])
        return order

    def dependents(self, slot):
        """كل المراحل التي تستهلك الخانة مباشرةً أو بواسطة"""
        out, frontier = set(), {slot}
        while frontier:
            nxt = set()
            for n, s in self.stages.items():
                if n not in out and set(s.requires) & frontier:
                    out.add(n)
                    nxt |= set(s.provides)
            frontier = nxt
        return [n for n in self.order if n in out]

    def graph(self):
        """رسم الاعتمادات الفعلي المولَّد من السجل: المنتِج ← الخانة ← المستهلك"""
        return [dict(stage=n, functional=list(s.functional), requires=list(s.requires), provides=list(s.provides),
                     upstream=sorted({self.producer_of.get(r, 'INPUT') for r in s.requires})) for n, s in
                ((n, self.stages[n]) for n in self.order)]

    def _execute(self, ctx, n, reason):
        s = self.stages[n]
        if not s.implemented:
            ctx.status[n] = (NOT_IMPLEMENTED, '; '.join(s.known_gaps) or 'غير منفّذة')
            ctx.trace.append(dict(stage=n, status=NOT_IMPLEMENTED, reason=reason))
            return
        missing = [r for r in s.requires if not ctx.has(r)]
        badv = [f'{r}: المطلوب {v} والمنتَج {ctx.slots[r].producer_version}' for r, v in s.requires_version.items()
                if r in ctx.slots and ctx.slots[r].producer_version != v]
        if missing or badv:
            ctx.status[n] = (BLOCKED, ('خانات غير منتَجة: ' + ', '.join(missing)) if missing else 'إصدارٌ مخالف: ' + '; '.join(badv))
            ctx.trace.append(dict(stage=n, status=BLOCKED, reason=ctx.status[n][1]))
            return
        t0 = time.time()
        try:
            out = s.fn(ctx, {r: ctx.get(r) for r in s.requires})
        except Exception as e:      # الإخفاق يُسجَّل ولا يُخفى
            ctx.status[n] = (FAILED, f'{type(e).__name__}: {e}')
            ctx.trace.append(dict(stage=n, status=FAILED, reason=ctx.status[n][1]))
            return
        out = out or {}
        miss_out = [p for p in s.provides if p not in out]
        bad = []
        for p in s.provides:
            if p in out and p in s.schema:
                why = s.schema[p](out[p])
                if why:
                    bad.append(f'{p}: {why}')
        if miss_out or bad:
            ctx.status[n] = (FAILED, ('مخرجاتٌ معلنة لم تُنتَج: ' + ', '.join(miss_out)) if miss_out else 'مخالفة المخطّط: ' + '; '.join(bad))
            ctx.trace.append(dict(stage=n, status=FAILED, reason=ctx.status[n][1]))
            return
        deps = {r: ctx.slots[r].fp for r in s.requires}
        changed = []
        for p in s.provides:
            old = ctx.slots.get(p)
            new = Slot(p, out[p], n, s.version, deps)
            if old is not None:
                new.history = old.history + [dict(fp=old.fp, reason=reason, value=old.value)]
            ctx.slots[p] = new
            changed.append(dict(slot=p, fp=new.fp, previous=old.fp if old else None))
        ctx.status[n] = (EXECUTED, reason)
        ctx.trace.append(dict(stage=n, status=EXECUTED, reason=reason, version=s.version, inputs=deps, outputs=changed,
                              seconds=round(time.time() - t0, 3)))

    def run(self, ctx, targets=None):
        need = set(self.order)
        if targets:
            need = set()
            stack = [self.producer_of[t] if t in self.producer_of else t for t in targets]
            while stack:
                n = stack.pop()
                if n in need:
                    continue
                need.add(n)
                stack += [self.producer_of[r] for r in self.stages[n].requires if r in self.producer_of]
        for n in self.order:
            if n in need:
                self._execute(ctx, n, 'تشغيلٌ أول')
        return ctx

    def revise(self, ctx, slot, value, reason):
        """دليلٌ لاحق يغيّر خانة: تُحفظ السابقة، ويُعاد حساب المتأثرين وحدهم؛ وما تجاوز الحدّ التقني يُؤجَّل بتسمية"""
        if slot not in ctx.slots:
            raise KeyError(slot)
        old = ctx.slots[slot]
        new = Slot(slot, value, f'REVISION:{old.producer}', old.producer_version, old.deps)
        new.history = old.history + [dict(fp=old.fp, reason=reason, value=old.value)]
        ctx.slots[slot] = new
        aff = self.dependents(slot)
        ctx.revisions.append(dict(slot=slot, previous=old.fp, new=new.fp, reason=reason, recomputed=aff))
        for n in aff:
            for p in self.stages[n].provides:
                if p in ctx.slots:
                    ctx.slots[p].stale = True
        steps = 0
        for n in aff:
            steps += 1
            if steps > self.max_revision_steps:
                for m in aff[aff.index(n):]:
                    ctx.status[m] = (SEARCH_LIMIT, f'بلغت المراجعة حدّها التقني ({self.max_revision_steps}) قبل {m}: نتائجه السابقة مُبطلة غير معادة')
                    ctx.trace.append(dict(stage=m, status=SEARCH_LIMIT, reason=ctx.status[m][1]))
                break
            self._execute(ctx, n, f'مراجعة راجعة: {slot} ({reason})')
        return ctx


# ---------- كشف دورات المقدّمات ----------
def evidence_cycles(records):
    """دورات المقدّمات بين العلاقات: مقدّمةٌ تساوي معرّف علاقةٍ أخرى ضمن السجلات → قائمة الدورات (كلٌّ قائمة معرّفات)"""
    ids = {r['relation_id'] for r in records}
    g = {r['relation_id']: [p for p in (r.get('premises') or []) if isinstance(p, str) and p in ids and p != r['relation_id']]
         for r in records}
    cycles, color, stack = [], {}, []

    def dfs(u):
        color[u] = 1
        stack.append(u)
        for v in g.get(u, ()):
            if color.get(v) == 1:
                cycles.append(stack[stack.index(v):] + [v])
            elif not color.get(v):
                dfs(v)
        stack.pop()
        color[u] = 2
    for u in sorted(g):
        if not color.get(u):
            dfs(u)
    return cycles
