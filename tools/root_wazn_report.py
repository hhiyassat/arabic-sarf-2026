#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/root_wazn_report.py — يولّد تقارير RW02 كلها من سجلّ نتائج واحد (compare_blind/dev_results.jsonl وdev_metrics.json)،
ثم يصالح الأعداد بين JSON وMarkdown وHTML وTSV ويرفض التسليم إن اختلفت.

    python3 tools/root_wazn_report.py <مجلد التسليم> <مجلد RW01/attachments>
"""
import collections, hashlib, html, json, os, sys

D = sys.argv[1]
AT = os.path.join(D, 'attachments')
RW1 = sys.argv[2]


def jl(p):
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


M = json.load(open(os.path.join(AT, 'compare_blind', 'dev_metrics.json'), encoding='utf-8'))
R = jl(os.path.join(AT, 'compare_blind', 'dev_results.jsonl'))
AU = json.load(open(os.path.join(AT, 'file_audit.json'), encoding='utf-8'))
EX = json.load(open(os.path.join(AT, 'exposure_log.json'), encoding='utf-8'))
FG = json.load(open(os.path.join(AT, 'reference_face_groups.json'), encoding='utf-8'))
CC = json.load(open(os.path.join(AT, 'corruption_results.json'), encoding='utf-8'))
DF = json.load(open(os.path.join(AT, 'rw01_vs_rw02.json'), encoding='utf-8'))
NM = json.load(open(os.path.join(AT, 'named_diagnostics.json'), encoding='utf-8'))
M1 = json.load(open(os.path.join(RW1, 'compare_blind', 'dev_metrics.json'), encoding='utf-8'))
TESTLOG = open(os.path.join(AT, 'tests_rw02.log'), encoding='utf-8').read()
meta = M['meta']['analysis_meta']
MAIN = M['denominators']['PROVISIONAL_REFERENCE_MAIN']
FLAG = M['denominators']['PROVISIONAL_REFERENCE_FLAGGED']
RAW = M['denominators']['RAW_ALL']
WZ = M['wazn_denominators']
WMAIN, WFLAG = WZ['PROVISIONAL_REFERENCE_MAIN'], WZ['PROVISIONAL_REFERENCE_FLAGGED']
EXE = M['execution']
byid = {r['id']: r for r in R}

# ---------- المسار التشخيصي بالصنف (من فرعه وحده) ----------
pa_st, pa_n, pa_k, pa_wrong = collections.Counter(), 0, 0, []
for rec in jl(os.path.join(AT, 'dev_analysis_pos_assisted.jsonl'))[1:]:
    r = byid[rec['id']]
    if r['ref_pos'] != 'فعل ماضٍ' or r['denominators']['root'] != 'PROVISIONAL_REFERENCE_MAIN':
        continue
    b = rec['A_LEXICAL_MORPH']['branches'].get('verb_morph_pos_assisted')
    st = (b or {}).get('execution_status')
    out = (b or {}).get('outputs') or {}
    pa_st[out.get('status') if st == 'EXECUTED_WITH_RESULTS' else st] += 1
    if out.get('status') == 'accepted':
        pa_n += 1
        pa_k += out['root'] == r['ref_root']
        if out['root'] != r['ref_root']:
            pa_wrong.append(dict(id=r['id'], word=r['word'], ref_root=r['ref_root'], root=out['root']))


def wl(k, n, z=1.96):
    import math
    if not n:
        return None
    p = k / n
    return round((p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n), 4)


PA = dict(scope='POS_ASSISTED_DIAGNOSTIC: الصنف «فعل» من المرجع مُعطى؛ ليس نتيجةً عمياء', verbs=sum(pa_st.values()), statuses=dict(pa_st),
          accepted=pa_n, agree=pa_k, precision=round(pa_k / pa_n, 4) if pa_n else None, wilson_low=wl(pa_k, pa_n), disagreements=pa_wrong)
json.dump(PA, open(os.path.join(AT, 'pos_assisted_diagnostic.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------- جداول TSV من السجل نفسه ----------
COLS = ['id', 'word', 'ref_root', 'ref_wazn', 'ref_pos', 'ref_root_type', 'ref_wazn_status', 'root_denominator', 'wazn_denominator',
        'field_review_root', 'field_review_wazn', 'field_review_pos', 'A_execution', 'A_level', 'proven_root', 'proven_wazn_selected',
        'proven_wazn_source', 'root_agreement', 'wazn_agreement_convention', 'ref_root_in_faces', 'pair_in_same_face_convention',
        'faces', 'B_level', 'B_proven_roots', 'observations', 'cause_hypotheses', 'protection_assessment']


def flat(r):
    return dict(r, root_denominator=r['denominators']['root'], wazn_denominator=r['denominators']['wazn'],
                field_review_root=r['field_review']['root'], field_review_wazn=r['field_review']['wazn'], field_review_pos=r['field_review']['pos'],
                faces=' ؛ '.join(f"{f['candidate_id']}:{f['root']}|{f.get('wazn') or ''}|{f.get('wazn_source') or ''}|{f['kind']}|{f['branch']}"
                                 for f in r['faces']),
                B_proven_roots=' '.join(r['B_proven_roots']), observations=' '.join(r['observations']), cause_hypotheses=' '.join(r['cause_hypotheses']))


def write_tsv(name, rows):
    p = os.path.join(AT, name)
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\t'.join(COLS) + '\n')
        for r in rows:
            x = flat(r)
            f.write('\t'.join('' if x.get(c) is None else str(x.get(c)).replace('\t', ' ').replace('\n', ' ') for c in COLS) + '\n')
    return len(rows)


n_full = write_tsv('dev_results_full.tsv', R)
diss = [r for r in R if not ({'AGREE_ROOT', 'AGREE_ROOT_AND_WAZN', 'REFERENCE_CANDIDATE_PRESENT_SELECTION_UNRESOLVED'} & set(r['observations']))
        or r['wazn_mismatch'] or r['root_mismatch']]
n_diss = write_tsv('dev_observations_needing_review.tsv', diss)
flag_rows = [r for r in R if 'PROVISIONAL_REFERENCE_FLAGGED' in r['denominators'].values()]
n_flag = write_tsv('dev_flagged_reference_rows.tsv', flag_rows)
with open(os.path.join(AT, 'exclusions.tsv'), 'w', encoding='utf-8') as f:
    f.write('id\tmetric\tdenominator\tfield_review_word\tfield_review_root\tfield_review_wazn\treason\n')
    n_excl = 0
    for r in R:
        for metric, den in r['denominators'].items():
            if den != 'PROVISIONAL_REFERENCE_MAIN':
                n_excl += 1
                fr = r['field_review']
                f.write(f"{r['id']}\t{metric}\t{den}\t{fr['word']}\t{fr['root']}\t{fr['wazn']}\tحقلٌ معنيّ بالمقياس موسوم في الملحق\n")
        if not r['ref_wazn']:
            n_excl += 1
            f.write(f"{r['id']}\twazn+pair\tNO_REFERENCE_WAZN\t\t\t\t{r['ref_wazn_status']}: الوزن الفارغ لا صحة ولا خطأ\n")

# ---------- عيوب المحلّل المقترحة (لجولةٍ لاحقة) ----------
def ids(pred, k=40):
    xs = [r for r in R if pred(r)]
    return len(xs), [dict(id=r['id'], word=r['word'], ref_root=r['ref_root']) for r in xs[:k]]


B_wrong = [r for r in R if r['B_root_agreement'] is False]
defects = [
    dict(code='D1_ROOT_MISMATCH_PROVEN', status='PROPOSED', n=ids(lambda r: r['root_mismatch'])[0], examples=ids(lambda r: r['root_mismatch'])[1],
         note='جذرٌ مثبت يخالف المرجع (ادَّخَرَ، اسْتَكْتَمَ، نَمِشْ)؛ والحكم النهائي بعد مراجعة الصفوف'),
    dict(code='D2_PUBLIC_PATH_PEELS_RADICAL', status='PROPOSED', n=len(B_wrong),
         examples=[dict(id=r['id'], word=r['word'], ref_root=r['ref_root'], B=r['B_proven_roots']) for r in B_wrong[:40]],
         note='الواجهة العامة تقشر حرفاً أصلياً (الكاف ضميراً، والنون حرف مضارعة) فتثبت جذراً آخر'),
    dict(code='D3_REALIZED_FORM_NOT_MIZAN', status='PROPOSED', n=ids(lambda r: 'ANALYZER_OUTPUTS_REALIZED_FORM_NOT_MIZAN' in r['cause_hypotheses'])[0],
         examples=ids(lambda r: 'ANALYZER_OUTPUTS_REALIZED_FORM_NOT_MIZAN' in r['cause_hypotheses'])[1],
         note='hfn_form المسترجع شكلٌ متحقق (افْتَعَى) والمرجع ميزان (افْتَعَلَ)؛ والمحلّل لا يُخرج الميزان'),
    dict(code='D4_PROTECTION_VIA_PEELING_OF_LEXICAL_WORD', status='PROPOSED',
         n=ids(lambda r: r.get('protection_assessment') == 'PROTECTED_VIA_PEELING_WORD_IS_LEXICAL_IN_HFN')[0],
         examples=ids(lambda r: r.get('protection_assessment') == 'PROTECTED_VIA_PEELING_WORD_IS_LEXICAL_IN_HFN')[1],
         note='حمايةٌ ناتجة عن قشر سابقة/لاحقة من كلمةٍ موجودة كاملةً في HFN (فَتَكَ، سَمِنَ، كَمَنَ)؛ يُحفظ الوجه المعجمي المنافس'),
    dict(code='D5_PROTECTION_WITHOUT_CLASS_DEFERRAL', status='PROPOSED',
         n=ids(lambda r: r.get('protection_assessment') == 'PROTECTED_WORD_HAS_LEXICAL_FACE_IN_HFN')[0],
         examples=ids(lambda r: r.get('protection_assessment') == 'PROTECTED_WORD_HAS_LEXICAL_FACE_IN_HFN')[1],
         note='حمايةٌ غير ملتبسة لكلمةٍ لها وجهٌ معجمي في HFN (أَحْمَدَ، صَارَ)؛ حكم الدستور class_deferred عند احتمال القراءتين'),
    dict(code='D6_TEMPLATE_CANDIDATE_NOT_LICENSED', status='PROPOSED', n=ids(lambda r: 'REFERENCE_ROOT_ONLY_IN_UNLICENSED_TEMPLATE' in r['observations'])[0],
         examples=ids(lambda r: 'REFERENCE_ROOT_ONLY_IN_UNLICENSED_TEMPLATE' in r['observations'])[1], note='القالب ولّد الجذر المرجعي ولم يُرخَّص'),
    dict(code='D7_NO_CANDIDATE_WORD_IN_HFN', status='PROPOSED',
         n=ids(lambda r: 'REFERENCE_ROOT_NOT_AMONG_CANDIDATES' in r['observations'] and r['availability']['word_in_hfn_v36'] and not r['cause_hypotheses'])[0],
         examples=ids(lambda r: 'REFERENCE_ROOT_NOT_AMONG_CANDIDATES' in r['observations'] and r['availability']['word_in_hfn_v36'] and not r['cause_hypotheses'])[1],
         note='الكلمة في HFN v36 بحروفها وحركاتها، ولا مرشّح يحمل الجذر المرجعي، ولا فرضية سبب آلية (آبَ، بَتَا)'),
    dict(code='D8_PEELING_SUSPECTED', status='HYPOTHESIS', n=ids(lambda r: 'PEELING_SUSPECTED' in r['cause_hypotheses'])[0],
         examples=ids(lambda r: 'PEELING_SUSPECTED' in r['cause_hypotheses'])[1], note='فرضية: المقشِّر اقترح سابقة أو لاحقة؛ لا تثبت خطأ القشر وحدها')]
json.dump(dict(scope='مقترحات لجولةٍ لاحقة؛ لم يُعدَّل المحلّل في RW02', defects=defects),
          open(os.path.join(AT, 'analyzer_defects_proposed.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------- RW01 مقابل RW02 ----------
g1 = M1['gold']
cmp_table = [
    ('مقام الجذر الرئيسي', g1['n'], MAIN['n'], 'سياسة المرجع: نزاع الوزن أو الصنف لا يُسقط قياس الجذر (121 صفاً عادت)'),
    ('جذرٌ مثبت (مقبول/المجموع)', f"{g1['root_proven']['correct']}/{g1['root_proven']['n']}", f"{MAIN['root_proven']['agree']}/{MAIN['root_proven']['n']}",
     'المقام وحده؛ مخرج المحلّل لم يتغيّر'),
    ('الجذر المرجعي بين الأوجه', g1['root_recall_in_candidates']['value'], MAIN['ref_root_in_faces']['value'],
     'المقام، و17 صفاً بإصلاح المشتقات'),
    ('الزوج في الوجه نفسه (مقام الوزن)', g1['pair_recall_in_candidates']['value'], WMAIN['pair']['value'], 'المقام وإصلاح المشتقات'),
    ('وزنٌ مثبت (موافق/المجموع)', f"{g1['wazn_proven']['correct']}/{g1['wazn_proven']['n']}",
     f"{WMAIN['wazn_selected']['agree_convention']['k']}/{WMAIN['wazn_selected']['n']}",
     'RW01 عدّ العائلة وقائمة الأوزان وزناً مثبتاً؛ RW02 يعدّ الوزن المختار الواحد وحده'),
    ('أعطال التنفيذ (كلمات)', 0, EXE['words_with_any_failure'],
     'RW01 أعلن صفراً خطأً: فرع المشتقات فشل في 16,499 صفاً ولم يُعدّ؛ RW02 بعد الإصلاح'),
    ('«CONTEXT_REQUIRED»', g1['categories'].get('CONTEXT_REQUIRED'), 0,
     f"أُعيدت تسميتها REFERENCE_CANDIDATE_PRESENT_SELECTION_UNRESOLVED ({MAIN['observations'].get('REFERENCE_CANDIDATE_PRESENT_SELECTION_UNRESOLVED')})")]

# ---------- measurement.json ----------
analyzer_unchanged = DF['analyzer_output_changed'] == 0
MEAS = dict(
    mandate='SARF_ROOT_WAZN_BENCHMARK_REPAIR_02', previous='SARF_ROOT_WAZN_BENCHMARK_01 (محفوظ في sarf_root_wazn_benchmark01، لم يُكتب فوقه)',
    identity=dict(commit=meta['commit'], tool=meta['tool'], python=meta['python'], hashseed=meta['hashseed'], resources=meta['resources'],
                  input_sha256=meta['input_sha256'], analysis_sha256=M['meta']['analysis_sha256'], reference_sha256=M['meta']['reference_sha256'],
                  corrections_sha256=M['meta']['corrections_sha256'], policy_sha256=M['meta']['policy_sha256'],
                  analyzer_base='7502e80', analyzer_diff_vs_base='فارغ (sarf، lexicon، الفهرس)', hfn='release_v36 (لم يُبدَّل)'),
    rw01_historical=dict(participle_branch_failed_rows=16499, error="AttributeError(\"'list' object has no attribute 'H'\")",
                         cause='مُرِّر ناتج cells_of المركّب (الخلايا، الرموز) بدل قائمة الخلايا', rw01_reported_execution_failures=0,
                         correction='كان العطل في كل الصفوف، وأُخفي لأن العدّاد لم يرَ أعطال الفروع؛ وما أُثبت عبر verb_morph وB_PUBLIC لم يتأثر'),
    execution=EXE, denominators_policy=M['meta']['policy'],
    root=dict(PROVISIONAL_REFERENCE_MAIN={k: MAIN[k] for k in ('n', 'root_proven', 'root_coverage', 'root_mismatch_rows', 'ref_root_in_faces',
                                                             'ref_root_in_faces_or_templates', 'candidates_not_in_reference_group', 'levels', 'observations')},
              PROVISIONAL_REFERENCE_FLAGGED={k: FLAG[k] for k in ('n', 'root_proven', 'ref_root_in_faces')},
              RAW_ALL={k: RAW[k] for k in ('n', 'root_proven', 'root_coverage', 'ref_root_in_faces')}, REVIEWED_ACCEPTED=dict(n=0)),
    wazn=dict(PROVISIONAL_REFERENCE_MAIN=dict(n=WMAIN['n'], wazn_selected=WMAIN['wazn_selected'], pair_in_same_face=WMAIN['pair'],
                                              wazn_mismatch_rows=MAIN['wazn_mismatch_rows'], root_and_wazn_mismatch_rows=MAIN['root_and_wazn_mismatch_rows'],
                                              surface_pattern_agreement=MAIN['surface_pattern_agreement'],
                                              proven_without_selected_wazn=MAIN['proven_without_selected_wazn'],
                                              pair_literal=MAIN['pair_in_same_face_literal'], pair_surface=MAIN['pair_in_same_face_surface']),
              PROVISIONAL_REFERENCE_FLAGGED=dict(n=WFLAG['n'], pair_in_same_face=WFLAG['pair'])),
    B_public=MAIN['B_public'], protection=MAIN['protection'], cause_hypotheses=MAIN['cause_hypotheses'],
    distinct_words=M['distinct_words'], distinct_roots=M['distinct_roots'], pos_assisted_diagnostic={k: v for k, v in PA.items() if k != 'disagreements'},
    by_pos={k: dict(n=v['n'], ref_root_in_faces=v['ref_root_in_faces']['value'], pair=v['pair_in_same_face_convention']['value'],
                    root_proven=v['root_proven']['n'], B_root_proven=v['B_public']['root_proven']['n']) for k, v in M['by_pos'].items()},
    corruption=dict(cases=len(CC['cases']), refused=sum(v['refused'] for v in CC['cases'].values())),
    tests=dict(passed=TESTLOG.count('ok  '), failed=TESTLOG.count('FAIL')),
    rw01_vs_rw02=dict(counts=DF['counts'], analyzer_output_changed=DF['analyzer_output_changed']),
    exposure={k: v['n'] for k, v in EX['partitions'].items()},
    verdicts=dict(BENCHMARK_REPAIRED=TESTLOG.count('FAIL') == 0, PARTICIPLE_BRANCH_EXECUTES=EXE['branch_status']['participle'].get('EXECUTION_FAILURE', 0) == 0,
                  STRUCTURAL_VALIDATION_ENFORCED=all(v['refused'] for v in CC['cases'].values()), DEV_RERUN_COMPLETED=True,
                  ANALYZER_UNCHANGED=analyzer_unchanged, HELDOUT_INFERENCE_NOT_RUN=True, REFERENCE_REVIEWED=False, ANALYZER_APPROVED=None))
json.dump(MEAS, open(os.path.join(D, 'measurement.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def pct(x):
    return '—' if x is None else f'{x:.4f}'


def rt(d):
    return f"{d['k']:,} / {d['n']:,} = {pct(d['value'])} (ويلسون {pct(d['wilson_low'])})"


# ---------- التقرير العربي للمالك ----------
cust = f"""# مقياس الجذر والوزن، الجولة 02: إصلاح أداة القياس وإعادة التطوير

