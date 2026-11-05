#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_batch_e.py — الدفعة E من SARF_SEQUENTIAL_COMPLETION_PLAN_01: العلاقات الموسّعة والتعلّق.

A02: الترخيص وجهٌ لا اختيار، والبدائل خارج التغطية تُبقي البحث غير مكتمل ولا تُسمّي «المضيف الوحيد».
M02: المصدر المؤوَّل من «أَنْ» الناصبة والمضارع تركيبٌ مرخَّص، ووظيفته مؤجَّلة إلا بحرف جرٍّ مكتوبٍ قبله مباشرةً.
وإفسادان يكشفهما الفاحص العابر للطبقات (القاعدتان ٨ و٩).

    PYTHONHASHSEED=0 python3 -P -s tests/test_batch_e.py
"""
import copy, os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
os.environ.setdefault('SARF_QURAN', 'hafs_kfgqpc')
from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.algebra import Trace, sentence_geo, linguistic_layer
from sarf.features import unit_features
from sarf.relations import verse_relations, check_records, check_cross, check_inflection

CAT = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
FAIL = []


def verse_text(s, v):
    for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 3 and p[0] == str(s) and p[1] == str(v):
            return p[2]


def run(text, s=0, v=0, ref='t'):
    a = analyze(CAT, text, 'auto')
    S, U = sentence_geo(a, 'Q' + ref, Trace())
    C, Rl = [], []
    linguistic_layer([(s, v, a, U, S)], Trace(), 'test', cond_out=C, rel_out=Rl)
    return verse_relations(a, U, unit_features(a, U), ref, legacy_cond=C, legacy_rel=Rl)


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {got}'))
    if not cond:
        FAIL.append(name)


# ---------- A02 ----------
o = run(verse_text(2, 282), 2, 282, '2:282')
a02 = [r for r in o['records'] if r['rule_id'] == 'A02']
check('E01 A02 في 2:282 («وَٱللَّهُ بِكُلِّ شَيۡءٍ عَلِيمٞ»): الوجه مرخَّص، والاختيار مؤجَّل، والبحث غير مكتمل، والبدائل خارج التغطية مسمّاة',
      a02 and all(r['status'] == 'LICENSED' and r.get('selection') == 'DEFERRED' and r['search_status'] == 'SEARCH_INCOMPLETE'
                  and r['search_scope'].get('outside_coverage') and r.get('face_note') for r in a02), [(r['status'], r.get('selection')) for r in a02])
check('E02 A02 لا يقول «مضيفها الوحيد» بإطلاق، بل «الوحيد بين مضيفي A01»',
      all('مضيفها الوحيد' not in r['reason'] and 'بين مضيفي A01' in r['reason'] for r in a02))
m = copy.deepcopy(o)
r_ = next(r for r in m['records'] if r['rule_id'] == 'A02')
r_['selection'] = None
r_['search_status'] = 'SEARCH_COMPLETE'
check('E03 إفساد A02 (اختيارٌ وبحثٌ مكتمل مع بدائل خارج التغطية) يكشفه الفاحص العابر للطبقات (القاعدة ٨)',
      sum('خارج التغطية' in e for e in check_cross(m['records'], m['axes'])) >= 2)

# ---------- M02 ----------
ms = [r for r in o['records'] if r['type'] == 'MASDAR']
check('E04 M02 في 2:282: خمسة مصادر مؤوَّلة («أن يكتب»، «أن يملّ»، «أن تضلّ»، «أن تكتبوه»، «أن تكون») مرخَّصةٌ تركيباً',
      sorted(r['texts']['verb'] for r in ms) == sorted(['يَكْتُبَ', 'يُمِلَّ', 'تَضِلَّ', 'تَكْتُبُو', 'تَكُونَ'])
      and all(r['status'] == 'LICENSED' for r in ms), [r['texts'] for r in ms])
check('E05 M02: الوظيفة مؤجَّلة بأبوابها حيث لا حرف جرٍّ قبله، ولا يُحكم بحرف جرٍّ محذوف',
      all(r['function']['status'] == 'DEFERRED' and r['alternatives'] == ['فاعل', 'مفعول به', 'مبتدأ', 'خبر'] for r in ms))
f44 = next(r for r in o['records'] if r['type'] == 'VERB_FRAME' and r['texts'].get('verb') == 'يَسْتَطِيعُ')
q44 = f44['frame'].get('object_requirement') or {}
check('E06 «يستطيع أن يملّ»: الكاشف يحيل إلى سجلّ M02، ويبقى التعلّق بالفعل غير محلَّل («أن + الفعل» ليس شهادة تعلّق)',
      q44.get('kind') == 'UNANALYZED_COMPLEMENT' and q44.get('masdar') in {r['relation_id'] for r in ms}
      and 'غير محلَّلين' in q44['note'] and 'المكمّل موجود' not in q44['note'], q44)
o2 = run('عَجِبْتُ مِنْ أَنْ يَكْتُبَ')
m2 = [r for r in o2['records'] if r['type'] == 'MASDAR']
check('E07 M02 بحرف جرٍّ مكتوبٍ قبله مباشرةً: الوظيفة مرخَّصة (مجرورٌ محلاً) بحاكمها',
      m2 and m2[0]['function']['status'] == 'LICENSED' and m2[0]['function']['governor'] and 'مِنْ' in m2[0]['function']['text'],
      [r.get('function') for r in m2])
m = copy.deepcopy(o2)
r_ = next(r for r in m['records'] if r['type'] == 'MASDAR')
r_['function']['governor'] = None
check('E08 إفساد M02 (وظيفةٌ مرخَّصة بلا حاكمٍ مكتوب) يكشفه الفاحص العابر للطبقات (القاعدة ٩)',
      any('بلا حاكمٍ مكتوب' in e for e in check_cross(m['records'], m['axes'])))
o4 = run(verse_text(2, 27), 2, 27, '2:27')
m4 = [r for r in o4['records'] if r['type'] == 'MASDAR']
check('E11 مقابلة M02: «أَمَرَ ٱللَّهُ بِهِۦٓ أَن يُوصَلَ» — الجار قبله له مجروره («هِ»)، فالوظيفة مؤجَّلة لا مجرورٌ به',
      m4 and all(r['function']['status'] == 'DEFERRED' for r in m4), [r['function'] for r in m4])
o5 = [run(verse_text(s_, v_), s_, v_, f'{s_}:{v_}') for s_, v_ in ((5, 116), (19, 35))]
check('E12 مقابلة M02: «يَكُونُ لِيٓ أَنۡ أَقُولَ» و«مَا كَانَ لِلَّهِ أَن يَتَّخِذَ» — الجار ومجروره في وحدةٍ قبله، فلا يُجرّ به المصدر',
      all(r['function']['status'] == 'DEFERRED' for o_ in o5 for r in o_['records'] if r['type'] == 'MASDAR'))
o6 = run(verse_text(6, 37), 6, 37, '6:37')
check('E13 موجبة M02: «قَادِرٌ عَلَىٰٓ أَن يُنَزِّلَ» (6:37) — المصدر مجرورٌ محلاً بـ«عَلَى»',
      any(r['function']['status'] == 'LICENSED' and 'عَلَى' in r['function']['text'] for r in o6['records'] if r['type'] == 'MASDAR'))
o3 = run('أَنْ يَكْتُبُ')
check('E09 مقابلة M02: «أَنْ» بلا نصبٍ متّسق في المضارع (يَكْتُبُ) لا تُرخِّص مصدراً مؤوَّلاً',
      not any(r['type'] == 'MASDAR' and r['status'] == 'LICENSED' for r in o3['records']))
check('E10 الفواحص الثلاثة بلا خلل على 2:282', not check_records(o['records'], o['tokens'], o.get('parts')) and
      not check_cross(o['records'], o['axes']) and not check_inflection(o['axes']))

print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
