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
check('55:5 مفردان: «الشمس» و«القمر»، وتثبيتٌ ضمن النطاق', c and c['A']['head'] == 'الشَّمْسُ' and
      c['B']['envelope_text'] == 'وَالْقَمَرُ' and '55:5:2:1' not in c['B']['units']
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
check('80:21 «أماته» و«فأقبره» جملتان: العطف مرخَّص، والاستئناف مؤجَّل بلا قاعدةٍ إيجابية (D8)، فالحسم مؤجَّل',
      c and c['level'] == 'جملة' and c['A']['head'] == 'أَمَاتَهُ' and r['decision'] == DECISIONS[2] and
      any(x['function'] == 'استئناف' and x['deferrals'][0][0] == 'D8' for x in r['candidates']),
      r and (r['decision'], r['preferred']))
check('80:21 «ثُمَّ» أول النص المقروء: تأجيل D7 لنقص السياق لا رفض', R.get('80:21:1:1', {}).get('decision') == DECISIONS[4]
      and 'D7' in R['80:21:1:1']['decision_codes'])
# ج. الرأس لا يساوي الامتداد، والأقرب ليس بالضرورة الطرف
R, _ = records([(2, v) for v in range(1, 6)])
r = R.get('2:4:6:1')
c = r and cand(r, status='مستوفٍ')
check('2:4 الرأس السابق «ما» في 2:4:3، وامتداده «ما أُنزل إليك» بلا الباء', c and c['A']['head_id'] == '2:4:3' and
      c['A']['text'] == 'مَا أُنْزِلَ إِلَيْكَ' and c['A']['envelope_text'] == 'بِمَا أُنْزِلَ إِلَيْكَ' and
      '2:4:3:1' not in c['A']['units'], c and (c['A']['text'], c['A']['units']))
check('2:4 الرأس اللاحق «ما» في 2:4:6، وامتداده «وما أُنزل من قبلك»', c and c['B']['head_id'] == '2:4:6' and
      c['B']['text'] == 'مَا أُنْزِلَ مِنْ قَبْلِكَ', c and c['B']['text'])
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
      c['B']['envelope_text'] == 'أَمْ لَمْ تُنْذِرْهُمْ' and any(x['function'].startswith('«أم» المنقطعة') and x['status'] == 'مرفوض'
                                                     for x in r['candidates']), c and c['B']['text'])
check('2:6 «سواء عليهم» مشتركٌ خارج المتعادلين', c and any('سَوَاءٌ' in s['element'] for s in c['shared']))
# هـ. واو الحال
R, _ = records([(2, 259)])
r = R.get('2:259:6:1')
check('2:259 «وهي خاوية»: الحال والعطف والاستئناف محفوظة، والحال مرجَّحة، والنطاق لا يبلغ «قال»',
      r and r['decision'] == DECISIONS[1] and r['preferred'] and 'حال' in next(x['function'] for x in r['candidates']
                                                                                 if x['id'] == r['preferred'][0]) and
      cand(r)['B']['envelope_text'] == 'وَهِيَ خَاوِيَةٌ عَلَى عُرُوشِهَا', r and (r['decision'], cand(r)['B']['text']))
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
c = r and next((x for x in r['candidates'] if x['function'] == 'عطف' and x['A']), None)
check('2:25 «الذين [آمنوا و[عملوا الصالحات]]»: العطف داخل الصلة مرخَّص الربط، و«الصالحات» في الطرف', c and
      c['LinkLicensed'] and c['container'] and c['container'].startswith('صلة') and
      c['B']['text'] == 'عَمِلُوا الصَّٰلِحَٰتِ', c and c['B'])
check('2:25 نطاق الصلة بلا دليلٍ مستقل (الموصول مفعولٌ لا مبتدأ): الصلة والاستئناف مؤجَّلان D3، فلا تثبيت ولا حدّ ثابت قبل الواو',
      not r['UniqueWithin'] and any(d[0] == 'D3' for d in c['deferrals']) and
      any(x['function'] == 'استئناف' and x['deferrals'] and x['deferrals'][0][0] == 'D3' for x in r['candidates']) and
      'لا يُحكم به' in r['closure']['Close_P'], r and (r['decision'], c and c['deferrals']))
