#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/audit_batch_a.py — الدفعة A من خطة الاستكمال: المصدر والتطبيع والخلايا والمقاطع على المصحف المدخل كله.

لكل آية: استرجاع المصدر من التمثيلين (التحليلي والعرضي) بالخلايا والسجل وحدهما؛ ولكل كلمةٍ في التمثيل التحليلي:
  I1 الشدة محفوظة (عددها في المصدر = عددها في التحليل)
  I2 لا نون مكتوبة للتنوين (عدد النون لا يزيد)
  I3 الخنجرية على الألف المقصورة تُحذف وحدها (لا «ىٰ» في التحليل، وعدد «ى» محفوظ)
  I4 كل حرفٍ مكتوب له خلية أو هو صامتٌ مسنَد إلى خلية (لا حرف ضائع)
  I5 كل خليةٍ في مقطعٍ واحد بالضبط، أو في قائمة ما لم يُبنَ له مقطع بسببه
  I6 لا خلية صامتة (حرف) تُنشأ لتنوين
ويكتب كل إخفاقٍ بموضعه وكلمته؛ ولا يُصلح شيئاً.

    python3 tools/audit_batch_a.py --json <تقرير.json>
"""
import argparse, collections, json, os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
from sarf import quran_source
from sarf.normalize_trace import normalize_traced, restore_source
from sarf.syllables import unit_syllables
from sarf.cells import letters
from sarf.core import Trace

SHADDA, DAGGER, MAQSURA, NUN, SMALL_NUN = '\u0651', '\u0670', '\u0649', '\u0646', '\u06E8'
TANWIN = 'ًٌٍ'


def audit_word(src_w, an_w, loc):
    fails = []
    if src_w.count(SHADDA) != an_w.count(SHADDA):
        fails.append(('I1_SHADDA', f'{src_w.count(SHADDA)}→{an_w.count(SHADDA)}'))
    src_nun = src_w.count(NUN) + src_w.count(SMALL_NUN)        # النون الصغيرة المكتوبة (نُـۨجِي) حرفٌ مكتوب لا تنوين
    if an_w.count(NUN) > src_nun:
        fails.append(('I2_TANWIN_NUN', f'{src_nun}→{an_w.count(NUN)}'))
    if MAQSURA + DAGGER in an_w or an_w.count(MAQSURA) != src_w.count(MAQSURA):
        fails.append(('I3_DAGGER_MAQSURA', ''))
    try:
        cells, sylls, stray, _ = unit_syllables(an_w, 'u', Trace())
    except Exception as e:
        return fails + [('SYLLABIFY_ERROR', repr(e)[:120])], 0, 0, 0
    toks = letters(an_w)
    covered = set()
    for c in cells:
        covered.update(c.O.get('tok', []))
        covered.update(j for j, _ in c.O.get('silent', []))
    missing = [j for j in range(len(toks)) if j not in covered]
    if missing:
        fails.append(('I4_LETTER_WITHOUT_CELL', ''.join(toks[j][0] for j in missing)))
    seen = collections.Counter(id(c) for G in sylls for c in G.A)
    stray_ids = {id(c) for c, _ in stray}
    bad = [c for c in cells if seen[id(c)] + (id(c) in stray_ids) != 1]
    if bad:
        fails.append(('I5_CELL_SYLLABLE_COVER', ' '.join(c.C for c in bad)))
    for c in cells:
        if c.C == NUN and not c.O.get('tok') and not c.O.get('glyph'):
            fails.append(('I6_TANWIN_CELL', c.id))
    return fails, len(cells), len(sylls), len(stray)


def word_pairs(text, r):
    """كلمات التحليل مع مقابلها في المصدر بمواضع المصدر لكل محرف (لا بتقسيم المسافات وحده: «هُدࣰ ى» في المصدر كلمةٌ واحدة
    في التحليل). → [(المصدر، التحليل)] أو None إن لم يُطابَق عدد المحارف"""
    A = r['analysis']
    cells = r['cells_analysis']
    if len(cells) != len(A):
        return None
    out, cur, idx = [], [], []
    for ch, c in list(zip(A, cells)) + [(' ', None)]:
        if ch == ' ':
            if cur:
                src = [i for i in idx if i is not None]
                out.append((text[min(src):max(src) + 1] if src else '', ''.join(cur)))
            cur, idx = [], []
            continue
        cur.append(ch)
        idx.extend(c['src'] or [None])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', required=True)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    rows = quran_source.rows()
    if a.limit:
        rows = rows[:a.limit]
    C = collections.Counter()
    F = collections.defaultdict(list)
    stray_reasons = collections.Counter()
    for s, v, text in rows:
        loc = f'{s}:{v}'
        r = normalize_traced(text, loc)
        C['verses'] += 1
        for which in ('analysis', 'display'):
            rec, fails = restore_source(r, which)
            if fails or rec != text:
                C[f'restore_fail_{which}'] += 1
                F[f'RESTORE_{which.upper()}'].append(dict(loc=loc, fails=[f['code'] for f in fails][:5]))
        pairs = word_pairs(text, r)
        if pairs is None:
            C['word_alignment_fail'] += 1
            F['WORD_ALIGNMENT'].append(dict(loc=loc))
            continue
        C['joined_source_words'] += sum(1 for x, _ in pairs if ' ' in x)
        sw, aw = [x for x, _ in pairs], [y for _, y in pairs]
        for i, (x, y) in enumerate(zip(sw, aw), 1):
            C['words'] += 1
            fails, nc, ns, nst = audit_word(x, y, loc)
            C['cells'] += nc
            C['syllables'] += ns
            C['stray_cells'] += nst
            for code, det in fails:
                C[code] += 1
                if len(F[code]) < 200:
                    F[code].append(dict(loc=f'{loc}:{i}', src=x, analysis=y, detail=det))
            if nst:
                _, _, stray, _ = unit_syllables(y, 'u', Trace())
                for c, why in stray:
                    stray_reasons[why] += 1
                    if len(F['STRAY']) < 200:
                        F['STRAY'].append(dict(loc=f'{loc}:{i}', analysis=y, cell=c.C, why=why))
    # تصنيف ما لم يُبنَ له مقطع: الحروف المقطّعة (تُقرأ بأسمائها، والكتابة لا تعيّن مقاطع أسمائها)، والساكن أول الوحدة
    # بعد كلمةٍ قبلها (لۡيَقۡطَعۡ بعد «ثُمَّ»): مقطعه عابرٌ لحدّ الكلمة، والمقطِّع يعمل داخل الوحدة
    MUQ = {'حم', 'طسم', 'المص', 'المر', 'كهيعص', 'طه', 'طس', 'يس', 'ص', 'عسق', 'ق', 'ن', 'الم', 'الر', 'طسم'}
    sk = lambda w: ''.join(ch for ch in w if '\u0621' <= ch <= '\u064A')
    C['stray_muqattaat'] = sum(1 for x in F['STRAY'] if sk(x['analysis']) in MUQ)
    C['stray_cross_word'] = sum(1 for x in F['STRAY'] if sk(x['analysis']) not in MUQ)
    out = dict(source=quran_source.name(), counts=dict(C), stray_reasons=dict(stray_reasons), examples=F)
    json.dump(out, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(dict(C), ensure_ascii=False))
    print(json.dumps(dict(stray_reasons), ensure_ascii=False))


if __name__ == '__main__':
    main()
