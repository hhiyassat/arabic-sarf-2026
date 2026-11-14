# -*- coding: utf-8 -*-
"""expected_states_v3.json: مثل v2 + بصمات ملفات الجذر في code_tree لكل مرحلة. يرفض الكتابة فوق موجود."""
import os, sys, json, hashlib, subprocess
OUT, TS = sys.argv[1], sys.argv[2]
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
dst = os.path.join(OUT, 'expected_states_v3.json')
if os.path.exists(dst): print('REFUSE_OVERWRITE'); sys.exit(3)
def git(*a): return subprocess.run(['git', '-C', ROOT, *a], capture_output=True, text=True).stdout.strip()
ROOT_FILES = ['operators_catalog.jsonl', 'operators_catalog_split_vocalized.csv', 'lexicon/mabniyat_lexicon.jsonl', 'tools/morph_engine_export.py']
SARF = git('rev-parse', 'HEAD:sarf'); ED2 = git('rev-parse', 'HEAD:tools/v48c2/engine_dump2.py')
RF = {f: git('rev-parse', 'HEAD:' + f) for f in ROOT_FILES}
STAGES = ['before', 'after_E0', 'after_E1', 'after_E2', 'after_E4']; TBD = 'TO_BE_DECLARED'
def stt(kind, fix=None, always=None):
    if always is not None: return {s: always for s in STAGES}
    i = STAGES.index(fix)
    return {s: (STAGES.index(s) < i) for s in STAGES} if kind == 'REPRO' else {s: (STAGES.index(s) >= i) for s in STAGES}
C = {}
for n in ['KEEP_1a_seg85','KEEP_1b_root85','KEEP_1c_root7','KEEP_1d_lookup_ajalh','KEEP_1e_lookup_ajalin','KEEP_2a_seg91','KEEP_2b_ops91','KEEP_2c_dep91_struct','KEEP_2d_ma_groups','KEEP_4_morph46','KEEP_5_protected','KEEP_6a_kana_laysa','KEEP_6b_lam_amr','KEEP_6c_yakuna']: C[n]=dict(type='KEEP',states=stt('K',always=True))
for n in ['REPRO_1_ajal_lookup','REPRO_5a_alla_single','REPRO_5b_mimman_single','REPRO_5c_mimman_pos','REPRO_6a_amil_pos','REPRO_6b_membership','REPRO_6b_title','REPRO_6c_waw_lam_merge','REPRO_6d_yakuna_schema','REPRO_cloud_shahada_mudaf']: C[n]=dict(type='REPRO',states=stt('K',always=True))
for n in ['REPRO_2a_lam_milk','REPRO_2b_ma_effect','REPRO_2c_ma_evidence']: C[n]=dict(type='REPRO',states=stt('REPRO','after_E4'))
C['REPRO_3_faces_text']=dict(type='REPRO',states=stt('REPRO','after_E1'))
C['ACCEPT_E0_unit_after_al']=dict(type='ACCEPT',states=stt('ACCEPT','after_E0'))
C['ACCEPT_E1_faces_contract']=dict(type='ACCEPT',states=stt('ACCEPT','after_E1'))
C['ACCEPT_E2_coverage']=dict(type='ACCEPT',states=stt('ACCEPT','after_E2'))
for n in ['ACCEPT_E4_ma_not_escalated','ACCEPT_E4_lam_relation_kept','ACCEPT_E4_order_invariant']: C[n]=dict(type='ACCEPT',states=stt('ACCEPT','after_E4'))
C['INFO_4_stems81']=dict(type='INFO',states=stt('K',always=True))
code_tree={'before':dict(sarf_tree=SARF,engine_dump2_blob=ED2,root_files=RF)}
for s in STAGES[1:]: code_tree[s]=dict(sarf_tree=TBD,engine_dump2_blob=TBD,root_files={f:TBD for f in ROOT_FILES})
export_outputs={'before':dict(E0_export=None,E2_coverage=None)}
for s in STAGES[1:]: export_outputs[s]=dict(E0_export=TBD,E2_coverage=TBD)
doc=dict(round='SARF_MORPH_EXPORT_REPAIR_01',batch='STEP_E0_partA',version=3,declared_at_utc=TS,supersedes='STEP2a_tests/expected_states_v2.json',
         engine_base='726131f',resource='release_v47',stages=STAGES,code_tree=code_tree,export_outputs=export_outputs,checks=C,
         principle='v3 adds root-file blobs (catalog/split/mabniyat/morph_engine_export) to code_tree per stage; ACCEPT_E0 compares export to engine features, not self-flags; after_E0 filled by a fingerprinted appendix before measurement')
body=json.dumps(doc,ensure_ascii=False,sort_keys=True); doc['self_fingerprint']=hashlib.sha256(body.encode()).hexdigest()
json.dump(doc,open(dst,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
fp=hashlib.sha256(open(dst,'rb').read()).hexdigest()
json.dump(dict(file='expected_states_v3.json',sha256=fp,declared_at_utc=TS,version=3),open(os.path.join(OUT,'expected_states_v3_fingerprint.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
print(json.dumps(dict(ok=True,checks=len(C),sarf=SARF[:8],root_files={k[:12]:v[:8] for k,v in RF.items()},sha=fp[:16]),ensure_ascii=False))
