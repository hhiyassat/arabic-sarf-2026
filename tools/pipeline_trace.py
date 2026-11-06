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
    from sarf import quran_source
    ROWS = {(s_, v_): t_ for s_, v_, t_ in quran_source.rows()}
    VERSES = [(int(s), v, ROWS[(int(s), v)]) for v in range(int(a_), int(b_) + 1)]
    tag = f"{s}_{a_}" + (f"-{b_}" if b_ != a_ else '')
if args.out:
    OUT = args.out
else:                                   # حكم المالك: التقرير صفحة المسار نفسها باسم arabic-sarf-<رقم>.html
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import report_serial
    OUT = os.path.join('reports', f'arabic-sarf-{report_serial.next_serial():03d}.html')
h = lambda x, quote=True: html.escape('—' if x is None else x if isinstance(x, str) else str(x), quote)
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
    ctx = ctx_cls(text, 'auto' if args.text else quran_source.uthmani_mode())
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
        cross += cross_ayah_links(lambda t_: analyze(cat, t_, 'auto' if args.text else quran_source.uthmani_mode()), prev, cur)
        ends.add((prev['s'], prev['v']))
    prev = cur
COND, RELS = [], []
REL_CACHE = {}
CERTS = []                     # شهادات الإغلاق الموحَّدة (الدفعة F) لكل جملة في الصفحة
LT, lstats, _ = linguistic_layer(items, Trace(), 'trace', cross=cross, checked_ends=frozenset(ends), cond_out=COND,
                                rel_out=RELS)

loc = lambda pv, wi: f"{pv['s']}:{pv['v']}:{wi + 1}"
N = args.words

# ١ المدخل
rows, tl = [], []
for pv in per_verse:
    sha = hashlib.sha256(pv['text'].encode()).hexdigest()[:16]
    rows.append([f"{pv['s']}:{pv['v']}", f"<span class='ar'>{h(pv['text'])}</span>", f'{len(pv["text"].split())}', f'<code>{sha}</code>'])
    tl.append(f"{pv['s']}:{pv['v']}  {pv['text']}")
    if not args.text:
        src_line = quran_source.source_line(pv['s'], pv['v'])
        if src_line and src_line != pv['text']:
            rows.append([f"{pv['s']}:{pv['v']} (المصدر)", f"<span class='ar'>{h(src_line)}</span>", '—',
                         '<code>' + hashlib.sha256(src_line.encode()).hexdigest()[:16] + '</code>'])
section(1, 'المدخل', ('النص المحلَّل، بحركاته ورسمه، من ' + (quran_source.tsv_path() if not args.text else '--text') +
                     ' (المصحف المعتمد: ' + (quran_source.name() if not args.text else 'نصّ حرّ') + ')' +
                     ('. وصفّ «المصدر» سطر الملف كما ورد: البسملة الملصقة بالآية الأولى مفصولةٌ عن التحليل، و«<sel>» وقفٌ غير '
                      'محدَّد النوع خارج التحليل (حكم المالك، 3 نوفمبر 2026)' if not args.text and quran_source.name() == 'quran_simple' else '')),
        rows, ['الموضع', 'النص', 'الكلمات', 'البصمة'], tl)

# ٢ التطبيع: محاذاةٌ بمجالات محارف المصدر، لا بترتيب القائمتين
from sarf.normalize import uthmani_normalize
from sarf.pipeline import UTHMANI


def _sk(t):
    """حروف الكلمة بلا حركاتها، للمحاذاة في العرض وحده (لا للتحليل): صور الهمزة والألف واحدة"""
    import re as _re, unicodedata as _ud
    t = _ud.normalize('NFC', t)                    # ا + ٔ ← أ: الهمزة على كرسيها حرفٌ واحد
    t = _re.sub('\u0640?[\u08f0-\u08ff\u064b-\u0652]*\u0654', 'ء', t)       # الهمزة فوق الكرسي أو التطويل: ء
    t = _re.sub('[\u064b-\u065f\u0670\u06d6-\u06ed\u0640\u08f0-\u08ff\u200e\u200f]', '', t)
    return t.translate(str.maketrans('ٱأإآؤئى', 'ااااءءي'))


def source_map(text, normalized):
    """→ [(رقم الكلمة المطبَّعة، [(بداية، نهاية)…]، أجزاء المصدر، مطابق؟)]: تُجمع أجزاء المصدر المتتالية (المفصولة بمسافةٍ داخل
    الكلمة: «مُّسَمّٗ ى») حتى تطابق حروفُها حروفَ الكلمة المطبَّعة؛ وما لا يطابق يُعلَن غير مقابَل ولا يُستهلك ما بعده"""
    toks, pos = [], 0
    for t in text.split():
        i = text.index(t, pos)
        toks.append((t, i, i + len(t)))
        pos = i + len(t)
    out, j = [], 0
    for wi, w in enumerate(normalized.split()):
        target, acc, ok = _sk(w), [], False
        for skip in range(0, 3):                   # فإن لم يطابق في موضعه يُبحث بعده قليلاً، ويُعلَن ما تُخطّي
            for k in range(1, 4):
                if j + skip + k > len(toks):
                    break
                if _sk(''.join(x[0] for x in toks[j + skip:j + skip + k])) == target:
                    acc, ok = toks[j + skip:j + skip + k], True
                    break
            if ok:
                j += skip + len(acc)
                break
        if not ok and j < len(toks):
            import difflib as _d
            src_sk = _sk(toks[j][0])
            if _d.SequenceMatcher(None, src_sk, target).ratio() >= 0.75:
                # التطبيع غيّر حروفاً (الواو الزائدة في «أُوْلَٰٓئِكَ»): يُقابَل الجزء ويُعلَن الفرق
                dif = ''.join(f'−{src_sk[i1:i2]}' if op in ('delete', 'replace') else '' for op, i1, i2, _, _ in
                              _d.SequenceMatcher(None, src_sk, target).get_opcodes()) + \
                    ''.join(f'+{target[j1:j2]}' if op in ('insert', 'replace') else '' for op, _, _, j1, j2 in
                            _d.SequenceMatcher(None, src_sk, target).get_opcodes())
                acc, ok = [toks[j]], 'changed:' + dif
                j += 1
        out.append((wi, [(x[1], x[2]) for x in acc], [x[0] for x in acc], ok))
    return out


rows, tl = [], []
from sarf.normalize_trace import normalize_traced
for pv in per_verse:
    nor = pv['a']['normalized'].split()
    pv['srcmap'] = source_map(pv['text'], pv['a']['normalized'])
    # العرض الإملائي (display) والعمليات المسجَّلة بقواعدها (sarf.normalize_trace)؛ والتحليل يجري على التمثيل التحليلي
    try:
        nt = normalize_traced(pv['text'], implicit_sukun=None if args.text else
                              {'on': True, 'off': False, 'auto': None}[quran_source.uthmani_mode()])
        disp = nt['display'].split()
        disp = disp if len(disp) == len(nor) else None
        ops = nt['ops_analysis']
    except Exception:                                 # التقرير لا يتوقف إن تعذّر السجل؛ ويُعلن ذلك في العمود
        disp, ops = None, []
    for wi, spans, parts, ok in pv['srcmap']:
        rules = sorted({o['rule_id'] for o in ops for a_, b_ in (o.get('source_spans') or [])
                        for x, y in spans if a_ < y and x < b_})
        src = ' + '.join(parts)
        sp = '، '.join(f'{a}–{b}' for a, b in spans)
        note = ('' if ok else 'غير مقابَل') + ('؛ جزآن في المصدر يُجمعان' if len(parts) > 1 else '') + \
            (f'؛ التطبيع غيّر الحروف ({ok[8:]})' if isinstance(ok, str) else '')
        rows.append([loc(pv, wi), f"<span class='ar'>{h(src)}</span>", f'<code>{sp}</code>',
                     f"<span class='ar'>{h(disp[wi]) if disp else '—'}</span>", f"<span class='ar'>{h(nor[wi])}</span>",
                     f"<code>{h(' '.join(rules)) or '—'}</code>", esc(note.strip('؛ '))])
        if wi < N or len(parts) > 1 or not ok:
            tl.append(f"{loc(pv, wi):<10} [{sp}] {src:<22} → {nor[wi]}  {note}")
