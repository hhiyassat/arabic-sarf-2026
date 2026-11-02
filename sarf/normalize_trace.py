# -*- coding: utf-8 -*-
"""التطبيع المتتبَّع: المصدر، والتمثيل التحليلي، والعرض الإملائي، ومعلومات الرسم، وسجلّ كل تحويل.

عقد التطبيع (NORM_CONTRACT = 'N1.0'):

أ. المصدر: نص الآية كما ورد في data/quran_hafs.tsv (العمود الثالث)، بمحارفه وعلاماته ومسافاته؛ لا يُكتب فوقه.
   الفهرسة: مواضع محارف Unicode (code points) في سلسلة الآية، تبدأ من الصفر، والمجال نصف مفتوح [من، إلى).

ب. تمثيلان مشتقّان، كلٌّ محرفاً محرفاً مربوطٌ بمحارف المصدر:
   1. التمثيل التحليلي (analysis): ما تقرؤه مراحل التحليل (sarf/pipeline.py). ليس «إملاءً معيارياً»: هو رسمٌ عثماني
      مخفَّف بقواعد معلنة (ألف الوصل ألفاً، وسكون المصحف سكوناً، وحذف ما عليه الصفر، وحذف علامات الوقف والأداء،
      والحرف العاري ساكناً بقاعدة الضبط)، وتبقى فيه الألف الخنجرية.
   2. العرض الإملائي (display): إملاءٌ معياري بقواعد معلنة (الخنجرية ألفاً إلا فيما تحذف الإملاء ألفه، والهمزة على
      كرسيّها بقواعد الهمزة، والياء والواو الصغيرتان حرفاً حيث هما حرف). لا يضيف سكوناً لم يُكتب.
      وما لا تحسمه قاعدةٌ مكتوبة يُعلَّم «غير محسوم» ولا يُخمَّن.

ج. معلومات الرسم: كل محرفٍ في المصدر لا يظهر في التمثيل يبقى في السجل بموضعه وصنفه (علامة وقف، ميم الإقلاب، صلة،
   صفر الزيادة، علامة المدّ، علامة الاتجاه…). والتطبيع ليس تحقيقاً صوتياً: لا وصل ولا وقف ولا إدغام.

كل محرفٍ ناتج يحمل: مجال مصدره (أو لا مصدر له إن كان مضافاً)، وهل هو مشتقّ، ومعرّفات العمليات التي أحدثته.
وكل عملية: معرّف القاعدة وإصدارها ومرجعها، ونوعها (استبدال، إضافة، حذف من العرض، نقل علامة، تركيب، جمع أجزاء)،
والمحارف قبلُ وبعدُ برموزها، ومجالاتها، وما حُفظ خارج العرض، والحالة وسبب التأجيل.

الاسترجاع: المصدر يُستعاد حرفياً من محارف الناتج ومحارف المصدر المحذوفة في السجل (restore_source)،
ولا يُقبل نصٌّ مطبَّع مدخلاً (أي نص بلا علامات المصحف يُعالَج معالجة الإملائي: implicit_sukun=False).
"""
import re
import unicodedata

from .chars import SUKUN, SHADDA, FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN, letters
from . import normalize as N

NORM_CONTRACT = 'N3.0'   # N3.0: شكل العلامة غير وظيفتها (التنوين)؛ N2.0: حقول السجل وحفظ صورة المستبدَل
DAGGER = 'ٰ'
TATWEEL = 'ـ'

