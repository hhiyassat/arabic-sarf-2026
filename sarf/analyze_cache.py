# -*- coding: utf-8 -*-
"""
sarf.analyze_cache — خبيئة التحليل الصرفي المشتركة بين أدوات التشغيل الكامل: يكتبها tools/algebra_quran.py بعد تحليل
المصحف، وتقرؤها أدوات القياس (eval_case، eval_root، eval_protected، audit_protected) بدل إعادة التحليل.

صلاحها مربوطٌ ببصمة الاعتماديات (الكود، وفهرس العوامل، وملف المبنيات، وأبنية سيبويه، وملفات HFN)؛ فإن تغيّر شيءٌ منها
بطلت، وعاد التحليل إلى analyze نفسه. والخبيئة في data/cache/ (خارج المستودع).
"""
import os, gzip, pickle, hashlib, glob

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
PATH = H + 'data/cache/analyze.pkl.gz'
_MEM = {'deps': None, 'an': None}


def dependency_files():
    from .root import hfn
    fs = sorted(glob.glob(H + 'sarf/*.py')) + [H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv',
                                               H + 'lexicon/mabniyat_lexicon.jsonl']
    fs += sorted(glob.glob(H + 'data/patterns/*.csv'))
    hp = hfn().path
    if hp:
        fs += [os.path.join(hp, x) for x in ('events.csv', 'lexical_units.csv', 'form_meanings.csv')]
    return [f for f in fs if os.path.exists(f)]


def fingerprint(files=None, extra=None):
    extra = os.environ.get('SARF_DEP_SALT', '').encode() if extra is None else extra
    h = hashlib.sha256(extra)
    for f in files if files is not None else dependency_files():
        h.update(os.path.relpath(f, H).encode() if f.startswith(H) else os.path.basename(f).encode())
        h.update(open(f, 'rb').read())
    return h.hexdigest()


def save(analyses, deps):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    open(PATH, 'wb').write(gzip.compress(pickle.dumps(dict(deps=deps, an=analyses), protocol=5), compresslevel=3))


def _load():
    if _MEM['an'] is None:
        _MEM['an'] = {}
        if os.path.exists(PATH):
            pack = pickle.loads(gzip.decompress(open(PATH, 'rb').read()))
            if pack.get('deps') == fingerprint():
                _MEM['an'] = pack['an']
    return _MEM['an']


def analyze_cached(cat, text):
    """التحليل من الخبيئة إن صلحت ووُجد النص فيها، وإلا analyze نفسه"""
    an = _load()
    if text in an:
        return an[text]
    from .analyze import analyze
    return analyze(cat, text)
