# -*- coding: utf-8 -*-
"""
sarf.features_ext — سماتٌ صرفية مضافة من سجل التغطية (coverage/registry.jsonl)، إضافةً خالصة:
لا تغيّر سمةً قائمة في sarf.features، وإنما تُضاف بأسماءٍ جديدة، كلٌّ بحالتها ودليلها وبدائلها.

  الفعل:  صنف الجذر (صحيح سالم، مهموز، مضعّف، مثال، أجوف، ناقص، لفيف)، وعدد الأصول، وتحويلات α،
          وجمود العامل الفعلي (ليس، عسى، نعم، بئس، حبذا)
  الاسم:  نوع المعرفة، وصورة الآخر (مقصور، ممدود، منقوص)، والعلامة المقدَّرة على المقصور،
          والممنوع من الصرف (مرشّح)، واسم التفضيل (مرشّح)، وأنواع الاشتقاق المحتملة للقالب (مؤجَّل ببدائله)،
          واللمّة (المدخل المعجمي في HFN)، وتحويلات α
  العلم:  نوع المعرفة لاسمٍ ذهبي ولفظ الجلالة

والحالات كما في sarf.features: المثبت بدليلٍ مكتوب أو بالجذر المقبول، والمرشّح لا يدخل الاستدلال، والمؤجَّل ببدائله.
"""
from .chars import letters, FATHA, DAMMA, KASRA, SUKUN, SHADDA, FATHATAN, DAMMATAN, KASRATAN, DAGGER_ALIF
from .features import feat, PROVEN, CAND, DEFER

TANWIN = {FATHATAN, DAMMATAN, KASRATAN}
VOWELS = {FATHA, DAMMA, KASRA} | TANWIN
WEAK = 'وي'
JAMID = ('لَيْسَ', 'عَسَى', 'نِعْمَ', 'بِئْسَ', 'حَبَّذَا')       # جامدٌ لا يتصرّف، من الجرد المعتمد VERBAL
# قوالب سيبويه ← أنواع الاشتقاق المحتملة لها: القالب وحده لا يعيّن أحدها، فهي بدائل (مؤجَّلة)
DERIV_ALT = {
    'فَعِيل': ['صفة مشبهة', 'صيغة مبالغة', 'اسم مفعول (فَعِيل بمعنى مفعول)', 'مصدر', 'جامد'],
    'فَعَّال': ['صيغة مبالغة', 'اسم نسبة (الحرفة)', 'جامد'],
    'فَعُول': ['صيغة مبالغة', 'صفة مشبهة', 'مصدر', 'جامد'],
    'فَعِل': ['صيغة مبالغة', 'صفة مشبهة'],
    'مِفْعَال': ['صيغة مبالغة', 'اسم آلة'],
    'مِفْعَل': ['اسم آلة', 'صيغة مبالغة'],
    'مَفْعَل': ['اسم مكان', 'اسم زمان', 'مصدر ميمي'],
    'مَفْعِل': ['اسم مكان', 'اسم زمان', 'مصدر ميمي'],
    'فَعْلَان': ['صفة مشبهة', 'مصدر', 'جامد'],
    'فُعْلَى': ['مؤنث اسم التفضيل', 'مصدر', 'صفة', 'جامد'],
    'فَعْلَى': ['صفة', 'مصدر', 'جامد'],
}


def root_class(R):
    """صنف الجذر بأصوله: → {النوع، الأصناف}. المهموز والمضعّف والمعتل بمواضع أصوله، والسالم ما خلا منها"""
    r = list(R)
    kinds = []
    pos = ('الفاء', 'العين', 'اللام', 'اللام الثانية')
    for k, c in enumerate(r):
        if c == 'ء':
            kinds.append('مهموز ' + pos[k])
    if len(r) == 3 and r[1] == r[2]:
        kinds.append('مضعّف')
    if len(r) == 4 and r[0] == r[2] and r[1] == r[3]:
        kinds.append('مضعّف رباعي')
    w = [k for k, c in enumerate(r[:3]) if c in WEAK]
    weak = None
    if 0 in w and 2 in w:
        weak = 'لفيف مفروق'
    elif 1 in w and 2 in w:
        weak = 'لفيف مقرون'
    elif 0 in w:
        weak = 'مثال'
    elif 1 in w:
        weak = 'أجوف'
    elif 2 in w:
        weak = 'ناقص'
    if weak:
        kinds.append(weak)
    return dict(type='معتل' if weak else 'صحيح', kinds=kinds or ['سالم'])


