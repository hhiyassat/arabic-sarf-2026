"""issue_registry.py <جذر الشيفرة> <OUT.json> [--md OUT.md] [--ref 2:282]
سجلّ القضايا (SARF_COMPLETION_FROM_REPORT_063 §١): يُعاد حسابه من مخرج المحرّك في الجذر المعطى، لا من نصّ الصفحة.

لكل قضية: issue_id، occurrence_id، section (المرحلة)، actual_output، rule_or_function، dependency، required_behavior، verification،
classification (ANALYZER_ERROR | IMPLEMENTATION_GAP | RESOURCE_GAP | VALID_AMBIGUITY | OWNER_RULING)، وclassification_basis.

التصنيف من نوع السبب المسجَّل في المخرج نفسه (نصّ التأجيل، ونوع «بلا عامل»، وحالة العلاقة)، ومن فحوصٍ مكتوبة هنا بأسمائها؛
والتعليقات اللغوية (ANNOTATIONS) شرحٌ لقضايا بعينها في 2:282 للتقرير، لا قوائم استثناء في المحلّل: لا يقرؤها المحرّك."""
import json, os, re, sys, collections

ROOT = os.path.abspath(sys.argv[1])
OUT = sys.argv[2]
REF = sys.argv[sys.argv.index('--ref') + 1] if '--ref' in sys.argv else '2:282'
MD = sys.argv[sys.argv.index('--md') + 1] if '--md' in sys.argv else None
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from sarf.stages import run_ref                                       # noqa: E402

C = run_ref(REF)
V = C.get('records')[REF]
U = C.get('units')[REF]['units']
tok = {u: (loc, t) for u, loc, t in V['tokens']}
loc_of = lambda wi: f'{REF}:{wi + 1}'
issues = []


def add(kind, occ, section, actual, rule, dep, required, verification, cls, basis, **kw):
    issues.append(dict(issue_id=f'{kind}#{len([i for i in issues if i["issue_id"].startswith(kind + "#")]) + 1:02d}', kind=kind,
                       occurrence_id=occ, section=section, actual_output=actual, rule_or_function=rule, dependency=dep,
                       required_behavior=required, verification=verification, classification=cls, classification_basis=basis, **kw))


# ١ الوحدات المعلّقة (المرحلة ١٢)
def unit_class(reason, text):
    if re.search(r'أكثر من جذر أو وزن مرخَّص|أكثر من جذر في HFN', reason):
        return 'VALID_AMBIGUITY', 'أكثر من جذرٍ مرخَّص في المورد يحقّق المكتوب؛ والحسم يحتاج دليلاً لا ترتيباً (ما لم يمنع التحقيق المكتوب أحدهما: انظر forward_check)'
    if 'لا مدخل له في HFN' in reason:
        return 'RESOURCE_GAP', 'HFN مورد أحداثٍ ومشتقّاتها؛ والاسم بلا مدخلٍ مشتقّ فيه (جامد، أو جمع تكسير، أو مثنّى من غير المدخل)'
    if 'لا تحليل جذري ووزني لـعامل+أل+جذع' in reason:
        return 'IMPLEMENTATION_GAP', 'مسار «عامل+أل+جذع» غير منفّذ في الجذر والوزن'
    if 'لم يثبت بالكتابة أنه فعل' in reason or 'لم تثبت الاسمية' in reason:
        return 'IMPLEMENTATION_GAP', 'مسار الاسم الجامد/الظرف/أفعل التفضيل لا يصل إلى الجذر: الوحدة تُفحص فعلاً فلا تطابق'
    if 'لا رخصة' in reason:
        return 'IMPLEMENTATION_GAP', 'مولّد المرشّحات في مسار الجذر لا يولّد الوجه الذي يولّده إطار الفعل (F01)'
    return 'IMPLEMENTATION_GAP', 'سببٌ غير مصنَّف آلياً'


def forward_check(text, roots):
    """فحصٌ أمامي مكتوب: الجذر الناقص (لامه و/ي) لا يحقّق كلمةً لامُها المكتوبة حرفٌ صحيح مشدَّد بلا و/ي بعده (الحقّ ← حقق لا حقو)"""
    out = {}
    for r in roots:
        if len(r) == 3 and r[2] in 'وي' and 'ّ' in text and not re.search('[وي]', text.split('ّ')[-1] if 'ّ' in text else text):
            last = re.findall('(.)[ً-ْ]*ّ', text)
            if last and last[-1] == r[1]:
                out[r] = 'REJECTED_BY_WRITTEN_FORM: عين الجذر مشدَّدة في آخر الكلمة ولا لام معتلّة مكتوبة'
    return out


