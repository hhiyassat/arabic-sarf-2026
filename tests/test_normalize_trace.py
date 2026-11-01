# -*- coding: utf-8 -*-
"""عقد التطبيع N1.0 (sarf/normalize_trace.py): الحالات المسمّاة، والحالات المقابلة، وسلامة السجل على القرآن كله.

    python3 tests/test_normalize_trace.py          (القرآن كله: نحو دقيقة)
    python3 tests/test_normalize_trace.py --quick  (الحالات المسمّاة وحدها)
"""
import os, re, sys, unicodedata
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.normalize_trace import normalize_traced, restore_source, RULES
from sarf.normalize import _uthmani_normalize_legacy

bad = 0


def check(name, ok, got=''):
    global bad
    bad += not ok
    print(('OK  ' if ok else 'BAD ') + name, '' if ok else got)


ROWS = [l.rstrip('\n').split('\t')[:3] for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8')]
TEXT = {(int(s), int(v)): t for s, v, t in ROWS}


def word(res, which, src_word):
    """كلمة الناتج التي تقابل الكلمة src_word (من الصفر) في المصدر، بخريطة المحارف لا بالترتيب"""
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


def find(ref_or_text, w):
    """موضع الكلمة في المصدر بمقارنة NFC (المصدر يكتب الهمزة مفكوكة: ا + ٔ)"""
    t = TEXT[ref_or_text] if isinstance(ref_or_text, tuple) else ref_or_text
    nw = unicodedata.normalize('NFC', w)
    return next((k for k, x in enumerate(t.split(' ')) if unicodedata.normalize('NFC', x).lstrip('\u06DE').startswith(nw)), None)


def ops_of(res, which, rule):
    return [o for o in res['ops_' + which] if o['rule'] == rule]


R282 = normalize_traced(TEXT[(2, 282)], '2:282')
src_words = TEXT[(2, 282)].split(' ')
W = {unicodedata.normalize('NFC', w): i for i, w in reversed(list(enumerate(src_words)))}
for _w, _i in list(W.items()):
    W[re.sub('[\u06D6-\u06DC]+$', '', _w)] = W.get(re.sub('[\u06D6-\u06DC]+$', '', _w), _i)


class _W(dict):
    def __getitem__(self, k):
        return dict.__getitem__(self, unicodedata.normalize('NFC', k))

    def get(self, k, d=None):
        return dict.get(self, unicodedata.normalize('NFC', k), d)
W = _W(W)

# ١ تنوين الإقلاب
for w, exp in (('كَاتِبُۢ', 'كَاتِبٌ'), ('فُسُوقُۢ', 'فُسُوقٌ')):
    i = W[w]
    check(f'١ «{w}» (المصدر 2:282 كلمة {i + 1}) ← «{exp}» تحليلاً وعرضاً، والميم محفوظة',
          word(R282, 'analysis', i) == exp and word(R282, 'display', i) == exp and
          any(p['cp'] == 'U+06E2' for o in ops_of(R282, 'analysis', 'N-IQLAB-TANWIN') for p in o['preserved']),
          (word(R282, 'analysis', i), word(R282, 'display', i)))
check('١ التنوين حركةٌ واحدة: لا نون مضافة في «كَاتِبٌ»', 'ن' not in word(R282, 'analysis', W['كَاتِبُۢ']))
for ref, w, exp in (((2, 95), 'أَبَدَۢا', 'أَبَدًا'), ((2, 41), 'كَافِرِۭ', 'كَافِرٍ'), ((3, 153), 'غَمَّۢا', 'غَمًّا')):
    r = normalize_traced(TEXT[ref])
    i = find(ref, w)
    check(f'١ «{w}» ← «{exp}» (فتحة/كسرة مع الميم)', word(r, 'analysis', i) == exp, word(r, 'analysis', i))
# مقابل: الميم على نونٍ عارية إقلاب نونٍ ساكنة لا تنوين
r = normalize_traced(TEXT[(2, 27)])
i = find((2, 27), 'مِنۢ')
check('١ مقابل: «مِنۢ» تبقى نوناً (لا تنوين)، والميم محفوظة بقاعدة N-IQLAB-NOON',
      word(r, 'analysis', i) == 'مِنْ' and word(r, 'display', i) == 'مِن' and ops_of(r, 'analysis', 'N-IQLAB-NOON'),
      (word(r, 'analysis', i), word(r, 'display', i)))

# ٢ سياسة الرسم في العرض الإملائي، والتمثيل التحليلي لا يُوصف بأنه إملاء
for w, exp in (('إِحۡدَىٰهُمَا', 'إِحْدَاهُمَا'), ('تَسۡـَٔمُوٓاْ', 'تَسْأَمُوا'), ('تِجَٰرَةً', 'تِجَارَةً'),
               ('لِلشَّهَٰدَةِ', 'لِلشَّهَادَةِ'), ('ذَٰلِكُمۡ', 'ذَلِكُمْ'), ('شَيۡـࣰٔ', 'شَيْئًا')):
    i = W.get(w)
    if i is None:
        check(f'٢ «{w}» في 2:282', False, 'غير موجودة')
        continue
    check(f'٢ «{w}» عرضاً ← «{exp}»', word(R282, 'display', i) == exp, word(R282, 'display', i))
check('٢ التحليلي يبقي الخنجرية كما كان (تِجَٰرَةً)', word(R282, 'analysis', W['تِجَٰرَةً']) == 'تِجَٰرَةً')
for ref, w, exp in (((2, 51), 'مُوسَىٰٓ', 'مُوسَى'), ((2, 189), 'يَسۡـَٔلُونَكَ', 'يَسْأَلُونَكَ'),
                    ((2, 108), 'سُئِلَ', 'سُئِلَ'), ((2, 2), 'ذَٰلِكَ', 'ذَلِكَ'), ((2, 43), 'ٱلصَّلَوٰةَ', 'الصَّلَاةَ'),
                    ((2, 3), 'ٱلصَّلَوٰةَ', 'الصَّلَاةَ'), ((2, 87), 'جَآءَكُمۡ', 'جَاءَكُمْ')):
    t = TEXT[ref]
    ws = t.split(' ')
    k = find(ref, w)
    if k is None:
        check(f'٢ «{w}» موجودة في {ref[0]}:{ref[1]}', False, 'غير موجودة في المصدر')
        continue
    r = normalize_traced(t)
    check(f'٢ مقابل/تعميم: «{w}» ({ref[0]}:{ref[1]}) ← «{exp}»', word(r, 'display', k) == exp, word(r, 'display', k))
# واو «أولئك» تُكتب إملاءً، وما سواها من حروف الصفر يُحذف (مقابل)
r = normalize_traced('فَأُوْلَٰٓئِكَ هُمُ ٱلۡمُفۡلِحُونَ وَأُوْلُواْ ٱلۡأَلۡبَٰبِ لَأَاْذۡبَحَنَّهُۥٓ سَأُوْرِيكُمۡ')
check('٢ «فَأُوْلَٰٓئِكَ» و«وَأُوْلُواْ» عرضاً بالواو، والتحليلي بلا واو كما كان (D21)',
      r['display'].split(' ')[:2] == ['فَأُولَئِكَ', 'هُمُ'] and r['display'].split(' ')[3] == 'وَأُولُو' and
      r['analysis'].split(' ')[0] == 'فَأُلَٰئِكَ', (r['display'], r['analysis']))
check('٢ مقابل: «لَأَاْذۡبَحَنَّهُۥٓ» و«سَأُوْرِيكُمۡ» يُحذف حرف الصفر فيهما عرضاً',
      r['display'].split(' ')[5:] == ['لَأَذْبَحَنَّهُ', 'سَأُرِيكُمْ'], r['display'])
# النداء الموصول رسماً: غير محسوم، لا يُفصل بالتخمين
check('٢ «يَٰٓأَيُّهَا» غير محسوم في العرض (لا فصلٌ بالتخمين)',
      any(o['rule'] == 'I-UNRESOLVED' and 'النداء' in (o['note'] or '') for o in R282['ops_display']))

# ٣ السكون: المكتوب، والغائب، والمضاف بقاعدة
for w in ('تَدَايَنتُم', 'أَن', 'مِمَّن'):
    i = W[w]
    a, d = word(R282, 'analysis', i), word(R282, 'display', i)
    cells = R282['cells_analysis']
    derived_sukun = [c for c in cells if c['c'] == 'ْ' and c['derived'] and not c['src']]
    check(f'٣ «{w}»: التحليلي يضيف السكون علامةً مشتقّة بلا مصدر، والعرض لا يضيفه',
          'ْ' in a and 'ْ' not in d and derived_sukun, (a, d))
written = [c for c in R282['cells_analysis'] if c['c'] == 'ْ' and c['src']]
check('٣ السكون المكتوب (ۡ) منسوبٌ إلى محرفه في المصدر', written and
      all(TEXT[(2, 282)][c['src'][0]] in ('ۡ', 'ْ') for c in written))
check('٣ كل سكونٍ مضاف مسجَّلٌ بقاعدة N-IMPLICIT-SUKUN وحالة «مشتقّ»',
      all(o['status'] == 'مشتقّ' for o in ops_of(R282, 'analysis', 'N-IMPLICIT-SUKUN')) and
      len(ops_of(R282, 'analysis', 'N-IMPLICIT-SUKUN')) == len([c for c in R282['cells_analysis']
                                                                if c['c'] == 'ْ' and c['derived'] and not c['src']]))

# ٤ العلامات المحفوظة خارج العرض
cats = {p['category'] for o in R282['ops_analysis'] for p in o['preserved']}
check('٤ علامات الوقف وميم الإقلاب والمدّ وعلامة الاتجاه محفوظةٌ بموضعها',
      {'علامة وقف', 'ميم الإقلاب', 'علامة المدّ'} <= cats, cats)

# ٥ جمع الأجزاء
j = ops_of(R282, 'analysis', 'N-JOIN-LONE-ALIF')
check('٥ «مُّسَمࣰّ ى» و«شَيۡـࣰٔ اۚ» جمعا أجزاءٍ بقاعدةٍ موثّقة (ألفٌ مفردة بعد تنوينٍ مفتوح)، ولا جمع غيرهما',
      len(j) == 2 and all(o['type'] == 'جمع أجزاء' for o in j) and word(R282, 'display', W['شَيۡـࣰٔ']) == 'شَيْئًا' and j[0]['type'] == 'جمع أجزاء' and word(R282, 'analysis', W['مُّسَمࣰّ']) == 'مُّسَمًّى', j)
check('٥ مقابل: كلمتان متجاورتان بلا ألفٍ مفردة لا تُجمعان (128 كلمة من 130، والفرق «ى» و«ا» وحدهما)',
      len(R282['analysis'].split(' ')) == len(src_words) - sum(1 for w in src_words if re.fullmatch('[اى][\u06D6-\u06ED]*', w)))

# مرجع كل قاعدة مستعملة
used = {o['rule'] for o in R282['ops_analysis'] + R282['ops_display']}
check('كل قاعدةٍ مستعملة معرَّفةٌ بإصدارها ومرجعها', used <= set(RULES), used - set(RULES))

if '--quick' not in sys.argv:
    n_restore = n_incomplete = n_attr = n_nfc = n_legacy = n_idem = 0
    ex = {}
    for s, v, t in ROWS:
        r = normalize_traced(t, f'{s}:{v}')
        for which in ('analysis', 'display'):
            rs, miss = restore_source(r, which)
            if rs != t or miss:
                n_restore += 1
                ex.setdefault('restore', f'{s}:{v}')
            # الاكتمال: كل محرفٍ في المصدر إما في الناتج بمحرفه نفسه، وإما في سجل عمليةٍ
            in_op = {i for o in r['ops_' + which] for a, b in o['src_spans'] for i in range(a, b)}
            same = {c['src'][0] for c in r['cells_' + which] if len(c['src']) == 1 and not c['derived']
                    and t[c['src'][0]] == c['c']}
            if any(i not in in_op and i not in same for i in range(len(t))):
                n_incomplete += 1
                ex.setdefault('complete', f'{s}:{v}')
            # النسبة: محارف كل كلمةٍ ناتجة من كلمةٍ واحدة في المصدر، إلا ما جمعته قاعدة الجمع
            joined = {i for o in r['ops_' + which] if o['rule'] == 'N-JOIN-LONE-ALIF' for a, b in o['src_spans']
                      for i in range(a, b)}
            sw = [None] * len(t)
            k = 0
            for i, ch in enumerate(t):
                if ch == ' ':
                    k += 1
                else:
                    sw[i] = k
            for ow in ''.join(c['c'] for c in r['cells_' + which]).split(' '):
                pass
            out = r['cells_' + which]
            cur = set()
            for c in out + [dict(c=' ', src=[], derived=False)]:
                if c['c'] == ' ':
                    if len(cur) > 1 and not (cur & {sw[i] for i in joined if sw[i] is not None}):
                        n_attr += 1
                        ex.setdefault('attr', f'{s}:{v}')
                    cur = set()
                else:
                    cur |= {sw[i] for i in c['src'] if sw[i] is not None}
            if unicodedata.normalize('NFC', r[which]) != r[which]:
                n_nfc += 1
                ex.setdefault('nfc', f'{s}:{v}')
        if r['analysis'] != _uthmani_normalize_legacy(t):
            if not ({o['rule'] for o in r['ops_analysis']} & {'N-IQLAB-TANWIN', 'N-SMALL-NOON', 'N-SMALL-CARRIER'}):
                n_legacy += 1
                ex.setdefault('legacy', f'{s}:{v}')
        # الثبات: التطبيع حتمي (المدخل نفسه ← الناتج نفسه)، والناتج المطبَّع يُرفض مدخلاً في الوضع الصارم
        r2 = normalize_traced(t, f'{s}:{v}')
        rejected = 0
        for x in (r['analysis'], r['display']):
            try:
                normalize_traced(x, strict=True)
            except ValueError:
                rejected += 1
        if r2['analysis'] != r['analysis'] or r2['display'] != r['display'] or rejected != 2:
            n_idem += 1
            ex.setdefault('idem', f'{s}:{v}')
    check('القرآن كله: المصدر يُستعاد حرفياً من الناتجين وسجلّهما', n_restore == 0, (n_restore, ex.get('restore')))
    check('القرآن كله: كل اختلافٍ بين المصدر والناتج مسجَّلٌ في عملية', n_incomplete == 0, (n_incomplete, ex.get('complete')))
    check('القرآن كله: لا محرف يُنسب إلى كلمةٍ أخرى (إلا جمع الأجزاء المسجَّل)', n_attr == 0, (n_attr, ex.get('attr')))
    check('القرآن كله: الناتجان على NFC', n_nfc == 0, (n_nfc, ex.get('nfc')))
    check('القرآن كله: التحليلي يطابق السلوك السابق إلا بقواعد الإصلاح الثلاث (الإقلاب، النون الصغيرة، حامل الحرف الصغير)', n_legacy == 0, (n_legacy, ex.get('legacy')))
    check('القرآن كله: التطبيع حتمي، والناتج المطبَّع يُرفض مدخلاً (العقد لا يدّعي الثبات على نصٍّ مطبَّع)',
          n_idem == 0, (n_idem, ex.get('idem')))

print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