def _marks(t):
    return t[1] if t else set()


def final_form(stem):
    """صورة الآخر من الكتابة: → (القيمة، الحالة، الدليل) أو None.
    المقصور: ألفٌ لازمة (ى أو ا) بلا حركة بعد فتحٍ أو تنوين فتح؛ والممدود: همزةٌ بعد ألفٍ في اسمٍ من أربعة أحرفٍ فأكثر؛
    والمنقوص: ياءٌ لازمة بلا حركة بعد كسر. وكلها مرشّحة: الألف قد تكون للتثنية أو منقلبة، والياء قد تكون ياء المتكلم"""
    t = letters(stem)
    if len(t) < 2:
        return None
    last, prev = t[-1], t[-2]
    lm = _marks(last) - {DAGGER_ALIF}
    if last[0] == 'ى' and not (lm & (VOWELS | {SUKUN, SHADDA})) and _marks(prev) & {FATHA, FATHATAN}:
        return 'مقصور', 'ألفٌ مقصورة «ى» لازمة في آخره بعد الفتح'
    if last[0] == 'ا' and not lm and FATHA in _marks(prev) and not (_marks(prev) & TANWIN) and len(t) >= 3:
        return 'مقصور', 'ألفٌ لازمة في آخره بعد الفتح، لا ألف تنوين'
    if last[0] in 'ءأإؤئ' and lm & VOWELS and prev[0] == 'ا' and not (_marks(prev) - {DAGGER_ALIF}) and len(t) >= 4:
        return 'ممدود', 'همزةٌ متطرّفة بعد ألف'
    if last[0] == 'ي' and not (lm & (VOWELS | {SUKUN, SHADDA})) and KASRA in _marks(prev):
        return 'منقوص', 'ياءٌ لازمة في آخره بلا حركة بعد كسر'
    return None


def _diptote(stem, has_al, enclitic):
    """الممنوع من الصرف (مرشّح): صيغة منتهى الجموع أو ألف التأنيث الممدودة، وآخره حركةٌ لا تنوين، بلا «أل» ولا ضمير.
    ولا يثبت بالكتابة وحدها: المضاف إلى ظاهرٍ لا يُنوَّن أيضاً"""
    if has_al or enclitic:
        return None
    t = letters(stem)
    if len(t) < 4:
        return None
    lm = _marks(t[-1])
    if lm & TANWIN or not lm & {FATHA, DAMMA}:      # الممنوع لا يُجرّ بالكسرة إلا مضافاً أو معرَّفاً: فالكسرة لا تشهد له
        return None
    if len(t) >= 5 and t[-1][0] in 'ءأ' and t[-2][0] == 'ا' and not _marks(t[-2]):
        return 'ألف التأنيث الممدودة (فُعَلَاء، أَفْعِلَاء، فَعْلَاء) بلا تنوين'
    if len(t) in (5, 6) and t[2][0] == 'ا' and not _marks(t[2]) and FATHA in _marks(t[1]) and KASRA in _marks(t[3]):
        return 'صيغة منتهى الجموع (مَفَاعِل، مَفَاعِيل) بلا تنوين'
    if len(t) in (4, 5) and DAGGER_ALIF in _marks(t[1]) and FATHA in _marks(t[1]) and KASRA in _marks(t[2]):
        return 'صيغة منتهى الجموع بالألف الخنجرية (مَسَٰجِد، مَصَٰبِيح) بلا تنوين'
    return None


