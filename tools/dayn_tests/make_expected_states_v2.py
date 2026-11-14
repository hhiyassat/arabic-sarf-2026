# -*- coding: utf-8 -*-
"""expected_states_v2.json: حالات بالمرحلة + قيمة شجرة الشيفرة بالمرحلة + مسارات مخرجات التصدير.
يُبصم ويؤرَّخ قبل أول تشغيل، ويرفض التوليدُ الكتابةَ فوق ملفٍ موجود. الاستعمال: make_expected_states_v2.py <out_dir> <iso_time>"""
import os, sys, json, hashlib, subprocess
OUT, TS = sys.argv[1], sys.argv[2]
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
dst = os.path.join(OUT, 'expected_states_v2.json')
if os.path.exists(dst):
    print('REFUSE_OVERWRITE %s already exists' % dst); sys.exit(3)

def git(*a): return subprocess.run(['git', '-C', ROOT, *a], capture_output=True, text=True).stdout.strip()
SARF_TREE = git('rev-parse', 'HEAD:sarf')
ED2_BLOB = git('rev-parse', 'HEAD:tools/v48c2/engine_dump2.py')
STAGES = ['before', 'after_E0', 'after_E1', 'after_E2', 'after_E4']
TBD = 'TO_BE_DECLARED'

def st(kind, fix_stage=None, always=None):
    if always is not None: return {s: always for s in STAGES}
    i = STAGES.index(fix_stage)
    if kind == 'REPRO': return {s: STAGES.index(s) < i for s in STAGES}
    if kind == 'ACCEPT': return {s: STAGES.index(s) >= i for s in STAGES}
checks = {
 'KEEP_1a_seg85': dict(type='KEEP', states=st('K', always=True)),
 'KEEP_1b_root85': dict(type='KEEP', states=st('K', always=True)),
 'KEEP_1c_root7': dict(type='KEEP', states=st('K', always=True)),
 'KEEP_1d_lookup_ajalh': dict(type='KEEP', states=st('K', always=True)),
 'KEEP_1e_lookup_ajalin': dict(type='KEEP', states=st('K', always=True)),
 'KEEP_2a_seg91': dict(type='KEEP', states=st('K', always=True)),
 'KEEP_2b_ops91': dict(type='KEEP', states=st('K', always=True)),
 'KEEP_2c_dep91_struct': dict(type='KEEP', states=st('K', always=True)),
 'KEEP_2d_ma_groups': dict(type='KEEP', states=st('K', always=True)),
 'KEEP_4_morph46': dict(type='KEEP', states=st('K', always=True)),
 'KEEP_5_protected': dict(type='KEEP', states=st('K', always=True)),
 'KEEP_6a_kana_laysa': dict(type='KEEP', states=st('K', always=True)),
 'KEEP_6b_lam_amr': dict(type='KEEP', states=st('K', always=True)),
 'KEEP_6c_yakuna': dict(type='KEEP', states=st('K', always=True)),
 'REPRO_1_ajal_lookup': dict(type='REPRO', states=st('K', always=True)),
 'REPRO_2a_lam_milk': dict(type='REPRO', states=st('REPRO', 'after_E4')),
 'REPRO_2b_ma_effect': dict(type='REPRO', states=st('REPRO', 'after_E4')),
 'REPRO_2c_ma_evidence': dict(type='REPRO', states=st('REPRO', 'after_E4')),
 'REPRO_3_faces_text': dict(type='REPRO', states=st('REPRO', 'after_E1')),
 'REPRO_5a_alla_single': dict(type='REPRO', states=st('K', always=True)),
 'REPRO_5b_mimman_single': dict(type='REPRO', states=st('K', always=True)),
 'REPRO_5c_mimman_pos': dict(type='REPRO', states=st('K', always=True)),
 'REPRO_6a_amil_pos': dict(type='REPRO', states=st('K', always=True)),
 'REPRO_6b_membership': dict(type='REPRO', states=st('K', always=True), desc='SPLIT: إِذَا member of group 7'),
 'REPRO_6b_title': dict(type='REPRO', states=st('K', always=True), desc='SPLIT: catalog group7 title=الشرط الجازمة فقط'),
 'REPRO_6c_waw_lam_merge': dict(type='REPRO', states=st('K', always=True)),
 'REPRO_6d_yakuna_schema': dict(type='REPRO', states=st('K', always=True)),
 'REPRO_cloud_shahada_mudaf': dict(type='REPRO', states=st('K', always=True)),
 'ACCEPT_E0_unit_after_al': dict(type='ACCEPT', states=st('ACCEPT', 'after_E0')),
 'ACCEPT_E1_faces_contract': dict(type='ACCEPT', states=st('ACCEPT', 'after_E1')),
 'ACCEPT_E2_coverage': dict(type='ACCEPT', states=st('ACCEPT', 'after_E2')),
 'ACCEPT_E4_ma_not_escalated': dict(type='ACCEPT', states=st('ACCEPT', 'after_E4')),
 'ACCEPT_E4_lam_relation_kept': dict(type='ACCEPT', states=st('ACCEPT', 'after_E4')),
 'ACCEPT_E4_order_invariant': dict(type='ACCEPT', states=st('ACCEPT', 'after_E4')),
 'INFO_4_stems81': dict(type='INFO', states=st('K', always=True)),
}
code_tree = {'before': dict(sarf_tree=SARF_TREE, engine_dump2_blob=ED2_BLOB)}
for s in STAGES[1:]: code_tree[s] = dict(sarf_tree=TBD, engine_dump2_blob=TBD)
export_outputs = {'before': dict(E0_export=None, E2_coverage=None)}
for s in STAGES[1:]: export_outputs[s] = dict(E0_export=TBD, E2_coverage=TBD)
doc = dict(round='SARF_MORPH_EXPORT_REPAIR_01', batch='STEP2a_tests', version=2, declared_at_utc=TS,
           supersedes='STEP2_tests/expected_states.json (v1)', engine_base='726131f', resource='release_v47',
           principle='identity pinned by CODE TREE (sarf tree + imported tool blobs), not branch head; later-stage tree/export values TO_BE_DECLARED per fix batch before its run; tool refuses TO_BE_DECLARED or mismatch; the tool also verifies THIS file against its recorded fingerprint and refuses a modified file',
           stages=STAGES, code_tree=code_tree, export_outputs=export_outputs, checks=checks)
body = json.dumps(doc, ensure_ascii=False, sort_keys=True)
doc['self_fingerprint'] = hashlib.sha256(body.encode()).hexdigest()
json.dump(doc, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
fp = hashlib.sha256(open(dst, 'rb').read()).hexdigest()
json.dump(dict(file='expected_states_v2.json', sha256=fp, declared_at_utc=TS, version=2),
          open(os.path.join(OUT, 'expected_states_v2_fingerprint.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(dict(ok=True, checks=len(checks), sarf_tree=SARF_TREE[:8], ed2_blob=ED2_BLOB[:8], sha256=fp[:16]), ensure_ascii=False))
