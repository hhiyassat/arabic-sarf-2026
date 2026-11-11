"""isolation_report.py <logs_dir> <steps.log> <OUT.json> — ملخّص العزل من سجلات الفتح النهائية (V48C03 §٨).

وحدة العدّ الخام: سطرٌ واحد لكل استدعاء open() لملفٍّ تحت جذرٍ مثبَّت، في كل عملية (ملفّ open_<T>.<pid>).
وتُنسب كل عمليةٍ إلى خطوتها بقاعدةٍ من السجلات نفسها (لا بوقت الملف، فنهاية eval وبداية axes في الثانية نفسها):
عملية eval_root وحدها يفتح فيها analyze_cache.py؛ والخطوات متتابعة (dump ثم eval ثم axes)، فما رقمه أصغر من رقمها لـ dump وما أكبر لـ axes.
وفي C: عمليات dump_C، وعملية contract_C (فاحص العقد: ما فتح فيه sidecar_contract.py) — بالبادئة نفسها.
والمشتقّ: العدد لكل خطوة، والفتحات المتمايزة (realpath، النمط، الغرض)، والمخالفات بالمسار المحلول (tools/hfn_isolation/check.py).
سبب الفرق عن ملخّص C02 (165/171): ذاك لُخّص بعد انتهاء dump وفي أثناء eval_root، قبل أن يكتب عاملا measure_axes (بالبادئة نفسها)."""
import datetime, glob, json, os, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'hfn_isolation'))
import check as ISO

H47 = '/home/user/ucr/repro03/pinned/hfn/release/release_v47'
H48 = '/home/user/c063/v48/pinned/hfn48/release/release_v48'


def windows(steps, day):
    w, start = {}, {}
    for l in open(steps, encoding='utf-8'):
        p = l.split()
        if len(p) >= 3 and p[1] in ('start', 'exit'):
            t = datetime.datetime.strptime(day + ' ' + p[0], '%Y-%m-%d %H:%M:%S').timestamp()
            if p[1] == 'start':
                start[p[2]] = t
            elif p[2] in start:
                w[p[2]] = (start[p[2]], t + 1)
    return w


def main(d, steps, outp, day):
    roots = dict(release_v47=H47, release_v48=H48)
    out = {}
    for t, exp in (('A', 'release_v47'), ('B', 'release_v48'), ('C', 'release_v48')):
        files = sorted(glob.glob(os.path.join(d, f'open_{t}.*')))
        per = {}
        recs_by = {f: [json.loads(x) for x in open(f, encoding='utf-8')] for f in files}
        pid = lambda f: int(f.rsplit('.', 1)[1])
        ev_p = [pid(f) for f, rs in recs_by.items() if any('analyze_cache.py' in r['caller'] for r in rs)]
        for f, recs in recs_by.items():
            if t == 'C':
                step = 'contract_C' if any('sidecar_contract.py' in r['caller'] for r in recs) else 'dump_C'
            elif pid(f) in ev_p:
                step = f'eval_{t}'
            elif ev_p and pid(f) < min(ev_p):
                step = f'dump_{t}'
            elif ev_p:
                step = f'axes_{t}'
            else:
                step = 'UNATTRIBUTED'
            res = ISO.check(recs, roots, exp)
            per[os.path.basename(f)] = dict(step=step, lines=len(recs), violations=len(res['violations']),
                                            purposes=dict(Counter(r['purpose'] for r in res['records'])))
        allrecs = [json.loads(x) for f in files for x in open(f, encoding='utf-8')]
        res = ISO.check(allrecs, roots, exp)
        out[t] = dict(expected=exp, unit='سطرٌ لكل open() لكل عملية', raw_lines=len(allrecs), processes=len(files),
                      by_step={s: sum(v['lines'] for v in per.values() if v['step'] == s) for s in sorted({v['step'] for v in per.values()})},
                      per_process=per, distinct_opens=len({(r['realpath'], r['mode'], r['purpose']) for r in res['records']}),
                      violations=len(res['violations']), violation_kinds=dict(Counter(w for v in res['violations'] for w in v['why'])),
                      other_release=sum(1 for r in res['records'] if r['release'] != exp),
                      ajnas=dict(Counter((r['purpose'], r['mode']) for r in res['records'] if os.path.basename(r['realpath']) == 'ahdath_ajnas.csv').most_common()))
        out[t]['ajnas'] = {f'{k[0]}|{k[1]}': v for k, v in out[t]['ajnas'].items()}
    out['reconciliation_with_c02_summary'] = dict(
        c02_reported=dict(A=165, B=171, C=504),
        explanation='ملخّص C02 أُخذ بعد انتهاء dump وفي أثناء eval_root: dump (عاملان) + eval_root؛ وأضاف عاملا measure_axes بعده بالبادئة نفسها',
        recomputed_at_c02_moment={t: sum(v['lines'] for v in out[t]['per_process'].values() if v['step'].startswith(('dump', 'eval'))) for t in 'AB'})
    json.dump(out, open(outp, 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({t: {k: out[t][k] for k in ('raw_lines', 'processes', 'by_step', 'distinct_opens', 'violations', 'other_release', 'ajnas')} for t in 'ABC'},
                     ensure_ascii=False))
    print(json.dumps(out['reconciliation_with_c02_summary'], ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else '2026-11-11')
