"""tools/morph_reconcile.py <ENGINE.jsonl.gz> <INV.jsonl.gz> <EVENTS.csv> <OUT_DIR> — مصالحة جرد التقشير والصرف (MORPH_COMPLETION_01).

قياس تطوير لا اختبار قبول: QAC مرجع قياسٍ وحده، وقد كُشفت مادته أثناء الجرد.
- الوحدة: الكلمة المحاذاة بكلمة QAC (inv: tools/morph_inventory.py)، ومخرج النظام لها من الواجهة العامة run() (engine: tools/morph_engine_export.py):
  الجذر النهائي = R في وحدة الإغلاق المغلقة لخاناتها «جذع»، للفعل والاسم معاً.
- لكل كلمة **صنفٌ رئيسي واحد** بترتيب أولويةٍ معلن (PRIMARY_ORDER)، فمجموع الأصناف = المقام؛ والأسباب الأخرى حقولٌ إضافية.
- تقسيم QAC المختلف ليس خطأً بذاته: يُقارن بعقد تمثيل SARF (الفعل يُبقي ضمير الفاعل وحرف المضارعة في جذعه).
- تدقيق الحماية: الحماية على الوجه الصحيح (الخانة المحمية = جذع QAC أو جذعه بلواحقه) أم مكتسبةٌ بعد فصلٍ غير مثبت.
- عدم مطابقة HFN في الأفعال يُفصل سببه: تقشير، أو مرشّحات (الجذر الصحيح ليس بينها)، أو مورد (لا فعل في HFN بالجذر والوزن)،
  أو توليد (الفعل في HFN والجذر بين المرشّحات ولم تُطابق قراءة)، مع الزمن والبناء للمجهول وصنف الجذر."""
import csv, gzip, json, os, re, sys
from collections import Counter, defaultdict
ENG, INV, EVENTS, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)
PROTECTED = {'عامل', 'مبني', 'لفظ الجلالة'}


def skel(t):
    t = re.sub('[ً-ٰٟۖ-ࣰۭ-ࣲـ]', '', t or '')
    return t.translate(str.maketrans('ٱأإآؤئىة', 'اااااييه')).replace('ء', '')


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarf.root import hfn_class
HV = defaultdict(set)
for e in csv.DictReader(open(EVENTS, encoding='utf-8')):
    if (e.get('layer') or '').startswith('verb') or e.get('verb'):
        HV[e['root_K']].add(hfn_class(e['form']))

slots = defaultdict(list)
for l in gzip.open(ENG, 'rt', encoding='utf-8'):
    x = json.loads(l)
    slots[f"{x['verse']}:{x['wi']}"].append(x)


def fam(m):
    if not m:
        return None
    s, rs = m['status'], m.get('reason') or ''
    if s in ('accepted', 'ranked', 'not_applicable', 'class_deferred'):
        return s.upper()
    if rs.startswith('لم يثبت بالكتابة أنه فعل، ولا يطابق'):
        return 'D_NOT_PROVEN_NO_HFN_MATCH'
    if rs.startswith('يطابق فعل HFN'):
        return 'D_HFN_EXACT_NOT_PROVEN'
    if rs.startswith('أكثر من جذر أو وزن'):
        return 'D_MULTI_LICENSED'
    if rs.startswith('لا رخصة'):
        return 'D_NO_LICENCE'
    if rs.startswith('قراءة بحرف محذوف'):
        return 'D_DELETED_LETTER_RIVAL'
    return 'D_OTHER'


def keeps_affix(stem, q):
    a, b = skel(stem), skel(q['stem'])
    pre, suf = [skel(x) for x in q['prefixes']], [skel(x) for x in q['suffixes']]
    for i in range(len(pre) + 1):
        for j in range(len(suf) + 1):
            if a == ''.join(pre[len(pre) - i:]) + b + ''.join(suf[:j]):
                return ('P' if i else '') + ('S' if j else '') or 'EXACT'
    return None


PRIMARY_ORDER = ['UNALIGNED', 'PEEL_MULTI_STEM', 'PEEL_VERB_PREFIX_KEPT', 'PEEL_AL_ON_NON_AL', 'PEEL_STEM_DIFF', 'PROTECTION_SUSPECT',
                 'PROTECTED_OK', 'NO_STEM_NO_GOLD_ROOT', 'STEM_NO_GOLD_ROOT', 'ROOT_CORRECT', 'ROOT_CORRECT_FORM_DIFF', 'ROOT_WRONG',
                 'NO_ROOT:<family>']


