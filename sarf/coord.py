# -*- coding: utf-8 -*-
"""
sarf/coord.py — سجلّ مرشّحات العطف وقرار الموضع (مواصفة صاحب النظرية في حدود العطف):

القاعدة الحاكمة: لا يُثبَّت طرفا العطف إلا بدليلٍ إيجابي على الربط والحدود، ولا يُرفض مرشّحٌ إلا بمانعٍ مثبت،
وما نقص دليله أو تعدّدت أوجهه يُؤجَّل.

وحدة التحليل مرشّحُ علاقةٍ كامل: وظيفة الحرف، والطرف السابق برأسه وامتداده، واللاحق كذلك، والمستوى، والتركيب
الحاوي، والعناصر المشتركة (لكلٍّ منها قرارٌ مستقل)، والأدلة، والبدائل؛ ثم يُحكم على كل مرشّح:
  مستوفٍ   — شروط القبول A1–A8 كلها متحققة (والقبول جوازٌ وفق القواعد المنفَّذة، لا اختيارٌ نهائي)
  مرفوض   — قام عليه مانعٌ مثبت R1–R7 (والرفض يخصّه، ولا ينتقل إلى غيره من مرشّحات الموضع)
  مؤجَّل   — سببٌ من D1–D9، مع ما يلزم لحسمه
ثم قرار الموضع (الجدول ٨): قبولٌ محدّد حين يبقى مستوفٍ واحد ويُرفض غيره بدليل والتغطية مكتملة؛ وتأجيلٌ حين يتعدّد
المستوفي أو يبقى منافسٌ مؤجَّل أو تنقص التغطية؛ ورفضُ العطف حين تُرفض المرشّحات كلها والتغطية مكتملة.

ليست موانع بمفردها: بُعد المعطوف عليه، واختلاف زمن الفعلين أو الجنس أو العدد، ونهاية الآية، وعدم ظهور الحركة.
وتطابق الحالة المكتوبة قرينةٌ لا دليلٌ كافٍ؛ والقرب يولّد مرشّحاً ولا يثبته.
"""
from .chars import letters

ACCEPT = {
    'A1': 'ثبوت وظيفة العطف للحرف في هذا الوجه',
    'A2': 'تعيين رأس كل طرف تعييناً قابلاً للتحقق',
    'A3': 'قاعدةٌ تجيز الربط بين الطرفين في مستواهما',
    'A4': 'توافق العامل والإعراب أو المحلّ بقدر ما تتطلبه القاعدة',
    'A5': 'تعيين امتداد الطرفين بلا قطع تابعٍ ثبت دخوله ولا إدخال ما ثبت خروجه',
    'A6': 'اتساق العلاقة مع التركيب الحاوي',
    'A7': 'إسناد كل حذفٍ أو مشاركةٍ في عامل إلى قاعدة موثقة',
    'A8': 'خلوّ المرشّح من مانع مثبت',
}
REJECT = {
    'R1': 'الحرف يؤدي وظيفةً غير العطف في هذا الوجه',
    'R2': 'مخالفة شروط قاعدة الربط',
    'R3': 'اقتطاع جزءٍ من تركيبٍ ثبت دخوله في الطرف',
    'R4': 'ضمّ عنصرٍ إلى الطرف رغم ثبوت تعلّقه خارجه',
    'R5': 'مخالفة علاقةٍ نحوية مثبتة بلا وجهٍ بديل',
    'R6': 'حذفٌ أو عاملٌ مقدَّر لا تجيزه القواعد',
    'R7': 'فساد مواضع النص',
}
DEFER = {
    'D1': ('وظيفة الحرف محتملة', 'دليلٌ يميّز العطف من الوظائف الأخرى'),
    'D2': ('أكثر من رأسٍ سابق جائز', 'دليلٌ على موضع التعلّق'),
    'D3': ('الرأس معلوم والامتداد مختلفٌ فيه', 'دليلٌ على دخول المتعلَّق أو خروجه'),
    'D4': ('اختلافٌ في مستوى العطف', 'تحليلٌ يميّز عطف المفردات من عطف الجمل'),
    'D5': ('نطاق عنصرٍ مشترك غير محسوم', 'دليلٌ على نطاقه'),
    'D6': ('التحليل يتوقف على حذفٍ مختلفٍ فيه', 'قاعدة حذفٍ وشروطٌ متحققة'),
    'D7': ('السياق المتاح لا يكفي', 'استكمال السياق'),
    'D8': ('القاعدة اللازمة غير مغطّاة في النظام', 'استكمال القاعدة وتوثيقها'),
    'D9': ('تعارض أدلةٍ أو تحليلاتٍ معتبرة', 'بيان التعارض ودليل الترجيح'),
}
# معنى العلاقة سؤالٌ غير سؤال الربط: ما يحتمله الحرف، لا ما ثبت
MEANING = {'و': 'مطلق الجمع (لا يثبت به ترتيبٌ ولا معيّة)', 'ف': 'الترتيب والتعقيب، وقد تفيد السببية',
           'ثم': 'الترتيب والتراخي', 'أو': 'التخيير أو الإباحة أو الشك أو التقسيم',
           'أم': 'المعادلة (المتصلة) أو الإضراب (المنقطعة)', 'بل': 'الإضراب', 'لكن': 'الاستدراك',
           'حتى': 'الغاية', 'لا': 'نفي الحكم عن المعطوف'}
SOURCE = 'مصحف المدينة النبوية (مجمع الملك فهد)'
GAMMA = 'coord-rules v1'                            # نسخة القواعد Γ

# سجلّ القواعد (البند ٦): لكل قاعدةٍ معرّفٌ ونسخة ونطاقٌ ومدخلات وسببٌ وشروطٌ وموانع ونتيجةٌ وأثرٌ بنيوي وشاهدٌ
# وحالةٌ مقابلة واعتماداتٌ وحدود تغطية. والشواهد من المصحف؛ والقاعدة لا تُستعمل مقدمةً لإثبات نفسها
def _rule(id_, scope, inputs, cause, conditions, barriers, result, effect, witness, counter, deps, coverage):
    return dict(id=id_, version=1, scope=scope, inputs=inputs, cause=cause, conditions=conditions, barriers=barriers,
                result=result, effect=effect, witness=witness, counter=counter, deps=deps, coverage=coverage)


RULES = {r['id']: r for r in (
    _rule('CO-SINGLE', 'و ف ثم أو، بين مفردين', 'رأسان اسميان بدليل المعجم، وحالتاهما المكتوبتان',
          'حرف عطفٍ يليه اسم', ['الطرف السابق اسمٌ بدليلٍ في الجملة الجارية', 'توافق الحالة أو خفاؤها (المحلّ)'],
          ['اختلاف الحالة الظاهرة (R2)', 'الطرف فعلٌ أو شبه جملة (R2)'], 'Coord(h, A, B) مفرداً',
          'المعطوف يشارك المعطوف عليه عامله', 'ٱلشَّمۡسُ وَٱلۡقَمَرُ (55:5)', 'وَٱلۡقَمَرِ بعد قسم (91:2) ليس قسماً مستأنفاً',
          ['دليل الاسمية', 'الحالة المكتوبة'], 'الاسم الظاهر والموصول والمؤوَّل والمنفصل؛ لا العطف على المتصل المجرور'),
    _rule('CO-MA', 'و، «ما» الموصولة بعد «ما»', '«ما» في كلمتها يليها فعل', 'وَمَا بعد بِمَا',
          ['«ما» الأولى موصولةٌ صلتها فعل', '«ما» الثانية يليها فعل'], ['«ما» نافيةٌ تبدأ جملة'], 'Coord موصولاً على موصول',
          'الصلة داخلة في الطرف، والجارّ خارجهما مشترك', 'بِمَآ أُنزِلَ إِلَيۡكَ وَمَآ أُنزِلَ مِن قَبۡلِكَ (2:4)',
          'وَمَا يَخۡدَعُونَ (2:9): «ما» نافية', ['CO-SINGLE'], '«ما» وحدها، لا «مَن»'),
    _rule('CO-PAIR', 'و، مرفوعان أولهما أول جملته', 'مرفوعان اسميان', 'مرفوعٌ بعد الحرف يلي مرفوعاً في أول جملته',
          ['الأول أول جملته', 'لا خبر بينهما'], ['المرفوع الثاني خبرٌ للأول'], 'Coord مفرداً، والخبر بعده للمجموع',
          'الخبر عنصرٌ مشترك خارج الطرفين', 'ٱلشَّمۡسُ وَٱلۡقَمَرُ بِحُسۡبَانٍ (55:5)', 'زَيۡدٌ قَائِمٌ وَعَمۡرٌو: الثاني جملة',
          ['CO-SINGLE'], 'المبتدآن المتجاوران فقط'),
    _rule('CO-PP', 'و، شبه جملةٍ على شبه جملة', 'جارٌّ ومجرور قبل الحرف وبعده', 'شبه جملةٍ بعد الحرف لا يليها ما يتمّ به كلام',
          ['شبه جملةٍ سابقة في الجملة الجارية', 'يُقدَّم الجارّ نفسه'], ['شبه الجملة يبدأ جملةً اسمية (خبرٌ مقدّم)'],
          'Coord شبهَ جملة', 'الطرفان متعلّقان بعاملٍ واحد', 'مَّتَٰعࣰا لَّكُمۡ وَلِأَنۡعَٰمِكُمۡ (80:32)',
          'وَلَهُمۡ عَذَابٌ: جملة اسمية', [], 'الجارّ المقطَّع أو المتصل بضمير أو باللام والباء المكسورتين'),
    _rule('CO-CLAUSE', 'و ف ثم أو أم، بين جملتين', 'رأس جملةٍ سابقة ورأس جملةٍ لاحقة', 'المعطوف يبدأ جملةً بنفسه',
          ['رأس الجملة السابقة أول رأسٍ رجوعاً لا يُعبر إليه صلةٌ ولا مقول'], ['الحرف رابطة جواب (R1)'],
          'Coord جملة', 'لكل جملةٍ نواتها، ولا توافق إعرابٍ مطلوب', 'ثُمَّ أَمَاتَهُۥ فَأَقۡبَرَهُۥ (80:21)',
          'وَهِيَ خَاوِيَةٌ (2:259): حالٌ مرشّحة', ['clause_word', 'Boundary'], 'الجمل ذات النواة المكشوفة'),
    _rule('CO-SILAH', 'و، صلةٌ على صلة', 'موصولٌ وصلته ونواةٌ بعد الحرف', 'الحرف يلي الصلة مباشرة والمعطوف جملة',
          ['الموصول ليس معمولاً لجملةٍ أوسع، أو فعل المعطوف يوافق فعل الصلة'], ['الصلة اكتملت بحدٍّ مثبت قبل الحرف'],
          'Coord داخل الصلة', 'لا يُغلق الحرفُ الصلة؛ وتبقى الحدود داخلها ممنوعة',
          'ٱلَّذِينَ ءَامَنُواْ وَعَمِلُواْ ٱلصَّٰلِحَٰتِ (2:25)', 'يُخَٰدِعُونَ ٱللَّهَ وَٱلَّذِينَ ءَامَنُواْ وَمَا يَخۡدَعُونَ (2:9)',
          ['relative_structs'], 'الموصول الاسمي'),
    _rule('CO-AM', 'أم بعد همزة', 'همزة في أول الطرف السابق، و«سواء» قبلها', 'أم بين جملتين',
          ['همزةٌ في أول الطرف السابق'], ['لا همزة: متصلةٌ أو منقطعة (D1)'], 'Coord بأم المتصلة، والمنقطعة مرفوضة بعد التسوية',
          '«سواء» وما بعده مشتركٌ خارج المتعادلين', 'سَوَآءٌ عَلَيۡهِمۡ ءَأَنذَرۡتَهُمۡ أَمۡ لَمۡ تُنذِرۡهُمۡ (2:6)',
          'أَمۡ يَقُولُونَ ٱفۡتَرَىٰهُ: منقطعة', [], 'همزة التسوية والاستفهام الظاهرة'),
    _rule('FN-HAL', 'و، واو الحال', 'جملةٌ فعلية تامّة قبل الحرف، وبعده ضميرٌ منفصل أو «قد» والماضي', 'الحرف يلي جملة تامّة',
          ['الجملة السابقة فعلية تامّة', 'المعطوف اسميةٌ مصدّرة بضمير أو «قد» وماضٍ'], [],
          'حالٌ مرشّحة لا تُغلق الجملة السابقة', 'الحدّ قبل الحرف يبقى محتملاً', 'مَرَّ عَلَىٰ قَرۡيَةࣲ وَهِيَ خَاوِيَةٌ (2:259)',
          'وَهُمۡ فِيهَا خَٰلِدُونَ (2:25): عطفٌ أو استئناف', [], 'الضمير والمطابقة الظاهرة'),
    _rule('FN-ISTI', 'و ف، الاستئناف', 'جملةٌ تامّة بعد الحرف', 'الحرف بين جملتين', ['لا تركيب حاوياً مفتوحاً'],
          ['يقطع صلةً أو شرطاً قبل اكتماله (R3)'], 'جملةٌ مستأنفة', 'لا ربط بالجملة السابقة', 'وَجَآءُوٓ أَبَاهُمۡ (12:16)',
          'وَيُقِيمُونَ ٱلصَّلَوٰةَ (2:3): داخل الصلة', ['CO-SILAH'], 'كل حرفٍ بين جملتين'),
    _rule('FN-QASAM', 'و، القسم', 'اسمٌ مجرور بعد الواو', 'الواو في أول السورة أو بعد «كلا»',
          ['لا عامل جرٍّ قبله', 'أول السورة'], ['مقسمٌ به قبله بلا جواب: فالثانية عاطفة (R2)'], 'قسم', 'يطلب جواباً',
          'وَٱلشَّمۡسِ (91:1)', 'وَٱلۡقَمَرِ (91:2): عاطفة', [], 'أول السورة وبعد «كلا»'),
    _rule('FN-JAWAB', 'ف، رابطة الجواب', 'أداة شرطٍ وجوابها', 'الفاء في موضع الجواب', ['ملكية الجواب للأداة'],
          ['الأداة محتملة (D1)'], 'ليست عاطفة', 'يُغلق الشرط بجوابه', 'فَإِن لَّمۡ تَفۡعَلُواْ … فَٱتَّقُواْ (2:24)',
          'الفاء العاطفة بعد جملة تامّة', ['cond_structs'], 'الجازمة وإذا ولو ولمّا'),
    _rule('FN-SABAB', 'ف، السببية', 'مضارعٌ منصوب بعد طلبٍ أو نفي', 'الفاء قبل مضارعٍ منصوب', ['طلبٌ أو نفي قبله'],
          [], 'فاء السببية، والعطف الجملي عليها مرفوض', 'مصدرٌ مؤوَّل', 'لَا تَطۡرُدِ … فَتَكُونَ (6:52)', 'فَيَكُونُ: رفع',
          ['mood'], 'النصب بالفتحة الظاهرة'),
    _rule('FN-BAL', 'بل لكن حتى', 'ما بعد الحرف', 'الحرف قبل جملة أو مفرد', ['ما بعدها جملة'], [],
          'حرف ابتداء، والعطف مرفوض', '—', 'قَالَ بَل لَّبِثۡتَ (2:259)', 'بل + مفرد: عاطفة بشروطها (غير منفَّذة)', [],
          'ما بعدها جملة؛ ومع المفرد مؤجَّل D8'),
    _rule('CO-NEAR', 'كل حرف', 'الكلمة قبل الحرف', 'القرب يولّد مرشّحاً', ['يُفحص كغيره'],
          ['من امتداد طرفٍ آخر (R3)', 'نوعه لا يوافق (R2)'], 'مرشّحٌ يُفحص', '—', 'إِلَيۡكَ وَمَآ (2:4) مرفوض',
          '—', [], 'كل حرف'),
    _rule('CO-LAM', 'و، لام التعليل', 'وَلِ + مضارع', 'لام التعليل بعد الواو', ['معطوفٌ على تعليلٍ مقدَّر'],
          ['لا يُنشأ المقدَّر كلمةً مكتوبة'], 'تأجيل D6', '—', 'وَلِنَجۡعَلَكَ ءَايَةࣰ (2:259)', '—', [], 'غير منفَّذة'),
)}


