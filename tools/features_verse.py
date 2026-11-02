#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/features_verse.py — صفحة HTML لمراحل الصرف (sarf/features.py) على آيةٍ أو آيات، كلمةً كلمة: لكل وحدةٍ لفظية
سماتها، ولكل سمةٍ قيمتها وحالتها (مثبت، مرشّح، مؤجَّل، غير منطبق) ودليلها والبدائل، وبجانبها قيمة QAC إن وُجد ملفها
(data/quran-morphology.txt، للقياس وحده).

    python3 tools/features_verse.py 2:282                 → reports/features_2_282.html
    python3 tools/features_verse.py 2:282 2:283 -o out.html
"""
import sys, os, re, json, html, argparse, collections
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
os.chdir(H)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.algebra import Trace, sentence_geo
from sarf.features import unit_features
from sarf.root import hfn

ap = argparse.ArgumentParser()
ap.add_argument('refs', nargs='+', help='سورة:آية')
ap.add_argument('-o', '--out')
args = ap.parse_args()
REFS = [tuple(int(x) for x in r.split(':')) for r in args.refs]
OUT = args.out or os.path.join('reports', 'features_' + '_'.join(f'{s}_{v}' for s, v in REFS) + '.html')

GN = re.compile(r'^([123])?([MF])?([SDP])$')


def qfeats(fs):
    d = {}
    for f in fs:
        m = GN.match(f)
        if m and (m.group(2) or m.group(3)):
            if m.group(1):
                d['person'] = int(m.group(1))
            if m.group(2):
                d['gender'] = {'M': 'masc', 'F': 'fem'}[m.group(2)]
            if m.group(3):
                d['number'] = {'S': 'singular', 'D': 'dual', 'P': 'plural'}[m.group(3)]
        elif f.startswith('VF:'):
            d['form'] = int(f[3:])
        elif f in ('PERF', 'IMPF', 'IMPV', 'PASS', 'INDEF'):
            d[f] = True
    if 'gender' in d and 'number' not in d and 'person' not in d:
        d['number'] = 'singular'          # QAC لا يوسم المفرد في الاسم
    return d


cat = Catalog(['operators_catalog.jsonl', 'operators_catalog_split_vocalized.csv'])
ROWS = {(int(x[0]), int(x[1])): x[2] for x in (l.rstrip('\n').split('\t') for l in open('data/quran_hafs.tsv', encoding='utf-8'))}
QAC = 'data/quran-morphology.txt'
Q = collections.defaultdict(list)
if os.path.exists(QAC):
    want = set(REFS)
    for l in open(QAC, encoding='utf-8'):
        loc, f, t, fe = l.rstrip('\n').split('\t')
        s, v, w, k = map(int, loc.split(':'))
        if (s, v) in want:
            Q[(s, v, w)].append((f, t, fe.split('|')))

LBL = dict(pos='الصنف', tense='الزمن', voice='البناء', subject='الفاعل', augmentation='التجرّد والزيادة',
           transitivity='اللزوم والتعدّي', bab='الباب', signified='المدلول (حدث HFN)', form_meaning='معنى الوزن',
           derivation='الاشتقاق', number='العدد', gender='الجنس', plural_type='نوع الجمع', fem_marker='علامة التأنيث',
           definiteness='التعريف والتنكير', person='الشخص')
# السمات المضافة من سجل التغطية (sarf.features_ext)
EXT_LBL = dict(root_class='صنف الجذر', root_arity='عدد الأصول', conjugability='التصرّف', transformations='التحويل (α)',
               definiteness_kind='نوع المعرفة', final_form='صورة الآخر', case_marking='العلامة', diptote='الصرف',
               derivation_candidates='الاشتقاق المحتمل', lemma='اللمّة (HFN)', elative='التفضيل', enclitic_case='محلّ الضمير',
               construction='التركيب', stem_root_candidates='جذر الجذع (مرشّح)', nisba='النسب', diminutive='التصغير',
               polarity='الإثبات والنفي', subject_kind='نوع الإسناد', vocative='النداء', idafa='الإضافة')
LBL.update(EXT_LBL)
NUM = dict(singular='مفرد', dual='مثنى', plural='جمع')
GEN = dict(masc='مذكر', fem='مؤنث', common='مشترك')
PER = {1: 'المتكلم', 2: 'المخاطب', 3: 'الغائب'}
BAB = {'a-u': 'فَعَلَ يَفْعُلُ (نَصَرَ)', 'a-i': 'فَعَلَ يَفْعِلُ (ضَرَبَ)', 'a-a': 'فَعَلَ يَفْعَلُ (فَتَحَ)',
       'i-a': 'فَعِلَ يَفْعَلُ (عَلِمَ)', 'u-u': 'فَعُلَ يَفْعُلُ (كَرُمَ)', 'i-i': 'فَعِلَ يَفْعِلُ (حَسِبَ)'}
PT = dict(sound_masc='جمع مذكر سالم', sound_fem='جمع مؤنث سالم', broken='جمع تكسير')
ROM = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10}
SC = {'مثبت': 'p', 'مرشّح': 'c', 'مؤجَّل': 'd', 'غير منطبق': 'n'}
h = html.escape


def fmt(f, v):
    if v is None:
        return '—'
    if f == 'subject' and isinstance(v, dict):
        return f"{PER.get(v['person'], v['person'])}، {NUM.get(v['number'], v['number'])}، {GEN.get(v['gender'], v['gender'])}"
    if f == 'augmentation' and isinstance(v, dict):
        return f"مجرد ({'ثلاثي' if v['radicals'] == 3 else 'رباعي'})" if v['type'] == 'مجرد' else \
            f"مزيد على {v['wazn']} ({v['letters']})"
    if f == 'signified' and isinstance(v, dict):
        return f"«{v['verb']}»" + (f"، مصدره «{v['masdar']}»" if v.get('masdar') else '')
    if isinstance(v, dict) and 'kinds' in v:
        return f"{v.get('type')}: {'، '.join(v['kinds'])}"
    if isinstance(v, list):
        return '، '.join(map(str, v)) if v else 'لا تحويل'
    if isinstance(v, dict):
        return '، '.join(f'{k}: {x}' for k, x in v.items())
    return str({'bab': BAB, 'number': NUM, 'gender': GEN, 'person': PER, 'plural_type': PT}.get(f, {}).get(v, v)) \
        if f != 'fem_marker' else ('مكتوبة' if v else '—')


def qac_value(u, f, r):
    """→ (قيمة المرجع منسّقة، يوافق أم لا أم None) أو None إن لا مقابل"""
    qv, qn, qp = u['qv'], u['qn'], u['qp']
    v, pos = r['v'], u['feats'].get('pos', {}).get('v')
    g = None
    if f == 'pos' and (v in ('فعل', 'اسم') or r.get('alt')):
        g = 'فعل' if qv else 'اسم' if qn else None
    elif pos == 'فعل' and qv:
        if f == 'tense':
            g = 'ماضٍ' if qv.get('PERF') else 'مضارع' if qv.get('IMPF') else 'أمر' if qv.get('IMPV') else None
        elif f == 'voice':
            g = 'مجهول' if qv.get('PASS') else 'معلوم'
        elif f == 'subject' and 'person' in qv:
            g = dict(person=qv['person'], number=qv['number'], gender=qv.get('gender', 'common'))
            if v and (g['person'] == 1 or (g['person'] == 2 and g['number'] == 'dual')):
                g['gender'] = v['gender']          # QAC لا يجنّس المتكلم ولا المثنى المخاطب
        elif f == 'augmentation' and 'form' in qv:
            vv = None if v is None else (1 if v['type'] == 'مجرد' else ROM[v['form']])
            return ('مجرد' if qv['form'] == 1 else f"مزيد (الوزن {qv['form']})", vv == qv['form'] if vv is not None else None)
    elif f in ('number', 'gender') and qn and pos != 'مبني':
        g = qn.get(f)
    elif f == 'definiteness' and qn:
        g = 'معرفة' if u['det'] or u['psuff'] else 'نكرة' if qn.get('INDEF') else None
    elif f in ('person', 'number', 'gender') and len(qp) == 1:
        g = qp[0].get(f)
    if g is None:
        return None
    shown = g if f in ('pos', 'tense', 'voice', 'definiteness') else fmt(f, g)
    return shown, (v == g) if v is not None else None


CSS = open(os.path.join(H, 'tools', 'features_verse.css'), encoding='utf-8').read()
S = collections.Counter()
bad, body, texts, nw, nu = [], [], [], 0, 0
for s, v in REFS:
    a = analyze(cat, ROWS[(s, v)])
    _, units = sentence_geo(a, f'Q{s}:{v}', Trace())
    F = unit_features(a, units)
    texts.append((s, v, ROWS[(s, v)]))
    words = collections.OrderedDict()
    for (wi, ui), rec in sorted(F.items()):
        segs = Q.get((s, v, wi + 1), [])
        words.setdefault(wi, []).append(dict(
            text=units[(wi, ui)].O['text'], feats=rec, qac=' + '.join(f for f, _, _ in segs),
            qv=next((qfeats(fs) for _, t, fs in segs if t == 'V'), None),
            qn=next((qfeats(fs) for _, t, fs in segs if t in ('N', 'ADJ', 'PN') and 'PRON' not in fs), None),
            qp=[qfeats(fs) for _, t, fs in segs if 'PRON' in fs], det=any('DET' in fs for _, _, fs in segs),
            psuff=any(t == 'N' and 'PRON' in fs and 'SUFF' in fs for _, t, fs in segs)))
    nw += len(words)
    for wi, us in words.items():
        nu += len(us)
        loc = f'{s}:{v}:{wi + 1}'
        rows = []
        for u in us:
            tr = []
            for f, r in u['feats'].items():
                S[(f, r['st'])] += 1
                q = qac_value(u, f, r) if Q else None
                cell = '<span class="q na">لا مقابل</span>'
                if q:
                    gv, ok = q
                    if ok is None:
                        cell = f'<span class="q na">{h(gv)}</span>'
                    else:
                        S[(f, r['st'], ok)] += 1
                        cell = f'<span class="q {"ok" if ok else "bad"}">{"✓" if ok else "✗"} {h(gv)}</span>'
                        if not ok and r['st'] == 'مثبت':
                            bad.append((loc, u['text'], f, r, gv))
                alt = ''
                if r.get('alt'):
                    alt = "<div class='ev'>البدائل: " + h('، '.join(fmt(f, x) for x in r['alt'])) + '</div>'
                tr.append(f"<tr><td>{h(LBL.get(f, f))}</td><td>{h(fmt(f, r['v']))}</td>"
                          f"<td><span class='st {SC.get(r['st'], 'd')}'>{h(r['st'])}</span></td><td>{cell}</td></tr>"
                          f"<tr><td></td><td colspan='3' class='ev'>{h(r.get('ev') or '')}{alt}</td></tr>")
            rows.append(f"<div class='unit'><span class='ut'>{h(u['text'])}</span><table class='ft'>{''.join(tr)}</table></div>")
        qtxt = f' · QAC: {h(us[0]["qac"])}' if us[0]['qac'] else ''
        body.append(f"<div class='word' id='w{loc}'><h3>{h(a['segments'][wi]['word'])} "
                    f"<span class='mut' style='font-size:.8rem'>{loc}{qtxt}</span></h3>{''.join(rows)}</div>")

feats = [f for f in LBL if any(k[0] == f for k in S)]
summ = ['<table><tr><th>السمة</th><th>مثبت</th><th>منه يوافق QAC / يخالف</th><th>مرشّح</th><th>مؤجَّل</th><th>غير منطبق</th></tr>']
for f in feats:
    summ.append(f"<tr><td>{LBL[f]}</td><td>{S[(f, 'مثبت')]}</td><td>{S[(f, 'مثبت', True)]} / "
                f"<b class='{'bad' if S[(f, 'مثبت', False)] else ''}'>{S[(f, 'مثبت', False)]}</b></td>"
                f"<td>{S[(f, 'مرشّح')]}</td><td>{S[(f, 'مؤجَّل')]}</td><td>{S[(f, 'غير منطبق')]}</td></tr>")
summ.append('</table>')
nP = sum(S[(f, 'مثبت')] for f in feats)
nQ = sum(S[(f, 'مثبت', True)] + S[(f, 'مثبت', False)] for f in feats)
nB = sum(S[(f, 'مثبت', False)] for f in feats)
badl = ''.join(f"<li><a href='#w{loc}'>{h(t)}</a> ({loc}) — {LBL[f]}: عندنا «{h(fmt(f, r['v']))}»، وQAC «{h(gv)}». "
               f"<span class='mut'>{h(r['ev'])}</span></li>" for loc, t, f, r, gv in bad) or '<li>لا شيء</li>'
title = 'السمات الصرفية: ' + '، '.join(f'{s}:{v}' for s, v in REFS)
page = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Amiri+Quran&family=Noto+Naskh+Arabic:wght@400;700&display=swap" rel="stylesheet">
<title>{h(title)}</title><style>{CSS}</style></head><body><main>
<h1>{h(title)}</h1>
<p class="mut">مراحل الصرف (<code>sarf/features.py</code>) · HFN: {h(os.path.basename(hfn().path or '—'))} · {'المرجع QAC للقياس وحده، غير مراجَع' if Q else 'لا ملف QAC: بلا مقارنة'}</p>
{''.join(f'<p class="mut">{s}:{v}</p><div class="verse">{h(t)}</div>' for s, v, t in texts)}
<h2>الخلاصة</h2>
<div class="kpis"><div class="k"><b>{nw}</b><span class="mut">كلمة</span></div><div class="k"><b>{nu}</b><span class="mut">وحدة لفظية</span></div>
<div class="k"><b>{nP}</b><span class="mut">سمة مثبتة</span></div>
<div class="k"><b class="{'bad' if nB else 'ok'}">{nB}</b><span class="mut">مثبتٌ يخالف QAC (من {nQ} لها مقابل)</span></div></div>
<p class="legend"><span class="st p">مثبت</span> بدليلٍ مكتوب أو معجمي يعيّن قيمة واحدة <span class="st c">مرشّح</span> دليلٌ غير كافٍ، لا يُقبل
<span class="st d">مؤجَّل</span> لا دليل أو تعدّدت القيم <span class="st n">غير منطبق</span></p>
<div class="wrap">{''.join(summ)}</div>
<h2>المثبت المخالف لـQAC</h2><ul>{badl}</ul>
<h2>الكلمات</h2>{''.join(body)}
</main></body></html>"""
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
open(OUT, 'w', encoding='utf-8').write(page)
print(f'كُتب {OUT}: {nw} كلمة، {nu} وحدة، {nP} سمة مثبتة، {nB} مثبتٌ يخالف QAC من {nQ}')
