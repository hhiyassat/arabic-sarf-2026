"""tools/upstream_candidates.py — دفعة الإضافة (SARF_UPSTREAM_CONSUMPTION_ADDENDUM_01، المسار الأول).

يمرّ على المصحف كله بالمحلّل كما هو، ويجمع لكل وقوعٍ فعلي مرشّحه الصرفي (frame.candidate) وجذره ووزنه، واللمّة المشكولة من
HFN v36 للمرشّح نفسه، ثم يسأل الموارد الخارجية في عمليةٍ فرعية معزولة (tools/upstream/worker.py)، ويكتب السمات المرشّحة في ملفٍّ
جانبي. لا يغيّر مخرجاً قائماً: المحلّل لا يستورد هذا الملف، ولا تدخل نتائجه قرار التعدية ولا غيره.

    SARF_UP_AMLN=… SARF_UP_WAZN=… SARF_UP_HFN=… SARF_UP_MAQ=… PYTHONHASHSEED=0 python3 -s tools/upstream_candidates.py OUT.jsonl.gz SUMMARY.json [--verses 2:282,112:3]

السلسلة لكل سمة: وقوع النص ← المرشّح الصرفي ← اللمّة المشكولة ← صفّ المصدر ← السمة المرشّحة.
"""
import collections, gzip, itertools, json, math, multiprocessing as mp, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'upstream'))
os.chdir(ROOT)


