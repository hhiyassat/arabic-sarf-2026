# -*- coding: utf-8 -*-
"""أدوات المقارنة والإرفاق (SARF_HFN_V48_VALIDATION_COMPLETION_02 §٦ و§٩ و§١٢): تُختبر بالإفساد لا بالتشغيل السليم وحده.
- البصمة بالمحتوى: تغيير حالة التزامٍ واحد، أو سنده وحده، يظهر في مفتاح جملته، وتصنّفه المقابلة (STATUS / EVIDENCE_ONLY).
- مرحلةٌ غير منفّذة، أو كائنٌ يُسلسل بعنوان ذاكرة: خطأٌ مسمّى، لا تساوٍ بين نصّي خطأ.
- مقابلة الجمل بالمدى: انقسامٌ تامّ، ودمج، وإضافة، وحذف، وانقسامٌ بفجوةٍ ليس انقساماً، ومفاتيح مكررة مرفوضة.
- الإرفاق المرشّح لا يغيّر السياق، وإفسادٌ يستعمل الرابط حقيقةً في شهادةٍ يكشفه فاحص التسرّب ومقارنة الجمل.
يحتاج SARF_HFN_V48_DIR (ومجلّد api بجانب release)؛ وبغيابه NOT_RUN (رمز 2)."""
import copy, json, os, sys
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V48 = os.environ.get('SARF_HFN_V48_DIR', '')
if not os.path.isdir(V48):
    print('NOT_RUN: SARF_HFN_V48_DIR غير معيَّن'); sys.exit(2)
os.environ.update(SARF_HFN=V48, SARF_HFN_TARGET_CONFIG='config/hfn_target_v48_experimental.json', SARF_HFN_EXPERIMENTAL_OK='release_v48',
                  SARF_AJNAS_RELEASE=V48, SARF_AJNAS_EXPECT_RELEASE='HFN_release_v48',
                  SARF_AJNAS_EXPECT_MANIFEST='6cd85dc63b1e920420b09e6d4be748188e37cfc32fe780a05fa2568534119a75')
sys.path.insert(0, H); os.chdir(H)
sys.path.insert(0, os.path.join(H, 'tools', 'v48c2'))
import engine_dump2 as D
sys.path.insert(0, os.path.join(H, 'tools', 'v48c3'))
import ajnas_sidecar as S   # الإرفاق الحيّ: عقد v3 (V48C03)
from sarf.stages import run
from sarf import quran_source
FAIL, N = [], [0]


def check(name, ok, got=''):
    N[0] += 1
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:400]}'))
    if not ok:
        FAIL.append(name)


rows = [r for r in quran_source.rows() if r[0] == 112 or (r[0] == 2 and r[1] == 282)]
C = run(rows, None, D.TARGETS)
P0, S0, T0 = D.fingerprint(C)
check('T01 تشغيل سليم: كل المراحل منفّذة، وبصمةٌ لكل منتَج ولكل مفتاح، وسجلّ جمل', len(P0) == 19 and S0 and all(p['keys'] for k, p in P0.items() if k not in ('evidence_audit',)), list(S0)[:3])
# T02 تغيير حالة التزامٍ واحد
C2 = copy.deepcopy(C)
sid = next(s for s, c in C2.get('certificates').items() if c['obligations'])
C2.get('certificates')[sid]['obligations'][0]['status'] = 'UNMET_INJECTED'
P2, S2, _ = D.fingerprint(C2)
m = D.match_sentences(S0, S2)
check('T02 حالة التزامٍ واحد: يتغيّر مفتاح الجملة وحده في certificates، والمقابلة تصنّفه STATUS',
      [k for k in P0['certificates']['keys'] if P0['certificates']['keys'][k] != P2['certificates']['keys'][k]] == [sid]
      and m['changed'] and m['changed'][0]['obligations'][0]['kind'] == 'STATUS', m['changed'][:1])
# T03 تغيير السند وحده
C3 = copy.deepcopy(C)
o = C3.get('certificates')[sid]['obligations'][0]
o['discharge_evidence_id'] = (o.get('discharge_evidence_id') or '') + '#INJECTED'
_, S3, _ = D.fingerprint(C3)
m = D.match_sentences(S0, S3)
check('T03 سند الاستيفاء وحده (الحالة نفسها): EVIDENCE_ONLY', m['changed'] and m['changed'][0]['obligations'][0]['kind'] == 'EVIDENCE_ONLY', m['changed'][:1])
# T04 مرحلةٌ غير منفّذة
C4 = copy.deepcopy(C); C4.status['relations'] = ('FAILED', 'injected')
try:
    D.fingerprint(C4); r = 'لم يُرفض'
except D.DumpError as e:
    r = str(e)
check('T04 مرحلةٌ فاشلة: STAGE_NOT_EXECUTED، لا تفريغ لنصّ خطأ', r.startswith('STAGE_NOT_EXECUTED'), r)
# T05 كائنٌ بلا حقول يُسلسل بعنوان ذاكرة
class Opaque:
    __slots__ = ()
try:
    D.Canon()({'x': Opaque()}); r = 'لم يُرفض'
except D.DumpError as e:
    r = str(e)
check('T05 repr بعنوان ذاكرة: IDENTITY_REPR', r.startswith('IDENTITY_REPR'), r)
class Slotted:
    __slots__ = ('a',)
    def __init__(self, a): self.a = a
