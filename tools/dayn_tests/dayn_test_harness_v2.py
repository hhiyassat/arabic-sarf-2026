# -*- coding: utf-8 -*-
"""dayn_test_harness_v2.py (STEP2a) — أداة مصحّحة: تثبيتٌ بشجرة الشيفرة لا برأس الفرع، فحوص ACCEPT بيانات،
بحثٌ بالهوية وحارس عدد، KEEP_2b/2d مساواةٌ كاملة، REPRO_6b مقسوم، إفسادٌ لكل فحص وضابطٌ موجب لكل ACCEPT،
فحصُ منع القراءة بالترتيب على شيفرة الأداة. 2:282 وحدها على v47. الاستعمال: harness_v2 <expected_v2.json> <out> [stage=before]"""
import os, sys, json, hashlib, copy, subprocess, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tools'), os.path.join(ROOT, 'tools', 'v48c2')]
EXP_PATH, OUT = sys.argv[1], sys.argv[2]
STAGE = sys.argv[3] if len(sys.argv) > 3 else 'before'
MANIFEST_SHA = 'aca692e38785573f811e93b4e2cab531a239642f3cac5d5225664645e987b919'
def sha_file(p):
    h = hashlib.sha256(); h.update(open(p, 'rb').read()); return h.hexdigest()
def git(*a): return subprocess.run(['git', '-C', ROOT, *a], capture_output=True, text=True).stdout.strip()

def load_expected():
    d = json.load(open(EXP_PATH, encoding='utf-8'))
    # verify the states file against its recorded fingerprint (reject a modified file)
    fpp = os.path.join(os.path.dirname(EXP_PATH), 'expected_states_v2_fingerprint.json')
    declared = json.load(open(fpp, encoding='utf-8'))['sha256'] if os.path.exists(fpp) else None
    actual = sha_file(EXP_PATH)
    return d, (declared, actual, declared == actual)

def pin(expected):
    problems = []
    ct = expected['code_tree'].get(STAGE, {})
    sarf_now = git('rev-parse', 'HEAD:sarf'); ed2_now = git('rev-parse', 'HEAD:tools/v48c2/engine_dump2.py')
    for name, now, decl in (('sarf_tree', sarf_now, ct.get('sarf_tree')), ('engine_dump2_blob', ed2_now, ct.get('engine_dump2_blob'))):
        if decl == 'TO_BE_DECLARED' or decl is None: problems.append('CODE_TREE_%s=TO_BE_DECLARED (stage %s)' % (name, STAGE))
        elif now != decl: problems.append('CODE_TREE_%s_MISMATCH %s != %s' % (name, now[:8], str(decl)[:8]))
    v47 = os.environ.get('SARF_HFN', ''); man = os.path.join(v47, 'MANIFEST.json')
    if not v47 or not os.path.exists(man): problems.append('RESOURCE_MISSING')
    elif sha_file(man) != MANIFEST_SHA: problems.append('RESOURCE_MANIFEST_MISMATCH')
    from sarf.hfn_pin import TARGET
    if TARGET['release'] != 'release_v47': problems.append('RELEASE_NOT_V47 %s' % TARGET['release'])
    # own-tool fingerprint recorded separately (NOT pinned)
    tool_fp = {f: sha_file(os.path.join(HERE, f)) for f in sorted(os.listdir(HERE)) if f.endswith('.py')}
    return dict(sarf_tree=sarf_now, engine_dump2_blob=ed2_now, release=TARGET['release'],
                test_tool_fingerprints=tool_fp, problems=problems)

