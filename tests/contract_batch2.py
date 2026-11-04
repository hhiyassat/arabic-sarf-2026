#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/contract_batch2.py — عقد الدفعة الثانية من خطة SARF_006_REPAIR_AND_COMPLETION_PLAN_01: الإسناد الفعلي ومعمولاته.

ليس بوّابة نجاح: لكل بندٍ من العقد حالةٌ مقيسة على الشيفرة الحالية — MET (مستوفى بشاهده)، أو PENDING (مطلوبٌ في الدفعة الثانية).
والدفعة الثانية تُعدّ مكتملةً في نطاقها إذا صارت بنودها كلها MET مع بقاء tests/test_round006.py ناجحاً، وبلا تراجعٍ مقيس.
والمدخل مصحف المجمّع وHFN v18، ولا تُمرَّر القيم المتوقعة إلى المحلّل.

    PYTHONHASHSEED=0 python3 -P -s tests/contract_batch2.py [--json out.json]
"""
import json, os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.algebra import Trace, sentence_geo, linguistic_layer
from sarf.features import unit_features
from sarf.relations import verse_relations

CAT = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
OUT = []


def verse(s, v):
    for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 3 and p[0] == str(s) and p[1] == str(v):
            return p[2]


def run(s, v):
    a = analyze(CAT, verse(s, v), 'auto')
    S, U = sentence_geo(a, f'Q{s}:{v}', Trace())
    C, Rl = [], []
    linguistic_layer([(s, v, a, U, S)], Trace(), 'contract', cond_out=C, rel_out=Rl)
    return verse_relations(a, U, unit_features(a, U), f'{s}:{v}', legacy_cond=C, legacy_rel=Rl)


def uid(o, loc, text):
    return next(u for u, l, t in o['tokens'] if l == loc and t == text)


def item(code, text, met, evidence):
    OUT.append(dict(code=code, item=text, status='MET' if met else 'PENDING', evidence=str(evidence)[:300]))
    print(f"{'MET    ' if met else 'PENDING'} {code} {text}")


o = run(2, 282)
subj = {r['heads'].get('subject'): r for r in o['records'] if r['type'] == 'SUBJECT' and r['status'] == 'LICENSED'}
frames = {r['heads']['verb']: r for r in o['records'] if r['type'] == 'VERB_FRAME'}

item('B2.01', '«كاتب» فاعل «يكتب» (13) و«يأب» (17)', uid(o, '2:282:13', 'كَاتِبٌ') in subj and uid(o, '2:282:17', 'كَاتِبٌ') in subj, '')
u25 = uid(o, '2:282:25', 'الَّذِي')
item('B2.02', '«الذي» فاعل «وليملل» (24) بقاعدة الفاعل المبني (محلّه رفع)، لا مرشّحاً مؤجَّلاً', u25 in subj,
     [r['status'] for r in o['records'] if r['type'] == 'SUBJECT' and u25 in sum(r['members'].values(), [])])
u50 = next((u for u, l, t in o['tokens'] if l == '2:282:50' and t.startswith('وَلِيُّ')), None)
item('B2.03', '«وليّه» فاعل «فليملل» (49): الصنف والتقطيع ثم الفاعل', u50 in subj, o['axes'].get(u50, {}).get('word_class'))
u68 = next((u for u, l, t in o['tokens'] if l == '2:282:68' and t == 'إِحْدَى'), None)
u70 = next((u for u, l, t in o['tokens'] if l == '2:282:70' and t == 'إِحْدَى'), None)
item('B2.04', '«إحدى» فاعل «تضل» (67) و«تذكر» (69)', u68 in subj and u70 in subj, o['axes'].get(u68, {}).get('word_class'))
objs = {(r['texts'].get('verb'), r['texts'].get('object')) for r in o['records'] if r['type'] == 'OBJECT' and r['status'] == 'LICENSED'}
want = {('اكْتُبُو', 'هُ'), ('عَلَّمَ', 'هُ'), ('تَكْتُبُو', 'هُ'), ('تُدِيرُونَ', 'هَا'), ('تَكْتُبُو', 'هَا'), ('يُعَلِّمُ', 'كُمُ')}
item('B2.05', 'ضمائر المفعول الستة (فاكتبوه، علّمه، تكتبوه، تديرونها، تكتبوها، يعلّمكم)', want <= objs, sorted(want - objs))
f77 = frames[uid(o, '2:282:77', 'دُعُوا')]['frame']
c1 = next((c for c in f77['candidates'] if c['voice'] == 'مجهول'), None)
item('B2.06', '«دُعُوا»: الماضي المبني للمجهول مرشّحٌ كامل مترابط (زمن، بناء، ضمير، نائب فاعل، تحقيق، جذر)', bool(c1 and c1['roots'] and c1['realization']), c1)
item('B2.07', '«دُعُوا»: حسم التحليل بدليلٍ غير ترتيب المرشّحات ولا إطار الشرط', frames[uid(o, '2:282:77', 'دُعُوا')]['selected_analysis'] is not None, 'selected_analysis=None')
f36 = frames[uid(o, '2:282:36', 'كَانَ')]['frame']
f58 = frames[uid(o, '2:282:58', 'يَكُونَا')]['frame']
item('B2.08', 'أسماء النواسخ وأخبارها لا تُخلط بفاعل التامّ («كان» V01، و«يكونا» غير محسوم)', f36['subject_requirement'] == 'اسم الناسخ' and
     f58['subject']['role'] == 'اسم الناسخ أو فاعل التامّ', (f36['subject'], f58['subject']))
item('B2.09', '«يكونا»: حسم الاستعمال (ناقص بخبر «رجلين» أو تامّ) بقاعدة', f58['subject']['status'] == 'LICENSED', f58['open'])
open_trans = [r['texts']['verb'] for r in o['records'] if r['type'] == 'VERB_FRAME' and any('المفعول به غير مربوط' in x for x in r['frame']['open'])]
item('B2.10', 'غياب المفعول الظاهر لا يُسجَّل التزاماً مفتوحاً لكل متعدٍّ: يُفحص الاستعمال وجواز الحذف', not open_trans, open_trans)
mixed = [r['texts']['verb'] for r in o['records'] if r['type'] == 'VERB_FRAME' and r['status'] == 'LICENSED' and
         any('مرشّح' in str(p) for p in r['premises'])]
item('B2.11', 'لا إطار متّسق يجمع سماتٍ من مرشّحاتٍ مختلفة', not mixed, mixed)
item('B2.12', 'الضمير المستتر عقدةٌ مستدلّ عليها بلا خلايا مكتوبة', all(not (r['frame'].get('subject') or {}).get('unit') for r in o['records']
                                                                  if r['type'] == 'VERB_FRAME' and 'مستتر' in str((r['frame'].get('subject') or {}).get('kind'))), '')
o2 = run(2, 255)
o3 = run(19, 20)
s3 = [r for r in o3['records'] if r['type'] == 'SUBJECT' and r['status'] == 'LICENSED']
item('B2.13', 'لا يُختار أقرب مرفوع عابراً فعلاً آخر (19:20)', not any(r['texts'].get('subject') == 'غُلَٰمٌ' and r['texts'].get('verb') == 'قَالَتْ' for r in s3),
     [(r['texts']) for r in s3])
item('B2.14', 'المفعول الظاهر المعرفة المنصوب بعد متعدٍّ مثبت (O02) يظهر في المصحف بشاهدٍ واحدٍ على الأقل', any(
    r['type'] == 'OBJECT' and r['rule_id'] == 'O02' and r['status'] == 'LICENSED' for oo in (o, o2) for r in oo['records']),
    'O02 LICENSED = 0 في القياس الأخير')
if '--json' in sys.argv:
    json.dump(OUT, open(sys.argv[sys.argv.index('--json') + 1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"MET {sum(x['status'] == 'MET' for x in OUT)} / {len(OUT)}")