def _elative(stem):
    """أَفْعَل (مرشّح اسم تفضيل): همزةٌ مفتوحة، ثم ساكن، ثم مفتوح، ثم لامٌ بحركةٍ لا تنوين أو ألفٌ مقصورة؛ أو أَفَلّ مضعّفاً"""
    t = letters(stem)
    if not t or t[0][0] != 'أ' or FATHA not in _marks(t[0]):
        return None
    if len(t) == 4 and SUKUN in _marks(t[1]) and FATHA in _marks(t[2]) and \
            (t[3][0] == 'ى' or (_marks(t[3]) & {FATHA, DAMMA, KASRA} and not _marks(t[3]) & TANWIN)):
        return t[3]
    if len(t) == 3 and FATHA in _marks(t[1]) and SHADDA in _marks(t[2]) and not _marks(t[2]) & TANWIN:
        return t[2]
    return None


def nisba_tasghir(stem):
    """النسب والتصغير من الكتابة (مرشّحان): ياءٌ مشدَّدة بعد كسرٍ في الآخر (ياء النسب، وقد تكون أصلية: وَلِيّ، عَلِيّ)؛
    وفُعَيْل وأخواته: ضمٌّ ففتحٌ فياءٌ ساكنة (التصغير، وقد يكون البناء أصلياً). → [(السمة، سجلّ)]"""
    t = letters(stem)
    out = []
    if len(t) >= 3 and t[-1][0] == 'ي' and SHADDA in _marks(t[-1]) and KASRA in _marks(t[-2]):
        out.append(('nisba', feat('منسوب', CAND, 'ياءٌ مشدَّدة بعد كسرٍ في آخره', alt=['منسوب', 'ياءٌ مشدَّدة أصلية (فَعِيل)'])))
    core = [x for x in t if x[0] != 'ة']
    if 4 <= len(core) <= 6 and DAMMA in _marks(t[0]) and FATHA in _marks(t[1]) and t[2][0] == 'ي' and SUKUN in _marks(t[2]):
        out.append(('diminutive', feat('مصغَّر', CAND, 'بناء فُعَيْل (ضمٌّ ففتحٌ فياءٌ ساكنة)', alt=['مصغَّر', 'بناءٌ أصلي على فُعَيْل'])))
    return out


def post_features(a, units, out):
    """سماتٌ تحتاج علاقات الآية: المصدر المؤوَّل من «أَنْ» الناصبة المقبولة ومضارعها المنصوب (يُضاف إلى وحدة الأداة)"""
    for o in a.get('operators', []):
        r = o.get('relation') or {}
        t = r.get('target') or {}
        if o.get('status') != 'accepted' or o.get('operator') != 'أَنْ' or str(o.get('group')) != '5' or not t:
            continue
        if r.get('expected') != 'نصب' or not r.get('consistent'):
            continue
        sl = o.get('slot') or {}
        ui = sl.get('unit') if isinstance(sl, dict) else None
        if ui is None or (o['word_index'], ui) not in out:
            continue
        out[(o['word_index'], ui)].setdefault('construction', feat(
            'مصدر مؤوَّل', PROVEN, f'«أَنْ» الناصبة مقبولة، ومعمولها «{t.get("text")}» مضارعٌ منصوب كتابةً: أَنْ والفعل في تأويل مصدر'))


def _base_pattern(P):
    p = (P or '').replace('بناء سيبويه: ', '').split(' (')[0]
    return ''.join(ch for ch in p if ch not in TANWIN)


# الضمير المتصل بصورته المكتوبة (حروفاً وحركات، بلا تجريد): ضمائر النصب بعد الفعل، وضمائر الرفع
OBJ_PRON = ('هُ', 'هِ', 'هَا', 'هُمْ', 'هِمْ', 'هُمُ', 'هِمُ', 'هُمَا', 'هِمَا', 'هُنَّ', 'هِنَّ', 'كَ', 'كِ', 'كُمْ', 'كُمُ', 'كُمَا',
            'كُنَّ', 'نِي', 'نِ', 'نِيَ')