def build_snapshot(expected):
    import engine_dump2 as E
    from sarf.stages import run_ref
    from sarf.output_schema import to_schema, _lex
    from sarf.catalog import Catalog
    from collections import Counter
    C = run_ref('2:282', None, E.TARGETS)
    A = C.get('analysis')['2:282']; U = C.get('units')['2:282']['units']; FF = C.get('features_final')['2:282']
    S = to_schema(A, Catalog(['operators_catalog.jsonl', 'operators_catalog_split_vocalized.csv']))
    M = A['morph']; lex = _lex()
    snap = {}
    snap['slots'] = {wi: [dict(type=s.get('type'), text=s.get('text'), role=s.get('role'), index=s.get('index'), unit=s.get('unit')) for s in A['segments'][wi]['slots']] for wi in range(len(A['segments']))}
    snap['morph'] = {m['word_index']: dict(status=m.get('status'), reason=m.get('reason'), root=m.get('root'),
                     n_candidates=m.get('n_candidates'), keys=sorted(m.keys()), candidate_faces=m.get('candidate_faces')) for m in M}
    snap['morph_count'] = len(M); snap['morph_status'] = dict(Counter(m['status'] for m in M))
    snap['deferred_wi'] = sorted(m['word_index'] for m in M if m['status'] == 'deferred')
    snap['ops'] = {}
    for o in A['operators']: snap['ops'].setdefault(o['word_index'], {})[(o['operator'], o['group'])] = o['status']
    snap['units'] = {}; snap['ff'] = {}
    for wi in snap['slots']:
        for s in snap['slots'][wi]:
            k = (wi, s['unit'])
            u = U.get(k)
            if u is not None: snap['units'][k] = dict(R=u.Theta.get('R'))
            f = FF.get(k, {})
            snap['ff'][k] = dict(pos=(f.get('pos') or {}).get('v'), operator=f.get('operator'), idafa=f.get('idafa'), lemma=(f.get('lemma') or {}).get('v'))
    snap['lex'] = {w: [e['entry_id'] for e in lex.lookup(w)] for w in ('أَجَلِ', 'أَجَلْ', 'أَجَلٍ')}
    def tok(idx):
        t = S['tokens'][idx]
        return dict(analyses=[dict(segments=[dict(pos=sg.get('pos'), particle=sg.get('particle')) for sg in a['segments']], evidence=a.get('evidence')) for a in t['analyses']])
    snap['schema'] = {i: tok(i) for i in (19, 75, 57, 97)}
    snap['deps'] = [dict(gov_token=d['governor']['token'], gov_seg=d['governor']['segment'], dep_seg=d['dependent']['segment'], operator_id=d.get('operator_id'), consistent=d.get('consistent')) for d in S['dependencies']]
    cat = [json.loads(l) for l in open(os.path.join(ROOT, 'operators_catalog.jsonl'), encoding='utf-8')]
    g7 = [r for r in cat if (r.get('operator_plain') == 'إذا' or r.get('operator_form') == 'إِذَا') and str(r.get('group_number')) == '7']
    snap['itha_g7_title'] = g7[0].get('group_name_ar') if g7 else None
    snap['stems_count'] = sum(1 for wi in snap['slots'] for s in snap['slots'][wi] if s['type'] == 'جذع')
    # declared E0/E2 export outputs for this stage (data checks read these; verify fingerprint)
    eo = expected.get('export_outputs', {}).get(STAGE, {})
    def load_decl(spec):
        if not spec or spec == 'TO_BE_DECLARED' or not isinstance(spec, dict): return None
        p = spec.get('path');
        if not p or not os.path.exists(p): return None
        if spec.get('sha256') and sha_file(p) != spec['sha256']: return 'FINGERPRINT_MISMATCH'
        return json.load(open(p, encoding='utf-8'))
    snap['e0_export'] = load_decl(eo.get('E0_export')); snap['e2_coverage'] = load_decl(eo.get('E2_coverage'))
    return snap

# ---------- identity helpers (no [0], no literal (wi,0)) ----------
def one(seq, name):
    seq = list(seq)
    if len(seq) != 1: raise AssertionError('COUNT_GUARD %s expected 1 got %d' % (name, len(seq)))
    return seq[0]
def slot_by(snap, wi, **ident): return [s for s in snap['slots'].get(wi, []) if all(s.get(k) == v for k, v in ident.items())]
def uk(snap, wi, **ident): return (wi, one(slot_by(snap, wi, **ident), 'slot@%d %s' % (wi, ident))['unit'])
def dep_gov(snap, tok): return [d for d in snap['deps'] if d['gov_token'] == tok]
def ma_face(snap, tok):
    for a in snap['schema'][tok]['analyses']:
        for sg in a['segments']:
            p = sg.get('particle') or {}
            if sg.get('pos') == 'particle' and 'ما_النفي_الحالي' in (p.get('operator_ids') or []): return a, sg
    return None, None