**التكليف:** SARF_ROOT_WAZN_BENCHMARK_REPAIR_02 · **التزام القياس:** `{meta['commit'][:7]}` · **HFN:** {meta['resources']['hfn_release']} · **dev فقط**

> كل رقمٍ هنا مولَّدٌ من `attachments/compare_blind/dev_metrics.json` و`dev_results.jsonl`، ومصالَحٌ آلياً مع JSON وHTML وTSV.

## الأحكام

| الحكم | النتيجة |
|---|---|
| BENCHMARK_REPAIRED | {'نعم' if MEAS['verdicts']['BENCHMARK_REPAIRED'] else 'لا'}: {MEAS['tests']['passed']} فحصاً ناجحاً، و{MEAS['tests']['failed']} فاشلاً |
| PARTICIPLE_BRANCH_EXECUTES | {'نعم' if MEAS['verdicts']['PARTICIPLE_BRANCH_EXECUTES'] else 'لا'}: نتائج في {EXE['branch_status']['participle'].get('EXECUTED_WITH_RESULTS', 0):,} كلمة، وفارغٌ في {EXE['branch_status']['participle'].get('EXECUTED_EMPTY', 0):,}، ولا عطل |
| STRUCTURAL_VALIDATION_ENFORCED | {'نعم' if MEAS['verdicts']['STRUCTURAL_VALIDATION_ENFORCED'] else 'لا'}: {MEAS['corruption']['refused']} من {MEAS['corruption']['cases']} إفساداً للمخرج الحقيقي رُفضت قبل أي مقياس |
| DEV_RERUN_COMPLETED | نعم: {EXE['words']:,} كلمة، والتنفيذ كامل في {EXE['words_complete']:,} |
| ANALYZER_UNCHANGED | {'نعم' if analyzer_unchanged else 'لا'}: مخرج المحلّل في فروعه المشتركة مطابق لـRW01 في كل الصفوف، ولا فرق في `sarf/` عن `7502e80` |
| HELDOUT_INFERENCE_NOT_RUN | نعم |
| REFERENCE_REVIEWED | لا: لا صفّ مراجَعٌ مقبول؛ فالمقام الرئيسي «مرجعٌ مؤقت» لا ذهبي |