# مراجعة التقرير وملفات الجمل السادسة: الرأس، والحاوي، والمستوى، وحالة العلاقة
def units_J(refs):
    T_ = Trace()
    items = []
    for r in refs:
        a = analyze(cat, ROWS[r])
        S, u = sentence_geo(a, 'Q%d:%d' % r, T_)
        items.append((r[0], r[1], a, u, S))
    LT, _, _ = linguistic_layer(items, T_, 't')
    return {R['letter_unit']: R for R in linguistic_layer.samples['coord_records']}, \
        [J for SP in LT for D in SP.A + SP.O.get('pending', []) for J in D.A + D.O.get('pending', [])]
R, Js = units_J([(12, v) for v in range(13, 17)])
r = R.get('12:16:1:1')
check('12:16 رأس «وجاءوا أباهم عشاءً يبكون» هو «جاءوا» لا «يبكون» (يبكون حالٌ في داخله)',
      r and all(x['B']['head'] == 'وَجَاءُو' for x in r['candidates'] if x['B']), r and [x['B']['head'] for x in r['candidates']])
check('12:16 جواب «لمّا» غير مثبت: لا يُرفض الاستئناف بحاوٍ مرشَّح، وتتعدّد رؤوس السابق (D2)',
      r and not any(b[0] == 'R3' for x in r['candidates'] for b in x['barriers']) and 'D2' in r['decision_codes'],
      r and (r['decision_codes'], [x['barriers'] for x in r['candidates']]))
check('12:13–16 العلاقات المرشّحة («ذهبوا» شرط «لمّا»…) تحمل حالتها، ولا تُغلق وحدتها',
      any(b[2] == 'مرشّحة' for J in Js for b in (J.O.get('bound') or [])) and not any(J.closed for J in Js if
                                                                                   any(b[2] == 'مرشّحة' for b in (J.O.get('bound') or []))))
R, Js = units_J([(74, v) for v in range(8, 12)])
r = R.get('74:11:2:1')
check('74:11 «ومن خلقت وحيدًا»: «من» موصولٌ مرشّحٌ معطوفًا على ياء «ذرني» مفردًا، ومنافسه الجملة؛ فالمستوى مؤجَّل (D4)',
      r and any(x['level'] == 'مفرد' and x['A'] and x['A']['head_id'] == '74:11:1' for x in r['candidates']) and
      'D4' in r['decision_codes'], r and r['decision_codes'])
check('74:11 الوحدة ليست مستوفاةً محليًا: علاقة «خلقت» مرشّحة غير محسومة',
      not any(J.closed and any('خَلَقْتُ' in b[0] for b in (J.O.get('bound') or [])) for J in Js))
R, Js = units_J([(64, 4)])
r = R.get('64:4:9:1')
check('64:4 «وما تعلنون»: «ما» موصولةٌ معطوفة على «ما تسرّون» (مفرد) مرشّحٌ منافسٌ للجملة (D4)، ولا استيفاء محلي',
      r and any(x['level'] == 'مفرد' and x['A'] and x['A']['head_id'] == '64:4:7' for x in r['candidates']) and
      'D4' in r['decision_codes'] and not any(J.closed and J.O.get('bound') for J in Js), r and r['decision_codes'])
R, Js = units_J([(2, 84)])
r = R.get('2:84:14:1')
check('2:84 «وأنتم تشهدون»: الحال مرشّحٌ مستوفٍ منافسٌ للعطف، فلا تثبيت ولا استيفاء محلي',
      r and any(x['function'].startswith('حال') and x['status'] == 'مستوفٍ' for x in r['candidates']) and
      not r['UniqueWithin'] and not any(J.closed and any('تَشْهَدُونَ' in b[0] for b in (J.O.get('bound') or [])) for J in Js))
R, Js = units_J([(8, 20)])
r = R.get('8:20:10:1')
check('8:20 «وأنتم تسمعون»: الحال مرشّحٌ مستوفٍ (الطرف السابق «لا تولّوا» فعلٌ بصورته)',
      r and any(x['function'].startswith('حال') and x['status'] == 'مستوفٍ' for x in r['candidates']))
# الفاحص والاختبارات المضادة
check('الفاحص: كل السجلات سليمة', not st.get('coordcheck:مرفوض'), st.get('coordcheck:مرفوض'))
check('الاختبارات المضادة: كُشف أكثرها', st.get('coordmut:كُشف', 0) >= 0.9 * st.get('coordmut:حالات', 1),
      (st.get('coordmut:كُشف'), st.get('coordmut:حالات')))
check('كل قاعدةٍ مستعملة مسجَّلةٌ بحقولها', all(set(RULES[x]) >= {'id', 'version', 'scope', 'conditions', 'barriers',
                                                                  'witness', 'counter', 'coverage'} for x in RULES))
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
