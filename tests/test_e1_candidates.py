# -*- coding: utf-8 -*-
"""E1 (ORDER_11): stem_licence preserves ALL root candidates (deterministic, deferred), and the
'فعل بالكتابة' evidence is bound to the FULL accepted face (root AND form_class), not the root alone.
  SARF_HFN=... python3 tests/test_e1_candidates.py <engine_worktree>"""
import sys,os; WT=sys.argv[1] if len(sys.argv)>1 else '.'; sys.path.insert(0,WT)
from sarf.cells import stem_licence
from sarf.root import morph, hfn

ok=True
# 1) multiple candidates preserved + deferred; excluded ones are NOT in HFN roots (documented reason)
L=list(stem_licence('يَمُدُّ'))
roots=[(r,c) for k,r,c in L]
has_both = ('مدد','I') in roots and ('ميد','IX') in roots and all(k=='فعل محتمل' for k,r,c in L)
cand=morph('يَمُدُّ').get('candidates') or []
excluded=[rc for rc in cand if rc not in roots]
excl_reason_ok = all(r not in hfn().roots for r,c in excluded)   # مود/IX excluded because مود ∉ HFN
print(('PASS' if (has_both and excl_reason_ok) else 'FAIL'),'يَمُدُّ preserves [مدد/I, ميد/IX] deferred; excluded %s (∉HFN: %s) -> %s'%(excluded,excl_reason_ok,L))
ok &= has_both and excl_reason_ok

# 2) face-identity binding: same root, different build — evidence does NOT transfer to the competitor
#    ينصرون: نصر/I is the accepted face (فعل بالكتابة); نصر/IV shares the root but must stay فعل محتمل
L2=list(stem_licence('يُنصَرُونَ'))
d={(r,c):k for k,r,c in L2 if 'فعل' in k}
binding_ok = d.get(('نصر','I'))=='فعل بالكتابة' and d.get(('نصر','IV'))=='فعل محتمل'
print(('PASS' if binding_ok else 'FAIL'),'ينصرون: نصر/I=بالكتابة, نصر/IV=محتمل (evidence bound to full face) ->',[(k,r,c) for k,r,c in L2 if 'فعل' in k])
ok &= binding_ok

# 3) at most ONE face may carry 'فعل بالكتابة' per word, and only the morph-accepted (root,form_class)
for w in ['يُنصَرُونَ','يَمُدُّ','كَتَبَ','يُنفِقُونَ']:
    Lw=list(stem_licence(w)); m=morph(w) or {}
    byk=[(r,c) for k,r,c in Lw if k=='فعل بالكتابة']
    acc=(m.get('root'),m.get('form_class'))
    good = len(byk)<=1 and all(rc==acc for rc in byk)
    print(('PASS' if good else 'FAIL'),'%-12s بالكتابة faces=%s accepted=%s'%(w,byk,acc)); ok&=good

# 4) determinism: candidates identical across hash seeds (run in subprocess)
import subprocess
def seedrun(seed):
    return subprocess.run([sys.executable,'-c',
        'import sys;sys.path.insert(0,%r)\nfrom sarf.cells import stem_licence\nprint(list(stem_licence("يَمُدُّ")))'%WT],
        capture_output=True,text=True,env=dict(os.environ,PYTHONHASHSEED=str(seed))).stdout.strip()
seeds=[seedrun(s) for s in (0,1,12345)]
det = len(set(seeds))==1 and seeds[0]
print(('PASS' if det else 'FAIL'),'seed-invariant stem_licence(يَمُدُّ):',seeds[0]); ok&=bool(det)

print('ALL_PASS:',ok); sys.exit(0 if ok else 1)