# ---------- القواعد ----------
# المرجع: K = اصطلاحات الضبط في مصحف المدينة (مجمع الملك فهد، رواية حفص: «التعريف بهذا المصحف»)؛
#         U = معيار Unicode (NFC، كتلة العربية)؛ O = حكم صاحب النظرية المسجَّل في sarf/normalize.py؛
#         I = قواعد الإملاء العربي (عبد السلام هارون، «قواعد الإملاء»؛ وقرارات مجمع اللغة العربية بالقاهرة في الهمزة)
RULES = {
    'N-JOIN-LONE-ALIF': ('1.0', 'K/عيبٌ رقمي', 'ألف تنوين النصب أو الألف المقصورة مفصولةٌ بمسافة عن كلمتها (مُّسَمࣰّ ى): '
                         'لا كلمة هي ألفٌ وحدها، فتُجمع إلى ما قبلها إن حمل ما قبلها تنويناً'),
    'N-NFC': ('1.0', 'U', 'التركيب القانوني NFC: تركيب الحرف وعلامته (ا+ٓ←آ، ي+ٔ←ئ) وترتيب العلامات بفئاتها'),
    'N-KFGQPC-TANWIN': ('1.0', 'K', 'التنوين «المتتابع» (ࣰ ࣱ ࣲ) صورةٌ للتنوين نفسه في الإخفاء والإدغام: يُكتب تنويناً، '
                        'وصورته محفوظة'),
    'N-RLM': ('1.0', 'U', 'علامة الاتجاه (U+200F) ليست من النص: تُحذف من العرض وتُحفظ'),
    'N-IMALA': ('1.0', 'O', 'علامة الإمالة تحت الراء (U+065C، هود ٤١): تُكتب فتحةً للخلية، وصورتها محفوظة'),
    'N-HAMZA-MADDA': ('1.0', 'U/K', 'الهمزة على الألف وعليها علامة المدّ (أٓ) تُكتب آ'),
    'N-SUKUN-ZERO': ('1.0', 'K', 'في ضبط المصحف السكون رأس الخاء (ۡ)، والدائرة (ْ) صفرٌ على الحرف الزائد؛ '
                     'وعلى الألف صفرٌ في كل حال'),
    'N-ZERO-DROP': ('1.0', 'O/D21', 'الحرف الموسوم بالصفر زائدٌ لا يُنطق: يُحذف من التمثيل، إلا ألف واو الجماعة '
                    'فتُحذف علامتها وحدها'),
    'N-HAMZA-SEAT': ('1.0', 'K', 'الهمزة المرسومة على المطّة أو الياء غير المنقوطة أو الواو أو الخنجرية تُكتب '
                     'على كرسيّها (ء، ئ، ؤ، أ)، والحركة بينهما تبقى'),
    'N-MADD-ALIF': ('1.0', 'K', '«آ» بعد فتحة ألفُ مدٍّ عليها علامة المدّ لا همزة: تُكتب ا، وعلامة المدّ محفوظة'),
    'N-DAGGER-MAQSURA': ('1.0', 'O', 'الخنجرية على الألف المقصورة (مُوسَىٰ) تُحذف في التمثيل التحليلي'),
    'N-WASLA': ('1.0', 'K', 'ألف الوصل ٱ تُكتب ا، وكونها همزة وصل محفوظ'),
    'N-SUKUN': ('1.0', 'K', 'سكون المصحف ۡ يُكتب سكوناً ْ'),
    'N-SMALL-YEH': ('1.0', 'K', 'الياء الصغيرة المرتفعة ۧ حرفٌ محذوف رسماً: تُكتب ي (ٱلنَّبِيِّـۧنَ)'),
    'N-SMALL-CARRIER': ('1.0', 'K', 'الحرف الصغير المرسوم بعد مطّةٍ عليها حركة (لِنُحۡـِۧيَ): الحركة له، فتُنقل بعده'),
    'N-SMALL-NOON': ('1.0', 'K', 'النون الصغيرة المرتفعة ۨ حرفٌ محذوف رسماً: تُكتب ن (نُـۨجِي، الأنبياء ٨٨)'),
    'N-IQLAB-TANWIN': ('1.1', 'K', 'الميم الصغيرة بعد حركةٍ قصيرة رسمُ تنوينٍ مُقلَب (شكلاً، لا وظيفةً): تُكتب الحركة بشكل التنوين '
                       '(كَاتِبُۢ ← كَاتِبٌ، أَبَدَۢا ← أَبَدًا، كَافِرِۭ ← كَافِرٍ)، والتنوين حركةٌ واحدة لا نون؛ والميم محفوظة'),
    'N-IQLAB-NOON': ('1.0', 'K', 'الميم الصغيرة على نونٍ عارية علامة إقلاب النون الساكنة (مِنۢ): النون تبقى، والميم محفوظة'),
    'N-SILAH': ('1.0', 'K', 'الواو والياء الصغيرتان بعد هاء الضمير (لَهُۥ، بِهِۦ) صلةٌ في الأداء لا حرفٌ مكتوب: '
                'تُحذف من العرض وتُحفظ'),
    'N-SMALL-LETTER': ('1.0', 'K', 'الواو والياء الصغيرتان في غير الصلة حرفٌ محذوف رسماً (يَلۡوُۥنَ، إِۦلَٰفِهِمۡ): '
                       'في التمثيل التحليلي تُحذف كما كانت (غير محسوم: إثباتها يغيّر ما بعدها، والقرار لصاحب النظرية)'),
    'N-WAQF': ('1.0', 'K', 'علامات الوقف والسجدة والحزب (ۖ ۗ ۚ ۛ ۘ ۜ ۞ ۩): ليست من الكلمة؛ تُحذف من العرض وتُحفظ بموضعها'),
    'N-PERFORMANCE': ('1.0', 'K', 'علامات الأداء (علامة المدّ ٓ ۤ، والصفر المستطيل ۠، والإشمام ۬، والتطويل): '
                      'تُحذف من العرض وتُحفظ'),
    'N-SPACE': ('1.0', 'U', 'المسافات المتعددة مسافةٌ واحدة'),
    'N-IMPLICIT-SUKUN': ('1.0', 'K/D22', 'الحرف العاري غير المدّي في ضبط المصحف مُخفى أو مدغم، فهو ساكن: يُضاف السكون '
                         'علامةً مشتقّة لا مكتوبة (تَدَايَنتُم ← نْ مْ)؛ إلا اللام بعد الألف واللام الشمسية قبل المشدَّد'),
    'N-REORDER': ('1.0', 'U', 'ترتيب علامات الحرف ترتيباً ثابتاً (بإعادة بنائه حرفاً وعلامات)'),
    # العرض الإملائي
    'I-DAGGER-ALIF': ('1.0', 'I', 'الألف الخنجرية بعد فتحة تُكتب ألفاً (تِجَٰرَةً ← تِجَارَةً، لِلشَّهَٰدَةِ ← لِلشَّهَادَةِ)'),
    'I-WAW-ALIF': ('1.0', 'I', 'الواو أو الألف المقصورة حاملةً الخنجرية بعد فتحة تُكتب ألفاً (ٱلصَّلَوٰةَ ← الصَّلَاةَ، '
                   'إِحۡدَىٰهُمَا ← إِحْدَاهُمَا)؛ والمقصورة الخنجرية في آخر الكلمة تبقى ى'),
    'I-MAQSURA-FINAL': ('1.0', 'I', 'الألف المقصورة الخنجرية في آخر الكلمة (مُوسَىٰ، إِلَىٰٓ) تبقى ى، وتُحذف الخنجرية'),
    'I-ALIF-OMIT': ('1.0', 'I', 'ما تحذف الإملاء ألفه (هَٰذَا، ذَٰلِكَ، أُولَٰٓئِكَ، لَٰكِنَّ، إِلَٰه، ٱلرَّحۡمَٰن، هَٰٓؤُلَآءِ، طه): '
                    'تُحذف الخنجرية ولا تُكتب ألفاً'),
    'I-HAMZA': ('1.0', 'I', 'الهمزة المتوسطة والمتطرفة على كرسيّها بأقوى الحركتين (كسر > ضم > فتح > سكون)، وبعد الياء الساكنة '
                'ياءً، وبعد المدّ على السطر (تَسۡـَٔمُوٓاْ ← تَسْأَمُوا، شَيۡـًٔا ← شَيْئًا)'),
    'I-HAMZA-MADD': ('1.0', 'I', 'الهمزة المفتوحة بعدها ألف مدٍّ تُكتب آ (ءَامَنُوا ← آمَنُوا، ٱلۡقُرۡءَان ← الْقُرْآن)'),
    'I-SMALL-LETTER': ('1.0', 'I', 'الواو والياء الصغيرتان في غير الصلة حرفٌ في الإملاء (يَلۡوُۥنَ ← يَلْوُونَ)، إلا «دَاوُۥد» '
                       'فالإملاء بواوٍ واحدة'),
    'I-TANWIN-HAMZA-ALIF': ('1.0', 'I', 'تنوين الفتح على همزةٍ فوق الألف لا تُكتب بعده ألف (خَطَأً، مَلْجَأً، مُتَّكَأً)'),
    'I-ULA-WAW': ('1.0', 'I', 'واو «أولئك، أولو، أولات، أولي» تُكتب في الإملاء وإن وُسمت بالصفر (فَأُوْلَٰٓئِكَ ← فَأُولَئِكَ)؛ '
                  'وتُحذف علامة الصفر وحدها، ويبقى حذفها في التمثيل التحليلي (D21)'),
    'N-MARK-FUNCTION': ('1.0', 'K/O', 'شكل العلامة غير وظيفتها: علامةٌ على شكل التنوين قد تكون نون توكيدٍ خفيفة على فعل '
                        '(لَنَسۡفَعَۢا)؛ فما احتملها في الكتابة يُؤجَّل تعيين وظيفته، ولا يُضاف نون ولا يُحسم تنويناً'),
    'I-UNRESOLVED': ('1.0', 'I', 'صورةٌ رسمية لا تحسمها قاعدةٌ مكتوبة هنا (يَٰٓأَيُّهَا: الإملاء يفصل «يا»؛ وما بقي فيه أثرٌ عثماني): '
                     'تُحفظ كما هي وتُعلَّم غير محسومة'),
}

