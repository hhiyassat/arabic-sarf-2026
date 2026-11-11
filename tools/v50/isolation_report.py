"""isolation_report.py <logs_dir> <OUT.json> <H48> <H50> — ملخّص العزل لتشغيلات V50C01 (A وB على release_v48؛ C وD على release_v50).

وحدة العدّ: سطرٌ لكل open() لملفٍّ تحت جذرٍ مثبَّت، في كل عملية (ملفّ open_<T>.<pid>). والجذران يُعطيان صراحةً (لا بحثٌ في الأسماء).
نسبة العملية إلى خطوتها من السجلات نفسها (القاعدة المعلنة في v48c3/isolation_report.py): عملية eval وحدها يفتح فيها analyze_cache.py،
والخطوات متتابعة (dump ثم eval ثم axes)، فالأصغر رقماً لـ dump والأكبر لـ axes؛ وفي D: عملية فاحص العقد (sidecar_contract.py) contract_D، والباقي dump_D.
والمخالفات بالمسار المحلول وبالغرض (tools/hfn_isolation/check.py)."""
import glob, json, os, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'hfn_isolation'))
import check as ISO

EXPECT = dict(A='release_v48', B='release_v48', C='release_v50', D='release_v50')


def step_of(t, f, recs, ev_p):
    pid = int(f.rsplit('.', 1)[1])
    if t == 'D':
        return 'contract_D' if any('sidecar_contract.py' in r['caller'] for r in recs) else 'dump_D'
    if pid in ev_p:
        return f'eval_{t}'
    if ev_p and pid < min(ev_p):
        return f'dump_{t}'
    if ev_p:
        return f'axes_{t}'
    return 'UNATTRIBUTED'


def main(d, outp, h48, h50):
    roots = dict(release_v48=h48, release_v50=h50)
    out = dict(roots=roots)
    for t, exp in EXPECT.items():
        files = sorted(glob.glob(os.path.join(d, f'open_{t}.*')))
        recs_by = {f: [json.loads(x) for x in open(f, encoding='utf-8')] for f in files}
        ev_p = [int(f.rsplit('.', 1)[1]) for f, rs in recs_by.items() if any('analyze_cache.py' in r['caller'] for r in rs)]
        per = {}
        for f, recs in recs_by.items():
            res = ISO.check(recs, roots, exp)
            per[os.path.basename(f)] = dict(step=step_of(t, f, recs, ev_p), lines=len(recs), violations=len(res['violations']),
                                            purposes=dict(Counter(r['purpose'] for r in res['records'])))
        allrecs = [r for rs in recs_by.values() for r in rs]
        res = ISO.check(allrecs, roots, exp)
        out[t] = dict(expected=exp, raw_lines=len(allrecs), processes=len(files),
                      by_step={s: sum(v['lines'] for v in per.values() if v['step'] == s) for s in sorted({v['step'] for v in per.values()})},
                      per_process=per, distinct_opens=len({(r['realpath'], r['mode'], r['purpose']) for r in res['records']}),
                      violations=len(res['violations']), violation_kinds=dict(Counter(w for v in res['violations'] for w in v['why'])),
                      violation_examples=res['violations'][:5],
                      other_release=sum(1 for r in res['records'] if r['release'] != exp),
                      ajnas={f'{k[0]}|{k[1]}': v for k, v in Counter((r['purpose'], r['mode']) for r in res['records']
                                                                      if os.path.basename(r['realpath']) == 'ahdath_ajnas.csv').items()})
    json.dump(out, open(outp, 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({t: {k: out[t][k] for k in ('raw_lines', 'processes', 'by_step', 'violations', 'violation_kinds', 'other_release', 'ajnas')}
                      for t in EXPECT}, ensure_ascii=False))
    return out


if __name__ == '__main__':
    o = main(*sys.argv[1:5])
    sys.exit(0 if all(o[t]['violations'] == 0 and o[t]['raw_lines'] > 0 for t in EXPECT) else 1)
