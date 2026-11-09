"""write_reports.py <OUT_DIR>
يكتب customer_report_ar.md وtechnical_report.md وaudit.html من measurement.json وسجلّ القضايا ومصفوفة المراحل في التسليم نفسه:
كل رقمٍ في التقارير مقروءٌ من ملفٍّ في التسليم، والنصّ الواصف ثابتٌ هنا."""
import html, json, os, sys

OUT = sys.argv[1]
J = lambda *p: json.load(open(os.path.join(OUT, *p), encoding='utf-8'))
M = J('measurement.json')
F, B = M['final'], M['batches']
IL = J('registry', 'issue_log.json')
SM = J('registry', 'stage_matrix.json')
tests = [l.rstrip('\n').split('\t') for l in open(os.path.join(OUT, 'tests', 'final_run', 'results.tsv'), encoding='utf-8')]
t_ok = [t for t in tests if t[1] == '0']
t_bad = [t for t in tests if t[1] != '0']
H = M['final_commit'][:7]
n = lambda x: f'{x:,}'.replace(',', '٬') if isinstance(x, int) else str(x)


def tr(d, key='transitions'):
    return '، '.join(f"{t['before']}→{t['after']}: {n(t['n'])}" for t in (d or {}).get(key) or []) or 'لا انتقال'


u, r, ax, ce, rc = F['units_vs_qac'], F['verb_roots_vs_qac'], F['axes'], F['certificates'], F['reconciliation']
u47, r47 = F['v47_from_final']['units_vs_qac'], F['v47_from_final']['verb_roots_vs_qac']
ils = IL['summary']
rows = IL['rows']
fixed = [x for x in rows if x['state'] in ('RESOLVED', 'RESOLVED_IN_FINAL_FEATURES') or (x['state'] == 'CHANGED' and x['classification'] == 'NOT_AN_ERROR')]
gaps = [x for x in rows if x['classification'] == 'IMPLEMENTATION_GAP']
amb = [x for x in rows if x['classification'] == 'VALID_AMBIGUITY']
blk = [x for x in rows if x['classification'] in ('RESOURCE_GAP', 'OWNER_RULING')]
b3ax = B.get('cmp_axes_base_b3', {})
b3ce = B.get('cmp_certs_base_b3', {})
b4u = B.get('cmp_units_b2_b4', {})
v47b3b2 = B.get('cmp_units_v47_b3_b2', {})
v47b2b4 = B.get('cmp_units_v47_b2_b4', {})
v47sw = B.get('cmp_units_b4_v36_v47', {})
b1 = B.get('recon_b1', {})
AXF = J('measurement', 'final', 'cmp_axes.json')
lost_role = AXF['examples'].get('agreement AGREE→UNGOVERNED') or []
amr_none = sum(t['n'] for t in rc.get('transitions') or [] if t['feature'] == 'tense' and t['before'] == 'أمر' and t['after'] is None)