CATEGORY = {   # صنف المعلومة المحفوظة خارج العرض، لكل محرفٍ يُحذف
    '‏': 'علامة اتجاه', 'ـ': 'تطويل', 'ۢ': 'ميم الإقلاب', 'ۭ': 'ميم الإقلاب (تحت)',
    'ۥ': 'واو صغيرة', 'ۦ': 'ياء صغيرة', '۟': 'صفر الزيادة', 'ْ': 'صفر الزيادة (دائرة)',
    'ٓ': 'علامة المدّ', 'ۤ': 'علامة المدّ الصغيرة', '۠': 'الصفر المستطيل', '۬': 'علامة الإشمام',
    '۞': 'علامة الحزب', '۩': 'علامة السجدة', DAGGER: 'ألف خنجرية', 'ٔ': 'همزة فوقية', 'ٕ': 'همزة تحتية',
    ' ': 'مسافة', '\u0651': 'شدّة الإدغام',
}
for _c in 'ۖۗۘۙۚۛۜ':
    CATEGORY[_c] = 'علامة وقف'
CATEGORY.update({
    chr(0x064E): 'فتحة (صارت تنويناً أو رُكّبت)', chr(0x064F): 'ضمة (صارت تنويناً أو رُكّبت)',
    chr(0x0650): 'كسرة (صارت تنويناً أو رُكّبت)', chr(0x064B): 'تنوين فتح', chr(0x064C): 'تنوين ضم', chr(0x064D): 'تنوين كسر',
    chr(0x08F0): 'تنوين فتحٍ متتابع (إخفاء أو إدغام)', chr(0x08F1): 'تنوين ضمٍّ متتابع (إخفاء أو إدغام)',
    chr(0x08F2): 'تنوين كسرٍ متتابع (إخفاء أو إدغام)', chr(0x06E1): 'سكون المصحف (رأس الخاء)', chr(0x0671): 'ألف الوصل',
    chr(0x0627): 'ألف (رُكّبت أو صارت مدّة)', chr(0x0621): 'همزة على السطر (صارت على كرسيّ)',
    chr(0x0649): 'ألف مقصورة (صارت ألفاً)', chr(0x0648): 'واو (صارت ألفاً أو كرسيّاً)', chr(0x064A): 'ياء (رُكّبت مع الهمزة)',
    chr(0x065C): 'علامة الإمالة', chr(0x06E7): 'ياء صغيرة', chr(0x06E8): 'نون صغيرة', chr(0x06EC): 'علامة التسهيل أو الإشمام',
})


def _cat(ch):
    return CATEGORY.get(ch, unicodedata.name(ch, f'U+{ord(ch):04X}'))


def cp(s):
    return ' '.join(f'U+{ord(c):04X}' for c in s)


class Tok:
    __slots__ = ('c', 'src', 'derived', 'ops')

    def __init__(self, c, src, derived=False, ops=()):
        self.c, self.src, self.derived, self.ops = c, tuple(src), derived, list(ops)


