import os,sys,hashlib
os.environ.pop('SARF_SEG_POLICY',None); os.environ.pop('SARF_SEG_RAISE_OPS',None)  # A = الغياب
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0,ROOT)
from sarf.pipeline import Pipeline
from sarf.catalog import Catalog
CAT=Catalog([os.path.join(ROOT,'operators_catalog.jsonl'),os.path.join(ROOT,'operators_catalog_split_vocalized.csv')])
PIPE=Pipeline(CAT)
M=os.path.expanduser("~/fractal/Huda/quran-simple-enhanced.txt")
lines=open(M,encoding='utf-8').read().splitlines()
ser=[]
for i in range(7,293):
    ws=' '.join(t for t in lines[i].split() if t!='<sel>')
    for w in PIPE.run(ws,until='segment').segments:
        ser.append('+'.join(s['text'] for s in w['slots']))
print(hashlib.sha256('\n'.join(ser).encode()).hexdigest()[:12])
