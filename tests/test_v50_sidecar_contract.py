# -*- coding: utf-8 -*-
"""عقد الإرفاق المرشّح v4 المدرك للمصدر (SARF_HFN_V50_COMPATIBILITY_01 §٤–§٦ و§٩): السليم يجتاز، وكل إفسادٍ يسقط بشرطه المسمّى.
الإفسادات تمسّ الإرفاق (لا المورد)؛ وإفساد المورد نفسه (صفٌّ معدَّل) يُقابَل بإرفاقٍ سليم فيسقط كذلك.
يحتاج SARF_HFN_V50_DIR؛ وبغيابه NOT_RUN (رمز 2)."""
import copy, os, sys
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V50 = os.environ.get('SARF_HFN_V50_DIR', '')
if not os.path.isdir(V50):
    print('NOT_RUN: SARF_HFN_V50_DIR غير معيَّن'); sys.exit(2)
M50 = '7e5dc7ad6244339f5a260aca2833eb0979e348cdb78ef86784ece3b0301033fb'
os.environ.update(SARF_HFN=V50, SARF_HFN_TARGET_CONFIG='config/hfn_target_v50_experimental.json', SARF_HFN_EXPERIMENTAL_OK='release_v50',
                  SARF_AJNAS_RELEASE=V50, SARF_AJNAS_EXPECT_RELEASE='HFN_release_v50', SARF_AJNAS_EXPECT_MANIFEST=M50)
sys.path.insert(0, H); os.chdir(H)
sys.path.insert(0, os.path.join(H, 'tools', 'v50'))
sys.path.insert(0, os.path.join(H, 'tools', 'ajnas'))
import ajnas_sidecar as S
import sidecar_contract as K
import source_contract as SC
from sarf.stages import run
from sarf import quran_source
FAIL, N = [], [0]


def check(name, ok, got=''):
    N[0] += 1
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:400]}'))
    if not ok:
        FAIL.append(name)


rows, ev, wd = K.load_release(V50)
VERSES = {(2, 5), (2, 21), (2, 96), (2, 102), (2, 105), (2, 282)}
C = run([r for r in quran_source.rows() if r[0] in (1, 112) or (r[0], r[1]) in VERSES], None, ['references'])
sc = S.attach(C)
rep = K.check_corpus([(0, sc)], rows, ev, wd)
links = [(vk, i, j) for vk, occ in sc['sidecar'].items() for i, r in enumerate(occ) for j, _ in enumerate((r.get('event_side') or {}).get('links') or [])]
L = lambda x: sc['sidecar'][x[0]][x[1]]['event_side']['links'][x[2]]
all_l = [L(x) for x in links]
first = lambda pred: next(x for x in links if pred(L(x)))
LIS = first(lambda l: l['source_kind'] == 'LISAN')
MUK = first(lambda l: l['source_kind'] == 'MUKHASSAS')
HUM = first(lambda l: 'GENERIC_HUMAN_NOT_GENUS' in l['flags'])
WID = first(lambda l: 'WIDER_FORM_NO_GENERALIZATION' in l['flags'])
R1 = first(lambda l: l['round'] == 'R1_MUKHASSAS')
metas = [(vk, i) for vk, occ in sc['sidecar'].items() for i, r in enumerate(occ) if (r.get('event_side') or {}).get('excluded_meta_citation')]

check('S01 السليم: إرفاقات > 0 من المصدرين، وصفر مخالفات، وهوية المحرّك مطابقة، والعقد v4',
      rep['attachments'] > 0 and rep['all_ok'] and not K.engine_identity(sc, C) and sc['contract'] == 'AJNAS_SIDECAR_CONTRACT_v4'
      and {l['source_kind'] for l in all_l} == {'LISAN', 'MUKHASSAS'}, {k: rep[k] for k in ('attachments', 'violation_kinds')})
check('S02 كل إرفاق: is_fact قيمةٌ منطقية false، والحالة والمرتبة CANDIDATE، والخام «False» محفوظ',
      all(l['is_fact'] is False and l['status'] == 'CANDIDATE' and l['rank'] == 'CANDIDATE' and l['is_fact_raw'] == 'False' for l in all_l), len(all_l))