class Run:
    """حالة التطبيع لآية: المحارف الحالية، والسجل"""

    def __init__(self, text, loc='', mode='analysis'):
        self.source, self.loc, self.mode = text, loc, mode
        self.T = [Tok(c, (i,)) for i, c in enumerate(text)]
        self.ops = []
        # بداية كل كلمة في المصدر (مفصولة بمسافة واحدة): لنسبة كل محرف إلى كلمته
        self.word_of = []
        w = 0
        for c in text:
            if c == ' ':
                self.word_of.append(None)
                w += 1
            else:
                self.word_of.append(w)

    @property
    def s(self):
        return ''.join(t.c for t in self.T)

    # ---- الأداة العامة: تحويل مقطعٍ من المحارف إلى سلسلةٍ جديدة، مع ربط كل محرفٍ ناتج بمصدره ----
    def replace(self, a, b, new, rule, status='مطبَّق', note=None, kind=None):
        """المحارف [a, b) تصير new. يُطابَق كل محرفٍ جديد بمحرفٍ قديم مثله بالترتيب؛ وما لم يُطابَق يأخذ مصدر ما بقي
        من القديم غير مطابَق (استبدال/تركيب)، أو لا مصدر له (إضافة). وما بقي من القديم بلا مقابل محذوفٌ من العرض."""
        old = self.T[a:b]
        used = [False] * len(old)
        matched = []
        for ch in new:
            j = next((j for j, t in enumerate(old) if not used[j] and t.c == ch), None)
            if j is not None:
                used[j] = True
            matched.append(j)
        rest = [t for j, t in enumerate(old) if not used[j]]
        rest_src = tuple(sorted({i for t in rest for i in t.src}))
        order = [j for j in matched if j is not None]
        reordered = order != sorted(order)
        unmatched_new = [ch for ch, j in zip(new, matched) if j is None]
        if not unmatched_new and not rest and not reordered:
            return False
        if kind is None:
            kind = ('نقل علامة' if reordered and not unmatched_new and not rest else
                    'إضافة' if unmatched_new and not rest else
                    'حذف من العرض' if rest and not unmatched_new else
                    'تركيب' if len(unmatched_new) < len(rest) else 'استبدال')
        oid = len(self.ops)
        out = []
        consumed = False
        for ch, j in zip(new, matched):
            if j is not None:
                t = old[j]
                out.append(Tok(ch, t.src, t.derived, t.ops + ([oid] if reordered else [])))
            elif rest_src and not consumed:
                out.append(Tok(ch, rest_src, any(t.derived for t in rest), [oid]))
                consumed = True              # المصدر غير المطابَق يُنسب إلى أول محرفٍ جديد (تركيب أو استبدال)
            elif rest_src:
                out.append(Tok(ch, rest_src, True, [oid]))       # محرفٌ ثانٍ من المصدر نفسه (١ ← متعدد)
            else:
                out.append(Tok(ch, (), True, [oid]))             # مضاف: لا يُنسب إلى المصدر
        # المعلومة المحفوظة: كل محرفٍ من المصدر لم يبقَ بعينه في الناتج (محذوفاً كان أو مستبدَلاً أو مركَّباً)،
        # بموضعه ورمزه ووظيفته؛ فصورة التنوين المتتابع مثلاً تبقى محفوظةً وإن صار تنويناً عادياً
        mapped = {}
        for tok in out:
            for i in tok.src:
                mapped.setdefault(i, tok.c)
        gone = sorted({i for t in rest for i in t.src if not t.derived and mapped.get(i) != self.source[i]})
        info = [dict(char=self.source[i], codepoint=f'U+{ord(self.source[i]):04X}', at=i, function=_cat(self.source[i]))
                for i in gone]
        src_all = sorted({i for t in old for i in t.src})
        wd = sorted({self.word_of[i] for i in src_all if self.word_of[i] is not None})
        occ = f"Q{self.loc}:{wd[0] + 1}" + (f"-{wd[-1] + 1}" if len(wd) > 1 else '') if wd and self.loc else (self.loc or 'نص')
        self.ops.append(dict(
            op_id=f'{self.loc}#{self.mode[0]}{oid}', occurrence_id=occ, words=[w + 1 for w in wd],
            source_spans=_spans(src_all), source_text=''.join(self.source[i] for i in src_all),
            source_codepoints=cp(''.join(self.source[i] for i in src_all)),
            input_text=''.join(t.c for t in old), input_codepoints=cp(''.join(t.c for t in old)),
            normalized_text=new, normalized_codepoints=cp(new), normalized_spans=None,
            operation=kind, rule_id=rule, rule_version=RULES[rule][0], rule_reference=RULES[rule][1],
            preserved_information=info, status=status, reason=note))
        self.T[a:b] = out
        return True

    def sub(self, pattern, repl, rule, flags=0, **kw):
        """re.sub على المحارف الحالية، مقطعاً مقطعاً من اليمين إلى اليسار (فلا تتغيّر مواضع ما قبله)"""
        ms = list(re.finditer(pattern, self.s, flags))
        for m in reversed(ms):
            new = repl(m) if callable(repl) else m.expand(repl)
            self.replace(m.start(), m.end(), new, rule, **kw)

    def charmap(self, fn, rule_of):
        """تحويل محرفٍ محرفاً: fn(ch) ← بديله (أو None للإبقاء)؛ rule_of(ch) ← معرّف القاعدة"""
        for i in range(len(self.T) - 1, -1, -1):
            ch = self.T[i].c
            new = fn(ch)
            if new is not None and new != ch:
                self.replace(i, i + 1, new, rule_of(ch))

    def finish(self):
        out = self.s
        for i, t in enumerate(self.T):
            for oid in t.ops:
                o = self.ops[oid]
                o.setdefault('_out', []).append(i)
        for o in self.ops:
            if o['normalized_spans'] is None:
                o['normalized_spans'] = _spans(o.pop('_out', []))
            o.pop('_out', None)
        return out


def _spans(ix):
    ix = sorted(set(ix))
    out = []
    for i in ix:
        if out and out[-1][1] == i:
            out[-1][1] = i + 1
        else:
            out.append([i, i + 1])
    return out


# ---------- خطوات التطبيع ----------
def _nfc(R):
    """NFC كتلةً كتلة (الحرف وعلاماته): التركيب والترتيب القانوني"""
    s = R.s
    starts = [i for i, c in enumerate(s) if not unicodedata.combining(c)] + [len(s)]
    if starts[0] != 0:
        starts = [0] + starts
    for a, b in reversed(list(zip(starts, starts[1:]))):
        seg = s[a:b]
        n = unicodedata.normalize('NFC', seg)
        if n != seg:
            R.replace(a, b, n, 'N-NFC')


def _zero_drop(R):
    """drop_zero_letters (D21) متتبَّعاً: الحرف + الصفر يُحذفان، إلا ألف واو الجماعة فالصفر وحده"""
    s = R.s
    words = s.split(' ')
    pos = 0
    edits = []
    for wi, w in enumerate(words):
        out = []
        i = 0
        while i < len(w):
            ch = w[i]
            if i + 1 < len(w) and w[i + 1] == N.ZERO and ch in 'اويى':
                k = len(out)
                while k and ('ً' <= out[k - 1] <= 'ٕ' or out[k - 1] == 'ٰ' or 'ۖ' <= out[k - 1] <= 'ۭ'):
                    k -= 1
                prev = out[k - 1] if k else ''
                keep = ch == 'ا' and prev == 'و' and N._jamaa_alif(words, wi, ''.join(out))
                # العرض الإملائي يكتب واو «أولئك، أولو، أولات» وإن لم تُنطق (فَأُوْلَٰٓئِكَ ← فَأُولَئِكَ)
                ula = R.mode == 'display' and ch == 'و' and re.match('^(?:[وفبلك][\u064E\u0650])?أُ$', ''.join(out)) \
                    and w[i + 2:i + 3] == 'ل'
                if keep or ula:
                    out.append(ch)
                edits.append((pos + i, pos + i + 2, ch if keep or ula else '', 'I-ULA-WAW' if ula else 'N-ZERO-DROP'))
                i += 2
                continue
            out.append(ch)
            i += 1
        pos += len(w) + 1
    for a, b, new, rule in reversed(edits):
        R.replace(a, b, new, rule)


def _hamza_seat(m):
    return N.HAMZA_SEAT[m.group(1) or m.group(3)] + (m.group(2) or '')


SMALL_LETTER_SILAH = re.compile('(\u0647[\u064F\u0650])([\u06E5\u06E6])(?=[\u0653\u06E4]?[\u06D6-\u06DC\u06DE\u06E9\u200F]*(?: |$))')
SMALL_LETTER_ANY = re.compile('[ۥۦ]')
IQLAB_TANWIN = re.compile('([َُِ])([ّٕٔ]*)([ۭۢ])')
TANWIN_OF = {FATHA: FATHATAN, DAMMA: DAMMATAN, KASRA: KASRATAN}


