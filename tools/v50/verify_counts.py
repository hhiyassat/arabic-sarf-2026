"""verify_counts.py <HFN_ROOT> <OUT.json> — التحقق من الأعداد المعلنة لـ v50 من البيانات نفسها، بمقام كلٍّ وتداخل الفئات (V50C01 §٣).
الجولة تُعرف من حقل method (R1 بلا بادئة R2/R3، وR2 wider forms، وR2 KHILAF re-read، وR3 Lisan)، والعلامات من مكوّنات residual
مفصولةً بـ «·» ومطابَقةً بالرمز كاملاً (فلا يُعدّ ROUND2_WIDER_FORMS من WIDER_FORM)."""
import csv, json, math, os, re, sys
from collections import Counter
HR, OUT = sys.argv[1:3]
D = lambda v: os.path.join(HR, 'release', f'release_v{v}')


def load(v):
    return list(csv.DictReader(open(os.path.join(D(v), 'ahdath_ajnas.csv'), encoding='utf-8')))


def marks(r):
    return {p.strip().split(' (')[0] for p in r['residual'].split('·') if p.strip()}


def round_of(r):
    m = r['method']
    return 'R3_LISAN' if m.startswith('R3 Lisan') else 'R2_WIDER' if m.startswith('R2 wider forms') else 'R2_KHILAF' if m.startswith('R2 KHILAF') else 'R1_MUKHASSAS'


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


r48, r49, r50 = load(48), load(49), load(50)
ev50 = {e['event_id']: e for e in csv.DictReader(open(os.path.join(D(50), 'events.csv'), encoding='utf-8'))}
WD = {i for i, e in ev50.items() if (e.get('event_review_v36') or '').startswith('WITHDRAWN')}
id49 = {r['link_id'] for r in r49}
new50 = [r for r in r50 if r['link_id'] not in id49]
lis = [r for r in r50 if 'SOURCE_LISAN_NO_GENUS_BAB' in marks(r)]
hum = [r for r in r50 if 'LISAN_GENERIC_HUMAN_DHAT' in marks(r)]
wid = [r for r in r50 if 'WIDER_FORM' in marks(r)]
e49, e50 = {r['event_id'] for r in r49}, {r['event_id'] for r in r50}
man = json.load(open(os.path.join(D(50), 'MANIFEST.json'), encoding='utf-8'))
r3 = man['ahdath_ajnas_round3_lisan']
C = dict(
    total_links=dict(declared=17215, measured=len(r50), denominator='صفوف ahdath_ajnas.csv في v50', unique_ids=len({r['link_id'] for r in r50})),
    lisan_links_added=dict(declared=1182, measured=len(new50), lisan_marker=len(lis), same_set=({r['link_id'] for r in new50} == {r['link_id'] for r in lis}),
                           denominator='الروابط الجديدة في v50 مقابل v49 بالمعرّف'),
    events_linked=dict(declared=9894, measured=len(e50), withdrawn_among=len(e50 & WD), denominator='الأحداث المتمايزة في الملف، ومنها المسحوبة'),
    events_newly_linked=dict(declared=915, measured=len(e50 - e49), denominator='أحداث v50 غير الموجودة في روابط v49', all_from_lisan=all(
        any(r['event_id'] == e for r in lis) for e in e50 - e49)),
    generic_human=dict(declared=282, guide_inside_v50_says=264, measured=len(hum), all_lisan=all(r in lis for r in hum), denominator='روابط اللسان (1182)',
                       dhat_words=dict(Counter(r['dhat'] for r in hum).most_common())),
    wider_form=dict(declared=151, measured=len(wid), all_lisan=all(r in lis for r in wid), denominator='روابط اللسان (1182)', overlap_with_generic_human=sum(1 for r in hum if r in wid)),
    by_round=dict(Counter(round_of(r) for r in r50)),
    round2=dict(declared_added=man['ahdath_ajnas_round2']['links_added'], measured_added=len(r49) - len(r48)),
    withdrawn_links=dict(v48=sum(1 for r in r48 if r['event_withdrawn'] == 'True'), v50=sum(1 for r in r50 if r['event_withdrawn'] == 'True'),
                         v50_by_events_csv=sum(1 for r in r50 if r['event_id'] in WD), by_round=dict(Counter(round_of(r) for r in r50 if r['event_id'] in WD))),
    wilson_round3=dict(declared=r3['yes_rows_wilson_low'], recomputed=round(wilson(r3['yes_rows_agree'], r3['yes_rows']), 6), denominator=f"{r3['yes_rows_agree']}/{r3['yes_rows']} صفوف نعم في الجولة الثالثة"),
    lisan_dhat_K_empty=sum(1 for r in lis if not r['dhat_K']), non_lisan_dhat_K_empty=sum(1 for r in r50 if r not in lis and not r['dhat_K']),
    lisan_mukhassas_fields_empty=all(not r['mukhassas_book'] and not r['mukhassas_bab'] and not r['mukhassas_sid'] for r in lis),
    lisan_qawl_pattern=sum(1 for r in lis if re.match(r'^على ذكر صاحب لسان العرب، مادّة «([^»]+)» \(سطر (\d+) من نصّ OpenITI\)$', r['qawl'])),
    manifest_block_names=dict(ahdath_ajnas_links=man['ahdath_ajnas']['links'], note='كتلة ahdath_ajnas في بيان v50 تخص الجولة الأولى وحدها (11943)؛ واسمها لا يقول ذلك'))
C['all_declared_match'] = all(x['declared'] == x['measured'] for k, x in C.items() if isinstance(x, dict) and 'declared' in x and 'measured' in x)
json.dump(C, open(OUT, 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk not in ('dhat_words',)} if isinstance(v, dict) else v) for k, v in C.items()}, ensure_ascii=False, indent=0))
