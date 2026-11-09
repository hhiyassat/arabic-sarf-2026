"""tools/fa02/run_tests.py [--out RES.tsv] [ملفات…] — مشغّل الاختبارات بعدٍّ منفصل (FA02، مراجعة المالك: «ALL OK» مع تخطٍّ لا يُعدّ نجاحاً).
يشغّل كل ملف tests/test_*.py (أو المسمّاة) بـ python3 -P -s، ويعدّ من مخرجه سطور PASS وFAIL وSKIP (والتخطّي بأي صيغةٍ تبدأ بـSKIP)،
ويحكم للملف: FAIL إن خرج بغير صفر أو فيه FAIL، وإلا SKIP إن فيه تخطٍّ، وإلا PASS. والملخّص يطبع العدّين (فحوصاً وملفات) منفصلين،
ولا يطبع «ALL OK» إلا إذا كان التخطّي والإخفاق صفراً."""
import os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
args = sys.argv[1:]
out = None
if '--out' in args:
    i = args.index('--out')
    out = args[i + 1]
    del args[i:i + 2]
files = args or sorted(os.path.join('tests', f) for f in os.listdir(os.path.join(ROOT, 'tests')) if f.startswith('test_') and f.endswith('.py'))
rows = []
tot = dict(PASS=0, FAIL=0, SKIP=0)
for f in files:
    t0 = time.time()
    p = subprocess.run([sys.executable, '-P', '-s', f], cwd=ROOT, capture_output=True, text=True)
    lines = (p.stdout + '\n' + p.stderr).splitlines()
    n = {k: sum(1 for l in lines if l.lstrip().startswith(k)) for k in ('PASS', 'FAIL', 'SKIP')}
    st = 'FAIL' if p.returncode != 0 or n['FAIL'] else 'SKIP' if n['SKIP'] else 'PASS'
    for k in tot:
        tot[k] += n[k]
    skips = [l.strip() for l in lines if l.lstrip().startswith('SKIP')]
    rows.append((f, st, p.returncode, n['PASS'], n['FAIL'], n['SKIP'], round(time.time() - t0, 1), ' | '.join(skips)[:300]))
    print(f'{st}\t{f}\trc={p.returncode}\tpass={n["PASS"]}\tfail={n["FAIL"]}\tskip={n["SKIP"]}' + (f'\t{skips[0][:120]}' if skips else ''), flush=True)
fs = {k: sum(1 for r in rows if r[1] == k) for k in ('PASS', 'FAIL', 'SKIP')}
summary = (f'SUMMARY files={len(rows)} files_pass={fs["PASS"]} files_fail={fs["FAIL"]} files_skip={fs["SKIP"]} '
           f'checks_pass={tot["PASS"]} checks_fail={tot["FAIL"]} checks_skip={tot["SKIP"]}')
print(summary)
print('ALL OK' if not fs['FAIL'] and not fs['SKIP'] else ('FAILED' if fs['FAIL'] else 'NOT ALL OK: تخطٍّ لا نجاح'))
if out:
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('file\tstatus\trc\tpass\tfail\tskip\tseconds\tskips\n')
        for r in rows:
            fh.write('\t'.join(map(str, r)) + '\n')
        fh.write('# ' + summary + '\n')
sys.exit(1 if fs['FAIL'] else 2 if fs['SKIP'] else 0)