def _common(R, implicit_sukun):
    """الخطوات المشتركة بين التمثيل التحليلي والعرض (بترتيب uthmani_normalize نفسه)"""
    # ١ جمع الألف المفصولة
    R.sub(N.LONE_ALIF.pattern, r'\1\2', 'N-JOIN-LONE-ALIF', kind='جمع أجزاء')
    # ٢ NFC
    _nfc(R)
    # ٣ ترميز المجمّع
    km = {chr(k): (chr(v) if v else '') for k, v in N.KFGQPC_MAP.items()}
    R.charmap(lambda ch: km.get(ch),
              lambda ch: 'N-RLM' if ch == '‏' else 'N-IMALA' if ch == 'ٜ' else 'N-KFGQPC-TANWIN')
    # ٤ أٓ ← آ
    R.sub('أٓ', 'آ', 'N-HAMZA-MADDA')
    # ٥ السكون والصفر
    if 'ۡ' in R.s:
        R.charmap(lambda ch: N.ZERO if ch == SUKUN else None, lambda ch: 'N-SUKUN-ZERO')
    else:
        R.sub(N.ALIF_ZERO.pattern, 'ا' + N.ZERO, 'N-SUKUN-ZERO')
    # ٦ الصفر
    _zero_drop(R)
    # ٧ الهمزة على كرسيّها
    R.sub(N.HAMZA_ON_TATWEEL.pattern, _hamza_seat, 'N-HAMZA-SEAT')
    _nfc(R)
    # ٨ آ بعد فتحة
    R.sub(N.MADD_AFTER_FATHA.pattern, r'\1ا', 'N-MADD-ALIF')
    # ٩ ميم الإقلاب (إصلاح N1.0: كانت تُحذف فيضيع التنوين)
    for m in reversed(list(IQLAB_TANWIN.finditer(R.s))):
        # عمليةٌ واحدة (تركيب): الحركة والميم معاً شكلُ التنوين، فمحرف التنوين الناتج مصدره الحركة والميم كلتاهما،
        # وكلتاهما محفوظتان بموضعيهما؛ وما بينهما (الشدّة، الهمزة) يبقى بعينه
        R.replace(m.start(), m.end(), TANWIN_OF[m.group(1)] + m.group(2), 'N-IQLAB-TANWIN')
    # ١٠ الحرف الصغير على المطّة: علامات المطّة له (لِنُحۡـِۧيَ ← حْ يِ يَ)، لا للحرف قبلها (إصلاح N1.0)
    for m in reversed(list(re.finditer(TATWEEL + '([\u064B-\u0652]+)([\u06E5-\u06E8])', R.s))):
        R.replace(m.start(), m.end(), TATWEEL + m.group(2) + m.group(1), 'N-SMALL-CARRIER', kind='نقل علامة')
    # ١١ النون الصغيرة (إصلاح N1.0: كانت تُحذف فيضيع حرف)
    R.sub(TATWEEL + '?\u06E8', 'ن', 'N-SMALL-NOON')


def _final_maps(R):
    def fn(ch):
        if ch in N.UTHMANI_MAP:
            return N.UTHMANI_MAP[ch]
        if ch in N.UTHMANI_DROP:
            return ''
        return None

    def rule(ch):
        if ch == 'ٱ':
            return 'N-WASLA'
        if ch == 'ۡ':
            return 'N-SUKUN'
        if ch == 'ۧ':
            return 'N-SMALL-YEH'
        if ch in 'ۭۢ':
            return 'N-IQLAB-NOON'
        if 'ۖ' <= ch <= 'ۜ' or ch in '۞۩':
            return 'N-WAQF'
        if ch in 'ۥۦ':
            return 'N-SMALL-LETTER'
        return 'N-PERFORMANCE'

    # الصلة أولاً (واو/ياء صغيرة بعد هاء الضمير): قاعدتها غير قاعدة الحرف الصغير
    for m in reversed(list(SMALL_LETTER_SILAH.finditer(R.s))):
        R.replace(m.start(2), m.end(2), '', 'N-SILAH')
    for m in reversed(list(SMALL_LETTER_ANY.finditer(R.s))):
        if R.mode == 'display':
            ws = R.s.rfind(' ', 0, m.start()) + 1
            if re.match('^(?:[وفل][َِ]|يَٰ?ا?)?دَاوُ', R.s[ws:]):
                R.replace(m.start(), m.end(), '', 'I-SMALL-LETTER', note='«داود» بواوٍ واحدة في الإملاء')
            else:
                R.replace(m.start(), m.end(), 'و' if m.group() == 'ۥ' else 'ي', 'I-SMALL-LETTER')
            continue
        R.replace(m.start(), m.end(), '', 'N-SMALL-LETTER', status='غير محسوم',
                  note='حرفٌ محذوف رسماً؛ حذفه من التمثيل التحليلي سلوكٌ سابق محفوظ، وإثباته يغيّر ما بعده')
    R.charmap(fn, rule)
    # المسافات
    s = R.s
    for m in reversed(list(re.finditer(r'\s{2,}|^\s+|\s+$', s))):
        keep = ' ' if 0 < m.start() and m.end() < len(s) else ''
        R.replace(m.start(), m.end(), keep, 'N-SPACE')


def _implicit_sukun(R):
    """N-IMPLICIT-SUKUN وإعادة بناء الحرف وعلاماته (letters) كما في uthmani_normalize"""
    s = R.s
    pos = 0
    edits = []
    for w in s.split(' '):
        toks = letters(w)
        rebuilt = []
        for i, (L, mk) in enumerate(toks):
            mk = set(mk)
            if not mk and L not in N.MADD_LETTERS and L != 'ة' and 'ء' <= L <= 'ي':
                prev_al = i > 0 and toks[i - 1][0] == 'ا'
                mudgham = L == 'ل' and i + 1 < len(toks) and SHADDA in toks[i + 1][1] and toks[i + 1][0] in N.SOLAR
                if not (L == 'ل' and prev_al) and not mudgham:
                    mk.add(SUKUN)
            rebuilt.append(L + ''.join(sorted(mk)))
        new = ''.join(rebuilt)
        if new != w:
            edits.append((pos, pos + len(w), w, new))
        pos += len(w) + 1
    for a, b, w, new in reversed(edits):
        # كتلةً كتلة: السكون المضاف إضافة، وترتيب العلامات نقل علامة
        old_cl = _clusters(w)
        new_cl = _clusters(new)
        if len(old_cl) != len(new_cl):
            R.replace(a, b, new, 'N-REORDER')
            continue
        off = a
        offs = []
        for oc in old_cl:
            offs.append(off)
            off += len(oc)
        for oc, nc, o in reversed(list(zip(old_cl, new_cl, offs))):
            if oc == nc:
                continue
            if len(nc) == len(oc) + 1 and sorted(nc) == sorted(oc + SUKUN):
                R.replace(o, o + len(oc), nc, 'N-IMPLICIT-SUKUN', kind='إضافة',
                          status='مشتقّ', note='سكونٌ مضاف بقاعدة الضبط، غير مكتوب في المصدر')
            else:
                R.replace(o, o + len(oc), nc, 'N-REORDER')


