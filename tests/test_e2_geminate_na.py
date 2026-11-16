# -*- coding: utf-8 -*-
"""MASAQ-E2 (ORDER_11): a verb stem ending in a root نون assimilated into the pronoun «نا» is
represented as the DECOMPOSED face [stemنْ, نَا] (shadda split, tied to the single written cell),
NOT merged whole and NOT the old un-decomposed cut. Licensed only when the restored-نون stem is a
verb. «نا» kept as an attached pronoun (not named subject by form). SEG-08 not relaxed.
  SARF_HFN=... python3 tests/test_e2_geminate_na.py <engine_worktree>"""
import sys,re; WT=sys.argv[1] if len(sys.argv)>1 else '.'; sys.path.insert(0,WT)
from sarf.stages import run_ref
import sarf.quran_source as qs
def sk(s): return re.sub('[ً-ْٰٓ-ٖۡۢـ]','',s)
def seg_of(ref,skel):
    aV=run_ref(ref).slots.get('analysis').value; aV=aV[list(aV.keys())[0]]
    for s in aV['segments']:
        if sk(s['word'])==skel: return s
    return None
ok=True
# POSITIVE: the 4 declared forms decompose [stem ending نْ, نَا enclitic]
for ref,skel in [('2:8','ءامنا'),('12:21','مكنا'),('6:108','زينا'),('2:118','بينا')]:
    seg=seg_of(ref,skel)
    if seg is None: print('FAIL E2+',ref,skel,'-> NOT FOUND'); ok=False; continue
    sl=[(x['text'],x.get('role')) for x in seg['slots']]
    good = len(sl)==2 and sl[0][1]=='stem' and sl[0][0].endswith('نْ') and sl[1]==('نَا','enclitic') \
           and any('MASAQ-E2' in (x.get('note') or '') for x in seg['slots'])
    print(('PASS' if good else 'FAIL'),'E2+',ref,skel,'->',sl); ok&=good
# CONTRAST: not decomposed — كُنَّا (existing operator path, not E2), جَنَّة (noun), nun-wiqaya مَكَّنِّي, dual ظَنَّا
for ref,skel,why in [('4:97','كنا','operator-path كُنْ+نَا, not MASAQ-E2'),
                     ('25:15','جنة','noun'),('18:95','مكني','nun-wiqaya نِّي'),('2:230','ظنا','dual آ not نا'),('6:53','فتنا','root-فاء wrongly peeled -> E2 must NOT fire on remainder (word-start guard)')]:
    seg=seg_of(ref,skel)
    if seg is None: print('FAIL E2-',ref,skel,'-> NOT FOUND'); ok=False; continue
    no_e2 = not any('MASAQ-E2' in (x.get('note') or '') for x in seg['slots'])
    print(('PASS' if no_e2 else 'FAIL'),'E2-',ref,skel,'(%s) ->'%why,[(x['text'],x.get('role')) for x in seg['slots']]); ok&=no_e2
print('ALL_PASS:',ok); sys.exit(0 if ok else 1)
