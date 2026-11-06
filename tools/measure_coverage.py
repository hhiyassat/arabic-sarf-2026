#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/measure_coverage.py — مقاييس تغطيةٍ مستقلة لمحاور الوحدة وعلاقاتها (جولة 006 وملحقها)، على المصحف المعتمد كله أو آية.

كل مقياسٍ بمقامه واستبعاداته ووحدة عدّه (تُكتب في JSON مع الأعداد)؛ ولا تُعدّ المواضع الصامتة إجاباتٍ صحيحة، ولا «صفر خلل» صحةً شاملة:
  M1 تغطية الصنف        الوحدة: وحدة التحليل؛ المقام: كل الوحدات؛ المحسوم: صنفٌ بدليل (اسم، فعل، حرف، حرف + اسم)
  M2 تغطية البناء       الوحدة: وحدة التحليل؛ المقام: كل الوحدات؛ المحسوم: «مبني» أو «معرب» بدليل
  M3 تغطية الإعراب      المقام: (أ) المعرب: حالةٌ متفقة (AGREE)؛ (ب) الاسم المبني: محلٌّ متفق؛ ويُستبعد ما لا ينتظر إعراباً:
                        الحرف (لا محلّ له مثبت)، والماضي والأمر المبنيّان، والأداة لا محلّ لها — فلا تُعدّ «فاقدة»
  M4 تغطية الأدوار      المقام: الأسماء (صنفها اسم)؛ المحسوم: دورٌ من علاقةٍ مرخَّصة (لا مجرّد وجودٍ في علاقة)
  M5 العلاقات بنوعها    الوحدة: السجل؛ بحالته (LICENSED، DEFERRED، REJECTED، CONFLICT)
  M6 متطلبات النوى      إطار الفعل: الإسناد مستوفى (فاعلٌ أو نائبه أو ضميره مرخَّص، أو ناسخٌ يُحال إلى V01)؛ الناسخ: الخبر مرخَّص؛
                        الإسناد الاسمي: nucleus_complete
  M7 اكتمال الجملة      من الطبقة القديمة (المرحلة ١٤) بجهتيها: التمام (F) والإغلاق؛ وشهادة الإغلاق الموحَّدة التي تستهلك علاقات 14أ
  وأسباب ما لم يُحسم: قاعدة غير منفذة، مدخل معجمي ناقص، صيغة صرفية متعددة، علاقة منافسة، نطاق غير محسوم، دليل سابق غير موصول،
  تعارض أدلة، غير منطبق.

    PYTHONHASHSEED=0 python3 tools/measure_coverage.py [--verse 2:282] [--jobs N] [--json out.json]
