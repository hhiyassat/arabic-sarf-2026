#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_batch_f.py — الدفعة F من SARF_SEQUENTIAL_COMPLETION_PLAN_01: الجملة تستهلك علاقات 14أ بشهادة إغلاقٍ موحَّدة.

كل التزامٍ مستوفى يسمّي العلاقة التي استوفته (أو دليل الطبقة القديمة)، وما استوفته الطبقة القديمة وأجّلته 14أ لا يُعدّ مستوفى،
و«مغلقة ومصالَحة» لا تكون مع مفتوحٍ في 14أ داخل المدى. وإفسادٌ يجب أن يغيّر الحكم.

    PYTHONHASHSEED=0 python3 -P -s tests/test_batch_f.py
"""
import copy, os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
os.environ.setdefault('SARF_QURAN', 'hafs_kfgqpc')
from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.algebra import Trace, sentence_geo, linguistic_layer, closure_certificate
from sarf.features import unit_features
from sarf.relations import verse_relations

CAT = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
FAIL = []


def verse_text(s, v):
    for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 3 and p[0] == str(s) and p[1] == str(v):
            return p[2]


def certs(s, v):
    a = analyze(CAT, verse_text(s, v), 'auto')
    S, U = sentence_geo(a, f'Q{s}:{v}', Trace())
    C, Rl = [], []
    LT, _, _ = linguistic_layer([(s, v, a, U, S)], Trace(), 'test', cond_out=C, rel_out=Rl)
    o = verse_relations(a, U, unit_features(a, U), f'{s}:{v}', legacy_cond=C, legacy_rel=Rl)
    Js = [J for SP in LT for D in SP.A + SP.O.get('pending', []) for J in D.A + D.O.get('pending', [])]
    return o, Js, [closure_certificate(J, o['records']) for J in Js]


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {got}'))
    if not cond:
        FAIL.append(name)


o, Js, C = certs(2, 282)
ids = {r['relation_id']: r for r in o['records']}
obs = [ob for c in C for ob in c['obligations']]
check('F01 (v2) كل التزامٍ مستوفى يسمّي ما استوفاه: معرّف علاقةٍ موجودةٍ مرخَّصة في 14أ ودليلها، أو دليل الطبقة القديمة موسوماً LEGACY',
      all((ob['discharge_relation_id'] in ids and ob['discharge_evidence_id'] and
           (ids[ob['discharge_relation_id']]['status'] == 'LICENSED' or ob['status'] == 'MET_IN_ALL_FACES' and
            ((ids[ob['discharge_relation_id']].get('frame') or {}).get('subject') or {}).get('status') == 'LICENSED'))
          if ob.get('discharge_relation_id') else all(x['status'] in ('LEGACY', 'LICENSED') for x in ob['satisfied_by'] or [{'status': None}])
          for ob in obs if ob['met']),
      [ob['obligation_id'] for ob in obs if ob['met'] and not ob.get('discharge_relation_id') and not ob['satisfied_by']])
w = next(ob for ob in obs if ob['name'] == 'فاعل «وَلْيُمْلِلِ»' or ob['name'] == 'فاعل «يُمْلِلِ»')
check('F02 «وليملل الذي»: الطبقة القديمة تستوفي الفاعل و14أ تؤجّله، فالالتزام غير مستوفى والحكمان معروضان',
      w['legacy_met'] and not w['met'] and 'تؤجّله' in w['note'] and w['candidates'], w)
k = [ob for ob in obs if ob['name'].startswith('فاعل «يَكْتُبْ»') and ob['source'] == '14أ']
check('F03 «وليكتب بينكم كاتب»: الفاعل مستوفى في 14أ بمعرّف S01', k and 'SUBJECT:S01' in k[0]['satisfied_by'][0]['relation'], k)
check('F04 (v2) لا «مغلقة» مع التزامٍ لازمٍ غير مستوفى، ولا «مغلقة في وجهها» مع باقٍ في 14أ داخل المدى',
      all(not (c['verdict'] in ('CLOSED_IN_FACE', 'CLOSED_WITH_SHARED_STRUCTURE') and any(ob['required'] and not ob['met'] for ob in c['obligations']))
          and not (c['verdict'] == 'CLOSED_IN_FACE' and c['residuals']) for c in C))
closed = [(J, c) for J, c in zip(Js, C) if J.closed]
check('F05 (v2) الجملة المغلقة في الطبقة القديمة وفي مداها اختيارٌ مؤجَّل في 14أ: «مغلقة بالبنية المشتركة» لا «مغلقة في وجهها»؛ '
      'والمؤجَّل في المدى لا يصير التزاماً لازماً تلقائياً (SARF_MAJOR_CLOSURE_01 §7)',
      closed and all(c['verdict'] != 'CLOSED_IN_FACE' for _, c in closed if c['residuals']) and
      all(c['verdict'] == 'CLOSED_WITH_SHARED_STRUCTURE' for _, c in closed if c['residuals'] and all(x['kind'] == 'SELECTION' for x in c['residuals'])),
      [(c['sentence'], c['verdict'], len(c['residuals'])) for _, c in closed])
# إفساد: علاقةٌ مرخَّصة تُنزَّل إلى مؤجَّلة داخل مدى جملةٍ مصالَحة أو مستوفاة ← يتغيّر الحكم أو الاستيفاء
J0, c0 = next(((J, c) for J, c in zip(Js, C) for ob in c['obligations'] if ob['source'] == '14أ'), (None, None))
rid = next(ob['satisfied_by'][0]['relation'] for ob in c0['obligations'] if ob['source'] == '14أ')
m = copy.deepcopy(o['records'])
next(r for r in m if r['relation_id'] == rid)['status'] = 'DEFERRED'
c1 = closure_certificate(J0, m)
ob1 = next(ob for ob in c1['obligations'] if any(x['relation'] == rid for x in (ob['candidates'] or [])))
check('F06 إفساد: تنزيل العلاقة المستوفية إلى مؤجَّلة يُسقط الاستيفاء ويُدخلها في المفتوح', (not ob1['met'] or ob1['source'] != '14أ')
      and any(x['relation'] == rid for x in c1['relation_open']), ob1)

print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
