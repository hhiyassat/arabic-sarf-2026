"""tests/test_engine.py — المحرّك الواحد (SARF_DEPENDENCY_PIPELINE_AND_COMPLETION_05 §١١): اختبارات المرحلة، والانتقال، والمراجعة الراجعة،
ومن المصدر إلى الفقرة عبر الواجهة العامة وحدها (بلا أدوات التقرير)."""
import copy, os, re, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from sarf.engine import Engine, EngineStage, Context, evidence_cycles, fingerprint, EXECUTED, FAILED, BLOCKED, SEARCH_LIMIT, NOT_IMPLEMENTED
from sarf.stages import run, run_ref, ENGINE, STAGES, matrix, FUNCTIONAL
from sarf import quran_source
FAIL = []


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {str(got)[:400]}'))
    if not cond:
        FAIL.append(name)


R = {(a, b): t for a, b, t in quran_source.rows()}
ctx = run_ref('112:1-4')
st = {n: ctx.status[n][0] for n in ENGINE.order}
check('E01 من المصدر إلى الفقرة عبر الواجهة العامة: كل المراحل المنفّذة EXECUTED، وغير المنفّذة NOT_IMPLEMENTED بنقصها المسمّى (لا DEFERRED لغوية تخفيها)',
      all(v == EXECUTED for n, v in st.items() if ENGINE.stages[n].implemented) and
      all(v == NOT_IMPLEMENTED and ctx.status[n][1] for n, v in st.items() if not ENGINE.stages[n].implemented), st)
order = ENGINE.order
check('E02 الجدولة بالاعتماد لا بالرقم: الوحدات (هندسة الجملة، ١٧) تسبق السمات (٩) لأن السمات تستهلكها؛ والتطبيع يسبق التحليل',
      order.index('units') < order.index('features') and order.index('normalization') < order.index('verse_analysis'), order)
k = '112:1'
an, nz = ctx.get('analysis')[k], ctx.get('normalization')[k]
n_norm = sum(1 for t in ctx.trace if t['stage'] == 'normalization')
check('E03 التطبيع مرةً واحدة يحمله السياق: التحليل يستهلك نصّه التحليلي نفسه، ولا يُعاد التطبيع في التحليل',
      an['normalized'] == nz['analysis'] and n_norm == 1 and ctx.get('verse_logs')[k]['logs'][0][0] == 'normalize'
      and 'من خانة التطبيع' in ctx.get('verse_logs')[k]['logs'][0][1], (n_norm, ctx.get('verse_logs')[k]['logs'][0]))
check('E04 اختبار انتقال: الشهادات أُنتجت من خانة العلاقات بهويتها (بصمة المقدّمة المسجَّلة = بصمة الخانة)',
      ctx.slots['certificates'].deps['records'] == ctx.slots['records'].fp and ctx.slots['paragraphs'].deps['certificates'] == ctx.slots['certificates'].fp)
rows = matrix()
check('E05 مصفوفة المراحل العشرين: لكل مرحلةٍ مسؤوليتها ومنتِجوها الفعليون ومستهلكوها وحالتها؛ وما لا منتِج له معلنٌ بحالته ونقصه، ومقابلها في سجل التغطية',
      len(rows) == 20 and all(r['implementation_status'] in ('EXECUTED_BY_PRODUCER', 'PARTIAL', 'NOT_IMPLEMENTED') for r in rows) and
      all(r['coverage_stages'] for r in rows) and any(r['implementation_status'] == 'PARTIAL' for r in rows), [(r['stage_id'], r['implementation_status']) for r in rows])

