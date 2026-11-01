# -*- coding: utf-8 -*-
"""مقارنة نسختين من الشيفرة على المصحف كله، بالموضع والسمة والتحليل والدليل، لا بمجموع الأعداد.

    python3 tools/compare_runs.py --base <مجلد النسخة الأساس> --new <مجلد النسخة الجديدة> [--out reports/compare]

يُفترض أن tools/run_full.sh شُغّل في كلٍّ منهما (فخبيئة التحليل وreports/sentences حديثة).
تُنسخ أداتا التفريغ (eval_features --dump، وdump_operators) من هذه النسخة إلى كلتيهما باسمٍ مؤقت ثم تُحذفان،
فيُقاس الطرفان بأداة قياسٍ واحدة، وتحليل كلٍّ بشيفرته.

المخرجات (فيها قيم QAC المرجعية، فلا تُلتزم؛ reports/compare/ في .gitignore):
  items.csv     كل ما تغيّر: الموضع، الوحدة، السمة أو الأداة، الحالة والقيمة قبلُ وبعدُ، المرجع، الصنف، الدليل قبلُ وبعدُ
  summary.json  الأعداد لكل صنف، وهوية النسختين
  summary.md    الخلاصة مقروءة

أصناف السمات المقابَلة بالمرجع:
  مكتسَبٌ صحيح        لم يكن مثبتاً صحيحاً، وصار مثبتاً يوافق المرجع
  مكتسَبٌ خاطئ        صار مثبتاً يخالف المرجع، ولم يكن مثبتاً بالقيمة نفسها
  صحيحٌ صار خاطئاً    كان مثبتاً يوافق المرجع، وصار مثبتاً يخالفه
  صحيحٌ أُجِّل         كان مثبتاً صحيحاً، وصار مرشّحاً أو مؤجَّلاً
  صحيحٌ فُقد          كان مثبتاً صحيحاً، ولم يعد له سجل (تغيّر التقطيع أو المقابلة)
  خاطئٌ زال           كان مثبتاً خاطئاً، ولم يعد مثبتاً
  خاطئٌ تغيّرت قيمته   مثبتٌ خاطئ قبلُ وبعدُ بقيمتين مختلفتين
"""
import argparse, csv, glob, hashlib, json, os, shutil, subprocess, sys, collections

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument('--base', required=True)
ap.add_argument('--new', default=HERE)
ap.add_argument('--out', default=os.path.join(HERE, 'reports', 'compare'))
ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
ap.add_argument('--reuse', action='store_true', help='لا تُعِد التفريغ إن وُجد')
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
PROVEN = 'مثبت'