for (wi, ui), G in sorted(U.items()):
    if G.closed:
        continue
    reason = G.O.get('deferred') or ''
    cls, basis = unit_class(reason, G.O['text'])
    roots = re.findall(r'[ء-ي]{3}(?= \(| ،|،|$)', reason.split(':')[-1]) if 'أكثر من جذر' in reason else []
    fc = forward_check(G.O['text'], roots) if roots else {}
    if fc and len(fc) == len(roots) - 1:
        cls, basis = 'ANALYZER_ERROR', 'التحقيق الأمامي المكتوب يمنع أحد الجذرين، والمحلّل لا يطبّقه: ' + '؛ '.join(f'{k}: {v}' for k, v in fc.items())
    add('UNIT_UNCLOSED', f'{loc_of(wi)}#u{ui}', '١٢ الوحدات اللفظية وإغلاقها', f'«{G.O["text"]}» معلَّقة: {reason}',
        'sarf.algebra (إغلاق الوحدة) ← sarf.root.morph / sarf.cells.lex_index', 'HFN v36 (events.csv، lexical_units.csv)',
        'إغلاقٌ بدليلٍ مكتوب، أو تأجيلٌ يسمّي سببه وبدائله', 'tools/completion063/issue_registry.py: إعادة التشغيل؛ والقياس على المصحف',
        cls, basis, text=G.O['text'], forward_check=fc or None)

# ٢ «بلا عامل» (المحور ١٤)
for uid, ax in V['axes'].items():
    inf = ax.get('inflection') or {}
    if inf.get('agreement') != 'UNGOVERNED':
        continue
    kind = inf.get('ungoverned_kind')
    cls = {'NO_MAHALL': ('NOT_AN_ERROR', 'حرفٌ لا محلّ له: الحكم صحيح، والوسم يقوله (كان يُعرض «بلا عامل» وحده كأنه ينقصه عامل)'),
           'ROLE_DEFERRED': ('VALID_AMBIGUITY', 'علاقةٌ مؤجَّلة تسمّيه بدليلها (تعدٍّ مرشّح، أو نواةٌ مؤجَّلة)'),
           'MAHALL_UNRESOLVED': ('VALID_AMBIGUITY', 'محلّ المبني غير محسوم: علاقةٌ مؤجَّلة تسمّيه'),
           'EVIDENCE_NOT_ADOPTED': ('IMPLEMENTATION_GAP', 'دليلٌ سابق لم تستوفِ قاعدة الطبقة شروطه'),
           'LEXICAL_ENTRY_MISSING': ('RESOURCE_GAP', 'لا مدخل في ملف المبنيات'),
           'ROLE_RULE_NOT_IMPLEMENTED': ('IMPLEMENTATION_GAP', 'قاعدة الدور غير منفّذة (حال، تمييز، خبر الناسخ، المضارع المرفوع بالتجرّد، …)'),
           None: ('UNCLASSIFIED', 'المخرج لا يحمل نوع «بلا عامل» (قبل §١ من هذه المهمة)')}[kind]
    add('UNGOVERNED', f'{tok[uid][0]}#{uid}', '١٤ المحاور: الإعراب', f'«{tok[uid][1]}»: UNGOVERNED' + (f' [{kind}]' if kind else ''),
        'sarf.relations._Tok.axes', 'العلاقات المرخَّصة (أدوار العمل)', 'وسمٌ يفصل «لا محلّ» عن «الدور مؤجَّل» عن «لا قاعدة»، ولا يغيّر الحكم',
        'tests/test_c063_objects.py K05، K09', cls[0], cls[1], ungoverned_kind=kind, pending_relations=inf.get('pending_relations'))

