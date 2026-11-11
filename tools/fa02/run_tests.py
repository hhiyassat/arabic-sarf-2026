"""tools/fa02/run_tests.py [--out RES.tsv] [--logs DIR] [--timeout S] [ملفات…] — مشغّل الاختبارات بأصنافٍ منفصلة.

(SARF_HFN_V48_VALIDATION_COMPLETION_02 §١١، عن نسخة FA02)
- لكل ملف: رمز الخروج وstdout وstderr كاملةً في DIR/<الاسم>.{stdout,stderr,rc} (DIR الافتراضي: مجلّدٌ مؤقت يُطبع مساره)،
  وSARF_TEST_OUT=DIR يُمرَّر للاختبارات التي تكتب نتائجها (فلا تكتب في reports/ للمالك).
- الأصناف: PASS، FAIL، ERROR (استثناءٌ بعد بدء الفحوص أو بلا سطور فحص)، SKIP، NOT_RUN (رمز 2 مع سطر NOT_RUN)،
  SETUP_ERROR (خروجٌ باستثناء ملفٍّ أو وحدةٍ مفقودة قبل أي فحص)، TIMEOUT.
- العدّ: سطور PASS/FAIL/SKIP المبلَّغة («FAILED n:» و«ALL OK» ليستا فحصاً)، و«Ran N» لـ unittest، و«CHECKS pass= fail= total=» إن أعلنها الاختبار.
  وعدد سطور PASS ليس عدد الاختبارات الكامل، وpass=0 لا يعني خلوّ الملف من الاختبارات: يُعلَن ذلك صراحةً.
- لا يعيد المشغّل أي ملفٍّ في نسخة العمل (أُزيل `git checkout -- reports/nominal_nucleus_02/tests.json` الذي كان يمحو تعديلاً سابقاً):
  تُلتقط حالة نسخة العمل قبل كل ملفٍّ وبعده، وما تغيّر يُسجَّل في عمود worktree_writes، ولا يُستعاد.
- رمز الخروج: 1 إن وُجد FAIL أو ERROR أو TIMEOUT؛ 2 إن وُجد NOT_RUN أو SETUP_ERROR أو SKIP؛ 0 إن نجح الكل."""
import hashlib, json, os, re, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
args = sys.argv[1:]


def opt(name, default=None):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default


out = opt('--out')
logs = opt('--logs') or tempfile.mkdtemp(prefix='sarf_tests_')
timeout = int(opt('--timeout', '3600'))
os.makedirs(logs, exist_ok=True)
files = args or sorted(os.path.join('tests', f) for f in os.listdir(os.path.join(ROOT, 'tests')) if f.endswith('.py') and not f.startswith('_'))
CHECK = re.compile(r'^\s*(PASS|FAIL|SKIP)(?![A-Z])')
SETUP_EXC = re.compile(r'^(FileNotFoundError|ModuleNotFoundError|ImportError|PermissionError|NotADirectoryError)\b', re.M)


def worktree_state():
    st = subprocess.run(['git', '-C', ROOT, 'status', '--porcelain=v1', '--untracked-files=all'], capture_output=True, text=True).stdout.splitlines()
    out_ = {}
    for s in st:
        f = s[3:].split(' -> ')[-1]; p = os.path.join(ROOT, f)
        out_[f] = (s[:2], hashlib.sha256(open(p, 'rb').read()).hexdigest() if os.path.isfile(p) and not os.path.islink(p) else 'link/dir')
    return out_