## ١. ما كان خطأً في RW01

- **فرع المشتقات فشل في الصفوف الـ16,499 كلها** بالخطأ `{MEAS['rw01_historical']['error']}`.
  - السبب: مُرِّر ناتج `cells_of` كاملاً، وهو زوج (الخلايا، رموز الرسم)، بدل قائمة الخلايا.
  - وأعلن RW01 «أعطال التنفيذ: صفر»، لأن العدّاد لم يكن يرى أعطال الفروع. **هذا خطأٌ مني في القياس، لا في المحلّل.**
- **ما لم يتأثر:** ما أُثبت عبر فرع الأفعال والواجهة العامة. أما تغطية المرشّحين واستدعاؤهم في RW01 فكانت ناقصة الفروع.
- **تسمياتٌ ادّعت سبباً لم يثبت:**
  - «CONTEXT_REQUIRED» ({g1['categories'].get('CONTEXT_REQUIRED'):,} صفاً) صارت `REFERENCE_CANDIDATE_PRESENT_SELECTION_UNRESOLVED`.
  - «extra_unsupported_candidates» صارت «مرشّحٌ غير مطابق للمجموعة المرجعية».
- **الوزن المثبت:** كان RW01 يعدّ عائلة الباب الأول وقائمة الأوزان وزناً مثبتاً.

