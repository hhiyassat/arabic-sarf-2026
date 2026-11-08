# -*- coding: utf-8 -*-
"""build_delivery_ucr02.py <REPRO_OUT> <REPO> <BASE_COMMIT> <DELIVERY_DIR> <REPRO_SELFTEST_LOG>: تسليم SARF_UPSTREAM_CONSUMER_REPAIR_02.
كل رقمٍ مقروءٌ من مخرجات reproduce.sh وسجلّاتها؛ ولا عددٌ مكتوبٌ باليد (والأعداد المرجعية للتدقيق السابق مسمّاةٌ مرجعاً لا نتيجة)."""
import sys, os, json, csv, glob, shutil, hashlib, html, datetime, subprocess, re
SRC, REPO, BASEC, D, SELFLOG = sys.argv[1:6]
M = os.path.join(SRC, 'm')
assert not os.path.exists(os.path.join(D, 'measurement.json')), 'لا يُستبدل تسليمٌ سابق'
for s in ('', 'code', 'tests', 'identity', 'evidence', 'counts', 'shadow', 'protection', 'reproduce', 'trace', 'logs'):
    os.makedirs(os.path.join(D, s), exist_ok=True)
J = lambda *p: json.load(open(os.path.join(*p), encoding='utf-8'))
N = lambda x: f'{x:,}' if isinstance(x, int) else str(x)
G = lambda *a: subprocess.run(['git', '-c', 'core.quotepath=off', '-C', REPO, *a], capture_output=True, text=True, check=True).stdout
HEAD = G('rev-parse', 'HEAD').strip()
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
REP, INV, CERT, ATT, CJ = J(M, 'repair.json'), J(M, 'invariants.json'), J(M, 'cert_check.json'), J(M, 'shadow_attribution.json'), J(M, 'cand.json')
CMP = J(M, 'cmp_base_branch.json')
AUDIT_REF = dict(identity={'hfn47': 989, 'sifat_v2': 969, 'transitivity_wasit_v5': 7}, ids_repeated=2657, ids_with_different_content=2386,
                 rows=15171, occurrence_records=6924, analysis_ids=2160, unattributed=3014)
# ---------- الشيفرة ----------
open(os.path.join(D, 'code', f'diff_{BASEC[:7]}_{HEAD[:7]}.patch'), 'w', encoding='utf-8').write(G('diff', '--binary', BASEC, HEAD))
changed = [l for l in G('diff', '--name-status', BASEC, HEAD).splitlines() if l]
subprocess.run(['git', '-C', REPO, 'archive', '--format=tar.gz', '-o', os.path.join(D, 'code', f'source_{HEAD[:7]}.tar.gz'), HEAD, 'tools', 'tests', 'CLAUDE.md'],
               check=True)
subprocess.run(['git', '-C', REPO, 'bundle', 'create', os.path.join(D, 'code', f'branch_{BASEC[:7]}_{HEAD[:7]}.bundle'), f'{BASEC}..upstream-consumer-repair-02'],
               check=True, capture_output=True)
LOG_ = G('log', '--format=%H %s', f'{BASEC}..{HEAD}')
with open(os.path.join(D, 'code', 'changed_files.tsv'), 'w', encoding='utf-8') as f:
    f.write('status\tpath\tsha256_at_head\n')
    for l in changed:
        st, p = l.split('\t', 1)
        q = os.path.join(REPO, p)
        f.write(f"{st}\t{p}\t{sha(q) if os.path.isfile(q) and st != 'D' else '—'}\n")
open(os.path.join(D, 'code', 'commits.txt'), 'w', encoding='utf-8').write(LOG_)
# ---------- الأدلّة ----------
CP = [('repair.json', 'identity'), ('repair_row_transitions.jsonl.gz', 'counts'), ('repair_evidence_collisions.tsv', 'evidence'),
      ('cand.jsonl.gz', 'logs'), ('cand.json', 'logs'), ('cand_old.json', 'logs'), ('cert_check.json', 'protection'), ('cmp_base_branch.json', 'protection'),
      ('shadow_v47.json', 'shadow'), ('shadow_attribution.json', 'shadow'), ('shadow_attribution.jsonl.gz', 'shadow'), ('invariants.json', 'tests')]
for f, sub in CP:
    shutil.copy(os.path.join(M, f), os.path.join(D, sub, f))