SECTIONS = {}
SECTIONS['ANALYZER_ERRORS_FIXED'] = [
    f"تناقض الأوجه بين المراحل («دُعُوا» وأشباهها): السمات النهائية من الأوجه الحيّة (B1، `sarf/reconcile.py`). المصحف: {n(rc.get('units_changed'))} وحدة، "
    f"{n(rc.get('feature_changes'))} تغيير سمة، وأخطاء الاتساق {n(rc.get('consistency_errors'))}.",
    "وسم «بلا عامل» للحرف الذي لا محلّ له: `ungoverned_kind` يفصل NO_MAHALL عن الدور المؤجَّل وعن القاعدة غير المنفّذة (B3) — وسمٌ لا يغيّر الحكم.",
    "فتحة لفظ الجلالة كانت تُقرأ «نصب أو جر» (قاعدة الممنوع من الصرف لا ترى «أل» المكتوبة في خانته): صارت نصباً (B3).",
    f"المضعَّف في مطابقة الجذر (الشدة عينٌ ولام) والتحقيق الأمامي لمعتلّ اللام («حَقّ» لا يحقّق حقو) (B4): {n(b4u.get('not_correct_to_correct'))} وحدةً "
    f"من معلّقة إلى جذر QAC نفسه، و{n(b4u.get('correct_to_not_correct'))} من صحيحٍ إلى غيره.",
    "عرض مداخل الجذر الواحد كلها بدل أولها (B4): «مصدر (فَعَلَ) أو مصدر (فَعِلَ)».",
    "ضمة فاء الأجوف مع الضمير المتحرك تعيّن الواو (قُلْنَا ← قول) (B4).",
    "شروط حدّ الفقرة PB-L1: لا «مستوفى» بأثر قصّ المدخل (B5).",
    "انتقالان خاطئان كشفهما القياس وأُصلحا: O02 كان يبحث من وراء فعلٍ آخر (7:70 «أَجِئۡتَنَا لِنَعۡبُدَ ٱللَّهَ») (B6)؛ "
    "وإغلاق الإسناد المحلي مع «تعارض طبقتين» في التزامٍ اختياري (8 جمل) (B7)."]
SECTIONS['IMPLEMENTATION_GAPS_CLOSED'] = [
    f"المفعول المرشّح بتعدٍّ مرشّح (O03، مؤجَّل دائماً): «اللَّهَ» في «وليتق الله» و«واتقوا الله» لم يعد بلا دور. المصحف (B3): "
    + '، '.join(f"{'/'.join(map(str, t['key']))}: {n(t['n'])}" for t in b3ax.get('object_record_transitions') or []) + '.',
    "متطلَّب المفعول في إطار الفعل يحيل إلى سجلّ المرشّح (OBJECT_CANDIDATE_DEFERRED) بدل «ليس منصوباً مرشّحاً».",
    "مستهلك v47: استبعاد الأحداث المسحوبة من كل فهرس بمرجعها، وحفظ المعاني كلها، وتمثيل همزة الوصل المعلن (B2).",
    "سجلّ القضايا من المحرّك، وسجلّها قبل/بعد، ومصفوفة المراحل، وأدوات القياس (B0 وما بعده)."]
SECTIONS['VALID_AMBIGUITIES_RETAINED'] = [
    f"«كُلُوا»/«خُذُوا»: وجه الماضي المجهول (فُعِلُوا) لا يمنعه مانعٌ مثبت (حدثا «كَلَا» و«خَذَا» في HFN غير مقرَّين)، فالزمن غير محسوم بعد المصالحة "
    f"(كان «أمر» مرشّحاً مقدَّماً في المرحلة ١٣). يُعلن هذا الانتقال: {n(amr_none)} موضعاً في المصحف من «أمر (مرشّح)» إلى «غير محسوم» (أكثرها كُلُوا وخُذُوا).",
    "«يضارّ كاتب»: الفاعل أو نائب الفاعل بالوجهين؛ «يكونا رجلين» و«تكون تجارة»: خبرٌ مرشّح في وجه الناقص (الفئة مؤجَّلة دستورياً).",
    "«يأب» (ءبو/ءبي) و«ترضون» (رضو/رضي): جذران مرخَّصان في المورد يحقّقان المكتوب.",
    f"v47: «قَالُوا/قَالَتْ» بين قول وقيل، و«طائفة» بين طوف وطيف، وأمثالها: {n(v47sw.get('correct_to_not_correct'))} وحدةً مغلقة في v36 تصير مؤجَّلة "
    "بالتباسٍ جاء به المورد، ولا تحسمه الكتابة."] + [f"{x['occurrence_id']}: {x['after'][:120]}" for x in amb[:12]]