# ---------- المراجعة الراجعة ----------
c2 = run_ref('2:282')
recs = copy.deepcopy(c2.get('records'))
k2 = '2:282'
subj = next(r for r in recs[k2]['records'] if r['type'] == 'SUBJECT' and r['status'] == 'LICENSED')
cert_before = next(c for c in c2.get('certificates').values() if any(o.get('discharge_relation_id') == subj['relation_id'] for o in c['obligations']))
ob_before = next(o for o in cert_before['obligations'] if o.get('discharge_relation_id') == subj['relation_id'])
n_trace = len(c2.trace)
recs[k2]['records'] = [r for r in recs[k2]['records'] if r['relation_id'] != subj['relation_id']]
ENGINE.revise(c2, 'records', recs, f"دليلٌ لاحق ينقض {subj['relation_id']}")
re_run = [t['stage'] for t in c2.trace[n_trace:]]
ob_after = next(o for o in c2.get('certificates')[cert_before['sentence']]['obligations'] if o['obligation_id'] == ob_before['obligation_id'])
check('E06 مراجعة راجعة: نقض علاقة فاعلٍ يعيد حساب المستهلكين وحدهم (التدقيق، الشهادات، الفقرة، الإحالات) ولا يعيد التطبيع ولا التحليل؛ '
      'والالتزام لم يعد مستوفى بها؛ والقيمة السابقة محفوظةٌ بسببها',
      # FA02 §٢: المصالحة تقرأ العلاقات الأولية (records_initial)، والسجلات النهائية (records) ناتج relations_final من السمات المصالَحة؛
      # فمراجعة السجلات النهائية تعيد مستهلكيها وحدهم، ولا تعيد المصالحة (لا دورة)
      set(re_run) == {'evidence_audit', 'certificates', 'paragraphs', 'references', 'contextual_meaning', 'discourse_semantics'} and
      'normalization' not in re_run and 'verse_analysis' not in re_run and
      all(c2.status[n_][0] == NOT_IMPLEMENTED for n_ in ('contextual_meaning', 'discourse_semantics')) and
      ob_after.get('discharge_relation_id') != subj['relation_id'] and c2.slots['records'].history and
      c2.revisions[-1]['recomputed'][:4] == ['evidence_audit', 'certificates', 'paragraphs', 'references'], (re_run, ob_after['status']))
recs2 = copy.deepcopy(c2.get('records'))
before_v = {k_: c['verdict_by_level'] for k_, c in c2.get('certificates').items()}
recs2[k2]['records'] = list(reversed(recs2[k2]['records']))
ENGINE.revise(c2, 'records', recs2, 'إعادة ترتيب المرشّحين')
after_v = {k_: c['verdict_by_level'] for k_, c in c2.get('certificates').items()}
check('E07 تغيير ترتيب المرشّحين (السجلات) لا يغيّر الحكم', before_v == after_v)

# ---------- دورة الأدلة ----------
cyc_recs = [dict(relation_id='A', premises=['B']), dict(relation_id='B', premises=['A']), dict(relation_id='C', premises=['A'])]
check('E08 دورة أدلّةٍ غير مسندة تُكشف (A ← B ← A)، والسلسلة المسندة (C ← A) ليست دورة', evidence_cycles(cyc_recs) == [['A', 'B', 'A']], evidence_cycles(cyc_recs))
c3 = run_ref('2:282')
recs3 = copy.deepcopy(c3.get('records'))
lic = [r for r in recs3['2:282']['records'] if r['status'] == 'LICENSED' and r['type'] in ('SUBJECT', 'OBJECT', 'PP')]
target = next(c for c in c3.get('certificates').values() if any(o.get('discharge_relation_id') == lic[0]['relation_id'] for o in c['obligations'])) if lic else None
if lic and target:
    rid = lic[0]['relation_id']
    for vk in recs3:
        for r in recs3[vk]['records']:
            if r['relation_id'] == rid:
                r['premises'] = list(r['premises']) + [lic[1]['relation_id']]
            if r['relation_id'] == lic[1]['relation_id']:
                r['premises'] = list(r['premises']) + [rid]
    ENGINE.revise(c3, 'records', recs3, 'إدخال دورة مقدّمات اختبارية')
    o_ = next(o for o in c3.get('certificates')[target['sentence']]['obligations'] if o.get('discharge_relation_id') == rid)
    check('E09 ما استوفاه دليلٌ في دورة مقدّماتٍ غير مسندة لا يُعدّ مستوفى في الشهادة (EVIDENCE_CYCLE)',
          rid in c3.get('evidence_audit')['in_cycle'] and o_['status'] == 'SELECTION' and 'EVIDENCE_CYCLE' in o_['residual_reason'], o_)
