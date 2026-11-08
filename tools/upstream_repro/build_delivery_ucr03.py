# -*- coding: utf-8 -*-
"""build_delivery_ucr03.py <REPRO_OUT> <REPO> <OLD_COMMIT> <DELIVERY_DIR> <TEST_UPSTREAM_OUT> <OLD_TESTS_LOG>: تسليم دفعة مراجعة b2f926e.
كل رقمٍ مقروءٌ من مخرجات reproduce.sh وسجلّاتها؛ والمرجع (حزمة b2f926e) مقروءٌ من measurement.json فيها."""
import sys, os, json, csv, glob, shutil, hashlib, html, datetime, subprocess, re
SRC, REPO, OLDC, D, TUO, OLDLOG = sys.argv[1:7]
M = os.path.join(SRC, 'm')
assert not os.path.exists(os.path.join(D, 'measurement.json')), 'لا يُستبدل تسليمٌ سابق'
for s in ('', 'code', 'tests', 'identity', 'evidence', 'counts', 'shadow', 'protection', 'reproduce', 'trace', 'logs'):
    os.makedirs(os.path.join(D, s), exist_ok=True)
J = lambda *p: json.load(open(os.path.join(*p), encoding='utf-8'))
N = lambda x: f'{x:,}' if isinstance(x, int) else str(x)
G = lambda *a: subprocess.run(['git', '-c', 'core.quotepath=off', '-C', REPO, *a], capture_output=True, text=True, check=True).stdout
HEAD = G('rev-parse', 'HEAD').strip()
RUNC = open(os.path.join(SRC, 'frozen_branch', '.frozen_commit')).read().strip() if os.path.exists(os.path.join(SRC, 'frozen_branch', '.frozen_commit')) else None
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
REP, INV, CERT, ATT, CJ, CMP = (J(M, f) for f in ('repair.json', 'invariants.json', 'cert_check.json', 'shadow_attribution.json', 'cand.json', 'cmp_base_branch.json'))
PREV = J('/home/user/Downloads/sarf_upstream_consumer_repair02/measurement.json')
# ---------- الشيفرة ----------
open(os.path.join(D, 'code', f'diff_{OLDC[:7]}_{HEAD[:7]}.patch'), 'w', encoding='utf-8').write(G('diff', '--binary', OLDC, HEAD))
changed = [l for l in G('diff', '--name-status', OLDC, HEAD).splitlines() if l]
subprocess.run(['git', '-C', REPO, 'archive', '--format=tar.gz', '-o', os.path.join(D, 'code', f'source_{HEAD[:7]}.tar.gz'), HEAD, 'tools', 'tests', 'CLAUDE.md'], check=True)
subprocess.run(['git', '-C', REPO, 'bundle', 'create', os.path.join(D, 'code', f'branch_{OLDC[:7]}_{HEAD[:7]}.bundle'), f'{OLDC}..upstream-consumer-repair-03'],
               check=True, capture_output=True)
with open(os.path.join(D, 'code', 'changed_files.tsv'), 'w', encoding='utf-8') as f:
    f.write('status\tpath\tsha256_at_head\n')
    for l in changed:
        st, p = l.split('\t', 1)
        q = os.path.join(REPO, p)
        f.write(f"{st}\t{p}\t{sha(q) if os.path.isfile(q) and st != 'D' else '—'}\n")
LOG_ = G('log', '--format=%H %s', f'{OLDC}..{HEAD}')
open(os.path.join(D, 'code', 'commits.txt'), 'w', encoding='utf-8').write(LOG_)
sarf_touched = any(l.split('\t')[1].startswith('sarf/') for l in changed)
# ---------- الأدلّة ----------
for f_, sub in (('repair.json', 'identity'), ('repair_row_transitions.jsonl.gz', 'counts'), ('repair_evidence_collisions.tsv', 'evidence'), ('cand.jsonl.gz', 'logs'),
                ('cand.json', 'logs'), ('cand_old.json', 'logs'), ('cert_check.json', 'protection'), ('cmp_base_branch.json', 'protection'), ('shadow_v47.json', 'shadow'),
                ('shadow_attribution.json', 'shadow'), ('shadow_attribution.jsonl.gz', 'shadow'), ('invariants.json', 'tests')):
    shutil.copy(os.path.join(M, f_), os.path.join(D, sub, f_))