section(2, 'التطبيع', 'تمثيلان من المصدر نفسه (sarf.normalize_trace، العقد N3.1): العرض الإملائي (display) والتمثيل التحليلي (analysis) '
        'الذي تجري عليه المراحل كلها؛ وعمود القواعد معرّفات العمليات المسجَّلة على محارف الكلمة في التمثيل التحليلي، وسجلّها الكامل '
        'بمجالاته في حزمة التطبيع. المحاذاة بمجالات محارف المصدر: كل كلمةٍ مطبَّعة تُربط بالجزء أو الأجزاء التي أنتجتها؛ فإن فُصلت '
        'الكلمة في المصدر بمسافة (مُّسَمّٗ ى، شَيۡـٔٗ اۚ) جُمع جزآها، ولا تُقابل القائمتان بترتيبهما',
        rows, ['الموضع', 'المصدر', 'مجال المحارف', 'العرض (display)', 'التحليلي (analysis)', 'القواعد', 'ملاحظة'], tl)

# ٣ الترقيم: خلايا المكتوب
rows, tl = [], []
for pv in per_verse:
    pv['codes'] = {}
    for i, w in enumerate(pv['a']['normalized'].split()):
        c = code(w)
        pv['codes'][i] = c.split()
        rows.append([loc(pv, i), f"<span class='ar'>{h(w)}</span>", f'<code>{h(c)}</code>'])
        if i < N:
            tl.append(f"{loc(pv, i):<10} {w:<20} {c}")
section(3, 'الترقيم: خلايا المكتوب', 'كل خلية ⟨حرف، حالة⟩ من الكلمة المكتوبة رقمٌ: Code = 4(i−1) + j + 1 (sarf.numbering)؛ المشدَّد خليتان، '
        'والتنوين حالةٌ موسومة بـ«ن». هذه خلايا المصدر، لا خلايا التحقيق', rows, ['الموضع', 'الكلمة', 'الأرقام'], tl)

# ٤ التقطيع المقطعي للكلمة: خلايا التحقيق في الدرج، وخريطة الفرق
import difflib as _dl


def cell_diff(src, real):
    """→ قائمة الفروق بين خلايا المكتوب وخلايا التحقيق: (+رقم) مضاف، (−رقم) محذوف"""
    out = []
    for op, i1, i2, j1, j2 in _dl.SequenceMatcher(None, src, real, autojunk=False).get_opcodes():
        if op in ('delete', 'replace'):
            out += [f'−{x}' for x in src[i1:i2]]
        if op in ('insert', 'replace'):
            out += [f'+{x}' for x in real[j1:j2]]
    return out


rows, tl = [], []
for pv in per_verse:
    res = cvmod.run(pv['a']['normalized'])
    by_w = collections.defaultdict(list)
    for rend, pat, verdict, ws in res['rows']:
        by_w[ws[0] if ws else -1].append((rend, pat, verdict))
    for i, w in enumerate(res['raw_words']):
        if i in res.get('divine_words', ()):
            sy, pats, nums, dif = 'لفظ الجلالة (لا يُقطَّع)', '', '', ''
        else:
            it = by_w.get(i, [])
            sy = ' . '.join(r for r, _, _ in it)
            pats = ' '.join(p for _, p, _ in it)
            nums = ' . '.join(code(r) for r, _, _ in it)
            dif = ' '.join(cell_diff(pv['codes'].get(i, []), ' '.join(code(r) for r, _, _ in it).split()))
        rows.append([loc(pv, i), f"<span class='ar'>{h(w)}</span>", f"<span class='ar'>{h(sy)}</span>", h(pats), f'<code>{h(nums)}</code>',
                     f'<code>{h(dif) or "—"}</code>'])
        if i < N:
            tl.append(f"{loc(pv, i):<10} {w:<20} {sy:<30} {pats}  فرق: {dif or '—'}")
section(4, 'التقطيع المقطعي: خلايا التحقيق في الدرج', 'مقاطع النص متصلاً (sarf.syllabify) بأنماطها وأرقامها، وعمود «الفرق» يقابل خلايا التحقيق بخلايا المكتوب (٣): '
        '«−» محذوفٌ في التحقيق، و«+» مضاف. وقواعد التحقيق المطبَّقة هنا: همزة الوصل تسقط في الدرج (فَكْ تُ بُو هُ)، ولام أل الشمسية '
        'تُدغم فيما بعدها، والمشدَّد خليتان، وألف تنوين النصب وألف الوصل لا تُنطقان، وتُقدَّم همزة الابتداء لأل في أول الكلام. '
        'وهذا تحقيقٌ صوتيٌّ معلَن، لا تبديلٌ للمكتوب: التحليل الصرفي يجري على خلايا المكتوب، والفرق يُحفظ هنا ولا يُحسب تساوياً',
        rows, ['الموضع', 'الكلمة', 'المقاطع', 'النمط', 'أرقام التحقيق', 'الفرق عن المكتوب'], tl)

# ٥ مطابقة العوامل ونفيها بالكتابة
rows, tl = [], []
for pv in per_verse:
    for c in pv['snaps'].get('evidence', []):
        st = ar(c.get('status') or 'مرشّح')
        rows.append([loc(pv, c['word_index']), f"<span class='ar'>{h(c['word'])}</span>", f"<span class='ar'>{h(c['operator'])}</span>",
                     esc(c.get('group')), esc(st), esc(c.get('note') or '—'), esc(c.get('reject_reason') or '—'),
                     esc('، '.join(c.get('checked') or []) or '—')])
        if len(tl) < N:
            tl.append(f"{loc(pv, c['word_index']):<10} {c['operator']:<8} مجموعة {c.get('group')} {st}  {c.get('reject_reason') or ''}")
section(5, 'مطابقة العوامل ونفيها بالكتابة', 'مرشّحو العوامل المائة من الفهرس (sarf.match)، ثم النفي بمانعٍ مكتوب (sarf.evidence). عمود «احتمال» '
        'تنبيهٌ لا دليل؛ والنفي بعمود «المانع»، والموانع المفحوصة بعده. في الكود تسبق هذه المرحلة التقشيرَ لأنه يبني خانات العوامل منها',
        rows, ['الموضع', 'الكلمة', 'العامل', 'المجموعة', 'الحالة', 'احتمال (لا دليل)', 'المانع', 'الموانع المفحوصة'], tl)

