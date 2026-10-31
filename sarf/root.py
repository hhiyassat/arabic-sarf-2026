# -*- coding: utf-8 -*-
"""
sarf.root — T19a–T19c: الخلية، وبناء اللفظ، والتحليل المرخَّص للجذر والصيغة.

  T19a  الخلية: صامت C وحالته: a i o (قصيرة)، A I O (طويلة)، ∅ (بلا حركة)
  T19b  اللفظ سلسلة خلايا: الشدة تُفك إلى صامتين أولهما ساكن (كَتَّبَ ↔ kva + t∅ + tva + bva)،
        والواو والياء صامتان إلا إذا كانتا حرفي مدّ، والهمزة صامت مستقل
  T19c  Morph(W, R, P, F; e_m): اللفظ W ← الجذر R والصيغة P والخصائص F، بدليل التحليل e_m.
        «لا يكفي وجود الصوامت في اللفظ أو عدّها لإثبات الجذر»: فالمرشَّح من قالب الوزن لا يُقبل
        إلا برخصة، وهي ورود الزوج (الجذر، الوزن) في أحداث HFN (شبكة حسين للإطار) مع شاهده:
        مصدره (معجم، أو قاعدة سيبويه)، وقاعدة المصدر عند سيبويه، ومعنى الصيغة.
        ولا يُفرض التحليل الجذري على المبنيات والعوامل (لا يصل إليها).

المصدر: HFN release_v18 (CC0)، يُقرأ من مكانه: متغير البيئة SARF_HFN، أو ../husseinframenet/release/release_v18،
أو data/hfn. فإن لم يوجد بقيت الجذور كلها مرشَّحةً بلا رخصة (مؤجَّلة).
"""
import csv, os, re
from collections import defaultdict

from .chars import FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN, letters, strip_marks
from .affix import stem_info
from .agreement import signature

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HFN_PATHS = [os.environ.get('SARF_HFN', ''),
             os.path.join(os.path.dirname(HERE), 'husseinframenet', 'release', 'release_v18'),
             os.path.expanduser('~/arabic-net/HusseinFrameNet/release/release_v18'),
             os.path.join(HERE, 'data', 'hfn')]

MADD = set('اويى')
HAMZA = {'أ': 'ء', 'إ': 'ء', 'ؤ': 'ء', 'ئ': 'ء', 'ء': 'ء'}
WEAK = ('و', 'ي')
VOWEL = {FATHA: 'a', KASRA: 'i', DAMMA: 'o'}
LONG = {'a': 'A', 'i': 'I', 'o': 'O'}


# ---------- T19a/T19b: الخلايا ----------
def cells(text):
    """→ [(C، الحالة)]: الحالة a/i/o أو A/I/O (بعدها حرف مدّ من جنسها) أو ∅؛ والشدة صامتان"""
    toks = [(L, set(m)) for L, m in letters(text)]
    out = []
    for i, (L, m) in enumerate(toks):
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if L in MADD and not m and out and out[-1][1] in ('a', 'i', 'o') and \
                {'ا': 'a', 'ى': 'a', 'ي': 'i', 'و': 'o'}[L] == out[-1][1]:
            out[-1] = (out[-1][0], LONG[out[-1][1]])          # حرف المدّ يُطيل حركة ما قبله
            continue
        v = next((VOWEL[x] for x in m if x in VOWEL), '∅')
        if SHADDA in m:
            out.append((L, '∅'))
        out.append((L, v))
        del nxt
    return out


def cell_code(cs):
    """ترميز T19a: kva + t∅ + tva …"""
    return ' + '.join(f"{c}v{s}" if s != '∅' else f"{c}∅" for c, s in cs)


# ---------- HFN: الرخصة ----------
CLASS_OF = [  # (الحروف بلا حركات، فيه شدة؟) ← الوزن
    ('استفعل', None, 'X'), ('افعنلل', None, 'QIII'), ('تفاعل', None, 'VI'), ('انفعل', None, 'VII'),
    ('افتعل', None, 'VIII'), ('افعلل', True, 'QIV'), ('افعل', True, 'IX'), ('تفعلل', None, 'QII'),
    ('تفعل', True, 'V'), ('فاعل', None, 'III'), ('أفعل', None, 'IV'), ('فعلل', None, 'QI'),
    ('فعل', True, 'II'), ('فعل', False, 'I'), ('فع', True, 'I'),
]


def hfn_class(form):
    """صيغة HFN («أَفْعَى (أفعل ناقص)»، «فَعَّلَ (أجوف)»، «فَعَّ») ← الوزن I…X وQI…QIV"""
    m = re.search(r'\(([^)]*)\)', form)
    cands = [m.group(1).split()[0]] if m else []
    cands.append(re.sub(r'\s*\(.*', '', form).split('/')[0])
    for c in cands:
        bare, sh = strip_marks(c), 'ّ' in c
        for pat, need, cls in CLASS_OF:
            if bare == pat and (need is None or need == sh):
                return cls
    return None