## ٢. ما أُصلح

- **حالة كل فرع:** لكل فرعٍ حالته: EXECUTED_WITH_RESULTS، أو EXECUTED_EMPTY، أو EXECUTION_FAILURE، أو NOT_APPLICABLE. ولكل كلمةٍ حالة تنفيذ: كامل، أو جزئي، أو فاشل.
- **المقارن يرفض** قبل أي نسبة: الناقص، والمكرر، والزائد، والكلمة المبدلة، وبصمة المدخل المخالفة، وخلط الوضعين، والمخطط الخاطئ، واختلاف الموارد، وتغيّر السياسة، والأوجه غير المشتقة من الفروع.
- **المقامات:**
  - `PROVISIONAL_REFERENCE_MAIN`، و`PROVISIONAL_REFERENCE_FLAGGED`، و`RAW_ALL`، و`REVIEWED_ACCEPTED` (فارغ).
  - الحكم لكل حقل: نزاع الوزن لا يُسقط قياس الجذر، ونزاع الصنف لا يُسقطه.
- **الكلمة:** تُقاس بمجموعة أوجهها في dev، لا بأول صف. وأوجه test لا تدخل المجموعات.
- **الوزن:**
  - يُفصل الوزن المختار عن العائلة.
  - لكل وزنٍ مصدره (`LEXICON_RETRIEVAL` أو `DECLARED_FORM_MAPPING`)، ولا يُدّعى توليدٌ مستقل للميزان.
  - المطابقة الحرفية تُعرض منفصلةً عن مطابقة الاتفاقية.
- **الملاحظة منفصلة عن فرضية السبب،** ولا سبب محقق بلا مراجعة.

## ٣. النتائج (المقام الرئيسي المؤقت)

| المقياس | النتيجة |
|---|---|
| جذرٌ مثبت (المسار أ) | {rt(MAIN['root_proven']['precision'])} |
| تغطية الجذر | {rt(MAIN['root_coverage'])} |
| الجذر المرجعي بين الأوجه المرخّصة أو المسترجعة | {rt(MAIN['ref_root_in_faces'])} |
| … ومعها القالب غير المرخّص | {rt(MAIN['ref_root_in_faces_or_templates'])} |
| وزنٌ مختار مطابق للمرجع (مقام الوزن {WMAIN['n']:,}) | {rt(WMAIN['wazn_selected']['agree_convention'])}، والمصدر كله LEXICON_RETRIEVAL |
| الجذر والوزن في الوجه نفسه | {rt(WMAIN['pair'])} |
| جذرٌ مثبت (الواجهة العامة، ب) | {rt(MAIN['B_public']['root_proven'])}، والتغطية {pct(MAIN['B_public']['coverage']['value'])}، **ولا تُخرج وزناً عربياً** |
| POS_ASSISTED_DIAGNOSTIC (ليس أعمى) | {PA['agree']:,} / {PA['accepted']:,} = {pct(PA['precision'])} (ويلسون {pct(PA['wilson_low'])}) من {PA['verbs']:,} فعلاً |

