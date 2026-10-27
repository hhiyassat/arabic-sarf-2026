# -*- coding: utf-8 -*-
"""
sarf.pipeline — تشغيل المراحل بالترتيب على كائن واحد للآية (VerseContext).

كل مرحلة لها اسم، وما تحتاجه (requires) وما تضيفه (provides). والكائن يُراكِم ولا يَستبدل:
تضيف كل مرحلة حقولها ولا تمحو ما قبلها، فيمكن فحص ناتج أي مرحلة.

المراحل الافتراضية:
    normalize  → normalized                 التطبيع (sarf.normalize)
    match      → words, candidates          مطابقة العوامل (sarf.match)
    evidence   → (status في candidates)     نفي المرشَّح بالكتابة (sarf.evidence)
    syllabify  → syll                       التقطيع (sarf.syllabify)
    align      → operators                  ربط العامل بمقاطعه (sarf.align)

موضع المقشِّر (حين يُكتب): مرحلة بين normalize وmatch.

result() يعيد القاموس نفسه الذي كانت analyze تعيده (verse, normalized, syllabified_text,
words, operators, syll)، فتبقى الاختبارات والنواتج السابقة محكّاً لأي تغيير في التركيب.
"""
from .normalize import uthmani_normalize
from .match import extract
from .evidence import reject_candidates
from .align import syllables_by_word, align
from . import syllabify as cv

UTHMANI = {'auto': None, 'on': True, 'off': False}   # auto←None (تلقائي) / on←True / off←False


class VerseContext:
    """كائن الآية: الدخل، وما تضيفه كل مرحلة، وسجل المراحل المنفَّذة."""

    def __init__(self, verse, uthmani='auto'):
        self.verse = verse
        self.uthmani = uthmani
        self.done = []          # أسماء المراحل المنفَّذة بالترتيب
        self.log = []           # (المرحلة، ملخّص قصير)

    def has(self, field):
        return hasattr(self, field)

    def result(self):
        """الناتج بصيغة analyze: النص كما هو، والتقطيع على النص المطبَّع نفسه"""
        return dict(verse=self.verse, normalized=self.normalized, syllabified_text=self.normalized,
                    words=self.words, operators=self.operators, syll=self.syll)


class Stage:
    def __init__(self, name, fn, requires, provides, doc):
        self.name, self.fn, self.requires, self.provides, self.doc = name, fn, requires, provides, doc

    def __repr__(self):
        return f"{self.name}: {', '.join(self.requires) or '—'} → {', '.join(self.provides) or '—'}"


# ---------- المراحل ----------
def _normalize(ctx, cat):
    ctx.normalized = uthmani_normalize(ctx.verse, implicit_sukun=UTHMANI[ctx.uthmani])
    return f"{len(ctx.normalized.split())} كلمة"

def _match(ctx, cat):
    ctx.words, ctx.candidates = extract(cat, ctx.normalized)
    return f"{len(ctx.candidates)} مرشَّحاً"

def _evidence(ctx, cat):
    ctx.candidates = reject_candidates(ctx.candidates, ctx.words)
    n = sum(f['status'] == 'rejected' for f in ctx.candidates)
    return f"مرفوضة بالكتابة: {n}"

def _syllabify(ctx, cat):
    ctx.syll = cv.run(ctx.normalized)
    return f"{ctx.syll['n_syll']} مقطعاً"

def _align(ctx, cat):
    ctx.operators = align(ctx.candidates, syllables_by_word(ctx.syll), ctx.words)
    return f"{len(ctx.operators)} عاملاً مربوطاً"

STAGES = [
    Stage('normalize', _normalize, (), ('normalized',), 'التطبيع: العثماني إلى إملائي'),
    Stage('match', _match, ('normalized',), ('words', 'candidates'), 'مطابقة العوامل بحسب الفهرس'),
    Stage('evidence', _evidence, ('words', 'candidates'), (), 'نفي المرشَّح بالكتابة'),
    Stage('syllabify', _syllabify, ('normalized',), ('syll',), 'التقطيع CV'),
    Stage('align', _align, ('words', 'candidates', 'syll'), ('operators',), 'ربط العامل بمقاطعه'),
]


class Pipeline:
    def __init__(self, cat, stages=None):
        self.cat = cat
        self.stages = list(stages or STAGES)

    def names(self):
        return [s.name for s in self.stages]

    def run(self, verse, uthmani='auto', until=None, skip=()):
        """
        until: آخر مرحلة تُنفَّذ (ثم يتوقف)؛ skip: مراحل تُتجاوز.
        المرحلة التي ينقصها حقل تحتاجه ترفع خطأً يسمّي الحقل والمرحلة.
        """
        for name in ([until] if until else []) + list(skip):
            if name not in self.names():
                raise ValueError(f"مرحلة غير معروفة: {name} (المراحل: {', '.join(self.names())})")
        ctx = VerseContext(verse, uthmani)
        for st in self.stages:
            if st.name in skip:
                ctx.log.append((st.name, 'تُجووزت'))
            else:
                missing = [f for f in st.requires if not ctx.has(f)]
                if missing:
                    raise RuntimeError(f"المرحلة {st.name} تحتاج {', '.join(missing)}، ولم تُنتجه مرحلة قبلها")
                ctx.log.append((st.name, st.fn(ctx, self.cat)))
                ctx.done.append(st.name)
            if st.name == until:
                break
        return ctx


def analyze(cat, verse, uthmani='auto'):
    """تحليل آية بكل المراحل الافتراضية → قاموس الناتج (كما كان في analyze السابقة)"""
    return Pipeline(cat).run(verse, uthmani).result()