def verbal_unit(snap, wi):
    ks = []
    for s in snap['slots'].get(wi, []):
        k = (wi, s['unit']); f = snap['ff'].get(k, {}); op = f.get('operator') or {}
        if f.get('pos') == 'فعل' and 'ناسخ' in str(op.get('v', '')): ks.append(k)
    return one(set(ks), 'verbal_unit@%d' % wi)
NAMED = re.compile(r'([ء-ي]{2,4})\s*\(')   # reason-named root pairs like «ءبو (I)»

# ---------- checks ----------
def KEEP_1a(s): return len(s['slots'][85]) == 2 and bool(slot_by(s, 85, type='جذع', text='أَجَلِ')) and bool(slot_by(s, 85, type='مبني', text='هِ'))
def KEEP_1b(s):
    k = uk(s, 85, type='جذع'); return s['units'].get(k, {}).get('R') == 'ءجل' and s['ff'].get(k, {}).get('lemma') == 'أَجَل'
def KEEP_1c(s): return s['units'].get(uk(s, 7, type='جذع'), {}).get('R') == 'ءجل'
def KEEP_1d(s): return 'mabniyat:particle:0235' in s['lex']['أَجَلْ']
def KEEP_1e(s): return s['lex']['أَجَلٍ'] == []
def KEEP_2a(s): return len(s['slots'][91]) == 3 and bool(slot_by(s, 91, type='عامل', text='لِ')) and bool(slot_by(s, 91, type='أل', text='ل')) and bool(slot_by(s, 91, type='جذع', text='شَّهَٰدَةِ'))
def KEEP_2b(s): return s['ops'].get(91) == {('لِ', '1'): 'accepted', ('لِ', '6'): 'blocked'}            # full dict equality
def KEEP_2c(s):
    d = one(dep_gov(s, 91), 'dep91'); return d['gov_seg'] == 0 and d['dep_seg'] == 2 and d['consistent'] is True
def KEEP_2d(s):
    return s['ops'].get(19) == {('كَ', '1'): 'deferred', ('مَا', '3'): 'deferred', ('مَا', '7'): 'deferred'} and \
           s['ops'].get(75) == {('مَا', '3'): 'deferred', ('مَا', '7'): 'deferred'}                      # full dict equality BOTH
def KEEP_4(s): return s['morph_count'] == 46 and s['morph_status'] == {'accepted': 27, 'deferred': 12, 'not_applicable': 7}
def KEEP_5(s):
    for wi in (61, 93, 105):
        m = s['morph'].get(wi)
        if not m: raise AssertionError('COUNT_GUARD morph%d' % wi)
        if not (m['status'] == 'not_applicable' and m['reason'] == 'CONSTITUTIONAL_PROTECTED_CLASS'): return False
    return True
def KEEP_6a(s):
    for wi in (35, 102):
        k = verbal_unit(s, wi); f = s['ff'][k]; op = f.get('operator') or {}
        if not (f['pos'] == 'فعل' and 'ناسخ' in str(op.get('v', '')) and 'VERBAL' in str(op.get('ev', ''))): return False
    return True
def KEEP_6b(s):
    for t in (10, 22, 23, 27, 48):
        ds = [d for d in dep_gov(s, t) if d['operator_id'] == 'ل_الأمر']
        if not ds or not all(d['consistent'] for d in ds): return False
    return True
def KEEP_6c(s):
    for wi in (57, 97):
        m = s['morph'].get(wi)
        if not m: raise AssertionError('COUNT_GUARD morph%d' % wi)
        if m['status'] != 'not_applicable': return False
    return True
def REPRO_1(s): return s['lex']['أَجَلِ'] == ['mabniyat:particle:0235']
def REPRO_2a(s): return one(dep_gov(s, 91), 'dep91')['operator_id'] == 'ل_الملك'
def REPRO_2b(s):
    _, sg = ma_face(s, 75); return sg is not None and (sg.get('particle') or {}).get('effect') == 'raf_ism_nasb_khabar'
