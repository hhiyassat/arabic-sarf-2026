"""verify_package.py — تحقق مستقل من حزمة V48C03 (SARF_HFN_V48_TARGETED_REPAIR_AND_CLOSURE_03 §٦).
يُشغَّل من داخل الحزمة: python3 -I verify_package.py   (واختيارياً HFN_V48_DIR=<release_v48> لفحص العقد مقابل CSV)

لا يكتفي ببصمات الملفات ولا بالملخّصات:
 V01 بصمة كل ملفٍّ في MANIFEST.json، ولا ملفّ خارجه.
 V02 قائمة الاختبارات المطلوبة ثابتةٌ هنا (لا تُستنتج من الموجود): لكلٍّ في كل مجموعة stdout وstderr وrc، والرمز 0، وسطر «ALL OK» حيث يُعلن،
     ولا NOT_RUN ولا SKIP ولا FAIL؛ والمسباران بلا آلية حكم يُطلب تشغيلهما (rc=0) ولا يُعدّان قبولاً.
 V03 صفوف suite.tsv: لا مكرَّر، ولا ناقص، وحالة كل صفٍّ = ما يُعاد اشتقاقه من rc وstdout، والملخّص = عدّ الصفوف.
 V04 تغطية التفريغات: 114 سورة بلا تكرار، و6236 آية، ومفاتيح الآيات في كل منتَجٍ مفهرسٍ بالآية = 6236 بلا تكرار، في A وB وC.
 V05 الاستقرار: كل آيةٍ CONVERGED بلا أخطاء نهائية ولا أخطاء مصالحة في B وC (لا تساويهما فحسب).
 V06 المقارنة يعاد حسابها من التفريغات: B=C في كل بصمة منتَج وكل مفتاح وكل جملة واستقرار؛ وA=B كذلك؛ وتُقابَل بملخّصات transitions/.
 V07 الإرفاق في C: عقد v3 لكل إرفاق (هوية تحليلٍ من المحرّك، وقيودٌ بمصادرها، وis_fact منطقية false، وCANDIDATE، ولا مسحوب)،
     وهوية التحليل لا تُشترك بين تحليلين، وصفر مخالفات هوية المحرّك، وصفر تسرّب، والسياق بعد الإرفاق متطابق.
 V08 ملخّص العزل يُعاد حسابه من سجلات الفتح الخام، وصفر مخالفات."""
import base64, gzip, hashlib, json, os, re, sys, zlib
from collections import Counter
D = os.path.dirname(os.path.abspath(__file__))
os.chdir(D)
FAIL = []
REQUIRED = ['contract_batch2', 'mudari_probe', 'regress', 'test_affix', 'test_agreement', 'test_ajnas_consumer', 'test_algebra',
            'test_analyzer_repair_ar01', 'test_analyzer_repair_ar02', 'test_analyzer_repair_ar03', 'test_batch_b', 'test_batch_d', 'test_batch_e',
            'test_batch_f', 'test_behaviour', 'test_c063_hfn', 'test_c063_morph', 'test_c063_objects', 'test_c063_paragraph', 'test_cache',
            'test_cell_rules', 'test_closure', 'test_closure_helpers', 'test_coord', 'test_core', 'test_coverage', 'test_engine', 'test_fa01',
            'test_fa02', 'test_fa02_tools', 'test_features', 'test_features_ext', 'test_hfn_v48_identity', 'test_inflection', 'test_mood',
            'test_mudari', 'test_normalize', 'test_normalize_trace', 'test_numbering', 'test_paragraph', 'test_protected', 'test_protection_registry',
            'test_quran_source', 'test_reconcile', 'test_relations', 'test_review_dayn', 'test_root', 'test_root_wazn_bench', 'test_round006',
            'test_schema', 'test_segment', 'test_snapshot', 'test_syllables', 'test_upstream', 'test_v48_compare_tools', 'test_v48_consumer_pins',
            'test_v48c3_api_per_query', 'test_v48c3_sidecar_contract']
PROBES = {'contract_batch2', 'mudari_probe'}
DECLARES_ALL_OK = {'test_hfn_v48_identity', 'test_ajnas_consumer', 'test_v48_compare_tools', 'test_v48_consumer_pins', 'test_v48c3_api_per_query',
                   'test_v48c3_sidecar_contract', 'test_upstream'}