def classify(r, S):
    q = r['qac']
    stems = [s for s in S if s['type'] == 'جذع']
    prot = [s for s in S if s['type'] in PROTECTED]
    sec = dict(qac_tag=q['tag'], qac_root=q['root'], qac_vf=q['vf'], aspect=q['aspect'], passive=q['passive'], proper=q['proper'],
               slots=[(s['type'], s['text']) for s in S])
    if len(stems) > 1:
        return 'PEEL_MULTI_STEM', sec
    if any(s['type'] == 'أل' for s in S) and not any(skel(p) in ('ال', 'ل') for p in q['prefixes']) and skel(q['stem'])[:2] in ('ال', 'لل'):
        return 'PEEL_AL_ON_NON_AL', sec
    if not stems:
        if not q['root']:
            return 'NO_STEM_NO_GOLD_ROOT', sec
        qs = skel(q['stem']); qsuf = ''.join(skel(x) for x in q['suffixes'])
        ok = any(skel(p['text']) in (qs, qs + qsuf) or (qs + qsuf).startswith(skel(p['text'])) and len(skel(p['text'])) >= len(qs) - 1
                 for p in prot)
        sec['protected'] = [(p['type'], p['text'], p.get('lexicon')) for p in prot]
        return ('PROTECTED_OK' if ok else 'PROTECTION_SUSPECT'), sec
    st = stems[0]
    ka = keeps_affix(st['text'], q)
    sec['peel'] = ka or 'DIFF'
    if ka in ('P', 'PS') and q['tag'] == 'V':
        return 'PEEL_VERB_PREFIX_KEPT', sec
    if ka is None:
        qa = skel(q['stem'])
        sec['peel_note'] = 'QAC_EXTRA_ALIF' if qa == skel(st['text']) + 'ا' else 'DIFF'
        if sec['peel_note'] == 'DIFF':
            return 'PEEL_STEM_DIFF', sec
    if not q['root']:
        return 'STEM_NO_GOLD_ROOT', sec
    u, m = st.get('unit') or {}, st.get('morph')
    R = u.get('R') if u.get('closed') in (True, 'True') else None
    sec.update(final_root=R, unit_P=u.get('P'), unit_F=u.get('F'), morph_family=fam(m), morph_root=(m or {}).get('root'), morph_form=(m or {}).get('form'),
               morph_reason=(m or {}).get('reason'))
    if R:
        if R != q['root']:
            return 'ROOT_WRONG', sec
        if q['tag'] == 'V' and (m or {}).get('form') and m['form'] != q['vf']:
            return 'ROOT_CORRECT_FORM_DIFF', sec
        return 'ROOT_CORRECT', sec
    f = fam(m) or ('NOUN_UNIT_OPEN' if q['tag'] != 'V' else 'VERB_NO_MORPH_RECORD')
    return 'NO_ROOT:' + f, sec


def verb_cause(r, sec, cands):
    q = r['qac']
    if q['root'] not in cands:
        return 'CANDIDATE_GAP'
    if q['vf'] not in HV.get(q['root'], set()):
        return 'RESOURCE_GAP'
    return 'GENERATION_GAP'


inv = [json.loads(l) for l in gzip.open(INV, 'rt', encoding='utf-8')]
rows, prim = [], Counter()
for r in inv:
    if not r.get('aligned'):
        rec = dict(loc=r['loc'], word=r['word'], primary='UNALIGNED')
    else:
        S = slots.get(r['loc'], [])
        p, sec = classify(r, S)
        rec = dict(loc=r['loc'], word=r['word'], primary=p, **sec)
        if p == 'NO_ROOT:D_NOT_PROVEN_NO_HFN_MATCH' and r['qac']['tag'] == 'V':
            cands = set((r['morph'] or [{}])[0].get('cands') or [])
            rec['cause'] = verb_cause(r, sec, cands)
    prim[rec['primary']] += 1
    rows.append(rec)
with gzip.open(os.path.join(OUT, 'per_word.jsonl.gz'), 'wt', encoding='utf-8') as f:
    for x in rows:
        f.write(json.dumps(x, ensure_ascii=False) + '\n')
by_tag = defaultdict(Counter)
for x in rows:
    by_tag[x.get('qac_tag', '-')][x['primary']] += 1
causes = Counter((x['cause'], x['aspect'], x['passive']) for x in rows if x.get('cause'))
summ = dict(denominator_words=len(rows), primary=dict(prim.most_common()), sum_primary=sum(prim.values()), by_qac_tag={k: dict(v.most_common()) for k, v in by_tag.items()},
            verb_no_match_causes={'|'.join(map(str, k)): v for k, v in causes.most_common()}, primary_order=PRIMARY_ORDER)
json.dump(summ, open(os.path.join(OUT, 'summary.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(summ, ensure_ascii=False, indent=1)[:6000])