DECISIONS = ('تثبيت ضمن النطاق المعلن', 'حفظ المستوفيات وتأجيل الانفراد', 'ترخيص الأول وتأجيل الحسم النهائي',
             'رفض العطف ضمن النطاق المختبَر', 'تأجيل محدد السبب')


def _strip(t):
    return ''.join(L for L, _ in letters(t))


class Ctx:
    """سياق السورة الجارية من الطبقة اللغوية"""
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def wid(self, p):
        s, v, wi = self.words[p][:3]
        return f'{s}:{v}:{wi + 1}'                    # ترقيم الكلمة من ١ كما في Quranic Arabic Corpus

    def segs(self, p, skip_conj=True, skip_jarr=False):
        """الوحدات الصرفية من الكلمة الداخلة في الطرف: يُستثنى حرف العطف (وموضعه غير موضع الكلمة)، والجارّ إن طُلب"""
        sg = self.feats[p].get('segs') or [('جذع', self.wtext[p])]
        out = []
        for i, (typ, txt) in enumerate(sg):
            if skip_conj and i == 0 and self.feats[p]['conj'] and len(sg) > 1:
                continue
            if skip_jarr and typ == 'عامل' and i <= 1 and _is_jarr(txt):
                continue
            out.append(f'{self.wid(p)}:{i + 1}')
        return out

    def unit_text(self, uid):
        """نصّ الوحدة الصرفية من معرّفها «الكلمة:الرقم»"""
        wid, i = uid.rsplit(':', 1)
        p = self.pos_of_wid(wid)
        sg = self.feats[p].get('segs') or [('جذع', self.wtext[p])]
        return sg[int(i) - 1][1] if 0 < int(i) <= len(sg) else ''

    def pos_of_wid(self, wid):
        if not hasattr(self, '_wid_pos'):
            self._wid_pos = {self.wid(p): p for p in range(len(self.words))}
        return self._wid_pos[wid]

    def letter_cells(self, p, letter):
        """خلايا الحرف الرابط (حرفٌ وحركة) في وحدات كلمته: هوية الحرف غير هوية الكلمة الحاملة"""
        want = {'و': 'و', 'ف': 'ف', 'ثم': 'ثم', 'أو': 'ءو', 'أم': 'ءم', 'بل': 'بل', 'لكن': 'لكن', 'حتى': 'حت'}.get(letter, '')
        if self.feats[p]['conj'] and self.feats[p]['conj_letter'] in ('و', 'ف') and letter not in ('و', 'ف'):
            want = self.feats[p]['conj_letter'] + want
        out = []
        for G in (self.wunits[p] if getattr(self, 'wunits', None) else []):
            for c in getattr(G, 'A', []) or []:
                L = getattr(c, 'C', None)
                if L is None:
                    continue
                if len(out) < len(want) and L == want[len(out)]:
                    out.append(dict(id=getattr(c, 'id', ''), letter=L))
                else:
                    return out if len(out) == len(want) else []
        return out if len(out) == len(want) else []

    def container(self, p):
        """التركيب الحاوي للموضع: أضيق صلةٍ تحويه، أو ما بين أداة الشرط وجوابها"""
        best = None
        for r in self.rels:
            if r['head'] < p < self.eff_end[r['head']] and (best is None or r['head'] > best[0]):
                best = (r['head'], f'صلة «{self.wtext[r["head"]]}» ({self.wid(r["head"])})')
        if best:
            return best[1]
        for h, q, tool, *rest in self.cond_spans:
            # الشرط حاوٍ إن ثبت جوابه مملوكاً له؛ والجواب المرشَّح لا يُنشئ حاوياً يُرفض به منافس
            if q is not None and h < p < q and (not rest or rest[0]):
                return f'جملة الشرط «{tool}» ({self.wid(h)})'
        return None

    def _khabar_after(self, r):
        """خبر الموصول المبتدأ بقرينةٍ مستقلة عن الطرف: الموصول أول آيته (أو بعد عاطفٍ في أولها)، وبعد صلته
        كلامٌ كلّه معطوفٌ بالواو، ثم أول مسندٍ بلا عاطف (اسم إشارة، أو ضمير، أو نواة) قبل ما له الصدارة"""
        f, h = self.feats, r['head']
        if not (h == 0 or self.ay_end[h - 1] or h > 1 and f[h]['conj'] and self.ay_end[h - 2]):
            return None, 'الموصول ليس أول آيته: لا يثبت أنه مبتدأ'
        lim = next((i for i in range(h + 1, len(f)) if self.ay_end[i] and i > h and
                    sum(1 for j in range(h, i + 1) if self.ay_end[j]) >= 2), len(f) - 1)
        for k in range(r['end'], min(len(f), lim + 1)):
            g = f[k]
            if self.starts[k]:
                return None, 'ما له الصدارة قبل الخبر'
            if g['conj']:
                continue
            if g.get('demo') or g.get('head') == 'pron' and k > r['end'] and f[k - 1]['conj'] is False and \
                    self.ay_end[k - 1]:
                return k, 'اسم إشارةٍ أو ضميرٌ بلا عاطفٍ بعد كلامٍ معطوف'
        return None, 'لا مسند بلا عاطفٍ بعد الصلة إلى آخر الآية التالية'

    def container_evidence(self, p, b_end):
        """الدليل المستقل على أن الحاوي باقٍ مفتوحاً بعد الطرف (مراجعة التقرير السادسة ٤): التزامٌ لازمٌ يُستوفى بعده
        → (الحاوي، الدليل أو None)"""
        c = self.container(p)
        if not c:
            return None, None
        for r in sorted(self.rels, key=lambda r: -r['head']):
            if r['head'] < p < self.eff_end[r['head']]:
                kk, why = self._khabar_after(r)
                if kk is not None and kk > b_end:
                    return c, (f'الموصول «{self.wtext[r["head"]]}» مبتدأٌ خبره عند {self.wid(kk)} «{self.wtext[kk]}» '
                               f'بعد الطرف ({why})، فالتزام الخبر مفتوحٌ عبره')
                return c, None
        for h, q, tool, *rest in self.cond_spans:
            if q is not None and h < p < q and (not rest or rest[0]) and q > b_end:
                return c, f'جواب «{tool}» ثابتٌ عند {self.wid(q)} بعد الطرف، فجملة الشرط مفتوحةٌ عبره'
        return c, None


def _is_jarr(t):
    from .algebra import JARR_V, is_form
    return is_form(t, JARR_V)


def _member(X, pos, head, typ, why, skip_jarr=False):
    pos = sorted(set(pos))
    segs = []
    for p in pos:
        segs += X.segs(p, skip_conj=(p == pos[0]), skip_jarr=skip_jarr and p == pos[0])
    return dict(head=X.wtext[head], head_id=X.wid(head), head_pos=head, positions=pos, words=[X.wid(p) for p in pos],
                units=segs, text=_units_text(X, segs), envelope_text=' '.join(X.wtext[p] for p in pos), type=typ,
                extent_evidence=why, envelope=[X.wid(pos[0]), X.wid(pos[-1])],
                representation='رأس الطرف: الاسم في المفرد، والجارّ ومجروره في شبه الجملة، والنواة في الجملة')


