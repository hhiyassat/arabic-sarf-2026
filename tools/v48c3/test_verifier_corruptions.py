"""test_verifier_corruptions.py <PACKAGE_DIR> <OUT.json> — إفسادات المدقّق المستقل (V48C03 §٦).
كل إفسادٍ على نسخةٍ منفصلة من الحزمة، مع تحديث بصمة الملف المُفسَد في MANIFEST.json حتى يتجاوز فحص البصمة ويختبر الشرط المقصود،
ثم يُشغَّل المدقّق ويُشترط أن يسقط بالفحص المسمّى. والحزمة الأصلية لا تُمسّ (يُتحقق من بصمة MANIFEST قبل وبعد)."""
import base64, gzip, hashlib, json, os, shutil, subprocess, sys, tempfile, zlib
SRC, OUT = sys.argv[1], sys.argv[2]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
before = sha(os.path.join(SRC, 'MANIFEST.json'))


def rehash(d, *files, drop=()):
    m = json.load(open(os.path.join(d, 'MANIFEST.json'), encoding='utf-8'))
    for f in files:
        m['files'][f] = sha(os.path.join(d, f))
    for f in drop:
        m['files'].pop(f, None)
    json.dump(m, open(os.path.join(d, 'MANIFEST.json'), 'w'), ensure_ascii=False, indent=1)


