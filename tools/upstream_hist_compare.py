"""tools/upstream_hist_compare.py — مقارنةٌ تاريخية: المستهلك السابق على مصادره المسجّلة (6 نوفمبر: HFN v36 + v37 سمةً، mutawaa_v3،
تعدّي الوسيط v1، AMLN 1cadaa3) مقابل الاستهلاك المرشّح الحالي (HFN v47، mutawaa_v7، الوسيط v5، AMLN 8da48f7)، لكل وقوعٍ ولمّةٍ ومورد.

    python3 tools/upstream_hist_compare.py <hist.jsonl.gz> <cand.jsonl.gz> <OUT_PREFIX>

المقارنة بقيمةٍ قانونية لكل عائلة (لا بأسماء المسالك ولا بشكل الحقول)، وما تغيّر يُعلَّل من الحقلين نفسيهما: رسم «ٱ»، أو تصحيح تشكيلٍ
(الحروف واحدة)، أو صفٌّ آخر؛ وفي تعدّي الوسيط من basis_v5 وtransitivity_v1. وتتغيّر هنا الشيفرة والبيانات معاً، فما لا يُعلَّل من الصفّ
يُعلَّم CONSUMER_OR_DATA ولا يُنسب إلى إصدار.
"""
import collections, gzip, json, re, sys

MARKS = re.compile('[ً-ْٰـ]')
J = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True)


def canon_old(x):
    p, r = x['provider'], x['route_id']
    lem = x['vocalized_lemma']
    if p == 'AMLN' and r in ('R1', 'R1W', 'T_JAL'):
        e = x.get('effect') or {}
        return 'ahdath', (lem, r, J({k: e.get(k) or None for k in ('fail', 'maful', 'mutawi', 'athar', 'sifa')}))
    if p == 'AMLN' and r in ('J_SAJIYYA', 'J_DAA'):
        return 'jiha', (lem, r, J(dict(jiha=x.get('jiha'), sifa=x.get('sifa') or None)))
    if p == 'WAZN' and x.get('feature') in ('mutawaa', 'mutawaa_base'):
        q = x.get('pair') or {}
        return x['feature'], (lem, J({k: q.get(k) or None for k in ('base', 'base_form', 'mutawaa', 'mutawaa_form', 'athar')}))
    if p == 'WAZN' and r == 'T_JAL':
        q = x.get('pair') or {}
        return 'taadiya_T_JAL', (lem, J({k: q.get(k) or None for k in ('lazim', 'mutaaddi', 'sifa', 'maful')}))
    if p == 'WAZN' and r == 'TRANSITIVITY_WASIT_V1':
        return 'transitivity_wasit', (lem, x.get('upstream_event_id'), J(dict(value=x.get('value'), harf=x.get('harf') or None)))
    if p == 'HFN37' and r == 'MASDAR_WASIT_V37':
        return 'hfn_masdar_wasit_v37', (lem, x.get('upstream_event_id'), J(x.get('value')))
    if p == 'HFN37' and r == 'TRANSITIVITY_WASIT_V37':
        return 'hfn_transitivity_wasit_v37', (lem, x.get('upstream_event_id'), J(x.get('value')))
    return None, None


def canon_new(x):
    k, lem, v = x['source_key'], x['vocalized_lemma'], x.get('value')
    if k == 'ahdath':
        return [('ahdath', (lem, x['route_id'], J({f: (v or {}).get(f) or None for f in ('fail', 'maful', 'mutawi', 'athar', 'sifa')})))]
    if k == 'jiha':
        return [('jiha', (lem, x['route_id'], J(dict(jiha=(v or {}).get('jiha'), sifa=(v or {}).get('sifa') or None))))]
    if k in ('mutawaa', 'mutawaa_base'):
        return [(k, (lem, J({f: (v or {}).get(f) or None for f in ('base', 'base_form', 'mutawaa', 'mutawaa_form', 'athar')})))]
    if k == 'taadiya_T_JAL':
        return [(k, (lem, J({f: (v or {}).get(f) or None for f in ('lazim', 'mutaaddi', 'sifa', 'maful')})))]
    if k == 'transitivity_wasit_v5':
        return [('transitivity_wasit', (lem, x.get('upstream_event_id'), J(dict(value=v, harf=x.get('harf') or None))))]
    if k == 'hfn47':
        out = [('hfn_event_v47', (lem, v['event_id'], J(dict(transitivity=v.get('transitivity'), masdar=v.get('masdar')))))]
        if v.get('masdar_wasit_v37'):
            out.append(('hfn_masdar_wasit_v37', (lem, v['event_id'], J(v['masdar_wasit_v37']))))
        if v.get('transitivity_wasit_v37'):
            out.append(('hfn_transitivity_wasit_v37', (lem, v['event_id'], J(v['transitivity_wasit_v37']))))
        return out
    if k == 'sifat_v2':
        return [('sifat_v2', (lem, x.get('upstream_event_id'), J(v)))]
    return []