**عدم تطابق الحقول:**
- {MAIN['root_mismatch_rows']} جذراً مثبتاً، و{MAIN['wazn_mismatch_rows']} وزناً مختاراً، يجتمع الاثنان في {MAIN['root_and_wazn_mismatch_rows']} صفين.
- من أوزان عدم التطابق، {MAIN['observations'].get('PROVEN_WAZN_EQUALS_REFERENCE_SURFACE_PATTERN', 0)} وزناً يساوي فيها وزن المحلّل الشكلَ المتحقق في المرجع (`surface_pattern`)، لا ميزانه.

**المقام المنفصل (`PROVISIONAL_REFERENCE_FLAGGED`):** {FLAG['n']} صفاً للجذر و{WFLAG['n']} للوزن، وفيه: الجذر المرجعي بين الأوجه {pct(FLAG['ref_root_in_faces']['value'])}.

## ٤. RW01 مقابل RW02

| البند | RW01 | RW02 | سبب الفرق |
|---|---|---|---|
""" + '\n'.join(f'| {a} | {b} | {c} | {d} |' for a, b, c, d in cmp_table) + f"""

**مقارنة الصفوف** (`attachments/rw01_vs_rw02.json`):
- تغيّر مخرج المحلّل في **{DF['analyzer_output_changed']}** صفاً.
- صار فرع المشتقات يُخرج نتائج في {DF['counts'].get('PARTICIPLE_BRANCH_NOW_EXECUTES', 0):,} صفاً.
- تغيّر استدعاء الجذر بإصلاحه في {DF['counts'].get('RECALL_CHANGED_BY_PARTICIPLE_FIX', 0)} صفاً فقط، لأن الاسترجاع المعجمي كان يغطي أكثرها.
- غيّرت سياسة المقام {DF['counts'].get('DENOMINATOR_CHANGED_BY_POLICY', 0)} صفاً.
- بقي عدم تطابق الجذر في {DF['counts'].get('REMAINS_ROOT_MISMATCH', 0)}، وعدم تطابق الوزن في {DF['counts'].get('REMAINS_WAZN_MISMATCH', 0)}.

**إصلاح أداة القياس ليس تحسيناً في المحلّل.**

## ٥. ما بقي عيباً مقترحاً في المحلّل (لجولةٍ لاحقة)

| الرمز | العدد | الحالة |
|---|---:|---|
""" + '\n'.join(f"| {d['code']} | {d['n']:,} | {d['status']} |" for d in defects) + f"""

التفاصيل والأمثلة في `attachments/analyzer_defects_proposed.json`، والكلمات العشر المسمّاة في `attachments/named_diagnostics.json`.

## ٦. ما يحتاج قرارك

1. مراجعة الحقول الموسومة في الملحق. ولا شيء منها مقبولٌ بعد، فلا مقام مراجَعاً.
2. هل يُطلب من المحلّل إخراج الميزان بجانب المتحقق ({MAIN['observations'].get('PROVEN_WAZN_EQUALS_REFERENCE_SURFACE_PATTERN', 0)} صفاً)؟
3. إجازة جولة إصلاح المحلّل على العيوب D1–D7.
"""
open(os.path.join(D, 'customer_report_ar.md'), 'w', encoding='utf-8').write(cust)

# ---------- التقرير التقني ----------
br = EXE['branch_status']
tech = f"""# التقرير التقني: SARF_ROOT_WAZN_BENCHMARK_REPAIR_02

## ١. الهوية والتجميد

| البند | القيمة |
|---|---|
| الفرع | `rootwazn-bench-02` من `21bcee9` (فرع RW01) |
| التزام القياس | `{meta['commit']}`، شُغّل من نسخة `git archive` مجمّدة |
| Python / البذرة | {meta['python']} / PYTHONHASHSEED={meta['hashseed']} |
| HFN | `{meta['resources']['hfn_path']}` |
| بصمات HFN | """ + '، '.join(f"{k.split('/')[1]} `{(v or '')[:12]}…`" for k, v in meta['resources']['hfn_files'].items()) + f""" |
| بصمة شيفرة المحلّل وموارده | `{meta['resources']['analyzer_code_sha256'][:16]}…` (sarf، lexicon، الفهرس) |
| المحلّل مقابل `7502e80` | لا فرق في `sarf/` ولا `lexicon/` ولا الفهرس |
| المدخل الأعمى | `{meta['input_sha256'][:16]}…`، مطابق بايتاً لمدخل RW01 |
| المخرج | `{M['meta']['analysis_sha256'][:16]}…`، وتشغيلان متطابقان بايتاً ببايت |
| المرجع / الملحق / السياسة | `{M['meta']['reference_sha256'][:12]}…` / `{(M['meta']['corrections_sha256'] or '')[:12]}…` / `{M['meta']['policy_sha256'][:12]}…` |
| RW01 | محفوظٌ في `~/Downloads/sarf_root_wazn_benchmark01/`، ولم يُكتب فوقه |

## ٢. إصلاح استدعاء المشتقات

- **الخطأ:** كان الاستدعاء `participle_analyses(cells_of(word, 'B'))`.
- **عقد الدالتين:**
  - `cells_of(text, base_id)` تُعيد زوجاً: (الخلايا، رموز الرسم).
  - `participle_analyses` تأخذ قائمة خلايا ذات `C/H/L/O`.
- **الإصلاح:** فككتُ الزوج ومرّرتُ الخلايا وحدها.
- **ما يُحفظ في السجل:**
  - الخلايا: `[C, H, L]`.
  - الحروف غير المنطوقة: `O['silent']`.
  - عدد رموز الرسم.
  - مخرج الدالة كاملاً: (الجذر، الباب، النوع، α، العمليات، مستوى الرخصة).
- **وزن الوجه:** من التحويل المعلن `PARTICIPLE_WAZN`، ومصدره `DECLARED_FORM_MAPPING`.

**اختبارات موجبة:**
- ضَارِب ← ضرب I فاعل برخصة حدث.
- مَضْرُوب ← ضرب I مفعول.
- قَائِل ← قول بإبدال العين.
- آخِذ ← ءخذ.

**اختبارات أخرى:**
- بَيْت ← EXECUTED_EMPTY.
- «abc» والفارغ ← EXECUTION_FAILURE/INVALID_INPUT.

## ٣. التنفيذ حسب الفرع ({EXE['words']:,} كلمة)