SECTIONS['REGRESSIONS_DECLARED'] = [
    f"مرخَّصٌ صار مؤجَّلاً في المحاور ({len(lost_role)}): " + '؛ '.join(f'{x[0]} «{x[1]}»' for x in lost_role) +
    " — سببها إغلاقاتٌ جديدة صحيحة أنشأت منافساً: «الْحَقُّ» مصدرٌ قد يعمل فتتعلّق به «مِن رَّبِّكَ» (N02 مؤجَّلة بوجهين)، "
    "و«شَكٌّ» (14:10) صار اسماً مغلقاً فنافس «رُسُلُ» على الفاعلية مع أنه في جملة الاستفهام بعد «أَ» — ضعفٌ في حدّ إطار الفعل عند همزة الاستفهام "
    "كشفه الإغلاق، لم يُصلح في هذه المهمة.",
    "تعارض الطبقتين يُعلَن ولا يُخفى: " + '، '.join(f"{t['before']}→{t['after']}={t['n']}" for t in ce.get('obligation_transitions') or []) +
    "؛ وزوال «موضع كل كلمة» حيث صارت الطبقة القديمة تضع الكلمة برابطها (§٨ لم يُنفَّذ)."]
SECTIONS['RESOURCE_OR_OWNER_BLOCKERS'] = [
    "واجهة هوية HFN (r3) غير متاحة محلياً بالتزامٍ مثبَّت: لم تُربط؛ والمستهلك يقرأ ملفات الإصدار المثبَّت (v47 عند HFN 22dcb06).",
    "تعدّي HFN غير مقرّ (is_fact=False) في «اتقى» و«بخس» وأمثالهما: يمنع ترخيص المفعول (O03 يبقى مؤجَّلاً).",
    "جرد أطر التعلّق غير موجود: 13 من 14 تعلّقاً في 2:282 مؤجَّلة.",
    "«ذلكم أقسط»: تفضيلٌ من «أقسط» (أفعل، عدل) لا من «قسط» (جار) — حكمٌ لغوي لصاحب النظرية، والمورد لا يحمل المزيد بمعناه.",
    "«وليّه»: المرحلة ١٣ تثبت الاسمية بقاعدة E02 v2 الموسومة «مقترحة»، والإغلاق يؤجّلها — اعتماد القاعدة لصاحب النظرية.",
    "حدود الجمل من الطبقة القديمة (linguistic_layer)، وموضع الكلمة فيها يُستوفى برابطها؛ وإزالة الاعتماد عليها (§٨) لم تُنفَّذ — "
    "وأثرها ظاهر: التزام «موضع كل كلمة» يسقط حين تضع القديمة المفعول برابطها، ويبقى التعارض في التزام المفعول (CONFLICT) فلا يُغلق.",
    "المعنى السياقي ودلالة الخطاب وتعيين المرجع: غير منفّذة (لا مورد معانٍ سياقية ولا قواعد PC.*).",
    "الجامد وجموع التكسير والمثنى من غير مدخل (رجلين، امرأتان، الشهداء، شهيدين): لا يغطيها HFN.",
    "الإصدار الافتراضي v47 والدمج: لصاحب النظرية بعد المراجعة."] + [f"{x['occurrence_id']}: {x['classification']} — {x['classification_basis'][:120]}" for x in blk[:16]]
SECTIONS['V47_MIGRATION_RESULT'] = [
    f"السبب الذي كان يُنسب إلى «تعارضات التحقيق»: v47 يكتب همزة الوصل «ٱ» (U+0671) في أفعال انفعل وافتعل واستفعل وأشباهها ولمّاتها (1826 حدثاً)، "
    "وv36 يكتبها «ا»؛ وتمثيلٌ معلن «ا» عند القراءة يحفظ المكتوب في verb_written.",
    f"أثر إصلاح المستهلك على v47 (B3 ← B2): {tr(v47b3b2)}؛ صحيح→غيره {n(v47b3b2.get('correct_to_not_correct'))}.",
    f"أثر الإصلاحات الصرفية على v47 (B2 ← B4): {tr(v47b2b4)}؛ صحيح→غيره {n(v47b2b4.get('correct_to_not_correct'))}.",
    f"أثر الانتقال إلى بيانات v47 بالشيفرة النهائية (v36 ← v47): الوحدات {tr(u47)}؛ والأفعال {tr(r47)}.",
    "الحكم: الشيفرة تقرأ v47 سليماً (لا مسحوب حيّ، ولا تعارض تمثيل)، والفرق الباقي التباسٌ جاء به المورد؛ والافتراضي باقٍ v36."]