def _units_text(X, units):
    """نصّ الطرف من عضويته (مراجعة التقرير السادسة ٥): وحداتُ الكلمة الواحدة متصلة، والكلمات بمسافة؛ فما خرج
    من العضوية (العاطف، والجارّ المشترك) لا يظهر في النص، والغلاف النصي يُعرض منفصلاً (envelope_text)"""
    out, cur, last = [], '', None
    for u in units:
        wid = u.rsplit(':', 1)[0]
        if wid != last and cur:
            out.append(cur)
            cur = ''
        cur += X.unit_text(u)
        last = wid
    if cur:
        out.append(cur)
    return ' '.join(out)


def _ma_silah(X, p, limit):
    """«ما» الموصولة في كلمتها (بِمَا، وَمَا) يليها فعل: صلتها إلى أول حدٍّ قبل limit"""
    from .algebra import is_form, _madi_like
    f = X.feats
    if not is_form(f[p]['text'], ('مَا', 'وَمَا', 'بِمَا', 'مِمَّا', 'لِمَا', 'عَمَّا', 'فِيمَا', 'وَبِمَا', 'وَمِمَّا',
                                  'مَنْ', 'وَمَنْ', 'بِمَنْ', 'لِمَنْ', 'مِمَّنْ')) or \
            p + 1 >= len(f) or not (f[p + 1]['verb'] or p + 1 in X.nset or _madi_like(f[p + 1]['text']) or
                                    f[p + 1].get('vshape') and not f[p + 1].get('noun')):
        return None
    return min(X.next_stop(p), limit)


def extent_single(X, p, limit):
    """امتداد الطرف المفرد من رأسه: المضاف إليه بعده، وصلة الموصول؛ ولا يُضمّ ما يجاور الرأس بلا علاقة
    → (المواضع، الأدلة)"""
    from .algebra import is_form, JARR_V
    f = X.feats
    pos, why = [p], ['الرأس']
    if p in X.rel_at:
        e = min(X.eff_end[p], limit)
        pos += list(range(p + 1, e))
        why.append(f'صلة الموصول إلى {X.wid(e - 1)}')
        return pos, why
    e = _ma_silah(X, p, limit)
    if e is not None:
        pos += list(range(p + 1, e))
        why.append('«ما» موصولةٌ يليها فعلٌ: صلتها داخلةٌ في الطرف')
        return pos, why
    if is_form(f[p]['text'], JARR_V) and p + 1 < limit and not f[p + 1]['conj']:
        pos.append(p + 1)
        why.append(f'مجرور الجارّ «{X.wtext[p + 1]}»')
        return pos, why
    q = p
    while q + 1 < limit and f[q].get('noun') and not f[q].get('al') and not f[q].get('nakira') and \
            not f[q + 1]['conj'] and f[q + 1].get('noun') and f[q + 1]['case'] in ('جر', 'جر أو نصب') and \
            not X.starts[q + 1] and len(pos) < 4 and len(f[q].get('segs') or ()) <= 2:
        q += 1
        pos.append(q)
        why.append(f'مضافٌ إليه «{X.wtext[q]}»: الأول بلا «أل» ولا تنوين، والثاني مجرور')
    return pos, why


def _cand(cid, function, level, A, B, letter, rules=()):
    return dict(id=cid, function=function, level=level, A=A, B=B, container=None, shared=[], checks={},
                barriers=[], deferrals=[], evidence=[], status=None, rules=list(rules),
                meaning=dict(possible=MEANING.get(letter, ''), established=None,
                             note='ثبوت الربط لا يثبت ترتيباً ولا سببيةً ولا تخييراً'),
                provenance='مستنتجٌ بقواعد النظام (لا وسم مرجعي في المدخلات)')


def _finish(c):
    """حالة المرشّح من شروطه وموانعه"""
    if c['barriers']:
        c['status'] = 'مرفوض'
    elif c['deferrals']:
        c['status'] = 'مؤجَّل'
    elif c['checks'] and all(v[0] for v in c['checks'].values()):
        c['status'] = 'مستوفٍ'
    else:
        miss = [k for k, v in c['checks'].items() if not v[0]]
        c['deferrals'].append(('D8', 'لم يتحقق: ' + '، '.join(miss), DEFER['D8'][1]))
        c['status'] = 'مؤجَّل'
    req = sorted({b for r in c['rules'] if r in RULES for b in RULES[r]['barriers']})
    c['checks']['A8'] = (not c['barriers'], ('انتفاء الموانع التي توجب القاعدة فحصها، وقد فُحصت: ' + '؛ '.join(req))
                         if not c['barriers'] and req else 'لا مانع تفرض القاعدة فحصه' if not c['barriers'] else 'قام مانع')
    ch = c['checks']
    g = lambda a: ch.get(a, (False,))[0]
    # جهاتٌ مستقلة: ترخيص الربط، وإثبات الامتداد (البند ١١)
    c['LinkLicensed'] = all(g(a) for a in ('A1', 'A3', 'A4', 'A6', 'A7', 'A8'))
    c['ExtentCertified'] = g('A2') and g('A5') and not any(d[0] in ('D3', 'D6') for d in c['deferrals'])
    return c


def _check(c, code, ok, why):
    c['checks'][code] = (bool(ok), why)


def _shared_single(X, c, letter):
    """العناصر المشتركة خارج الطرفين في عطف المفرد، لكلٍّ قرارٌ مستقل"""
    from .algebra import is_form
    f, A, B = X.feats, c['A'], c['B']
    out = []
    a0 = A['positions'][0]
    sg = f[a0].get('segs') or []
    jarr = next((t for i, (typ, t) in enumerate(sg[:2]) if typ == 'عامل' and _is_jarr(t)), None)
    bsg = f[B['positions'][0]].get('segs') or []
    b_jarr = any(typ == 'عامل' and _is_jarr(t) for typ, t in bsg[:2])
    if jarr and not b_jarr and c['level'] == 'مفرد':
        out.append(dict(element=f'الجارّ «{jarr}» في {X.wid(a0)}', between=[A['head_id'], B['head_id']],
                        status='اشتراك مثبت', evidence='المعطوف على المجرور يتبعه في عامله، والجارّ خارج امتداد الطرف'))
    if c['level'] == 'شبه جملة' and a0 > 0 and not X.starts[a0] and not X.ay_end[a0 - 1] and \
            (f[a0 - 1].get('noun') or f[a0 - 1]['verb'] or (a0 - 1) in X.nset):
        # المتعلَّق الأعلى: الجارّ داخل كل طرف، والطرفان متعلّقان معاً بما قبلهما (مَتَٰعࣰا لَّكُمۡ وَلِأَنۡعَٰمِكُمۡ)
        out.append(dict(element=f'المتعلَّق «{X.wtext[a0 - 1]}» ({X.wid(a0 - 1)})', between=[A['head_id'], B['head_id']],
                        status='اشتراك مثبت', evidence='الطرفان شبها جملة متعلّقان بعاملٍ واحد بحكم العطف؛ '
                                                         'والجارّ عضوٌ في كل طرف لا مشترك'))
    # عامل الجملة قبل الطرف السابق (لا من داخل صلته)
    gov = next((j for j in range(a0 - 1, max(-1, a0 - 6), -1) if j in X.nset or f[j]['verb']), None)
    if gov is not None and not any(X.starts[j] for j in range(gov + 1, a0 + 1)) and \
            not any(r['head'] < gov < X.eff_end[r['head']] <= a0 for r in X.rels) and not X.ay_end[gov]:
        out.append(dict(element=f'العامل «{X.wtext[gov]}» ({X.wid(gov)})', between=[A['head_id'], B['head_id']],
                        status='اشتراك مثبت', evidence='الطرفان معمولان لعاملٍ واحد بواسطة الحرف'))
    neg = next((j for j in range(a0 - 1, max(-1, a0 - 5), -1) if f[j].get('neg') and not X.starts[j]), None)
    if neg is not None and gov is not None and neg < gov:
        out.append(dict(element=f'النفي «{X.wtext[neg]}»', between=[A['head_id'], B['head_id']], status='اشتراك مثبت',
                        evidence='المفرد المعطوف داخل الجملة المنفية نفسها'))
    e = B['positions'][-1] + 1
    if c.get('khabar') is not None:
        k0, k1 = c['khabar']
        out.append(dict(element=f'الخبر «{" ".join(X.wtext[k0:k1])}» ({X.wid(k0)})', between=[A['head_id'], B['head_id']],
                        status='اشتراك مثبت',
                        evidence='الطرفان مبتدآن ولا خبر بينهما، وما بعد الثاني خبرٌ عن المجموع لا جزءٌ من الطرف'))
    elif e < len(f) and not f[e]['conj'] and not X.starts[e] and not X.ay_end[e - 1]:
        g = f[e]
        if is_form(g['text'], ('إِلَّا',)):
            out.append(dict(element=f'الاستثناء «{X.wtext[e]}» ({X.wid(e)})', between=None, status='نطاق مؤجَّل',
                            evidence='يُستثنى من الأخير أو من المجموعة', defer='D5'))
        elif g.get('head') == 'pp' or g.get('noun') and g['case'] and f[B['head_pos']]['case'] and \
                g['case'] == f[B['head_pos']]['case'] and (g.get('al') == f[B['head_pos']].get('al')):
            out.append(dict(element=f'«{X.wtext[e]}» ({X.wid(e)})', between=None, status='نطاق مؤجَّل',
                            evidence='صفةٌ أو حالٌ أو متعلَّقٌ بعد المعطوف: للأخير أو للمجموعة', defer='D5'))
    for h, q, tool, *_ in X.cond_spans:
        if q is not None and h < a0 and B['positions'][-1] < q:
            out.append(dict(element=f'الشرط «{tool}» ({X.wid(h)})', between=[A['head_id'], B['head_id']],
                            status='اشتراك مثبت', evidence='الطرفان بين الأداة وجوابها'))
    return out


def _shared_clause(X, c, letter):
    from .algebra import is_form
    f, A, B = X.feats, c['A'], c['B']
    out = []
    a0, b0 = A['positions'][0], B['positions'][0]
    an = any(f[p].get('neg') for p in A['positions'][:2])
    bn = any(f[p].get('neg') for p in ([b0 + 1] if letter in ('أو', 'ثم', 'أم') else [b0]) + B['positions'][1:2]
             if p < len(f))
    if an and bn:
        out.append(dict(element='النفي', between=None, status='اختصاص مثبت', evidence='لكلّ طرفٍ نفيُه الظاهر'))
    elif an:
        out.append(dict(element=f'النفي في الطرف السابق ({X.wid(a0)})', between=None, status='نطاق مؤجَّل',
                        evidence='ثبوت الطرفين لا يثبت اشتراكهما في النفي', defer='D5'))
    for h, q, tool, *_ in X.cond_spans:
        if q is None:
            continue
        if h < a0 and B['positions'][-1] < q:
            out.append(dict(element=f'الشرط «{tool}» ({X.wid(h)})', between=[A['head_id'], B['head_id']],
                            status='اشتراك مثبت', evidence='الطرفان بين الأداة وجوابها: كلاهما في جملة الشرط'))
        elif a0 >= q > h and A['positions'][0] <= q:
            out.append(dict(element=f'جواب «{tool}» ({X.wid(h)})', between=None, status='نطاق مؤجَّل',
                            evidence='الطرف السابق جوابٌ: دخول اللاحق في الجواب أو استقلاله', defer='D5'))
    if letter == 'أم':
        pre = [j for j in range(a0 - 1, max(-1, a0 - 4), -1)
               if not (j in X.nset or f[j]['verb']) and not X.ay_end[j]]
        pre = [j for j in pre if all(not (i in X.nset or f[i]['verb']) for i in range(j, a0))]
        if any(is_form(f[j]['text'], ('سَوَاءٌ', 'سَوَآءٌ', 'وَسَوَاءٌ'), prefix=True) for j in pre):
            j0 = min(pre)
            out.append(dict(element=f'«{" ".join(X.wtext[j0:a0])}» ({X.wid(j0)})', between=[A['head_id'], B['head_id']],
                            status='اشتراك مثبت', evidence='المتعادلان بعد «سواء» وهمزة التسوية في محلٍّ واحد معاً'))
    return out


