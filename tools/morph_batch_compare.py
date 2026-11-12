"""tools/morph_batch_compare.py <M_DIR_BASE> <M_DIR_NEW> <TAG> <OUT_DIR> — انتقالات دفعة صرفية (MORPH_COMPLETION_01) بين الأساس والدفعة،
بالمورد نفسه، من مخرج المحرّك عبر run():
1. التقسيم: كل كلمةٍ تغيّرت خاناتها، منسوبةً إلى قاعدتها المعلنة (attribute)؛ وما لا تفسّره قاعدةٌ معلنة UNEXPLAINED.
2. الصنف الرئيسي لكل كلمة (tools/morph_reconcile.py): مصفوفة الانتقال، وقوائم: ما فُقد من صحيح، والخطأ الجديد، وتغيّر الحماية.
3. الجذر والوزن والحماية في eval_root (cmp_roots) كما هي.
4. الجمل والاستقرار: من مقارنة التفريغين (cmp_dump)، مع الآيات التي تغيّرت جملها دون أن تتغيّر فيها كلمةٌ بالتقسيم (UNEXPLAINED_VERSE).
5. المحاور (الإعراب والعلاقات والأدوار): cmp_axes كما هي، ومواضعها."""
import gzip, json, os, sys
from collections import Counter, defaultdict
MB, MN, TAG, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)


def load_engine(p):
    W = defaultdict(list)
    for l in gzip.open(p, 'rt', encoding='utf-8'):
        x = json.loads(l)
        W[(x['verse'], x['wi'])].append(x)
    return W


def sig(S):
    return [(s['type'], s['text']) for s in S]


def attribute(b, p):
    """القاعدة المعلنة التي تفسّر الانتقال، من شكله وحده (لا من القائمة)"""
    has = lambda S, t, x=None: any(s[0] == t and (x is None or s[1] == x) for s in S)
    if has(p, 'مبني', 'أَ') and not has(b, 'مبني', 'أَ'):
        return 'P1a_INTERROGATIVE_A'
    if has(p, 'مبني', 'لَ') and not has(b, 'مبني', 'لَ'):
        return 'P1a_EMPHATIC_LA'
    if has(b, 'أل') and not has(p, 'أل'):
        return 'P1d_NOT_ARTICLE'
    if sum(1 for s in b if s[0] == 'جذع') > sum(1 for s in p if s[0] == 'جذع') and any('نَّا' in s[1] for s in p if s[0] == 'جذع'):
        return 'P1c_ASSIMILATED_NAA'
    if any(s[0] == 'مبني' and s[1] in ('وَ', 'فَ') for s in p) and not any(s[1] in ('وَ', 'فَ') for s in b):
        return 'P1b_WASL_DROPPED'
    return 'UNEXPLAINED'


EB, EN = load_engine(os.path.join(MB, 'engine_base.jsonl.gz')), load_engine(os.path.join(MN, f'engine_{TAG}.jsonl.gz'))
seg = []
for k in sorted(set(EB) | set(EN)):
    b, p = sig(EB.get(k, [])), sig(EN.get(k, []))
    if b != p:
        seg.append(dict(verse=k[0], wi=k[1], word=(EB.get(k) or EN.get(k))[0]['word'], before=b, after=p, rule=attribute(b, p)))
seg_verses = {x['verse'] for x in seg}


def load_rec(d):
    return {json.loads(l)['loc']: json.loads(l) for l in gzip.open(os.path.join(d, 'per_word.jsonl.gz'), 'rt', encoding='utf-8')}


RB, RN = load_rec(os.path.join(MB, 'rec_base')), load_rec(os.path.join(MN, f'rec_{TAG}'))
trans = Counter()
lost, new_wrong, prot, gained = [], [], [], []
for loc in sorted(set(RB) | set(RN)):
    a, b = (RB.get(loc) or {}).get('primary', 'ABSENT'), (RN.get(loc) or {}).get('primary', 'ABSENT')
    if a != b:
        trans[(a, b)] += 1
        rec = dict(loc=loc, word=(RN.get(loc) or RB.get(loc))['word'], before=a, after=b, slots_before=(RB.get(loc) or {}).get('slots'),
                   slots_after=(RN.get(loc) or {}).get('slots'), root_before=(RB.get(loc) or {}).get('final_root'), root_after=(RN.get(loc) or {}).get('final_root'),
                   qac_root=(RN.get(loc) or RB.get(loc)).get('qac_root'))
        if a == 'ROOT_CORRECT':
            lost.append(rec)
        if b == 'ROOT_WRONG':
            new_wrong.append(rec)
        if 'PROTECT' in a or 'PROTECT' in b or 'NOT_APPLICABLE' in a + b or 'CLASS_DEFERRED' in a + b:
            prot.append(rec)
        if b == 'ROOT_CORRECT':
            gained.append(rec)