rows = []
for f in files:
    name = os.path.basename(f)[:-3]
    before = worktree_state()
    t0 = time.time()
    env = dict(os.environ, SARF_TEST_OUT=logs)
    timed_out = False
    try:
        p = subprocess.run([sys.executable, '-P', '-s', f], cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env)
        rc, so, se = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        timed_out = True
        rc = 124
        so = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or '')
        se = (e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or '')) + f'\nTIMEOUT {timeout}s'
    for ext, v in (('stdout', so), ('stderr', se), ('rc', str(rc))):
        open(os.path.join(logs, f'{name}.{ext}'), 'w', encoding='utf-8').write(v)
    after = worktree_state()
    writes = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    lines = (so + '\n' + se).splitlines()
    n = {k: 0 for k in ('PASS', 'FAIL', 'SKIP')}
    for l in lines:
        m = CHECK.match(l)
        if m:
            n[m.group(1)] += 1
    ran = sum(int(x) for x in re.findall(r'^Ran (\d+) tests?', se + so, re.M))
    decl = re.findall(r'^CHECKS pass=(\d+) fail=(\d+) total=(\d+)', so, re.M)
    has_tb = 'Traceback (most recent call last)' in se
    if timed_out:
        st = 'TIMEOUT'
    elif rc == 2 and any(l.startswith('NOT_RUN') for l in lines):
        st = 'NOT_RUN'
    elif rc != 0 and has_tb and not (n['PASS'] or n['FAIL'] or ran) and SETUP_EXC.search(se):
        st = 'SETUP_ERROR'
    elif rc != 0 and has_tb and not n['FAIL']:
        st = 'ERROR'
    elif rc != 0 or n['FAIL']:
        st = 'FAIL'
    elif n['SKIP']:
        st = 'SKIP'
    else:
        st = 'PASS'
    note = []
    if not (n['PASS'] or n['FAIL'] or ran or decl):
        note.append('لا سطور فحص مبلَّغة: نجاحه برمز الخروج وحده، ولا يعني ذلك خلوّه من الاختبارات')
    if decl and int(decl[-1][2]) != n['PASS'] + n['FAIL']:
        note.append(f'المعلن total={decl[-1][2]} يخالف سطور PASS/FAIL المعدودة')
    skips = [l.strip() for l in lines if l.lstrip().startswith('SKIP')]
    reason = next((l for l in lines if l.startswith('NOT_RUN')), '') or (se.strip().splitlines()[-1] if st in ('SETUP_ERROR', 'ERROR', 'TIMEOUT') and se.strip() else '')
    rows.append(dict(file=f, status=st, rc=rc, pass_lines=n['PASS'], fail_lines=n['FAIL'], skip_lines=n['SKIP'], unittest_ran=ran,
                     declared=decl[-1] if decl else None, seconds=round(time.time() - t0, 1), worktree_writes=writes,
                     reason=reason[:300], skips=' | '.join(skips)[:300], note='؛ '.join(note)))
    print(f'{st}\t{f}\trc={rc}\tpass={n["PASS"]}\tfail={n["FAIL"]}\tskip={n["SKIP"]}' + (f'\tran={ran}' if ran else '')
          + (f'\tWRITES={writes}' if writes else '') + (f'\t{reason[:120]}' if reason else ''), flush=True)
K = ('PASS', 'FAIL', 'ERROR', 'SKIP', 'NOT_RUN', 'SETUP_ERROR', 'TIMEOUT')
fs = {k: sum(1 for r in rows if r['status'] == k) for k in K}
summary = (f'SUMMARY files={len(rows)} ' + ' '.join(f'{k.lower()}={fs[k]}' for k in K) +
           f' pass_lines={sum(r["pass_lines"] for r in rows)} fail_lines={sum(r["fail_lines"] for r in rows)} skip_lines={sum(r["skip_lines"] for r in rows)}'
           f' unittest_ran={sum(r["unittest_ran"] for r in rows)} worktree_writers={sum(1 for r in rows if r["worktree_writes"])} logs={logs}')
print(summary)
bad = fs['FAIL'] + fs['ERROR'] + fs['TIMEOUT']
incomplete = fs['NOT_RUN'] + fs['SETUP_ERROR'] + fs['SKIP']
print('ALL OK' if not bad and not incomplete else 'FAILED' if bad else 'NOT ALL OK: ملفاتٌ لم تُشغَّل أو تخطّت — لا نجاح')
if out:
    with open(out, 'w', encoding='utf-8') as fh:
        cols = ['file', 'status', 'rc', 'pass_lines', 'fail_lines', 'skip_lines', 'unittest_ran', 'declared', 'seconds', 'worktree_writes', 'reason', 'skips', 'note']
        fh.write('\t'.join(cols) + '\n')
        for r in rows:
            fh.write('\t'.join(json.dumps(r[c], ensure_ascii=False) if isinstance(r[c], (list, tuple)) else str(r[c]) for c in cols) + '\n')
        fh.write('# ' + summary + '\n')
sys.exit(1 if bad else 2 if incomplete else 0)