class HFN:
    """فهرس الأحداث: (الجذر، الوزن) ← الأحداث، ومعنى الصيغة لكل حدث"""
    def __init__(self, path=None):
        self.path = path or next((p for p in HFN_PATHS if p and os.path.exists(os.path.join(p, 'events.csv'))), None)
        self.index = defaultdict(list)
        self.roots = set()
        self.meanings = {}
        if not self.path:
            return
        for e in csv.DictReader(open(os.path.join(self.path, 'events.csv'), encoding='utf-8')):
            cls = hfn_class(e['form'])
            self.roots.add(e['root_K'])
            if cls:
                self.index[(e['root_K'], cls)].append(e)
        mp = os.path.join(self.path, 'form_meanings.csv')
        if os.path.exists(mp):
            for r in csv.DictReader(open(mp, encoding='utf-8')):
                self.meanings.setdefault(r['event_id'], r['meaning'])

    def __bool__(self):
        return bool(self.index)


_HFN = None


def hfn():
    global _HFN
    if _HFN is None:
        _HFN = HFN()
    return _HFN


# ---------- T19c: المرشَّح من قالب الوزن ----------
# القوالب على الحروف بعد فك الشدة ونزع حرف المضارعة وهمزة الوصل واللواحق:
#   R جذري، X تكرار الجذري السابق (الشدة)، وما سواهما حرف زائد بعينه
PAST = {'I': 'RRR', 'II': 'RRXR', 'III': 'RاRR', 'IV': 'أRRR', 'V': 'تRRXR', 'VI': 'تRاRR',
        'VII': 'نRRR', 'VIII': 'RتRR', 'IX': 'RRRX', 'X': 'ستRRR', 'QI': 'RRRR', 'QII': 'تRRRR',
        'QIV': 'RRRRX'}
MUDARI = {'I': 'RRR', 'II': 'RRXR', 'III': 'RاRR', 'IV': 'RRR', 'V': 'تRRXR', 'VI': 'تRاRR',
          'VII': 'نRRR', 'VIII': 'RتRR', 'IX': 'RRRX', 'X': 'ستRRR', 'QI': 'RRRR', 'QII': 'تRRRR'}
AMR = {'I': 'RRR', 'II': 'RRXR', 'III': 'RاRR', 'IV': 'أRRR', 'V': 'تRRXR', 'VI': 'تRاRR',
       'VII': 'نRRR', 'VIII': 'RتRR', 'IX': 'RRRX', 'X': 'ستRRR', 'QI': 'RRRR'}
WASL_FORMS = {'VII', 'VIII', 'IX', 'X', 'QIV'}
SUFFIX_LEN = {  # (الزمن، توقيع اللاحقة) ← عدد حروف اللاحقة في آخر الكلمة
    ('madi', 'وا'): 2, ('madi', 'تْ'): 1, ('madi', 'تُ'): 1, ('madi', 'تَ'): 1, ('madi', 'تِ'): 1,
    ('madi', 'تُمْ'): 2, ('madi', 'تُمَا'): 3, ('madi', 'تُنَّ'): 2, ('madi', 'نَا'): 2, ('madi', 'ا'): 1,
    ('madi', 'تَا'): 2, ('madi', 'نَ'): 1,
}
SUFFIX_LEN_BY_AFFIX = {('madi', 'و'): 1}   # واو الجماعة قبل الضمير: ٱعۡتَزَلُوكُمۡ


def _plain_vowels(t):
    """الحروف والحركات بلا الخنجرية والعلامات العثمانية، والهمزات موحّدة"""
    return ''.join(_norm(c) for c in re.sub('[\u0670\u06D6-\u06ED\u0640]', '', t))


def _norm(L):
    return HAMZA.get(L, L)