# ٦ التقشير
rows, tl = [], []
for pv in per_verse:
    for seg in pv['a']['segments']:
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
        j = c.get('judgement') or {}
        proof = '؛ '.join(j.get('proof') or []) or ('المانع: ' + c['reject_reason'] if c.get('reject_reason') else '—')
        why = '؛ '.join(j.get('deferred_because') or []) or '—'
        lic = c.get('licence') or {}
        lic_s = f"البقية: {lic.get('rest_strength', '—')}" if lic else '—'
        rows.append([loc(pv, c['word_index']), f"<span class='ar'>{h(c['operator'])}</span>", esc(c.get('group')), esc(c.get('status')),
                     esc(proof), esc(why), esc(lic_s)])
        if len(tl) < N:
            tl.append(f"{loc(pv, c['word_index']):<10} {c['operator']:<8} {ar(c.get('status')):<8} {proof[:80]}")
section(7, 'الحكم على العوامل', 'القبول بدليلٍ إيجابي: السبب والشرط والموانع المفحوصة (judgement.proof)؛ والتأجيل بسببه؛ والمنع بمانعه؛ '
        'ورخصة بقية الكلمة بعد فصل العامل (licence) قوةً عددية', rows,
        ['الموضع', 'العامل', 'المجموعة', 'الحكم', 'دليل القبول أو المنع', 'سبب التأجيل', 'رخصة البقية'], tl)

# ٨ الإسناد: سمات الصيغة، لا تعيين الفاعل
rows, tl = [], []
for pv in per_verse:
    for g in pv['a'].get('agreement', []):
        txt = pv['a']['segments'][g['word_index']]['slots'][g['slot']]['text']
        ui = pv['a']['segments'][g['word_index']]['slots'][g['slot']].get('unit', 0)
        fr = pv['F'].get((g['word_index'], ui), {})
        tst = fr.get('tense', {}).get('st', '—')
        sst = fr.get('subject', {}).get('st', '—')
        vst = fr.get('voice', {}).get('st', '—')
        rows.append([loc(pv, g['word_index']), f"<span class='ar'>{h(txt)}</span>", f"{esc(g.get('kind'))} <span class='mut'>({tst})</span>",
                     f"{esc(g.get('voice'))} <span class='mut'>({vst})</span>",
                     f"<span class='ar'>{h(' أو '.join(g.get('pronouns') or []))}</span> <span class='mut'>({sst})</span>",
                     esc(g.get('rule')), esc(g.get('verb_by_lexicon') or g.get('verb_by_operator') or '—')])
        tl.append(f"{loc(pv, g['word_index']):<10} {txt:<16} {ar(g.get('kind'))}({tst}) ضمير الصيغة: {' أو '.join(g.get('pronouns') or [])}({sst})")
section(8, 'الإسناد: سمات الصيغة', 'الصيغة وضمير الإسناد الذي تدلّ عليه لاحقتها وحرف مضارعتها (sarf.agreement، T18). «ضمير الصيغة» سمةٌ في الفعل، '
        'لا تعيينٌ للفاعل في الجملة: «وَلۡيَكۡتُبۡ بَيۡنَكُمۡ كَاتِبٌ» صيغتها للغائب، وفاعلها الظاهر «كَاتِبٌ» يُعيَّن في طبقة الجملة. '
        'وبين القوسين حالة السمة في المرحلة ١٣ (مثبت أو مرشّح)، فما كان مرشّحاً هنا لا يُبنى عليه', rows,
        ['الموضع', 'الفعل', 'الصيغة', 'البناء', 'ضمير الصيغة', 'القاعدة', 'دليل الفعلية إن لم تكفِ الكتابة'], tl[:N])

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
rows, tl, seen_ids = [], [], {}
for pv in per_verse:
    segs_ = pv['a']['segments']
    for o in pv['a'].get('operators', []):
        r = o.get('relation') or {}
        t_ = r.get('target') or {}
        tgt = f"{t_.get('text', '—')} ({pv['s']}:{pv['v']}:{t_['word_index'] + 1}، خانة {t_.get('slot')})" if t_ else '—'
        j = o.get('judgement') or {}
        ev = '؛ '.join(j.get('proof') or []) or (o.get('reject_reason') or '—')
        alts = len(o.get('meanings') or [])
        # الموضع النصّي، وفرضية العلاقة (الأداة ووظيفتها ومعمولها)، وتحليل المعمول المستعمَل: ثلاثة معرّفات لا واحد
        site = f"S{pv['s']}:{pv['v']}:{o.get('word_index', 0) + 1}/{(o.get('slot') or {}).get('index', '—')}"
        rid = f"H{site[1:]}·{o.get('operator', '')}·مج{o.get('group', '—')}→{t_.get('word_index', -1) + 1 if t_ else '—'}" \
              f"{'/' + str(t_.get('slot')) if t_ and t_.get('slot') is not None else ''}"
        aid = (f"A{pv['s']}:{pv['v']}:{t_['word_index'] + 1}.{t_.get('slot', 0)}"
               f"[{r.get('observed') or 'بلا علامة'}{'، ' + r['note'] if r.get('note') else ''}]") if t_ else '—'
        seen_ids[rid] = seen_ids.get(rid, 0) + 1
        rows.append([loc(pv, o.get('word_index', 0)), f"<span class='ar'>{h(str(o.get('operator', '')))}</span>", esc(o.get('status')),
                     f'<code>{h(site)}</code><br><code>{h(rid)}</code><br><code>{h(aid)}</code>',
                     f"<span class='ar'>{h(tgt)}</span>", esc(r.get('role') or '—'),
                     esc(f"المتوقَّع {r.get('expected') or '—'}، المكتوب {r.get('observed') or '—'}، متّسق: {ar(r.get('consistent'))}" if r else '—'),
                     esc(ev), esc(f'{alts} معنىً محتمل' if alts else '—')])
        if len(tl) < N:
            tl.append(f"{loc(pv, o.get('word_index', 0)):<10} {o.get('operator')} {ar(o.get('status')):<8} ← {tgt}  {r.get('role') or ''}")
dup_ids = {k: v for k, v in seen_ids.items() if v > 1}
if dup_ids:                                   # معرّف الفرضية فريد بحكم البناء؛ فإن تكرّر فهو خللٌ يُعلَن لا يُخفى
    print(f'تنبيه: {len(dup_ids)} معرّف فرضيةٍ مكرَّر في المرحلة ١١: {list(dup_ids)[:5]}', file=sys.stderr)
section(11, 'ربط العامل بمعموله', 'لكل عاملٍ ثلاثة معرّفات: S الموضع النصّي، وH فرضية العلاقة (الأداة ومجموعتها ومعمولها)، '
        'وA تحليل المعمول المستعمَل وعلامته. ' + (f'مكرَّر: {len(dup_ids)}. ' if dup_ids else 'لا معرّف فرضيةٍ مكرَّر. ') + 'لكل عاملٍ معرّف علاقته، ومعموله بموضعه وخانته، ودوره، والمتوقَّع والمكتوب، ودليل الحكم، وعدد معانيه المحتملة '
        '(البدائل لا تُحسم هنا). والنطاق: معمولٌ واحد مباشر في الآية؛ وما يتجاوزه في طبقة الجملة (١٤)', rows,
        ['الموضع', 'العامل', 'الحكم', 'المعرّفات (S/H/A)', 'المعمول', 'الدور', 'العلامة', 'الدليل', 'البدائل'], tl)

