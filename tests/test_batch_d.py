#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_batch_d.py — الدفعة D من SARF_SEQUENTIAL_COMPLETION_PLAN_01: الإسناد ومعمولاته.

المشترك المثبت بين أوجه ضمير الصيغة يُحفظ: إذا كان الفاعل في كل الأوجه الضميرَ المتصل المكتوب (واو الجماعة)، والمختلف الشخص
وحده، فالإسناد مرخَّص والشخص مؤجَّل. وإذا اختلف نوع الفاعل بين الأوجه (مستترٌ في وجه، وظاهرٌ مرشّح في آخر) بقي مؤجَّلاً.

    PYTHONHASHSEED=0 python3 -P -s tests/test_batch_d.py
"""
import os, sys

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


def run(s, v):
    a = analyze(CAT, verse_text(s, v), 'auto')
    S, U = sentence_geo(a, f'Q{s}:{v}', Trace())
    C, Rl = [], []
    linguistic_layer([(s, v, a, U, S)], Trace(), 'test', cond_out=C, rel_out=Rl)
    return verse_relations(a, U, unit_features(a, U), f'{s}:{v}', legacy_cond=C, legacy_rel=Rl)


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {got}'))
    if not cond:
        FAIL.append(name)


o = run(2, 282)
fr = {r['texts']['verb']: r['frame'] for r in o['records'] if r['type'] == 'VERB_FRAME'}
s3 = fr['ءَامَنُوا']['subject']
check('D01 «ءَامَنُوا»: الزمن مرشّح (ماضٍ أو أمر)، والفاعل في الوجهين واو الجماعة المكتوبة: الإسناد مرخَّص والشخص مؤجَّل',
      s3['status'] == 'LICENSED' and s3['kind'] == 'ضمير متصل مكتوب' and 'الشخص وحده' in s3['why'], s3)
s67 = fr['تَضِلَّ']['subject']
f67 = {x['signature']['person']: x for x in s67.get('subject_faces') or []}
check('D02 مقابلة: «تَضِلَّ» يختلف فاعله بين الوجهين (مستترٌ وجوباً للمخاطب مرخَّصٌ في وجهه؛ وللغائبة مؤجَّلٌ بصنف «إحدى»): '
      'الحكم مؤجَّل، والأوجه بهويات (عُدّل لعقد SARF_MUDARI_AGREEMENT_AND_ISNAD_01: الأوجه سجلّاتٌ لا نصّ)',
      s67['status'] == 'DEFERRED' and f67[2]['status'] == 'LICENSED' and 'وجوباً' in f67[2]['kind'] and f67[3]['status'] == 'DEFERRED'
      and f67[3]['blocked_by'] == 'NOUN_CLASS_UNRESOLVED' and 'غائب، مفرد، مؤنث' in s67['why'], s67)
check('D03 لا يُقال «مستترٌ وجوباً» لوجهٍ في الجمع أو المثنى: الواو والألف ضميران مكتوبان',
      not any('جمع، مذكر: فاعله مستترٌ' in f_['subject']['why'] or 'مثنى، مذكر: فاعله مستترٌ' in f_['subject']['why'] for f_ in fr.values()))
check('D04 «دُعُوا»: المرشّحان (الماضي المجهول والأمر) باقيان، والإسناد مؤجَّل بهما (لا يُحسم بإطار الشرط)',
      fr['دُعُوا']['subject']['status'] == 'DEFERRED', fr['دُعُوا']['subject'])
check('D05 الفواحص الثلاثة بلا خلل على 2:282', not check_records(o['records'], o['tokens'], o.get('parts')) and
      not check_cross(o['records'], o['axes']) and not check_inflection(o['axes']))

print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