cmp_dump = json.load(open(os.path.join(MN, 'cmp_dump.json'), encoding='utf-8'))
sent_verses = set()
for d in cmp_dump.get('sentence_diffs', []) or []:
    v = d.get('verse') or (d.get('span') or [''])[0].rsplit(':', 1)[0]
    if v:
        sent_verses.add(v)
import re as _re
VK = _re.compile(r'^\d+:\d+$')
key_verses = {kd['key'] for kd in cmp_dump.get('key_diffs', []) if isinstance(kd, dict) and VK.match(str(kd.get('key')))}
by_prod = Counter(kd.get('product') for kd in cmp_dump.get('key_diffs', []) if isinstance(kd, dict))
unexpl = Counter(kd.get('product') for kd in cmp_dump.get('key_diffs', []) if isinstance(kd, dict) and VK.match(str(kd.get('key')))
                 and kd['key'] not in seg_verses)
def _near(v, k=3):
    s_, n_ = map(int, v.split(':'))
    return [f'{s_}:{x}' for x in range(n_ - k, n_ + k + 1) if f'{s_}:{x}' in seg_verses]


no_own = sorted({kd['key'] for kd in cmp_dump.get('key_diffs', []) if isinstance(kd, dict) and VK.match(str(kd.get('key')))
                 and kd['key'] not in seg_verses}, key=lambda v: tuple(map(int, v.split(':'))))
neighbour = {v: _near(v) for v in no_own if _near(v)}
unexpl_verses = [v for v in no_own if v not in neighbour]
_SID = _re.compile(r'L\d+\.d\d+\.J')
_n = lambda x: _SID.sub('L#', json.dumps(x, ensure_ascii=False, sort_keys=True))
sc = cmp_dump.get('sentences') or {}
renum, content = [], []
for c in sc.get('changed') or []:
    f = c.get('fields') or {}
    (content if any(_n(v[0]) != _n(v[1]) for v in f.values()) else renum).append(c)
seg_by_verse = defaultdict(list)
for x in seg:
    seg_by_verse[x['verse']].append(f"{x['word']}:{x['rule']}")


def span_verses(span):
    a, b = span[0].rsplit(':', 1)[0], span[1].rsplit(':', 1)[0]
    sa, va = map(int, a.split(':')); sb, vb = map(int, b.split(':'))
    return [f'{sa}:{v}' for v in range(va, vb + 1)] if sa == sb else [a, b]


struct = []
for kind in ('split', 'merge'):
    for c in sc.get(kind) or []:
        vs = span_verses(c['span'])
        struct.append(dict(kind=kind, span=c['span'], seg_changes_in_span={v: seg_by_verse[v] for v in vs if v in seg_by_verse},
                           explained=any(v in seg_by_verse for v in vs)))
for c in content:
    vs = span_verses(c['span'])
    struct.append(dict(kind='content', span=c['span'], fields=c.get('fields'), seg_changes_in_span={v: seg_by_verse[v] for v in vs if v in seg_by_verse},
                       explained=any(v in seg_by_verse for v in vs)))
json.dump(struct, open(os.path.join(OUT, 'sentence_changes.json'), 'w'), ensure_ascii=False, indent=1)
summ = dict(tag=TAG,
            sentences_classified=dict(same=sc.get('same'), renumbering_only=len(renum), content_changed=len(content),
                                      split=len(sc.get('split') or []), merge=len(sc.get('merge') or []),
                                      structural_or_content_unexplained=sum(1 for x in struct if not x['explained'])), segmentation_changed_words=len(seg), by_rule=dict(Counter(x['rule'] for x in seg).most_common()),
            primary_transitions={f'{a} → {b}': n for (a, b), n in trans.most_common()},
            lost_root_correct=len(lost), new_root_wrong=len(new_wrong), protection_transitions=len(prot), gained_root_correct=len(gained),
            dump=dict(identical_all=cmp_dump.get('identical_all'), key_diffs=len(cmp_dump.get('key_diffs', [])),
                      stability_transitions=cmp_dump.get('stability_transitions')),
            key_diffs_by_product=dict(by_prod.most_common()), verse_key_diffs_without_segmentation_change_by_product=dict(unexpl.most_common()),
            verses_with_key_diffs=len(key_verses), verses_changed_without_own_segmentation_change=len(no_own),
            explained_by_neighbour_segmentation_change=len(neighbour), neighbour_examples=dict(list(neighbour.items())[:10]),
            verses_with_key_diffs_unexplained=len(unexpl_verses),
            unexplained_verse_examples=unexpl_verses[:20])
json.dump(summ, open(os.path.join(OUT, 'summary.json'), 'w'), ensure_ascii=False, indent=1)
for name, data in (('segmentation_changes', seg), ('lost_root_correct', lost), ('new_root_wrong', new_wrong), ('protection_transitions', prot),
                   ('gained_root_correct', gained)):
    json.dump(data, open(os.path.join(OUT, f'{name}.json'), 'w'), ensure_ascii=False, indent=0)
print(json.dumps(summ, ensure_ascii=False, indent=1)[:5000])
