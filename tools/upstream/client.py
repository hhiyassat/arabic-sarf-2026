"""tools/upstream/client.py — استدعاء العامل المعزول (tools/upstream/worker.py) في عمليةٍ فرعية، بتثبيتٍ صريح للمصادر.

التثبيت (SARF_UPSTREAM_CONSUMPTION_2026_11_08 §٢): لا يُحمَّل «أحدث» شيءٍ تلقائياً. يلزم:
  SARF_UP_PINS   ملفّ التثبيت (tools/upstream/pins_2026_11_08.json): الالتزامات الأربعة، وإصدار HFN وبصمة MANIFEST، وبصمة كل ملفٍّ مستهلك
  SARF_UP_HFN، SARF_UP_WAZN، SARF_UP_AMLN، SARF_UP_MAQ   نسخٌ مثبتة (git archive عند الالتزام، وفيها .pinned_commit) أو مستودعاتٌ HEAD فيها هو الالتزام
وغياب أيٍّ منها، أو اختلاف الالتزام أو بصمة MANIFEST، خطأ إعدادٍ مسمّى (PIN_*)، لا رجوعٌ إلى غيره.

العزل: `python3 -I -B`، وHOME مؤقت فيه arabic-net بروابط إلى النسخ المثبتة، وAMLN_HFN_RELEASE وARABIC_NET_HFN_RELEASE معيَّنان على
الإصدار المثبت (فلا تأخذ طبقات AMLN ولا واجهتها أحدث إصدار)، وPYTHONDONTWRITEBYTECODE. وتُقارن حالة المصادر قبل الاستدعاء وبعده.
"""
import hashlib, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WORKER = os.path.join(HERE, 'worker.py')
ENV = dict(hfn='SARF_UP_HFN', wazn='SARF_UP_WAZN', amln='SARF_UP_AMLN', maq='SARF_UP_MAQ')
CALLS = []          # سجلّ الاستدعاءات الفعلية في هذه العملية (لاختبار البوابة بعدّ الاستدعاءات لا بشكل المخرج)


class UpstreamError(RuntimeError):
    pass