SUBJ_PRON_V = ('تُمْ', 'تُمُ', 'تُمَا', 'تُنَّ', 'تُ', 'تَ', 'تِ', 'نَ', 'ا', 'وا', 'تَا')
AMBIG_PRON = ('نَا',)                 # فاعلٌ في الماضي (كَتَبْنَا) أو مفعولٌ (كَتَبَنَا): لا تعيّنه الكتابة وحدها


def enclitic_case(text, host):
    """محلّ الضمير المتصل من مضيفه: بعد الاسم المثبت جرٌّ بالإضافة؛ وبعد الفعل المثبت نصبٌ (مفعول) لضمائر النصب،
    ورفعٌ (فاعل) لضمائر الرفع، و«نَا» مؤجَّلة. → سجلّ سمة أو None"""
    hp = (host or {}).get('pos') or {}
    if hp.get('st') != PROVEN:
        return None
    if hp.get('v') == 'اسم':
        return feat('جر', PROVEN, 'ضميرٌ متصلٌ باسمٍ مثبت: مضافٌ إليه في محلّ جر')
    if hp.get('v') == 'فعل':
        if text in OBJ_PRON:
            return feat('نصب', PROVEN, f'«{text}» ضمير نصبٍ متصلٌ بفعلٍ مثبت: مفعولٌ به في محلّ نصب')
        if text in SUBJ_PRON_V:
            return feat('رفع', PROVEN, f'«{text}» ضمير رفعٍ متصلٌ بفعلٍ مثبت: فاعلٌ في محلّ رفع')
        if text in AMBIG_PRON:
            return feat(None, DEFER, '«نَا» بعد الفعل فاعلٌ أو مفعول', alt=['رفع', 'نصب'])
    return None


DEFINITE_BY = {'pronoun': 'معرفة: ضمير', 'demonstrative': 'معرفة: اسم إشارة', 'relative': 'معرفة: اسم موصول'}
_MABNI = []


def mabni_definiteness(text):
    """نوع المعرفة للمبني من ملف المبنيات المعتمد (noun.definite_by)، إن اتفقت مداخل الصورة كلها عليه"""
    if not _MABNI:
        from .lexicon import MabniLexicon
        _MABNI.append(MabniLexicon())
    ents = _MABNI[0].lookup(text) or []
    kinds = {(e.get('noun') or {}).get('definite_by') for e in ents}
    if len(kinds) == 1 and None not in kinds and next(iter(kinds)) in DEFINITE_BY:
        k = next(iter(kinds))
        return feat(DEFINITE_BY[k], PROVEN, f'ملف المبنيات: {ents[0].get("entry_id")} (definite_by = {k})')
    return None


