"""test_v08_corruptions.py <PACKAGE_DIR> <OUT.json> — إفسادات V08 (SARF_HFN_V48_FINAL_VERIFIER_REPAIR_04 §٤).
لكل إفساد: نسخةٌ منفصلة من الحزمة؛ الأصل ينجح، ثم الإفساد (مع تحديث بصمة الملف المُفسَد في MANIFEST.json فلا يكشفه V01) يُرفض بفحص V08
نفسه، ثم استعادة الأصل في النسخة نفسها تنجح. والحزمة الأصلية لا تُمسّ (بصمة MANIFEST قبل وبعد)."""
import hashlib, json, os, shutil, subprocess, sys, tempfile
SRC, OUT = sys.argv[1], sys.argv[2]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
V47 = '/home/user/ucr/repro03/pinned/hfn/release/release_v47'
V48 = '/home/user/c063/v48/pinned/hfn48/release/release_v48'


def manifest(d, changed=(), renamed=()):
    m = json.load(open(os.path.join(d, 'MANIFEST.json'), encoding='utf-8'))
    for a, b in renamed:
        m['files'][b] = m['files'].pop(a)
    for f in changed:
        m['files'][f] = sha(os.path.join(d, f))
    json.dump(m, open(os.path.join(d, 'MANIFEST.json'), 'w'), ensure_ascii=False, indent=1)


