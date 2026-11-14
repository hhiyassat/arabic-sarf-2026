# -*- coding: utf-8 -*-
"""dayn_test_harness.py (SARF_MORPH_EXPORT_REPAIR_01 / §2) — أداةُ اختبارٍ مُصلَّبة لتقييم عيوب 2:282.
- REPRO_* يصف العيب القائم · ACCEPT_* عقد الإصلاح · KEEP_* يجب أن يمرّ دائمًا · INFO_* معلوماتي خارج رمز الخروج.
- تقييمٌ مؤجَّل (كل فحص دالة في إطار يلتقط الاستثناء)، بحثٌ بالهوية لا بالترتيب، حارسُ عددٍ قبل كل فحص.
- تثبيتُ هوية المحرك والمورد يوقف التنفيذ عند الاختلاف. يشغّل 2:282 وحدها على 726131f بالمورد v47.
الاستعمال: dayn_test_harness.py <expected_states.json> <out_dir> [stage=before]"""
import os, sys, json, hashlib, copy, subprocess, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tools'), os.path.join(ROOT, 'tools', 'v48c2')]

EXP_PATH, OUT = sys.argv[1], sys.argv[2]
STAGE = sys.argv[3] if len(sys.argv) > 3 else 'before'
EXPECTED = json.load(open(EXP_PATH, encoding='utf-8'))
PIN = dict(engine_base='726131f', manifest_sha='aca692e38785573f811e93b4e2cab531a239642f3cac5d5225664645e987b919', release='release_v47')

def sha_file(p):
    h = hashlib.sha256(); h.update(open(p, 'rb').read()); return h.hexdigest()

