"""stage_matrix20.py <جذر الشيفرة> <OUT.json> [--md OUT.md] [--ref 2:282] [--measures M.json]
مصفوفة المراحل العشرين (SARF_FINAL_COMPLETION_AND_ACCEPTANCE_01 §٤): لكل مرحلةٍ من العشرين المتفق عليها:
- التنفيذ: مراحل المحرّك التي تعلن تغطيتها (EngineStage.functional)، ومنتِجوها (الملف والدالة)، ومدخلها ومخرجها، ومستهلكوها الفعليون
  (مراحل تطلب مخرجها)، وحالتها في التشغيل (C.status)؛
- تغطية القواعد: ASSESSED بمتبقٍّ معدودٍ من المخرج بتعريفٍ مكتوب هنا، أو NOT_ASSESSED حين لا فاحص اكتمالٍ لها — لا يُعدّ غياب
  التعريف غيابَ النقص؛
- صحة النتائج: MEASURED بمقياسٍ مستقل (من --measures) أو NOT_MEASURED؛
- اكتمال الوقوع في المرجع (2:282): عدد ما بقي مفتوحاً، أو NOT_ASSESSED؛
- الاختبارات: ملفات tests/ التي تستورد وحدة منتِجٍ للمرحلة أو تستدعي دالته أو تشغّلها — ربطٌ خشن حيث تخدم الوحدة مراحل عدّة
  (المراحل 12–16 كلها من relations، فاختباراتها مشتركة)، لا شهادةٌ بأن كل قاعدةٍ مختبَرة."""
import collections, json, os, re, sys

ROOT = os.path.abspath(sys.argv[1])
OUT = sys.argv[2]
REF = sys.argv[sys.argv.index('--ref') + 1] if '--ref' in sys.argv else '2:282'
MEAS = json.load(open(sys.argv[sys.argv.index('--measures') + 1], encoding='utf-8')) if '--measures' in sys.argv else {}
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from sarf.stages import STAGES, run_ref                       # noqa: E402

TWENTY = {1: 'استلام النص وتثبيت المصدر', 2: 'التطبيع الموثّق', 3: 'خلايا المكتوب وترقيمها', 4: 'التقطيع المقطعي',
          5: 'التقشير وبناء الوحدات', 6: 'الحماية', 7: 'صنف اللفظ', 8: 'الجذر والوزن والتحقيق الصرفي', 9: 'السمات الصرفية',
          10: 'الهوية المعجمية وأطر الاستعمال', 11: 'العوامل وقدراتها', 12: 'البناء والإعراب', 13: 'الإسناد الفعلي ومعمولاته',
          14: 'الإسناد الاسمي والنواسخ', 15: 'العلاقات والتراكيب الممتدة', 16: 'التعلّق والنطاق', 17: 'هندسة الجملة وتصنيفها',
          18: 'الدلالة السياقية وتعيين المرجع', 19: 'اكتمال الجملة وحدّها وإغلاقها', 20: 'الخطاب والفقرة'}
C = run_ref(REF)
st = C.status
need = collections.defaultdict(list)
for s in STAGES:
    for r in s.requires:
        need[r].append(s.name)
tests = {f: open(os.path.join('tests', f), encoding='utf-8').read() for f in sorted(os.listdir('tests')) if f.endswith('.py')}


def tests_for(s):
    """الاختبارات التي تستورد وحدة منتِجٍ للمرحلة باسمها الكامل (sarf.x أو from sarf import x أو from sarf.x import)، أو تستدعي دالته
    باسمها (ستة أحرفٍ فأكثر)، أو تشغّل المرحلة باسمها في المحرّك"""
    pats = []
    for p in s.producers:
        mod = p if p.count('.') == 1 else p.rsplit('.', 1)[0]
        base = mod.split('.')[-1]
        pats += [re.escape(mod) + r'\b', r'from sarf import [^\n]*\b' + re.escape(base) + r'\b']
        if p.count('.') >= 2 and len(p.rsplit('.', 1)[1]) >= 6:
            pats.append(r'\b' + re.escape(p.rsplit('.', 1)[1]) + r'\(')
    pats.append(r"'" + re.escape(s.name) + r"'")
    return sorted(f for f, t in tests.items() if any(re.search(x, t) for x in pats))


A = C.get('analysis')[REF]
F = C.get('features')[REF]
FF = C.get('features_final')[REF]
U = C.get('units')[REF]['units']
V = C.get('records')[REF]
recs = V['records']
ax = V['axes']
cert = C.get('certificates')
par = C.get('paragraphs')
ung = collections.Counter((a.get('inflection') or {}).get('ungoverned_kind') for a in ax.values()
                          if (a.get('inflection') or {}).get('agreement') == 'UNGOVERNED')
