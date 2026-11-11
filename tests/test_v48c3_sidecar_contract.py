# -*- coding: utf-8 -*-
"""عقد الإرفاق المرشّح v3 (SARF_HFN_V48_TARGETED_REPAIR_AND_CLOSURE_03 §٢–§٥): السليم يجتاز، وكل إفسادٍ يسقط بشرطه المسمّى.
يحتاج SARF_HFN_V48_DIR؛ وبغيابه NOT_RUN (رمز 2)."""
import copy, os, sys
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V48 = os.environ.get('SARF_HFN_V48_DIR', '')
if not os.path.isdir(V48):
    print('NOT_RUN: SARF_HFN_V48_DIR غير معيَّن'); sys.exit(2)
os.environ.update(SARF_HFN=V48, SARF_HFN_TARGET_CONFIG='config/hfn_target_v48_experimental.json', SARF_HFN_EXPERIMENTAL_OK='release_v48',
                  SARF_AJNAS_RELEASE=V48, SARF_AJNAS_EXPECT_RELEASE='HFN_release_v48',
                  SARF_AJNAS_EXPECT_MANIFEST='6cd85dc63b1e920420b09e6d4be748188e37cfc32fe780a05fa2568534119a75')
sys.path.insert(0, H); os.chdir(H)
sys.path.insert(0, os.path.join(H, 'tools', 'v48c3'))
import ajnas_sidecar as S
import sidecar_contract as K
from sarf.stages import run
from sarf import quran_source
FAIL, N = [], [0]


def check(name, ok, got=''):
    N[0] += 1
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:400]}'))
    if not ok:
        FAIL.append(name)


rows, ev, wd = K.load_release(V48)
C = run([r for r in quran_source.rows() if r[0] in (1, 112) or (r[0] == 2 and r[1] in (5, 21, 282))], None, ['references'])
sc = S.attach(C)
rep = K.check_corpus([(0, sc)], rows, ev, wd)
links = [(vk, i, j) for vk, occ in sc['sidecar'].items() for i, r in enumerate(occ) for j, _ in enumerate((r.get('event_side') or {}).get('links') or [])]
check('K01 السليم: إرفاقات > 0 وصفر مخالفات وصفر تفرّدٍ مكسور وهوية المحرّك مطابقة', rep['attachments'] > 0 and rep['all_ok'] and not K.engine_identity(sc, C),
      {k: rep[k] for k in ('attachments', 'violation_kinds', 'shared_identity_count')})
all_l = [sc['sidecar'][vk][i]['event_side']['links'][j] for vk, i, j in links]
check('K02 كل إرفاقٍ حيّ: is_fact قيمةٌ منطقية false (لا نصّ)، والحالة والمرتبة CANDIDATE، والخام محفوظ',
      all(l['is_fact'] is False and l['status'] == 'CANDIDATE' and l['rank'] == 'CANDIDATE' and l['is_fact_raw'] == 'False' for l in all_l), len(all_l))
nb = next(r for r in sc['sidecar']['1:5'] if r['occurrence'] == '1:5:w1.s0')
check('K03 «نَعْبُدُ» (1:5): تحليلٌ غير مختار (DEFERRED_MULTIPLE_LEMMAS) يؤجَّل بسببه، لا هويةٌ شكلية',
      nb['event_side']['decision'] == 'DEFERRED' and nb['event_side']['reason'] == 'DEFERRED_ANALYSIS_NOT_SELECTED:DEFERRED_MULTIPLE_LEMMAS'
      and 'links' not in nb['event_side'], nb['event_side'])


def mutate(fn):
    s2 = copy.deepcopy(sc)
    vk, i, j = links[0]
    fn(s2, s2['sidecar'][vk][i], s2['sidecar'][vk][i]['event_side']['links'][j])
    return s2


def kinds(s2):
    return K.check_corpus([(0, s2)], rows, ev, wd)


def expect(name, fn, kind, also=None):
    s2 = mutate(fn)
    r = kinds(s2)
    ok = kind in r['violation_kinds'] or (kind == 'ANALYSIS_ID_SHARED_BY_DIFFERENT_ANALYSES' and r['shared_identity_count'])
    if also:
        ok = ok and also(s2)
    check(name, ok and not r['all_ok'], r['violation_kinds'])


expect('K04 analysis_id=null يسقط', lambda s, rec, l: l['match_constraints']['analysis_id'].update(value=None), 'CONSTRAINT_MISSING:analysis_id')
other = next(m['analysis_id'] for a in C.get('analysis').values() for m in a['morph'] if m.get('analysis_id')
             and m['analysis_id'] != all_l[0]['match_constraints']['analysis_id']['value'])
expect('K05 هويةٌ صالحة الشكل لا تطابق تحليل الوقوع: يسقطها فاحص هوية المحرّك وسجلّ الوقوع',
       lambda s, rec, l: l['match_constraints']['analysis_id'].update(value=other), 'ANALYSIS_ID_RECORD_MISMATCH',
       also=lambda s2: bool(K.engine_identity(s2, C)))
def same_id(s, rec, l):
    vk2, i2, j2 = next(x for x in links if s['sidecar'][x[0]][x[1]]['event_side']['links'][x[2]]['match_constraints']['root']['value']
                       != l['match_constraints']['root']['value'])
    rec2 = s['sidecar'][vk2][i2]; l2 = rec2['event_side']['links'][j2]
    l2['match_constraints']['analysis_id']['value'] = l['match_constraints']['analysis_id']['value']; rec2['analysis_id'] = l['match_constraints']['analysis_id']['value']