def pin_identity():
    head = subprocess.run(['git', '-C', ROOT, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    v47 = os.environ.get('SARF_HFN', '')
    man = os.path.join(v47, 'MANIFEST.json')
    problems = []
    if not head.startswith(PIN['engine_base']): problems.append('ENGINE_COMMIT_MISMATCH %s != %s' % (head[:8], PIN['engine_base']))
    if not v47 or not os.path.exists(man): problems.append('RESOURCE_PATH_MISSING SARF_HFN=%s' % (v47 or '<unset>'))
    else:
        msha = sha_file(man)
        if msha != PIN['manifest_sha']: problems.append('RESOURCE_MANIFEST_MISMATCH %s != pinned' % msha[:8])
    from sarf.hfn_pin import TARGET
    if TARGET['release'] != PIN['release']: problems.append('RELEASE_NOT_V47 (got %s) — v52-experimental not allowed' % TARGET['release'])
    return dict(engine_head=head, manifest=(sha_file(man) if os.path.exists(man) else None),
                release=TARGET['release'], hfn_path=v47, problems=problems)

def build_snapshot():
    import engine_dump2 as E
    from sarf.stages import run_ref
    from sarf.output_schema import to_schema, _lex
    from sarf.catalog import Catalog
    C = run_ref('2:282', None, E.TARGETS)
    A = C.get('analysis')['2:282']; U = C.get('units')['2:282']['units']; FF = C.get('features_final')['2:282']
    S = to_schema(A, Catalog(['operators_catalog.jsonl', 'operators_catalog_split_vocalized.csv']))
    M = A['morph']; lex = _lex()
    from collections import Counter
    snap = {}
    snap['slots'] = {wi: [dict(type=s.get('type'), text=s.get('text'), role=s.get('role'), index=s.get('index'), unit=s.get('unit')) for s in A['segments'][wi]['slots']] for wi in range(len(A['segments']))}
    snap['morph'] = {}
    for m in M:
        wi = m['word_index']
        snap['morph'][wi] = dict(status=m.get('status'), reason=m.get('reason'), root=m.get('root'),
                                 n_candidates=m.get('n_candidates'), keys=sorted(m.keys()),
                                 candidate_faces=m.get('candidate_faces'))
    snap['morph_count'] = len(M); snap['morph_status'] = dict(Counter(m['status'] for m in M))
    snap['ops'] = {}
    for o in A['operators']:
        snap['ops'].setdefault(o['word_index'], {})[(o['operator'], o['group'])] = o['status']
    def ff_view(k):
        f = FF.get(k, {})
        return dict(pos=(f.get('pos') or {}).get('v'), operator=f.get('operator'), idafa=f.get('idafa'), lemma=(f.get('lemma') or {}).get('v'))
    def u_view(k):
        u = U.get(k)
        return dict(R=(u.Theta.get('R') if u is not None else None)) if u is not None else None
    # units/features keyed by (wi, slot['unit'])
    snap['units'] = {}; snap['ff'] = {}
    for wi in snap['slots']:
        for s in snap['slots'][wi]:
            k = (wi, s['unit'])
            if k in U: snap['units'][k] = u_view(k)
            snap['ff'][k] = ff_view(k)
    snap['ff'][(85, 0)] = ff_view((85, 0)); snap['units'][(85, 0)] = u_view((85, 0)); snap['units'][(7, 0)] = u_view((7, 0))
    snap['lex'] = {w: [e['entry_id'] for e in lex.lookup(w)] for w in ('أَجَلِ', 'أَجَلْ', 'أَجَلٍ')}
    # schema tokens we read (75, 57, 97) reduced
    def tok_view(idx):
        t = S['tokens'][idx]
        return dict(analyses=[dict(segments=[dict(pos=sg.get('pos'), particle=sg.get('particle')) for sg in a['segments']],
                                   evidence=a.get('evidence')) for a in t['analyses']])
    snap['schema'] = {i: tok_view(i) for i in (75, 57, 97)}
    snap['deps'] = [dict(gov_token=d['governor']['token'], gov_seg=d['governor']['segment'],
                         dep_seg=d['dependent']['segment'], operator_id=d.get('operator_id'), consistent=d.get('consistent')) for d in S['dependencies']]
    # catalog group-7 title for إذا
    cat = [json.loads(l) for l in open(os.path.join(ROOT, 'operators_catalog.jsonl'), encoding='utf-8')]
    g7 = [r for r in cat if (r.get('operator_plain') == 'إذا' or r.get('operator_form') == 'إِذَا') and str(r.get('group_number')) == '7']
    snap['itha_g7_title'] = g7[0].get('group_name_ar') if g7 else None
    snap['stems'] = sum(1 for wi in snap['slots'] for s in snap['slots'][wi] if s['type'] == 'جذع')
    return snap

# ---------- helpers (identity + count guard) ----------
def one(seq, name):
    seq = list(seq)
    if len(seq) != 1: raise AssertionError('COUNT_GUARD %s expected 1 got %d' % (name, len(seq)))
    return seq[0]
def slot_by(snap, wi, **ident):
    return [s for s in snap['slots'].get(wi, []) if all(s.get(k) == v for k, v in ident.items())]
def stem_unit(snap, wi):
    s = one(slot_by(snap, wi, type='جذع'), 'stem@%d' % wi); return (wi, s['unit'])
def dep_gov(snap, tok):
    return [d for d in snap['deps'] if d['gov_token'] == tok]
def ma_analysis(snap, tok):
    # identity: the analysis whose segment is a ما particle carrying catalog_group '3'
    for a in snap['schema'][tok]['analyses']:
        for sg in a['segments']:
            p = sg.get('particle') or {}
            if sg.get('pos') == 'particle' and 'ما_النفي_الحالي' in (p.get('operator_ids') or []):
                return a, sg
    return None, None

# ---------- checks (return bool = condition holds) ----------
def C_KEEP_1a(s):
    sl = s['slots'][85]; return len(sl) == 2 and bool(slot_by(s, 85, type='جذع', text='أَجَلِ')) and bool(slot_by(s, 85, type='مبني', text='هِ'))
def C_KEEP_1b(s):
    k = stem_unit(s, 85); return s['units'].get(k, {}).get('R') == 'ءجل' and s['ff'].get(k, {}).get('lemma') == 'أَجَل'
def C_KEEP_1c(s):
    k = stem_unit(s, 7); return s['units'].get(k, {}).get('R') == 'ءجل'
def C_KEEP_1d(s): return 'mabniyat:particle:0235' in s['lex']['أَجَلْ']
def C_KEEP_1e(s): return s['lex']['أَجَلٍ'] == []
def C_REPRO_1(s): return s['lex']['أَجَلِ'] == ['mabniyat:particle:0235']
def C_REPRO_2a(s):
    d = one(dep_gov(s, 91), 'dep91'); return d['operator_id'] == 'ل_الملك'
def C_KEEP_2a(s):
    sl = s['slots'][91]; return len(sl) == 3 and bool(slot_by(s, 91, type='عامل', text='لِ')) and bool(slot_by(s, 91, type='أل', text='ل')) and bool(slot_by(s, 91, type='جذع', text='شَّهَٰدَةِ'))
def C_KEEP_2b(s):
    o = s['ops'].get(91, {}); return o.get(('لِ', '1')) == 'accepted' and o.get(('لِ', '6')) == 'blocked'
def C_KEEP_2c(s):
    d = one(dep_gov(s, 91), 'dep91'); return d['gov_seg'] == 0 and d['dep_seg'] == 2 and d['consistent'] is True
def C_REPRO_2b(s):
    a, sg = ma_analysis(s, 75); return sg is not None and (sg.get('particle') or {}).get('effect') == 'raf_ism_nasb_khabar'
def C_REPRO_2c(s):
    a, sg = ma_analysis(s, 75)
    if a is None: return False
    cat_ev = [e for e in (a.get('evidence') or []) if e.get('source') == 'catalog']
    return bool(cat_ev) and cat_ev[0].get('id') == 'ما_النفي_الحالي'
def C_KEEP_2d(s):
    o75 = s['ops'].get(75, {}); o19 = s['ops'].get(19, {})
    return o75.get(('مَا', '3')) == 'deferred' and o75.get(('مَا', '7')) == 'deferred' and o19.get(('مَا', '3')) == 'deferred' and o19.get(('مَا', '7')) == 'deferred'
def C_REPRO_3(s):
    m = s['morph'].get(15)
    if not m: raise AssertionError('COUNT_GUARD morph15 missing')
    return ('ءبو' in (m['reason'] or '')) and (m['root'] is None) and not any(k in m['keys'] for k in ('candidate_faces', 'candidates', 'licensed'))
def C_KEEP_4(s): return s['morph_count'] == 46 and s['morph_status'] == {'accepted': 27, 'deferred': 12, 'not_applicable': 7}
def C_KEEP_5(s):
    ok = True
    for wi in (61, 93, 105):
        m = s['morph'].get(wi)
        if not m: raise AssertionError('COUNT_GUARD morph%d missing' % wi)
        ok = ok and m['status'] == 'not_applicable' and m['reason'] == 'CONSTITUTIONAL_PROTECTED_CLASS'
    return ok
def C_KEEP_6a(s):
    for k in ((35, 0), (102, 1)):
        f = s['ff'].get(k, {}); op = f.get('operator') or {}
        if not (f.get('pos') == 'فعل' and 'ناسخ' in str(op.get('v', '')) and 'VERBAL' in str(op.get('ev', ''))): return False
    return True
def C_KEEP_6b(s):
    for tok in (10, 22, 23, 27, 48):
        ds = [d for d in dep_gov(s, tok) if d['operator_id'] == 'ل_الأمر']
        if not ds or not all(d['consistent'] for d in ds): return False
    return True
def C_KEEP_6c(s):
    for wi in (57, 97):
        m = s['morph'].get(wi)
        if not m: raise AssertionError('COUNT_GUARD morph%d missing' % wi)
        if m['status'] != 'not_applicable': return False
    return True
def C_REPRO_5a(s):
    sl = s['slots'][93]; return len(sl) == 1 and sl[0]['type'] == 'جذع' and sl[0]['text'] == 'أَلَّا'
def C_REPRO_5b(s):
    sl = s['slots'][61]; return len(sl) == 1 and sl[0]['type'] == 'جذع' and sl[0]['text'] == 'مِمَّنْ'
def C_REPRO_5c(s): return s['ff'].get((61, 0), {}).get('pos') == 'عامل من العوامل المائة'
def C_REPRO_6a(s): return s['ff'].get((3, 0), {}).get('pos') == 'عامل' and s['ff'].get((75, 0), {}).get('pos') == 'عامل'
def C_REPRO_6b(s):
    return s['ops'].get(3, {}).get(('إِذَا', '7')) is not None and s['itha_g7_title'] == 'الشرط الجازمة فقط'
def C_REPRO_6c(s): return s['ff'].get((10, 0), {}).get('pos') == 'مبني+عامل'
def C_REPRO_6d(s):
    return s['schema'][57]['analyses'][0]['segments'][0]['pos'] == 'undetermined' and \
           s['schema'][97]['analyses'][0]['segments'][0]['pos'] == 'undetermined' and \
           not s['ops'].get(57) and not s['ops'].get(97)
def C_REPRO_cloud(s):
    idf = s['ff'].get((91, 0), {}).get('idafa') or {}
    op_slot = one(slot_by(s, 91, type='عامل', text='لِ'), 'lam91'); stem = one(slot_by(s, 91, type='جذع'), 'stem91')
    jar_inside_unit = (op_slot['unit'] == stem['unit'])
    return idf.get('v') == 'مضاف إليه' and jar_inside_unit
# ACCEPT (fix contracts) — genuinely False before the fixes
def _faces_contract(faces, reason, n_candidates):
    if not faces: return False
    # separate denominators allowed; do NOT force len==n_candidates
    for f in faces:
        if not all(f.get(x) is not None for x in ('root', 'door', 'pattern', 'form_class', 'status', 'face_id')): return False
    roots = [f['root'] for f in faces]
    if len(roots) != len(set(f['face_id'] for f in faces)): return False      # no duplicate ids
    # match reason-named pairs (e.g. ءبو/ءبي)
    named = [r for r in ('ءبو', 'ءبي') if r in (reason or '')]
    return all(any(f['root'] == r for f in faces) for r in named) if named else True
def C_ACCEPT_E1(s):
    m = s['morph'].get(15) or {}
    return _faces_contract(m.get('candidate_faces'), m.get('reason'), m.get('n_candidates'))
def C_ACCEPT_E0(s):
    return os.path.exists(os.path.join(HERE, '_e0_export_check.json'))   # produced by the E0 batch; absent now
def C_ACCEPT_E2(s):
    return os.path.exists(os.path.join(HERE, '_e2_coverage.json'))       # produced by the E2 batch; absent now
def C_ACCEPT_E4_ma(s):
    a, sg = ma_analysis(s, 75)
    # achieved = effect NOT escalated to segment level (lives inside a candidate face instead)
    return sg is not None and (sg.get('particle') or {}).get('effect') in (None, '')
def C_ACCEPT_E4_lam(s):
    d = one(dep_gov(s, 91), 'dep91'); return d['operator_id'] in (None, '')   # relation kept, meaning NOT chosen
def C_INFO_4(s): return s['stems'] == 81

CHECKS = {
 'KEEP_1a_seg85': C_KEEP_1a, 'KEEP_1b_root85': C_KEEP_1b, 'KEEP_1c_root7': C_KEEP_1c,
 'KEEP_1d_lookup_ajalh': C_KEEP_1d, 'KEEP_1e_lookup_ajalin': C_KEEP_1e, 'KEEP_2a_seg91': C_KEEP_2a,
 'KEEP_2b_ops91': C_KEEP_2b, 'KEEP_2c_dep91_struct': C_KEEP_2c, 'KEEP_2d_ma_groups': C_KEEP_2d,
 'KEEP_4_morph46': C_KEEP_4, 'KEEP_5_protected': C_KEEP_5, 'KEEP_6a_kana_laysa': C_KEEP_6a,
 'KEEP_6b_lam_amr': C_KEEP_6b, 'KEEP_6c_yakuna': C_KEEP_6c,
 'REPRO_1_ajal_lookup': C_REPRO_1, 'REPRO_2a_lam_milk': C_REPRO_2a, 'REPRO_2b_ma_effect': C_REPRO_2b,
 'REPRO_2c_ma_evidence': C_REPRO_2c, 'REPRO_3_faces_text': C_REPRO_3, 'REPRO_5a_alla_single': C_REPRO_5a,
 'REPRO_5b_mimman_single': C_REPRO_5b, 'REPRO_5c_mimman_pos': C_REPRO_5c, 'REPRO_6a_amil_pos': C_REPRO_6a,
 'REPRO_6b_itha_group': C_REPRO_6b, 'REPRO_6c_waw_lam_merge': C_REPRO_6c, 'REPRO_6d_yakuna_schema': C_REPRO_6d,
 'REPRO_cloud_shahada_mudaf': C_REPRO_cloud,
 'ACCEPT_E0_unit_after_al': C_ACCEPT_E0, 'ACCEPT_E1_faces_contract': C_ACCEPT_E1, 'ACCEPT_E2_coverage': C_ACCEPT_E2,
 'ACCEPT_E4_ma_not_escalated': C_ACCEPT_E4_ma, 'ACCEPT_E4_lam_relation_kept': C_ACCEPT_E4_lam,
 'INFO_4_stems81': C_INFO_4,
}

def run_checks(snap, stage):
    rows = []; info = []
    for name, fn in CHECKS.items():
        meta = EXPECTED['checks'][name]; expected = meta['states'][stage]
        try:
            actual = bool(fn(snap)); err = None
        except Exception as e:
            actual = None; err = '%s: %s' % (type(e).__name__, e)
        if meta['type'] == 'INFO':
            info.append(dict(check=name, actual=actual, error=err)); continue
        if err is not None: cat = 'execution_error'
        elif actual == expected: cat = 'match'
        elif meta['type'] == 'KEEP': cat = 'broken_KEEP'
        else: cat = 'undeclared_flip'
        rows.append(dict(check=name, type=meta['type'], expected=expected, actual=actual, category=cat, error=err))
    return rows, info

# ---------- corruption tests ----------
def corrupt_tests(snap):
    res = []
    def expect_fail(name, mut, check_name):
        c = copy.deepcopy(snap); mut(c)
        try: still = bool(CHECKS[check_name](c))
        except Exception: still = False
        res.append(dict(corruption=name, target=check_name, check_now=still, PASS=(still is False)))
    def del_morph(wi):
        return lambda c: c['morph'].pop(wi, None)
    expect_fail('delete_morph_93', del_morph(93), 'KEEP_5_protected')
    expect_fail('delete_morph_57', del_morph(57), 'KEEP_6c_yakuna')
    expect_fail('delete_unit_key_85', lambda c: c['units'].pop((85, 0), None) or c['units'].__setitem__((85, 0), {}), 'KEEP_1b_root85')
    # face corruptions: inject a valid candidate_faces into morph15, then break it -> ACCEPT_E1 must fail
    valid_faces = [dict(root='ءبو', door='I', pattern='يَفْعَل', form_class='I', status='LICENSED_NOT_SELECTED', face_id='f0'),
                   dict(root='ءبي', door='I', pattern='يَفْعِل', form_class='I', status='LICENSED_NOT_SELECTED', face_id='f1')]
    def with_faces(faces):
        def m(c):
            c['morph'][15]['candidate_faces'] = copy.deepcopy(faces); c['morph'][15]['keys'] = sorted(set(c['morph'][15]['keys']) | {'candidate_faces'})
        return m
    # sanity: with valid faces ACCEPT_E1 would PASS (so these corruptions start from a passing base)
    def face_drop(c): with_faces(valid_faces[:1])(c)
    def face_dup(c): with_faces(valid_faces + [dict(valid_faces[0])])(c)   # duplicate face_id f0
    def face_rootswap(c):
        f = copy.deepcopy(valid_faces); f[0]['root'] = 'xyz'; with_faces(f)(c)
    expect_fail('face_drop_one', face_drop, 'ACCEPT_E1_faces_contract')          # drops ءبي -> named pair missing
    expect_fail('face_duplicate', face_dup, 'ACCEPT_E1_faces_contract')          # duplicate face_id
    expect_fail('face_root_swap', face_rootswap, 'ACCEPT_E1_faces_contract')     # root no longer matches ءبو
    # reorder invariance: identity-based REPRO_2c must be UNCHANGED after reordering operator_ids/evidence
    def reorder(c):
        a = c['schema'][75]['analyses']
        for an in a:
            an['evidence'] = list(reversed(an.get('evidence') or []))
            for sg in an['segments']:
                p = sg.get('particle') or {}
                if p.get('operator_ids'): p['operator_ids'] = list(reversed(p['operator_ids']))
    c = copy.deepcopy(snap); base = C_REPRO_2b(snap); reorder(c); after = C_REPRO_2b(c)
    res.append(dict(corruption='reorder_entries_invariance', target='REPRO_2b_ma_effect', invariant=(base == after), PASS=(base == after),
                    note='identity-based check must be order-invariant'))
    return res

def main():
    os.makedirs(OUT, exist_ok=True)
    pin = pin_identity()
    if pin['problems']:
        json.dump(dict(stage=STAGE, identity_pin=pin, verdict='IDENTITY_MISMATCH_STOP'), open(os.path.join(OUT, 'report_%s.json' % STAGE), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(json.dumps(dict(verdict='IDENTITY_MISMATCH_STOP', problems=pin['problems']), ensure_ascii=False)); sys.exit(2)
    snap = build_snapshot()
    rows, info = run_checks(snap, STAGE)
    from collections import Counter
    cats = Counter(r['category'] for r in rows)
    corr = corrupt_tests(snap)
    all_match = (cats.get('undeclared_flip', 0) == 0 and cats.get('broken_KEEP', 0) == 0 and cats.get('execution_error', 0) == 0)
    corr_ok = all(c['PASS'] for c in corr)
    exit_code = 0 if (all_match and corr_ok) else 1
    report = dict(round='SARF_MORPH_EXPORT_REPAIR_01', batch='STEP2_tests', stage=STAGE,
                  identity_pin=dict(engine_head=pin['engine_head'], manifest=pin['manifest'], release=pin['release']),
                  expected_states_fingerprint=sha_file(EXP_PATH),
                  categories=dict(cats), rows=rows, info=info,
                  corruption=dict(all_pass=corr_ok, tests=corr),
                  gate=dict(before_matches_expected=all_match, every_corruption_fails_its_check=corr_ok,
                            no_claim_of_fixing_any_defect=True),
                  verdict=('STEP2_PASS' if exit_code == 0 else 'STEP2_FAIL'), exit_code=exit_code)
    json.dump(report, open(os.path.join(OUT, 'report_%s.json' % STAGE), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(dict(stage=STAGE, verdict=report['verdict'], categories=dict(cats),
                          corruption_all_pass=corr_ok, info=[(i['check'], i['actual']) for i in info], exit_code=exit_code), ensure_ascii=False))
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
