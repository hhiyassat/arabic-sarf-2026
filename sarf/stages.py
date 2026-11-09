# -*- coding: utf-8 -*-
"""
sarf.stages — منتِجو المحرّك (sarf.engine) ومصفوفة المراحل العشرين (SARF_DEPENDENCY_PIPELINE_AND_COMPLETION_05 §٣–٥).

كل منتِجٍ هنا يستدعي الشيفرة الحقيقية التي تنفّذ المرحلة (لا قيمةً ثابتة)، ويعلن ما يحتاجه وما ينتجه ومخطّط مخرجه.
والمراحل التي لا منتِج حقيقيّ لها بعد معلنةٌ NOT_IMPLEMENTED بنواقصها، لا مغطّاةً بغلاف.

    from sarf.stages import run, run_ref, ENGINE, MATRIX
    ctx = run_ref('2:282')
"""
import os
from .engine import Engine, EngineStage, Context

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CAT = {}


def _catalog():
    if 'c' not in _CAT:
        from .catalog import Catalog
        _CAT['c'] = Catalog([os.path.join(H, 'operators_catalog.jsonl'), os.path.join(H, 'operators_catalog_split_vocalized.csv')])
    return _CAT['c']


def _key(s, v):
    return f'{s}:{v}'


# ---------- المخطّطات: نوع المخرج وهويات محتواه، لا وجود الحقل وحده ----------
def _per_verse(check):
    def f(x):
        if not isinstance(x, dict) or not x:
            return 'ليس قاموساً بالآيات'
        for k, v in x.items():
            if not isinstance(k, str) or k.count(':') != 1:
                return f'مفتاحٌ ليس «سورة:آية»: {k!r}'
            w = check(v)
            if w:
                return f'{k}: {w}'
        return None
    return f


def _sch_source(x):
    if not isinstance(x, dict) or not x.get('verses'):
        return 'لا آيات'
    if set(x['fingerprints']) != {_key(s, v) for s, v, _ in x['verses']}:
        return 'بصمات المصدر لا تطابق الآيات'
    return None


_sch_norm = _per_verse(lambda v: None if isinstance(v, dict) and isinstance(v.get('analysis'), str) and v.get('ops_analysis') is not None
                       and v.get('cells_analysis') is not None else 'ناتج التطبيع ناقص (analysis، ops_analysis، cells_analysis)')
_sch_an = _per_verse(lambda a: None if isinstance(a, dict) and all(k in a for k in ('normalized', 'words', 'segments', 'operators', 'syll',
                                                                                      'agreement', 'morph')) and
                     len(a['segments']) == len(a['normalized'].split()) else 'التحليل ناقص أو عدد الخانات لا يطابق عدد الكلمات')


def _sch_records(x):
    if not isinstance(x, dict):
        return 'ليس قاموساً'
    ids = [r['relation_id'] for v in x.values() for r in v['records']]
    if len(ids) != len(set(ids)):
        return 'معرّف علاقةٍ مكرّر'
    for v in x.values():
        for r in v['records']:
            if r.get('status') not in ('LICENSED', 'DEFERRED', 'REJECTED', 'CONFLICT', 'CANDIDATE', 'PREFERRED'):
                return f"حالة علاقةٍ غير معروفة: {r.get('status')}"
    return None


def _sch_certs(x):
    if not isinstance(x, dict):
        return 'ليس قاموساً'
    for k, c in x.items():
        if c.get('sentence') != k or 'verdict_by_level' not in c:
            return f'شهادةٌ بلا هوية جملتها: {k}'
        oids = [o['obligation_id'] for o in c['obligations']]
        if len(oids) != len(set(oids)):
            return f'{k}: التزامٌ مكرّر'
    return None


# ---------- المنتِجون ----------
def p_source(ctx, _):
    import hashlib
    from . import quran_source
    mode = ctx.options.get('mode') or quran_source.uthmani_mode()
    return dict(source=dict(verses=list(ctx.input), mode=mode,
                            fingerprints={_key(s, v): hashlib.sha256(t.encode()).hexdigest()[:16] for s, v, t in ctx.input}))


