"""compare_rootdumps.py <قبل.jsonl> <بعد.jsonl> <OUT.json>
يقابل تفريغي tools/eval_root.py (SARF_ROOT_DUMP) بالموضع والنص: انتقالات الحالة والجذر والوزن، مصنَّفةً بمقابلة QAC (للقياس وحده):
صحيح→خطأ، وخطأ→صحيح، ومؤجَّل→مقبول صحيح/خطأ، ومقبول صحيح→مؤجَّل. «صحيح» = مقبول وجذره ووزنه جذر QAC ووزنه."""
import json, sys, collections


def load(p):
    out = {}
    for l in open(p, encoding='utf-8'):
        d = json.loads(l)
        out[(d['loc'], d['text'])] = d
    return out


def cls(d):
    if d is None:
        return 'ABSENT'
    if d['status'] in ('not_applicable', 'class_deferred'):
        return d['status']
    if d['status'] != 'accepted':
        return d['status'].upper()
    if d.get('gold') is None:
        return 'ACCEPTED_NO_GOLD'
    return 'CORRECT' if d['root'] == d['gold'] and d['form'] == d.get('gold_form') else \
        'ROOT_OK_FORM_WRONG' if d['root'] == d['gold'] else 'WRONG'


A, B = load(sys.argv[1]), load(sys.argv[2])
T = collections.Counter()
ex = collections.defaultdict(list)
for k in sorted(set(A) | set(B)):
    a, b = A.get(k), B.get(k)
    ca, cb = cls(a), cls(b)
    if ca != cb or (a and b and (a.get('root'), a.get('form')) != (b.get('root'), b.get('form'))):
        T[(ca, cb)] += 1
        ex[f'{ca}→{cb}'].append(dict(loc=k[0], text=k[1], before=[(a or {}).get('status'), (a or {}).get('root'), (a or {}).get('form')],
                                     after=[(b or {}).get('status'), (b or {}).get('root'), (b or {}).get('form')],
                                     gold=[(b or a or {}).get('gold'), (b or a or {}).get('gold_form')], reason_after=((b or {}).get('reason') or '')[:120]))
summ = lambda D: dict(collections.Counter(cls(d) for d in D.values()))
res = dict(before=summ(A), after=summ(B), transitions=[dict(before=a, after=b, n=n) for (a, b), n in T.most_common()],
           correct_to_not_correct=sum(n for (a, b), n in T.items() if a == 'CORRECT' and b != 'CORRECT'),
           not_correct_to_correct=sum(n for (a, b), n in T.items() if a != 'CORRECT' and b == 'CORRECT'),
           examples={k: v[:40] for k, v in ex.items()}, example_counts={k: len(v) for k, v in ex.items()})
json.dump(res, open(sys.argv[3], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: res[k] for k in ('before', 'after', 'transitions', 'correct_to_not_correct', 'not_correct_to_correct')}, ensure_ascii=False))
