#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_batch_b.py — الدفعة B من SARF_SEQUENTIAL_COMPLETION_PLAN_01: الصنف والسمات بقواعد عامة لا بقوائم كلمات.

E02 الاسمية قبل الضمير المتصل، E03 الهمزة المكسورة في أول الجذع، F03 تحقيق البدائل الزمنية، والمكمّل غير المكتوب الحالة،
وأوجه ضمير الصيغة غير المثبت، وحدّ بحث الفاعل عند العاطف المستقل. موجبةٌ ومقابلةٌ وعابرةٌ للطبقات.

    PYTHONHASHSEED=0 python3 -P -s tests/test_batch_b.py
"""
import os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
os.environ.setdefault('SARF_QURAN', 'hafs_kfgqpc')
from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.algebra import Trace, sentence_geo, linguistic_layer
from sarf.features import unit_features, host_case_vowel_proof, initial_hamza_kasra_proof, tense_realization
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
    return a, U, verse_relations(a, U, unit_features(a, U), f'{s}:{v}', legacy_cond=C, legacy_rel=Rl)


def at(o, loc, text):
    return next(u for u, l, t in o['tokens'] if l == loc and t == text)


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {got}'))
    if not cond:
        FAIL.append(name)


# ---------- E02 وE03: وحدات القاعدة (موجبة ومقابلة) ----------
pos = [('وَلِيُّ', 'هُ'), ('رَبُّ', 'كَ'), ('شَيَٰطِينِ', 'هِمْ'), ('بَعْضُ', 'كُمْ')]
neg = [('سَنُدْخِلُ', 'هُمْ'), ('يَنْفَعُ', 'هُمْ'), ('ادْعُ', 'هُنَّ'), ('كَتَبْتُ', 'هُ'), ('قِ', 'هِمُ'), ('بُورِ', 'كَ'),
       ('ءَاتِ', 'نَا'), ('نُنْسِ', 'هَا'), ('أُمَتِّعُ', 'هُ'), ('فَسَيَحْشُرُ', 'هُمْ'), ('وَلِّ', 'هِ'), ('خَلَقَ', 'كُمْ'), ('أَيَأْمُرُ', 'كُمْ')]
check('B01 E02 موجبة: «وليّه» «ربّك» «شياطينهم» «بعضكم» أسماءٌ بنفي صيغ الفعل قبل الضمير',
      all(host_case_vowel_proof(h, e) for h, e in pos), [(h, bool(host_case_vowel_proof(h, e))) for h, e in pos])
check('B02 E02 مقابلة: المضارع بحرف مضارعة (ولو بعد السين والفاء)، والأمر بهمزة وصل أو همزة أَفۡعِلۡ أو حرفين، وضمير الرفع، '
      'وفُوعِلَ، وفَعِّ، والماضي المفتوح: لا يُحكم باسميتها',
      not any(host_case_vowel_proof(h, e) for h, e in neg), [h for h, e in neg if host_case_vowel_proof(h, e)])
check('B03 E02 لا يعمل بلا ضميرٍ متصل ولا مع التنوين', not host_case_vowel_proof('وَلِيُّ', None) and
      not host_case_vowel_proof('رَجُلٌ', 'هُ'))
check('B04 E03: «إِحْدَى» اسم، و«أَحْسِنُ» و«ٱدْعُ» ليسا من مجالها',
      initial_hamza_kasra_proof('إِحْدَى') and not initial_hamza_kasra_proof('أَحْسِنُ') and not initial_hamza_kasra_proof('ٱدْعُ'))

# ---------- F03: تحقيق البدائل الزمنية ----------
def live(w, R, P):
    t = tense_realization(w, R, P, True) or {}
    return sorted(x for x in ('ماضٍ', 'أمر', 'مضارع') if t.get(x, ('LICENSED',))[0] != 'REJECTED')


cases = [('عَلَّمُوا', 'علم', 'II', ['ماضٍ']),
         ('عَلِّمُوا', 'علم', 'II', ['أمر']), ('يُؤْمِنُوا', 'أمن', 'IV', ['مضارع']), ('يُحْسِنُوا', 'حسن', 'IV', ['مضارع']), ('اكْتُبُوا', 'كتب', 'I', ['أمر']),
         ('كَتَبُوا', 'كتب', 'I', ['ماضٍ']), ('تَكْتُبُوا', 'كتب', 'I', ['مضارع']), ('ٱسْتَشْهِدُوا', 'شهد', 'X', ['أمر'])]
check('B05 F03 موجبة: كل بديلٍ زمني يُفحص تحقيقه للمكتوب، فيبقى وحده ما يحقّقه',
      all(live(w, R, P) == want for w, R, P, want in cases), [(w, live(w, R, P)) for w, R, P, want in cases if live(w, R, P) != want])
absent = [('ءَامَنُوا', 'أمن', 'IV'), ('أَحْسِنُوا', 'حسن', 'IV'), ('أَقَتَلْتَ', 'قتل', 'I'), ('أُفْرِغْ', 'فرغ', 'IV'),
          ('تَتَّبِعُوا', 'تبع', 'VIII'), ('نَنْسَخْ', 'نسخ', 'I'), ('نُنَزِّلْ', 'نزل', 'II'), ('تَصَدَّقُوا', 'صدق', 'V'),
          ('تَدَبَّرُوا', 'دبر', 'V')]
check('B06 F03 مقابلة: لا حكم حيث لا تفصل الكتابة — الهمزة في أوله (استفهامٌ أو متكلم أو أَفۡعَلَ)، وحرف مضارعةٍ يليه مثله من '
      'الجذر أو القالب، وتاء تَفَعَّلَ وتَفَاعَلَ (حذف إحدى التاءين)؛ والمعتلّ والمضعّف وغير المقبول جذره خارج المجال',
      all(tense_realization(w, R, P, True) is None for w, R, P in absent) and tense_realization('اتَّقُوا', 'وقي', 'VIII', True) is None and
      tense_realization('تَعَاوَنُوا', 'عون', 'VI', True) is None and tense_realization('ءَامَنُوا', 'أمن', 'IV', False) is None)

# ---------- عابرة للطبقات على 2:282 ----------
a, U, o = run(2, 282)
u50 = at(o, '2:282:50', 'وَلِيُّ')
subj = {r['heads'].get('subject'): r for r in o['records'] if r['type'] == 'SUBJECT' and r['status'] == 'LICENSED'}
check('B07 «وليّه»: الصنف بـE02، ثم فاعلٌ مرخَّص لـ«فليملل» بالقاعدة القائمة S01 (بلا قاعدة خاصة)',
      o['axes'][u50]['word_class'][0] == 'اسم' and 'E02' in o['axes'][u50]['word_class'][1] and u50 in subj
      and subj[u50]['texts']['verb'] == 'يُمْلِلْ', (o['axes'][u50]['word_class'], u50 in subj))
u68 = at(o, '2:282:68', 'إِحْدَى')
f67 = next(r for r in o['records'] if r['type'] == 'VERB_FRAME' and r['texts'].get('verb') == 'تَضِلَّ')
q67 = f67['frame'].get('object_requirement') or {}
check('B08 «إحداهما»: اسمٌ بـE03؛ والكاشف لا يقول «منصوبٌ مكتوب» والعلامة مقدّرة (CASE_NOT_WRITTEN)',
      o['axes'][u68]['word_class'][0] == 'اسم' and q67.get('kind') == 'CASE_NOT_WRITTEN' and 'منصوبٌ مكتوب' not in q67.get('note', ''),
      q67)
s67 = f67['frame']['subject']
check('B09 «تضلّ إحداهما»: ضمير الصيغة غير مثبت، فالأوجه معروضة بمرشّحها («إحدى» فاعلٌ في وجه الغائبة) ولا يُختار وجه',
      s67['status'] == 'DEFERRED' and u68 in (s67.get('candidates') or []) and 'غائب، مفرد، مؤنث' in s67['why']
      and 'مخاطب، مفرد، مذكر' in s67['why'] and u68 not in subj, s67)
u3 = at(o, '2:282:52', 'اسْتَشْهِدُوا')
t3 = o['axes'][u3]
fa = next(r for r in o['records'] if r['type'] == 'VERB_FRAME' and r['heads']['verb'] == u3)
check('B10 «ٱسۡتَشۡهِدُوا»: الأمر مثبتٌ بـF03 في الإطار (لا مرشّح ثلاثي الأوجه)', list(fa['frame']['tense'])[:2] == ['أمر', 'مثبت'] and
      'F03' in str(unit_features(a, U)[(51, 1)]['tense']['ev']), fa['frame']['tense'])
check('B11 الفواحص الثلاثة بلا خلل على 2:282', not check_records(o['records'], o['tokens'], o.get('parts')) and
      not check_cross(o['records'], o['axes']) and not check_inflection(o['axes']))

# ---------- حدّ بحث الفاعل عند العاطف المستقل (6:60) ----------
a, U, o = run(6, 60)
u13 = at(o, '6:60:13', 'أَجَلٌ')
s60 = next(r for r in o['records'] if r['type'] == 'SUBJECT' and r['texts'].get('verb') == 'يُقْضَى')
check('B12 «لِيُقۡضَىٰٓ أَجَلٞ … ثُمَّ إِلَيۡهِ مَرۡجِعُكُمۡ»: لا يُعبر «ثُمَّ» إلى منافس، فـ«أجل» نائب فاعلٍ مرخَّص',
      s60['status'] == 'LICENSED' and s60['heads'].get('subject') == u13, s60['reason'])

print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
