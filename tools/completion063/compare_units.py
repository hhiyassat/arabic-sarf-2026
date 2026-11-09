"""compare_units.py <قبل.pkl.gz> <بعد.pkl.gz> <data/quran-morphology.txt> <OUT.json>
يقابل الوحدات اللفظية (المرحلة ١٢) بين لقطتين من tools/snapshot_outputs.py على المصحف كله: الإغلاق والجذر والوزن لكل وحدة،
مصنَّفةً بمقابلة جذر QAC للكلمة (للقياس وحده، لا مدخل): CORRECT (مغلقة وجذرها جذر QAC)، WRONG (مغلقة بجذرٍ آخر)، OPEN (معلّقة)،
NO_ROOT (مغلقة بلا جذر: محمية أو مبنية)، NO_GOLD (لا جذر لها في QAC). والمحاذاة بين كلمات الآية وكلمات QAC بالهيكل كما في eval_root."""
import gzip, pickle, json, sys, re, collections, difflib

A = pickle.load(gzip.open(sys.argv[1]))
B = pickle.load(gzip.open(sys.argv[2]))
Q = collections.defaultdict(list)
for l in open(sys.argv[3], encoding='utf-8'):
    loc, form, tag, feats = l.rstrip('\n').split('\t')
    s, v, w, k = map(int, loc.split(':'))
    Q[(s, v, w)].append((form, tag, feats.split('|')))
HZ = str.maketrans('أإؤئآ', 'ءءءءء')


def skel(t):
    t = re.sub('[ً-ٰٟۖ-ࣰۭ-ࣲـ]', '', t)
    return t.translate(str.maketrans('ٱأإآؤئىة', 'اااااييه')).replace('ء', '')


def gold_roots(s, v):
    ws = sorted(k[2] for k in Q if k[0] == s and k[1] == v)
    return ws, [skel(''.join(f for f, _, _ in Q[(s, v, w)])) for w in ws], \
        [{f[5:].translate(HZ) for _, _, fs in Q[(s, v, w)] for f in fs if f.startswith('ROOT:')} for w in ws]


QV = collections.defaultdict(list)
for (s, v, w) in Q:
    QV[(s, v)].append(w)


def classify(u, golds):
    if u is None:
        return 'ABSENT'
    if not golds:
        return 'NO_GOLD'
    if not u['closed']:
        return 'OPEN'
    R = (u.get('Theta') or {}).get('R')
    if not R:
        return 'NO_ROOT'
    return 'CORRECT' if str(R).translate(HZ) in golds else 'WRONG'


T = collections.Counter()
ex = collections.defaultdict(list)
tot_a, tot_b = collections.Counter(), collections.Counter()
for ref in A:
    s, v = map(int, ref.split(':'))
    ua, ub = A[ref]['units'], B[ref]['units']
    words = [seg['word'] for seg in A[ref]['a']['segments']]
    ws, qtext, groots = gold_roots(s, v)
    amap = {}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, [skel(w) for w in words], qtext, autojunk=False).get_opcodes():
        if op in ('equal', 'replace') and i2 - i1 == j2 - j1:
            for k in range(i2 - i1):
                amap[i1 + k] = j1 + k
    for key in sorted(set(ua) | set(ub)):
        wi = int(re.match(r'\((\d+),', key).group(1))
        golds = groots[amap[wi]] if wi in amap else set()
        a, b = ua.get(key), ub.get(key)
        ca, cb = classify(a, golds), classify(b, golds)
        tot_a[ca] += 1
        tot_b[cb] += 1
        ra = (a or {}).get('Theta', {}).get('R') if a else None
        rb = (b or {}).get('Theta', {}).get('R') if b else None
        pa = (a or {}).get('Theta', {}).get('P') if a else None
        pb = (b or {}).get('Theta', {}).get('P') if b else None
        if (ca, ra) != (cb, rb) or bool((a or {}).get('closed')) != bool((b or {}).get('closed')) or pa != pb:
            T[(ca, cb)] += 1
            ex[f'{ca}→{cb}'].append(dict(loc=f'{ref}:{wi + 1}', unit=key, text=(b or a).get('text'), root_before=ra, root_after=rb,
                                         pattern_before=pa, pattern_after=pb, gold=sorted(golds),
                                         deferred_before=((a or {}).get('deferred') or '')[:100], deferred_after=((b or {}).get('deferred') or '')[:100]))
res = dict(before=dict(tot_a), after=dict(tot_b), transitions=[dict(before=a, after=b, n=n) for (a, b), n in T.most_common()],
           correct_to_not_correct=sum(n for (a, b), n in T.items() if a == 'CORRECT' and b != 'CORRECT'),
           not_correct_to_correct=sum(n for (a, b), n in T.items() if a != 'CORRECT' and b == 'CORRECT'),
           examples={k: v[:60] for k, v in ex.items()}, example_counts={k: len(v) for k, v in ex.items()})
json.dump(res, open(sys.argv[4], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: res[k] for k in ('before', 'after', 'transitions', 'correct_to_not_correct', 'not_correct_to_correct')}, ensure_ascii=False))
