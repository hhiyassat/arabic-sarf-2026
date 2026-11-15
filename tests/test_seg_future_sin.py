# -*- coding: utf-8 -*-
"""MASAQ-SEG-02: سين الاستقبال تُفصل عن المضارع (ي/ت)، ولا تُفصل من الجذر السينيّ.
الاستعمال: SARF_HFN=... python3 tests/test_seg_future_sin.py <engine_worktree>"""
import sys,os,re; WT=sys.argv[1] if len(sys.argv)>1 else '.'; sys.path.insert(0,WT)
from sarf.stages import run_ref
def pieces(ref,skel):
    aV=run_ref(ref).slots.get('analysis').value; aV=aV[list(aV.keys())[0]]
    for s in aV['segments']:
        if re.sub('[ً-ْٰٓ-ٖۡۢـ]','',s['word'])==skel: return [x['text'] for x in s['slots']], [x['role'] for x in s['slots']]
    return None,None
POS=[('2:142','سيقول'),('4:91','ستجدون')]       # يجب أن تُفصل: [سَ proclitic, verb]
NEG=[('2:186','سءلك'),('2:261','سنابل'),('17:1','سبحن'),('2:23','سورة')]  # يجب ألّا تُفصل (جذر/مضموم)
ok=True
for ref,sk in POS:
    t,r=pieces(ref,sk)
    passed = t and len(t)>=2 and r[0]=='proclitic' and re.sub('[^س]','',t[0])=='س'
    print(('PASS' if passed else 'FAIL'),'POS',ref,sk,'->',t); ok&=bool(passed)
for ref,sk in NEG:
    t,r=pieces(ref,sk)
    passed = (t is None) or (len(t)==1) or (r[0]!='proclitic')
    print(('PASS' if passed else 'FAIL'),'NEG',ref,sk,'->',t); ok&=bool(passed)
print('ALL_PASS:',ok); sys.exit(0 if ok else 1)
