#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبارات حدود العطف (مواصفة صاحب النظرية): مرشّحاتٌ كاملة بشروط القبول A1–A8 وموانع R1–R7 وأسباب التأجيل D1–D9،
وقرار الموضع، والعناصر المشتركة بقراراتها المستقلة، والتداخل، وفاحص الشهادة واختباراته المضادة.

    python3 tests/test_coord.py
"""
import os, sys
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
os.chdir(H)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.algebra import Trace, sentence_geo, linguistic_layer
from sarf.coord import DECISIONS, RULES

bad = 0


def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)


cat = Catalog(['operators_catalog.jsonl', 'operators_catalog_split_vocalized.csv'])
ROWS = {(int(x[0]), int(x[1])): x[2] for x in (l.rstrip('\n').split('\t')
                                                 for l in open('data/quran_hafs.tsv', encoding='utf-8'))}


def records(refs):
    T_ = Trace()
    items = []
    for r in refs:
        a = analyze(cat, ROWS[r])
        S, u = sentence_geo(a, 'Q%d:%d' % r, T_)
        items.append((r[0], r[1], a, u, S))
    _, st, _ = linguistic_layer(items, T_, 't')
    return {R['letter_unit']: R for R in linguistic_layer.samples['coord_records']}, st


def cand(R, func='عطف', status=None):
    return next((c for c in R['candidates'] if c['function'].startswith(func) and
                 (status is None or c['status'] == status)), None)


# أ. طرفان اسميان وخبر مشترك خارجهما
R, _ = records([(55, v) for v in range(1, 6)])
r = R.get('55:5:2:1')
c = r and cand(r, status='مستوفٍ')
check('55:5 الواو في 55:5:2:1 (موضع الحرف غير موضع الكلمة)، وخلاياها من كلمتها', r and r['carrier_word'] == '55:5:2' and
      r['letter_cells'] and r['letter_cells'][0]['letter'] == 'و', r and (r['carrier_word'], r['letter_cells']))
check('55:5 مفردان: «الشمس» و«القمر»، وتثبيتٌ ضمن النطاق', c and c['A']['head'] == 'الشَّمْسُ' and c['B']['text'] == 'وَالْقَمَرُ'
      and r['decision'] == DECISIONS[0], r and r['decision'])
check('55:5 «بحسبان» خبرٌ مشترك خارج الطرفين (اشتراك مثبت)', c and any('بِحُسْبَانٍ' in s['element'] and
                                                                    s['status'] == 'اشتراك مثبت' for s in c['shared']))
check('55:5 إدخال «بحسبان» في الطرف اللاحق مرشّحٌ مرفوض بـR4', any(x['status'] == 'مرفوض' and x['B'] and
                                                               'بِحُسْبَانٍ' in x['B']['text'] and x['barriers'][0][0] == 'R4'
                                                               for x in r['candidates']))
# ب. شبه جملة على شبه جملة
R, _ = records([(80, 31), (80, 32)])
r = R.get('80:32:3:1')
c = r and cand(r, status='مستوفٍ')
check('80:32 «لكم» و«لأنعامكم»: شبه جملة على شبه جملة', c and c['level'] == 'شبه جملة' and c['A']['head'] == 'لَّكُمْ',
      r and [(x['level'], x['status']) for x in r['candidates']])
# جمل
R, _ = records([(80, 21)])
r = R.get('80:21:3:1')
c = r and cand(r, status='مستوفٍ')
check('80:21 «أماته» و«فأقبره» جملتان، والوظيفة بين العطف والاستئناف محفوظةٌ (D1) مع ترجيح العطف',
      c and c['level'] == 'جملة' and c['A']['head'] == 'أَمَاتَهُ' and r['decision'] == DECISIONS[1] and
      'D1' in r['decision_codes'] and r['preferred'] and r['preferred'][0] == c['id'], r and (r['decision'], r['preferred']))
check('80:21 «ثُمَّ» أول النص المقروء: تأجيل D7 لنقص السياق لا رفض', R.get('80:21:1:1', {}).get('decision') == DECISIONS[4]
      and 'D7' in R['80:21:1:1']['decision_codes'])
# ج. الرأس لا يساوي الامتداد، والأقرب ليس بالضرورة الطرف
R, _ = records([(2, v) for v in range(1, 6)])
r = R.get('2:4:6:1')
c = r and cand(r, status='مستوفٍ')
check('2:4 الرأس السابق «ما» في 2:4:3، وامتداده «ما أُنزل إليك» بلا الباء', c and c['A']['head_id'] == '2:4:3' and
      c['A']['text'] == 'بِمَا أُنْزِلَ إِلَيْكَ' and '2:4:3:1' not in c['A']['units'], c and (c['A']['text'], c['A']['units']))
check('2:4 الرأس اللاحق «ما» في 2:4:6، وامتداده «وما أُنزل من قبلك»', c and c['B']['head_id'] == '2:4:6' and
      c['B']['text'] == 'وَمَا أُنْزِلَ مِنْ قَبْلِكَ', c and c['B']['text'])
check('2:4 الباء عاملٌ مشترك خارج امتداد الموصول الأول', c and any(s['element'].startswith('الجارّ «بِ»') and
                                                                   s['status'] == 'اشتراك مثبت' for s in c['shared']))
check('2:4 «إليك» مرشّح القرب مرفوض بمانعٍ مثبت', any(x['A'] and x['A']['head'] == 'إِلَيْكَ' and x['status'] == 'مرفوض'
                                                    for x in r['candidates']))
r = R.get('2:4:10:1')
check('2:4 «وبالآخرة هم يوقنون» معطوفةٌ داخل الصلة، والاستئناف مرفوض بـR3 (لا يُقطع الحاوي)',
      r and r['decision'] == DECISIONS[0] and any(x['function'] == 'استئناف' and x['barriers'][0][0] == 'R3'
                                                  for x in r['candidates']))
r = R.get('2:4:6:1')
check('2:4 العطف المفرد داخل طرف العطف الجملي (تداخل، لا سلسلة مسطّحة)', r and r.get('inside', {}).get('of') == '2:4:10:1')
# د. أم المتصلة واختلاف الصيغة
R, _ = records([(2, 6)])
r = R.get('2:6:7:1')
c = r and cand(r, status='مستوفٍ')
check('2:6 «أأنذرتهم أم لم تنذرهم»: المتصلة مثبتة والمنقطعة مرفوضة بعد التسوية', c and r['decision'] == DECISIONS[0] and
      c['B']['text'] == 'أَمْ لَمْ تُنْذِرْهُمْ' and any(x['function'].startswith('«أم» المنقطعة') and x['status'] == 'مرفوض'
                                                     for x in r['candidates']), c and c['B']['text'])
check('2:6 «سواء عليهم» مشتركٌ خارج المتعادلين', c and any('سَوَاءٌ' in s['element'] for s in c['shared']))
# هـ. واو الحال
R, _ = records([(2, 259)])
r = R.get('2:259:6:1')
check('2:259 «وهي خاوية»: الحال والعطف والاستئناف محفوظة، والحال مرجَّحة، والنطاق لا يبلغ «قال»',
      r and r['decision'] == DECISIONS[1] and r['preferred'] and 'حال' in next(x['function'] for x in r['candidates']
                                                                                 if x['id'] == r['preferred'][0]) and
      cand(r)['B']['text'] == 'وَهِيَ خَاوِيَةٌ عَلَى عُرُوشِهَا', r and (r['decision'], cand(r)['B']['text']))
check('2:259 «ولنجعلك»: معطوفٌ على تعليلٍ مقدَّر — تأجيل D6 بلا إنشاء كلمةٍ مقدَّرة',
      R.get('2:259:46:1', {}).get('decision_codes') == ['D6'])
check('2:259 «بل لبثت»: «بل» حرف ابتداء، والعطف مرفوض', R.get('2:259:33:1', {}).get('decision') == DECISIONS[0] and
      cand(R['2:259:33:1'], 'حرف ابتداء')['status'] == 'مستوفٍ')
# و. القسم والعطف عبر حدّ الآية
R, _ = records([(91, 1), (91, 2)])
r1, r2 = R.get('91:1:1:1'), R.get('91:2:1:1')
check('91:1 «والشمس» قسمٌ أول السورة، والعطف مرفوض (لا طرف سابق)', r1 and r1['decision'] == DECISIONS[0] and
      cand(r1, 'قسم')['status'] == 'مستوفٍ', r1 and r1['decision'])
check('91:2 «والقمر» معطوفٌ على «والشمس» عبر حدّ الآية', r2 and cand(r2, status='مستوفٍ')['A']['head'] == 'وَالشَّمْسِ')
r = R.get('91:1:2:1')
check('91:1 «وضحاها» (مقصورٌ قبل الضمير): مرشّحه «الشمس»، ويؤجَّل لنقص دليل اسمية «ضحى» في المعجم (D8) لا يُرفض',
      r and cand(r)['A']['head'] == 'وَالشَّمْسِ' and r['decision_codes'] == ['D8'] and 'وَضُحَىهَا' in
      cand(r)['deferrals'][0][1], r and (cand(r)['A'], cand(r)['deferrals']))
# ز. الاستئناف محتمل لا مفروض
R, _ = records([(12, 15), (12, 16)])
r = R.get('12:16:1:1')
check('12:16 «وجاءوا»: العطف والاستئناف مستوفيان، فيُحفظان ويؤجَّل الانفراد (D1)', r and r['decision'] == DECISIONS[1] and
      {x['function'] for x in r['candidates']} >= {'عطف', 'استئناف'})
# ح. العطف لا يغلق الصلة
R, st = records([(2, 25)])
r = R.get('2:25:4:1')
c = r and cand(r, status='مستوفٍ')
check('2:25 «الذين [آمنوا و[عملوا الصالحات]]»: العطف داخل الصلة، و«الصالحات» في الطرف', c and
      c['container'] and c['container'].startswith('صلة') and c['B']['text'] == 'وَعَمِلُوا الصَّٰلِحَٰتِ', c and c['B'])
check('2:25 الاستئناف يقطع الصلة: مرفوض بـR3، ولا يُغلق التركيب الحاوي باكتمال العطف',
      any(x['function'] == 'استئناف' and x['barriers'] and x['barriers'][0][0] == 'R3' for x in r['candidates']) and
      'لا يُحكم به' in r['closure']['Close_P'], r['closure'])
# الفاحص والاختبارات المضادة
check('الفاحص: كل السجلات سليمة', not st.get('coordcheck:مرفوض'), st.get('coordcheck:مرفوض'))
check('الاختبارات المضادة: كُشف أكثرها', st.get('coordmut:كُشف', 0) >= 0.9 * st.get('coordmut:حالات', 1),
      (st.get('coordmut:كُشف'), st.get('coordmut:حالات')))
check('كل قاعدةٍ مستعملة مسجَّلةٌ بحقولها', all(set(RULES[x]) >= {'id', 'version', 'scope', 'conditions', 'barriers',
                                                                  'witness', 'counter', 'coverage'} for x in RULES))
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
