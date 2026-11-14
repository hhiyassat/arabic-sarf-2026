# -*- coding: utf-8 -*-
"""يكتب expected_states.json (حالة كل فحص في كل مرحلة) ويبصمه ويؤرّخه قبل أي تشغيلٍ للأداة.
لا يُعدَّل بعد التشغيل؛ أي تعديل لاحق إصدارٌ جديد ببصمةٍ ووقت. الاستعمال: make_expected_states.py <out_dir> <iso_time>"""
import os, sys, json, hashlib
OUT, TS = sys.argv[1], sys.argv[2]
# True = «condition holds». REPRO: defect present. KEEP: must hold. ACCEPT: fix achieved. INFO: not in exit code.
STAGES = ['before', 'after_E0', 'after_E1', 'after_E2', 'after_E4']
def row(kind, fix_stage=None, always=None):
    # always: same value at all stages (KEEP=True; out-of-scope REPRO=True [present]).
    if always is not None: return {s: always for s in STAGES}
    idx = STAGES.index(fix_stage)
    if kind == 'REPRO':   # present(True) before fix_stage, absent(False) at/after
        return {s: STAGES.index(s) < idx for s in STAGES}
    if kind == 'ACCEPT':  # not achieved(False) before fix_stage, achieved(True) at/after
        return {s: STAGES.index(s) >= idx for s in STAGES}
    raise ValueError(kind)