else:
    check('E09 دورة المقدّمات في الشهادة', False, 'لا علاقة مرخَّصة في 112')

# ---------- عقود المحرّك ----------
def _ok(ctx_, d):
    return dict(x=1)


bad = Engine([EngineStage('a', _ok, (), ('x',), (1,)), EngineStage('b', lambda c, d: {}, ('x',), ('y',), (2,)),
              EngineStage('c', lambda c, d: dict(z=1), ('y',), ('z',), (3,))])
cb = bad.run(Context([]))
check('E10 مرحلةٌ تعلن مخرجاً ولا تنتجه: FAILED بسببه، ومستهلكها BLOCKED_DEPENDENCY (لا يُخفى ولا يمرّ)',
      cb.status['b'][0] == FAILED and 'لم تُنتَج' in cb.status['b'][1] and cb.status['c'][0] == BLOCKED, cb.status)
ver = Engine([EngineStage('a', _ok, (), ('x',), (1,), version='1'), EngineStage('b', lambda c, d: dict(y=1), ('x@2',), ('y',), (2,))])
cv = ver.run(Context([]))
check('E11 اعتمادٌ من إصدارٍ مخالف: BLOCKED_DEPENDENCY بسببه', cv.status['b'][0] == BLOCKED and 'إصدار' in cv.status['b'][1], cv.status)
sch = Engine([EngineStage('a', lambda c, d: dict(x='نص'), (), ('x',), (1,), schema={'x': lambda v: None if isinstance(v, dict) else 'ليس قاموساً'})])
cs = sch.run(Context([]))
check('E12 وجود الحقل لا يثبت صلاحيته: مخرجٌ يخالف مخطّطه FAILED', cs.status['a'][0] == FAILED and 'المخطّط' in cs.status['a'][1], cs.status)


def _boom(c, d):
    raise RuntimeError('عطلٌ مصطنع')


fl = Engine([EngineStage('a', _boom, (), ('x',), (1,)), EngineStage('b', lambda c, d: dict(y=1), ('x',), ('y',), (2,))])
cf = fl.run(Context([]))
check('E13 فشل مرحلة يُسجَّل بسببه، ومستهلكها محجوب', cf.status['a'][0] == FAILED and cf.status['b'][0] == BLOCKED, cf.status)
try:
    Engine([EngineStage('a', _ok, ('y',), ('x',), (1,)), EngineStage('b', _ok, ('x',), ('y',), (2,))])
    cyc_ok = False
except ValueError as e:
    cyc_ok = 'دورة' in str(e)
check('E14 دورة اعتمادٍ بين المراحل خطأٌ معماري يُرفع عند التسجيل', cyc_ok)
lim = Engine([EngineStage('a', _ok, (), ('x',), (1,)), EngineStage('b', lambda c, d: dict(y=1), ('x',), ('y',), (2,)),
              EngineStage('c', lambda c, d: dict(z=1), ('y',), ('z',), (3,))], max_revision_steps=1)
cl = lim.run(Context([]))
lim.revise(cl, 'x', 2, 'اختبار الحدّ')
check('E15 بلوغ حدّ المراجعة التقني تأجيلٌ مسمّى (DEFERRED_SEARCH_LIMIT) لا إغلاق: c لم تُعَد وحالتها معلنة',
      cl.status['b'][0] == EXECUTED and cl.status['c'][0] == SEARCH_LIMIT and cl.slots['z'].stale, cl.status)
