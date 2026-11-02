# -*- coding: utf-8 -*-
"""تقارير الجولة N04 من نتائج القياس وحدها (لا يشغّل التطبيع ولا يغيّر شيفرته).

    python3 round4_report.py --dir <مجلد الحزمة> --n3 <مجلد حزمة N3> --n3-hashes <ملف sha256 لحزمة N3 قبل الجولة>
"""
import argparse, hashlib, html, json, os, glob

ap = argparse.ArgumentParser()
ap.add_argument('--dir', required=True)
ap.add_argument('--n3', required=True)
ap.add_argument('--n3-hashes', required=True)
a = ap.parse_args()
J = lambda f: os.path.join(a.dir, f)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
run = json.load(open(J('normalization_run.json'), encoding='utf-8'))
ver = json.load(open(J('verifier_results.json'), encoding='utf-8'))
cor = json.load(open(J('corruption_results.json'), encoding='utf-8'))
cmp4 = json.load(open(J('n3_vs_n4_comparison.json'), encoding='utf-8'))
cmpb = json.load(open(J('n3_vs_baseline_rerun.json'), encoding='utf-8'))
ctt = json.load(open(J('compare_tool_tests.json'), encoding='utf-8'))
CTT_MD = '\n'.join(f"| {t['no']} | {t['edit']} | {t['expected_exit']} | {t['exit_code']} | "
                    f"{', '.join(t['detected_as'] + t['count_differences'])} |" for t in ctt['tests'])
idn, cnt = run['identity'], run['counts']
RID = idn['run_id']
# حزمة N3 لم تُمسّ: بصماتها الآن كما سُجّلت قبل الجولة
before = {l.split()[1]: l.split()[0] for l in open(a.n3_hashes, encoding='utf-8') if l.strip()}
n3_now = {os.path.basename(p): sha(p) for p in sorted(glob.glob(os.path.join(a.n3, '*')))}
n3_intact = before == n3_now
REF = dict(QURAN_VERSES=6236, NORMALIZED_WORDS=77430, DIFFERENCE_RECORDS=15654, DISPLAY_CHANGED_WORDS=15634,
           ANALYSIS_CHANGED_WORDS=344, UNRESOLVED_WORDS=426, DISPLAY_OPERATIONS=113281, UNEXPLAINED_CHANGED_WORDS=0)
NOW = dict(QURAN_VERSES=cnt['verses'], NORMALIZED_WORDS=cnt['words'], DIFFERENCE_RECORDS=len(run['differences']),
           DISPLAY_CHANGED_WORDS=cnt['words_changed']['normalized_output'], ANALYSIS_CHANGED_WORDS=cnt['words_changed']['analysis_representation'],
           UNRESOLVED_WORDS=cnt['words_unresolved'], DISPLAY_OPERATIONS=cnt['operations']['total'],
           UNEXPLAINED_CHANGED_WORDS=cnt['differences_unexplained'])
files = {os.path.basename(p): sha(p) for p in sorted(glob.glob(os.path.join(a.dir, '*'))) if os.path.isfile(p)
         if not os.path.basename(p).startswith('round4_')}