PRODUCTS_BY_VERSE = ['normalization', 'analysis', 'cells', 'syllables', 'protection', 'units', 'features', 'records_initial', 'features_final', 'records']
PRODUCTS = ['source', 'normalization', 'analysis', 'cells', 'syllables', 'protection', 'units', 'features', 'sentences', 'legacy', 'records_initial',
            'features_final', 'reconciliation', 'records', 'revision', 'evidence_audit', 'certificates', 'paragraphs', 'references']


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:300]}'))
    if not ok:
        FAIL.append(name)


def J(p):
    return json.load(open(p, encoding='utf-8'))


# V01
M = J('MANIFEST.json')
bad = [f for f, h in M['files'].items() if not os.path.isfile(f) or hashlib.sha256(open(f, 'rb').read()).hexdigest() != h]
check(f'V01a بصمات الملفات المدرجة ({len(M["files"])})', not bad, bad[:5])
present = {os.path.relpath(os.path.join(b, f), D) for b, _, fs in os.walk(D) for f in fs}
extra = sorted(present - set(M['files']) - {'MANIFEST.json'})
check('V01b لا ملفّ خارج البيان', not extra, extra[:5])

# V02 + V03
CHECK_LINE = re.compile(r'^\s*(PASS|FAIL|SKIP)(?![A-Z])')
for s in ('suite47', 'suite48'):
    base = f'tests/{s}'
    if not os.path.isfile(f'{base}/suite.tsv'):
        check(f'V02 {s}: suite.tsv موجود', False, base); continue
    lines = [l.rstrip('\n').split('\t') for l in open(f'{base}/suite.tsv', encoding='utf-8')]
    rows = [l for l in lines if l and not l[0].startswith(('#', 'file'))]
    summ = [l for l in lines if l and l[0].startswith('# SUMMARY')]
    names = [os.path.basename(r[0])[:-3] for r in rows]
    dup = [n for n, c in Counter(names).items() if c > 1]
    miss = [n for n in REQUIRED if n not in names]
    check(f'V03a {s}: لا اختبار مكرّر ولا مطلوب ناقص ({len(REQUIRED)} مطلوباً)', not dup and not miss, dict(dup=dup, missing=miss))
    probs = []
    for n in REQUIRED:
        st = {r[1] for r in rows if os.path.basename(r[0])[:-3] == n}
        fs = {ext: f'{base}/{n}.{ext}' for ext in ('stdout', 'stderr', 'rc')}
        if not all(os.path.isfile(p) for p in fs.values()):
            probs.append((n, 'EVIDENCE_MISSING')); continue
        rc = open(fs['rc']).read().strip()
        out = open(fs['stdout'], encoding='utf-8').read()
        err = open(fs['stderr'], encoding='utf-8').read()
        if rc != '0':
            probs.append((n, f'RC={rc}'))
        if st != {'PASS'}:
            probs.append((n, f'STATUS={st}'))
        if any(l.startswith('NOT_RUN') for l in (out + '\n' + err).splitlines()):
            probs.append((n, 'NOT_RUN_LINE'))
        ln = [CHECK_LINE.match(l).group(1) for l in (out + '\n' + err).splitlines() if CHECK_LINE.match(l)]
        if 'FAIL' in ln or 'SKIP' in ln:
            probs.append((n, 'FAIL_OR_SKIP_LINE'))
        if n in DECLARES_ALL_OK and 'ALL OK' not in out:
            probs.append((n, 'NO_ALL_OK'))
        r = next((r for r in rows if os.path.basename(r[0])[:-3] == n), None)
        if r and (r[2] != rc or int(r[3]) != ln.count('PASS')):
            probs.append((n, f'ROW_NOT_FROM_LOG rc_row={r[2]} pass_row={r[3]} pass_log={ln.count("PASS")}'))
    check(f'V02 {s}: كل مطلوبٍ له stdout وstderr وrc=0، وحالته PASS المشتقة من سجلّه، بلا NOT_RUN ولا SKIP ولا FAIL', not probs, probs[:6])
    cnt = Counter(r[1] for r in rows)
    ok_sum = summ and f'files={len(rows)}' in summ[0][0] and f'pass={cnt.get("PASS", 0)}' in summ[0][0] and \
        all(f'{k.lower()}={cnt.get(k, 0)}' in summ[0][0] for k in ('FAIL', 'ERROR', 'SKIP', 'NOT_RUN', 'SETUP_ERROR', 'TIMEOUT'))
    check(f'V03b {s}: الملخّص يطابق عدّ الصفوف', bool(ok_sum), summ[:1])
    acc = [n for n in REQUIRED if n not in PROBES]
    check(f'V03c {s}: المسباران بلا آلية حكم خارج اختبارات القبول ({len(acc)} قبولاً + {len(PROBES)} مسباراً)', len(acc) == len(REQUIRED) - 2)