expect('K06 هويةٌ واحدة لتحليلين مختلفين: يسقط', same_id, 'ANALYSIS_ID_SHARED_BY_DIFFERENT_ANALYSES')
oe = next(e for e in ev.values() if e['form'] != ev[all_l[0]['event_id']]['form'])
expect('K07 قيد صيغةٍ مأخوذ من حدثٍ آخر (event_form): يسقط', lambda s, rec, l: l['match_constraints']['event_form'].update(value=oe['form']),
       'EVENT_FORM_NOT_FROM_THIS_EVENT')
expect('K08 فئة صيغةٍ لا تطابق الحدث: يسقط', lambda s, rec, l: l['match_constraints']['form_class'].update(value='ZZ'), 'FORM_CLASS_INCONSISTENT_WITH_EVENT')
expect('K09 الحدث في الإرفاق غير حدث الرابط: يسقط', lambda s, rec, l: l.update(event_id=oe['event_id']), 'EVENT_MISMATCH')
expect('K10 تحفّظٌ لازم محذوف: يسقط', lambda s, rec, l: l.update(residual=l['residual'].replace('EVENT_NOT_SENSE_SPECIFIC', '')),
       'RESIDUAL_MISSING_OR_ALTERED')
expect('K11 ترقية المرشّح إلى حقيقة (is_fact=true): يسقط', lambda s, rec, l: l.update(is_fact=True), 'IS_FACT_NOT_BOOLEAN_FALSE')
expect('K12 الحالة FACT: يسقط', lambda s, rec, l: l.update(status='FACT'), 'NOT_CANDIDATE')
expect('K13 is_fact نصّ «False»: يسقط', lambda s, rec, l: l.update(is_fact='False'), 'IS_FACT_NOT_BOOLEAN_FALSE')
expect('K14 is_fact مفقود: يسقط', lambda s, rec, l: l.pop('is_fact'), 'IS_FACT_NOT_BOOLEAN_FALSE')
expect('K15 الميزان مأخوذٌ مكان الفئة (lemma_pattern في form_class): يسقط',
       lambda s, rec, l: l['match_constraints']['form_class'].update(value=l['match_constraints']['lemma_pattern']['value']), 'FORM_CLASS_INCONSISTENT_WITH_EVENT')
expect('K16 مصدرٌ مدّعى لقيدٍ (الصيغة من المورد مدّعاةً للمحرّك): يسقط',
       lambda s, rec, l: l['match_constraints']['event_form'].update(source='ENGINE'), 'CONSTRAINT_SOURCE:event_form=ENGINE')
expect('K17 رابطٌ لحدثٍ مسحوب حيّ: يسقط', lambda s, rec, l: l.update(event_withdrawn_raw='True'), 'WITHDRAWN_LIVE')
expect('K18 الشاهد مغيَّر: يسقط', lambda s, rec, l: l['source'].update(shahid_line='0'), 'SOURCE_OR_SHAHID_MISMATCH')
s2 = copy.deepcopy(sc)
next(r for occ in s2['sidecar'].values() for r in occ if (r.get('event_side') or {}).get('decision') == 'DEFERRED')['event_side']['reason'] = 'X'
check('K19 تأجيلٌ بلا سببٍ مسمّى من القائمة: يسقط', kinds(s2)['deferral_reason_invalid_count'] == 1)
# التحويل عند حدّ الاستهلاك: جدولٌ صريح، لا bool(نص)
row = dict(rows[all_l[0]['link_id']])
cons = all_l[0]['match_constraints']
check('K20 is_fact الخام «False» ← false منطقية؛ و«True» ← true؛ وغير المعروف ← None (لا bool(نص) الذي يجعل «False» صادقاً)',
      S.link_view(dict(row, is_fact='False'), cons, '')['is_fact'] is False and S.link_view(dict(row, is_fact='True'), cons, '')['is_fact'] is True
      and S.link_view(dict(row, is_fact='maybe'), cons, '')['is_fact'] is None and S.link_view({k: v for k, v in row.items() if k != 'is_fact'}, cons, '')['is_fact'] is None
      and bool('False') is True)
c = S.consumer()
orig = c.query
ev0 = all_l[0]['event_id']
for raw, reason in (('True', 'EXCLUDED_CANDIDATE_MARKED_FACT'), ('maybe', 'DEFERRED_UNKNOWN_IS_FACT')):
    def q(iface, qq, role=None, _raw=raw):
        r = orig(iface, qq, role)
        if iface == 'event' and qq == ev0:
            r = dict(r, links=[dict(l, is_fact=_raw) for l in r['links']])
        return r
    c.query = q
    s3 = S.attach(C)
    c.query = orig
    live = [l for occ in s3['sidecar'].values() for r in occ for l in (r.get('event_side') or {}).get('links') or [] if l['event_id'] == ev0]
    check(f'K21 مورّدٌ يعيد is_fact={raw}: لا يدخل الإرفاق الحي، ويُسجَّل {reason}',
          not live and any(x['reason'] == reason for x in s3['contract_excluded']), (len(live), s3['contract_excluded'][:1]))
print(f'CHECKS pass={N[0] - len(FAIL)} fail={len(FAIL)} total={N[0]}')
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