def _base(text, info):
    """الحروف بعد نزع الضمير المفعول ولواحق الإسناد وحرف المضارعة وهمزة الوصل؛ والشدة حرفان"""
    # الألف الخنجرية ألفٌ (يُخَٰدِعُونَ، عَٰهَدُوا)
    toks = [(L, set(m)) for L, m in letters(re.sub('\u0670', 'ا', text.replace('آ', 'ءا')))]
    if info.get('object'):
        toks = toks[:-len(letters(info['object']))]
    sig = signature(text, info)
    k = info['kind']
    n = SUFFIX_LEN_BY_AFFIX.get((k, info.get('suffix')), 0) or SUFFIX_LEN.get((k, sig), 0)
    if k in ('mudari', 'amr') and toks and toks[-1][0] == 'ن' and SHADDA in toks[-1][1] and FATHA in toks[-1][1]:
        toks = toks[:-1]                              # نون التوكيد الثقيلة: تَجِدَنَّ
    if k in ('mudari', 'amr'):
        if toks and toks[-1][0] == 'ن' and sig in ('ون', 'ين', 'ان', 'ن'):
            toks = toks[:-1]
        if toks and toks[-1][0] == 'ا' and not toks[-1][1] and sig in ('وا؟', 'ون', 'ان'):
            toks = toks[:-1]
        if toks and toks[-1][0] in ('و', 'ي', 'ا') and not toks[-1][1] and sig in ('ون', 'ين', 'ان'):
            toks = toks[:-1]
        if toks and info.get('suffix') == 'ي' and toks[-1][0] in ('ي', 'ى'):
            toks = toks[:-1]
    elif n:
        toks = toks[:-n]
    elif k == 'madi' and len(toks) > 2 and toks[-1][0] == 'ت' and toks[-1][1] & {KASRA, SUKUN} and \
            FATHA in toks[-2][1]:
        toks = toks[:-1]                              # فُتِحَتِ: تاء التأنيث مكسورة لالتقاء الساكنين
    wasl = False
    if k == 'mudari' and toks:
        toks = toks[1:]
    elif toks and toks[0][0] == 'ا' and not toks[0][1]:
        toks, wasl = toks[1:], True
    out = []
    for L, m in toks:
        if SHADDA in m:
            out.append((L, {SUKUN}))
        out.append((L, m))
    return out, wasl, sig


class _Written(str):
    """عينُ الفعل حرفَ علةٍ متحركاً أو مشدَّداً: صامتٌ كما كُتب، لا يُبدَّل (تَدَايَنۡتُمۡ ← دين لا دون، تَعَاوَنُوا ← عون)"""


def _match(tmpl, toks):
    """→ الجذور (قوائم حروف) التي يطابق بها القالبُ الحروف، أو []"""
    if len(tmpl) != len(toks):
        return []
    rad = []
    for t, (L, m) in zip(tmpl, toks):
        if t == 'R':
            rad.append(_Written(L) if len(rad) == 1 and L in WEAK and set(m) & {FATHA, KASRA, DAMMA, SHADDA} else L)
        elif t == 'X':
            if not rad or rad[-1] != L:
                return []
        elif _norm(t) != _norm(L):
            return []
    return [rad]


def _weak_variants(rad, pos_vowels=None, cls=None, fixed=None, keep_madd=False):
    """البدائل المعتلة: الألف والياء والواو في موضع جذري ← و أو ي؛ والهمزات ← ء.
    pos_vowels: حركة ما قبل كل حرف جذري (لتعيين المحذوف/المقلوب: الضمة ← و، الكسرة ← ي)"""
    out = [[]]
    for i, L in enumerate(rad):
        opts = [_norm(L)]
        if i == fixed:
            pass                                       # حرف علة محذوف عُيِّن بحركة ما قبله
        elif L in ('ا', 'ى'):
            opts = list(WEAK)
            if i == 0 and cls in ('IV', 'III', 'VI'):
                opts = ['ء'] + opts                    # آمَنَ: أَ + أْمَنَ
        elif L in WEAK and not isinstance(L, _Written) and not (i == 1 and cls == 'I' and keep_madd):
            opts = list(dict.fromkeys([L] + list(WEAK)))   # ومضارع الثلاثي الأجوف: المدّ هو الأصل (يَتِيهُ، يَقُولُ)
        out = [o + [x] for o in out for x in opts]
    return [''.join(r) for r in out]


def _short(m):
    return bool(set(m) & {FATHA, KASRA, DAMMA})


# حركات الحروف الزائدة في القوالب: تاء الافتعال وتاء تفعّل وتفاعل مفتوحة، وسين استفعل ونون انفعل ساكنتان
AFFIX_VOWEL = {'VIII': {1: FATHA}, 'X': {0: SUKUN, 1: FATHA}, 'VII': {0: SUKUN}, 'V': {0: FATHA}, 'VI': {0: FATHA}}


def _affix_vowels_ok(cls, tmpl, seq):
    need = AFFIX_VOWEL.get(cls, {})
    for i, mk in need.items():
        if i < len(seq) and i < len(tmpl) and tmpl[i] not in 'RX' and mk not in seq[i][1]:
            return False
    return True


