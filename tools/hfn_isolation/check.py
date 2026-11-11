"""فاحص العزل (§٣): يقرأ سجلات sitecustomize المنظَّمة، وينسب كل فتحٍ إلى إصداره بمساره المحلول، ويصنّف غرضه بالإطار الذي فتحه.
الإصدار يُعيَّن بالجذور المحلولة المعطاة (اسم ← مجلّد)، لا بالبحث النصي في الأسماء. والفتح عبر رابطٍ رمزي من إصدارٍ إلى آخر مخالفة.
الغرض: HASH_VERIFY (حساب البصمة)، MANIFEST_READ، LOAD_ROWS (تحميل صفوف)، CONSUMER_LOAD (مستهلك الروابط)، INJECTED، UNCLASSIFIED.
ونمط rb وحده لا يُعدّ دليلاً على الغرض."""
import glob, json, os

PURPOSE = [  # (لاحقة الملف، الدالة) ← الغرض
    (('sarf/hfn_pin.py', '_sha'), 'HASH_VERIFY'),
    (('sarf/hfn_pin.py', 'verify_release'), 'MANIFEST_READ'),
    (('sarf/root.py', '__init__'), None),           # rb = بصمة events، r = صفوف
    (('sarf/cells.py', 'lex_index'), 'LOAD_ROWS'),
    (('sarf/analyze_cache.py', None), 'HASH_VERIFY'),
    (('hfn_api.py', '_sha'), 'HASH_VERIFY'),
    (('hfn_api.py', '__init__'), 'MANIFEST_READ'),
    (('hfn_api.py', '_rows'), 'CONSUMER_LOAD'),
    (('hfn_isolation/sitecustomize.py', '<lambda>'), 'INJECTED'),
]


def load(prefix):
    out = []
    for f in sorted(glob.glob(prefix + '.*')):
        for line in open(f, encoding='utf-8'):
            out.append(json.loads(line))
    return out


def purpose(r):
    c = r.get('caller', '')
    parts = c.rsplit(':', 2)
    fn, func = (parts[0], parts[1]) if len(parts) == 3 else (c, '')
    for (suf, fu), p in PURPOSE:
        if fn.endswith(suf) and (fu is None or fu == func):
            if p is None:
                return 'HASH_VERIFY' if 'b' in r['mode'] else 'LOAD_ROWS'
            return p
    return 'INJECTED' if 'sitecustomize' in fn else 'UNCLASSIFIED'


def release_of(path, roots):
    for name, root in roots.items():
        if path == root or path.startswith(root + os.sep):
            return name
    return None


def check(records, roots, expected, allow_purposes=None):
    """→ dict(records=[…مع release وpurpose], violations=[…]). roots: {اسم: مسار} (يُحلّ هنا)."""
    roots = {k: os.path.realpath(v) for k, v in roots.items()}
    rows, viol = [], []
    for r in records:
        rel_real = release_of(r['realpath'], roots)
        rel_abs = release_of(os.path.normpath(r['abspath']), {k: v for k, v in roots.items()}) or release_of(r['abspath'], roots)
        p = purpose(r)
        x = dict(r, release=rel_real, release_by_path=rel_abs, purpose=p)
        rows.append(x)
        why = []
        if rel_real is None:
            why.append('OUTSIDE_PINNED_RELEASES')
        elif rel_real != expected:
            why.append(f'READ_FROM_OTHER_RELEASE:{rel_real}')
        if rel_abs and rel_real and rel_abs != rel_real:
            why.append(f'SYMLINK_CROSS:{rel_abs}->{rel_real}')
        if p in ('UNCLASSIFIED', 'INJECTED'):
            why.append('PURPOSE_' + p)
        if allow_purposes and p not in allow_purposes:
            why.append('PURPOSE_NOT_ALLOWED:' + p)
        if why:
            viol.append(dict(x, why=why))
    return dict(records=rows, violations=viol)


def summary(res):
    from collections import Counter
    return dict(n=len(res['records']), violations=len(res['violations']),
                by_file_purpose=sorted(Counter((os.path.basename(r['realpath']), r['release'], r['purpose'], r['mode']) for r in res['records']).items()),
                violation_kinds=sorted(Counter(w for v in res['violations'] for w in v['why']).items()))
