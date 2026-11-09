"""census.py <جذر الشيفرة> <OUT.json> [--jobs N]
إحصاء الموانع على المصحف كله (SARF_FINAL_COMPLETION_AND_ACCEPTANCE_01 §١٣): بالمحرّك حتى المراجع، لكل سورة:
العلاقات بنوعها وحالتها، والتعلّق المؤجَّل، وأنواع «بلا عامل»، ومتطلَّب المفعول، والوحدات المعلّقة بسببها، والإحالات غير المعيَّنة،
وأحكام الجمل ومستوياتها، وحدود الفقرات؛ مع أمثلةٍ بهوياتها. لا يغيّر شيئاً في التحليل."""
import collections, itertools, json, multiprocessing as mp, os, re, sys

_ROOT = []


def reason_class(d):
    d = d or ''
    for k, pat in (('MULTI_ROOT', 'أكثر من جذر'), ('NO_HFN_ENTRY', 'لا مدخل له في HFN'), ('NOMINALITY_UNPROVEN', 'لم تثبت الاسمية'),
                   ('NOT_VERB_NO_MATCH', 'لم يثبت بالكتابة أنه فعل'), ('NO_LICENCE', 'لا رخصة'), ('OP_AL_STEM', 'عامل\\+'),
                   ('INSERTED_RIVAL', 'قراءة بحرف محذوف')):
        if re.search(pat, d):
            return k
    return 'OTHER'


def one(items):
    sys.path.insert(0, _ROOT[0])
    os.chdir(_ROOT[0])
    from sarf.stages import run
    C = run(items, None, ['references'])
    c = collections.Counter()
    ex = collections.defaultdict(list)
    for k, V in C.get('records').items():
        tok = {u: (l, t) for u, l, t in V['tokens']}
        for r in V['records']:
            c[f"rel|{r['type']}|{r['status']}"] += 1
            if r['type'] == 'ATTACH' and r['status'] != 'LICENSED':
                ex['ATTACH_DEFERRED'].append(f"{k} {r['texts']}") if len(ex['ATTACH_DEFERRED']) < 5 else None
            if r['type'] == 'VERB_FRAME':
                kind = (r['frame'].get('object_requirement') or {}).get('kind')
                c[f'objreq|{kind}'] += 1
        for u, a in V['axes'].items():
            inf = a.get('inflection') or {}
            c[f"agreement|{inf.get('agreement')}"] += 1
            if inf.get('agreement') == 'UNGOVERNED':
                c[f"ungoverned|{inf.get('ungoverned_kind')}"] += 1
                if inf.get('ungoverned_kind') == 'ROLE_RULE_NOT_IMPLEMENTED' and len(ex['ROLE_RULE_NOT_IMPLEMENTED']) < 8:
                    ex['ROLE_RULE_NOT_IMPLEMENTED'].append(f'{tok[u][0]} {tok[u][1]}')
    for k, U in C.get('units').items():
        for key, G in U['units'].items():
            c['units'] += 1
            if not G.closed:
                c[f'unit_open|{reason_class(G.O.get("deferred"))}'] += 1
    for cid, cert in C.get('certificates').items():
        c[f"verdict|{cert.get('verdict')}"] += 1
        for lv, v in (cert.get('verdict_by_level') or {}).items():
            c[f'level|{lv}|{v}'] += 1
        for o in cert['obligations']:
            c[f"obl|{o['requirement_kind']}|{o['status']}"] += 1
    for p in C.get('paragraphs'):
        c[f"paragraph|{(p['candidate'].get('boundary') or {}).get('linguistic')}"] += 1
        c[f"paragraph_status|{p['candidate'].get('status')}"] += 1
    for p in C.get('references') or []:
        for x in p.get('references') or []:
            c[f"reference|{x.get('kind')}|{x.get('status')}"] += 1
    for s_, (stt, why) in C.status.items():
        c[f'stage|{s_}|{stt}'] += 1
    return dict(c), {k: v for k, v in ex.items()}


def main():
    root, out = os.path.abspath(sys.argv[1]), sys.argv[2]
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2
    _ROOT.append(root)
    sys.path.insert(0, root)
    from sarf import quran_source
    from sarf.root import hfn
    V = quran_source.rows()
    groups = [list(g) for _, g in itertools.groupby(V, key=lambda x: x[0])]
    with mp.get_context('fork').Pool(jobs) as P:
        parts = P.map(one, groups, chunksize=1)
    tot = collections.Counter()
    ex = collections.defaultdict(list)
    for c, e in parts:
        tot.update(c)
        for k, v in e.items():
            ex[k] += v[:3]
    H = hfn()
    json.dump(dict(root=root, release=H.release, pin=H.pin, verses=len(V), counts=dict(sorted(tot.items())),
                   examples={k: v[:20] for k, v in ex.items()}), open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    print(len(V), H.release, sum(v for k, v in tot.items() if k.startswith('rel|')))


if __name__ == '__main__':
    main()