def candidates(text, info=None, any_pos=False, _nested=False):
    """T19c: → [(الجذر، الوزن)] مرشَّحة من قوالب الأوزان، بلا رخصة بعد.
    تُجرَّب القراءات التي تحتملها الكتابة، والرخصة تفصل بينها:
      - ما أوّله حرف من أحرف المضارعة يُجرَّب ماضياً أيضاً (أَذِنَ، نَادَىٰ، تَنَفَّسَ)، وأَفۡعِلۡ أمراً
      - الفاء والواو وهمزة الاستفهام في أوله تُجرَّب سابقةً (فَقُلۡ، أَرَءَيۡتَ)
    any_pos: يُجرَّب قالب الماضي على ما لم يثبت أنه فعل"""
    info = info or stem_info(text)
    if not _nested:
        INSERTED.clear(); READING.clear()          # حالة الكلمة وحدها: لا يتسرّب إليها ما قبلها
    if info['pos'] != 'verb' and not any_pos:
        return []
    readings, rest_c = [], []
    kind = info['kind'] if info['kind'] in ('madi', 'mudari', 'amr') else 'madi'
    if PAST_SUFFIX.search(text):
        kind = 'madi'                                # تُمۡ، نَا، تُ بعد ساكن: لاحقة الماضي تنفي المضارع (أَقۡرَرۡتُمۡ)
    readings.append((text, dict(info, kind=kind)))
    t0 = letters(text)
    if kind == 'madi' and info.get('suffix') in ('وا', 'و') and t0:
        if len(t0) == 4 and FATHA in t0[0][1]:
            readings.append((text, dict(info, kind='amr')))      # ذَرُوا، دَعُوا: أمر المثال (وذر، ودع)
        if t0[0][0] in ('ي', 'ت') and FATHA in t0[0][1]:
            readings.append((text, dict(info, kind='mudari', prefix=t0[0][0])))   # تَهِنُوا: مضارع المثال
    if t0 and t0[0][0] in ('أ', 'ن', 'ي', 'ت') and set(t0[0][1]) & {FATHA, DAMMA} and kind == 'madi' and \
            not PAST_SUFFIX.search(text) and len(t0) > 3:
        readings.append((text, dict(info, kind='mudari', prefix=t0[0][0], suffix=info['suffix'])))   # نَكۡتُمُ
    if t0 and t0[0][0] in ('أ', 'ن', 'ي', 'ت') and set(t0[0][1]) & {FATHA, DAMMA} and kind == 'mudari':
        readings.append((text, dict(info, kind='madi', suffix=info['suffix'] if info['suffix'] in ('وا', 'و') else None)))
        if t0[0][0] == 'أ' and FATHA in t0[0][1]:
            readings.append((text, dict(info, kind='amr')))
    if len(t0) > 2 and t0[0][0] in ('ف', 'و', 'أ') and t0[0][1] == {FATHA} and \
            not (t0[0][0] == 'أ' and SUKUN in t0[1][1]):   # أَصۡلَحُوا: همزة أفعل لا همزة استفهام
        rest = ''.join(L + ''.join(sorted(m)) for L, m in t0[1:])
        ri = stem_info(rest)
        if t0[0][0] == 'أ' and (ri['kind'] == 'amr' or kind == 'amr'):
            pass                                     # همزة الاستفهام لا تدخل على الأمر (أَتِمُّوا: أمر أَفۡعَلَ)
        elif not _nested:
            for c in candidates(rest, ri if ri['pos'] == 'verb' else dict(ri, pos='verb'), _nested=True):
                if c not in rest_c:
                    rest_c.append(c)                 # فَأَعۡرِضۡ: البقية بقراءاتها كلها (أمر أَفۡعَلَ)
    res = []
    for t, inf in readings:
        for c in _candidates_kind(t, inf):
            if c not in res:
                res.append(c)
            READING[c] = READING.get(c) or t
    for c in rest_c:
        if c not in res:
            res.append(c)
    return res


PAST_SUFFIX = re.compile('\u0652(تُمْ|تُمَا|تُنَّ|نَا|تُ|تَ|تِ)$')
INSERTED = set()   # (الجذر، الوزن) الذي افتُرض فيه حرف محذوف، للكلمة الجارية (يُفرَّغ مع كل كلمة)
READING = {}   # (الجذر، الوزن) ← نص القراءة التي أنتجته (بلا السابقة إن نُزعت)


