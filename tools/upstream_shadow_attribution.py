"""tools/upstream_shadow_attribution.py — تعليل فروق الانتقال الظلي فرقاً فرقاً (SARF_UPSTREAM_CONSUMER_REPAIR_02 §٥).

    python3 tools/upstream_shadow_attribution.py <shadow.jsonl.gz> <snap_base.pkl.gz> <snap_shadow.pkl.gz> <HFN_base> <HFN_shadow> <OUT_PREFIX>

المدخل: فروق tools/upstream_shadow_diff.py (شيفرةٌ واحدة على إصدارين). ولكل كلمةٍ تُجمع سجلّات البيانات التي تغيّرت لها بين الإصدارين، بالمفاتيح
التي يستعملها المحلّل نفسه (قراءة فقط): أحداث (الجذر، الوزن) لوجهها (hfn_class)، وأحداث الكلمة كلها (_plain_vowels)، ولمّات الأسماء
(_lex_key، NOUN_POS)، والجذور المسمّاة في نصّ سبب التأجيل. ثم يُصنَّف كل فرق:

  PROVEN_RECORD           مدخلٌ صرفي (وجه) تغيّرت أحداث مفتاحه هو، أو مفتاحٌ سمّاه سببه — بمعرّفات السجلّات؛ لا رصيد الكلمة
  LINKED_BY_NAMED_RECORD  في قيمة الفرق نفسها سجلٌّ متغيّر مسمّى (معرّفه أو لمّته أو جذره المقتبس): رابطٌ مسمّى، أقوى من المكاني ولا يثبت السببية وحده
  REPRESENTATION_WASL     القيمتان واحدةٌ إذا وُحّدت «ٱ» و«ا» (تمثيل، HFN-D068)
  AGGREGATE_REPRESENTATION تمثيلٌ تجميعي للآية كلها (S، أو مدخل trace لا يحمل سجلاً)
  SPATIAL_WORD            في كلمةٍ تغيّر لها سجلٌّ مثبت، ولا رابط من الفرق نفسه إليه: ارتباطٌ مكاني لا سبب
  SPATIAL_VERSE           في آيةٍ فيها تغيّرٌ مثبت في كلمةٍ أخرى
  UNRESOLVED              لا سجلّ ولا رابط
والاكتمال COMPLETE إن لم يبق UNRESOLVED، وإلا PARTIAL. ولا يُحكم على فرقٍ بالصواب.
"""
import collections, csv, gzip, json, os, pickle, re, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarf.root import hfn_class, _plain_vowels
from sarf.cells import _lex_key, NOUN_POS

CLASSES = ('PROVEN_RECORD', 'LINKED_BY_NAMED_RECORD', 'REPRESENTATION_WASL', 'AGGREGATE_REPRESENTATION', 'SPATIAL_WORD', 'SPATIAL_VERSE', 'UNRESOLVED')


def load(path):
    ev = {e['event_id']: e for e in csv.DictReader(open(os.path.join(path, 'events.csv'), encoding='utf-8'))}
    by_key, whole, lu = collections.defaultdict(dict), collections.defaultdict(dict), collections.defaultdict(dict)
    for e in ev.values():
        by_key[(e['root_K'], hfn_class(e['form']))][e['event_id']] = (e['verb'], e['form'], e.get('transitivity'), e.get('masdar'), e.get('event_review_v36', '')[:20])
        whole[_plain_vowels(e['verb'])][e['event_id']] = e['verb']
    for x in csv.DictReader(open(os.path.join(path, 'lexical_units.csv'), encoding='utf-8')):
        if x['pos_ar'] in NOUN_POS and x['event_id'] in ev:
            lu[_lex_key(x['lemma'])][x['lu_id']] = (x['lemma'], x['pos_ar'], x['pattern'])
    return by_key, whole, lu, {e['root_K']: e['event_id'] for e in ev.values()}