def git(root, *a):
    try:
        return subprocess.run(['git', '-C', root, *a], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ''


def ident(root):
    m = hashlib.sha256()
    for p in sorted(glob.glob(os.path.join(root, 'sarf', '*.py'))):
        m.update(os.path.basename(p).encode()); m.update(open(p, 'rb').read())
    dirty = [l for l in git(root, 'status', '--porcelain', '--untracked-files=no').splitlines()
             if l and not l[3:].startswith('reports/')]
    diff = git(root, 'diff', 'HEAD', '--', 'sarf')
    return dict(root=root, commit=git(root, 'rev-parse', 'HEAD'), dirty=dirty, analysis_code_sha=m.hexdigest()[:16],
                analysis_diff_sha=hashlib.sha256(diff.encode()).hexdigest()[:16] if diff else '—')


def dump(root, tag):
    fe, op = os.path.join(args.out, f'{tag}_features.jsonl'), os.path.join(args.out, f'{tag}_operators.jsonl')
    if args.reuse and os.path.exists(fe) and os.path.exists(op):
        return fe, op
    env = dict(os.environ, PYTHONHASHSEED=os.environ.get('PYTHONHASHSEED', '0'))
    tmp = []
    try:
        for src, dst in (('eval_features.py', '_cmp_ef.py'), ('dump_operators.py', '_cmp_ops.py')):
            d = os.path.join(root, 'tools', dst)
            shutil.copy(os.path.join(HERE, 'tools', src), d)
            tmp.append(d)
        # أداة القياس تكتب reports/features_eval.json في مجلدها؛ يُحفظ ويُعاد كما كان
        fj = os.path.join(root, 'reports', 'features_eval.json')
        keep = open(fj, 'rb').read() if os.path.exists(fj) else None
        subprocess.run([sys.executable, 'tools/_cmp_ef.py', '--jobs', str(args.jobs), '--dump', fe], cwd=root, env=env,
                       check=True, stdout=subprocess.DEVNULL)
        if keep is not None:
            open(fj, 'wb').write(keep)
        subprocess.run([sys.executable, 'tools/_cmp_ops.py', op, '--jobs', str(args.jobs)], cwd=root, env=env, check=True,
                       stdout=subprocess.DEVNULL)
    finally:
        for d in tmp:
            os.remove(d)
    return fe, op


def load(p):
    return [json.loads(l) for l in open(p, encoding='utf-8')]


def j(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True) if isinstance(x, (dict, list)) else ('' if x is None else str(x))


IB, IN = ident(args.base), ident(args.new)
fb, ob = dump(args.base, 'base')
fn, on = dump(args.new, 'new')
FB, FN = load(fb), load(fn)
items, C = [], collections.Counter()
per_feat = collections.defaultdict(collections.Counter)

# ١ السمات المقابَلة بالمرجع
def key(r):
    return (r['loc'], r['ui'], r['txt'], r['feat'])
SB = {key(r): r for r in FB if r['kind'] == 'scored'}
SN = {key(r): r for r in FN if r['kind'] == 'scored'}
for k in sorted(set(SB) | set(SN), key=lambda k: ([int(x) for x in k[0].split(':')], k[1] or 0, k[3])):
    b, n = SB.get(k), SN.get(k)
    def pc(r): return r is not None and r['st'] == PROVEN and r['v'] == r['gold']
    def pw(r): return r is not None and r['st'] == PROVEN and r['v'] != r['gold']
    cat_ = None
    if pc(b) and pc(n):
        continue
    if pc(b) and pw(n):
        cat_ = 'صحيحٌ صار خاطئاً'
    elif pc(b) and n is not None:
        cat_ = 'صحيحٌ أُجِّل'
    elif pc(b):
        cat_ = 'صحيحٌ فُقد'
    elif pc(n):
        cat_ = 'مكتسَبٌ صحيح'
    elif pw(n) and not (pw(b) and b['v'] == n['v']):
        cat_ = 'خاطئٌ تغيّرت قيمته' if pw(b) else 'مكتسَبٌ خاطئ'
    elif pw(b) and not pw(n):
        cat_ = 'خاطئٌ زال'
    elif b is not None and n is not None and (b['st'], j(b['v'])) != (n['st'], j(n['v'])):
        cat_ = 'تغيّرٌ في غير المثبت'
    elif (b is None) != (n is None):
        cat_ = 'سجلٌّ غير مثبت ظهر أو غاب'
    if not cat_:
        continue
    C[cat_] += 1
    per_feat[k[3]][cat_] += 1
    r0 = n or b
    items.append(dict(layer='سمة مقابَلة', loc=k[0], unit=k[2], what=k[3], category=cat_,
                      before=f"{b['st']}: {j(b['v'])}" if b else '—', after=f"{n['st']}: {j(n['v'])}" if n else '—',
                      gold=j(r0['gold']), ev_before=j(b and b['ev']), ev_after=j(n and n['ev'])))

# ٢ كل السمات (ومنها ما لا مقابل له): انتقال الحالة
def key2(r):
    return (r['loc'], r['ui'], r['txt'], r['feat'])
AB = {key2(r): r for r in FB if r['kind'] == 'feature'}
AN = {key2(r): r for r in FN if r['kind'] == 'feature'}
trans = collections.Counter()
for k in sorted(set(AB) | set(AN), key=lambda k: ([int(x) for x in k[0].split(':')], k[1] or 0, k[3])):
    b, n = AB.get(k), AN.get(k)
    sb, sn = (b['st'] if b else 'لا سجل'), (n['st'] if n else 'لا سجل')
    if b and n and sb == sn and j(b['v']) == j(n['v']):
        continue
    trans[(k[3], sb, sn)] += 1
    items.append(dict(layer='سمة', loc=k[0], unit=k[2], what=k[3], category=f'{sb} → {sn}' if sb != sn else 'تغيّرت القيمة',
                      before=f"{sb}: {j(b and b['v'])}", after=f"{sn}: {j(n and n['v'])}", gold='',
                      ev_before=j(b and b['ev']), ev_after=j(n and n['ev'])))

# ٣ العوامل
def key3(r):
    return (r['loc'], r['op'], str(r['group']), r['slot'])
OB = {key3(r): r for r in load(ob)}
ON = {key3(r): r for r in load(on)}
op_trans = collections.Counter()
for k in sorted(set(OB) | set(ON), key=lambda k: ([int(x) for x in k[0].split(':')], k[3] if k[3] is not None else -1, k[1], k[2])):
    b, n = OB.get(k), ON.get(k)
    fields = ('st', 'target', 'observed', 'consistent', 'why')
    if b and n and all(j(b[f]) == j(n[f]) for f in fields):
        continue
    sb, sn = (b['st'] if b else 'لا مرشّح'), (n['st'] if n else 'لا مرشّح')
    op_trans[(sb, sn)] += 1
    w = (n or b)['word']
    items.append(dict(layer='عامل', loc=k[0], unit=w, what=f'{k[1]} مج{k[2]} خانة{k[3]}',
                      category=f'{sb} → {sn}' if sb != sn else 'تغيّر الدليل أو المعمول',
                      before=f"{sb}: معمول {b['target']}، مكتوب {b['observed']}" if b else '—',
                      after=f"{sn}: معمول {n['target']}، مكتوب {n['observed']}" if n else '—', gold='',
                      ev_before=j(b and b['why']), ev_after=j(n and n['why'])))

# ٤ الجمل وعلاقاتها (reports/sentences)
STAT = ('مرخّصة', 'مرجّحة', 'مرشّحة', 'مرفوضة')
def sentences(root):
    out = {}
    for p in sorted(glob.glob(os.path.join(root, 'reports', 'sentences', 'surah_*.csv'))):
        for r in csv.DictReader(open(p, encoding='utf-8')):
            rel = next((v for k, v in r.items() if k and k.startswith('العلاقات')), '') or ''
            out[(r['من'], r['إلى'], r['النص'])] = dict(rel=rel, state=r['الحالة'], why=r['سبب الحدّ'])
    return out
JB, JN = sentences(args.base), sentences(args.new)
rel_count = {t: collections.Counter() for t in ('base', 'new')}
for t, S in (('base', JB), ('new', JN)):
    for x in S.values():
        for s_ in STAT:
            rel_count[t][s_] += x['rel'].count(f'[{s_}]')
sent_c = collections.Counter()
def lk(k):
    return [int(x) for x in k[0].split(':')]
for k in sorted(set(JB) | set(JN), key=lk):
    b, n = JB.get(k), JN.get(k)
    if b and n and b['rel'] == n['rel'] and b['state'] == n['state']:
        continue
    c_ = 'حدٌّ جديد' if not b else 'حدٌّ زال' if not n else 'تغيّرت العلاقات أو الحالة'
    sent_c[c_] += 1
    items.append(dict(layer='جملة', loc=f'{k[0]}–{k[1]}', unit=k[2][:60], what='العلاقات', category=c_,
                      before=(b['state'] + ' | ' + b['rel']) if b else '—', after=(n['state'] + ' | ' + n['rel']) if n else '—',
                      gold='', ev_before=b and b['why'] or '', ev_after=n and n['why'] or ''))

# ٥ العلاقة الواحدة: النواة ونوع العلاقة وأداتها، بترتيب ورودها في السورة (لا يتوقف على حدود الجمل)
import re
BOND = re.compile(r'([^،←\[\]]*?«[^»]*»)\s*←\s*(.*?)\s*\[(' + '|'.join(STAT) + r')\]')
def bonds(S):
    out, occ = {}, collections.Counter()
    for k in sorted(S, key=lk):
        for m in BOND.finditer(S[k]['rel']):
            nuc, lab, st_ = m.group(1).strip(' ،'), m.group(2), m.group(3)
            kind = re.split(r'[«:(]', lab)[0].strip()
            tool = (re.findall(r'«([^»]*)»', lab) or [''])[0]
            base = (k[0].split(':')[0], nuc, kind, tool)
            occ[base] += 1
            out[base + (occ[base],)] = dict(st=st_, label=lab, sent=f'{k[0]}–{k[1]}')
    return out
BB, BN = bonds(JB), bonds(JN)
bond_c = collections.Counter()
for k in sorted(set(BB) | set(BN), key=lambda k: (int(k[0]), k[1:])):
    b, n = BB.get(k), BN.get(k)
    sb, sn = (b['st'] if b else 'لا علاقة'), (n['st'] if n else 'لا علاقة')
    if b and n and sb == sn and b['label'] == n['label']:
        continue
    bond_c[(k[2], sb, sn)] += 1
    items.append(dict(layer='علاقة', loc=(n or b)['sent'], unit=k[1], what=f'{k[2]} «{k[3]}» #{k[4]}',
                      category=f'{sb} → {sn}' if sb != sn else 'تغيّر الوصف', before=f"{sb}: {b['label']}" if b else '—',
                      after=f"{sn}: {n['label']}" if n else '—', gold='', ev_before='', ev_after=''))

with open(os.path.join(args.out, 'items.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['layer', 'loc', 'unit', 'what', 'category', 'before', 'after', 'gold', 'ev_before', 'ev_after'])
    w.writeheader()
    w.writerows(items)
summary = dict(base=IB, new=IN, scored=dict(C), scored_by_feature={k: dict(v) for k, v in per_feat.items()},
               feature_transitions={f'{a} | {b} → {c}': v for (a, b, c), v in sorted(trans.items())},
               operator_transitions={f'{a} → {b}': v for (a, b), v in sorted(op_trans.items())},
               sentences=dict(sent_c), bond_transitions={f'{a} | {b} → {c}': v for (a, b, c), v in sorted(bond_c.items())},
               relations_by_status={t: dict(v) for t, v in rel_count.items()},
               items=len(items))
json.dump(summary, open(os.path.join(args.out, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

L = ['# مقارنة نسختين على المصحف كله', '',
     f"- الأساس: `{IB['commit'][:10]}`، تعديلات غير ملتزم بها: {len(IB['dirty'])}، بصمة شيفرة التحليل `{IB['analysis_code_sha']}`",
     f"- الجديد: `{IN['commit'][:10]}`، تعديلات غير ملتزم بها: {len(IN['dirty'])} {IN['dirty']}، بصمة شيفرة التحليل "
     f"`{IN['analysis_code_sha']}`، بصمة فرق التحليل `{IN['analysis_diff_sha']}`", '',
     '## السمات المقابَلة بالمرجع', '', '| السمة | ' + ' | '.join(CATS := [
         'مكتسَبٌ صحيح', 'مكتسَبٌ خاطئ', 'صحيحٌ صار خاطئاً', 'صحيحٌ أُجِّل', 'صحيحٌ فُقد', 'خاطئٌ زال', 'خاطئٌ تغيّرت قيمته',
         'تغيّرٌ في غير المثبت', 'سجلٌّ غير مثبت ظهر أو غاب']) + ' |', '|' + '---|' * (len(CATS) + 1)]
for f_, c in sorted(per_feat.items()):
    L.append(f'| {f_} | ' + ' | '.join(str(c.get(x, 0)) for x in CATS) + ' |')
L.append('| **المجموع** | ' + ' | '.join(f'**{C.get(x, 0)}**' for x in CATS) + ' |')
L += ['', '## العوامل: انتقال الحكم', ''] + [f'- {a} → {b}: {v}' for (a, b), v in sorted(op_trans.items())]
L += ['', '## الجمل', ''] + [f'- {k}: {v}' for k, v in sorted(sent_c.items())]
L += ['', '## العلاقات بحالتها', '', '| الحالة | الأساس | الجديد |', '|---|---|---|'] + \
     [f"| {s_} | {rel_count['base'][s_]} | {rel_count['new'][s_]} |" for s_ in STAT]
L += ['', '## العلاقة الواحدة: نوعها وحالتها قبلُ ← بعدُ', '', '| نوع العلاقة | قبلُ | بعدُ | العدد |', '|---|---|---|---|'] + \
     [f'| {a} | {b} | {c} | {v} |' for (a, b, c), v in sorted(bond_c.items(), key=lambda x: -x[1])]
L += ['', '## انتقال حالة السمات (كلها، ومنها ما لا مقابل له)', ''] + \
     [f'- {a}: {b} → {c}: {v}' for (a, b, c), v in sorted(trans.items())]
L += ['', f'التفاصيل كلها بالموضع والسمة والدليل: `items.csv` ({len(items)} سطراً).']
open(os.path.join(args.out, 'summary.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('\n'.join(L))