def _candidates_kind(text, info):
    toks, wasl, sig = _base(text, info)
    kind = info['kind']
    alt_bases = [toks]
    if sig == 'وا؟' and toks and toks[-1][0] == 'و':
        alt_bases.append(toks[:-1])                  # تَهِنُوا: الواو للجمع لا لام الناقص
    tmpls = {'madi': PAST, 'mudari': MUDARI, 'amr': AMR}[kind]
    allowed = set(tmpls)
    if kind == 'mudari':
        first = letters(text)[0][1]
        # حركة ما قبل الآخر، والمشدَّد في الآخر حرفان: يُرَدُّ ← حركة الراء
        k = -3 if len(toks) > 2 and toks[-2][0] == toks[-1][0] and SUKUN in toks[-2][1] else -2
        pen = toks[k][1] if len(toks) >= -k else set()
        pen_alif = len(toks) >= -k and toks[k][0] == 'ا' and not toks[k][1]
        if DAMMA in first and FATHA not in pen and not pen_alif:   # والألف قبل الآخر: مجهول الأجوف أيضاً (يُسَاقُ)
            allowed &= {'II', 'III', 'IV', 'QI'}       # يُفۡعِلُ: المعلوم من المزيد (يُؤۡمِنُ ← آمَنَ)
            c1 = toks[0][1] if toks else set()
            # فَعَّلَ وفَاعَلَ والرباعي: أولها بعد حرف المضارعة مفتوح (يُعَلِّمُ، يُقَاتِلُ، يُدَحۡرِجُ)؛
            # وأَفۡعَلَ: ساكن أو مكسور في المضعَّف والأجوف (يُخۡرِجُ، يُحِبُّ، يُقِيمُ)
            allowed -= {'IV'} if FATHA in c1 else {'II', 'III', 'QI'}
        elif FATHA in first:
            allowed -= {'II', 'III', 'IV', 'QI'}       # يَفۡعَلُ: لا فعّل ولا فاعل ولا أفعل
    out = []
    for cls in allowed:
        tmpl = tmpls[cls]
        if kind == 'madi' and (cls in WASL_FORMS) != wasl:
            continue
        seqs = list(alt_bases)
        # افتعل وحده: تاء الافتعال تُقلب طاءً أو دالاً (ٱصۡطَبِرۡ، ٱدَّكَرَ)
        if cls == 'VIII' and len(toks) > 1 and toks[1][0] in ('ط', 'د'):
            seqs.append([toks[0], ('ت', toks[1][1])] + toks[2:])
        for seq in seqs:
            if kind == 'madi' and not sig and seq and not (FATHA in seq[-1][1] or seq[-1][0] in ('ى', 'ا')) and \
                    not text.endswith(('تْ', 'تِ')):
                continue                               # الماضي بلا لاحقة آخره مفتوح (يَكُنۡ ليس ماضياً)
            if kind == 'madi' and cls in ('V', 'VI') and FATHA not in seq[0][1]:
                continue                               # تَفَعَّلَ وتَفَاعَلَ: تاؤهما مفتوحة (تُحِبُّوا ليس ماضيهما)
            if kind == 'madi' and cls == 'I' and len(seq) == 3 and (not _short(seq[0][1]) or
                                                                     SUKUN in seq[1][1] and seq[1][0] != seq[2][0]):
                continue                               # ماضي الثلاثي: فَعَلَ يتحرك أوله وثانيه (يَدۡعُوا ليس ماضي «ودع»)
            if not _affix_vowels_ok(cls, tmpl, seq):
                continue
            for rad in _match(tmpl, seq):
                out.append((rad, cls, None))           # (الجذر، الوزن، موضع المحذوف المعيَّن)
            if len(seq) != len(tmpl) - 1:
                continue
            # المحذوف حرف علة واحد، يُعرف بحركات ما بقي:
            ridx = [i for i, t in enumerate(tmpl) if t == 'R']
            for j in ridx:
                before = seq[j - 1][1] if j > 0 else set()
                after = seq[j][1] if j < len(seq) else None
                if j == ridx[0] and cls == 'I' and kind in ('mudari', 'amr') and after is not None and \
                        after & {KASRA, FATHA}:
                    ws = ['و']                          # المثال: يَلِدۡ، عِدۡ ← و ل د
                elif j == ridx[1] and _short(before) and after is not None and SUKUN in after:
                    # الأجوف: قُلۡ ← و، بِعۡ ← ي؛ وفي الماضي مع ضمير متحرك لا تعيّن الحركةُ الحرف (خِفۡتُمۡ ← خوف)
                    ws = list(WEAK) if kind == 'madi' or cls != 'I' else ['و'] if DAMMA in before else \
                        ['ي'] if KASRA in before else list(WEAK)     # والمزيد: يُصِبۡ، يَسۡتَطِعۡ (صوب، طوع)
                elif j == ridx[-1] and after is None and _short(before) and \
                        (kind == 'mudari' and not text.endswith('نَّ') or     # ولا حذف مع نون التوكيد (تَجِدَنَّ)
                         kind == 'amr' and (wasl or cls != 'I' or SUKUN in seq[0][1]) or
                         kind == 'madi' and (sig in ('وا', 'تْ', 'تَا') or text.endswith('تْ') or text.endswith('تِ'))):
                    # الناقص: يَدۡعُ، أَلۡقَتۡ، وٱدۡعُ؛ وأمر الثلاثي الناقص لا يكون بلا همزة وصل (كُلُوا ليس ناقصاً).
                    # والضمة قبل واو الجمع للجمع لا للجذر (فَأۡتُوا): فالحرف واوٌ أو ياء
                    plural = sig in ('وا', 'ون', 'وا؟')
                    ws = list(WEAK) if plural else ['و'] if DAMMA in before else ['ي'] if KASRA in before else list(WEAK)
                elif j == ridx[0] and cls == 'I' and kind == 'amr' and not wasl and after is not None and _short(after):
                    ws = ['ء']                          # كُلۡ، خُذۡ، مُرۡ: أمر المهموز الفاء بلا همزة (أكل، أخذ، أمر)
                elif j == ridx[1] and kind in ('mudari', 'amr') and before and FATHA in before and \
                        len(seq) - j <= 1 and (j == len(seq) or seq[j][0] in MADD):
                    ws = ['ء']                          # رأى: الهمزة تُحذف في المضارع والأمر (يَرَىٰ، تَرَوُنَّ)
                else:
                    continue
                for w in ws:
                    for rad in _match(tmpl, seq[:j] + [(w, set())] + seq[j:]):
                        out.append((rad, cls, ridx.index(j)))   # المحذوف عُيِّن بالحركة: لا يُبدَّل
                        INSERTED.add((''.join(_norm(x) for x in rad), cls))
    res = []
    for rad, cls, fixed in out:
        rad_opts = [rad] + ([[x] + rad[1:] for x in ('و', 'ي', 'ء')] if cls == 'VIII' and rad[0] == 'ت' else [])
        for r in rad_opts:
            for root in _weak_variants(r, cls=cls, fixed=fixed, keep_madd=kind in ('mudari', 'amr')):
                if (root, cls) not in res:
                    res.append((root, cls))
    return res