def REPRO_2c(s):
    a, sg = ma_face(s, 75)
    if a is None: return False
    ev = [e for e in (a.get('evidence') or []) if e.get('source') == 'catalog']
    return bool(ev) and ev[0].get('id') == 'ما_النفي_الحالي'
def REPRO_3(s):
    m = s['morph'].get(15)
    if not m: raise AssertionError('COUNT_GUARD morph15')
    return ('ءبو' in (m['reason'] or '')) and m['root'] is None and not any(k in m['keys'] for k in ('candidate_faces', 'candidates', 'licensed'))
def REPRO_5a(s):
    sl = s['slots'][93]; return len(sl) == 1 and sl[0]['type'] == 'جذع' and sl[0]['text'] == 'أَلَّا'   # LINT_OK: after count==1 guard
def REPRO_5b(s):
    sl = s['slots'][61]; return len(sl) == 1 and sl[0]['type'] == 'جذع' and sl[0]['text'] == 'مِمَّنْ'  # LINT_OK: after count==1 guard
def REPRO_5c(s): return s['ff'].get(uk(s, 61, type='جذع'), {}).get('pos') == 'عامل من العوامل المائة'
def REPRO_6a(s): return s['ff'].get(uk(s, 3, text='إِذَا'), {}).get('pos') == 'عامل' and s['ff'].get(uk(s, 75, text='مَا'), {}).get('pos') == 'عامل'
def REPRO_6b_membership(s): return s['ops'].get(3, {}).get(('إِذَا', '7')) is not None
def REPRO_6b_title(s): return s['itha_g7_title'] == 'الشرط الجازمة فقط'
def REPRO_6c(s): return any(s['ff'].get((10, u['unit']), {}).get('pos') == 'مبني+عامل' for u in s['slots'][10])
def REPRO_6d(s):
    def all_undet(tok):
        poss = [sg['pos'] for a in s['schema'][tok]['analyses'] for sg in a['segments']]
        return bool(poss) and all(p == 'undetermined' for p in poss)
    return all_undet(57) and all_undet(97) and not s['ops'].get(57) and not s['ops'].get(97)
def REPRO_cloud(s):
    ku = uk(s, 91, type='عامل', text='لِ'); ks = uk(s, 91, type='جذع')
    idf = s['ff'].get(ks, {}).get('idafa') or {}
    return ku[1] == ks[1] and idf.get('v') == 'مضاف إليه'      # jar unit == stem unit (jar inside unit) + idafa face
def INFO_4(s): return s['stems_count'] == 81
# ---- ACCEPT (data contracts) ----
def _faces_contract(faces, reason):
    if not faces: return False
    for f in faces:
        for x in ('root', 'door', 'pattern', 'form_class', 'status', 'face_id'):
            if x not in f or (f[x] is None and f.get(x + '_absence_reason') is None): return False
    denoms = faces  # separate denominators are declared at the record level (checked below)
    # content duplicate detection (root+pattern+class+status), not id only
    sig = [(f['root'], f['pattern'], f['form_class'], f['status']) for f in faces]
    if len(sig) != len(set(sig)): return False
    named = NAMED.findall(reason or '')
    return all(any(f['root'] == r for f in faces) for r in named) if named else True
def ACCEPT_E1(s):
    # applies to ALL 12 deferred records; each must satisfy the structural contract with separate denominators
    recs = [s['morph'].get(wi) for wi in s['deferred_wi']]
    if len(recs) != 12 or any(r is None for r in recs): return False
    for r in recs:
        cf = r.get('candidate_faces')
        if not isinstance(cf, dict): return False
        for dn in ('generated', 'licensed', 'rejected', 'selected', 'distinct_pairs'):
            if dn not in cf: return False       # separate denominators present, no forced equality
        if not _faces_contract(cf.get('faces'), r.get('reason')): return False
    return True
def ACCEPT_E0(s):
    exp = s.get('e0_export')
    if not isinstance(exp, dict): return False
    recs = exp.get('stem_records') or {}
    declared_n = exp.get('declared_count')
    targets = [(wi, st) for wi in s['slots'] for st in s['slots'][wi] if st['type'] == 'جذع' and st['index'] != st['unit']]
    if declared_n is None or declared_n != len(targets): return False   # count guard
    for wi, st in targets:
        key = '%d.%d' % (wi, st['unit'])
        r = recs.get(key)
        if not r or not r.get('features_readable') or r.get('attributed_to_other_cell'): return False
    return True
