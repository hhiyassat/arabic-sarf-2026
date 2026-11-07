# -*- coding: utf-8 -*-
"""اختبارات أداة القياس RW02 (SARF_ROOT_WAZN_BENCHMARK_REPAIR_02). لا تحتاج الحزمة: تُبنى حزمةٌ مصطنعة صغيرة.
العزل (من RW01): I1 المدخل (id، word) وحدهما · I2 test مرفوض · I3 قلب الأجوبة لا يغيّر المخرج · I4 الترتيب لا يغيّر مخرج الصف
المشتقات: P1 فاعل سالم · P2 مفعول سالم · P3 معتلّ ومهموز · P4 لا مطابقة · P5 مدخلٌ غير صالح إخفاقٌ مسمّى
الإلزامية (§15): M1…M16
Unicode: U1 NFC يوحّد ترتيباً مختلفاً دون فقد علامة · U2 لا تجريد ولا تسوية · U3 الحرفي منفصل عن الاتفاقية"""
import copy, json, os, random, subprocess, sys, tempfile, unicodedata

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
sys.path.insert(0, os.path.join(H, 'tools'))
import root_wazn_bench as B

FAILS = []


def check(name, ok, info=''):
    print(('ok  ' if ok else 'FAIL') + ' ' + name + (' — ' + str(info)[:300] if info and not ok else ''))
    if not ok:
        FAILS.append(name)


# (id، split، root، word، pos، wazn، surface)
ROWS = [('MTX01', 'dev', 'كتب', 'كَتَبَ', 'فعل ماضٍ', 'فَعَلَ', 'فَعَلَ'),
        ('MTX02', 'dev', 'ضرب', 'ضَارِب', 'اسم فاعل', 'فَاعِل', 'فَاعِل'),
        ('MTX03', 'dev', 'ضرب', 'مَضْرُوب', 'اسم مفعول', 'مَفْعُول', 'مَفْعُول'),
        ('MTX04', 'test', 'قول', 'قَالَ', 'فعل ماضٍ', 'فَعَلَ', 'فَعَلَ'),
        ('MTX05', 'dev', 'صبر', 'اِصْطَبَرَ', 'فعل ماضٍ', 'افْتَعَلَ', 'افْتَعَلَ'),
        ('MTX06', 'dev', 'بيت', 'بَيْت', 'مصدر', 'فَعْل', 'فَعْل'),
        ('MTX07', 'dev', 'كرم', 'أَكْرَمَ', 'فعل ماضٍ', 'أَفْعَلَ', 'أَفْعَلَ')]


def pkg(d, rows=ROWS, wrong=False):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'testset_all.tsv'), 'w', encoding='utf-8') as f:
        f.write('\t'.join(B.COLS) + '\n')
        for i, sp, r, w, pos, wz, sf in rows:
            if wrong:
                r, wz, pos = 'زيف', 'مُفْتَعَل', 'مصدر'
            row = dict(id=i, split=sp, root=r, root_spaced=' '.join(r), root_type='سالم', word=w, pos=pos, wazn=wz, surface_pattern=sf,
                       wazn_status='VERIFIED', verb='', verb_form='', source='TEST', evidence='', event_id='', rank='CANDIDATE')
            f.write('\t'.join(row[c] for c in B.COLS) + '\n')


def run_tool(*args, check_rc=True):
    env = dict(os.environ, PYTHONHASHSEED='0')
    r = subprocess.run([sys.executable, '-P', '-s', os.path.join(H, 'tools', 'root_wazn_bench.py')] + list(args), env=env,
                       capture_output=True, text=True)
    if check_rc and r.returncode:
        raise RuntimeError(r.stderr[-800:])
    return r


def blind(d, order=None):
    inp, out = os.path.join(d, 'in.tsv'), os.path.join(d, 'out.jsonl')
    B.blind_input(d, inp, 'dev')
    if order:
        ls = open(inp, encoding='utf-8').read().splitlines()
        body = [ls[1:][k] for k in order]
        open(inp, 'w', encoding='utf-8').write('\n'.join([ls[0]] + body) + '\n')
    run_tool('run', inp, out)
    return inp, out


def recs_by_id(out):
    ls = open(out, encoding='utf-8').read().splitlines()
    return json.loads(ls[0])['meta'], {json.loads(l)['id']: json.dumps(json.loads(l), ensure_ascii=False, sort_keys=True) for l in ls[1:]}