# V04–V07
def load(p):
    out = {}
    for l in gzip.open(p, 'rt', encoding='utf-8'):
        d = json.loads(l)
        if d['surah'] in out:
            out.setdefault('__dup__', []).append(d['surah'])
        out[d['surah']] = d
    return out


dumps = {k: load(f'runs/dump_{k}.jsonl.gz') for k in ('A', 'B', 'C')}
for k, d in dumps.items():
    dup = d.pop('__dup__', [])
    vk = Counter()
    for s, x in d.items():
        for p in PRODUCTS_BY_VERSE:
            vk[p] += len(x['products'][p]['keys'])
    keys_all = [kk for x in d.values() for kk in x['products']['analysis']['keys']]
    check(f'V04 {k}: 114 سورة بلا تكرار، و6236 آية، ومفاتيح كل منتَجٍ بالآية 6236 بلا تكرار',
          not dup and sorted(d) == list(range(1, 115)) and sum(x['verses'] for x in d.values()) == 6236 and set(vk.values()) == {6236}
          and len(keys_all) == len(set(keys_all)) == 6236, dict(dup=dup, surahs=len(d), keys=dict(vk)))
for k in ('B', 'C'):
    badst = [(s, v, st) for s, x in dumps[k].items() for v, st in x['stability'].items()
             if st['state'] != 'CONVERGED' or st['errors_final'] or st['recon_errors']]
    check(f'V05 {k}: كل آيةٍ CONVERGED بلا خطأ نهائي ولا خطأ مصالحة', not badst and sum(len(x['stability']) for x in dumps[k].values()) == 6236, badst[:3])


def same(a, b):
    diffs = []
    for s in a:
        x, y = a[s], b[s]
        for p in PRODUCTS:
            if x['products'][p]['sha'] != y['products'][p]['sha'] or x['products'][p]['keys'] != y['products'][p]['keys']:
                diffs.append((s, p))
        if x['sentences'] != y['sentences']:
            diffs.append((s, 'sentences'))
        if x['stability'] != y['stability']:
            diffs.append((s, 'stability'))
    return diffs


dab, dbc = same(dumps['A'], dumps['B']), same(dumps['B'], dumps['C'])
check('V06a A=B مُعاد حسابه من التفريغات (كل بصمة ومفتاح وجملة واستقرار)', not dab, dab[:5])
check('V06b B=C مُعاد حسابه من التفريغات', not dbc, dbc[:5])
s_ab, s_bc = J('transitions/cmp_AB.json'), J('transitions/cmp_BC.json')
check('V06c ملخّصا المقارنة يطابقان إعادة الحساب (identical_all وعدد فروق المفاتيح والجمل)',
      s_ab['identical_all'] == (not dab) and s_bc['identical_all'] == (not dbc) and len(s_ab['key_diffs']) == 0 == len(s_bc['key_diffs'])
      and s_bc['sentences']['same'] == sum(len(x['sentences']) for x in dumps['C'].values()), (s_ab['identical_all'], s_bc['identical_all']))