# ٣ التعلّق المؤجَّل (14أ)
att = [r for r in V['records'] if r['type'] == 'ATTACH']
for r in att:
    if r['status'] == 'LICENSED':
        continue
    rs = r['reason'] or ''
    cls = ('RESOURCE_GAP', 'لا جرد لأطر التعلّق (الفعل/المشتقّ ← حروف الجرّ التي يتعدّى بها) في المشروع') if 'جرد' in rs else \
        ('VALID_AMBIGUITY', 'أكثر من متعلَّقٍ مرشّح')
    add('ATTACH_DEFERRED', r['relation_id'], '14أ العلاقات: التعلّق', f'{r["texts"]}: {r["status"]} — {rs[:160]}', f'sarf.relations ({r["rule_id"]})',
        'جرد أطر التعلّق (غير موجود)', 'تعلّقٌ مرخَّص بإطارٍ مثبت، أو مؤجَّلٌ ببدائله', 'إعادة التشغيل', *cls)

# ٤ النواة «ذلكم أقسط»
for r in V['records']:
    if r['type'] in ('PREDICATION', 'PREDICATIVE_PP') and 'ذَٰلِكُمْ' in str(r['texts'].get('subject')):
        add('NUCLEUS', r['relation_id'], '14أ العلاقات: الإسناد', f'{r["texts"]}: {r["status"]} — {r["reason"][:200]}', f'sarf.relations ({r["rule_id"]}) + E01',
            'HFN v36: مدخل «قَسِطَ» (فعِل) يمنع E01 من إثبات أفعل التفضيل', 'نواةٌ مرخَّصة إن ثبت الخبر اسماً (أفعل تفضيل)، وإلا مؤجَّلة بدليلها',
            'tests/test_relations.py T13', 'OWNER_RULING' if r['status'] != 'LICENSED' else 'VALID_AMBIGUITY',
            '«أقسط» تفضيلٌ من «أقسط» (أفعل، عَدَل) لا من «قسط» (جار): بناء التفضيل من غير الثلاثي حكمٌ لغوي يعود لصاحب النظرية، والمورد لا يحمل المزيد بمعناه')

# ٥ تناقض الأوجه بين المراحل (دعوا وأشباهها)
FF = (C.get('features_final') or {}).get(REF) if 'face_reconciliation' in C.status else None
F13 = C.get('features')[REF]
for r in V['records']:
    if r['type'] != 'VERB_FRAME' or not (r.get('frame') or {}).get('candidates'):
        continue
    m = re.search(r'\.w(\d+)\.u(\d+)$', r['heads']['verb'])
    k = (int(m.group(1)), int(m.group(2)))
    rej = [c for c in r['frame']['candidates'] if c['status'] == 'REJECTED']
    live13 = [(f, F13[k][f]['v']) for f in ('tense', 'voice') if any(F13[k].get(f, {}).get('v') == c.get(f) for c in rej)]
    if not live13:
        continue
    after = None if FF is None else [(f, FF[k][f]['v']) for f in ('tense', 'voice') if any(FF[k][f]['v'] == c.get(f) for c in rej)]
    add('FACE_CONTRADICTION', r['heads']['verb'], '١٣ السمات ↔ 14أ إطار الفعل',
        f'«{r["texts"]["verb"]}»: المرحلة ١٣ تعرض {live13} حيّةً، و{r["relation_id"].split(":")[3]} يمنع وجهها',
        'sarf.reconcile.reconcile_features (جديد)', 'أوجه إطار الفعل', 'سماتٌ نهائية من الأوجه الحيّة ومن الوجه نفسه، والمستبعد محفوظ بسببه',
        'tests/test_reconcile.py C01–C12؛ measure_reconciliation.py', 'ANALYZER_ERROR', 'قيمة وجهٍ ممنوع تُعرض حيّة: خطأ',
        resolved_in_this_run=(after == [] if after is not None else False))