def roots_named(t):
    """الجذور المسمّاة صراحةً في نصّ القيمة: بين علامتي اقتباس ('رحمت')، أو «الجذر «X»»، أو قائمة بعد «HFN:»، أو «X (I)»"""
    out = set(re.findall(r"'([\u0621-\u064A]{3,4})'", t)) | set(re.findall(r'الجذر «([\u0621-\u064A]{3,4})»', t))
    out |= set(re.findall(r'([\u0621-\u064A]{3,4}) \((?:I{1,3}|IV|V|VI{1,3}|IX|X|Q[IV]+)\)', t))
    for m in re.findall(r'HFN: ([\u0621-\u064A، ]+)', t):
        out |= {x.strip() for x in m.split('،') if 3 <= len(x.strip()) <= 4}
    return out


def changed(a, b):
    """→ معرّفات السجلّات المتغيّرة بين قاموسين، والرموز النصية المرتبطة بها (المعرّفات والرسوم في الطرفين)"""
    ids = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    toks = set()
    for k in ids:
        toks.add(k)
        for v in (a.get(k), b.get(k)):
            if v:
                for t in (v if isinstance(v, (tuple, list)) else (v,)):
                    if isinstance(t, str) and len(t) > 2 and not t.startswith(('فَعَ', 'أَفْ', 'تَفَ', 'افْ', 'اسْ', 'انْ')):
                        toks.add(t)
    return ids, toks


