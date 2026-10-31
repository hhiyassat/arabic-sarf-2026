#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/eval_protected.py — قياس بوابة الحماية الدستورية مستقلاً عن دقة الجذور: صحة التعرّف على الوحدات المحمية
(العوامل المائة بصيغها، والمبنيات، والأسماء الذهبية) وحفظ هويتها، مقابل مدوَّنة القرآن الصرفية (QAC) للقياس وحده.

  المرجع (للقياس لا مدخلاً): الاسم الذهبي = في كلمة QAC مقطعٌ موسوم PN؛ والعامل الفعلي = فعلٌ جذره جذر عاملٍ فعلي
  (كون، ليس، صير…)؛ والمبني = كلمةٌ لا جذر لأيٍّ من مقاطعها الاسمية والفعلية.
  → reports/protected_eval.json

    python3 tools/eval_protected.py [1-114]
"""
import sys, os, re, json, difflib, collections
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.protected import protected_slot, CLASS_OPERATOR, CLASS_MABNI, CLASS_GOLDEN

lo, hi = (int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else '1-114').split('-'))
cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
OP_ROOTS = {'كون', 'ليس', 'صير', 'صبح', 'مسو', 'ضحو', 'ظلل', 'بيت', 'زيل', 'برح', 'فتأ', 'فكك', 'دوم', 'عسي', 'كود',
            'كرب', 'وشك', 'نعم', 'بأس', 'سوأ', 'حبب', 'حسب', 'خيل', 'ظنن', 'رأي', 'علم', 'وجد', 'زعم'}
HZ = str.maketrans('أإؤئآ', 'ءءءءء')
# العوامل الفعلية بلفظ مدخلها في QAC (للقياس وحده): الثلاثي المجرّد وما في الفهرس، لا ما اشتُقّ من جذرها (عَلَّمَ، أَنۡعَمَ)
OP_LEMMAS = {x.translate(HZ) for x in ('كان', 'ليس', 'صار', 'أصبح', 'أمسى', 'أضحى', 'ظل', 'بات', 'زال', 'برح', 'فتئ',
                                         'انفك', 'دام', 'عسى', 'كاد', 'كرب', 'أوشك', 'نعم', 'بئس', 'ساء', 'حبذا', 'حسب',
                                         'خال', 'ظن', 'رأى', 'علم', 'وجد', 'زعم')}
Q = collections.defaultdict(list)
for l in open(H + 'data/quran-morphology.txt', encoding='utf-8'):
    loc, form, tag, feats = l.rstrip('\n').split('\t')
    s, v, w, k = map(int, loc.split(':'))
    if lo <= s <= hi:
        Q[(s, v, w)].append((form, tag, feats.split('|')))


def skel(t):
    t = re.sub('[ً-ٰٟۖ-ࣰۭ-ࣲـ]', '', t)
    return t.translate(str.maketrans('ٱأإآؤئىة', 'اااااييه')).replace('ء', '')


def gold_class(segs):
    feats = [f for _, _, fs in segs for f in fs]
    if 'PN' in feats:
        return CLASS_GOLDEN
    for form, tag, fs in segs:
        lem = next((f[4:] for f in fs if f.startswith('LEM:')), '')
        if tag == 'V' and re.sub('[ًٌٍَُِْٰ]', '', lem).translate(HZ) in OP_LEMMAS:
            return CLASS_OPERATOR
    if not any(f.startswith('ROOT:') for _, tag, fs in segs if tag in ('N', 'V') for f in fs):
        return CLASS_MABNI
    return None


C = collections.Counter()
ex = collections.defaultdict(list)
for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'):
    s, v, text = l.rstrip('\n').split('\t')
    s, v = int(s), int(v)
    if not lo <= s <= hi:
        continue
    a = analyze(cat, text)
    qws = sorted(k[2] for k in Q if k[0] == s and k[1] == v)
    qtext = [skel(''.join(f for f, _, _ in Q[(s, v, w)])) for w in qws]
    otext = [skel(seg['word']) for seg in a['segments']]
    amap = {}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, otext, qtext, autojunk=False).get_opcodes():
        if op in ('equal', 'replace') and i2 - i1 == j2 - j1:
            for k in range(i2 - i1):
                amap[i1 + k] = qws[j1 + k]
    for seg in a['segments']:
        wi = seg['word_index']
        if wi not in amap:
            C['غير مقابَل'] += 1
            continue
        p = protected_slot(seg)
        g = gold_class(Q[(s, v, amap[wi])])
        ours = p['cls'] if p else None
        loc = f'{s}:{v}:{wi + 1}'
        C['كلمات'] += 1
        if p and p['ambiguous']:
            C[f'فئة مؤجَّلة:{ours}'] += 1
            C[f'فئة مؤجَّلة:{ours}:المرجع ' + (g or 'غير محمي')] += 1
            continue
        if ours and g:
            C[f'محمي:{ours}:المرجع {g}'] += 1
            C['محمي ومحمي في المرجع'] += 1
        elif ours:
            C[f'محمي:{ours}:المرجع غير محمي'] += 1
            if len(ex[f'زائد:{ours}']) < 40:
                ex[f'زائد:{ours}'].append(f'{loc} {seg["word"]} → «{p["identity"]}»')
        elif g:
            C[f'فائت:{g}'] += 1
            if len(ex[f'فائت:{g}']) < 60:
                ex[f'فائت:{g}'].append(f'{loc} {seg["word"]}')
        C['محمي في المرجع'] += bool(g)
        C['محمي عندنا'] += bool(ours)
out = dict(counts=dict(C), examples={k: v for k, v in ex.items()})
json.dump(out, open(H + 'reports/protected_eval.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, n in sorted(C.items()):
    print(k, n)
