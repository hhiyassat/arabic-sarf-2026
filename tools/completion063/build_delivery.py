"""build_delivery.py <REPO> <OUT_DIR> <REPRO_DIR> <BATCH_DIR> <TRACE_DIR>
يجمع تسليم SARF_COMPLETION_FROM_REPORT_063 في مجلدٍ جديد (لا يستبدل موجوداً): القياس الموحَّد measurement.json من مخرجات
reproduce.sh (الأساس ← النهائي) ومن قياسات الدفعات في نسخها المجمّدة، والشيفرة (الفرق والحزمة والمصدر)، وبصمات الموارد،
وصفحة المسار وسجلّ قراءتها، والاختبارات، وMANIFEST.json ببصمة كل ملف. التقارير النصّية الثلاثة تُكتب بيدٍ من هذه الأرقام."""
import csv, hashlib, json, os, shutil, subprocess, sys

REPO, OUT, REPRO, BATCH, TRACE = (os.path.abspath(x) for x in sys.argv[1:6])
if os.path.exists(OUT) and os.listdir(OUT):
    sys.exit(f'OUT موجود وفيه ملفات: لا يُستبدل تسليمٌ سابق ({OUT})')
G = lambda *a: subprocess.run(['git', '-C', REPO, *a], capture_output=True, text=True, check=True).stdout
BASE = '67a4df885fbd4d8e9ae8295d34f6c68f4b7a29e0'
HEAD = G('rev-parse', 'HEAD').strip()
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
J = lambda p: json.load(open(p, encoding='utf-8'))
for d in ('code', 'measurement', 'measurement/batches', 'measurement/final', 'trace', 'tests', 'reproduce', 'registry', 'resources'):
    os.makedirs(os.path.join(OUT, d), exist_ok=True)

# ١ الشيفرة
open(os.path.join(OUT, 'code', 'commits.txt'), 'w', encoding='utf-8').write(G('log', '--format=%H %ad %s', '--date=iso', f'{BASE}..{HEAD}'))
open(os.path.join(OUT, 'code', f'diff_{BASE[:7]}_{HEAD[:7]}.patch'), 'w', encoding='utf-8').write(G('diff', BASE, HEAD))
with open(os.path.join(OUT, 'code', 'changed_files.tsv'), 'w', encoding='utf-8') as f:
    f.write('status\tpath\n' + G('diff', '--name-status', BASE, HEAD))
subprocess.run(['git', '-C', REPO, 'bundle', 'create', os.path.join(OUT, 'code', f'branch_{BASE[:7]}_{HEAD[:7]}.bundle'), 'completion-from-063', f'^{BASE}'],
               check=True, capture_output=True)
with open(os.path.join(OUT, 'code', f'source_{HEAD[:7]}.tar.gz'), 'wb') as f:
    f.write(subprocess.run(['git', '-C', REPO, 'archive', '--format=tar.gz', HEAD], capture_output=True, check=True).stdout)

# ٢ القياس: النهائي من reproduce.sh، والدفعات من نسخها المجمّدة
M = os.path.join(REPRO, 'm')
fin = {}
for name in ('cmp_snap', 'cmp_axes', 'cmp_certs', 'cmp_roots', 'cmp_units', 'recon_final', 'cmp_snap_v47', 'cmp_roots_v47', 'cmp_units_v47',
             'issue_log', 'stage_matrix', 'registry_base', 'registry_final'):
    p = os.path.join(M, name + '.json')
    if os.path.exists(p):
        shutil.copy(p, os.path.join(OUT, 'measurement', 'final', name + '.json'))
        fin[name] = J(p)
for p in ('issue_log.md',):
    if os.path.exists(os.path.join(M, p)):
        shutil.copy(os.path.join(M, p), os.path.join(OUT, 'registry', p))
for p in ('stage_matrix.json', 'issue_log.json', 'registry_base.json', 'registry_final.json'):
    if os.path.exists(os.path.join(M, p)):
        shutil.copy(os.path.join(M, p), os.path.join(OUT, 'registry', p))
if os.path.exists(os.path.join(M, 'stage_matrix.md')):
    shutil.copy(os.path.join(M, 'stage_matrix.md'), os.path.join(OUT, 'registry', 'stage_matrix.md'))
bat = {}
for f_ in sorted(os.listdir(BATCH)):
    if f_.startswith(('cmp_', 'recon_b1')) and f_.endswith('.json'):
        shutil.copy(os.path.join(BATCH, f_), os.path.join(OUT, 'measurement', 'batches', f_))
        bat[f_[:-5]] = J(os.path.join(BATCH, f_))
for f_ in ('eval_root_b2.txt', 'eval_root_b4.txt'):
    if os.path.exists(os.path.join(BATCH, f_)):
        shutil.copy(os.path.join(BATCH, f_), os.path.join(OUT, 'measurement', 'batches', f_))


def brief(d, keys):
    return {k: d.get(k) for k in keys if k in d}