rs = lambda typ: [r for r in recs if r['type'] in typ]
nonlic = lambda typ: sum(1 for r in rs(typ) if r['status'] != 'LICENSED')
frames = rs(('VERB_FRAME',))
objreq = collections.Counter((r['frame'].get('object_requirement') or {}).get('kind') for r in frames)
# أبواب المرحلة ١٥ المطلوبة، وما يولّده المحلّل منها (من الشيفرة: _rec(ref, 'TYPE'…) في sarf/relations.py، ومن المخرج)
REQ15 = ('IDAFA', 'COORD', 'SILAH', 'MASDAR', 'CONDITION', 'VOCATIVE', 'TAWABI', 'HAL', 'TAMYIZ', 'ISTITHNA')
CODE_TYPES = set(re.findall(r"_rec\(ref, '([A-Z_]+)'", open(os.path.join(ROOT, 'sarf', 'relations.py'), encoding='utf-8').read()))
OUT_TYPES = {r['type'] for r in recs}
MISSING15 = [t for t in REQ15 if t not in CODE_TYPES and t not in OUT_TYPES]
F13_RES = sum(1 for k, f in F.items() for n, x in f.items() if isinstance(x, dict) and 'st' in x and x['st'] not in ('مثبت',))
RES = {  # تغطية القواعد: (المتبقّي، تعريفه) أو None = NOT_ASSESSED
    5: (sum(1 for G in U.values() if not G.closed and 'لم تثبت الاسمية' in (G.O.get('deferred') or '')),
        'وحداتٌ صنفها غير ثابت بالكتابة (مسار الجامد/الظرف)'),
    7: (sum(1 for k, f in F.items() if (f.get('pos') or {}).get('st') != 'مثبت'), 'وحداتٌ صنفها غير مثبت في السمات'),
    8: (sum(1 for G in U.values() if not G.closed and re.search('الجذر|HFN|عامل\\+أل', G.O.get('deferred') or '')),
        'وحداتٌ معلّقة بسبب الجذر/الوزن'),
    9: (sum(1 for k, f in FF.items() for n, x in f.items() if isinstance(x, dict) and 'st' in x and x['st'] not in ('مثبت',)),
        'سماتٌ غير مثبتة في السمات النهائية (features_final، بعد المصالحة)؛ وعدّ سمات المرحلة ١٣ (features) في stage9_features13'),
    11: (sum(1 for o in A.get('operators', []) if o.get('status') == 'deferred'), 'عوامل مؤجَّلة الحكم'),
    12: (ung.get('ROLE_RULE_NOT_IMPLEMENTED', 0), 'وحداتٌ بلا عامل لأن قاعدة دورها غير منفّذة (نقص تنفيذ)'),
    13: (nonlic(('SUBJECT', 'OBJECT')) + sum(n for k, n in objreq.items() if k in ('UNLINKED_CANDIDATE', 'UNANALYZED_COMPLEMENT', 'NOT_FOUND_IN_SCOPE')),
         'فاعلٌ/مفعولٌ غير مرخَّص، ومتطلَّب مفعولٍ غير مربوط أو غير محلَّل'),
    14: (nonlic(('PREDICATION', 'PREDICATIVE_PP', 'NASIKH')) + objreq.get('KHABAR_CANDIDATE', 0), 'إسنادٌ اسمي/ناسخ غير مرخَّص'),
    15: (nonlic(REQ15) + len(MISSING15),
         'علاقاتٌ ممتدة غير مرخَّصة، وأبوابٌ مطلوبة لا يولّد لها المحلّل نوع علاقة (MISSING_CHAPTERS: ' + ('، '.join(MISSING15) or '—') + ')'),
    16: (nonlic(('ATTACH',)), 'تعلّقٌ غير مرخَّص'),
    19: (sum(1 for c in cert.values() if not str(c.get('verdict')).startswith('CLOSED')), 'جملٌ غير مغلقة'),
    20: (sum(1 for p in par if (p['candidate'].get('boundary') or {}).get('linguistic') != 'PROVEN'), 'فقراتٌ حدّها غير مثبت'),
    18: (sum(1 for p in (C.get('references') or []) for x in p.get('references') or [] if x.get('status') != 'LICENSED'),
         'إحالاتٌ غير معيَّنة'),
}
rows = []
for n, title in TWENTY.items():
    es = [s for s in STAGES if n in s.functional]
    stat = {s.name: st.get(s.name, ('ABSENT', ''))[0] for s in es}
    executed = bool(es) and all(v == 'EXECUTED' for v in stat.values())
    not_impl = [k for k, v in stat.items() if v == 'NOT_IMPLEMENTED']
    cov = RES.get(n)
    meas = MEAS.get(str(n))
    rows.append(dict(
        stage=n, title=title, engine_stages=[s.name for s in es], engine_status=stat,
        producers=sorted({p for s in es for p in s.producers}), requires=sorted({r for s in es for r in s.requires}),
        provides=sorted({p for s in es for p in s.provides}),
        consumers=sorted({c for s in es for p in s.provides for c in need.get(p, []) if c not in [x.name for x in es]}),
        tests=sorted({t for s in es for t in tests_for(s)}),
        known_gaps=sorted({g for s in es for g in s.known_gaps}),
        EXECUTION='EXECUTED' if executed else ('NOT_IMPLEMENTED' if not_impl else 'PARTIAL' if es else 'NO_ENGINE_STAGE'),
        RULE_COVERAGE=('NOT_ASSESSED' if cov is None else 'ASSESSED'), residual=None if cov is None else cov[0],
        residual_definition=None if cov is None else cov[1],
        CORRECTNESS=('MEASURED' if meas else 'NOT_MEASURED'), correctness=meas,
        OCCURRENCE_COMPLETE_IN_REF=('NOT_ASSESSED' if cov is None else 'YES' if cov[0] == 0 else 'NO'),
        NOT_IMPLEMENTED_PARTS=not_impl,
        **({'required_chapters': list(REQ15), 'generated_types_in_code': sorted(CODE_TYPES & set(REQ15)), 'missing_chapters': MISSING15}
           if n == 15 else {}),
        **({'stage9_features13': dict(slot='features', residual=F13_RES, definition='سماتٌ غير مثبتة في مخرج المرحلة ١٣ قبل المصالحة'),
            'stage9_features_final': dict(slot='features_final', residual=cov[0], definition='سماتٌ غير مثبتة بعد المصالحة')} if n == 9 else {})))
