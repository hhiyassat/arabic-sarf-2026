# -*- coding: utf-8 -*-
import os,sys,json,hashlib,time
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0,HERE); sys.path.insert(0,ROOT)
import b3_decide as b
from sarf.analyze import analyze
from sarf.catalog import Catalog
CAT=Catalog([os.path.join(ROOT,'operators_catalog.jsonl'),os.path.join(ROOT,'operators_catalog_split_vocalized.csv')])
M=os.path.expanduser("~/fractal/Huda/quran-simple-enhanced.txt")
lines=open(M,encoding='utf-8').read().splitlines()
BAQ=[(i-6, [t for t in lines[i].split() if t!='<sel>']) for i in range(7,293)]   # 2:1..2:286
def segs(verse,policy,ops):
    for k in ('SARF_SEG_POLICY','SARF_SEG_RAISE_OPS'): os.environ.pop(k,None)
    if policy!='A': os.environ['SARF_SEG_POLICY']=policy
    if ops: os.environ['SARF_SEG_RAISE_OPS']='1'
    return analyze(CAT,verse)['segments']
def tot(segfn):
    k={'كامل':0,'قُسمت':0,'جذع':0}; ser=[]
    for ay,ws in BAQ:
        sg=segfn(' '.join(ws))
        for w in sg:
            sl=w['slots']; t=[s['type'] for s in sl]
            ser.append('+'.join(s['text'] for s in sl))
            if len(sl)>1:k['قُسمت']+=1
            elif t and t[0] in ('مبني','عامل','لفظ الجلالة'):k['كامل']+=1
            else:k['جذع']+=1
    return k,hashlib.sha256('\n'.join(ser).encode()).hexdigest()[:12]
t0=time.time()
states={}
states['A']=tot(lambda v:segs(v,'A',False))
states['B(مبني)']=tot(lambda v:segs(v,'B',False))
states['B(مبني+عامل)']=tot(lambda v:segs(v,'B',True))
states['B2(مبني)']=tot(lambda v:segs(v,'B2',False))
states['B2(مبني+عامل)']=tot(lambda v:segs(v,'B2',True))
# B3 (decide): per-word من A-slots + B-slots
import unicodedata,re
def _nz(s):
    s=unicodedata.normalize('NFC',s)
    while s and s[-1] in set('ًٌٍَُِّْ'): s=s[:-1]
    return s
def _skel(s):   # الحروفُ + الشدّةُ وحدها (النفيُ يحذف الفتحةَ فيلاصقُ الحرفُ الشدّة): لكشفِ إدغام النون
    s=unicodedata.normalize('NFC',s)
    return ''.join(c for c in s if c=='ّ' or not unicodedata.combining(c))
