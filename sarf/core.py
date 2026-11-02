# -*- coding: utf-8 -*-
"""
sarf.core — نواة الجبر اللساني المشتركة بين مراحل المشروع كلها:
المستويات، والدليل e، والالتزام في Ω، والهندسة G، والأثر T، وعمليات Extend وClose وDefer.

نُقلت كما هي من sarf.algebra (التي تستوردها منها)، لتستعملها كل مرحلةٍ من الاستلام إلى الجملة،
لا طبقة الجملة وحدها. لا منطق تحليلٍ هنا: أنواعٌ وعملياتٌ وقوانينها فقط.

    الدليل   e = ⟨السبب، الشروط، الموانع المنتفية مع برهان انتفائها⟩
    الامتداد G' = Extend_{k,r,e}(G, x)،   Ω(G') = (Ω(G) ∖ D_e) ∪ N_e
    الإغلاق  Ĝ = Close_k(G; e_c, e_b)     لا يكون إلا بشهادتَي الإكمال والحدّ، وΩ خالية من اللازم
"""
from dataclasses import dataclass, field

# طبقتان على النص نفسه تشتركان في الخلايا:
#   اللغوية: خلية ≺ مقطع ≺ وحدة لفظية ≺ جملة ≺ وحدة خطابية ≺ خطاب السورة
#   المصحفية: خلية ≺ كلمة ≺ آية ≺ سورة ≺ مصحف
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

    def stage(self, name, summary):
        """سجلّ مرحلةٍ من مراحل المحلّل (sarf.pipeline) في الأثر نفسه: اسمها وملخّص ناتجها"""
        self.append(dict(op='Stage', stage=name, summary=summary))


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
