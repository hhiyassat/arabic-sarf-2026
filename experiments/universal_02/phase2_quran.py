# -*- coding: utf-8 -*-
import os,sys,json,hashlib,time,unicodedata,csv,re
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0,HERE); sys.path.insert(0,ROOT)
import b3_decide as b
from sarf.pipeline import Pipeline
from sarf.catalog import Catalog
CAT=Catalog([os.path.join(ROOT,'operators_catalog.jsonl'),os.path.join(ROOT,'operators_catalog_split_vocalized.csv')])
PIPE=Pipeline(CAT)   # التقطيعُ وحده (until='segment')؛ مرحلةُ الصرف/الجذر لاحقةٌ، تُعطِب بعضَ الآي، ولا نستعملها (نقرأ slots فقط)
M=os.path.expanduser("~/fractal/Huda/quran-simple-enhanced.txt")
lines=open(M,encoding='utf-8').read().splitlines()
AYA=[7,286,200,176,120,165,206,75,129,109,123,111,43,52,99,128,111,110,98,135,112,78,118,64,77,227,93,88,69,60,34,30,73,54,45,83,182,88,75,85,54,53,89,59,37,35,38,29,18,45,60,49,62,55,78,96,29,22,24,13,14,11,11,18,12,12,30,52,52,44,28,28,20,56,40,31,50,40,46,42,29,19,36,25,22,17,19,26,30,20,15,21,11,8,8,19,5,8,8,11,11,8,3,9,5,4,7,3,6,3,5,4,5,6]
assert sum(AYA)==6236, sum(AYA)
# خريطةُ السطر → (سورة، آية)
L2SA=[]; s=1; a=1
for cnt in AYA:
    for k in range(cnt): L2SA.append((s,k+1))
    s+=1
assert len(L2SA)==6236
HAR=set('ًٌٍَُِّْ')
def nz(x):
    x=unicodedata.normalize('NFC',x)
    while x and x[-1] in HAR: x=x[:-1]
    return x
def skel(x):
    x=unicodedata.normalize('NFC',x)
    return ''.join(c for c in x if c=='ّ' or not unicodedata.combining(c))
def segs(verse,policy,ops):
    for k in ('SARF_SEG_POLICY','SARF_SEG_RAISE_OPS'): os.environ.pop(k,None)
    if policy!='A': os.environ['SARF_SEG_POLICY']=policy
    if ops: os.environ['SARF_SEG_RAISE_OPS']='1'
    return PIPE.run(verse,until='segment').segments
def cl(sl,chosen=None):
    t=[x['type'] for x in sl]; n=len(chosen) if chosen is not None else len(sl)
    if n>1: return 'قُسمت'
    if t and t[0] in ('مبني','عامل','لفظ الجلالة'): return 'كامل'
    return 'جذع'
