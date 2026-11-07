#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/root_wazn_bench.py — اختبار الجذر والوزن الأعمى على حزمة MORPH_TESTSET (SARF_ROOT_WAZN_BENCHMARK_01).

لا تدخل الحزمة git (مشتقّة من HFN)، ولا تُعدَّل؛ والأداة تقرأها من مسارٍ يُمرَّر. والمحلّل لا يرى إلا (id، word).

    python3 tools/root_wazn_bench.py audit       <مجلد الحزمة> <out>           تدقيق البنية والأعداد والمقامات
    python3 tools/root_wazn_bench.py exposure    <مجلد الحزمة> <out>           التعرّض والتداخل بين dev وtest والعيّنة
    python3 tools/root_wazn_bench.py faces       <مجلد الحزمة> <out>           الأوجه المرجعية لكل كلمة (جذر+وزن مقترنان)
    python3 tools/root_wazn_bench.py blind-input <مجلد الحزمة> <out.tsv> --split dev     (id، word) وحدهما؛ test ممنوع
    PYTHONHASHSEED=0 python3 tools/root_wazn_bench.py run <in.tsv> <out.jsonl> [--pos-assisted <pos.tsv>]
    python3 tools/root_wazn_bench.py compare     <مجلد الحزمة> <analysis.jsonl> <out> [--corrections c.tsv]

المساران في run:
  A_LEXICAL_MORPH  محرّك الصرف على الكلمة المعجمية بلا سياق: morph (قوالب الفعل برخصة HFN)، وcandidates(any_pos)،
                   وparticiple_analyses (قوالب اسمي الفاعل والمفعول برخصة HFN)، وlex_index (استرجاع مدخل الاسم من HFN)،
                   والحماية الدستورية. لكل وجهٍ مصدره: RULE (قالب برخصة) أو RETRIEVAL (مطابقة مدخل)
  B_PUBLIC         واجهة المحلّل العامة: analyze ← sentence_geo ← unit_features، ومستوى ما بلغه وسبب تأجيله
