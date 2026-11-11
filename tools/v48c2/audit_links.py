"""audit_links.py <HFN_ROOT (f06fd7c)> <OUT_DIR> — تدقيق ahdath_ajnas.csv كاملاً من الملفات المجمّدة (V48C02 §٧ و§١٠).
يُعاد حساب كل رقمٍ هنا من الملف نفسه ومن events.csv وroots.csv في الإصدار نفسه، ومن ملفات التسليم (KHILAF وCHUNK_SCORES)؛
ولا يُنقل رقمٌ مبلَّغ بوصفه نتيجة. ويكتب: links_audit.json، وrows_795_dhat_readers_differ.tsv، وrows_5_withdrawn.tsv، وagreement_0768.json."""
import csv, json, math, os, re, sys
from collections import Counter

HR, OUT = sys.argv[1], sys.argv[2]
D = os.path.join(HR, 'release', 'release_v48')
os.makedirs(OUT, exist_ok=True)
rows = list(csv.DictReader(open(os.path.join(D, 'ahdath_ajnas.csv'), encoding='utf-8')))
cols = list(rows[0].keys())
ev = {e['event_id']: e for e in csv.DictReader(open(os.path.join(D, 'events.csv'), encoding='utf-8'))}
roots = {r.get('root_K') or r.get('root') for r in csv.DictReader(open(os.path.join(D, 'roots.csv'), encoding='utf-8'))}
WD = {i for i, e in ev.items() if (e.get('event_review_v36') or '').startswith('WITHDRAWN')}
R = dict(file=os.path.join(D, 'ahdath_ajnas.csv'), columns=cols, rows=len(rows))
ids = Counter(r['link_id'] for r in rows)
R['link_id_unique'] = len(ids); R['link_id_duplicates'] = sorted(k for k, v in ids.items() if v > 1)
R['exact_row_duplicates'] = sum(v - 1 for v in Counter(tuple(r.values()) for r in rows).values() if v > 1)
ck = Counter((r['event_id'], r['dhat_K'], r['role'], r['mukhassas_sid'], r['shahid_line']) for r in rows)
R['content_key_duplicates(event,dhat_K,role,sid,line)'] = sum(v - 1 for v in ck.values() if v > 1)
R['event_ref_missing'] = sorted({r['event_id'] for r in rows if r['event_id'] not in ev})
R['root_mismatch_with_event'] = [r['link_id'] for r in rows if r['event_id'] in ev and r['root_K'] != ev[r['event_id']]['root_K']]
R['root_not_in_roots_csv'] = sorted({r['root_K'] for r in rows if r['root_K'] not in roots})
R['verb_mismatch_with_event'] = [r['link_id'] for r in rows if r['event_id'] in ev and r['verb'] != ev[r['event_id']]['verb']]
R['masdar_mismatch_with_event'] = [r['link_id'] for r in rows if r['event_id'] in ev and r['masdar'] != ev[r['event_id']]['masdar']]
R['events_covered'] = len({r['event_id'] for r in rows}); R['events_in_release'] = len(ev)
R['roots_covered'] = len({r['root_K'] for r in rows}); R['roots_in_release'] = len(roots)
for c in ('role', 'dalala', 'luzum_naw', 'luzum_martaba', 'rank', 'is_fact', 'method', 'event_withdrawn', 'mukhassas_book'):
    R['dist_' + c] = dict(Counter(r[c] for r in rows).most_common())
R['role_dalala_luzum'] = dict(Counter(f"{r['dalala']}|{r['luzum_naw']}|{r['luzum_martaba']}" for r in rows))
R['luzum_consistent_with_dalala'] = all((r['dalala'] == 'تضمّن') == (r['luzum_naw'] == '-' and r['luzum_martaba'] == '-') for r in rows)
R['sanad'] = {c: dict(empty=sum(1 for r in rows if not r[c].strip())) for c in ('mukhassas_book', 'mukhassas_bab', 'mukhassas_sid', 'shahid_line', 'shahid', 'qawl', 'method')}
R['sanad']['mukhassas_sid_numeric'] = sum(1 for r in rows if r['mukhassas_sid'].isdigit())
R['sanad']['shahid_line_numeric'] = sum(1 for r in rows if r['shahid_line'].isdigit())
R['reader_notes'] = {c: dict(empty=sum(1 for r in rows if not (r.get(c) or '').strip())) for c in ('reader_note_1', 'reader_note_2')}
comp = Counter(p.strip() for r in rows for p in re.split(r'[;|،·]', r['residual']) if p.strip())
R['residual_components'] = dict(comp.most_common())
R['owner_ruling_column'] = [c for c in cols if 'owner' in c.lower() or 'ruling' in c.lower()]
R['owner_ruling_status'] = 'NONE: لا عمود لحكم المالك؛ وكل الصفوف rank=CANDIDATE وis_fact=False' if not R['owner_ruling_column'] else 'COLUMN_PRESENT'
d795 = [r for r in rows if '|' in r['dhat_readers']]
R['dhat_readers_differ_rows'] = len(d795)
R['dhat_readers_differ_residual_rows'] = sum(1 for r in rows if 'DHAT_WORD_READERS_DIFFER' in r['residual'])
R['dhat_K_multi(·)'] = sum(1 for r in rows if '·' in r['dhat_K'])
wd = [r for r in rows if r['event_withdrawn'] == 'True']
R['withdrawn_flag_rows'] = len(wd)
R['withdrawn_by_events_csv_rows'] = sum(1 for r in rows if r['event_id'] in WD)
R['withdrawn_flag_vs_events_csv_disagree'] = [r['link_id'] for r in rows if (r['event_withdrawn'] == 'True') != (r['event_id'] in WD)]
R['withdrawn_rows'] = [dict(link_id=r['link_id'], event_id=r['event_id'], verb=r['verb'], dhat=r['dhat'], role=r['role'],
                            review=ev[r['event_id']]['event_review_v36']) for r in wd]