def _clusters(w):
    out = []
    for ch in w:
        if out and (unicodedata.combining(ch) or ch == DAGGER) and ch != TATWEEL:
            out[-1] += ch
        else:
            out.append(ch)
    return out


# ---------- العرض الإملائي ----------
OMIT_ALIF = re.compile(
    '^(?:[وفبلك][َِ]|أَ)*(?:'
    'هَٰ?ذَ|هَٰ?ذِ|هَٰٓؤُ|هَٰ?كَذَ|ذَٰلِكَ|ذَٰلِكُ|ذَٰلِكِ|أُو?لَٰٓ?ئِك|لَٰكِن|لَٰكِنَّ|إِلَٰه|ءِلَٰه|ٱلرَّحۡمَٰن|الرَّحْمَٰن|طه'
    ')')


def _display_rules(R):
    s = R.s
    # الكلمات بمواضعها
    words = [(m.start(), m.end(), m.group()) for m in re.finditer(r'[^ ]+', s)]
    for a, b, w in reversed(words):
        omit = bool(OMIT_ALIF.match(w))
        # الهمزة المفتوحة بعدها ألف مدٍّ ← آ (ما لم يسبقها مدّ)
        for m in reversed(list(re.finditer('([^اوي]?)(ء)َ(ا)', w))):
            if not (m.group(1) or m.start() == 0):
                continue
            before = w[:m.start(2)]
            pm = re.search('[\u064B-\u0652]*$', before).group()
            pb = re.sub('[\u064B-\u0652\u0670]', '', before)[-1:]
            after = re.sub('[\u064B-\u0652\u0670]', '', w[m.end(3):])
            prefix_only = re.fullmatch('[\u0648\u0641\u0628\u0644\u0643][\u064E\u0650]', before) is not None
            if not prefix_only and (KASRA in pm or pb == 'ي' and (not pm or SUKUN in pm)):
                continue
            if '\u06EC' in R.source and any(R.source[i] == '\u06EC' for t in R.T[a:a + len(w)] for i in t.src) or \
                    any('\u06EC' in R.source[max(0, i - 1):i + 2] for i in R.T[a + m.start(3)].src):
                continue                                      # الألف عليها علامة التسهيل (ءَا۬عۡجَمِيࣱّ): همزةٌ ثانية لا مدّ                                      # كرسيّها الياء (ٱلسَّيِّـَٔاتِ ← السَّيِّئَاتِ): لا مدّة
            if not after:
                continue                                      # الألف آخر الكلمة (رَءَا): غير محسوم، يُعلَّم في _unresolved
            R.replace(a + m.start(2), a + m.end(3), 'آ', 'I-HAMZA-MADD')
        w = R.s[a:R.s.find(' ', a) if R.s.find(' ', a) >= 0 else len(R.s)]
        b = a + len(w)
        # الخنجرية
        for m in reversed(list(re.finditer('([وى])' + DAGGER, w))):
            body = w.rstrip(''.join(chr(c) for c in range(0x064B, 0x0653)) + DAGGER)
            if m.start() > 0 and FATHA in w[max(0, m.start() - 3):m.start()] and m.end() < len(body):
                R.replace(a + m.start(), a + m.end(), 'ا', 'I-WAW-ALIF')
            elif m.group(1) == 'و' and m.start() > 0 and FATHA in w[max(0, m.start() - 3):m.start()]:
                # الواو الخنجرية في آخر الكلمة قبل ألفٍ زائدة (ٱلرِّبَوٰٓاْ): الإملاء «الربا»
                R.replace(a + m.start(), a + m.end(), 'ا', 'I-WAW-ALIF')
        w = R.s[a:R.s.find(' ', a) if R.s.find(' ', a) >= 0 else len(R.s)]
        for m in reversed(list(re.finditer(DAGGER, w))):
            if omit:
                R.replace(a + m.start(), a + m.end(), '', 'I-ALIF-OMIT')
                continue
            k = m.start()
            pre = ''
            while k > 0 and unicodedata.combining(w[k - 1]):
                k -= 1
                pre += w[k]
            if FATHA in pre:
                R.replace(a + m.start(), a + m.end(), 'ا', 'I-DAGGER-ALIF')
            elif m.start() > 0 and w[m.start() - 1] == 'ى':
                R.replace(a + m.start(), a + m.end(), '', 'I-MAQSURA-FINAL')
    # الهمزة المرسومة على المطّة أو على السطر وسطاً: كرسيّها بقواعد الإملاء
    _imlai_hamza(R)
    # الهمزة على الألف وبعدها ألفٌ من الخنجرية داخل الكلمة (ٱلۡـَٰٔنَ، قُرۡءَٰنًا): مدّة (آ)
    for m in reversed(list(re.finditer('أَا(?=[^ ])', R.s))):
        R.replace(m.start(), m.end(), 'آ', 'I-HAMZA-MADD')
    # تنوين الفتح على همزةٍ فوق الألف لا تُكتب بعده ألف (خَطَـࣰٔا ← خَطَأً، مَلۡجَـًٔا ← مَلْجَأً)
    for m in reversed(list(re.finditer('أً(ا)(?= |$)', R.s))):
        R.replace(m.start(1), m.end(1), '', 'I-TANWIN-HAMZA-ALIF')
    # والشدّة تبقى حيث كُتبت، ومنها شدّة الإدغام على أول الكلمة (مُّسَمًّى): حفظ الشدّة وعلاقتها بحرفها من العقد


VOW = {FATHA: 2, DAMMA: 3, KASRA: 4, FATHATAN: 2, DAMMATAN: 3, KASRATAN: 4}
NONCONNECT = set('اأإآدذرزوؤء')


