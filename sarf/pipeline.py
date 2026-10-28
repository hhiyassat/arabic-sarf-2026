# -*- coding: utf-8 -*-
"""
sarf.pipeline — تشغيل المراحل بالترتيب على كائن واحد للآية (VerseContext).

كل مرحلة لها اسم، وما تحتاجه (requires) وما تضيفه (provides). والكائن يُراكِم ولا يَستبدل:
تضيف كل مرحلة حقولها ولا تمحو ما قبلها، فيمكن فحص ناتج أي مرحلة.

المراحل الافتراضية:
    normalize  → normalized                 التطبيع (sarf.normalize)
    match      → words, candidates          مطابقة العوامل (sarf.match)
    evidence   → (status في candidates)     نفي المرشَّح بالكتابة (sarf.evidence)
    segment    → segments, relations        الخانات وأنواعها، والعامل ← المعمول (sarf.segment)
    judge      → (status في candidates)     القبول بدليل إيجابي، وإلا التأجيل (sarf.judge، T09)
    syllabify  → syll                       تقطيع ما ليس عاملاً ولا مبنياً (sarf.segment)
    align      → operators                  ربط العامل بخانته وعلاقته (sarf.align)

المقشِّر بعد المطابقة والنفي لأنه يبني خانات العوامل منها؛ وحين يُكتب تقشير زوائد البنية
(سألتمونيها) تصير المطابقة على الخانات.

result() يعيد القاموس نفسه الذي كانت analyze تعيده (verse, normalized, syllabified_text,
words, operators, syll)، فتبقى الاختبارات والنواتج السابقة محكّاً لأي تغيير في التركيب.
"""
from .normalize import uthmani_normalize
from .match import extract
from .evidence import reject_candidates
from .status import BLOCKED, ACCEPTED
from .judge import judge
from .agreement import verse_agreement
from .align import align
from .segment import segment, syllabify_units
from .lexicon import MabniLexicon

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
                    words=self.words, operators=self.operators, segments=self.segments,
                    relations=self.relations, syll=self.syll, agreement=getattr(self, 'agreement', []))


class Stage:
    def __init__(self, name, fn, requires, provides, doc):
        self.name, self.fn, self.requires, self.provides, self.doc = name, fn, requires, provides, doc

    def __repr__(self):
        return f"{self.name}: {', '.join(self.requires) or '—'} → {', '.join(self.provides) or '—'}"


# ---------- المراحل ----------
def _normalize(ctx, res):
    ctx.normalized = uthmani_normalize(ctx.verse, implicit_sukun=UTHMANI[ctx.uthmani])
    return f"{len(ctx.normalized.split())} كلمة"

def _match(ctx, res):
    ctx.words, ctx.candidates = extract(res.cat, ctx.normalized)
    return f"{len(ctx.candidates)} مرشَّحاً"

def _evidence(ctx, res):
    ctx.candidates = reject_candidates(ctx.candidates, ctx.words)
    n = sum(f['status'] == BLOCKED for f in ctx.candidates)
    return f"ممنوعة بالكتابة: {n}"

def _segment(ctx, res):
    ctx.segments, ctx.relations = segment(ctx.words, ctx.candidates, res.lex)
    n = sum(len(s['slots']) for s in ctx.segments)
    return f"{n} خانة، {len(ctx.relations)} علاقة"

def _judge(ctx, res):
    judge(ctx.candidates, ctx.segments, ctx.relations)
    n = sum(f['status'] == ACCEPTED for f in ctx.candidates)
    return f"مقبولة: {n}"

def _agree(ctx, res):
    ctx.agreement = [dict(word_index=wi, slot=si, **{k: v for k, v in agr.items()})
                     for (wi, si), agr in sorted(verse_agreement(ctx.segments).items())]
    return f"{len(ctx.agreement)} فعلاً بسمات التوافق"

def _syllabify(ctx, res):
    ctx.syll = syllabify_units(ctx.segments)
    return f"{ctx.syll['n_syll']} مقطعاً"

def _align(ctx, res):
    ctx.operators = align(ctx.candidates, ctx.segments, ctx.relations)
    return f"{len(ctx.operators)} عاملاً مربوطاً"

STAGES = [
    Stage('normalize', _normalize, (), ('normalized',), 'التطبيع: العثماني إلى إملائي'),
    Stage('match', _match, ('normalized',), ('words', 'candidates'), 'مطابقة العوامل بحسب الفهرس'),
    Stage('evidence', _evidence, ('words', 'candidates'), (), 'نفي المرشَّح بالكتابة'),
    Stage('segment', _segment, ('words', 'candidates'), ('segments', 'relations'),
          'الخانات (عامل، مبني، أل، جذع) والعامل ← المعمول'),
    Stage('judge', _judge, ('candidates', 'segments', 'relations'), (),
          'الحكم بالقبول بدليل إيجابي (T07، T09)؛ وما سواه مؤجَّل أو ممنوع'),
    Stage('agree', _agree, ('segments',), ('agreement',), 'سمات الفعل بالتوافق مع الضمير (T18)'),
    Stage('syllabify', _syllabify, ('segments',), ('syll',), 'تقطيع ما ليس عاملاً ولا مبنياً'),
    Stage('align', _align, ('candidates', 'segments', 'relations'), ('operators',), 'ربط العامل بخانته وعلاقته'),
]


class Pipeline:
    def __init__(self, cat, stages=None, lex=None):
        self.cat = cat
        self.lex = lex if lex is not None else MabniLexicon()
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
                ctx.log.append((st.name, st.fn(ctx, self)))
                ctx.done.append(st.name)
            if st.name == until:
                break
        return ctx


def analyze(cat, verse, uthmani='auto'):
    """تحليل آية بكل المراحل الافتراضية → قاموس الناتج (كما كان في analyze السابقة)"""
    return Pipeline(cat).run(verse, uthmani).result()
