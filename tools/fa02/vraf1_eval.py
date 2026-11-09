"""tools/fa02/vraf1_eval.py dump <جذر الشيفرة> <OUT.jsonl.gz> [--jobs N] | eval <dump.jsonl.gz> <quran-morphology.txt> <OUT.json> [--base dump0]
تقييم V-RAF1 على مجتمعه كله (FA02، مراجعة المالك: المجتمع كل سجلات MOOD المرخَّصة — 3828 عند FA01 على v47 — لا الوحدات التي يعرض
محورها الدور، والخطأ المعروف باقٍ فيه، والمراجعة المستقلة مطلوبة):
- dump: كل سجلّ MOOD مرخَّص بمعرّفه ووحدته وموضعه ونصّه ومقدّماته، ودور المحور وصنفه في السمات النهائية.
- eval: مقابلةٌ مستقلة بمدوّنة QAC (للقياس وحده، لا مدخل في التحليل): لكل سجلّ مقاطع الكلمة نفسها في QAC بموضعها؛ AGREE إن كان فيها
  فعلٌ مضارع MOOD:IND، وDISAGREE_MOOD إن كان مضارعاً منصوباً أو مجزوماً، وNOT_IMPF_IN_QAC إن لم يكن فيها مضارع؛ مع نصّ QAC للمراجعة.
  وبـ--base: انتقالات المجتمع بين نسختين بالهوية (الموضع والنصّ). ولا يُعدّ اتفاق QAC صحةً نهائية: هو مقابلٌ مستقل يُراجَع."""
import collections, gzip, itertools, json, multiprocessing as mp, os, sys

_R = []


def one(items):
    sys.path.insert(0, _R[0])
    os.chdir(_R[0])
    from sarf.stages import run
    C = run(items, None, ['relations_final'] if 'relations_final' in __import__('sarf.stages', fromlist=['ENGINE']).ENGINE.stages else ['relations'])
    FF = C.get('features_final') if C.has('features_final') else C.get('features')
    out = []
    for k, V in C.get('records').items():
        tok = {u: (l, t) for u, l, t in V['tokens']}
        for r in V['records']:
            if r['type'] != 'MOOD' or r['status'] != 'LICENSED':
                continue
            u = r['heads']['verb']
            w, ui = (int(x) for x in u.rsplit('.w', 1)[1].split('.u'))
            ax = V['axes'].get(u) or {}
            out.append(dict(verse=k, unit=u, loc=tok[u][0], text=tok[u][1], relation_id=r['relation_id'], premises=r.get('premises'),
                            axis_role=str(ax.get('role'))[:200], axis_word_class=str(ax.get('word_class'))[:200],
                            pos_final=((FF.get(k) or {}).get((w, ui)) or {}).get('pos')))
    return out


def dump(root, path, jobs):
    _R.append(os.path.abspath(root))
    sys.path.insert(0, _R[0])
    from sarf import quran_source
    from sarf.root import hfn
    groups = [list(g) for _, g in itertools.groupby(quran_source.rows(), key=lambda x: x[0])]
    with mp.get_context('fork').Pool(jobs) as P:
        rows = [x for p in P.map(one, groups, chunksize=1) for x in p]
    with gzip.open(path, 'wt', encoding='utf-8') as f:
        f.write(json.dumps(dict(meta=dict(root=_R[0], release=hfn().release, n=len(rows))), ensure_ascii=False) + '\n')
        for x in rows:
            f.write(json.dumps(x, ensure_ascii=False, default=str) + '\n')
    print(hfn().release, 'licensed MOOD', len(rows))


def load(p):
    L = [json.loads(l) for l in gzip.open(p, 'rt', encoding='utf-8')]
    return L[0]['meta'], L[1:]


def qac(path):
    Q = collections.defaultdict(list)
    for l in open(path, encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) < 4 or p[0].count(':') != 3:
            continue
        s, v, w, _ = p[0].split(':')
        Q[(int(s), int(v), int(w))].append(dict(form=p[1], pos=p[2], feats=p[3]))
    return Q


def judge(x, Q):
    s, v, w = (int(t) for t in x['loc'].split(':'))
    segs = Q.get((s, v, w)) or []
    imp = [g for g in segs if g['pos'] == 'V' and 'IMPF' in g['feats'].split('|')]
    moods = sorted({f for g in imp for f in g['feats'].split('|') if f.startswith('MOOD:')})
    cls = ('NO_QAC_WORD' if not segs else 'NOT_IMPF_IN_QAC' if not imp else 'AGREE' if moods == ['MOOD:IND'] else 'DISAGREE_MOOD')
    return cls, ' + '.join(f"{g['form']}/{g['pos']}/{g['feats']}" for g in segs)


def evaluate(dp, qp, outp, base=None):
    meta, rows = load(dp)
    Q = qac(qp)
    cnt = collections.Counter()
    ex = collections.defaultdict(list)
    for x in rows:
        c, q = judge(x, Q)
        x['qac_class'], x['qac'] = c, q
        cnt[c] += 1
        if c != 'AGREE':
            ex[c].append(dict(loc=x['loc'], text=x['text'], qac=q, pos_final=x.get('pos_final'), axis_role=x['axis_role'][:120]))
    res = dict(population=meta, n=len(rows), qac_classes=dict(cnt), non_agree=ex,
               note='QAC مقابلٌ مستقل للقياس وحده؛ اتفاقه ليس صحةً نهائية، واختلافه يُراجَع بموضعه — والمراجعة المستقلة البشرية مطلوبة')
    if base:
        m0, r0 = load(base)
        k = lambda x: (x['loc'], x['text'])
        A, B = {k(x): x for x in r0}, {k(x): x for x in rows}
        res['base'] = dict(population=m0, n=len(r0))
        res['removed'] = [dict(loc=a[0], text=a[1], qac=judge(A[a], Q)[1], qac_class=judge(A[a], Q)[0],
                               pos_final_after=None) for a in sorted(set(A) - set(B))]
        res['added'] = [dict(loc=b[0], text=b[1], qac=B[b]['qac'], qac_class=B[b]['qac_class']) for b in sorted(set(B) - set(A))]
        res['removed_by_qac_class'] = dict(collections.Counter(x['qac_class'] for x in res['removed']))
        res['added_by_qac_class'] = dict(collections.Counter(x['qac_class'] for x in res['added']))
    json.dump(res, open(outp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    with open(outp.rsplit('.', 1)[0] + '_all.tsv', 'w', encoding='utf-8') as f:
        f.write('loc\ttext\tqac_class\tqac\trelation_id\taxis_role\n')
        for x in rows:
            f.write('\t'.join(str(x.get(c, '')).replace('\t', ' ') for c in ('loc', 'text', 'qac_class', 'qac', 'relation_id', 'axis_role')) + '\n')
    print(json.dumps({k_: res[k_] for k_ in ('n', 'qac_classes')}, ensure_ascii=False),
          json.dumps({k_: res.get(k_) for k_ in ('removed_by_qac_class', 'added_by_qac_class')}, ensure_ascii=False))


if __name__ == '__main__':
    if sys.argv[1] == 'dump':
        dump(sys.argv[2], sys.argv[3], int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 3)
    else:
        evaluate(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[sys.argv.index('--base') + 1] if '--base' in sys.argv else None)