def wilson(k, n, z=1.959964):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    return round((p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d, 3)


# سجلّ المسالك: ما يُستهلك وما يُحجب، بقياسه ومصدر القياس. «reported» قيمةٌ منقولة من سجلّ القياس الأصلي، «recomputed» أُعيد حسابها هنا
ROUTES = {
    ('AMLN', 'R1'): dict(status='ACCEPTED_ROUTE', measurement_id='AMLN:qabiliyyat/SCORES_v1.json#R1_MUTAWAA',
                         precision=0.964, wilson_low=0.877, wilson_source='reported (SCORES_v1.json: wilson_low)',
                         sanad='كشف الأسرار:9670'),
    ('AMLN', 'R1W'): dict(status='ACCEPTED_ROUTE', measurement_id='AMLN:ahdath/mutawaa_R1W_gold.tsv (v2)', precision=round(53 / 57, 3),
                          wilson_low=wilson(53, 57), wilson_source='recomputed from 53/57 (handoff)', sanad='الكليات:27626–27627'),
    ('AMLN', 'T_JAL'): dict(status='ACCEPTED_ROUTE', measurement_id='AMLN:ahdath T_JAL 25/25', precision=1.0, wilson_low=wilson(25, 25),
                            wilson_source='recomputed from 25/25 (handoff)', sanad='الكتاب:16451–16455'),
    ('AMLN', 'J_SAJIYYA'): dict(status='ACCEPTED_ROUTE', measurement_id='AMLN:ahdath/jiha_gold_J_SAJIYYA.tsv', precision=1.0,
                                wilson_low=0.890, wilson_source='reported (word_tree/ahdath.py JIHA_ROUTES)', sanad='الكتاب:16143–16144'),
    ('AMLN', 'J_DAA'): dict(status='ACCEPTED_ROUTE', measurement_id='AMLN:ahdath/jiha_gold_J_DAA.tsv', precision=0.975,
                            wilson_low=0.871, wilson_source='reported (word_tree/ahdath.py JIHA_ROUTES)', sanad='الكتاب:16016؛ 16108'),
    ('WAZN', 'R1_QABILIYYAT'): dict(status='ACCEPTED_ROUTE', measurement_id='AMLN:qabiliyyat/SCORES_v1.json#R1_MUTAWAA', precision=0.964,
                                    wilson_low=0.877, wilson_source='reported', sanad='كشف الأسرار:9670'),
    ('WAZN', 'LEX_FORMULA'): dict(status='ACCEPTED_ROUTE', measurement_id='WAZN:evidence/mutawaa_sample60_judged.tsv', precision=round(56 / 59, 3),
                                  wilson_low=0.861, wilson_source='reported (HANDOFF_ARABIC_MOTHER_NET.md: R56/W3/?1)', sanad='المعاجم (صيغة «فعلته فانفعل»)'),
    ('WAZN', 'R1W_WASIT'): dict(status='ACCEPTED_ROUTE', measurement_id='AMLN:ahdath/mutawaa_R1W_gold.tsv (v2)', precision=round(53 / 57, 3),
                                wilson_low=wilson(53, 57), wilson_source='recomputed from 53/57', sanad='الكليات:27626–27627'),
    ('WAZN', 'T_JAL'): dict(status='ACCEPTED_ROUTE', measurement_id='AMLN:ahdath T_JAL 25/25', precision=1.0, wilson_low=wilson(25, 25),
                            wilson_source='recomputed from 25/25', sanad='الكتاب:16451–16455'),
    ('HFN37', 'MASDAR_WASIT_V37'): dict(status='ACCEPTED_ROUTE', measurement_id='HFN:06_handoff/MASDAR_WASIT_PROPOSE_sample60_judged.tsv',
                                        precision=round(53 / 59, 3), wilson_low=wilson(53, 59), wilson_source='recomputed from 53/59 (handoff)',
                                        sanad='المعجم الوسيط (M11)؛ إضافةٌ لا استبدال'),
    ('HFN37', 'TRANSITIVITY_WASIT_V37'): dict(status='ACCEPTED_ROUTE', measurement_id='WAZN:evidence/transitivity_wasit_sample60_judged.tsv (مصدر FILL)',
                                              precision=1.0, wilson_low=wilson(44, 44), wilson_source='recomputed from 44/44',
                                              sanad='المعجم الوسيط (M11)'),
    ('WAZN', 'TRANSITIVITY_WASIT_V1'): dict(status='ACCEPTED_ROUTE', measurement_id='WAZN:evidence/transitivity_wasit_sample60_judged.tsv',
                                            precision=1.0, wilson_low=wilson(44, 44), wilson_source='recomputed from 44/44 (handoff)',
                                            sanad='المعجم الوسيط (M11)'),
}
# المحجوب: لا يُستعمل دليلاً، ويُحفظ في سجلّه بسببه
BLOCKED = {
    ('AMLN', 'R2'): 'ويلسون 0.422 (24/42)', ('AMLN', 'T'): 'ويلسون 0.488 (33/53)', ('AMLN', 'T_TAD'): 'ويلسون 0.458 (18/28)',
    ('AMLN', 'J_LAWN'): 'ويلسون 0.742، الحوض 30', ('AMLN', 'J_MUTAWAA'): 'ويلسون 0.656',
    ('WAZN', 'TRANSITIVITY_WASIT_V1:مشترك'): '«مشترك» محجوب (0.75)', ('WAZN', 'TRANSITIVITY_WASIT_V2'): 'ويلسون 0.763 (OCR)',
    ('WAZN', 'TRANSITIVITY_WASIT_V3'): 'ويلسون 0.746 (OCR)', ('WAZN', 'MUTAWAA:BASE_UNRESOLVED'): 'أصلٌ غير محسوم',
    ('HFN', 'v37_side_files'): 'غير معتمدة؛ لا تُستهلك في هذه الدفعة',
}
# يُرفق بالمرشّح المطابقُ التامّ وحده؛ وفرق السكون وحده يبقى مستبعداً بسببه (حكم المالك، 6 نوفمبر)
ATTACH = ('EXACT_VOCALIZED_MATCH',)
EXCLUDE_REASON = {'SUKUN_ONLY_DIFFERENCE': 'فرقٌ في السكون وحده: مستبعدٌ بحكم المالك (6 نوفمبر)',
                  'VOCALIZATION_MISMATCH': 'حروفٌ واحدة وتشكيلٌ مختلف (والشدّة منه)', 'LETTERS_DIFFER': 'حروفٌ مختلفة (ومنها كرسيّ الهمزة)'}
FEATURE = {('AMLN', 'R1'): 'ahdath_effect', ('AMLN', 'R1W'): 'ahdath_effect', ('AMLN', 'T_JAL'): 'ahdath_effect',
           ('AMLN', 'J_SAJIYYA'): 'fail_jiha', ('AMLN', 'J_DAA'): 'fail_jiha', ('WAZN', 'T_JAL'): 'taadiya',
           ('WAZN', 'TRANSITIVITY_WASIT_V1'): 'transitivity_wasit', ('HFN37', 'MASDAR_WASIT_V37'): 'hfn_v37_masdar',
           ('HFN37', 'TRANSITIVITY_WASIT_V37'): 'hfn_v37_transitivity'}
RANK_MEASURED = ('EXTERNAL_MEASURED', 'دليل خارجي مقيس')
RANK_OCR = ('OCR_UNVERIFIED_WITNESS', 'شاهد OCR غير محقّق')


def evidence_records(fr, feats, rm, prov):
    """سمات المنبع في نظام الأدلّة (مراجعة 036): معرّف UPSTREAM:{الوقوع}:{feature}:{route}:{commit}، ورتبة؛ ولا يُستوفى بها التزام،
    ولا يُغلق بها وجه، ولا تُعدّ CONDITIONS_MET"""
    out = []
    for x in feats:
        com = (x['repository_commit_or_dataset_version'] or '')[:7]
        out.append(dict(id=f"UPSTREAM:{fr['unit']}:{x['feature']}:{x['route_id']}:{com}", unit=fr['unit'], feature=x['feature'],
                        route=x['route_id'], provider=x['provider'], commit=com, rank=RANK_MEASURED[1], rank_code=RANK_MEASURED[0],
                        value=x.get('value') or x.get('effect') or x.get('pair') or x.get('jiha') or x.get('masdar'),
                        measurement_id=x['measurement_id'], wilson_low=x['wilson_low'], match_status=x['match_status'],
                        discharges_obligation=False, closes_face=False, conditions_met=False))
    mq = (rm or {}).get('maqayis') or {}
    if mq.get('status') == 'FOUND':
        com = (prov.get('maq', {}).get('commit') or '')[:7]
        out.append(dict(id=f"UPSTREAM:{fr['unit']}:root_meaning:MAQAYIS_FALLBACK:{com}", unit=fr['unit'], feature='root_meaning',
                        route='MAQAYIS_FALLBACK', provider='MAQAYIS', commit=com, rank=RANK_OCR[1], rank_code=RANK_OCR[0],
                        value=dict(retrieval_key=mq['retrieval_key'], records=[dict(id=r['id'], display=r['display'], axes=r['semantic_axes'])
                                                                              for r in mq['records']]),
                        note='معنى الجذر ليس المعنى المختار في السياق؛ والنصّ OCR غير محقّق', discharges_obligation=False,
                        closes_face=False, conditions_met=False))
    return out


def frames(items):
    """→ لكل آية: أطر الفعل بمرشّحها الصرفي وجذرها ووزنها، ولمّاتها المشكولة من HFN v36 (index[(R، P)])"""
    from sarf.catalog import Catalog
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo, linguistic_layer
    from sarf.features import unit_features
    from sarf import relations as RL, quran_source
    from sarf.root import hfn
    from sarf.protected import protected
    CAT = Catalog([os.path.join(ROOT, 'operators_catalog.jsonl'), os.path.join(ROOT, 'operators_catalog_split_vocalized.csv')])
    its, per = [], []
    for s, v, text in items:
        a = analyze(CAT, text, quran_source.uthmani_mode())
        S_, U = sentence_geo(a, f'Q{s}:{v}', Trace())
        its.append((s, v, a, U, S_))
        per.append((s, v, a, U, unit_features(a, U)))
    C, Rl = [], []
    linguistic_layer(its, Trace(), 'up', cond_out=C, rel_out=Rl)
    H = hfn()
    out = []
    for s, v, a, U, F in per:
        o = RL.verse_relations(a, U, F, f'{s}:{v}', legacy_cond=C, legacy_rel=Rl)
        for r in o['records']:
            if r['type'] != 'VERB_FRAME':
                continue
            f_ = r.get('frame') or {}
            c_ = f_.get('candidate') or {}
            R_, P_ = f_.get('root'), f_.get('pattern')
            ev = [dict(event_id=e['event_id'], verb=e['verb'], form=e.get('form'), transitivity=e.get('transitivity'))
                  for e in H.index.get((R_, P_), [])] if R_ and P_ else []
            pr = protected(r['texts'].get('verb'))
            out.append(dict(verse=f'{s}:{v}', relation_id=r['relation_id'], unit=r['heads'].get('verb'), text=r['texts'].get('verb'),
                            protected=(dict(cls=pr['cls'], identity=pr['identity'], ambiguous=pr.get('ambiguous', False)) if pr else None),
                            morph_candidate_id=c_.get('id'), root=R_, pattern=P_, voice=c_.get('voice'), tense=c_.get('tense'),
                            hfn_events=ev))
    return out


def lemma_status(fr):
    ev = fr['hfn_events']
    if fr.get('protected'):
        # البوابة الدستورية قبل كل استدعاء: لا تُسأل الموارد عن وحدةٍ محمية، ولا عن بديلها ما دامت الفئة مؤجَّلة
        return 'PROTECTED_NOT_QUERIED', ('وحدةٌ محمية دستورياً (' + fr['protected']['cls'] + '، ' + fr['protected']['identity'] + ')' +
                                         ('؛ والفئة مؤجَّلة فلا يُسأل عن البديل' if fr['protected']['ambiguous'] else ''))
    if not fr['root'] or not fr['pattern']:
        return 'LEMMA_NOT_ESTABLISHED', 'لا جذر ولا وزن مقبولان للمرشّح'
    if not ev:
        return 'LEMMA_NOT_ESTABLISHED', 'لا حدث في HFN v36 للجذر والوزن'
    if len({e['verb'] for e in ev}) > 1:
        return 'LEMMA_NOT_ESTABLISHED', 'أكثر من لمّة مشكولة في HFN للجذر والوزن: ' + '، '.join(sorted({e['verb'] for e in ev}))
    return 'LEMMA_ESTABLISHED', 'لمّةٌ واحدة في HFN v36 للجذر والوزن'


def feature_rows(fr, lem, W, res):
    """السمات المرشّحة من نتيجة العامل لِلمّةٍ واحدة، بحقولها المطلوبة؛ والمستبعد بسببه"""
    P = res['provenance']
    rs = res['resources']
    keep, drop = [], []

    def base(provider, route, row_id, file_key, form, src_ref, match, scope, extra):
        meta = ROUTES.get((provider, route))
        return dict(provider=provider, repository_commit_or_dataset_version=P[{'AMLN': 'amln', 'WAZN': 'wazn', 'HFN37': 'hfn37'}[provider]]['commit'],
                    file_hash=(rs.get(file_key) or {}).get('file_hash'), file=file_key, row_or_entry_id=row_id, route_id=route,
                    vocalized_lemma=lem, root=fr['root'], pattern_or_form=form, source_reference=src_ref,
                    measurement_id=(meta or {}).get('measurement_id'), wilson_low=(meta or {}).get('wilson_low'),
                    route_status=(meta or {}).get('status', 'UNREGISTERED'), owner_status='CANDIDATE_PENDING_OWNER',
                    match_status=match, consumer_scope=scope, feature=FEATURE.get((provider, route)) or extra.pop('feature', None),
                    exclusion_reason=None if match in ATTACH else EXCLUDE_REASON.get(match, match), **extra)

    if isinstance(W['ahdath'], list):
        for x in W['ahdath']:
            row = base('AMLN', x['route'], x['event_id'], {'R1': 'AMLN:ahdath/rules_R1.tsv', 'R1W': 'AMLN:ahdath/mutawaa_R1W_pool.tsv',
                                                           'T_JAL': 'AMLN:ahdath/taadiya_T_JAL.tsv'}[x['route']], None, x['src'], x['match'],
                       'event_effect (الحدث وأثره على الصفة): candidate, not a syntactic transitivity decision',
                       dict(effect=dict(fail=x['fail'], maful=x['maful'], mutawi=x['mutawi'], athar=x['athar'], sifa=x['sifa'],
                                        label=x['label_ar']), upstream_event_id=x['event_id'],
                            event_id_agrees=x['event_id'] in {e['event_id'] for e in fr['hfn_events']}, upstream_verb=x['verb']))
            (keep if x['match'] in ATTACH else drop).append(row)
    if isinstance(W['jiha'], list):
        for x in W['jiha']:
            row = base('AMLN', x['route'], x['event_id'], 'AMLN:ahdath/jiha_pool.tsv', None, x['src'], x['match'],
                       'subject_semantic_side (جهة الفاعل الدلالية): لا يغيّر دوره النحوي ولا يجعله نائب فاعل',
                       dict(jiha=x['jiha'], musabbib_verb=dict(value=x['musabbib_verb'] or None, route=x['musabbib_route'] or None,
                                                               note='علاقةٌ معجمية مرشّحة، لا إثبات مسبِّبٍ محذوف في الجملة'),
                            sifa=x['sifa'], upstream_event_id=x['event_id'], upstream_verb=x['verb'],
                            event_id_agrees=x['event_id'] in {e['event_id'] for e in fr['hfn_events']}))
            (keep if x['match'] in ATTACH else drop).append(row)
    for key, side in (('mutawaa', 'base'), ('mutawaa_base', 'mutawaa')):
        if isinstance(W[key], list):
            for x in W[key]:
                unresolved = not x['base']
                row = base('WAZN', x['route'], f"{x['root']}:{x['base']}→{x['mutawaa']}", 'WAZN:data/mutawaa_v3.tsv',
                           x['base_form'] if side == 'base' else x['mutawaa_form'], x['evidence'] or x['lexicons'], x['match'],
                           'mutawaa (المطاوعة): ' + ('اللمّة أصلٌ لها مطاوع' if side == 'base' else 'اللمّة مطاوِعٌ لأصل'),
                           dict(pair=dict(base=x['base'], base_form=x['base_form'], mutawaa=x['mutawaa'], mutawaa_form=x['mutawaa_form'],
                                          athar=x['athar']), lemma_side=side, feature='mutawaa' if side == 'base' else 'mutawaa_base', upstream_verb=x['base'] if side == 'base' else x['mutawaa']))
                if unresolved:
                    row['route_status'] = 'BLOCKED: BASE_UNRESOLVED'
                    drop.append(row)
                elif any(r_ not in ('R1_QABILIYYAT', 'LEX_FORMULA', 'R1W_WASIT') for r_ in x['route'].split('+')):
                    row['route_status'] = 'UNREGISTERED_ROUTE'
                    drop.append(row)
                else:
                    if '+' in x['route']:
                        row['route_status'] = 'ACCEPTED_ROUTE'
                        row['measurement_id'] = ' + '.join(ROUTES[('WAZN', r_)]['measurement_id'] for r_ in x['route'].split('+'))
                    (keep if x['match'] in ATTACH else drop).append(row)
    if isinstance(W['taadiya_T_JAL'], list):
        for x in W['taadiya_T_JAL']:
            row = base('WAZN', 'T_JAL', f"{x['lazim']}→{x['mutaaddi']}", 'WAZN:taadiya_engine.AHDATH', x['form'], x['measure'], x['match'],
                       'taadiya (التعدية بالهمزة): اللمّة لازمٌ له متعدٍّ مسموع — نتيجة ظلية لا تدخل قرار التعدية',
                       dict(pair=dict(lazim=x['lazim'], mutaaddi=x['mutaaddi'], sifa=x['sifa'], maful=x['maful']), upstream_verb=x['lazim']))
            (keep if x['match'] in ATTACH else drop).append(row)
    if isinstance(W['transitivity_wasit'], list):
        for x in W['transitivity_wasit']:
            tv = x['transitivity_wasit']
            row = base('WAZN', 'TRANSITIVITY_WASIT_V1', x['event_id'], 'WAZN:data/transitivity_wasit.tsv', x['form'],
                       'المعجم الوسيط: ' + (x['evidence'] or '—'), x['match'],
                       'transitivity_shadow (تعدّي المجرّد من الوسيط): نتيجة ظلية تُقارن بالحكم القائم ولا تدخله',
                       dict(value=tv, hfn_transitivity=x['hfn_transitivity'], harf=x['harf'] or None, upstream_event_id=x['event_id'],
                            upstream_verb=x['verb'],
                            event_id_agrees=x['event_id'] in {e['event_id'] for e in fr['hfn_events']}))
            if tv == 'مشترك':
                row['route_status'] = 'BLOCKED: ' + BLOCKED[('WAZN', 'TRANSITIVITY_WASIT_V1:مشترك')]
                drop.append(row)
            elif tv not in ('لازم', 'متعدي'):
                row['route_status'] = 'NO_VALUE: ' + tv
                drop.append(row)
            else:
                (keep if x['match'] in ATTACH else drop).append(row)
    if isinstance(W.get('hfn_v37'), list):
        for x in W['hfn_v37']:
            for fld, route in (('masdar_wasit_v37', 'MASDAR_WASIT_V37'), ('transitivity_wasit_v37', 'TRANSITIVITY_WASIT_V37')):
                if not x.get(fld):
                    continue
                row = base('HFN37', route, x['event_id'], 'HFN37:release_v37/events.csv', x['form'], 'HFN release_v37 (HFN-D059): ' + fld,
                           x['match'], 'hfn_v37 (إضافة v37 سمةً جديدة): لا تحلّ محلّ قيمة v36 ولا تدخل قرارها',
                           dict(value=x[fld], upstream_event_id=x['event_id'], upstream_verb=x['verb'],
                                event_id_agrees=x['event_id'] in {e['event_id'] for e in fr['hfn_events']}))
                (keep if x['match'] in ATTACH else drop).append(row)
    return keep, drop


def load_evidence(path):
    """→ {الوحدة: [سجلات أدلّة UPSTREAM]} من مخرج هذه الأداة"""
    out = collections.defaultdict(list)
    for l in gzip.open(path, 'rt', encoding='utf-8'):
        r = json.loads(l)
        if r.get('unit'):
            out[r['unit']] += r.get('evidence') or []
    return dict(out)


def main():
    import client
    out_path, sum_path = sys.argv[1], sys.argv[2]
    from sarf import quran_source
    V = quran_source.rows()
    if '--verses' in sys.argv:
        want = set(sys.argv[sys.argv.index('--verses') + 1].split(','))
        V = [x for x in V if f'{x[0]}:{x[1]}' in want]
    groups = [list(g) for _, g in itertools.groupby(V, key=lambda x: x[0])]
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2
    with mp.get_context('fork').Pool(jobs) as P:
        FR = [x for g in P.map(frames, groups, chunksize=1) for x in g]
    lemmas = sorted({e['verb'] for fr in FR if not fr.get('protected') for e in fr['hfn_events']})
    roots = sorted({fr['root'] for fr in FR if fr['root'] and not fr.get('protected')})
    res = client.call([dict(lemma=l) for l in lemmas], roots)
    S = collections.Counter()
    ex = collections.defaultdict(list)
    with gzip.open(out_path, 'wt', encoding='utf-8') as f:
        for fr in FR:
            st, why = lemma_status(fr)
            S['occurrences'] += 1
            S['lemma:' + st] += 1
            feats, drops = [], []
            # كل لمّةٍ بديلة تُفحص وحدها؛ ولا يُرفق بالمرشّح إلا ما كانت لمّته ثابتة
            for lem in ([] if st == 'PROTECTED_NOT_QUERIED' else sorted({e['verb'] for e in fr['hfn_events']})):
                k, d = feature_rows(fr, lem, res['lemma'][lem], res)
                if st != 'LEMMA_ESTABLISHED':
                    for x in k:
                        x['attach_status'] = 'NOT_ATTACHED: LEMMA_NOT_ESTABLISHED'
                    d = d + k
                    k = []
                feats += k
                drops += d
            for x in feats:
                S[f"attached:{x['provider']}:{x['route_id']}:{x['match_status']}"] += 1
            for x in drops:
                why_ = x.get('attach_status', '').split(': ')[-1] if x.get('attach_status') else x['route_status'].split(':')[0]
                S[f"excluded:{x['provider']}:{x['route_id']}:{x['match_status']}:{why_}"] += 1
            rm = res['root'].get(fr['root']) if fr['root'] and st != 'PROTECTED_NOT_QUERIED' else None
            if rm:
                S['root_meaning:' + (rm['root_meaning'].get('error') or 'IN_BANK').split(':')[0]] += 1
                S['maqayis:' + rm['maqayis']['status']] += 1
            ev_ = evidence_records(fr, feats, rm, res['provenance'])
            for e in ev_:
                S[f"evidence:{e['rank_code']}:{e['feature']}"] += 1
            row = dict(fr, lemma_status=st, lemma_reason=why, evidence=ev_,
                       upstream_candidates=dict(features=feats, excluded=drops, root_meaning=rm))
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
            if feats and len(ex['attached']) < 12:
                ex['attached'].append(dict(verse=fr['verse'], text=fr['text'], lemma=feats[0]['vocalized_lemma'], route=feats[0]['route_id'],
                                           provider=feats[0]['provider'], match=feats[0]['match_status']))
            for x in drops:
                if x['match_status'] in ('VOCALIZATION_MISMATCH', 'SUKUN_ONLY_DIFFERENCE') and len(ex['mismatch']) < 12:
                    ex['mismatch'].append(dict(verse=fr['verse'], lemma=x['vocalized_lemma'], upstream=x.get('upstream_verb'), route=x['route_id'],
                                               match=x['match_status']))
    summary = dict(counts=dict(sorted(S.items())), examples=ex, resources=res['resources'], provenance=res['provenance'],
                   isolation=res['isolation'], routes={f'{a}:{b}': v for (a, b), v in ROUTES.items()},
                   blocked={f'{a}:{b}': v for (a, b), v in BLOCKED.items()}, n_lemmas=len(lemmas), n_roots=len(roots))
    json.dump(summary, open(sum_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(dict(occurrences=S['occurrences'], lemmas=len(lemmas), roots=len(roots),
                          writes=res['isolation'].get('resource_writes')), ensure_ascii=False))


if __name__ == '__main__':
    main()