def _has_taswiya(X, a0):
    from .algebra import is_form
    f = X.feats
    hamza = f[a0]['text'][:1] in 'ءأ' and _strip(f[a0]['text'])[:1] in 'ءأ' and len(letters(f[a0]['text'])) > 3
    sawa = any(is_form(f[j]['text'], ('سَوَاءٌ', 'سَوَآءٌ'), prefix=True) for j in range(max(0, a0 - 3), a0))
    return hamza, sawa


def site_record(c_, X):
    """سجلّ الموضع لمرشّحات العطف من بنية coord_structs بعد تعيين طرفيها في الطبقة اللغوية"""
    from .algebra import (is_form, PRON_FREE_V, CASE_COMPAT, clause_word, _madi_like, _hollow_madi)
    f, w = X.feats, X.wtext
    k, letter, level = c_['pos'], c_['letter'], c_['level']
    standalone = letter in ('أو', 'ثم', 'أم')
    h = c_['B']
    n = len(f)
    cands = []
    coverage = 'مكتملة ضمن نطاق البحث المعلن (الجملة الجارية والسورة المقروءة)'
    if k <= 1 and not X.surah_start:
        coverage = 'ناقصة: النص المقروء يبدأ بعد أول السورة'
    verse_initial = k > 0 and X.ay_end[k - 1]
    cont = X.container(k)

    def coord_checks(c, a_ok, rule, case_ok, ext_ok, cont_ok):
        _check(c, 'A1', True, f'«{letter}» من حروف العطف، ولم يثبت لها في هذا الوجه وظيفةٌ أخرى')
        _check(c, 'A2', a_ok, 'الرأسان معيَّنان' if a_ok else 'لم يُعيَّن رأس الطرف السابق')
        _check(c, 'A3', bool(rule), rule or 'لا قاعدة ربط')
        _check(c, 'A4', case_ok[0], case_ok[1])
        _check(c, 'A5', ext_ok[0], ext_ok[1])
        _check(c, 'A6', cont_ok[0], cont_ok[1])
        _check(c, 'A7', True, 'لا حذفَ مقدَّراً في هذا الوجه، والمشاركة في العامل من حكم العطف نفسه')

    # ---------- مرشّحات العطف ----------
    if level in ('مفرد', 'شبه جملة'):
        b_pos, b_why = extent_single(X, h, n)
        khabar = None
        if c_.get('note', '').startswith('مرفوعان'):
            e = b_pos[-1] + 1
            if e < n and not f[e]['conj'] and not X.starts[e]:
                k1 = min(X.next_stop(e - 1), n)
                khabar = (e, max(k1, e + 1))
        B = _member(X, b_pos, h, 'شبه جملة' if level == 'شبه جملة' else 'مفرد', b_why)
        a_list = list(c_['A'])
        weak = []
        # بلا مرشّحٍ بدليل الاسمية: ما في الجملة الجارية من كلمةٍ ظاهرة الحالة لم تثبت اسميتها مرشّحٌ مؤجَّل (D8)،
        # لا موضعٌ يُسقط؛ ويقف البحث عند أول فعلٍ أو ما له الصدارة أو آخر الآية (سببٌ لغوي معلن)
        if not a_list and level == 'مفرد':
            for j in range(k - 1, max(-1, k - 12), -1):
                fj = f[j]
                if X.ay_end[j] and j < k - 1:
                    break
                if fj['verb'] or j in X.nset or fj.get('vshape') and not fj.get('noun'):
                    break
                if fj['case'] and fj.get('head') != 'pp' and \
                        (not f[h]['case'] or f[h]['case'] in CASE_COMPAT and fj['case'] in CASE_COMPAT[f[h]['case']] or
                         fj['case'] in CASE_COMPAT and f[h]['case'] in CASE_COMPAT[fj['case']]):
                    weak.append(j)
                if X.starts[j]:
                    break
            a_list = weak[:3]
        lam_v = _lam_verb(f[h])
        # المعطوف المرفوع على ضمير رفعٍ منفصلٍ قبله (ٱسۡكُنۡ أَنتَ وَزَوۡجُكَ): المنفصل يؤكّد المستتر فيجوز العطف
        if level == 'مفرد' and f[h]['case'] == 'رفع' and k > 0 and is_form(f[k - 1]['text'], PRON_FREE_V) and \
                k - 1 not in a_list:
            a_list.append(k - 1)
        for i, j in enumerate(a_list or [None]):
            c = _cand(f'C{len(cands) + 1}', 'عطف', level, None, B, letter, ['CO-PP'] if level == 'شبه جملة' else ['CO-PAIR', 'CO-SINGLE'] if c_.get('note', '').startswith('مرفوعان') else ['CO-MA', 'CO-SINGLE'] if c_.get('note', '').startswith('«') else ['CO-SINGLE'])
            if j is not None:
                a_pos, a_why = extent_single(X, j, k)
                c['A'] = _member(X, a_pos, j, B['type'], a_why, skip_jarr=level == 'مفرد')
                fa, fb = f[j], f[h]
                if level == 'شبه جملة':
                    rule, case_ok = 'جارٌّ ومجرور على جارٍّ ومجرور', (True, 'لا يُشترط إعرابٌ ظاهر لشبه الجملة')
                else:
                    rule = 'اسمٌ على اسم' if (fa.get('noun') or fa.get('rel') or fa.get('an') or fa.get('maqsur') or
                                               is_form(fa['text'], PRON_FREE_V) or _ma_silah(X, j, k)) else None
                    hidden = fa.get('maqsur') or fb.get('maqsur') or fa.get('rel') or fb.get('rel') or \
                        fb.get('an') or fa.get('an') or not fa['case'] or not fb['case'] or \
                        is_form(fa['text'], PRON_FREE_V) or _ma_silah(X, h, n)
                    if hidden:
                        case_ok = (True, 'لا تعارض في الإعراب: الحالة لا تظهر في أحد الطرفين (مبنيٌّ أو مقصورٌ أو مؤوَّل)؛ '
                                         'والمحلّ نتيجةٌ للعطف لا دليلٌ عليه، فلا يُحتجّ بخفاء العلامة')
                    elif fb['case'] in CASE_COMPAT and fa['case'] in CASE_COMPAT[fb['case']]:
                        case_ok = (True, f'توافق الحالة المكتوبة ({fa["case"]}): قرينةٌ لا دليلٌ كافٍ وحدها')
                    else:
                        case_ok = (False, f'اختلاف الحالة الظاهرة ({fa["case"]} / {fb["case"]})')
                ca = X.container(j)
                cont_ok = (True, f'الطرفان في {ca}' if ca else 'الطرفان خارج كل تركيبٍ حاوٍ') if ca == cont else \
                    (False, f'الطرف السابق في {ca or "الجملة الخارجية"} والحرف في {cont or "الجملة الخارجية"}')
                a_nom = bool(fa.get('noun') or fa.get('rel') or fa.get('an') or fa.get('maqsur') or
                             is_form(fa['text'], PRON_FREE_V) or _ma_silah(X, j, k))
                b_nom = bool(fb.get('noun') or fb.get('rel') or fb.get('an') or _ma_silah(X, h, n))
                if level == 'مفرد' and not (a_nom and b_nom):
                    who = [w[x] for x, ok_ in ((j, a_nom), (h, b_nom)) if not ok_]
                    c['deferrals'].append(('D8', 'لم يثبت دليل الاسمية لـ' + ' و'.join(f'«{x}»' for x in who) +
                                           ' في المعجم المنفَّذ' + ('، والمقصور لا يدلّ عليها وحده'
                                                                    if fb.get('maqsur') and not b_nom else ''),
                                           DEFER['D8'][1]))
                    rule = rule or 'اسمٌ على اسم (مشروطٌ بثبوت الاسمية)'
                coord_checks(c, True, rule, case_ok, (True, 'الامتداد بعلاقاتٍ مثبتة: ' + '؛ '.join(a_why[1:] + b_why[1:])
                                                      if len(a_why) + len(b_why) > 2 else 'كلٌّ من الطرفين كلمته'),
                             cont_ok)
                if not cont_ok[0]:
                    c['deferrals'].append(('D3', cont_ok[1] + ': امتداد التركيب الحاوي غير محسوم', DEFER['D3'][1]))
                if not case_ok[0]:
                    c['barriers'].append(('R2', case_ok[1]))
                if len(a_list) > 1:
                    c['evidence'].append('مرشَّحٌ من أكثر من رأسٍ سابق جائز')
            elif lam_v:
                coord_checks(c, False, None, (False, '—'), (False, 'لا طرف سابق مكتوب'), (True, '—'))
                c['level'] = 'جملة'
                c['B'] = _member(X, list(range(k, X.b_stop(h))), h, 'جملة', ['لام التعليل والمضارع إلى حدّه المشتقّ'])
                c['rules'].append('CO-LAM')
                c['deferrals'].append(('D6', 'لامُ التعليل والمضارع بعد الواو: المعطوف عليه تعليلٌ مقدَّر، ولا يُنشأ '
                                             'المقدَّر كلمةً مكتوبة بلا قاعدة حذفٍ منفَّذة', DEFER['D6'][1]))
            else:
                coord_checks(c, False, None, (False, '—'), (False, 'لا طرف سابق'), (True, '—'))
                c['deferrals'].append(('D2' if coverage.startswith('مكتملة') else 'D7',
                                       'لم يُعيَّن رأسٌ سابق صالح' + ('' if coverage.startswith('مكتملة') else '؛ ' + coverage),
                                       DEFER['D2' if coverage.startswith('مكتملة') else 'D7'][1]))
            c['container'] = cont
            c['khabar'] = khabar
            if c['A']:
                c['shared'] = _shared_single(X, c, letter)
            c.pop('khabar')
            cands.append(_finish(c))
        # المرشّح الأقرب (الكلمة قبل الحرف) إن لم يكن منها: القرب يولّد مرشّحاً، ويُفحص
        near = k - 1 if not standalone else k - 1
        if near >= 0 and near not in a_list and not X.ay_end[near] and not X.starts[k]:
            c = _cand(f'C{len(cands) + 1}', 'عطف', level, _member(X, [near], near, 'مفرد', ['الأقرب']), B, letter, ['CO-NEAR'])
            c['evidence'].append('مرشّح القرب وحده')
            inside = next((x for x in cands if x['A'] and near in x['A']['positions'] and near != x['A']['head_pos']), None)
            fn = f[near]
            if inside:
                c['barriers'].append(('R3', f'«{w[near]}» من امتداد الطرف «{inside["A"]["head"]}» '
                                            f'({"؛ ".join(inside["A"]["extent_evidence"][1:]) or "تابعٌ له"})، وجعله طرفاً يقتطعه'))
            elif level == 'مفرد' and (fn['verb'] or near in X.nset):
                c['barriers'].append(('R2', f'«{w[near]}» فعلٌ والمعطوف اسم: لا يُعطف المفرد على الفعل'))
            elif level == 'مفرد' and fn.get('head') == 'pp' and not f[h].get('head') == 'pp' and \
                    not is_form(fn['text'], PRON_FREE_V):
                c['barriers'].append(('R2', f'«{w[near]}» شبه جملة والمعطوف اسمٌ مفرد'))
            if c['barriers']:
                c['checks'] = {'A1': (True, '')}
                cands.append(_finish(c))
        if khabar is not None:
            e0, e1 = khabar
            bx = _member(X, b_pos + list(range(e0, e1)), h, 'مفرد', b_why + ['ضمّ ما بعده'])
            c = _cand(f'C{len(cands) + 1}', 'عطف', level, cands[0]['A'], bx, letter, ['CO-PAIR'])
            c['checks'] = {'A1': (True, '')}
            c['barriers'].append(('R4', f'«{" ".join(w[e0:e1])}» خبرٌ عن الطرفين معاً، فإدخاله في الطرف اللاحق ضمٌّ لما ثبت '
                                        'تعلّقه خارجه'))
            cands.append(_finish(c))
    elif level == 'جملة':
        bf = c_.get('B_full') or {}
        sp = bf.get('span') or (k, k)
        b_pos = list(range(sp[0], sp[1] + 1))
        # رأس اللاحق: أول فعلٍ من أوله (c_['b_head'] من الطبقة)، لا أول نواةٍ فيه (يَبۡكُونَ حالٌ داخل «وَجَآءُوٓ»)
        bh = c_['b_head'] if c_.get('b_head') is not None and c_['b_head'] in b_pos else \
            next((p for p in b_pos if p in X.nset or f[p]['verb']), b_pos[0] if not standalone else min(k + 1, n - 1))
        B = _member(X, b_pos, bh, bf.get('type') or 'جملة', [bf.get('evidence', '')] + list(bf.get('relations') or []))
        alts = [a for a in c_['A'] if isinstance(a, dict)]
        cont_c, cont_ev = X.container_evidence(k, b_pos[-1])
        # رؤوسٌ أبعد رجوعاً (مراجعة التقرير السادسة ٧): أول رأسٍ رجوعاً مرشّحٌ لا مثبت؛ فيُولَّد ما قبله في الآية
        # والتي قبلها رؤوساً بديلة، إلا ما خرج عن حاوٍ ثبت بقاؤه مفتوحاً
        hd = getattr(X, 'clause_head', None)
        if hd and alts and not any('صلة' in a['type'] for a in alts) and \
                not (letter == 'أم' and _has_taswiya(X, alts[0]['span'][0])[0]):
            a_first = min(a['span'][0] for a in alts)
            lim = a_first
            vs = [j for j in range(a_first - 1, -1, -1) if X.ay_end[j]]
            floor = vs[1] + 1 if len(vs) > 1 else 0
            extra = []
            for j in range(a_first - 1, max(floor - 1, a_first - 16), -1):
                if hd(j) and j not in [a['span'][0] for a in alts]:
                    if cont_ev and X.container(j) != X.container(k):
                        break
                    extra.append(dict(span=(j, lim - 1), head=w[j], type='جملة سابقة أبعد',
                                      container=None, evidence='رأسٌ أبعد رجوعاً: الطرف السابق قد يكون في مستوى أعلى'))
                    lim = j
                    if len(extra) == 2:
                        break
            alts = alts + extra
        bvk = f[bh]['verb'] or f[bh].get('vshape')
        for a in alts or [None]:
            c = _cand(f'C{len(cands) + 1}', 'عطف', 'جملة', None, B, letter, ['CO-AM'] if letter == 'أم' else ['CO-CLAUSE'])
            if a:
                a0, a1 = a['span']
                ah = next((p for p in range(a0, a1 + 1) if w[p] == a['head']), a0)
                c['A'] = _member(X, list(range(a0, a1 + 1)), ah, a['type'], [a.get('evidence', '')])
                c['container'] = a.get('container')
                if c['container'] and c['container'].startswith('الموصول'):
                    c['container'] = 'صلة ' + c['container']
                    c['rules'].append('CO-SILAH')
                    if not cont_ev:
                        c['deferrals'].append(('D3', 'نطاق الصلة غير مثبتٍ بدليلٍ مستقل: لا التزامَ لازماً للموصول يُستوفى '
                                                     'بعد الطرف، وموافقة الفعلين قرينةٌ لا دليل', DEFER['D3'][1]))
                    else:
                        c['evidence'].append('دليل بقاء الحاوي مفتوحاً: ' + cont_ev)
                avk = f[ah]['verb'] or f[ah].get('vshape')
                rule = 'جملةٌ على جملة' if clause_word(f, k if not standalone else k + 1, X.nset) or bh in X.nset or \
                    f[bh]['verb'] or (bf.get('type') or '').startswith('جملة') else None
                coord_checks(c, True, rule, (True, 'عطف الجمل لا يُشترط فيه توافق الإعراب' +
                                             ('؛ واختلاف زمن الفعلين ليس مانعاً' if avk and bvk and avk != bvk else '')),
                             (True, 'الطرف السابق من رأسه إلى الحرف، واللاحق إلى أول حدٍّ يبدأ بعد اكتماله'),
                             (True, f'الطرفان في {c["container"]}' if c['container'] else 'جملتان في مستوى واحد'))
                if 'بديل' in a['type']:
                    c['evidence'].append('بديلٌ محفوظ: الموصول حجّةٌ في جملةٍ أوسع')
                c['tense'] = (avk, bvk)
                c['shared'] = _shared_clause(X, c, letter)
                if letter == 'أم':
                    hamza, sawa = _has_taswiya(X, a0)
                    c['function'] = 'عطف («أم» المتصلة)'
                    if hamza:
                        c['evidence'].append('همزةٌ في أول الطرف السابق' + (' بعد «سواء»: همزة التسوية' if sawa else ''))
                    else:
                        c['deferrals'].append(('D1', 'لا همزة استفهامٍ أو تسويةٍ ظاهرة قبل «أم»: متصلةٌ أو منقطعة',
                                               DEFER['D1'][1]))
            else:
                coord_checks(c, False, None, (False, '—'), (False, 'لا طرف سابق'), (True, '—'))
                c['deferrals'].append(('D7' if not coverage.startswith('مكتملة') else 'D2',
                                       'لم يُعيَّن رأس جملةٍ سابقة' + ('' if coverage.startswith('مكتملة') else '؛ ' + coverage),
                                       DEFER['D7' if not coverage.startswith('مكتملة') else 'D2'][1]))
            cands.append(_finish(c))
        # «وَمَنۡ خَلَقۡتُ»، «وَمَا تُعۡلِنُونَ»: «مَن» و«ما» بعد الواو قد تكونان موصولتين معطوفتين على مفرد (على ياء
        # «ذَرۡنِي»، أو على «ما» قبلها)، فيُولَّد مرشّحٌ مفردٌ منافسٌ للجملة، ولا يُحسم المستوى بلا دليل (D4)
        if letter == 'و' and is_form(f[k]['text'], ('وَمَنْ', 'وَمَا')) and _ma_silah(X, k, n):
            e = _ma_silah(X, k, n)
            bm = _member(X, list(range(k, e)), k, 'مفرد', ['«مَن» أو «ما» موصولةٌ وصلتها داخلة في الطرف'])
            prev = [j for j in range(k - 1, max(-1, k - 9), -1)
                    if is_form(f[j]['text'], ('مَا', 'مَنْ', 'بِمَا', 'لِمَا', 'مِمَّا', 'بِمَنْ', 'لِمَنْ'), prefix=True) and
                    _ma_silah(X, j, k)]
            enc = None
            if not prev and k > 0:
                sg = f[k - 1].get('segs') or []
                seg_enc = len(sg) > 1 and sg[-1][0] == 'مبني' and is_form(sg[-1][1], ('نِي', 'هُ', 'هُمْ', 'كَ', 'كُمْ', 'نَا', 'هَا'))
                # نون الوقاية وياء المتكلم في آخر الكلمة (ذَرۡنِي): ضمير نصبٍ متصلٌ بفعل، وإن لم يقطّعه المقشِّر
                wiqaya = _strip(f[k - 1]['text']).endswith('ني') and len(letters(f[k - 1]['text'])) >= 3 and \
                    not f[k - 1].get('noun')
                if seg_enc and (f[k - 1]['verb'] or (k - 1) in X.nset or f[k - 1].get('vshape')) or wiqaya:
                    enc = k - 1
            for j in prev[:1] or ([enc] if enc is not None else []):
                c = _cand(f'C{len(cands) + 1}', 'عطف', 'مفرد', None, bm, letter, ['CO-MA', 'CO-SINGLE'])
                if j == enc:
                    am = _member(X, [j], j, 'مفرد', ['الضمير المتصل في آخر الفعل'])
                    if len(f[j].get('segs') or ()) > 1:
                        am['units'] = [f'{X.wid(j)}:{len(f[j]["segs"])}']
                        am['text'] = _units_text(X, am['units'])
                        am['head'] = am['text']
                    else:
                        am['extent_evidence'].append('الضمير غير مقطَّعٍ عن فعله: العضوية الكلمة كلها، والرأس ضميرها')
                    c['evidence'].append('المعطوف عليه ضمير نصبٍ متصل: العطف على الضمير المنصوب جائزٌ بلا فصل')
                else:
                    am = _member(X, list(range(j, _ma_silah(X, j, k))), j, 'مفرد', ['موصولٌ وصلته'],
                                 skip_jarr=True)
                c['A'] = am
                coord_checks(c, True, 'موصولٌ على موصولٍ أو على ضمير', (True, 'لا تعارض في الإعراب: الموصول مبنيّ، '
                                                                         'والمحلّ نتيجةٌ للعطف لا دليلٌ عليه'),
                             (True, 'الطرف موصولٌ وصلته'), (True, '—'))
                c['shared'] = []
                cands.append(_finish(c))
        # الوظائف الأخرى للحرف في عطف الجمل
        if letter == 'أم' and alts:
            hamza, sawa = _has_taswiya(X, alts[0]['span'][0])
            c = _cand(f'C{len(cands) + 1}', '«أم» المنقطعة (إضراب)', 'جملة', None, B, letter, ['CO-AM'])
            c['checks'] = {'A1': (True, '')}
            if hamza and sawa:
                c['barriers'].append(('R2', '«أم» بعد همزة التسوية لا تكون إلا متصلة'))
            else:
                c['deferrals'].append(('D1', 'المنقطعة جائزةٌ ما لم تثبت همزة التسوية', DEFER['D1'][1]))
            cands.append(_finish(c))
        lead = f[k if not standalone else min(k + 1, n - 1)]
        b_start = k if not standalone else min(k + 1, n - 1)
        a_ok = [x for x in cands if x['A']]
        conts = {x['container'] for x in a_ok}
        in_cont = cont or (next(iter(conts)) if len(conts) == 1 else None)
        if letter == 'و' and a_ok:
            pr = lead.get('head') == 'pron' or is_form(lead['text'], tuple('وَ' + p for p in PRON_FREE_V))
            qad = lead.get('qad') and b_start + 1 < n and (f[b_start + 1]['verb'] == 'madi' or _madi_like(f[b_start + 1]['text']))
            a_v = any(f[p]['verb'] or p in X.nset or _madi_like(f[p]['text']) or _hollow_madi(f[p]['text']) or
                      f[p].get('vshape') and not f[p].get('noun') for p in a_ok[0]['A']['positions'])
            if (pr or qad) and a_v:
                c = _cand(f'C{len(cands) + 1}', 'حال (واو الحال)', 'جملة', None, B, letter, ['FN-HAL'])
                c['A'] = a_ok[0]['A']
                ref = _pron_ref(X, b_start, a_ok[0]['A']['positions']) if pr else None
                _check(c, 'A1', True, 'واو الحال: ' + ('جملةٌ اسمية مصدَّرة بضمير' if pr else '«قد» والماضي') +
                       ' بعد جملةٍ فعلية تامّة')
                _check(c, 'A2', True, 'صاحب الحال في الطرف السابق' + (f': «{ref}» يعود عليه الضمير' if ref else ''))
                _check(c, 'A3', True, 'الجملة الحالية تربطها الواو' + (' والضمير' if ref else ''))
                for a_ in ('A4', 'A5', 'A6', 'A7'):
                    _check(c, a_, True, '—')
                if ref:
                    c['evidence'].append(f'الضمير «{w[b_start]}» يوافق «{ref}» في الطرف السابق')
                    c['rank'] = 'الحال أرجح: الضمير يعود على اسمٍ في الجملة السابقة ويصف حاله'
                cands.append(_finish(c))
        if letter in ('و', 'ف'):
            c = _cand(f'C{len(cands) + 1}', 'استئناف', 'جملة', None, B, letter, ['FN-ISTI'])
            c['checks'] = {a_: (True, '—') for a_ in ('A2', 'A3', 'A4', 'A5', 'A6', 'A7')}
            c['checks']['A1'] = (True, f'{"رأس آية، و" if verse_initial else ""}ما بعد الحرف جملةٌ تامّة الأركان')
            if in_cont and cont_ev:
                c['barriers'].append(('R3', f'الاستئناف يقطع {in_cont} قبل اكتماله: {cont_ev}'))
            elif in_cont:
                c['deferrals'].append(('D3', f'{in_cont} مرشَّحٌ حاوياً بلا دليلٍ مستقلٍّ على بقائه مفتوحاً بعد الطرف',
                                       DEFER['D3'][1]))
            elif not a_ok:
                c['deferrals'].append(('D7', 'لا جملة سابقة معيَّنة يُستأنف بعدها', DEFER['D7'][1]))
            else:
                # غياب الحاوي المفتوح لا يثبت الاستئناف: لا قاعدة إيجابية له منفَّذة (FN-ISTI قرينة بحثٍ لا ترخيص)
                c['deferrals'].append(('D8', 'لا قاعدة إيجابية للاستئناف منفَّذة؛ وخلوّ الموضع من حاوٍ مفتوح لا يثبته',
                                       DEFER['D8'][1]))
            cands.append(_finish(c))
        if letter == 'ف' and f[bh]['verb'] == 'mudari' and f[bh].get('mood') == 'نصب' and a_ok:
            talab = any(f[p]['verb'] == 'amr' or f[p].get('neg') for p in a_ok[0]['A']['positions'])
            c = _cand(f'C{len(cands) + 1}', 'سببية (فاء السببية)', 'جملة', a_ok[0]['A'], B, letter, ['FN-SABAB'])
            c['checks'] = {a_: (True, '—') for a_ in ('A2', 'A3', 'A4', 'A5', 'A6', 'A7')}
            c['checks']['A1'] = (talab, 'مضارعٌ منصوب بعد طلبٍ أو نفي' if talab else 'لا طلب ولا نفي ظاهر قبله')
            cands.append(_finish(c))
            if talab:
                for x in cands:
                    if x['function'] == 'عطف':
                        x['barriers'].append(('R2', 'المضارع المنصوب بعد الطلب أو النفي لا يُعطف على جملة الطلب عطفَ جملة'))
                        _finish(x)
    rec = _decide(X, c_, cands, coverage, letter)
    return rec


