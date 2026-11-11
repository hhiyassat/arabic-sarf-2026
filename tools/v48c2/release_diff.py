"""release_diff.py <v47_dir> <v48_dir> <OUT_DIR> — مقارنة الإصدارين ملفاً ملفاً (V48C02 §٥).
لكل ملفٍّ في أيٍّ من المجلّدين: البصمة في كلٍّ، وتصريحه في MANIFEST كلٍّ والبصمة المصرَّح بها، وحالته (UNCHANGED_BYTES، ADDED، REMOVED، CHANGED)،
وصنفه (DATA_ANALYSIS: يقرؤه محلّل SARF، DATA_OTHER، DOC، RELEASE_METADATA)، والملفات الموجودة غير المصرَّح بها.
وفحصٌ محتوائي لملفات التحليل والأحداث والجذور والمعاني والتعدية والسحب: عدد الصفوف والمسحوب في كلٍّ.
وفرق MANIFEST حقلاً حقلاً."""
import csv, hashlib, json, os, sys
V47, V48, OUT = sys.argv[1:4]
os.makedirs(OUT, exist_ok=True)
ANALYSIS = {'events.csv', 'lexical_units.csv', 'form_meanings.csv', 'MANIFEST.json'}     # ما يقرأ محلّل SARF صفوفه (sarf/root.py، sarf/cells.py)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def files(d):
    out = {}
    for b, ds, fs in os.walk(d):
        for f in fs:
            p = os.path.join(b, f)
            out[os.path.relpath(p, d)] = sha(p)
    return out


def kind(f):
    if f == 'MANIFEST.json':
        return 'RELEASE_METADATA'
    if f.endswith(('.md', '.txt')):
        return 'DOC'
    return 'DATA_ANALYSIS' if f in ANALYSIS else 'DATA_OTHER'


F47, F48 = files(V47), files(V48)
M47, M48 = (json.load(open(os.path.join(d, 'MANIFEST.json'), encoding='utf-8')) for d in (V47, V48))
rows = []
for f in sorted(set(F47) | set(F48)):
    a, b = F47.get(f), F48.get(f)
    st = 'ADDED' if a is None else 'REMOVED' if b is None else 'UNCHANGED_BYTES' if a == b else 'CHANGED'
    rows.append(dict(file=f, status=st, kind=kind(f), sha_v47=a, sha_v48=b,
                     declared_v47=f in M47['files'], declared_v48=f in M48['files'],
                     declared_hash_ok_v47=(M47['files'].get(f) == a) if f in M47['files'] else None,
                     declared_hash_ok_v48=(M48['files'].get(f) == b) if f in M48['files'] else None))
undeclared = [r['file'] for r in rows if (r['sha_v48'] and not r['declared_v48'] and r['file'] != 'MANIFEST.json')
              or (r['sha_v47'] and not r['declared_v47'] and r['file'] != 'MANIFEST.json')]
with open(os.path.join(OUT, 'release_file_diff.tsv'), 'w', encoding='utf-8') as fh:
    cols = list(rows[0])
    fh.write('\t'.join(cols) + '\n')
    for r in rows:
        fh.write('\t'.join(str(r[c]) for c in cols) + '\n')


def count(d, f, pred=None):
    p = os.path.join(d, f)
    if not os.path.exists(p):
        return None
    rs = list(csv.DictReader(open(p, encoding='utf-8')))
    return dict(rows=len(rs), **({'matching': sum(1 for r in rs if pred(r))} if pred else {}))


wd = lambda r: (r.get('event_review_v36') or '').startswith('WITHDRAWN')
content = {f: dict(v47=count(V47, f, wd if f == 'events.csv' else None), v48=count(V48, f, wd if f == 'events.csv' else None))
           for f in ('events.csv', 'roots.csv', 'lexical_units.csv', 'form_meanings.csv', 'valence.csv', 'valence_realizations.csv', 'concepts.csv')}


def mdiff(a, b, pre=''):
    out = []
    for k in sorted(set(a) | set(b)):
        if k not in a:
            out.append(dict(path=pre + k, change='ADDED', v48=b[k]))
        elif k not in b:
            out.append(dict(path=pre + k, change='REMOVED', v47=a[k]))
        elif a[k] != b[k]:
            if isinstance(a[k], dict) and isinstance(b[k], dict):
                out += mdiff(a[k], b[k], pre + k + '.')
            else:
                out.append(dict(path=pre + k, change='CHANGED', v47=a[k], v48=b[k]))
    return out


md = mdiff(M47, M48)
summary = dict(files_v47=len(F47), files_v48=len(F48), declared_v47=len(M47['files']), declared_v48=len(M48['files']),
               status={s: sum(1 for r in rows if r['status'] == s) for s in ('UNCHANGED_BYTES', 'ADDED', 'CHANGED', 'REMOVED')},
               changed=[(r['file'], r['kind']) for r in rows if r['status'] == 'CHANGED'], added=[(r['file'], r['kind']) for r in rows if r['status'] == 'ADDED'],
               removed=[r['file'] for r in rows if r['status'] == 'REMOVED'], undeclared_present=undeclared,
               declared_hash_mismatch=[r['file'] for r in rows if r['declared_hash_ok_v47'] is False or r['declared_hash_ok_v48'] is False],
               analysis_data_all_unchanged=all(r['status'] == 'UNCHANGED_BYTES' for r in rows if r['kind'] == 'DATA_ANALYSIS'),
               content=content, manifest_diff=md,
               withdrawn_declared=dict(v47=M47.get('events_withdrawn'), v48=M48.get('events_withdrawn')))
json.dump(summary, open(os.path.join(OUT, 'release_diff.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: summary[k] for k in ('files_v47', 'files_v48', 'status', 'changed', 'added', 'removed', 'undeclared_present',
                                          'declared_hash_mismatch', 'analysis_data_all_unchanged')}, ensure_ascii=False))
print(json.dumps(content, ensure_ascii=False))
print('MANIFEST diff paths:', [d['path'] + ':' + d['change'] for d in md])
