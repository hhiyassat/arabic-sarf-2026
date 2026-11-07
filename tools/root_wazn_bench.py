#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/root_wazn_bench.py — مقياس الجذر والوزن الأعمى على حزمة MORPH_TESTSET (الإصدار 2: SARF_ROOT_WAZN_BENCHMARK_REPAIR_02).

الحزمة لا تدخل git (مشتقّة من HFN)، ولا تُعدَّل. والمحلّل لا يرى إلا (id، word). والمقارن يقرأ المرجع بعد تجميد المخرج.

    audit       <pkg> <out.json>                       تدقيق البنية والأعداد والمقامات
    exposure    <pkg> <out.json>                       التعرّض والتداخل
    faces       <pkg> <out.json>                       مجموعات الأوجه المرجعية (dev وحده للقياس)
    blind-input <pkg> <out.tsv> --split dev            (id، word) وحدهما؛ test مرفوض
    run         <in.tsv> <out.jsonl> [--pos-assisted <pos.tsv>]
    compare     <pkg> <in.tsv> <analysis.jsonl> <outdir> [--corrections c.tsv]
    corrupt-check <pkg> <in.tsv> <analysis.jsonl> <out.json>     إفساد المخرج الحقيقي والتحقق من رفض المقارن
    diagnose    <out.json> [كلمات…]                    سجلّ تشخيصي للكلمات المسمّاة
    diff-runs   <rw01_analysis.jsonl> <rw01_results.jsonl> <rw02_analysis.jsonl> <rw02_outdir> <out>   مقارنة الجولتين

فروع المسار A_LEXICAL_MORPH (لكلٍّ: branch، execution_status، error_type، error_message، outputs):
  protection        البوابة الدستورية (sarf/protected.py)
  stem_info         ما يقترحه المقشِّر من سابقة ولاحقة (sarf/affix.py)
  verb_morph        قوالب الفعل برخصة HFN (sarf/root.py morph)
  verb_templates    القالب بلا رخصة (candidates any_pos)
  participle        قوالب اسمي الفاعل والمفعول برخصة HFN (sarf/cells.py participle_analyses على خلايا cells_of)
  lexical_retrieval مطابقة مدخل الاسم في HFN (lex_index)
  verb_morph_pos_assisted  (في POS_ASSISTED_DIAGNOSTIC وحده) morph بصنف «فعل» معطى