def _lam_verb(g):
    """لام التعليل ملتصقةً بالمضارع في الجذع (وَلِنَجۡعَلَكَ): لامٌ مكسورة يليها حرف المضارعة"""
    stem = next((x[1] for x in (g.get('segs') or []) if x[0] == 'جذع'), '')
    st = letters(stem)
    return len(st) > 3 and st[0][0] == 'ل' and st[0][1] == {'\u0650'} and st[1][0] in 'أنيت' and \
        st[1][1] & {'\u064e', '\u064f'} and g['case'] in ('نصب', None)


def _pron_ref(X, b, a_pos):
    """ما يعود عليه ضمير الجملة الحالية في الطرف السابق: اسمٌ مفردٌ مؤنث (ة) لـ«هي»، أو جمعٌ لـ«هم»"""
    from .algebra import is_form
    t = X.wtext[b]
    for p in reversed(a_pos):
        fp = X.feats[p]
        if not fp.get('noun'):
            continue
        st = _strip(fp['text'])
        if is_form(t, ('وَهِيَ',)) and st.rstrip('اًٌٍ')[-1:] in 'ة':
            return X.wtext[p]
        if is_form(t, ('وَهُوَ',)) and st[-1:] not in 'ة':
            return X.wtext[p]
    return None


def _decide(X, c_, cands, coverage, letter):
    k = c_['pos']
    ok = [c for c in cands if c['status'] == 'مستوفٍ']
    dfr = [c for c in cands if c['status'] == 'مؤجَّل']
    rej = [c for c in cands if c['status'] == 'مرفوض']
    full = coverage.startswith('مكتملة')
    codes = []
    if len(ok) == 1 and not dfr and full:
        dec = DECISIONS[0]
        why = f'مرشّحٌ واحد مستوفٍ ({ok[0]["id"]}: {ok[0]["function"]})، وغيره مرفوضٌ بدليل، والتغطية مكتملة ضمن النطاق المعلن'
        if not ok[0]['function'].startswith('عطف'):
            why += '؛ فالحرف هنا ليس عاطفاً'
    elif len(ok) > 1:
        dec = DECISIONS[1]
        fn = {c['function'] for c in ok}
        lv = {c['level'] for c in ok}
        hd = {(c['A'] or {}).get('head_id') for c in ok if c['function'].startswith('عطف')}
        codes = (['D1'] if len(fn) > 1 else []) + (['D4'] if len(lv) > 1 else []) + (['D2'] if len(hd) > 1 else []) or ['D9']
        why = 'أكثر من مرشّحٍ مستوفٍ: ' + '، '.join(f'{c["id"]} ({c["function"]})' for c in ok)
    elif len(ok) == 1 and dfr:
        dec = DECISIONS[2]
        codes = sorted({d[0] for c in dfr for d in c['deferrals']})
        why = f'مرشّحٌ مستوفٍ ({ok[0]["id"]}) ومنافسٌ مؤجَّل: ' + '، '.join(f'{c["id"]} ({c["function"]})' for c in dfr)
    elif not ok and rej and not dfr and full:
        dec = DECISIONS[3]
        why = 'المرشّحات كلها مرفوضة بموانع مثبتة، والتغطية مكتملة ضمن النطاق المعلن'
    else:
        dec = DECISIONS[4]
        codes = sorted({d[0] for c in dfr for d in c['deferrals']}) or (['D7'] if not full else ['D8'])
        why = 'لا مرشّح مستوفٍ' + ('، والتغطية ناقصة' if not full else '') if not ok else coverage
    pref = None
    for c in ok + dfr:
        if c.get('rank'):
            pref = (c['id'], c['rank'])
            break
    if pref is None and dec != DECISIONS[0] and ok:
        silah = [c for c in ok if c['function'] == 'عطف' and c['container'] and c['container'].startswith('صلة')]
        outer = [c for c in ok if c['function'] == 'عطف' and not c['container']]
        if silah and outer and silah[0].get('tense') and outer[0].get('tense'):
            (sa, sb), (oa, ob) = silah[0]['tense'], outer[0]['tense']
            if sa == sb and oa != ob:
                pref = (silah[0]['id'], 'الصلة أرجح: فعل المعطوف يوافق فعل الصلة زمناً، ويخالف فعل الجملة الخارجية')
            elif oa == ob and sa != sb:
                pref = (outer[0]['id'], 'الجملة الخارجية أرجح: فعل المعطوف يوافق فعلها زمناً، ويخالف فعل الصلة')
        if pref is None and letter == 'ف':
            co = next((c for c in ok if c['function'] == 'عطف' and c.get('tense') and c['tense'][0] and
                       c['tense'][0] == c['tense'][1]), None)
            if co:
                pref = (co['id'], 'العطف أرجح: فعلان من زمنٍ واحد متعاقبان بالفاء')
    established, open_ = [], []
    if all(c['level'] == cands[0]['level'] for c in ok + dfr if c['function'].startswith('عطف')):
        established.append(f'المستوى: {cands[0]["level"]}')
    bs = {tuple(c['B']['positions']) for c in ok if c['B']}
    if len(bs) == 1 and ok:
        established.append(f'الطرف اللاحق: «{ok[0]["B"]["text"]}» برأسه «{ok[0]["B"]["head"]}»')
    for c in ok:
        for s in c['shared']:
            if s['status'] == 'نطاق مؤجَّل':
                open_.append(f'{s["element"]}: {s["evidence"]}')
    needed = sorted({DEFER[d][1] for d in codes if d in DEFER})
    f0 = X.feats[k]
    seg = f'{X.wid(k)}:1' if f0['conj'] and len(f0.get('segs') or ()) > 1 else f'{X.wid(k)}:1'
    omega = [f'{d[0]}: {d[1]} ← يلزم: {d[2]}' for c in dfr for d in c['deferrals']]
    omega += [f'D5: {x}' for x in open_]
    ch = next((c for c in ok if c['function'].startswith('عطف')), None)
    closure = dict(
        Complete_A=bool(ch and ch['A'] and ch['ExtentCertified']), Complete_B=bool(ch and ch['ExtentCertified']),
        Complete_C=bool(ch and dec == DECISIONS[0]),
        Close_P='لا يُحكم به من العطف: اكتمال العلاقة لا يُغلق التركيب الحاوي' if X.container(k) else 'لا تركيب حاوياً')
    return dict(
        text_id=dict(source=SOURCE, reading=X.q, verse=f'{X.words[k][0]}:{X.words[k][1]}'),
        letter=letter, letter_unit=seg, carrier_word=X.wid(k), carrier_pos=k, carrier_text=X.wtext[k],
        container=X.container(k), coverage=coverage, candidates=cands, decision=dec, decision_codes=codes,
        reason=why, preferred=pref, established=established, open=open_, needed=needed,
        UniqueWithin=dec == DECISIONS[0], omega=omega, closure=closure, gamma=GAMMA,
        letter_cells=X.letter_cells(k, letter),
        generation=dict(functions=sorted({c['function'] for c in cands}),
                        scope='الجملة الجارية للمفرد وشبه الجملة (إلى ١٢ كلمة، ويقف عند فعلٍ أو ما له الصدارة أو رأس آية)، '
                              'ورأس الجملة السابقة رجوعاً للجمل (إلى ١٥ كلمة)',
                        stop='لغوي' if full else 'تقني: النص المقروء لا يبدأ من أول السورة',
                        complete_by_rules=full, arabic_coverage='غير مثبت: اكتمال التوليد وفق Γ لا يثبت اكتمال الأوجه العربية',
                        uncovered=['عطف البيان والبدل والنعت (علاقاتٌ أخرى)', 'العطف على الضمير المتصل المجرور',
                                   'واو المعية', '«لا» و«بل» و«لكن» و«حتى» العاطفة للمفرد', 'الحذف المقدَّر']),
        sources=dict(text=SOURCE, reading=X.q, reference_tags='لم تُستعمل مدخلاً؛ QAC للقياس وحده'))