check('T06 كائنٌ بـ __slots__ يُسلسل بحقوله: قيمتان مختلفتان ← بصمتان مختلفتان',
      D.js(D.Canon()(Slotted(1))) != D.js(D.Canon()(Slotted(2))))
# T07 مقابلة الجمل بالمدى
def s(span, v='X'):
    return dict(span=span, verdict=v, level='S', by_level={}, boundary={}, obligations=[], sha=D.sha(json.dumps([span, v])))
A = dict(a1=s(['1:1:1', '1:1:2', '1:1:3']), a2=s(['1:2:1', '1:2:2']), a3=s(['1:3:1']), a4=s(['1:4:1', '1:4:2', '1:4:3']), a5=s(['1:5:1']))
B = dict(b1=s(['1:1:1']), b2=s(['1:1:2', '1:1:3']), b3=s(['1:2:1', '1:2:2', '1:3:1']), b4=s(['1:4:1']), b5=s(['1:4:3']), b6=s(['1:6:1']),
         b7=s(['1:5:1'], 'Y'))
m = D.match_sentences(A, B)
check('T07 انقسامٌ تامّ (a1→b1+b2)، ودمج (a2+a3→b3)، وانقسامٌ بفجوة ليس انقساماً (a4 محذوفة، b4 وb5 مضافتان)، وتغيّر بالمدى نفسه (a5/b7)، وإضافة (b6)',
      [x['a'] for x in m['split']] == ['a1'] and [x['b'] for x in m['merge']] == ['b3'] and {x['id'] for x in m['removed']} == {'a4'}
      and {x['id'] for x in m['added']} == {'b4', 'b5', 'b6'} and [x['a'] for x in m['changed']] == ['a5'], m)
m = D.match_sentences(dict(x=s(['1:1:1']), y=s(['1:1:1'])), dict(z=s(['1:1:1'])))
check('T08 مفتاحا مدى مكرران: مرفوضان ومعلنان', m['duplicate_spans'], m)
# T09 الإرفاق لا يغيّر السياق، وضوابطه حاضرة
sc = S.attach(C)
P9, S9, T9 = D.fingerprint(C)
check('T09 الإرفاق المرشّح لا يغيّر شيئاً في السياق (كل البصمات والجمل والاستقرار)', P9 == P0 and S9 == S0 and T9 == T0)
links = [l for occ in sc['sidecar'].values() for r in occ for l in (r.get('event_side') or {}).get('links') or []]
check('T10 كل رابطٍ مرفق: CANDIDATE، وis_fact قيمةٌ منطقية false (V48C03: لا نصّ «False»)، وحكم المالك غير صادر، والدور «دلالي» لا نحوي، وقيود المطابقة محفوظة',
      len(links) > 0 and all(l['status'] == 'CANDIDATE' and l['is_fact'] is False and l.get('is_fact_raw') == 'False' and l['owner_ruling'].startswith('NONE') and 'semantic_role' in l
          and 'role' not in l and l['match_constraints']['event_id']['value'] == l['event_id'] for l in links), len(links))
check('T11 فاحص التسرّب على السياق السليم: لا أثر للروابط في منتجات المحرّك', not S.leak_scan(C, D.PRODUCTS))
# T12 إفساد: رابطٌ مرشّح يُستعمل حقيقةً في شهادة
C12 = copy.deepcopy(C)
o = C12.get('certificates')[sid]['obligations'][0]
o['satisfied_by'] = list(o.get('satisfied_by') or []) + [dict(id='HFN-AJ-4ab5fe7109', status='LICENSED', relation='AJNAS_ROLE')]
hits = S.leak_scan(C12, D.PRODUCTS)
_, S12, _ = D.fingerprint(C12)
m = D.match_sentences(S0, S12)
check('T12 رابطٌ مرشّح مُدخَلٌ سنداً في شهادة: يكشفه فاحص التسرّب، وتظهر الجملة متغيّرة السند',
      hits and hits[0][0] == 'certificates' and m['changed'] and m['changed'][0]['obligations'][0]['kind'] == 'EVIDENCE_ONLY', (hits[:1], m['changed'][:1]))
C13 = copy.deepcopy(C)
C13.get('records')[next(iter(C13.get('records')))]  # موجود
rk = next(iter(C13.get('records')))
C13.get('records')[rk] = dict(C13.get('records')[rk]) if isinstance(C13.get('records')[rk], dict) else C13.get('records')[rk]
if isinstance(C13.get('records')[rk], dict):
    C13.get('records')[rk]['__injected_relation'] = dict(type='SUBJECT', evidence='ahdath_ajnas:HFN-AJ-7d8858df4d (محلّ)')
else:
    C13.get('records')[rk].append(dict(type='SUBJECT', evidence='ahdath_ajnas:HFN-AJ-7d8858df4d (محلّ)'))
P13, _, _ = D.fingerprint(C13)
check('T13 إفساد: «محلّ» مُدخَلٌ فاعلاً نحوياً في السجلات: يكشفه فاحص التسرّب وبصمة مفتاح الآية',
      S.leak_scan(C13, ['records']) and P13['records']['keys'][rk] != P0['records']['keys'][rk])
print(f'CHECKS pass={N[0] - len(FAIL)} fail={len(FAIL)} total={N[0]}')
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