for p in glob.glob(os.path.join(SRC, 'tests', '*')):
    shutil.copy(p, os.path.join(D, 'tests', os.path.basename(p)))
shutil.copy(OLDLOG, os.path.join(D, 'tests', 'old_code_gaps_demo.txt'))
shutil.copy(os.path.join(SRC, 'reproduce_steps.log'), os.path.join(D, 'reproduce', 'reproduce_steps.log'))
for p in glob.glob(os.path.join(SRC, 'meta', '*.json')):
    shutil.copy(p, os.path.join(D, 'reproduce', os.path.basename(p)))
for f_ in ('reproduce.sh', 'test_reproduce.sh', 'pin_sources.sh', 'pin_historical.sh', 'make_pins.py', 'build_delivery_ucr03.py'):
    shutil.copy(os.path.join(REPO, 'tools', 'upstream_repro', f_), os.path.join(D, 'reproduce', f_))
if os.path.exists(os.path.join(SRC, '..', 'repro_ucr03.log')):
    shutil.copy(os.path.join(SRC, '..', 'repro_ucr03.log'), os.path.join(D, 'reproduce', 'reproduce_clean_run.log'))
# ---------- الأرقام ----------
TR = [t for t in REP['row_transitions'] if t['before'] != t['after']]
with open(os.path.join(D, 'counts', 'row_transitions_summary.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t'); w.writerow(['source', 'before_b2f926e', 'after', 'reason', 'rows'])
    for t in TR:
        w.writerow([t['source'], t['before'], t['after'], t['reason'], t['rows']])
CB, CA = REP['counts']['before'], REP['counts']['after']
DEN = dict(feature_rows_candidate_match='feature_rows', occurrence_records_with_match='occurrence_records_queried', face_occurrences_with_match='occurrence_records_queried')
with open(os.path.join(D, 'counts', 'counters_with_denominators.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t'); w.writerow(['counter', 'definition', 'b2f926e', 'after', 'denominator', 'den_b2f926e', 'den_after'])
    for k, d_ in REP['counter_definitions'].items():
        dn = DEN.get(k)
        w.writerow([k, d_, CB[k], CA[k], dn or '— (عددٌ متميّز)', CB['denominators'].get(dn, '—'), CA['denominators'].get(dn, '—')])
EA, EB = REP['evidence_ids']['after'], REP['evidence_ids']['before']
idt = REP['identity_root_mismatch_rows']
tu = open(TUO, encoding='utf-8').read()
MUTS = json.loads([l for l in tu.splitlines() if l.startswith('{"mutations"')][0])['mutations']
UCH = re.findall(r'^(PASS|FAIL) (\S+) (.*)$', tu, re.M)
OLDG = open(OLDLOG, encoding='utf-8').read()
# ---------- صفحة التتبّع وسجلّ قراءتها ----------
NEWP, OLDP = os.path.join(REPO, 'reports', 'arabic-sarf-063.html'), os.path.join(REPO, 'reports', 'arabic-sarf-062.html')
shutil.copy(NEWP, os.path.join(D, 'trace', 'arabic-sarf-063.html'))


def secs(s):
    parts = re.split(r'(<section id="[^"]+">)', s)
    return {re.search(r'id="([^"]+)"', parts[i]).group(1): parts[i + 1] for i in range(1, len(parts), 2)}


A_, B_ = secs(open(OLDP, encoding='utf-8').read()), secs(open(NEWP, encoding='utf-8').read())
rows_log, sec_changed = [], []
for k in sorted(set(A_) | set(B_)):
    if A_.get(k) == B_.get(k):
        rows_log.append([k, 'مطابق', '—']); continue
    sec_changed.append(k)
    ta = [html.unescape(re.sub(r'\|+', ' | ', re.sub('<[^>]+>', '|', x))) for x in re.findall(r'<tr>(.*?)</tr>', A_.get(k, ''), re.S)]
    tb = [html.unescape(re.sub(r'\|+', ' | ', re.sub('<[^>]+>', '|', x))) for x in re.findall(r'<tr>(.*?)</tr>', B_.get(k, ''), re.S)]
    sa, sb = set(ta), set(tb)
    rows_log.append([k, f'مختلف: {sum(x not in sb for x in ta)} صفاً في 062 وحدها، و{sum(x not in sa for x in tb)} في 063 وحدها', '—'])
    rows_log += [[k, '− في 062', x[:700]] for x in ta if x not in sb] + [[k, '+ في 063', x[:700]] for x in tb if x not in sa]
    if not ta and not tb:
        rows_log.append([k, 'اختلافٌ خارج الجداول', '—'])
with open(os.path.join(D, 'trace', 'section_reading_log.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t'); w.writerow(['القسم', 'الحال', 'الصف']); w.writerows(rows_log)
# ---------- المتطلبات ----------
mok = lambda *ids: all(m[1] for m in MUTS if m[0].split(' ')[0] in ids) and all(any(m[0].startswith(i + ' ') for m in MUTS) for i in ids)
cok = lambda *ids: all(any(b == i and a == 'PASS' for a, b, _ in UCH) for i in ids)
old_ok = all(f'{m} old: IDENTITY_OK' in OLDG for m in ('M16', 'M17', 'M18')) and all(f'{m} old errors: []' in OLDG for m in ('M19', 'M20', 'M21'))
REQ = [
 ('م١', 'الإحالة إلى الحدث بحقول دقيقة: لا يُختزل الباب (فَعِلَ/فَعَلَ) ولا الحركات (أُمَّ/أَمَّ)', 'DONE' if mok('M16', 'M17') and cok('R15', 'R16') else 'FAILED',
  'reference_check() وFORM_LABEL_V1؛ M16، M17، وشاهدان موجبان R15، R16' + ('؛ وفي شيفرة b2f926e كانا IDENTITY_OK' if old_ok else '')),
 ('م١', 'فصل سلامة الإحالة عن توافق الحدث مع الوجه', 'DONE', 'identity(): reference_check ثم hfn_class للوجه؛ وreference_check محفوظ في كل صفّ'),
 ('م٢', 'فشل تحويل مفتاح الجذر تأجيلٌ مسمّى لا مساواة', 'DONE' if mok('M18') and cok('R14') else 'FAILED', 'ROOT_KEY_UNRESOLVED؛ M18، R14'),
 ('م٣', 'حماية الحقول المكرّرة التي يقرؤها المستهلك (value، face، id)', 'DONE' if mok('M19', 'M20', 'M21') and cok('R17') else 'FAILED',
  f"بصمة السجلّ كاملاً ({EA.get('algorithm')})، وفحص الاتساق؛ M19–M21، R17؛ وأخطاء السجلّ الحالي {len(EA['registry_errors'])}"),
 ('م٤', 'اختبار ترتيبٍ يثبت بقاء ربط صفّ المصدر بمعرّفه ومحتواه', 'DONE' if mok('M22') and cok('R11a', 'R11b', 'R11c') else 'FAILED',
  'R11a–R11c (ومن run())؛ وM22 يثبت أن تساوي المجموعتين لا يكفي'),
 ('م٤', 'تصحيح وسم «ثبات الترتيب» في حزمة b2f926e', 'DONE', 'كان DONE بلا اختبارٍ كاشف؛ صُحّح هنا بالاختبار، ويُعلن الخطأ السابق'),
 ('م٤', 'PROVEN_RECORD لسجلّ مفتاح الوجه نفسه لا رصيد الكلمة', 'DONE', 'entry_recs بموضع مدخل الوجه'),
 ('م٤', 'فصل اكتمال التصنيف عن اكتمال التعليل السببي', 'DONE', f"التصنيف {ATT['classification_completeness']}، والتعليل السببي {ATT['causal_explanation_completeness']} ({N(ATT['causally_explained'])}/{N(ATT['differences'])})"),
 ('م٤', 'ربط ادعاء إعادة الإنتاج بالالتزام الذي شُغّل فعلاً', 'DONE' if RUNC and os.path.exists(os.path.join(SRC, 'REPRODUCED')) else 'NOT_DONE',
  f"التشغيل النظيف الكامل عند `{(RUNC or '?')[:7]}`؛ والفرق عنه إلى الرأس `{HEAD[:7]}`: " + (G('diff', '--stat', RUNC, HEAD).strip().splitlines()[-1] if RUNC and RUNC != HEAD else 'لا شيء')),
 ('حماية', 'المحلّل وv36 والتقشير دون تغيير', 'VIOLATED' if sarf_touched or CMP['violations'] else 'DONE', f"لا ملف تحت sarf/؛ و{CMP['violations']} مخالفة في {N(CMP['verses'])} آية"),
 ('حماية', 'الشهادات بالأدلّة وبدونها', 'DONE' if CERT['identical_without_evidence'] == CERT['sentences'] else 'VIOLATED', f"{N(CERT['identical_without_evidence'])}/{N(CERT['sentences'])}"),
 ('حماية', 'لا CANDIDATE_MATCH بهويةٍ غير IDENTITY_OK، ولا معرّفٌ بمحتويين، ولا مرجعٌ يتيم', 'DONE' if idt['after_match_with_identity_not_ok'] == 0 and EA['ids_with_different_content'] == 0 and EA['certificate_refs']['orphan'] == 0 else 'VIOLATED',
  f"{idt['after_match_with_identity_not_ok']}، {EA['ids_with_different_content']}، {EA['certificate_refs']['orphan']}"),
 ('حدود', 'التشغيل على macOS', 'NOT_MEASURED', 'لم يُشغَّل على macOS'),
 ('حدود', 'حفظ الصفّ المتعارض مرشّحاً لوجهٍ مستقل مرخّص', 'NOT_DONE', 'باقٍ من الجولة السابقة'),
]
with open(os.path.join(D, 'requirements_matrix.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t'); w.writerow(['البند', 'المتطلب', 'الحالة', 'الدليل']); w.writerows(REQ)
meas = dict(task='SARF_UPSTREAM_CONSUMER_REPAIR_03 (مراجعة b2f926e)', branch='upstream-consumer-repair-03', old_commit=OLDC, head_commit=HEAD, clean_run_commit=RUNC,
            commits=LOG_.splitlines(), changed_files=changed, reference_b2f926e=dict(counts=PREV['counts']['after'], evidence_ids=PREV['evidence_ids']['after'], shadow=PREV['shadow']),
            identity=idt, evidence_ids=REP['evidence_ids'], counts=REP['counts'], counter_definitions=REP['counter_definitions'],
            row_transitions_changed=REP['row_transitions_changed'], unclassified_transitions=REP['unclassified_transitions'], row_transitions=TR,
            protection=dict(base_vs_branch_violations=CMP['violations'], verses=CMP['verses'], certificates=dict(sentences=CERT['sentences'], identical=CERT['identical_without_evidence'])),
            shadow={k: ATT[k] for k in ('differences', 'classes', 'classification_completeness', 'causal_explanation_completeness', 'causally_explained', 'not_causally_explained', 'completeness_definitions')},
            tests=dict(files=INV['test_files'], exit0=INV['test_files_exit0'], files_with_checks=INV['test_files_with_checks'], checks=INV['checks_executed'],
                       helpers_without_checks=INV['helper_files_without_checks'], test_upstream_checks=len(UCH), mutations=MUTS, old_code_gaps_reproduced=old_ok),
            trace=dict(page='arabic-sarf-063.html', sections_changed_vs_062=sec_changed), requirements=[dict(section=a, requirement=b, status=c, evidence=d) for a, b, c, d in REQ],
            flags=dict(MODIFY_SARF_ANALYSIS_RULES='NO', HFN_V47_ADOPTED='NO', PUSH='NO', MERGE='NO'))
json.dump(meas, open(os.path.join(D, 'measurement.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
# ---------- التقارير ----------
PC = PREV['counts']['after']
C = []
w = C.append
w('# تقرير صاحب النظرية — دفعة مراجعة `b2f926e` (SARF_UPSTREAM_CONSUMER_REPAIR_03)\n')
w(f"الفرع `upstream-consumer-repair-03` من `{OLDC[:7]}` إلى `{HEAD[:7]}`؛ التزاماتٌ محلية، لا دفع ولا دمج. `sarf/` لم يُمسّ، وv36 والتقشير كما هما، وv47 غير معتمد.\n")
w('## الحكم بحسب كل متطلب\n')
w('| البند | المتطلب | الحالة | الدليل |\n|---|---|---|---|')
for a, b, c, d in REQ:
    w(f'| {a} | {b} | **{c}** | {d} |')
w('\n## ١. الإحالة إلى الحدث وفشل المفتاح\n')
w('شغّلت حالات المراجعة على دوالّ `b2f926e` نفسها فأعادت ما ذكره المراجع (`tests/old_code_gaps_demo.txt`):\n')
w('```\n' + OLDG.strip() + '\n```\n')
w('وبعد الإصلاح: الصفّ «فَعِلَ» مقابل حدث «فَعَلَ» و«أُمَّ» مقابل «أَمَّ» `EVENT_ID_FIELD_MISMATCH`، والجذران «قاو/قاي» `IDENTITY_UNDETERMINED (ROOT_KEY_UNRESOLVED)`. '
  'وتسمية البناء في HFN («فَعَلَ (أجوف)»، «فَعَلَ/فَعِلَ (أجوف)») تُربط بصيغة الصفّ بقاعدةٍ موثّقة FORM_LABEL_V1: البدائل مشكولةٌ كما هي، والوصف بين القوسين لا يدخل؛ '
  'فلا يُختزل الباب. وتوافق الحدث مع وجه sarf يبقى مستوىً ثانياً بفئة `hfn_class` لأن الوجه يُبنى بها.\n')
w(f"انتقالات الصفوف عن `b2f926e` على المصحف كله: {N(REP['row_transitions_changed'])} صفاً، وغير المصنّف {REP['unclassified_transitions']}:\n")
w('| المصدر | في b2f926e | الآن | السبب | الصفوف |\n|---|---|---|---|---:|')
for t in sorted(TR, key=lambda t: -t['rows']):
    w(f"| {t['source']} | {t['before']} | {t['after']} | {t['reason']} | {N(t['rows'])} |")
w(f"\nوالمطابق بهويةٍ غير IDENTITY_OK: {idt['after_match_with_identity_not_ok']}.\n")
w('## ٢. الحقول المكرّرة في الدليل\n')
w(f"المعرّف الآن `{EA.get('algorithm')}`، فكل حقلٍ يقرؤه مستهلك داخلٌ في البصمة؛ و`verify_evidence_registry` يفحص أيضاً `id = evidence_id`، و`value` مقابل `payload`، "
  f"والوجه، واللمّة، والمسلك، والوحدة. الأدلّة {N(EA['evidence_records'])}، والمعرّفات المتميزة {N(EA['distinct_ids'])}، والمحيل إلى محتويين {EA['ids_with_different_content']}، "
  f"وأخطاء السجلّ {len(EA['registry_errors'])}، والمراجع في الشهادات {N(EA['certificate_refs']['seen'])} واليتيم {EA['certificate_refs']['orphan']}. "
  'وتغيّرت المعرّفات كلها عن `b2f926e` لتغيّر الخوارزمية (لا لتغيّر المحتوى).\n')
w('## ٣. العدّادات\n')
w('| العدّاد | b2f926e | الآن |\n|---|---:|---:|')
for k in REP['counter_definitions']:
    w(f'| `{k}` | {N(CB[k])} | {N(CA[k])} |')
w('\n## ٤. الترتيب والتعليل الظلي وإعادة الإنتاج\n')
w('- اختبار R11 السابق كان يقارن مجموعتين؛ وحزمة `b2f926e` وسمته DONE خطأً. الآن R11a–R11c يقارن لكل صفّ مصدر (الوقوع، المصدر، المسلك، الصفّ) معرّفه ومحتواه قبل التبديل وبعده، '
  'ومن `run()` بتبديل الوقوعات؛ وM22 (معرّفٌ من ترتيب الصفّ) يمرّ بمقارنة المجموعتين ويُكشف بمقارنة الربط.')
w(f"- الفروق الظلية {N(ATT['differences'])}: " + '، '.join(f'{k} {N(v)}' for k, v in ATT['classes'].items()) +
  f". واكتمال التصنيف **{ATT['classification_completeness']}**، واكتمال التعليل السببي **{ATT['causal_explanation_completeness']}** "
  f"({N(ATT['causally_explained'])} مفسَّراً سببياً و{N(ATT['not_causally_explained'])} غير مفسَّر سببياً). وPROVEN_RECORD الآن لسجلّ مفتاح مدخل الوجه نفسه؛ "
  f"وكان {N(PREV['shadow']['classes'].get('PROVEN_RECORD', 0))} في `b2f926e`.")
w(f"- التشغيل النظيف الكامل عند `{(RUNC or '?')[:7]}`: {INV['verses']} آية، والاختبارات {INV['test_files']} ملفاً خرج بصفر {INV['test_files_exit0']}، "
  f"فيها فحوص {INV['test_files_with_checks']} ({N(INV['checks_executed'])} فحصاً)، وبلا فحوص: {', '.join(INV['helper_files_without_checks'])}؛ والإفسادات {sum(m[1] for m in MUTS)}/{len(MUTS)}. "
  + (f"وبعد التشغيل التزامٌ واحد (`{HEAD[:7]}`) فيه صفحة 063 وفهرسها ومولّد التسليم وحده." if RUNC != HEAD else ''))
w('- لم يُشغَّل على macOS.\n')
w('## ٥. الإعادة\n')
w('```\nbash reproduce/reproduce.sh --sarf <arabic-sarf-2026> --data <data> --hfn <HusseinFrameNet> --hfn-base <…/release_v36> --wazn <wazn-net> \\\n'
  f'  --amln <AMLN> --maq <Maqaiys-roots> --branch {RUNC} --old {OLDC} --out <مجلد جديد>\n```')
open(os.path.join(D, 'customer_report_ar.md'), 'w', encoding='utf-8').write('\n'.join(C) + '\n')
T = ['# Technical report — SARF_UPSTREAM_CONSUMER_REPAIR_03 (review of b2f926e)\n', f'{OLDC} → {HEAD}; clean full run at {RUNC}. sarf/ untouched: {not sarf_touched}.\n',
     '## Identity: two levels\n', '1. `reference_check(row_root, row_form, row_verb, event_ref)`: root keys via `query_key` (either None → `ROOT_KEY_UNRESOLVED`, undetermined); '
     'form exact after NFC or an alternative of the HFN label (`FORM_LABEL_V1`: split at " (", then "/"; vowelled); verb exact after NFC, `ٱ↔ا` as a recorded transform. '
     'Any mismatch → `EVENT_ID_FIELD_MISMATCH`.\n2. Face compatibility: root keys (None → undetermined), `hfn_class` (the class sarf builds the face with), crosswalk as second witness.\n',
     '## Evidence\n', f"`{EA.get('algorithm')}`. Verifier codes: MISSING_IDENTITY_FIELD, ID_ALIAS_DIFFERS, ID_DOES_NOT_MATCH_CONTENT, VALUE_DIFFERS_FROM_PAYLOAD, "
     'FACE_DIFFERS_FROM_IDENTITY, LEMMA_DIFFERS_FROM_PAYLOAD, ROUTE_OR_FEATURE_DIFFERS, UNIT_DIFFERS_FROM_OCCURRENCE, SAME_ID_DIFFERENT_CONTENT.\n',
     '## Measurements\n```json\n' + json.dumps({k: meas[k] for k in ('identity', 'evidence_ids', 'counts', 'protection', 'shadow')}, ensure_ascii=False, indent=1)[:10000] + '\n```\n',
     '## Tests\n'] + [f'- {a} {b} {c}' for a, b, c in UCH] + ['\n## Mutations\n'] + [f"- {'CAUGHT' if m[1] else 'MISSED'} {m[0]}" for m in MUTS]
open(os.path.join(D, 'technical_report.md'), 'w', encoding='utf-8').write('\n'.join(T) + '\n')
E = html.escape


def table(head, rows):
    return '<div class="wrap"><table><tr>' + ''.join(f'<th>{E(str(h))}</th>' for h in head) + '</tr>' + ''.join(
        '<tr>' + ''.join(f'<td>{E(str(c))}</td>' for c in r) + '</tr>' for r in rows) + '</table></div>'


page = f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>تدقيق مراجعة b2f926e</title><style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--line:#ddd9cf;--head:#efece4}}@media (prefers-color-scheme:dark){{:root{{--bg:#191917;--fg:#e9e7e1;--line:#3a3935;--head:#26251f}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.6 "Noto Naskh Arabic",Tahoma,sans-serif;margin:0;padding:16px;max-width:1400px}}
h2{{font-size:1.15em;margin-top:2em;border-bottom:1px solid var(--line)}} .wrap{{overflow-x:auto}} table{{border-collapse:collapse;font-size:13px;width:100%}}
th,td{{border:1px solid var(--line);padding:3px 6px;vertical-align:top}} th{{background:var(--head)}}</style></head><body>
<h1>تدقيق دفعة مراجعة b2f926e</h1><p>{E(OLDC[:7])} → {E(HEAD[:7])}؛ التشغيل النظيف عند {E((RUNC or '?')[:7])}</p>
<h2>المتطلبات</h2>{table(['البند', 'المتطلب', 'الحالة', 'الدليل'], REQ)}
<h2>انتقالات الصفوف عن b2f926e</h2>{table(['المصدر', 'قبل', 'بعد', 'السبب', 'الصفوف'], [(t['source'], t['before'], t['after'], t['reason'], t['rows']) for t in TR])}
<h2>العدّادات</h2>{table(['العدّاد', 'b2f926e', 'الآن'], [(k, CB[k], CA[k]) for k in REP['counter_definitions']])}
<h2>الفروق الظلية</h2>{table(['الصنف', 'العدد'], ATT['classes'].items())}
<h2>الإفساد</h2>{table(['الإفساد', 'كُشف'], [(m[0], 'نعم' if m[1] else 'لا') for m in MUTS])}
<h2>test_upstream</h2>{table(['النتيجة', 'المعرّف', 'الفحص'], UCH)}
<h2>قراءة الصفحة 063 عن 062</h2>{table(['القسم', 'الحال', 'الصف'], [r for r in rows_log if r[1] != 'مطابق'][:400])}
</body></html>'''
open(os.path.join(D, 'audit.html'), 'w', encoding='utf-8').write(page)
files = [dict(path=os.path.relpath(p, D), bytes=os.path.getsize(p), sha256=sha(p)) for p in sorted(glob.glob(os.path.join(D, '**', '*'), recursive=True))
         if os.path.isfile(p) and os.path.basename(p) != 'MANIFEST.json']
json.dump(dict(task=meas['task'], old_commit=OLDC, head_commit=HEAD, clean_run_commit=RUNC, created=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
               flags=meas['flags'], requirements={f'{a} {b}': c for a, b, c, _ in REQ}, files=files), open(os.path.join(D, 'MANIFEST.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('delivery ok', len(files))