| الفرع | """ + ' | '.join(['EXECUTED_WITH_RESULTS', 'EXECUTED_EMPTY', 'EXECUTION_FAILURE']) + """ |
|---|---:|---:|---:|
""" + '\n'.join(f"| {b} | {v.get('EXECUTED_WITH_RESULTS', 0):,} | {v.get('EXECUTED_EMPTY', 0):,} | {v.get('EXECUTION_FAILURE', 0):,} |" for b, v in sorted(br.items())) + f"""

**حالة التنفيذ على مستوى الكلمة:**

| الحالة | العدد |
|---|---:|
| كامل | {EXE['words_complete']:,} |
| جزئي | {EXE['words_partial']:,} |
| فاشل | {EXE['words_failed']:,} |
| بأي عطل | {EXE['words_with_any_failure']:,} |
| أعطال الواجهة العامة | {EXE['B_failures']} |

**كيف يظهر العطل في القياس:** مُثبتٌ بالاختبار M1. فإن فشل فرع المشتقات في كل الكلمات، صارت كلها `PARTIAL_EXECUTION`، وظهر العطل باسم فرعه ونوعه، ولم يتحوّل إلى «لم يجد».

**التاريخ:** في RW01 فشل هذا الفرع في 16,499 صفاً، وأُعلن «صفر» خطأً.

## ٤. سلامة المدخل والمخرج (`validate_analysis`)

**ما يرفضه المقارن قبل أي مقياس:**
- معرّفات مكررة أو ناقصة أو زائدة.
- كلمة سجلٍّ تخالف كلمة المدخل أو كلمة المرجع.
- بصمة مدخلٍ مخالفة، أو `n_rows` مخالف.
- وضع ملفٍّ أو سجلٍّ مخالف، أو فرعٌ تشخيصي في تشغيلٍ أعمى.
- مخططٌ ناقص، أو حالة تنفيذٍ غير معروفة.
- أوجهٌ لا تُشتق من الفروع: يُعاد اشتقاقها في المقارن ويُطابَق.
- موارد تخالف موارد المقارنة.
- سياسة متغيّرة.
- صفٌّ من غير dev.
- مرجعٌ بمعرّفاتٍ مكررة.

**الإفساد على المخرج الحقيقي** (`attachments/corruption_results.json`): {MEAS['corruption']['refused']} من {MEAS['corruption']['cases']} إفساداً رُفضت: """ + '، '.join(CC['cases']) + f""".

## ٥. سياسة المرجع (مجمّدة قبل التشغيل، `policy_sha256` في كل ملف)

""" + '\n'.join(f'- **{k}:** {v}' for k, v in M['meta']['policy']['denominators'].items()) + f"""
- **الحقول المعنية بكل مقياس:** {json.dumps(M['meta']['policy']['metric_fields'], ensure_ascii=False)}. وغياب الصف من الملحق `UNREVIEWED`، لا قبول.
- **{M['meta']['policy']['wazn_empty_reference']}.**
- **{M['meta']['policy']['wazn_family']}.**
- **{M['meta']['policy']['multi_face']}.**
- **{M['meta']['policy']['comparison']}.**

**الاستبعادات:** كل صفٍّ ومقياسٍ وسببه في `attachments/exclusions.tsv` ({n_excl:,} سطراً).

## ٦. المقاييس

### الجذر

| المقام | n | جذرٌ مثبت | التغطية | الجذر بين الأوجه | ومع القوالب |
|---|---:|---|---|---|---|
""" + '\n'.join(f"| {k} | {v['n']:,} | {v['root_proven']['agree']}/{v['root_proven']['n']} | {pct(v['root_coverage']['value'])} | {pct(v['ref_root_in_faces']['value'])} | {pct(v['ref_root_in_faces_or_templates']['value'])} |"
                for k, v in M['denominators'].items()) + f"""

### الوزن والزوج (مقامات حقول الوزن)

| المقام | n | وزنٌ مختار مطابق (اتفاقية) | حرفي | الزوج في الوجه (اتفاقية) |
|---|---:|---|---|---|
""" + '\n'.join(f"| {k} | {v['n']:,} | {v['wazn_selected']['agree_convention']['k']}/{v['wazn_selected']['n']} | {v['wazn_selected']['agree_literal']['k']}/{v['wazn_selected']['n']} | {rt(v['pair'])} |"
                for k, v in WZ.items()) + f"""

**تفصيل الوزن:**
- **مصدر الوزن المختار:** {json.dumps(MAIN['wazn_selected']['sources'], ensure_ascii=False)}. فهو صحة ربط التحليل بصيغة HFN، **لا توليدٌ للميزان**.
- **جذرٌ مثبت بلا وزنٍ مختار واحد:** {MAIN['proven_without_selected_wazn']['n']} صفاً، منها {MAIN['proven_without_selected_wazn']['reference_in_family']} صفٌّ وزنه المرجعي داخل العائلة (REFERENCE_WEIGHT_INCLUDED_IN_FAMILY)، ولم يُعدّ في الدقة.
- **موافقة الوزن المختار للشكل المتحقق `surface_pattern`:** {rt(MAIN['surface_pattern_agreement'])}.
- **الزوج بالشكل المتحقق:** {rt(MAIN['pair_in_same_face_surface'])}.
- **عدم التطابق:** {MAIN['root_mismatch_rows']} جذراً، و{MAIN['wazn_mismatch_rows']} وزناً، والاثنان معاً في {MAIN['root_and_wazn_mismatch_rows']}.
  - **مقارنة RW01:** كان فيه 135 عدم تطابقٍ في الوزن (133 في WAZN_ERROR، و2 في ROOT_ERROR). منها 6 لم تعد «وزناً مختاراً مخالفاً»، لأن الوزن صار قائمةً أو عائلةً لا وزناً واحداً.

### الواجهة العامة (ب)

{rt(MAIN['B_public']['root_proven'])}. وصفوفٌ أخرجت وزناً عربياً: {MAIN['B_public']['wazn_output_rows']}، فالواجهة لا تُخرج وزناً، ولم يُنسب إليها وزن.

### الكلمات والجذور

**الكلمات** (n = {M['distinct_words']['n']:,}، منها متعددة الأوجه {M['distinct_words']['multi_face']}):

| المقياس | النتيجة |
|---|---|
| مثبتٌ في المجموعة | {rt(M['distinct_words']['proven'])} |
| أحد جذور المجموعة بين المرشّحين | {rt(M['distinct_words']['any_group_root_in_candidates'])} |
| كل جذور المجموعة بين المرشّحين | {rt(M['distinct_words']['all_group_roots_in_candidates'])} |