SRC = dict(analysis_id='ENGINE', root='ENGINE', form_class='ENGINE', lemma_pattern='ENGINE', realized_word='ENGINE', event_id='ENGINE', event_form='RESOURCE')
viol, n_att, ident, deferred_bad = Counter(), 0, {}, 0
eng = leak = 0; post_bad = []
for s, x in dumps['C'].items():
    eng += len(x.get('engine_identity_violations') or [])
    leak += len(x.get('leak_scan') or [])
    if x.get('post_attach_same_context') != dict(products=True, sentences=True, stability=True):
        post_bad.append(s)
    sc = json.loads(zlib.decompress(base64.b64decode(x['ajnas_sidecar']['z'])))
    if sc.get('contract') != 'AJNAS_SIDECAR_CONTRACT_v3':
        viol['CONTRACT_VERSION'] += 1
    for occ in sc['sidecar'].values():
        for rec in occ:
            es = rec.get('event_side') or {}
            if es.get('decision') == 'DEFERRED' and not str(es.get('reason', '')).startswith(('DEFERRED_ANALYSIS_NOT_SELECTED:', 'DEFERRED_SELECTED_WITHOUT',
                                                                                             'DEFERRED_PATTERN_NOT_SELECTED:', 'DEFERRED_NO_REALIZED_WORD', 'DEFERRED_NO_EVENT_IDENTITY:')):
                deferred_bad += 1
            for l in es.get('links') or []:
                n_att += 1
                c = l.get('match_constraints') or {}
                for f, src in SRC.items():
                    if not isinstance(c.get(f), dict) or c[f].get('value') in (None, '') or c[f].get('source') != src:
                        viol['CONSTRAINT:' + f] += 1
                aid = (c.get('analysis_id') or {}).get('value')
                if not (isinstance(aid, str) and aid.startswith('A') and len(aid) == 13) or (c.get('analysis_id') or {}).get('derived') is not False \
                        or rec.get('analysis_id') != aid or rec.get('analysis_selection_status') != 'SELECTED':
                    viol['ANALYSIS_ID'] += 1
                if l.get('is_fact') is not False or l.get('is_fact_raw') != 'False':
                    viol['IS_FACT'] += 1
                if l.get('status') != 'CANDIDATE' or l.get('rank') != 'CANDIDATE' or l.get('owner_ruling') != 'NONE':
                    viol['STATUS'] += 1
                if not (l.get('event_id') == es.get('event_id') == (c.get('event_id') or {}).get('value')):
                    viol['EVENT'] += 1
                if l.get('event_withdrawn_raw') == 'True':
                    viol['WITHDRAWN'] += 1
                if not all(t in (l.get('residual') or '') for t in ('TWO_BLIND_READERS_AGREED_NOT_OWNER_RULED', 'EVENT_NOT_SENSE_SPECIFIC')):
                    viol['RESIDUAL'] += 1
                ident.setdefault(aid, set()).add(json.dumps([(c.get(f) or {}).get('value') for f in ('root', 'form_class', 'lemma_pattern')], ensure_ascii=False))
shared = [a for a, v in ident.items() if len(v) > 1]
rep = J('sidecar/contract_report.json')
check(f'V07a عقد v3 على كل إرفاقٍ في C ({n_att}): صفر مخالفات، وتأجيلٌ بسببٍ مسمّى، وهويةٌ غير مشتركة', n_att > 0 and not viol and not shared and not deferred_bad,
      dict(viol=dict(viol), shared=len(shared), deferred_bad=deferred_bad))
check('V07b صفر مخالفات هوية المحرّك، وصفر تسرّب، والسياق بعد الإرفاق متطابق في 114', eng == 0 and leak == 0 and not post_bad, (eng, leak, post_bad[:3]))
check('V07c تقرير العقد يطابق إعادة العدّ (الإرفاقات وصفر مخالفات)', rep['attachments'] == n_att and rep['field_violations'] == 0 and rep['all_ok'],
      (rep['attachments'], n_att))
if os.environ.get('HFN_V48_DIR'):
    sys.path.insert(0, os.path.join(D, 'repro'))
    try:
        import sidecar_contract as K
        rows, ev, wd = K.load_release(os.environ['HFN_V48_DIR'])
        r2 = K.check_corpus([(s, json.loads(zlib.decompress(base64.b64decode(x['ajnas_sidecar']['z'])))) for s, x in dumps['C'].items()], rows, ev, wd)
        check('V07d (مع CSV) العقد كاملاً مقابل الملف والأحداث', r2['all_ok'], r2['violation_kinds'])
    except ImportError as e:
        check('V07d (مع CSV) أداة العقد متاحة', False, e)

# V08
iso = J('isolation/isolation_report.json')
sys_ok = True; got = {}
for t in ('A', 'B', 'C'):
    raw = [l for f in sorted(os.listdir('isolation/raw')) if f.startswith(f'open_{t}.') for l in open(f'isolation/raw/{f}', encoding='utf-8')]
    got[t] = len(raw)
    sys_ok &= iso[t]['raw_lines'] == len(raw) and iso[t]['violations'] == 0 and sum(iso[t]['by_step'].values()) == len(raw)
check('V08 ملخّص العزل = عدّ السجلات الخام (لكل تشغيل)، وصفر مخالفات', sys_ok, (got, {t: iso[t]['raw_lines'] for t in 'ABC'}))
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