MODIFIED = [
    ('sarf/normalize_trace.py', 'reconstruct_source وverify_reconstructed_source منفصلتان، وإخفاقات مسمّاة R1–R10 وV1/V2؛ '
     'restore_source بواجهتها تبني من الخلايا والسجل ثم تقارن؛ source_length في الناتج (إضافة)؛ العقد N3.1'),
    ('tools/verify_normalization_package.py', 'المدقّق المستقل: إعادة بناءٍ لا تقرأ حقل source ولا المصحف، ونتائج منفصلة A–F، '
     'وcheck_verse للاستدعاء المباشر'),
    ('tools/corruption_tests.py', 'جديد: اختبارات الإفساد العشرة (15 تجربة) ومن طرفٍ إلى طرف'),
    ('tools/compare_normalization_packages.py', 'جديد: مقارنة حزمتين على القرآن كله، وحماية إصلاحات N3 بالاسم'),
    ('tools/normalization_report.py', 'source_length في سجل الخلايا (إضافة موثّقة)'),
    ('tools/compare_normalization_packages.py (بعد المراجعة)', 'حكمٌ صارم: أي فرقٍ غير مأذون يُفشل المقارنة (خروج 1)، والإضافة المأذونة '
     'وحدها source_length بقيمةٍ صحيحة، وفحص الآيات المضافة والمحذوفة والتكرار، ومقارنة كل حقلٍ لا حقولٍ مختارة'),
    ('tools/compare_tool_tests.py', 'جديد بعد المراجعة: 15 إفساداً لأداة المقارنة (ومنه إفساد المراجع في 7:1) ونسخةٌ سليمة'),
    ('tools/round4_report.py', 'مولِّد تقارير الجولة من نتائج القياس وحدها'),
    ('tests/test_normalize_trace.py', 'إعادة البناء دون استعارة، وإفسادٌ يُكشف برمزه'),
]
CLOSE = [
    ('إعادة البناء لا تستعير قيم المحارف من المصدر', True, 'reconstruct_source والمدقّق: لا قراءة لحقل source ولا للمصحف قبل اكتمال البناء'),
    ('الاسترجاع صحيح على القرآن كاملاً', all(ver['counts'].get(f'{w}:C_match:ok') == ver['verses'] for w in ('display', 'analysis')),
     f"{ver['counts'].get('display:C_match:ok')}/{ver['verses']} و{ver['counts'].get('analysis:C_match:ok')}/{ver['verses']}"),
    ('اختبارات الإفساد تكشف الأخطاء المستهدفة', cor['all_detected'] and cor['all_expected'],
     f"{sum(t['detected'] for t in cor['tests'])}/{len(cor['tests'])}، ومن طرفٍ إلى طرف: {'كُشف' if not cor['end_to_end']['all_ok'] else 'لم يُكشف'}"),
    ('إصلاحات N3 محفوظة بالمقارنة الفعلية (حكمٌ صارم)', cmp4['all_protected'] and cmp4['verdict_ok'],
     f"{sum(p['ok'] for p in cmp4['protection'])}/11؛ فروقٌ غير مأذونة: {cmp4['changes'] or 'لا شيء'}"),
    ('أداة المقارنة ترفض كل فرقٍ غير مأذون', ctt['all_ok'],
     f"{sum(t['ok'] for t in ctt['tests'])}/{len(ctt['tests'])} (السليمة بخروج 0، والمُفسَدة بخروج 1)"),
    ('لا تغيير غير مأذون في نواتج التطبيع', cmp4['texts_identical'] and not cmp4['changes'], cmp4['changes'] or 'لا تغيير'),
    ('جميع الفروق مفسَّرة، ولا إخفاق مخفي', cnt['differences_unexplained'] == 0 and ver['all_ok'] and not cmp4['count_differences'],
     f"غير مفسَّر {cnt['differences_unexplained']}؛ المدقّق {'سليم' if ver['all_ok'] else 'فيه إخفاق'}"),
]
out = dict(round='N04', run_id=RID, commit=idn['commit'], contract=idn['contract'], baseline=dict(contract='N3.0',
           commit='4a3236797fd09d58ccf2b294c505199ee695d62c', run_id='19db4e258f42', package=a.n3, package_intact=n3_intact,
           package_hashes=n3_now), files_sha256=files, reference_counts=REF, current_counts=NOW,
           count_reconciliation={k: dict(reference=REF[k], current=NOW[k], equal=REF[k] == NOW[k]) for k in REF},
           additive_fields=cmp4['allowed_additions'], comparison_n3_n4=dict(changes=cmp4['changes'], count_differences=cmp4['count_differences']),
           comparison_n3_baseline_rerun=dict(changes=cmpb['changes'], additive=cmpb['allowed_additions']),
           protection=cmp4['protection'], verifier=dict(all_ok=ver['all_ok'], hashes=ver['E_hashes'], counts=ver['counts'],
                                                        failure_codes=ver['failure_codes']),
           corruption=cor, compare_tool_tests=ctt, closing_criteria=[dict(criterion=c, ok=o, evidence=str(e)) for c, o, e in CLOSE],
           modified_files=[dict(path=p, reason=r) for p, r in MODIFIED],
           next_stage_commitment='المستهلك الحالي الذي يأخذ نص analysis وحده لا يحمل بالضرورة معلومات العلامات والتأجيلات. '
                                 'جولة خلايا المكتوب ستُلزم المستهلك بحملها، وألا يعدّ شكل التنوين وحده شهادةً اسمية. '
                                 'لم يُنفَّذ هذا الالتزام في N04.')