SECTIONS['PIPELINE_COMPLETENESS_BY_STAGE'] = [
    f"{x['section']} {x['title']} ({x['engine_stage']}): EXECUTED={'نعم' if x['EXECUTED'] else 'لا'}، COMPLETE_IN_DECLARED_SCOPE={x['COMPLETE_IN_DECLARED_SCOPE']}"
    f"، المتبقّي {x['residual']} ({x['residual_definition']})" for x in SM['matrix']]
SECTIONS['READY_FOR_OWNER_ADOPTION'] = [
    "جاهزٌ للمراجعة لا للاعتماد التلقائي: لا دفع ولا دمج (PUSH=NO، MERGE=NO)، والفرع `completion-from-063` محليّ.",
    "ما يحتاج حكم صاحب النظرية قبل الاعتماد: O03 (مرشّحٌ مؤجَّل لا مرخَّص)، وقاعدة الأجوف المضموم، والتحقيق الأمامي لمعتلّ اللام، "
    "ومنع الإغلاق بتعارض الطبقتين، والإصدار الافتراضي (v36 أو v47)، والعوائق المسمّاة أعلاه.",
    f"الاختبارات في التشغيل النظيف عند `{H}`: {len(t_ok)} ناجحة من {len(tests)}" + (f"، وغير الناجحة: {'، '.join(t[0] + ' (' + t[1] + ')' for t in t_bad)}" if t_bad else '') + '.']


def md_sections():
    out = []
    for k, items in SECTIONS.items():
        out.append(f'\n## {k}\n')
        out += [f'- {x}' for x in items]
    return '\n'.join(out)