meas = dict(
    mandate='SARF_COMPLETION_FROM_REPORT_063', base_commit=BASE, final_commit=HEAD, branch='completion-from-063',
    default_hfn_release='release_v36', push='NO', merge='NO',
    final=dict(
        snapshot=brief(fin.get('cmp_snap', {}), ('verses', 'violations')),
        units_vs_qac=brief(fin.get('cmp_units', {}), ('before', 'after', 'transitions', 'correct_to_not_correct', 'not_correct_to_correct')),
        verb_roots_vs_qac=brief(fin.get('cmp_roots', {}), ('before', 'after', 'transitions', 'correct_to_not_correct', 'not_correct_to_correct')),
        axes=brief(fin.get('cmp_axes', {}), ('agreement_transitions', 'ungoverned_kind_after', 'role_changes', 'object_requirement_transitions',
                                              'object_record_transitions', 'licensed_lost')),
        certificates=brief(fin.get('cmp_certs', {}), ('sentences_before', 'sentences_after', 'verdict_transitions', 'by_level_transitions',
                                                      'obligation_transitions', 'closed_lost')),
        reconciliation=brief(fin.get('recon_final', {}), ('verses', 'units_changed', 'feature_changes', 'consistency_errors', 'transitions')),
        v47_from_final=dict(units_vs_qac=brief(fin.get('cmp_units_v47', {}), ('before', 'after', 'transitions', 'correct_to_not_correct',
                                                                                'not_correct_to_correct')),
                            verb_roots_vs_qac=brief(fin.get('cmp_roots_v47', {}), ('before', 'after', 'transitions', 'correct_to_not_correct',
                                                                                     'not_correct_to_correct'))),
        issue_log=(fin.get('issue_log') or {}).get('summary'), stage_matrix=(fin.get('stage_matrix') or {}).get('summary')),
    batches={k: brief(v, ('verses', 'violations', 'units_changed', 'feature_changes', 'consistency_errors', 'before', 'after', 'transitions',
                          'correct_to_not_correct', 'not_correct_to_correct', 'agreement_transitions', 'ungoverned_kind_after',
                          'object_record_transitions', 'object_requirement_transitions', 'verdict_transitions', 'by_level_transitions',
                          'obligation_transitions', 'closed_lost', 'licensed_lost')) for k, v in bat.items()},
    qac_use='القياس وحده: لا مدخل في التحليل')
json.dump(meas, open(os.path.join(OUT, 'measurement.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)

# ٣ الاختبارات وإعادة الإنتاج
if os.path.exists(os.path.join(REPRO, 'tests')):
    shutil.copytree(os.path.join(REPRO, 'tests'), os.path.join(OUT, 'tests', 'final_run'), dirs_exist_ok=True)
for f_ in ('reproduce_steps.log',):
    shutil.copy(os.path.join(REPRO, f_), os.path.join(OUT, 'reproduce', f_))
for f_ in os.listdir(os.path.join(REPO, 'tools', 'completion063')):
    if f_.endswith(('.py', '.sh')):
        shutil.copy(os.path.join(REPO, 'tools', 'completion063', f_), os.path.join(OUT, 'reproduce', f_))
open(os.path.join(OUT, 'reproduce', 'REPRODUCED_AT.txt'), 'w').write(
    f"{'REPRODUCED' if os.path.exists(os.path.join(REPRO, 'REPRODUCED')) else 'NOT_COMPLETE'} final={HEAD}\n")

# ٤ صفحة المسار وسجلّ قراءتها
shutil.copy(os.path.join(REPO, 'reports', 'arabic-sarf-064.html'), os.path.join(OUT, 'trace', 'arabic-sarf-064.html'))
shutil.copy(os.path.join(TRACE, 'section_reading_log.tsv'), os.path.join(OUT, 'trace', 'section_reading_log.tsv'))

# ٥ بصمات الموارد (لا تُنسخ بيانات HFN ولا QAC)
res = {}
for label, p in (('hfn_release_v36/events.csv', '/home/user/husseinframenet/release/release_v36/events.csv'),
                 ('hfn_release_v36/lexical_units.csv', '/home/user/husseinframenet/release/release_v36/lexical_units.csv'),
                 ('hfn_release_v36/form_meanings.csv', '/home/user/husseinframenet/release/release_v36/form_meanings.csv'),
                 ('hfn_release_v47/events.csv (HFN 22dcb06)', '/home/user/ucr/repro03/pinned/hfn/release/release_v47/events.csv'),
                 ('hfn_release_v47/lexical_units.csv', '/home/user/ucr/repro03/pinned/hfn/release/release_v47/lexical_units.csv'),
                 ('hfn_release_v47/form_meanings.csv', '/home/user/ucr/repro03/pinned/hfn/release/release_v47/form_meanings.csv'),
                 ('data/quran_hafs.tsv', os.path.join(REPO, 'data', 'quran_hafs.tsv')),
                 ('data/quran-morphology.txt (QAC، للقياس وحده)', os.path.join(REPO, 'data', 'quran-morphology.txt')),
                 ('SARF_UP_EVIDENCE c3_2282.jsonl.gz (صفحتا 063 و064)', '/home/user/ucr/out/c3_2282.jsonl.gz')):
    res[label] = sha(p) if os.path.exists(p) else 'MISSING'
json.dump(res, open(os.path.join(OUT, 'resources', 'resource_hashes.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ٦ MANIFEST (يُعاد بعد كتابة التقارير)
def manifest():
    files = {}
    for root, _, fs in os.walk(OUT):
        for f_ in fs:
            p = os.path.join(root, f_)
            rel = os.path.relpath(p, OUT)
            if rel != 'MANIFEST.json':
                files[rel] = dict(sha256=sha(p), bytes=os.path.getsize(p))
    json.dump(dict(mandate='SARF_COMPLETION_FROM_REPORT_063', base_commit=BASE, final_commit=HEAD, files=files),
              open(os.path.join(OUT, 'MANIFEST.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


manifest()
print(json.dumps(dict(out=OUT, head=HEAD, files=sum(len(f) for _, _, f in os.walk(OUT))), ensure_ascii=False))