for p in glob.glob(os.path.join(SRC, 'tests', '*')):
    shutil.copy(p, os.path.join(D, 'tests', os.path.basename(p)))
shutil.copy(os.path.join(SRC, 'reproduce_steps.log'), os.path.join(D, 'reproduce', 'reproduce_steps.log'))
for p in glob.glob(os.path.join(SRC, 'meta', '*.json')):
    shutil.copy(p, os.path.join(D, 'reproduce', os.path.basename(p)))
shutil.copy(SELFLOG, os.path.join(D, 'reproduce', 'test_reproduce.log'))
for f in ('reproduce.sh', 'test_reproduce.sh', 'pin_sources.sh', 'pin_historical.sh', 'make_pins.py', 'build_delivery_ucr02.py'):
    shutil.copy(os.path.join(REPO, 'tools', 'upstream_repro', f), os.path.join(D, 'reproduce', f))
if os.path.exists(os.path.join(SRC, '..', 'repro_ucr02.log')):
    shutil.copy(os.path.join(SRC, '..', 'repro_ucr02.log'), os.path.join(D, 'reproduce', 'reproduce_clean_run.log'))
# ---------- الهوية قبل وبعد ----------
idb, ida = REP['identity_root_mismatch_rows']['before'], REP['identity_root_mismatch_rows']['after']
with open(os.path.join(D, 'identity', 'identity_before_after.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t')
    w.writerow(['source', 'audit_reference_rows', 'recomputed_before_rows', 'difference_vs_audit', 'after_rows', 'unit'])
    for k in sorted(set(AUDIT_REF['identity']) | set(idb) | set(ida)):
        ref = AUDIT_REF['identity'].get(k)
        w.writerow([k, ref if ref is not None else '—', idb.get(k, 0), (idb.get(k, 0) - ref) if ref is not None else '—', ida.get(k, 0),
                    'صفوف CANDIDATE_MATCH (لا كلمات)'])
TR = [t for t in REP['row_transitions'] if t['before'] != t['after']]
with open(os.path.join(D, 'counts', 'row_transitions_summary.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t'); w.writerow(['source', 'before', 'after', 'reason', 'rows'])
    for t in TR:
        w.writerow([t['source'], t['before'], t['after'], t['reason'], t['rows']])
CB, CA = REP['counts']['before'], REP['counts']['after']
DEN = dict(feature_rows_candidate_match='feature_rows', occurrence_records_with_match='occurrence_records_queried',
           face_occurrences_with_match='occurrence_records_queried')
with open(os.path.join(D, 'counts', 'counters_with_denominators.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t'); w.writerow(['counter', 'definition', 'before', 'after', 'denominator', 'denominator_before', 'denominator_after'])
    for k, d_ in REP['counter_definitions'].items():
        dn = DEN.get(k)
        w.writerow([k, d_, CB[k], CA[k], dn or '— (عددٌ متميّز بلا مقامٍ طبيعي)', CB['denominators'].get(dn, '—'), CA['denominators'].get(dn, '—')])
# ---------- الاختبارات ----------
tu = open(os.path.join(SRC, 'tests', 'test_upstream.out'), encoding='utf-8').read()
MUTS = json.loads([l for l in tu.splitlines() if l.startswith('{"mutations"')][0])['mutations']
UCH = re.findall(r'^(PASS|FAIL) (\S+) (.*)$', tu, re.M)
SELF = re.findall(r'^(PASS|FAIL) (R\d) (.*)$', open(SELFLOG, encoding='utf-8').read(), re.M)
# ---------- صفحة التتبّع وسجلّ قراءتها ----------
NEWP = sorted(glob.glob(os.path.join(REPO, 'reports', 'arabic-sarf-0*.html')))[-1]
OLDP = os.path.join(REPO, 'reports', 'arabic-sarf-061.html')
shutil.copy(NEWP, os.path.join(D, 'trace', os.path.basename(NEWP)))


def secs(s):
    parts = re.split(r'(<section id="[^"]+">)', s)
    return {re.search(r'id="([^"]+)"', parts[i]).group(1): parts[i + 1] for i in range(1, len(parts), 2)}


A_, B_ = secs(open(OLDP, encoding='utf-8').read()), secs(open(NEWP, encoding='utf-8').read())
rows_log, sec_changed = [], []
for k in sorted(set(A_) | set(B_)):
    if A_.get(k) == B_.get(k):
        rows_log.append([k, 'مطابق', '—'])
        continue
    sec_changed.append(k)
    ta = [re.sub(r'\|+', ' | ', re.sub('<[^>]+>', '|', x)) for x in re.findall(r'<tr>(.*?)</tr>', A_.get(k, ''), re.S)]
    tb = [re.sub(r'\|+', ' | ', re.sub('<[^>]+>', '|', x)) for x in re.findall(r'<tr>(.*?)</tr>', B_.get(k, ''), re.S)]
    sa, sb = set(ta), set(tb)
    rows_log.append([k, f'مختلف: {sum(x not in sb for x in ta)} صفاً في 061 وحدها، و{sum(x not in sa for x in tb)} في الجديدة وحدها', '—'])
    rows_log += [[k, '− في 061', html.unescape(x)[:700]] for x in ta if x not in sb]
    rows_log += [[k, '+ في الجديدة', html.unescape(x)[:700]] for x in tb if x not in sa]
    if not ta and not tb:
        rows_log.append([k, 'اختلافٌ خارج الجداول (الهوية/البصمة/الشرح)', '—'])
with open(os.path.join(D, 'trace', 'section_reading_log.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t'); w.writerow(['القسم', 'الحال', 'الصف']); w.writerows(rows_log)
# ---------- المتطلبات ----------
idok = REP['identity_root_mismatch_rows']['after_match_with_identity_not_ok'] == 0 and not ida
EA = REP['evidence_ids']['after']
evok = EA['ids_with_different_content'] == 0 and not EA['registry_errors']
orph = EA['certificate_refs']
sarf_touched = any(l.split('\t')[1].startswith('sarf/') for l in changed)
REQ = [
 ('§1', 'الأساس 72e17c4 مثبت وتعديلات المالك محفوظة، وفرعٌ معزول ونسخٌ مجمّدة', 'DONE', f'upstream-consumer-repair-02 من {BASEC[:7]}؛ لا تعديل غير ملتزم'),
 ('§1', 'لا مساس بـsarf/ ولا حارس HFN ولا التقشير', 'VIOLATED' if sarf_touched else 'DONE', 'code/changed_files.tsv'),
 ('§1', 'الشيفرة والاختبارات والأدوات: فرقٌ كامل وأرشيف وحزمة git ببصماتها', 'DONE', 'code/ وMANIFEST.json'),
 ('§2', 'إعادة حساب الأعداد المرجعية وإعلان الفرق', 'DONE', '؛ '.join(f"{k}: {idb.get(k, 0)} (المرجع {v})" for k, v in AUDIT_REF['identity'].items())),
 ('§2', 'الشاهد الحاكم يَقُولُ 2:8', 'DONE' if any(b == 'R01' and a == 'PASS' for a, b, _ in UCH) else 'FAILED', 'test_upstream R01'),
 ('§2', 'فحص الجذر والبناء واللمّة والحدث والسحب والمسلك في كل العائلات', 'DONE', 'identity()؛ R02–R06'),
 ('§2', 'LEXEME_IDENTITY_CONFLICT محفوظاً بلا دليل، والنقص تأجيل', 'DONE', 'R01، R04؛ counts/row_transitions_summary.tsv'),
 ('§2', 'حفظ الصفّ مرشّحاً لوجهٍ مستقلّ موجودٍ مرخّص', 'NOT_DONE', 'لم يُبحث عن وجهٍ بديلٍ مرخّص للوقوع؛ الصفّ محفوظ بحالته وسببه، ولا يُنشأ وجه'),
 ('§3', 'صفر معرّفٍ بمحتويين، وصفر مرجعٍ يتيم أو ملتبس، وثبات الهوية بتبديل الترتيب', 'DONE' if evok and orph.get('orphan') == 0 else 'PARTIAL',
  f"تصادم {EA['ids_with_different_content']}، أخطاء السجلّ {len(EA['registry_errors'])}، يتيم {orph.get('orphan')} من {orph.get('seen')} مرجعاً في الشهادات"),
 ('§3', 'تحديث المراجع في الشهادات والصفحة معاً', 'DONE', 'external_evidence_ids والصفحة 14ج بالمعرّف نفسه'),
 ('§4', 'وحدات العدّ منفصلة بمقاماتها وتعريفها', 'DONE', 'counts/counters_with_denominators.tsv'),
 ('§5', 'تعليل كل فرقٍ ظلي، وغير المحسوم معلن', 'PARTIAL' if ATT['classes'].get('UNRESOLVED') else 'DONE',
  f"UNRESOLVED {ATT['classes'].get('UNRESOLVED')} من {N(ATT['differences'])}؛ والاكتمال {ATT['completeness']}"),
 ('§6', 'المسحوب في بيئةٍ سليمة وبالحقن بعد التحقّق، ومنافذ الفهرس والعلاقات والذاكرة', 'DONE', 'R07، R08، R09؛ وM05 باقٍ'),
 ('§6', 'الإفسادات الستة الجديدة', 'DONE' if all(m[1] for m in MUTS) else 'PARTIAL', ' '.join(m[0].split(' ')[0] for m in MUTS if m[0][:3] in ('M10', 'M11', 'M12', 'M13', 'M14', 'M15'))),
 ('§7', 'reproduce.sh محمول: PID، رفض الناقص والمكرّر والمختلط، مهلة محمولة، مصفوفات، مسافات، عدّ الآيات', 'DONE' if SELF and all(a == 'PASS' for a, _, _ in SELF) else 'PARTIAL',
  'test_reproduce: ' + '، '.join(f'{b} {a}' for a, b, _ in SELF)),
 ('§7', 'التشغيل على macOS', 'NOT_MEASURED', 'لا يعتمد على GNU (bash 3.2، بلا timeout ولا mapfile)، ولم يُشغَّل على جهاز macOS في هذه البيئة'),
 ('§7', 'الملفات الخارجة بصفر منفصلة عن الفحوص المنفّذة', 'DONE', f"{INV['test_files_exit0']}/{INV['test_files']} ملفاً بصفر؛ {INV['test_files_with_checks']} فيها فحوص؛ {N(INV['checks_executed'])} فحصاً؛ بلا فحوص: {', '.join(INV['helper_files_without_checks']) or '—'}"),
 ('§8', 'المحلّل قبل وبعد: صفر تغيير', 'DONE' if CMP['violations'] == 0 else 'VIOLATED', f"{CMP['violations']} مخالفة في {N(CMP['verses'])} آية"),
 ('§8', 'الشهادات بالأدلّة وبدونها', 'DONE' if CERT['identical_without_evidence'] == CERT['sentences'] else 'VIOLATED', f"{N(CERT['identical_without_evidence'])}/{N(CERT['sentences'])} جملة"),
 ('§8', 'كل صفٍّ تغيّر بين المستهلكين مصنّف', 'DONE' if REP['unclassified_transitions'] == 0 else 'PARTIAL', f"{N(REP['row_transitions_changed'])} صفاً؛ غير المصنّف {REP['unclassified_transitions']}"),
 ('§8', 'لا CANDIDATE_MATCH بتعارض هوية', 'DONE' if idok else 'VIOLATED', f"بعد: {ida or 0}"),
 ('§9', 'صفحة تتبّع جديدة وسجلّ قراءة الأقسام صفاً صفاً', 'DONE', f"{os.path.basename(NEWP)}؛ {len(sec_changed)} قسماً متغيّراً"),
 ('§9', 'إعادة الإنتاج من نسخةٍ نظيفة', 'DONE' if os.path.exists(os.path.join(SRC, 'REPRODUCED')) else 'NOT_DONE', 'reproduce/reproduce_clean_run.log'),
]
with open(os.path.join(D, 'requirements_matrix.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t'); w.writerow(['البند', 'المتطلب', 'الحالة', 'الدليل']); w.writerows(REQ)
meas = dict(task='SARF_UPSTREAM_CONSUMER_REPAIR_02', branch='upstream-consumer-repair-02', base_commit=BASEC, head_commit=HEAD,
            hfn_analyzer_baseline='release_v36', hfn_candidate_source='release_v47', commits=LOG_.splitlines(), changed_files=changed,
            audit_reference=AUDIT_REF,
            identity=dict(recomputed_before=idb, after=ida, after_match_with_identity_not_ok=REP['identity_root_mismatch_rows']['after_match_with_identity_not_ok']),
            evidence_ids=REP['evidence_ids'], collisions_treated=REP['collisions_treated'], counts=REP['counts'], counter_definitions=REP['counter_definitions'],
            row_transitions_changed=REP['row_transitions_changed'], unclassified_transitions=REP['unclassified_transitions'], row_transitions=TR,
            protection=dict(base_vs_branch_violations=CMP['violations'], verses=CMP['verses'], certificates=dict(sentences=CERT['sentences'],
                            identical=CERT['identical_without_evidence']), display_only_paths=['certificate.external_evidence_ids', 'certificate.obligations[*].external_evidence']),
            shadow=dict(differences=ATT['differences'], classes=ATT['classes'], completeness=ATT['completeness'], previous_unattributed=ATT['previous_unattributed']),
            tests=dict(files=INV['test_files'], exit0=INV['test_files_exit0'], files_with_checks=INV['test_files_with_checks'], checks=INV['checks_executed'],
                       helpers_without_checks=INV['helper_files_without_checks'], test_upstream_checks=len(UCH), mutations=MUTS,
                       reproduce_selftest=[dict(result=a, id=b, name=c) for a, b, c in SELF]),
            trace=dict(page=os.path.basename(NEWP), sections_changed_vs_061=sec_changed),
            sources=dict(commits=CJ['pins']['commits'], hfn_release=CJ['pins']['hfn_release'], hfn_manifest_sha256=CJ['pins']['hfn_manifest_sha256']),
            requirements=[dict(section=a, requirement=b, status=c, evidence=d) for a, b, c, d in REQ],
            flags=dict(MODIFY_SARF_ANALYSIS_RULES='NO', MODIFY_SEGMENTATION='NO', MODIFY_UPSTREAM_DATA='NO', HFN_V47_ADOPTED='NO', PUSH='NO', MERGE='NO'))
json.dump(meas, open(os.path.join(D, 'measurement.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ================= التقارير =================
tr_by = {}
for t in TR:
    tr_by.setdefault((t['source'], t['before'], t['after']), []).append(t)
C = []
w = C.append
w('# تقرير صاحب النظرية — SARF_UPSTREAM_CONSUMER_REPAIR_02\n')
w(f"الفرع `upstream-consumer-repair-02` من `{BASEC[:7]}` إلى `{HEAD[:7]}`؛ التزاماتٌ محلية: لا دفع ولا دمج. `sarf/` لم يُمسّ"
  f"{' (مخالفة!)' if sarf_touched else ''}، وv47 غير معتمد.\n")
w('## الحكم بحسب كل متطلب\n')
w('| البند | المتطلب | الحالة | الدليل |\n|---|---|---|---|')
for a, b, c, d in REQ:
    w(f'| {a} | {b} | **{c}** | {d} |')
w('\n## ١. هوية المعجم (§٢)\n')
w('أعدتُ حساب صفوف CANDIDATE_MATCH التي يختلف جذر مصدرها عن جذر الوجه، بالطريقة نفسها قبل الإصلاح وبعده (الوحدة: صفّ، لا كلمة):\n')
w('| المصدر | مرجع التدقيق | المعاد قبل الإصلاح | بعد الإصلاح |\n|---|---:|---:|---:|')
for k, v in AUDIT_REF['identity'].items():
    w(f'| {k} | {v} | {idb.get(k, 0)} | {ida.get(k, 0)} |')
w('\nالإعادة طابقت المرجع في كل مصدر.' if all(idb.get(k, 0) == v for k, v in AUDIT_REF['identity'].items()) else
  '\nاختلفت الإعادة عن المرجع في: ' + '، '.join(k for k, v in AUDIT_REF['identity'].items() if idb.get(k, 0) != v) + '.')
w('\nالشاهد الحاكم: «يَقُولُ» (2:8، وجهه قول) كان يُرفق به الحدث `HFN-E-e1bbafba2a` (قَالَ تحت قيل، مصدره قَيْلُولَة)؛ وهو الآن `LEXEME_IDENTITY_CONFLICT` بلا دليل، '
  'وحدث قول نفسه وحده مرفق. والفحص في كل العائلات: جذر الصفّ أو جذر حدثه، والبناء بتصنيف sarf (`hfn_class`) وجدول `hfn_form_crosswalk` شاهداً ثانياً '
  '(اختلافهما تأجيل)، ومعرّف الحدث وحقوله، والسحب عبر المعرّف، والمسلك.\n')
w('انتقالات الصفوف بين المستهلكين (تصحيحٌ في الأهلية، والصفوف محفوظة بأسبابها):\n')
w('| المصدر | قبل | بعد | السبب | الصفوف |\n|---|---|---|---|---:|')
for t in sorted(TR, key=lambda t: -t['rows'])[:40]:
    w(f"| {t['source']} | {t['before']} | {t['after']} | {t['reason']} | {N(t['rows'])} |")
w(f"\nمجموع الصفوف المتغيّرة {N(REP['row_transitions_changed'])}، وغير المصنّف منها {REP['unclassified_transitions']} (الجدول كاملاً: `counts/row_transitions_summary.tsv`، والصفوف: `counts/repair_row_transitions.jsonl.gz`).\n")
w('## ٢. معرّفات الأدلّة (§٣)\n')
EB = REP['evidence_ids']['before']
w(f"- قبل: {N(EB['evidence_records'])} سجلّ دليل، {N(EB['distinct_ids'])} معرّفاً، منها {N(EB['ids_repeated'])} مكرّر و{N(EB['ids_with_different_content'])} يحيل إلى محتويين (المرجع {AUDIT_REF['ids_repeated']} و{AUDIT_REF['ids_with_different_content']}).")
w(f"- بعد: المعرّف `{EA.get('algorithm')}` على الوقوع والوجه والمصدر والإصدار والصفّ والمسلك والحمولة؛ {N(EA['evidence_records'])} سجلّاً، {N(EA['distinct_ids'])} معرّفاً، "
  f"المكرّر {EA['ids_repeated']} (إشارةٌ إلى الدليل نفسه) والمحيل إلى محتويين {EA['ids_with_different_content']}، وأخطاء السجلّ {len(EA['registry_errors'])}؛ "
  f"والمراجع في الشهادات {N(orph.get('seen') or 0)}، اليتيم منها {orph.get('orphan')}.")
w(f"- معالجة التصادمات القديمة ({N(REP['collisions_treated'])}): كل محتوى بمعرّف بصمته؛ لا اختيار لأول دليلٍ ولا حذف للمختلف (`evidence/repair_evidence_collisions.tsv`).\n")
w('## ٣. وحدات العدّ (§٤)\n')
w('| العدّاد | التعريف | قبل | بعد |\n|---|---|---:|---:|')
for k, d_ in REP['counter_definitions'].items():
    w(f'| `{k}` | {d_} | {N(CB[k])} | {N(CA[k])} |')
w(f"\nالمقامات: سجلات الوقوع {N(CA['denominators']['occurrence_records'])} (المسؤول عنها {N(CA['denominators']['occurrence_records_queried'])})، وصفوف السمات {N(CA['denominators']['feature_rows'])} بعد.\n")
w('## ٤. الانتقال الظلي (§٥)\n')
w(f"{N(ATT['differences'])} فرقاً (كان {N(ATT['previous_unattributed'])} منها UNATTRIBUTED):\n")
w('| الصنف | المعنى | العدد |\n|---|---|---:|')
MEAN = dict(PROVEN_RECORD='سجلٌّ متغيّر لمفتاح الوجه نفسه (الجذر والوزن)', LINKED_BY_NAMED_RECORD='في الفرق نفسه سجلٌّ متغيّر مسمّى: رابطٌ لا يثبت السببية وحده',
            REPRESENTATION_WASL='تمثيل «ٱ/ا» وحده', AGGREGATE_REPRESENTATION='تمثيلٌ تجميعي للآية (S أو trace)', SPATIAL_WORD='في كلمةٍ تغيّر لها سجلّ، ولا رابط من الفرق: مكانيٌّ لا سبب',
            SPATIAL_VERSE='في آيةٍ فيها تغيّرٌ مثبت في كلمةٍ أخرى', UNRESOLVED='غير محسوم')
for k, v in ATT['classes'].items():
    w(f'| {k} | {MEAN.get(k, "")} | {N(v)} |')
w(f"\nالاكتمال **{ATT['completeness']}**: يبقى {ATT['classes'].get('UNRESOLVED')} فرقاً غير محسوم (`shadow/shadow_attribution.jsonl.gz`)، ولم يُختلق لها سبب.\n")
w('## ٥. الحماية والاختبارات\n')
w(f"- المحلّل قبل الإصلاح وبعده: {CMP['violations']} مخالفة في {N(CMP['verses'])} آية. والشهادات بالأدلّة وبدونها متطابقة في {N(CERT['identical_without_evidence'])}/{N(CERT['sentences'])} جملة عدا مسارَي العرض المعلنين.")
w(f"- الاختبارات: {INV['test_files']} ملفاً، خرج بصفر {INV['test_files_exit0']}، وفيها فحوص {INV['test_files_with_checks']} ({N(INV['checks_executed'])} فحصاً)؛ "
  f"وبلا فحوص (مساعد لا اختبار مستقل): {', '.join(INV['helper_files_without_checks']) or '—'}. وtest_upstream {len(UCH)} فحصاً، والإفسادات {sum(m[1] for m in MUTS)}/{len(MUTS)} مكشوفة.")
w('- اختبار أداة الإعادة: ' + '؛ '.join(f'{b} {a}: {c}' for a, b, c in SELF) + '.\n')
w('## ٦. ما بقي\n')
for a, b, c, d in REQ:
    if c not in ('DONE',):
        w(f'- **{c}** — {b}: {d}')
w('\n- لم يُعدَّل تحقيق «ٱ» ولا ترجيح قول/قيل في المحلّل، ولم يُعتمد v47.\n')
w('## ٧. الإعادة\n')
w('```\nbash reproduce/reproduce.sh --sarf <arabic-sarf-2026> --data <data> --hfn <HusseinFrameNet> --hfn-base <…/release_v36> --wazn <wazn-net> \\\n'
  f'  --amln <AMLN> --maq <Maqaiys-roots> --branch {HEAD} --old {BASEC} --out <مجلد جديد>\n```')
open(os.path.join(D, 'customer_report_ar.md'), 'w', encoding='utf-8').write('\n'.join(C) + '\n')
T = ['# Technical report — SARF_UPSTREAM_CONSUMER_REPAIR_02\n', f'Base `{BASEC}` → head `{HEAD}` (branch `upstream-consumer-repair-02`). `sarf/` untouched: {not sarf_touched}.\n',
     '## Identity gate (`tools/upstream_candidates.py identity()`)\n',
     'Inputs per row: row root, row form (or the event\'s), row verb, `event_ref` (fields of the referenced event in the pinned release, attached by the worker; '
     'event ids missing from the engine API are recovered from the pinned tables: mutawaa_v7 base_event/mutawaa_event, AMLN taadiya_T_JAL base_event). '
     'Order: ambiguous/missing event id → `IDENTITY_UNDETERMINED`; withdrawn → `WITHDRAWN_RECORD`; event fields disagree with row → `EVENT_ID_FIELD_MISMATCH`; '
     'missing root/form → `IDENTITY_UNDETERMINED`; form class = `sarf.root.hfn_class` (crosswalk code as a second witness; disagreement → `IDENTITY_UNDETERMINED`); '
     'root key (documented seat normalization) or class differs from the face → `LEXEME_IDENTITY_CONFLICT`. State precedence: WITHDRAWN > ROUTE_BLOCKED > identity > match.\n',
     '## Evidence ids\n', f"`{EA.get('algorithm')}` over {', '.join(('occurrence_id', 'morph_candidate_id', 'analysis_id', 'source_key', 'provider', 'route_id', 'source_commit', 'release_id', 'source_file_sha256', 'source_row_id', 'payload'))}. "
     '`verify_evidence_registry()` recomputes every id and rejects one id with two contents.\n',
     '## Measurements\n', '```json\n' + json.dumps({k: meas[k] for k in ('identity', 'evidence_ids', 'counts', 'protection', 'shadow', 'tests')}, ensure_ascii=False, indent=1)[:12000] + '\n```\n',
     '## Row transitions\n'] + [f"- {t['source']}: {t['before']} → {t['after']} ({t['reason']}): {t['rows']}" for t in TR] + [
     '\n## Portable reproduction\n', 'bash ≥ 3.2; no `timeout`/`mapfile`/GNU flags; per-job PIDs with individual `wait`; Python `subprocess.run(timeout=)` wrapper; '
     'env passed as arrays; paths with spaces (self-test R1); verse-count, duplicate and release-mix checks on every result; tests counted by executed checks.\n']
open(os.path.join(D, 'technical_report.md'), 'w', encoding='utf-8').write('\n'.join(T) + '\n')
E = html.escape


def table(head, rows):
    return '<div class="wrap"><table><tr>' + ''.join(f'<th>{E(str(h))}</th>' for h in head) + '</tr>' + ''.join(
        '<tr>' + ''.join(f'<td>{E(str(c))}</td>' for c in r) + '</tr>' for r in rows) + '</table></div>'


tiles = [('تعارض هوية مرفق بعد', N(sum(ida.values()) if ida else 0)), ('معرّف بمحتويين بعد', EA['ids_with_different_content']),
         ('مراجع يتيمة', orph.get('orphan')), ('صفوف مطابقة بعد', N(CA['feature_rows_candidate_match'])), ('مخالفات المحلّل', CMP['violations']),
         ('غير محسوم ظلي', ATT['classes'].get('UNRESOLVED')), ('إفسادات مكشوفة', f"{sum(m[1] for m in MUTS)}/{len(MUTS)}")]
page = f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>تدقيق إصلاح المستهلك</title><style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#ddd9cf;--head:#efece4}}
@media (prefers-color-scheme:dark){{:root{{--bg:#191917;--fg:#e9e7e1;--mut:#a3a19a;--line:#3a3935;--head:#26251f}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.6 "Noto Naskh Arabic",Tahoma,sans-serif;margin:0;padding:16px;max-width:1400px}}
h2{{font-size:1.15em;margin-top:2em;border-bottom:1px solid var(--line)}} .wrap{{overflow-x:auto}} table{{border-collapse:collapse;font-size:13px;width:100%}}
th,td{{border:1px solid var(--line);padding:3px 6px;vertical-align:top}} th{{background:var(--head)}} .k{{display:inline-block;margin:0 0 6px 10px;padding:6px 10px;border:1px solid var(--line);border-radius:6px}} .k b{{display:block;font-size:1.2em}}
</style></head><body><h1>تدقيق SARF_UPSTREAM_CONSUMER_REPAIR_02</h1><p>{E(BASEC[:7])} → {E(HEAD[:7])} · release_v36 أساساً · v47 مرشّح · لا دفع ولا دمج</p>
<div>{''.join(f'<span class="k">{E(a)}<b>{E(str(b))}</b></span>' for a, b in tiles)}</div>
<h2>المتطلبات</h2>{table(['البند', 'المتطلب', 'الحالة', 'الدليل'], REQ)}
<h2>الهوية قبل وبعد</h2>{table(['المصدر', 'المرجع', 'قبل', 'بعد'], [(k, v, idb.get(k, 0), ida.get(k, 0)) for k, v in AUDIT_REF['identity'].items()])}
<h2>انتقالات الصفوف</h2>{table(['المصدر', 'قبل', 'بعد', 'السبب', 'الصفوف'], [(t['source'], t['before'], t['after'], t['reason'], t['rows']) for t in TR])}
<h2>العدّادات</h2>{table(['العدّاد', 'التعريف', 'قبل', 'بعد'], [(k, d_, CB[k], CA[k]) for k, d_ in REP['counter_definitions'].items()])}
<h2>الفروق الظلية</h2>{table(['الصنف', 'العدد'], ATT['classes'].items())}
<h2>الإفساد</h2>{table(['الإفساد', 'كُشف'], [(m[0], 'نعم' if m[1] else 'لا') for m in MUTS])}
<h2>اختبارات test_upstream</h2>{table(['النتيجة', 'المعرّف', 'الفحص'], UCH)}
<h2>سجلّ قراءة الصفحة (الأقسام المتغيّرة)</h2>{table(['القسم', 'الحال', 'الصف'], [r for r in rows_log if r[1] != 'مطابق'][:400])}
</body></html>'''
open(os.path.join(D, 'audit.html'), 'w', encoding='utf-8').write(page)
files = [dict(path=os.path.relpath(p, D), bytes=os.path.getsize(p), sha256=sha(p)) for p in sorted(glob.glob(os.path.join(D, '**', '*'), recursive=True))
         if os.path.isfile(p) and os.path.basename(p) != 'MANIFEST.json']
json.dump(dict(task='SARF_UPSTREAM_CONSUMER_REPAIR_02', base_commit=BASEC, head_commit=HEAD, created=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
               flags=meas['flags'], requirements={f'{a} {b}': c for a, b, c, _ in REQ}, files=files), open(os.path.join(D, 'MANIFEST.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('delivery ok', len(files))