l = L(LIS)
check('S03 رابط اللسان: علامة SOURCE_LISAN_NO_GENUS_BAB في التحفّظ، والمادة والسطر من qawl ويساوي السطر shahid_line، والشاهد غير فارغ، '
      'وحقول المخصّص None بعلّة not_applicable، وbab=None، والجولة R3 وقياسها 0.822 بمقامها',
      SC.LISAN_MARK in l['residual'] and l['source']['madda'] and l['source']['line'] == l['source']['shahid_line'] and l['source']['shahid']
      and l['source']['mukhassas']['book'] is None and l['source']['mukhassas']['not_applicable'] and l['bab'] is None
      and l['round'] == 'R3_LISAN' and l['measurement']['value'] == 0.822 and l['measurement']['rows'] == 1403, l)
m = L(MUK)
check('S04 رابط المخصّص: الكتاب والباب والسند والسطر والشاهد من الصف، وقياس جولته من كتلتها لا 0.822',
      all((m['bab']['book'], m['bab']['bab'], m['source']['sid'], m['source']['shahid_line'], m['source']['shahid']))
      and m['measurement'] == K.MEAS[m['round']] and (m['round'] == 'R2_KHILAF' or m['measurement'].get('value') != 0.822), m)
check('S05 كل جوابٍ فيه تحفّظ 0.768 الخام يحمل معه ملاحظة المقام (الجولة الأولى 11943/15412)، ولا يُستبدل الخام',
      all(K.RAW_0768 in r['event_side']['api_residuals'] and any(n.startswith(K.SCOPE_PREFIX) for n in r['event_side']['api_notes'])
          for occ in sc['sidecar'].values() for r in occ if (r.get('event_side') or {}).get('links')))
check('S06 الاستبعاد الوصفي (META_CITATION) مسجَّلٌ بمعرّفه ودليله، ولا يدخل الحي', metas and all(
    x['evidence']['decision'] == 'EXCLUDE' and x['link_id'] not in {k['link_id'] for k in sc['sidecar'][vk][i]['event_side']['links']}
    for vk, i in metas for x in sc['sidecar'][vk][i]['event_side']['excluded_meta_citation']), metas[:3])


def expect(name, at, fn, kind, rows_=None):
    s2 = copy.deepcopy(sc)
    vk, i, j = at
    rec = s2['sidecar'][vk][i]
    fn(s2, rec, rec['event_side']['links'][j] if j is not None else None)
    r = K.check_corpus([(0, s2)], rows_ or rows, ev, wd)
    check(name, kind in r['violation_kinds'] and not r['all_ok'], r['violation_kinds'])


def drop_mark(tok):
    return lambda s, rec, l: l.update(residual='·'.join(p for p in l['residual'].split('·') if p.strip().split(' (')[0] != tok))


expect('S07 علامة اللسان محذوفة من التحفّظ: يسقط', LIS, drop_mark(SC.LISAN_MARK), 'RESIDUAL_MISSING_OR_ALTERED')
expect('S08 رابط لسان معروضٌ مصدرُه مخصّصاً: يسقط', LIS, lambda s, rec, l: l.update(source_kind='MUKHASSAS'), 'SOURCE_KIND_MISMATCH')
expect('S09 شاهد اللسان محذوف: يسقط', LIS, lambda s, rec, l: l['source'].update(shahid=''), 'LISAN_SOURCE_MISMATCH')
expect('S10 مادة اللسان مغيَّرة: يسقط', LIS, lambda s, rec, l: l['source'].update(madda='زيد'), 'LISAN_SOURCE_MISMATCH')
expect('S11 سطر اللسان مغيَّر: يسقط', LIS, lambda s, rec, l: l['source'].update(line='1'), 'LISAN_SOURCE_MISMATCH')
expect('S12 حقل مخصّصٍ مختلق على رابط لسان (باب): يسقط', LIS, lambda s, rec, l: l.update(bab=dict(book='X', bab='Y')), 'LISAN_FABRICATED_MUKHASSAS')
expect('S13 رابط مخصّص بلا باب: يسقط', MUK, lambda s, rec, l: l['bab'].update(bab=''), 'SOURCE_OR_SHAHID_MISMATCH')
expect('S14 رابط مخصّص بلا رقم سند: يسقط', MUK, lambda s, rec, l: l['source'].update(sid=''), 'SOURCE_OR_SHAHID_MISMATCH')
expect('S15 is_fact نصّ «False»: يسقط', LIS, lambda s, rec, l: l.update(is_fact='False'), 'IS_FACT_NOT_BOOLEAN_FALSE')
expect('S16 is_fact=true: يسقط', MUK, lambda s, rec, l: l.update(is_fact=True), 'IS_FACT_NOT_BOOLEAN_FALSE')
expect('S17 تحفّظٌ لازم محذوف (EVENT_NOT_SENSE_SPECIFIC): يسقط', LIS,
       lambda s, rec, l: l.update(residual=l['residual'].replace('EVENT_NOT_SENSE_SPECIFIC', '')), 'RESIDUAL_MISSING_OR_ALTERED')
