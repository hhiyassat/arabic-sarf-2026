"""tools/fa02/certs.py dump <جذر الشيفرة> <OUT.jsonl.gz> [--jobs N] | cmp <قبل.jsonl.gz> <بعد.jsonl.gz> <OUT.json>
مقارنة الشهادات بالمدى لا بالترقيم (FA02 §٥، ومراجعة المالك لأداة certs_by_span):
- المفتاح (السورة، المدى بالكلمات)؛ ومفتاحٌ مكرّر في أحد الطرفين يُرفض (خطأ صريح، لا يُكتب فوق الأول بصمت)؛
- SPLIT: مدى قبلُ صار أجزاءً بعدُ — بشرط أن تغطّيه الأجزاء تغطيةً تامة (اتحادها = المدى) بلا تداخل؛ وMERGE عكسه بالشرط نفسه؛
  وما لم يتمّ غطاؤه يُسمّى PARTIAL (بما نقص وما زاد) لا تقسيماً؛ وما بقي REMOVED أو ADDED؛
- الجمل المشتركة: انتقال الحكم بمستوياته، وانتقال كل التزام (بالاسم والمالك) في حالته **وفي دليل استيفائه** (معرّف العلاقة
  ومعرّف الدليل وأعضاء satisfied_by)، فالتساوي في الحالة وحدها لا يكفي.
dump يكتب لكل جملة: الحكم ومستوياته، ولكل التزامٍ اسمه ومالكه وحالته ومعرّف علاقته ودليله وأعضاء استيفائه وأصناف غير الموضوع."""
import collections, gzip, itertools, json, multiprocessing as mp, os, sys

_ROOT = []


def ob_rec(o):
    return dict(id=o.get('obligation_id'), name=o.get('name'), owner=o.get('owner'), status=o.get('status'), met=o.get('met'),
                legacy=o.get('legacy_met'), rel=o.get('discharge_relation_id'), ev=o.get('discharge_evidence_id'),
                sat=sorted(f"{x.get('unit')}←{x.get('relation')}" for x in (o.get('satisfied_by') or []) if isinstance(x, dict)),
                unplaced=o.get('unplaced_by_class'))


def one(items):
    sys.path.insert(0, _ROOT[0])
    os.chdir(_ROOT[0])
    from sarf.stages import run
    C = run(items, None, ['certificates'])
    return [json.dumps(dict(id=cid, span=[str(x) for x in (c.get('span') or [])], verdict=c.get('verdict'), by_level=c.get('verdict_by_level'),
                            obligations=[ob_rec(o) for o in c.get('obligations') or []]), ensure_ascii=False)
            for cid, c in C.get('certificates').items()]


def dump(root, path, jobs):
    _ROOT.append(os.path.abspath(root))
    sys.path.insert(0, _ROOT[0])
    from sarf import quran_source
    groups = [list(g) for _, g in itertools.groupby(quran_source.rows(), key=lambda x: x[0])]
    with mp.get_context('fork').Pool(jobs) as P:
        parts = P.map(one, groups, chunksize=1)
    with gzip.open(path, 'wt', encoding='utf-8') as f:
        for i, p in enumerate(parts):
            for line in p:
                d = json.loads(line)
                d['key'] = f'{groups[i][0][0]}|{d["id"]}'
                f.write(json.dumps(d, ensure_ascii=False) + '\n')
    print('dumped', sum(len(p) for p in parts))


class DuplicateSpan(ValueError):
    pass


def load(p):
    out = {}
    for l in gzip.open(p, 'rt', encoding='utf-8'):
        d = json.loads(l)
        k = (d['key'].split('|')[0], tuple(d['span']))
        if k in out:
            raise DuplicateSpan(f'{p}: مدىً مكرّر {k[0]} {k[1][:1]}…{k[1][-1:]} لجملتين ({out[k]["id"]} و{d["id"]})')
        out[k] = d
    return out


def cover(whole, parts):
    """→ (تامّ؟، الناقص، الزائد، المتداخل)"""
    u = collections.Counter(x for p in parts for x in p)
    over = sorted(x for x, n in u.items() if n > 1)
    return set(u) == set(whole) and not over, sorted(set(whole) - set(u)), sorted(set(u) - set(whole)), over


def ob_key(o):
    return (o.get('name'), o.get('owner'))