def p_normalization(ctx, d):
    from .normalize_trace import normalize_traced
    from .pipeline import UTHMANI
    src = d['source']
    return dict(normalization={_key(s, v): normalize_traced(t, implicit_sukun=UTHMANI[src['mode']]) for s, v, t in src['verses']})


def p_verse_analysis(ctx, d):
    """المراحل الصرفية للآية (sarf.pipeline.STAGES) على التطبيع المنتَج مرةً واحدة: لا يُعاد التطبيع هنا"""
    import copy
    from .pipeline import Pipeline, VerseContext
    pipe = Pipeline(_catalog())
    out, logs = {}, {}
    for s, v, t in d['source']['verses']:
        k = _key(s, v)
        vc = VerseContext(t, d['source']['mode'])
        vc.normalized = d['normalization'][k]['analysis']
        lg, snaps = [('normalize', 'من خانة التطبيع (sarf.normalize_trace)، منتَجةً مرةً واحدة')], {}
        vc.done.append('normalize')
        for st in pipe.stages[1:]:
            lg.append((st.name, st.fn(vc, pipe)))
            vc.done.append(st.name)
            if st.name in ('evidence', 'judge'):
                snaps[st.name] = copy.deepcopy(vc.candidates)
        out[k] = vc.result()
        logs[k] = dict(logs=lg, snaps=snaps, docs={st.name: st.doc for st in pipe.stages})
    return dict(analysis=out, verse_logs=logs)


def p_cells(ctx, d):
    from .numbering import code
    return dict(cells={k: [code(w) for w in a['normalized'].split()] for k, a in d['analysis'].items()})


def p_syllables(ctx, d):
    from . import syllabify as cvmod
    return dict(syllables={k: cvmod.run(a['normalized']) for k, a in d['analysis'].items()})


def p_protection(ctx, d):
    """الحماية بالوجه: لكل وحدةٍ صرفية حكم البوابة (sarf.protected) كما طُبّق قبل توليد الجذور في sarf.root"""
    out = {}
    for k, a in d['analysis'].items():
        rows = []
        for m in a.get('morph') or []:
            pr = m.get('protected')
            if pr or m.get('status') == 'not_applicable':
                rows.append(dict(word_index=m.get('word_index'), slot=m.get('slot'), text=m.get('text'), status=m.get('status'),
                                 reason=m.get('reason'), cls=(pr or {}).get('cls'), alternative=m.get('alternative')))
        out[k] = rows
    return dict(protection=out)


def p_units(ctx, d):
    from .algebra import sentence_geo, Trace
    T = Trace()
    out = {}
    for s, v, _ in d['source']['verses']:
        k = _key(s, v)
        S_, U = sentence_geo(d['analysis'][k], f'Q{s}:{v}', T)
        out[k] = dict(S=S_, units=U)
    return dict(units=out)


def p_features(ctx, d):
    from .features import unit_features
    return dict(features={k: unit_features(d['analysis'][k], d['units'][k]['units']) for k in d['analysis']})


def p_linguistic(ctx, d):
    from .algebra import Trace, linguistic_layer, cross_ayah_links
    from .analyze import analyze
    items, prev, cross, ends = [], None, [], set()
    for s, v, t in d['source']['verses']:
        k = _key(s, v)
        a, U, S_ = d['analysis'][k], d['units'][k]['units'], d['units'][k]['S']
        items.append((s, v, a, U, S_))
        cur = dict(s=s, v=v, text=t, a=a, units=U, S=S_)
        if prev is not None:
            cross += cross_ayah_links(lambda t_: analyze(_catalog(), t_, d['source']['mode']), prev, cur)
            ends.add((prev['s'], prev['v']))
        prev = cur
    cond, rels, coords = [], [], []
    LT, st, _ = linguistic_layer(items, Trace(), 'engine', cross=cross, checked_ends=frozenset(ends), cond_out=cond, rel_out=rels,
                                 coord_out=coords)
    return dict(sentences=dict(LT=LT, stats=st, cross=cross), legacy=dict(cond=cond, rel=rels, coord=coords))