expect('S18 قيد «الرجل/فلان ليس جنساً» محذوف من القيود: يسقط', HUM,
       lambda s, rec, l: l.update(flags=[f for f in l['flags'] if f != 'GENERIC_HUMAN_NOT_GENUS']), 'CONSTRAINT_FLAGS_MISSING_OR_ALTERED')
expect('S19 علامة الرجل/فلان محذوفة من التحفّظ: يسقط', HUM, drop_mark('LISAN_GENERIC_HUMAN_DHAT'), 'RESIDUAL_MISSING_OR_ALTERED')
expect('S20 قيد WIDER_FORM محذوف: يسقط', WID,
       lambda s, rec, l: l.update(flags=[f for f in l['flags'] if f != 'WIDER_FORM_NO_GENERALIZATION']), 'CONSTRAINT_FLAGS_MISSING_OR_ALTERED')
expect('S21 قياس 0.822 معمَّمٌ على رابط من الجولة الأولى: يسقط', R1,
       lambda s, rec, l: l.update(measurement=dict(l['measurement'], value=0.822)), 'ROUND_OR_MEASUREMENT_MISMATCH')
expect('S22 جولة الرابط مغيَّرة: يسقط', LIS, lambda s, rec, l: l.update(round='R1_MUKHASSAS'), 'ROUND_OR_MEASUREMENT_MISMATCH')
other = next(m_['analysis_id'] for a in C.get('analysis').values() for m_ in a['morph'] if m_.get('analysis_id')
             and m_['analysis_id'] != L(LIS)['match_constraints']['analysis_id']['value'])
expect('S23 تحليلٌ غير مطابق (هوية تحليلٍ آخر): يسقط', LIS,
       lambda s, rec, l: l['match_constraints']['analysis_id'].update(value=other), 'ANALYSIS_ID_RECORD_MISMATCH')
oe = next(e for e in ev.values() if e['event_id'] != L(LIS)['event_id'] and e['form'] != ev[L(LIS)['event_id']]['form'])
expect('S24 حدثٌ غير مطابق: يسقط', LIS, lambda s, rec, l: l.update(event_id=oe['event_id']), 'EVENT_MISMATCH')
expect('S25 الإرفاق محوَّلٌ إلى فاعلٍ/مفعولٍ نحوي (حقل role): يسقط', MUK, lambda s, rec, l: l.update(role='فاعل'), 'ROLE_FIELD')
expect('S26 الدور الدلالي مغيَّر (محلّ → مفعول به): يسقط', MUK, lambda s, rec, l: l.update(semantic_role='مفعول به'), 'ROLE_FIELD')
expect('S27 رابط حدثٍ مسحوب حيّ: يسقط', MUK, lambda s, rec, l: l.update(event_withdrawn_raw='True'), 'WITHDRAWN_LIVE')
expect('S28 مخالفة متطلبات المصدر مخفيّة في الإرفاق: يسقط', LIS, lambda s, rec, l: l.update(requirement_violations=['X']), 'SOURCE_REQUIREMENTS_UNMET')
# استبعادٌ وصفي: محوَّلٌ إلى حي، أو محذوف بصمت، أو بلا دليل
vk0, i0 = metas[0]
mid = sc['sidecar'][vk0][i0]['event_side']['excluded_meta_citation'][0]['link_id']
j0 = 0 if sc['sidecar'][vk0][i0]['event_side']['links'] else None


def revive(s, rec, l):
    es = rec['event_side']
    es['excluded_meta_citation'] = es['excluded_meta_citation'][1:]
    tpl = copy.deepcopy(es['links'][0]) if es['links'] else None
    if tpl:
        r = rows[mid]
        tpl.update(link_id=mid, residual=r['residual'], semantic_role=r['role'], dalala=r['dalala'])
        es['links'].append(tpl)


