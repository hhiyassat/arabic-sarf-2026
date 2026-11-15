# -*- coding: utf-8 -*-
"""MASAQ-SEG-02: سين الاستقبال تُفصل عن المضارع (ي/ت بحركة مضارعة)، ولا تُفصل من الجذر السينيّ.
هذا هو الاختبار الجاري الوحيد (لا نسخة في tools/). يتحقق من:
  - الأجزاء والأدوار؛
  - التبليط/المحاذاة الداخلية: تسلسل نصوص الخانات يعيد بناء الكلمة تمامًا، بلا فجوة ولا تداخل؛
  - النص المتبقي بعد سَ = الفعل؛
  - حفظ اللاحقة (الضمير المتصل) حين وجودها؛
  - غيابُ الشاهد أو تعذّرُ العثور عليه = فشل (لا تمرير على None).
القياس مقابل MASAQ خارج هذا الاختبار عمدًا (عزل: اختبارات المحرك لا تقرأ المرجع).
  SARF_HFN=... python3 tests/test_seg_future_sin.py <engine_worktree>"""
import sys,re; WT=sys.argv[1] if len(sys.argv)>1 else '.'; sys.path.insert(0,WT)
from sarf.stages import run_ref
from sarf.cells import stem_licence
import sarf.quran_source as qs
FATHA='َ'; DAMMA='ُ'; SHADDA='ّ'
def sk(s): return re.sub('[ً-ْٰٓ-ٖۡۢـ]','',s)
def seg_of(ref,skel):
    aV=run_ref(ref).slots.get('analysis').value; aV=aV[list(aV.keys())[0]]
    for s in aV['segments']:
        if sk(s['word'])==skel: return s
    return None
def tiles(seg):
    """internal alignment: the ordered slot texts reconstruct the word exactly (no gap/overlap)."""
    return ''.join(x['text'] for x in seg['slots'])==seg['word']

def run_positive():
    ok=True
    # (ref, skel, expect_suffix): the last case carries an enclitic pronoun to test suffix preservation
    for ref,skel,suf in [('2:142','سيقول',False),('4:91','ستجدون',False),('6:138','سيجزيهم',True)]:
        seg=seg_of(ref,skel)
        if seg is None: print('FAIL POS',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        sl=[(x['text'],x['role']) for x in seg['slots']]
        head = len(sl)>=2 and sl[0][1]=='proclitic' and sl[0][0]=='سَ' and sl[1][1]=='stem'
        tiled = tiles(seg)                                   # boundary/alignment: exact reconstruction
        rest = seg['word'][len(sl[0][0]):]                   # remaining text after سَ
        rest_ok = rest==''.join(x['text'] for x in seg['slots'][1:])
        suf_ok = (not suf) or (sl[-1][1]=='enclitic' and len(sl[-1][0])>0)   # suffix preserved when expected
        passed = head and tiled and rest_ok and suf_ok
        print(('PASS' if passed else 'FAIL'),'POS',ref,skel,
              '| head=%s tile=%s rest=%s suffix=%s'%(head,tiled,rest_ok,suf_ok),'->',sl)
        ok&=passed
    return ok

def run_negative():
    ok=True
    for ref,skel in [('9:86','سورة'),('2:154','سبيل'),('17:1','سبحن'),('12:25','سيدها')]:
        seg=seg_of(ref,skel)
        if seg is None: print('FAIL NEG',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        sl=[(x['text'],x['role']) for x in seg['slots']]
        not_future_sin = not (sl[0][1]=='proclitic' and sk(sl[0][0])=='س')
        tiled = tiles(seg)
        passed = not_future_sin and tiled
        print(('PASS' if passed else 'FAIL'),'NEG',ref,skel,'| not_future_sin=%s tile=%s'%(not_future_sin,tiled),'->',sl)
        ok&=passed
    return ok

def run_detector_no_competitor():
    # SIGNAL, not proof: among words matching the strengthened شكل, the engine's licensor finds NO
    # whole-word non-verb reading. This reports "detector found no competitor"; it does NOT claim a
    # competitor is impossible — only that the current licensor surfaces none.
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
    passed = n>0 and not comp   # the signal we require: detector surfaces no whole-word competitor
    print(('PASS' if passed else 'FAIL'),
          'DETECTOR_NO_COMPETITOR: %d rule-shape words, detector found %d whole-word competitor(s)'%(n,len(comp)))
    if comp: print('  competitors surfaced:',comp[:20])
    return passed

if __name__=='__main__':
    ok = run_positive() & run_negative() & run_detector_no_competitor()
    print('ALL_PASS:',ok); sys.exit(0 if ok else 1)
