#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/eval_features.py — قياس مراحل الصرف (sarf/features.py) على القرآن كله، مقابل مدوَّنة QAC للقياس وحده.

  لكل سمة: عدد المثبت وصحته، والمرشّح وصحته (منفصلاً، فالمرشّح لا يُقبل)، والمؤجَّل، وأمثلة الخلاف.
  السمات المقيسة: صنف الكلمة (فعل/اسم)، وزمن الفعل، وبناؤه للمعلوم أو المجهول، وفاعله (الشخص والعدد والجنس)،
  ووزنه (التجرّد والزيادة، رقم الوزن)، وعدد الاسم وجنسه، وتعريفه وتنكيره، وسمات الضمائر والمبنيات.
  ولا مقابل في QAC للّزوم والتعدّي ولا للباب ولا للمدلول: يُعدّ ما ثبت منها، ولا تُقاس صحته هنا.
  → reports/features_eval.json

    python3 tools/eval_features.py [1-114] [--jobs N]
"""
import sys, os, re, json, difflib, collections, argparse
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
ap = argparse.ArgumentParser()
ap.add_argument('range', nargs='?', default='1-114')
ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
args = ap.parse_args()
lo, hi = (int(x) for x in args.range.split('-'))

GN = re.compile(r'^([123])?([MF])?([SDP])$')


def skel(t):
    t = re.sub('[ً-ٰٟۖ-ࣰۭ-ࣲـ]', '', t)
    return t.translate(str.maketrans('ٱأإآؤئىة', 'اااااييه')).replace('ء', '')


def qfeats(fs):
    """→ dict من سمات مقطع QAC"""
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
        elif f in ('PERF', 'IMPF', 'IMPV', 'PASS', 'INDEF', 'DET', 'PRON', 'SUFF', 'PREF'):
            d[f] = True
    if 'gender' in d and 'number' not in d and 'person' not in d:
        d['number'] = 'singular'      # QAC لا يوسم المفرد في الاسم: الجنس وحده (M، F) مفرد
    return d


Q = collections.defaultdict(list)
for l in open(H + 'data/quran-morphology.txt', encoding='utf-8'):
    loc, form, tag, feats = l.rstrip('\n').split('\t')
    s, v, w, k = map(int, loc.split(':'))
    if lo <= s <= hi:
        Q[(s, v, w)].append((form, tag, feats.split('|')))
ROWS = [(int(s), int(v), t) for s, v, t in (l.rstrip('\n').split('\t') for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'))
        if lo <= int(s) <= hi]
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10}
TENSE = {'ماضٍ': 'PERF', 'مضارع': 'IMPF', 'أمر': 'IMPV'}


def surah_job(s):
    from sarf.analyze_cache import analyze_cached
    from sarf.catalog import Catalog
    from sarf.algebra import Trace, sentence_geo
    from sarf.features import unit_features, PROVEN, CAND, DEFER
    cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
    C = collections.Counter()
    ex = collections.defaultdict(list)

    def score(feat, rec, gold, loc, txt):
        st = rec['st']
        if st == PROVEN or st == CAND:
            tag = 'مثبت' if st == PROVEN else 'مرشّح'
            if gold is None:
                C[f'{feat}:{tag}:بلا مقابل'] += 1
                return
            ok = rec['v'] == gold
            C[f'{feat}:{tag}'] += 1
            C[f'{feat}:{tag}:صحيح'] += ok
            if not ok and len(ex[f'{feat}:{tag}']) < 30:
                ex[f'{feat}:{tag}'].append(f'{loc} {txt}: عندنا {rec["v"]} ({rec["ev"][:70]}) | QAC {gold}')
        elif st == DEFER:
            C[f'{feat}:مؤجَّل'] += 1
            if gold is not None and rec.get('alt') and gold not in rec['alt'] and not isinstance(gold, dict):
                C[f'{feat}:مؤجَّل:المرجع خارج البدائل'] += 1

    for s_, v, text in [r for r in ROWS if r[0] == s]:
        a = analyze_cached(cat, text)
        _, units = sentence_geo(a, f'Q{s_}:{v}', Trace())
        F = unit_features(a, units)
        qws = sorted(k[2] for k in Q if k[0] == s_ and k[1] == v)
        qtext = [skel(''.join(f for f, _, _ in Q[(s_, v, w)])) for w in qws]
        otext = [skel(seg['word']) for seg in a['segments']]
        amap = {}
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, otext, qtext, autojunk=False).get_opcodes():
            if op in ('equal', 'replace') and i2 - i1 == j2 - j1:
                for k in range(i2 - i1):
                    amap[i1 + k] = qws[j1 + k]
        for (wi, ui), rec in F.items():
            C['وحدات'] += 1
            for f_, r_ in rec.items():
                C[f'حالة:{f_}:{r_["st"]}'] += 1
            if wi not in amap:
                C['غير مقابَل'] += 1
                continue
            segs = Q[(s_, v, amap[wi])]
            loc = f'{s_}:{v}:{wi + 1}'
            txt = units[(wi, ui)].O['text']
            pos = rec.get('pos', {})
            qv = next((qfeats(fs) for _, tag, fs in segs if tag == 'V'), None)
            qn = next((qfeats(fs) for _, tag, fs in segs if tag in ('N', 'ADJ', 'PN') and 'PRON' not in fs), None)
            # صنف الكلمة: فعل/اسم
            if pos.get('v') in ('فعل', 'اسم') or (pos.get('st') == DEFER and set(pos.get('alt') or []) == {'اسم', 'فعل'}):
                gold = 'فعل' if qv is not None else 'اسم' if qn is not None else None
                score('الصنف', pos, gold, loc, txt)
            if pos.get('v') == 'فعل' and qv is not None:
                if 'tense' in rec:
                    score('الزمن', rec['tense'], next((k for k, t in TENSE.items() if qv.get(t)), None), loc, txt)
                if 'voice' in rec:
                    score('البناء للمعلوم أو المجهول', rec['voice'], 'مجهول' if qv.get('PASS') else 'معلوم', loc, txt)
                if 'subject' in rec and all(k in qv for k in ('person', 'number')):
                    g = dict(person=qv['person'], number=qv['number'], gender=qv.get('gender', 'common'))
                    r = dict(rec['subject'])
                    if r['v']:
                        r['v'] = dict(r['v'])
                        if g['person'] == 1 or (g['person'] == 2 and g['number'] == 'dual'):
                            g['gender'] = r['v'].get('gender')        # QAC لا يجنّس المتكلم ولا المثنى المخاطب
                    score('الفاعل', r, g, loc, txt)
                if 'augmentation' in rec and 'form' in qv:
                    a_ = rec['augmentation']
                    rr = dict(a_, v=(1 if a_['v']['type'] == 'مجرد' else ROMAN[a_['v']['form']]) if a_['v'] else None)
                    score('التجرّد والزيادة (رقم الوزن)', rr, qv['form'], loc, txt)
            if pos.get('v') == 'اسم' or (pos.get('st') == DEFER and qn is not None and qv is None):
                if qn is not None:
                    if 'number' in rec:
                        score('عدد الاسم', rec['number'], qn.get('number'), loc, txt)
                    if 'gender' in rec:
                        score('جنس الاسم', rec['gender'], qn.get('gender'), loc, txt)
                    if 'definiteness' in rec:
                        has_det = any('DET' in fs for _, _, fs in segs)
                        has_suff = any(t_ == 'N' and 'PRON' in fs and 'SUFF' in fs for _, t_, fs in segs)
                        gold = 'معرفة' if has_det or has_suff else 'نكرة' if qn.get('INDEF') else None
                        score('التعريف والتنكير', rec['definiteness'], gold, loc, txt)
            if 'person' in rec or ('number' in rec and pos.get('v') == 'مبني'):
                qp = [qfeats(fs) for _, t_, fs in segs if 'PRON' in fs]
                if len(qp) == 1:
                    for k in ('person', 'number', 'gender'):
                        if k in rec:
                            score(f'الضمير/{k}', rec[k], qp[0].get(k), loc, txt)
            for f_ in ('transitivity', 'bab', 'signified'):
                if f_ in rec and rec[f_]['st'] == PROVEN:
                    C[f'{f_}:مثبت بلا مقابل في QAC'] += 1
    return C, ex


if __name__ == '__main__':
    import multiprocessing as mp
    C, ex = collections.Counter(), collections.defaultdict(list)
    with mp.get_context('fork').Pool(args.jobs) as P:
        for c, e in P.imap_unordered(surah_job, range(lo, hi + 1)):
            C.update(c)
            for k, v in e.items():
                ex[k] += v
    feats = sorted({k.split(':')[0] for k in C if k.count(':') >= 1 and not k.startswith('حالة')})
    table = {}
    for f in feats:
        row = {}
        for tag in ('مثبت', 'مرشّح'):
            n, ok = C.get(f'{f}:{tag}', 0), C.get(f'{f}:{tag}:صحيح', 0)
            if n:
                row[tag] = dict(n=n, correct=ok, acc=round(100 * ok / n, 2))
        if C.get(f'{f}:مؤجَّل'):
            row['مؤجَّل'] = C[f'{f}:مؤجَّل']
        if row:
            table[f] = row
    out = dict(range=args.range, counts=dict(C), table=table, examples={k: v[:30] for k, v in ex.items()})
    json.dump(out, open(H + 'reports/features_eval.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for f, row in table.items():
        print(f, row)
    for k in sorted(C):
        if 'بلا مقابل' in k or k in ('وحدات', 'غير مقابَل'):
            print(k, C[k])