expect('S29 رابط استشهادٍ وصفي (قال سيبويه…) معادٌ إلى الحي: يسقط', (vk0, i0, j0), revive, 'META_CITATION_LIVE' if j0 is not None else 'META_EXCLUSION_NOT_RECORDED')
expect('S30 استبعادٌ وصفي محذوفٌ بصمت (لا في الحي ولا في السجل): يسقط', (vk0, i0, None),
       lambda s, rec, l: rec['event_side'].update(excluded_meta_citation=rec['event_side']['excluded_meta_citation'][1:]), 'META_EXCLUSION_NOT_RECORDED')
expect('S31 استبعادٌ وصفي بلا دليله: يسقط', (vk0, i0, None),
       lambda s, rec, l: rec['event_side']['excluded_meta_citation'][0].update(evidence=None), 'META_EXCLUSION_UNJUSTIFIED')
expect('S32 رابطٌ حيّ محذوفٌ بصمت من الإرفاق: يسقط', (LIS[0], LIS[1], None),
       lambda s, rec, l: rec['event_side'].update(links=rec['event_side']['links'][1:]), 'LIVE_SET_NOT_FILE_MINUS_DECLARED_EXCLUSIONS')
expect('S33 ملاحظة المقام مُسقطة مع بقاء 0.768 الخام: يسقط', (LIS[0], LIS[1], None),
       lambda s, rec, l: rec['event_side'].update(api_notes=[]), 'SCOPE_NOTE_MISSING')
expect('S34 تحفّظ 0.768 الخام مستبدَلٌ بـ 0.822: يسقط', (LIS[0], LIS[1], None),
       lambda s, rec, l: rec['event_side'].update(api_residuals=[x.replace('0.768', '0.822') for x in rec['event_side']['api_residuals']]),
       'API_RAW_RESIDUAL_ALTERED')
# إفساد المورد نفسه: صفّ اللسان معدَّل (سطر qawl ≠ shahid_line) مع إرفاقٍ سليم → متطلبات المصدر غير مستوفاة
r2 = copy.deepcopy(rows)
lid = L(LIS)['link_id']
r2[lid]['qawl'] = r2[lid]['qawl'].replace('(سطر ', '(سطر 9')
expect('S35 صفّ لسانٍ في المورد معدَّل (سطر qawl لا يساوي shahid_line): يسقط', LIS, lambda s, rec, l: None, 'SOURCE_REQUIREMENTS_UNMET', rows_=r2)
r3 = copy.deepcopy(rows)
r3[L(MUK)['link_id']]['mukhassas_bab'] = ''
expect('S36 صفّ مخصّصٍ في المورد بلا باب: يسقط', MUK, lambda s, rec, l: None, 'SOURCE_REQUIREMENTS_UNMET', rows_=r3)
# حدّ الاستهلاك: مخالفة متطلبات المصدر في المورد تؤجِّل الرابط، لا تُرفقه ولا تملأ حقله
c = S.consumer(); orig = c.query
ev0 = L(LIS)['event_id']


def q(iface, qq, role=None):
    r = orig(iface, qq, role)
    if iface == 'event' and qq == ev0:
        r = dict(r, links=[dict(x, shahid='') if x['link_id'] == lid else x for x in r['links']],
                 link_meta={k: (SC.describe(dict(rows[k], shahid=''), K.MEAS) if k == lid else v) for k, v in r['link_meta'].items()})
    return r


c.query = q
s3 = S.attach(C)
c.query = orig
live = [x for occ in s3['sidecar'].values() for r in occ for x in (r.get('event_side') or {}).get('links') or [] if x['link_id'] == lid]
check('S37 مورّدٌ يعيد رابط لسانٍ بلا شاهد: لا يدخل الحي، ويُسجَّل DEFERRED_SOURCE_REQUIREMENTS:LISAN_MISSING:shahid',
      not live and any(x['link_id'] == lid and x['reason'].startswith('DEFERRED_SOURCE_REQUIREMENTS') and 'LISAN_MISSING:shahid' in x['reason']
                       for x in s3['contract_excluded']), s3['contract_excluded'][:2])
print(f'CHECKS pass={N[0] - len(FAIL)} fail={len(FAIL)} total={N[0]}')
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
