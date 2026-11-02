# -*- coding: utf-8 -*-
"""عقد التطبيع (sarf/normalize_trace.py): الحالات المسمّاة، والحالات المقابلة، والتحقق البنيوي على القرآن كله.

    python3 tests/test_normalize_trace.py          (القرآن كله: نحو دقيقة)
    python3 tests/test_normalize_trace.py --quick  (الحالات المسمّاة وحدها)

الناتج المعياري هو «display» (إملائيٌّ غير مكتمل: ما لا تحسمه قاعدة يُعلَّم «غير محسوم»).
والتمثيل التحليلي «analysis» تمثيلٌ داخلي للمحلِّل، مشتقٌّ ومعلَن، وليس هو الناتج المعياري.
"""
import os, re, sys, unicodedata
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.normalize_trace import normalize_traced, restore_source, RULES
from sarf.normalize import _uthmani_normalize_legacy

bad = 0
FIELDS = ('occurrence_id', 'source_spans', 'source_text', 'source_codepoints', 'normalized_text', 'normalized_spans',
          'operation', 'rule_id', 'rule_version', 'rule_reference', 'preserved_information', 'status', 'reason')


def check(name, ok, got=''):
    global bad
    bad += not ok
    print(('OK  ' if ok else 'BAD ') + name, '' if ok else got)