def extra_sites(X, done):
    """مواضع لا تبلغها coord_structs: الحرف أول النص (القسم والاستئناف)، وفاء الجواب، وبل ولكن وحتى"""
    from .algebra import is_form, clause_word
    f, w = X.feats, X.wtext
    n = len(f)
    out = []
    for k in range(n):
        if k in done:
            continue
        fk = f[k]
        cands = []
        letter = fk['conj_letter'] if fk['conj'] else None
        verse_initial = k == 0 or X.ay_end[k - 1]
        if fk['conj'] and letter == 'و' and verse_initial and fk.get('noun') and fk['case'] in ('جر', 'جر أو نصب'):
            first = k == 0 and X.surah_start or k > 0 and is_form(w[k - 1], ('كَلَّا',))
            c = _cand('C1', 'قسم (واو القسم)', 'مفرد', None, _member(X, [k], k, 'مقسمٌ به', ['الرأس']), 'و', ['FN-QASAM'])
            _check(c, 'A1', first, 'اسمٌ مجرور بعد الواو في أول السورة لا عامل جرٍّ قبله: الواو جارّةٌ للقسم'
                   if first else 'اسمٌ مجرور بعد الواو في أول الآية')
            for a_ in ('A2', 'A3', 'A4', 'A5', 'A6', 'A7'):
                _check(c, a_, True, '—')
            if not first:
                c['deferrals'].append(('D7', 'لا يُعرف من النص المقروء ما قبل الآية', DEFER['D7'][1]))
            cands.append(_finish(c))
            c = _cand('C2', 'عطف', 'مفرد', None, cands[0]['B'], 'و', ['FN-QASAM', 'CO-SINGLE'])
            c['checks'] = {'A1': (True, '')}
            if first:
                c['barriers'].append(('R2', 'لا معطوفَ عليه قبله في السورة: العطف يقتضي طرفاً سابقاً'))
            else:
                c['deferrals'].append(('D7', 'الطرف السابق خارج النص المقروء', DEFER['D7'][1]))
            cands.append(_finish(c))
            cov = 'مكتملة ضمن نطاق البحث المعلن (السورة من أولها)' if first else 'ناقصة: ما قبل الموضع خارج النص المقروء'
        elif fk['conj'] and k == 0:
            b0 = k + 1 if letter in ('أو', 'ثم', 'أم') and n > 1 else k
            c = _cand('C1', 'عطف', 'جملة', None, _member(X, list(range(k, X.b_stop(b0))), k, 'جملة', ['إلى حدّه المشتقّ']),
                      letter, ['CO-CLAUSE'])
            c['checks'] = {'A1': (True, '')}
            c['deferrals'].append(('D7', 'الحرف أول النص المقروء: الطرف السابق خارجه', DEFER['D7'][1]))
            cands.append(_finish(c))
            c = _cand('C2', 'استئناف', 'جملة', None, cands[0]['B'], letter, ['FN-ISTI'])
            c['checks'] = {'A1': (True, '')}
            c['deferrals'].append(('D7', 'لا يُحكم بالاستئناف بلا ما قبله', DEFER['D7'][1]))
            cands.append(_finish(c))
            cov = 'ناقصة: الحرف أول النص المقروء'
        elif fk['conj'] and k in X.not_conj_why:
            r = X.not_conj_why[k]
            c = _cand('C1', f'رابطة لجواب الشرط «{r["tool"]}»', 'جملة', None,
                      _member(X, list(range(k, X.b_stop(k))), k, 'جواب', ['إلى حدّه المشتقّ']), 'ف', ['FN-JAWAB'])
            for a_ in ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7'):
                _check(c, a_, True, '—')
            if r['amb'] or r['s_deferred']:
                c['deferrals'].append(('D1', 'الأداة محتملة الشرطية أو فعل الشرط لم يثبت', DEFER['D1'][1]))
            cands.append(_finish(c))
            c = _cand('C2', 'عطف', 'جملة', None, cands[0]['B'], 'ف', ['FN-JAWAB'])
            c['checks'] = {'A1': (True, '')}
            if r['amb'] or r['s_deferred']:
                c['deferrals'].append(('D1', 'العطف جائزٌ إن لم تثبت الشرطية', DEFER['D1'][1]))
            else:
                c['barriers'].append(('R1', f'الفاء رابطةٌ لجواب «{r["tool"]}» ({X.wid(r["head"])}) في هذا الوجه'))
            cands.append(_finish(c))
            cov = 'مكتملة ضمن نطاق البحث المعلن'
            letter = 'ف'
        elif is_form(fk['text'], ('بَلْ', 'وَلَٰكِنْ', 'وَلَكِنْ', 'لَٰكِنْ', 'لَكِنْ', 'حَتَّىٰ', 'حَتَّى')) and k + 1 < n:
            t = _strip(fk['text'])
            letter = 'بل' if t == 'بل' else 'حتى' if t.startswith('حت') else 'لكن'
            nx = f[k + 1]
            clause = clause_word(f, k + 1, X.nset) or nx['verb'] or k + 1 in X.nset
            B = _member(X, list(range(k + 1, X.b_stop(k + 1))) if clause else extent_single(X, k + 1, n)[0], k + 1,
                        'جملة' if clause else 'مفرد', ['إلى حدّه المشتقّ' if clause else 'الرأس'])
            fn = {'بل': 'حرف ابتداءٍ وإضراب', 'لكن': 'حرف ابتداءٍ واستدراك', 'حتى': 'حرف ابتداءٍ أو جرٍّ أو نصب'}[letter]
            c = _cand('C1', fn, B['type'], None, B, letter, ['FN-BAL'])
            c['checks'] = {'A1': (True, '')}
            c2 = _cand('C2', 'عطف', B['type'], None, B, letter, ['FN-BAL'])
            c2['checks'] = {'A1': (True, '')}
            if letter == 'لكن' and t.startswith('و'):
                c2['barriers'].append(('R2', '«لكن» المسبوقة بالواو حرف استدراك، والعاطف الواو'))
                c['checks'].update({a_: (True, '—') for a_ in ('A2', 'A3', 'A4', 'A5', 'A6', 'A7')})
            elif clause:
                c2['barriers'].append(('R2', f'«{fk["text"]}» لا تعطف إلا مفرداً، وما بعدها جملة'))
                c['checks'].update({a_: (True, '—') for a_ in ('A2', 'A3', 'A4', 'A5', 'A6', 'A7')})
            else:
                c2['deferrals'].append(('D8', f'شروط «{letter}» العاطفة للمفرد غير منفَّذة', DEFER['D8'][1]))
                c['deferrals'].append(('D8', 'وظيفة الحرف مع المفرد غير منفَّذة', DEFER['D8'][1]))
            cands += [_finish(c), _finish(c2)]
            cov = 'مكتملة ضمن نطاق البحث المعلن'
        else:
            continue
        rec = _decide(X, dict(pos=k), cands, cov, letter)
        out.append(rec)
    return out