def rewrite_dump(d, name, fn):
    p = os.path.join(d, 'runs', name)
    rows = [json.loads(l) for l in gzip.open(p, 'rt', encoding='utf-8')]
    rows = fn(rows)
    with gzip.open(p, 'wt', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    rehash(d, f'runs/{name}')


def set_row(d, suite, test, status, rc):
    p = os.path.join(d, 'tests', suite, 'suite.tsv')
    L = open(p, encoding='utf-8').read().splitlines()
    L = ['\t'.join([c[0], status, str(rc)] + c[3:]) if c[0] == f'tests/{test}.py' else l for l, c in ((l, l.split('\t')) for l in L)]
    open(p, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    rehash(d, f'tests/{suite}/suite.tsv')


def c1(d):   # اختبارٌ لازم غير منفّذ: NOT_RUN ورمز 2، والبصمات محدّثة
    set_row(d, 'suite48', 'test_upstream', 'NOT_RUN', 2)
    open(os.path.join(d, 'tests/suite48/test_upstream.rc'), 'w').write('2')
    open(os.path.join(d, 'tests/suite48/test_upstream.stdout'), 'w').write('NOT_RUN: SARF_UP_PINS غير معيَّن\n')
    rehash(d, 'tests/suite48/test_upstream.rc', 'tests/suite48/test_upstream.stdout')


def c2(d):   # ملفّ دليلٍ مفقود (مع حذفه من البيان)
    os.remove(os.path.join(d, 'tests/suite47/test_ajnas_consumer.stderr'))
    rehash(d, drop=('tests/suite47/test_ajnas_consumer.stderr',))


def c3(d):   # اختبارٌ مكرَّر مع حذف آخر
    p = os.path.join(d, 'tests/suite48/suite.tsv')
    L = open(p, encoding='utf-8').read().splitlines()
    i = next(k for k, l in enumerate(L) if l.startswith('tests/test_relations.py'))
    j = next(k for k, l in enumerate(L) if l.startswith('tests/test_root.py'))
    L[j] = L[i]
    open(p, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    rehash(d, 'tests/suite48/suite.tsv')


def c4(d):   # تغيير ملخّص المقارنة دون تغيير التفريغات
    p = os.path.join(d, 'transitions/cmp_BC.json')
    j = json.load(open(p, encoding='utf-8')); j['identical_all'] = False
    json.dump(j, open(p, 'w'), ensure_ascii=False, indent=1)
    rehash(d, 'transitions/cmp_BC.json')


def c5(d):   # تغيير التفريغ مع تحديث بصمته: منتَجٌ في C يختلف عن B
    def fn(rows):
        rows[0]['products']['records']['sha'] = '0' * 64
        k = next(iter(rows[0]['products']['records']['keys'])); rows[0]['products']['records']['keys'][k] = '0' * 64
        return rows
    rewrite_dump(d, 'dump_C.jsonl.gz', fn)


def c6(d):   # حالةٌ غير مستقرة متساوية في التشغيلين
    def fn(rows):
        v = next(iter(rows[0]['stability'])); rows[0]['stability'][v]['state'] = 'NOT_CONVERGED'
        return rows
    for n in ('dump_A.jsonl.gz', 'dump_B.jsonl.gz', 'dump_C.jsonl.gz'):
        rewrite_dump(d, n, fn)


def c7(d):   # إرفاقٌ ناقص الهوية أو غير صحيح النوع
    def fn(rows):
        for r in rows:
            sc = json.loads(zlib.decompress(base64.b64decode(r['ajnas_sidecar']['z'])))
            for occ in sc['sidecar'].values():
                for rec in occ:
                    for l in (rec.get('event_side') or {}).get('links') or []:
                        l['is_fact'] = 'False'
                        l['match_constraints']['analysis_id']['value'] = None
                        r['ajnas_sidecar']['z'] = base64.b64encode(zlib.compress(json.dumps(sc, ensure_ascii=False).encode())).decode()
                        return rows
        return rows
    rewrite_dump(d, 'dump_C.jsonl.gz', fn)


def c8(d):   # ملخّص العزل لا يطابق السجلات الخام
    p = os.path.join(d, 'isolation/isolation_report.json')
    j = json.load(open(p, encoding='utf-8')); j['A']['raw_lines'] = 165
    json.dump(j, open(p, 'w'), ensure_ascii=False, indent=1)
    rehash(d, 'isolation/isolation_report.json')


def c9(d):   # تفريغٌ ناقص سورة
    rewrite_dump(d, 'dump_B.jsonl.gz', lambda rows: rows[:-1])


CASES = [('C1 اختبارٌ لازم NOT_RUN ورمز 2 مع تحديث البصمة', c1, 'V02 suite48'), ('C2 ملفّ دليلٍ مفقود', c2, 'V02 suite47'),
         ('C3 اختبارٌ مكرَّر مع حذف آخر', c3, 'V03a suite48'), ('C4 ملخّص المقارنة مغيَّر والتفريغات كما هي', c4, 'V06c'),
         ('C5 التفريغ مغيَّر مع تحديث بصمته', c5, 'V06b'), ('C6 حالةٌ غير مستقرة متساوية في A وB وC', c6, 'V05'),
         ('C7 إرفاقٌ بهويةٍ فارغة وis_fact نصّي', c7, 'V07a'), ('C8 ملخّص العزل يخالف السجلات الخام', c8, 'V08'),
         ('C9 تفريغٌ ناقص سورة', c9, 'V04 B')]
res = []
for name, fn, expect in CASES:
    t = tempfile.mkdtemp(prefix='vcor_')
    d = os.path.join(t, 'pkg'); shutil.copytree(SRC, d)
    fn(d)
    p = subprocess.run([sys.executable, '-I', os.path.join(d, 'verify_package.py')], capture_output=True, text=True, cwd=d)
    fails = [l for l in p.stdout.splitlines() if l.startswith('FAIL ')]
    v01 = [l for l in fails if l.startswith('FAIL V01')]
    ok = p.returncode == 1 and any(l.startswith('FAIL ' + expect) for l in fails) and not v01
    res.append(dict(case=name, expected_check=expect, rc=p.returncode, detected=ok, failing_checks=[l[:160] for l in fails], hash_check_bypassed=not v01))
    print(('PASS ' if ok else 'FAIL ') + name + ' → ' + (fails[0][:120] if fails else 'لم يسقط'))
    shutil.rmtree(t, ignore_errors=True)
after = sha(os.path.join(SRC, 'MANIFEST.json'))
res.append(dict(case='الحزمة الأصلية لم تُمسّ', detected=before == after))
print(('PASS ' if before == after else 'FAIL ') + 'الحزمة الأصلية لم تُمسّ (بصمة MANIFEST قبل وبعد)')
json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1)
ok = all(r['detected'] for r in res)
print('ALL OK' if ok else 'FAILED')
sys.exit(0 if ok else 1)
