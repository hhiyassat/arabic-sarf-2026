"""tools/morph_inventory.py <OUT.jsonl.gz> [1-114] — جرد الحالة الفعلية للتقشير والتحليل الصرفي (MORPH_COMPLETION_01، الجرد).

للقياس وحده، ولا يغيّر شيئاً في المحلّل: يقرأ تحليل كل آيةٍ (analyze_cached، كما في tools/eval_root.py) ويقابل كل كلمةٍ بكلمة QAC
بالمحاذاة نفسها التي يستعملها eval_root، ثم يسجّل لكل كلمة:
- التقشير: جذوعنا (خانات «جذع») مقابل جذع QAC (المقطع الذي ليس سابقةً ولا لاحقة)، بالهيكل skel المستعمل في eval_root للقياس وحده
  (QAC مرجع قياس، لا مدخل). وتصنيف الخلاف: NO_STEM، MULTI_STEM، EXTRA_SUFFIX، EXTRA_PREFIX، STEM_TRUNCATED، OTHER.
- الجذر والوزن: نتيجة morph لكل جذعٍ (الحالة، والجذر، والوزن، والمستوى، والسبب، والمرشّحات) مقابل جذر QAC ووزنه، للأفعال والأسماء معاً
  (eval_root يقيس الأفعال وحدها).
- خصائص QAC: الصنف (V/N/…)، والزمن (PERF/IMPF/IMPV)، والبناء للمجهول، وعلامة العلم، والسوابق واللواحق.
والوقوع الذي لم تُحاذَ كلمته يُسجَّل UNALIGNED، ولا يُحذف."""
import collections, difflib, gzip, json, os, re, sys
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.analyze_cache import analyze_cached
from sarf.catalog import Catalog
from sarf.root import morph

cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
OUT = sys.argv[1]
lo, hi = (int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else '1-114').split('-'))
HZ = str.maketrans('أإؤئآ', 'ءءءءء')
VF = {str(i): r for i, r in enumerate(['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII'])}


def skel(t):
    """هيكل القياس (eval_root): للمحاذاة بمرجع القياس وحده، لا للتحليل"""
    t = re.sub('[ً-ٰٟۖ-ࣰۭ-ࣲـ]', '', t or '')
    return t.translate(str.maketrans('ٱأإآؤئىة', 'اااااييه')).replace('ء', '')


Q = collections.defaultdict(list)
for l in open(H + 'data/quran-morphology.txt', encoding='utf-8'):
    loc, form, tag, feats = l.rstrip('\n').split('\t')
    s, v, w, k = map(int, loc.split(':'))
    if lo <= s <= hi:
        Q[(s, v, w)].append((form, tag, feats.split('|')))


def qac_word(segs):
    pre = [f for f, t, fe in segs if 'PREF' in fe]
    suf = [f for f, t, fe in segs if 'SUFF' in fe]
    stem = [(f, t, fe) for f, t, fe in segs if 'PREF' not in fe and 'SUFF' not in fe]
    f0, t0, fe0 = stem[0] if stem else ('', '', [])
    g = lambda p: next((x[len(p):] for x in fe0 if x.startswith(p)), '')
    return dict(stem=''.join(f for f, _, _ in stem), n_stem_segs=len(stem), tag=t0, root=g('ROOT:').translate(HZ), lemma=g('LEM:'),
                vf=VF.get(g('VF:'), '') if t0 == 'V' else '', aspect=next((x for x in fe0 if x in ('PERF', 'IMPF', 'IMPV')), ''),
                passive='PASS' in fe0, proper='PN' in fe0, prefixes=pre, suffixes=suf, feats=fe0)


def peel_class(ours, q):
    if not ours:
        return 'NO_STEM'
    if len(ours) > 1:
        return 'MULTI_STEM'
    a, b = skel(ours[0]), skel(q)
    if a == b:
        return 'OK'
    if a.startswith(b):
        return 'EXTRA_SUFFIX'
    if a.endswith(b):
        return 'EXTRA_PREFIX'
    if b.startswith(a) or b.endswith(a) or a in b:
        return 'STEM_TRUNCATED'
    if b in a:
        return 'EXTRA_BOTH'
    return 'OTHER'


n = collections.Counter()
with gzip.open(OUT, 'wt', encoding='utf-8') as f:
    for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'):
        s, v, text = l.rstrip('\n').split('\t'); s, v = int(s), int(v)
        if not lo <= s <= hi:
            continue
        a = analyze_cached(cat, text)
        qws = sorted(k[2] for k in Q if k[0] == s and k[1] == v)
        qtext = [skel(''.join(fm for fm, _, _ in Q[(s, v, w)])) for w in qws]
        otext = [skel(seg['word']) for seg in a['segments']]
        amap = {}
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, otext, qtext, autojunk=False).get_opcodes():
            if op in ('equal', 'replace') and i2 - i1 == j2 - j1:
                for k in range(i2 - i1):
                    amap[i1 + k] = qws[j1 + k]
        for seg in a['segments']:
            wi = seg['word_index']
            rec = dict(loc=f'{s}:{v}:{wi}', word=seg['word'], slots=[dict(type=sl['type'], role=sl.get('role'), text=sl['text']) for sl in seg['slots']])
            if wi not in amap:
                rec['aligned'] = False; n['UNALIGNED'] += 1
                f.write(json.dumps(rec, ensure_ascii=False) + '\n'); continue
            q = qac_word(Q[(s, v, amap[wi])])
            stems = [sl['text'] for sl in seg['slots'] if sl['type'] == 'جذع']
            rec.update(aligned=True, qac_loc=f'{s}:{v}:{amap[wi]}', qac=q, stems=stems, peel=peel_class(stems, q['stem']))
            ms = []
            for t in stems:
                m = morph(t)
                if m:
                    ms.append(dict(stem=t, status=m['status'], root=m.get('root'), form=m.get('form_class'), level=m.get('level'), reason=m.get('reason'),
                                   cands=sorted({r for r, _ in m.get('candidates') or []}), selection=m.get('selection'),
                                   protected=(m.get('protected') or {}).get('identity')))
            rec['morph'] = ms
            n['aligned'] += 1; n['peel:' + rec['peel']] += 1
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
print(json.dumps(dict(n), ensure_ascii=False))