def ACCEPT_E2(s):
    cov = s.get('e2_coverage')
    if not isinstance(cov, dict): return False
    recs = cov.get('records') or []
    stems = [(wi, st) for wi in s['slots'] for st in s['slots'][wi] if st['type'] == 'جذع']
    seen = set()
    for r in recs:
        for x in ('occ', 'cell', 'unit', 'path', 'state_source'):
            if x not in r: return False
        seen.add((r['cell'][0] if isinstance(r['cell'], list) else r.get('wi'), r.get('cell')))
    return len(recs) == len(stems) and len(set(json.dumps(r.get('occ'), ensure_ascii=False) + str(r.get('cell')) for r in recs)) == len(recs)
def ACCEPT_E4_ma(s):
    a, sg = ma_face(s, 75)
    if sg is None: return False
    seg_eff = (sg.get('particle') or {}).get('effect')
    in_face = (sg.get('particle') or {}).get('candidate_effect')     # effect kept inside the candidate face with status
    return (seg_eff in (None, '')) and bool(in_face)
def ACCEPT_E4_lam(s):
    d = one(dep_gov(s, 91), 'dep91')
    return d['operator_id'] in (None, '') and d['gov_seg'] == 0 and d['dep_seg'] == 2 and d['consistent'] is True
def ACCEPT_E4_order(s):
    # no order-derived single choice present in 19/75/91 outputs
    if one(dep_gov(s, 91), 'dep91')['operator_id'] not in (None, ''): return False
    for tok in (19, 75):
        a, sg = ma_face(s, tok)
        if sg is not None and (sg.get('particle') or {}).get('effect') not in (None, ''): return False
    return True

CHECKS = {'KEEP_1a_seg85': KEEP_1a, 'KEEP_1b_root85': KEEP_1b, 'KEEP_1c_root7': KEEP_1c, 'KEEP_1d_lookup_ajalh': KEEP_1d,
 'KEEP_1e_lookup_ajalin': KEEP_1e, 'KEEP_2a_seg91': KEEP_2a, 'KEEP_2b_ops91': KEEP_2b, 'KEEP_2c_dep91_struct': KEEP_2c,
 'KEEP_2d_ma_groups': KEEP_2d, 'KEEP_4_morph46': KEEP_4, 'KEEP_5_protected': KEEP_5, 'KEEP_6a_kana_laysa': KEEP_6a,
 'KEEP_6b_lam_amr': KEEP_6b, 'KEEP_6c_yakuna': KEEP_6c, 'REPRO_1_ajal_lookup': REPRO_1, 'REPRO_2a_lam_milk': REPRO_2a,
 'REPRO_2b_ma_effect': REPRO_2b, 'REPRO_2c_ma_evidence': REPRO_2c, 'REPRO_3_faces_text': REPRO_3, 'REPRO_5a_alla_single': REPRO_5a,
 'REPRO_5b_mimman_single': REPRO_5b, 'REPRO_5c_mimman_pos': REPRO_5c, 'REPRO_6a_amil_pos': REPRO_6a,
 'REPRO_6b_membership': REPRO_6b_membership, 'REPRO_6b_title': REPRO_6b_title, 'REPRO_6c_waw_lam_merge': REPRO_6c,
 'REPRO_6d_yakuna_schema': REPRO_6d, 'REPRO_cloud_shahada_mudaf': REPRO_cloud, 'ACCEPT_E0_unit_after_al': ACCEPT_E0,
 'ACCEPT_E1_faces_contract': ACCEPT_E1, 'ACCEPT_E2_coverage': ACCEPT_E2, 'ACCEPT_E4_ma_not_escalated': ACCEPT_E4_ma,
 'ACCEPT_E4_lam_relation_kept': ACCEPT_E4_lam, 'ACCEPT_E4_order_invariant': ACCEPT_E4_order, 'INFO_4_stems81': INFO_4}

