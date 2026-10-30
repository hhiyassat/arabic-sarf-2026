"""tools/eval_root.py — قياس T19c (الجذر والوزن) بمدوَّنة القرآن الصرفية: على الأفعال التي حكم بها المحلل
يحتاج data/quran_hafs.tsv وdata/quran-morphology.txt (QAC، GPL: لا تُرفع إلى المستودع)، وHFN لقياس الجذور.
الاستعمال: python3 tools/eval_root.py [1-114]
"""
import sys, collections, difflib, re
import os, json
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.root import morph
from sarf.affix import stem_info
cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
lo, hi = (int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else '1-114').split('-'))
Q = collections.defaultdict(list)
for l in open(H + 'data/quran-morphology.txt', encoding='utf-8'):
    loc, form, tag, feats = l.rstrip('\n').split('\t')
    s, v, w, k = map(int, loc.split(':'))
    if lo <= s <= hi:
        Q[(s, v, w)].append((form, tag, feats.split('|')))
def skel(t):
    t = re.sub('[ً-ٰٟۖ-ࣰۭ-ࣲـ]', '', t)
    return t.translate(str.maketrans('ٱأإآؤئىة', 'اااااييه')).replace('ء', '')
HZ = str.maketrans('أإؤئآ', 'ءءءءء')
VF = {str(i): r for i, r in enumerate(['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII'])}
C = collections.Counter(); ex = collections.defaultdict(list)
# سجلٌّ لكل وقوعِ فعلٍ مقابَل بـQAC (للمصالحة بالهويات بين نسختين): SARF_ROOT_DUMP=مسار
DUMP = open(os.environ['SARF_ROOT_DUMP'], 'w', encoding='utf-8') if os.environ.get('SARF_ROOT_DUMP') else None
for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'):
    s, v, text = l.rstrip('\n').split('\t'); s, v = int(s), int(v)
    if not lo <= s <= hi:
        continue
    a = analyze(cat, text)
    qws = sorted(k[2] for k in Q if k[0] == s and k[1] == v)
    qtext = [skel(''.join(f for f, _, _ in Q[(s, v, w)])) for w in qws]
    otext = [skel(seg['word']) for seg in a['segments']]
    amap = {}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, otext, qtext, autojunk=False).get_opcodes():
        if op in ('equal', 'replace') and i2 - i1 == j2 - j1:
            for k in range(i2 - i1):
                amap[i1 + k] = qws[j1 + k]
    for seg in a['segments']:
        wi = seg['word_index']
        if wi not in amap:
            continue
        qv = next((q for q in Q[(s, v, amap[wi])] if q[1] == 'V'), None)
        for sl in seg['slots']:
            if sl['type'] != 'جذع':
                continue
            m = morph(sl['text'])
            if not m:
                continue
            C['morph'] += 1
            if not qv:
                C['not_qac_verb'] += 1
                if m['status'] == 'accepted': ex['acc_not_verb'].append(f"{s}:{v} {sl['text']} {m.get('root')}")
                continue
            groot = next((f[5:] for f in qv[2] if f.startswith('ROOT:')), '').translate(HZ)
            gvf = VF.get(next((f[3:] for f in qv[2] if f.startswith('VF:')), ''), '')
            C['qv'] += 1
            cand_roots = {r for r, _ in m['candidates']}
            C['gold_in_cands'] += groot in cand_roots
            if groot not in cand_roots:
                ex['gold_not_in_cands'].append(f"{s}:{v} {sl['text']} gold={groot}/{gvf} cands={sorted(cand_roots)[:5]}")
            if DUMP is not None:
                DUMP.write(json.dumps(dict(loc=f'{s}:{v}:{wi}', text=sl['text'], status=m['status'], root=m.get('root'),
                                           form=m.get('form_class'), level=m.get('level'), reason=m.get('reason'),
                                           selection=m.get('selection'), gold=groot, gold_form=gvf),
                                      ensure_ascii=False) + '\n')
            if m['status'] == 'accepted':
                C['acc'] += 1; C['acc_' + m['level']] += 1
                okr = m['root'] == groot; okf = m['form_class'] == gvf
                C['acc_root_ok'] += okr; C['acc_form_ok'] += okf
                C[f"acc_{m['level']}_root_ok"] += okr
                if not okr or not okf:
                    ex['acc_wrong'].append(f"{s}:{v} {sl['text']} ours={m['root']}/{m['form_class']}/{m['level']} gold={groot}/{gvf}")
            else:
                C['deferred'] += 1
                ex['deferred'].append(f"{s}:{v} {sl['text']} gold={groot}/{gvf} :: {m.get('reason','')[:80]}")
for k, n in sorted(C.items()): print(k, n)
# المقاييس تُحفظ ليعرضها تقرير HTML (reports/quran_metrics.json)
if (lo, hi) == (1, 114):
    P = H + 'reports/quran_metrics.json'
    M = json.load(open(P, encoding='utf-8')) if os.path.exists(P) else {}
    M['root'] = dict(C)
    json.dump(M, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
for k in ex:
    print('==', k, len(ex[k]))
    for e in ex[k][:30]: print('  ', e)
