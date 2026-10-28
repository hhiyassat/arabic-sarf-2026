"""tools/eval_qac.py — قياس المحلل على مدوَّنة القرآن الصرفية (QAC): الفعل، والإسناد (T18)، والجهة
يحتاج data/quran_hafs.tsv وdata/quran-morphology.txt (QAC، GPL: لا تُرفع إلى المستودع)، وHFN لقياس الجذور.
الاستعمال: python3 tools/eval_qac.py [1-114]
"""
import sys, collections, difflib, re
import os, json
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.affix import stem_info
cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
lo, hi = (int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else '1-114').split('-'))
Q = collections.defaultdict(list)
for l in open(H + 'data/quran-morphology.txt', encoding='utf-8'):
    loc, form, tag, feats = l.rstrip('\n').split('\t')
    s, v, w, k = map(int, loc.split(':'))
    if lo <= s <= hi:
        Q[(s, v, w)].append((form, tag, feats.split('|')))
PNG = {'1S': (1, 'singular'), '1P': (1, 'plural'), '2MS': (2, 'singular', 'masc'), '2FS': (2, 'singular', 'fem'),
       '2D': (2, 'dual'), '2MP': (2, 'plural', 'masc'), '2FP': (2, 'plural', 'fem'), '3MS': (3, 'singular', 'masc'),
       '3FS': (3, 'singular', 'fem'), '3MD': (3, 'dual'), '3FD': (3, 'dual'), '3D': (3, 'dual'), '3MP': (3, 'plural', 'masc'),
       '3FP': (3, 'plural', 'fem'), '2MD': (2, 'dual'), '2FD': (2, 'dual')}
C = collections.Counter(); ex = collections.defaultdict(list)
def skel(t):
    t = re.sub('[\u064B-\u065F\u0670\u06D6-\u06ED\u08F0-\u08F2\u0640]', '', t)
    return t.translate(str.maketrans('ٱأإآؤئىة', 'اااااييه')).replace('ء', '')
for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'):
    s, v, text = l.rstrip('\n').split('\t'); s, v = int(s), int(v)
    if not lo <= s <= hi:
        continue
    a = analyze(cat, text)
    agr = {(g['word_index'], g['slot']): g for g in a['agreement']}
    # الربط كلمةً بكلمة بمطابقة الحروف (لا برقم الموضع): تقسيم الكلمات قد يختلف بين النصين
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
            C['unaligned'] += 1
            continue
        qsegs = Q.get((s, v, amap[wi]), [])
        qv = next((q for q in qsegs if q[1] == 'V'), None)
        for sl in seg['slots']:
            if sl['type'] != 'جذع':
                continue
            m = stem_info(sl['text'])
            ours = m['pos'] == 'verb' or (wi, sl['index']) in agr
            if ours:
                C['ours_verb'] += 1
                if qv: C['ours_verb_ok'] += 1
                else: ex['false_verb'].append(f'{s}:{v} {seg["word"]} {[q[1] for q in qsegs]}')
            g = agr.get((wi, sl['index']))
            if g and qv:
                C['agr'] += 1
                png = next((f for f in qv[2] if f in PNG), None)
                want = PNG.get(png)
                got = [f for f in g['features']]
                hit = want and any(f[:len(want)] == want for f in got)
                C['agr_hit'] += bool(hit)
                if len(got) == 1: C['agr_single'] += 1; C['agr_single_hit'] += bool(hit)
                if not hit: ex['agr_miss'].append(f'{s}:{v} {seg["word"]} ours={g["pronouns"]} qac={png}')
                qpass = 'PASS' in qv[2]
                if g.get('voice') is not None:
                    C['voice'] += 1; C['voice_hit'] += (g['voice'] == 'passive') == qpass
                    if (g['voice'] == 'passive') != qpass: ex['voice_miss'].append(f'{s}:{v} {seg["word"]} ours={g["voice"]} qac={"PASS" if qpass else "ACT"}')
        if qv and not any(stem_info(sl['text'])['pos'] == 'verb' or (wi, sl['index']) in agr for sl in seg['slots'] if sl['type'] == 'جذع'):
            C['qac_verb_missed'] += 1
        if qv: C['qac_verbs'] += 1
for k, n in sorted(C.items()): print(k, n)
# المقاييس تُحفظ ليعرضها تقرير HTML (reports/quran_metrics.json)
if (lo, hi) == (1, 114):
    P = H + 'reports/quran_metrics.json'
    M = json.load(open(P, encoding='utf-8')) if os.path.exists(P) else {}
    M['qac'] = dict(C)
    json.dump(M, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
for k in ex:
    print('==', k, len(ex[k]))
    for e in ex[k][:25]: print('  ', e)