CFG=[('A','A',False),('B(مبني)','B',False),('B(مبني+عامل)','B',True),('B2(مبني)','B2',False),('B2(مبني+عامل)','B2',True)]
tot={n:{'كامل':0,'قُسمت':0,'جذع':0} for n,_,_ in CFG}; tot['B3(المصحَّح)']={'كامل':0,'قُسمت':0,'جذع':0}
ser={n:[] for n in tot}
persura={}   # sura -> {state->counts}
newsplits=[]; REJ_c={}; DEF_c={}; REJX={}; DEFX={}; rtot={'REJECTED':0,'DEFERRED':0}; changed=0
gaps={}; lost=0; noev=0
adef={}      # BASELINE_DEFECTS: تنوينٌ على مبنيّ (صنفُ سَفِي+هاً)
NAMED_DEFECTS={'سَفِيهاً':'سَفِي+هاً','كَبِيراً':'كَ+بِيراً'}
t0=time.time()
for li,line in enumerate(lines):
    su,ay=L2SA[li]
    verse=' '.join(t for t in line.split() if t!='<sel>')
    sg={}
    for name,pol,ops in CFG: sg[name]=segs(verse,pol,ops)
    ps=persura.setdefault(su,{n:{'كامل':0,'قُسمت':0,'جذع':0} for n in tot})
    for name,_,_ in CFG:
        for w in sg[name]:
            c=cl(w['slots']); tot[name][c]+=1; ps[name][c]+=1; ser[name].append('+'.join(x['text'] for x in w['slots']))
    # B3 من A + B
    sgA=sg['A']; sgB=sg['B(مبني)']
    for wi,wA in enumerate(sgA):
        word=wA['word']; A=[x['text'] for x in wA['slots']]
        lib=[x['text'] for x in sgB[wi]['slots']] if wi<len(sgB) else A
        d=b.decide(word,A,lib); ch=d['chosen']
        c=cl(wA['slots'],ch); tot['B3(المصحَّح)'][c]+=1; ps['B3(المصحَّح)'][c]+=1; ser['B3(المصحَّح)'].append('+'.join(ch))
        if ch!=A and len(ch)>=len(A) and d['a_b3'] in ('فُصل بنصّ','فُصل تقديرًا'):
            newsplits.append(dict(ref=f"{su}:{ay}",n=wi+1,word=word,A='+'.join(A),B3='+'.join(ch),
                cls=('نصّ:'+d['qarina'] if d['a_b3']=='فُصل بنصّ' else 'نمط-تقدير:'+d['qarina']),
                alts=['+'.join(x) for x in d['alternatives']]))
        if d['a_b3']=='فُصل بلا دليل': noev+=1
        if len(A)>1 and len(ch)<len(A) and not any(x['parts']==A and x['barriers'] for x in d['candidates']): lost+=1
        for cc in d['candidates']:
            if cc['decision'] in ('REJECTED','DEFERRED'):
                rtot[cc['decision']]+=1; bn,detail=cc['barriers'][0]
                if not (cc['decision']=='REJECTED' and bn.startswith('R1')): changed+=1
                if cc['decision']=='REJECTED':
                    REJ_c[bn]=REJ_c.get(bn,0)+1; REJX.setdefault(bn,[])
                    if len(REJX[bn])<10: REJX[bn].append(dict(ref=f"{su}:{ay}",word=word,rejected='+'.join(cc['parts']),host=detail))
                else:
                    DEF_c[detail]=DEF_c.get(detail,0)+1; DEFX.setdefault(detail,[])
                    if len(DEFX[detail])<10: DEFX[detail].append(dict(ref=f"{su}:{ay}",word=word,candidate='+'.join(cc['parts'])))
        sk=skel(word)
        if sk.endswith('نّا') and not (len(ch)>1 and skel(ch[-1]) in ('نا','ننا')):
            gaps.setdefault(nz(word),{'refs':[],'b3':'+'.join(ch)})['refs'].append(f"{su}:{ay}")
        # BASELINE_DEFECTS: شريحةٌ مبنيّة تحمل تنوينًا (الضمير لا يُنوَّن) → عيبُ A (صنفُ سَفِيهاً)
        for sl_ in wA['slots']:
            if sl_['type'] in ('مبني','عامل') and ('ً' in sl_['text'] or 'ٌ' in sl_['text'] or 'ٍ' in sl_['text']):
                adef.setdefault(nz(word),{'A':'+'.join(A),'refs':[],'slot':sl_['text']})['refs'].append(f"{su}:{ay}")
        if nz(word) in NAMED_DEFECTS:
            adef.setdefault(nz(word),{'A':'+'.join(A),'refs':[],'slot':'—'})['refs'].append(f"{su}:{ay}")
shas={n:hashlib.sha256('\n'.join(v).encode()).hexdigest()[:12] for n,v in ser.items()}
dur=round(time.time()-t0,1)
# CSV الفصول الجديدة كاملًا
with open(os.path.join(HERE,'quran_new_splits.csv'),'w',encoding='utf-8',newline='') as f:
    w=csv.writer(f); w.writerow(['السورة:الآية','#','الكلمة','A','B3','صنف الدليل','البدائل'])
    for r in newsplits: w.writerow([r['ref'],r['n'],r['word'],r['A'],r['B3'],r['cls'],' | '.join(r['alts'])])
out=dict(ayat=6236,suras=114,seconds=dur,
  states={n:{'v':tot[n],'sha':shas[n]} for n in tot},
  persura={str(s):persura[s] for s in sorted(persura)},
  guards=dict(LOST_WITHOUT_BARRIER=lost,NEW_SPLIT_WITHOUT_EVIDENCE=noev),
  newsplits_count=len(newsplits),
  rejected=dict(total=rtot,REJECTED_counts=REJ_c,DEFERRED_counts=DEF_c,REJECTED_examples=REJX,DEFERRED_examples=DEFX,decisions_changed=changed),
  generator_gaps={k:dict(count=len(v['refs']),b3=v['b3'],refs=v['refs'][:10]) for k,v in gaps.items()},
  baseline_defects={k:dict(A=v['A'],slot=v['slot'],count=len(v['refs']),refs=v['refs'][:10]) for k,v in adef.items()})
json.dump(out,open(os.path.join(HERE,'quran_phase2.json'),'w'),ensure_ascii=False,indent=1)
print("DONE %ss ayat=6236"%dur)
for n in tot: print("  %-16s كامل=%5d قُسمت=%5d جذع=%5d sha=%s"%(n,tot[n]['كامل'],tot[n]['قُسمت'],tot[n]['جذع'],shas[n]))
print("guards LOST=%d NOEV=%d | newsplits=%d | REJECTED=%d DEFERRED=%d changed=%d"%(lost,noev,len(newsplits),rtot['REJECTED'],rtot['DEFERRED'],changed))
print("gaps=%d defects=%d"%(len(gaps),len(adef)))