# ---------- مصدرٌ مبتور ----------
pre = ' '.join(R[(112, 4)].split()[:3])
cp = run([(112, 1, R[(112, 1)]), (112, 2, R[(112, 2)]), (112, 3, R[(112, 3)]), (112, 4, pre)])
pb = cp.get('paragraphs')[-1]['candidate']['boundary']
check('E16 بتر آخر آيةٍ قبل كلمتها الأخيرة عبر الواجهة العامة: لا حدّ مصدرٍ «آخر السورة» ولا حدّ لغوي', pb['source_end'] is None and pb['linguistic'] == 'NOT_PROVEN', pb)
# ---------- تزوير شهادةٍ وتحديث بصمتها ----------
from sarf.stages import verify_certificates
c4 = run_ref('112:1-4')
certs = copy.deepcopy(c4.get('certificates'))
kk = sorted(certs)[0]
certs[kk]['verdict_by_level']['LOCAL_PREDICATION'] = 'CLOSED_IN_FACE'
ENGINE.revise(c4, 'certificates', certs, 'تزويرٌ اختباري')
check('E17 تزوير شهادةٍ مع تحديث بصمة الخانة: المراجعة تعيد إنتاجها من مقدّماتها فتُكشف (verify_certificates)',
      any(kk in e for e in verify_certificates(c4)), verify_certificates(c4))
# ---------- كل حكمٍ في الصفحة يشير إلى سجلٍّ في المحرّك ----------
out1 = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'p05_e18_a.html')
out2 = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'p05_e18_b.html')
env = dict(os.environ)
r1 = subprocess.run([sys.executable, '-s', 'tools/pipeline_trace.py', '112:1-4', '-o', out1, '--quiet', '--words', '3'], env=env, capture_output=True, text=True)
r2 = subprocess.run([sys.executable, '-s', 'tools/pipeline_trace.py', '112:1-4', '-o', out2, '--quiet', '--words', '40'], env=env, capture_output=True, text=True)
strip = lambda t: re.sub(r'<section id="s0".*?</section>', '', re.sub(r'(هوية التشغيل|وقت البدء)[^<]*', '', t), flags=re.S)
h1, h2 = open(out1, encoding='utf-8').read(), open(out2, encoding='utf-8').read()
# ما يختلف بين التشغيلين هويةٌ لا تحليل: الأمر المعروض، ووقت البدء، وهوية التشغيل وبصمة الصفحة
_norm = lambda t: re.sub(r'tools/pipeline_trace\.py[^<]*|\d{4}-\d\d-\d\dT[\d:+]+|[0-9a-f]{12,16}|\b[0-9a-f]{4}</code', '', t)
check('E18 تغيير شكل العرض (عدد سطور الطرفية) لا يغيّر التحليل ولا أدلّته في الصفحة', r1.returncode == 0 and r2.returncode == 0 and
      _norm(h1) == _norm(h2), r1.stderr[-300:])
# معرّف الدليل (…#subject، …#premises، …#single) يشير إلى علاقته: يُفحص وجود العلاقة نفسها
rel_ids = {x.rstrip(':').split('#')[0] for x in re.findall(r'\b112:\d+:[A-Z_]+:[A-Z0-9.]+:[^\s<()،؛]+', h1)}
eng_ids = {r['relation_id'] for v in c4.get('records').values() for r in v['records']}
sent_ids = set(re.findall(r'L112\.d\d+\.J', h1))
check('E19 كل معرّف علاقةٍ وجملةٍ معروضٍ في الصفحة سجلٌّ موجود في ناتج المحرّك', rel_ids and rel_ids <= eng_ids and sent_ids <= set(c4.get('certificates')),
      (sorted(rel_ids - eng_ids)[:5], sorted(sent_ids - set(c4.get('certificates')))))
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