def edit_record(d, run, fn, line=0):
    raw = os.path.join(d, 'isolation/raw')
    f = next(x for x in sorted(os.listdir(raw)) if x.startswith(f'open_{run}.') and sum(1 for _ in open(os.path.join(raw, x))) > line)
    p = os.path.join(raw, f)
    L = open(p, encoding='utf-8').read().splitlines()
    r = json.loads(L[line]); fn(r); L[line] = json.dumps(r, ensure_ascii=False)
    open(p, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    manifest(d, [f'isolation/raw/{f}'])
    return f


def k1(d):   # قراءة من v47 في B
    return edit_record(d, 'B', lambda r: r.update(realpath=V47 + '/events.csv', abspath=V47 + '/events.csv'))


def k2(d):   # قراءة من v48 في A
    return edit_record(d, 'A', lambda r: r.update(realpath=V48 + '/events.csv', abspath=V48 + '/events.csv'))


def k3(d):   # مسارٌ مطلق داخل v48 ومحلولٌ داخل v47 (رابطٌ رمزي عابر)
    return edit_record(d, 'B', lambda r: r.update(abspath=V48 + '/lexical_units.csv', realpath=V47 + '/lexical_units.csv'))


def k4(d):   # مسارٌ خارج جذور الموارد المثبّتة
    return edit_record(d, 'C', lambda r: r.update(abspath='/tmp/release_v48/events.csv', realpath='/tmp/release_v48/events.csv'))


def k5a(d):  # غياب realpath
    return edit_record(d, 'B', lambda r: r.pop('realpath'))


def k5b(d):  # realpath تالف (نسبيّ)
    return edit_record(d, 'B', lambda r: r.update(realpath='release_v48/../release_v47/events.csv'))


def k6(d):   # الخام فيه مخالفة والملخّص يقول صفراً (الملخّص لم يُمسّ)، وبصمة الخام محدّثة
    return edit_record(d, 'B', lambda r: r.update(realpath=V47 + '/form_meanings.csv'), line=10)


def k7(d):   # مخالفة الخام مع تحديث بصمته — على C هذه المرة، في سجلّ الإرفاق
    return edit_record(d, 'C', lambda r: r.update(realpath=V47 + '/ahdath_ajnas.csv'), line=5)


def k8(d):   # تبديل نسبة سجلات A وB (إعادة تسمية الملفات مع تحديث البيان)
    raw = os.path.join(d, 'isolation/raw')
    ren = []
    for f in sorted(os.listdir(raw)):
        if f.startswith(('open_A.', 'open_B.')):
            g = ('open_B.' if f.startswith('open_A.') else 'open_A.') + f.split('.', 1)[1]
            os.rename(os.path.join(raw, f), os.path.join(raw, g + '.tmp'))
            ren.append((f'isolation/raw/{f}', f'isolation/raw/{g}'))
    for f in os.listdir(raw):
        if f.endswith('.tmp'):
            os.rename(os.path.join(raw, f), os.path.join(raw, f[:-4]))
    manifest(d, renamed=ren)
    return 'A<->B'


def k9(d):   # سجلٌّ بـ pid لا يطابق ملفّه (منسوبٌ إلى عمليةٍ أخرى)
    return edit_record(d, 'A', lambda r: r.update(pid=r['pid'] + 1))


def k10(d):  # ملفات تشغيلٍ كامل مفقودة (مع حذفها من البيان): الغياب ليس نجاحاً
    raw = os.path.join(d, 'isolation/raw')
    gone = [f for f in os.listdir(raw) if f.startswith('open_C.')]
    for f in gone:
        os.remove(os.path.join(raw, f))
    m = json.load(open(os.path.join(d, 'MANIFEST.json'), encoding='utf-8'))
    for f in gone:
        m['files'].pop(f'isolation/raw/{f}')
    json.dump(m, open(os.path.join(d, 'MANIFEST.json'), 'w'), ensure_ascii=False, indent=1)
    return f'{len(gone)} files'


CASES = [('K1 قراءةٌ من v47 في تشغيل B', k1, 'V08 B'), ('K2 قراءةٌ من v48 في تشغيل A', k2, 'V08 A'),
         ('K3 مسارٌ مطلق في v48 ومحلولٌ في v47', k3, 'V08 B'), ('K4 مسارٌ خارج جذور الموارد المثبّتة', k4, 'V08 C'),
         ('K5a غياب realpath', k5a, 'V08 B'), ('K5b realpath تالف (نسبيّ)', k5b, 'V08 B'),
         ('K6 الملخّص «صفر مخالفات» والخام فيه مخالفة', k6, 'V08 B'), ('K7 مخالفة الخام مع تحديث بصمته (C)', k7, 'V08 C'),
         ('K8 تبديل نسبة سجلات A وB', k8, 'V08 A'), ('K9 سجلٌّ منسوبٌ إلى عمليةٍ أخرى (pid)', k9, 'V08 A'),
         ('K10 سجلات تشغيلٍ كامل مفقودة', k10, 'V08 C')]


def verify(d):
    p = subprocess.run([sys.executable, '-I', os.path.join(d, 'verify_package.py')], capture_output=True, text=True, cwd=d)
    return p.returncode, [l for l in p.stdout.splitlines() if l.startswith('FAIL ')]


before = sha(os.path.join(SRC, 'MANIFEST.json'))
res = []
for name, fn, expect in CASES:
    t = tempfile.mkdtemp(prefix='v08_')
    d = os.path.join(t, 'pkg'); shutil.copytree(SRC, d)
    rc0, f0 = verify(d)
    keep = os.path.join(t, 'orig'); shutil.copytree(d, keep)
    what = fn(d)
    rc1, f1 = verify(d)
    shutil.rmtree(d); shutil.copytree(keep, d)
    rc2, f2 = verify(d)
    hit = [l for l in f1 if l.startswith('FAIL ' + expect)]
    ok = rc0 == 0 and rc1 != 0 and bool(hit) and not [l for l in f1 if l.startswith('FAIL V01')] and rc2 == 0
    res.append(dict(case=name, mutated=what, original_rc=rc0, corrupted_rc=rc1, corrupted_failures=[l[:400] for l in f1], restored_rc=rc2,
                    detected_by=expect, hash_check_bypassed=not [l for l in f1 if l.startswith('FAIL V01')], sequence_ok=ok))
    print(('PASS ' if ok else 'FAIL ') + f'{name}: الأصل rc={rc0} → الإفساد rc={rc1} ({(hit or f1 or ["لم يسقط"])[0][:110]}) → الاستعادة rc={rc2}')
    shutil.rmtree(t, ignore_errors=True)
after = sha(os.path.join(SRC, 'MANIFEST.json'))
res.append(dict(case='الحزمة الأصلية لم تُمسّ', sequence_ok=before == after))
print(('PASS ' if before == after else 'FAIL ') + 'الحزمة الأصلية لم تُمسّ')
json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1)
ok = all(r['sequence_ok'] for r in res)
print('ALL OK' if ok else 'FAILED')
sys.exit(0 if ok else 1)