def run_checks(snap, expected):
    rows, info = [], []
    for name, fn in CHECKS.items():
        meta = expected['checks'][name]; exp = meta['states'][STAGE]
        try: actual = bool(fn(snap)); err = None
        except Exception as e: actual = None; err = '%s: %s' % (type(e).__name__, e)
        if meta['type'] == 'INFO': info.append(dict(check=name, actual=actual, error=err)); continue
        cat = 'execution_error' if err else ('match' if actual == exp else ('broken_KEEP' if meta['type'] == 'KEEP' else 'undeclared_flip'))
        rows.append(dict(check=name, type=meta['type'], expected=exp, actual=actual, category=cat, error=err))
    return rows, info

# ---------- positive controls (synthetic) for ACCEPT ----------
def control_snap(name, snap):
    c = copy.deepcopy(snap); c['_synthetic'] = True
    if name == 'ACCEPT_E1_faces_contract':
        for wi in c['deferred_wi']:
            r = c['morph'][wi]; named = NAMED.findall(r.get('reason') or '') or ['xxx']
            r['candidate_faces'] = dict(generated=len(named), licensed=len(named), rejected=0, selected=0, distinct_pairs=len(set(named)),
                faces=[dict(root=rt, door='I', pattern='ف', form_class='I', status='LICENSED_NOT_SELECTED', face_id='f%d' % i) for i, rt in enumerate(named)])
    elif name == 'ACCEPT_E0_unit_after_al':
        targets = [(wi, st) for wi in c['slots'] for st in c['slots'][wi] if st['type'] == 'جذع' and st['index'] != st['unit']]
        c['e0_export'] = dict(declared_count=len(targets), stem_records={'%d.%d' % (wi, st['unit']): dict(features_readable=True, attributed_to_other_cell=False) for wi, st in targets})
    elif name == 'ACCEPT_E2_coverage':
        stems = [(wi, st) for wi in c['slots'] for st in c['slots'][wi] if st['type'] == 'جذع']
        c['e2_coverage'] = dict(records=[dict(occ='Q2:282#%d' % wi, cell=st['index'], unit=st['unit'], wi=wi, path='noun_unit', state_source='units') for wi, st in stems])
    elif name == 'ACCEPT_E4_ma_not_escalated':
        for tok in (75,):
            for a in c['schema'][tok]['analyses']:
                for sg in a['segments']:
                    p = sg.get('particle') or {}
                    if sg.get('pos') == 'particle': p['effect'] = None; p['candidate_effect'] = dict(effect='raf_ism_nasb_khabar', status='CANDIDATE')
    elif name in ('ACCEPT_E4_lam_relation_kept', 'ACCEPT_E4_order_invariant'):
        for d in c['deps']:
            if d['gov_token'] == 91: d['operator_id'] = None
        for tok in (19, 75):
            for a in c['schema'][tok]['analyses']:
                for sg in a['segments']:
                    p = sg.get('particle') or {}
                    if sg.get('pos') == 'particle': p['effect'] = None
    return c

