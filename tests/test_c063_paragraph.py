"""tests/test_c063_paragraph.py — SARF_COMPLETION_FROM_REPORT_063 §١٠: شروط حدّ الفقرة PB-L1 لا تُستوفى بأثر قصّ المدخل."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from sarf.stages import run_ref, run
from sarf import quran_source
FAIL = []


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:300]}'))
    if not ok:
        FAIL.append(name)


P = run_ref('2:282').get('paragraphs')[0]['candidate']
cd = P['boundary']['conditions']
check('G01 2:282 وحدها: ما قبلها وما بعدها خارج المدخل ← «لم يُفحص»، لا «مستوفى»',
      cd['start']['b'].startswith('NOT_CHECKED') and cd['end']['b'].startswith('NOT_CHECKED') and cd['end']['c'].startswith('NOT_CHECKED'), cd)
check('G02 لا شرط «MET» يستند إلى غياب جملةٍ في المدخل', not any(v.startswith('MET') and 'في المدخل' in v for side in ('start', 'end') for v in cd[side].values()), cd)
check('G03 الحكم باقٍ NOT_PROVEN (الإصلاح لا يغيّر الحكم، يغيّر ما يُعلَن مستوفى)', P['boundary']['linguistic'] == 'NOT_PROVEN', P['boundary'])
fat = [x for x in quran_source.rows() if x[0] == 1]
C = run(fat, None, ['paragraphs'])
P1 = C.get('paragraphs')[0]['candidate']
c1 = P1['boundary']['conditions']
check('G04 الفاتحة كاملة (FA02 §٦): بداية السورة وآخرها حدّا مصدر (SOURCE_ONLY) لا يستوفيان (أ) ولا (ب)، والمرشّح الداخلي لا يستوفي (ج)؛ '
      'فالحدّ اللغوي NOT_PROVEN، والتقطيع «SOURCE:surah» معلن',
      all(c1[s_][k_].startswith('SOURCE_ONLY') for s_ in ('start', 'end') for k_ in ('a', 'b')) and not c1['start']['c'].startswith('MET')
      and P1['boundary']['linguistic'] == 'NOT_PROVEN' and P1['boundary']['segmentation_basis'] == 'SOURCE:surah'
      and all(x['outside_referent_excluded'] is False for x in P1['references']), (c1, P1['boundary'].get('segmentation_basis')))
mid = [x for x in quran_source.rows() if x[0] == 2 and 281 <= x[1] <= 283]
C3 = run(mid, None, ['paragraphs'])
c3 = [p['candidate']['boundary']['conditions'] for p in C3.get('paragraphs')]
check('G05 مدخل 2:281–283: (ب) للبداية «لم يُفحص» (ما قبل 2:281 خارج المدخل)، وليس «مستوفى»',
      all(c['start']['b'].startswith(('NOT_CHECKED', 'NOT_MET')) for c in c3), c3)
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
