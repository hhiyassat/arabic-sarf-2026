"""sidecar_contract.py (v4، V50C01 §٤–§٥ و§٩) — فاحص عقد الإرفاق v4: شروط v3 كلها، ومتطلبات المصدر مشتقةً من صفّ الملف نفسه
(لا من الإرفاق): المصدر والجولة وقياس الجولة من MANIFEST والقيود الظاهرة وقاعدة META_CITATION وسند اللسان (المادة والسطر).

(أصله: فاحص عقد الإرفاق على كل إرفاق، V48C03 §٥.)

check_record(...) يفحص إرفاقاً واحداً بشروطه الفعلية؛ وcheck_corpus(...) يفحص المصحف كله، ومنه تفرّد الهوية؛
وengine_identity(...) يقابل هوية الإرفاق بسجلّ المحرّك (يُستدعى داخل التفريغ حيث السياق متاح).
field_violations = عدد الإرفاقات التي خالفت شرطاً واحداً على الأقل من الشروط المسمّاة هنا، وتُحفظ أنواعها كلها.

    python3 sidecar_contract.py <dump_C.jsonl.gz> <release_v48> <OUT.json>"""
import base64, csv, gzip, json, os, sys, zlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ajnas'))
import source_contract as SC
from collections import Counter, defaultdict

ALLOWED_DEFER = ('DEFERRED_ANALYSIS_NOT_SELECTED:', 'DEFERRED_SELECTED_WITHOUT_ENGINE_ANALYSIS_ID', 'DEFERRED_PATTERN_NOT_SELECTED:',
                 'DEFERRED_NO_REALIZED_WORD', 'DEFERRED_NO_EVENT_IDENTITY:')
REQUIRED_RESIDUALS = ('TWO_BLIND_READERS_AGREED_NOT_OWNER_RULED', 'EVENT_NOT_SENSE_SPECIFIC')
CONS_REQUIRED = ('analysis_id', 'root', 'form_class', 'lemma_pattern', 'realized_word', 'event_id', 'event_form')
SRC = dict(analysis_id='ENGINE', root='ENGINE', form_class='ENGINE', lemma_pattern='ENGINE', realized_word='ENGINE', event_id='ENGINE',
           event_form='RESOURCE')


MEAS = {}


def load_release(rel):
    MEAS.clear(); MEAS.update(SC.measurements(rel))
    rows = {r['link_id']: r for r in csv.DictReader(open(os.path.join(rel, 'ahdath_ajnas.csv'), encoding='utf-8'))}
    ev = {e['event_id']: e for e in csv.DictReader(open(os.path.join(rel, 'events.csv'), encoding='utf-8'))}
    wd = {i for i, e in ev.items() if (e.get('event_review_v36') or '').startswith('WITHDRAWN')}
    return rows, ev, wd


def hfn_class(form):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from sarf.root import hfn_class as hc
    return hc(form)


def plain(t):
    """تطبيع المحرّك نفسه لمفتاح التحليل (sarf.root._plain_vowels)، لا تجريدٌ جديد"""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from sarf.root import _plain_vowels
    return _plain_vowels(t or '')


