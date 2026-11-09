"""stage_matrix.py <جذر الشيفرة> <OUT.json> [--md OUT.md] [--ref 2:282]
مصفوفة المراحل (SARF_COMPLETION_FROM_REPORT_063 §١١): لكل قسمٍ من صفحة المسار ومرحلته في المحرّك:
EXECUTED (من حالة المحرّك C.status) منفصلةً عن COMPLETE_IN_DECLARED_SCOPE (من المتبقّي في المخرج نفسه: لا متبقّي = YES).
المتبقّي يُعدّ من المخرج بتعريفٍ مكتوب هنا لكل مرحلة، لا يُقدَّر."""
import json, os, sys, collections

ROOT = os.path.abspath(sys.argv[1])
OUT = sys.argv[2]
REF = sys.argv[sys.argv.index('--ref') + 1] if '--ref' in sys.argv else '2:282'
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from sarf.stages import run_ref                      # noqa: E402

C = run_ref(REF)
st = C.status
A = C.get('analysis')[REF]
F = C.get('features')[REF]
U = C.get('units')[REF]['units']
V = C.get('records')[REF]
certs = C.get('certificates')
paras = C.get('paragraphs')
rec_c = collections.Counter((r['type'], r['status']) for r in V['records'])
ops = collections.Counter(str(o.get('status')) for o in A.get('operators', []))
feat_unproven = sum(1 for k, f in F.items() for n, x in f.items() if isinstance(x, dict) and 'st' in x and x['st'] != 'مثبت')
feat_total = sum(1 for k, f in F.items() for n, x in f.items() if isinstance(x, dict) and 'st' in x)
morph = [m for m in A.get('morph', []) if isinstance(m, dict)] if isinstance(A.get('morph'), list) else []
ung = collections.Counter((a.get('inflection') or {}).get('ungoverned_kind') for a in V['axes'].values()
                          if (a.get('inflection') or {}).get('agreement') == 'UNGOVERNED')
recon = (C.get('reconciliation') or {}).get('errors', {}).get(REF, []) if 'face_reconciliation' in st else None
non_closed = [c for c in certs.values() if not str(c.get('verdict')).startswith('CLOSED')]
pnp = [p for p in paras if (p['candidate'].get('boundary') or {}).get('linguistic') != 'PROVEN']
rel_def = sum(n for (t, s), n in rec_c.items() if s != 'LICENSED')
rel_tot = sum(rec_c.values())
refs = C.get('references') if 'references' in st else None


def row(sec, title, stage, scope, residual, residual_def, blocker=None):
    ex = st.get(stage, ('ABSENT', ''))[0]
    complete = 'YES' if ex == 'EXECUTED' and residual == 0 else ('NO' if ex == 'EXECUTED' else 'N/A')
    return dict(section=sec, title=title, engine_stage=stage, EXECUTED=ex == 'EXECUTED', engine_status=list(st.get(stage, ('ABSENT', ''))),
                declared_scope=scope, residual=residual, residual_definition=residual_def, COMPLETE_IN_DECLARED_SCOPE=complete,
                blocker=blocker)