checks = {
 # --- KEEP: hold at every stage ---
 'KEEP_1a_seg85': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='85 = stem أَجَلِ + enclitic هِ (2 slots)'),
 'KEEP_1b_root85': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='U(85,stem).R=ءجل, lemma=أَجَل'),
 'KEEP_1c_root7': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='U(7,stem).R=ءجل'),
 'KEEP_1d_lookup_ajalh': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='lookup(أَجَلْ) finds particle:0235'),
 'KEEP_1e_lookup_ajalin': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='lookup(أَجَلٍ)=[]'),
 'KEEP_2a_seg91': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='91 = عامل لِ + أل ل + stem شَّهَٰدَةِ (3 slots)'),
 'KEEP_2b_ops91': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='لِ group1 accepted, group6 blocked'),
 'KEEP_2c_dep91_struct': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='jar gov seg0 -> dep seg2, consistent'),
 'KEEP_2d_ma_groups': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='ما groups 3&7 deferred at BOTH 19 and 75'),
 'KEEP_4_morph46': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='morph=46 (27/12/7)'),
 'KEEP_5_protected': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='61,93,105 exist+unique, not_applicable CONSTITUTIONAL_PROTECTED_CLASS'),
 'KEEP_6a_kana_laysa': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='كان(35)+ليس(102,1) pos=فعل with naasikh operator content'),
 'KEEP_6b_lam_amr': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='lam-amr 10,22,23,27,48 operator=ل_الأمر consistent'),
 'KEEP_6c_yakuna': dict(type='KEEP', in_exit=True, states=row('K', always=True), desc='57,97 exist+unique, not_applicable'),
 # --- REPRO: defect present now; fix stage within E0-E4 or out-of-scope (present at all declared stages) ---
 'REPRO_1_ajal_lookup': dict(type='REPRO', in_exit=True, states=row('REPRO', always=True), desc='E3 scope: lookup(أَجَلِ)=[particle:0235]'),
 'REPRO_2a_lam_milk': dict(type='REPRO', in_exit=True, states=row('REPRO', fix_stage='after_E4'), desc='dep(91) operator_id=ل_الملك (first-choice)'),
 'REPRO_2b_ma_effect': dict(type='REPRO', in_exit=True, states=row('REPRO', fix_stage='after_E4'), desc='ما deferred face carries effect raf_ism_nasb_khabar'),
 'REPRO_2c_ma_evidence': dict(type='REPRO', in_exit=True, states=row('REPRO', fix_stage='after_E4'), desc='ما evidence first id = ما_النفي_الحالي'),
 'REPRO_3_faces_text': dict(type='REPRO', in_exit=True, states=row('REPRO', fix_stage='after_E1'), desc='15 يَأْبَ: reason names ءبو/ءبي, no structural candidate_faces'),
 'REPRO_5a_alla_single': dict(type='REPRO', in_exit=True, states=row('REPRO', always=True), desc='E7 scope: 93 أَلَّا single slot'),
 'REPRO_5b_mimman_single': dict(type='REPRO', in_exit=True, states=row('REPRO', always=True), desc='E7 scope: 61 مِمَّنْ single slot'),
 'REPRO_5c_mimman_pos': dict(type='REPRO', in_exit=True, states=row('REPRO', always=True), desc='E7 scope: 61 pos=عامل من العوامل المائة'),
 'REPRO_6a_amil_pos': dict(type='REPRO', in_exit=True, states=row('REPRO', always=True), desc='E5 scope: إِذَا(3)/مَا(75) pos=عامل'),
 'REPRO_6b_itha_group': dict(type='REPRO', in_exit=True, states=row('REPRO', always=True), desc='E5/C1 scope: إِذَا in group7 + group title from catalog'),
 'REPRO_6c_waw_lam_merge': dict(type='REPRO', in_exit=True, states=row('REPRO', always=True), desc='E8 scope: 10 features unit pos=مبني+عامل'),
 'REPRO_6d_yakuna_schema': dict(type='REPRO', in_exit=True, states=row('REPRO', always=True), desc='E6 scope: 57&97 schema pos undetermined, no operator'),
 'REPRO_cloud_shahada_mudaf': dict(type='REPRO', in_exit=True, states=row('REPRO', always=True), desc='OUT OF SCOPE: لِلشَّهَٰدَةِ carries مضاف-إليه face with jar inside unit'),
 # --- ACCEPT: fix contract, flips True at its stage ---
 'ACCEPT_E0_unit_after_al': dict(type='ACCEPT', in_exit=True, states=row('ACCEPT', fix_stage='after_E0'), desc='stem after أل / وَ+لْ has its own unit+features, not on previous cell'),
 'ACCEPT_E1_faces_contract': dict(type='ACCEPT', in_exit=True, states=row('ACCEPT', fix_stage='after_E1'), desc='structural candidate_faces: exist; separate denominators; per-face root/door/pattern/class/status/id; match reason-named pairs; no forced len==n_candidates'),
 'ACCEPT_E2_coverage': dict(type='ACCEPT', in_exit=True, states=row('ACCEPT', fix_stage='after_E2'), desc='per-stem coverage record (layer/unit/state-source), 81 no gap/dup'),
 'ACCEPT_E4_ma_not_escalated': dict(type='ACCEPT', in_exit=True, states=row('ACCEPT', fix_stage='after_E4'), desc='ما effect kept inside candidate face, not escalated; reorder entries/faces invariant'),
 'ACCEPT_E4_lam_relation_kept': dict(type='ACCEPT', in_exit=True, states=row('ACCEPT', fix_stage='after_E4'), desc='لِلشَّهَٰدَةِ jar relation kept, lam meaning NOT chosen, no ids[0]'),
 # --- INFO: not in exit code ---
 'INFO_4_stems81': dict(type='INFO', in_exit=False, states=row('K', always=True), desc='81 stems (informational; not a classification/alignment proof)'),
}
doc = dict(round='SARF_MORPH_EXPORT_REPAIR_01', batch='STEP2_tests', declared_at_utc=TS, version=1,
           engine_base='726131f', resource='release_v47', scope='2:282 only',
           principle='declared BEFORE first run; not modified after; this batch RUNS only the "before" stage; '
                     'after_E* columns are the contract for later batches',
           stages=STAGES, checks=checks)
body = json.dumps(doc, ensure_ascii=False, sort_keys=True)
doc['self_fingerprint'] = hashlib.sha256(body.encode()).hexdigest()
p = os.path.join(OUT, 'expected_states.json'); json.dump(doc, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
fp = hashlib.sha256(open(p, 'rb').read()).hexdigest()
json.dump(dict(file='expected_states.json', sha256=fp, declared_at_utc=TS, version=1,
               note='written+fingerprinted BEFORE the harness first run'),
          open(os.path.join(OUT, 'expected_states_fingerprint.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(dict(ok=True, checks=len(checks), sha256=fp[:16]), ensure_ascii=False))