def commit_of(p):
    f = os.path.join(p, '.pinned_commit')
    if os.path.exists(f):
        return open(f).read().strip(), 'PINNED_ARCHIVE'
    try:
        c = subprocess.run(['git', '-C', p, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(['git', '-C', p, 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()
        return c, 'GIT_CHECKOUT' + (' (DIRTY)' if dirty else '')
    except Exception:
        return None, 'UNKNOWN'


def load_pins():
    pf = os.environ.get('SARF_UP_PINS', '')
    if not pf:
        raise UpstreamError('PIN_MISSING: SARF_UP_PINS غير معيَّن — لا تحميل لأحدث إصدار تلقائياً')
    if not os.path.isfile(pf):
        raise UpstreamError(f'PIN_MISSING: ملفّ التثبيت غير موجود: {pf}')
    pins = json.load(open(pf, encoding='utf-8'))
    check_sarf_release(pins)
    return pins


def check_sarf_release(pins):
    """§٤ (SARF_HFN_V48_VALIDATION_COMPLETION_02): إصدار HFN في العامل يطابق إصدار SARF المستهدف (الإعداد الإنتاجي أو التجريبي المأذون)،
    وإلا فإخفاق هويةٍ مسمّى؛ ولا يُقبل اختلافهما إلا بإذنٍ صريح بالظلّ: SARF_UP_HFN_SHADOW_OK=<إصدار العامل>."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
    from sarf.hfn_pin import TARGET
    if pins.get('hfn_release') != TARGET['release'] and os.environ.get('SARF_UP_HFN_SHADOW_OK', '') != pins.get('hfn_release'):
        raise UpstreamError(f'HFN_IDENTITY_MISMATCH: العامل مثبَّت على {pins.get("hfn_release")}، وSARF يستهدف {TARGET["release"]} '
                            f'({TARGET.get("config_mode")})؛ لظلٍّ مقصود عيّن SARF_UP_HFN_SHADOW_OK={pins.get("hfn_release")}')


def paths(pins=None):
    pins = pins or load_pins()
    out, bad = {}, []
    for k, e in ENV.items():
        v = os.environ.get(e, '')
        if not v:
            bad.append(f'PIN_PATH_MISSING: {e} غير معيَّن')
            continue
        if not os.path.isdir(v):
            bad.append(f'PIN_PATH_MISSING: {e} يشير إلى مسارٍ غير موجود: {v}')
            continue
        c, how = commit_of(v)
        if c != pins['commits'][k]:
            bad.append(f'PIN_COMMIT_MISMATCH: {k} عند {c} ({how})، والمثبت {pins["commits"][k]}')
        elif 'DIRTY' in how:
            bad.append(f'PIN_DIRTY: {k} فيه تعديلات محلية ({v})')
        out[k] = v
    if 'hfn' in out:
        mf = os.path.join(out['hfn'], 'release', pins['hfn_release'], 'MANIFEST.json')
        if not os.path.exists(mf):
            bad.append(f'PIN_RELEASE_MISSING: {mf}')
        elif hashlib.sha256(open(mf, 'rb').read()).hexdigest() != pins['hfn_manifest_sha256']:
            bad.append(f'PIN_MANIFEST_MISMATCH: {pins["hfn_release"]}')
    if bad:
        raise UpstreamError('؛ '.join(bad))
    return out


def tree_state(p):
    st = {}
    for d, dirs, files in os.walk(p):
        dirs[:] = [x for x in dirs if x != '.git']
        for f in files + [x for x in dirs]:
            q = os.path.join(d, f)
            try:
                s = os.lstat(q)
                st[os.path.relpath(q, p)] = (s.st_size, int(s.st_mtime))
            except OSError:
                pass
    return st


def call(lemmas, roots, P=None, pins=None, check_writes=True, origin='public'):
    pins = pins or load_pins()
    P = P or paths(pins)
    CALLS.append(dict(origin=origin, lemmas=[x['lemma'] for x in lemmas], roots=[x['root'] for x in roots]))
    home = tempfile.mkdtemp(prefix='up_home_')
    an = os.path.join(home, 'arabic-net')
    os.makedirs(an)
    os.symlink(P['amln'], os.path.join(an, 'Arabic-Mother-language-net'))
    os.symlink(P['hfn'], os.path.join(an, 'HusseinFrameNet'))
    os.symlink(P['wazn'], os.path.join(an, 'Arabic-Mother-language-wazn-net'))
    before = {k: tree_state(v) for k, v in P.items()} if check_writes else None
    rel_dir = os.path.join(P['hfn'], 'release', pins['hfn_release'])
    env = dict(PATH=os.environ.get('PATH', '/usr/bin:/bin'), HOME=home, LANG='C.UTF-8', PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1',
               ARABIC_NET_HOME=an, AMLN_HFN_RELEASE=pins['hfn_release'], ARABIC_NET_HFN_RELEASE=rel_dir)
    cwd = tempfile.mkdtemp(prefix='up_cwd_')
    p = subprocess.run([sys.executable, '-I', '-B', WORKER],
                       input=json.dumps(dict(paths=P, pins=pins, lemmas=lemmas, roots=roots), ensure_ascii=False),
                       capture_output=True, text=True, env=env, cwd=cwd)
    if p.returncode != 0:
        raise UpstreamError(f'INTERFACE_ERROR: العامل خرج بالرمز {p.returncode}: {p.stderr[-800:]}')
    res = json.loads(p.stdout)
    res['provenance'] = {k: dict(path=v, commit=commit_of(v)[0], how=commit_of(v)[1], pinned=pins['commits'][k]) for k, v in P.items()}
    res['provenance']['hfn_release'] = dict(requested=pins['hfn_release'], manifest_sha256=pins['hfn_manifest_sha256'],
                                            env=dict(AMLN_HFN_RELEASE=env['AMLN_HFN_RELEASE'], ARABIC_NET_HFN_RELEASE=env['ARABIC_NET_HFN_RELEASE']))
    res['isolation'] = dict(worker_stderr=p.stderr[-400:], cwd_files=sorted(os.listdir(cwd)), home_files=sorted(os.listdir(home)))
    if check_writes:
        after = {k: tree_state(v) for k, v in P.items()}
        res['isolation']['resource_writes'] = {k: sorted(set(after[k].items()) ^ set(before[k].items())) for k in P}
    return res
