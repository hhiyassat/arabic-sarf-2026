# -*- coding: utf-8 -*-
"""MASAQ-SEG-02: سين الاستقبال تُفصل عن المضارع (ي/ت بحركة مضارعة)، ولا تُفصل من الجذر السينيّ.
الأدلة ثلاثة: (1) مواضع موجبة تُفصل فعلاً؛ (2) مواضع جذرية/مضمومة لا تُفصل؛ (3) انعدام المنافس:
لا كلمةَ على شكل القاعدة يُرخَّص وجهُها الكامل اسمًا/علمًا. غيابُ الشاهد أو تعذّرُ العثور = فشل.
  SARF_HFN=... python3 tests/test_seg_future_sin.py <engine_worktree>"""
import sys,re; WT=sys.argv[1] if len(sys.argv)>1 else '.'; sys.path.insert(0,WT)
from sarf.stages import run_ref
from sarf.cells import stem_licence
import sarf.quran_source as qs
FATHA='َ'; DAMMA='ُ'; SHADDA='ّ'
def sk(s): return re.sub('[ً-ْٰٓ-ٖۡۢـ]','',s)
def find(ref,skel):
    aV=run_ref(ref).slots.get('analysis').value; aV=aV[list(aV.keys())[0]]
    for s in aV['segments']:
        if sk(s['word'])==skel: return [(x['text'],x['role']) for x in s['slots']]
    return None

def run_positive():
    ok=True
    for ref,skel in [('2:142','سيقول'),('4:91','ستجدون')]:
        sl=find(ref,skel)
        if sl is None: print('FAIL POS',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        passed = len(sl)>=2 and sl[0][1]=='proclitic' and sk(sl[0][0])=='س' and sl[1][1]=='stem'
        print(('PASS' if passed else 'FAIL'),'POS',ref,skel,'->',sl); ok&=passed
    return ok

def run_negative():
    ok=True
    for ref,skel in [('9:86','سورة'),('2:154','سبيل'),('17:1','سبحن'),('12:25','سيدها')]:
        sl=find(ref,skel)
        if sl is None: print('FAIL NEG',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        not_future_sin = not (sl[0][1]=='proclitic' and sk(sl[0][0])=='س')
        print(('PASS' if not_future_sin else 'FAIL'),'NEG',ref,skel,'->',sl); ok&=not_future_sin
    return ok

def run_competition():
    # every word matching the strengthened شكل: whole word must NOT license as non-verb (no discarded face)
    comp=[]; n=0; seen=set()
    for s,v,t in qs.rows():
        for w in t.split():
            if w in seen: continue
            seen.add(w)
            m=re.match(r'^سَ(ي|ت)([ؘ-ًؚ-ْٰۜ-ۭ]*)',w)
            if not m: continue
            marks=set(m.group(2))
            if SHADDA in marks or not (marks & {FATHA,DAMMA}): continue
            n+=1
            if [x for x in stem_licence(w) if 'فعل' not in x[0]]: comp.append((sk(w),))
    passed = n>0 and not comp
    print(('PASS' if passed else 'FAIL'),'COMPETITION: %d rule-shape words, %d with discarded whole-word competitor'%(n,len(comp)))
    if comp: print('  competitors:',comp[:20])
    return passed

if __name__=='__main__':
    ok = run_positive() & run_negative() & run_competition()
    print('ALL_PASS:',ok); sys.exit(0 if ok else 1)