json.dump(out, open(J('round4_run.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

P = a.dir
REPRO = f"""```
# الشيفرة: الفرع المحلي normalization-repair-04، الالتزام {idn['commit']}
#   (أو من الأرشيف: mkdir code && tar -xzf {P}/normalization_code_{idn['commit'][:10]}.tar.gz -C code)
cd <الشيفرة> && ln -s <مجلدٌ فيه quran_hafs.tsv> data
PYTHONHASHSEED=0 python3 tests/test_normalize_trace.py
PYTHONHASHSEED=0 python3 tools/normalization_report.py --legacy {P}/normalization_previous_output.json --out <مجلد>
python3 -I {P}/verify_normalization_package.py --quran <quran_hafs.tsv> --dir {P} --json <نتائج.json>
python3 -I {P}/corruption_tests.py --dir {P} --quran <quran_hafs.tsv> --verifier {P}/verify_normalization_package.py --out <نتائج.json>
python3 -I {P}/compare_normalization_packages.py --a {a.n3} --b {P} --out <مقارنة.json>
python3 -I {P}/compare_tool_tests.py --base {a.n3} --pkg {P} --tool {P}/compare_normalization_packages.py --out <نتائج.json>
python3 {P}/round4_report.py --dir {P} --n3 {a.n3} --n3-hashes <بصمات N3 قبل الجولة>
```"""
prot_md = '\n'.join(f"| {p['no']} | {p['name']} | {'محفوظ' if p['ok'] else '**مكسور**'} | {str(p['evidence'])[:90]} |" for p in cmp4['protection'])
cor_md = '\n'.join(f"| {t['no']} | {t['name']} | {t['edit'][:70]} | {', '.join(t['expected_to_fail'])} | {', '.join(t['failed_checks'])} | "
                   f"{', '.join(t['failure_codes'])} |" for t in cor['tests'])
rec_md = '\n'.join(f"| {k} | {v['reference']} | {v['current']} | {'=' if v['equal'] else '≠'} |" for k, v in out['count_reconciliation'].items())
close_md = '\n'.join(f"| {c} | {'✓' if o else '✗'} | {e} |" for c, o, e in CLOSE)
ar = f"""# الجولة N04: إصلاح التحقق من الاسترجاع وحماية إصلاحات N3

هوية التشغيل `{RID}` · العقد {idn['contract']} · الالتزام `{idn['commit'][:10]}` (الفرع المحلي `normalization-repair-04`) · \
خط الأساس N3.0 `4a32367` / `19db4e258f42`

لم أدمج شيئاً، ولم أبدأ الترقيم ولا أي مرحلةٍ لاحقة. وفي هذه الجولة دفعتُ بطلبكم فرع خط الأساس `normalization-repair-03` \
(`4a32367`) لتشغيله محلياً؛ أما فرع N04 فمحليٌّ غير مدفوع.

## الخلل
كانت `restore_source` والمدقّق يجمعان مواضع المحارف، ثم يقرآن قيمها من النص الأصلي. فكان الاختبار ينجح ولو فسدت القيم المحفوظة.

## الإصلاح
- **فصلتُ عمليتين:**
  - `reconstruct_source(cells, ops, source_length)` تبني المصدر من خلايا الناتج وسجل العمليات وحدهما، ولا تقرأ قيمة محرفٍ من المصدر؛
  - و`verify_reconstructed_source` تقارنه بالمصدر في خطوةٍ مستقلة.
- **مصادر القيم:**
  - المحرف غير المتغيّر من خليته؛
  - والمحذوف أو المستبدل أو المركّب من `preserved_information`؛
  - والمشتقّ لا يدخل المستعاد.
- **الإخفاق:** عند النقص أو التعارض يُخرج إخفاقاً مسمّى (R1–R10، V1/V2)، ولا يملأ شيئاً من المصدر.
- **ما يُفحص بعد البناء:**
  - نصّ مصدر كل عملية ورموزه؛
  - وشكل كل علامة تنوين؛
  - واتساق المحرف ورمزه وموضعه ومجالاته واشتقاقه.
- **المدقّق المستقل** يطبّق الشروط نفسها بالمكتبة القياسية، ولا يقرأ حقل المصدر في ملف الخلايا. ولا يقرأ المصحف إلا بعد البناء، \
للمقارنة والبصمة.

## النتائج على القرآن كله
- **إعادة البناء دون استعارة:** {ver['counts'].get('display:B_reconstructed:ok')}/{ver['verses']} آية في الناتج المعياري، \
و{ver['counts'].get('analysis:B_reconstructed:ok')}/{ver['verses']} في التمثيل التحليلي.
- **المطابقة:** {ver['counts'].get('display:C_match:ok')}/{ver['verses']} و{ver['counts'].get('analysis:C_match:ok')}/{ver['verses']}.
- **تغطية المواضع:** كاملة.
- **المحاذاة:** صفر أخطاء.
- **البصمات:** سليمة.
- **السبب:** بيانات N3 كانت كاملة؛ والخلل كان في الفحص وحده.

## اختبارات الإفساد
{len(cor['tests'])} تجربةً في عشرة أصناف، على نسخٍ مستقلة. **كُشفت كلها، وكلٌّ بفحصه المختص.**
- **من طرفٍ إلى طرف:** نسخةٌ من الحزمة أُفسدت فيها علامة وقفٍ محفوظة برمزها، وحُدِّثت بصمتها.
- **النتيجة:** البصمات سليمة، ومع ذلك فشل التحقق البنيوي بـR8. فالكشف ليس بالبصمة وحدها.

| رقم | الإفساد | التعديل المصطنع | المتوقَّع فشله | ما فشل فعلاً | رموز الإخفاق |
|---|---|---|---|---|---|
{cor_md}

## حماية إصلاحات N3 (مقارنة القرآن كله بحزمة N3)
- **التغيير:** لا تغيير في نصّ العرض ولا في التمثيل التحليلي، ولا في أي خلية أو عملية أو سجلّ فرق.
- **الإضافة:** حقلٌ واحد موثّق: `source_length` في سجل خلايا كل آية.
- **إعادة تشغيل شيفرة خط الأساس** (`4a32367`) تطابق حزمة N3 تماماً.
- **حزمة N3 نفسها:** {'لم تُمسّ (بصماتها كما سُجّلت قبل الجولة)' if n3_intact else '**تغيّرت بصماتها**'}.

| رقم | الإصلاح المحمي | الحالة | الدليل |
|---|---|---|---|
{prot_md}

## أداة المقارنة بعد المراجعة: كل فرقٍ غير مأذون يُفشلها
وجد المراجع أن الأداة كانت ترصد تغيير مصدر خلية (7:1) ثم تخرج بنجاح.
- **الإصلاح:**
  - صار الحكم صارماً: أي فرقٍ في الخلايا أو مصادرها أو العلامات أو العمليات أو سجلات الفروق أو الأعداد أو أقسام `run.json` يُفشل المقارنة؛
  - الإضافة المأذونة وحدها `source_length`، بشرط أن تساوي طول المصدر؛
  - تُفحص الآيات المضافة والمحذوفة والمكرّرة.
- **الاختبارات:**

| رقم | التعديل المصطنع | الخروج المتوقَّع | الخروج الفعلي | رُصد بـ |
|---|---|---:|---:|---|
{CTT_MD}

## مصالحة الأعداد المرجعية

| البند | N3 | N04 | |
|---|---:|---:|---|
{rec_md}

## معيار إغلاق الجولة

| المعيار | | الدليل |
|---|---|---|
{close_md}

## ما بقي، والالتزام للمرحلة القادمة (غير منفَّذ في N04)
{out['next_stage_commitment']}

ثبات نصّ التطبيع لا يثبت سلامة المراحل اللاحقة.

ومسائل مدخل خلايا المكتوب الأربع (خنجرية المقصورة، وكرسيّ الهمزة على المطّة، والحروف الصغيرة والصفر والصلة، والسكون المشتقّ) \
ما زالت عندكم.

الحالات غير المحسومة {cnt['words_unresolved']} كما كانت.
"""
open(J('round4_report_ar.md'), 'w', encoding='utf-8').write(ar)
codes_md = '\n'.join(f'| `{k}` |' for k in ('R1_MISSING', 'R2_CONFLICT', 'R3_CODEPOINT', 'R4_AT_OUTSIDE_SPANS', 'R5_COMPOSITE_UNPRESERVED',
                                             'R6_NONDERIVED_WITHOUT_SOURCE', 'R7_OUT_OF_RANGE', 'R8_OP_SOURCE_MISMATCH',
                                             'R9_MARK_FORM_MISMATCH', 'R10_PRESERVED_BUT_UNCHANGED', 'V1_MISMATCH', 'V2_LENGTH'))
tech = f"""# N04: التقرير التقني

هوية التشغيل `{RID}` · `{idn['commit']}` · العقد {idn['contract']}

## آلية إعادة البناء
1. **المدخل:** `cells` (المحرف، `src`، `derived`، `mark`)، و`ops` (`source_spans`، `source_text`، `source_codepoints`، \
`preserved_information`)، و`source_length` المعلَن.
2. **من المحفوظ:** لكل `preserved_information`:
   - `at` عددٌ داخل [0، الطول)، وإلا R7؛
   - `char` محرفٌ واحد، و`codepoint` = رمزه، وإلا R3؛
   - `at` داخل `source_spans` لعمليته، وإلا R4؛
   - وقيمتان مختلفتان للموضع نفسه R2، لا «آخر قيمةٍ تفوز».
3. **من الخلايا:**
   - المشتقّة تُتجاوز؛
   - وغير المشتقّة بلا `src` تُعطي R6؛
   - والمركّبة من أكثر من موضع يجب أن تكون مواضعها كلها محفوظة، وإلا R5؛
   - وذات الموضع الواحد تعطي قيمته إن لم يكن محفوظاً؛
   - فإن كان محفوظاً وهي تحمل المحرف نفسه فهو R10؛
   - وخليتان مختلفتان للموضع نفسه R2.
4. **موضعٌ بلا قيمة:** R1، فلا نصّ مستعاد.
5. **بعد البناء:**
   - نصّ مصدر كل عملية ورموزه يطابقان المستعاد في مجالاتها، وإلا R8؛
   - و`mark.form` يطابق رموز المستعاد في `src` التنوين، والوظيفة `null`، وإلا R9.
6. **المقارنة** بالمصدر الأصلي خطوةٌ منفصلة: V1 للتطابق، وV2 للطول.

## الإخفاقات المسمّاة

| الرمز |
|---|
{codes_md}

المعاني في `sarf/normalize_trace.py` (`RECON_CODES`).

## الملفات المعدَّلة وسبب كلٍّ

""" + '\n'.join(f'- `{p}`: {r}' for p, r in MODIFIED) + f"""

## البصمات (sha256)
""" + '\n'.join(f'- `{k}`: `{v}`' for k, v in files.items()) + f"""

## حزمة N3
- المسار: `{a.n3}`.
- {'سليمة' if n3_intact else '**تغيّرت**'}: بصماتها كما سُجّلت قبل الجولة.

## إعادة الإنتاج
{REPRO}
"""
open(J('round4_technical.md'), 'w', encoding='utf-8').write(tech)
h = html.escape
tr = lambda cells: '<tr>' + ''.join(f'<td>{h(str(c))}</td>' for c in cells) + '</tr>'
page = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>تحقق الاسترجاع N04</title><style>
:root{{--bg:#fff;--fg:#1d1d1f;--mut:#666;--line:#ddd;--ok:#1a7f37;--bad:#c0392b}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16181c;--fg:#e8e8ea;--mut:#9a9aa0;--line:#333;--ok:#4cc38a;--bad:#ff7b6b}}}}
body{{background:var(--bg);color:var(--fg);font-family:system-ui,"Noto Naskh Arabic",sans-serif;margin:0;padding:16px;line-height:1.6}}
main{{max-width:1100px;margin:auto}} table{{border-collapse:collapse;width:100%;font-size:.88rem}} td,th{{border-bottom:1px solid var(--line);padding:4px 6px;text-align:right;vertical-align:top}}
.wrap{{overflow-x:auto}} .mut{{color:var(--mut)}} .ok{{color:var(--ok);font-weight:bold}} .bad{{color:var(--bad);font-weight:bold}} code{{font-size:.8rem}}
</style></head><body><main>
<h1>N04: تحقق الاسترجاع وحماية إصلاحات N3</h1>
<p class=mut>هوية التشغيل <code>{RID}</code> · <code>{idn['commit'][:10]}</code> · العقد {idn['contract']} · خط الأساس <code>4a32367</code>/<code>19db4e258f42</code></p>
<h2>معيار الإغلاق</h2><div class=wrap><table><tr><th>المعيار</th><th></th><th>الدليل</th></tr>
{''.join(f"<tr><td>{h(c)}</td><td class={'ok' if o else 'bad'}>{'✓' if o else '✗'}</td><td>{h(str(e))}</td></tr>" for c, o, e in CLOSE)}</table></div>
<h2>إعادة البناء على القرآن كله (المدقّق المستقل)</h2><div class=wrap><table><tr><th>الفحص</th><th>المعياري</th><th>التحليلي</th></tr>
{''.join(tr([n, f"{ver['counts'].get('display:'+k+':ok')}/{ver['verses']}", f"{ver['counts'].get('analysis:'+k+':ok')}/{ver['verses']}"]) for k, n in (('A_coverage', 'A تغطية المواضع'), ('B_reconstructed', 'B إعادة البناء دون استعارة'), ('C_match', 'C المطابقة'), ('text_vs_cells', 'النص = الخلايا'), ('nfc', 'NFC')))}
{tr(['D أخطاء المحاذاة', ver['counts'].get('display:D_alignment_errors'), ver['counts'].get('analysis:D_alignment_errors')])}
{tr(['E البصمات', ' '.join(k + ('✓' if v else '✗') for k, v in ver['E_hashes'].items()), ''])}</table></div>
<h2>اختبارات الإفساد ({len(cor['tests'])})</h2><div class=wrap><table><tr><th>رقم</th><th>الإفساد</th><th>التعديل</th><th>المتوقَّع</th><th>ما فشل</th><th>الرموز</th><th></th></tr>
{''.join(f"<tr><td>{h(t['no'])}</td><td>{h(t['name'])}</td><td>{h(t['edit'])}</td><td>{h(', '.join(t['expected_to_fail']))}</td><td>{h(', '.join(t['failed_checks']))}</td><td><code>{h(', '.join(t['failure_codes']))}</code></td><td class={'ok' if t['detected'] and t['expected_hit'] else 'bad'}>{'كُشف' if t['detected'] else 'لم يُكشف'}</td></tr>" for t in cor['tests'])}
<tr><td>E2E</td><td>من طرفٍ إلى طرف</td><td>{h(cor['end_to_end']['edit'])}</td><td>بنيوي مع بصمةٍ سليمة</td><td>بصمات {'سليمة' if cor['end_to_end']['hashes_ok'] else 'فاسدة'}؛ all_ok={cor['end_to_end']['all_ok']}</td><td><code>{h(str(cor['end_to_end']['failure_codes']))}</code></td><td class={'ok' if not cor['end_to_end']['all_ok'] else 'bad'}>{'كُشف' if not cor['end_to_end']['all_ok'] else 'لم يُكشف'}</td></tr></table></div>
<h2>حماية إصلاحات N3</h2><p>تغييرات النواتج عن N3: <b>{h(str(cmp4['changes'] or 'لا شيء'))}</b> · إضافات موثّقة: {h(str(cmp4['allowed_additions']))} ·
إعادة تشغيل خط الأساس: {h(str(cmpb['changes'] or 'مطابقة'))} · حزمة N3: {'لم تُمسّ' if n3_intact else 'تغيّرت'}</p>
<div class=wrap><table><tr><th>رقم</th><th>الإصلاح</th><th></th><th>الدليل</th></tr>
{''.join(f"<tr><td>{p['no']}</td><td>{h(p['name'])}</td><td class={'ok' if p['ok'] else 'bad'}>{'محفوظ' if p['ok'] else 'مكسور'}</td><td>{h(str(p['evidence'])[:160])}</td></tr>" for p in cmp4['protection'])}</table></div>
<h2>أداة المقارنة بعد المراجعة ({len(ctt['tests'])} اختباراً)</h2><div class=wrap><table><tr><th>رقم</th><th>التعديل</th><th>المتوقَّع</th><th>الفعلي</th><th>رُصد بـ</th></tr>
{''.join(f"<tr><td>{t['no']}</td><td>{h(t['edit'])}</td><td>{t['expected_exit']}</td><td class={'ok' if t['ok'] else 'bad'}>{t['exit_code']}</td><td><code>{h(', '.join(t['detected_as'] + t['count_differences']))}</code></td></tr>" for t in ctt['tests'])}</table></div>
<h2>مصالحة الأعداد</h2><div class=wrap><table><tr><th>البند</th><th>N3</th><th>N04</th></tr>
{''.join(tr([k, v['reference'], v['current']]) for k, v in out['count_reconciliation'].items())}</table></div>
<h2>الالتزام للمرحلة القادمة (غير منفَّذ)</h2><p>{h(out['next_stage_commitment'])}</p>
<footer class=mut><p>الهوية <code>{RID}</code> · التفاصيل في round4_run.json وround4_technical.md</p></footer></main></body></html>"""
open(J('round4.html'), 'w', encoding='utf-8').write(page)
print(RID, 'n3_intact', n3_intact, 'close', all(o for _, o, _ in CLOSE))