newsplits=[]; b3k={'كامل':0,'قُسمت':0,'جذع':0}; b3ser=[]
lost=0; noev=0
REJECTED={'R1: لا مضيف ملاصق':[], 'R3: حدٌّ يشطر':[], 'لا ابتداء بساكن':[]}
DEFERRED={}                       # miss -> examples (≤10)
REJ_count={}; DEF_count={}        # العددُ الكامل لكلّ مانع (لا المقتطع)
rej_total={'REJECTED':0,'DEFERRED':0}
changed=0                         # قراراتٌ انتقلت من رفضِ R1 القديم إلى تأجيل/مانعٍ آخر
gengaps={}                        # عائلةُ «فعل + نا/نّ بإدغام النون»
NUN_IDGHAM=re.compile('نّ')       # شدّةٌ على النون
for ay,ws in BAQ:
    sgA=segs(' '.join(ws),'A',False); sgB=segs(' '.join(ws),'B',False)
    for wi,wA in enumerate(sgA):
        word=wA['word']; A=[s['text'] for s in wA['slots']]
        lib=[s['text'] for s in sgB[wi]['slots']] if wi<len(sgB) else A
        d=b.decide(word,A,lib)
        ch=d['chosen']; b3ser.append('+'.join(ch))
        tA=[s['type'] for s in wA['slots']]
        if len(ch)>1:b3k['قُسمت']+=1
        elif tA and tA[0] in ('مبني','عامل','لفظ الجلالة'):b3k['كامل']+=1
        else:b3k['جذع']+=1
        if ch!=A and len(ch)>=len(A) and d['a_b3'] in ('فُصل بنصّ','فُصل تقديرًا'):
            ref=d['qarina']
            newsplits.append(dict(ref=f"2:{ay}",n=wi+1,word=word,A='+'.join(A),B3='+'.join(ch),
                cls=('نصّ:'+ref if d['a_b3']=='فُصل بنصّ' else 'نمط-تقدير:'+ref),
                alts=['+'.join(a) for a in d['alternatives']]))
        if d['a_b3']=='فُصل بلا دليل': noev+=1
        if len(A)>1 and len(ch)<len(A) and not any(c['parts']==A and c['barriers'] for c in d['candidates']): lost+=1
        for c in d['candidates']:
            if c['decision'] in ('REJECTED','DEFERRED'):
                rej_total[c['decision']]+=1
                bn,detail=c['barriers'][0]
                # القديم: كلُّها رفضُ R1 ؛ فكلُّ ما ليس REJECTED/R1 الآن قرارٌ تغيّر
                if not (c['decision']=='REJECTED' and bn.startswith('R1')): changed+=1
                if c['decision']=='REJECTED':
                    key=next((k for k in REJECTED if bn.startswith(k.split(':')[0])), bn)
                    if key not in REJECTED: REJECTED[key]=[]
                    REJ_count[key]=REJ_count.get(key,0)+1
                    if len(REJECTED[key])<10:
                        REJECTED[key].append(dict(ref=f"2:{ay}",word=word,rejected='+'.join(c['parts']),host=detail))
                else:
                    DEFERRED.setdefault(detail,[])
                    DEF_count[detail]=DEF_count.get(detail,0)+1
                    if len(DEFERRED[detail])<10:
                        DEFERRED[detail].append(dict(ref=f"2:{ay}",word=word,candidate='+'.join(c['parts'])))
        # GENERATOR_GAPS: فعل + نا/نّ بإدغام النون (تسجيلٌ لا بناء) — حيث لا يُخرج المقشِّر فصلًا نظيفًا «…+نا»
        sk=_skel(word)   # «س+نا» بإدغام نون (نّا): فعلٌ/ناسخ/جارّ + نا المتكلّمين
        if sk.endswith('نّا') and not (len(ch)>1 and _skel(ch[-1]) in ('نا','ننا')):
            gengaps.setdefault(_nz(word),{'refs':[],'b3':'+'.join(ch)})['refs'].append(f"2:{ay}")
states['B3(المصحَّح)']=(b3k,hashlib.sha256('\n'.join(b3ser).encode()).hexdigest()[:12])
dur=round(time.time()-t0,1)
out=dict(states={k:{'v':v[0],'sha':v[1]} for k,v in states.items()},
         guards=dict(LOST_WITHOUT_BARRIER=lost,NEW_SPLIT_WITHOUT_EVIDENCE=noev),
         newsplits=newsplits,
         rejected=dict(total=rej_total, REJECTED_counts=REJ_count, DEFERRED_counts=DEF_count,
                       REJECTED_examples=REJECTED, DEFERRED_examples=DEFERRED,
                       decisions_changed=changed),
         generator_gaps={k:dict(count=len(v['refs']),b3=v['b3'],refs=v['refs'][:10]) for k,v in gengaps.items()},
         seconds=dur, ayat=len(BAQ))
json.dump(out,open(os.path.join(HERE,'baqara_phase1.json'),'w'),ensure_ascii=False,indent=1)
print("=== البقرة (286 آية) ===  زمن %ss"%dur)
for k,(v,sh) in states.items(): print(f"  {k:16} كامل={v['كامل']:4} قُسمت={v['قُسمت']:4} جذع={v['جذع']:4} sha={sh}")
print("LOST_WITHOUT_BARRIER=%d  NEW_SPLIT_WITHOUT_EVIDENCE=%d"%(lost,noev))
print("فصولٌ جديدة في B3 ليست في A: %d"%len(newsplits))
print("REJECTED=%d  DEFERRED=%d  (قراراتٌ تغيّرت عن رفضِ R1 القديم: %d)"%(rej_total['REJECTED'],rej_total['DEFERRED'],changed))
print("REJECTED بالموانع:", REJ_count)
print("DEFERRED بما ينقصه:", DEF_count)
print("GENERATOR_GAPS (نا/نّ بإدغام):", {k:len(v['refs']) for k,v in gengaps.items()})
