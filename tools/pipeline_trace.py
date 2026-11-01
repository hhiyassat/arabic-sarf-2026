#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/pipeline_trace.py — المحلِّل مرحلةً مرحلة على مدخلٍ واحد، بالتسلسل المنطقي، وناتج كل مرحلة مطبوعاً:

   ١ المدخل ← ٢ التطبيع ← ٣ الترقيم ← ٤ التقطيع المقطعي للكلمة ← ٥ مطابقة العوامل ونفيها بالكتابة ← ٦ التقشير (الخانات)
   ← ٧ الحكم على العوامل ← ٨ الإسناد والتوافق ← ٩ الجذر والوزن ← ١٠ مقاطع الوحدات وأرقامها ← ١١ ربط العامل بمعموله
   ← ١٢ الوحدات اللفظية وإغلاقها ← ١٣ السمات الصرفية ← ١٤ الجملة ← ١٥ الوحدة الخطابية ← ١٦ الفقرة (غير منفَّذة بعد)

  ترتيب التنفيذ في الكود كما يُعرض، إلا أن مطابقة العوامل (٥) تسبق التقشير لأنه يبني خانات العوامل منها، ومقاطع
  الوحدات (١٠) تلي التقشير؛ والتقطيع المقطعي للكلمة كاملة (٤) عرضٌ مستقل قبل التقشير.

    python3 tools/pipeline_trace.py 2:282                → يطبع المراحل، ويكتب reports/trace_2_282.html
    python3 tools/pipeline_trace.py 2:282-283            → آيتان متتاليتان (الجمل والوحدات الخطابية عبرهما)
    python3 tools/pipeline_trace.py --text "نصٌّ مشكول"   → مدخلٌ حرّ (آيةٌ واحدة مفترضة)
    خيارات: -o ملف.html، --quiet (بلا طباعة)، --words 20 (حدّ الكلمات المطبوعة في الطرفية لكل مرحلة)