def compare(A, B):
    onlyA, onlyB = set(A) - set(B), set(B) - set(A)
    used_a, used_b, struct = set(), set(), []
    for k in sorted(onlyA):
        s, sp = k
        parts = sorted((x for x in onlyB - used_b if x[0] == s and set(x[1]) & set(sp)), key=lambda x: x[1])
        if not parts or any(not set(x[1]) <= set(sp) for x in parts):
            continue                                # جزءٌ يتجاوز المدى: يُنظر فيه من جهة الدمج
        if len(parts) > 1 or set(parts[0][1]) != set(sp):
            ok, miss, extra, over = cover(sp, [x[1] for x in parts])
            kind = 'SPLIT' if ok and len(parts) > 1 else 'PARTIAL'
            struct.append(dict(kind=kind, surah=s, before=[sp[0], sp[-1]], after=[[x[1][0], x[1][-1]] for x in parts], missing=miss, extra=extra,
                               overlap=over, before_levels=A[k]['by_level'], after_levels=[B[x]['by_level'] for x in parts]))
            used_a.add(k)
            used_b.update(parts)
    for k in sorted(onlyB - used_b):
        s, sp = k
        parts = sorted((x for x in onlyA - used_a if x[0] == s and set(x[1]) & set(sp)), key=lambda x: x[1])
        if parts:
            ok, miss, extra, over = cover(sp, [x[1] for x in parts])
            kind = 'MERGE' if ok and len(parts) > 1 else 'PARTIAL'
            struct.append(dict(kind=kind, surah=s, before=[[x[1][0], x[1][-1]] for x in parts], after=[sp[0], sp[-1]], missing=miss, extra=extra,
                               overlap=over, before_levels=[A[x]['by_level'] for x in parts], after_levels=B[k]['by_level']))
            used_b.add(k)
            used_a.update(parts)
    struct += [dict(kind='REMOVED', surah=k[0], before=[k[1][0], k[1][-1]], before_levels=A[k]['by_level']) for k in sorted(onlyA - used_a)]
    struct += [dict(kind='ADDED', surah=k[0], after=[k[1][0], k[1][-1]], after_levels=B[k]['by_level']) for k in sorted(onlyB - used_b)]
    common = sorted(set(A) & set(B))
    changed, ob_tr, ev_only = [], collections.Counter(), []
    for k in common:
        a, b = A[k], B[k]
        if (a['verdict'], a['by_level']) != (b['verdict'], b['by_level']):
            changed.append(dict(surah=k[0], span=[k[1][0], k[1][-1]], verdict_before=a['verdict'], verdict_after=b['verdict'],
                                levels_before=a['by_level'], levels_after=b['by_level']))
        oa = {ob_key(o): o for o in a['obligations']}
        obb = {ob_key(o): o for o in b['obligations']}
        for ok_ in sorted(set(oa) | set(obb), key=str):
            x, y = oa.get(ok_), obb.get(ok_)
            sx, sy = (x or {}).get('status'), (y or {}).get('status')
            if sx != sy:
                ob_tr[(ok_[0] if not str(ok_[0]).startswith(('إغلاق «', 'فاعل «', 'مفعول «', 'معمول «', 'خبر «')) else
                       str(ok_[0]).split('«')[0].strip() + ' «…»', sx, sy)] += 1
            elif x and y and (x.get('rel'), x.get('ev'), x.get('sat'), x.get('unplaced')) != (y.get('rel'), y.get('ev'), y.get('sat'), y.get('unplaced')):
                ev_only.append(dict(surah=k[0], span=[k[1][0], k[1][-1]], obligation=ok_[0], owner=ok_[1], status=sx,
                                    before=dict(rel=x.get('rel'), ev=x.get('ev'), sat=x.get('sat'), unplaced=x.get('unplaced')),
                                    after=dict(rel=y.get('rel'), ev=y.get('ev'), sat=y.get('sat'), unplaced=y.get('unplaced'))))
    lv = collections.Counter()
    for c in changed:
        for L in sorted(set(c['levels_before'] or {}) | set(c['levels_after'] or {})):
            if (c['levels_before'] or {}).get(L) != (c['levels_after'] or {}).get(L):
                lv[(L, (c['levels_before'] or {}).get(L), (c['levels_after'] or {}).get(L))] += 1
    return dict(sentences_before=len(A), sentences_after=len(B), common=len(common), common_changed=len(changed),
                level_transitions=[dict(level=k[0], before=k[1], after=k[2], n=n) for k, n in lv.most_common()],
                obligation_status_transitions=[dict(obligation=k[0], before=k[1], after=k[2], n=n) for k, n in ob_tr.most_common()],
                evidence_only_changes=len(ev_only), evidence_only_examples=ev_only[:200],
                structural_counts={k: sum(1 for x in struct if x['kind'] == k) for k in ('SPLIT', 'MERGE', 'PARTIAL', 'REMOVED', 'ADDED')},
                structural=struct, changed=changed)


if __name__ == '__main__':
    if sys.argv[1] == 'dump':
        dump(sys.argv[2], sys.argv[3], int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2)
    else:
        res = compare(load(sys.argv[2]), load(sys.argv[3]))
        res.update(before=sys.argv[2], after=sys.argv[3])
        json.dump(res, open(sys.argv[4], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(json.dumps({k: res[k] for k in ('sentences_before', 'sentences_after', 'common', 'common_changed', 'evidence_only_changes',
                                              'structural_counts')}, ensure_ascii=False))