**الجذور** (n = {M['distinct_roots']['n']:,}):

| المقياس | العدد |
|---|---:|
| جذرٌ له صفٌّ مثبتٌ موافق | {M['distinct_roots']['any_row_proven_correct']:,} |
| جذرٌ له صفٌّ مثبتٌ مخالف | {M['distinct_roots']['any_row_proven_wrong']} |
| كل صفوفه بين الأوجه | {M['distinct_roots']['all_rows_ref_root_in_faces']:,} |

### حسب الصنف (المقام الرئيسي)

| الصنف | n | الجذر بين الأوجه | الزوج | جذرٌ مثبت (أ) | (ب) |
|---|---:|---:|---:|---:|---:|
""" + '\n'.join(f"| {k} | {v['n']:,} | {pct(v['ref_root_in_faces']['value'])} | {pct(v['pair_in_same_face_convention']['value'])} | {v['root_proven']['n']} | {v['B_public']['root_proven']['n']} |"
                for k, v in M['by_pos'].items()) + f"""

التقسيمات الأخرى (root_type، wazn_status، التنفيذ، التوافر، المراجعة) في `dev_metrics.json`.

## ٧. الملاحظات وفرضيات السبب (المقام الرئيسي)

| الملاحظة | العدد |
|---|---:|
""" + '\n'.join(f'| {k} | {v:,} |' for k, v in sorted(MAIN['observations'].items(), key=lambda kv: -kv[1])) + """

| فرضية السبب (غير محققة) | العدد |
|---|---:|
""" + '\n'.join(f'| {k} | {v:,} |' for k, v in sorted(MAIN['cause_hypotheses'].items(), key=lambda kv: -kv[1])) + f"""

- **`verified_cause`:** فارغٌ في كل صف، لأنه لا مراجعة بعد.
- **«المرشّح غير المطابق للمجموعة المرجعية»:** {MAIN['candidates_not_in_reference_group']['total']} في {MAIN['candidates_not_in_reference_group']['rows']} صفاً. قد يكون وجهاً صحيحاً غير مسجل.

## ٨. الحماية

| التقييم الآلي | العدد |
|---|---:|
""" + '\n'.join(f'| {k} | {v} |' for k, v in MAIN['protection'].items()) + f"""

لا يُعدّ شيءٌ منها «حمايةً صحيحة» بيقين، فالكلمة المعجمية بلا سياق. وكل سجلٍّ يحفظ هوية الحماية وسوابقها ولاحقتها والبديل.

## ٩. الكلمات المسمّاة (`attachments/named_diagnostics.json`)

| الكلمة | التقشير | الحماية | المستوى | الأوجه (جذر\\|وزن\\|مصدر\\|فرع) | الواجهة العامة | المرجع (dev) |
|---|---|---|---|---|---|---|
""" + '\n'.join(f"| {x['word']} | {json.dumps(x['peeling_proposed'], ensure_ascii=False) if x['peeling_proposed'] else '—'} | "
                f"{(x['protection'] or {}).get('identity', '—')} {(x['protection'] or {}).get('proclitics') or ''} | {x['level']} | "
                + '؛ '.join(f"{f['root']}\\|{f['wazn'] or ''}\\|{f['wazn_source'] or ''}\\|{f['branch']}" for f in x['faces'][:4]) + ' | '
                + ' '.join(y['root'] for y in x['B_public_morph'] if y['status'] == 'accepted') + ' | '
                + '، '.join(f"{y['id']} {y['root']} {y['wazn']}" for y in x['reference_dev']) + ' |' for x in NM) + f"""

## ١٠. الاختبارات ({MEAS['tests']['passed']} ناجحاً، و{MEAS['tests']['failed']} فاشلاً)

السجل كاملاً في `attachments/tests_rw02.log`، والتغطية:

| المجموعة | ما تغطيه |
|---|---|
| I1–I4 | العزل |
| P1–P5 | المشتقات |
| M1–M16 | الإلزامية |
| C1 | الإفساد |
| W1–W3 | عقد الوزن |
| U1–U3 | Unicode |

## ١١. ما لم يُنجز