summ = dict(ref=REF, root=ROOT, stages=20, executed=sum(r['EXECUTION'] == 'EXECUTED' for r in rows),
            not_implemented=[r['stage'] for r in rows if r['EXECUTION'] == 'NOT_IMPLEMENTED' or r['NOT_IMPLEMENTED_PARTS']],
            coverage_not_assessed=[r['stage'] for r in rows if r['RULE_COVERAGE'] == 'NOT_ASSESSED'],
            residual_nonzero=[r['stage'] for r in rows if r['residual']],
            missing_chapters_15=MISSING15,
            correctness_measured=[r['stage'] for r in rows if r['CORRECTNESS'] == 'MEASURED'],
            complete_all_dimensions=[r['stage'] for r in rows if r['EXECUTION'] == 'EXECUTED' and r['RULE_COVERAGE'] == 'ASSESSED'
                                     and r['residual'] == 0 and r['CORRECTNESS'] == 'MEASURED'])
json.dump(dict(summary=summ, matrix=rows), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
if '--md' in sys.argv:
    with open(sys.argv[sys.argv.index('--md') + 1], 'w', encoding='utf-8') as f:
        f.write(f"# مصفوفة المراحل العشرين — {REF}\n\nمنفّذة {summ['executed']} من 20؛ غير منفّذة (كلاً أو جزءاً): {summ['not_implemented']}؛ "
                f"تغطيةٌ غير مقيسة: {summ['coverage_not_assessed']}؛ متبقٍّ غير صفري: {summ['residual_nonzero']}؛ صحةٌ مقيسة: "
                f"{summ['correctness_measured']}؛ مكتملة في الأبعاد الأربعة: {summ['complete_all_dimensions']}.\n\n"
                "عمود الاختبارات عددُ ملفاتٍ تستورد وحدة منتِجٍ للمرحلة أو تستدعي دالته: ربطٌ خشن (المراحل 12–16 من relations كلها)، لا تغطية قواعد.\n\n"
                '| # | المرحلة | مراحل المحرّك | المنتِجون | المستهلكون | التنفيذ | تغطية القواعد | المتبقّي | الصحة | اكتمال الوقوع | الاختبارات |\n'
                '|---|---|---|---|---|---|---|---|---|---|---|\n')
        for r in rows:
            f.write('| ' + ' | '.join(str(x).replace('|', '¦') for x in (
                r['stage'], r['title'], '، '.join(r['engine_stages']) or '—', '، '.join(r['producers']) or '—', '، '.join(r['consumers']) or '—',
                r['EXECUTION'], r['RULE_COVERAGE'], (f"{r['residual']} ({r['residual_definition']})" if r['residual'] is not None else '—'),
                r['CORRECTNESS'] + (f" {json.dumps(r['correctness'], ensure_ascii=False)[:120]}" if r['correctness'] else ''),
                r['OCCURRENCE_COMPLETE_IN_REF'], len(r['tests']))) + ' |\n')
print(json.dumps(summ, ensure_ascii=False))