def p_relations(ctx, d):
    from .relations import verse_relations
    out = {}
    for s, v, _ in d['source']['verses']:
        k = _key(s, v)
        out[k] = verse_relations(d['analysis'][k], d['units'][k]['units'], d['features'][k], k,
                                 legacy_cond=d['legacy']['cond'], legacy_rel=d['legacy']['rel'],
                                 legacy_coord=d['legacy'].get('coord'))
    return dict(records_initial=out)


def p_face_reconciliation(ctx, d):
    from .reconcile import reconcile_features, check_consistency
    out, log, errs = {}, {}, {}
    for k in d['features']:
        recs = d['records_initial'][k]['records']
        out[k], log[k] = reconcile_features(d['features'][k], recs)
        errs[k] = check_consistency(out[k], recs)
    return dict(features_final=out, reconciliation=dict(log=log, errors=errs))


def p_relations_final(ctx, d):
    """FA02 §٢ (مراجعة المالك: features_final لا يستهلكها أحد): العلاقات النهائية تُبنى من السمات المصالَحة، بلا دورة — فالمصالحة
    تقرأ العلاقات الأولية (من مخرج المرحلة ١٣)، وهذه المرحلة تقرأ ناتج المصالحة. ثم مراجعةٌ مضبوطة واحدة: تُعاد المصالحة على
    العلاقات النهائية؛ فإن خرجت سماتٌ غير التي بُنيت عليها فالحالة NOT_CONVERGED مسمّاةً بوحداتها (لا تُكرَّر بلا حدّ، ولا يُخفى
    الفرق)، والفاحص المستقل يُشغَّل على الناتج النهائي"""
    from .relations import verse_relations
    from .reconcile import reconcile_features, check_consistency, _canon
    out, conv, errs = {}, {}, {}
    for s, v, _ in d['source']['verses']:
        k = _key(s, v)
        FF = d['features_final'][k]
        out[k] = verse_relations(d['analysis'][k], d['units'][k]['units'], FF, k,
                                 legacy_cond=d['legacy']['cond'], legacy_rel=d['legacy']['rel'], F13=d['features'][k],
                                 legacy_coord=d['legacy'].get('coord'))
        recs = out[k]['records']
        F2, _ = reconcile_features(d['features'][k], recs)
        diff = sorted(str(u) for u in set(FF) | set(F2)
                      if _canon({f: (FF.get(u) or {}).get(f, {}).get('v') if isinstance((FF.get(u) or {}).get(f), dict) else None
                                 for f in ('pos', 'tense', 'voice', 'subject')}) !=
                      _canon({f: (F2.get(u) or {}).get(f, {}).get('v') if isinstance((F2.get(u) or {}).get(f), dict) else None
                              for f in ('pos', 'tense', 'voice', 'subject')}))
        conv[k] = dict(state='CONVERGED' if not diff else 'NOT_CONVERGED', units=diff)
        errs[k] = check_consistency(FF, recs)
    return dict(records=out, revision=dict(convergence=conv, errors_final=errs))


def p_evidence_audit(ctx, d):
    from .engine import evidence_cycles
    recs = [r for v in d['records'].values() for r in v['records']]
    cyc = evidence_cycles(recs)
    return dict(evidence_audit=dict(cycles=cyc, in_cycle=sorted({x for c in cyc for x in c})))


def _sentences(LT):
    return [J for SP in LT for D in SP.A + SP.O.get('pending', []) for J in D.A + D.O.get('pending', [])]