def _imlai_hamza(R):
    s = R.s
    T = R.T
    for i in range(len(T) - 1, -1, -1):
        if T[i].c != 'ء':
            continue
        # من المطّة في المصدر، أو على السطر وسط الكلمة
        src_chars = {R.source[j] for j in T[i].src}
        from_tatweel = TATWEEL in src_chars
        s = R.s
        a = s.rfind(' ', 0, i) + 1
        e = s.find(' ', i)
        e = len(s) if e < 0 else e
        w_before, w_after = s[a:i], s[i + 1:e]
        base_before = [c for c in w_before if not unicodedata.combining(c) and c != DAGGER]
        if not base_before:
            continue                                          # أول الكلمة: همزة القطع مرسومة بكرسيّها في المصدر
        if re.fullmatch('[\u0648\u0641\u0628\u0644\u0643][\u064E\u0650]', w_before):
            # بعد سابقةٍ من حرفٍ واحد (بِـَٔايَٰتِ): همزةٌ أولى، كرسيّها الألف بحركتها هي
            hv0 = next((c for c in w_after[:1] if c in (FATHA, DAMMA, KASRA)), None)
            seat = 'إ' if hv0 == KASRA else 'أ'
            R.replace(i, i + 1, seat, 'I-HAMZA', note='همزةٌ أولى بعد سابقة')
            continue
        after_marks = ''
        for c in w_after:                                     # علامات الهمزة نفسها حتى الحرف التالي
            if not (unicodedata.combining(c) or c == DAGGER):
                break
            after_marks += c
        rest_letters = [c for c in w_after if not unicodedata.combining(c) and c != DAGGER]
        final = not rest_letters or rest_letters == ['ا'] and FATHATAN in after_marks
        if not from_tatweel and final:
            continue                                          # المتطرفة على السطر في المصدر صحيحةٌ إملاءً غالباً
        prev = base_before[-1]
        # حركة الحرف قبلها
        j = len(w_before) - 1
        pm = ''
        while j >= 0 and (unicodedata.combining(w_before[j]) or w_before[j] == DAGGER):
            pm += w_before[j]
            j -= 1
        pv = max([VOW.get(c, 0) for c in pm] + [1 if SUKUN in pm or not pm else 0])
        hv = max([VOW.get(c, 0) for c in after_marks] + [1 if SUKUN in after_marks or not after_marks else 0])
        if prev in 'اوي' and pv <= 1 and prev != 'ي':
            seat = 'ء'                                        # بعد مدٍّ أو واوٍ ساكنة: على السطر
        elif prev == 'ي' and pv <= 1:
            seat = 'ئ'
            # بعد الياء الساكنة ياءً (هَيْئَة، شَيْئًا، خَطِيئَة): قرار مجمع اللغة العربية بالقاهرة
        elif final:
            seat = {4: 'ئ', 3: 'ؤ', 2: 'أ'}.get(pv, 'ء')
            if rest_letters == ['ا'] and pv <= 1:            # شَيۡـًٔا، جُزۡءًا
                seat = 'ئ' if prev not in NONCONNECT else 'ء'
        else:
            k = max(pv, hv)
            seat = {4: 'ئ', 3: 'ؤ', 2: 'أ'}.get(k, 'ء')
            if seat == 'أ' and prev == 'ا':
                seat = 'ء'                                    # تَسَآءَلُونَ
        if seat != 'ء':
            R.replace(i, i + 1, seat, 'I-HAMZA')


def _unresolved(R):
    """ما بقي في العرض من أثرٍ عثماني لا تحسمه قاعدة: يُعلَّم ولا يُغيَّر"""
    s = R.s
    for m in re.finditer(r'[^ ]+', s):
        w = m.group()
        why = []
        srcw = sorted({R.word_of[i] for t in R.T[m.start():m.end()] for i in t.src if R.word_of[i] is not None})
        sw = R.source.split(' ')[srcw[0]] if srcw else ''
        swn = unicodedata.normalize('NFC', sw)
        if re.match('^[وف]?\u064E?يَ' + DAGGER, swn):
            why.append('النداء «يا» موصولٌ بما بعده رسماً، والإملاء يفصله (حكمه عند صاحب النظرية)')
        elif re.match('^[وف]?\u064E?هَ' + DAGGER + '\u0653?أ', swn):
            why.append('«ها» التنبيه موصولةٌ بما بعدها رسماً (هَٰٓأَنتُمۡ)، والإملاء يفصلها')
        if DAGGER in w:
            why.append('ألفٌ خنجرية لم تحسمها قاعدة')
        if re.match('^لْ[أإآءئؤ]', w):
            why.append('لام التعريف بلا ألفٍ رسماً (لۡـَٔيۡكَةِ)؛ وإثبات الألف قراءةٌ لا رسم')
        if '\u06EC' in sw and 'ا\u06EC' in swn:
            why.append('ألفٌ عليها علامة التسهيل (ءَا۬عۡجَمِيࣱّ): همزةٌ ثانية مسهَّلة، وكتابتها إملاءً «أأعجمي» قراءةٌ لا رسم')
        if re.search('[ءأ]َا$', w):
            why.append('الألف بعد الهمزة في آخر الكلمة (رَءَا)، والإملاء «رأى»: تحويلها ياءً معرفةٌ بالكلمة لا رسم')
        if why:
            ws = sorted({R.word_of[i] + 1 for t in R.T[m.start():m.end()] for i in t.src if R.word_of[i] is not None})
            sp = sorted({i for t in R.T[m.start():m.end()] for i in t.src})
            R.ops.append(dict(op_id=f'{R.loc}#{R.mode[0]}{len(R.ops)}',
                              occurrence_id=f"Q{R.loc}:{ws[0]}" + (f"-{ws[-1]}" if len(ws) > 1 else '') if ws else R.loc,
                              words=ws, source_spans=_spans(sp), source_text=''.join(R.source[i] for i in sp),
                              source_codepoints=cp(''.join(R.source[i] for i in sp)), input_text=w, input_codepoints=cp(w),
                              normalized_text=w, normalized_codepoints=cp(w), normalized_spans=[[m.start(), m.end()]],
                              operation='غير محسوم', rule_id='I-UNRESOLVED', rule_version=RULES['I-UNRESOLVED'][0],
                              rule_reference=RULES['I-UNRESOLVED'][1], preserved_information=[],
                              status='غير محسوم', reason='؛ '.join(why)))


# ---------- الواجهة ----------
SOURCE_MARKERS = '\u06E1\u0671\u08F0\u08F1\u08F2\u06E2\u06ED\u0654\u0655'