# ---------- corruption (one per non-INFO check) ----------
def corruptions(snap):
    res = []
    def flip(name, mut, base=None):
        c = copy.deepcopy(base if base is not None else snap)
        mut(c)
        try: r = bool(CHECKS[name](c))
        except Exception: r = None
        res.append(dict(corruption='corrupt_%s' % name, target=name, result_after=r, PASS=(r is not True)))
    def del_slot(wi, **id):
        def m(c):
            c['slots'][wi] = [s for s in c['slots'][wi] if not all(s.get(k) == v for k, v in id.items())]
        return m
    def set_lex(w, v): return lambda c: c['lex'].__setitem__(w, v)
    def del_unit(k): return lambda c: c['units'].pop(k, None)
    def set_ff(k, field, v): return lambda c: c['ff'].setdefault(k, {}).__setitem__(field, v)
    def del_morph(wi): return lambda c: c['morph'].pop(wi, None)
    def set_ops(wi, v): return lambda c: c['ops'].__setitem__(wi, v)
    def set_dep91(field, v):
        def m(c):
            for d in c['deps']:
                if d['gov_token'] == 91: d[field] = v
        return m
    # KEEP
    flip('KEEP_1a_seg85', del_slot(85, type='مبني', text='هِ'))
    flip('KEEP_1b_root85', lambda c: c['units'].__setitem__((85, 0), {'R': 'XXX'}))
    flip('KEEP_1c_root7', lambda c: c['units'].__setitem__((7, 0), {'R': 'XXX'}))
    flip('KEEP_1d_lookup_ajalh', set_lex('أَجَلْ', []))
    flip('KEEP_1e_lookup_ajalin', set_lex('أَجَلٍ', ['x']))
    flip('KEEP_2a_seg91', del_slot(91, type='جذع'))
    flip('KEEP_2b_ops91', set_ops(91, {('لِ', '1'): 'accepted'}))     # missing group6 -> full-dict fails
    flip('KEEP_2c_dep91_struct', set_dep91('consistent', False))
    flip('KEEP_2d_ma_groups', lambda c: c['ops'].__setitem__(19, {('مَا', '3'): 'deferred', ('مَا', '7'): 'deferred'}))  # missing (كَ,1)
    flip('KEEP_4_morph46', lambda c: c.__setitem__('morph_count', 45))
    flip('KEEP_5_protected', del_morph(93))
    flip('KEEP_6a_kana_laysa', set_ff((35, 0), 'operator', {'v': 'x', 'ev': 'y'}))
    flip('KEEP_6b_lam_amr', lambda c: [d.__setitem__('operator_id', 'x') for d in c['deps'] if d['gov_token'] == 10])
    flip('KEEP_6c_yakuna', del_morph(57))
    # REPRO
    flip('REPRO_1_ajal_lookup', set_lex('أَجَلِ', []))
    flip('REPRO_2a_lam_milk', set_dep91('operator_id', None))
    flip('REPRO_2b_ma_effect', lambda c: [sg.get('particle', {}).__setitem__('effect', None) for a in c['schema'][75]['analyses'] for sg in a['segments'] if sg.get('particle')])
    flip('REPRO_2c_ma_evidence', lambda c: [a.__setitem__('evidence', []) for a in c['schema'][75]['analyses']])
    flip('REPRO_3_faces_text', lambda c: c['morph'][15].__setitem__('reason', ''))
    flip('REPRO_5a_alla_single', del_slot(93, type='جذع'))
    flip('REPRO_5b_mimman_single', del_slot(61, type='جذع'))
    flip('REPRO_5c_mimman_pos', set_ff((61, 0), 'pos', 'x'))
    flip('REPRO_6a_amil_pos', set_ff((3, 0), 'pos', 'x'))
    flip('REPRO_6b_membership', set_ops(3, {}))
    flip('REPRO_6b_title', lambda c: c.__setitem__('itha_g7_title', 'x'))
    flip('REPRO_6c_waw_lam_merge', set_ff((10, 0), 'pos', 'x'))
    flip('REPRO_6d_yakuna_schema', lambda c: [sg.__setitem__('pos', 'noun') for a in c['schema'][57]['analyses'] for sg in a['segments']])
    flip('REPRO_cloud_shahada_mudaf', lambda c: c['ff'].setdefault((91, 0), {}).__setitem__('idafa', None))
    # ACCEPT: corrupt a passing positive control
    def corrupt_ctrl(name, mut):
        base = control_snap(name, snap)
        ctrl_ok = None
        try: ctrl_ok = bool(CHECKS[name](base))
        except Exception: ctrl_ok = None
        flip(name, mut, base=base)
        res[-1]['positive_control_passes'] = (ctrl_ok is True)
    corrupt_ctrl('ACCEPT_E1_faces_contract', lambda c: [c['morph'][wi]['candidate_faces']['faces'].pop() for wi in c['deferred_wi'] if c['morph'][wi]['candidate_faces']['faces']])  # drop a face
    corrupt_ctrl('ACCEPT_E0_unit_after_al', lambda c: next(iter(c['e0_export']['stem_records'].values())).__setitem__('attributed_to_other_cell', True))
    corrupt_ctrl('ACCEPT_E2_coverage', lambda c: c['e2_coverage']['records'].pop())
    corrupt_ctrl('ACCEPT_E4_ma_not_escalated', lambda c: [sg.get('particle', {}).__setitem__('effect', 'raf_ism_nasb_khabar') for a in c['schema'][75]['analyses'] for sg in a['segments'] if sg.get('particle')])
    corrupt_ctrl('ACCEPT_E4_lam_relation_kept', set_dep91('operator_id', 'ل_الملك'))
    corrupt_ctrl('ACCEPT_E4_order_invariant', set_dep91('operator_id', 'ل_الملك'))
    return res

