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

def run_fasa_positive():
    # MASAQ-SEG-03: فَسَ/وَسَ — conj (ف/و) + future سَ + مضارع. First piece = conj, second = lone سَ proclitic.
    ok=True
    for ref,skel,suf in [('10:31','فسيقولون',False),('3:144','وسيجزي',False),('8:36','فسينفقونها',True)]:
        seg=seg_of(ref,skel)
        if seg is None: print('FAIL FASA+',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        sl=[(x['text'],x['role']) for x in seg['slots']]
        head = len(sl)>=3 and sk(sl[0][0]) in ('ف','و') and sl[1][1]=='proclitic' and sl[1][0]=='سَ' and sl[2][1]=='stem'
        tiled = tiles(seg)
        suf_ok = (not suf) or (sl[-1][1]=='enclitic' and len(sl[-1][0])>0)
        passed = head and tiled and suf_ok
        print(('PASS' if passed else 'FAIL'),'FASA+',ref,skel,'| head=%s tile=%s suffix=%s'%(head,tiled,suf_ok),'->',sl)
        ok&=passed
    return ok

def run_fasa_contrast():
    # MUST NOT split the سَ after ف/و: roots (فَسَجَدُوا, فَسَوَّىٰ, وَسَعَىٰ), the particle فَسَوۡفَ (3rd letter و),
    # and سَنَ futures (وَسَنَزِيدُ, وَسَنَجۡزِي) — ن restricted, deferred to a later family. Here the piece after
    # the conj must NOT be a lone سَ proclitic.
    ok=True
    for ref,skel in [('2:34','فسجدوا'),('2:29','فسوىهن'),('2:114','وسعى'),('4:30','فسوف')]:
        seg=seg_of(ref,skel)
        if seg is None: print('FAIL FASA-',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        sl=[(x['text'],x['role']) for x in seg['slots']]
        # if a conj was peeled, the NEXT piece must not be a lone سَ; otherwise the whole stem keeps سَ
        after_conj_not_sin = not (len(sl)>=2 and sk(sl[0][0]) in ('ف','و') and sl[1][1]=='proclitic' and sk(sl[1][0])=='س')
        tiled = tiles(seg)
        passed = after_conj_not_sin and tiled
        print(('PASS' if passed else 'FAIL'),'FASA-',ref,skel,'| no_sin_split=%s tile=%s'%(after_conj_not_sin,tiled),'->',sl)
        ok&=passed
    return ok

def run_lam_positive():
    # MASAQ-SEG-04: فصل اللام السابقة للفعل — لِ(kasra) before a مضارع, peeled as a function-NEUTRAL
    # proclitic (role 'proclitic', note 'لام سابقة للفعل'); no grammatical function assigned.
    ok=True
    for ref,skel,suf in [('2:185','ولتكملوا',False),('19:21','ولنجعله',True),('3:50','ولأحل',False)]:
        seg=seg_of(ref,skel)
        if seg is None: print('FAIL LAM+',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        sl=[(x['text'],x['role']) for x in seg['slots']]
        lam_peeled = any(sk(tx)=='ل' and ro=='proclitic' for tx,ro in sl)   # our neutral lam peel fired
        tiled = tiles(seg)
        suf_ok = (not suf) or (sl[-1][1]=='enclitic' and len(sl[-1][0])>0)
        passed = lam_peeled and tiled and suf_ok
        print(('PASS' if passed else 'FAIL'),'LAM+',ref,skel,'| lam_proclitic=%s tile=%s suffix=%s'%(lam_peeled,tiled,suf_ok),'->',sl)
        ok&=passed
    return ok

def run_lam_contrast():
    # our neutral lam peel must NOT fire on: divine لِلَّهِ (protected), lam of amr لْ (sukun), and
    # lam-of-jar before a NOUN (لِكُلِّ, لِيَوۡمِ — those are the operator layer's لِ, role 'operator').
    ok=True
    for ref,skel in [('2:115','ولله'),('2:186','فليستجيبوا'),('4:12','فلكل'),('21:47','ليوم')]:
        seg=seg_of(ref,skel)
        if seg is None: print('FAIL LAM-',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        sl=[(x['text'],x['role']) for x in seg['slots']]
        no_neutral_lam = not any(sk(tx)=='ل' and ro=='proclitic' for tx,ro in sl)   # MASAQ-SEG-04 did NOT fire
        tiled = tiles(seg)
        passed = no_neutral_lam and tiled
        print(('PASS' if passed else 'FAIL'),'LAM-',ref,skel,'| no_neutral_lam=%s tile=%s'%(no_neutral_lam,tiled),'->',sl)
        ok&=passed
    return ok

def run_fa_pronoun_positive():
    # MASAQ-SEG-05: فَ/وَ before a detached pronoun -> [conj, separate_pronoun]; verify entry_id too
    ok=True
    for ref,skel,eid in [('2:18','فهم','mabniyat:separate_pronoun:0010'),
                         ('2:184','فهو','mabniyat:separate_pronoun:0007'),
                         ('2:74','فهي','mabniyat:separate_pronoun:0008')]:
        seg=seg_of(ref,skel)
        if seg is None: print('FAIL FPRON+',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        sl=[(x['text'],x['role']) for x in seg['slots']]
        id_ok = seg['slots'][-1].get('lexicon')==[eid]
        passed = len(sl)==2 and sk(sl[0][0])=='ف' and sl[0][1]=='conj' and sl[1][1]=='lexicon' and tiles(seg) and id_ok
        print(('PASS' if passed else 'FAIL'),'FPRON+',ref,skel,'| id=%s'%id_ok,'->',sl); ok&=passed
    return ok

def run_fa_pronoun_unit(WT):
    # direct helper + synthetic engine checks (owner #2): فَهِمَ (root), harakat-differing forms, و-branch, entry ids
    import sarf.segment as S
    from sarf.stages import run_ref as _rr
    cap={}; orig=S._host
    def spy(w,t,o,a,b,lex,aws): cap['lex']=lex; return orig(w,t,o,a,b,lex,aws)
    S._host=spy; _rr('2:18'); lex=cap['lex']; S._host=orig
    ok=True
    # _separate_pronoun: exact + connecting-vowel (هُمُ) accepted; root/internal-diff rejected
    want_hit={'هُمۡ':'mabniyat:separate_pronoun:0010','هُوَ':'mabniyat:separate_pronoun:0007',
              'هُمُ':'mabniyat:separate_pronoun:0010','هُنَّ':'mabniyat:separate_pronoun:0011'}
    want_miss=['هِمَ','هَمَّ','هَمْ']          # فَهِمَ remainder, هَمَّ (همم root), هَمْ: internal harakat differ
    for r,eid in want_hit.items():
        m=S._separate_pronoun(r,lex); good=bool(m) and m[0]['entry_id']==eid
        print(('PASS' if good else 'FAIL'),'FPRON-unit hit',r,'->',[h['entry_id'] for h in m]); ok&=good
    for r in want_miss:
        m=S._separate_pronoun(r,lex); good=(m==[])
        print(('PASS' if good else 'FAIL'),'FPRON-unit miss',r,'->',[h.get('form') for h in m]); ok&=good
    # synthetic engine: فَهِمَ (root فهم) must NOT be pronoun-peeled; وَهُمۡ (و-branch) must peel [conj, pronoun]
    r1=S.segment_word('فَهِمَ',0,[],lex); s1=[(x['text'],x['role']) for x in r1['slots']]
    g1 = not any(x.get('note')=='ضمير منفصل' for x in r1['slots'])
    print(('PASS' if g1 else 'FAIL'),'FPRON-synthetic فَهِمَ ->',s1); ok&=g1
    r2=S.segment_word('وَهُمۡ',0,[],lex); s2=[(x['text'],x['role']) for x in r2['slots']]
    g2 = len(r2['slots'])==2 and sk(r2['slots'][0]['text'])=='و' and r2['slots'][0]['role']=='conj' and r2['slots'][1].get('note')=='ضمير منفصل'
    print(('PASS' if g2 else 'FAIL'),'FPRON-synthetic وَهُمۡ (و-branch) ->',s2); ok&=g2
    return ok

def run_fa_pronoun_contrast():
    # فَ + non-pronoun must NOT get the detached-pronoun peel: فَقَالُوا (verb), فَمَن (particle, peeled by another path)
    ok=True
    for ref,skel in [('4:153','فقالوا'),('2:38','فمن')]:
        seg=seg_of(ref,skel)
        if seg is None: print('FAIL FPRON-',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        sl=[(x['text'],x['role']) for x in seg['slots']]
        no_pron = not any(x.get('note')=='ضمير منفصل' for x in seg['slots'])
        print(('PASS' if (no_pron and tiles(seg)) else 'FAIL'),'FPRON-',ref,skel,'->',sl); ok&=(no_pron and tiles(seg))
    return ok

def run_sanna_positive():
    # MASAQ-SEG-06: سَ before نون المضارعة (future سَنَ) -> [سَ proclitic, verb]
    ok=True
    for ref,skel in [('4:57','سندخلهم'),('3:181','سنكتب'),('7:161','سنزيد'),('2:58','وسنزيد')]:
        seg=seg_of(ref,skel)
        if seg is None: print('FAIL SANNA+',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        sl=[(x['text'],x['role']) for x in seg['slots']]
        has_sin = any(x['text']=='سَ' and x['role']=='proclitic' and x.get('note')=='سين الاستقبال' for x in seg['slots'])
        passed = has_sin and tiles(seg)
        print(('PASS' if passed else 'FAIL'),'SANNA+',ref,skel,'->',sl); ok&=passed
    return ok

def run_sanna_contrast():
    # root/noun سَنَ must NOT split: سَنَابِل (نَ+ابِل alif), سَنَا (whole licensed); also سُنَّة (not سَ fatha)
    ok=True
    for ref,skel in [('2:261','سنابل'),('24:43','سنا'),('15:13','سنة')]:
        seg=seg_of(ref,skel)
        if seg is None: print('FAIL SANNA-',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        sl=[(x['text'],x['role']) for x in seg['slots']]
        no_split = not any(x.get('note')=='سين الاستقبال' for x in seg['slots'])
        print(('PASS' if (no_split and tiles(seg)) else 'FAIL'),'SANNA-',ref,skel,'->',sl); ok&=(no_split and tiles(seg))
    return ok

def run_protected_particle():
    # MASAQ-SEG-07: a word that wholly matches a mabniyat 'particle' is protected (kept whole),
    # not over-peeled: كَلَّا is not [كَ, لَّا]. Contrast: فَلَا/أَلَا (not whole-particles) stay segmented.
    ok=True
    for ref,skel in [('19:79','كلا'),('2:260','بلى')]:     # protected particles -> whole
        seg=seg_of(ref,skel)
        if seg is None: print('FAIL PART+',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        whole = len(seg['slots'])==1 and tiles(seg)
        print(('PASS' if whole else 'FAIL'),'PART+',ref,skel,'->',[(x['text'],x['role']) for x in seg['slots']]); ok&=whole
    for ref,skel in [('2:22','فلا'),('6:84','كلا')]:      # فَلَا (ف+لا) and كُلًّا (كل+tanwin) NOT protected-whole-particle
        seg=seg_of(ref,skel)
        if seg is None: print('FAIL PART-',ref,skel,'-> WITNESS NOT FOUND'); ok=False; continue
        # must NOT be tagged the protected-particle note
        notprot = not any(x.get('note')=='مبنيٌّ محميٌّ كاملاً: لا يُقشَّر منه عامل' for x in seg['slots'])
        print(('PASS' if (notprot and tiles(seg)) else 'FAIL'),'PART-',ref,skel,'->',[(x['text'],x['role']) for x in seg['slots']]); ok&=(notprot and tiles(seg))
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
    ok = (run_positive() & run_negative() & run_fasa_positive() & run_fasa_contrast()
          & run_lam_positive() & run_lam_contrast()
          & run_fa_pronoun_positive() & run_fa_pronoun_unit(WT) & run_fa_pronoun_contrast()
          & run_sanna_positive() & run_sanna_contrast() & run_protected_particle() & run_detector_no_competitor())
    print('ALL_PASS:',ok); sys.exit(0 if ok else 1)