def refused(fn):
    try:
        fn()
        return False
    except SystemExit:
        return True


def main():
    with tempfile.TemporaryDirectory() as t:
        a, b = os.path.join(t, 'a'), os.path.join(t, 'b')
        pkg(a)
        pkg(b, wrong=True)
        inp, out = blind(a)
        # ---- العزل ----
        head = open(inp, encoding='utf-8').readline().rstrip('\n').split('\t')
        txt = open(inp, encoding='utf-8').read()
        check('I1 المدخل (id، word) وحدهما بلا جذر ولا وزن ولا صنف', head == ['id', 'word'] and not any(x in txt for x in ('كتب\t', 'فَعَلَ', 'فعل ماضٍ')))
        bad = os.path.join(a, 'bad.tsv')
        open(bad, 'w', encoding='utf-8').write('id\tword\troot\nMTX01\tكَتَبَ\tكتب\n')
        check('I1 يُرفض مدخلٌ فيه عمود الجذر', run_tool('run', bad, os.path.join(a, 'x.jsonl'), check_rc=False).returncode != 0)
        check('I2 قسم الاختبار مرفوض في blind-input', refused(lambda: B.blind_input(a, os.path.join(a, 't.tsv'), 'test')) and 'MTX04' not in txt)
        _, out_b = blind(b)
        ma, ra = recs_by_id(out)
        mb, rb = recs_by_id(out_b)
        check('I3 قلب الأجوبة لا يغيّر المخرج', ra == rb)
        _, out_c = blind(os.path.join(t, 'c') if os.path.isdir(os.path.join(t, 'c')) else (pkg(os.path.join(t, 'c')) or os.path.join(t, 'c')), order=[5, 3, 1, 0, 2, 4])
        _, rc = recs_by_id(out_c)
        check('I4 الترتيب لا يغيّر مخرج كل صف', ra == rc)
        # ---- المشتقات ----
        def part(w):
            r = B._branch('participle', lambda: B._participle_branch(w))
            return r, [(x['root'], x['form_class'], x['kind'], x['license_level']) for x in (r['outputs'] or {}).get('analyses', [])] if r['outputs'] else []
        r1, p1 = part('ضَارِب')
        check('P1 اسم فاعل سالم: ضَارِب ← ضرب I فاعل برخصة حدث', r1['execution_status'] == 'EXECUTED_WITH_RESULTS' and ('ضرب', 'I', 'فاعل', 'حدث') in p1, p1)
        A = B._analyze_word('ضَارِب')
        fp = [f for f in A['faces'] if f['branch'] == 'participle']
        check('P1 الوجه: ضرب|فَاعِل|DECLARED_FORM_MAPPING|دليل الحدث', any(f['root'] == 'ضرب' and f['wazn'] == 'فَاعِل' and
                                                                              f['wazn_source'] == 'DECLARED_FORM_MAPPING' and f['evidence'] == 'حدث' for f in fp), fp)
        r2, p2 = part('مَضْرُوب')
        check('P2 اسم مفعول سالم: مَضْرُوب ← ضرب I مفعول', ('ضرب', 'I', 'مفعول', 'حدث') in p2, p2)
        _, p3 = part('قَائِل')
        _, p3b = part('آخِذ')
        check('P3 أجوف: قَائِل ← قول بإبدال العين', any(x[0] == 'قول' and x[2] == 'فاعل' for x in p3), p3)
        check('P3 مهموز: آخِذ ← ءخذ', any(x[0] == 'ءخذ' for x in p3b), p3b)
        r4, p4 = part('بَيْت')
        check('P4 لا مطابقة: بَيْت ← EXECUTED_EMPTY', r4['execution_status'] == 'EXECUTED_EMPTY' and not p4, r4)
        r5, _ = part('abc')
        r6, _ = part('')
        check('P5 مدخلٌ غير صالح ← EXECUTION_FAILURE/INVALID_INPUT', r5['execution_status'] == 'EXECUTION_FAILURE' and r5['error_type'] == 'INVALID_INPUT'
              and r6['error_type'] == 'INVALID_INPUT', (r5, r6))
        # ---- الإلزامية ----
        cmp_dir = os.path.join(a, 'cmp')
        M, res = B.compare(a, inp, out, cmp_dir)
        # M1 عطل فرع المشتقات يظهر في المقاييس
        ls = open(out, encoding='utf-8').read().splitlines()
        recs = [json.loads(l) for l in ls[1:]]
        broken = copy.deepcopy(recs)
        for r in broken:
            br = r['A_LEXICAL_MORPH']['branches']['participle']
            br.update(execution_status='EXECUTION_FAILURE', error_type='AttributeError', error_message="'list' object has no attribute 'H'", outputs=None)
            r['A_LEXICAL_MORPH'].update(B.assemble(r['A_LEXICAL_MORPH']))
        p_broken = os.path.join(a, 'broken.jsonl')
        open(p_broken, 'w', encoding='utf-8').write(ls[0] + '\n' + '\n'.join(json.dumps(r, ensure_ascii=False) for r in broken) + '\n')
        Mb, resb = B.compare(a, inp, p_broken, os.path.join(a, 'cmpb'))
        ex = Mb['execution']
        check('M1 عطل المشتقات يظهر: كل الكلمات جزئية، والعطل باسم فرعه ونوعه',
              ex['words_with_any_failure'] == len(recs) and ex['words_partial'] == len(recs) and
              ex['failures_by_branch_and_type'].get('participle|AttributeError') == len(recs), ex)
        rz = {r['id']: r for r in resb}
        check('M1 ضَارِب بعد العطل: PARTIAL_EXECUTION والفرع المعطّل مسمّى',
              rz['MTX02']['A_execution'] == 'PARTIAL_EXECUTION' and 'participle' in rz['MTX02']['A_failed_branches'], rz['MTX02']['observations'])
        check('M2 تنفيذ المشتقات الصحيح: ضرب في أوجه ضَارِب ومَضْرُوب، والزوج في الوجه نفسه',
              {r['id']: r for r in res}['MTX02']['pair_in_same_face_convention'] and {r['id']: r for r in res}['MTX03']['pair_in_same_face_convention'])
        bad_cases = dict(
            M3_missing=ls[:-1],
            M4_duplicate=ls + [ls[1]],
            M5_unknown=ls[:1] + [json.dumps(dict(json.loads(ls[1]), id='MTX99'), ensure_ascii=False)] + ls[2:],
            M6_swapped_word=ls[:1] + [json.dumps(dict(json.loads(ls[1]), word='كَتَبُوا'), ensure_ascii=False)] + ls[2:])
        mt = json.loads(ls[0])
        mt['meta']['input_sha256'] = '0' * 64
        bad_cases['M7_input_sha'] = [json.dumps(mt, ensure_ascii=False)] + ls[1:]
        mixed = json.loads(ls[1])
        mixed['mode'] = 'POS_ASSISTED_DIAGNOSTIC'
        bad_cases['M8_mixed_mode'] = ls[:1] + [json.dumps(mixed, ensure_ascii=False)] + ls[2:]
        mr = json.loads(ls[0])
        mr['meta']['resources']['hfn_files']['HFN/lexical_units.csv'] = 'f' * 64
        bad_cases['M15_resources_differ'] = [json.dumps(mr, ensure_ascii=False)] + ls[1:]
        for name, lines in bad_cases.items():
            p = os.path.join(a, name + '.jsonl')
            open(p, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
            check(f'{name} يرفضه المقارن قبل أي مقياس', refused(lambda: B.compare(a, inp, p, os.path.join(a, 'c_' + name))) and
                  not os.path.exists(os.path.join(a, 'c_' + name, 'dev_metrics.json')))
        # M8: وضع POS في مقارنٍ أعمى
        pos_f = os.path.join(a, 'pos.tsv')
        open(pos_f, 'w', encoding='utf-8').write('id\tpos\n' + ''.join(f'{r[0]}\t{r[4]}\n' for r in ROWS if r[1] == 'dev'))
        out_pos = os.path.join(a, 'pos.jsonl')
        run_tool('run', inp, out_pos, '--pos-assisted', pos_f)
        check('M8 ملف المسار التشخيصي يرفضه المقارن الأعمى', refused(lambda: B.compare(a, inp, out_pos, os.path.join(a, 'c_pos'))))
        Mp, _ = B.compare(a, inp, out_pos, os.path.join(a, 'c_pos2'), allow_mode=('POS_ASSISTED_DIAGNOSTIC',))
        check('M8 ويقبله المقارن التشخيصي المسمّى وحده', Mp['meta']['analysis_meta']['mode'] == 'POS_ASSISTED_DIAGNOSTIC')
        # M9 عائلة الباب لا تُعرض وزناً مثبتاً
        ref = dict(id='X', word='كَتَبَ', root='كتب', wazn='فَعِلَ', pos='فعل ماضٍ', root_type='سالم', wazn_status='VERIFIED', surface_pattern='فَعِلَ')
        rec = dict(id='X', word='كَتَبَ', A_LEXICAL_MORPH=dict(level='ROOT_PROVEN', execution='COMPLETE', faces=[], branches={},
                   proven=dict(root='كتب', form_class='I', wazn_selected=None, wazn_candidates=[], wazn_family=['فَعَلَ', 'فَعِلَ', 'فَعُلَ'])),
                   B_PUBLIC=dict(morph=[], level='DEFERRED'))
        av = dict(root_in_hfn_v36=True, word_in_hfn_v36=True)
        e9 = B.evaluate_row(ref, rec, [dict(root='كتب')], av)
        check('M9 العائلة: REFERENCE_WEIGHT_INCLUDED_IN_FAMILY، والوزن المختار None، ولا اتفاق وزن',
              e9['reference_wazn_in_family'] == 'REFERENCE_WEIGHT_INCLUDED_IN_FAMILY' and e9['proven_wazn_selected'] is None and
              e9['wazn_agreement_convention'] is None, e9)
        e9['denominators'] = dict(root='PROVISIONAL_REFERENCE_MAIN', wazn='PROVISIONAL_REFERENCE_MAIN', pair='PROVISIONAL_REFERENCE_MAIN')
        m9 = B.compute_metrics([e9], [])['denominators']['PROVISIONAL_REFERENCE_MAIN']
        check('M9 العائلة لا تدخل مقام دقة الوزن المختار', m9['wazn_selected']['n'] == 0 and m9['proven_without_selected_wazn']['reference_in_family'] == 1)
        # M10 جذرٌ من وجه ووزنٌ من آخر
        rec10 = dict(id='X', word='w', A_LEXICAL_MORPH=dict(level='CANDIDATES_ONLY', execution='COMPLETE', branches={}, proven=None,
                     faces=[dict(root='كتب', wazn='مَفْعُول', wazn_source='LEXICON_RETRIEVAL', kind='اسم مفعول', branch='lexical_retrieval'),
                            dict(root='كذب', wazn='فَعَلَ', wazn_source='LEXICON_RETRIEVAL', kind='فعل', branch='verb_morph')]),
                     B_PUBLIC=dict(morph=[], level='DEFERRED'))
        ref10 = dict(ref, wazn='فَعَلَ')
        e10 = B.evaluate_row(ref10, rec10, [dict(root='كتب')], av)
        check('M10 جذرٌ ووزنٌ من وجهين مختلفين ليسا زوجاً', e10['ref_root_in_faces'] and e10['ref_wazn_in_any_face'] and not e10['pair_in_same_face_convention'])
        check('M10 المرشّح غير المطابق يُسمّى «غير مطابق للمجموعة المرجعية» لا «بلا سند»', e10['candidates_not_in_reference_group'] == ['كذب'] and
              'extra_unsupported_candidates' not in e10)
        # M11 كلمة متعددة الأوجه
        def mk(i, root, proven_root):
            r = dict(id=i, word='عَلِمَ', ref_root=root, ref_wazn='فَعِلَ', proven_root=proven_root, root_agreement=proven_root == root,
                     proven_wazn_selected=None, proven_wazn_source=None, reference_wazn_in_family=None, wazn_mismatch=False,
                     root_mismatch=proven_root != root, surface_pattern_agreement=None, ref_root_in_faces=True, ref_root_in_faces_or_templates=True,
                     pair_in_same_face_convention=False, pair_in_same_face_literal=False, pair_in_same_face_surface=False,
                     candidates_not_in_reference_group=[], B_root_agreement=None, B_proven_roots=[], B_wazn_output=None, B_level='DEFERRED',
                     A_level='ROOT_PROVEN', A_execution='COMPLETE', observations=[], cause_hypotheses=[], ref_root_type='سالم', ref_pos='فعل ماضٍ',
                     ref_wazn_status='VERIFIED', availability=av, faces=[dict(root='علم'), dict(root='علو')],
                     denominators=dict(root='PROVISIONAL_REFERENCE_MAIN', wazn='PROVISIONAL_REFERENCE_MAIN', pair='PROVISIONAL_REFERENCE_MAIN'))
            return r
        mf = [mk('A1', 'علو', 'علم'), mk('A2', 'علم', 'علم')]
        M11 = B.compute_metrics(mf, [])
        check('M11 الكلمة متعددة الأوجه: الصف الأول مخالف، والكلمة موافقة بمجموعتها (لا بأول صف)',
              M11['denominators']['PROVISIONAL_REFERENCE_MAIN']['root_proven']['agree'] == 1 and M11['distinct_words']['proven']['k'] == 1 and
              M11['distinct_words']['n'] == 1 and M11['distinct_words']['multi_face'] == 1, M11['distinct_words'])
        # M12 ترتيب المرجع والمخرجات والمرشّحين لا يغيّر المقاييس
        res_sh = copy.deepcopy(res)
        random.Random(7).shuffle(res_sh)
        for r in res_sh:
            random.Random(3).shuffle(r['faces'])
        M12a = B.compute_metrics(res, recs)
        M12b = B.compute_metrics(res_sh, list(reversed(recs)))
        check('M12 الترتيب (صفوف ومرشّحون) لا يغيّر المقاييس', json.dumps(M12a, sort_keys=True) == json.dumps(M12b, sort_keys=True))
        sh_dir = os.path.join(t, 'sh')
        rows_sh = list(ROWS)
        random.Random(11).shuffle(rows_sh)
        pkg(sh_dir, rows_sh)
        M12c, _ = B.compare(sh_dir, inp, out, os.path.join(sh_dir, 'cmp'))
        strip = lambda m: json.dumps({k: v for k, v in m.items() if k != 'meta'}, sort_keys=True)
        check('M12 ترتيب ملف المرجع لا يغيّر المقاييس', strip(M12c) == strip(M))
        dup_dir = os.path.join(t, 'dup')
        pkg(dup_dir, ROWS + [ROWS[0]])
        check('M12 تكرار صف المرجع يُرفض لا يُضاعَف', refused(lambda: B.compare(dup_dir, inp, out, os.path.join(dup_dir, 'cmp'))))
        # M13 لا ترقية لغير المراجَع
        check('M13 لا مقام «gold»؛ والمقام الرئيسي PROVISIONAL_REFERENCE_MAIN؛ وREVIEWED_ACCEPTED فارغ بلا مراجعة',
              'gold' not in json.dumps(M) and 'PROVISIONAL_REFERENCE_MAIN' in M['denominators'] and 'REVIEWED_ACCEPTED' not in M['denominators'])
        corr = os.path.join(a, 'corr.tsv')
        open(corr, 'w', encoding='utf-8').write('\t'.join(B.CORR_COLS) + '\n' +
                                              'MTX02\twazn\tفَاعِل\t\tr\ts\tagent\tREVIEW_REQUIRED\tR\n' +
                                              'MTX03\tpos\tاسم مفعول\t\tr\ts\tagent\tDISPUTED\tR\n')
        M13, res13 = B.compare(a, inp, out, os.path.join(a, 'c13'), corrections=corr)
        r13 = {r['id']: r for r in res13}
        check('M13 مراجعة الوزن لا تُسقط قياس الجذر، ونزاع الصنف لا يُسقطه أيضاً',
              r13['MTX02']['denominators'] == dict(root='PROVISIONAL_REFERENCE_MAIN', wazn='PROVISIONAL_REFERENCE_FLAGGED', pair='PROVISIONAL_REFERENCE_FLAGGED')
              and r13['MTX03']['denominators']['root'] == 'PROVISIONAL_REFERENCE_MAIN', (r13['MTX02']['denominators'], r13['MTX03']['denominators']))
        check('M13 غياب الصف من الملحق = UNREVIEWED لا قبول', r13['MTX01']['field_review']['root'] == 'UNREVIEWED')
        # M14 الصف المحجوب
        leak = json.loads(ls[1])
        leak['id'], leak['word'] = 'MTX04', 'قَالَ'
        inp_leak = os.path.join(a, 'in_leak.tsv')
        open(inp_leak, 'w', encoding='utf-8').write(open(inp, encoding='utf-8').read() + 'MTX04\tقَالَ\n')
        mleak = json.loads(ls[0])
        mleak['meta']['input_sha256'] = B.sha(inp_leak)
        mleak['meta']['n_rows'] += 1
        p14 = os.path.join(a, 'leak.jsonl')
        open(p14, 'w', encoding='utf-8').write('\n'.join([json.dumps(mleak, ensure_ascii=False)] + ls[1:] + [json.dumps(leak, ensure_ascii=False)]) + '\n')
        check('M14 صفٌّ محجوب في التحليل يرفضه المقارن حتى لو اتسق ملفه', refused(lambda: B.compare(a, inp_leak, p14, os.path.join(a, 'c14'))))
        # M16 خطأ الجذر مع خطأ الوزن
        rec16 = dict(id='X', word='w', A_LEXICAL_MORPH=dict(level='ROOT_PROVEN', execution='COMPLETE', faces=[], branches={},
                     proven=dict(root='دخر', form_class='VIII', wazn_selected='افْتَعَى', wazn_candidates=[], wazn_family=['افْتَعَلَ'],
                                 wazn_selected_source='LEXICON_RETRIEVAL')), B_PUBLIC=dict(morph=[], level='DEFERRED'))
        e16 = B.evaluate_row(dict(ref, root='ذخر', wazn='افْتَعَلَ', surface_pattern='افْتَعَلَ'), rec16, [dict(root='ذخر')], av)
        check('M16 خطأ الجذر وخطأ الوزن كلاهما ظاهر', e16['root_mismatch'] and e16['wazn_mismatch'] and
              'PROVEN_ROOT_DIFFERS_FROM_REFERENCE' in e16['observations'] and 'PROVEN_WAZN_DIFFERS_FROM_REFERENCE' in e16['observations'], e16['observations'])
        # التسميات: لا CONTEXT_REQUIRED آلياً
        check('L1 لا يُستنتج CONTEXT_REQUIRED آلياً', 'CONTEXT_REQUIRED' not in json.dumps([r['observations'] + r['cause_hypotheses'] for r in res]))
        # الإفساد على المخرج الحقيقي
        cc = B.corrupt_check(a, inp, out, os.path.join(a, 'corrupt.json'))
        check('C1 كل إفسادٍ للمخرج مرفوض', cc['all_refused'], {k: v['refused'] for k, v in cc['cases'].items()})
    # ---- عقد الوزن وUnicode ----
    from sarf.root import WAZN
    check('W1 الباب الأول عائلة ثلاثة موازين', B.FORM_CLASS_TO_WAZN['I'] == {'فَعَلَ', 'فَعِلَ', 'فَعُلَ'})
    check('W2 التحويل يوافق جدول المحلّل WAZN', all(B.wazn_convention(WAZN[k]) in {B.wazn_convention(x) for x in v}
                                                  for k, v in B.FORM_CLASS_TO_WAZN.items() if k in WAZN))
    check('W3 «IV» لا يساوي وزناً عربياً', B.wazn_convention('IV') != B.wazn_convention('أَفْعَلَ'))
    a1 = 'فَ' + 'ع' + 'َّ' + 'لَ'      # شدّة ثم فتحة
    a2 = 'فَ' + 'ع' + 'َّ' + 'لَ'      # فتحة ثم شدّة
    check('U1 ترتيبان مختلفان لعلامتي الشدّة والفتحة: مختلفان خاماً، متساويان بعد NFC', a1 != a2 and B.wazn_literal(a1) == B.wazn_literal(a2))
    check('U1 NFC لا يفقد علامة', sorted(B.wazn_literal(a2)) == sorted(a2) and 'ّ' in B.wazn_literal(a2) and 'َ' in B.wazn_literal(a2))
    check('U2 الفتحة والكسرة والضمة لا تُمحى', len({B.wazn_convention(x) for x in ('فَعَلَ', 'فَعِلَ', 'فَعُلَ', 'فعل')}) == 4)
    check('U2 الهمزات والواو والياء لا تُسوّى', B.wazn_convention('أَفْعَلَ') != B.wazn_convention('إِفْعَلَ') and
          B.wazn_convention('فَوْعَل') != B.wazn_convention('فَيْعَل') and B.nfc('سَأَلَ') != B.nfc('سَءَلَ'))
    check('U3 الحرفي منفصل عن الاتفاقية: اِفْتَعَلَ/افْتَعَلَ', B.wazn_literal('اِفْتَعَلَ') != B.wazn_literal('افْتَعَلَ') and
          B.wazn_convention('اِفْتَعَلَ') == B.wazn_convention('افْتَعَلَ'))
    check('U3 الاتفاقية للوزن وحده: nfc الكلمات لا يحذف كسرة ألف الوصل', B.nfc('اِصْطَبَرَ').startswith('اِ'))
    print('نجح' if not FAILS else f'فشل {len(FAILS)}: {FAILS}')
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