"""
import argparse, collections, json, os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
_CAT = []
REASONS = ('قاعدة غير منفذة', 'مدخل معجمي ناقص', 'صيغة صرفية متعددة', 'علاقة منافسة', 'نطاق غير محسوم', 'دليل سابق غير موصول',
           'تعارض أدلة', 'غير منطبق')
MABNI_REASON = {'EVIDENCE_NOT_ADOPTED': 'دليل سابق غير موصول', 'LEXICAL_ENTRY_MISSING': 'مدخل معجمي ناقص',
                'MAHALL_UNRESOLVED': 'علاقة منافسة', 'ROLE_RULE_NOT_IMPLEMENTED': 'قاعدة غير منفذة', 'NO_MAHALL': 'غير منطبق'}


def _surah(items):
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo, linguistic_layer
    from sarf.features import unit_features
    from sarf.relations import verse_relations, check_inflection, check_records, check_cross
    from sarf import quran_source
    its, per = [], []
    for s, v, text in items:
        a = analyze(_CAT[0], text, quran_source.uthmani_mode())
        S, U = sentence_geo(a, f'Q{s}:{v}', Trace())
        its.append((s, v, a, U, S))
        per.append((s, v, a, U, unit_features(a, U)))
    C, Rl = [], []
    LT, st, _ = linguistic_layer(its, Trace(), 'cov', cond_out=C, rel_out=Rl)
    J = collections.defaultdict(int, total=0, closed=0, F_complete=0, closed_unreconciled=0)
    closed_spans = []
    for SP in LT:
        for D in SP.A + SP.O.get('pending', []):
            for Jx in D.A + D.O.get('pending', []):
                J['total'] += 1
                J['closed'] += bool(Jx.closed)
                if Jx.closed:
                    closed_spans.append({f'{a_}:{b_}:{c_ + 1}' for (a_, b_, c_) in Jx.O.get('location', [])})
                J['F_complete'] += 'تام' in str((Jx.O.get('boundary') or {}).get('F') or '')
    out = []
    unrec = []
    RECS_BY_VERSE = {}
    for s, v, a, U, F in per:
        ref = f'{s}:{v}'
        o = verse_relations(a, U, F, ref, legacy_cond=C, legacy_rel=Rl)
        RECS_BY_VERSE[(s, v)] = o['records']
        chk = check_records(o['records'], o['tokens']) + check_cross(o['records'], o['axes']) + check_inflection(o['axes'], o['tokens'])
        pend = collections.defaultdict(set)
        for r in o['records']:
            if r['status'] != 'LICENSED':
                for us in r['members'].values():
                    for u in us:
                        pend[u].add(r['type'])
        units = []
        for uid, loc, tx in o['tokens']:
            ax = o['axes'][uid]
            inf = ax['inflection']
            units.append(dict(uid=uid, loc=loc, text=tx, wc=ax['word_class'][0], build=inf['build'][0], agreement=inf['agreement'],
                              mark_kind=inf.get('mark_kind'), role=(ax.get('role') or [None])[0], role_status=ax.get('role_status'),
                              mabni=(ax.get('mabni_state') or {}).get('code'), state=inf['state'][1] if inf.get('state') else '',
                              mark=inf['mark'] and inf['mark'][0], gov_rel=(inf.get('governor') or {}).get('relation'),
                              pend=sorted(pend.get(uid, ()))))
        for r in o['records']:
            if r['status'] != 'LICENSED' or r['type'] == 'VERB_FRAME' and (r.get('frame') or {}).get('open'):
                ls_ = {l_ for v_ in r['positions'].values() for l_ in v_}
                if ls_:
                    unrec.append(ls_)
        recs = [dict(type=r['type'], rule=r['rule_id'], status=r['status'], frame=r.get('frame'), nucleus_complete=r.get('nucleus_complete'),
                     heads=list(r['heads']), resumptive=(r.get('resumptive') or {}).get('status')) for r in o['records']]
        out.append(dict(verse=ref, units=units, records=recs, check=chk))
    J['closed_unreconciled'] = sum(any(ls_ <= sp for ls_ in unrec) for sp in closed_spans)
    # شهادة الإغلاق الموحَّدة (الدفعة F): الحكم لكل جملة، والتزاماتها المستوفاة بمصدرها، وتعارض الطبقتين
    from sarf.algebra import closure_certificate, CLOSURE_AR, OBL_STATUS_AR, CLOSURE_LEVELS
    for lv in CLOSURE_LEVELS:
        for k_ in CLOSURE_AR:
            J[f'lv:{lv}:{k_}'] = 0
    for k_ in list(CLOSURE_AR) + ['obl:' + x for x in OBL_STATUS_AR] + ['obl_discharged_by_14a', 'residual:SELECTION', 'residual:BOUNDARY',
                                                                        'residual:COVERAGE', 'residual:REQUIRED', 'rejected_faces']:
        J[k_] = 0
    for SP in LT:
        for D in SP.A + SP.O.get('pending', []):
            for Jx in D.A + D.O.get('pending', []):
                vv = sorted({(x[0], x[1]) for x in Jx.O.get('location', [])})
                c_ = closure_certificate(Jx, [r for x in vv for r in RECS_BY_VERSE.get(x, [])])
                J[c_['verdict']] += 1
                for lv, v_ in c_['verdict_by_level'].items():
                    J[f'lv:{lv}:{v_}'] += 1
                for lv, b_ in c_['boundary']['levels'].items():
                    J[f'blv:{lv}:{b_}'] += 1
                J['face_mismatch'] += sum(str(ob['residual_reason']).startswith(('FACE_MISMATCH', 'FACE_PARTIAL')) for ob in c_['obligations'])
                for ob in c_['obligations']:
                    J['obl:' + ob['status']] += 1
                    J['obl_discharged_by_14a'] += bool(ob.get('discharge_relation_id'))
                for x in c_['residuals']:
                    J['residual:' + x['kind']] += 1
                J['rejected_faces'] += len(c_['rejected_faces'])
    return dict(verses=out, sentences=dict(J))


def reason(u):
    """سبب ما لم يُحسم في الإعراب أو المحلّ"""
    if u['agreement'] == 'CONFLICT':
        return 'تعارض أدلة'
    if u['mabni']:
        return MABNI_REASON[u['mabni']]
    if u['agreement'] == 'N/A':
        return 'صيغة صرفية متعددة'
    if u['agreement'] == 'UNVERIFIED':
        if u['gov_rel'] == 'غير مرخَّص في الجرد':
            return 'مدخل معجمي ناقص'
        return 'صيغة صرفية متعددة'
    if u['agreement'] == 'UNGOVERNED':
        if u['pend']:
            return 'علاقة منافسة'
        if (u['mark'] or '') in ('الحرف أو الحركة',):
            return 'صيغة صرفية متعددة'
        return 'قاعدة غير منفذة'
    return 'قاعدة غير منفذة'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verse')
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--json')
    a = ap.parse_args()
    from sarf.catalog import Catalog
    from sarf import quran_source
    _CAT.append(Catalog([os.path.join(H, 'operators_catalog.jsonl'), os.path.join(H, 'operators_catalog_split_vocalized.csv')]))
    V = quran_source.rows()
    if a.verse:
        s, v = map(int, a.verse.split(':'))
        groups = [[t for t in V if t[0] == s and t[1] == v]]
    else:
        by = collections.OrderedDict()
        for t in V:
            by.setdefault(t[0], []).append(t)
        groups = list(by.values())
    import multiprocessing as mp
    with mp.get_context('fork').Pool(a.jobs) as P:
        res = P.map(_surah, groups, chunksize=1)
    U = [u for r in res for x in r['verses'] for u in x['units']]
    RECS = [rc for r in res for x in r['verses'] for rc in x['records']]
    CHK = [f"{x['verse']}: {e}" for r in res for x in r['verses'] for e in x['check']]
    SENT = collections.Counter()
    for r in res:
        SENT.update(r['sentences'])
    n = len(U)
    M = {}
    M['M1_class'] = dict(unit='وحدة التحليل', scope='كل الوحدات', exclusions=[], total=n, resolved=sum(u['wc'] is not None for u in U),
                         by_value=dict(collections.Counter(str(u['wc']) for u in U)))
    M['M2_build'] = dict(unit='وحدة التحليل', scope='كل الوحدات', exclusions=[], total=n, resolved=sum(u['build'] is not None for u in U),
                         by_value=dict(collections.Counter(str(u['build']) for u in U)))
    murab = [u for u in U if u['build'] == 'معرب']
    # المستبعد: ما ثبت أنه لا ينتظر علامة إعراب — الحرف (NO_MAHALL) والفعل المبني؛ وما سواه من المبني (اسمٌ، أو أداةٌ لها مداخل اسمية،
    # أو بلا مدخل) يبقى في المقام بسبب عدم حسمه
    excl = [u for u in U if u['build'] == 'مبني' and (u['mabni'] == 'NO_MAHALL' or u['wc'] == 'فعل')]
    mnoun = [u for u in U if u['build'] == 'مبني' and u not in excl]
    nob = [u for u in U if u['build'] is None]
    M['M3_irab'] = dict(unit='وحدة التحليل', scope='(أ) المعرب، (ب) المبني غير الحرف وغير الفعل (الاسم، والأداة ذات المداخل الاسمية)، (ج) غير محسوم البناء',
                        exclusions='الحرف والأداة والماضي والأمر المبنيّان: لا ينتظر علامة إعرابٍ لفظية ولا يُعدّ فاقداً',
                        murab=dict(total=len(murab), resolved=sum(u['agreement'] == 'AGREE' for u in murab),
                                   by_agreement=dict(collections.Counter(u['agreement'] for u in murab))),
                        unknown_build_units=dict(total=len(nob), note='بناؤها غير محسوم (صنفٌ غير محسوم أو زمنٌ مرشّح): في المقام غير محسومة'),
                        mabni_nonparticle=dict(total=len(mnoun), resolved=sum(u['agreement'] == 'AGREE' for u in mnoun),
                                        by_state=dict(collections.Counter(u['mabni'] or u['agreement'] for u in mnoun))),
                        excluded=len(excl), excluded_by=dict(collections.Counter(u['mabni'] or u['agreement'] for u in excl)),
                        unknown_build=sum(u['build'] is None for u in U))
    nouns = [u for u in U if (u['wc'] or '').startswith(('اسم', 'حرف + اسم'))]
    M['M4_roles'] = dict(unit='وحدة التحليل', scope='الأسماء (صنفها اسم بدليل)', exclusions='الأفعال والحروف: أدوارها ليست موضع هذا المقياس',
                         total=len(nouns), resolved=sum(u['role'] is not None and u['role_status'] == 'LICENSED' for u in nouns),
                         by_role=dict(collections.Counter(str(u['role']).split(' (')[0].split('«')[0] for u in nouns if u['role'])),
                         note='الدور من علاقةٍ مرخَّصة وحدها؛ ووجود الوحدة في علاقةٍ مؤجَّلة لا يُعدّ دوراً')
    M['M5_relations'] = dict(unit='سجل العلاقة', by_type_status=dict(collections.Counter(f"{r['type']}|{r['rule']}|{r['status']}" for r in RECS)))
    fr = [r for r in RECS if r['type'] == 'VERB_FRAME']
    def subj_ok(r):
        s_ = (r['frame'] or {}).get('subject') or {}
        return s_.get('status') == 'LICENSED' or (r['frame'] or {}).get('subject_requirement') == 'اسم الناسخ'
    nas = [r for r in RECS if r['type'] == 'NASIKH']
    pr = [r for r in RECS if r['type'] in ('PREDICATION', 'PREDICATIVE_PP')]
    M['M6_nuclei'] = dict(unit='سجل النواة', verb_frames=dict(total=len(fr), subject_satisfied=sum(subj_ok(r) for r in fr),
                                                              coherent=sum(r['status'] == 'LICENSED' for r in fr),
                                                              by_subject_kind=dict(collections.Counter(
                                                                  str(((r['frame'] or {}).get('subject') or {}).get('kind')) for r in fr))),
                          nasikh=dict(total=len(nas), complete=sum(r['status'] == 'LICENSED' for r in nas)),
                          nominal=dict(total=len(pr), complete=sum(bool(r['nucleus_complete']) for r in pr)),
                          note='الفعل لا يحتاج كلُّه فاعلاً ومفعولاً: المتطلَّب بحسب البناء والاستعمال (الناسخ يطلب اسماً وخبراً، والمبني للمجهول نائب فاعل)')
    from sarf.algebra import CLOSURE_AR, OBL_STATUS_AR, CLOSURE_LEVELS
    M['M7_sentences'] = dict(unit='جملة الطبقة القديمة (المرحلة ١٤)', total=SENT['total'], closed=SENT['closed'], F_complete=SENT['F_complete'],
                             closed_unreconciled=SENT['closed_unreconciled'],
                             unified=dict(verdicts={k: SENT.get(k, 0) for k in CLOSURE_AR},
                                          obligations={k: SENT.get('obl:' + k, 0) for k in OBL_STATUS_AR},
                                          obligations_discharged_by_named_14a_relation=SENT.get('obl_discharged_by_14a', 0),
                                          residuals={k: SENT.get('residual:' + k, 0) for k in ('SELECTION', 'BOUNDARY', 'COVERAGE', 'REQUIRED')},
                                          rejected_faces=SENT.get('rejected_faces', 0),
                                          verdict_level='SENTENCE',
                                          verdicts_by_level={lv: {k: SENT.get(f'lv:{lv}:{k}', 0) for k in CLOSURE_AR} for lv in CLOSURE_LEVELS},
                                          boundary_by_level={lv: {k.split(':')[2]: v for k, v in SENT.items() if k.startswith(f'blv:{lv}:')}
                                                             for lv in CLOSURE_LEVELS},
                                          face_mismatch=SENT.get('face_mismatch', 0)),
                             note='closed وF_complete من الطبقة القديمة وحدها؛ وunified من شهادة الإغلاق الموحَّدة v2 (sarf.algebra.closure_certificate): '
                                  'أحكام الجملة السبعة، وحالات الالتزامات بأنواعها (لا يُستوفى التزامٌ إلا بعلاقةٍ من نوعه للوحدة والوجه)، '
                                  'وما في 14أ داخل المدى مؤجَّلاً مصنَّفاً (اختيار، حدّ، تغطية، لازم). '
                                  'closed_unreconciled: المغلقة التي في مداها علاقةٌ في 14أ مؤجَّلة أو إطارٌ بالتزامٍ مفتوح')
    unres = collections.Counter()
    ex = collections.defaultdict(list)
    for u in murab + mnoun + nob:
        if u['agreement'] != 'AGREE':
            r_ = reason(u)
            unres[r_] += 1
            if len(ex[r_]) < 8:
                ex[r_].append(f"{u['loc']} {u['text']}")
    unres['غير منطبق'] += len(excl)
    att = [r for r in RECS if r['type'] == 'ATTACH']
    M['unresolved_reasons'] = dict(unit='وحدة التحليل (المعرب والاسم المبني غير المحسومَين)، وغير المنطبق للمستبعد', counts={k: unres.get(k, 0) for k in REASONS},
                                   examples=dict(ex), attach_scope_unresolved=sum(r['status'] != 'LICENSED' for r in att),
                                   attach_note='التعلّق غير المرخَّص يُعدّ «نطاق غير محسوم» على مستوى العلاقة، لا الوحدة')
    rep = dict(source=quran_source.name(), scope=a.verse or 'المصحف كله', units=n, metrics=M, checker_errors=len(CHK), checker_examples=CHK[:20])
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk not in ('examples', 'by_value', 'by_type_status')})
                      for k, v in M.items()}, ensure_ascii=False, indent=1)[:6000])
    print('checker errors', len(CHK))
    if a.json:
        json.dump(rep, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