# ١٢ الوحدات اللفظية وإغلاقها
rows, tl = [], []
for pv in per_verse:
    for (wi, ui), G in sorted(pv['units'].items()):
        th = G.Theta
        what = th.get('lex') or (th.get('protected') or {}).get('cls') or ''
        rp = ' '.join(x for x in [th.get('R') and f"الجذر {th['R']}", th.get('P') and f"الوزن {th['P']}"] if x)
        if str(th.get('P') or '').startswith('بناء سيبويه') and 'ة' in G.O['text'] and 'ة' not in str(th.get('P')):
            rp += ' (وزن الجذع؛ وتاء التأنيث لاحقةٌ خارجه)'
        # خريطة المطابقة α: كل خليةٍ ↦ موقعها من الجذر أو الزوائد، وعمليات التحويل (sarf.algebra.align_alpha)
        cl = G.O.get('cells') or []
        al = th.get('alpha')
        amap = ' '.join(f"{c.C}:{x or '—'}" for c, x in zip(cl, al)) if al and len(al) == len(cl) else ''
        if th.get('ops'):
            amap += ' | ' + '، '.join(th['ops'])
        rows.append([loc(pv, wi), f"<span class='ar'>{h(G.O['text'])}</span>", 'مغلقة' if G.closed else 'معلَّقة',
                     esc(what), esc(rp), f"<span class='ar'>{h(amap)}</span>" if amap else '—',
                     esc('' if G.closed else (G.O.get('deferred') or '')[:100])])
        if len(tl) < N:
            tl.append(f"{loc(pv, wi):<10} {G.O['text']:<16} {'مغلقة' if G.closed else 'معلَّقة':<8} {what} {rp}")
section(12, 'الوحدات اللفظية وإغلاقها', 'كل وحدةٍ بخلاياها: تُغلق بالمعجم أو الحماية أو بإنجاز الجذر والوزن Realize(R, P, F)، وإلا تبقى معلَّقة بسببها (sarf.algebra)',
        rows, ['الموضع', 'الوحدة', 'الحالة', 'الإغلاق', 'الجذر والوزن', 'خريطة α والتحويل', 'سبب التعليق'], tl)

# ١٣ السمات الصرفية
LBL = dict(pos='الصنف', tense='الزمن', voice='البناء', subject='ضمير الصيغة', augmentation='التجرّد والزيادة', transitivity='التعدّي',
           bab='الباب', signified='المدلول (مدخل HFN)', number='العدد', gender='الجنس', plural_type='نوع الجمع', fem_marker='علامة التأنيث',
           definiteness='التعريف', derivation='الاشتقاق', pattern='البناء الصرفي', person='الشخص')
# السمات المضافة من سجل التغطية (sarf.features_ext)
EXT_LBL = dict(root_class='صنف الجذر', root_arity='عدد الأصول', conjugability='التصرّف', transformations='التحويل (α)',
               definiteness_kind='نوع المعرفة', final_form='صورة الآخر', case_marking='العلامة', diptote='الصرف',
               derivation_candidates='الاشتقاق المحتمل', lemma='اللمّة (HFN)', elative='التفضيل', enclitic_case='محلّ الضمير',
               construction='التركيب', stem_root_candidates='جذر الجذع (مرشّح)', nisba='النسب', diminutive='التصغير',
               polarity='الإثبات والنفي', subject_kind='نوع الإسناد', vocative='النداء', idafa='الإضافة')
LBL.update(EXT_LBL)


PER = {1: 'المتكلم', 2: 'المخاطب', 3: 'الغائب'}


def fv(v):
    if isinstance(v, list):
        return '، '.join(ar(x) for x in v) if v else 'لا تحويل'
    if isinstance(v, dict) and 'kinds' in v:
        return f"{v.get('type')}: {'، '.join(v['kinds'])}"
    if isinstance(v, dict):
        if 'person' in v:
            return f"{PER.get(v['person'])}، {ar(v.get('number'))}، {ar(v.get('gender'))}"
        if v.get('type') == 'مجرد':
            return 'مجرد'
        if v.get('type') == 'مزيد':
            return f"مزيد على {v.get('wazn')}"
        if 'verb' in v:
            return f"«{v['verb']}» [{v.get('event')}]"
        return '، '.join(ar(x) for k, x in v.items() if k not in ('event',))
    return ar(v)


rows, tl = [], []
for pv in per_verse:
    for (wi, ui), rec in sorted(pv['F'].items()):
        shown = [(LBL.get(f, f), r) for f, r in rec.items() if f in LBL and r['st'] in ('مثبت', 'مرشّح')]
        cells = '؛ '.join(f"{n}: {h(fv(r['v']))} <span class='st {'p' if r['st'] == 'مثبت' else 'c'}'>{r['st']}</span>" +
                         (f" <span class='mut'>[البدائل: {h('، '.join(fv(x) for x in r['alt']))}]</span>"
                          if r['st'] == 'مرشّح' and r.get('alt') else '') for n, r in shown)
        rows.append([loc(pv, wi), f"<span class='ar'>{h(pv['units'][(wi, ui)].O['text'])}</span>", cells or '<span class="mut">مؤجَّل كله</span>'])
        if len(tl) < N:
            tl.append(f"{loc(pv, wi):<10} {pv['units'][(wi, ui)].O['text']:<16} " +
                      '؛ '.join(f"{n}={fv(r['v'])}({r['st'][0]})" for n, r in shown if n != 'الصنف' or True)[:150])
