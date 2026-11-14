# -*- coding: utf-8 -*-
"""actual_file_pin.py — تثبيتٌ بالملفات الفعلية في شجرة العمل (لا ببصمات الالتزام).
يشمل كل ملفٍ تحت sarf/ (ومنه المستثنى بـ.gitignore) + ملفات الجذر الأربعة، مع شرط نظافة الشجرة.
يكشف تعديلًا أو إضافةً غير ملتزمة. الاستعمال: actual_file_pin.py <root> [declared_manifest.json]"""
import os, sys, json, hashlib, subprocess
ROOT_FILES = ['operators_catalog.jsonl', 'operators_catalog_split_vocalized.csv', 'lexicon/mabniyat_lexicon.jsonl', 'tools/morph_engine_export.py']
def sha(p):
    h = hashlib.sha256(); h.update(open(p, 'rb').read()); return h.hexdigest()
def actual_fingerprints(root):
    """بصمة المحتوى الفعلي: كل ما تحت sarf/ (ومنه المُتجاهَل) + ملفات الجذر."""
    fp = {}
    sarf = os.path.join(root, 'sarf')
    for dp, _, fs in os.walk(sarf):
        for f in sorted(fs):
            if f.endswith('.pyc') or '__pycache__' in dp: continue
            p = os.path.join(dp, f); fp[os.path.relpath(p, root)] = sha(p)
    for rf in ROOT_FILES:
        p = os.path.join(root, rf)
        if os.path.exists(p): fp[rf] = sha(p)
    return fp
def tree_clean(root):
    paths = ['sarf/'] + ROOT_FILES
    out = subprocess.run(['git', '-C', root, 'status', '--porcelain', '--', *paths], capture_output=True, text=True).stdout.strip()
    return (out == ''), out
def verify(root, declared):
    cur = actual_fingerprints(root); clean, porcelain = tree_clean(root)
    added = sorted(set(cur) - set(declared)); removed = sorted(set(declared) - set(cur))
    changed = sorted(k for k in cur if k in declared and cur[k] != declared[k])
    problems = []
    if added: problems.append('ADDED_FILES %s' % added[:5])
    if removed: problems.append('REMOVED_FILES %s' % removed[:5])
    if changed: problems.append('CHANGED_FILES %s' % changed[:5])
    if not clean: problems.append('WORKTREE_DIRTY %s' % porcelain.splitlines()[:5])
    return dict(count=len(cur), clean=clean, added=added, removed=removed, changed=changed, problems=problems)
if __name__ == '__main__':
    root = os.path.abspath(sys.argv[1])
    cur = actual_fingerprints(root)
    if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
        r = verify(root, json.load(open(sys.argv[2])))
        print(json.dumps(dict(ok=not r['problems'], **r), ensure_ascii=False))
    else:
        clean, _ = tree_clean(root)
        print(json.dumps(dict(ok=True, count=len(cur), clean=clean, note='no declared manifest; emitting current'), ensure_ascii=False))
        json.dump(cur, open('/dev/stdout', 'w') if False else sys.stderr, ensure_ascii=False)
