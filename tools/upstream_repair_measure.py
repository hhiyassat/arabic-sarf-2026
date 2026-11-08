"""tools/upstream_repair_measure.py — قياس SARF_UPSTREAM_CONSUMER_REPAIR_02: المستهلك قبل الإصلاح وبعده، صفاً صفاً.

    python3 tools/upstream_repair_measure.py <cand_old.jsonl.gz> <cand_new.jsonl.gz> <HFN_v47_dir> <WAZN_dir> <OUT_PREFIX> [cert_new.json]

1. هوية المعجم قبل وبعد: صفوف CANDIDATE_MATCH التي يختلف جذر مصدرها عن جذر الوجه، لكل مصدر (جذر المصدر من صفّه: HFN بمعرّف الحدث، والصفات
   وتعدّي الوسيط بمعرّف الحدث في جدولهما) — الطريقة نفسها قبل الإصلاح وبعده.
2. معرّفات الأدلّة: المكرّر، والمكرّر بمحتويين، والمعرّف الذي لا يطابق بصمة محتواه؛ والمراجع اليتيمة والملتبسة في الشهادات.
3. انتقالات الصفوف: لكل صفٍّ (الوقوع، اللمّة، المصدر، معرّف الصفّ، المسلك) حالته قبل وبعد، وسبب التغيّر من حقل الهوية.
4. العدّادات بمقاماتها وتعريفها الحسابي.
"""
import collections, csv, gzip, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upstream_candidates import verify_evidence_registry, EVIDENCE_ID_ALGO

COUNTER_DEFS = {
    'feature_rows_candidate_match': 'عدد صفوف السمات بحالة CANDIDATE_MATCH (صفٌّ لكل وقوع × لمّة × مصدر × صفّ مصدر)',
    'occurrence_records_with_match': 'عدد سجلات الوقوع (الآية، relation_id) التي فيها صفٌّ واحدٌ مطابق على الأقل',
    'distinct_analysis_ids_with_match': 'عدد قيم analysis_id المتميزة في الصفوف المطابقة (هوية تحليلٍ معجمية، تتكرّر عبر الوقوعات)',
    'face_occurrences_with_match': 'عدد الأزواج المتميزة (الآية، relation_id، analysis_id) في الصفوف المطابقة: وقوعات الأوجه',
    'words_with_match': 'عدد الكلمات المتميزة (الآية، رقم الكلمة) في الصفوف المطابقة',
    'evidence_records': 'عدد سجلات الأدلّة المكتوبة (بالتكرار عبر الوقوعات)',
    'distinct_evidence_ids': 'عدد معرّفات الأدلّة المتميزة',
}


def src_root_fn(H, W):
    ev = {e['event_id']: e for e in csv.DictReader(open(os.path.join(H, 'events.csv'), encoding='utf-8'))}
    sif = {}
    for r in csv.DictReader(open(os.path.join(W, 'data', 'sifat_v2.tsv'), encoding='utf-8'), delimiter='\t'):
        sif.setdefault(r['event_id'], r['root'])
    tw = {r['event_id']: r['root'] for r in csv.DictReader(open(os.path.join(W, 'data', 'transitivity_wasit_v5.tsv'), encoding='utf-8'), delimiter='\t')}

    def f(x):
        k = x['source_key']
        if k == 'hfn47':
            return (ev.get((x.get('value') or {}).get('event_id')) or {}).get('root_K')
        if k == 'sifat_v2':
            return sif.get(x.get('upstream_event_id'))
        if k == 'transitivity_wasit_v5':
            return tw.get(x.get('upstream_event_id'))
        return None
    return f


def rkey(r, x):
    return (r['verse'], r['relation_id'], x.get('vocalized_lemma'), x['source_key'], str(x.get('row_id')), x.get('route_id'))


def counts(R):
    m = [(r, x) for r in R for x in r['upstream_candidates']['rows'] if x['state'] == 'CANDIDATE_MATCH']
    ev = [e for r in R for e in r['evidence']]
    return dict(feature_rows_candidate_match=len(m), occurrence_records_with_match=len({(r['verse'], r['relation_id']) for r, _ in m}),
                distinct_analysis_ids_with_match=len({x['face'].get('analysis_id') for _, x in m}),
                face_occurrences_with_match=len({(r['verse'], r['relation_id'], x['face'].get('analysis_id')) for r, x in m}),
                words_with_match=len({(r['verse'], r['word_index']) for r, _ in m}),
                evidence_records=len(ev), distinct_evidence_ids=len({e.get('evidence_id') or e['id'] for e in ev}),
                denominators=dict(occurrence_records=len(R), feature_rows=sum(len(r['upstream_candidates']['rows']) for r in R),
                                  occurrence_records_queried=sum(1 for r in R if r['lemma_status'] != 'PROTECTED_NOT_QUERIED')))


def id_report(R, new):
    ev = [e for r in R for e in r['evidence']]
    by = collections.defaultdict(set)
    n = collections.Counter()
    for e in ev:
        i = e.get('evidence_id') or e['id']
        n[i] += 1
        c = {k: v for k, v in e.items() if k not in ('id',)}
        by[i].add(json.dumps(c, ensure_ascii=False, sort_keys=True))
    dup = [i for i, k in n.items() if k > 1]
    out = dict(evidence_records=len(ev), distinct_ids=len(n), ids_repeated=len(dup), ids_with_different_content=sum(1 for i in dup if len(by[i]) > 1))
    if new:
        out['registry_errors'] = verify_evidence_registry(ev)
        out['algorithm'] = EVIDENCE_ID_ALGO
    return out, by