والمسار B_PUBLIC: analyze ← sentence_geo ← unit_features؛ ولا يُخرج وزناً عربياً صريحاً، فلا يُنسب إليه وزن.
"""
import argparse, collections, csv, hashlib, json, math, os, re, subprocess, sys, unicodedata

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL_VERSION = 'RW02'
COLS = ('id', 'split', 'root', 'root_spaced', 'root_type', 'word', 'pos', 'wazn', 'surface_pattern', 'wazn_status', 'verb',
        'verb_form', 'source', 'evidence', 'event_id', 'rank')
REF_ONLY = ('root', 'root_spaced', 'root_type', 'pos', 'wazn', 'surface_pattern', 'wazn_status', 'verb', 'verb_form', 'source',
            'evidence', 'event_id')
ROOT_TYPES = {'سالم', 'مهموز', 'مثال', 'أجوف', 'ناقص', 'لفيف', 'مضعّف', 'رباعي'}
POS = {'فعل ماضٍ', 'مصدر', 'اسم فاعل', 'اسم مفعول', 'صفة مشبّهة', 'صيغة مبالغة', 'صفة (فَعِيل/فَعُول)'}
STATUSES = {'VERIFIED', 'INVENTORY', 'WEAK_SUBST', 'HFN_FORM', 'UNRESOLVED', 'FORM_MISMATCH'}
TASHKEEL = set('ًٌٍَُِّْٰ')
ARABIC_LETTER = re.compile('[ء-غف-يٱ-ۓ]')

# ---------- عقد الوزن ----------
# تحويلٌ معلن ومختبر من الباب إلى الميزان: الباب الأول عائلةٌ لا ميزانٌ واحد؛ ولا يُقارن «IV» بوزنٍ عربي مباشرة
FORM_CLASS_TO_WAZN = {'I': {'فَعَلَ', 'فَعِلَ', 'فَعُلَ'}, 'II': {'فَعَّلَ'}, 'III': {'فَاعَلَ'}, 'IV': {'أَفْعَلَ'},
                      'V': {'تَفَعَّلَ'}, 'VI': {'تَفَاعَلَ'}, 'VII': {'انْفَعَلَ'}, 'VIII': {'افْتَعَلَ'}, 'IX': {'افْعَلَّ'},
                      'X': {'اسْتَفْعَلَ'}, 'QI': {'فَعْلَلَ'}, 'QII': {'تَفَعْلَلَ'}, 'QIII': {'افْعَنْلَلَ'}, 'QIV': {'افْعَلَلَّ'}}
# اسما الفاعل والمفعول: تحويلٌ معلن من (الباب، النوع) إلى الميزان (DECLARED_FORM_MAPPING)
PARTICIPLE_WAZN = {('I', 'فاعل'): 'فَاعِل', ('I', 'مفعول'): 'مَفْعُول', ('II', 'فاعل'): 'مُفَعِّل', ('II', 'مفعول'): 'مُفَعَّل',
                   ('III', 'فاعل'): 'مُفَاعِل', ('III', 'مفعول'): 'مُفَاعَل', ('IV', 'فاعل'): 'مُفْعِل', ('IV', 'مفعول'): 'مُفْعَل',
                   ('V', 'فاعل'): 'مُتَفَعِّل', ('V', 'مفعول'): 'مُتَفَعَّل', ('VI', 'فاعل'): 'مُتَفَاعِل', ('VI', 'مفعول'): 'مُتَفَاعَل',
                   ('VII', 'فاعل'): 'مُنْفَعِل', ('VII', 'مفعول'): 'مُنْفَعَل', ('VIII', 'فاعل'): 'مُفْتَعِل', ('VIII', 'مفعول'): 'مُفْتَعَل',
                   ('IX', 'فاعل'): 'مُفْعَلّ', ('X', 'فاعل'): 'مُسْتَفْعِل', ('X', 'مفعول'): 'مُسْتَفْعَل',
                   ('QI', 'فاعل'): 'مُفَعْلِل', ('QI', 'مفعول'): 'مُفَعْلَل', ('QII', 'فاعل'): 'مُتَفَعْلِل', ('QII', 'مفعول'): 'مُتَفَعْلَل'}
WAZN_SOURCES = ('DIRECT_ANALYZER_OUTPUT', 'LEXICON_RETRIEVAL', 'DECLARED_FORM_MAPPING', 'CANDIDATE_FAMILY')
EXEC_STATES = ('EXECUTED_WITH_RESULTS', 'EXECUTED_EMPTY', 'EXECUTION_FAILURE', 'NOT_APPLICABLE', 'NOT_IMPLEMENTED')

# ---------- سياسة المرجع (مجمّدة قبل التشغيل؛ تُسجَّل بصمتها) ----------
REFERENCE_POLICY = dict(
    version='RW02-P1',
    denominators=dict(
        RAW_ALL='كل صفوف dev، بلا استبعاد',
        PROVISIONAL_REFERENCE_MAIN='صفوف dev التي ليس في حقولها المعنية بالمقياس حالة DISPUTED أو REVIEW_REQUIRED أو UNRESOLVED في الملحق؛ '
                                   'وهي غير مراجَعة لغوياً، فليست ذهبية',
        PROVISIONAL_REFERENCE_FLAGGED='صفوف dev التي في حقولها المعنية حالةٌ من تلك الثلاث (مقامٌ منفصل)',
        REVIEWED_ACCEPTED='صفوف dev التي حقولها المعنية كلها REVIEWED_ACCEPTED'),
    metric_fields=dict(root=['word', 'root'], wazn=['word', 'root', 'wazn'], pair=['word', 'root', 'wazn']),
    unreviewed_is_not_acceptance=True,
    wazn_empty_reference='الوزن الفارغ في المرجع (UNRESOLVED/FORM_MISMATCH) لا يُعدّ صحةً ولا خطأً، ويخرج من مقامات الوزن والزوج',
    wazn_family='موافقة المرجع لعنصرٍ من عائلة الباب تُسجَّل REFERENCE_WEIGHT_INCLUDED_IN_FAMILY ولا تُعدّ وزناً مختاراً',
    multi_face='الكلمة تُقاس بمجموعة أوجهها في dev؛ والصف يُقاس بوجهه؛ وأوجه test لا تدخل المجموعات',
    comparison='مطابقةٌ حرفية (NFC) ومطابقةٌ وفق اتفاقية الميزان (ألف الوصل المكسورة أول الميزان = غير المكسورة) تُعرضان منفصلتين؛ '
               'ولا تجريد للحركات ولا تسوية للهمزات ولا للواو والياء')
POLICY_SHA = hashlib.sha256(json.dumps(REFERENCE_POLICY, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def nfc(s):
    return unicodedata.normalize('NFC', s or '')


def wazn_literal(s):
    """المطابقة الحرفية: NFC وحده"""
    return nfc(s).strip()


def wazn_convention(s):
    """اتفاقية كتابة الميزان (للوزن وحده، لا للكلمات): ألف الوصل المكسورة أول الميزان = غير المكسورة"""
    s = wazn_literal(s)
    return 'ا' + s[2:] if s.startswith('اِ') else s


def hfn_form_wazn(s):
    """hfn_form كما في HFN: «أَفَالَ (أفعل أجوف)» ← «أَفَالَ» (الشرح بين القوسين ليس جزءاً من الوزن)"""
    return re.sub(r'\s*\(.*\)$', '', nfc(s or '')).strip()


def read_tsv(p):
    with open(p, encoding='utf-8') as f:
        r = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE)
        head = next(r)
        rows = []
        for row in r:
            if len(row) != len(head):
                raise SystemExit(f'{p}: صفٌّ بعددٍ غير متوقع من الأعمدة ({len(row)} لا {len(head)})')
            rows.append(dict(zip(head, row)))
        return head, rows


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def wilson_low(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    return round((p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n), 4)


def ratio(k, n):
    return dict(k=k, n=n, value=round(k / n, 4) if n else None, wilson_low=wilson_low(k, n))


def unmarked_consonants(w):
    """عدد الحروف غير المضبوطة في غير آخر الكلمة، سوى الألف وآ وى وحرفي المدّ بعد حركتهما (معيارٌ تقريبي لنقص الضبط)"""
    base = []
    for c in w:
        if c in TASHKEEL and base:
            base[-1][1].append(c)
        elif c not in TASHKEEL:
            base.append((c, []))
    n = 0
    for i, (c, marks) in enumerate(base[:-1]):
        pm = base[i - 1][1] if i else []
        if marks or c in 'اآى' or (c == 'و' and 'ُ' in pm) or (c == 'ي' and 'ِ' in pm):
            continue
        n += 1
    return n


# ---------- بصمة الموارد ----------
def resource_fingerprint():
    """بصمة ما يقرؤه المحلّل: شيفرته ومعاجمه وفهرسه وملفات HFN التي يحمّلها"""
    from sarf.root import hfn
    hp = hfn().path
    files = {}
    for f in ('lexical_units.csv', 'events.csv', 'roots.csv', 'MANIFEST.json'):
        p = os.path.join(hp, f)
        files['HFN/' + f] = sha(p) if os.path.exists(p) else None
    code = hashlib.sha256()
    for d in ('sarf', 'lexicon'):
        for root, _, fs in sorted(os.walk(os.path.join(H, d))):
            for f in sorted(fs):
                if f.endswith(('.py', '.jsonl', '.csv', '.json', '.tsv')) and '__pycache__' not in root:
                    p = os.path.join(root, f)
                    code.update(os.path.relpath(p, H).encode())
                    code.update(open(p, 'rb').read())
    for f in ('operators_catalog.jsonl', 'operators_catalog_split_vocalized.csv'):
        p = os.path.join(H, f)
        if os.path.exists(p):
            code.update(f.encode())
            code.update(open(p, 'rb').read())
    return dict(hfn_path=hp, hfn_release=os.path.basename(os.path.normpath(hp)), hfn_files=files, analyzer_code_sha256=code.hexdigest())


def git_commit():
    try:
        return subprocess.run(['git', '-C', H, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip() or None
    except Exception:
        return None


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
    c['root_spaced_consistent'] = dict(ok=not bad_sp, n_bad=len(bad_sp), bad=bad_sp[:50])
    c['rank_all_candidate'] = dict(ok=all(r['rank'] == 'CANDIDATE' for r in rows), values=dict(collections.Counter(r['rank'] for r in rows)))
    c['split_values'] = dict(collections.Counter(r['split'] for r in rows))
    roots_split = collections.defaultdict(set)
    for r in rows:
        roots_split[r['root']].add(r['split'])
    c['split_by_root_disjoint'] = dict(ok=all(len(v) == 1 for v in roots_split.values()),
                                       roots_in_both=sorted(k for k, v in roots_split.items() if len(v) > 1))
    c['pos_values'] = dict(collections.Counter(r['pos'] for r in rows))
    c['pos_unexpected'] = sorted(set(c['pos_values']) - POS)
    c['root_type_unexpected'] = sorted({r['root_type'] for r in rows if not set(r['root_type'].split('+')) <= ROOT_TYPES})
    c['wazn_status_values'] = dict(collections.Counter(r['wazn_status'] for r in rows))
    c['wazn_status_unexpected'] = sorted(set(c['wazn_status_values']) - STATUSES)
    c['empty_by_column'] = {k: sum(1 for r in rows if not r[k]) for k in COLS}
    c['empty_wazn_matches_status'] = dict(
        ok=all((not r['wazn']) == (r['wazn_status'] in ('UNRESOLVED', 'FORM_MISMATCH')) for r in rows))
    # Unicode: ما ليس NFC، وأثره على المقارنة (المقارنة تُجرى على نسخة NFC، والأصل محفوظ)
    nn = collections.Counter()
    affects = 0
    for r in rows:
        for k in ('word', 'wazn', 'surface_pattern', 'verb', 'verb_form'):
            if r[k] != nfc(r[k]):
                nn[k] += 1
                affects += k in ('word', 'wazn', 'surface_pattern')
    c['nfc'] = dict(not_nfc_by_column=dict(nn), compared_columns_affected=affects,
                    handling='الأصل محفوظ؛ والمقارنة على نسخة NFC؛ وعمود verb لا يدخل المقارنة')
    c['word_without_any_tashkeel'] = dict(n=sum(1 for r in rows if not set(r['word']) & TASHKEEL))
    c['wazn_without_any_tashkeel'] = dict(n=sum(1 for r in rows if r['wazn'] and not set(r['wazn']) & TASHKEEL))
    # حرفٌ أصلي غير ظاهر يحتاج تفسيراً (لا حكم بخطأ): يُفصل ما يفسّره إبدال افتعل وإدغامه عمّا لم يُفسَّر
    HAMZ = set('ءأإؤئآ')
    expl, unexpl = [], []
    for r in rows:
        w = [ch for ch in r['word'] if ch not in TASHKEEL]
        miss = [L for L in r['root'] if not (L in w or (L == 'ء' and set(w) & HAMZ))]
        if not miss or set(miss) <= set('وي'):
            continue
        rec = dict(id=r['id'], split=r['split'], word=r['word'], root=r['root'], missing=''.join(miss), source=r['source'])
        if r['pos'] == 'فعل ماضٍ' and r['wazn'] in ('افْتَعَلَ', 'اِفْتَعَلَ') and len(miss) == 1 and miss[0] in 'ذزث' and 'دَّ' in r['word']:
            rec['explanation_candidate'] = 'إبدال تاء الافتعال دالاً وإدغام الفاء فيها (ادَّكَرَ)'
            expl.append(rec)
        else:
            unexpl.append(rec)
    c['root_letter_not_visible_needs_explanation'] = dict(
        n=len(expl) + len(unexpl), explained_candidates=expl, unexplained=dict(n=len(unexpl), ids=[x['id'] for x in unexpl]),
        note='مشاهدة لا حكم: لا يُعدّ خطأ تنقيطٍ قبل فحص الإبدال والإدغام والقلب')
    sub = {}
    for f, cond in (('dev.tsv', lambda r: r['split'] == 'dev' and r['wazn']), ('test.tsv', lambda r: r['split'] == 'test' and r['wazn']),
                    ('unresolved_wazn.tsv', lambda r: not r['wazn'])):
        _, r2 = read_tsv(os.path.join(pkg, f))
        exp = [r['id'] for r in rows if cond(r)]
        sub[f] = dict(rows=len(r2), expected_from_all=len(exp), ids_equal=sorted(x['id'] for x in r2) == sorted(exp),
                      rows_identical=all(by.get(x['id']) == x for x in r2))
    c['subfiles'] = sub
    _, vm = read_tsv(os.path.join(pkg, 'verb_form_mismatch.tsv'))
    fm = [r for r in rows if r['wazn_status'] == 'FORM_MISMATCH']
    c['verb_form_mismatch'] = dict(rows=len(vm), form_mismatch_rows=[r['id'] for r in fm],
                                   events_match=sorted(x['event_id'] for x in vm) == sorted(r['event_id'] for r in fm))
    st = json.load(open(os.path.join(pkg, 'STATS.json'), encoding='utf-8'))
    with_w = [r for r in rows if r['wazn']]
    counts = dict(rows=len(rows), roots=len({r['root'] for r in rows}), with_wazn=len(with_w),
                  dev_with_wazn=sum(1 for r in with_w if r['split'] == 'dev'), test_with_wazn=sum(1 for r in with_w if r['split'] == 'test'),
                  without_wazn=len(rows) - len(with_w), unresolved=c['wazn_status_values'].get('UNRESOLVED', 0),
                  form_mismatch=c['wazn_status_values'].get('FORM_MISMATCH', 0))
    expected = dict(rows=20581, roots=5443, with_wazn=19218, dev_with_wazn=15431, test_with_wazn=3787, without_wazn=1363,
                    unresolved=1361, form_mismatch=2)
    rep['counts'] = dict(found=counts, expected=expected, match={k: counts[k] == v for k, v in expected.items()})
    rt_with = dict(collections.Counter(r['root_type'] for r in with_w))
    rep['denominators'] = dict(by_root_type_STATS=dict(matches_with_wazn=rt_with == st['by_root_type']),
                               by_pos_STATS=dict(matches_all=dict(collections.Counter(r['pos'] for r in rows)) == st['by_pos']))
    json.dump(rep, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = all(rep['counts']['match'].values()) and c['id_unique']['ok'] and c['root_spaced_consistent']['ok'] and \
        c['rank_all_candidate']['ok'] and c['split_by_root_disjoint']['ok'] and all(v['ids_equal'] and v['rows_identical'] for v in sub.values())
    print('PACKAGE_STRUCTURALLY_VALID' if ok else 'PACKAGE_STRUCTURAL_ISSUES', json.dumps(rep['counts']['match'], ensure_ascii=False))
    return rep


# ---------- التعرّض ----------
def exposure(pkg, out, extra_read=None):
    _, rows = read_tsv(os.path.join(pkg, 'testset_all.tsv'))
    _, s60 = read_tsv(os.path.join(pkg, 'sample60.tsv'))
    by = {r['id']: r for r in rows}
    dev_roots = {r['root'] for r in rows if r['split'] == 'dev'}
    test_roots = {r['root'] for r in rows if r['split'] == 'test'}
    wd, wt = collections.defaultdict(set), collections.defaultdict(set)
    for r in rows:
        (wd if r['split'] == 'dev' else wt)[nfc(r['word'])].add(r['root'])
    shared = sorted(set(wd) & set(wt))
    sw_w = {nfc(r['word']) for r in rows if r['split'] == 'dev' and r['wazn']} & {nfc(r['word']) for r in rows if r['split'] == 'test' and r['wazn']}
    s60_test = [x['id'] for x in s60 if by.get(x['id'], {}).get('split') == 'test']
    s60_roots = sorted({by[i]['root'] for i in s60_test})
    roots_rows_tsv = [r['id'] for r in rows if r['split'] == 'test' and r['wazn'] and r['root'] in s60_roots]
    roots_rows_all = [r['id'] for r in rows if r['split'] == 'test' and r['root'] in s60_roots]
    shared_ids = sorted(r['id'] for r in rows if r['split'] == 'test' and nfc(r['word']) in set(shared))
    read_ids = sorted(extra_read or [])
    exposed = set(roots_rows_all) | set(shared_ids) | set(read_ids)
    rep = dict(
        shared_roots_dev_test=sorted(dev_roots & test_roots),
        shared_words_with_wazn=dict(n=len(sw_w), denominator='صفوف ذات وزن (dev.tsv/test.tsv)'),
        shared_words=dict(n=len(shared), different_roots=sum(1 for w in shared if wd[w] != wt[w]), denominator='كل الصفوف',
                          list=[dict(word=w, dev_roots=sorted(wd[w]), test_roots=sorted(wt[w])) for w in shared]),
        sample60=dict(test_rows=len(s60_test), test_roots=s60_roots, test_tsv_rows_of_those_roots=len(roots_rows_tsv),
                      all_test_rows_of_those_roots=len(roots_rows_all)),
        partitions=dict(DEVELOPMENT=dict(n=sum(1 for r in rows if r['split'] == 'dev')),
                        TEST_EXPOSED_SAMPLE_ROOTS=dict(n=len(roots_rows_all), ids=roots_rows_all),
                        TEST_SHARED_WORD_WITH_DEV=dict(n=len(shared_ids), ids=shared_ids),
                        TEST_READ_DURING_AUDIT=dict(n=len(read_ids), ids=read_ids),
                        TEST_ANY_EXPOSURE=dict(n=len(exposed)),
                        TEST_UNEXPOSED=dict(n=sum(1 for r in rows if r['split'] == 'test' and r['id'] not in exposed))),
        heldout_inference='NOT_RUN')
    json.dump(rep, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"جذور مشتركة {len(rep['shared_roots_dev_test'])}، كلمات مشتركة ذات وزن {len(sw_w)}، وفي كل الصفوف {len(shared)}، "
          f"عيّنة: {len(s60_test)} من test، جذورها {len(s60_roots)} ← {len(roots_rows_tsv)} صفاً في test.tsv")
    return rep


# ---------- الملحق ----------
CORR_COLS = ('row_id', 'field', 'original_value', 'proposed_value', 'reason', 'source_reference', 'reviewer', 'review_status', 'revision_id')
REVIEW_STATES = ('REVIEWED_ACCEPTED', 'REVIEW_REQUIRED', 'DISPUTED', 'UNRESOLVED')
FLAGGED = ('REVIEW_REQUIRED', 'DISPUTED', 'UNRESOLVED')


def load_corrections(p):
    if not p:
        return {}
    head, rows = read_tsv(p)
    if tuple(head) != CORR_COLS:
        raise SystemExit(f'أعمدة الملحق غير متوقعة: {head}')
    out = collections.defaultdict(dict)
    for r in rows:
        if r['review_status'] not in REVIEW_STATES:
            raise SystemExit(f'حالة مراجعةٍ غير معروفة: {r}')
        prev = out[r['row_id']].get(r['field'])
        order = {s: i for i, s in enumerate(('DISPUTED', 'UNRESOLVED', 'REVIEW_REQUIRED', 'REVIEWED_ACCEPTED'))}
        if prev is None or order[r['review_status']] < order[prev]:
            out[r['row_id']][r['field']] = r['review_status']
    return dict(out)


def field_status(rid, field, corr):
    """غياب الصف من الملحق = UNREVIEWED، لا شهادة صحة"""
    return corr.get(rid, {}).get(field, 'UNREVIEWED')


def denominators_for(rid, corr):
    out = {}
    for metric, fields in REFERENCE_POLICY['metric_fields'].items():
        st = [field_status(rid, f, corr) for f in fields]
        if any(s in FLAGGED for s in st):
            out[metric] = 'PROVISIONAL_REFERENCE_FLAGGED'
        elif all(s == 'REVIEWED_ACCEPTED' for s in st):
            out[metric] = 'REVIEWED_ACCEPTED'
        else:
            out[metric] = 'PROVISIONAL_REFERENCE_MAIN'
    return out


# ---------- مجموعات الأوجه المرجعية ----------
def reference_groups(rows, corr, split='dev'):
    g = collections.defaultdict(list)
    for r in rows:
        if r['split'] != split:
            continue
        g[nfc(r['word'])].append(dict(word=r['word'], root=r['root'], wazn=r['wazn'], pos=r['pos'], analysis_id=r['id'], split=r['split'],
                                      review_status={f: field_status(r['id'], f, corr) for f in ('word', 'root', 'wazn', 'pos')}))
    for w in g:
        g[w].sort(key=lambda x: x['analysis_id'])
    return dict(g)


def faces(pkg, out, corrections=None):
    _, rows = read_tsv(os.path.join(pkg, 'testset_all.tsv'))
    corr = load_corrections(corrections)
    dev = reference_groups(rows, corr, 'dev')
    test_words = {nfc(r['word']) for r in rows if r['split'] == 'test'}
    multi = {w: v for w, v in dev.items() if len({(x['root'], x['wazn']) for x in v}) > 1}
    rep = dict(policy=REFERENCE_POLICY['multi_face'], dev_words=len(dev), dev_multi_face_words=len(multi),
               dev_multi_root_words=sum(1 for v in multi.values() if len({x['root'] for x in v}) > 1),
               dev_words_also_in_test=sum(1 for w in dev if w in test_words),
               note='أوجه test لا تدخل المجموعات؛ والكلمة المشتركة بين القسمين تُقاس في dev بأوجهها في dev وحدها',
               groups=[dict(word=w, faces=v, group_status='UNREVIEWED_POSSIBILITIES', approved=False) for w, v in sorted(multi.items())])
    json.dump(rep, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"كلمات dev {rep['dev_words']}، متعددة الأوجه {rep['dev_multi_face_words']} (متعددة الجذر {rep['dev_multi_root_words']})")
    return rep


# ---------- المدخل الأعمى ----------
def blind_input(pkg, out, split):
    if split != 'dev':
        raise SystemExit('RUN_HELDOUT_INFERENCE = NO: لا يُبنى مدخلٌ أعمى لقسم الاختبار')
    _, rows = read_tsv(os.path.join(pkg, 'testset_all.tsv'))
    with open(out, 'w', encoding='utf-8') as f:
        f.write('id\tword\n')
        for r in rows:
            if r['split'] == split:
                f.write(f"{r['id']}\t{r['word']}\n")
    print(f'كُتب {out}: (id، word) وحدهما')


def read_blind_input(inp):
    head, rows = read_tsv(inp)
    if tuple(head) != ('id', 'word'):
        raise SystemExit(f'المدخل الأعمى عموداه id وword وحدهما؛ وُجد: {head}')
    ids = [r['id'] for r in rows]
    dup = [k for k, n in collections.Counter(ids).items() if n > 1]
    if dup:
        raise SystemExit(f'معرّفات مكررة في المدخل: {dup[:10]}')
    bad = [r['id'] for r in rows if not r['word'] or not ARABIC_LETTER.search(r['word'])]
    if bad:
        raise SystemExit(f'كلماتٌ فارغة أو بلا حرفٍ عربي في المدخل: {bad[:10]}')
    return rows


# ---------- التشغيل ----------
def _branch(name, fn):
    """→ سجلّ الفرع: لا يُستبدل الإخفاق بقائمة فارغة"""
    try:
        res = fn()
    except InvalidInput as e:
        return dict(branch=name, execution_status='EXECUTION_FAILURE', error_type='INVALID_INPUT', error_message=str(e)[:300], outputs=None)
    except Exception as e:
        return dict(branch=name, execution_status='EXECUTION_FAILURE', error_type=type(e).__name__, error_message=str(e)[:300], outputs=None)
    if isinstance(res, tuple) and res and res[0] == 'NOT_APPLICABLE':
        return dict(branch=name, execution_status='NOT_APPLICABLE', error_type=None, error_message=res[1], outputs=None)
    empty = res is None or res == [] or res == {}
    return dict(branch=name, execution_status='EXECUTED_EMPTY' if empty else 'EXECUTED_WITH_RESULTS', error_type=None, error_message=None,
                outputs=res)


class InvalidInput(Exception):
    pass


def _participle_branch(word):
    from sarf.cells import cells_of, participle_analyses
    if not ARABIC_LETTER.search(word or ''):
        raise InvalidInput('لا حرف عربي في الكلمة')
    cells, toks = cells_of(word, 'B')            # العقد: (الخلايا، رموز الرسم)؛ والدالة تأخذ الخلايا وحدها
    if not cells:
        raise InvalidInput('لا خلايا للكلمة')
    silent = [dict(cell=c.id, silent=c.O.get('silent')) for c in cells if c.O.get('silent')]
    out = []
    for p in participle_analyses(cells):
        root, cls, kind, alpha, ops, level = p
        out.append(dict(root=root, form_class=cls, kind=kind, alpha=alpha, ops=ops, license_level=level))
    return dict(analyses=out, cells=[[c.C, c.H, c.L] for c in cells], silent_letters=silent, glyph_tokens=len(toks)) if out else []


def _analyze_word(word, pos_assisted=False):
    from sarf.root import morph, candidates
    from sarf.affix import stem_info
    from sarf.cells import lex_index, _lex_key
    from sarf.protected import protected
    rec = dict(word=word, branches={})
    B = rec['branches']

    def prot_fn():
        p = protected(word)
        return None if p is None else dict(cls=p.get('cls'), identity=p.get('identity'), ambiguous=p.get('ambiguous'),
                                            proclitics=p.get('proclitics'), enclitic=p.get('enclitic'), alternative=p.get('alternative'),
                                            root_status=p.get('root_status'), reason=p.get('reason'))
    B['protection'] = _branch('protection', prot_fn)
    B['stem_info'] = _branch('stem_info', lambda: {k: v for k, v in stem_info(word).items() if k in ('pos', 'kind', 'prefix', 'suffix', 'object') and v})

    def morph_fn():
        m = morph(word)
        if m is None:
            return None
        return dict(status=m.get('status'), root=m.get('root'), form_class=m.get('form_class'), level=m.get('level'),
                    reason=str(m.get('reason') or '')[:300], root_status=m.get('root_status'),
                    licensed=[dict(root=x['root'], form_class=x.get('form_class'), hfn_form=x.get('hfn_form'), verb=x.get('verb'),
                                   event_id=x.get('event_id'), tier=x.get('tier')) for x in m.get('licensed') or []],
                    alternative=m.get('alternative'))
    B['verb_morph'] = _branch('verb_morph', morph_fn)
    B['verb_templates'] = _branch('verb_templates', lambda: [dict(root=r, form_class=c) for r, c in candidates(word, any_pos=True)])
    B['participle'] = _branch('participle', lambda: _participle_branch(word))
    B['lexical_retrieval'] = _branch('lexical_retrieval', lambda: [dict(root=r, pos=p, pattern=pt, lu_id=lu, lemma=lm)
                                                                   for (r, p, pt, lu, lm) in lex_index().get(_lex_key(word), [])])
    if pos_assisted:
        def pa():
            mv = morph(word, dict(stem_info(word), pos='verb'))
            return None if mv is None else dict(status=mv.get('status'), root=mv.get('root'), form_class=mv.get('form_class'),
                                                reason=str(mv.get('reason') or '')[:300])
        B['verb_morph_pos_assisted'] = _branch('verb_morph_pos_assisted', pa)
    rec.update(assemble(rec))
    return rec


def assemble(rec):
    """الأوجه والمستوى والحالة الإجمالية من الفروع (تُعاد حسابها في المقارن للتحقق)"""
    B = rec['branches']
    faces_ = []
    vm = B['verb_morph']
    if vm['execution_status'] == 'EXECUTED_WITH_RESULTS':
        for x in vm['outputs']['licensed']:
            fam = sorted(FORM_CLASS_TO_WAZN.get(x['form_class'], set()))
            faces_.append(dict(root=x['root'], kind='فعل', form_class=x['form_class'],
                               wazn=hfn_form_wazn(x['hfn_form']) if x.get('hfn_form') else None,
                               wazn_source='LEXICON_RETRIEVAL' if x.get('hfn_form') else None, wazn_raw=x.get('hfn_form'),
                               wazn_family=fam, branch='verb_morph', evidence=x.get('event_id')))
    pb = B['participle']
    if pb['execution_status'] == 'EXECUTED_WITH_RESULTS':
        for x in pb['outputs']['analyses']:
            w = PARTICIPLE_WAZN.get((x['form_class'], x['kind']))
            faces_.append(dict(root=x['root'], kind='اسم ' + x['kind'], form_class=x['form_class'], wazn=w,
                               wazn_source='DECLARED_FORM_MAPPING' if w else None, wazn_raw=None, wazn_family=[w] if w else [],
                               branch='participle', evidence=x['license_level'], ops=x['ops']))
    lr = B['lexical_retrieval']
    if lr['execution_status'] == 'EXECUTED_WITH_RESULTS':
        for x in lr['outputs']:
            nounish = x['pos'] in ('اسم فاعل', 'اسم مفعول')
            faces_.append(dict(root=x['root'], kind=x['pos'], form_class=None, wazn=nfc(x['pattern']) if nounish else None,
                               wazn_source='LEXICON_RETRIEVAL' if nounish else None, wazn_raw=x['pattern'],
                               verb_pattern=None if nounish else hfn_form_wazn(x['pattern']), wazn_family=[],
                               branch='lexical_retrieval', evidence=x['lu_id']))
    uniq, seen = [], set()
    for f in sorted(faces_, key=lambda f: (f['root'], f['kind'], f.get('wazn') or '', f.get('form_class') or '', f['branch'], str(f.get('evidence')))):
        k = (f['root'], f['kind'], f.get('wazn'), f.get('form_class'), f['branch'], str(f.get('evidence')))
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    for i, f in enumerate(uniq):
        f['candidate_id'] = f'C{i + 1}'
    templ = B['verb_templates']['outputs'] if B['verb_templates']['execution_status'] == 'EXECUTED_WITH_RESULTS' else []
    prot = B['protection']['outputs'] if B['protection']['execution_status'] == 'EXECUTED_WITH_RESULTS' else None
    m = vm['outputs'] if vm['execution_status'] == 'EXECUTED_WITH_RESULTS' else None
    # الحالة الإجمالية للتنفيذ
    core = ('protection', 'stem_info', 'verb_morph', 'verb_templates', 'participle', 'lexical_retrieval')
    failed = [b for b in core if B[b]['execution_status'] == 'EXECUTION_FAILURE']
    execution = 'COMPLETE' if not failed else ('FAILED' if len(failed) == len(core) else 'PARTIAL_EXECUTION')
    # المستوى
    if prot and not prot.get('ambiguous'):
        level, reason = 'PROTECTED', 'CONSTITUTIONAL_PROTECTED_CLASS'
    elif m is not None and m.get('status') == 'accepted':
        level, reason = 'ROOT_PROVEN', None
    elif uniq:
        level, reason = 'CANDIDATES_ONLY', (m or {}).get('reason') or 'مرشّحون بلا اختيارٍ مثبت'
    elif execution != 'COMPLETE':
        level, reason = 'NO_CANDIDATE_WITH_FAILED_BRANCH', 'فرعٌ معطّل: ' + ', '.join(failed)
    else:
        level, reason = 'NO_CANDIDATE', (m or {}).get('reason') or 'لا قالب مرخَّص ولا مدخل يطابق'
    proven = None
    if level == 'ROOT_PROVEN':
        lic = [x for x in m['licensed'] if x['root'] == m['root']]
        forms = sorted({hfn_form_wazn(x['hfn_form']) for x in lic if x.get('hfn_form')})
        proven = dict(root=m['root'], form_class=m['form_class'], branch='verb_morph',
                      wazn_selected=forms[0] if len(forms) == 1 else None,
                      wazn_selected_source='LEXICON_RETRIEVAL' if len(forms) == 1 else None,
                      wazn_candidates=forms if len(forms) > 1 else [],
                      wazn_family=sorted(FORM_CLASS_TO_WAZN.get(m['form_class'], set())),
                      wazn_family_source='CANDIDATE_FAMILY')
    return dict(faces=uniq, unlicensed_template_candidates=templ, level=level, reason=reason, proven=proven, execution=execution,
                failed_branches=failed, candidate_roots=sorted({f['root'] for f in uniq}))


def _public(word, CAT):
    from sarf.analyze import analyze
    from sarf.algebra import sentence_geo, Trace
    from sarf.features import unit_features
    a = analyze(CAT, word, 'auto')
    S, U = sentence_geo(a, 'B', Trace())
    F = unit_features(a, U)
    us = []
    for uid, G in U.items():
        f = F.get(uid) if isinstance(F, dict) else None
        us.append(dict(unit=uid, closed=bool(G.closed), deferred=G.O.get('deferred'),
                       pos=((f or {}).get('pos') or {}).get('v'), derivation=((f or {}).get('derivation') or {}).get('v'),
                       lemma=((f or {}).get('lemma') or {}).get('v')))
    mr = [dict(status=x.get('status'), root=x.get('root'), form_class=x.get('form_class'), reason=str(x.get('reason') or '')[:300])
          for x in a.get('morph') or []]
    level = 'ROOT_PROVEN' if any(x['status'] == 'accepted' for x in mr) else ('UNIT_CLOSED' if any(u['closed'] for u in us) else 'DEFERRED')
    return dict(execution_status='EXECUTED', level=level, units=us, morph=mr,
                wazn_output=None, wazn_output_note='الواجهة العامة لا تُخرج وزناً عربياً صريحاً (form_class وحده)')


def run(inp, out, pos_file=None):
    rows = read_blind_input(inp)
    mode = 'POS_ASSISTED_DIAGNOSTIC' if pos_file else 'BLIND'
    pos_by = {}
    if pos_file:
        head, pr = read_tsv(pos_file)
        if tuple(head) != ('id', 'pos'):
            raise SystemExit('ملف المسار التشخيصي عموداه id وpos وحدهما')
        pos_by = {r['id']: r['pos'] for r in pr}
    from sarf.catalog import Catalog
    CAT = Catalog([os.path.join(H, 'operators_catalog.jsonl'), os.path.join(H, 'operators_catalog_split_vocalized.csv')])
    meta = dict(tool=TOOL_VERSION, mode=mode, python=sys.version.split()[0], hashseed=os.environ.get('PYTHONHASHSEED'), commit=git_commit(),
                input_sha256=sha(inp), n_rows=len(rows), resources=resource_fingerprint(), policy_sha256=POLICY_SHA,
                pos_file_sha256=sha(pos_file) if pos_file else None)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(json.dumps(dict(meta=meta), ensure_ascii=False, sort_keys=True) + '\n')
        for r in rows:
            rec = dict(id=r['id'], word=r['word'], mode=mode)
            try:
                rec['A_LEXICAL_MORPH'] = _analyze_word(r['word'], pos_assisted=pos_by.get(r['id']) == 'فعل ماضٍ')
            except Exception as e:
                rec['A_LEXICAL_MORPH'] = dict(level='EXECUTION_FAILURE', execution='FAILED', error_type=type(e).__name__, error_message=str(e)[:300])
            try:
                rec['B_PUBLIC'] = _public(r['word'], CAT)
            except Exception as e:
                rec['B_PUBLIC'] = dict(execution_status='EXECUTION_FAILURE', level='EXECUTION_FAILURE', error_type=type(e).__name__,
                                       error_message=str(e)[:300])
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + '\n')
    print(f'كُتب {out}: {len(rows)} صفاً ({mode})')


# ---------- التحقق البنيوي من المخرج ----------
class InvalidAnalysis(Exception):
    pass


def validate_analysis(inp, analysis, allow_mode=('BLIND',), check_resources=True):
    """يرفض قبل أي نسبة: نقص، تكرار، زيادة، كلمة مبدلة، بصمة مدخل مخالفة، خلط أوضاع، مخطط خاطئ، اختلاف الموارد"""
    problems = []
    rows = read_blind_input(inp)
    want = {r['id']: r['word'] for r in rows}
    lines = open(analysis, encoding='utf-8').read().splitlines()
    if not lines:
        raise InvalidAnalysis(['ملف التحليل فارغ'])
    try:
        meta = json.loads(lines[0])['meta']
    except Exception:
        raise InvalidAnalysis(['السطر الأول ليس meta'])
    if meta.get('tool') != TOOL_VERSION:
        problems.append(f"أداة غير متوقعة: {meta.get('tool')}")
    if meta.get('input_sha256') != sha(inp):
        problems.append('بصمة المدخل في meta تخالف بصمة المدخل المعطى')
    if meta.get('mode') not in allow_mode:
        problems.append(f"وضع التشغيل {meta.get('mode')} غير مقبول هنا ({allow_mode})")
    if meta.get('n_rows') != len(rows):
        problems.append(f"n_rows في meta ({meta.get('n_rows')}) لا يساوي صفوف المدخل ({len(rows)})")
    if check_resources:
        cur = resource_fingerprint()
        if meta.get('resources') != cur:
            problems.append('موارد التشغيل (HFN أو شيفرة المحلّل) تخالف موارد المقارنة')
    if meta.get('policy_sha256') != POLICY_SHA:
        problems.append('سياسة المرجع تغيّرت بين التشغيل والمقارنة')
    seen = collections.Counter()
    recs = []
    for i, l in enumerate(lines[1:], 2):
        try:
            r = json.loads(l)
        except Exception:
            problems.append(f'سطر {i}: ليس JSON')
            continue
        for k in ('id', 'word', 'mode', 'A_LEXICAL_MORPH', 'B_PUBLIC'):
            if k not in r:
                problems.append(f'سطر {i}: الحقل {k} مفقود')
        if r.get('mode') != meta.get('mode'):
            problems.append(f"سطر {i}: وضع السجل {r.get('mode')} يخالف وضع الملف {meta.get('mode')}")
        A = r.get('A_LEXICAL_MORPH') or {}
        if meta.get('mode') == 'BLIND' and 'verb_morph_pos_assisted' in (A.get('branches') or {}):
            problems.append(f"سطر {i}: فرع المسار التشخيصي في تشغيلٍ أعمى")
        if A.get('level') != 'EXECUTION_FAILURE':
            for b, v in (A.get('branches') or {}).items():
                if v.get('execution_status') not in EXEC_STATES:
                    problems.append(f'سطر {i}: حالة تنفيذ غير معروفة للفرع {b}')
            if 'branches' not in A:
                problems.append(f'سطر {i}: لا فروع في المسار A')
        seen[r.get('id')] += 1
        if r.get('id') in want and want[r['id']] != r.get('word'):
            problems.append(f"سطر {i}: كلمة السجل «{r.get('word')}» تخالف كلمة المدخل «{want[r['id']]}» للمعرّف {r['id']}")
        if r.get('id') not in want:
            problems.append(f"سطر {i}: معرّف غير معروف في المدخل {r.get('id')}")
        recs.append(r)
    dup = [k for k, n in seen.items() if n > 1]
    if dup:
        problems.append(f'معرّفات مكررة في المخرج: {dup[:10]} (المجموع {len(dup)})')
    missing = [k for k in want if k not in seen]
    if missing:
        problems.append(f'صفوف ناقصة من المخرج: {missing[:10]} (المجموع {len(missing)})')
    if problems:
        raise InvalidAnalysis(problems)
    return meta, recs


# ---------- المقارنة ----------
def _hfn_presence():
    from sarf.root import hfn
    from sarf.cells import lex_index
    Hh = hfn()
    verbs = set()
    for es in Hh.index.values():
        for e in es:
            verbs.add(nfc(e['verb']))
    return Hh, verbs, lex_index()


def evaluate_row(ref, rec, group, avail):
    """صفٌّ واحد: الجذر والوزن والزوج والشكل المتحقق، كلٌّ منفصل؛ والملاحظة منفصلة عن فرضية السبب"""
    A, B = rec['A_LEXICAL_MORPH'], rec['B_PUBLIC']
    faces_ = A.get('faces') or []
    proven = A.get('proven')
    rw = ref['wazn']
    out = dict(id=rec['id'], word=rec['word'], ref_root=ref['root'], ref_wazn=rw, ref_pos=ref['pos'], ref_root_type=ref['root_type'],
               ref_wazn_status=ref['wazn_status'], ref_surface_pattern=ref['surface_pattern'], availability=avail,
               A_level=A.get('level'), A_execution=A.get('execution'), A_failed_branches=A.get('failed_branches') or [],
               A_reason=A.get('reason'), faces=faces_, unlicensed_template_roots=sorted({x['root'] for x in A.get('unlicensed_template_candidates') or []}),
               B_level=B.get('level'), B_execution=B.get('execution_status'))
    # الجذر
    out['proven_root'] = proven['root'] if proven else None
    out['root_agreement'] = (proven['root'] == ref['root']) if proven else None
    # الوزن المثبت المختار (لا العائلة)
    sel = proven.get('wazn_selected') if proven else None
    out['proven_wazn_selected'] = sel
    out['proven_wazn_source'] = proven.get('wazn_selected_source') if proven else None
    out['proven_wazn_family'] = proven.get('wazn_family') if proven else None
    if proven and rw:
        out['wazn_agreement_literal'] = (wazn_literal(sel) == wazn_literal(rw)) if sel else None
        out['wazn_agreement_convention'] = (wazn_convention(sel) == wazn_convention(rw)) if sel else None
        fam = {wazn_convention(x) for x in proven.get('wazn_family') or []} | {wazn_convention(x) for x in proven.get('wazn_candidates') or []}
        out['reference_wazn_in_family'] = 'REFERENCE_WEIGHT_INCLUDED_IN_FAMILY' if (not sel and wazn_convention(rw) in fam) else None
        out['surface_pattern_agreement'] = (wazn_convention(sel) == wazn_convention(ref['surface_pattern'])) if sel and ref['surface_pattern'] else None
    else:
        out['wazn_agreement_literal'] = out['wazn_agreement_convention'] = out['surface_pattern_agreement'] = None
        out['reference_wazn_in_family'] = None
    # المرشّحون: الجذر، والزوج في الوجه نفسه
    roots_f = {f['root'] for f in faces_}
    out['ref_root_in_faces'] = ref['root'] in roots_f
    out['ref_root_in_faces_or_templates'] = ref['root'] in roots_f or ref['root'] in out['unlicensed_template_roots']
    if rw:
        out['pair_in_same_face_literal'] = any(f['root'] == ref['root'] and f.get('wazn') and wazn_literal(f['wazn']) == wazn_literal(rw) for f in faces_)
        out['pair_in_same_face_convention'] = any(f['root'] == ref['root'] and f.get('wazn') and wazn_convention(f['wazn']) == wazn_convention(rw)
                                                  for f in faces_)
        out['pair_in_same_face_surface'] = any(f['root'] == ref['root'] and f.get('wazn') and ref['surface_pattern'] and
                                               wazn_convention(f['wazn']) == wazn_convention(ref['surface_pattern']) for f in faces_)
        out['ref_wazn_in_any_face'] = any(f.get('wazn') and wazn_convention(f['wazn']) == wazn_convention(rw) for f in faces_)
        out['wazn_sources_for_pair'] = sorted({f['wazn_source'] for f in faces_ if f['root'] == ref['root'] and f.get('wazn') and
                                               wazn_convention(f['wazn']) == wazn_convention(rw)})
    else:
        out['pair_in_same_face_literal'] = out['pair_in_same_face_convention'] = out['pair_in_same_face_surface'] = None
        out['ref_wazn_in_any_face'] = None
        out['wazn_sources_for_pair'] = []
    group_roots = {x['root'] for x in group}
    out['candidates_not_in_reference_group'] = sorted(roots_f - group_roots)
    # B
    bacc = sorted({x['root'] for x in B.get('morph') or [] if x['status'] == 'accepted' and x.get('root')})
    out['B_proven_roots'] = bacc
    out['B_root_agreement'] = (bacc == [ref['root']]) if bacc else None
    out['B_wazn_output'] = B.get('wazn_output')
    # الحماية
    P = None
    for b in ('protection',):
        br = (A.get('branches') or {}).get(b) or {}
        if br.get('execution_status') == 'EXECUTED_WITH_RESULTS':
            P = br['outputs']
    out['protection'] = P
    if A.get('level') == 'PROTECTED':
        peeled = bool(P.get('proclitics') or P.get('enclitic'))
        out['protection_assessment'] = ('PROTECTED_VIA_PEELING_WORD_IS_LEXICAL_IN_HFN' if peeled and avail['word_in_hfn_v36'] else
                                        'PROTECTED_WORD_HAS_LEXICAL_FACE_IN_HFN' if avail['word_in_hfn_v36'] else
                                        'PROTECTED_NO_LEXICAL_FACE_IN_HFN')
    # الملاحظة (ما رُئي) وفرضيات السبب (لا سبب محقق إلا بمراجعة)
    obs, hyp = [], []
    if A.get('level') == 'EXECUTION_FAILURE':
        obs.append('WORD_EXECUTION_FAILURE')
    if A.get('execution') == 'PARTIAL_EXECUTION':
        obs.append('PARTIAL_EXECUTION:' + ','.join(A.get('failed_branches')))
    if A.get('level') == 'PROTECTED':
        obs.append('PROTECTED')
    if proven:
        if proven['root'] != ref['root']:
            obs.append('PROVEN_ROOT_DIFFERS_FROM_REFERENCE')
            obs.append('REFERENCE_ROOT_AMONG_CANDIDATES' if ref['root'] in roots_f else 'REFERENCE_ROOT_NOT_AMONG_CANDIDATES')
        if rw and sel and wazn_convention(sel) != wazn_convention(rw):
            obs.append('PROVEN_WAZN_DIFFERS_FROM_REFERENCE')
            if out['surface_pattern_agreement']:
                obs.append('PROVEN_WAZN_EQUALS_REFERENCE_SURFACE_PATTERN')
        if out['reference_wazn_in_family']:
            obs.append('REFERENCE_WEIGHT_INCLUDED_IN_FAMILY')
        if proven['root'] == ref['root'] and (not rw or not sel or wazn_convention(sel) == wazn_convention(rw)):
            obs.append('AGREE_ROOT' + ('_AND_WAZN' if rw and sel else ''))
    elif A.get('level') in ('CANDIDATES_ONLY', 'NO_CANDIDATE', 'NO_CANDIDATE_WITH_FAILED_BRANCH'):
        if ref['root'] in roots_f:
            obs.append('REFERENCE_CANDIDATE_PRESENT_SELECTION_UNRESOLVED')
        elif ref['root'] in out['unlicensed_template_roots']:
            obs.append('REFERENCE_ROOT_ONLY_IN_UNLICENSED_TEMPLATE')
        else:
            obs.append('REFERENCE_ROOT_NOT_AMONG_CANDIDATES')
    si = ((A.get('branches') or {}).get('stem_info') or {}).get('outputs') or {}
    if 'REFERENCE_ROOT_NOT_AMONG_CANDIDATES' in obs or 'PROVEN_ROOT_DIFFERS_FROM_REFERENCE' in obs:
        if si.get('object') or si.get('suffix') or si.get('prefix'):
            hyp.append('PEELING_SUSPECTED')
        if not avail['word_in_hfn_v36']:
            hyp.append('WORD_ABSENT_FROM_HFN_V36_OBSERVED')
        if not set(ref['word']) & TASHKEEL or unmarked_consonants(ref['word']) >= 2:
            hyp.append('INSUFFICIENT_DIACRITICS_OBSERVED')
        r = ref['root']
        if len(r) == 3 and r[1] == r[2] and 'ّ' not in ref['word'] and sum(1 for ch in ref['word'] if ch not in TASHKEEL) == 2:
            hyp.append('GEMINATE_WITHOUT_SHADDA_OBSERVED')
        if A.get('execution') != 'COMPLETE':
            hyp.append('FAILED_BRANCH_MAY_HAVE_HIDDEN_CANDIDATE')
    if 'PROVEN_WAZN_EQUALS_REFERENCE_SURFACE_PATTERN' in obs:
        hyp.append('ANALYZER_OUTPUTS_REALIZED_FORM_NOT_MIZAN')
    if A.get('level') == 'PROTECTED':
        hyp.append(out['protection_assessment'])
    out['observations'], out['cause_hypotheses'], out['verified_cause'] = obs, hyp, None
    out['root_mismatch'] = bool(proven and proven['root'] != ref['root'])
    out['wazn_mismatch'] = bool(proven and rw and sel and wazn_convention(sel) != wazn_convention(rw))
    return out


def compute_metrics(res, recs):
    """المقاييس من سجلّ النتائج وحده (ترتيب الصفوف والمرشّحين لا يؤثر)"""
    def m_rows(rs):
        n = len(rs)
        pr = [r for r in rs if r['proven_root']]
        prw = [r for r in pr if r['ref_wazn']]
        sel = [r for r in prw if r['proven_wazn_selected']]
        withw = [r for r in rs if r['ref_wazn']]
        exe = collections.Counter(r['A_execution'] for r in rs)
        return dict(
            n=n,
            root_proven=dict(n=len(pr), agree=sum(1 for r in pr if r['root_agreement']), precision=ratio(sum(1 for r in pr if r['root_agreement']), len(pr))),
            root_coverage=ratio(len(pr), n),
            wazn_selected=dict(n=len(sel), agree_convention=ratio(sum(1 for r in sel if r['wazn_agreement_convention']), len(sel)),
                               agree_literal=ratio(sum(1 for r in sel if r['wazn_agreement_literal']), len(sel)),
                               sources=dict(collections.Counter(r['proven_wazn_source'] for r in sel))),
            wazn_selected_coverage=ratio(len(sel), len(withw)),
            proven_without_selected_wazn=dict(n=len(prw) - len(sel),
                                              reference_in_family=sum(1 for r in prw if r['reference_wazn_in_family'])),
            wazn_mismatch_rows=sum(1 for r in rs if r['wazn_mismatch']),
            root_mismatch_rows=sum(1 for r in rs if r['root_mismatch']),
            root_and_wazn_mismatch_rows=sum(1 for r in rs if r['root_mismatch'] and r['wazn_mismatch']),
            surface_pattern_agreement=ratio(sum(1 for r in sel if r['surface_pattern_agreement']), len(sel)),
            ref_root_in_faces=ratio(sum(1 for r in rs if r['ref_root_in_faces']), n),
            ref_root_in_faces_or_templates=ratio(sum(1 for r in rs if r['ref_root_in_faces_or_templates']), n),
            pair_in_same_face_convention=ratio(sum(1 for r in withw if r['pair_in_same_face_convention']), len(withw)),
            pair_in_same_face_literal=ratio(sum(1 for r in withw if r['pair_in_same_face_literal']), len(withw)),
            pair_in_same_face_surface=ratio(sum(1 for r in withw if r['pair_in_same_face_surface']), len(withw)),
            candidates_not_in_reference_group=dict(rows=sum(1 for r in rs if r['candidates_not_in_reference_group']),
                                                   total=sum(len(r['candidates_not_in_reference_group']) for r in rs)),
            B_public=dict(root_proven=ratio(sum(1 for r in rs if r['B_root_agreement']), sum(1 for r in rs if r['B_proven_roots'])),
                          coverage=ratio(sum(1 for r in rs if r['B_proven_roots']), n),
                          wazn_output_rows=sum(1 for r in rs if r['B_wazn_output']), levels=dict(collections.Counter(r['B_level'] for r in rs))),
            levels=dict(collections.Counter(r['A_level'] for r in rs)), execution=dict(exe),
            protection=dict(collections.Counter(r.get('protection_assessment') for r in rs if r['A_level'] == 'PROTECTED')),
            observations=dict(collections.Counter(o.split(':')[0] for r in rs for o in r['observations'])),
            cause_hypotheses=dict(collections.Counter(h for r in rs for h in r['cause_hypotheses'])))
    # التنفيذ: من السجلات الخام
    ex = dict(words=len(recs), words_with_any_failure=0, words_complete=0, words_partial=0, words_failed=0,
              failures_by_branch_and_type=collections.Counter(), proven_despite_other_branch_failure=0, B_failures=0)
    for r in recs:
        A = r['A_LEXICAL_MORPH']
        if A.get('level') == 'EXECUTION_FAILURE':
            ex['words_failed'] += 1
            ex['words_with_any_failure'] += 1
            ex['failures_by_branch_and_type']['WHOLE_WORD|' + A.get('error_type', '?')] += 1
            continue
        f = [(b, v['error_type']) for b, v in A['branches'].items() if v['execution_status'] == 'EXECUTION_FAILURE']
        for b, t in f:
            ex['failures_by_branch_and_type'][f'{b}|{t}'] += 1
        if f:
            ex['words_with_any_failure'] += 1
            ex['words_partial' if A['execution'] == 'PARTIAL_EXECUTION' else 'words_failed'] += 1
            if A['level'] == 'ROOT_PROVEN':
                ex['proven_despite_other_branch_failure'] += 1
        else:
            ex['words_complete'] += 1
        if r['B_PUBLIC'].get('execution_status') == 'EXECUTION_FAILURE':
            ex['B_failures'] += 1
    ex['failures_by_branch_and_type'] = dict(ex['failures_by_branch_and_type'])
    ex['branch_status'] = {}
    for r in recs:
        for b, v in (r['A_LEXICAL_MORPH'].get('branches') or {}).items():
            ex['branch_status'].setdefault(b, collections.Counter())[v['execution_status']] += 1
    ex['branch_status'] = {b: dict(c) for b, c in ex['branch_status'].items()}

    def by(key, rs):
        g = collections.defaultdict(list)
        for r in rs:
            g[key(r)].append(r)
        return {k: m_rows(v) for k, v in sorted(g.items(), key=lambda kv: (-len(kv[1]), str(kv[0])))}
    dens = collections.defaultdict(list)
    for r in res:
        dens['RAW_ALL'].append(r)
        dens[r['denominators']['root']].append(r)
    out = dict(execution=ex, denominators={k: m_rows(v) for k, v in sorted(dens.items())})
    main = dens['PROVISIONAL_REFERENCE_MAIN']
    # مقامات الوزن والزوج: حسب حقول الوزن
    wz = collections.defaultdict(list)
    for r in res:
        wz[r['denominators']['wazn']].append(r)
    out['wazn_denominators'] = {k: dict(n=len(v), wazn_selected=m_rows(v)['wazn_selected'], pair=m_rows(v)['pair_in_same_face_convention'])
                                for k, v in sorted(wz.items())}
    out['by_root_type'] = by(lambda r: r['ref_root_type'], main)
    out['by_pos'] = by(lambda r: r['ref_pos'], main)
    out['by_wazn_status'] = by(lambda r: r['ref_wazn_status'], main)
    out['by_execution'] = by(lambda r: r['A_execution'], main)
    out['by_availability'] = by(lambda r: ('word_in_v36' if r['availability']['word_in_hfn_v36'] else 'word_not_in_v36'), main)
    out['by_review_root'] = by(lambda r: r['denominators']['root'], res)
    # الكلمات: نتيجة الكلمة من مجموعة أوجهها في dev (لا أول صف)
    W = collections.defaultdict(list)
    for r in main:
        W[nfc(r['word'])].append(r)
    wres = []
    for w, rs in sorted(W.items()):
        group = {x['ref_root'] for x in rs}
        pr = {x['proven_root'] for x in rs if x['proven_root']}
        if len(pr) > 1:
            raise SystemExit(f'كلمةٌ واحدة بجذرين مثبتين مختلفين في صفوفها: {w}')
        cands = set().union(*[{f['root'] for f in x['faces']} for x in rs])
        wres.append(dict(word=w, n_faces=len(rs), group_roots=sorted(group), proven=next(iter(pr), None),
                         proven_in_group=(next(iter(pr)) in group) if pr else None,
                         any_group_root_in_candidates=bool(group & cands), all_group_roots_in_candidates=group <= cands))
    nw = len(wres)
    pw = [x for x in wres if x['proven']]
    out['distinct_words'] = dict(n=nw, multi_face=sum(1 for x in wres if x['n_faces'] > 1),
                                 proven=ratio(sum(1 for x in pw if x['proven_in_group']), len(pw)), coverage=ratio(len(pw), nw),
                                 any_group_root_in_candidates=ratio(sum(1 for x in wres if x['any_group_root_in_candidates']), nw),
                                 all_group_roots_in_candidates=ratio(sum(1 for x in wres if x['all_group_roots_in_candidates']), nw))
    R = collections.defaultdict(list)
    for r in main:
        R[r['ref_root']].append(r)
    out['distinct_roots'] = dict(n=len(R), any_row_proven_correct=sum(1 for v in R.values() if any(x['root_agreement'] for x in v)),
                                 any_row_proven_wrong=sum(1 for v in R.values() if any(x['root_agreement'] is False for x in v)),
                                 all_rows_ref_root_in_faces=sum(1 for v in R.values() if all(x['ref_root_in_faces'] for x in v)))
    return out


def compare(pkg, inp, analysis, out_dir, corrections=None, allow_mode=('BLIND',)):
    try:
        meta, recs = validate_analysis(inp, analysis, allow_mode=allow_mode)
    except InvalidAnalysis as e:
        os.makedirs(out_dir, exist_ok=True)
        json.dump(dict(valid=False, problems=e.args[0]), open(os.path.join(out_dir, 'validation.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        raise SystemExit('ملف التحليل غير صالح بنيوياً؛ لا مقاييس:\n  ' + '\n  '.join(e.args[0][:20]))
    head, rows = read_tsv(os.path.join(pkg, 'testset_all.tsv'))
    ids = [r['id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit('المرجع فيه معرّفات مكررة: يُرفض قبل القياس')
    ref_by = {r['id']: r for r in rows}
    if any(ref_by.get(r['id'], {}).get('split') != 'dev' for r in recs):
        raise SystemExit('صفٌّ من غير dev في التحليل: ممنوع (RUN_HELDOUT_INFERENCE = NO)')
    for r in recs:
        if nfc(ref_by[r['id']]['word']) != nfc(r['word']):
            raise SystemExit(f"كلمة السجل تخالف كلمة المرجع للمعرّف {r['id']}")
    corr = load_corrections(corrections)
    groups = reference_groups(rows, corr, 'dev')
    Hh, hverbs, LEX = _hfn_presence()
    from sarf.cells import _lex_key
    res = []
    for rec in sorted(recs, key=lambda r: r['id']):
        ref = ref_by[rec['id']]
        avail = dict(root_in_hfn_v36=ref['root'] in Hh.roots, word_in_hfn_v36=nfc(ref['word']) in hverbs or _lex_key(ref['word']) in LEX)
        A = rec['A_LEXICAL_MORPH']
        if A.get('level') != 'EXECUTION_FAILURE':
            again = assemble(dict(branches=A['branches']))
            if json.dumps(again, sort_keys=True, ensure_ascii=False) != json.dumps({k: A[k] for k in again}, sort_keys=True, ensure_ascii=False):
                raise SystemExit(f"الأوجه المسجّلة لا تُشتق من الفروع للمعرّف {rec['id']}")
        else:
            A.setdefault('faces', [])
            A.setdefault('execution', 'FAILED')
        r = evaluate_row(ref, rec, groups[nfc(ref['word'])], avail)
        r['field_review'] = {f: field_status(rec['id'], f, corr) for f in ('word', 'root', 'wazn', 'pos')}
        r['denominators'] = denominators_for(rec['id'], corr)
        res.append(r)
    M = compute_metrics(res, recs)
    M['meta'] = dict(analysis_meta=meta, analysis_sha256=sha(analysis), input_sha256=sha(inp),
                     reference_sha256=sha(os.path.join(pkg, 'testset_all.tsv')), corrections_sha256=sha(corrections) if corrections else None,
                     policy=REFERENCE_POLICY, policy_sha256=POLICY_SHA, compare_commit=git_commit(),
                     scope='dev فقط؛ الاختبار المحجوب لم يُشغَّل')
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'dev_results.jsonl'), 'w', encoding='utf-8') as f:
        for r in res:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    json.dump(M, open(os.path.join(out_dir, 'dev_metrics.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
    json.dump(dict(valid=True, problems=[]), open(os.path.join(out_dir, 'validation.json'), 'w', encoding='utf-8'))
    main = M['denominators']['PROVISIONAL_REFERENCE_MAIN']
    print(json.dumps(dict(execution={k: M['execution'][k] for k in ('words', 'words_with_any_failure', 'words_complete', 'words_partial')},
                          main_n=main['n'], root_proven=main['root_proven'], ref_root_in_faces=main['ref_root_in_faces']['value'],
                          pair=main['pair_in_same_face_convention']['value']), ensure_ascii=False))
    return M, res


# ---------- إفساد المخرج الحقيقي ----------
def corrupt_check(pkg, inp, analysis, out):
    import tempfile
    lines = open(analysis, encoding='utf-8').read().splitlines()
    meta = json.loads(lines[0])
    body = lines[1:]
    cases = {}

    def write(name, ls):
        p = os.path.join(td, name + '.jsonl')
        open(p, 'w', encoding='utf-8').write('\n'.join(ls) + '\n')
        return p

    def setmeta(**kw):
        m = json.loads(lines[0])
        m['meta'].update(kw)
        return json.dumps(m, ensure_ascii=False, sort_keys=True)

    def edit(i, fn):
        r = json.loads(body[i])
        fn(r)
        return body[:i] + [json.dumps(r, ensure_ascii=False, sort_keys=True)] + body[i + 1:]

    def swap_word(r):
        r['word'] = r['word'] + 'ا'

    def unknown_id(r):
        r['id'] = 'MT999999'

    def pos_mode(r):
        r['mode'] = 'POS_ASSISTED_DIAGNOSTIC'

    def add_pos_branch(r):
        r['A_LEXICAL_MORPH'].setdefault('branches', {})['verb_morph_pos_assisted'] = dict(
            branch='verb_morph_pos_assisted', execution_status='EXECUTED_EMPTY', error_type=None, error_message=None, outputs=None)

    def drop_branches(r):
        r['A_LEXICAL_MORPH'].pop('branches', None)

    def forge_face(r):
        r['A_LEXICAL_MORPH']['faces'] = r['A_LEXICAL_MORPH'].get('faces', []) + [dict(root='زيف', kind='فعل', branch='verb_morph')]
    res = meta['meta']['resources']
    bad_res = json.loads(json.dumps(res))
    bad_res['hfn_files']['HFN/lexical_units.csv'] = '0' * 64
    with tempfile.TemporaryDirectory() as td:
        specs = dict(
            missing_row=[lines[0]] + body[:-1],
            duplicate_row=[lines[0]] + body + [body[0]],
            unknown_id=[lines[0]] + edit(0, unknown_id),
            swapped_word=[lines[0]] + edit(1, swap_word),
            input_sha_mismatch=[setmeta(input_sha256='0' * 64)] + body,
            mode_mixed_record=[lines[0]] + edit(2, pos_mode),
            pos_branch_in_blind=[lines[0]] + edit(3, add_pos_branch),
            file_mode_pos=[setmeta(mode='POS_ASSISTED_DIAGNOSTIC')] + body,
            schema_missing_branches=[lines[0]] + edit(4, drop_branches),
            forged_face_not_from_branches=[lines[0]] + edit(5, forge_face),
            resources_differ=[setmeta(resources=bad_res)] + body,
            policy_changed=[setmeta(policy_sha256='0' * 64)] + body)
        for name, ls in specs.items():
            p = write(name, ls)
            try:
                compare(pkg, inp, p, os.path.join(td, 'cmp_' + name))
                cases[name] = dict(refused=False)
            except SystemExit as e:
                cases[name] = dict(refused=True, message=str(e)[:400])
    rep = dict(analysis_sha256=sha(analysis), cases=cases, all_refused=all(v['refused'] for v in cases.values()))
    json.dump(rep, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"إفساد: {sum(v['refused'] for v in cases.values())}/{len(cases)} مرفوضة")
    return rep


# ---------- التشخيص المسمّى ----------
NAMED = ['ادَّخَرَ', 'اسْتَكْتَمَ', 'نَمِشْ', 'تَبَرَّكَ', 'تَحَرَّكَ', 'نَاقِه', 'فَتَكَ', 'سَمِنَ', 'كَمَنَ', 'ضَارِب']


def diagnose(out, words=None, pkg=None):
    from sarf.catalog import Catalog
    CAT = Catalog([os.path.join(H, 'operators_catalog.jsonl'), os.path.join(H, 'operators_catalog_split_vocalized.csv')])
    ref = {}
    if pkg:
        _, rows = read_tsv(os.path.join(pkg, 'testset_all.tsv'))
        for r in rows:
            if r['split'] == 'dev':
                ref.setdefault(nfc(r['word']), []).append(dict(id=r['id'], root=r['root'], wazn=r['wazn'], pos=r['pos']))
    recs = []
    for w in words or NAMED:
        A = _analyze_word(w)
        B = _public(w, CAT)
        Bm = B['morph']
        si = A['branches']['stem_info']['outputs'] or {}
        recs.append(dict(word=w, peeling_proposed=si, protection=A['branches']['protection']['outputs'],
                         level=A['level'], execution=A['execution'], reason=A['reason'],
                         faces=[dict(candidate_id=f['candidate_id'], root=f['root'], wazn=f.get('wazn'), wazn_source=f.get('wazn_source'),
                                     kind=f['kind'], branch=f['branch'], evidence=f.get('evidence')) for f in A['faces']],
                         proven=A['proven'], B_public_morph=Bm, B_level=B['level'], reference_dev=ref.get(nfc(w), []),
                         branch_status={b: v['execution_status'] for b, v in A['branches'].items()}))
    json.dump(recs, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in recs:
        print(r['word'], r['level'], r['execution'], [(f['root'], f['wazn'], f['branch']) for f in r['faces']][:4],
              (r['protection'] or {}).get('identity'), [x['root'] for x in r['B_public_morph'] if x['status'] == 'accepted'])
    return recs


# ---------- مقارنة الجولتين ----------
def diff_runs(rw01_analysis, rw01_results, rw02_analysis, rw02_dir, out):
    old_a = {json.loads(l)['id']: json.loads(l) for l in open(rw01_analysis, encoding='utf-8').read().splitlines()[1:]}
    old_r = {json.loads(l)['id']: json.loads(l) for l in open(rw01_results, encoding='utf-8')}
    new_a = {json.loads(l)['id']: json.loads(l) for l in open(rw02_analysis, encoding='utf-8').read().splitlines()[1:]}
    new_r = {json.loads(l)['id']: json.loads(l) for l in open(os.path.join(rw02_dir, 'dev_results.jsonl'), encoding='utf-8')}
    if set(old_a) != set(new_a):
        raise SystemExit('مجموعتا الصفوف مختلفتان بين الجولتين')
    C = collections.Counter()
    rows = []
    for i in sorted(new_a):
        oa, na = old_a[i]['A_LEXICAL_MORPH'], new_a[i]['A_LEXICAL_MORPH']
        o_faces = {(f['root'], f.get('wazn') or None) for f in oa.get('faces') or [] if f['source'].startswith('RULE+RETRIEVAL')}
        n_vm = {(f['root'], f.get('wazn') or None) for f in na.get('faces') or [] if f['branch'] == 'verb_morph'}
        o_lex = {f['root'] for f in oa.get('faces') or [] if f['source'].startswith('RETRIEVAL')}
        n_lex = {f['root'] for f in na.get('faces') or [] if f['branch'] == 'lexical_retrieval'}
        n_part = {f['root'] for f in na.get('faces') or [] if f['branch'] == 'participle'}
        same_vm = o_faces == {(r, w if w is None else hfn_form_wazn(w)) for r, w in n_vm}
        same_morph = (oa.get('morph') or {}).get('status') == ((na['branches']['verb_morph'].get('outputs') or {}).get('status')) and \
            (oa.get('morph') or {}).get('root') == ((na['branches']['verb_morph'].get('outputs') or {}).get('root'))
        same_prot = ((oa.get('protected') or {}).get('identity')) == ((na['branches']['protection'].get('outputs') or {}) or {}).get('identity')
        same_B = [x['root'] for x in old_a[i]['B_PUBLIC'].get('morph') or [] if x['status'] == 'accepted'] == \
            [x['root'] for x in new_a[i]['B_PUBLIC'].get('morph') or [] if x['status'] == 'accepted']
        o, n = old_r[i], new_r[i]
        ref_root = n['ref_root']
        o_in, n_in = o['root_in_candidates'], n['ref_root_in_faces']
        why = []
        if not (same_vm and same_morph and same_prot and same_B and o_lex == n_lex):
            why.append('ANALYZER_OUTPUT_CHANGED')          # لا يُتوقّع: المحلّل لم يتغيّر
        if n_part:
            why.append('PARTICIPLE_BRANCH_NOW_EXECUTES')
        if o_in != n_in:
            why.append('RECALL_CHANGED_BY_PARTICIPLE_FIX' if (ref_root in n_part and ref_root not in o_lex | {r for r, _ in o_faces}) else 'RECALL_CHANGED_OTHER')
        o_den = 'FLAGGED' if o['row_review'] in ('DISPUTED', 'REVIEW_REQUIRED') else 'MAIN'
        n_den = 'FLAGGED' if n['denominators']['root'] == 'PROVISIONAL_REFERENCE_FLAGGED' else 'MAIN'
        if o_den != n_den:
            why.append('DENOMINATOR_CHANGED_BY_POLICY')
        o_lvl, n_lvl = o['A_level'], n['A_level']
        if o_lvl != n_lvl:
            why.append(f'LEVEL:{o_lvl}->{n_lvl}')
        if o['category'] == 'CONTEXT_REQUIRED':
            why.append('RW01_CONTEXT_REQUIRED_RELABELLED_' + ('SELECTION_UNRESOLVED' if 'REFERENCE_CANDIDATE_PRESENT_SELECTION_UNRESOLVED' in n['observations'] else 'OTHER'))
        if (o['root_proven_correct'] is False) and n['root_mismatch']:
            why.append('REMAINS_ROOT_MISMATCH')
        if o['category'] == 'WAZN_ERROR' and not n['wazn_mismatch']:
            why.append('RW01_WAZN_ERROR_NOT_A_SELECTED_WAZN_MISMATCH_IN_RW02')
        if o['category'] == 'WAZN_ERROR' and n['wazn_mismatch']:
            why.append('REMAINS_WAZN_MISMATCH')
        if n['denominators']['root'] == 'PROVISIONAL_REFERENCE_FLAGGED':
            why.append('REMAINS_FLAGGED_REFERENCE')
        for w in why:
            C[w.split(':')[0] if w.startswith('LEVEL') else w] += 1
            if w.startswith('LEVEL'):
                C[w] += 1
        if why:
            rows.append(dict(id=i, word=n['word'], ref_root=ref_root, rw01_category=o['category'], rw01_level=o_lvl, rw02_level=n_lvl,
                             rw02_observations=n['observations'], changes=why))
    rep = dict(rows=len(new_a), counts=dict(sorted(C.items())), analyzer_output_changed=C.get('ANALYZER_OUTPUT_CHANGED', 0), changed_rows=rows)
    json.dump(rep, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(rep['counts'], ensure_ascii=False))
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd')
    ap.add_argument('args', nargs='*')
    ap.add_argument('--split')
    ap.add_argument('--corrections')
    ap.add_argument('--pos-assisted')
    ap.add_argument('--pkg')
    ap.add_argument('--read-ids')
    a = ap.parse_args()
    sys.path.insert(0, H)
    if a.cmd == 'audit':
        audit(*a.args)
    elif a.cmd == 'exposure':
        exposure(*a.args, extra_read=(a.read_ids.split(',') if a.read_ids else None))
    elif a.cmd == 'faces':
        faces(*a.args, corrections=a.corrections)
    elif a.cmd == 'blind-input':
        blind_input(*a.args, split=a.split)
    elif a.cmd == 'run':
        run(*a.args, pos_file=a.pos_assisted)
    elif a.cmd == 'compare':
        compare(*a.args, corrections=a.corrections)
    elif a.cmd == 'compare-pos':
        compare(*a.args, corrections=a.corrections, allow_mode=('POS_ASSISTED_DIAGNOSTIC',))
    elif a.cmd == 'corrupt-check':
        corrupt_check(*a.args)
    elif a.cmd == 'diagnose':
        diagnose(a.args[0], a.args[1:] or None, pkg=a.pkg)
    elif a.cmd == 'diff-runs':
        diff_runs(*a.args)
    else:
        ap.error('أمرٌ غير معروف')


if __name__ == '__main__':
    main()