def _madi_exact(t, verb):
    """الماضي المكتوب بلاحقته يطابق فعل HFN حرفاً وحركة إلا حركة لامه (وَضَعَتۡهَا ← وَضَعَ، فَشِلۡتُمۡ ← فَشِلَ):
    حروفه وحركاته إلى ما قبل اللام هي هي، ثم اللام، ثم لواحق الإسناد والمفعول"""
    vt, tt = letters(verb), letters(t)
    k = len(vt) - 1
    if k < 2 or len(tt) <= k + 0 or [x for x in tt[:k]] != [x for x in vt[:k]] or tt[k][0] != vt[k][0]:
        return False
    return len(tt) > k + 1 and all(L in 'تنواهمكيا' for L, _ in tt[k + 1:])


def morph(text, info=None):
    """→ dict(cells, candidates, licensed=[…], status, root, form, wazn, evidence) أو None إن لم يكن فعلاً.
    بوابة الحماية الدستورية أولاً (sarf/protected.py): العوامل المائة والمبنيات والأسماء الذهبية لا يُستخرج لها جذر،
    فالحالة not_applicable (root_status = NOT_APPLICABLE، reason = CONSTITUTIONAL_PROTECTED_CLASS) بلا مرشّحات؛
    فإن احتمل الموضع وحدةً محمية وتحليلاً آخر فالحالة class_deferred: الحماية باقية، والتحليل الآخر بديلٌ لا يُقبل"""
    from .protected import protected
    prot = protected(text)
    if prot and not prot['ambiguous']:
        return dict(cells=cell_code(cells(text)), candidates=[], licensed=[], kind=None, level=None, selection={},
                    status='not_applicable', root=None, form_class=None, root_status=prot['root_status'],
                    reason=prot['reason'], protected=prot)
    out = _morph(text, info)
    if prot and out is not None:
        alt = {k: out.get(k) for k in ('status', 'root', 'form_class', 'level', 'reason')}
        out.update(status='class_deferred', root=None, form_class=None, level=None, root_status='CLASS_DEFERRED',
                   protected=prot, alternative=alt,
                   reason=f'تعيين الفئة مؤجَّل: وحدةٌ محمية مرشّحة ({prot["cls"]} «{prot["identity"]}») أو {prot["alternative"]}')
    elif prot:
        return dict(cells=cell_code(cells(text)), candidates=[], licensed=[], kind=None, level=None, selection={},
                    status='not_applicable', root=None, form_class=None, root_status=prot['root_status'],
                    reason=prot['reason'], protected=prot)
    return out