R['withdrawn_events_in_release'] = len(WD)
R['dhat_has_diacritics'] = sum(1 for r in rows if re.search('[ً-ْٰ]', r['dhat']))
R['dhat_K_starts_with_al'] = sorted({r['dhat_K'] for r in rows if any(p.startswith('ال') for p in r['dhat_K'].split('·'))})
for name, sel in (('rows_795_dhat_readers_differ.tsv', d795), ('rows_5_withdrawn.tsv', wd)):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter='\t'); w.writeheader(); w.writerows(sel)
json.dump(R, open(os.path.join(OUT, 'links_audit.json'), 'w'), ensure_ascii=False, indent=1)

# ── 0.768: مصدره ومقامه، من ملفات التسليم المثبّتة ──
HD = os.path.join(HR, '06_handoff', 'ahdath_ajnas_v48')
man = json.load(open(os.path.join(D, 'MANIFEST.json'), encoding='utf-8'))['ahdath_ajnas']
kh = list(csv.DictReader(open(os.path.join(HD, 'KHILAF.tsv'), encoding='utf-8'), delimiter='\t'))
cs = list(csv.DictReader(open(os.path.join(HD, 'CHUNK_SCORES.tsv'), encoding='utf-8'), delimiter='\t'))


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


yes = lambda x: (x or '').startswith('YES')
kh_yes2 = sum(1 for r in kh if yes(r['A']) and yes(r['B'])); kh_yes1 = sum(1 for r in kh if yes(r['A']) != yes(r['B']))
k, n = man['agreement_yes_rows']['agree'], man['agreement_yes_rows']['rows']
ex = [r for r in cs if r['chunk'] in man['excluded_chunks']]
A = dict(manifest_block=man, released_links=len(rows),
         denominator=dict(manifest=n, recomputed=len(rows) + kh_yes2 + kh_yes1, links=len(rows), khilaf_both_yes_but_differ=kh_yes2,
                          khilaf_one_yes=kh_yes1, khilaf_rows=len(kh)),
         candidates=dict(raw_rate=round(k / n, 6), wilson95_lower=round(wilson(k, n), 6), wilson95_lower_3dp=round(wilson(k, n), 3),
                         raw_3dp=round(k / n, 3), reported=man['agreement_yes_rows']['rate']),
         all_rows=dict(manifest=man['agreement_all_rows'], raw=round(man['agreement_all_rows']['agree'] / man['agreement_all_rows']['rows'], 6),
                       wilson95_lower=round(wilson(man['agreement_all_rows']['agree'], man['agreement_all_rows']['rows']), 6),
                       chunk_scores_sum=dict(rows=sum(int(r['rows']) for r in cs), agree=sum(int(r['agree']) for r in cs)),
                       excluded_chunks=[dict(r) for r in ex],
                       chunk_sum_minus_excluded_agree=sum(int(r['agree']) for r in cs) - sum(int(r['agree']) for r in ex),
                       excluded_rows_kept_in_denominator=sum(int(r['rows']) for r in ex)),
         method_source=dict(declared=man.get('source'), code_available=False,
                            note='الالتزام AMLN 069adf7 غير موجودٍ في المستودع المحلي ولا في origin؛ فطريقة الحساب لا تُثبت من شيفرتها'),
         verdict=None)
A['verdict'] = ('0.768 يساوي الحدّ الأدنى لفاصل ويلسون 95% (0.7683) مقرَّباً إلى ثلاث خانات، ولا يساوي النسبة الخام (0.7749 ← 0.775)؛ '
                'ورقم «كل الصفوف» في البيان نفسه مسمّى wilson_low ويساوي ويلسون لبسطه ومقامه. فالأرجح أنه حدّ ويلسون مسمّى rate، '
                'ولا يُثبت ذلك إلا بشيفرة الحساب غير المتاحة. ونوعه: اتفاق قارئَين آليَّين في صفوفٍ قال فيها أحدهما YES، لا دقّةٌ على معيار ذهبي، '
                'وهو دون حدّ البيان نفسه (0.78)')
json.dump(A, open(os.path.join(OUT, 'agreement_0768.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(dict(rows=R['rows'], unique=R['link_id_unique'], d795=R['dhat_readers_differ_rows'], withdrawn=R['withdrawn_flag_rows'],
                      denominator=A['denominator'], candidates=A['candidates']), ensure_ascii=False))