def nest(records, X):
    """التداخل والسلاسل: موضعٌ داخل طرفٍ لعطفٍ أكبر، وعدة أطرافٍ على مستوى واحد تجمعها مجموعة العطف"""
    def chosen(r):
        ok = [c for c in r['candidates'] if c['status'] == 'مستوفٍ' and c['function'].startswith('عطف') and c['A']]
        if r['preferred']:
            p = next((c for c in ok if c['id'] == r['preferred'][0]), None)
            if p:
                return p
        return ok[0] if ok else None
    ch = [(r, chosen(r)) for r in records]
    by_a = {}
    for r, c in ch:
        if c:
            by_a.setdefault((c['A']['head_pos'], c['level']), []).append((r, c))
    for (ap, lv), grp in by_a.items():
        if len(grp) > 1:
            members = [grp[0][1]['A']['head_id']] + [c['B']['head_id'] for _, c in grp]
            for i, (r, c) in enumerate(grp):
                r['chain'] = dict(kind='سلسلة على مستوى واحد', group=members, local_previous=members[i],
                                  first=members[0], note='المعطوفات كلها على الأول، والسابق المباشر يُحفظ رابطاً محلياً')
    for r, c in ch:
        k = r['carrier_pos']
        for r2, c2 in ch:
            if r2 is r or not c2:
                continue
            for side, m in (('السابق', c2['A']), ('اللاحق', c2['B'])):
                if m and k in m['positions'] and k != m['positions'][0]:
                    r['inside'] = dict(of=r2['letter_unit'], side=side, level=c2['level'],
                                       note=('عطفٌ داخل طرف' + (' مع انتقال المستوى' if c and c['level'] != c2['level']
                                                                else '')))
    return records


