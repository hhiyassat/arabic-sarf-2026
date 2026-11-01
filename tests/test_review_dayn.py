# -*- coding: utf-8 -*-
"""مراجعة آية الدين (2:282): الأخطاء المسمّاة في التدقيق، كلٌّ باختبار.

ملكية الشرط والجواب، وحدود الصلة، وأنواع طرفَي العطف، ومقدمات الترخيص، وثغرات العوامل.
تُختبر هنا قبل إعادة إعلان السلامة على القرآن كاملاً.
"""
import os, sys
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.root import hfn
bad = 0


def check(name, ok, got=''):
    global bad
    bad += not ok
    print(('OK  ' if ok else 'BAD ') + name, '' if ok else got)


if not hfn() or not os.path.exists(H + 'data/quran_hafs.tsv'):
    print('SKIP: يحتاج SARF_HFN وdata/quran_hafs.tsv')
    sys.exit(0)

from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.algebra import Trace, sentence_geo, linguistic_layer, cross_ayah_links

cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
rows = {(int(x[0]), int(x[1])): x[2] for x in
        (l.rstrip('\n').split('\t') for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'))}

# الروابط في جمل الآية ٢٨٢ (مع جارتيها كما في التتبّع)
items, prev, cross, ends, T = [], None, [], set(), Trace()
A282 = None
for vv in (281, 282, 283):
    a = analyze(cat, rows[(2, vv)])
    if vv == 282:
        A282 = a
    S, u = sentence_geo(a, f'Q2:{vv}', T)
    items.append((2, vv, a, u, S))
    cur = dict(s=2, v=vv, text=rows[(2, vv)], a=a, units=u, S=S)
    if prev:
        cross += cross_ayah_links(lambda t: analyze(cat, t), prev, cur)
        ends.add((2, prev['v']))
    prev = cur
LT, st, _ = linguistic_layer(items, Trace(), 'x', cross=cross, checked_ends=frozenset(ends))
bonds = []
for SP in LT:
    for D in SP.A + SP.O.get('pending', []):
        for J in D.A + D.O.get('pending', []):
            if any(x[1] == 282 for x in (J.O.get('location') or [])):
                bonds += list(J.O.get('bound') or [])


def find(head, label_part=''):
    return [b for b in bonds if f'«{head}»' in b[0] and label_part in b[1]]


# ١ «تَرۡضَوۡنَ» ليست جواب «إِن لَّمۡ يَكُونَا»: الجواب يبدأ بـ«فَرَجُلٌ»
check('١ «تَرْضَوْنَ» لا تُرخَّص جواباً لـ«إِنْ»', not find('تَرْضَوْنَ', 'جواب الشرط'), find('تَرْضَوْنَ'))
check('١ «لَمْ يَكُونَا» فعل شرطٍ منفيّ مرخَّص', any(b[2] == 'مرخّصة' and 'منفيٌّ' in b[1] for b in find('يَكُونَا', 'فعل الشرط')),
      find('يَكُونَا'))
# ٢ «فَلَيۡسَ» ليست جواب «إِذَا مَا دُعُواْ»
check('٢ «لَيْسَ» ليست جواب «إِذَا»', not find('لَيْسَ', 'جواب الشرط «إِذَا»'), find('لَيْسَ'))
# ٣ الرؤوس لا تُعطف على الموصول أو الجار
check('٣ «يَتَّقِ» معطوفةٌ على جملةٍ فعلية لا على «جملة الذي»',
      any('جملة فعلية' in b[1] for b in find('يَتَّقِ')) and not any('الَّذِي' in b[1] for b in find('يَتَّقِ')), find('يَتَّقِ'))
check('٣ «تَسْءَمُوا» لا تُعطف على «جملة ما»', not any('«مَا»' in b[1] for b in find('تَسْءَمُوا')), find('تَسْءَمُوا'))
check('٣ «يَسْتَطِيعُ» لا مرشَّح لها «الَّذِي» ولا «عَلَيْهِ»، وعطفها مؤجَّلٌ غير مرخَّص',
      find('يَسْتَطِيعُ') and all(b[2] != 'مرخّصة' and '«الَّذِي»' not in b[1] and '«عَلَيْهِ»' not in b[1]
                                  for b in find('يَسْتَطِيعُ')), find('يَسْتَطِيعُ'))
# ٤ «دُعُواْ»: الترخيص يُظهر التحليل الصرفي المستعمَل وحالته
d = find('دُعُوا', 'فعل الشرط')
check('٤ «دُعُوا» فعل الشرط غير مرخَّص ومقدّمته (التحليل أمر) ظاهرة', d and all(b[2] != 'مرخّصة' and '[' in b[1] and 'أمر' in b[1]
                                                                         for b in d), d)
check('٤ كل ترخيصٍ لشرطٍ أو جوابٍ يحمل مقدّماته بين معقوفين',
      all('[' in b[1] for b in bonds if b[2] == 'مرخّصة' and ('فعل الشرط' in b[1] or 'جواب الشرط' in b[1])),
      [b for b in bonds if b[2] == 'مرخّصة' and 'الشرط' in b[1] and '[' not in b[1]])
# ٥ ثغرات العوامل
ops = {}
for c in A282['operators']:
    w = A282['segments'][c['word_index']]['word']
    ops.setdefault(w, []).append(c)
def st_(w, op):
    return [c['status'] for c in ops.get(w, []) if c['operator'] == op]
check('٥ «لَمْ يَكُونَا»: حذف النون في المثنى يُثبت الجزم', 'accepted' in st_('لَّمْ', 'لَمْ'), st_('لَّمْ', 'لَمْ'))
check('٥ «وَلْيُمْلِلِ»: كسر التقاء الساكنين جزمٌ', 'accepted' in st_('وَلْيُمْلِلِ', 'لِ'), ops.get('وَلْيُمْلِلِ'))
check('٥ «وَلْيَتَّقِ»: حذف حرف العلة جزمٌ', 'accepted' in st_('وَلْيَتَّقِ', 'لِ'), ops.get('وَلْيَتَّقِ'))
w_amr = [c for c in A282['operators'] if c['operator'] == 'وَ' and c.get('group') == '1' and
         A282['segments'][c['word_index']]['word'] == 'وَامْرَأَتَانِ']
check('٥ واو القسم قبل «امْرَأَتَانِ» المرفوعة ممنوعة بالعلامة المكتوبة', w_amr and all(c['status'] == 'blocked' for c in w_amr),
      [(c['status'], c.get('reject_reason')) for c in w_amr])
other = [c for c in A282['operators'] if A282['segments'][c['word_index']]['word'] == 'وَامْرَأَتَانِ' and c['status'] == 'deferred']
check('٥ والمنافس الممنوع لا يُعدّ منافساً قائماً في تأجيل غيره',
      not any('مج 1' in str((c.get('judgement') or {}).get('rivals')) for c in other),
      [(c['group'], (c.get('judgement') or {}).get('rivals')) for c in other])
kan = [c for c in A282['operators'] if c['operator'] == 'كَانَ' and c['status'] == 'accepted' and
       A282['segments'][c['word_index'] + 1]['word'] == 'الَّذِي']
check('٥ «كَانَ الَّذِي»: الدليل «اسم موصول مبني» لا «ضمير مبني»',
      kan and all(any('اسم موصول مبني' in p for p in c['judgement']['proof']) and
                  not any('ضمير مبني' in p for p in c['judgement']['proof']) for c in kan),
      [(c.get('judgement') or {}).get('proof') for c in kan])
# ٦ لا معرّف فرضيةٍ مكرَّر: الموضع والأداة ومجموعتها والمعمول
hid = [(c['word_index'], (c.get('slot') or {}).get('index'), c['operator'], c.get('group'),
        ((c.get('relation') or {}).get('target') or {}).get('word_index'),
        ((c.get('relation') or {}).get('target') or {}).get('slot')) for c in A282['operators']]
check('٦ معرّف الفرضية فريدٌ لكل علاقة', len(hid) == len(set(hid)), len(hid) - len(set(hid)))

print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