def extra_features(G, rec, has_al=False, enclitic=None, prot=None, lexk=None, verbal_ident=None, host=None):
    """→ السمات المضافة للوحدة (لا تُضاف منها إلا الأسماء الغائبة عن rec). host: سمات الوحدة قبلها إن كانت هذه ضميراً متصلاً"""
    out = {}
    if host is not None:
        ec = enclitic_case(G.O.get('text') or '', host)
        if ec:
            out['enclitic_case'] = ec
    pos = (rec.get('pos') or {}).get('v')
    pos_st = (rec.get('pos') or {}).get('st')
    R, P = G.Theta.get('R'), G.Theta.get('P')
    text = G.O.get('text') or ''
    if pos == 'فعل' and G.closed and R:
        rc = root_class(R)
        out['root_class'] = feat(rc, PROVEN, f'أصول الجذر المقبول «{R}»')
        out['root_arity'] = feat({3: 'ثلاثي', 4: 'رباعي'}.get(len(R)), PROVEN, f'الجذر المقبول «{R}» من {len(R)} أصول')
    if verbal_ident:
        if verbal_ident in JAMID:
            out['conjugability'] = feat('جامد', PROVEN, f'«{verbal_ident}» جامدٌ لا يتصرّف (الجرد المعتمد)')
        else:
            out['conjugability'] = feat(None, DEFER, f'«{verbal_ident}» من النواسخ المتصرّفة أو ناقصة التصرّف؛ ولا جرد معتمد لتصرّفها',
                                        alt=['متصرّف تامّ التصرّف', 'ناقص التصرّف'])
    if G.closed and R and G.Theta.get('alpha') is not None and pos in ('فعل', 'اسم'):
        ops = list(G.Theta.get('ops') or [])
        out['transformations'] = feat(ops, PROVEN, f'مطابقة Realize(R, P) للخلايا (α)، الجذر «{R}» والوزن {P}' +
                                      ('' if ops else '؛ ولم يُسجَّل تحويل'))
    if pos == 'اسم':
        stem = G.O.get('stem') or text
        if has_al:
            out['definiteness_kind'] = feat('معرفة بأل', PROVEN, '«أل» مكتوبة')
        elif enclitic:
            out['definiteness_kind'] = feat('معرفة بالإضافة إلى ضمير', PROVEN, f'الضمير المتصل «{enclitic}» مكتوب بعده')
        ff = final_form(stem)
        if ff:
            out['final_form'] = feat(ff[0], CAND, ff[1] + '؛ وقد تكون الألف أو الياء غير لازمة',
                                     alt=[ff[0], 'صحيح الآخر'])
            if ff[0] == 'مقصور':
                out['case_marking'] = feat('مقدَّرة على الألف للتعذّر', CAND, 'لازمُ المقصور، إن ثبت')
        dp = _diptote(stem, has_al, enclitic)
        if dp:
            out['diptote'] = feat('ممنوع من الصرف', CAND, dp + '؛ ولا يثبت بالكتابة وحدها: المضاف إلى ظاهرٍ لا يُنوَّن',
                                  alt=['ممنوع من الصرف', 'مضاف'])
        for k_, v_ in nisba_tasghir(stem):
            out[k_] = v_
        st_ = [x for x in (G.O.get('slots') or []) if x[0] == 'جذع']
        if not G.closed and len(G.O.get('slots') or []) > 1 and st_ and 'لا تحليل جذري ووزني' in str(G.O.get('deferred')):
            from .cells import stem_licence
            lic = [list(x) for x in stem_licence(st_[0][1])]
            if lic:
                out['stem_root_candidates'] = feat(None, CAND, f'رخصة الجذع «{st_[0][1]}» وحده في الوحدة المركَّبة؛ لا تدخل الإغلاق',
                                                   alt=lic)
        bp = _base_pattern(P)
        if G.closed and bp in DERIV_ALT and (rec.get('derivation') or {}).get('st') != PROVEN:
            out['derivation_candidates'] = feat(None, DEFER, f'القالب «{bp}» يحتمل أكثر من نوع اشتقاق', alt=DERIV_ALT[bp])
        if G.Theta.get('lex') and G.closed and R:
            out['lemma'] = feat(G.Theta['lex'], PROVEN, f'المدخل المعجمي في HFN، الجذر «{R}»')
    if pos != 'فعل' and pos_st != PROVEN or pos == 'اسم':
        el = _elative(G.O.get('stem') or text)
        if el is not None and not G.closed:
            alt = ['اسم تفضيل', 'صفة مشبهة على أَفْعَل', 'مضارع المتكلم']
            if el[0] == 'ى':
                alt.append('فعل ماضٍ على أَفْعَلَ')
            out['elative'] = feat('اسم تفضيل', CAND, 'قالب أَفْعَل في الكتابة؛ ولم يثبت الصنف', alt=alt)
    if prot and prot.get('cls') and 'ذهبي' in str(prot.get('cls')):
        out['definiteness_kind'] = feat('علم', PROVEN, f'اسمٌ ذهبي في الجرد المعتمد: «{prot.get("identity")}»')
    if pos == 'مبني' or lexk == 'مبني':
        md = mabni_definiteness(text)
        if md:
            out['definiteness_kind'] = md
    if lexk == 'لفظ الجلالة':
        out['definiteness_kind'] = feat('علم', PROVEN, 'لفظ الجلالة (sarf/divine.py)')
    return out