# ٦ السمة المثبتة في ١٣ مع وحدةٍ معلّقة الاسمية (وليّه)
for (wi, ui), G in sorted(U.items()):
    f = F13.get((wi, ui)) or {}
    if not G.closed and 'لم تثبت الاسمية' in (G.O.get('deferred') or '') and (f.get('pos') or {}).get('st') == 'مثبت':
        add('STAGE_CONTRADICTION', f'{loc_of(wi)}#u{ui}', '١٢ الإغلاق ↔ ١٣ السمات',
            f'«{G.O["text"]}»: ١٣ تثبت الصنف «{f["pos"]["v"]}» ({f["pos"].get("ev")})، والإغلاق يقول: {G.O.get("deferred")}',
            'sarf.features (pos) ↔ sarf.algebra (closure)', '—', 'مرحلةٌ لا تثبت ما تؤجّله الأخرى بلا ربط الدليل بينهما',
            'إعادة التشغيل', 'OWNER_RULING' if 'مقترحة' in str(f['pos'].get('ev')) else 'ANALYZER_ERROR',
            'الإثبات في ١٣ بقاعدةٍ موسومة «مقترحة» لم يعتمدها صاحب النظرية: لا يُرفع إلى الإغلاق ولا يُسقط حتى يُحكم فيها'
            if 'مقترحة' in str(f['pos'].get('ev')) else 'تناقضٌ بين مرحلتين')

# ٧ الفقرة: شروط الحدّ
for P in C.get('paragraphs'):
    cand = P['candidate']
    cond = (cand.get('boundary') or {}).get('conditions') or {}
    for side in ('start', 'end'):
        for k_, v_ in cond.get(side, {}).items():
            if k_ == 'b' and v_.startswith('MET') and 'المدخل' in v_ and not (cond[side]['a'].startswith('MET')):
                add('PARAGRAPH_BOUNDARY', f'{cand["paragraph_id"]}#{side}.{k_}', '١٥ الفقرة', f'{side}.{k_}: {v_}',
                    'sarf.algebra.pb_conditions', 'حدّ المدخل المحلَّل',
                    'غياب جملةٍ في المدخل المحلَّل ليس دليل حدّ: «لم يُفحص» ما لم يكن حدّ مصدر', 'tests/test_paragraph.py',
                    'ANALYZER_ERROR', 'شرطٌ يُعلَن مستوفى بأثر قصّ المدخل (تحليل آيةٍ وحدها)، لا بدليلٍ لغوي')

# ٨ المراحل غير المنفّذة
for st, (s_, why) in C.status.items():
    if s_ == 'NOT_IMPLEMENTED':
        add('STAGE_NOT_IMPLEMENTED', st, st, f'{s_}: {why}', f'sarf.stages ({st})', 'مورد معانٍ سياقية/قواعد أدوات الخطاب',
            'مرحلةٌ منفّذة في نطاقٍ معلن', 'C.status', 'RESOURCE_GAP' if 'المدخل المعجمي' in why else 'IMPLEMENTATION_GAP', why)

summary = dict(ref=REF, root=ROOT, head=os.popen(f'git -C "{ROOT}" rev-parse HEAD 2>/dev/null').read().strip(),
               by_kind=dict(collections.Counter(i['kind'] for i in issues)),
               by_class=dict(collections.Counter(i['classification'] for i in issues)),
               by_kind_class={f'{a}|{b}': n for (a, b), n in collections.Counter((i['kind'], i['classification']) for i in issues).items()},
               units_total=len(U), units_unclosed=sum(1 for G in U.values() if not G.closed),
               attach_total=len(att), attach_deferred=sum(1 for r in att if r['status'] != 'LICENSED'))
json.dump(dict(summary=summary, issues=issues), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
if MD:
    with open(MD, 'w', encoding='utf-8') as f:
        f.write(f'# سجلّ القضايا — {REF}\n\nالجذر: `{ROOT}` عند `{summary["head"]}`\n\n')
        f.write('| الفئة | العدد |\n|---|---|\n' + ''.join(f'| {k} | {v} |\n' for k, v in summary['by_kind'].items()))
        f.write('\n| التصنيف | العدد |\n|---|---|\n' + ''.join(f'| {k} | {v} |\n' for k, v in summary['by_class'].items()))
        f.write('\n| issue_id | الموضع | المرحلة | المخرج الفعلي | القاعدة/الدالة | الاعتماد | السلوك المطلوب | التحقق | التصنيف | أساسه |\n'
                '|---|---|---|---|---|---|---|---|---|---|\n')
        for i in issues:
            f.write('| ' + ' | '.join(str(i[k]).replace('|', '¦').replace('\n', ' ')[:220] for k in
                                      ('issue_id', 'occurrence_id', 'section', 'actual_output', 'rule_or_function', 'dependency',
                                       'required_behavior', 'verification', 'classification', 'classification_basis')) + ' |\n')
print(json.dumps(summary, ensure_ascii=False))