# ---------- code lint: no [0] on output lists, no literal (wi,0) keys (except LINT_OK) ----------
def code_lint():
    # scope: the CHECK functions only (production read path). Corruption/control fixtures deliberately
    # target positions and are declared out of scope (between the markers below).
    src = open(os.path.join(HERE, os.path.basename(__file__)), encoding='utf-8').read().splitlines()
    start = next((i for i, l in enumerate(src) if '# ---------- checks ----------' in l), 0)
    end = next((i for i, l in enumerate(src) if '# ---------- positive controls' in l), len(src))
    bad = []
    pat_idx = re.compile(r'(analyses|segments|slots|deps|rows|faces|records|evidence)\]?\[0\]')
    pat_tup = re.compile(r'\((\d+),\s*0\)')
    for i in range(start, end):
        ln = src[i]
        if 'LINT_OK' in ln: continue
        if pat_idx.search(ln) or pat_tup.search(ln): bad.append(dict(line=i + 1, text=ln.strip()[:80]))
    return dict(scope='check functions [%d..%d]; corruption/control fixtures excluded (declared)' % (start + 1, end + 1), violations=bad)

def main():
    os.makedirs(OUT, exist_ok=True)
    expected, (decl_fp, act_fp, fp_ok) = load_expected()
    p = pin(expected)
    stop = list(p['problems'])
    if decl_fp is not None and not fp_ok: stop.append('EXPECTED_STATES_FINGERPRINT_MISMATCH (file modified after fingerprint)')
    if stop:
        json.dump(dict(stage=STAGE, verdict='IDENTITY_MISMATCH_STOP', problems=stop, pin=p), open(os.path.join(OUT, 'report_%s.json' % STAGE), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(json.dumps(dict(verdict='IDENTITY_MISMATCH_STOP', problems=stop), ensure_ascii=False)); sys.exit(2)
    snap = build_snapshot(expected)
    rows, info = run_checks(snap, expected)
    from collections import Counter
    cats = Counter(r['category'] for r in rows)
    corr = corruptions(snap); lint = code_lint()
    all_match = cats.get('undeclared_flip', 0) == 0 and cats.get('broken_KEEP', 0) == 0 and cats.get('execution_error', 0) == 0
    corr_ok = all(c['PASS'] for c in corr) and all(c.get('positive_control_passes', True) for c in corr)
    lint_ok = not lint['violations']
    exit_code = 0 if (all_match and corr_ok and lint_ok) else 1
    report = dict(round='SARF_MORPH_EXPORT_REPAIR_01', batch='STEP2a_tests', stage=STAGE,
                  pin=dict(sarf_tree=p['sarf_tree'], engine_dump2_blob=p['engine_dump2_blob'], release=p['release'],
                           test_tool_fingerprints=p['test_tool_fingerprints']),
                  expected_states_fingerprint=dict(declared=decl_fp, actual=act_fp, ok=fp_ok),
                  categories=dict(cats), rows=rows, info=info,
                  corruption=dict(all_pass=corr_ok, count=len(corr), tests=corr),
                  code_lint=dict(ok=lint_ok, **lint),
                  gate=dict(before_matches=all_match, every_check_has_failing_corruption=corr_ok, lint_ok=lint_ok, no_claim_of_fixing_any_defect=True),
                  verdict='STEP2a_PASS' if exit_code == 0 else 'STEP2a_FAIL', exit_code=exit_code)
    json.dump(report, open(os.path.join(OUT, 'report_%s.json' % STAGE), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(dict(stage=STAGE, verdict=report['verdict'], categories=dict(cats), corruption_all_pass=corr_ok, lint_ok=lint_ok,
                          info=[(i['check'], i['actual']) for i in info], exit_code=exit_code), ensure_ascii=False))
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