"""
import sys, os, copy, html, argparse, hashlib, collections
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
os.chdir(H)
from sarf.catalog import Catalog
from sarf.pipeline import Pipeline
from sarf import syllabify as cvmod
from sarf.numbering import code, syllables_code
from sarf.algebra import Trace, sentence_geo, linguistic_layer, cross_ayah_links
from sarf.features import unit_features
from sarf.analyze import analyze
from sarf.root import hfn

ap = argparse.ArgumentParser()
ap.add_argument('ref', nargs='?', help='سورة:آية أو سورة:من-إلى')
ap.add_argument('--text')
ap.add_argument('-o', '--out')
ap.add_argument('--quiet', action='store_true')
ap.add_argument('--words', type=int, default=12)
args = ap.parse_args()
if not args.ref and not args.text:
    ap.error('أعطِ مرجعاً (2:282) أو --text')

cat = Catalog(['operators_catalog.jsonl', 'operators_catalog_split_vocalized.csv'])
if args.text:
    VERSES = [(0, 1, args.text)]
    tag = 'text'
else:
    s, vv = args.ref.split(':')
    a_, b_ = (vv.split('-') + [vv])[:2]
    ROWS = {(int(x[0]), int(x[1])): x[2] for x in (l.rstrip('\n').split('\t')
                                                     for l in open('data/quran_hafs.tsv', encoding='utf-8'))}
    VERSES = [(int(s), v, ROWS[(int(s), v)]) for v in range(int(a_), int(b_) + 1)]
    tag = f"{s}_{a_}" + (f"-{b_}" if b_ != a_ else '')
OUT = args.out or f'reports/trace_{tag}.html'
h = html.escape
SECTIONS = []          # (رقم، عنوان، شرح، html، نصّ للطرفية)


def section(no, title, doc, rows, head, text_lines):
    """rows: قائمة صفوف (خلايا نصية)"""
    t = ['<div class="wrap"><table><tr>' + ''.join(f'<th>{h(x)}</th>' for x in head) + '</tr>']
    for r in rows:
        t.append('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>')
    t.append('</table></div>')
    SECTIONS.append((no, title, doc, ''.join(t), text_lines))


AR = {'accepted': 'مقبول', 'deferred': 'مؤجَّل', 'blocked': 'ممنوع', 'rejected': 'مرفوض', 'ranked': 'مرجَّح',
      'not_applicable': 'غير منطبق', 'class_deferred': 'فئة مؤجَّلة', 'madi': 'ماضٍ', 'mudari': 'مضارع', 'amr': 'أمر',
      'active': 'معلوم', 'passive': 'مجهول', 'singular': 'مفرد', 'dual': 'مثنى', 'plural': 'جمع', 'masc': 'مذكر',
      'fem': 'مؤنث', 'common': 'مشترك', 'sound_masc': 'جمع مذكر سالم', 'sound_fem': 'جمع مؤنث سالم', 'True': 'نعم', 'False': 'لا'}


def ar(x):
    return AR.get(str(x), str(x)) if x is not None else '—'


def esc(x):
    return h(ar(x))


# ---------- المراحل الصرفية لكل آية، مع لقطةٍ بعد كل مرحلة ----------
PIPE = Pipeline(cat)
per_verse = []
for s, v, text in VERSES:
    ctx_cls = __import__('sarf.pipeline', fromlist=['VerseContext']).VerseContext
    ctx = ctx_cls(text, 'auto')
    snaps, logs = {}, []
    for st in PIPE.stages:
        logs.append((st.name, st.doc, st.fn(ctx, PIPE)))
        if st.name in ('evidence', 'judge'):
            snaps[st.name] = copy.deepcopy(ctx.candidates)
    a = ctx.result()
    per_verse.append(dict(s=s, v=v, text=text, ctx=ctx, a=a, snaps=snaps, logs=logs))

# ---------- الطبقة اللغوية عبر الآيات ----------
T = Trace()
items, prev, cross, ends = [], None, [], set()
for pv in per_verse:
    S_, units = sentence_geo(pv['a'], f"Q{pv['s']}:{pv['v']}", T)
    pv['units'], pv['S'] = units, S_
    pv['F'] = unit_features(pv['a'], units)
    items.append((pv['s'], pv['v'], pv['a'], units, S_))
    cur = dict(s=pv['s'], v=pv['v'], text=pv['text'], a=pv['a'], units=units, S=S_)
    if prev is not None:
        cross += cross_ayah_links(lambda t_: analyze(cat, t_), prev, cur)
        ends.add((prev['s'], prev['v']))
    prev = cur
LT, lstats, _ = linguistic_layer(items, Trace(), 'trace', cross=cross, checked_ends=frozenset(ends))

loc = lambda pv, wi: f"{pv['s']}:{pv['v']}:{wi + 1}"
N = args.words

# ١ المدخل
rows, tl = [], []
for pv in per_verse:
    sha = hashlib.sha256(pv['text'].encode()).hexdigest()[:16]
    rows.append([f"{pv['s']}:{pv['v']}", f"<span class='ar'>{h(pv['text'])}</span>", f'{len(pv["text"].split())}', f'<code>{sha}</code>'])
    tl.append(f"{pv['s']}:{pv['v']}  {pv['text']}")
section(1, 'المدخل', 'النص كما ورد، بحركاته ورسمه (data/quran_hafs.tsv أو --text)', rows, ['الموضع', 'النص', 'الكلمات', 'البصمة'], tl)

# ٢ التطبيع
rows, tl = [], []
for pv in per_verse:
    raw, nor = pv['text'].split(), pv['a']['normalized'].split()
    for i, (r_, n_) in enumerate(zip(raw, nor)):
        rows.append([loc(pv, i), f"<span class='ar'>{h(r_)}</span>", f"<span class='ar'>{h(n_)}</span>", '' if r_ == n_ else 'تغيّر'])
        if i < N:
            tl.append(f"{loc(pv, i):<10} {r_:<20} → {n_}")
section(2, 'التطبيع', 'العثماني إلى إملائيٍّ مشكول بحركاته (sarf.normalize): علامات الوقف تُحذف، وصور الرسم تُوحَّد، ولا تُجرَّد الحركات',
        rows, ['الموضع', 'المدخل', 'بعد التطبيع', ''], tl)

# ٣ الترقيم
rows, tl = [], []
for pv in per_verse:
    for i, w in enumerate(pv['a']['normalized'].split()):
        c = code(w)
        rows.append([loc(pv, i), f"<span class='ar'>{h(w)}</span>", f'<code>{h(c)}</code>'])
        if i < N:
            tl.append(f"{loc(pv, i):<10} {w:<20} {c}")
section(3, 'الترقيم', 'كل خلية ⟨حرف، حالة⟩ رقمٌ: Code = 4(i−1) + j + 1 (sarf.numbering)؛ المشدَّد خليتان، والتنوين حالةٌ موسومة بـ«ن»',
        rows, ['الموضع', 'الكلمة', 'الأرقام'], tl)

# ٤ التقطيع المقطعي للكلمة كاملة
rows, tl = [], []
for pv in per_verse:
    res = cvmod.run(pv['a']['normalized'])
    by_w = collections.defaultdict(list)
    for rend, pat, verdict, ws in res['rows']:
        by_w[ws[0] if ws else -1].append((rend, pat, verdict))
    for i, w in enumerate(res['raw_words']):
        if i in res.get('divine_words', ()):
            sy, pats, nums = 'لفظ الجلالة (لا يُقطَّع)', '', ''
        else:
            it = by_w.get(i, [])
            sy = ' . '.join(r for r, _, _ in it)
            pats = ' '.join(p for _, p, _ in it)
            nums = ' . '.join(code(r) for r, _, _ in it)
        rows.append([loc(pv, i), f"<span class='ar'>{h(w)}</span>", f"<span class='ar'>{h(sy)}</span>", h(pats), f'<code>{h(nums)}</code>'])
        if i < N:
            tl.append(f"{loc(pv, i):<10} {w:<20} {sy:<30} {pats}")
section(4, 'التقطيع المقطعي للكلمة', 'مقاطع الكلمة كاملةً قبل التقشير (sarf.syllabify)، بأنماطها وأرقامها؛ والمقاطع التي تستعملها المراحل بعدُ مقاطعُ الوحدات (١٠)',
        rows, ['الموضع', 'الكلمة', 'المقاطع', 'النمط', 'الأرقام'], tl)

# ٥ مطابقة العوامل ونفيها بالكتابة
rows, tl = [], []
for pv in per_verse:
    for c in pv['snaps'].get('evidence', []):
        st = ar(c.get('status') or 'مرشّح')
        rows.append([loc(pv, c['word_index']), f"<span class='ar'>{h(pv['a']['normalized'].split()[c['word_index']])}</span>",
                     f"<span class='ar'>{h(c['operator'])}</span>", esc(c.get('group')), esc(st), esc((c.get('reason') or c.get('note') or '')[:90])])
        if len(tl) < N:
            tl.append(f"{loc(pv, c['word_index']):<10} {c['operator']:<10} مجموعة {c.get('group')} {st}")
section(5, 'مطابقة العوامل ونفيها بالكتابة', 'مرشّحو العوامل المائة من الفهرس (sarf.match)، ثم نفي ما تمنعه الكتابة (sarf.evidence). في الكود تسبق هذه المرحلة التقشيرَ لأنه يبني خانات العوامل منها',
        rows, ['الموضع', 'الكلمة', 'العامل', 'المجموعة', 'الحالة', 'السبب'], tl)

# ٦ التقشير
rows, tl = [], []
for pv in per_verse:
    for seg in pv['a']['segments']:
        sl = ' + '.join(f"{x['text']}<sub>{x['type']}</sub>" for x in seg['slots'])
        rows.append([loc(pv, seg['word_index']), f"<span class='ar'>{h(seg['word'])}</span>",
                     f"<span class='ar'>{' + '.join(h(x['text']) + '<sub>' + h(x['type']) + '</sub>' for x in seg['slots'])}</span>",
                     esc(len(seg['units']))])
        if seg['word_index'] < N:
            tl.append(f"{loc(pv, seg['word_index']):<10} {seg['word']:<20} " + ' + '.join(f"{x['text']}[{x['type']}]" for x in seg['slots']))
section(6, 'التقشير', 'الخانات: عامل، مبني، أل، جذع، لفظ الجلالة (sarf.segment)؛ والوحدات اللفظية من الخانات', rows,
        ['الموضع', 'الكلمة', 'الخانات', 'الوحدات'], tl)

# ٧ الحكم على العوامل
rows, tl = [], []
for pv in per_verse:
    for c in pv['snaps'].get('judge', []):
        rows.append([loc(pv, c['word_index']), f"<span class='ar'>{h(c['operator'])}</span>", esc(c.get('group')), esc(c.get('status')),
                     esc((c.get('reason') or c.get('note') or '')[:100])])
        if len(tl) < N:
            tl.append(f"{loc(pv, c['word_index']):<10} {c['operator']:<10} {ar(c.get('status'))}")
    for r in pv['a']['relations']:
        t_ = r.get('target') or {}
        rows.append([loc(pv, r['word_index']), f"<span class='ar'>{h(r['operator'])}</span> ← <span class='ar'>{h(t_.get('text', '—'))}</span>",
                     esc(r.get('group')), 'علاقة', esc(f"المتوقَّع {r.get('expected') or '—'}، المكتوب {r.get('observed') or '—'}، متّسق: {r.get('consistent')}")])
section(7, 'الحكم على العوامل وعلاقاتها', 'القبول بدليلٍ إيجابي، وإلا التأجيل أو المنع (sarf.judge)؛ والعامل ← المعمول بالمتوقَّع والمكتوب', rows,
        ['الموضع', 'العامل', 'المجموعة', 'الحكم', 'الدليل'], tl)

# ٨ الإسناد والتوافق
rows, tl = [], []
for pv in per_verse:
    for g in pv['a'].get('agreement', []):
        txt = pv['a']['segments'][g['word_index']]['slots'][g['slot']]['text']
        rows.append([loc(pv, g['word_index']), f"<span class='ar'>{h(txt)}</span>", esc(g.get('kind')), esc(g.get('voice')),
                     f"<span class='ar'>{h(' أو '.join(g.get('pronouns') or []))}</span>", esc(g.get('rule'))])
        tl.append(f"{loc(pv, g['word_index']):<10} {txt:<16} {ar(g.get('kind'))} الفاعل: {' أو '.join(g.get('pronouns') or [])}")
section(8, 'الإسناد والتوافق', 'الفعل بصيغته وضمير فاعله من لاحقته وحرف مضارعته (sarf.agreement، T18)', rows,
        ['الموضع', 'الفعل', 'الصيغة', 'البناء', 'الفاعل', 'القاعدة'], tl[:N])

# ٩ الجذر والوزن
rows, tl = [], []
for pv in per_verse:
    for m in pv['a'].get('morph', []):
        txt = pv['a']['segments'][m['word_index']]['slots'][m['slot']]['text']
        rows.append([loc(pv, m['word_index']), f"<span class='ar'>{h(txt)}</span>", esc(m['status']), esc(m.get('root')),
                     esc(m.get('form_class')), esc((m.get('reason') or '')[:110])])
        tl.append(f"{loc(pv, m['word_index']):<10} {txt:<16} {ar(m['status']):<14} {m.get('root') or '—'} {m.get('form_class') or ''}")
section(9, 'الجذر والوزن', 'مرشّحو الجذر بشهادة HFN (sarf.root، T19c): مقبول، أو مرجَّح (لا يُقبل)، أو مؤجَّل، أو غير منطبق للمحمي دستورياً',
        rows, ['الموضع', 'الجذع', 'الحالة', 'الجذر', 'الوزن', 'السبب'], tl[:N])

# ١٠ مقاطع الوحدات وأرقامها
rows, tl = [], []
for pv in per_verse:
    for seg in pv['a']['segments']:
        for u in seg['units']:
            if not u.get('syllables'):
                continue
            sy = ' . '.join(x['syl'] for x in u['syllables'])
            rows.append([loc(pv, seg['word_index']), f"<span class='ar'>{h(u['text'])}</span>", f"<span class='ar'>{h(sy)}</span>",
                         h(' '.join(x.get('cv', '') for x in u['syllables'])), f"<code>{h(syllables_code(u['syllables']))}</code>"])
            if len(tl) < N:
                tl.append(f"{loc(pv, seg['word_index']):<10} {u['text']:<16} {sy:<26} {syllables_code(u['syllables'])}")
section(10, 'مقاطع الوحدات وأرقامها', 'تقطيع ما ليس عاملاً ولا مبنياً بعد التقشير (syllabify_units)، وهو ما تستعمله المراحل التالية', rows,
        ['الموضع', 'الوحدة', 'المقاطع', 'النمط', 'الأرقام'], tl)

# ١١ ربط العامل بمعموله
rows, tl = [], []
for pv in per_verse:
    for o in pv['a'].get('operators', []):
        rows.append([loc(pv, o.get('word_index', 0)), f"<span class='ar'>{h(str(o.get('operator', '')))}</span>",
                     esc(o.get('status')), esc(str({k: o[k] for k in o if k in ('slot', 'target', 'effect', 'expected')})[:120])])
        if len(tl) < N:
            tl.append(f"{loc(pv, o.get('word_index', 0)):<10} {o.get('operator')} {ar(o.get('status'))}")
section(11, 'ربط العامل بمعموله', 'العامل بخانته وعلاقته (sarf.align)', rows, ['الموضع', 'العامل', 'الحالة', 'الربط'], tl)

# ١٢ الوحدات اللفظية وإغلاقها
rows, tl = [], []
for pv in per_verse:
    for (wi, ui), G in sorted(pv['units'].items()):
        th = G.Theta
        what = th.get('lex') or (th.get('protected') or {}).get('cls') or ''
        rp = ' '.join(x for x in [th.get('R') and f"الجذر {th['R']}", th.get('P') and f"الوزن {th['P']}"] if x)
        rows.append([loc(pv, wi), f"<span class='ar'>{h(G.O['text'])}</span>", 'مغلقة' if G.closed else 'معلَّقة',
                     esc(what), esc(rp), esc('' if G.closed else (G.O.get('deferred') or '')[:100])])
        if len(tl) < N:
            tl.append(f"{loc(pv, wi):<10} {G.O['text']:<16} {'مغلقة' if G.closed else 'معلَّقة':<8} {what} {rp}")
section(12, 'الوحدات اللفظية وإغلاقها', 'كل وحدةٍ بخلاياها: تُغلق بالمعجم أو الحماية أو بإنجاز الجذر والوزن Realize(R, P, F)، وإلا تبقى معلَّقة بسببها (sarf.algebra)',
        rows, ['الموضع', 'الوحدة', 'الحالة', 'الإغلاق', 'الجذر والوزن', 'سبب التعليق'], tl)

# ١٣ السمات الصرفية
LBL = dict(pos='الصنف', tense='الزمن', voice='البناء', subject='الفاعل', augmentation='التجرّد والزيادة', transitivity='التعدّي',
           bab='الباب', signified='المدلول', number='العدد', gender='الجنس', plural_type='نوع الجمع', fem_marker='علامة التأنيث',
           definiteness='التعريف', derivation='الاشتقاق', person='الشخص')


PER = {1: 'المتكلم', 2: 'المخاطب', 3: 'الغائب'}


def fv(v):
    if isinstance(v, dict):
        if 'person' in v:
            return f"{PER.get(v['person'])}، {ar(v.get('number'))}، {ar(v.get('gender'))}"
        if v.get('type') == 'مجرد':
            return 'مجرد'
        if v.get('type') == 'مزيد':
            return f"مزيد على {v.get('wazn')}"
        if 'verb' in v:
            return f"«{v['verb']}»"
        return '، '.join(ar(x) for k, x in v.items() if k not in ('event',))
    return ar(v)


rows, tl = [], []
for pv in per_verse:
    for (wi, ui), rec in sorted(pv['F'].items()):
        shown = [(LBL.get(f, f), r) for f, r in rec.items() if f in LBL and r['st'] in ('مثبت', 'مرشّح')]
        cells = '؛ '.join(f"{n}: {h(fv(r['v']))} <span class='st {'p' if r['st'] == 'مثبت' else 'c'}'>{r['st']}</span>" for n, r in shown)
        rows.append([loc(pv, wi), f"<span class='ar'>{h(pv['units'][(wi, ui)].O['text'])}</span>", cells or '<span class="mut">مؤجَّل كله</span>'])
        if len(tl) < N:
            tl.append(f"{loc(pv, wi):<10} {pv['units'][(wi, ui)].O['text']:<16} " +
                      '؛ '.join(f"{n}={fv(r['v'])}({r['st'][0]})" for n, r in shown if n != 'الصنف' or True)[:150])
section(13, 'السمات الصرفية', 'لكل سمةٍ حالتها: مثبت أو مرشّح (يُعرضان هنا)، والمؤجَّل وغير المنطبق في tools/features_verse.py (sarf.features)', rows,
        ['الموضع', 'الوحدة', 'السمات'], tl)

# ١٤ الجملة و١٥ الوحدة الخطابية
rows_j, rows_d, tl_j, tl_d = [], [], [], []
for SP in LT:
    for D in SP.A + SP.O.get('pending', []):
        Js = D.A + D.O.get('pending', [])
        dl = D.O.get('location') or []
        rows_d.append([esc(D.id), esc(f"{dl[0]} … {dl[-1]}" if dl else '—'), esc(len(Js)), 'مغلقة' if D.closed else 'مؤجَّلة',
                       esc(str((D.O.get('boundary') or {}).get('F', ''))[:100])])
        tl_d.append(f"{D.id}: {len(Js)} جملة، {'مغلقة' if D.closed else 'مؤجَّلة'}")
        for J in Js:
            lc = [tuple(x) for x in J.O.get('location', [])]
            frm, to = (f'{lc[0][0]}:{lc[0][1]}:{lc[0][2] + 1}', f'{lc[-1][0]}:{lc[-1][1]}:{lc[-1][2] + 1}') if lc else ('—', '—')
            words = []
            for (s_, v_, w_) in lc:
                pv = next((p for p in per_verse if p['s'] == s_ and p['v'] == v_), None)
                if pv:
                    words.append(pv['a']['segments'][w_]['word'])
            opn = [o.name for o in J.Omega if o.required and not o.met]
            rows_j.append([esc(J.id), f'{frm} – {to}', f"<span class='ar'>{h(' '.join(words))}</span>", 'مغلقة' if J.closed else 'مفتوحة',
                           esc(len(J.O.get('bound') or [])), esc(len(J.O.get('unplaced') or [])), esc('، '.join(opn[:6]) + (' …' if len(opn) > 6 else ''))])
            tl_j.append(f"{J.id:<14} {frm}–{to}  {'مغلقة' if J.closed else 'مفتوحة'}  روابط {len(J.O.get('bound') or [])}  "
                        f"بلا موضع {len(J.O.get('unplaced') or [])}  {' '.join(words)[:70]}")
section(14, 'الجملة', 'حدّ الجملة = اكتمال ∧ امتناع الامتداد (الطبقة اللغوية في sarf.algebra)؛ والآية لا تُغلق الجملة؛ ولكل جملةٍ روابطها المرخَّصة والتزاماتها المفتوحة',
        rows_j, ['الجملة', 'من – إلى', 'النص', 'الحالة', 'روابط', 'كلمات بلا موضع', 'التزامات مفتوحة'], tl_j)
section(15, 'الوحدة الخطابية', 'الجمل المتصلة بحدودها وتعلّقها؛ والإغلاق الخارجي لا يثبت إلا في آخر السورة', rows_d,
        ['الوحدة', 'المدى', 'الجمل', 'الحالة', 'الحدّ'], tl_d)
section(16, 'الفقرة', 'غير منفَّذة بعد: لا قاعدة مكتوبة لحدّ الفقرة في المشروع. والمدخل ينتهي هنا', [['—', 'غير منفَّذة']], ['', ''], ['غير منفَّذة بعد'])

# ---------- الإخراج ----------
if not args.quiet:
    for no, title, doc, _, tl in SECTIONS:
        print(f"\n═══ {no}. {title} ═══\n    {doc}")
        for line in tl[:N]:
            print('   ', line)
        if len(tl) > N:
            print(f'    … و{len(tl) - N} سطراً آخر (في ملف HTML)')
CSS = open(os.path.join(H, 'tools', 'features_verse.css'), encoding='utf-8').read() + \
    '.ar{font-family:"Amiri Quran","Noto Naskh Arabic",serif;font-size:1.1rem}sub{color:var(--mut);font-size:.7rem}' \
    'nav a{display:inline-block;margin:2px 6px}section{margin-top:1.5em}'
nav = ' '.join(f'<a href="#s{no}">{no}. {h(t)}</a>' for no, t, _, _, _ in SECTIONS)
body = ''.join(f'<section id="s{no}"><h2>{no}. {h(t)}</h2><p class="mut">{h(d)}</p>{tb}</section>' for no, t, d, tb, _ in SECTIONS)
title = 'مسار التحليل: ' + (args.ref or 'نصّ حرّ')
page = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Amiri+Quran&family=Noto+Naskh+Arabic:wght@400;700&display=swap" rel="stylesheet">
<title>{h(title)}</title><style>{CSS}</style></head><body><main><h1>{h(title)}</h1>
<p class="mut">HFN: {h(os.path.basename(hfn().path or '—'))} · {len(VERSES)} آية · المراحل بترتيبها المنطقي، وناتج كلٍّ منها</p><nav>{nav}</nav>{body}</main></body></html>"""
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(page)
print(f'\nكُتب {OUT}')
