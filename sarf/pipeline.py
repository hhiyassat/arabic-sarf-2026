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
from .root import verse_morph, hfn
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
                    relations=self.relations, syll=self.syll, agreement=getattr(self, 'agreement', []),
                    morph=getattr(self, 'morph', []))


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
    ctx.candidates = reject_candidates(ctx.candidates, ctx.words, res.lex)
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

def _governed_verbs(ctx):
    """الجذع الذي يعمل فيه عاملٌ مقبول عملَ الفعل (لَنۡ نَّبۡرَحَ، حَتَّىٰ يَرۡجِعَ، لِيُعَذِّبَ): ثبتت فعليته بالعامل
    وإن لم تثبت بصيغته. → {(رقم الكلمة، رقم الخانة): العامل}"""
    status = {(f['word_index'], f['operator'], f['group']): f.get('status') for f in ctx.candidates}
    out = {}
    for r in ctx.relations:
        t = r.get('target')
        if t and t.get('pos') == 'verb' and t['type'] == 'جذع' and \
                status.get((r['word_index'], r['operator'], r['group'])) == ACCEPTED:
            out[(t['word_index'], t['slot'])] = r['operator']
    return out

def _governed_nouns(ctx):
    """الجذع الذي يعمل فيه حرف جرٍّ مقبول: ثبتت اسميته بالعامل (بِدَيۡنٍ، إِلَىٰ أَجَلٍ)"""
    status = {(f['word_index'], f['operator'], f['group']): f.get('status') for f in ctx.candidates}
    return {(r['target']['word_index'], r['target']['slot']) for r in ctx.relations
            if r.get('target') and r.get('expected') == 'جر' and r['target']['type'] == 'جذع' and
            status.get((r['word_index'], r['operator'], r['group'])) == ACCEPTED}

LEX_MADI_FORMS = ('II', 'V', 'VI', 'VII', 'VIII', 'IX', 'X')       # لا فَاعَلَ (خَاتَم، عَالَم)
# عواملُ لا يليها إلا المضارع بصورتها المكتوبة: لَمْ، لَنْ، كَيْ، ولام الأمر والتعليل
VERB_ONLY_OPS = {'لَمْ', 'لَنْ', 'كَيْ', 'لِكَيْ', 'لْ'}      # لا «لِ»: لام الجر مكسورةٌ مثلها (لِنُورِهِ)


def _noun_licence(text):
    """رخصةُ اسمٍ للكلمة كلّها (مدخلٌ أو بناءٌ اسمي في HFN)، دون رخص الفعل"""
    from .cells import stem_licence, licence_strength
    lic = list(stem_licence(text, verbs=False))
    return bool(lic) and licence_strength(lic) >= 1


def _elative_shape(text):
    """أَفۡعَلُ: همزةٌ مفتوحة، فساكن، فمفتوح (أَقۡسَطُ، أَقۡوَمُ، أَدۡنَىٰ): يلتبس فيه مضارع المتكلم باسم التفضيل"""
    from .chars import letters, FATHA, SUKUN
    t = letters(text)
    return len(t) >= 3 and t[0][0] == 'أ' and FATHA in t[0][1] and SUKUN in t[1][1] and FATHA in t[2][1]


