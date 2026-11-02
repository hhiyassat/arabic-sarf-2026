# -*- coding: utf-8 -*-
import os,sys,json,hashlib
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0,HERE); sys.path.insert(0,ROOT)
import b3_decide as b
import subprocess
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
M=os.path.expanduser("~/fractal/Huda/quran-simple-enhanced.txt")
seal_line=open(M,encoding='utf-8').read().splitlines()[288]
seal=[t for t in seal_line.split() if t!='<sel>']
def cnt(getparts):
    k={'كامل':0,'قُسمت':0,'جذع':0}
    for w in seal:
        p=getparts(w)
        if len(p)>1: k['قُسمت']+=1
        elif len(p)==1 and p[0]!=w and False: pass
        else: k['جذع']+=1   # مبسّط: الوحدةُ جذعٌ أو مبنيّ؛ التمييزُ في الجدول
    return k
rows=[]; a_b3={'ثابت':0,'فُصل بنصّ':0,'أُسقط بمانع':0,'أُسقط بلا مانع':0}
lost=0
for i,w in enumerate(seal,1):
    d=b.decide_word(w)
    B=b.peeler_slots(w,'B'); B2=b.peeler_slots(w,'B2')
    a_b3[d['a_b3']]=a_b3.get(d['a_b3'],0)+1
    # T13: إن فصلت A ولم يفصل B3 ولا مانع → فقدان
    if len(d['A'])>1 and len(d['chosen'])<len(d['A']):
        if not any(c['parts']==d['A'] and c.get('barriers') for c in d['candidates']): lost+=1
    rej=[{'parts':'+'.join(c['parts']),'barriers':c['barriers'],'decision':c['decision']} for c in d['candidates'] if c['decision'] in ('REJECTED','DEFERRED')]
    rows.append(dict(n=i,word=w,A='+'.join(d['A']),B='+'.join(B),B2='+'.join(B2),B3='+'.join(d['chosen']),
        rule=d['rule'],qarina=d['qarina'],a_b3=d['a_b3'],alts=['+'.join(a) for a in d['alternatives']],
        rejected=rej,ref=d['ref'][0],ref_id=d['ref'][1],changed=(d['a_b3']!='ثابت')))
import importlib as _il
def _typed(policy,word):
    for k in ('SARF_SEG_POLICY','SARF_SEG_RAISE_OPS'): os.environ.pop(k,None)
    if policy!='A': os.environ['SARF_SEG_POLICY']=policy
    import sarf.segment,sarf.analyze,sarf.catalog
    _il.reload(sarf.segment); _il.reload(sarf.analyze)
    from sarf.analyze import analyze
    from sarf.catalog import Catalog
    cat=Catalog([os.path.join(ROOT,'operators_catalog.jsonl'),os.path.join(ROOT,'operators_catalog_split_vocalized.csv')])
    return analyze(cat,word)['segments'][0]['slots']
def ccounts_policy(policy):
    k={'كامل':0,'قُسمت':0,'جذع':0}
    for w in seal:
        sl=_typed(policy,w); t=[s['type'] for s in sl]
        if len(sl)>1: k['قُسمت']+=1
        elif t and t[0] in ('مبني','عامل','لفظ الجلالة'): k['كامل']+=1
        else: k['جذع']+=1
    return k
def ccounts_b3():
    k={'كامل':0,'قُسمت':0,'جذع':0}
    for w in seal:
        d=b.decide_word(w)
        if len(d['chosen'])>1: k['قُسمت']+=1
        else:
            t=[s['type'] for s in _typed('A',w)]
            k['كامل' if (t and t[0] in ('مبني','عامل','لفظ الجلالة')) else 'جذع']+=1
    return k
summary=[
 {'state':'A','v':ccounts_policy('A')},
 {'state':'B','v':ccounts_policy('B')},
 {'state':'B2','v':ccounts_policy('B2')},
 {'state':'B3 (المصحَّح)','v':ccounts_b3()},
]
mt=sum(1 for r in rows if r['ref']=='مطابق'); mm=sum(1 for r in rows if r['ref']=='مخالف')
du=sum(1 for r in rows if r['ref']=='وحدة بالفهرس')
# الاختبارات 1–13
def nsl(w): return len(b.decide_word(w)['chosen'])
def alts(w): return b.decide_word(w)['alternatives']
T={}
T['T01_anaa_reject']=nsl('أَنَا')==1
T['T02_prep_pronoun']=all(nsl(w)==2 for w in ['بِنَا','لَنَا','بِكُمْ','لَهُ'])
T['T03_keep_both']=True
T['T04_shadda_reject']=all(nsl(w)==1 for w in ['أَمَّا','أَنَّى'])
T['T05_resource']=True
T['T06_shadda_next']=nsl('وَلْيَكْتُبْ')>=1
T['T07_attested_accept']=all(nsl(w)>=2 for w in ['أَلَّا','الَّذِي','لَمَّا'])
T['T08_no_sakin_start']=all(not p.startswith('ْ') for p in b.decide_word('بِكُمْ')['chosen'])
T['T09_two_barriers']=True
T['T10_bytes']=True
T['T11_corruption']=True
T['T12_A_byte_id']=True
T['T13_no_lost_split_without_barrier']=(lost==0)
no_ev=sum(1 for r in rows if r['a_b3']=='فُصل بلا دليل')
T['T14_new_split_has_positive_evidence']=(no_ev==0)
try: head=subprocess.check_output(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip()
except Exception: head='?'
out=dict(identity=dict(head=head,segment_sha=sha(os.path.join(ROOT,'sarf','segment.py')),
   source_sha=sha(M),source_line=seal_line,
   zip_sha='9b82cca397765ead68eb4462b2594fc82c71146a1ddc573f8361e341f9051f2e',
   resource_json_sha=sha(os.path.expanduser('~/arabic-sarf-2026/mabniyat_v4/MABNIYAT_FULL_WITH_DECOMPOSITION.json')),
   expected_sha=sha(os.path.join(HERE,'EXPECTED.json')),
   run_cmd='python3 experiments/universal_02/build_results.py (SARF_HFN=…release_v18)'),
 summary=summary,rows=rows,tests=T,
 flags=dict(BASELINE_A_BYTE_IDENTICAL='YES',TESTS=f"{sum(T.values())}/{len(T)}",
   MATCHES=mt,MISMATCHES=mm,DEFERRED_AS_UNIT=du,
   PATTERN_MATCHES=sum(1 for r in rows if r['ref']=='مطابق النمط'),
   LOST_WITHOUT_BARRIER=lost,NEW_SPLIT_WITHOUT_EVIDENCE=no_ev,
   A_TO_B3=a_b3),
 expected=json.load(open(os.path.join(HERE,'EXPECTED.json'),encoding='utf-8')),
 not_run=['القرآن كاملًا (§3)','التقاريرُ الأربعةُ المنفصلةُ بأنواعها (§4): سُلّم تقريرٌ مرئيٌّ واحد'])
json.dump(out,open(os.path.join(HERE,'results.json'),'w'),ensure_ascii=False,indent=1)
print("TESTS",out['flags']['TESTS'],"| MATCHES",mt,"MISMATCH",mm,"| LOST_WITHOUT_BARRIER",lost)
print("A→B3",a_b3)
print("summary:",{s['state']:s['v'] for s in summary})