def _morph(text, info=None):
    info = info or stem_info(text)
    exact_only = info['pos'] != 'verb'
    shown = text
    if info.get('moved'):                     # قُلِ ٱللَّهُمَّ: الكسر لالتقاء الساكنين، والأصل السكون
        text = text[:-1] + SUKUN
    cands = candidates(text, info, any_pos=exact_only)
    if not cands:
        return None
    H = hfn()
    licensed = []
    surface = _plain_vowels(text)
    for root, cls in cands:
        for e in H.index.get((root, cls), []):
            if exact_only and _plain_vowels(e['verb']) not in (surface, _plain_vowels(READING.get((root, cls), text))):
                continue                     # ما لم يثبت أنه فعل: لا يُرخَّص إلا بمطابقة فعل HFN حرفاً وحركة (كَتَبَ)
            licensed.append(dict(root=root, form_class=cls, hfn_form=e['form'], verb=e['verb'],
                                 masdar=e['masdar'], event_id=e['event_id'], source=e['source'],
                                 sibawayh=e['sibawayh_rules'], tier=e['tier'],
                                 meaning=H.meanings.get(e['event_id'])))
    # قراءة النص كله تطابق فعلاً في HFN حرفاً وحركة (وَضَعَتۡ ← وَضَعَ بلاحقته): تُقدَّم على قراءةٍ نُزعت منها سابقة
    # (ضَعَتۡ ← «ضعو»)، فالحرف الذي بقي أصلياً بالمطابقة لا يُعاد سابقةً
    exact = [x for x in licensed if READING.get((x['root'], x['form_class'])) == text and
             (_plain_vowels(x['verb']) == _plain_vowels(text) or _madi_exact(text, x['verb']))]
    pairs_x = {(x['root'], x['form_class']) for x in exact}
    others = [x for x in licensed if (x['root'], x['form_class']) not in pairs_x]   # المنافس جذرٌ أو وزنٌ آخر
    def _tier(xs):
        return min((x['tier'][:1] or 'Z') for x in xs) if xs else 'Z'
    selection = dict(candidates=[dict(root=x['root'], form=x['form_class'], verb=x['verb'], tier=x['tier'][:1],
                                      reading=READING.get((x['root'], x['form_class'])),
                                      exact=x in exact) for x in licensed])
    # الحسم بين قراءة النص كله المطابقة وقراءةٍ نُزعت منها سابقة: تُقدَّم المطابقة إن كانت شهادتها في HFN أقوى
    # من كل منافسٍ (وَضَعَتۡ: «وضع» C على «ضعو» E)؛ فإن تساوتا أو ضعفت (وَلَسۡتُمۡ: «ولس» C و«ليس» C؛ تَهِنُواْ: «تهن» E
    # و«وهن» C) بقي التعارض مؤجَّلاً بمرشحيه، ولا يُختار بأولوية البحث
    # الترجيح لا الإثبات (مراجعة التقرير الخامسة ٣): قراءة النص كله المطابقة حرفاً وحركة تُرجَّح على منافسٍ لا يطابق،
    # والمنافس محفوظٌ بسببه؛ فالنتيجة «مرجَّح» لا «مثبت»، و«مثبت» ما لا منافس له
    if exact and others:
        selection['decision'] = (f'ترجيح بالمطابقة: قراءة النص كله تطابق فعلاً في HFN حرفاً وحركة (شهادتها {_tier(exact)})، '
                                 f'ومنافسها لا يطابق (شهادته {_tier(others)})؛ والمنافس محفوظ')
        selection['ranked'] = True
        selection['alternatives'] = sorted({f"{x['root']}/{x['form_class']}" for x in others})
        licensed = [x for x in licensed if (x['root'], x['form_class']) in pairs_x]
    elif exact:
        selection['decision'] = 'قراءة النص كله المطابقة لفعل HFN (لا منافس)'
    if info['kind'] == 'madi' and licensed:
        # الماضي: الحدث الذي يطابق فعلُه المكتوب حرفاً وحركة يُقدَّم على أخيه في الوزن (جَعَلَ لا جَعِلَ)
        same = [x for x in licensed if _plain_vowels(x['verb']) == surface]
        if same:
            licensed = same + [x for x in licensed if x not in same]
    pairs = list(dict.fromkeys((x['root'], x['form_class']) for x in licensed))
    out = dict(cells=cell_code(cells(shown)), candidates=cands, licensed=licensed, kind=info['kind'],
               level=None, selection=selection)
    if not H:
        out.update(status='deferred', reason='لا معجم مرخِّص (HFN غير موجود)')
        return out
    if exact_only and pairs:
        # يطابق فعلاً في HFN حرفاً وحركة، ولم يثبت أنه فعل بالكتابة (مَالَ: فعلٌ أو اسم): مرشَّح لا مقبول
        out.update(status='deferred', level='lemma', reason='يطابق فعل HFN «' + licensed[0]['verb'] +
                   '» حرفاً وحركة، ولم يثبت بالكتابة أنه فعل', root=None)
        return out
    # الاقتصاد: قراءةٌ لا تفترض حرفاً محذوفاً وجذرها مسجَّل تمنع قبول قراءةٍ تفترضه (يُسِرُّونَ: سرر لا سرو)
    direct = [(r, c) for r, c in cands if (r, c) not in INSERTED and r in H.roots]
    if len(pairs) == 1 and pairs[0] in INSERTED and any(d != pairs[0] for d in direct):
        out.update(status='deferred', reason='قراءة بحرف محذوف (' + f'{pairs[0][0]} {pairs[0][1]}' +
                   ') تنافسها قراءة تامة جذرها مسجَّل: ' + '، '.join(f'{r} ({c})' for r, c in direct[:3]))
        return out
    if len(pairs) == 1:
        out.update(status='accepted', root=pairs[0][0], form_class=pairs[0][1], level='event')
        if selection.get('ranked'):
            # الترجيح منفصلٌ عن الإثبات (مراجعة التقرير السادسة ٦): المرجَّح لا يُقبل ولا يدخل الإغلاق ولا الاستدلال،
            # ويُحفظ بقراءته ومنافسيه حتى يُحسم
            out.update(status='ranked', level='ranked', reason='مرجَّح لا مثبت: ' + selection['decision'] +
                       ' — البدائل: ' + '، '.join(selection['alternatives']))
        return out
    if pairs:
        out.update(status='deferred', reason='أكثر من جذر أو وزن مرخَّص: ' +
                   '، '.join(f'{r} ({c})' for r, c in pairs))
        return out
    # رخصة الجذر: الجذر في HFN والوزن من القالب، ولا حدث مسجَّل (آمَنَ، ٱتَّقَى): يُقبل الجذر بشهادته،
    # ويبقى الحدث ومعناه مؤجَّلين. ولا يُطبَّق على ما لم يثبت أنه فعل.
    rooted = list(dict.fromkeys((r, c) for r, c in cands if r in H.roots)) if not exact_only else []
    if len(rooted) == 1:
        out.update(status='accepted', root=rooted[0][0], form_class=rooted[0][1], level='root',
                   reason='الجذر مسجَّل في HFN، والوزن بالقالب؛ ولا حدث مسجَّل بهذا الوزن، فالحدث ومعناه مؤجَّلان')
    elif rooted:
        out.update(status='deferred', reason='أكثر من جذر مسجَّل في HFN، ولا حدث بالوزن: ' +
                   '، '.join(f'{r} ({c})' for r, c in rooted))
    else:
        out.update(status='deferred', reason='لم يثبت بالكتابة أنه فعل، ولا يطابق فعلاً في HFN حرفاً وحركة'
                   if exact_only else 'لا رخصة: لم يرد أيٌّ من المرشَّحات في HFN')
    return out