والمسار POS_ASSISTED_DIAGNOSTIC (اختياري، منفصل): morph بصنف «فعل» معطى، لما صنفه في المرجع فعل.
"""
import argparse, collections, csv, hashlib, json, math, os, re, sys, unicodedata

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_FIELDS = ('root', 'root_spaced', 'root_type', 'pos', 'wazn', 'surface_pattern', 'wazn_status', 'verb', 'verb_form', 'source',
              'evidence', 'event_id')
COLS = ('id', 'split', 'root', 'root_spaced', 'root_type', 'word', 'pos', 'wazn', 'surface_pattern', 'wazn_status', 'verb',
        'verb_form', 'source', 'evidence', 'event_id', 'rank')
ROOT_TYPES = {'سالم', 'مهموز', 'مثال', 'أجوف', 'ناقص', 'لفيف', 'مضعّف', 'رباعي'}
POS = {'فعل ماضٍ', 'مصدر', 'اسم فاعل', 'اسم مفعول', 'صفة مشبّهة', 'صيغة مبالغة', 'صفة (فَعِيل/فَعُول)'}
STATUSES = {'VERIFIED', 'INVENTORY', 'WEAK_SUBST', 'HFN_FORM', 'UNRESOLVED', 'FORM_MISMATCH'}
TASHKEEL = set('ًٌٍَُِّْٰ')
# تحويلٌ معلن ومختبر من تسمية الباب إلى ميزانٍ عربي (لا يقارن «IV» بوزنٍ عربي مباشرة)؛ والباب الأول عائلةٌ لا ميزانٌ واحد
FORM_CLASS_TO_WAZN = {'I': {'فَعَلَ', 'فَعِلَ', 'فَعُلَ'}, 'II': {'فَعَّلَ'}, 'III': {'فَاعَلَ'}, 'IV': {'أَفْعَلَ'},
                      'V': {'تَفَعَّلَ'}, 'VI': {'تَفَاعَلَ'}, 'VII': {'انْفَعَلَ', 'اِنْفَعَلَ'}, 'VIII': {'افْتَعَلَ', 'اِفْتَعَلَ'},
                      'IX': {'افْعَلَّ', 'اِفْعَلَّ'}, 'X': {'اسْتَفْعَلَ', 'اِسْتَفْعَلَ'}, 'QI': {'فَعْلَلَ'},
                      'QII': {'تَفَعْلَلَ'}, 'QIII': {'افْعَنْلَلَ'}, 'QIV': {'افْعَلَلَّ'}}
PARTICIPLE_WAZN = {('I', 'فاعل'): 'فَاعِل', ('I', 'مفعول'): 'مَفْعُول'}


def nfc(s):
    return unicodedata.normalize('NFC', s or '')


def cmp_form(s):
    """نسخة المقارنة: NFC، وألف الوصل المكسورة في أول الميزان دون كسرتها (اِفْتَعَلَ = افْتَعَلَ: فرق ترميزٍ للهمزة الوصلية)؛
    ولا تجريد للحركات، ولا تسوية للواو والياء أو الهمزات"""
    s = nfc(s).strip()
    s = re.sub(r'\s*\(.*\)$', '', s)                    # «أَفَالَ (أفعل أجوف)» ← «أَفَالَ»
    if s.startswith('اِ'):
        s = 'ا' + s[2:]
    return s


def read_tsv(p):
    with open(p, encoding='utf-8') as f:
        r = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE)
        head = next(r)
        return head, [dict(zip(head, row)) for row in r]


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def wilson_low(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    return round((p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n), 4)


# ---------- التدقيق ----------
def audit(pkg, out):
    rep = dict(files={}, checks={}, counts={}, denominators={})
    for f in sorted(os.listdir(pkg)):
        p = os.path.join(pkg, f)
        if os.path.isfile(p):
            rep['files'][f] = dict(sha256=sha(p), lines=sum(1 for _ in open(p, encoding='utf-8')))
    head, rows = read_tsv(os.path.join(pkg, 'testset_all.tsv'))
    ids = [r['id'] for r in rows]
    by = {r['id']: r for r in rows}
    c = rep['checks']
    c['columns'] = dict(expected=list(COLS), found=head, ok=tuple(head) == COLS)
    c['id_unique'] = dict(ok=len(ids) == len(set(ids)), duplicates=[k for k, n in collections.Counter(ids).items() if n > 1])
    bad_sp = [r['id'] for r in rows if ' '.join(r['root'].replace(' ', '')) != r['root_spaced']]
    c['root_spaced_consistent'] = dict(ok=not bad_sp, bad=bad_sp[:50], n_bad=len(bad_sp))
    c['rank_all_candidate'] = dict(ok=all(r['rank'] == 'CANDIDATE' for r in rows),
                                   values=dict(collections.Counter(r['rank'] for r in rows)))
    c['split_values'] = dict(collections.Counter(r['split'] for r in rows))
    roots_split = collections.defaultdict(set)
    for r in rows:
        roots_split[r['root']].add(r['split'])
    c['split_by_root_disjoint'] = dict(ok=all(len(v) == 1 for v in roots_split.values()),
                                       roots_in_both=sorted(k for k, v in roots_split.items() if len(v) > 1))
    c['pos_values'] = dict(collections.Counter(r['pos'] for r in rows))
    c['pos_unexpected'] = sorted(set(c['pos_values']) - POS)
    rt_bad = sorted({r['root_type'] for r in rows if not set(r['root_type'].split('+')) <= ROOT_TYPES})
    c['root_type_unexpected'] = rt_bad
    c['wazn_status_values'] = dict(collections.Counter(r['wazn_status'] for r in rows))
    c['wazn_status_unexpected'] = sorted(set(c['wazn_status_values']) - STATUSES)
    empty = {k: sum(1 for r in rows if not r[k]) for k in COLS}
    c['empty_by_column'] = empty
    c['empty_wazn_matches_status'] = dict(
        ok=all((not r['wazn']) == (r['wazn_status'] in ('UNRESOLVED', 'FORM_MISMATCH')) for r in rows),
        bad=[r['id'] for r in rows if (not r['wazn']) != (r['wazn_status'] in ('UNRESOLVED', 'FORM_MISMATCH'))][:50])
    nonnfc = [r['id'] for r in rows if any(r[k] != nfc(r[k]) for k in ('word', 'wazn', 'surface_pattern', 'verb', 'verb_form'))]
    c['nfc'] = dict(n_not_nfc=len(nonnfc), examples=nonnfc[:30])
    undiac = [r['id'] for r in rows if not (set(r['word']) & TASHKEEL)]
    c['word_without_any_tashkeel'] = dict(n=len(undiac), examples=undiac[:30])
    # الجذر في الكلمة: كل حرف أصلي ظاهر في الكلمة (معياراً تقريبياً للاتساق، لا حكماً)؛ الهمزة بصورها، والمعتلّ قد يُقلب
    HAMZ = set('ءأإؤئآ')

    def root_letters_visible(r):
        w = [ch for ch in r['word'] if ch not in TASHKEEL]
        miss = []
        for L in r['root'].replace(' ', ''):
            if L == 'ء' and set(w) & HAMZ or L in w:
                continue
            miss.append(L)
        return miss
    inv = []
    for r in rows:
        m = root_letters_visible(r)
        if m and not set(m) <= set('وي'):
            inv.append(dict(id=r['id'], word=r['word'], root=r['root'], missing=''.join(m)))
    c['root_letters_not_visible_non_weak'] = dict(n=len(inv), examples=inv[:60])
    # الملفات الفرعية
    sub = {}
    for f, cond in (('dev.tsv', lambda r: r['split'] == 'dev' and r['wazn']), ('test.tsv', lambda r: r['split'] == 'test' and r['wazn']),
                    ('unresolved_wazn.tsv', lambda r: not r['wazn'])):
        h2, r2 = read_tsv(os.path.join(pkg, f))
        exp = [r['id'] for r in rows if cond(r)]
        same = all(by.get(x['id']) == x for x in r2)
        sub[f] = dict(rows=len(r2), expected_from_all=len(exp), ids_equal=sorted(x['id'] for x in r2) == sorted(exp), rows_identical=same)
    c['subfiles'] = sub
    h3, vm = read_tsv(os.path.join(pkg, 'verb_form_mismatch.tsv'))
    fm = [r for r in rows if r['wazn_status'] == 'FORM_MISMATCH']
    c['verb_form_mismatch'] = dict(rows=len(vm), form_mismatch_rows=[r['id'] for r in fm],
                                   events_match=sorted(x['event_id'] for x in vm) == sorted(r['event_id'] for r in fm))
    st = json.load(open(os.path.join(pkg, 'STATS.json'), encoding='utf-8'))
    with_w = [r for r in rows if r['wazn']]
    counts = dict(rows=len(rows), roots=len({r['root'] for r in rows}), with_wazn=len(with_w),
                  dev_with_wazn=sum(1 for r in with_w if r['split'] == 'dev'), test_with_wazn=sum(1 for r in with_w if r['split'] == 'test'),
                  without_wazn=len(rows) - len(with_w), unresolved=c['wazn_status_values'].get('UNRESOLVED', 0),
                  form_mismatch=c['wazn_status_values'].get('FORM_MISMATCH', 0),
                  dev_all=sum(1 for r in rows if r['split'] == 'dev'), test_all=sum(1 for r in rows if r['split'] == 'test'))
    expected = dict(rows=20581, roots=5443, with_wazn=19218, dev_with_wazn=15431, test_with_wazn=3787, without_wazn=1363,
                    unresolved=1361, form_mismatch=2)
    rep['counts'] = dict(found=counts, expected=expected, match={k: counts[k] == v for k, v in expected.items()})
    rt_with = collections.Counter(r['root_type'] for r in with_w)
    rt_all = collections.Counter(r['root_type'] for r in rows)
    pos_all = collections.Counter(r['pos'] for r in rows)
    rep['denominators'] = dict(
        by_root_type_STATS=dict(value=st['by_root_type'], denominator='الصفوف ذات الوزن (19,218)' if dict(rt_with) == st['by_root_type']
                                else ('جميع الصفوف (20,581)' if dict(rt_all) == st['by_root_type'] else 'غير مطابق لأيٍّ منهما'),
                                matches_with_wazn=dict(rt_with) == st['by_root_type'], matches_all=dict(rt_all) == st['by_root_type']),
        by_pos_STATS=dict(value=st['by_pos'], denominator='جميع الصفوف (20,581)' if dict(pos_all) == st['by_pos'] else 'غير مطابق',
                          matches_all=dict(pos_all) == st['by_pos']),
        by_root_type_all_rows=dict(rt_all), by_pos_with_wazn=dict(collections.Counter(r['pos'] for r in with_w)))
    json.dump(rep, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = all(rep['counts']['match'].values()) and c['id_unique']['ok'] and c['root_spaced_consistent']['ok'] and \
        c['rank_all_candidate']['ok'] and c['split_by_root_disjoint']['ok'] and all(v['ids_equal'] and v['rows_identical'] for v in sub.values())
    print('PACKAGE_STRUCTURALLY_VALID' if ok else 'PACKAGE_STRUCTURAL_ISSUES', json.dumps(rep['counts']['match'], ensure_ascii=False))
    return rep


# ---------- التعرّض ----------
def exposure(pkg, out):
    _, rows = read_tsv(os.path.join(pkg, 'testset_all.tsv'))
    _, s60 = read_tsv(os.path.join(pkg, 'sample60.tsv'))
    by = {r['id']: r for r in rows}
    dev_roots = {r['root'] for r in rows if r['split'] == 'dev'}
    test_roots = {r['root'] for r in rows if r['split'] == 'test'}
    w_dev = collections.defaultdict(set)
    w_test = collections.defaultdict(set)
    for r in rows:
        (w_dev if r['split'] == 'dev' else w_test)[nfc(r['word'])].add(r['root'])
    shared_words = sorted(set(w_dev) & set(w_test))
    shared_diff_root = [w for w in shared_words if w_dev[w] != w_test[w]]
    s60_test = [x['id'] for x in s60 if by.get(x['id'], {}).get('split') == 'test']
    s60_test_roots = sorted({by[i]['root'] for i in s60_test})
    rows_of_those_roots_in_test_tsv = [r['id'] for r in rows if r['split'] == 'test' and r['wazn'] and r['root'] in s60_test_roots]
    rows_of_those_roots_all_test = [r['id'] for r in rows if r['split'] == 'test' and r['root'] in s60_test_roots]
    shared_test_ids = sorted(r['id'] for r in rows if r['split'] == 'test' and nfc(r['word']) in set(shared_words))
    exposed_test = set(rows_of_those_roots_all_test) | set(shared_test_ids)
    rep = dict(
        shared_roots_dev_test=sorted(dev_roots & test_roots),
        shared_words_with_wazn=dict(n=len({nfc(r['word']) for r in rows if r['split'] == 'dev' and r['wazn']} &
                                          {nfc(r['word']) for r in rows if r['split'] == 'test' and r['wazn']}),
                                    denominator='صفوف dev.tsv وtest.tsv (ذات الوزن)'),
        shared_words=dict(n=len(shared_words), with_different_roots=len(shared_diff_root), denominator='كل الصفوف (ومنها بلا وزن)',
                          list=[dict(word=w, dev_roots=sorted(w_dev[w]), test_roots=sorted(w_test[w])) for w in shared_words]),
        sample60=dict(rows=len(s60), test_rows=len(s60_test), test_ids=s60_test, test_roots=s60_test_roots,
                      test_tsv_rows_of_those_roots=len(rows_of_those_roots_in_test_tsv),
                      all_test_rows_of_those_roots=len(rows_of_those_roots_all_test)),
        partitions=dict(
            DEVELOPMENT=dict(n=sum(1 for r in rows if r['split'] == 'dev'), use='تطوير وتشخيص (هذه الجولة)'),
            TEST_EXPOSED_SAMPLE_ROOTS=dict(n=len(rows_of_those_roots_all_test), type='عُرضت جذورها في عيّنة الستين مع أحكامها (تعرّضٌ بالقراءة)',
                                           ids=rows_of_those_roots_all_test),
            TEST_SHARED_WORD_WITH_DEV=dict(n=len(shared_test_ids), type='لفظها مشكولاً في dev بجذرٍ آخر', ids=shared_test_ids),
            TEST_UNEXPOSED=dict(n=sum(1 for r in rows if r['split'] == 'test' and r['id'] not in exposed_test),
                                type='لم تُقرأ صفوفها في هذه الجولة إلا بالتدقيق الآلي البنيوي؛ ولم يُشغَّل عليها المحلّل')),
        exposure_types=dict(AUTOMATED_STRUCTURAL_AUDIT='كل الصفوف (أعداد وحقول) بلا استعمالٍ في قاعدة',
                            READ_BY_AGENT='صفوف العينة والصفوف المسمّاة في التكليف',
                            USED_FOR_RULE_CHANGE='لا شيء في هذه الجولة (المحلّل لم يُعدَّل)'),
        heldout_inference='NOT_RUN')
    json.dump(rep, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"جذور مشتركة {len(rep['shared_roots_dev_test'])}، كلمات مشتركة ذات وزن {rep['shared_words_with_wazn']['n']}، وفي كل الصفوف {len(shared_words)} (بجذور مختلفة {len(shared_diff_root)})، "
          f"عيّنة: {len(s60_test)} من test، جذورها {len(s60_test_roots)} ← {len(rows_of_those_roots_in_test_tsv)} صفاً في test.tsv")
    return rep


# ---------- الأوجه المرجعية ----------
def faces(pkg, out, corrections=None):
    _, rows = read_tsv(os.path.join(pkg, 'testset_all.tsv'))
    corr = load_corrections(corrections)
    g = collections.defaultdict(list)
    for r in rows:
        g[nfc(r['word'])].append(dict(word=r['word'], root=r['root'], wazn=r['wazn'], pos=r['pos'], analysis_id=r['id'],
                                      split=r['split'], wazn_status=r['wazn_status'],
                                      review_status=row_review_status(r['id'], corr)))
    multi = {w: v for w, v in g.items() if len({(x['root'], x['wazn']) for x in v}) > 1}
    rep = dict(words=len(g), multi_face_words=len(multi),
               multi_root_words=sum(1 for v in multi.values() if len({x['root'] for x in v}) > 1),
               cross_split=sum(1 for v in multi.values() if len({x['split'] for x in v}) > 1),
               groups=[dict(word=w, faces=v, kind=('TEST_INCLUDED' if any(x['split'] == 'test' for x in v) else 'DEV_ONLY'),
                            status='MULTIPLE_UNREVIEWED') for w, v in sorted(multi.items())])
    json.dump(rep, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"كلمات {rep['words']}، متعددة الأوجه {rep['multi_face_words']} (متعددة الجذر {rep['multi_root_words']}، عابرة للقسمين {rep['cross_split']})")
    return rep


# ---------- التصحيحات ----------
CORR_COLS = ('row_id', 'field', 'original_value', 'proposed_value', 'reason', 'source_reference', 'reviewer', 'review_status', 'revision_id')
REVIEW_STATES = ('REVIEWED_ACCEPTED', 'REVIEW_REQUIRED', 'DISPUTED', 'UNRESOLVED')


def load_corrections(p):
    if not p or not os.path.exists(p):
        return []
    _, rows = read_tsv(p)
    for r in rows:
        assert r['review_status'] in REVIEW_STATES, r
    return rows


def row_review_status(rid, corr):
    st = [c['review_status'] for c in corr if c['row_id'] == rid]
    if not st:
        return 'UNREVIEWED'
    for s in ('DISPUTED', 'REVIEW_REQUIRED', 'UNRESOLVED', 'REVIEWED_ACCEPTED'):
        if s in st:
            return s


# ---------- المدخل الأعمى ----------
def blind_input(pkg, out, split):
    if split != 'dev':
        raise SystemExit('RUN_HELDOUT_INFERENCE = NO: لا يُبنى مدخلٌ أعمى لقسم الاختبار في هذه الجولة')
    _, rows = read_tsv(os.path.join(pkg, 'testset_all.tsv'))
    with open(out, 'w', encoding='utf-8') as f:
        f.write('id\tword\n')
        for r in rows:
            if r['split'] == split:
                f.write(f"{r['id']}\t{r['word']}\n")
    print(f'كُتب {out}: (id، word) وحدهما')


# ---------- التشغيل ----------
def _analyze_word(word, pos_assisted=False):
    from sarf.root import morph, candidates, hfn
    from sarf.affix import stem_info
    from sarf.cells import participle_analyses, cells_of, lex_index, _lex_key
    from sarf.protected import protected
    out = dict(word=word)
    prot = protected(word)
    out['protected'] = dict(cls=prot.get('cls'), identity=prot.get('identity'), ambiguous=prot.get('ambiguous'),
                            root_status=prot.get('root_status')) if prot else None
    faces_ = []
    # الفعل: قوالب الماضي برخصة HFN (morph)؛ وما لم يثبت أنه فعل يُرخَّص بمطابقة فعل HFN حرفاً وحركة (استرجاع)
    m = morph(word)
    if m is not None:
        out['morph'] = dict(status=m.get('status'), root=m.get('root'), form_class=m.get('form_class'), level=m.get('level'),
                            reason=m.get('reason'), root_status=m.get('root_status'))
        for x in m.get('licensed') or []:
            faces_.append(dict(root=x['root'], wazn=cmp_form(x['hfn_form']), form_class=x['form_class'], kind='فعل',
                               source='RULE+RETRIEVAL:verb_template_licensed_by_HFN', evidence=x['event_id'], verb=x['verb']))
    else:
        out['morph'] = None
    try:
        cand = candidates(word, any_pos=True)
    except Exception as e:                       # لا يُخفى العطل
        cand, out['candidates_error'] = [], repr(e)
    out['template_candidates'] = [dict(root=r, form_class=c) for r, c in cand]
    try:
        pa = participle_analyses(cells_of(word, 'B'))
    except Exception as e:
        pa, out['participle_error'] = [], repr(e)
    for p in pa:
        root, cls, kind = p[0], p[1], p[2]
        faces_.append(dict(root=root, wazn=PARTICIPLE_WAZN.get((cls, kind)), form_class=cls, kind='اسم ' + kind,
                           source='RULE:participle_template_licensed_by_HFN', evidence=p[5] if len(p) > 5 else None))
    for (root, pos, pattern, lu, lemma) in lex_index().get(_lex_key(word), []):
        faces_.append(dict(root=root, wazn=None, verb_pattern=cmp_form(pattern), kind=pos, source='RETRIEVAL:hfn_lexical_unit',
                           evidence=lu, lemma=lemma))
    uniq, seen = [], set()
    for f in faces_:
        k = (f['root'], f.get('wazn'), f['kind'], f.get('form_class'), f.get('verb_pattern'))
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    for i, f in enumerate(uniq):
        f['candidate_id'] = f'C{i + 1}'
    out['faces'] = uniq
    roots = sorted({f['root'] for f in uniq})
    # المستوى: الحماية، أو جذرٌ مثبت (morph مقبول)، أو مرشّحون، أو لا شيء؛ ولا يُختار من المرشّحين بلا دليل
    if prot and not prot.get('ambiguous'):
        out['level'], out['reason'] = 'PROTECTED', 'CONSTITUTIONAL_PROTECTED_CLASS'
    elif m is not None and m.get('status') == 'accepted':
        out['level'] = 'ROOT_PROVEN'
    elif uniq:
        out['level'] = 'CANDIDATES_ONLY'
        out['reason'] = (m or {}).get('reason') or 'مرشّحون بلا إثبات صنف ولا سياق'
    else:
        out['level'] = 'NO_CANDIDATE'
        out['reason'] = (m or {}).get('reason') or 'لا قالب ولا مدخل يطابق'
    if out['level'] == 'ROOT_PROVEN':
        lw = sorted({cmp_form(x['hfn_form']) for x in m.get('licensed') or [] if x['root'] == m.get('root') and x.get('hfn_form')})
        out['proven'] = dict(root=m.get('root'), form_class=m.get('form_class'),
                             wazn=lw or sorted(FORM_CLASS_TO_WAZN.get(m.get('form_class'), set())),
                             wazn_source='hfn_form' if lw else 'FORM_CLASS_FAMILY')
    else:
        out['proven'] = None
    out['candidate_roots'] = roots
    if pos_assisted:
        mv = morph(word, dict(stem_info(word), pos='verb'))
        out['pos_assisted'] = None if mv is None else dict(status=mv.get('status'), root=mv.get('root'), form_class=mv.get('form_class'),
                                                           reason=mv.get('reason'))
    return out


def _public(word, CAT):
    from sarf.analyze import analyze
    from sarf.algebra import sentence_geo, Trace
    from sarf.features import unit_features
    from sarf import quran_source
    a = analyze(CAT, word, 'auto')
    S, U = sentence_geo(a, 'B', Trace())
    F = unit_features(a, U)
    us = []
    for uid, G in U.items():
        f = F.get(uid) if isinstance(F, dict) else None
        us.append(dict(unit=uid, closed=bool(G.closed), deferred=G.O.get('deferred'),
                       pos=((f or {}).get('pos') or {}).get('v'), pos_status=((f or {}).get('pos') or {}).get('st'),
                       derivation=((f or {}).get('derivation') or {}).get('v'), lemma=((f or {}).get('lemma') or {}).get('v'),
                       segments=G.O.get('slots')))
    mr = [dict(status=x.get('status'), root=x.get('root'), form_class=x.get('form_class'), reason=str(x.get('reason') or '')[:300])
          for x in a.get('morph') or []]
    level = ('ROOT_PROVEN' if any(x['status'] == 'accepted' for x in mr) else
             'UNIT_CLOSED' if any(u['closed'] for u in us) else 'DEFERRED')
    return dict(level=level, units=us, morph=mr, n_segments=len(a['segments']))


def run(inp, out, pos_file=None):
    head, rows = read_tsv(inp)
    if tuple(head) != ('id', 'word'):
        raise SystemExit(f'المدخل الأعمى عموداه id وword وحدهما؛ وُجد: {head}')
    pos_by = {}
    if pos_file:
        _, pr = read_tsv(pos_file)
        pos_by = {r['id']: r['pos'] for r in pr}
    from sarf.catalog import Catalog
    from sarf.root import hfn
    CAT = Catalog([os.path.join(H, 'operators_catalog.jsonl'), os.path.join(H, 'operators_catalog_split_vocalized.csv')])
    meta = dict(hfn_path=hfn().path, python=sys.version.split()[0], hashseed=os.environ.get('PYTHONHASHSEED'),
                input_sha256=sha(inp), mode='POS_ASSISTED_DIAGNOSTIC' if pos_file else 'BLIND')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(json.dumps(dict(meta=meta), ensure_ascii=False) + '\n')
        for r in rows:
            rec = dict(id=r['id'], word=r['word'])
            try:
                rec['A_LEXICAL_MORPH'] = _analyze_word(r['word'], pos_assisted=pos_by.get(r['id']) == 'فعل ماضٍ')
            except Exception as e:
                rec['A_LEXICAL_MORPH'] = dict(level='EXECUTION_FAILURE', error=repr(e)[:300])
            try:
                rec['B_PUBLIC'] = _public(r['word'], CAT)
            except Exception as e:
                rec['B_PUBLIC'] = dict(level='EXECUTION_FAILURE', error=repr(e)[:300])
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + '\n')
    print(f'كُتب {out}: {len(rows)} صفاً')


# ---------- المقارنة ----------
def _hfn_presence():
    from sarf.root import hfn
    from sarf.cells import lex_index
    Hh = hfn()
    verbs = {}
    for k, es in Hh.index.items():
        for e in es:
            verbs.setdefault(nfc(e['verb']), set()).add(k[0])
    return Hh, verbs, lex_index()


def classify(ref, rec, avail):
    """تصنيف الخلاف بموضع العجز (لا حكماً على المرجع)"""
    A = rec.get('A_LEXICAL_MORPH') or {}
    if A.get('level') == 'EXECUTION_FAILURE':
        return 'EXECUTION_FAILURE'
    if A.get('level') == 'PROTECTED':
        return 'PROTECTED_NOT_APPLICABLE'
    if ref['row_review'] in ('DISPUTED', 'REVIEW_REQUIRED'):
        return 'REFERENCE_DISPUTE'
    roots = {f['root'] for f in A.get('faces') or []}
    pr = (A.get('proven') or {}).get('root')
    if pr:
        if pr == ref['root']:
            return 'WAZN_ERROR'
        return 'CORRECT_CANDIDATE_NOT_SELECTED' if ref['root'] in roots else 'ROOT_ERROR'
    if ref['root'] in roots:
        return 'CONTEXT_REQUIRED'                 # المرشّح الصحيح حاضر، والإثبات ينتظر صنفاً أو سياقاً
    if not (set(ref['word']) & TASHKEEL) or ref['missing_tashkeel']:
        return 'INSUFFICIENT_DIACRITICS'
    if not avail['root_in_hfn_v36'] or not avail['word_in_hfn_v36']:
        return 'LEXICON_GAP'
    if roots:
        return 'ROOT_ERROR'
    return 'REALIZATION_ERROR'                     # الكلمة في المعجم بحروفها وحركاتها، ولم يُطابقها قالب ولا مدخل


def compare(pkg, analysis, out_dir, corrections=None):
    os.makedirs(out_dir, exist_ok=True)
    _, rows = read_tsv(os.path.join(pkg, 'testset_all.tsv'))
    ref_by = {r['id']: r for r in rows}
    corr = load_corrections(corrections)
    Hh, hfn_verbs, LEX = _hfn_presence()
    from sarf.cells import _lex_key
    recs = [json.loads(l) for l in open(analysis, encoding='utf-8')]
    meta, recs = recs[0]['meta'], recs[1:]
    if any(ref_by[r['id']]['split'] != 'dev' for r in recs):
        raise SystemExit('صفٌّ من غير dev في التحليل: ممنوع في هذه الجولة')
    per = []
    for rec in recs:
        ref = dict(ref_by[rec['id']])
        ref['row_review'] = row_review_status(rec['id'], corr)
        ref['missing_tashkeel'] = sum(1 for ch in ref['word'] if ch not in TASHKEEL) > 2 * sum(1 for ch in ref['word'] if ch in TASHKEEL)
        A, B = rec['A_LEXICAL_MORPH'], rec['B_PUBLIC']
        avail = dict(root_in_hfn_v36=ref['root'] in Hh.roots, word_in_hfn_v36=(nfc(ref['word']) in hfn_verbs or _lex_key(ref['word']) in LEX))
        faces_ = A.get('faces') or []
        pair_ok = ref['wazn'] and any(f['root'] == ref['root'] and f.get('wazn') and cmp_form(f['wazn']) == cmp_form(ref['wazn']) for f in faces_)
        verbform_ok = any(f['root'] == ref['root'] and cmp_form(f.get('verb_pattern') or f.get('wazn') or '') == cmp_form(ref['verb_form'])
                          for f in faces_) if ref['verb_form'] else None
        proven = A.get('proven')
        res = dict(id=rec['id'], word=ref['word'], ref_root=ref['root'], ref_wazn=ref['wazn'], ref_pos=ref['pos'], ref_root_type=ref['root_type'],
                   ref_wazn_status=ref['wazn_status'], ref_verb_form=ref['verb_form'], row_review=ref['row_review'],
                   availability=avail, A_level=A.get('level'), A_reason=A.get('reason'),
                   A_candidate_roots=A.get('candidate_roots'), A_faces=faces_, A_protected=A.get('protected'),
                   B_level=(B or {}).get('level'), B_units=(B or {}).get('units'), B_morph=(B or {}).get('morph'),
                   proven_root=(proven or {}).get('root'), proven_wazn=(proven or {}).get('wazn'),
                   root_proven_correct=(proven['root'] == ref['root']) if proven else None,
                   wazn_proven_correct=(cmp_form(ref['wazn']) in {cmp_form(x) for x in proven['wazn']} if proven and ref['wazn'] else None),
                   root_in_candidates=ref['root'] in {f['root'] for f in faces_},
                   pair_in_candidates=bool(pair_ok), verb_form_in_candidates=verbform_ok,
                   extra_unsupported_candidates=len({f['root'] for f in faces_} - {ref['root']}))
        ok = res['root_proven_correct'] is True and (res['wazn_proven_correct'] in (True, None))
        res['category'] = 'AGREE' if ok else classify(ref, rec, avail)
        per.append(res)
    with open(os.path.join(out_dir, 'dev_results.jsonl'), 'w', encoding='utf-8') as f:
        for r in per:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    gold = [r for r in per if r['row_review'] not in ('DISPUTED', 'REVIEW_REQUIRED')]
    disputed = [r for r in per if r['row_review'] in ('DISPUTED', 'REVIEW_REQUIRED')]

    def metrics(rs):
        n = len(rs)
        pr = [r for r in rs if r['proven_root']]
        prc = sum(1 for r in pr if r['root_proven_correct'])
        pw = [r for r in rs if r['proven_root'] and r['ref_wazn']]
        pwc = sum(1 for r in pw if r['wazn_proven_correct'])
        rc = sum(1 for r in rs if r['root_in_candidates'])
        withw = [r for r in rs if r['ref_wazn']]
        pc = sum(1 for r in withw if r['pair_in_candidates'])
        prot = sum(1 for r in rs if r['A_level'] == 'PROTECTED')
        return dict(n=n,
                    root_proven=dict(n=len(pr), correct=prc, precision=round(prc / len(pr), 4) if pr else None, wilson_low=wilson_low(prc, len(pr))),
                    root_coverage=dict(k=len(pr), n=n, value=round(len(pr) / n, 4) if n else None),
                    wazn_proven=dict(n=len(pw), correct=pwc, precision=round(pwc / len(pw), 4) if pw else None, wilson_low=wilson_low(pwc, len(pw))),
                    wazn_coverage=dict(k=len(pw), n=len(withw), value=round(len(pw) / len(withw), 4) if withw else None),
                    root_recall_in_candidates=dict(k=rc, n=n, value=round(rc / n, 4) if n else None, wilson_low=wilson_low(rc, n)),
                    pair_recall_in_candidates=dict(k=pc, n=len(withw), value=round(pc / len(withw), 4) if withw else None, wilson_low=wilson_low(pc, len(withw))),
                    wrong_decision=sum(1 for r in pr if not r['root_proven_correct']),
                    extra_unsupported_candidates=dict(rows_with_extra=sum(1 for r in rs if r['extra_unsupported_candidates']),
                                                      total=sum(r['extra_unsupported_candidates'] for r in rs)),
                    protected=prot, levels=dict(collections.Counter(r['A_level'] for r in rs)),
                    public_levels=dict(collections.Counter(r['B_level'] for r in rs)),
                    deferral_reasons=dict(collections.Counter((r['A_reason'] or '')[:70] for r in rs if r['A_level'] != 'ROOT_PROVEN').most_common(15)),
                    execution_failures=sum(1 for r in rs if r['A_level'] == 'EXECUTION_FAILURE' or r['B_level'] == 'EXECUTION_FAILURE'),
                    categories=dict(collections.Counter(r['category'] for r in rs)))

    def by(key, rs):
        g = collections.defaultdict(list)
        for r in rs:
            g[key(r)].append(r)
        return {k: metrics(v) for k, v in sorted(g.items(), key=lambda kv: -len(kv[1]))}
    words = {}
    for r in gold:
        words.setdefault(nfc(r['word']), r)
    M = dict(meta=meta, scope='dev فقط (testset_all split=dev)؛ الاختبار المحجوب لم يُشغَّل',
             gold=metrics(gold), disputed_or_review_required=metrics(disputed),
             distinct_words=metrics(list(words.values())),
             by_root_type=by(lambda r: r['ref_root_type'], gold), by_pos=by(lambda r: r['ref_pos'], gold),
             by_wazn_status=by(lambda r: r['ref_wazn_status'], gold), by_review=by(lambda r: r['row_review'], per),
             by_availability=by(lambda r: ('root_in_v36' if r['availability']['root_in_hfn_v36'] else 'root_not_in_v36') + '|' +
                                           ('word_in_v36' if r['availability']['word_in_hfn_v36'] else 'word_not_in_v36'), gold))
    json.dump(M, open(os.path.join(out_dir, 'dev_metrics.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(dict(n=M['gold']['n'], root_proven=M['gold']['root_proven'], coverage=M['gold']['root_coverage'],
                          recall=M['gold']['root_recall_in_candidates'], pair=M['gold']['pair_recall_in_candidates'],
                          cats=M['gold']['categories']), ensure_ascii=False))
    return M


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd')
    ap.add_argument('args', nargs='*')
    ap.add_argument('--split')
    ap.add_argument('--corrections')
    ap.add_argument('--pos-assisted')
    a = ap.parse_args()
    sys.path.insert(0, H)
    if a.cmd == 'audit':
        audit(*a.args)
    elif a.cmd == 'exposure':
        exposure(*a.args)
    elif a.cmd == 'faces':
        faces(*a.args, corrections=a.corrections)
    elif a.cmd == 'blind-input':
        blind_input(*a.args, split=a.split)
    elif a.cmd == 'run':
        run(*a.args, pos_file=a.pos_assisted)
    elif a.cmd == 'compare':
        compare(*a.args, corrections=a.corrections)
    else:
        ap.error('أمرٌ غير معروف')


if __name__ == '__main__':
    main()