def main():
    D, B0, B1, H0, H1, OUT = sys.argv[1:7]
    S0, S1 = pickle.load(gzip.open(B0)), pickle.load(gzip.open(B1))
    K0, W0, L0, R0 = load(H0)
    K1, W1, L1, R1 = load(H1)
    # روابط عامة: الجذور الجديدة في مجموعة جذور الإصدار (تظهر في نصوص الرخص بين علامتي اقتباس)، ولمّات الأسماء المتغيّرة بأيّ مفتاح
    NEWROOT = {r_: R1[r_] for r_ in set(R1) - set(R0)}
    ROOTCHG = collections.defaultdict(list)
    for k in set(K0) | set(K1):
        ids, _ = changed(K0.get(k, {}), K1.get(k, {}))
        if ids:
            ROOTCHG[k[0]] += ids
    LULEM = collections.defaultdict(set)
    for k in set(L0) | set(L1):
        for i in set(L0.get(k, {})) | set(L1.get(k, {})):
            if L0.get(k, {}).get(i) != L1.get(k, {}).get(i):
                for v_ in (L0.get(k, {}).get(i), L1.get(k, {}).get(i)):
                    if v_:
                        LULEM[v_[0]].add(i)
    diffs = [json.loads(l) for l in gzip.open(D, 'rt', encoding='utf-8')]
    # سجلّات كل كلمة: من مداخلها الصرفية (مفاتيح الوجه، والجذور المسمّاة في السبب) ومن نصوص وحداتها (الكلمة كلها، ولمّات الأسماء)
    word_recs = collections.defaultdict(lambda: dict(ids=set(), toks=set(), kinds=set()))
    face_of = {}
    entry_recs = collections.defaultdict(lambda: dict(ids=set(), keys=set(), faces=set()))
    for v in S0:
        for side, S in ((0, S0), (1, S1)):
            a = (S.get(v) or {}).get('a', {})
            for mi, m in enumerate(a.get('morph', [])):
                w = m.get('word_index')
                keys = {(m.get('root'), m.get('form_class'))} if m.get('root') else set()
                for r_, c_ in re.findall(r'(\S{3,4}) \((I{1,3}|IV|V|VI{1,3}|IX|X|Q[IV]+)\)', str(m.get('reason') or '')):
                    keys.add((r_, c_))
                for k in keys:
                    ids, toks = changed(K0.get(k, {}), K1.get(k, {}))
                    if ids:
                        word_recs[(v, w)]['ids'] |= set(ids)
                        word_recs[(v, w)]['toks'] |= toks
                        word_recs[(v, w)]['kinds'].add(f'EVENTS_OF_KEY {k[0]}/{k[1]}')
                        # سجلّات مدخل الوجه نفسه (بموضعه في الطرفين): مفتاحاه وما سمّاه سببه — لا رصيد الكلمة كلها
                        e_ = entry_recs[(v, mi)]
                        e_['ids'] |= set(ids)
                        e_['keys'].add(f'{k[0]}/{k[1]}')
                        e_['faces'].add(m.get('analysis_id'))
                if side == 0:
                    face_of.setdefault((v, w), set()).add(m.get('analysis_id'))
            for uk, u in (S.get(v) or {}).get('units', {}).items():
                mm = re.match(r'\((\d+), (\d+)\)', uk)
                if not mm or not u.get('text'):
                    continue
                w = int(mm.group(1))
                for key_fn, A_, B_, kind in ((_plain_vowels, W0, W1, 'WHOLE_WORD_EVENTS'), (_lex_key, L0, L1, 'NOUN_LEXICAL_UNITS')):
                    k = key_fn(u['text'])
                    ids, toks = changed(A_.get(k, {}), B_.get(k, {}))
                    if ids:
                        word_recs[(v, w)]['ids'] |= set(ids)
                        word_recs[(v, w)]['toks'] |= toks
                        word_recs[(v, w)]['kinds'].add(f'{kind} «{u["text"]}»')
    # المرور الأول: رابطٌ نصّي عام من الفرق نفسه إلى سجلٍّ متغيّر (جذرٌ جديد مقتبس، أو قيمةٌ هي لمّةُ اسمٍ تغيّرت)
    for d in diffs:
        sb, ss = str(d['base']), str(d['shadow'])
        hits = {f"NEW_ROOT {r_}": e_ for r_, e_ in NEWROOT.items() if f"'{r_}'" in sb or f"'{r_}'" in ss}
        for r_ in roots_named(sb + ' ' + ss) & set(ROOTCHG):
            hits[f'ROOT_EVENTS_CHANGED {r_}'] = '|'.join(ROOTCHG[r_][:20])
        for lem_, ids_ in LULEM.items():
            if f'«{lem_}»' in sb or f'«{lem_}»' in ss:
                hits[f'NOUN_LU_LEMMA «{lem_}»'] = '|'.join(sorted(ids_))
        for t in (d['base'], d['shadow']):
            if isinstance(t, str) and t in LULEM:
                hits[f'NOUN_LU_LEMMA «{t}»'] = '|'.join(sorted(LULEM[t]))
        if hits:
            r = word_recs[(d['verse'], d.get('word_index'))]
            r['ids'] |= set('|'.join(hits.values()).split('|'))
            r['kinds'] |= set(hits)
            r['toks'] |= {k.split(' ', 1)[1].strip('«»') for k in hits}
    verse_has = {v for (v, w), r in word_recs.items() if r['ids']}
    C = collections.Counter()
    by_cls_path = collections.Counter()
    with gzip.open(OUT + '.jsonl.gz', 'wt', encoding='utf-8') as f:
        for d in diffs:
            v, w, p = d['verse'], d.get('word_index'), d['path']
            top = p.split('/')[0]
            sb, ss = str(d['base']), str(d['shadow'])
            rec = word_recs.get((v, w))
            cls, ev = 'UNRESOLVED', None
            mi = int(p.split('/')[2]) if p.startswith('a/morph/') and p.split('/')[2].isdigit() else None
            er = entry_recs.get((v, mi)) if mi is not None else None
            if er and er['ids']:
                # مثبتٌ للوجه: سجلٌّ متغيّر لمفتاح مدخل الوجه نفسه (جذره ووزنه، أو مفتاحٌ سمّاه سببه) في الموضع نفسه من الطرفين
                cls, ev = 'PROVEN_RECORD', dict(records=sorted(er['ids'])[:20], face_keys=sorted(er['keys']), faces=sorted(x for x in er['faces'] if x))
            elif rec and rec['ids'] and any(t in sb or t in ss for t in rec['toks']):
                hit = sorted(t for t in rec['toks'] if t in sb or t in ss)[:6]
                cls, ev = 'LINKED_BY_NAMED_RECORD', dict(records=sorted(rec['ids'])[:20], tokens=hit, via=sorted(rec['kinds']))
            elif p.startswith('a/morph/') and rec and rec['ids']:
                # سجلّ الكلمة لا مدخل الوجه: ارتباطٌ مكاني (لا يُسمّى مثبتاً للوجه)
                cls, ev = 'SPATIAL_WORD', dict(records_in_word=sorted(rec['ids'])[:10], note='سجلٌّ لكلمة الوجه لا لمفتاح مدخله')
            elif sb.replace('ٱ', 'ا') == ss.replace('ٱ', 'ا') and sb != ss:
                cls, ev = 'REPRESENTATION_WASL', dict(decision='HFN-D068 (release_v44): همزة الوصل «ٱ» في حقول الكلمات')
            elif top in ('S', 'trace'):
                cls = 'AGGREGATE_REPRESENTATION'
            elif rec and rec['ids']:
                cls, ev = 'SPATIAL_WORD', dict(records_in_word=sorted(rec['ids'])[:10])
            elif v in verse_has:
                cls = 'SPATIAL_VERSE'
            C[cls] += 1
            by_cls_path[(cls, '/'.join(x for x in p.split('/')[:4] if not x.isdigit() and not x.startswith('(')))] += 1
            f.write(json.dumps(dict(verse=v, word_index=w, analysis_ids_base=sorted(x for x in face_of.get((v, w), set()) if x), path=p, base=d['base'],
                                    shadow=d['shadow'], previous_reasons=d.get('reasons'), attribution=cls, evidence=ev), ensure_ascii=False, default=str) + '\n')
    prev_un = sum(1 for d in diffs if d.get('reasons') == ['UNATTRIBUTED'])
    causal = C.get('PROVEN_RECORD', 0) + C.get('REPRESENTATION_WASL', 0)
    summ = dict(differences=len(diffs), classes={k: C.get(k, 0) for k in CLASSES},
                classification_completeness='COMPLETE' if not C.get('UNRESOLVED') else 'PARTIAL',
                causal_explanation_completeness='COMPLETE' if causal == len(diffs) else 'PARTIAL',
                causally_explained=causal, not_causally_explained=len(diffs) - causal,
                completeness_definitions=dict(classification='كل فرقٍ في صنفٍ غير UNRESOLVED',
                                              causal='كل فرقٍ PROVEN_RECORD (سجلٌّ لمفتاح الوجه نفسه) أو REPRESENTATION_WASL؛ والمسمّى والمكاني والتجميعي ليست تعليلاً سببياً'),
                completeness='PARTIAL' if (C.get('UNRESOLVED') or causal != len(diffs)) else 'COMPLETE',
                previous_unattributed=prev_un, top_paths_by_class={f'{a} | {b}': n for (a, b), n in by_cls_path.most_common(60)},
                note='SPATIAL_* ارتباطٌ مكاني لا سبب؛ وPROVEN_RECORD سجلٌّ لمفتاح الوجه نفسه؛ وLINKED_BY_NAMED_RECORD سجلٌّ مسمّى في الفرق؛ ولا يُحكم على فرقٍ بالصواب')
    json.dump(summ, open(OUT + '.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(dict(differences=len(diffs), classes=summ['classes'], classification=summ['classification_completeness'],
                          causal=summ['causal_explanation_completeness'], causally_explained=causal, previous_unattributed=prev_un), ensure_ascii=False))


if __name__ == '__main__':
    main()