def main():
    A, B, H, W, OUT = sys.argv[1:6]
    CERT = json.load(open(sys.argv[6], encoding='utf-8')) if len(sys.argv) > 6 else None
    RA = [json.loads(l) for l in gzip.open(A, 'rt', encoding='utf-8')]
    RB = [json.loads(l) for l in gzip.open(B, 'rt', encoding='utf-8')]
    sr = src_root_fn(H, W)
    # ١ هوية المعجم قبل وبعد
    ident = {}
    for name, R in (('before', RA), ('after', RB)):
        c = collections.Counter()
        for r in R:
            for x in r['upstream_candidates']['rows']:
                if x['state'] == 'CANDIDATE_MATCH':
                    s_ = sr(x)
                    if s_ is not None and s_ != x['face']['root']:
                        c[x['source_key']] += 1
        ident[name] = dict(c)
    ident['after_match_with_identity_not_ok'] = sum(1 for r in RB for x in r['upstream_candidates']['rows']
                                                    if x['state'] == 'CANDIDATE_MATCH' and x.get('identity_status') != 'IDENTITY_OK')
    # ٢ المعرّفات
    ida, bya = id_report(RA, False)
    idb, _ = id_report(RB, True)
    # معالجة كل معرّفٍ قديمٍ متصادم: كم دليلاً جديداً متميزاً يقابل محتوياته (بالوقوع والمصدر والمسلك)
    newmap = collections.defaultdict(set)
    for r in RB:
        for e in r['evidence']:
            newmap[(e['unit'], e['source_key'], e['route_id'])].add(e['evidence_id'])
    coll_rows = []
    for i, cs in bya.items():
        if len(cs) > 1:
            parts = i.split(':')
            unit = ':'.join(parts[1:3]) if len(parts) > 4 else None
            k = (unit, parts[-3] if len(parts) >= 5 else None, parts[-2] if len(parts) >= 5 else None)
            coll_rows.append(dict(old_id=i, old_distinct_contents=len(cs), new_distinct_ids_for_same_unit_source_route=len(newmap.get(k, set())),
                                  treatment='كل محتوى بمعرّف بصمته؛ لا اختيار لأولٍ ولا حذف للمختلف'))
    ids_cert = set()
    if CERT is not None:
        ids_cert = set(CERT.get('external_evidence_ids_seen') or [])
    reg = {e['evidence_id'] for r in RB for e in r['evidence']}
    idb['certificate_refs'] = dict(seen=len(ids_cert), orphan=len(ids_cert - reg) if ids_cert else None, note='من فحص الشهادات على المصحف كله' if ids_cert else 'لم يُمرَّر')
    # ٣ انتقالات الصفوف
    old = {rkey(r, x): x for r in RA for x in r['upstream_candidates']['rows']}
    new = {rkey(r, x): x for r in RB for x in r['upstream_candidates']['rows']}
    T = collections.Counter()
    with gzip.open(OUT + '_row_transitions.jsonl.gz', 'wt', encoding='utf-8') as f:
        for k in sorted(set(old) | set(new)):
            a, b = old.get(k), new.get(k)
            sa, sb = (a or {}).get('state', '<ABSENT>'), (b or {}).get('state', '<ABSENT>')
            why = 'UNCHANGED' if sa == sb else (
                f"IDENTITY: {(b.get('identity') or {}).get('reason')}" if b and b.get('identity_status') not in (None, 'IDENTITY_OK') and sb == b.get('identity_status')
                else 'WITHDRAWN_VIA_EVENT_ID' if sb == 'WITHDRAWN_RECORD' else f'OTHER: {sa}→{sb}')
            T[(k[3], sa, sb, why.split(' (')[0][:60])] += 1
            if sa != sb:
                f.write(json.dumps(dict(verse=k[0], relation_id=k[1], lemma=k[2], source=k[3], row_id=k[4], route=k[5], before=sa, after=sb, reason=why,
                                        identity=(b or {}).get('identity')), ensure_ascii=False) + '\n')
    trans = [dict(source=a, before=b, after=c, reason=d, rows=n) for (a, b, c, d), n in sorted(T.items())]
    res = dict(identity_root_mismatch_rows=ident, evidence_ids=dict(before=ida, after=idb), collisions_treated=len(coll_rows),
               counts=dict(before=counts(RA), after=counts(RB)), counter_definitions=COUNTER_DEFS, row_transitions=trans,
               row_transitions_changed=sum(t['rows'] for t in trans if t['before'] != t['after']),
               unclassified_transitions=sum(t['rows'] for t in trans if t['before'] != t['after'] and t['reason'].startswith('OTHER')))
    json.dump(res, open(OUT + '.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(OUT + '_evidence_collisions.tsv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['old_id', 'old_distinct_contents', 'new_distinct_ids_for_same_unit_source_route', 'treatment'])
        for x in coll_rows:
            w.writerow([x[k] for k in ('old_id', 'old_distinct_contents', 'new_distinct_ids_for_same_unit_source_route', 'treatment')])
    print(json.dumps(dict(identity=ident, ids_before=ida, ids_after={k: v for k, v in idb.items() if k != 'registry_errors'},
                          registry_errors=len(idb['registry_errors']), changed=res['row_transitions_changed'], unclassified=res['unclassified_transitions'],
                          counts=res['counts']), ensure_ascii=False))


if __name__ == '__main__':
    main()
