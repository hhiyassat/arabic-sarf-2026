"""tools/upstream/client.py — استدعاء العامل المعزول (tools/upstream/worker.py) في عمليةٍ فرعية، وسجلّ المصادر.

العزل: عمليةٌ فرعية بـ`python3 -I` (لا PYTHONPATH، ولا مجلد السكربت في المسار)، ومجلد عملٍ مؤقت، وHOME مؤقت فيه روابطُ
للموارد بالتخطيط الذي تتوقّعه (~/arabic-net/…). فلا تُحمَّل وحدات الموارد في عملية المحلّل، ولا يتغيّر مسار استيرادها.
"""
import hashlib, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WORKER = os.path.join(HERE, 'worker.py')

# مسارات الموارد: متغيّرات بيئةٍ صريحة؛ وإن عُيّن متغيّرٌ ومساره غير موجود يُعلن ذلك ولا يُستبدل به غيره
ENV = dict(amln='SARF_UP_AMLN', wazn='SARF_UP_WAZN', hfn='SARF_UP_HFN', maq='SARF_UP_MAQ')


class UpstreamError(RuntimeError):
    pass


def paths():
    out, bad = {}, []
    for k, e in ENV.items():
        v = os.environ.get(e, '')
        if not v:
            bad.append(f'{e} غير معيَّن')
        elif not os.path.isdir(v):
            bad.append(f'{e} يشير إلى مسارٍ غير موجود: {v}')
        out[k] = v
    if bad:
        raise UpstreamError('؛ '.join(bad))
    return out


def git_head(p):
    try:
        return subprocess.run(['git', '-C', p, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def git_dirty(p):
    try:
        return subprocess.run(['git', '-C', p, 'status', '--porcelain', '--ignored'], capture_output=True, text=True,
                              check=True).stdout.splitlines()
    except Exception:
        return None


def tree_state(p):
    """حالة المورد قبل الاستدعاء وبعده: الملفات بأحجامها وأوقاتها (لكشف أي كتابةٍ أو خبيئةٍ أو قاعدة بيانات)"""
    st = {}
    for d, dirs, files in os.walk(p):
        dirs[:] = [x for x in dirs if x != '.git']
        for f in files:
            q = os.path.join(d, f)
            try:
                s = os.lstat(q)
                st[os.path.relpath(q, p)] = (s.st_size, int(s.st_mtime))
            except OSError:
                pass
    return st


def call(lemmas, roots, P=None, check_writes=True):
    P = P or paths()
    home = tempfile.mkdtemp(prefix='up_home_')
    an = os.path.join(home, 'arabic-net')
    os.makedirs(an)
    os.symlink(P['amln'], os.path.join(an, 'Arabic-Mother-language-net'))
    os.symlink(P['hfn'], os.path.join(an, 'HusseinFrameNet'))
    os.symlink(P['wazn'], os.path.join(an, 'Arabic-Mother-language-wazn-net'))
    before = {k: tree_state(v) for k, v in P.items()} if check_writes else None
    env = dict(PATH=os.environ.get('PATH', '/usr/bin:/bin'), HOME=home, LANG='C.UTF-8', PYTHONHASHSEED='0',
               PYTHONDONTWRITEBYTECODE='1')
    cwd = tempfile.mkdtemp(prefix='up_cwd_')
    p = subprocess.run([sys.executable, '-I', '-B', WORKER], input=json.dumps(dict(paths=P, lemmas=lemmas, roots=roots), ensure_ascii=False),
                       capture_output=True, text=True, env=env, cwd=cwd)
    if p.returncode != 0:
        raise UpstreamError(f'العامل خرج بالرمز {p.returncode}: {p.stderr[-800:]}')
    res = json.loads(p.stdout)
    res['provenance'] = {k: dict(path=v, commit=git_head(v)) for k, v in P.items()}
    res['isolation'] = dict(worker_stderr=p.stderr[-400:], cwd_files=sorted(os.listdir(cwd)))
    if check_writes:
        after = {k: tree_state(v) for k, v in P.items()}
        res['isolation']['resource_writes'] = {k: sorted(set(after[k].items()) ^ set(before[k].items())) for k in P}
    return res
