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

المصدر: HFN release_v36 (CC0؛ خط الأساس المعتمد)، يُقرأ من مكانه: متغير البيئة SARF_HFN، أو ../husseinframenet/release/release_v36،
أو data/hfn. فإن لم يوجد بقيت الجذور كلها مرشَّحةً بلا رخصة (مؤجَّلة).
"""
import csv, os, re
from collections import defaultdict

from .chars import FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN, letters, strip_marks
from .affix import stem_info
from .agreement import signature

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# خط أساس المعجم المعتمد: HFN release_v36 (حكم المالك، SARF_SEQUENTIAL_COMPLETION_PLAN_01، 5 نوفمبر 2026)
HFN_BASELINE = 'release_v36'
HFN_PATHS = [os.environ.get('SARF_HFN', ''),
             os.path.join(os.path.dirname(HERE), 'husseinframenet', 'release', 'release_v36'),
             os.path.expanduser('~/arabic-net/HusseinFrameNet/release/release_v36'),
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


# تمثيل همزة الوصل في مدخلات HFN (SARF_COMPLETION_FROM_REPORT_063 §٥): v36 يكتبها «ا»، وv47 يكتبها «ٱ» (U+0671) في أوزان
# انفعل وافتعل وافعلّ واستفعل وأشباهها ومصادرها. والتمثيل المعلن في المستهلك «ا» (تمثيل خط الأساس الذي بُنيت عليه القوالب والمطابقة)،
# ويُحفظ المكتوب في المورد بعينه (verb_written / lemma_written). وهو تحويلٌ مسمّى للحرف الأول وحده، لا تجريدٌ للحركات
WASL_SOURCE, WASL_REPRESENTATION = '\u0671', 'ا'


def hfn_wasl(text):
    """→ (النص بالتمثيل المعلن، هل حُوِّل)؛ همزة الوصل في أول الكلمة وحدها"""
    if text and text[0] == WASL_SOURCE:
        return WASL_REPRESENTATION + text[1:], True
    return text, False


def hfn_withdrawn(e):
    """الحدث المسحوب في الإصدار (event_review_v36 يبدأ بـ WITHDRAWN): لا يُقرأ حدثاً حياً في أي فهرس"""
    return (e.get('event_review_v36') or '').startswith('WITHDRAWN')


class HFN:
    """فهرس الأحداث: (الجذر، الوزن) ← الأحداث، ومعنى الصيغة لكل حدث"""
    def __init__(self, path=None):
        env_ = os.environ.get('SARF_HFN', '')
        if not path and env_ and not os.path.exists(os.path.join(env_, 'events.csv')):
            # مسارٌ صريحٌ غير موجود لا يُستبدل به غيره صامتاً: كان يرجع إلى release_v36 فيُظنّ التشغيل على إصدارٍ لم يُستعمل
            raise FileNotFoundError(f'SARF_HFN يشير إلى مسارٍ ليس فيه events.csv: {env_} — لا رجوع صامت إلى إصدارٍ آخر')
        if not path and env_ and os.path.basename(os.path.normpath(env_)) != HFN_BASELINE and \
                os.environ.get('SARF_HFN_RELEASE_OK', '') != os.path.basename(os.path.normpath(env_)):
            # إصدارٌ موجودٌ غير خط الأساس (بيئةٌ تحمل release_v19 مثلاً): لا يُقرأ صامتاً؛ ومن أراده يسمّيه صراحةً
            raise RuntimeError(f'SARF_HFN يشير إلى {os.path.basename(os.path.normpath(env_))}، وخط الأساس المعتمد {HFN_BASELINE}: '
                               f'لتشغيلٍ مقصود عليه عيّن SARF_HFN_RELEASE_OK={os.path.basename(os.path.normpath(env_))}')
        self.path = path or next((p for p in HFN_PATHS if p and os.path.exists(os.path.join(p, 'events.csv'))), None)
        self.index = defaultdict(list)
        self.roots = set()
        self.meanings = {}                              # الأول لكل حدث (للمستهلكين القدامى)
        self.meanings_all = defaultdict(list)           # §٥: كل المعاني بترتيبها في المورد، لا يُسقط شيءٌ منها
        self.withdrawn = []                             # §٥: الأحداث المسحوبة بمعرّفها وسببها وإصدارها وبصمة الملف
        self.wasl_converted = 0
        self.release = os.path.basename(os.path.normpath(self.path)) if self.path else None
        self.events_sha256 = None
        if not self.path:
            return
        import hashlib
        ep = os.path.join(self.path, 'events.csv')
        self.events_sha256 = hashlib.sha256(open(ep, 'rb').read()).hexdigest()
        self.withdrawn_ids = set()
        for e in csv.DictReader(open(ep, encoding='utf-8')):
            if hfn_withdrawn(e):
                self.withdrawn.append(dict(event_id=e['event_id'], root=e['root_K'], verb=e['verb'], form=e['form'],
                                           reason=e['event_review_v36'], release=self.release, events_sha256=self.events_sha256))
                self.withdrawn_ids.add(e['event_id'])
                continue
            v_, conv = hfn_wasl(e['verb'])
            if conv:
                e['verb_written'], e['verb'] = e['verb'], v_
                self.wasl_converted += 1
            cls = hfn_class(e['form'])
            self.roots.add(e['root_K'])
            if cls:
                self.index[(e['root_K'], cls)].append(e)
        mp = os.path.join(self.path, 'form_meanings.csv')
        if os.path.exists(mp):
            for r in csv.DictReader(open(mp, encoding='utf-8')):
                if r['event_id'] in self.withdrawn_ids:
                    continue
                self.meanings.setdefault(r['event_id'], r['meaning'])
                self.meanings_all[r['event_id']].append(dict(meaning=r['meaning'], concept_id=r.get('concept_id'),
                                                             status=r.get('status'), rank=r.get('rank')))

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


MATCH_TRANSFORMS = {
    'UTHMANI_MARKS_AND_TATWEEL_REMOVED': 'حذف الألف الخنجرية والعلامات العثمانية (U+06D6–U+06ED) والتطويل',
    'HAMZA_SEAT_UNIFIED': 'توحيد كراسي الهمزة (أ إ ؤ ئ آ ← ء)',
}


def match_transformations(a, b):
    """AR03 §٩: → قائمة التحويلات المسمّاة التي تحققت بها المطابقة ([] = NFC وحده)، أو None إن لم تتحقق"""
    import unicodedata
    nf = lambda x: unicodedata.normalize('NFC', x or '')
    if nf(a) == nf(b):
        return []
    marks = lambda x: nf(re.sub('[\u0670\u06D6-\u06ED\u0640]', '', x or ''))
    if marks(a) == marks(b):
        return ['UTHMANI_MARKS_AND_TATWEEL_REMOVED']
    if _plain_vowels(a) == _plain_vowels(b):
        return (['UTHMANI_MARKS_AND_TATWEEL_REMOVED'] if marks(a) != nf(a) or marks(b) != nf(b) else []) + ['HAMZA_SEAT_UNIFIED']
    return None


def match_policy(a, b):
    """AR02 §١٢، مضبوطة في AR03 §٩: NFC_LITERAL تعني NFC وحده؛ وغيرها اسم أقوى تحويلٍ لزم (UTHMANI_MARKS_AND_TATWEEL_REMOVED أو
    HAMZA_SEAT_UNIFIED)، والقائمة الكاملة في match_transformations؛ أو None"""
    t = match_transformations(a, b)
    if t is None:
        return None
    return t[-1] if t else 'NFC_LITERAL'


MATCH_POLICY_AR = {'NFC_LITERAL': 'حرفاً وحركة', 'UTHMANI_MARKS_AND_TATWEEL_REMOVED': 'حرفاً وحركة بعد حذف العلامات العثمانية والتطويل',
                   'HAMZA_SEAT_UNIFIED': 'حرفاً وحركة بعد توحيد كراسي الهمزة'}


def _norm(L):
    return HAMZA.get(L, L)


def _plain_toks(text):
    """حروف التحليل: الخنجرية ألف، و«آ» همزةٌ مفتوحة بعدها ألف مدّ (آبَ = ءَابَ، آمَنَ = ءَامَنَ). الرسم الأصلي لا يُمسّ"""
    return [(L, set(m)) for L, m in letters(re.sub('\u0670', 'ا', text.replace('آ', 'ء' + FATHA + 'ا')))]


def _expand_base(toks):
    """همزة الوصل أولاً تُنزع، والشدة حرفان"""
    wasl = False
    if toks and toks[0][0] == 'ا' and not toks[0][1]:
        toks, wasl = toks[1:], True
    out = []
    for L, m in toks:
        if SHADDA in m:
            out.append((L, {SUKUN}))
        out.append((L, m))
    return out, wasl


def _base(text, info):
    """الحروف بعد نزع الضمير المفعول ولواحق الإسناد وحرف المضارعة وهمزة الوصل؛ والشدة حرفان"""
    # الألف الخنجرية ألفٌ (يُخَٰدِعُونَ، عَٰهَدُوا)
    toks = _plain_toks(text)
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


def candidates(text, info=None, any_pos=False, _nested=False, extended=False):
    """T19c: → [(الجذر، الوزن)] مرشَّحة من قوالب الأوزان، بلا رخصة بعد.
    تُجرَّب القراءات التي تحتملها الكتابة، والرخصة تفصل بينها:
      - ما أوّله حرف من أحرف المضارعة يُجرَّب ماضياً أيضاً (أَذِنَ، نَادَىٰ، تَنَفَّسَ)، وأَفۡعِلۡ أمراً
      - الفاء والواو وهمزة الاستفهام في أوله تُجرَّب سابقةً (فَقُلۡ، أَرَءَيۡتَ)
    any_pos: يُجرَّب قالب الماضي على ما لم يثبت أنه فعل
    extended (AR01، لمحرّك الجذر _morph وحده حيث الرخصة مقيّدة): قراءة الكلمة كلها بلا ضمير مفعول (R5)، والألف الأخيرة لامَ
    الناقص (R2). ولا تصل إلى مستهلكين آخرين (رخصة العامل) بلا قيدها"""
    info = info or stem_info(text)
    if not _nested:
        INSERTED.clear(); READING.clear()          # حالة الكلمة وحدها: لا يتسرّب إليها ما قبلها
    if info['pos'] != 'verb' and not any_pos:
        return []
    readings, rest_c = [], []
    kind = info['kind'] if info['kind'] in ('madi', 'mudari', 'amr') else 'madi'
    if PAST_SUFFIX.search(text):
        kind = 'madi'                                # تُمۡ، نَا، تُ بعد ساكن: لاحقة الماضي تنفي المضارع (أَقۡرَرۡتُمۡ)
    readings.append((text, dict(info, kind=kind, extended=extended)))
    if extended and info.get('object') and not _nested:
        # الطرف يشبه ضميراً متصلاً، وقد يكون من أصل الكلمة: تُجرَّب الكلمة كلها ماضياً بلا لاحقة، ولا تُرخَّص هذه
        # القراءة إلا بمطابقة فعل HFN حرفاً وحركة (UNPEELED)
        readings.append((text, dict(info, kind='madi', object=None, suffix=None, prefix=None, unpeeled=True)))
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
    if not _nested:
        UNPEELED.clear()
    for t, inf in readings:
        for c in _candidates_kind(t, inf):
            if inf.get('unpeeled'):
                if c in res:
                    continue
                UNPEELED.add(c)
            if c not in res:
                res.append(c)
            READING[c] = READING.get(c) or t
    for c in rest_c:
        if c not in res:
            res.append(c)
    return res


PAST_SUFFIX = re.compile('\u0652(تُمْ|تُمَا|تُنَّ|نَا|تُ|تَ|تِ)$')
EXTENDED = set()   # ما زادته القراءات الموسّعة على المرشّحات الأساسية للكلمة الجارية
UNPEELED = set()   # (الجذر، الوزن) من قراءة الكلمة كلها بلا ضمير مفعول: لا تُرخَّص إلا بالمطابقة التامة
INSERTED = set()   # (الجذر، الوزن) الذي افتُرض فيه حرف محذوف، للكلمة الجارية (يُفرَّغ مع كل كلمة)
READING = {}   # (الجذر، الوزن) ← نص القراءة التي أنتجته (بلا السابقة إن نُزعت)


def _candidates_kind(text, info):
    toks, wasl, sig = _base(text, info)
    kind = info['kind']
    alt_bases = [toks]
    if info.get('extended') and kind == 'madi' and sig in ('ا', 'تَا') and not info.get('object'):
        full, w_full = _expand_base(_plain_toks(text))
        # شكل الماضي وحده: أوله مفتوح أو بعد همزة وصل، وما قبل الألف مفتوح (دَعَا، ٱشۡتَرَىٰ)؛ لا «كُلَا» (أمر المثنى)
        # والقراءة بعد نزع الألف أقصر من أي ماضٍ (دَعَ، بَ): فإن صلحت ماضياً تاماً (ٱسۡتَبَقَ + ا) فالألف للتثنية، ولا تُولَّد
        if w_full == wasl and full != toks and len(toks) <= 2 and len(full) >= 3 and (FATHA in full[0][1] or w_full) and \
                FATHA in full[-2][1]:
            alt_bases.append(full)                   # دَعَا، بَتَا: الألف لام الناقص لا ألف التثنية (والرخصة تفصل)
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
            if toks[0][0] == 'د' and toks[1][0] == 'د':
                # سيبويه (الكتاب ٤/٤٦٨): اذتكر ← ادَّكَرَ؛ فالدال المدغمة فاؤها دالٌ أو ذال
                seqs.append([('ذ', toks[0][1]), ('ت', toks[1][1])] + toks[2:])
        for seq in seqs:
            if not seq:
                continue                               # تسلسلٌ فارغ بعد نزع اللواحق (أَتَاكَ في الرسم الإملائي): لا قالب يطابقه
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


# لواحق الماضي (AR03 §٩): بحروفها وحركاتها، وحركة اللام التي تقتضيها؛ والمفعول بعد الفاعل لا قبله
SUBJ_SUFFIXES = (('تُ', SUKUN, False), ('تَ', SUKUN, False), ('تِ', SUKUN, False), ('تُمَا', SUKUN, False), ('تُمْ', SUKUN, False),
                 ('تُمُو', SUKUN, True), ('تُنَّ', SUKUN, False), ('نَا', SUKUN, False), ('نَ', SUKUN, False), ('تْ', FATHA, False),
                 ('تَا', FATHA, False), ('ا', FATHA, False), ('وا', DAMMA, False), ('و', DAMMA, True), ('', FATHA, True))
OBJ_SUFFIXES = ('هُ', 'هِ', 'هَا', 'هُمْ', 'هُمَا', 'هُنَّ', 'كَ', 'كِ', 'كُمْ', 'كُمَا', 'كُنَّ', 'نِي', 'نَا')
_SUFFIX_TRANSFORMS = (('\u06E1', SUKUN, 'UTHMANI_SUKUN_AS_SUKUN'), ('\u06DF', '', 'UTHMANI_SILENT_MARK_REMOVED'),
                      ('\u06E5', '', 'UTHMANI_SILAH_MARK_REMOVED'), ('\u06E6', '', 'UTHMANI_SILAH_MARK_REMOVED'))


def madi_suffix_parse(t, verb):
    """→ None إن لم يطابق الجذع حروف الماضي وحركاته إلى ما قبل اللام؛ وإلا dict(status, spans, transformations):
    MATCHED_STEM_AND_LICENSED_SUFFIX إن انقسم الباقي لاحقةَ إسنادٍ تقتضي حركة اللام المكتوبة ثم ضميرَ مفعولٍ واحداً على الأكثر
    (بهذا الترتيب، حرفاً وحركة)، وإلا SUFFIX_NOT_LICENSED (كَتَبَتَتَ). وكل تحويلٍ للرسم العثماني يُسمّى"""
    import unicodedata
    tr = []
    for a, b, name in _SUFFIX_TRANSFORMS:
        if a in t:
            t = t.replace(a, b)
            if name not in tr:
                tr.append(name)
    t = unicodedata.normalize('NFC', t)
    vt, tt = letters(verb), letters(t)
    k = len(vt) - 1
    if k < 2 or len(tt) <= k or list(tt[:k]) != list(vt[:k]) or tt[k][0] != vt[k][0]:
        return None
    lam = tt[k][1]
    rest = tt[k + 1:]
    if not rest:
        return None                          # لا لاحقة: الكلمة على حروف الماضي بحركة لامٍ أخرى (بَرِمْ) — خارج قاعدة اللواحق
    stem_span = ''.join(L + ''.join(sorted(m)) for L, m in tt[:k + 1])

    def eat(seq, inv):
        it = letters(inv)
        if len(seq) < len(it) or [L for L, _ in seq[:len(it)]] != [L for L, _ in it]:
            return None
        moved = False
        for j, ((L, m), (L2, m2)) in enumerate(zip(seq[:len(it)], it)):
            if set(m) == set(m2):
                continue
            if j == len(seq) - 1 == len(it) - 1 and set(m2) <= {SUKUN} and len(set(m)) == 1 and set(m) <= {FATHA, DAMMA, KASRA}:
                moved = True                 # الساكن آخر الكلمة يُحرَّك لالتقاء الساكنين (قَالَتِ ٱمْرَأَتُ)
                continue
            return None
        return len(it), moved
    incomplete = None
    for subj, need, obj_only in SUBJ_SUFFIXES:
        if need not in lam:
            continue
        seq, assim = rest, False
        r = eat(seq, subj) if subj else (0, False)
        if r is None and subj.startswith('ت') and tt[k][0] in 'دطت' and rest and rest[0][0] == 'ت' and SHADDA in rest[0][1]:
            # تاء الفاعل بعد لامٍ دالٍ أو طاءٍ أو تاء تُدغم فيها فتُكتب مشدّدة (وَعَدتُّمْ، بَسَطتَّ)
            seq = [(rest[0][0], frozenset(set(rest[0][1]) - {SHADDA}))] + list(rest[1:])
            r, assim = eat(seq, subj), True
        if r is None:
            continue
        n, moved = r
        tail = seq[n:]
        if obj_only and not tail and subj:
            incomplete = subj                # «و» أو «تُمُو» بلا ألف آخر الامتداد: ضمير المفعول بعده في خانةٍ أخرى (اتَّبَعُو|هُ)
            continue
        objs = [None] if not tail else []
        for o in OBJ_SUFFIXES if tail else ():
            r2 = eat(tail, o)
            if r2 and r2[0] == len(tail):
                objs.append((o, r2[1]))
        for ob in objs:
            if ob is None and obj_only:
                continue
            ops = list(tr) + (['TA_ASSIMILATED_AFTER_DAL_TA'] if assim else []) + \
                (['FINAL_SUKUN_MOVED'] if moved and not tail or (ob and ob[1]) else [])
            return dict(status='MATCHED_STEM_AND_LICENSED_SUFFIX',
                        spans=dict(stem=stem_span, subject_suffix=subj or None, object_suffix=ob[0] if ob else None),
                        transformations=ops)
    if incomplete:
        return dict(status='SUFFIX_REQUIRES_OBJECT_OUTSIDE_SPAN', spans=dict(stem=stem_span, subject_suffix=incomplete), transformations=tr)
    return dict(status='SUFFIX_NOT_LICENSED', spans=dict(stem=stem_span, rest=''.join(L + ''.join(sorted(m)) for L, m in rest)),
                transformations=tr)


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
    if out is not None:
        out['faces'] = morph_faces(text, out)
        out = _contest_by_noun_template(text, info or stem_info(text), out)
        if out.get('status') == 'ranked' and out.get('pattern'):
            out['ranked_pattern'] = out['pattern']         # المرجَّح ليس إثباتاً: وزنه محفوظٌ باسمه، لا وزناً للوقوع
        if out.get('status') != 'accepted':
            out['pattern'] = None
        if out.get('status') == 'accepted':
            # وزن الوقوع من الوجه المختار وحده (لمّته وقالبه)، لا من مجموعة الجذر والباب؛ ولا وزن بلا وجهٍ مختار (§٤)
            sf = [f for f in out['faces'] if f['status'] == 'SELECTED']
            out['pattern'] = pattern_record([x for x in out['licensed'] if (x['root'], x['form_class'], x['verb'], x.get('hfn_form')) ==
                                             (sf[0]['root'], sf[0]['form_class'], sf[0]['lemma'], (sf[0]['hfn_forms'] or [None])[0])],
                                            sf[0]['form_class']) if sf else None
    if prot and out is not None:
        alt = {k: out.get(k) for k in ('status', 'root', 'form_class', 'level', 'reason')}
        out.update(status='class_deferred', root=None, form_class=None, level=None, root_status='CLASS_DEFERRED',
                   protected=prot, alternative=alt, pattern=None,
                   faces=[dict(f, status='LICENSED', selection_basis='CLASS_DEFERRED')
                          if f['status'] in ('SELECTED', 'SELECTED_ROOT_LICENCE') or f.get('selection_basis') else f
                          for f in out.get('faces') or []],
                   reason=f'تعيين الفئة مؤجَّل: وحدةٌ محمية مرشّحة ({prot["cls"]} «{prot["identity"]}») أو {prot["alternative"]}')
    elif prot:
        return dict(cells=cell_code(cells(text)), candidates=[], licensed=[], kind=None, level=None, selection={},
                    status='not_applicable', root=None, form_class=None, root_status=prot['root_status'],
                    reason=prot['reason'], protected=prot)
    if out is not None:
        out['statuses'] = selection_statuses(out)
    return out


NOUN_RIVAL_EVIDENCE = ('حرف المضارعة',)


def _no_case_vowel(text):
    """آخر الكلمة بلا حركة إعراب (سكونٌ أو لا علامة أو شدةٌ وحدها)"""
    t = letters(text)
    return bool(t) and not (set(t[-1][1]) & {FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN})


def _contest_by_noun_template(text, info, out):
    """AR02 §٨: الفعل المضارع الذي دليله حرف المضارعة وسكون الآخر وحدهما لا يثبت إن قرأ بناءٌ اسميٌّ من أبنية سيبويه الكلمةَ كلها
    والحرفُ الأول فيه أصلٌ لجذرٍ في HFN (نَمِشْ: «نمش» فَعِلٌ)، ولم يثبت الفعل بعاملٍ يحكمه؛ فالسكون في كلمةٍ مفردة قد يكون وقفاً.
    الوجهان محفوظان، ولا يُضاف حرفٌ ولا حركة. ولا يُنازَع بالبناء الذي يقرأ الحرف زائداً (يَعْلَمْ ← «علم» يَفْعَلٌ: الجذر نفسه)"""
    if out.get('status') != 'accepted' or info.get('governed') or not _no_case_vowel(text):
        return out
    ev = info.get('evidence') or []
    if not ev or not all(any(e.startswith(k) for k in NOUN_RIVAL_EVIDENCE) for e in ev):
        return out
    from .cells import noun_template_faces
    first = letters(text)[0][0]
    if _norm(first) == _norm((out.get('root') or ' ')[0]):
        return out                    # قراءة الفعل نفسها تجعل الحرف أصلاً (أَذِّنْ ← ءذن): لا خلاف على الحرف
    rivals = [f for f in noun_template_faces(text) if f['root'] != out.get('root') and _norm(f['root'][0]) == _norm(first)
              and not f.get('number_mark')]
    if not rivals:
        return out
    faces = [dict(f, status='LICENSED' if f.get('status') in ('SELECTED', 'SELECTED_ROOT_LICENCE') else f.get('status'))
             for f in out.get('faces') or []]
    return dict(out, status='deferred', level=None, root=None, form_class=None, faces=faces, pattern=None,
                noun_template_rivals=rivals,
                reason='الفعل غير مثبت: دليله حرف المضارعة وسكون الآخر وحدهما، وبناءٌ اسميٌّ يقرأ الكلمة كلها والحرف أصلاً: ' +
                       '، '.join(f"{r['root']} {r['pattern']} ({r['sid']})" for r in rivals[:3]) + f' — وقراءة الفعل: {out.get("root")}')


def morph_faces(text, out):
    """أوجه الكلمة (AR03 §٣): لكل (جذر، وزن، لمّة، صيغة HFN) وجهٌ مستقلٌّ بأدلته، فلا تُدمج لمّتان أو صيغتان في وجهٍ واحد؛
    ولكل (جذر، وزن) مولَّدٍ بلا رخصة وجهٌ GENERATED. ولا يُختار وجهٌ (SELECTED) إلا إذا انفرد بالجذر والوزن المقبولين، ولم
    يُعارضه تحقيقٌ مغطّى (§٨). وإذا تعدّدت لمّات الجذر والوزن المقبولين فالجذر مثبت والاختيار الكامل مؤجَّل.
    الحالات: GENERATED، LICENSED، SELECTED، SELECTED_ROOT_LICENCE (رخصة جذرٍ بلا حدث)، RANKED، REJECTED_WITH_BARRIER"""
    # التجميع بمفتاح التحليل نفسه (analysis_key): حدثان لِلّمّة نفسها يختلفان في كرسيّ الهمزة وحده (سَءِمَ/سَئِمَ في HFN v36) تحليلٌ
    # واحد بدليلين، لا لمّتان؛ والهجاءات محفوظة في lemma_spellings، ويُعرض منها ما يتحقق من الجذر والقالب إن انفرد
    raw = {}
    for x in out.get('licensed') or []:
        k = (x['root'], x['form_class'], _plain_vowels(x['verb']), x.get('hfn_form') or '')
        raw.setdefault(k, {}).setdefault(x['verb'], set()).add(x['event_id'])
    groups, spell = {}, {}
    for (r, c, _, f), sp in raw.items():
        ok = sorted(v for v in sp if face_realization(text, r, c, f, v)['lemma']['status'] == 'MATCHED')
        lemma = ok[0] if len(ok) == 1 else sorted(sp)[0]
        groups[(r, c, lemma, f)] = set().union(*sp.values())
        spell[(r, c, lemma, f)] = (sorted(sp), 'REALIZED_SPELLING' if len(ok) == 1 else 'SINGLE_SPELLING' if len(sp) == 1 else
                                   'SORTED_SPELLING_NO_SINGLE_REALIZATION')
    acc = out.get('status') == 'accepted'
    sel_pair = (out.get('root'), out.get('form_class')) if acc else None
    n_sel = sum(1 for (r, c, v, f) in groups if (r, c) == sel_pair)
    # إذا تعدّدت لمّات الجذر والوزن المقبولين فالمكتوب دليل الاختيار: ما تحقّقت الكلمة الداخلة منه بحروفها وحركاتها (MATCHED أو
    # MATCHED_STEM) وانفرد بذلك اختير؛ وإلا فالاختيار مؤجَّل والجذر مثبت (حَسَبَ/فَعَلَ وحَسِبَ/فَعِلَ وجهان لا وجهٌ بلمّةٍ فارغة)
    written = {}
    if n_sel > 1:
        for (r, c, v, f) in groups:
            if (r, c) == sel_pair:
                rz = face_realization(text, r, c, f, v)
                written[(r, c, v, f)] = rz['lemma']['status'] == 'MATCHED' and rz['word']['status'] in ('MATCHED', 'MATCHED_STEM_AND_LICENSED_SUFFIX')
    by_writing = [k for k, ok in written.items() if ok]
    faces = []
    for (root, cls, lemma, form), evs in sorted(groups.items()):
        key = analysis_key(text, root, cls, 'فعل', lemma, form)
        face = dict(analysis_id=analysis_id(key), root=root, form_class=cls, kind='فعل', lemma=lemma, hfn_forms=[form] if form else [],
                    evidence_ids=sorted(evs))
        if len(spell[(root, cls, lemma, form)][0]) > 1:
            face['lemma_spellings'], face['lemma_spelling_basis'] = spell[(root, cls, lemma, form)]
        face['realization'] = face_realization(text, root, cls, form, lemma)
        face['patterns'] = pattern_targets(text, cls, form, lemma, face['evidence_ids'])
        if (root, cls) == sel_pair:
            conflict = 'REALIZATION_MISMATCH' if face['realization']['lemma']['status'] == 'MISMATCH' else \
                'SUFFIX_NOT_LICENSED' if face['realization']['word']['status'] == 'SUFFIX_NOT_LICENSED' else None
            only = n_sel == 1 or (len(by_writing) == 1 and by_writing[0] == (root, cls, lemma, form))
            face['status'] = 'SELECTED' if only and not conflict else 'LICENSED'
            if n_sel > 1:
                face['selection_basis'] = 'WRITTEN_FORM_UNIQUE' if face['status'] == 'SELECTED' else 'NOT_SELECTED_AMONG_LEMMAS'
            if conflict:
                face['selection_blocked_by'] = conflict
        elif (root, cls) == (out.get('root'), out.get('form_class')) and out.get('status') == 'ranked':
            face['status'] = 'RANKED'
        else:
            face['status'] = 'REJECTED_WITH_BARRIER' if acc else 'LICENSED'
        faces.append(face)
    lic_pairs = {(r, c) for (r, c, v, f) in groups}
    for root, cls in sorted(set(out.get('candidates') or []) - lic_pairs):
        st = 'GENERATED'
        ev = []
        if acc and out.get('level') == 'root' and (root, cls) == sel_pair:
            st, ev = 'SELECTED_ROOT_LICENCE', [f'ROOT:{root}']
        faces.append(dict(analysis_id=analysis_id(analysis_key(text, root, cls, 'فعل', None)), root=root, form_class=cls, kind='فعل',
                          lemma=None, hfn_forms=[], evidence_ids=ev, status=st))
    return faces


def selection_statuses(out):
    """AR03 §٤: أربع حالاتٍ مستقلة من الأوجه نفسها"""
    st = out.get('status')
    faces = out.get('faces') or []
    if st == 'not_applicable':
        return dict(root_status='NOT_APPLICABLE', pattern_status='NOT_APPLICABLE', analysis_selection_status='NOT_APPLICABLE',
                    class_status='PROTECTED')
    if st == 'class_deferred':
        return dict(root_status='CLASS_DEFERRED', pattern_status='DEFERRED', analysis_selection_status='DEFERRED', class_status='CLASS_DEFERRED')
    sel = [f for f in faces if f.get('status') == 'SELECTED']
    root_sel = [f for f in faces if f.get('status') == 'SELECTED_ROOT_LICENCE']
    if st == 'accepted':
        a = 'SELECTED' if sel else ('ROOT_LICENCE_ONLY' if root_sel else
                                    'DEFERRED_REALIZATION_CONFLICT' if any(f.get('selection_blocked_by') for f in faces) else 'DEFERRED_MULTIPLE_LEMMAS')
        p = sel[0]['patterns']['lemma_pattern']['status'] if sel else 'DEFERRED'
        return dict(root_status='PROVEN', pattern_status=p, analysis_selection_status=a, class_status='VERB_PROVEN')
    return dict(root_status='RANKED' if st == 'ranked' else 'DEFERRED', pattern_status='DEFERRED', analysis_selection_status='DEFERRED',
                class_status='DEFERRED' if out.get('noun_template_rivals') else 'NOT_PROVEN_BY_THIS_LAYER')


def face_realization(text, root, cls, hfn_form, lemma):
    """التحقيق العكسي للوجه (AR02 §١٠): اللمّة من الجذر وصيغة HFN بعملياتٍ مسمّاة مقابل لمّة الحدث؛ ثم الكلمة الداخلة:
    إن كانت اللمّة نفسها، أو ماضياً بلاحقة إسنادٍ تطابق حروفه وحركاته اللمّةَ إلى ما قبل حركة اللام (_madi_exact)، وإلا NOT_COVERED"""
    from .realize import verify
    lem = verify(root, cls, hfn_form, lemma)
    import unicodedata
    nf = lambda x: unicodedata.normalize('NFC', x or '')
    sp = madi_suffix_parse(text, lemma) if lem['status'] == 'MATCHED' and nf(text) != nf(lemma) else None
    if lem['status'] == 'MATCHED' and nf(text) == nf(lemma):
        word = dict(reconstruction_target='INPUT_WORD', comparison_policy='NFC_LITERAL', status='MATCHED', transformations=[])
    elif sp and sp['status'] == 'MATCHED_STEM_AND_LICENSED_SUFFIX':
        # الجذع حتى اللام كاللمّة، ثم لاحقة إسنادٍ مرخّصة بحركة اللام، ثم ضمير مفعول — بهذا الترتيب؛ لا تحقّقٌ لتصريف الكلمة كلها
        word = dict(reconstruction_target='INPUT_WORD', status=sp['status'], spans=sp['spans'], transformations=sp['transformations'],
                    comparison_policy='NFC_LITERAL' if not sp['transformations'] else 'NAMED_TRANSFORMATIONS',
                    note='الجذع واللاحقة متحقَّقان بقاعدة لواحق الماضي؛ والإعراب والزمن والإسناد خارج هذا الحكم')
    elif sp and sp['status'] == 'SUFFIX_REQUIRES_OBJECT_OUTSIDE_SPAN':
        word = dict(reconstruction_target='INPUT_WORD', status='NOT_COVERED', reason=sp['status'], spans=sp['spans'],
                    transformations=sp['transformations'],
                    note='لاحقة الإسناد «' + sp['spans']['subject_suffix'] + '» لا تأتي إلا قبل ضمير مفعول، والضمير خارج هذا الامتداد')
    elif sp:
        word = dict(reconstruction_target='INPUT_WORD', status='SUFFIX_NOT_LICENSED', spans=sp['spans'], transformations=sp['transformations'],
                    note='الجذع حتى اللام كاللمّة، والباقي لا ينقسم لاحقةَ إسنادٍ ثم ضميرَ مفعول')
    else:
        word = dict(reconstruction_target='INPUT_WORD', status='NOT_COVERED',
                    note='التصريف (المضارع والأمر والمزيد بلواحق متحركة) خارج تغطية التحقيق في هذه الجولة'
                    if lem['status'] == 'MATCHED' else 'اللمّة نفسها لم تتحقق')
    return dict(lemma=lem, word=word)


def pattern_targets(text, cls, hfn_form, lemma, evidence_ids):
    """أهداف الوزن منفصلة (AR02 §١١): لكلٍّ target وvalue_or_alternatives وstatus وsource وevidence_ids.
    e['form'] في HFN صيغة اللمّة المتحققة، لا شكل الكلمة الداخلة؛ وعائلة الباب لا تُختار وزناً"""
    import unicodedata
    lp, src = lemma_pattern(cls, hfn_form)
    same = unicodedata.normalize('NFC', text) == unicodedata.normalize('NFC', lemma or '')
    real = re.sub(r'\s*\(.*\)$', '', hfn_form or '')
    return dict(
        lemma_pattern=dict(target='ميزان اللمّة المجرّد', value_or_alternatives=lp,
                           status='SELECTED' if len(lp) == 1 else 'ALTERNATIVES', source=src, evidence_ids=evidence_ids),
        lemma_realized_pattern=dict(target='صيغة اللمّة المتحققة كما في HFN (form)', value_or_alternatives=[real], status='RETRIEVED',
                                    source='LEXICON_RETRIEVAL', evidence_ids=evidence_ids),
        stem_pattern=dict(target='وزن جذع الكلمة الداخلة', value_or_alternatives=[real] if same else [], status='DERIVED_INPUT_EQUALS_LEMMA'
                          if same else 'NOT_COVERED', source='INPUT_EQUALS_LEMMA' if same else None, evidence_ids=evidence_ids if same else []),
        word_pattern=dict(target='وزن الكلمة الداخلة بلواحقها', value_or_alternatives=[real] if same else [],
                          status='DERIVED_INPUT_EQUALS_LEMMA' if same else 'NOT_COVERED', source='INPUT_EQUALS_LEMMA' if same else None,
                          evidence_ids=evidence_ids if same else []),
        form_family=dict(target='باب الفعل', value_or_alternatives=[cls], status='FAMILY_NOT_A_SELECTED_WAZN', source='TEMPLATE_CLASS',
                         evidence_ids=evidence_ids))


def _morph(text, info=None):
    info = info or stem_info(text)
    exact_only = info['pos'] != 'verb'
    shown = text
    if info.get('moved'):                     # قُلِ ٱللَّهُمَّ: الكسر لالتقاء الساكنين، والأصل السكون
        text = text[:-1] + SUKUN
    base_c = candidates(text, info, any_pos=exact_only)
    cands = candidates(text, info, any_pos=exact_only, extended=True)
    # ما زادته القراءات الموسّعة (R2، R5) لا يُرخَّص إلا بمطابقة فعل HFN حرفاً وحركة، ولا يُعرض مرشّحاً بلا رخصة
    # (فلا يتسرّب إلى رخصة العامل «فعلاً محتملاً»: لِيُّنَا ليس «لين»)
    EXTENDED.clear()
    EXTENDED.update(c for c in cands if c not in base_c)
    if not cands:
        return None
    H = hfn()
    licensed = []
    surface = _plain_vowels(text)
    for root, cls in cands:
        for e in H.index.get((root, cls), []):
            if exact_only and _plain_vowels(e['verb']) not in (surface, _plain_vowels(READING.get((root, cls), text))):
                continue                     # ما لم يثبت أنه فعل: لا يُرخَّص إلا بمطابقة فعل HFN حرفاً وحركة (كَتَبَ)
            if ((root, cls) in UNPEELED or (root, cls) in EXTENDED) and _plain_vowels(e['verb']) != surface:
                continue                     # القراءات الموسّعة: بالمطابقة التامة وحدها
            lp, lps = lemma_pattern(cls, e['form'])
            licensed.append(dict(root=root, form_class=cls, hfn_form=e['form'], verb=e['verb'],
                                 match_policy=match_policy(e['verb'], text) or match_policy(e['verb'], READING.get((root, cls), text)),
                                 lemma_pattern=lp, lemma_pattern_source=lps, realized_pattern=e['form'],
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
        pol = sorted({MATCH_POLICY_AR.get(x.get('match_policy'), 'حرفاً وحركة') for x in exact})
        selection['decision'] = (f'ترجيح بالمطابقة: قراءة النص كله تطابق فعلاً في HFN {"؛ ".join(pol)} (شهادتها {_tier(exact)})، '
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
    lic_pairs = set(pairs)
    cands = [c for c in cands if c not in EXTENDED or c in lic_pairs]
    if not cands:
        return None                          # لم يبقَ إلا ما زادته القراءات الموسّعة بلا رخصة: كأنه لم يكن
    out = dict(cells=cell_code(cells(shown)), candidates=cands, licensed=licensed, kind=info['kind'],
               level=None, selection=selection)
    if not H:
        out.update(status='deferred', reason='لا معجم مرخِّص (HFN غير موجود)')
        return out
    if exact_only and pairs:
        # يطابق فعلاً في HFN حرفاً وحركة، ولم يثبت أنه فعل بالكتابة (مَالَ: فعلٌ أو اسم): مرشَّح لا مقبول
        out.update(status='deferred', level='lemma', reason='يطابق فعل HFN «' + licensed[0]['verb'] + '» ' +
                   MATCH_POLICY_AR.get(licensed[0].get('match_policy'), 'حرفاً وحركة') + '، ولم يثبت بالكتابة أنه فعل', root=None)
        return out
    # الاقتصاد: قراءةٌ لا تفترض حرفاً محذوفاً وجذرها مسجَّل تمنع قبول قراءةٍ تفترضه (يُسِرُّونَ: سرر لا سرو)
    direct = [(r, c) for r, c in cands if (r, c) not in INSERTED and r in H.roots]
    if len(pairs) == 1 and pairs[0] in INSERTED and any(d != pairs[0] for d in direct):
        out.update(status='deferred', reason='قراءة بحرف محذوف (' + f'{pairs[0][0]} {pairs[0][1]}' +
                   ') تنافسها قراءة تامة جذرها مسجَّل: ' + '، '.join(f'{r} ({c})' for r, c in direct[:3]))
        return out
    if len(pairs) == 1:
        out.update(status='accepted', root=pairs[0][0], form_class=pairs[0][1], level='event')
        out['pattern'] = pattern_record([x for x in licensed if (x['root'], x['form_class']) == pairs[0]], pairs[0][1])
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
        out['pattern'] = pattern_record([], rooted[0][1])
        out.update(status='accepted', root=rooted[0][0], form_class=rooted[0][1], level='root',
                   reason='الجذر مسجَّل في HFN، والوزن بالقالب؛ ولا حدث مسجَّل بهذا الوزن، فالحدث ومعناه مؤجَّلان')
    elif rooted:
        out.update(status='deferred', reason='أكثر من جذر مسجَّل في HFN، ولا حدث بالوزن: ' +
                   '، '.join(f'{r} ({c})' for r, c in sorted(rooted)))   # ترتيبٌ ثابت لا يتبع PYTHONHASHSEED
    else:
        out.update(status='deferred', reason='لم يثبت بالكتابة أنه فعل، ولا يطابق فعلاً في HFN حرفاً وحركة'
                   if exact_only else 'لا رخصة: لم يرد أيٌّ من المرشَّحات في HFN')
    return out


# ---------- الميزان والشكل المتحقق ----------
I_WAZN = ('فَعَلَ', 'فَعِلَ', 'فَعُلَ')


def lemma_pattern(cls, hfn_form):
    """ميزان الماضي المجرّد للوجه (لا شكله بعد الإعلال): المزيد بالتحويل المعلن WAZN؛ والثلاثي من صيغة HFN إن عيّنت
    حركة العين (فَعِلَ، «فَعَلَ (ناقص واوي)»، «فَعَلَ/فَعِلَ (أجوف)» بديلان)، وإلا فالعائلة كلها بدائل لا اختيار"""
    if cls != 'I':
        return ([WAZN[cls]], 'DECLARED_FORM_MAPPING') if cls in WAZN else ([], 'NONE')
    base = (hfn_form or '').split(' (')[0]
    opts = [x for x in base.split('/') if x in I_WAZN]
    return (opts, 'LEXICON_FORM') if opts else (list(I_WAZN), 'CANDIDATE_FAMILY')


def pattern_record(lic, cls):
    """حقول الوزن للوجه المقبول: الميزان (lemma_pattern) والشكل المتحقق (realized_pattern) وعائلة الباب، كلٌّ بحالته.
    لا يُختار من البدائل بأولها"""
    lps = sorted({p for x in lic for p in x.get('lemma_pattern') or []}) or lemma_pattern(cls, None)[0]
    srcs = sorted({x.get('lemma_pattern_source') for x in lic}) or [lemma_pattern(cls, None)[1]]
    real = sorted({x['realized_pattern'] for x in lic if x.get('realized_pattern')})
    return dict(lemma_pattern=lps[0] if len(lps) == 1 else None, lemma_pattern_alternatives=lps if len(lps) > 1 else [],
                lemma_pattern_status='SELECTED' if len(lps) == 1 else 'ALTERNATIVES', lemma_pattern_source=srcs,
                realized_pattern=real[0] if len(real) == 1 else None, realized_pattern_alternatives=real if len(real) > 1 else [],
                realized_pattern_source='LEXICON_RETRIEVAL' if real else None, form_family=cls)


# ---------- هوية الوجه (AR02): من محتوى التحليل لا من ترتيب العرض ----------
def analysis_key(span, root, cls, kind, lemma, wazn=None):
    """مفتاح التحليل: الجزء المغطّى (بحروفه وحركاته كما في _plain_vowels)، والجذر، والوزن أو الصنف، ونوع الوجه، واللمّة،
    وصيغة الوزن (قالب HFN) إن عُرفت (AR03 §٢: فَعَلَ وفَعِلَ تحليلان). ولا يُضاف الحقل السادس إلا إذا عُرف، فتبقى هويات ما لا قالب له"""
    k = (_plain_vowels(span or ''), root or '', cls or '', kind or '', _plain_vowels(lemma or ''))
    return k + (_plain_vowels(wazn),) if wazn else k


def analysis_id(key):
    import hashlib, json
    return 'A' + hashlib.sha1(json.dumps(list(key), ensure_ascii=False).encode('utf-8')).hexdigest()[:12]


def face_rivals(peeled, whole_faces):
    """→ (المنافسون، الشواهد المكرّرة، الجذر المشترك أو None) — AR03 §٢.
    هوية التحليل: الامتداد (التقسيم) والجذر والوزن أو الصنف ونوع الوجه واللمّة (analysis_key). فوجهان يتفقان في الجذر والباب
    واللمّة ويختلفان في الامتداد أو الصنف تحليلان مختلفان. وتكرار الدليل للتحليل نفسه (المفتاح نفسه) لا يُنشئ وجهاً ثانياً:
    يُجمع في وجهٍ واحد بأدلته كلها. وما طابق مفتاحُه وجهَ القطع نفسه شاهدٌ مكرّر له"""
    pkey = analysis_key(peeled['span'], peeled['root'], peeled.get('form_class'), peeled.get('kind') or 'فعل', peeled.get('lemma'),
                        peeled.get('wazn'))
    groups = {}
    for f in whole_faces:
        fk = analysis_key(f['span'], f['root'], f.get('form_class') or f.get('pos'), f.get('kind'), f.get('lemma'), f.get('wazn'))
        g = groups.setdefault(fk, dict(f, analysis_id=analysis_id(fk), evidence=[]))
        ev = f.get('evidence')
        if ev is not None and ev not in g['evidence']:
            g['evidence'].append(ev)
    rivals, dup = [], []
    for fk in sorted(groups):
        g = groups[fk]
        g['evidence'] = sorted(g['evidence'], key=str)
        (dup if fk == pkey else rivals).append(g)
    shared = peeled['root'] if rivals and all(r['root'] == peeled['root'] for r in rivals) else None
    return rivals, dup, shared


# ---------- قراءة الكلمة كلها منافساً لقراءة القطع ----------
_WHOLE = None


def _match_policy_text(text, rivals):
    """وصف المطابقة بحسب ما تحققه فعلاً: حرفاً وحركة (NFC)، أو بتوحيد كراسي الهمزة، أو بمفتاح الاسم الذي يُسقط حركة الآخر"""
    import unicodedata
    pols = set()
    for r in rivals:
        if r['kind'] != 'فعل':
            pols.add('بمفتاح الاسم: بلا حركة الآخر والسكون')
        elif unicodedata.normalize('NFC', r['lemma']) == unicodedata.normalize('NFC', text):
            pols.add('حرفاً وحركة')
        else:
            pols.add('حرفاً وحركة بعد توحيد كراسي الهمزة وحذف العلامات العثمانية')
    return '؛ '.join(sorted(pols))


def whole_word_matches(text):
    """→ مداخل HFN التي تطابقها الكلمة كلها حرفاً وحركة: أفعالٌ (بالحركات كاملة) وأسماءٌ (بمفتاح المعجم الاسمي)"""
    global _WHOLE
    H = hfn()
    if not H:
        return []
    if _WHOLE is None:
        _WHOLE = {}
        for (root, cls), es in H.index.items():
            for e in es:
                _WHOLE.setdefault(_plain_vowels(e['verb']), set()).add((root, cls, e['verb'], 'فعل'))
    out = sorted(_WHOLE.get(_plain_vowels(text), ()))
    from .cells import lex_index, _lex_key
    for (root, pos, pattern, lu, lemma) in lex_index().get(_lex_key(text), []):
        out.append((root, None, lemma, pos))
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
            nxt = seg['slots'][s['index'] + 1] if s['index'] + 1 < len(seg['slots']) else None
            if info.get('suffix') is None and nxt is not None and nxt['type'] == 'مبني' and nxt.get('role') == 'enclitic' and \
                    (seg['word_index'], s['index']) in governed:
                # الجذع قبل ضميرٍ متصل فصله المقشِّر (تَكۡتُبُو | هُ)، وفعليته ثابتةٌ بعاملٍ أو بالتوافق: لاحقته لا تُعرف إلا
                # بالكلمة كلها (واو الجماعة قبل الضمير). وما لم تثبت فعليته لا يُمسّ: فَاعِلُو + ضمير يحتمل اسم الفاعل (بَٰلِغُوهُ)
                whole = stem_info(s['text'] + nxt['text'])
                if whole.get('suffix') and whole.get('object') == nxt['text']:
                    info = dict(whole, object=None)
            if (seg['word_index'], s['index']) in governed:
                # الحكم بعاملٍ مقبول يثبت الفعل؛ أما شهادة HFN وحدها ('HFN') والتوافق ('T18') فلا تنفيان الوجه الاسمي في §٨
                info = dict(info, pos='verb', governed=governed[(seg['word_index'], s['index'])] not in ('HFN', 'T18'))
            m = morph(s['text'], info)
            if not m:
                continue
            whole = seg.get('word') or ''
            # الكلمة كلها، والجذع مع ما بعده من اللواحق (فَتَبَرَّكَ: «تَبَرَّكَ» بعد الفاء)
            span = ''.join(x['text'] for x in seg['slots'][s['index']:])
            spans = [t for t in dict.fromkeys((whole, span)) if t and _plain_vowels(t) != _plain_vowels(s['text'])]
            occ = f"w{seg['word_index']}.s{s['index']}"
            if m['status'] in ('accepted', 'ranked') and spans:
                lic = [x for x in m['licensed'] if (x['root'], x['form_class']) == (m.get('root'), m.get('form_class'))]
                peeled = dict(span=s['text'], root=m.get('root'), form_class=m.get('form_class'), kind='فعل',
                              lemma=lic[0]['verb'] if len({x['verb'] for x in lic}) == 1 else None)
                wf = [dict(span=t, root=r, form_class=c, pos=p if c is None else None, kind=p, lemma=l, evidence=f'{r}|{c or p}|{l}')
                      for t in spans for (r, c, l, p) in whole_word_matches(t)]
                rivals, dup, shared = face_rivals(peeled, wf)
                if rivals:
                    # القطع لم يثبت: الكلمة كلها (أو الجذع مع لواحقه) تطابق مدخلاً في HFN بتحليلٍ آخر — جذرٍ أو وزنٍ أو صنفٍ آخر،
                    # أو التقشير نفسه (تَبَرَّكَ ماضي «برك»، نَاقِه اسم فاعل «نقه»)؛ فالأوجه محفوظة، والاختيار مؤجَّل.
                    # وإن اتفقت الأوجه كلها في الجذر ثبت الجذر المشترك، وبقي التقشير والصنف والوزن مؤجَّلة
                    pid = analysis_id(analysis_key(peeled['span'], peeled['root'], peeled['form_class'], 'فعل', peeled['lemma']))
                    t0 = rivals[0]['span']
                    m = dict(m, status='deferred', level=None, root=None, form_class=None, occurrence_id=occ,
                             peeled_face=dict(peeled, analysis_id=pid, status='LICENSED_NOT_SELECTED'),
                             whole_word_rivals=[dict(root=r['root'], form_class=r.get('form_class'), lemma=r['lemma'], pos=r['kind'],
                                                     span=r['span'], analysis_id=r['analysis_id'], status='LICENSED_NOT_SELECTED')
                                                for r in rivals],
                             shared_root=shared, shared_root_status='PROVEN_COMMON_TO_ALL_FACES' if shared else None,
                             reason='قطع الكلمة غير مثبت: «' + t0 + '» تطابق مدخل HFN (' + _match_policy_text(t0, rivals) + '): ' +
                                    '، '.join(f"{r['lemma']} ({r['root']})" for r in rivals[:3]) + f' — وقراءة القطع: {peeled["root"]}' +
                                    (f' — والجذر المشترك بين الأوجه: {shared}' if shared else ''))
                elif dup:
                    m = dict(m, duplicate_evidence=[d['analysis_id'] for d in dup])
            top = m['licensed'][0] if m['licensed'] else None
            out.append(dict(word_index=seg['word_index'], slot=s['index'], status=m['status'], level=m.get('level'),
                            root=m.get('root'), form_class=m.get('form_class'), cells=m['cells'],
                            pattern=m.get('pattern') if m['status'] == 'accepted' else None,
                            whole_word_rivals=m.get('whole_word_rivals'),
                            occurrence_id=f"w{seg['word_index']}.s{s['index']}",
                            # هوية التحليل هوية الوجه المختار وحده، لا أول مرشّح (§١١)؛ فإن لم يُختر وجهٌ كامل فلا هوية تحليلٍ مختار
                            analysis_id=next((f['analysis_id'] for f in m.get('faces') or [] if f.get('status') == 'SELECTED'), None)
                            if m['status'] == 'accepted' else None,
                            statuses=selection_statuses(m),
                            peeled_face=m.get('peeled_face'), shared_root=m.get('shared_root'),
                            noun_template_rivals=m.get('noun_template_rivals'),
                            shared_root_status=m.get('shared_root_status'),
                            reason=m.get('reason'), n_candidates=len(m['candidates']),
                            event=({k: top[k] for k in ('event_id', 'verb', 'masdar', 'hfn_form', 'source',
                                                         'sibawayh', 'meaning')}
                                   if top and m['status'] == 'accepted' and m.get('level') == 'event' else None)))
    return out