# ---------- الطبقة في الآية ----------
WAZN = {'I': 'فَعَلَ', 'II': 'فَعَّلَ', 'III': 'فَاعَلَ', 'IV': 'أَفْعَلَ', 'V': 'تَفَعَّلَ', 'VI': 'تَفَاعَلَ',
        'VII': 'انْفَعَلَ', 'VIII': 'افْتَعَلَ', 'IX': 'افْعَلَّ', 'X': 'اسْتَفْعَلَ', 'QI': 'فَعْلَلَ',
        'QII': 'تَفَعْلَلَ', 'QIII': 'افْعَنْلَلَ', 'QIV': 'افْعَلَلَّ'}


def soundness(root):
    """صحة الجذر واعتلاله (الثلاثي): مهموز، مضعَّف، مثال، أجوف، ناقص، لفيف؛ وإلا سالم"""
    if len(root) != 3:
        return 'salim' if 'ء' not in root and not set(root) & set(WEAK) else None
    r1, r2, r3 = root
    w1, w2, w3 = r1 in WEAK, r2 in WEAK, r3 in WEAK
    if w2 and w3:
        return 'lafif_maqrun'
    if w1 and w3:
        return 'lafif_mafruq'
    if w1:
        return 'mithal'
    if w2:
        return 'ajwaf'
    if w3:
        return 'naqis'
    if r2 == r3:
        return 'mudaaf'
    if 'ء' in root:
        return 'mahmuz'
    return 'salim'


def verse_morph(segs, governed=None, nouns=()):
    """لكل جذع في الآية: (رقم الكلمة، رقم الخانة) ← Morph مختصراً.
    governed: الجذوع التي ثبتت فعليتها بعاملٍ مقبول فيها، فتُعامَل معاملة الفعل الثابت.
    والطبقة للفعل: فما ثبتت اسميته لا يُحلَّل (بعد «أل»، أو منوَّناً، أو مجروراً بحرف جرٍّ مقبول: nouns)"""
    governed = governed or {}
    out = []
    for seg in segs:
        for s in seg['slots']:
            if s['type'] != 'جذع':
                continue
            prev_al = s['index'] > 0 and seg['slots'][s['index'] - 1]['type'] == 'أل'
            if prev_al or (seg['word_index'], s['index']) in nouns or set(s['text']) & {FATHATAN, DAMMATAN, KASRATAN}:
                continue
            info = stem_info(s['text'])
            if (seg['word_index'], s['index']) in governed:
                info = dict(info, pos='verb')
            m = morph(s['text'], info)
            if not m:
                continue
            top = m['licensed'][0] if m['licensed'] else None
            out.append(dict(word_index=seg['word_index'], slot=s['index'], status=m['status'], level=m.get('level'),
                            root=m.get('root'), form_class=m.get('form_class'), cells=m['cells'],
                            reason=m.get('reason'), n_candidates=len(m['candidates']),
                            event=({k: top[k] for k in ('event_id', 'verb', 'masdar', 'hfn_form', 'source',
                                                         'sibawayh', 'meaning')}
                                   if top and m['status'] == 'accepted' and m.get('level') == 'event' else None)))
    return out