def is_source_encoding(text):
    """العقد يقبل ترميز المصدر (مصحف المجمّع) وحده؛ والناتج المطبَّع ليس مدخلاً صالحاً (لا ثبات مدّعى عليه)"""
    return any(ch in SOURCE_MARKERS or '\u06D6' <= ch <= '\u06ED' for ch in text)


def normalize_traced(text, loc='', implicit_sukun=None, strict=False):
    """→ dict(source, analysis, display, cells_analysis, cells_display, ops_analysis, ops_display)
    strict: يُرفض ما ليس بترميز المصدر (ValueError)"""
    if strict and not is_source_encoding(text):
        raise ValueError(f'ليس بترميز المصدر: العقد {NORM_CONTRACT} لا يقبل نصاً مطبَّعاً مدخلاً')
    if implicit_sukun is None:
        implicit_sukun = any(ch in N.UTHMANI_SIGNS or ord(ch) in N.KFGQPC_MAP or ch in 'ٕۡٔ' for ch in text)
    A = Run(text, loc, 'analysis')
    _common(A, implicit_sukun)
    A.sub(N.DAGGER_ON_MAQSURA.pattern, r'\1', 'N-DAGGER-MAQSURA')
    _final_maps(A)
    if implicit_sukun:
        _implicit_sukun(A)
    _mark_function(A)
    analysis = A.finish()
    D = Run(text, loc, 'display')
    _common(D, implicit_sukun)
    _final_maps(D)
    _display_rules(D)
    _unresolved(D)
    _mark_function(D)
    display = D.finish()
    return dict(source=text, analysis=analysis, display=display, contract=NORM_CONTRACT,
                cells_analysis=[_cell(t, text) for t in A.T], cells_display=[_cell(t, text) for t in D.T],
                ops_analysis=A.ops, ops_display=D.ops)


TANWIN_MARKS = {FATHATAN, DAMMATAN, KASRATAN}
MARK_FUNCTION_UNSET = 'غير معيَّنة في التطبيع: التطبيع يثبت شكل العلامة لا وظيفتها (تنوين اسمٍ أو نون توكيدٍ خفيفة)'
# شكل تنوين الفتح وبعده ألف على كلمةٍ أولها لامٌ مفتوحة وحرف مضارعةٍ متحرّك: يحتمل نون التوكيد الخفيفة على فعل
# (لَنَسۡفَعَۢا، وَلَيَكُونࣰا) كما يحتمل تنوين اسمٍ بعد لام التوكيد (لَأَجۡرًا)؛ والكتابة لا تفصل بينهما
NUN_KHAFIFA_SHAPE = re.compile('^(?:[\u0648\u0641]\u064E)?\u0644\u064E[\u0623\u0646\u064A\u062A][\u064E\u064F].*\u064B\u0651?\u0627$')


def _cell(t, text):
    """المحرف الناتج: مصدره، وهل هو مشتقّ؛ وللتنوين شكله في المصدر ووظيفته غير المعيَّنة"""
    d = dict(c=t.c, src=list(t.src), derived=t.derived)
    if t.c in TANWIN_MARKS:
        d['mark'] = dict(form=cp(''.join(text[i] for i in t.src)), function=None, function_status=MARK_FUNCTION_UNSET)
    return d


def _mark_function(R):
    """كل عمليةٍ أنتجت شكل تنوين تحمل شكلها ووظيفتها غير المعيَّنة؛ وما احتمل نون التوكيد الخفيفة في الكتابة
    يُؤجَّل في سجل الوقوع نفسه (غير محسوم)، ولا يُضاف حرف نون ولا يُحسم أنه تنوين اسم"""
    for o in R.ops:
        if o['rule_id'] in ('N-IQLAB-TANWIN', 'N-KFGQPC-TANWIN') and set(o['normalized_text']) & TANWIN_MARKS:
            o['mark_form'] = o['source_codepoints']
            o['mark_function'] = None
            o['mark_function_status'] = MARK_FUNCTION_UNSET
    s = R.s
    for m in re.finditer(r'[^ ]+', s):
        w = m.group()
        if not NUN_KHAFIFA_SHAPE.match(w):
            continue
        ws = sorted({R.word_of[i] + 1 for t in R.T[m.start():m.end()] for i in t.src if R.word_of[i] is not None})
        why = ('شكل تنوين الفتح وبعده ألف على كلمةٍ أولها لامٌ مفتوحة وحرف مضارعة: يحتمل نون التوكيد الخفيفة على فعل '
               '(لَنَسۡفَعَۢا) وتنوين اسمٍ بعد لام التوكيد (لَأَجۡرًا)؛ الوظيفة مؤجَّلة إلى ما بعد التطبيع بدليلها')
        for o in R.ops:
            if set(o['words']) & set(ws) and o.get('mark_function_status'):
                o['status'] = 'غير محسوم'
                o['reason'] = why
        k = next(i for i in range(m.start(), m.end()) if R.T[i].c == FATHATAN)
        sp = sorted(R.T[k].src)
        R.ops.append(dict(op_id=f'{R.loc}#{R.mode[0]}{len(R.ops)}',
                          occurrence_id=f"Q{R.loc}:{ws[0]}" + (f"-{ws[-1]}" if len(ws) > 1 else '') if ws else R.loc,
                          words=ws, source_spans=_spans(sp), source_text=''.join(R.source[i] for i in sp),
                          source_codepoints=cp(''.join(R.source[i] for i in sp)), input_text=w, input_codepoints=cp(w),
                          normalized_text=w, normalized_codepoints=cp(w), normalized_spans=[[k, k + 1]],
                          operation='غير محسوم', rule_id='N-MARK-FUNCTION', rule_version=RULES['N-MARK-FUNCTION'][0],
                          rule_reference=RULES['N-MARK-FUNCTION'][1], preserved_information=[], status='غير محسوم',
                          reason=why, mark_form=cp(''.join(R.source[i] for i in sp)), mark_function=None,
                          mark_function_status=MARK_FUNCTION_UNSET))


def restore_source(res, which='analysis'):
    """المصدر حرفياً من محارف الناتج غير المشتقّة ومحارف المصدر المحذوفة في السجل"""
    got = {}
    for c in res['cells_' + which]:
        for i in c['src']:
            got[i] = None
    for o in res['ops_' + which]:
        for p in o['preserved_information']:
            got[p['at']] = None
    src = res['source']
    missing = [i for i in range(len(src)) if i not in got]
    return ''.join(src[i] for i in sorted(got)), missing