R = [
    row('1', 'المدخل', 'source', 'نصّ الآية من مصحف المجمّع بهويته', 0, 'لا متبقّي معرَّف'),
    row('2', 'التطبيع', 'normalization', 'التطبيع المسمّى (العلامات العثمانية، الوقف) بأثره', 0, 'لا متبقّي معرَّف'),
    row('3', 'الترقيم: خلايا المكتوب', 'cells', 'خلايا الحرف والحركة', 0, 'لا متبقّي معرَّف'),
    row('4', 'التقطيع المقطعي', 'syllables', 'مقاطع التحقيق في الدرج', 0, 'لا متبقّي معرَّف'),
    row('5', 'مطابقة العوامل ونفيها بالكتابة', 'verse_analysis', 'العوامل المائة في الجرد', ops.get('deferred', 0) + ops.get('None', 0),
        'عوامل حالتها مؤجَّلة أو بلا حالة'),
    row('6', 'التقشير', 'verse_analysis', 'السوابق واللواحق والجذع', 0, 'لا متبقّي معرَّف'),
    row('7', 'الحكم على العوامل', 'verse_analysis', 'قبول العامل أو منعه بالكتابة', ops.get('deferred', 0), 'عوامل مؤجَّلة الحكم'),
    row('8', 'الإسناد: سمات الصيغة', 'features', 'الزمن والبناء والضمير', feat_unproven, f'سماتٌ غير مثبتة من {feat_total}'),
    row('9', 'الجذر والوزن', 'units', 'الجذر والوزن للأفعال والأسماء المشتقة في HFN',
        sum(1 for G in U.values() if not G.closed and ('الجذر' in (G.O.get('deferred') or '') or 'HFN' in (G.O.get('deferred') or ''))),
        'وحدات معلّقة بسبب الجذر/الوزن', 'HFN لا يغطّي الجامد وجموع التكسير'),
    row('10', 'مقاطع الوحدات وأرقامها', 'syllables', 'مقاطع كل وحدة', 0, 'لا متبقّي معرَّف'),
    row('11', 'ربط العامل بمعموله', 'linguistic', 'معمولٌ واحد مباشر في الآية', 0, 'لا متبقّي معرَّف في النطاق المعلن'),
    row('12', 'الوحدات اللفظية وإغلاقها', 'units', 'إغلاق الوحدة بدليلٍ مكتوب', sum(1 for G in U.values() if not G.closed),
        f'وحداتٌ معلّقة من {len(U)}', 'مسار الجامد والظرف وأفعل التفضيل؛ مدخلات HFN'),
    row('13', 'السمات الصرفية', 'features', 'السمات بقيمها وأدلتها', feat_unproven, 'سماتٌ مرشّحة أو مؤجَّلة'),
    row('13+', 'وحدة الحقيقة بين المراحل', 'face_reconciliation', 'السمات النهائية من أوجه إطار الفعل الحيّة', len(recon or []),
        'تناقضات LIVE_VALUE_FROM_EXCLUDED_FACE / MIXED_FACES'),
    row('14', 'الجملة', 'certificates', 'شهادة إغلاق الجملة بمستوياتها', len(non_closed), f'جملٌ غير مغلقة من {len(certs)}',
        'حدود الجمل من الطبقة القديمة (linguistic_layer)؛ حدّ الآية غير مفحوص لفظاً'),
    row('14أ', 'العلاقات المحلية بأدلتها', 'relations', 'العلاقات المحلية بقواعدها المنفّذة', rel_def, f'علاقاتٌ غير مرخَّصة من {rel_tot}',
        'جرد أطر التعلّق؛ تعدّي HFN غير مقرّ (is_fact=False)'),
    row('14ب', 'محاور الصنف المستقلة', 'relations', 'البناء والإعراب والدور والعلامة',
        sum(n for k, n in ung.items() if k != 'NO_MAHALL'), 'UNGOVERNED بغير NO_MAHALL (الدور مؤجَّل أو قاعدته غير منفّذة)'),
    row('14ج', 'سمات المصادر الحديثة (مرشّحة)', 'evidence_audit', 'مرشّحات من مصادر مثبَّتة، لا مدخلات', 0, 'مرشّحة بطبيعتها؛ لا تدخل التحليل'),
    row('15', 'الوحدة الخطابية', 'paragraphs', 'الوحدة الخطابية من الجمل', len(pnp), 'حدودٌ غير مثبتة', 'قاعدة بدء الخطاب غير منفّذة'),
    row('16', 'الفقرة', 'paragraphs', 'مرشّح الفقرة بعقد PC-04 (مقترح)', len(pnp), 'فقراتٌ حدّها PB-L1 غير مثبت',
        'اعتماد PC-04 لصاحب النظرية؛ قاعدة بدء الخطاب'),
    row('—', 'المراجع', 'references', 'مرشّحات المرجع داخل الفقرة (لا تعيين)', 0 if refs is None else
        sum(1 for p in refs for x in p.get('references') or [] if x.get('status') != 'LICENSED'),
        'إحالاتٌ غير معيَّنة', 'تعيين المرجع غير منفّذ (REFERENCE_RESOLUTION)'),
    row('—', 'المعنى السياقي', 'contextual_meaning', '—', 1, 'المرحلة غير منفّذة', st.get('contextual_meaning', ('', ''))[1]),
    row('—', 'دلالة الخطاب', 'discourse_semantics', '—', 1, 'المرحلة غير منفّذة', st.get('discourse_semantics', ('', ''))[1]),
]
summ = dict(ref=REF, root=ROOT, head=os.popen(f'git -C "{ROOT}" rev-parse HEAD').read().strip(), rows=len(R),
            executed=sum(1 for r in R if r['EXECUTED']), complete=sum(1 for r in R if r['COMPLETE_IN_DECLARED_SCOPE'] == 'YES'),
            not_implemented=[r['engine_stage'] for r in R if r['engine_status'][0] == 'NOT_IMPLEMENTED'])
json.dump(dict(summary=summ, matrix=R), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if '--md' in sys.argv:
    with open(sys.argv[sys.argv.index('--md') + 1], 'w', encoding='utf-8') as f:
        f.write(f'# مصفوفة المراحل — {REF} عند `{summ["head"][:10]}`\n\nمنفّذة {summ["executed"]} من {summ["rows"]}، ومكتملة في نطاقها المعلن '
                f'{summ["complete"]}. «منفّذة» حالة المحرّك؛ و«مكتملة» لا متبقّي في المخرج بالتعريف المذكور.\n\n'
                '| القسم | المرحلة | المحرّك | EXECUTED | COMPLETE_IN_DECLARED_SCOPE | المتبقّي | تعريفه | النطاق المعلن | العائق |\n'
                '|---|---|---|---|---|---|---|---|---|\n')
        for r in R:
            f.write('| ' + ' | '.join(str(x).replace('|', '¦') for x in (r['section'], r['title'], r['engine_stage'], 'نعم' if r['EXECUTED'] else 'لا',
                                                                      r['COMPLETE_IN_DECLARED_SCOPE'], r['residual'], r['residual_definition'],
                                                                      r['declared_scope'], r['blocker'] or '—')) + ' |\n')
print(json.dumps(summ, ensure_ascii=False))