# ---------- فاحص شهادة العطف (البند ١٥): يعيد اشتقاق كل ما يدّعيه السجل من النص، لا من حقوله وحدها ----------
def check_coord(rec, X):
    """→ قائمة المشكلات ([] للسجل السليم). يُفحص: هوية الحرف وخلاياه، وهوية كل طرفٍ ورأسه وعضويته ومقابلتها
    بالنص، وانفصال الطرفين وموقعهما من الحرف، وبقاء العناصر المشتركة خارجهما، ووجود القواعد في السجل،
    واتساق حالة كل مرشّح مع شروطه وموانعه، واتساق قرار الموضع مع حالات مرشّحاته"""
    from .algebra import CASE_COMPAT
    P = []
    k = rec['carrier_pos']
    f = X.feats
    if not (0 <= k < len(f)) or rec['carrier_word'] != X.wid(k) or rec['carrier_text'] != X.wtext[k]:
        return ['R7: الكلمة الحاملة لا تطابق موضعها في النص']
    if not rec['letter_unit'].startswith(X.wid(k) + ':'):
        P.append('R7: وحدة الحرف ليست من كلمته الحاملة')
    for c in rec['letter_cells']:
        if not c['id'].startswith(f'Q{X.words[k][0]}:{X.words[k][1]}.w{X.words[k][2]}.'):
            P.append(f'R7: خلية الحرف {c["id"]} ليست من كلمته')
    seen = set()
    for c in rec['candidates']:
        if c['id'] in seen:
            P.append(f'{c["id"]}: معرّفٌ مكرَّر')
        seen.add(c['id'])
        for r in c['rules']:
            if r not in RULES:
                P.append(f'{c["id"]}: قاعدةٌ غير مسجَّلة {r}')
        for side, m in (('A', c['A']), ('B', c['B'])):
            if not m:
                continue
            pos = m['positions']
            if m['head_pos'] not in pos:
                P.append(f'{c["id"]}.{side}: الرأس خارج عضوية الطرف')
            if m['head'] not in (X.wtext[m['head_pos']], _units_text(X, [u for u in m['units'] if u.startswith(
                    X.wid(m['head_pos']) + ':')])) or m['head_id'] != X.wid(m['head_pos']):
                P.append(f'{c["id"]}.{side}: الرأس لا يطابق النص في موضعه')
            if m['words'] != [X.wid(p) for p in pos] or m.get('envelope_text') != ' '.join(X.wtext[p] for p in pos) or \
                    m['text'] != _units_text(X, m['units']):
                P.append(f'{c["id"]}.{side}: العضوية لا تطابق النص')
            if any(not any(u.startswith(wd + ':') for wd in m['words']) for u in m['units']):
                P.append(f'{c["id"]}.{side}: وحدةٌ صرفية من غير كلمات الطرف')
            if m['envelope'] != [X.wid(pos[0]), X.wid(pos[-1])]:
                P.append(f'{c["id"]}.{side}: الغلاف النصي لا يطابق العضوية')
        A, B = c['A'], c['B']
        # المضمون لا الحقول: يُعاد اشتقاق الامتداد من النص بالقواعد نفسها، ويُفحص الرأس بنوعه
        for side, m, lim in (('A', A, k), ('B', B, len(f))):
            if not m or c['status'] == 'مرفوض':
                continue
            if c['level'] in ('مفرد', 'شبه جملة') and m['type'] in ('مفرد', 'شبه جملة'):
                exp, _ = extent_single(X, m['head_pos'], lim)
                if m['positions'] != exp:
                    P.append(f'{c["id"]}.{side}: العضوية لا يشتقّها النص بقواعد الامتداد')
                if m['head_pos'] != m['positions'][0]:
                    P.append(f'{c["id"]}.{side}: رأس المفرد ليس أول عضويته')
            elif c['level'] == 'جملة':
                if m['positions'] != list(range(m['positions'][0], m['positions'][-1] + 1)):
                    P.append(f'{c["id"]}.{side}: عضوية الجملة غير متصلة')
                b0 = m['positions'][0] + (1 if rec['letter'] in ('أو', 'ثم', 'أم') else 0)
                if side == 'B' and getattr(X, 'b_stop', None) and m['positions'][-1] + 1 != X.b_stop(b0) and \
                        c['function'] not in ('استئناف',) and not c['function'].startswith('رابطة'):
                    P.append(f'{c["id"]}.B: حدّ الطرف اللاحق لا يطابق حدّه المشتقّ')
                far = m['type'] == 'جملة سابقة أبعد'
                if side == 'A' and not far and m['positions'][-1] != k - 1:
                    P.append(f'{c["id"]}.A: الطرف السابق الجملي لا ينتهي قبل الحرف')
                hd = getattr(X, 'clause_head', None)
                if side == 'A' and far:
                    if not (hd and hd(m['head_pos'])) or m['head_pos'] != m['positions'][0] or m['positions'][-1] >= k:
                        P.append(f'{c["id"]}.A: الرأس الأبعد ليس رأس جملةٍ قبل الحرف')
                elif side == 'A' and hd and m['type'].startswith('صلة'):
                    if m['positions'][0] - 1 not in X.rel_at:
                        P.append(f'{c["id"]}.A: الصلة لا تبدأ بعد موصول')
                elif side == 'A' and hd and c['function'].startswith('عطف'):
                    exp = next((j for j in range(k - 1, max(-1, k - 15), -1) if hd(j)), None)
                    if m['head_pos'] != exp:
                        P.append(f'{c["id"]}.A: رأس الجملة السابقة ليس أول رأسٍ رجوعاً من الحرف')
                    pre = m['head_pos'] - m['positions'][0]
                    if pre < 0 or any(not (X.feats[p].get('neg') or X.feats[p].get('qad'))
                                      for p in range(m['positions'][0], m['head_pos'])):
                        P.append(f'{c["id"]}.A: ما قبل الرأس في الطرف ليس نفياً ولا «قد»')
        if c['function'].startswith('عطف') and A and B:
            if max(A['positions']) >= k:
                P.append(f'{c["id"]}: الطرف السابق يتجاوز الحرف')
            if min(B['positions']) < k:
                P.append(f'{c["id"]}: الطرف اللاحق يبدأ قبل الحرف')
            if set(A['positions']) & set(B['positions']):
                P.append(f'{c["id"]}: الطرفان متداخلان')
            a4 = c['checks'].get('A4', (None, ''))
            fa_, fb_ = f[A['head_pos']], f[B['head_pos']]
            if c['level'] == 'مفرد' and c['status'] != 'مرفوض':
                from .algebra import PRON_FREE_V, is_form
                def nom(g):
                    return g.get('noun') or g.get('rel') or g.get('an') or g.get('maqsur') or is_form(g['text'], PRON_FREE_V)
                enc_ = any('الضمير' in e for e in A.get('extent_evidence', []))   # ضمير نصبٍ متصلٌ بفعله (ذَرۡنِي)
                if not (nom(fa_) or enc_ or _ma_silah(X, A['head_pos'], k)) and not any(d[0] == 'D8' for d in c['deferrals']):
                    P.append(f'{c["id"]}.A: الرأس السابق بلا دليل اسمية ولا تأجيلٍ لها')
                if a4[0] and a4[1].startswith('الحالة لا تظهر'):
                    hid = lambda g: g.get('maqsur') or g.get('rel') or g.get('an') or not g['case'] or \
                        is_form(g['text'], PRON_FREE_V)
                    if not (hid(fa_) or hid(fb_) or _ma_silah(X, A['head_pos'], k) or _ma_silah(X, B['head_pos'], len(f))):
                        P.append(f'{c["id"]}: دعوى خفاء الحالة لا تطابق الطرفين')
            # نطاق البحث المعلن: لا يُعبر ما له الصدارة (سوى الكلمة قبل الحرف) إلا لمعطوفٍ لا تظهر حالته
            any_b = fb_.get('maqsur') or fb_.get('rel') or fb_.get('an')
            if c['level'] == 'مفرد' and A['head_pos'] < k and any(X.starts[j] for j in range(A['head_pos'] + 1, k - 1)) and \
                    not any_b:
                P.append(f'{c["id"]}.A: بين الرأس السابق والحرف ما له الصدارة (خارج نطاق البحث المعلن)')
            if a4[0] and a4[1].startswith('توافق الحالة'):
                fa, fb = f[A['head_pos']]['case'], f[B['head_pos']]['case']
                if not (fb in CASE_COMPAT and fa in CASE_COMPAT[fb]):
                    P.append(f'{c["id"]}: دعوى توافق الحالة لا تطابق الحالتين ({fa} / {fb})')
            for s in c['shared']:
                if s['status'] == 'اشتراك مثبت' and s['element'] and any(w_ in s['element'] for w_ in
                                                                         [f'({wd})' for wd in A['words'] + B['words']]):
                    P.append(f'{c["id"]}: عنصرٌ مشترك منسوخٌ داخل أحد الطرفين')
        want = 'مرفوض' if c['barriers'] else 'مؤجَّل' if c['deferrals'] else \
            'مستوفٍ' if all(v[0] for v in c['checks'].values()) else 'مؤجَّل'
        if c['status'] != want:
            P.append(f'{c["id"]}: الحالة «{c["status"]}» لا تطابق الشروط والموانع («{want}»)')
        for b in c['barriers']:
            if b[0] not in REJECT:
                P.append(f'{c["id"]}: مانعٌ غير معرَّف {b[0]}')
        for d in c['deferrals']:
            if d[0] not in DEFER:
                P.append(f'{c["id"]}: سبب تأجيلٍ غير معرَّف {d[0]}')
    ok = [c for c in rec['candidates'] if c['status'] == 'مستوفٍ']
    dfr = [c for c in rec['candidates'] if c['status'] == 'مؤجَّل']
    full = rec['generation']['complete_by_rules']
    want = DECISIONS[0] if len(ok) == 1 and not dfr and full else DECISIONS[1] if len(ok) > 1 else \
        DECISIONS[2] if len(ok) == 1 and dfr else \
        DECISIONS[3] if not ok and not dfr and rec['candidates'] and full else DECISIONS[4]
    if rec['decision'] != want:
        P.append(f'القرار «{rec["decision"]}» لا يطابق حالات المرشّحات («{want}»)')
    if rec['UniqueWithin'] != (rec['decision'] == DECISIONS[0]):
        P.append('UniqueWithin لا يطابق القرار')
    # إعادة التوليد (مراجعة التقرير السادسة ٨): الشهادة تخصّ البنية التي يولّدها النص بالقواعد نفسها؛ فإحلال مرشّحٍ
    # آخر جائزٍ محلّ الرأس، وإن اتّسقت حقوله، لا يطابق ما يُعاد توليده
    src = getattr(X, 'src', {}).get(rec['letter_unit'])
    if src is not None and not P:
        fresh = site_record(src, X)
        sig = lambda r_: [(c['id'], c['function'], c['status'], (c['A'] or {}).get('head_pos'),
                           tuple((c['A'] or {}).get('positions', ())), tuple((c['B'] or {}).get('positions', ())))
                          for c in r_['candidates']] + [r_['decision']]
        if sig(fresh) != sig(rec):
            P.append('الشهادة لا تطابق إعادة توليد المرشّحات من النص: البنية المسجَّلة غير ما تُرخّصه القواعد في الموضع')
    return P


def mutations(rec, X):
    """اختبارات مضادة: تغيير الرأس أو العضوية أو الحدّ أو الرابط أو الدليل مع إبقاء بقية السجل → [(الاسم، السجل المغيَّر)]"""
    import copy
    out = []
    c0 = next((c for c in rec['candidates'] if c['A'] and c['B'] and c['function'].startswith('عطف')), None)
    if c0 is None:
        return out
    i = rec['candidates'].index(c0)
    n = len(X.feats)

    def mut(name, fn):
        r = copy.deepcopy(rec)
        fn(r, r['candidates'][i])
        out.append((name, r))

    def remember(m, pos=None, head=None):
        # تغييرٌ متّسق: تُحدَّث الحقول المشتقّة كلها، فلا يُكشف إلا بفحص المضمون
        pos = sorted(set(pos if pos is not None else m['positions']))
        head = m['head_pos'] if head is None else head
        units = [u for p in pos for u in X.segs(p, skip_conj=(p == pos[0]))]
        m.update(positions=pos, head_pos=head, head=X.wtext[head], head_id=X.wid(head),
                 words=[X.wid(p) for p in pos], text=_units_text(X, units),
                 envelope_text=' '.join(X.wtext[p] for p in pos), envelope=[X.wid(pos[0]), X.wid(pos[-1])],
                 units=units)
    a0 = c0['A']['positions']
    alt = next((p for p in range(min(a0) - 1, -1, -1) if p not in a0), None)
    if alt is not None:
        mut('تغيير رأس السابق (متّسق)', lambda r, c: remember(c['A'], [alt] + [p for p in a0 if p > alt] if
                                                             c['level'] == 'جملة' else [alt], alt))
    mut('ضمّ كلمةٍ قبل السابق (متّسق)', lambda r, c: remember(c['A'], [min(a0) - 1] + a0) if min(a0) > 0 else
        remember(c['A'], a0[:-1] or a0))
    if c0['B']['positions'][-1] + 1 < n:
        mut('مدّ حدّ اللاحق كلمة (متّسق)', lambda r, c: remember(c['B'], c['B']['positions'] +
                                                                [c['B']['positions'][-1] + 1]))
    mut('ضمّ الحرف إلى السابق', lambda r, c: c['A'].update(positions=c['A']['positions'] + [r['carrier_pos']]))
    mut('نقل الرابط إلى كلمةٍ أخرى', lambda r, c: r.update(letter_unit=X.wid(max(0, r['carrier_pos'] - 1)) + ':1'))
    mut('قاعدةٌ غير مسجَّلة', lambda r, c: c['rules'].append('CO-FAKE'))
    mut('قلب حالة المرشّح', lambda r, c: c.update(status='مرفوض' if c['status'] != 'مرفوض' else 'مستوفٍ'))
    mut('قرارٌ لا يطابق المرشّحات', lambda r, c: r.update(
        decision=DECISIONS[3] if r['decision'] != DECISIONS[3] else DECISIONS[0]))
    mut('حذف المانع مع إبقاء الرفض', lambda r, c: [x.update(barriers=[]) for x in r['candidates']
                                                   if x['status'] == 'مرفوض'] or c.update(status='مرفوض'))
    return out
