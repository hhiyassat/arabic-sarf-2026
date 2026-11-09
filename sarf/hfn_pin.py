"""sarf.hfn_pin — تثبيت إصدار HFN المستهدف والتحقق منه قبل القراءة (SARF_FINAL_COMPLETION_AND_ACCEPTANCE_01 §١).

verify_release(path) → سجلّ الهوية (الإصدار، التزام HFN، بصمة MANIFEST، بصمة كل ملفٍّ مصرَّح به، المسحوب المصرَّح به)،
أو يرفع HFNPinError: إصدارٌ غير المستهدف، أو MANIFEST ببصمةٍ أخرى، أو ملفٌّ مصرَّح به مفقود أو ببصمةٍ أخرى.
الإصدار التاريخي (v36) يُقبل بطلبٍ صريح وحده، ولا يُتحقّق منه إلا ببصمة events.csv المسجّلة."""
import hashlib, json, os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTION_CONFIG = os.path.join(HERE, 'config', 'hfn_target.json')


class HFNPinError(RuntimeError):
    pass


def _load_target():
    """الإعداد الإنتاجي config/hfn_target.json؛ وإعدادٌ تجريبيّ لا يُقرأ إلا بطلبين صريحين معاً (SARF_HFN_V48_COMPARATIVE_VALIDATION_01 §٢):
    SARF_HFN_TARGET_CONFIG مساره، وSARF_HFN_EXPERIMENTAL_OK اسم إصداره. وأحدهما بلا الآخر، أو اختلافهما، خطأ هويةٍ مسمّى لا رجوعٌ صامت."""
    cp = os.environ.get('SARF_HFN_TARGET_CONFIG', '')
    ok = os.environ.get('SARF_HFN_EXPERIMENTAL_OK', '')
    if not cp:
        if ok:
            raise HFNPinError(f'HFN_IDENTITY_MISMATCH: SARF_HFN_EXPERIMENTAL_OK={ok} بلا SARF_HFN_TARGET_CONFIG')
        return dict(json.load(open(PRODUCTION_CONFIG, encoding='utf-8')), config=PRODUCTION_CONFIG, config_mode='PRODUCTION')
    cp = cp if os.path.isabs(cp) else os.path.join(HERE, cp)
    t = json.load(open(cp, encoding='utf-8'))
    if ok != t.get('release'):
        raise HFNPinError(f'HFN_IDENTITY_MISMATCH: الإعداد {os.path.basename(cp)} يعلن {t.get("release")}، '
                          f'والإذن الصريح SARF_HFN_EXPERIMENTAL_OK={ok or "غير معيَّن"}')
    return dict(t, config=cp, config_mode='EXPERIMENTAL')


TARGET = _load_target()


def _sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def verify_release(path):
    rel = os.path.basename(os.path.normpath(path))
    if rel == TARGET['release']:
        mp = os.path.join(path, 'MANIFEST.json')
        if not os.path.exists(mp):
            raise HFNPinError(f'{path}: لا MANIFEST.json — لا يُقرأ الإصدار المستهدف بلا بيانه')
        ms = _sha(mp)
        if ms != TARGET['manifest_sha256']:
            raise HFNPinError(f'{path}: بصمة MANIFEST {ms[:12]} تخالف المثبَّتة {TARGET["manifest_sha256"][:12]} (التزام HFN {TARGET["hfn_commit"][:7]})')
        m = json.load(open(mp, encoding='utf-8'))
        if m.get('release') != TARGET['release_name_in_manifest']:
            raise HFNPinError(f'{path}: MANIFEST يعلن {m.get("release")}')
        bad = [f for f, h in (m.get('files') or {}).items() if not os.path.exists(os.path.join(path, f)) or _sha(os.path.join(path, f)) != h]
        if bad:
            raise HFNPinError(f'{path}: ملفاتٌ مصرَّح بها مفقودة أو ببصمةٍ أخرى: {bad[:5]}')
        return dict(release=rel, mode='TARGET', config_mode=TARGET['config_mode'], hfn_commit=TARGET['hfn_commit'], manifest_sha256=ms,
                    files_verified=len(m.get('files') or {}), withdrawn_declared=list(m.get('events_withdrawn') or []))
    hist = (TARGET.get('historical') or {}).get(rel)
    if hist is not None:
        if os.environ.get('SARF_HFN_RELEASE_OK', '') != rel:
            raise HFNPinError(f'{path}: {rel} إصدارٌ تاريخي، والمستهدف {TARGET["release"]}؛ لتشغيلٍ تاريخي مقصود عيّن SARF_HFN_RELEASE_OK={rel}')
        es = _sha(os.path.join(path, 'events.csv'))
        if es != hist['events_sha256']:
            raise HFNPinError(f'{path}: بصمة events.csv {es[:12]} تخالف المسجّلة للإصدار التاريخي {rel}')
        return dict(release=rel, mode='HISTORICAL', hfn_commit=None, manifest_sha256=None, events_sha256=es, files_verified=1,
                    withdrawn_declared=None)
    raise HFNPinError(f'{path}: {rel} ليس الإصدار المستهدف ({TARGET["release"]}) ولا إصداراً تاريخياً مسجّلاً')