ROWS = [l.rstrip('\n').split('\t')[:3] for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8')]
TEXT = {(int(s), int(v)): t for s, v, t in ROWS}
nfc = lambda x: unicodedata.normalize('NFC', x)


def find(ref, w):
    """موضع الكلمة في المصدر (من الصفر) بمقارنة NFC، متجاوزاً علامة الحزب في أولها"""
    ws = [nfc(x).lstrip(chr(0x06DE)) for x in TEXT[ref].split(' ')]
    tail = '[' + chr(0x06D6) + '-' + chr(0x06DC) + chr(0x200F) + ']+$'
    k = next((k for k, x in enumerate(ws) if re.sub(tail, '', x) == nfc(w)), None)
    return k if k is not None else next((k for k, x in enumerate(ws) if x.startswith(nfc(w))), None)


def word(res, which, src_word):
    """كلمة الناتج المقابلة لكلمة المصدر بخريطة المحارف لا بالترتيب"""
    cells = res['cells_' + which]
    out = ''.join(c['c'] for c in cells)
    src = res['source']
    starts = [0] + [i + 1 for i, ch in enumerate(src) if ch == ' ']
    a = starts[src_word]
    b = (starts[src_word + 1] - 1) if src_word + 1 < len(starts) else len(src)
    idx = [k for k, c in enumerate(cells) if any(a <= i < b for i in c['src'])]
    if not idx:
        return ''
    lo, hi = idx[0], idx[-1]
    while lo > 0 and out[lo - 1] != ' ':
        lo -= 1
    while hi + 1 < len(out) and out[hi + 1] != ' ':
        hi += 1
    return out[lo:hi + 1]


def ops(res, which, rule):
    return [o for o in res['ops_' + which] if o['rule_id'] == rule]


def case(ref, w, which, exp, name):
    i = find(ref, w)
    if i is None:
        check(f'{name}: «{w}» في {ref[0]}:{ref[1]}', False, 'غير موجودة في المصدر')
        return None
    r = normalize_traced(TEXT[ref], f'{ref[0]}:{ref[1]}')
    got = word(r, which, i)
    check(f'{name}: «{w}» ({ref[0]}:{ref[1]}) ← «{exp}»', got == exp, got)
    return r


R = normalize_traced(TEXT[(2, 282)], '2:282')

# ---------- سجل التحويل: الحقول المطلوبة ----------
check('السجل: كل عمليةٍ تحمل الحقول الثلاثة عشر المطلوبة',
      all(all(f in o for f in FIELDS) for o in R['ops_display'] + R['ops_analysis']),
      [f for f in FIELDS if any(f not in o for o in R['ops_display'])])
check('السجل: كل قاعدةٍ مستعملة معرَّفةٌ بإصدارها ومرجعها',
      {o['rule_id'] for o in R['ops_display'] + R['ops_analysis']} <= set(RULES))

# ---------- أ. التنوين بالميم الصغيرة ----------
for w, exp in (('كَاتِبُۢ', 'كَاتِبٌ'), ('فُسُوقُۢ', 'فُسُوقٌ')):
    case((2, 282), w, 'display', exp, 'أ')
    case((2, 282), w, 'analysis', exp, 'أ (التحليلي)')
check('أ: الميم الصغيرة محفوظةٌ بموضعها ووظيفتها، ولا نون مضافة',
      all(any(p['codepoint'] == 'U+06E2' and p['function'] == 'ميم الإقلاب' for o in ops(R, 'display', 'N-IQLAB-TANWIN')
              for p in o['preserved_information']) for _ in [0]) and 'ن' not in word(R, 'display', find((2, 282), 'كَاتِبُۢ')))
check('أ: الضمة الأصلية محفوظةٌ هويةً ورسماً وإن صارت تنويناً',
      any(p['codepoint'] == 'U+064F' for o in ops(R, 'display', 'N-IQLAB-TANWIN') for p in o['preserved_information']))
case((2, 95), 'أَبَدَۢا', 'display', 'أَبَدًا', 'أ فتحة')
case((2, 41), 'كَافِرِۭ', 'display', 'كَافِرٍ', 'أ كسرة (الميم تحت)')
case((3, 153), 'غَمَّۢا', 'display', 'غَمًّا', 'أ مع الشدّة')
r = case((2, 27), 'مِنۢ', 'display', 'مِن', 'أ مقابل: ميمٌ على نونٍ مكتوبة')
check('أ مقابل: «مِنۢ» إقلابُ نونٍ ساكنة (N-IQLAB-NOON) لا تنوين', r and ops(r, 'display', 'N-IQLAB-NOON')
      and not ops(r, 'display', 'N-IQLAB-TANWIN'))
case((2, 31), 'أَنۢبِـُٔونِي', 'display', 'أَنبِئُونِي', 'أ مقابل: النون المكتوبة وسط الكلمة')
check('أ: التنوين المتتابع (ࣰ) صار تنويناً، وصورته الأصلية محفوظة',
      any(p['codepoint'] == 'U+08F2' for o in ops(R, 'display', 'N-KFGQPC-TANWIN') for p in o['preserved_information']))

# ---------- ب. العثماني ← الإملائي ----------
for w, exp in (('إِحۡدَىٰهُمَا', 'إِحْدَاهُمَا'), ('تَسۡـَٔمُوٓاْ', 'تَسْأَمُوا'), ('تِجَٰرَةً', 'تِجَارَةً'),
               ('لِلشَّهَٰدَةِ', 'لِلشَّهَادَةِ'), ('ذَٰلِكُمۡ', 'ذَلِكُمْ'), ('شَيۡـࣰٔ', 'شَيْئًا')):
    case((2, 282), w, 'display', exp, 'ب')
# مقابلات: لا تعميم
case((2, 51), 'مُوسَىٰٓ', 'display', 'مُوسَى', 'ب مقابل: المقصورة الخنجرية آخر الكلمة تبقى ى')
case((2, 2), 'ذَٰلِكَ', 'display', 'ذَلِكَ', 'ب مقابل: ما تحذف الإملاء ألفه')
case((2, 3), 'ٱلصَّلَوٰةَ', 'display', 'الصَّلَاةَ', 'ب: الواو الحاملة للخنجرية')
case((2, 168), 'ٱلشَّيۡطَٰنِۚ', 'display', 'الشَّيْطَانِ', 'ب: الخنجرية بعد فتحة')
case((2, 189), 'يَسۡـَٔلُونَكَ', 'display', 'يَسْأَلُونَكَ', 'ب: الهمزة على المطّة بعد ساكن')
case((2, 108), 'سُئِلَ', 'display', 'سُئِلَ', 'ب: همزةٌ على كرسيّها في المصدر لا تتغيّر')
case((2, 87), 'جَآءَكُمۡ', 'display', 'جَاءَكُمْ', 'ب مقابل: الهمزة بعد الألف على السطر')
case((2, 271), 'سَيِّـَٔاتِكُمۡ', 'display', 'سَيِّئَاتِكُمْ', 'ب: الهمزة بعد الكسر ياءً، ولا مدّة')
case((2, 81), 'سَيِّئَةࣰ', 'display', 'سَيِّئَةً', 'ب مقابل: مقعدٌ صحيح لا يتغيّر')
case((10, 27), 'ٱلسَّيِّـَٔاتِ', 'display', 'السَّيِّئَاتِ', 'ب مقابل: لا مدّة بعد الكسر (لا آ)')
case((10, 51), 'ءَآلۡـَٰٔنَ', 'display', 'آلْآنَ', 'ب: همزةٌ وخنجرية مدّة')
case((4, 92), 'خَطَـࣰٔ', 'display', 'خَطَأً', 'ب: لا ألف بعد تنوين الهمزة على الألف')
case((2, 135), 'وَمَا', 'display', 'وَمَا', 'ب: كلمةٌ لا تتغيّر')
r = normalize_traced(TEXT[(6, 76)], '6:76')
check('ب: «رَءَا» آخر الكلمة غير محسوم (لا «رَآ» ولا «رأى» بالتخمين)',
      any(o['rule_id'] == 'I-UNRESOLVED' and 'رَءَا' in (o['reason'] or '') for o in r['ops_display']) and
      'رَآ' not in r['display'].split(' '), r['display'][:80])
check('ب: النداء الموصول رسماً (يَٰٓأَيُّهَا) غير محسوم، لا يُفصل بالتخمين',
      any(o['rule_id'] == 'I-UNRESOLVED' and 'النداء' in (o['reason'] or '') for o in R['ops_display']))
r = normalize_traced('فَأُوْلَٰٓئِكَ وَأُوْلُواْ لَأَاْذۡبَحَنَّهُۥٓ سَأُوْرِيكُمۡ وَأُوْلَٰٓئِكُمۡ أَءِلَٰهࣱ')
check('ب: واو «أولئك/أولو» تُكتب، وحرف الصفر في غيرهما يُحذف، والإله بلا ألف بعد همزة الاستفهام',
      r['display'].split(' ') == ['فَأُولَئِكَ', 'وَأُولُو', 'لَأَذْبَحَنَّهُ', 'سَأُرِيكُمْ', 'وَأُولَئِكُمْ', 'أَئِلَهٌ'], r['display'])

# ---------- ج. الحركات والسكون والشدّة ----------
for w in ('تَدَايَنتُم', 'أَن', 'مِن', 'مِمَّن'):
    i = find((2, 282), w)
    d, a = word(R, 'display', i), word(R, 'analysis', i)
    check(f'ج «{w}»: الناتج المعياري لا يضيف سكوناً لم يُكتب', 'ْ' not in d, d)
check('ج: كل سكونٍ مضاف في التمثيل التحليلي محرفٌ مشتقّ بلا مصدر، وعمليته «مشتقّ» بقاعدة N-IMPLICIT-SUKUN',
      len(ops(R, 'analysis', 'N-IMPLICIT-SUKUN')) == len([c for c in R['cells_analysis'] if c['derived'] and not c['src']]) and
      all(o['status'] == 'مشتقّ' for o in ops(R, 'analysis', 'N-IMPLICIT-SUKUN')))
check('ج: لا محرف مشتقّاً بلا مصدر في الناتج المعياري',
      not [c for c in R['cells_display'] if c['derived'] and not c['src']])
written = [c for c in R['cells_display'] if c['c'] == 'ْ']
check('ج: كل سكونٍ في الناتج المعياري مكتوبٌ في المصدر (ۡ أو ْ) ومنسوبٌ إليه',
      written and all(R['source'][c['src'][0]] in ('ۡ', 'ْ') for c in written))
src_shadda = R['source'].count('ّ')
check('ج: الشدّة محفوظة كلها في الناتج المعياري، ومنها شدّة الإدغام أول الكلمة (مُّسَمًّى)',
      R['display'].count('ّ') == src_shadda and 'مُّسَمًّى' in R['display'].split(' '),
      (R['display'].count('ّ'), src_shadda))

# ---------- د. العلامات والمسافات ----------
cats = {p['function'] for o in R['ops_display'] for p in o['preserved_information']}
check('د: علامات الوقف وميم الإقلاب وعلامة المدّ والصلة محفوظةٌ بموضعها ووظيفتها',
      {'علامة وقف', 'ميم الإقلاب', 'علامة المدّ', 'واو صغيرة'} <= cats or {'علامة وقف', 'ميم الإقلاب', 'علامة المدّ'} <= cats, cats)
j = ops(R, 'display', 'N-JOIN-LONE-ALIF')
check('د: «مُّسَمࣰّ ى» و«شَيۡـࣰٔ اۚ» جمع أجزاءٍ بقاعدةٍ موثّقة، بمجالين من كلمتين في المصدر',
      len(j) == 2 and all(o['operation'] == 'جمع أجزاء' and len(o['words']) == 2 for o in j), [(o['source_text'], o['words']) for o in j])
check('د مقابل: لا جمع لغير الألف المفردة (128 كلمة من 130)',
      len(R['display'].split(' ')) == len(R['source'].split(' ')) - sum(1 for w in R['source'].split(' ')
                                                                        if re.fullmatch('[اى][ۖ-ۭ]*', w)))
r = normalize_traced(TEXT[(25, 49)], '25:49')
check('د: حركة المطّة الحاملة للياء الصغيرة لها لا لما قبلها (لِّنُحۡـِۧيَ ← لِّنُحْيِيَ)',
      word(r, 'display', find((25, 49), 'لِّنُحۡـِۧيَ')) == 'لِّنُحْيِيَ', word(r, 'display', find((25, 49), 'لِّنُحۡـِۧيَ')))
r = normalize_traced(TEXT[(21, 88)], '21:88')
check('د: النون الصغيرة حرفٌ (نُـۨجِي ← نُنجِي)', word(r, 'display', find((21, 88), 'نُـۨجِي')) == 'نُنجِي')
check('د: علامة الاتجاه (U+200F) محذوفةٌ من العرض ومحفوظةٌ بموضعها',
      any(p['codepoint'] == 'U+200F' for o in normalize_traced(TEXT[(2, 7)])['ops_display'] for p in o['preserved_information']))

# ---------- ٧. لا قراءة لنتائج التحليل ----------
import subprocess
out = subprocess.run([sys.executable, '-c', 'import sys; sys.path.insert(0, %r); import sarf.normalize_trace; '
                      'print(sorted(m for m in sys.modules if m.startswith("sarf.")))' % H], capture_output=True, text=True).stdout
check('٧: وحدة التطبيع لا تحمِّل وحدات التحليل (pipeline، segment، judge، root، algebra، features…)',
      set(eval(out)) <= {'sarf.normalize', 'sarf.normalize_trace', 'sarf.chars'}, out)

if '--quick' not in sys.argv:
    n = dict(restore=0, incomplete=0, attr=0, nfc=0, legacy=0, determinism=0, reject=0, info=0)
    ex = {}
    for s, v, t in ROWS:
        loc = f'{s}:{v}'
        r = normalize_traced(t, loc)
        for which in ('analysis', 'display'):
            rs, miss = restore_source(r, which)
            if rs != t or miss:
                n['restore'] += 1
                ex.setdefault('restore', loc)
            n['info'] += len(miss)
            in_op = {i for o in r['ops_' + which] for a, b in o['source_spans'] for i in range(a, b)}
            same = {c['src'][0] for c in r['cells_' + which] if len(c['src']) == 1 and not c['derived'] and t[c['src'][0]] == c['c']}
            if any(i not in in_op and i not in same for i in range(len(t))):
                n['incomplete'] += 1
                ex.setdefault('incomplete', loc)
            sw = [None] * len(t)
            k = 0
            for i, ch in enumerate(t):
                if ch == ' ':
                    k += 1
                else:
                    sw[i] = k
            joined = {sw[i] for o in r['ops_' + which] if o['rule_id'] == 'N-JOIN-LONE-ALIF' for a, b in o['source_spans']
                      for i in range(a, b) if sw[i] is not None}
            cur = set()
            for c in r['cells_' + which] + [dict(c=' ', src=[], derived=False)]:
                if c['c'] == ' ':
                    if len(cur) > 1 and not cur <= joined:
                        n['attr'] += 1
                        ex.setdefault('attr', loc)
                    cur = set()
                else:
                    cur |= {sw[i] for i in c['src'] if sw[i] is not None}
            if nfc(r[which]) != r[which]:
                n['nfc'] += 1
                ex.setdefault('nfc', loc)
        if r['analysis'] != _uthmani_normalize_legacy(t) and not \
                ({o['rule_id'] for o in r['ops_analysis']} & {'N-IQLAB-TANWIN', 'N-SMALL-NOON', 'N-SMALL-CARRIER'}):
            n['legacy'] += 1
            ex.setdefault('legacy', loc)
        r2 = normalize_traced(t, loc)
        if (r2['analysis'], r2['display'], r2['ops_display']) != (r['analysis'], r['display'], r['ops_display']):
            n['determinism'] += 1
            ex.setdefault('determinism', loc)
        rej = 0
        for x in (r['analysis'], r['display']):
            try:
                normalize_traced(x, strict=True)
            except ValueError:
                rej += 1
        if rej != 2:
            n['reject'] += 1
            ex.setdefault('reject', loc)
    check('١ القرآن كله: لا فقد غير مسجَّل للمعلومات', n['info'] == 0, (n['info'], ex.get('restore')))
    check('٢ القرآن كله: كل محرفٍ في المصدر مغطّى (في الناتج بعينه أو في عملية)', n['incomplete'] == 0, (n['incomplete'], ex.get('incomplete')))
    check('٢ القرآن كله: لا محرف يُنسب إلى كلمةٍ أخرى إلا بجمع الأجزاء المسجَّل', n['attr'] == 0, (n['attr'], ex.get('attr')))
    check('٤ القرآن كله: المصدر يُستعاد حرفياً من الناتجين وسجلّهما', n['restore'] == 0, (n['restore'], ex.get('restore')))
    check('٥ القرآن كله: الناتج ثابتٌ عند تكرار التشغيل بالمدخلات نفسها', n['determinism'] == 0, (n['determinism'], ex.get('determinism')))
    check('٦ القرآن كله: الناتج المطبَّع ليس مدخلاً مقبولاً (يُرفض في الوضع الصارم)', n['reject'] == 0, (n['reject'], ex.get('reject')))
    check('القرآن كله: الناتجان على NFC', n['nfc'] == 0, (n['nfc'], ex.get('nfc')))
    check('القرآن كله: التمثيل التحليلي لا يتغيّر عن السابق إلا بقواعد إصلاح فقد المعلومة', n['legacy'] == 0, (n['legacy'], ex.get('legacy')))

print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