def _lexical_verbs(ctx, governed):
    """الفعلية بشهادة HFN حيث لا تثبتها الكتابة وحدها ولا عامل (يَسۡتَطِيعُ، تُذَكِّرَ، عَلَّمَ):
      - صورة المضارع (حرف مضارعةٍ في أوله) يقبل قالبُها جذراً ووزناً بحدثٍ في HFN (مستوى الحدث)، بلا منافس؛
      - أو ماضٍ يطابق فعل HFN حرفاً وحركة في وزنٍ لا يكون للاسم (II، III، V–X)؛ لا فَعَلَ (مَالَ اسمٌ وفعل)
        ولا أَفۡعَلَ (أَكۡبَرَ اسم تفضيلٍ وفعل).
    والكلمة بعد «أل» أو المنوَّنة أو المجرورة بحرفٍ مقبول اسمٌ، فلا تدخل. → {(رقم الكلمة، رقم الخانة): الدليل}"""
    from .affix import stem_info
    from .root import morph
    from .chars import FATHATAN, DAMMATAN, KASRATAN
    from .root import _plain_vowels
    nouns = _governed_nouns(ctx)
    ctx.lexical_madi = set()
    verb_only = {}
    for r in ctx.relations:
        t = r.get('target') or {}
        try:
            w = ctx.segments[r['word_index']]['slots'][r['slot']]['text']
        except (IndexError, KeyError, TypeError):
            continue
        if t.get('type') == 'جذع' and w in VERB_ONLY_OPS:
            verb_only[(t['word_index'], t['slot'])] = w
    out = {}
    for seg in ctx.segments:
        for s in seg['slots']:
            key = (seg['word_index'], s['index'])
            if s['type'] != 'جذع' or key in governed or key in nouns:
                continue
            if s['index'] > 0 and seg['slots'][s['index'] - 1]['type'] == 'أل':
                continue
            if set(s['text']) & {FATHATAN, DAMMATAN, KASRATAN}:
                continue
            info = stem_info(s['text'])
            if info['pos'] is not None:
                continue
            if info['kind'] == 'mudari':
                from .protected import protected as _prot
                pr = _prot(s['text'])
                if pr and not pr['ambiguous'] and 'VERBAL' in (pr.get('source') or ''):
                    # تصريفٌ مسجَّل في جرد العوامل الفعلية المعتمد (يَكُونَ، تَكُونَ، أَكُونَ): فعلٌ بالجرد، ولا جذر له بحكم الدستور
                    out[key] = f'تصريفٌ من تصاريف العامل الفعلي «{pr["identity"]}» في الجرد المعتمد (sarf/protected.py VERBAL)'
                    continue
            if info['kind'] == 'mudari' and info['prefix'] == 'أ' and key not in verb_only:
                continue                     # «أ» في أوله: همزةٌ أصلية (أَمۡر، أَهۡل) أو أَفۡعُل وأَفۡعَل (أَنۡفُس، أَشَدّ، أَقۡوَمُ)
            if info['kind'] == 'mudari' and key not in verb_only and _noun_licence(s['text']):
                continue                     # للكلمة كلّها رخصةُ اسم (نَفۡس، يَد، تَقَلُّب): فقد يكون حرفها الأول أصلياً
            if info['kind'] == 'mudari':
                m = morph(s['text'], dict(info, pos='verb'))
                if m and m['licensed'] and any(x['root'][:1] in (info['prefix'], 'ء' if info['prefix'] == 'أ' else '')
                                               for x in m['licensed']):
                    continue                 # جذرٌ أوله حرف المضارعة نفسه (نُور، نَار): فالحرف قد يكون أصلياً
                if m and m['licensed'] and m['status'] in ('accepted', 'deferred'):
                    # كل قراءةٍ مرخَّصة حدثٌ في HFN (فعل)، وإن تعدّد جذرها (يَأۡبَ: أبو أو أبي): فالفعلية ثابتة والجذر مؤجَّل
                    vs = sorted({x['verb'] for x in m['licensed']})
                    out[key] = f'صورة المضارع (حرف المضارعة «{info["prefix"]}») تطابق حدث HFN ' + ' أو '.join(f'«{v}»' for v in vs)
                    # تَفَعَّلَ وتَفَاعَلَ: التاء من قالب الماضي؛ فإن طابق الماضيَ حرفاً وحركة وختم بالفتح فهو ماضٍ (تَقَبَّلَ)،
                    # والمضموم آخره أو الساكن مضارعٌ حُذفت إحدى تاءيه (تَنَزَّلُ)
                    if info['prefix'] == 'ت' and any(x['form_class'] in ('V', 'VI') and _plain_vowels(x['verb']) == _plain_vowels(s['text'])
                                                     for x in m['licensed']):
                        ctx.lexical_madi.add(key)
                        out[key] += '؛ ويطابق ماضيه حرفاً وحركة (التاء من قالب تَفَعَّلَ أو تَفَاعَلَ)'
                elif m and m['status'] == 'accepted' and m.get('level') == 'root' and key in verb_only:
                    out[key] = f'العامل «{verb_only[key]}» لا يدخل إلا على المضارع، وقالب المضارع يقبل الجذر {m["root"]} ' \
                               f'(الوزن {m["form_class"]}) المسجَّل في HFN'
            else:
                m = morph(s['text'], info)
                if m and m.get('level') == 'lemma' and m['licensed'] and not s['text'].rstrip('ًٌٍَُِّْٰ').endswith('ى') and \
                        {x['form_class'] for x in m['licensed']} <= set(LEX_MADI_FORMS):
                    x = m['licensed'][0]
                    out[key] = f'يطابق فعل HFN «{x["verb"]}» حرفاً وحركة في وزنٍ لا يكون للاسم ({x["form_class"]})'
                    ctx.lexical_madi.add(key)            # ماضٍ: يُحسب إسناده بصيغة الماضي
    return out


def _agree(ctx, res):
    ctx.governed = _governed_verbs(ctx)
    ctx.lexical_verbs = _lexical_verbs(ctx, ctx.governed)
    ctx.governed = {**ctx.governed, **{k: 'HFN' for k in ctx.lexical_verbs}}
    va = verse_agreement(ctx.segments, ctx.governed)
    from .affix import stem_info
    from .agreement import agreement as _agr
    for key in getattr(ctx, 'lexical_madi', ()):
        txt = ctx.segments[key[0]]['slots'][key[1]]['text']
        g = _agr(txt, dict(stem_info(txt), pos='verb', kind='madi', prefix=None))
        if g:
            va[key] = dict(g, verb_by_lexicon=ctx.lexical_verbs.get(key))
    for key, ev in getattr(ctx, 'lexical_verbs', {}).items():
        if key in va:
            va[key] = dict(va[key], verb_by_lexicon=ev)
    ctx.agreement = [dict(word_index=wi, slot=si, **{k: v for k, v in agr.items()}) for (wi, si), agr in sorted(va.items())]
    return f"{len(ctx.agreement)} فعلاً بسمات التوافق"

def _root(ctx, res):
    ctx.morph = verse_morph(ctx.segments, getattr(ctx, 'governed', None) or _governed_verbs(ctx),
                            nouns=_governed_nouns(ctx))
    n = sum(m['status'] == 'accepted' for m in ctx.morph)
    return f"{n} جذراً مقبولاً من {len(ctx.morph)}" + ('' if hfn() else ' (HFN غير موجود)')

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
    Stage('agree', _agree, ('segments', 'relations', 'candidates'), ('agreement',), 'سمات الفعل بالتوافق مع الضمير (T18)'),
    Stage('root', _root, ('segments', 'relations', 'candidates'), ('morph',), 'الجذر والصيغة المرخَّصان (T19c) بشهادة HFN'),
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