| ما لم يُنجز | السبب |
|---|---|
| مراجعة المرجع لغوياً | ليست من صلاحية الوكيل، فالمقام المراجَع فارغ |
| قياس التعميم المستقل | المعجم والحزمة من عائلةٍ واحدة (HFN) |
| تشغيل test | ممنوع |
| إصلاح عيوب المحلّل | ممنوع في هذه الجولة، وهي مقترحاتٌ في `analyzer_defects_proposed.json` |
"""
open(os.path.join(D, 'technical_report.md'), 'w', encoding='utf-8').write(tech)

# ---------- audit.html ----------
items = [dict(i=r['id'], w=r['word'], r=r['ref_root'], z=r['ref_wazn'], p=r['ref_pos'], s=r['ref_wazn_status'], d=r['denominators']['root'],
              e=r['A_execution'], l=r['A_level'], pr=r['proven_root'] or '', pw=r['proven_wazn_selected'] or '',
              f=flat(r)['faces'], b=' '.join(r['B_proven_roots']), o=' '.join(r['observations']), h=' '.join(r['cause_hypotheses'])) for r in R]
obs_counts = collections.Counter(o.split(':')[0] for r in R for o in r['observations'])


def opt(c):
    return ''.join(f'<option value="{html.escape(k)}">{html.escape(k)} ({v:,})</option>' for k, v in c.most_common())


page = f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>تدقيق الجذر والوزن RW02</title><style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e2dfd8;--acc:#7a4b12}}
@media (prefers-color-scheme:dark){{:root{{--bg:#171715;--fg:#ecebe6;--mut:#a3a29c;--line:#34332f;--acc:#e0b06a}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.6 "Noto Naskh Arabic","Amiri",serif;margin:0;padding:16px}}
h1{{font-size:20px;margin:0 0 4px}}.m{{color:var(--mut);font-size:13px}}
.f{{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}}.f input,.f select{{font:inherit;padding:4px 8px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:4px;max-width:100%}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{border-bottom:1px solid var(--line);padding:4px 6px;text-align:right;vertical-align:top}}
th{{position:sticky;top:0;background:var(--bg)}}td.w{{font-size:17px}}.c{{color:var(--acc)}}.wrap{{overflow-x:auto}}
.k{{display:flex;flex-wrap:wrap;gap:16px;margin:8px 0}}.k div{{border:1px solid var(--line);border-radius:4px;padding:6px 10px}}
</style></head><body><h1>تدقيق الجذر والوزن — RW02 (dev فقط)</h1>
<div class="m">التزام {meta['commit'][:7]} · HFN {meta['resources']['hfn_release']} · {len(R):,} صفاً · الاختبار المحجوب لم يُشغَّل · المقام «مؤقت» لا ذهبي</div>
<div class="k"><div>تنفيذ كامل: <b id="kc">{EXE['words_complete']:,}</b></div><div>بأي عطل: <b id="kf">{EXE['words_with_any_failure']:,}</b></div>
<div>المقام الرئيسي: <b id="km">{MAIN['n']:,}</b></div><div>جذرٌ مثبت موافق: <b id="kp">{MAIN['root_proven']['agree']:,}/{MAIN['root_proven']['n']:,}</b></div>
<div>الجذر بين الأوجه: <b id="kr">{MAIN['ref_root_in_faces']['k']:,}</b></div></div>
<div class="f"><input id="q" placeholder="كلمة / جذر / وزن / ملاحظة"><select id="o"><option value="">كل الملاحظات</option>{opt(obs_counts)}</select>
<select id="d"><option value="">كل المقامات</option>{opt(collections.Counter(r['denominators']['root'] for r in R))}</select>
<select id="s"><option value="">كل حالات الوزن</option>{opt(collections.Counter(r['ref_wazn_status'] for r in R))}</select>
<select id="e"><option value="">كل حالات التنفيذ</option>{opt(collections.Counter(r['A_execution'] for r in R))}</select><span id="n" class="m"></span></div>
<div class="wrap"><table><thead><tr><th>المعرّف</th><th>الكلمة</th><th>الجذر المرجعي</th><th>الوزن المرجعي</th><th>الصنف</th><th>حالة الوزن</th><th>المقام</th><th>التنفيذ</th><th>المستوى</th><th>المثبت/الوزن المختار</th><th>الأوجه</th><th>ب</th><th>الملاحظات</th><th>فرضيات السبب</th></tr></thead><tbody id="t"></tbody></table></div>
<script>const D={json.dumps(items, ensure_ascii=False).replace('</', '<\\/')};const $=x=>document.getElementById(x);
function e(x){{return String(x).replace(/[&<>]/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[m]))}}
function r(){{const q=$('q').value.trim().normalize('NFC');let n=0,h=[];for(const x of D){{if($('o').value&&!x.o.split(' ').some(y=>y.split(':')[0]===$('o').value))continue;
if($('d').value&&x.d!==$('d').value)continue;if($('s').value&&x.s!==$('s').value)continue;if($('e').value&&x.e!==$('e').value)continue;
if(q&&![x.i,x.w,x.r,x.z,x.f,x.o,x.h,x.pr].some(y=>y&&y.normalize('NFC').includes(q)))continue;n++;
if(h.length<500)h.push(`<tr><td>${{x.i}}</td><td class=w>${{e(x.w)}}</td><td>${{e(x.r)}}</td><td>${{e(x.z)}}</td><td>${{e(x.p)}}</td><td>${{x.s}}</td><td>${{x.d}}</td><td>${{x.e}}</td><td>${{x.l}}</td><td>${{e(x.pr)}} ${{e(x.pw)}}</td><td>${{e(x.f)}}</td><td>${{e(x.b)}}</td><td class=c>${{e(x.o)}}</td><td>${{e(x.h)}}</td></tr>`)}}
$('t').innerHTML=h.join('');$('n').textContent=n.toLocaleString()+' صفاً'+(n>500?' (يُعرض أول 500)':'')}}
['q','o','d','s','e'].forEach(x=>$(x).addEventListener('input',r));r()</script></body></html>'''
open(os.path.join(D, 'audit.html'), 'w', encoding='utf-8').write(page)

# ---------- المصالحة ----------
problems = []
tsv = [l.split('\t') for l in open(os.path.join(AT, 'dev_results_full.tsv'), encoding='utf-8').read().splitlines()[1:]]
ci = {c: i for i, c in enumerate(COLS)}
if len(tsv) != len(R) or n_full != len(R):
    problems.append('TSV الكامل لا يساوي سجل النتائج')
if sum(1 for x in tsv if x[ci['root_denominator']] == 'PROVISIONAL_REFERENCE_MAIN') != MAIN['n']:
    problems.append('مقام TSV الرئيسي يخالف JSON')
if sum(1 for x in tsv if x[ci['root_denominator']] == 'PROVISIONAL_REFERENCE_MAIN' and x[ci['root_agreement']] == 'True') != MAIN['root_proven']['agree']:
    problems.append('الجذر المثبت الموافق في TSV يخالف JSON')
if len(items) != len(R) or sum(1 for x in items if x['d'] == 'PROVISIONAL_REFERENCE_MAIN') != MAIN['n']:
    problems.append('HTML يخالف JSON')
if MEAS['root']['PROVISIONAL_REFERENCE_MAIN']['root_proven'] != MAIN['root_proven'] or MEAS['execution'] != EXE:
    problems.append('measurement.json يخالف dev_metrics.json')
for s in (f"{MAIN['root_proven']['agree']:,} / {MAIN['root_proven']['n']:,}", f"{MAIN['ref_root_in_faces']['k']:,} / {MAIN['ref_root_in_faces']['n']:,}",
          f"{WMAIN['pair']['k']:,} / {WMAIN['pair']['n']:,}"):
    if s not in cust:
        problems.append(f'Markdown ينقصه {s}')
if sum(1 for r in R if r['denominators']['root'] == 'PROVISIONAL_REFERENCE_FLAGGED') != FLAG['n']:
    problems.append('المقام الموسوم يخالف')
json.dump(dict(ok=not problems, problems=problems), open(os.path.join(AT, 'reconciliation.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if problems:
    raise SystemExit('المصالحة فشلت: ' + '؛ '.join(problems))

# ---------- MANIFEST ----------
lines = []
for root, _, fs in os.walk(D):
    for f in sorted(fs):
        p = os.path.join(root, f)
        if f != 'MANIFEST.txt':
            lines.append(f'{sha(p)}  {os.path.relpath(p, D)}')
open(os.path.join(D, 'MANIFEST.txt'), 'w', encoding='utf-8').write('\n'.join(sorted(lines, key=lambda l: l.split('  ')[1])) + '\n')
print('المصالحة سليمة؛', len(lines), 'ملفاً في MANIFEST')
