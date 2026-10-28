#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار السجل الجامع (sarf.output_schema): كل آية في ملفات الآيات صالحة بالمخطَّط
schema/morph_analysis.schema.json، وأحكام بعينها كما ينبغي.

    python3 tests/test_schema.py
"""
import glob, json, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from sarf.analyze import analyze
from sarf.catalog import Catalog
from sarf.output_schema import to_schema
from schema_check import Validator

CAT = Catalog([os.path.join(HERE, 'operators_catalog.jsonl'),
               os.path.join(HERE, 'operators_catalog_split_vocalized.csv')])
V = Validator(os.path.join(HERE, 'schema', 'morph_analysis.schema.json'))

bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

# 1. الصلاحية: كل آية في ملفات الآيات، وأمثلة المخطَّط اليدوية
for fn in sorted(glob.glob(os.path.join(HERE, 'verses*.txt'))):
    for v in open(fn, encoding='utf-8'):
        if v.strip():
            e = V.errors(json.loads(json.dumps(to_schema(analyze(CAT, v.strip()), CAT), ensure_ascii=False)))
            check(f'صالح: {v.strip()[:40]}', not e, e[:2])
for fn in sorted(glob.glob(os.path.join(HERE, 'schema', 'examples', '*.json'))):
    check(f'مثال 1.0: {os.path.basename(fn)}', not V.errors(json.load(open(fn))))


def first(text, wi):
    d = to_schema(analyze(CAT, text), CAT)
    return d, d['tokens'][wi]['analyses'][0]

# 2. أحكام بعينها
d, an = first('لَمْ يَلِدْ', 1)
v = an['segments'][0]['verb']
check('يَلِدْ: مضارع مجزوم بالسكون للغائب', (v['tense'], v['inflection'].get('mood'), v['subject']['person']) ==
      ('imperfect', 'jussive', 3), v)
check('لم ← يلد: مقبول ومتسق', d['dependencies'][0]['consistent'] is True)
d, an = first('لَيْسَ كَمِثْلِهِۦ شَىْءٌ', 1)
segs = an['segments']
check('كَمِثْلِهِ: كاف جارّة، ومثل اسم مجرور، والهاء ضمير مضاف إليه',
      (segs[0]['pos'], segs[0]['particle']['effect'], segs[1]['noun']['inflection'].get('case'),
       segs[2]['pronoun'].get('function')) == ('particle', 'jarr', 'gen', 'possessive'), segs)
d, an = first('فَإِنَّمَا', 0)
check('إِنَّمَا: «ما» الكافة لاحقة وإنّ مكفوفة',
      [s['role'] for s in an['segments']] == ['proclitic', 'stem', 'suffix'] and
      an['segments'][1]['particle'].get('kaffa') is True, an['segments'])
d, an = first('لَا تَحْزَنْ', 1)
check('تَحْزَنْ: إسنادان (أنتَ، هي) لا تفصل الكتابة بينهما',
      len(d['tokens'][1]['analyses']) == 2 and an['segments'][0]['verb']['inflection'].get('mood') == 'jussive',
      d['tokens'][1]['analyses'])
d, an = first('وَيۡلࣱ لِّلۡمُطَفِّفِينَ', 1)
check('لِّلۡمُطَفِّفِينَ: لام جر، ولام أل، واسم مجرور بالياء',
      [s.get('clitic_type') for s in an['segments'][:2]] == ['preposition', 'definite_article'] and
      an['segments'][2]['noun']['inflection'] .get('marker') == 'ya' and
      an['segments'][2]['noun']['inflection'].get('case') == 'gen', an['segments'])
d, _ = first('وَيۡلࣱ لِّلۡمُطَفِّفِينَ', 0)
rej = [a for a in d['tokens'][0]['analyses'] if a['status'] == 'rejected']
check('وَيۡلٌ: الواو الجارّة ممنوعة ومعها سببها', rej and 'ساكن' in rej[0]['evidence'][0]['note'], rej)
d, an = first('يَعۡمَلۡ مِثۡقَالَ', 1)
check('مِثۡقَالَ: لا دليل على نوعه بالكتابة ← undetermined', an['segments'][0]['pos'] == 'undetermined',
      an['segments'][0])
d, _ = first('ٱلْحَمْدُ لِلَّهِ', 1)
check('لِلَّهِ: لفظ الجلالة بلا مقاطع', 'syllables' not in d['tokens'][1] and
      d['tokens'][1]['fixed_lexeme']['kind'] == 'divine_name')
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
