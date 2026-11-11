"""resource_diff.py <OLD_RELEASE_DIR> <NEW_RELEASE_DIR> <OUT.json> — مقارنة إصدارين ملفاً ملفاً، وصفاً صفاً بالمفتاح (SARF_HFN_V50_COMPATIBILITY_01 §٣).
لكل ملف: بصمتاه، وحالته (UNCHANGED_BYTES / ADDED / REMOVED / CHANGED)، وتصريحه في MANIFEST كلٍّ.
ولكل CSV متغيّر أو مشترك: مفتاح المقابلة (عمودٌ فريد في الطرفين، بالترتيب: link_id، event_id، lu_id، id، أول عمود؛ وإلا الصف كله)،
والصفوف المضافة والمحذوفة والمتغيّرة بالمفتاح، والأعمدة المتغيّرة؛ واختلاف الترتيب وحده لا يُعدّ تغييراً."""
import csv, hashlib, json, os, sys
from collections import Counter
csv.field_size_limit(10 ** 9)
OLD, NEW, OUT = sys.argv[1:4]


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def tree(d):
    return {os.path.relpath(os.path.join(b, f), d): sha(os.path.join(b, f)) for b, _, fs in os.walk(d) for f in fs}


def rows(p):
    with open(p, encoding='utf-8', newline='') as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)


def key_of(cols_a, ra, cols_b, rb):
    for k in ('link_id', 'event_id', 'lu_id', 'id', (cols_a or [None])[0]):
        if k and k in cols_a and k in cols_b and len({x[k] for x in ra}) == len(ra) and len({x[k] for x in rb}) == len(rb):
            return k
    return None


A, B = tree(OLD), tree(NEW)
MA, MB = (json.load(open(os.path.join(d, 'MANIFEST.json'), encoding='utf-8')) for d in (OLD, NEW))
files, csvs = [], {}
for f in sorted(set(A) | set(B)):
    st = 'ADDED' if f not in A else 'REMOVED' if f not in B else 'UNCHANGED_BYTES' if A[f] == B[f] else 'CHANGED'
    files.append(dict(file=f, status=st, sha_old=A.get(f), sha_new=B.get(f), declared_old=f in MA.get('files', {}), declared_new=f in MB.get('files', {})))
    if f.endswith('.csv') and f in A and f in B:
        ca, ra = rows(os.path.join(OLD, f)); cb, rb = rows(os.path.join(NEW, f))
        k = key_of(ca, ra, cb, rb)
        if k:
            ia, ib = {x[k]: x for x in ra}, {x[k]: x for x in rb}
            ch = [i for i in ia if i in ib and ia[i] != ib[i]]
            colch = Counter(c for i in ch for c in set(ia[i]) | set(ib[i]) if ia[i].get(c) != ib[i].get(c))
            order_only = st == 'CHANGED' and not ch and set(ia) == set(ib) and ca == cb
        else:
            ta, tb = Counter(tuple(sorted(x.items())) for x in ra), Counter(tuple(sorted(x.items())) for x in rb)
            ia, ib, ch, colch = ta, tb, [], Counter()
            order_only = st == 'CHANGED' and ta == tb and ca == cb
        csvs[f] = dict(key=k or 'WHOLE_ROW', rows_old=len(ra), rows_new=len(rb), columns_equal=ca == cb, columns_added=[c for c in cb if c not in ca],
                       columns_removed=[c for c in ca if c not in cb], added=len(set(ib) - set(ia)), removed=len(set(ia) - set(ib)), changed=len(ch),
                       changed_columns=dict(colch.most_common()), order_only_change=order_only,
                       examples=dict(added=sorted(set(ib) - set(ia))[:5] if k else [], removed=sorted(set(ia) - set(ib))[:5] if k else [], changed=ch[:5]))
summ = dict(old=OLD, new=NEW, manifest_old=sha(os.path.join(OLD, 'MANIFEST.json')), manifest_new=sha(os.path.join(NEW, 'MANIFEST.json')),
            status=dict(Counter(x['status'] for x in files)), changed=[x['file'] for x in files if x['status'] == 'CHANGED'],
            added=[x['file'] for x in files if x['status'] == 'ADDED'], removed=[x['file'] for x in files if x['status'] == 'REMOVED'],
            undeclared_new=[x['file'] for x in files if x['sha_new'] and not x['declared_new'] and x['file'] != 'MANIFEST.json'],
            csv_semantic_changes={f: {k: v for k, v in c.items() if k != 'examples'} for f, c in csvs.items() if c['added'] or c['removed'] or c['changed'] or not c['columns_equal']},
            analysis_files_unchanged={f: next(x['status'] for x in files if x['file'] == f) for f in ('events.csv', 'lexical_units.csv', 'form_meanings.csv', 'roots.csv', 'valence.csv', 'valence_realizations.csv')})
json.dump(dict(summary=summ, files=files, csv=csvs), open(OUT, 'w'), ensure_ascii=False, indent=1)
print(json.dumps(summ, ensure_ascii=False, indent=0)[:3000])