def p_certificates(ctx, d):
    """شهادة الإغلاق لكل جملة؛ وما استوفاه دليلٌ في دورة مقدّماتٍ غير مسندة لا يُعدّ مستوفى (§٧)"""
    from .algebra import closure_certificate
    recs = [r for v in d['records'].values() for r in v['records']]
    cyc = set(d['evidence_audit']['in_cycle'])
    out = {}
    for J in _sentences(d['sentences']['LT']):
        c = closure_certificate(J, recs, upstream=ctx.options.get('upstream'))
        for o in c['obligations']:
            if o.get('discharge_relation_id') in cyc and o['status'] in ('MET', 'MET_IN_ALL_FACES'):
                o.update(status='SELECTION', residual_reason='EVIDENCE_CYCLE: دليل الاستيفاء في دورة مقدّماتٍ غير مسندة')
        out[J.id] = c
    return dict(certificates=out)


def p_paragraphs(ctx, d):
    from .algebra import paragraph_candidates, check_paragraph
    LT = d['sentences']['LT']
    recs = [r for v in d['records'].values() for r in v['records']]
    certs = list(d['certificates'].values())
    pcs = paragraph_candidates(LT, certs, recs)
    return dict(paragraphs=[dict(candidate=p, check=check_paragraph(p, LT, certs, recs)) for p in pcs])


def p_references(ctx, d):
    out = []
    for p in d['paragraphs']:
        out.append(dict(paragraph=p['candidate']['paragraph_id'], references=p['candidate']['references']))
    return dict(references=out)


# ---------- السجل التنفيذي ----------
def _stage(*a, **k):
    return EngineStage(*a, **k)