def check_record(rec, l, rows, ev, wd):
    """إرفاقٌ واحد (l) في سجلّ وقوع (rec) → قائمة المخالفات المسمّاة"""
    v = []
    es = rec.get('event_side') or {}
    c = l.get('match_constraints') or {}
    for k in CONS_REQUIRED:
        x = c.get(k)
        if not isinstance(x, dict) or x.get('value') in (None, ''):
            v.append(f'CONSTRAINT_MISSING:{k}')
        elif x.get('source') != SRC[k]:
            v.append(f'CONSTRAINT_SOURCE:{k}={x.get("source")}')
    aid = (c.get('analysis_id') or {})
    if not (isinstance(aid.get('value'), str) and aid['value'].startswith('A') and len(aid['value']) == 13):
        v.append('ANALYSIS_ID_INVALID')
    if aid.get('derived') is not False:
        v.append('ANALYSIS_ID_NOT_ENGINE')
    if rec.get('analysis_id') != aid.get('value'):
        v.append('ANALYSIS_ID_RECORD_MISMATCH')
    if rec.get('analysis_selection_status') != 'SELECTED':
        v.append('ANALYSIS_NOT_SELECTED')
    if (c.get('lemma_pattern') or {}).get('status') != 'SELECTED':
        v.append('LEMMA_PATTERN_NOT_SELECTED')
    e_id = (c.get('event_id') or {}).get('value')
    if not (e_id == l.get('event_id') == es.get('event_id')):
        v.append('EVENT_MISMATCH')
    row = rows.get(l.get('link_id'))
    if row is None:
        v.append('LINK_NOT_IN_FILE')
        return v
    if row['event_id'] != l.get('event_id'):
        v.append('LINK_EVENT_MISMATCH_FILE')
    e = ev.get(l.get('event_id')) or {}
    if (c.get('root') or {}).get('value') != row['root_K'] or row['root_K'] != e.get('root_K') or l.get('root_K') != row['root_K']:
        v.append('ROOT_MISMATCH')
    if (c.get('event_form') or {}).get('value') != e.get('form'):
        v.append('EVENT_FORM_NOT_FROM_THIS_EVENT')
    if (c.get('form_class') or {}).get('value') != hfn_class(e.get('form')):
        v.append('FORM_CLASS_INCONSISTENT_WITH_EVENT')
    if l.get('status') != 'CANDIDATE' or l.get('rank') != 'CANDIDATE' or row['rank'] != 'CANDIDATE':
        v.append('NOT_CANDIDATE')
    if l.get('is_fact') is not False:
        v.append('IS_FACT_NOT_BOOLEAN_FALSE')
    if l.get('is_fact_raw') != row['is_fact']:
        v.append('IS_FACT_RAW_MISMATCH')
    if l.get('owner_ruling') != 'NONE':
        v.append('OWNER_RULING')
    if l.get('residual') != row['residual'] or not all(r in (l.get('residual') or '') for r in REQUIRED_RESIDUALS):
        v.append('RESIDUAL_MISSING_OR_ALTERED')
    s = l.get('source') or {}
    src = SC.source_of(row)
    if l.get('source_kind') != src or s.get('kind') != src:
        v.append('SOURCE_KIND_MISMATCH')
    if src == 'MUKHASSAS':
        b = l.get('bab') or {}
        if (s.get('sid'), s.get('shahid_line'), s.get('shahid'), b.get('book'), b.get('bab')) != \
                (row['mukhassas_sid'], row['shahid_line'], row['shahid'], row['mukhassas_book'], row['mukhassas_bab']) or not all(
                (s.get('sid'), s.get('shahid_line'), s.get('shahid'), b.get('book'), b.get('bab'))):
            v.append('SOURCE_OR_SHAHID_MISMATCH')
    else:
        md = SC.lisan_madda(row)
        if (s.get('madda'), s.get('line'), s.get('shahid_line'), s.get('shahid'), s.get('qawl')) != (md['madda'], md['line'], row['shahid_line'], row['shahid'], row['qawl']) \
                or md['status'] != 'OK' or not s.get('shahid'):
            v.append('LISAN_SOURCE_MISMATCH')
        if l.get('bab') is not None or any((s.get('mukhassas') or {}).get(k) for k in ('book', 'bab', 'sid')) or not (s.get('mukhassas') or {}).get('not_applicable'):
            v.append('LISAN_FABRICATED_MUKHASSAS')
    if SC.requirements(row) or l.get('requirement_violations'):
        v.append('SOURCE_REQUIREMENTS_UNMET')
    if l.get('round') != SC.round_of(row) or l.get('measurement') != MEAS.get(SC.round_of(row)):
        v.append('ROUND_OR_MEASUREMENT_MISMATCH')
    if sorted(l.get('flags') or []) != sorted(SC.flags(row)):
        v.append('CONSTRAINT_FLAGS_MISSING_OR_ALTERED')
    if (SC.meta_citation(row) or {}).get('decision') == 'EXCLUDE':
        v.append('META_CITATION_LIVE')
    if (l.get('semantic_role'), l.get('dalala')) != (row['role'], row['dalala']) or 'role' in l:
        v.append('ROLE_FIELD')
    if l.get('event_id') in wd or row['event_withdrawn'] == 'True' or l.get('event_withdrawn_raw') == 'True':
        v.append('WITHDRAWN_LIVE')
    return v