def why_changed(a, b, fam, rows):
    """→ أسباب الفرق من الحقلين: «ٱ»، تصحيح تشكيل، صفٌّ آخر؛ وفي الوسيط basis_v5"""
    sa, sb = ' '.join(map(str, sorted(a))), ' '.join(map(str, sorted(b)))
    rs = []
    if sa.replace('ٱ', 'ا') == sb.replace('ٱ', 'ا'):
        rs.append('WASL_SPELLING (رسم «ٱ»)')
    elif MARKS.sub('', sa).replace('ٱ', 'ا') == MARKS.sub('', sb).replace('ٱ', 'ا'):
        rs.append('VOCALIZATION_CORRECTED (الحروف واحدة والتشكيل مختلف)')
    if fam == 'transitivity_wasit':
        for x in rows:
            if x['source_key'] == 'transitivity_wasit_v5' and x['state'] in ('CANDIDATE_MATCH', 'ROUTE_BLOCKED'):
                if x['state'] == 'ROUTE_BLOCKED':
                    rs.append('BLOCKED_IN_V5: ' + ('المزيد' if 'المزيد' in (x.get('block_reason') or '') else '«مشترك»'))
                elif x['changed_from_v1']:
                    rs.append(f"STATISTICALLY_CORRECTED_TRANSITIVITY (basis_v5={x['basis_v5']}، v1={x['transitivity_v1']})")
    return rs or ['CONSUMER_OR_DATA (لا يُفصل)']


def main():
    H, C, OUT = sys.argv[1:4]
    old, new = {}, {}
    for l in gzip.open(H, 'rt', encoding='utf-8'):
        r = json.loads(l)
        att = collections.defaultdict(set)
        for x in r['upstream_candidates']['features']:
            f, t = canon_old(x)
            if f:
                att[f].add(t)
        mq = (r['upstream_candidates'].get('root_meaning') or {}).get('maqayis') or {}
        old[(r['verse'], r['relation_id'])] = dict(status=r['lemma_status'], att=att, maq=mq.get('status'),
                                                   maq_ids={str(x['id']) for x in mq.get('records') or []})
    for l in gzip.open(C, 'rt', encoding='utf-8'):
        r = json.loads(l)
        att = collections.defaultdict(set)
        rows = r['upstream_candidates']['rows']
        for x in rows:
            if x['state'] == 'CANDIDATE_MATCH':
                for f, t in canon_new(x):
                    att[f].add(t)
        mq = ((r['upstream_candidates'].get('root_meaning') or {}).get('maqayis_fallback') or {})
        new[(r['verse'], r['relation_id'])] = dict(status=r['lemma_status'], att=att, rows=rows, maq=mq.get('status'),
                                                   maq_ids={str(x.get('entry_id')) for x in mq.get('records') or []})
    S = collections.Counter()
    out = []
    NEW_ONLY = {'hfn_event_v47', 'sifat_v2'}
    for k in sorted(set(old) | set(new)):
        o, n = old.get(k), new.get(k)
        if o is None or n is None:
            S['occurrence_only_in_' + ('new' if o is None else 'old')] += 1
            continue
        S['occurrences'] += 1
        S[f"gate:{o['status']}→{n['status']}"] += 1
        for fam in sorted(set(o['att']) | set(n['att'])):
            a, b = o['att'].get(fam, set()), n['att'].get(fam, set())
            if fam in NEW_ONLY:
                S[f'{fam}:NEW_RESOURCE_ATTACHED'] += bool(b)
                continue
            if a == b:
                S[f'{fam}:SAME'] += 1
                continue
            kind = 'ADDED' if not a else 'REMOVED' if not b else 'CHANGED'
            why = why_changed(a, b, fam, n['rows'])
            if kind == 'REMOVED':
                lost = [x for x in n['rows'] if x['state'] != 'CANDIDATE_MATCH' and
                        x['source_key'] in (fam, {'transitivity_wasit': 'transitivity_wasit_v5'}.get(fam), 'hfn47')]
                why = sorted({f"{x['state']}" + (f":{x.get('match')}" if x.get('match') else '') for x in lost}) or why
                if n['status'] != o['status']:
                    why = [f"GATE {o['status']}→{n['status']}"] + why
            S[f'{fam}:{kind}'] += 1
            for w in why:
                S[f'{fam}:{kind}:{w[:70]}'] += 1
            out.append(dict(verse=k[0], relation_id=k[1], family=fam, kind=kind, old=sorted(map(list, a)), new=sorted(map(list, b)), reasons=why))
        if o['maq'] or n['maq']:
            S[f"root_maqayis:{o['maq']}→{n['maq']}" + (':same_entries' if o['maq_ids'] == n['maq_ids'] else ':entries_differ')] += 1
    with gzip.open(OUT + '.jsonl.gz', 'wt', encoding='utf-8') as f:
        for x in out:
            f.write(json.dumps(x, ensure_ascii=False) + '\n')
    json.dump(dict(counts=dict(sorted(S.items())), n_changes=len(out), examples={fam: [x for x in out if x['family'] == fam][:10]
                                                                                 for fam in sorted({x['family'] for x in out})},
                   note='الطرفان مستهلكان مختلفان على مصادر مختلفة: مقارنةٌ تاريخية إضافية، لا إعادةٌ للإعداد القديم بالمحرّكات الحديثة'),
              open(OUT + '.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(dict(sorted(S.items())), ensure_ascii=False, indent=0))


if __name__ == '__main__':
    main()