section(13, 'السمات الصرفية', 'لكل سمةٍ حالتها: مثبت أو مرشّح (يُعرضان هنا)، والمؤجَّل وغير المنطبق في tools/features_verse.py (sarf.features). '
        '«ضمير الصيغة» سمة الفعل لا فاعل الجملة؛ و«البناء الصرفي» قالبٌ من أبنية سيبويه لا نوع اشتقاق؛ و«المدلول» مدخلٌ معجميٌّ بمعرّفه في HFN '
        'تطابقه الكلمة، لا اختيارٌ لمعناه السياقي', rows,
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
        d_idx, c0 = len(rows_d) - 1, len(CERTS)
        for J in Js:
            lc = [tuple(x) for x in J.O.get('location', [])]
            frm, to = (f'{lc[0][0]}:{lc[0][1]}:{lc[0][2] + 1}', f'{lc[-1][0]}:{lc[-1][1]}:{lc[-1][2] + 1}') if lc else ('—', '—')
            words = []
            for (s_, v_, w_) in lc:
                pv = next((p for p in per_verse if p['s'] == s_ and p['v'] == v_), None)
                if pv:
                    words.append(pv['a']['segments'][w_]['word'])
            opn = [o.name for o in J.Omega if o.required and not o.met]
            bnd = J.O.get('boundary') or {}
            # شهادة الإغلاق الموحَّدة (sarf.algebra.closure_certificate، الدفعة F): التزامات الطبقة القديمة بما استوفاها في 14أ،
            # والتزامات 14أ المفتوحة داخل مدى الجملة، والحكم الموحَّد
            recs_ = []
            for (s_, v_) in sorted({(x[0], x[1]) for x in lc}):
                pv_ = next((p for p in per_verse if p['s'] == s_ and p['v'] == v_), None)
                if pv_ is None:
                    continue
                from sarf.relations import verse_relations
                if (s_, v_) not in REL_CACHE:
                    REL_CACHE[(s_, v_)] = verse_relations(pv_['a'], pv_['units'], pv_['F'], f'{s_}:{v_}', legacy_cond=COND, legacy_rel=RELS)
                recs_ += REL_CACHE[(s_, v_)]['records']
            from sarf.algebra import closure_certificate
            cert_ = closure_certificate(J, recs_)
            CERTS.append(cert_)
            un_ = [f"{x['rule']} {x['status']} ({x['kind']})" for x in cert_['residuals']]
            # الشهادة كاملةً بلا بتر (مراجعة 038): الملخّص من رموز حالات الالتزامات نفسها، والسجلّ الكامل في عنصرٍ قابلٍ للطيّ
            def ob_line(o_):
                src_ = '، '.join(((x['relation'] or x.get('id') or x.get('evidence') or '') + (f" ({x['status']})" if x.get('status') else '') +
                                  (f" ← {x['unit']}" if x.get('unit') else '')) for x in (o_['satisfied_by'] or []))
                return (f"{o_['obligation_id']} {o_['name']} [{o_['requirement_kind']}، {'لازم' if o_['required'] else 'جائز'}، "
                        f"{o_['status']}: {o_['status_ar']}]" + (f" ← {src_}" if src_ else '') +
                        (f"؛ الدليل: {o_['discharge_evidence_id']}" if o_.get('discharge_evidence_id') else '') +
                        (f"؛ الباقي: {o_['residual_reason']}" if o_['residual_reason'] else '') +
                        (f"؛ القياس: {o_['measure']}" if o_.get('measure') else ''))
            bd_ = cert_['boundary']
            bline_ = (f"الحدّ اللغوي: {bd_['linguistic_status']}" +
                      (f"؛ القاعدة: {bd_['rule_id']}؛ معرّف الدليل: {bd_['evidence_id']}؛ الدليل: {bd_['linguistic_evidence']}" if bd_.get('rule_id') else '') +
                      (f"؛ الثبات في البدائل: {bd_['stable_across_alternatives']}" if bd_.get('stable_across_alternatives') else '') +
                      f"؛ الاستقلال في المستوى الأعلى: {bd_['independence']}" +
                      (f"؛ حدّ المصدر: {bd_['source']}" if bd_.get('source') else ''))
            det_ = ('<details><summary>السجلّ الكامل للشهادة</summary>' +
                    '<br>'.join(h(ob_line(o_)) for o_ in cert_['obligations']) +
                    ('<br>' + '<br>'.join(h(f"باقٍ في 14أ [{x['kind']}، {x['status']}] {x['relation']}: {x['why']}" +
                                            (f"؛ خارج المدى: {'، '.join(x['outside'])}" if x.get('outside') else '')) for x in cert_['residuals'])
                     if cert_['residuals'] else '') +
                    ('<br>' + '<br>'.join(h(f"وجهٌ ممنوع {x['rule']} ({x['relation']}): {x['barrier']}") for x in cert_['rejected_faces'])
                     if cert_['rejected_faces'] else '') + '</details>')
            scope_ = (f"الشهادة الموحَّدة: {cert_['verdict_ar']}؛ " +
                      (f'وفي 14أ داخل مداها {len(un_)} باقياً مصنَّفاً (' +
                       '، '.join(f'{k_}×{c_}' for k_, c_ in sorted(__import__('collections').Counter(un_).items())) + ')'
                       if un_ else 'ولا باقٍ في 14أ داخل مداها') + '؛ ' + bline_)
            bonds = '<br>'.join(h(f'{b[0]}: {b[1]} → {b[2]}') for b in (J.O.get('bound') or [])) or '—'
            pl_ob = next((o_ for o_ in cert_['obligations'] if o_['requirement_kind'] == 'PLACEMENT'), None)
            pl_ = (f"الشهادة: {pl_ob['status_ar']}" + (f" — {pl_ob['residual_reason']}" if pl_ob['residual_reason'] else '') +
                   f"<br><sub>{h(pl_ob.get('measure') or '')}</sub>") if pl_ob else 'الشهادة: لا التزام موضع'
            from sarf.algebra import certificate_unmet
            nm_ = certificate_unmet(cert_)
            un_req_ = 'الشهادة: ' + ('<br>'.join(h(f"{o_['name']} [{'لازم' if o_['required'] else 'جائز'}، {o_['status']}: {o_['status_ar']}]")
                                                  for o_ in nm_) or 'كل الالتزامات مستوفاة أو جائزةٌ غائبة')
            rows_j.append([esc(J.id), f'{frm} – {to}', f"<span class='ar'>{h(' '.join(words))}</span>",
                           ('مغلقة (الطبقة القديمة)' if J.closed else 'مفتوحة') + f"<br><b>{h(cert_['verdict_ar'])}</b><br><sub>{h(scope_)}</sub>" + det_,
                           esc(bnd.get('F') or '—') + '<br><sub>الطبقة القديمة</sub>', bonds,
                           f"{h(pl_.split('<br><sub>')[0])}" + ('<br><sub>' + pl_.split('<br><sub>')[1] if '<br><sub>' in pl_ else '') +
                           f"<br><sub>الطبقة القديمة: {len(J.O.get('unplaced') or [])}</sub>",
                           f"{un_req_}<br><sub>الطبقة القديمة: {h('، '.join(opn) or '—')}</sub>"])
            # ١٥ تحمل قيد جملها: الوحدة الخطابية لا تُعرض «مغلقة» وفي جملها حكمٌ موحَّد غير مغلق؛ ويُعرض أشدّ أحكامها
            from sarf.algebra import CLOSURE_AR
            order_ = list(CLOSURE_AR)
            vs_ = [c['verdict'] for c in CERTS[c0:]]
            worst_ = max(vs_, key=lambda x: (x not in ('CLOSED_IN_FACE', 'CLOSED_WITH_SHARED_STRUCTURE'), order_.index(x)))
            dv_ = ('مغلقة (الطبقة القديمة)' if D.closed else 'مؤجَّلة (الطبقة القديمة)') + \
                f"<br><b>الحكم الموحَّد لجملها: {h(CLOSURE_AR[worst_])}</b><br><sub>{h('، '.join(f'{k_}×{c_}' for k_, c_ in sorted(__import__('collections').Counter(vs_).items())))}</sub>"
            rows_d[d_idx][3] = dv_
            tl_d[d_idx] = f"{D.id}: {len(Js)} جملة، {'مغلقة' if D.closed else 'مؤجَّلة'} [الموحَّد: {worst_}]"
            tl_j.append(f"{J.id:<14} {frm}–{to}  القديم: {'مغلقة' if J.closed else 'مفتوحة'} | الموحَّد: [{cert_['verdict']}] ({'باقٍ في 14أ: ' + str(len(un_)) if un_ else 'لا باقٍ في 14أ'})  روابط {len(J.O.get('bound') or [])}  "
                        f"موضع: {pl_ob['status'] if pl_ob else '—'}  {' '.join(words)[:70]}")
section(14, 'الجملة', '(الجملة تُبنى في الطبقة القديمة قبل علاقات 14أ؛ ثم تمرّ شهادة الإغلاق الموحَّدة v2 (sarf.algebra.closure_certificate) بعدهما: لكل التزامٍ سجلٌّ بمعرّفه ونوعه ووجهه وحالته، ولا يُستوفى إلا بعلاقةٍ من نوعه للوحدة والوجه نفسيهما (فلا يُختزل «فاعل أو نائب فاعل» في «فاعل»، ولا يُلغي جدول الإسناد القديم تأجيلاً صريحاً في 14أ)؛ وما في 14أ داخل المدى مؤجَّلاً ليس التزاماً لازماً تلقائياً، بل يُصنَّف اختياراً أو حدّاً أو نقص تغطية؛ والحكم واحدٌ من سبعة: مغلقة في وجهها، مغلقة بالبنية المشتركة، التزامٌ لازمٌ غير مستوفى، حدٌّ مؤجَّل، اختيارٌ مؤجَّل، نقص تغطية، والوجه الممنوع يُعرض بمانعه) جهتان مختلفتان: «التمام» (F) أن في المدى نواةً ولا التزامَ نحويٍّ لازمٍ مفتوحاً (معمول، خبر، فاعل)؛ و«الإغلاق» أن تُستوفى '
        'الالتزامات كلها: إغلاق كل وحدة، وموضع كل كلمة، وحسم كل علاقة. فالجملة قد تكون تامّةً في التحليل مفتوحةً غير مغلقة. والآية لا تُغلق الجملة. '
        'والروابط معروضةٌ بأطرافها، والالتزامات المفتوحة كاملةً بلا اختصار',
        rows_j, ['الجملة', 'من – إلى', 'النص', 'الإغلاق (القديم ثم الموحَّد)', 'التمام (F) — الطبقة القديمة', 'الروابط — الطبقة القديمة',
                 'موضع الكلمات (تغطية الأدوار المحلية) — الشهادة (والقديم تحته)',
                 'غير مستوفى (لازمٌ وجائز) — الشهادة (والقديم تحته)'], tl_j)
# ١٤أ العلاقات المحلية (عقد النواة الاسمية والتعلّق، sarf.relations) بأدلتها؛ و١٤ب محاور الصنف المستقلة
from sarf.relations import verse_relations, check_records
rows_r, tl_r, rows_x, tl_x = [], [], [], []
for pv in per_verse:
    ref = f"{pv['s']}:{pv['v']}"
    rel = verse_relations(pv['a'], pv['units'], pv['F'], ref, legacy_cond=COND, legacy_rel=RELS)
    errs = check_records(rel['records'], rel['tokens'], rel.get('parts'))
    from sarf.relations import check_cross
    errs += check_cross(rel['records'], rel['axes'])
    for r in rel['records']:
        alts = '<br>'.join(h(a if isinstance(a, str) else f"{a['host_kind']}: «{a['host_text']}» ({a['host_position']}) — {a['status']}")
                           for a in r['alternatives']) or '—'
        fr = r.get('frame')
        if fr:
            sb = fr.get('subject') or {}
            alts = (f"الهوية: {h(fr['identity'])} (الجذر {h(fr.get('root') or '—')}، الوزن {h(fr.get('pattern') or '—')})"
                    f"<br>الزمن: {h(fr['tense'][0])} ({h(fr['tense'][1])})؛ البناء: {h(fr['voice'][0])} ({h(fr['voice'][1])})"
                    f"<br>الاستعمال: {h(fr['usage'])}؛ متطلَّب الإسناد: {h(fr['subject_requirement'])}"
                    f"<br>التعدّي: {h(fr['transitivity'][0] or '—')} ({h(fr['transitivity'][1] or '—')})"
                    f"<br>الإسناد: {h(sb.get('role') or '—')} — {h(sb.get('kind') or '—')} [{h(sb.get('status') or '—')}]: {h(sb.get('why') or '')}"
                    f"<br>المفاعيل: {h('، '.join(fr.get('objects') or []) or '—')}"
                    + ''.join(f"<br>مرشّح {h(c['id'])}: {h(c.get('tense'))}، {h(c.get('voice'))}، {h(c.get('subject_role'))} "
                              f"[{h(c['status'])}] {h(c.get('realization') or '')} {h(c.get('reason') or '')}" for c in fr.get('candidates') or [])
                    + ''.join(f"<br>التزامٌ مفتوح: {h(x)}" for x in fr.get('open') or [])
                    + (f"<br>كاشف المكمّل: {h(fr['object_requirement']['status'])} ({h(fr['object_requirement']['kind'])}) — {h(fr['object_requirement']['note'])}"
                       if fr.get('object_requirement') else '')
                    + (f"<br>سمات المرحلة ٨: {h(fr['stage8'].get('tense'))}، {h(fr['stage8'].get('voice'))} — {h(fr['stage8'].get('note'))}"
                       if fr.get('stage8') else ''))
        if r.get('parts'):
            alts += ''.join(f"<br>جزء {h(p_['part'])}: «<span class='ar'>{h(p_['text'])}</span>» <code>{h(p_['part_id'])}</code> "
                            f"المحارف {h('[' + '، '.join(map(str, p_['span'])) + ')' if p_.get('span') else '—')}، المقاطع {h('، '.join(map(str, p_.get('syllables') or [])) or '—')}" + (f" — {h(p_['note'])}" if p_.get('note') else '')
                            for p_ in r['parts'])
        if r.get('parts_status'):
            alts += '<br>' + h('، '.join(f'{k}={v}' for k, v in r['parts_status'].items()))
        if r.get('resumptive'):
            alts += f"<br>العائد: {h(r['resumptive'].get('status'))} — {h(r['resumptive'].get('note'))}"
            alts += ''.join(f"<br>مرشّح العائد {h(x.get('id') or '')}: «{h(x.get('candidate'))}» في الوجه {h(x.get('face') or '—')}، ترخيصه [{h(x.get('status'))}] ← {h(x.get('source'))}"
                            for x in r['resumptive'].get('candidates') or [])
        if r.get('silah_kinds'):
            alts += ''.join(f"<br>وجه الصلة {h(x.get('id') or '')}: {h(x['kind'])}، ترخيصه [{h(x['status'])}] ← {h(x['source'])}"
                            + (f" — {h(x['why'])}" if x.get('why') and x.get('layer') == 'LEGACY' else '') for x in r['silah_kinds'])
        if r.get('shared'):
            alts += f"<br>المشترك بين الأوجه: الحدّ {h(r['shared'].get('boundary'))} — {h(r['shared'].get('note'))}"
        if r.get('function'):
            alts += f"<br>الوظيفة (المحلّ): [{h(r['function'].get('status'))}] {h(r['function'].get('text'))}"
        if isinstance(r.get('extent'), dict):
            e_ = r['extent']
            alts += (f"<br>الامتداد المثبت: «{h(e_['proven_text'])}» ← {h('، '.join(e_['evidence']))}"
                     f"<br>الامتداد المرشّح: «{h(e_['candidate_text'] or '—')}»؛ الحدّ [{h(e_['boundary_status'])}]: {h(e_['boundary_note'])}")
        if (r.get('search_scope') or {}).get('outside_coverage'):
            alts += '<br>خارج التغطية (مؤجَّل لا مرفوض): ' + h('، '.join(r['search_scope']['outside_coverage']))
        if r.get('face') and r.get('selection'):
            alts += f"<br>الوجه: {h(r['face'])}، ترخيصه [{h(r['status'])}]؛ الاختيار: {h(r['selection'])} — {h(r.get('face_note') or '')}"
        if r.get('parts'):
            alts += '<br><sub>المحارف: مواضع الحروف المجمَّعة (الحرف بحركاته) في نص الوحدة التحليلي، بمجالٍ نصف مفتوح [من، إلى)؛ والمقاطع أرقام مقاطع الوحدة</sub>'
        if r.get('head_parts'):
            alts += '<br>أجزاء الأطراف: ' + h('، '.join(f'{k}={v}' for k, v in r['head_parts'].items()))
        if r.get('kind_status'):
            alts += f"<br>اختيار النوع: {h(r['kind_status'])}" + (f" — {h(r['kind_note'])}" if r.get('kind_note') else '')
        if r.get('reason_before_rank'):
            alts += f"<br>قبل الرتبة: {h(r['reason_before_rank'])}"
        rows_r.append([h(r['type']), f"{h(r['rule_id'])} {h(r['rule_version'])}", f"<span class='st {'p' if r['status'] == 'LICENSED' else 'c'}'>{h(r['status'])}</span>",
                       '<br>'.join(f"{h(k)}: <span class='ar'>{h(v)}</span> <sub>{h('، '.join(r['positions'][k]))}</sub>" for k, v in r['texts'].items()),
                       h(r['reason']), '<br>'.join(h(str(x)) + ''.join(
                           f" <sub>← المرشّح {h(l_['candidate'])}" + (f"، العلاقة [{h(l_.get('status'))}]" if l_.get('relation') else '') + '</sub>'
                           for l_ in r.get('premise_links') or [] if l_.get('premise') == x and l_.get('candidate') not in (None, 'self'))
                           for x in r['premises']) or '—', alts,
                       h(' / '.join(f'{k}={r.get(k)}' for k in ('nucleus_complete', 'clause_complete', 'boundary_proven', 'sentence_closed'))) +
                       (f"<br>{h(r.get('search_status'))}" if r.get('search_status') else ''),
                       f"<code>{h(r['relation_id'])}</code>"])
        if len(tl_r) < N:
            tl_r.append(f"{r['type']:<18} {r['rule_id']} {r['status']:<9} " + ' / '.join(f'{k}=«{v}»' for k, v in r['texts'].items())[:110])
    rows_r.append(['—', '—', '—', f'الفحص البنيوي: {"سليم" if not errs else h("؛ ".join(errs))} (بنية السجلات وهوياتها ومقدّماتها، لا صحة الأحكام اللغوية)', '', '', '', '', ''])
    from sarf.relations import check_inflection
    ierrs = check_inflection(rel['axes'], rel['tokens'])
    cell = lambda v: f"{h(ar(v[0]) if v[0] is not None else 'غير محسوم')}<br><sub>{h(str(v[1] or ''))}</sub>"
    for uid, ax in rel['axes'].items():
        loc_ = next((l for u, l, _ in rel['tokens'] if u == uid), '')
        txt = next((t for u, _, t in rel['tokens'] if u == uid), '')
        inf = ax['inflection']
        g = inf.get('governor') or {}
        gov = '—' if not g else (f"«{h(g['operator'])}» ({h(g.get('position'))}) يقتضي {h(g.get('expected'))}؛ العلاقة: {h(g.get('relation'))}"
                                 f"<br>القدرة اللفظية: {h('، '.join(g.get('capacity') or []) or '—')} <sub>({h(g.get('capacity_source'))})</sub>"
                                 f"؛ بوساطة: {h('، '.join(g.get('capacity_mediated') or []) or '—')}"
                                 f"؛ محلّ المعمول الأصلي في الجرد: {h('، '.join(g.get('capacity_mahall_of_complement') or []) or '—')}"
                                 f"<br>المشاهَد في ١١: {h(g.get('observed'))}"
                                 + (f"<br><sub>بدائل معجمية لا تُثبت الاتفاق ولا تنفيه: {h('؛ '.join(str(x['meaning']) + (' (' + '، '.join(x['capacity']) + ')' if x.get('capacity') else ' (بلا أثرٍ إعرابي)') for x in g.get('lexical_alternatives') or []))}</sub>"
                                    if g.get('lexical_alternatives') else '')
                                 + (f"<br>الدور: {h(g.get('role_name'))} ({h(g.get('role_rule'))})" if g.get('role_name') else '')
                                 if g.get('kind') == 'عامل' else f"الدور «{h(g.get('role_name'))}» ({h(g.get('role_rule'))}، {h(g.get('relation_status'))}) يقتضي {h(g.get('expected'))}؛ العلاقة: {h(g.get('relation'))} "
                                 f"<sub><code>{h(g.get('relation_id'))}</code></sub>")
        ef = inf.get('effect') or {}
        eff = '—' if not ef else '؛ '.join(f'{k}: {h(v)}' for k, v in (('لفظي', ef.get('lafzi')), ('تقديري', ef.get('taqdiri')),
                                                                       ('محلّي', ef.get('mahalli'))) if v) or '—'
        dm = inf.get('mark_dims') or {}
        dims = '—' if not dm else f"الحامل: {h(dm.get('carrier') or '—')}؛ الظهور: {h(dm.get('visibility') or '—')}؛ " \
            f"الأصالة: {h(dm.get('originality') or '—')}" + (f"<br><sub>{h(dm.get('reason'))}</sub>" if dm.get('reason') else '')
        nat = ''.join(f"<br><sub>{h(c['what'])}؛ مرشّحات السبب: {h('، '.join(c['candidate_causes']))} — {h(c['note'])}</sub>"
                      for c in inf.get('conflict_nature') or [])
        notes = ''.join(f'<br><sub>{h(n)}</sub>' for n in inf.get('notes') or [])
        mk = inf.get('mark')
        if len(tl_x) < N:
            tl_x.append(f"{loc_:<10} {txt:<14} {inf['agreement']:<10} " + (inf['statement'] or (inf['state'][1] or '')[:70]))
        rl = ax.get('role') or (None, '')
        role_cell = (f"{h(rl[0])} [{h(ax.get('role_status') or '—')}]<br><sub>{h(str(rl[1] or ''))}</sub>" if rl[0] else
                     f"غير مرخَّص<br><sub>{h(str(rl[1] or ''))}</sub>") + \
            (f"<br><sub>حالة المبني: {h((ax.get('mabni_state') or {}).get('code'))}</sub>" if ax.get('mabni_state') else '')
        ca = ax.get('case_axis') or (None, '')
        role_cell += f"<br>الحالة أو المحلّ: {h(ca[0] or 'غير محسوم')}" + (f" ({h(ca[1])})" if ca[0] and not ca[0].startswith('لا محلّ') else '')
        wcell = cell(ax['word_class']) + ''.join(f"<br><sub>جزء {h(p_['part'])}: «{h(p_['text'])}» {h(p_['part_id'])} المحارف {h('[' + '، '.join(map(str, p_['span'])) + ')' if p_.get('span') else '—')} المقاطع {h('، '.join(map(str, p_.get('syllables') or [])) or '—')}</sub>"
                                                 for p_ in ax.get('parts') or [])
        us = ax.get('operator_usage') or {}
        ucell = cell(ax['operator']) + ''.join(
            f"<br><sub>مقبول: «{h(u['operator'])}» (مج {h(u['group'])}) — الاستعمال: {h('، '.join(u.get('usage') or []) or '—')}؛ "
            f"أثره هنا: {h(u.get('effect_in_analysis') or '—')} في «{h(u.get('target_text') or '—')}» ({h(u.get('level') or '—')})"
            + (f"؛ بوساطة: {h(u['mediation'])}" if u.get('mediation') else '') +
            (f"؛ بدائل معجمية: {h('؛ '.join(str(x['meaning']) + (' (' + '، '.join(x['capacity']) + ')' if x.get('capacity') else ' (بلا أثرٍ إعرابي)') for x in u.get('lexical_alternatives') or []))}"
             if u.get('lexical_alternatives') else '') + '</sub>' for u in us.get('accepted', [])) + \
            (f"<br><sub>استعمالاتٌ أخرى للخانة: {h('؛ '.join(str(x['operator']) + ' (مج ' + str(x['group']) + ') ' + str(x['status']) for x in us.get('alternatives', [])))}</sub>"
             if us.get('alternatives') else '')
        pd = ax.get('protection_detail') or {}
        pcell = cell(ax['protection']) + (f"<br><sub>النطاق: {h(pd.get('scope'))}؛ السبب: {h(pd.get('reason'))}؛ المصدر: {h(pd.get('source'))}</sub>"
                                          if pd.get('cls') else '')
        idn = ax.get('identity') or {}
        wcell += f"<br><sub>الهوية: {h(idn.get('analysis_id'))}؛ الخانات {h('، '.join(str(x) for x in idn.get('slots') or []) or '—')}؛ المرحلة ١١: {h('، '.join(idn.get('stage11') or []))}</sub>"
        rows_x.append([h(loc_), f"<span class='ar'>{h(txt)}</span>", wcell, cell(inf['build']), role_cell, gov,
                       cell(inf['state']) + f'<br><sub>الأثر: {eff}</sub>', (f"{h(mk[0])}" if mk else h(inf.get('mark_kind') or '—')) +
                       f'<br><sub>{dims}</sub>', h(inf.get('cause') or (mk[1] if mk else '') or '—'),
                       f"<b>{h(inf['agreement'])}</b>" + ''.join(f'<br>{h(c)}' for c in inf['conflicts']) + nat + notes,
                       h(inf['statement'] or '—'), pcell, ucell])
    rows_x.append(['—', '—', '—', '—', '—', '—', '—', '—', '—',
                   f'الفاحص المستقل للإعراب: {"سليم" if not ierrs else h("؛ ".join(ierrs))} (يفحص محاور الإعراب وحدها: لا يشهد لشهادة الإغلاق ولا لاكتمال التغطية)', '', '', ''])
section('14أ', 'العلاقات المحلية بأدلتها (عقد النواة الاسمية والتعلّق v1)',
        'سجلات sarf.relations: لكل علاقةٍ قاعدتها وإصدارها، وأطرافها بمواضعها، وسببها، ومقدّماتها (حقائق مصدرية أو علاقاتٌ قبلها)، '
        'وبدائلها ومضيفوها، وحقول الاكتمال المستقلة. «LICENSED» علاقةٌ محلية في وجهها، لا اختيارٌ نهائي ولا إغلاق جملة. '
        'وصفوف الجار والمجرور (P01) والظرف (P02) معروضةٌ هنا، وهي مقدّماتٌ لما بعدها بمعرّفاتها',
        rows_r, ['النوع', 'القاعدة', 'الحالة', 'الأطراف', 'السبب', 'المقدّمات', 'البدائل والمضيفون', 'الاكتمال', 'المعرّف'], tl_r)
section('14ب', 'محاور الصنف المستقلة',
        'صنف الكلمة ← البناء أو الإعراب ← العامل ← الحالة ← العلامة (ظاهرة، أو مقدّرة، أو بالحرف، أو بالحذف، أو محلّية) ← سببها. '
        'والعبارة لا تُقال إلا إذا اتفق مقتضى العامل والعلامة المقروءة من النص بصنف الكلمة (AGREE)؛ وما اختلف سُجّل CONFLICT بلا عبارة؛ '
        'والاتفاق اتساقٌ لا إثباتٌ لوظيفة العامل. والفاحص المستقل يعيد قراءة العلامة من النص. '
        'صنف الكلمة (اسم، فعل، حرف)، والبناء والإعراب، والحماية الدستورية، والعمل: محاور لا يُغني أحدها عن الآخر؛ '
        'و«مبني» ليس بديلاً عن «اسم»، و«عامل» ليس صنفاً رابعاً. وشكل التنوين وحده لا يثبت الاسمية في هذا المحور (العقد T19)، '
        'وسمة الصنف في المرحلة ١٣ باقيةٌ كما هي بدليلها',
        rows_x, ['الموضع', 'الوحدة', 'صنف الكلمة', 'البناء', 'الدور النحوي ودليله', 'العامل وعلاقته وقدرته', 'الحالة والأثر', 'العلامة وأبعادها', 'سببها', 'الاتفاق',
                 'العبارة', 'الحماية', 'العمل'], tl_x)
section(15, 'الوحدة الخطابية', 'المعرّفات (2,282,n) فهرسٌ داخلي يبدأ من 0 (internal_index_0_based): الكلمة n فيها هي الكلمة n+1 في المواضع الخارجية. الجمل المتصلة بحدودها وتعلّقها. ونهاية السورة تحدّ نطاق المصدر ولا تثبت وحدها اكتمال البنية: '
        'الإغلاق الخارجي لا يُحكم به إلا باستيفاء التزامات الوحدة', rows_d,
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
import provenance
PROV = provenance.identity('\n'.join(f'{s_}:{v_}\t{t_}' for s_, v_, t_ in VERSES), [
    ('التحليل', 'حيٌّ في هذا التشغيل: analyze() لكل آية، بلا خبيئة (sarf/analyze_cache غير مستعمَلة)'),
    ('المراحل ١–١١', 'Pipeline.run على نص الآية في هذا التشغيل'),
    ('المراحل ١٢–١٦', 'sentence_geo وlinguistic_layer وcross_ayah_links على ناتج هذا التشغيل'),
    ('السمات', 'unit_features على ناتج هذا التشغيل'),
    ('ما لا يُقرأ', 'لا تقرير سابق ولا ملف من reports/ ولا مدوّنة QAC'),
])
prov_tb = '<table><tbody>' + ''.join(f'<tr><th>{h(k)}</th><td><code>{h(str(v))}</code></td></tr>'
                                     for k, v in provenance.rows(PROV)) + '</tbody></table>'
if PROV['dirty']:
    prov_tb = '<p><b>تنبيه: مولَّد من شيفرةٍ فيها تعديلات غير ملتزم بها؛ لا يُعتمد إلا مع بصمة الفرق.</b></p>' + prov_tb
title = 'مسار التحليل: ' + (args.ref or 'نصّ حرّ')
page = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Amiri+Quran&family=Noto+Naskh+Arabic:wght@400;700&display=swap" rel="stylesheet">
<title>{h(title)}</title><style>{CSS}</style></head><body><main><h1>{h(title)}</h1>
<p class="mut">HFN: {h(os.path.basename(hfn().path or '—'))} · {len(VERSES)} آية · المراحل بترتيبها المنطقي، وناتج كلٍّ منها</p>
<section id="run"><h2>هوية التشغيل</h2><p class="mut">ما يلزم لإعادة إنتاج هذا التقرير، والتحقق من الشيفرة التي وَلَدته</p>{prov_tb}</section>
<nav>{nav}</nav>{body}</main>"""
page += f'<footer class="mut">بصمة المخرج (sha256 للصفحة قبل هذا السطر): <code>{provenance.stamp(page)}</code> · هوية التشغيل <code>{PROV["run_id"]}</code></footer></body></html>'
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(page)
print(f'\nكُتب {OUT}')
if not args.out:
    report_serial.register(OUT, title, f"`tools/pipeline_trace.py {args.ref or '--text'}`", commit=PROV['commit'][:7],
                           note=f"هوية التشغيل {PROV['run_id']}" + (' (تعديلات غير ملتزم بها)' if PROV['dirty'] else ''))
print(f"هوية التشغيل {PROV['run_id']} · الالتزام {PROV['commit'][:10]} · "
      f"{'تعديلات غير ملتزم بها: ' + str(len(PROV['dirty'])) if PROV['dirty'] else 'الشيفرة مطابقة للالتزام'}")
