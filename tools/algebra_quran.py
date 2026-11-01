#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/algebra_quran.py — الجبر اللساني على المصحف كله: يبني المستويات الستة لكل آية
(خلية ≺ مقطع ≺ وحدة لفظية ≺ جملة/آية ≺ فقرة/سورة ≺ موضوع/مصحف)، ويفحص المبرهنات الخمس آليّاً
على كل وقوع، ويكتب reports/algebra_metrics.json وreports/algebra_report.html.

يحتاج data/quran_hafs.tsv، وHFN (SARF_HFN أو مساره المعتاد).
الاستعمال: python3 tools/algebra_quran.py [--limit N]
"""
import os, sys, json, argparse, collections, html

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.algebra import (Trace, clause_start, word_feats, sentence_geo, mushaf_layer, linguistic_layer, cross_ayah_links, SENTENCE, DISCOURSE, render_sentence, render_cells, spans, flatten, build, cv,
                          Geo, Cell, LEVELS, PARAGRAPH, TOPIC)

ap = argparse.ArgumentParser()
ap.add_argument('--limit', type=int, default=0)
ap.add_argument('--no-cross', action='store_true', help='بلا فحص الروابط عبر حدّ الآية (أسرع)')
ap.add_argument('--reanalyze-every', type=int, default=20, help='كل كم آية يُفحص Analyze(Render(a)) ∋ a')
ap.add_argument('--all', action='store_true', help='يُعاد تحليل السور المجازة أيضاً (حين يُكتشف خطأٌ يمسّ السابق)')
ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1, help='عدد العمليات المتوازية على السور')
args = ap.parse_args()

import time as _time
_T0 = [_time.time()]
TIMING = {}


def _phase(name):
    # زمن كل مرحلة (لتقصير التشغيل الكامل): يُطبع ويُحفظ في المقاييس
    t = _time.time()
    TIMING[name] = round(t - _T0[0], 1)
    _T0[0] = t
    print(f'⏱ {name}: {TIMING[name]}ث', file=sys.stderr)


cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
rows = [l.rstrip('\n').split('\t') for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8')]
if args.limit:
    rows = rows[:args.limit]

C = collections.Counter()
unit_reason = collections.Counter()
open_kind = collections.Counter()
close_route = collections.Counter()
fail = collections.defaultdict(list)
by_surah = collections.defaultdict(list)
samples = {}
SAMPLE_REFS = {(37, 137), (37, 138), (112, 1), (112, 2), (112, 4), (2, 282), (5, 6), (18, 60), (8, 33), (2, 283), (42, 11), (2, 173), (2, 194),
               (1, 2), (21, 57), (3, 26), (10, 59), (6, 32), (49, 10), (35, 28), (18, 110), (47, 20)}


def unit_expr(G):
    cells = G.O['cells']
    cs = ''.join(c.show() for c in cells)
    if G.Theta.get('lex') and not G.Theta.get('R'):
        return f'{G.O["text"]} = Lex[{G.Theta["lex"]}]({cs})'
    if G.closed and G.Theta.get('R'):
        sy = ' ⊕ '.join(''.join(c.show() for c in S.A) for S in G.A)
        F = G.Theta.get('F') or {}
        f = '، '.join(f'{k}={v}' for k, v in F.items() if v)
        return (f'{G.O["text"]} = Realize({" ".join(G.Theta["R"])}, {G.Theta["P"]}{"; " + f if f else ""}) = {sy}'
                f'   α=⟨{", ".join(G.Theta["alpha"])}⟩   β=⟨{" ".join(G.Theta.get("beta", []))}⟩')
    return f'{G.O["text"]} = {cs}   ⟂ معلّق: {G.O.get("deferred", "")}'


def check_verse(s, v, a, S, units, T):
    ok = {}
    # المبرهنة الأولى: حفظ الوقوعات — كل موضع رسمٍ مغطّى مرةً، وكل خلية بلغها البناء
    t1 = True
    all_ids = set()
    for G in units.values():
        txt, seen = render_cells(G.O['cells'], G.O['text'], G.O.get('orphans', ()))
        if sorted(seen) != list(range(len(spans(G.O['text'])))) or len(seen) != len(set(seen)):
            t1 = False
            fail['T1'].append(f'{s}:{v} {G.O["text"]}')
        all_ids |= {c.id for c in G.O['cells']}
    reach = {c.id for c in flatten(S)}
    if reach != all_ids:
        t1 = False
        fail['T1'].append(f'{s}:{v} خلايا لم يبلغها البناء: {len(all_ids - reach)}')
    ok['T1'] = t1
    # المبرهنة الثانية: اتساق الجذر والوزن والتقطيع في الوحدة المغلقة
    t2 = True
    for G in units.values():
        if G.tau[1] != 'مقطَّعة':
            continue
        if G.A and all(isinstance(x, Geo) for x in G.A):
            flat = [c for X in G.A for c in X.A]
            whole = not G.O.get('pending')
            C['cut_units_syllabified'] += whole
            if whole:
                C['beta_agrees'] += bool(G.Theta.get('beta_agrees'))
                if not G.Theta.get('beta_agrees') and len(fail['beta']) < 60:
                    fail['beta'].append(f'{s}:{v} {G.O["text"]} الجبر={G.Theta.get("beta")} المقطِّع={[x["cv"] for x in a["segments"][G.O["word_index"]]["units"][G.O["unit"]]["syllables"]]}')
        if G.closed:
            alpha = G.Theta.get('alpha') or []
            if G.Theta.get('protected'):
                # الوحدة المحمية دستورياً لا خريطة جذرية لها (لا يُطالَب بما منعه الدستور): تُفحص خلاياها وتقطيعها ورسمها
                C['T2_na_protected'] += 1
                if flat == G.O['cells']:
                    C['T2_na_protected_cells_ok'] += 1
                else:
                    t2 = False
                    fail['T2'].append(f'{s}:{v} {G.O["text"]}: وحدة محمية لم تُحفظ خلاياها')
                continue
            C['T2_applicable'] += 1
            good = flat == G.O['cells'] and len(alpha) == len(flat) and None not in alpha
            if not good:
                t2 = False
                C['T2_applicable_fail'] += 1
                fail['T2'].append(f'{s}:{v} {G.O["text"]}: ' + ('الخلايا لا تطابق التقطيع' if flat != G.O['cells'] else
                                                             'الخريطة الجذرية الوزنية ناقصة'))
            else:
                C['T2_applicable_pass'] += 1
    ok['T2'] = t2
    # المبرهنة الثالثة والرابعة: كل مغلقٍ بشهادتين صالحتين ولا التزام لازم مفتوح فيه
    t34 = True
    stack = [S]
    while stack:
        X = stack.pop()
        if isinstance(X, Cell):
            continue
        if X.closed and (X.ec is None or X.eb is None or not X.ec.valid() or not X.eb.valid() or X.open_required()):
            t34 = False
            fail['T3'].append(f'{s}:{v} {X.id}')
        stack.extend(X.A)
        stack.extend(x for x in X.O.get('pending', []) if isinstance(x, (Geo, Cell)))
    ok['T3'] = ok['T4'] = t34
    C['trace_ops'] += len(T)
    C['trace_extend'] += sum(1 for t in T if t['op'] == 'Extend')
    C['trace_close'] += sum(1 for t in T if t['op'] == 'Close')
    C['trace_defer'] += sum(1 for t in T if t['op'] == 'Defer')
    # المبرهنة الخامسة: Render(Analyze(x)) = x
    r = render_sentence(S, units)
    ok['T5'] = r == a['normalized']
    if not ok['T5']:
        fail['T5'].append(f'{s}:{v}')
    return ok, r


# السور المجازة (اقتراح صاحب النظرية): يُحمَّل تحليلها من الخبيئة ولا يُعاد؛ وتُعاد طبقة الجمل عليها لتُقارن
# بالملف المجاز، فإن اختلف فذلك خطأٌ يمسّ السابق: يُبلَّغ، ولا يُكتب فوق المجاز، والإعادة من البداية (--all) قرارٌ
import csv as _csv, gzip as _gzip, pickle as _pickle, hashlib as _hashlib
APPROVED_CSV = H + 'approved/surahs.csv'
APPROVED = {int(r['surah']): r for r in _csv.DictReader(open(APPROVED_CSV, encoding='utf-8'))} \
    if os.path.exists(APPROVED_CSV) else {}
CACHE = H + 'data/cache/'
def _cache_path(s_):
    return f'{CACHE}surah_{s_:03d}.pkl.gz'
# بصمة الاعتماديات (مراجعة التقرير الخامسة ٤): صلاح الخبيئة مربوطٌ بالنص وبكل ما أنتج التحليل — الكود، وفهرس العوامل،
# وملف المبنيات، وملفات HFN، وأبنية سيبويه. فإن تغيّر شيءٌ منها بطلت الخبيئة: يُعاد التحليل، ويُقارن بالمجاز دون مساسه
from sarf.analyze_cache import dependency_files, fingerprint
DEPS = fingerprint(dependency_files(), os.environ.get('SARF_DEP_SALT', '').encode())
def _surah_text_fp(s_):
    return _hashlib.sha256('\n'.join(t for ss, _, t in rows if int(ss) == s_).encode()).hexdigest()
def _cache_valid(s_):
    if not os.path.exists(_cache_path(s_)):
        return False
    pack = _pickle.loads(_gzip.decompress(open(_cache_path(s_), 'rb').read()))
    ok = pack.get('deps') == DEPS and pack.get('text') == _surah_text_fp(s_)
    if not ok:
        C['cache_invalidated'] += 1
        fail['cache_invalidated'].append(f'سورة {s_}: تغيّرت اعتماديات تحليلها أو نصّها، فأُعيد تحليلها')
    return ok
frozen = {s_ for s_ in APPROVED if not args.all and _cache_valid(s_)}
# بطلان الخبيئة يُسجَّل هنا، قبل التحليل الذي يصفّر العدّادات (في العملية نفسها أو في عمليات التوازي)، فيُعاد بعده
INVALIDATED = (C['cache_invalidated'], list(fail['cache_invalidated']))
loaded, fresh = set(), collections.defaultdict(list)
verses = []
cross, checked_ends, prev = [], set(), None
ANALYSES = {}                                      # خبيئة التحليل للأدوات التالية (sarf/analyze_cache.py)


def _merge_pack(s, pack):
    global cross, checked_ends
    for r_ in pack['verses']:
        C.update(r_['C']); close_route.update(r_['close_route']); unit_reason.update(r_['unit_reason'])
        for k_, xs in r_['fail'].items():
            fail[k_] += xs
        by_surah[s].append(r_['item'])
        if r_.get('sample'):
            samples[(r_['item'][0], r_['item'][1])] = r_['sample']
    cross += pack['cross']
    checked_ends |= set(pack['checked_ends'])


def _surah_pack(job):
    """تحليل سورةٍ واحدة في عمليةٍ مستقلة (التوازي على السور): تُصفَّر العدّادات، ويُعاد سجلّ السورة بالبنية نفسها
    التي تُحفظ في الخبيئة، فيُدمج في العملية الأم كما يُدمج المحمَّل منها"""
    global C, close_route, unit_reason, fail, by_surah, samples, cross, checked_ends, prev, fresh
    s_job, rows_job = job
    C, close_route, unit_reason = collections.Counter(), collections.Counter(), collections.Counter()
    fail, by_surah, samples, fresh = collections.defaultdict(list), collections.defaultdict(list), {}, collections.defaultdict(list)
    cross, checked_ends, prev = [], set(), None
    an = {}
    for n, (s, v, text) in rows_job:
        s, v = int(s), int(v)
        snap = (C.copy(), close_route.copy(), unit_reason.copy(), {k_: len(x) for k_, x in fail.items()}, len(cross),
                set(checked_ends))
        a = analyze(cat, text)
        T = Trace()
        S, units = sentence_geo(a, f'Q{s}:{v}', T)
        # الروابط عبر حدّ الآية: الآية السابقة من السورة نفسها مع هذه
        cur = dict(s=s, v=v, text=text, a=a, units=units, S=S)
        if not args.no_cross and prev is not None and prev['s'] == s:
            cross += cross_ayah_links(lambda t: analyze(cat, t), prev, cur)
            checked_ends.add((prev['s'], prev['v']))
        prev = cur
        ok, rendered = check_verse(s, v, a, S, units, T)
        for k, x in ok.items():
            C[f'{k}_pass'] += x
        C['verses'] += 1
        for G in units.values():
            C['units'] += 1
            C['cells'] += len(G.O['cells'])
            C['syllables'] += sum(1 for X in G.A if isinstance(X, Geo))
            C['syllables_closed'] += sum(1 for X in G.A if isinstance(X, Geo) and X.closed)
            if G.closed:
                C['units_closed'] += 1
                route = ('حماية دستورية: ' + G.Theta['protected']['cls'] if G.Theta.get('protected') else
                         'Lex' if not G.Theta.get('R') else
                         'Realize: فعل' if (G.Theta.get('F') or {}).get('kind') != 'اسم' else
                         'Realize: اسم فاعل/مفعول' if 'اسم' in str(G.Theta.get('P', ''))[:4] else
                         'Realize: بناء سيبويه' if str(G.Theta.get('P', '')).startswith('بناء سيبويه') else 'بناء معجمي: مصدر وغيره')
                close_route[route] += 1
            else:
                unit_reason[G.O.get('deferred', '').split(':')[0]] += 1
        # Analyze(Render(a)) ∋ a على عيّنة: إعادة التحليل من النص المستخرَج تعطي الخلايا والإغلاق أنفسهما
        if args.reanalyze_every and n % args.reanalyze_every == 0:
            a2 = analyze(cat, rendered)
            S2, units2 = sentence_geo(a2, f'Q{s}:{v}', Trace())
            same = ({k: ([c.key() for c in G.O['cells']], G.closed) for k, G in units.items()} ==
                    {k: ([c.key() for c in G.O['cells']], G.closed) for k, G in units2.items()})
            # تكافؤ البنية لا الخلايا وحدها (مراجعة التقرير ٩): الجذر والوزن وα لكل وحدة، والروابط والتزامات الجملة
            def struct(units_, S_):
                return ({k: (str(G.Theta.get('R')), str(G.Theta.get('P')), tuple(G.Theta.get('alpha') or ()), G.closed)
                         for k, G in units_.items()},
                        sorted((b[0], str(b[1]), str(b[2])) for b in S_.B),
                        sorted((o.name, o.met) for o in S_.Omega))
            same_struct = struct(units, S) == struct(units2, S2)
            C['reanalyze'] += 1
            C['reanalyze_same'] += same
            C['reanalyze_same_structure'] += same and same_struct
            if not same:
                fail['T5b'].append(f'{s}:{v}')
        for o in S.Omega:
            k = o.name.split(' ')[0]
            if k in ('خبر', 'مفعول', 'معمول', 'فاعل'):
                C[f'obl_{k}'] += 1
                C[f'obl_{k}_met'] += bool(o.met)
                if k == 'خبر' and o.met and o.ev:
                    C['khabar_kind:' + o.ev.cause.split(' ', 2)[-1]] += 1
        lite = dict(verse=a['verse'], normalized=a['normalized'], segments=[dict(word=g['word'], units=g['units']) for g in a['segments']],
                    starts=[clause_start(a, wi) for wi in range(len(a['segments']))], feats=word_feats(a),
                    operators=[dict(word_index=f['word_index'], operator=f['operator'], group=f['group'], status=f.get('status'))
                               for f in a['operators']],
                    relations=[dict(word_index=r['word_index'], operator=r['operator'], group=r['group'],
                                    target=bool(r.get('target'))) for r in a.get('relations', [])])
        by_surah[s].append((s, v, lite, units, S))
        if (s, v) in SAMPLE_REFS:
            samples[(s, v)] = dict(text=a['normalized'], units={G.id: unit_expr(G) for G in units.values()})
        fresh[s].append(dict(C=C - snap[0], close_route=close_route - snap[1], unit_reason=unit_reason - snap[2],
                             fail={k_: x[snap[3].get(k_, 0):] for k_, x in fail.items() if len(x) > snap[3].get(k_, 0)},
                             item=by_surah[s][-1], sample=samples.get((s, v)), cross=cross[snap[4]:],
                             checked_ends=sorted(checked_ends - snap[5])))
        if n % 500 == 0:
            print(n, dict(C), file=sys.stderr)

        an[text] = a
    recs = fresh[s_job]
    return s_job, dict(deps=DEPS, text=_surah_text_fp(s_job),
                       verses=[{k_: r_[k_] for k_ in ('C', 'close_route', 'unit_reason', 'fail', 'item', 'sample')} for r_ in recs],
                       cross=[c for r_ in recs for c in r_['cross']], checked_ends=[e for r_ in recs for e in r_['checked_ends']]), an


jobs = []
by_s = collections.OrderedDict()
for n, (s, v, text) in enumerate(rows):
    by_s.setdefault(int(s), []).append((n, (s, v, text)))
for s_, rs_ in by_s.items():
    if s_ not in frozen:
        jobs.append((s_, rs_))
packs = {}
if jobs:
    import multiprocessing as _mp
    nj = max(1, min(args.jobs, len(jobs)))
    if nj > 1:
        with _mp.get_context('fork').Pool(nj) as pool:
            for s_, pack, an in pool.imap_unordered(_surah_pack, sorted(jobs, key=lambda j: -len(j[1])), chunksize=1):
                packs[s_] = pack
                ANALYSES.update(an)
                print('سورة', s_, file=sys.stderr)
    else:
        for job in jobs:
            s_, pack, an = _surah_pack(job)
            packs[s_] = pack
            ANALYSES.update(an)
    C, close_route, unit_reason = collections.Counter(), collections.Counter(), collections.Counter()
    fail, by_surah, samples = collections.defaultdict(list), collections.defaultdict(list), {}
    cross, checked_ends = [], set()
    if INVALIDATED[0]:
        C['cache_invalidated'], fail['cache_invalidated'] = INVALIDATED[0], list(INVALIDATED[1])
fresh_packs = {}
for s_ in by_s:
    if s_ in frozen:
        pack = _pickle.loads(_gzip.decompress(open(_cache_path(s_), 'rb').read()))
        C['surahs_from_cache'] += 1
    else:
        pack = packs[s_]
        fresh_packs[s_] = pack
    _merge_pack(s_, pack)
# خبيئة كل سورةٍ حُلِّلت الآن، لتُحمَّل إن أُجيزت
os.makedirs(CACHE, exist_ok=True)
for s_, pack in fresh_packs.items():
    open(_cache_path(s_), 'wb').write(_gzip.compress(_pickle.dumps(pack, protocol=5)))
# خبيئة التحليل الصرفي للأدوات التالية (eval_case، eval_root، eval_protected، audit_protected): بصمة الاعتماديات نفسها
if ANALYSES and not args.limit:
    from sarf.analyze_cache import save as _save_an
    _save_an(ANALYSES, DEPS)

# الطبقتان على النص كله: المصحفية (كلمة ← آية ← سورة ← مصحف) واللغوية (جملة ← وحدة خطابية ← خطاب السورة)
T = Trace()
items = [x for s in sorted(by_surah) for x in by_surah[s]]
_phase('التحليل')
MU = mushaf_layer([(s, v, a, units) for s, v, a, units, S in items], T)
import subprocess
a_id = subprocess.run(['git', '-C', H, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
_phase('الطبقة المصحفية')
def _group(s_):
    return 2 if s_ <= 2 else s_                    # الفاتحة والبقرة معاً: ميزانية الاختبارات المضادة كالتشغيل التتابعي


def _layer_job(g_):
    # الطبقة اللغوية لسورةٍ أو أكثر (السور مستقلةٌ فيها): تُعاد أشجارها وعدّاداتها وسجلات حدودها وعيّناتها
    its = [x for x in items if _group(x[0]) == g_]
    ss = {x[0] for x in its}
    cr = [c for c in cross if any(str(c.get('src', '')).startswith(f'Q{x}:') for x in ss)]
    out_ = linguistic_layer(its, Trace(), a_id=f'experiment@{a_id}', cross=cr,
                            checked_ends=frozenset(e for e in checked_ends if e[0] in ss), mut_budget=400 if g_ == 2 else 0)
    return g_, out_, getattr(linguistic_layer, 'samples', {})


surahs_ = sorted({_group(x[0]) for x in items})
if args.jobs > 1 and len(surahs_) > 1:
    import multiprocessing as _mp
    res_ = {}
    with _mp.get_context('fork').Pool(min(args.jobs, len(surahs_))) as pool:
        for s_, out_, smp in pool.imap_unordered(_layer_job, sorted(surahs_, key=lambda x: -sum(1 for y in items if _group(y[0]) == x)),
                                                  chunksize=1):
            res_[s_] = (out_, smp)
    LT, st, brecs = [], collections.Counter(), []
    SMP = collections.defaultdict(list)
    FAILS = collections.defaultdict(list)
    for s_ in surahs_:
        (lt_, st_, br_), smp = res_[s_]
        LT += lt_; st.update(st_); brecs += br_
        for k_, v_ in smp.items():
            if k_ == 'coord_failures':
                for kk, vv in v_.items():
                    FAILS[kk] += vv
            else:
                SMP[k_] += v_
    # العيّنات مقصورةٌ كما في التشغيل التتابعي: أول ما يُجمع بترتيب السور، وسجلات العطف المرصودة كلها
    from sarf.algebra import COORD_WATCH as _CW
    caps = dict(rel=40, cond=40, coord=60)
    smp_all = {k_: v_[:caps[k_]] if k_ in caps else v_ for k_, v_ in SMP.items()}
    if 'coord_records' in smp_all:
        cr_ = SMP['coord_records']
        smp_all['coord_records'] = cr_[:60] + [r for r in cr_[60:] if r['text_id']['verse'] in _CW]
    smp_all['coord_failures'] = {k_: v_[:30] if k_ != 'coordmut_examples' else v_[:24] for k_, v_ in FAILS.items()}
    linguistic_layer.samples = smp_all
else:
    LT, st, brecs = linguistic_layer(items, T, a_id=f'experiment@{a_id}', cross=cross, checked_ends=frozenset(checked_ends))
C['ayah_ends_checked'] = len(checked_ends)
# الفاحص المستقل: يعيد اشتقاق الالتزامات من سجلّ التحليل، ولا يثق بشهادة الإغلاق
from sarf.checker import check_layer
_phase('الطبقة اللغوية')
chk_n, chk_bad, chk_list = check_layer(LT, {(s_, v_): a_ for s_, v_, a_, _, _ in items})
C['checker_closed'], C['checker_rejected'] = chk_n, chk_bad
# ملف الجمل لكل سورة (reports/sentences/surah_NNN.csv)، ومقارنة المجازة بملفها المجاز
words_of = {(s_, v_): [g['word'] for g in a_['segments']] for s_, v_, a_, _, _ in items}
os.makedirs(H + 'reports/sentences/drift', exist_ok=True)
COLS = ['الوحدة', 'من', 'إلى', 'النص', 'الحالة', 'سبب الحدّ', 'الخلوّ من التعلّق الخارجي', 'النوى',
        'العلاقات (النواة ← العلاقة [حالتها: مرخّصة، مرجّحة، مرشّحة])', 'علاقات غير محسومة',
        'وقوعات بلا موضع (الموضع [الوحدة] «النص»: الناقص)', 'الالتزامات المفتوحة']
SENT_BASE = os.environ.get('SARF_SENTENCES_BASE', '')   # الإصدار المرجعي لبيان التغيّر
CHANGES = []                                       # بيان التغيّر عن الملف السابق لكل صف (مراجعة ملفات الجمل ٤)
_phase('الفاحص المستقل')
for SP in LT:
    s_ = int(SP.id.lstrip('L')) if SP.id.lstrip('L').isdigit() else None
    if s_ is None:
        continue
    out_rows = []
    for D in SP.A + SP.O.get('pending', []):
        for J in D.A + D.O.get('pending', []):
            loc = [tuple(x) for x in J.O.get('location', [])]
            if not loc:
                continue
            rec_ = D.O.get('boundary') or {}
            out_rows.append([J.id, '%d:%d:%d' % loc[0], '%d:%d:%d' % loc[-1],
                             ' '.join(words_of[(x[0], x[1])][x[2]] for x in loc),
                             # الوحدة المؤجَّلة لم يثبت أنها جملة واحدة: محفوظةٌ لم يثبت تقسيمها الداخلي
                             'مستوفاة محلياً وفق القواعد المنفَّذة' if J.closed else
                             'وحدة تحليلٍ مؤجَّلة: لم يثبت تقسيمها الداخلي ولا أنها جملة واحدة',
                             'آخر السورة: نهاية نطاق القراءة، لا حدّ جملةٍ مثبت' if rec_.get('J_why') == 'آخر السورة'
                             else rec_.get('J_why', ''),
                             (J.O.get('closure') or {}).get('external', ''), '، '.join(J.O.get('nuclei', [])),
                             '، '.join(f'{x[0]} ← {x[1]} [{x[2] if len(x) > 2 else "مرخّصة"}]' for x in J.O.get('bound', [])),
                             sum(1 for x in J.O.get('bound', []) if len(x) > 2 and x[2] != 'مرخّصة'),
                             ' | '.join(J.O.get('unplaced', [])),
                             '؛ '.join(f'{o.name}: {o.reason}' for o in J.Omega if o.required and not o.met)])
    import io as _io
    buf = _io.StringIO(); w_ = _csv.writer(buf); w_.writerow(COLS); w_.writerows(out_rows)
    data = buf.getvalue().encode('utf-8')
    sha = _hashlib.sha256(data).hexdigest()
    if s_ in APPROVED:
        if APPROVED[s_].get('sha256') == sha:
            C['approved_same'] += 1
        else:
            # تغيّرٌ يحتاج مراجعة: قد يكون إصلاحاً، أو تراجعاً، أو تغيّراً في المصدر؛ لا خطأً تلقائياً
            C['approved_changed'] += 1
            fail['approved_changed'].append(f'سورة {s_}: تغيّرٌ يحتاج مراجعة: جملها تخالف الملف المجاز '
                                            f'(الجديد في reports/sentences/drift/surah_{s_:03d}.csv)')
            open(H + f'reports/sentences/drift/surah_{s_:03d}.csv', 'wb').write(data)
        continue                                         # لا يُكتب فوق الملف المجاز
    old_p = H + f'reports/sentences/surah_{s_:03d}.csv'
    # بيان التغيّر مقابل إصدارٍ مرجعي معلَن (SARF_SENTENCES_BASE: الإصدار المدقَّق)، لا مقابل آخر تشغيلٍ على القرص
    _old_txt = subprocess.run(['git', '-C', H, 'show', f'{SENT_BASE}:reports/sentences/surah_{s_:03d}.csv'],
                              capture_output=True, text=True).stdout if SENT_BASE else ''
    if _old_txt or os.path.exists(old_p):
        old = list(_csv.reader(_io.StringIO(_old_txt) if _old_txt else open(old_p, encoding='utf-8')))
        oh = old[0] if old else []
        idx = {k: oh.index(k) for k in ('من', 'إلى', 'النص', 'الحالة') if k in oh}
        if len(idx) == 4:
            old_by = {(r[idx['من']], r[idx['إلى']]): r for r in old[1:]}
            new_by = {(r[1], r[2]): r for r in out_rows}
            starts_old = {k[0] for k in old_by}
            for key, r in new_by.items():
                o_ = old_by.get(key)
                if o_ is None:
                    CHANGES.append([s_, key[0], key[1], 'حدٌّ جديد' if key[0] in starts_old else 'صفٌّ جديد', '', r[4], r[3][:80]])
                elif o_[idx['الحالة']] != r[4]:
                    CHANGES.append([s_, key[0], key[1], 'تغيّر الحالة', o_[idx['الحالة']], r[4],
                                    '؛ '.join(x for x in str(r[-1]).split('؛ ') if x.startswith(('علاقة غير محسومة', 'إغلاق')))[:160]])
            for key, o_ in old_by.items():
                if key not in new_by:
                    CHANGES.append([s_, key[0], key[1], 'صفٌّ زال (تغيّر حدّه)', o_[idx['الحالة']], '', o_[idx['النص']][:80]])
    open(old_p, 'wb').write(data)
# بيان التغيّر، وبيانات الإصدار التي تربط المجموعة بنسخة الكود والنص والقواعد والموارد
with open(H + 'reports/sentences/CHANGES.csv', 'w', encoding='utf-8', newline='') as fh_:
    w_ = _csv.writer(fh_)
    w_.writerow(['السورة', 'من', 'إلى', 'التغيّر', 'قبل', 'بعد', 'السبب أو النص'])
    w_.writerows(CHANGES)
C['sentence_changes'] = len(CHANGES)
from sarf.coord import GAMMA as _GAMMA
json.dump(dict(code_version=subprocess.run(['git', '-C', H, 'rev-parse', '--short', 'HEAD'], capture_output=True,
                                           text=True).stdout.strip(),
               text=dict(file='data/quran_hafs.tsv', sha256=_hashlib.sha256(open(H + 'data/quran_hafs.tsv', 'rb').read()).hexdigest()),
               reading='حفص عن عاصم (مصحف المجمّع)', coord_rules=_GAMMA, dependencies_fingerprint=DEPS,
               changes_base=SENT_BASE or 'آخر ملفات الجمل على القرص',
               protected_inventory=dict(file='sarf/protected.py', sha256=_hashlib.sha256(open(H + 'sarf/protected.py', 'rb').read()).hexdigest()),
               columns=COLS, note='سجلٌّ تجريبي للمراجعة؛ لا إجازة إلا بقرار صاحب النظرية'),
          open(H + 'reports/sentences/MANIFEST.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for jid, why in chk_list[:20]:
    fail['checker'].append(f'{jid}: ' + '؛ '.join(why[:2]))
# اختبارات الفاحص على جملٍ مغلقة حقيقية: تُزيَّف الشهادة أو يُحذف التزامٌ أو يُبدَّل طرف رابطٍ بطرفٍ من نوعٍ خطأ،
# فيُسجَّل لكل تزييف هل رُفض، وبأيّ سبب؛ ويُحفظ سجلّ أدلة أمثلةٍ من الجمل المقبولة كما هو
import copy as _copy
from sarf.checker import check_sentence, relation_problems
from sarf.algebra import Evidence as _Ev
an_all = {(s_, v_): a_ for s_, v_, a_, _, _ in items}
_phase('ملفات الجمل')
closed_J = [J for SP in LT for D in SP.A for J in D.A if J.closed]
checker_tests, closed_evidence = [], []
def _forge(J, name, fn):
    J2 = _copy.deepcopy(J)
    if fn(J2) is False:
        return
    why = check_sentence(J2, an_all)
    checker_tests.append(dict(test=name, J=J.id, rejected=bool(why), reasons=why[:2]))
def _swapped(X, i, d):
    Y = _copy.copy(X); Y.B = list(X.B); Y.B[i] = (X.B[i][0], X.B[i][1], d, X.B[i][3]); return Y
for J in closed_J[:6] + [J for J in closed_J[6:] if any('«' in c and 'ُ' in c for o in J.Omega if o.ev for c in o.ev.conditions)][:3]:
    checker_tests.append(dict(test='الجملة كما بُنيت', J=J.id, rejected=bool(check_sentence(J, an_all)),
                              reasons=check_sentence(J, an_all)[:2]))
    _forge(J, 'حذف التزامٍ يلزم بالتحليل', lambda X: (X.Omega.__setitem__(slice(None), [o for o in X.Omega
                                                     if not o.name.startswith(('معمول', 'خبر'))]) or True)
           if any(o.name.startswith(('معمول', 'خبر')) for o in X.Omega) else False)
    _forge(J, 'شهادة إكمال خالية', lambda X: setattr(X, 'ec', _Ev('', [])))
    _forge(J, 'التزامٌ لازم غير مستوفى', lambda X: setattr(X.Omega[0], 'met', False) if X.Omega else False)
    _forge(J, 'كلمةٌ بلا موضع', lambda X: X.O.__setitem__('unplaced', ['%d:%d:%d' % tuple(X.O['location'][0])]))
    def _swap(X):
        ids = [b[2] for b in X.B if isinstance(b[2], str) and b[2].startswith('Q')]
        for i, b in enumerate(X.B):
            if b[0] == 'مفعول به' or 'خبر' in b[0] or 'مجرور' in b[0]:
                other = next((d for d in ids if d != b[2] and relation_problems(_swapped(X, i, d))), None)
                if other:
                    X.B[i] = (b[0], b[1], other, b[3])
                    return True
        return False
    _forge(J, 'تبديل طرف رابطٍ بطرفٍ من نوعٍ خطأ', _swap)
    # تزوير الشاهد مع بقاء الشهادة مكتملة: حرفٌ في اللاحقة المستشهد بها، أو حركةٌ فيها
    import re as _re
    def _forge_witness(X, mode):
        for o in X.Omega:
            if not (o.met and o.ev):
                continue
            for i, c in enumerate(o.ev.conditions):
                m_ = _re.search(r'(?:لاحقة[^«]*|اللاحقة)\s*«([^»—]+)»', c)
                if not m_:
                    continue
                x = m_.group(1)
                if mode == 'حرف':
                    y = x[:-1] + ('ن' if x[-1] != 'ن' else 'ت')
                else:
                    sw = {'\u064E': '\u0650', '\u0650': '\u064F', '\u064F': '\u064E'}
                    if not any(ch in sw for ch in x):
                        continue
                    y = ''.join(sw.get(ch, ch) for ch in x)
                o.ev.conditions[i] = c.replace(f'«{x}»', f'«{y}»', 1)
                return True
        return False
    _forge(J, 'تزوير حرفٍ في الشاهد (اللاحقة المستشهد بها)', lambda X: _forge_witness(X, 'حرف'))
    _forge(J, 'تزوير حركةٍ في الشاهد', lambda X: _forge_witness(X, 'حركة'))
# الأنفال ٣٣ (مراجعة التقرير الثانية): طرف خبر «كان» يُبدَّل بضمير المفعول «هُمۡ» والحقول مكتملة
J833 = next((J for SP in LT for D in SP.A + SP.O['pending'] for J in D.A + D.O['pending']
             if [8, 33, 3] in [list(x) for x in J.O['location']]), None)
if J833 is not None:
    kb = [i for i, b in enumerate(J833.B) if b[0].startswith('خبر «كَانَ»') and '.w3.' in str(b[2])]
    checker_tests.append(dict(test='الأنفال ٣٣ كما بُنيت: أنواع الأطراف', J=J833.id,
                              rejected=bool(relation_problems(J833)), reasons=relation_problems(J833)[:2],
                              bond=[f'{b[1]} →[{b[0]}] {b[2]}' for b in J833.B if b[0].startswith('خبر «كَانَ»')]))
    if kb:
        J9 = _swapped(J833, kb[0], str(J833.B[kb[0]][2]).replace('.u1', '.u2'))
        J9.B[kb[0]] = (J9.B[kb[0]][0].replace('محذوف يتعلّق به المصدر المؤوَّل (لام الجحود)', 'جملة فعلية'), *J9.B[kb[0]][1:])
        checker_tests.append(dict(test='الأنفال ٣٣ مزيَّفة: طرف الخبر الجملي ضمير المفعول «هُمۡ»', J=J833.id,
                                  rejected=bool(relation_problems(J9)), reasons=relation_problems(J9)[:2]))
for J in closed_J[:5]:
    closed_evidence.append(dict(J=J.id, location=['%d:%d:%d' % tuple(x) for x in J.O['location']],
                                ec=J.ec.text() if J.ec else None, eb=J.eb.text() if J.eb else None,
                                obligations=[(o.name, o.met, o.ev.text() if o.ev else o.reason) for o in J.Omega],
                                bonds=[f'{b[1]} →[{b[0]}] {b[2]}' for b in J.B if b[0] != 'تجاور']))
for k, x in st.items():
    C[k] = x
# أمثلة الروابط عبر حدّ الآية
cross_samples = collections.defaultdict(list)
for c in cross:
    k = ('ثابت: ' if c['proven'] else 'محتمل: ') + c['rule'].split(':')[0]
    if len(cross_samples[k]) < 6:
        cross_samples[k].append(f"{c['src'].split('.w')[0]} → {c['dst'].split('.w')[0]} [{c['rel']}]")
# سجلات الحدود: علامة المصحف × الصنف المشتق، وموافقة أقوال العلماء
xtab = collections.defaultdict(collections.Counter)
scholar_cmp = []
brec_samples = []
SAMPLE_B = {(37, 137), (37, 138), (3, 167), (2, 282), (103, 2), (103, 3), (2, 9), (112, 1), (112, 2), (112, 3), (112, 4)}
for r in brecs:
    w = r['mark'] or ('رأس آية' if r['ayah_end'] else '—')
    xtab[w][r['category'].split(':')[0].split(' (')[0]] += 1
    for e in r['E']:
        if e['scholar'] != 'لجنة مصحف المجمّع':
            scholar_cmp.append(dict(location='%d:%d:%d' % r['location'], scholar=e['scholar'], book=e['book'],
                                    said=e['judgement'], derived=r['category'], F=r['F'], L=r['L']))
    if r['location'][:2] in SAMPLE_B:
        brec_samples.append(dict(location='%d:%d:%d' % r['location'], W=r['W'], F=r['F'], L=r['L'], Lp=r.get('Lp', []), L_checked=r['L_checked'],
                                 M=r['M'], I=r['I'], category=r['category'], E=r['E'], a=r['a'], q=r['q']))
C['mushaf_closed'] = int(MU.closed)
C['mushaf_ayahs_closed'] = sum(1 for su in MU.A for ay in su.A if ay.closed)
C['speech'] = len(LT)
C['speech_closed'] = sum(1 for x in LT if x.closed)
# المبرهنة الأولى على الطبقتين: الخلايا نفسها تبلغها الطبقتان كلتاهما، ولا تزيد ولا تنقص
all_cells = {c.id for s, v, a, units, S in items for G in units.values() for c in G.O['cells']}
cm = {c.id for c in flatten(MU)}
cl = {c.id for x in LT for c in flatten(x)}
C['T1_layers'] = int(cm == all_cells == cl)
# Location: كل كلمة في المصحف تقع في وحدة خطابية واحدة بالضبط
locs = collections.Counter(loc for x in LT for D in x.A + x.O['pending'] for loc in D.O['location'])
C['T_location'] = int(all(n == 1 for n in locs.values()) and len(locs) == sum(len(a['segments']) for s, v, a, u, S in items))
for x in LT:
    for D in x.A + x.O['pending']:
        J = (D.A + D.O['pending'])[0]
        for o in J.open_required():
            open_kind[o.name.split(' ')[0]] += 1
        ay = set(D.O['ayahs'])
        if ay & set(SAMPLE_REFS):
            units = [u for u in J.A + J.O['pending']]
            ex = {}
            for (s_, v_) in ay:
                ex.update(samples.get((s_, v_), {}).get('units', {}))
            samples.setdefault('du', []).append(dict(
                id=D.id, location=[f'{l[0]}:{l[1]}:{l[2]}' for l in D.O['location']], ayahs=[f'{a}:{b}' for a, b in D.O['ayahs']],
                closed=D.closed, sentence_closed=J.closed, nuclei=J.O.get('nuclei', []),
                boundary=(D.eb.text() if D.eb else ''), units=[ex.get(u.id, u.O['text']) for u in units],
                bonds=[f'{b[1]} →[{b[0]}] {b[2]}' for b in J.B],
                open=[o.name + (f' ({o.reason})' if o.reason else '') for o in J.open_required()]))
M = dict(timing=TIMING, checker_tests=checker_tests, closed_evidence=closed_evidence, counts=dict(C), unit_deferred=dict(unit_reason.most_common()), sentence_open=dict(open_kind.most_common()),
         unit_closed_by=dict(close_route.most_common()), failures={k: v[:40] for k, v in fail.items()},
         samples=samples.get('du', []),
         cross=dict(cross_samples),
         boundaries=dict(xtab={k: dict(v) for k, v in xtab.items()}, scholars=scholar_cmp, samples=brec_samples),
         structures=getattr(linguistic_layer, 'samples', {}))
_phase('البطارية والمقاييس')
json.dump(M, open(os.environ.get('SARF_ALG_METRICS', H + 'reports/algebra_metrics.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(M['counts'], ensure_ascii=False, indent=1))
print('unit_deferred', M['unit_deferred'])
print('sentence_open', M['sentence_open'])
print('closed_by', M['unit_closed_by'])
print({k: len(v) for k, v in fail.items()})