STAGES = [
    _stage('source', p_source, (), ('source',), (1,), {'source': _sch_source}, doc='استلام النص وتثبيت المصدر وبصمته',
           producers=('sarf.quran_source',), linguistic_scope='المصحف المعتمد أو نصٌّ حرّ'),
    _stage('normalization', p_normalization, ('source',), ('normalization',), (2,), {'normalization': _sch_norm},
           doc='التطبيع الموثّق مرةً واحدة', producers=('sarf.normalize_trace.normalize_traced',)),
    _stage('verse_analysis', p_verse_analysis, ('source', 'normalization'), ('analysis', 'verse_logs'), (5, 8, 11),
           {'analysis': _sch_an}, doc='التقشير والعوامل والجذر (sarf.pipeline.STAGES بلا إعادة تطبيع)',
           producers=('sarf.match', 'sarf.evidence', 'sarf.segment', 'sarf.judge', 'sarf.agreement', 'sarf.root', 'sarf.align')),
    _stage('cells', p_cells, ('analysis',), ('cells',), (3,), doc='خلايا المكتوب وترقيمها', producers=('sarf.numbering',)),
    _stage('syllables', p_syllables, ('analysis',), ('syllables',), (4,), doc='التقطيع المقطعي للمكتوب متصلاً',
           producers=('sarf.syllabify',), known_gaps=('لا مراجعة لتوافق التقطيع مع مرشّح الصرف',)),
    _stage('protection', p_protection, ('analysis',), ('protection',), (6,), doc='الحماية بالوجه كما طُبّقت قبل توليد الجذور',
           producers=('sarf.protected', 'sarf.root')),
    _stage('units', p_units, ('source', 'analysis'), ('units',), (5, 17), doc='الوحدات اللفظية وهندسة الجملة المحلية',
           producers=('sarf.algebra.sentence_geo',)),
    _stage('features', p_features, ('analysis', 'units'), ('features',), (7, 9, 10), doc='الصنف والسمات الصرفية والمدخل المعجمي',
           producers=('sarf.features.unit_features',), known_gaps=('إثبات الفعل بلا عامل غير منفّذ (B01)',
                                                                  'المدخل المعجمي ليس معنىً سياقياً')),
    _stage('linguistic', p_linguistic, ('source', 'analysis', 'units'), ('sentences', 'legacy'), (17, 19),
           doc='الجمل وحدودها (الطبقة اللغوية)', producers=('sarf.algebra.linguistic_layer', 'sarf.algebra.cross_ayah_links')),
    _stage('relations', p_relations, ('source', 'analysis', 'units', 'features', 'legacy'), ('records_initial',), (12, 13, 14, 15, 16),
           {'records_initial': _sch_records}, doc='العلاقات الأولية من مخرج المرحلة ١٣ (مدخل المصالحة وحدها)',
           producers=('sarf.relations.verse_relations',),
           known_gaps=('التوابع والمكمّلات (B03)', 'قواعد الأدوات PC.* (B05)')),
    _stage('face_reconciliation', p_face_reconciliation, ('features', 'records_initial'), ('features_final', 'reconciliation'), (9, 10),
           doc='وحدة الحقيقة بين المراحل: السمات النهائية من أوجه إطار الفعل الحيّة، ومخرج المرحلة ١٣ موسومٌ بما تجاوزه',
           producers=('sarf.reconcile.reconcile_features', 'sarf.reconcile.check_consistency')),
    _stage('relations_final', p_relations_final, ('source', 'analysis', 'units', 'features', 'features_final', 'legacy'),
           ('records', 'revision'), (12, 13, 14, 15, 16), {'records': _sch_records},
           doc='العلاقات النهائية من السمات المصالَحة، ومراجعةٌ مضبوطة واحدة بحالة الثبات؛ وهي ما تستهلكه الشهادات والفقرات والإحالات',
           producers=('sarf.relations.verse_relations', 'sarf.reconcile.reconcile_features')),
    _stage('evidence_audit', p_evidence_audit, ('records',), ('evidence_audit',), (19,), doc='كشف دورات المقدّمات',
           producers=('sarf.engine.evidence_cycles',)),
    _stage('certificates', p_certificates, ('sentences', 'records', 'evidence_audit'), ('certificates',), (19,),
           {'certificates': _sch_certs}, doc='شهادة الإغلاق لكل جملة', producers=('sarf.algebra.closure_certificate',)),
    _stage('paragraphs', p_paragraphs, ('sentences', 'records', 'certificates'), ('paragraphs',), (20,),
           doc='مرشّحات الفقرة وشهاداتها ومدقّقها', producers=('sarf.algebra.paragraph_candidates', 'sarf.algebra.check_paragraph')),
    _stage('references', p_references, ('paragraphs',), ('references',), (18,), doc='الإحالات (مرشّحةً لا معيَّنة)',
           producers=('sarf.algebra._references',), known_gaps=('تعيين المرجع (B04)',)),
    _stage('contextual_meaning', None, ('features', 'records'), ('contextual_meaning',), (18,), implemented=False,
           doc='المعنى السياقي', known_gaps=('لا قاعدة لتضييق المعنى السياقي: المدخل المعجمي ليس معنىً سياقياً',)),
    _stage('discourse_semantics', None, ('paragraphs',), ('discourse_semantics',), (20,), implemented=False,
           doc='العلاقات الدلالية بين الجمل', known_gaps=('قواعد الأدوات PC.* غير منفّذة (B05)',)),
]
ENGINE = Engine(STAGES)


def run(verses, options=None, targets=None):
    """الواجهة العامة الواحدة: من المصدر إلى الفقرة → Context"""
    return ENGINE.run(Context(verses, options), targets)


def run_ref(ref, options=None, targets=None):
    from . import quran_source
    s, vv = ref.split(':')
    a_, b_ = (vv.split('-') + [vv])[:2]
    R = {(s_, v_): t_ for s_, v_, t_ in quran_source.rows()}
    return run([(int(s), v, R[(int(s), v)]) for v in range(int(a_), int(b_) + 1)], options, targets)


# ---------- مصفوفة المراحل العشرين ----------
FUNCTIONAL = {1: 'استلام النص وتثبيت المصدر', 2: 'التطبيع الموثّق', 3: 'خلايا المكتوب وترقيمها', 4: 'التقطيع المقطعي',
              5: 'التقشير وبناء الوحدات اللفظية', 6: 'التعرّف إلى الوحدات المحمية', 7: 'تحديد صنف اللفظ',
              8: 'الجذر والوزن والتحقيق الصرفي', 9: 'السمات الصرفية', 10: 'الهوية المعجمية وأطر الاستعمال',
              11: 'العوامل وقدراتها', 12: 'البناء والإعراب', 13: 'الإسناد الفعلي ومعمولاته', 14: 'الإسناد الاسمي والنواسخ',
              15: 'العلاقات والتراكيب الممتدة', 16: 'التعلّق والنطاق', 17: 'هندسة الجملة وتصنيفها',
              18: 'الدال والمدلول والدلالة السياقية والإحالة', 19: 'اكتمال الجملة وحدّها وإغلاقها', 20: 'الروابط الخطابية وبناء الفقرة'}