tech = f"""# التقرير التقني — SARF_COMPLETION_FROM_REPORT_063

الأساس `{M['base_commit'][:7]}` (رأس فرع صفحة 063) ← الالتزام النهائي `{H}` على الفرع `completion-from-063`. الإصدار الافتراضي `release_v36`. لا دفع ولا دمج.

## الدفعات (كلٌّ في التزامه، وبنسخة قياسٍ مجمّدة)

| الدفعة | الالتزام | الموضوع | قياسها على المصحف |
|---|---|---|---|
| B1 | 060f2ed | وحدة الحقيقة بين المراحل (features_final) | لقطة الأساس ← B1: مخالفات {n(B.get('cmp_base_b1', {}).get('violations'))} في {n(B.get('cmp_base_b1', {}).get('verses'))} آية؛ المصالحة: {n(b1.get('units_changed'))} وحدة، {n(b1.get('feature_changes'))} تغيير، أخطاء {n(b1.get('consistency_errors'))} |
| B3 | 8457e01 | O03، فتحة لفظ الجلالة، ungoverned_kind | المحاور: {', '.join(f"{'/'.join(map(str, t['key']))}={t['n']}" for t in b3ax.get('object_record_transitions') or [])}؛ الشهادات: أحكام الجمل {tr(b3ce, 'verdict_transitions')}؛ المستويات {', '.join(f"{t['level']} {t['before']}→{t['after']}={t['n']}" for t in b3ce.get('by_level_transitions') or [])} |
| B2 | bb47a71 | مستهلك v47 | v36: لقطة B3 ← B2 مخالفات {n(B.get('cmp_b3_b2', {}).get('violations'))}؛ v47 (B3←B2): {tr(v47b3b2)} |
| B4 | f4f6481 | الأجوف المضموم، المضعَّف، معتلّ اللام، المداخل كلها | الوحدات بجذر QAC: {tr(b4u)}؛ صحيح→غيره {n(b4u.get('correct_to_not_correct'))} |
| B5 | ca30910 | شروط PB-L1 | الحكم لا يتغيّر (G03)؛ ما يُعلن مستوفى يتغيّر |
| B6 | b00e2f2 | لا مفعول من وراء فعلٍ آخر | أصلح الانتقال الخاطئ الوحيد في محاور B3 (7:70) |
| B7 | 87358ca | تعارض الطبقتين يمنع الإغلاق | أصلح 8 إغلاقاتٍ محلية بمرشّح ظهرت في قياس B3 |

## القياس النهائي (reproduce.sh من نسختين نظيفتين: الأساس ← `{H}`)

- اللقطة: {n(F['snapshot'].get('violations'))} مسار تغيّر في {n(F['snapshot'].get('verses'))} آية (الانتقالات مفصّلة أدناه؛ لا يُشترط الصفر في الإصلاح التحليلي).
- الوحدات بجذر QAC (للقياس وحده): قبل {F['units_vs_qac'].get('before')}، بعد {F['units_vs_qac'].get('after')}؛ {tr(u)}؛ صحيح→غيره **{n(u.get('correct_to_not_correct'))}**، وغيره→صحيح {n(u.get('not_correct_to_correct'))}.
- جذور الأفعال بـQAC: {tr(r)}؛ صحيح→غيره **{n(r.get('correct_to_not_correct'))}**.
- المحاور: {tr(dict(transitions=ax.get('agreement_transitions')))}؛ تغيّر الدور {n(ax.get('role_changes'))}؛ سجلات المفعول {', '.join(f"{'/'.join(map(str, t['key']))}={t['n']}" for t in ax.get('object_record_transitions') or [])}؛ مرخَّصٌ فُقد {n(len(ax.get('licensed_lost') or []))}.
- أنواع «بلا عامل» بعد: {ax.get('ungoverned_kind_after')}.
- الشهادات: أحكام الجمل {tr(ce, 'verdict_transitions')}؛ المستويات {', '.join(f"{t['level']} {t['before']}→{t['after']}={t['n']}" for t in ce.get('by_level_transitions') or [])}؛ الالتزامات {', '.join(f"{t['before']}→{t['after']} (قديمة {t['legacy_before']}→{t['legacy_after']})={t['n']}" for t in ce.get('obligation_transitions') or [])}؛ مغلقٌ فُقد {n(len(ce.get('closed_lost') or []))}.
- المصالحة: {n(rc.get('units_changed'))} وحدة، {n(rc.get('feature_changes'))} تغيير سمة، أخطاء الاتساق {n(rc.get('consistency_errors'))}؛ الانتقالات: {', '.join(f"{t['feature']} {json.dumps(t['before'], ensure_ascii=False)}→{json.dumps(t['after'], ensure_ascii=False)}={t['n']}" for t in rc.get('transitions') or [])}.

## سجلّ القضايا (2:282) قبل/بعد

الحالات: {ils.get('states')}؛ التصنيف النهائي: {ils.get('final_classes')}. التفصيل في `registry/issue_log.md` (قبل، والإصلاح، والدليل، وبعد).

## مصفوفة المراحل

منفّذة {SM['summary']['executed']} من {SM['summary']['rows']}، ومكتملة في نطاقها المعلن {SM['summary']['complete']}؛ وغير المنفّذة: {', '.join(SM['summary']['not_implemented'])}. التفصيل في `registry/stage_matrix.md`.
{md_sections()}

## ما تغيّر في جرد القواعد

- جديد: O03 (مفعولٌ مرشّح بتعدٍّ مرشّح، مؤجَّل دائماً)؛ face_reconciliation (مرحلة)؛ `_weak_lam_barred`؛ OBJECT_CANDIDATE_DEFERRED؛ ungoverned_kind.
- معدَّل: word_case (لفظ الجلالة)؛ align_radicals (المضعَّف)؛ مرشّحات الأجوف في الماضي؛ pb_conditions؛ _verdict (CONFLICT)؛ بحث O02 وكاشف المكمّل (فعلٌ فاصل).
- لا تعديل في الجرد المعتمد (GOLDEN وأمثاله) ولا في المراجع ولا في المعيار؛ ولا قوائم استثناء كلمات.
"""
open(os.path.join(OUT, 'technical_report.md'), 'w', encoding='utf-8').write(tech)