def check_corpus(sidecars, rows, ev, wd):
    """sidecars: [(سورة، مخرج attach)] → تقرير"""
    viol = Counter(); bad = []; n_att = 0; n_occ = 0; ident = defaultdict(set); dec = Counter(); defer_bad = []
    for s, sc in sidecars:
        for vk, occ in sc['sidecar'].items():
            for rec in occ:
                es = rec.get('event_side')
                if not es:
                    continue
                d = es['decision'].split(' ')[0]
                dec[d + ('|' + es['reason'].split(':')[0] if es.get('reason') else '')] += 1
                if d == 'DEFERRED' and not str(es.get('reason', '')).startswith(ALLOWED_DEFER):
                    defer_bad.append((rec['occurrence'], es.get('reason')))
                if d == 'ATTACHED_CANDIDATES' and not es.get('links'):
                    viol['ATTACHED_WITHOUT_LINKS'] += 1
                if es.get('links'):
                    n_occ += 1
                for l in es.get('links') or []:
                    n_att += 1
                    w = check_record(rec, l, rows, ev, wd)
                    c = l.get('match_constraints') or {}
                    aid = (c.get('analysis_id') or {}).get('value')
                    ident[aid].add(json.dumps([(c.get(k) or {}).get('value') for k in ('root', 'form_class', 'lemma_pattern')]
                                              + [plain((c.get('realized_word') or {}).get('value'))], ensure_ascii=False))
                    for x in w:
                        viol[x] += 1
                    if w:
                        bad.append(dict(occurrence=rec['occurrence'], link_id=l.get('link_id'), violations=w))
    shared = {k: sorted(v) for k, v in ident.items() if len(v) > 1}
    if shared:
        viol['ANALYSIS_ID_SHARED_BY_DIFFERENT_ANALYSES'] += len(shared)
    viol_records = len(bad) + (len(shared) and 0)
    return dict(attachments=n_att, occurrences_with_attachments=n_occ, decisions=dict(dec), violation_kinds=dict(viol),
                field_violations=len(bad), shared_identity=dict(list(shared.items())[:20]), shared_identity_count=len(shared),
                deferral_reason_invalid=defer_bad[:50], deferral_reason_invalid_count=len(defer_bad), examples=bad[:50],
                distinct_analysis_ids=len(ident), all_ok=not bad and not shared and not defer_bad and not viol)


def engine_identity(sc, C):
    """داخل التفريغ: هوية كل إرفاق تساوي analysis_id في سجلّ المحرّك للوقوع نفسه، والحدث كذلك"""
    an = C.get('analysis'); out = []
    for vk, occ in sc['sidecar'].items():
        M = {f"{vk}:w{m.get('word_index')}.s{m.get('slot')}": m for m in an[vk].get('morph') or []}
        for rec in occ:
            for l in (rec.get('event_side') or {}).get('links') or []:
                m = M.get(rec['occurrence']) or {}
                c = l['match_constraints']
                if c['analysis_id']['value'] != m.get('analysis_id') or c['event_id']['value'] != (m.get('event') or {}).get('event_id') \
                        or c['form_class']['value'] != m.get('form_class') or c['root']['value'] != m.get('root') \
                        or c['lemma_pattern']['value'] != ((m.get('pattern') or {}).get('lemma_pattern')):
                    out.append(dict(occurrence=rec['occurrence'], link_id=l['link_id']))
    return out


def main(dump, rel, outp):
    rows, ev, wd = load_release(rel)
    sc = []; eng = []
    for line in gzip.open(dump, 'rt', encoding='utf-8'):
        d = json.loads(line)
        sc.append((d['surah'], json.loads(zlib.decompress(base64.b64decode(d['ajnas_sidecar']['z'])))))
        eng += d.get('engine_identity_violations') or []
    rep = check_corpus(sc, rows, ev, wd)
    rep['engine_identity_violations'] = len(eng)
    rep['all_ok'] = rep['all_ok'] and not eng
    json.dump(rep, open(outp, 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({k: rep[k] for k in ('attachments', 'occurrences_with_attachments', 'decisions', 'violation_kinds', 'field_violations',
                                          'shared_identity_count', 'deferral_reason_invalid_count', 'engine_identity_violations', 'all_ok')},
                     ensure_ascii=False))
    return rep


if __name__ == '__main__':
    r = main(*sys.argv[1:4])
    sys.exit(0 if r['all_ok'] else 1)