# مقابلها في سجل التغطية ذي الثلاثين مرحلة (coverage/registry.jsonl: الحقل stage)
COVERAGE_MAP = {1: [1, 2], 2: [3], 3: [5], 4: [6], 5: [4, 8, 18], 6: [8], 7: [9, 13], 8: [10, 11], 9: [13, 14], 10: [12, 16, 17],
                11: [7, 15], 12: [20], 13: [21], 14: [19, 27], 15: [19, 22], 16: [23], 17: [27, 28], 18: [24, 25, 26],
                19: [28], 20: [29, 30]}


def matrix():
    """→ صفٌّ لكل مرحلةٍ وظيفية: المنتِجون الفعليون، وما يحتاجونه وما ينتجونه، والحالة التنفيذية المعلنة، والنواقص"""
    import json
    cov = {}
    p = os.path.join(H, 'coverage', 'registry.jsonl')
    if os.path.exists(p):
        for l in open(p, encoding='utf-8'):
            if l.strip():
                x = json.loads(l)
                cov.setdefault(x['stage'], []).append(x['status'])
    rows = []
    for i, name in FUNCTIONAL.items():
        st = [s for s in STAGES if i in s.functional]
        impl = [s for s in st if s.implemented]
        rows.append(dict(stage_id=i, responsibility=name,
                         module_and_entrypoint=[f'sarf.stages.{s.fn.__name__}' for s in impl],
                         engine_stages=[s.name for s in st], requires=sorted({r for s in st for r in s.requires}),
                         provides=sorted({p for s in st for p in s.provides}), producers=sorted({p for s in impl for p in s.producers}),
                         consumers=sorted({c.name for c in STAGES for s in st if set(c.requires) & set(s.provides)}),
                         implementation_status=('EXECUTED_BY_PRODUCER' if impl and len(impl) == len(st) else
                                                'PARTIAL' if impl else 'NOT_IMPLEMENTED'),
                         linguistic_scope='; '.join(s.linguistic_scope for s in st if s.linguistic_scope) or None,
                         known_gaps=sorted({g for s in st for g in s.known_gaps}),
                         coverage_stages=COVERAGE_MAP.get(i, []),
                         coverage_status={c: dict(__import__('collections').Counter(cov.get(c, []))) for c in COVERAGE_MAP.get(i, [])}))
    return rows


def verify_certificates(ctx):
    """فاحصٌ مستقل للشهادات في السياق: يعيد إنتاج كل شهادةٍ من مقدّماتها (الجمل والسجلات) ويقارن بصمتها بالمحفوظة → قائمة أخطاء"""
    from .algebra import closure_certificate
    from .engine import fingerprint
    recs = [r for v in ctx.get('records').values() for r in v['records']]
    cyc = set(ctx.get('evidence_audit')['in_cycle'])
    err = []
    for J in _sentences(ctx.get('sentences')['LT']):
        c = closure_certificate(J, recs, upstream=ctx.options.get('upstream'))
        for o in c['obligations']:
            if o.get('discharge_relation_id') in cyc and o['status'] in ('MET', 'MET_IN_ALL_FACES'):
                o.update(status='SELECTION', residual_reason='EVIDENCE_CYCLE: دليل الاستيفاء في دورة مقدّماتٍ غير مسندة')
        have = ctx.get('certificates').get(J.id)
        if have is None or fingerprint(have) != fingerprint(c):
            err.append(f'{J.id}: الشهادة المحفوظة لا تطابق المعاد إنتاجها من مقدّماتها')
    return err