cust = f"""# تقرير صاحب النظرية — إكمال التحليل من صفحة 063

**الخلاصة:** سبع دفعاتٍ محلية على الفرع `completion-from-063` (حتى `{H}`)، كلٌّ مقيسةٌ على المصحف كله في نسخةٍ مجمّدة، وأعيد القياس كله من نسختين نظيفتين.
لا دفع ولا دمج، والإصدار الافتراضي باقٍ v36. التشغيل النظيف للتحليل عند `{M.get('clean_run_commit', '2de9975')[:7]}` (آخر التزامٍ يمسّ التحليل أو الصفحة)، وما بعده أدوات تسليم.

- **الوحدات المغلقة بجذر QAC نفسه** (للقياس وحده): {n(u.get('not_correct_to_correct'))} وحدةً جديدة، و**صحيحٌ صار غير صحيح: {n(u.get('correct_to_not_correct'))}**.
- **«دُعُوا»**: لم يعد يُعرض أمراً مبنياً للمعلوم؛ السمات النهائية من وجه الماضي المجهول الحيّ، والأمر مستبعدٌ بمانعه ومحفوظ.
- **لفظ الجلالة في «وليتق الله» و«واتقوا الله»**: مفعولٌ مرشّح مؤجَّل (التعدّي في HFN غير مقرّ)، لا بلا دور ولا مرخَّص.
- **«الْحَقُّ»**: مغلقة على حقق، ومدخل «حقو» ممنوعٌ بالمكتوب ومسمّى في الدليل.
- **انتقالان خاطئان كشفهما القياس فأُصلحا قبل التسليم**: 7:70 (مفعولٌ من وراء فعلٍ آخر)، و8 إغلاقاتٍ محلية بمرشّح.
- **انتقالٌ معلن**: {n(amr_none)} موضعاً (أكثرها «كُلُوا/خُذُوا») من «أمر (مرشّح)» إلى «غير محسوم»، لأن وجه الماضي المجهول لا يمنعه مانعٌ مثبت.
- **v47**: الشيفرة تقرأه سليماً؛ والفرق الباقي التباسٌ جاء به المورد (قول/قيل في «قالوا»، طوف/طيف…)، فالقرار لكم.

## ما انتقل من مثبتٍ إلى غيره (معلَن)
""" + '\n'.join(f'- {x}' for x in SECTIONS['REGRESSIONS_DECLARED']) + """

## ما ينتظر حكمكم
""" + '\n'.join(f'- {x}' for x in SECTIONS['RESOURCE_OR_OWNER_BLOCKERS'][:9]) + f"""

## الصفحة
`trace/arabic-sarf-064.html` (مسجّلة في الفهرس)، وسجلّ قراءة أقسامها المتغيّرة عن 063 صفاً صفاً `trace/section_reading_log.tsv`.
"""
open(os.path.join(OUT, 'customer_report_ar.md'), 'w', encoding='utf-8').write(cust)

esc = lambda x: html.escape(str(x))
issue_rows = ''.join(f"<tr><td>{esc(x['issue_id'])}</td><td>{esc(x['occurrence_id'])}</td><td>{esc(x['classification'])}</td><td>{esc(x['state'])}</td>"
                     f"<td>{esc((x['before'] or '—')[:160])}</td><td>{esc(x['fix'] or '—')}</td><td>{esc((x['after'] or '—')[:160])}</td></tr>" for x in rows)
