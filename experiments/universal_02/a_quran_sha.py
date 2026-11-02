import os,sys,hashlib
os.environ.pop('SARF_SEG_POLICY',None); os.environ.pop('SARF_SEG_RAISE_OPS',None)
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0,ROOT)
from sarf.pipeline import Pipeline
from sarf.catalog import Catalog
PIPE=Pipeline(Catalog([os.path.join(ROOT,'operators_catalog.jsonl'),os.path.join(ROOT,'operators_catalog_split_vocalized.csv')]))
M=os.path.expanduser("~/fractal/Huda/quran-simple-enhanced.txt")
ser=[]
for ln in open(M,encoding='utf-8').read().splitlines():
    v=' '.join(t for t in ln.split() if t!='<sel>')
    for w in PIPE.run(v,until='segment').segments:
        ser.append('+'.join(s['text'] for s in w['slots']))
print(hashlib.sha256('\n'.join(ser).encode()).hexdigest()[:12])