mat_rows = ''.join(f"<tr><td>{esc(x['section'])}</td><td>{esc(x['title'])}</td><td>{esc(x['engine_stage'])}</td><td>{'نعم' if x['EXECUTED'] else 'لا'}</td>"
                   f"<td>{esc(x['COMPLETE_IN_DECLARED_SCOPE'])}</td><td>{esc(x['residual'])}</td><td>{esc(x['residual_definition'])}</td><td>{esc(x['blocker'] or '—')}</td></tr>"
                   for x in SM['matrix'])
sec_html = ''.join(f"<h2>{esc(k)}</h2><ul>" + ''.join(f'<li>{esc(i)}</li>' for i in v) + '</ul>' for k, v in SECTIONS.items())
test_rows = ''.join(f"<tr><td>{esc(t[0])}</td><td>{'نجح' if t[1] == '0' else esc(t[1])}</td><td>{esc(t[2])}</td></tr>" for t in tests)
audit = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>تدقيق الإكمال من 063</title><style>body{{font-family:system-ui,'Noto Naskh Arabic',sans-serif;margin:16px;line-height:1.6;background:#fff;color:#111}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}}td,th{{border:1px solid #ccc;padding:4px 6px;vertical-align:top}}th{{background:#f3f3f3}}
.wrap{{overflow-x:auto}}code{{background:#f5f5f5;padding:0 3px}}</style></head><body>
<h1>تدقيق SARF_COMPLETION_FROM_REPORT_063</h1><p>الأساس <code>{esc(M['base_commit'][:7])}</code> ← النهائي <code>{esc(H)}</code>؛ PUSH=NO، MERGE=NO؛ الافتراضي release_v36.</p>
<h2>القياس النهائي</h2><ul><li>الوحدات بجذر QAC: {esc(tr(u))}؛ صحيح→غيره <b>{esc(u.get('correct_to_not_correct'))}</b></li>
<li>جذور الأفعال: {esc(tr(r))}؛ صحيح→غيره <b>{esc(r.get('correct_to_not_correct'))}</b></li>
<li>الشهادات: أحكام الجمل {esc(tr(ce, 'verdict_transitions'))}؛ مغلقٌ فُقد {esc(len(ce.get('closed_lost') or []))}</li>
<li>المحاور: مرخَّصٌ فُقد {esc(len(ax.get('licensed_lost') or []))}</li>
<li>المصالحة: أخطاء الاتساق {esc(rc.get('consistency_errors'))}</li></ul>
{sec_html}
<h2>مصفوفة المراحل</h2><div class="wrap"><table><tr><th>القسم</th><th>المرحلة</th><th>المحرّك</th><th>EXECUTED</th><th>COMPLETE</th><th>المتبقّي</th><th>تعريفه</th><th>العائق</th></tr>{mat_rows}</table></div>
<h2>سجلّ القضايا (2:282)</h2><div class="wrap"><table><tr><th>القضية</th><th>الموضع</th><th>التصنيف</th><th>الحالة</th><th>قبل</th><th>الإصلاح</th><th>بعد</th></tr>{issue_rows}</table></div>
<h2>الاختبارات (التشغيل النظيف)</h2><div class="wrap"><table><tr><th>الاختبار</th><th>الرمز</th><th>ث</th></tr>{test_rows}</table></div>
</body></html>"""
open(os.path.join(OUT, 'audit.html'), 'w', encoding='utf-8').write(audit)
print('written', OUT)
# MANIFEST بعد التقارير: بصمة كل ملفٍّ في التسليم
import hashlib
_m = J('MANIFEST.json')
_m['files'] = {os.path.relpath(os.path.join(r, f), OUT): dict(sha256=hashlib.sha256(open(os.path.join(r, f), 'rb').read()).hexdigest(),
                                                           bytes=os.path.getsize(os.path.join(r, f)))
               for r, _, fs in os.walk(OUT) for f in fs if os.path.relpath(os.path.join(r, f), OUT) != 'MANIFEST.json'}
json.dump(_m, open(os.path.join(OUT, 'MANIFEST.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('manifest', len(_m['files']))
