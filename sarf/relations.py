# -*- coding: utf-8 -*-
"""
sarf.relations — عقد النواة الاسمية والتعلّق، الإصدار المقترح ١ (3 نوفمبر 2026): سجلات علاقاتٍ قابلة للتحقق
فوق طبقة الآية، لا تغيّر شيئاً مما قبلها (تُقرأ منها: analyze، والوحدات الجبرية، والسمات).

القواعد (كلٌّ بمعرّفه وإصداره، وسجلّ مقدّماته وموانعه المفحوصة وبدائله):
  P01 v1  بناء الجار والمجرور: حرف جرٍّ مقبول الحكم ومعموله ← PP وحافة GOVERN. لا يثبت متعلَّقه.
  P02 v1  الظرف: ظرفٌ من جرد المشروع (sarf.algebra.ZURUF_V) يليه مضافٌ إليه (ضميرٌ متصل أو اسمٌ مجرور) ← ADVP
  V01 v1  وصلة الناسخ: كان وأخواتها (مج 10) وإنّ وأخواتها (مج 2) المقبولة: اسمها معمولها المربوط، وخبرها
          بشرطه (المنصوب كتابةً لكان، والمرفوع كتابةً لإنّ، أو شبه جملةٍ مقدَّمة قبل الاسم النكرة)
  R01 v1  إطار الصلة المحدود: موصولٌ مختصّ (الذي وأخواته) تليه شبه جملة ثم اسمٌ مرفوع ← حاويةٌ وفيها نواة N02؛
          والعائد علاقةٌ مستقلة بالمطابقة
  N01 v1  إسنادٌ اسمي بخبرٍ مفرد: مسندٌ إليه معرفةٌ مرفوع (أو مبنيٌّ في محلّ رفع) في أول الكلام، ومسندٌ اسمٌ نكرةٌ مرفوع
  N02 v1  إسنادٌ بشبه جملة: معرفةٌ مرفوعة ثم شبه جملة في آخر الإطار، أو شبه جملة ثم نكرةٌ مرفوعة في آخره
  A01 v1  توليد مرشّحات التعلّق: كل مضيفٍ ممكن في الإطار (فعل، أو وصف، أو مصدر)، ويُفحص إطار تعلّقه؛
          ولا جرد لأطر التعلّق في المشروع بعد، فالبحث SEARCH_INCOMPLETE ولا يُرخَّص تعلّق

الحالات: LICENSED (علاقة محلية جائزة بمقدّماتٍ مثبتة)، REJECTED (مانعٌ مثبت)، DEFERRED (نقص دليل)، CONFLICT (تعارضٌ مثبت).
وحقولٌ مستقلة: selected_analysis، nucleus_complete، clause_complete، boundary_proven، sentence_closed:
قبول العلاقة لا يرفعها إلى اختيارٍ نهائي ولا إلى إغلاق الجملة. والحماية الدستورية لا تعطّل الموقع النحوي.
"""
from .chars import letters, FATHA, DAMMA, KASRA, SUKUN, FATHATAN, DAMMATAN, KASRATAN, SHADDA

VERSION = 'v1'
LICENSED, REJECTED, DEFERRED, CONFLICT = 'LICENSED', 'REJECTED', 'DEFERRED', 'CONFLICT'
SEARCH_INCOMPLETE, SEARCH_COMPLETE = 'SEARCH_INCOMPLETE', 'SEARCH_COMPLETE'
NASIKH_KANA, NASIKH_INNA, JARR = '10', '2', '1'
REL_SPECIFIC = ('الَّذِي', 'الَّتِي', 'الَّذِينَ', 'اللَّذَانِ', 'اللَّتَانِ', 'اللَّذَيْنِ', 'اللَّتَيْنِ', 'اللَّاتِي', 'اللَّائِي', 'اللَّٰتِي')
REL_AGR = {'الَّذِي': (3, 'singular', 'masc'), 'الَّتِي': (3, 'singular', 'fem'), 'الَّذِينَ': (3, 'plural', 'masc')}


def _fv(F, k, key):
    r = (F.get(k) or {}).get(key) or {}
    return r.get('v'), r.get('st')


class _Tok:
    """وحدةٌ تحليلية بهويتها وما يلزم القواعد منها، من الطبقات القائمة (لا يُحسب هنا شيءٌ جديد عنها)"""
    def __init__(self, a, G, k, F, seg, ref):
        from .algebra import word_case
        self.k, self.G, self.wi, self.ui = k, G, k[0], k[1]
        self.uid = G.id
        self.loc = f'{ref}:{k[0] + 1}'
        self.text = G.O.get('text') or ''
        u = seg['units'][k[1]]
        self.slots = [seg['slots'][i] for i in u.get('slots', [])]
        self.types = [s['type'] for s in self.slots]
        self.lex = G.Theta.get('lex')
        self.pos, self.pos_st = _fv(F, k, 'pos')
        self.defin, self.defin_st = _fv(F, k, 'definiteness')
        self.dkind, _ = _fv(F, k, 'definiteness_kind')
        self.enclitic = bool(self.slots) and all(s['type'] == 'مبني' and s.get('role') == 'enclitic' for s in self.slots)
        # العاطف أو الرابط في أول الكلمة (وَ، فَ) وحده أو مدموجاً بأداةٍ بعده في وحدةٍ واحدة (وَلْ، فَلْ)
        self.conj = k[1] == 0 and len(seg['units']) > 1 and (self.text in ('وَ', 'فَ') or
                                                             self.text[:2] in ('وَ', 'فَ') and self.lex == 'مبني+عامل')
        stem_last = k[1] == max(i for i, x in enumerate(seg['units']) if any(seg['slots'][j]['type'] in ('جذع', 'لفظ الجلالة')
                                                                             for j in x.get('slots', []))) \
            if any(s['type'] in ('جذع', 'لفظ الجلالة') for s in seg['slots']) else False
        self.case = word_case(a, k[0]) if stem_last and any(t in ('جذع', 'لفظ الجلالة') for t in self.types) else None
        self.divine = 'لفظ الجلالة' in self.types
        tl = letters(self.text)
        self.tanwin = bool(tl) and bool(tl[-1][1] & {FATHATAN, DAMMATAN, KASRATAN})
        self.feats = F.get(k) or {}
        self.case_written = self.case
        self.roles = []                                 # مصادر العمل فيه: عاملٌ مقبول، أو دورٌ في علاقةٍ مرخَّصة
        self.adverb = None

        prot = G.Theta.get('protected') or {}
        self.golden = prot.get('cls') == 'اسم ذهبي'
        self.mcat = _mabni_cat(self.text, prot.get('identity')) if self.lex == 'مبني' or prot.get('cls') == 'مبني' else None

        pe = str((self.feats.get('pos') or {}).get('ev') or '')
        # شكل التنوين وحده ليس شهادة اسمية في هذه الطبقة (العقد T19)؛ وسمة الصنف القائمة في sarf.features لا تُغيَّر
        self.shape_only = self.pos == 'اسم' and pe.strip() == 'التنوين'
        self.noun_ev = pe or None
        self._elative = None
        if self.case is None and self.pos == 'اسم' and stem_last:
            nm, cs, _ = _written_mark(self)
            if nm in ('الألف', 'الواو') and cs == frozenset({'رفع'}):
                self.case = 'رفع'                       # المثنى والجمع بالحرف (العدد مثبت): الطبقة نفسها التي يقرأ بها المحور (F22)
            elif nm == 'الياء':
                self.case = 'جر أو نصب'
        if self.pos == 'فعل' and not self.elative_proof():
            self.case = None                            # قارئ الحالة المكتوبة للاسم وحده: الفعل لا يُجرّ (F04)؛ وأَفْعَل بـE01 اسم

    def nounish(self):
        """اسمٌ بدليلٍ غير شكل التنوين وحده: السمة المثبتة بدليلٍ آخر، أو لفظ الجلالة، أو اسمٌ ذهبي، أو أَفْعَل المثبت بنفي البدائل (E01)"""
        return self.pos == 'اسم' and self.pos_st == 'مثبت' and not self.shape_only or self.divine or self.golden or \
            bool(self.elative_proof())

    def elative_proof(self):
        """E01 v1 (مقترحة): «أَفْعَلُ» مختومٌ بضمة أو كسرة بلا تنوين ولا «أل» اسمٌ بنفي البدائل الثلاثة في مجالٍ معلن:
        الماضي (الآخر غير مفتوح)، ومضارع المتكلم من أَفْعَلَ (الهمزة مفتوحة لا مضمومة)، ومضارع المتكلم من الثلاثي:
        فَعَلَ لا يكون مضارعه يَفْعَلُ إلا وعينه أو لامه حرف حلق (سيبويه)، وفَعُلَ يُضمّ مضارعه، والأجوف لا يُكتب هكذا؛
        والماضي من HFN. → نصّ الدليل أو None"""
        if self._elative is not None:
            return self._elative or None
        self._elative = ''
        t = letters(self.text)
        from .chars import DAGGER_ALIF
        if len(t) != 4 or t[0][0] != 'أ' or FATHA not in t[0][1] or SUKUN not in t[1][1] or FATHA not in t[2][1] or \
                DAGGER_ALIF in t[2][1]:
            return None                                 # والخنجرية بعد العين مدٌّ: أَفۡعَال (أَيۡمَٰن)، لا أَفۡعَل
        last = t[3][1]
        if last & {FATHATAN, DAMMATAN, KASRATAN} or not last & {DAMMA, KASRA}:
            return None
        R = ''.join('ء' if c in 'أإؤئ' else c for c in (t[1][0], t[2][0], t[3][0]))
        from .root import hfn
        H = hfn()
        if H is None or R not in H.roots:
            return None
        pasts = [e['verb'] for e in H.index.get((R, 'I'), [])]
        if R[1] in 'وي':
            why = 'الأجوف لا يأتي مضارعه على أَفْعَلُ بعينٍ مفتوحة بعد ساكن'
        else:
            vs = set()
            for pv in pasts:
                pt = letters(pv)
                if len(pt) >= 2:
                    vs |= {x for x in (FATHA, DAMMA, KASRA) if x in pt[1][1]}
            if not vs or KASRA in vs or (FATHA in vs and set(R[1:]) & set('ءهعحغخ')):
                return None                             # فَعِلَ يَفْعَلُ، أو حرف حلق، أو لا ماضٍ في HFN: مضارع المتكلم باقٍ
            why = 'ماضيه في HFN «' + '، '.join(pasts) + '» فَعَلَ أو فَعُلَ، ولا حرف حلق في عينه ولامه: فلا يكون مضارعه أَفْعَلُ'
        self._elative = f'E01 (مقترحة): «{self.text}» آخره غير مفتوح فلا يكون ماضياً، وهمزته مفتوحة فلا يكون مضارع أَفْعَلَ، و{why}'
        return self._elative

    def axes(self, nxt=None):
        """محاور مستقلة لا يُغني أحدها عن الآخر: صنف الكلمة، والبناء والإعراب، والحماية، والعمل؛ كلٌّ بدليله أو «غير محسوم»"""
        wc = ('اسم', self.noun_ev or 'لفظ الجلالة' if self.divine else 'اسمٌ ذهبي' if self.golden else self.elative_proof()) \
            if self.nounish() else \
            ('اسم', f'ملف المبنيات: {self.mcat}') if self.mcat in ('separate_pronoun', 'demonstrative', 'relative', 'attached_pronoun') else \
            ('فعل', (self.feats.get('pos') or {}).get('ev')) if self.pos == 'فعل' and self.pos_st == 'مثبت' else \
            ('حرف', f'ملف المبنيات: {self.mcat}') if self.mcat == 'particle' else \
            (None, 'الاسمية من شكل التنوين وحده: غير محسوم في هذه الطبقة (العقد T19)؛ وسمة المرحلة ١٣ «اسم» بدليل التنوين '
                   'قديمةٌ (LEGACY) لم تُغيَّر، وهذا المحور يصحّحها إلى التأجيل' if self.shape_only else 'غير محسوم')
        inf = _inflection(self, nxt)
        th = self.G.Theta
        prot = th.get('protected') or {}
        if prot.get('cls'):
            pr = (prot['cls'], f"الجرد المعتمد: «{prot.get('identity')}» (root_status={th.get('root_status')})")
        elif self.divine or th.get('lex') == 'لفظ الجلالة':
            pr = ('لفظ الجلالة', 'sarf/divine.py: لا جذر')
        elif self.golden:
            pr = ('اسم ذهبي', 'الجرد GOLDEN: لا جذر')
        elif (self.lex or '') in ('مبني', 'عامل', 'مبني+عامل'):
            pr = ('مبني أو عامل' if self.lex != 'عامل' else 'عامل من العوامل المائة',
                  f'وحدةٌ معجمية مغلقة (lex={self.lex}) قبل توليد الجذر: CONSTITUTIONAL_PROTECTED_CLASS')
        else:
            pr = (None, 'غير محمية: يُستخرج جذرها')
        op = (self.lex or '').startswith('عامل') or 'عامل' in (self.lex or '')
        return dict(word_class=wc, build=inf['build'], inflection=inf,
                    protection=(pr[0], pr[1] + ('؛ والحماية من الجذر لا تمنع التحليل النحوي' if pr[0] else '')),
                    operator=(True, f'خانة {self.lex}') if op else (False, '—'))

    def definite(self):
        """→ (معرفة؟، الدليل) من السمات القائمة؛ وNone إن لم يثبت"""
        if self.divine:
            return True, 'لفظ الجلالة (علم)'
        if self.golden:
            return True, 'اسمٌ ذهبي في الجرد المعتمد (علم)'
        if self.mcat in ('separate_pronoun', 'demonstrative'):
            return True, f'ملف المبنيات: {self.mcat}'
        if self.dkind:
            return True, f'نوع المعرفة: {self.dkind}'
        if self.defin == 'معرفة' and self.defin_st == 'مثبت':
            return True, 'التعريف مثبت'
        if self.defin == 'نكرة' and self.defin_st == 'مثبت':
            return False, 'التنكير مثبت (التنوين)'
        if self.elative_proof() and 'أل' not in self.types:
            return False, 'أَفْعَل بلا «أل» ولا إضافةٍ مكتوبة: نكرةٌ ممنوعة من الصرف'
        return None, 'التعريف والتنكير غير مثبتين'

    def nominative(self):
        """→ (مرفوعٌ أو في محلّ رفع؟، الدليل)"""
        if self.case == 'رفع':
            return True, 'الرفع مكتوب (الضمة)'
        if self.case in ('نصب', 'جر', 'نصب أو جر', 'جر أو نصب'):
            return False, f'العلامة المكتوبة {self.case}'
        if self.lex == 'مبني' or self.mcat or self.dkind in ('معرفة: ضمير', 'معرفة: اسم إشارة', 'معرفة: اسم موصول'):
            return None, 'مبنيٌّ: المحلّ يُعيَّن بموقعه'
        return None, 'لا علامة إعرابٍ مكتوبةٌ تدلّ'


STATE_ADJ = {'رفع': 'مرفوع', 'نصب': 'منصوب', 'جر': 'مجرور', 'جزم': 'مجزوم'}
STATE_NOUN = {'رفع': 'رفعه', 'نصب': 'نصبه', 'جر': 'جرّه', 'جزم': 'جزمه'}
_EFFECT = {'جر ما بعده': 'جر', 'نصب الفعل المضارع': 'نصب', 'جزم المضارع': 'جزم'}
def _caps(effect):
    """قدرة العامل من نصّ أثره في الجرد: الحالات المذكورة فيه (جر، نصب، رفع، جزم)؛ ولا يُستنتج غير المذكور"""
    e = effect or ''
    return {c for c, ws in (('جر', ('جر', 'مجرور')), ('نصب', ('نصب', 'منصوب')), ('رفع', ('رفع', 'مرفوع')), ('جزم', ('جزم', 'مجزوم')))
            if any(w in e for w in ws)}


ROLE_AR = {'ibtida': 'الابتداء', 'khabar': 'الخبرية للمبتدأ', 'nasikh': 'الخبرية للناسخ', 'idafa': 'الإضافة'}
HARAKA_OF = {'رفع': 'الضمة', 'نصب': 'الفتحة', 'جر': 'الكسرة'}
BUILD_VOWEL = {FATHA: 'الفتح', DAMMA: 'الضم', KASRA: 'الكسر', SUKUN: 'السكون'}


def _mark_kind(name):
    """نوع العلامة: ظاهرة (حركةٌ مكتوبة)، أو مقدّرة، أو بالحرف نيابةً، أو بالحذف"""
    if not name:
        return None
    if name.startswith('مقدّرة'):
        return 'مقدّرة'
    if name in ('الكسرة', 'الفتحة', 'الضمة', 'السكون') or name.startswith('السكون'):
        return 'ظاهرة'
    if name.startswith('حذف'):
        return 'بالحذف'
    return 'بالحرف نيابةً عن الحركة'


def _mark_phrase(name, cap):
    k = _mark_kind(name)
    if k == 'ظاهرة' and name in ('الكسرة', 'الفتحة', 'الضمة', 'السكون'):
        return f'{name} الظاهر' if name == 'السكون' else f'{name} الظاهرة'
    if k == 'مقدّرة':
        return f'{HARAKA_OF.get(cap, "الحركة")} المقدّرة على الألف للتعذّر'
    return name


def _build_vowel(t):
    tl = letters(t.text)
    return next((v for c, v in BUILD_VOWEL.items() if tl and c in tl[-1][1]), None)


def _written_mark(t, nxt=None):
    """العلامة المكتوبة على آخر الوحدة مقروءةً بصنفها (لا بالحركة وحدها) → (اسم العلامة، الحالات التي تدلّ عليها، الدليل)؛
    والحالات frozenset، وفارغةٌ إن لم تدلّ العلامة على حالةٍ في هذا الصنف"""
    tl = letters(t.text)
    if not tl:
        return None, frozenset(), 'لا حروف'
    L, m = tl[-1]
    p = tl[-2] if len(tl) >= 2 else ('', set())
    R = (t.G.Theta.get('R') or '') if isinstance(t.G.Theta.get('R'), str) else ''
    if t.pos == 'فعل':
        sv = (t.feats.get('subject') or {}).get('v')
        sv = sv if isinstance(sv, dict) else {}
        five = sv.get('person') in (2, 3) and sv.get('number') in ('plural', 'dual') or sv.get('person') == 2 and sv.get('number') == 'singular' and sv.get('gender') == 'fem'
        five_ev = f"ضمير الصيغة ({sv.get('person')}، {sv.get('number')}، {sv.get('gender')})"
        if five and tl[0][0] in 'يتأن':
            if L == 'ن' and p[0] in 'اوي' and (FATHA in m or KASRA in m):
                return 'ثبوت النون', frozenset({'رفع'}), f'الأفعال الخمسة ({five_ev}): النون ثابتة'
            if L == 'ا' and p[0] in 'و' or L == 'و' and DAMMA in p[1] or L == 'ا' and FATHA in p[1] or L == 'ي' and KASRA in p[1]:
                return 'حذف النون', frozenset({'نصب', 'جزم'}), f'الأفعال الخمسة ({five_ev}): النون محذوفة'
        if len(R) == 3 and R[2] in 'وي' and L not in 'اويى' and L == R[1] and tl[0][0] in 'يتأن':
            return 'حذف حرف العلة', frozenset({'جزم'}), f'لام الجذر «{R[2]}» محذوفة من آخر المضارع ({R})'
        if len(R) == 3 and R[1] == R[2] and L == R[2] and SHADDA in m and FATHA in m:
            return 'الفتحة', frozenset({'نصب', 'جزم'}), f'المضعّف المدغم ({R}): يُحرَّك آخره بالفتح في الجزم، والفتحة علامة النصب'
        if SUKUN in m:
            return 'السكون', frozenset({'جزم'}), 'السكون على الآخر'
        if KASRA in m and nxt is not None and letters(nxt.text) and letters(nxt.text)[0][0] == 'ا' and \
                not (letters(nxt.text)[0][1] - {SHADDA}):
            return 'السكون (حُرِّك بالكسر لالتقاء الساكنين)', frozenset({'جزم'}), f'بعده همزة وصل «{nxt.text}»: الكسرة حركة تخلّص لا علامة'
        if DAMMA in m:
            return 'الضمة', frozenset({'رفع'}), 'الضمة على الآخر'
        if FATHA in m:
            return 'الفتحة', frozenset({'نصب'}), 'الفتحة على الآخر' + ('' if R else
                                                                         '؛ والجذر غير مثبت: إن كانت لامه حرف علة محذوفاً فالفتحة '
                                                                         'حركة العين لا علامة النصب، فلا يُنفى الجزم بها')
        if KASRA in m:
            return 'الكسرة', frozenset(), 'الكسرة لا تكون علامة إعرابٍ في الفعل' + ('' if R else '؛ والجذر غير مثبت: قد تكون اللام محذوفة')
        return None, frozenset(), 'لا علامة على الآخر'
    nf = t.feats.get('number') or {}
    num = nf.get('v') if nf.get('st') == 'مثبت' else None   # العدد المرشّح لا يُقرأ به حرف الإعراب (ٱلۡقُرۡءَانِ ليس مثنى)
    cand = nf.get('v') if nf.get('st') != 'مثبت' else None
    if L == 'ن' and p[0] in 'اي' and cand in ('dual', 'plural') and (FATHA in m or KASRA in m):
        return ('الحرف أو الحركة', frozenset(),
                f'العدد مرشّح ({cand}): الحرف قبل النون علامةٌ إن كان مثنى أو جمعاً، والحركة علامةٌ إن كان مفرداً؛ فلا تُعيَّن العلامة')
    if L == 'ن' and p[0] == 'ا' and KASRA in m and num == 'dual':
        return 'الألف', frozenset({'رفع'}), 'المثنى (العدد مثبت): الألف'
    if L == 'ن' and p[0] == 'ي' and SUKUN in p[1] and num == 'dual':
        return 'الياء', frozenset({'نصب', 'جر'}), 'المثنى: الياء'
    if L == 'ن' and p[0] == 'و' and FATHA in m and num == 'plural':
        return 'الواو', frozenset({'رفع'}), 'جمع المذكر السالم: الواو'
    if L == 'ن' and p[0] == 'ي' and FATHA in m and num == 'plural':
        return 'الياء', frozenset({'نصب', 'جر'}), 'جمع المذكر السالم: الياء'
    if L == 'ت' and (p[0] == 'ا' or p[1] & {'ٰ'}) and m & {KASRA, KASRATAN}:
        return 'الكسرة', frozenset({'نصب', 'جر'}), 'جمع المؤنث السالم: الكسرة في النصب والجر'
    if L == 'ا' and p[1] & {FATHATAN}:
        return 'الفتحة', frozenset({'نصب'}), 'تنوين الفتح (والألف بعده ألف التنوين)'
    if L in 'ىا' and not (m & {DAMMA, KASRA, DAMMATAN, KASRATAN}) or L == 'ى':
        return 'مقدّرة على الألف', frozenset({'رفع', 'نصب', 'جر'}), 'الاسم المقصور: الحركة مقدّرة'
    if m & {KASRA, KASRATAN}:
        return 'الكسرة', frozenset({'جر'}), 'الكسرة على الآخر'
    if m & {DAMMA, DAMMATAN}:
        return 'الضمة', frozenset({'رفع'}), 'الضمة على الآخر'
    if FATHATAN in m or L == 'ا' and p[1] & {FATHATAN}:
        return 'الفتحة', frozenset({'نصب'}), 'تنوين الفتح'
    if FATHA in m:
        mudaf = nxt is not None and nxt.wi == t.wi and nxt.enclitic
        if 'أل' not in t.types and not t.tanwin and not t.divine and not t.adverb and not mudaf:
            return 'الفتحة', frozenset({'نصب', 'جر'}), 'فتحةٌ بلا تنوين ولا «أل» ولا إضافةٍ مكتوبة: نصب، أو جرٌّ في الممنوع من الصرف'
        return 'الفتحة', frozenset({'نصب'}), 'الفتحة على الآخر' + ('، والظرف منصوبٌ على الظرفية' if t.adverb else '')
    return None, frozenset(), 'لا علامة إعرابٍ مكتوبة على الآخر'


def _madi_build(t):
    tx = t.text
    for suf, on in (('تُمْ', 'السكون'), ('تُمَا', 'السكون'), ('تُنَّ', 'السكون'), ('نَا', 'السكون'), ('تُ', 'السكون'), ('تَ', 'السكون'),
                    ('تِ', 'السكون'), ('نَ', 'السكون'), ('وا', 'الضم')):
        if tx.endswith(suf) and len(letters(tx)) > 3:
            return on
    tl = letters(tx)
    return 'الفتح' if tl and FATHA in tl[-1][1] else None


def _inflection(t, nxt=None):
    """محور البناء والإعراب: يُبنى على نوع الكلمة وحكم العامل، ثم يُطابَق بين ثلاثة: قدرة العامل (ما يقتضيه)، والعلامة المكتوبة
    مقروءةً بالصنف، والعبارة المولَّدة منهما. فلا تُقال العبارة إلا إذا اتفق الثلاثة؛ وما اختلف سُجّل CONFLICT، لا اختيار"""
    out = dict(uid=t.uid, text=t.text, build=(None, 'غير محسوم'), governor=None, state=(None, 'غير محسوم'), mark=None,
               mark_kind=None, cause=None, statement=None, agreement='N/A', conflicts=[],
               note='الاتفاق اتساقٌ بين العامل والعلامة والعبارة، لا إثباتٌ مستقل لوظيفة العامل: '
                    'العامل مقبولٌ في المرحلة ١١ بأدلته، والعلامة تُقرأ هنا من النص بصنف الكلمة')
    tense = (t.feats.get('tense') or {})
    lex = t.lex or ''
    mabni_unit = lex in ('مبني', 'مبني+عامل') or t.mcat is not None or t.enclitic
    # ١ البناء: من نوع الكلمة وزمن الفعل
    opsrc = next((r for r in t.roles if r['src'] == 'operator'), None)
    mood_op = opsrc is not None and opsrc['r'].get('expected') in ('نصب', 'جزم') and \
        (opsrc['r'].get('target') or {}).get('pos') == 'verb'
    if t.pos == 'فعل':
        tv, tst = tense.get('v'), tense.get('st')
        if tst != 'مثبت' and mood_op:
            out['build'] = ('معرب', f'العامل «{opsrc["o"]["operator"]}» مقبولٌ عاملاً في المضارع: المعمول مضارع معرب '
                                    f'(وسمة الزمن في المرحلة ١٣ «{tv}» مرشّحة: تُصالَح بهذا العامل)')
        elif tst != 'مثبت':
            out['build'] = (None, f'زمن الفعل غير مثبت ({tv}، {tst}): البناء يتبعه')
            name, cases, ev = _written_mark(t, nxt)
            out['mark'] = (name, ev) if name else None
            out['mark_kind'] = _mark_kind(name)
            out['state'] = (None, f'زمن الفعل غير مثبت؛ والعلامة «{name or "—"}» لا تُقال حالةً قبله')
            out['agreement'] = 'UNVERIFIED'
            return out
        elif tv == 'ماضٍ':
            on = _madi_build(t)
            out['build'] = ('مبني', f'فعلٌ ماضٍ: مبني' + (f' على {on}' if on else ''))
            out['cause'] = 'الماضي مبني: حركة آخره حركة بناءٍ لا علامة إعراب' + (f' (على {on})' if on else '')
            out['statement'] = 'فعل ماضٍ مبني' + (f' على {on}' if on else '')
            out['agreement'] = 'MABNI'
            return out
        elif tv == 'أمر':
            out['build'] = ('مبني', 'فعل أمر: مبني على ما يُجزم به مضارعه')
            out['agreement'] = 'MABNI'
            return out
        else:
            out['build'] = ('معرب', 'فعلٌ مضارع (الزمن مثبت): معرب، ولا نون نسوة ولا توكيد مكتوبة في هذه القراءة')
    elif t.divine or t.golden:
        out['build'] = ('معرب', 'لفظ الجلالة أو اسمٌ ذهبي: معرب' + ('، والوحدة تضمّ عامله' if 'عامل' in lex or len(t.types) > 1 else ''))
    elif (lex == 'عامل' or 'عامل' in str(t.pos or '')) and t.pos != 'اسم':
        out['build'] = ('مبني', 'أداةٌ أو فعلٌ جامد من جرد العوامل: مبني')
        out['state'] = (None, 'أداةٌ مبنية؛ ومحلّها (إن كان) لا يُعيَّن في هذا المحور')
        out['agreement'] = 'MABNI'
        return out
    elif mabni_unit:
        out['build'] = ('مبني', f'ملف المبنيات ({t.mcat or lex})')
    elif t.pos == 'اسم' and not t.shape_only or t.divine or t.golden or t.nounish():
        out['build'] = ('معرب', 'اسمٌ غير مبني: معرب' + (' (E01)' if t.elative_proof() else ''))
    elif getattr(t, 'adverb', None):
        out['build'] = ('معرب', f'ظرفٌ من جرد المشروع في علاقة {t.adverb}: معرب')
    elif t.shape_only:
        out['build'] = (None, 'الاسمية من شكل التنوين وحده (T19): البناء والإعراب يتبعانها')
        return out
    else:
        return out
    # ٢ العامل: عاملٌ مقبول (المرحلة ١١)، أو دورٌ في علاقةٍ مرخَّصة
    src = next((r for r in t.roles if r['src'] == 'operator'), None) or (t.roles[0] if t.roles else None)
    if src is None:
        name, cases, ev = _written_mark(t, nxt) if out['build'][0] == 'معرب' else (None, frozenset(), '')
        out['mark'] = (name, ev) if name else None
        out['mark_kind'] = _mark_kind(name)
        if out['build'][0] == 'مبني':
            out['state'] = (None, 'مبني: المحلّ يُعيَّن بالعامل، ولا عامل مثبت فيه')
        elif cases:
            out['state'] = (None, f'العلامة المكتوبة «{name}» تحتمل: {"، ".join(sorted(cases))}؛ ولا عامل مقبول ولا دور مرخَّص: لا يُقال')
        else:
            out['state'] = (None, f'{ev}؛ ولا عامل مقبول ولا دور مرخَّص')
        out['agreement'] = 'UNGOVERNED'
        return out
    if src['src'] == 'operator':
        o, r, op = src['o'], src['r'], src['op']
        cap = r.get('expected')
        caps = set().union(*[_caps(x.get('effect')) for x in o.get('meanings') or []]) if o.get('meanings') else set()
        out['governor'] = dict(kind='عامل', operator=o['operator'], position=op.loc, group=o['group'], expected=cap,
                               observed=r.get('observed'), consistent=r.get('consistent'), role=r.get('role'),
                               target_uid=t.uid, operator_proof=list((o.get('judgement') or {}).get('proof') or []),
                               capacity=sorted(set().union(*[_caps(x.get('effect')) for x in o.get('meanings') or []])
                                               if o.get('meanings') else []))
        gov_txt = f'بـ«{o["operator"]}»'
        obs = r.get('observed')
        obs_cases = {'حذف النون': {'نصب', 'جزم'}, 'جر أو نصب': {'جر', 'نصب'}, 'نصب أو جر': {'جر', 'نصب'}}.get(
            obs, {obs} if obs in STATE_ADJ else None)
        if obs_cases is not None and cap not in obs_cases:
            out['conflicts'].append(f'المرحلة ١١ سجّلت المشاهَد «{obs}» والمقتضى «{cap}»')
        if caps and cap not in caps and cap:
            out['conflicts'].append(f'قدرة العامل في الجرد {sorted(caps)} لا تشمل ما سُجّل له «{cap}»')
    else:
        cap = src['expected']
        out['governor'] = dict(kind=ROLE_AR.get(src['src'], src['src']), relation_id=src['rid'], expected=cap, of=src.get('of'))
        gov_txt = {'ibtida': 'بالابتداء', 'khabar': f'خبراً للمبتدأ «{src.get("of")}»',
                   'nasikh': f'خبراً لـ«{src.get("of")}»', 'idafa': f'مضافاً إليه لـ«{src.get("of")}»'}.get(src['src'], '')
    if out['build'][0] == 'مبني':
        kw = 'ضمير' if t.enclitic or t.mcat in ('separate_pronoun', 'attached_pronoun') else 'اسم'
        # حركة البناء تُذكر للضمير وحده: آخر الوحدة في غيره قد يكون لاحقةً لا آخر المبني (ذَٰلِكُمْ: الميم حرف خطاب)
        bv = _build_vowel(t) if kw == 'ضمير' else None
        out['state'] = (f'في محلّ {cap}', f'مبني، ومحلّه بالعامل {gov_txt}')
        out['mark_kind'] = 'محلّي'
        out['cause'] = f'{kw} مبني' + (f' على {bv}: حركة آخره حركة بناءٍ لا علامة إعراب' if bv else '') + \
            '؛ والحكم إعرابٌ محلّي'
        out['statement'] = f'{kw} مبني' + (f' على {bv}' if bv else '') + f' في محلّ {cap} {gov_txt}'
        if src['src'] == 'operator' and src['r'].get('observed') not in ('محلاً', None):
            out['conflicts'].append(f'المرحلة ١١ قرأت على المبني علامةً «{src["r"].get("observed")}»')
        out['agreement'] = 'AGREE' if not out['conflicts'] else 'CONFLICT'
        return out
    name, cases, ev = _written_mark(t, nxt)
    out['mark'] = (name, ev) if name else None
    if t.pos == 'فعل' and cap == 'جر':
        out['conflicts'].append('العامل يقتضي الجرّ والمعمول فعل: الفعل لا يُجرّ')
    if not name or not cases:
        out['state'] = (cap, f'مقتضى العامل {gov_txt}؛ والعلامة غير مقروءة بالصنف ({ev}): المطابقة غير مثبتة')
        out['agreement'] = 'UNVERIFIED' if not out['conflicts'] else 'CONFLICT'
        return out
    if cap not in cases:
        out['conflicts'].append(f'العلامة «{name}» تدلّ على {"، ".join(sorted(cases))} والعامل يقتضي {cap}')
    if out['conflicts']:
        out['state'] = (None, 'تعارض: ' + '؛ '.join(out['conflicts']))
        out['agreement'] = 'CONFLICT'
        return out
    kind = 'فعل مضارع' if t.pos == 'فعل' else 'اسم'
    out['state'] = (cap, f'العامل {gov_txt} يقتضي {cap}، والعلامة «{name}» تدلّ عليه ({ev})')
    out['mark_kind'] = _mark_kind(name)
    out['cause'] = ev
    out['statement'] = f'{kind} {STATE_ADJ[cap]} {gov_txt} وعلامة {STATE_NOUN[cap]} {_mark_phrase(name, cap)}'
    out['agreement'] = 'AGREE'
    return out


_LEX = []


def _mabni_cat(text, identity=None):
    """فئة المبني من ملف المبنيات بصورته المكتوبة، أو بهويته المحمية؛ إن اتّفقت مداخله"""
    if not _LEX:
        from .lexicon import MabniLexicon
        _LEX.append(MabniLexicon())
    for t in (text, identity):
        cats = {e.get('category') for e in (_LEX[0].lookup(t) or [])} if t else set()
        if len(cats) == 1:
            return next(iter(cats))
    # المندمج رسماً في الجرد المعتمد (sarf.protected.MERGED): «ذَٰلِكَ، ذَٰلِكُمْ» = ذَا + لِ + كاف الخطاب: إشارة
    from .protected import MERGED
    parts = MERGED.get(identity or text)
    if parts and len(parts) == 3 and parts[0] == 'ذَا' and parts[1] == 'لِ':
        return 'demonstrative'
    return None


def _pron_feats(text):
    """(الشخص، العدد، الجنس) للضمير المتصل من ملف المبنيات المعتمد، إن اتّفقت مداخله؛ وإلا (None، None، None)"""
    if not _LEX:
        from .lexicon import MabniLexicon
        _LEX.append(MabniLexicon())
    ents = [e for e in (_LEX[0].lookup(text) or []) if e.get('category') == 'attached_pronoun']
    vals = {(e.get('extra') or {}).get('person') and ((e.get('extra') or {}).get('person'), (e.get('extra') or {}).get('number'),
                                                     (e.get('extra') or {}).get('gender')) for e in ents}
    vals.discard(None)
    return next(iter(vals)) if len(vals) == 1 else (None, None, None)


def _rec(ref, typ, rule, heads, members, status, reason, premises=(), checked=(), alternatives=(), container=None, **kw):
    rid = f'{ref}:{typ}:{rule}:' + '+'.join(f'{r}={u.uid}' for r, u in sorted(heads.items()))
    out = dict(relation_id=rid, source_id=ref, type=typ, rule_id=rule, rule_version=VERSION,
               analysis_id='+'.join(f'{u.uid}@{VERSION}' for _, u in sorted(heads.items())),
               container_id=container, heads={r: u.uid for r, u in heads.items()},
               members={r: [u.uid for u in us] for r, us in members.items()},
               positions={r: [u.loc for u in us] for r, us in members.items()},
               texts={r: ' '.join(u.text for u in us) for r, us in members.items()},
               premises=list(premises), checked=list(checked), alternatives=list(alternatives),
               status=status, reason=reason, selected_analysis=None, nucleus_complete=None, clause_complete=None,
               boundary_proven=False, sentence_closed=False)
    out.update(kw)
    return out


def verse_relations(a, units, F, ref):
    """→ dict(records=[…], tokens=[(uid، الموضع، النص)]) لآيةٍ واحدة"""
    from .algebra import ZURUF_V, is_form
    toks = [_Tok(a, units[k], k, F, a['segments'][k[0]], ref) for k in sorted(units)]
    idx = {t.k: i for i, t in enumerate(toks)}
    by_k = {t.k: t for t in toks}
    R = []
    st = {(f['word_index'], f['operator'], f['group']): f.get('status') for f in a['operators']}
    governed = {}
    for o in a['operators']:
        r = o.get('relation') or {}
        t = r.get('target') or {}
        if o.get('status') == 'accepted' and t:
            seg = a['segments'][t['word_index']]
            ui = next((i for i, u in enumerate(seg['units']) if t['slot'] in u.get('slots', [])), None)
            sl = o.get('slot') or {}
            if ui is not None and (o['word_index'], sl.get('unit')) in by_k and (t['word_index'], ui) in by_k:
                governed[(t['word_index'], ui)] = (by_k[(o['word_index'], sl.get('unit'))], o, r)
    for k_, (op_t, o, r) in governed.items():
        by_k[k_].roles.append(dict(src='operator', op=op_t, o=o, r=r))

    def nxt(i):
        return toks[i + 1] if i + 1 < len(toks) else None

    def word_start(t):
        return t.ui == 0 or all(x.conj for x in toks[idx[(t.wi, 0)]:idx[t.k]])

    def frame_end(i):
        """أول وحدةٍ بعد i تبدأ إطاراً جديداً: كلمةٌ أولها عاطف، أو ما له الصدارة؛ أو آخر الآية (حدّ مصدر لا حدّ تركيب)"""
        from .algebra import clause_start
        for j in range(i + 1, len(toks)):
            t = toks[j]
            if t.ui == 0 and (t.conj or clause_start(a, t.wi)):
                return j
        return len(toks)

    # P01 الجار والمجرور
    obliques = {}
    for k, (op_t, o, r) in governed.items():
        if str(o['group']) != JARR or k not in by_k:
            continue
        comp = [by_k[k]] if by_k[k] is not op_t else []   # الجار والمجرور في وحدةٍ واحدة (لِلشَّهَٰدَةِ): الوحدة نفسها
        i = idx[k]
        if not comp:
            rec = _rec(ref, 'PP', 'P01', {'preposition': op_t}, {'preposition': [op_t]}, LICENSED,
                       'حرف جرٍّ مقبول ومعموله في وحدةٍ واحدة', premises=[f'حكم العامل «{o["operator"]}» (مج 1): مقبول',
                                                                          f'العلامة في المعمول: {r.get("observed")}'],
                       merged_unit=True, attachment='غير مثبت: انظر A01')
            R.append(rec)
            obliques[op_t.k] = (rec, [op_t])
            continue
        ext = []
        if nxt(i) is not None and nxt(i).wi == comp[0].wi and nxt(i).enclitic and comp[0].nounish():
            comp.append(nxt(i))                      # المضاف إلى ضميرٍ متصل في كلمته (رِجَالِكُمْ)
        elif nxt(i) is not None and nxt(i).wi == comp[0].wi + 1 and (nxt(i).feats.get('idafa') or {}).get('v') == 'مضاف إليه' and \
                (comp[0].feats.get('idafa') or {}).get('v') == 'مضاف':
            ext = [nxt(i)]                           # مضافٌ إليه مرشّح (بِكُلِّ شَيْءٍ): جزءٌ من المكمّل، وحالته مرشّحة
        members = {'preposition': [op_t], 'complement': comp}
        if ext:
            members['complement_ext'] = ext
        rec = _rec(ref, 'PP', 'P01', {'preposition': op_t, 'complement': comp[0]},
                   members, LICENSED, 'حرف جرٍّ مقبول ومعموله' + ('، ومضافٌ إليه مرشّح يمدّ المكمّل' if ext else ''),
                   premises=[f'حكم العامل «{o["operator"]}» (مج 1): مقبول — ' + str((o.get('judgement') or {}).get('proof') or '')[:120],
                             f'العلامة في المعمول: {r.get("observed")}'],
                   checked=['R6 المرفوع بعد الجار (في حكم العامل)'],
                   edges=[('GOVERN', op_t.uid, comp[0].uid)], attachment='غير مثبت: انظر A01')
        R.append(rec)
        obliques[op_t.k] = (rec, [op_t] + comp + ext)
    # P02 الظرف
    for i, t in enumerate(toks):
        if 'جذع' not in t.types or not is_form(t.text, ZURUF_V, i3rab=True):
            continue
        n = nxt(i)
        comp = None
        if n is not None and n.wi == t.wi and n.enclitic:
            comp, why = [n], f'ضميرٌ متصل «{n.text}» مضافٌ إليه'
        elif n is not None and n.wi == t.wi + 1 and word_start(n) and not n.conj and (n.divine or n.nounish()) and \
                n.case in ('جر', 'جر أو نصب'):
            comp, why = [n], f'«{n.text}» مجرورٌ كتابةً بعده بلا جار'
        if comp:
            rec = _rec(ref, 'ADVP', 'P02', {'adverb': t, 'complement': comp[0]}, {'adverb': [t], 'complement': comp}, LICENSED,
                       'ظرفٌ من جرد المشروع ومضافٌ إليه', premises=['جرد الظروف sarf.algebra.ZURUF_V', why],
                       checked=['ليس حرف جر: الظرف اسمٌ منصوب على الظرفية والمضاف إليه بعده'],
                       edges=[('GOVERN', t.uid, comp[0].uid)], attachment='غير مثبت: انظر A01', phrase_kind='OBL/ADVP')
        elif n is not None and n.wi == t.wi + 1 and word_start(n) and not n.conj and n.shape_only and n.case in ('جر', 'جر أو نصب'):
            rec = _rec(ref, 'ADVP', 'P02', {'adverb': t}, {'adverb': [t], 'complement_candidate': [n]}, DEFERRED,
                       f'«{n.text}» مجرورٌ بعده، واسميته من شكل التنوين وحده (العقد T19): المضاف إليه غير مثبت',
                       premises=['جرد الظروف sarf.algebra.ZURUF_V'], alternatives=[f'«{n.text}» مضافٌ إليه'], phrase_kind='OBL/ADVP')
        else:
            rec = _rec(ref, 'ADVP', 'P02', {'adverb': t}, {'adverb': [t]}, DEFERRED, 'ظرفٌ بلا مضافٍ إليه مثبت بعده',
                       premises=['جرد الظروف sarf.algebra.ZURUF_V'], phrase_kind='OBL/ADVP')
        R.append(rec)
        t.adverb = 'P02'
        obliques[t.k] = (rec, [t] + (comp or rec['members'].get('complement_candidate') and [n] or []))
    span_of = {}                                    # وحدة ← شبه الجملة التي تضمّها
    for hk, (rec, us) in obliques.items():
        for u in us:
            span_of[u.k] = hk

    def oblique_at(i):
        """→ (السجل، وحداته، فهرس ما بعدها) إن بدأت شبه جملةٍ مرخَّصة عند i"""
        if i < len(toks) and toks[i].k in obliques:
            rec, us = obliques[toks[i].k]
            if rec['status'] == LICENSED:
                return rec, us, idx[us[-1].k] + 1
        return None

    bound = {}                                      # وحدة ← السجل الذي جعلها طرفاً في ناسخ أو صلة (تمنع N01)
    used_as_pred = set()                            # شبه جملةٍ صارت خبراً في وجهٍ مرخَّص: لا تُرسل إلى A01 في هذا الوجه
    containers = {}
    # R01 إطار الصلة المحدود، وفيه نواة N02
    for i, t in enumerate(toks):
        if t.lex != 'مبني' or not is_form(t.text, REL_SPECIFIC):
            continue
        ob = oblique_at(i + 1)
        if not ob:
            continue
        prec, pus, j = ob
        s = toks[j] if j < len(toks) else None
        if s is not None and s.shape_only and s.k not in governed and s.nominative()[0] is True:
            R.append(_rec(ref, 'CONTAINER_RELATIVE', 'R01', {'relative': t}, {'relative': [t], 'content': pus + [s]}, DEFERRED,
                          f'اسمية «{s.text}» من شكل التنوين وحده (العقد T19): لا تُبنى الصلة الاسمية بها',
                          premises=[prec['relation_id']]))
            continue
        if s is None or not s.nounish() or s.k in governed or s.nominative()[0] is not True:
            continue
        rel_gov = governed.get(t.k)
        verbs_ = {(g['word_index'], g['slot']) for g in a.get('agreement', [])}
        verb_before = next((toks[x] for x in range(i - 1, -1, -1)
                            if toks[x].pos == 'فعل' or 'فعل' in ((toks[x].feats.get('pos') or {}).get('alt') or []) or
                            any((toks[x].wi, sl['index']) in verbs_ for sl in toks[x].slots)), None)   # الفعل المحتمل منافسٌ كافٍ للتأجيل
        if s.definite()[0] is not False and rel_gov and str(rel_gov[1]['group']) == JARR and verb_before is not None:
            R.append(_rec(ref, 'CONTAINER_RELATIVE', 'R01', {'relative': t}, {'relative': [t], 'content': pus + [s]}, DEFERRED,
                          f'الموصول مجرور، وقبله الفعل «{verb_before.text}»: المعرفة المرفوعة «{s.text}» قد تكون فاعله لا مسنداً في الصلة',
                          premises=[prec['relation_id']], alternatives=[f'«{s.text}» فاعل «{verb_before.text}»، والصلة شبه الجملة وحدها']))
            continue
        members = [t] + pus + [s]
        stop = toks[j + 1] if j + 1 < len(toks) else None
        stop_why = 'آخر الآية (حدّ مصدر)' if stop is None else \
            f'«{stop.text}» {"منصوب" if stop.case == "نصب" else "لا يتّصل بالصلة بقاعدةٍ في هذا الإصدار"}'
        crec = _rec(ref, 'CONTAINER_RELATIVE', 'R01', {'relative': t}, {'relative': [t], 'content': pus + [s]}, LICENSED,
                    'الموصول المختصّ تليه شبه جملة ثم مرفوع: صلةٌ اسمية (خبرها شبه الجملة المقدَّمة)',
                    premises=[f'«{t.text}» موصولٌ مختصّ (ملف المبنيات)', prec['relation_id'], f'«{s.text}» مرفوعٌ كتابةً'],
                    checked=[f'حدّ الصلة بعد «{s.text}»: {stop_why}'], container=None,
                    extent=[u.uid for u in members])
        R.append(crec)
        cid = crec['relation_id']
        containers[cid] = members
        used_as_pred.add(prec['relation_id'])
        nrec = _rec(ref, 'PREDICATIVE_PP', 'N02', {'subject': s, 'predicate_pp': pus[0]},
                    {'subject': [s], 'predicate_pp': pus}, LICENSED,
                    'في إطار الصلة: شبه الجملة المقدَّمة خبر، والمرفوع بعدها مسندٌ إليه',
                    premises=[crec['relation_id'], prec['relation_id'], f'«{s.text}»: {s.nominative()[1]}'],
                    checked=['الصلة لا تكون مفرداً: فالمرفوع بعد شبه الجملة ليس معطوفاً عليها ولا مضافاً إليها'],
                    container=cid, nucleus_complete=True,
                    display_convention='شبه الجملة خبرٌ في هذا الوجه (أو متعلّقٌ بخبرٍ محذوف)؛ ولا يُكتب المحذوف')
        R.append(nrec)
        for u in members:
            bound[u.k] = crec['relation_id']
        comp = pus[-1]
        if comp.enclitic and comp.text in ('هِ', 'هُ', 'هَا', 'هُمْ', 'هِمْ', 'هُمَا', 'هِمَا', 'هُنَّ', 'هِنَّ'):
            want = REL_AGR.get(t.text)
            got = _pron_feats(comp.text)
            if want and all(got) and got == want:
                st_, why = LICENSED, f'الضمير «{comp.text}» للغائب {got[1]} {got[2]} يطابق «{t.text}»'
            else:
                st_, why = DEFERRED, (f'ملف المبنيات لا يسجّل شخص «{comp.text}» وعدده وجنسه: المطابقة غير مثبتة'
                                      if not any(got) else f'المطابقة غير مثبتة (الموصول {want}، الضمير {got})')
            R.append(_rec(ref, 'RESUMPTIVE', 'R01', {'pronoun': comp, 'relative': t}, {'pronoun': [comp], 'relative': [t]}, st_, why,
                          premises=[crec['relation_id'], 'سمات الضمير من ملف المبنيات'], container=cid))
    # V01 وصلة الناسخ
    for k, (op_t, o, r) in governed.items():
        g = str(o['group'])
        if g not in (NASIKH_KANA, NASIKH_INNA) or k not in by_k:
            continue
        ism = by_k[k]
        i_n, i_s = idx[op_t.k], idx[k]
        if ism is op_t or ism.wi == op_t.wi and g == NASIKH_KANA:
            R.append(_rec(ref, 'NASIKH', 'V01', {'nasikh': op_t}, {'nasikh': [op_t]}, DEFERRED,
                          'الاسم المربوط هو الناسخ نفسه أو ضميرٌ في كلمته (كَانُوا): الاسم ضمير الصيغة، والخبر غير مربوطٍ بهذه القاعدة',
                          premises=[f'حكم الناسخ «{o["operator"]}» (مج {g})']))
            continue
        if g == NASIKH_KANA and ism.case == 'نصب':
            R.append(_rec(ref, 'NASIKH', 'V01', {'nasikh': op_t}, {'nasikh': [op_t], 'khabar_candidate': [ism]}, DEFERRED,
                          f'المربوط «{ism.text}» منصوبٌ كتابةً فلا يكون اسم «{o["operator"]}»: الاسم ضميرٌ مستتر، والمنصوب خبرٌ مرشّح',
                          premises=[f'حكم الناسخ «{o["operator"]}» (مج {g})', f'«{ism.text}»: النصب مكتوب'],
                          alternatives=[f'«{ism.text}» خبر «{o["operator"]}» واسمها ضمير الصيغة']))
            continue
        prem = [f'حكم الناسخ «{o["operator"]}» (مج {g}): مقبول، واسمه «{ism.text}» ({r.get("observed")})']
        khabar, kwhy, kst = None, 'لا خبر مثبتٌ بشرط هذا الإصدار', DEFERRED
        kcand = None
        between = [toks[j] for j in range(i_n + 1, i_s) if not toks[j].enclitic or toks[j].wi != op_t.wi]
        ob = oblique_at(i_n + 1) if between else None
        if ob and ob[2] == i_s and ism.definite()[0] is False:
            khabar, kwhy, kst = ob[1], 'شبه جملةٍ مقدَّمة بين الناسخ واسمه النكرة: خبرٌ مقدَّم', LICENSED
            prem.append(ob[0]['relation_id'])
            used_as_pred.add(ob[0]['relation_id'])
        else:
            j = i_s + 1
            cont = next((cid for cid, us in containers.items() if us[0].k == ism.k), None)
            if cont:
                j = idx[containers[cont][-1].k] + 1   # الاسم موصولٌ وصلته حاويةٌ مستقلة الدليل (R01): الخبر بعدها
                prem.append(cont)
            while j < len(toks) and toks[j].enclitic:
                j += 1
            c = toks[j] if j < len(toks) else None
            want = 'نصب' if g == NASIKH_KANA else 'رفع'
            if c is not None and c.nounish() and c.case == want and c.k not in governed:
                khabar, kwhy, kst = [c], f'«{c.text}» اسمٌ {"منصوب" if want == "نصب" else "مرفوع"} كتابةً بعد الاسم' + \
                    (' وصلته' if cont else ''), LICENSED
            elif c is not None and (c.nounish() or c.shape_only) and c.case in ('نصب', 'رفع', 'جر') and c.case != want:
                kwhy = f'«{c.text}» {c.case} كتابةً، والناسخ يقتضي {want}: لا يُرخَّص خبراً'
            elif c is not None and c.shape_only and c.k not in governed and c.case == want:
                kwhy = f'«{c.text}» خبرٌ مرشّح، واسميته من شكل التنوين وحده (العقد T19): لا يُرخَّص به الخبر'
                kcand = [c]
        heads = {'nasikh': op_t, 'ism': ism}
        members = {'nasikh': [op_t], 'ism': [ism]}
        if khabar:
            heads['khabar'] = khabar[0]
            members['khabar'] = khabar
        elif kcand:
            members['khabar_candidate'] = kcand     # المرشّح ظاهرٌ في السجل لا يسقط، ولا يُثبَّت خبراً
        rec = _rec(ref, 'NASIKH', 'V01', heads, members, kst, kwhy, premises=prem, nasikh_group=g,
                   alternatives=[f'«{kcand[0].text}» خبر «{o["operator"]}» إن ثبتت اسميته بدليلٍ غير التنوين'] if kcand else [],
                   checked=['N01 غير المنسوخة لا تُطبَّق على اسم الناسخ وخبره'], nucleus_complete=kst == LICENSED)
        R.append(rec)
        for us in members.values():
            for u in us:
                if u is not op_t:
                    bound[u.k] = rec['relation_id']
    nuclei = []                                     # النوى المرخَّصة بـN01 وإطاراتها (لقاعدة A02)

    licensed_subjects = set()                       # المسند إليه في نواةٍ مرخَّصة: لا يكون منافس عطفٍ لما بعده

    def coord_rival(s):
        """منافس العطف: أقرب اسمٍ مرفوعٍ كتابةً قبل العاطف في الآية (في ثماني كلماتٍ قبله)، خارج شبه الجملة.
        ولا منافس: إن كان المسند إليه ضميراً منفصلاً (يُبتدأ به بعد الواو حالاً أو استئنافاً)، أو فصل بينهما فعلٌ ليس
        في صلة موصولٍ بعد المنافس (اكتمل كلامه)، أو كان المنافس مسنداً إليه في نواةٍ مرخَّصة"""
        from .algebra import PRON_FREE_V
        if s.mcat == 'separate_pronoun' or is_form(s.text, PRON_FREE_V):
            return None
        i0 = idx[(s.wi, 0)]
        verb_between, rel_between = False, False
        for j in range(i0 - 1, -1, -1):
            x = toks[j]
            if x.wi < s.wi - 8:
                break
            if x.pos == 'فعل':
                verb_between = True
            if x.lex == 'مبني' and is_form(x.text, REL_SPECIFIC):
                rel_between = True
            if x.k in span_of or x.enclitic or x.conj:
                continue
            if x.case == 'رفع' and x.pos != 'فعل':
                if x.k in licensed_subjects or verb_between and not rel_between:
                    return None
                return x                                # المنافس المحتمل يكفي للتأجيل: رفعٌ مكتوب في غير فعل
        return None

    # N01 وN02 خارج الحاويات
    for i, s in enumerate(toks):
        if s.conj or s.enclitic or not word_start(s) or s.k in bound or s.k in span_of:
            continue
        if not (s.nounish() or s.shape_only or s.mcat in ('separate_pronoun', 'demonstrative') or
                s.lex == 'مبني' and s.dkind in ('معرفة: ضمير', 'معرفة: اسم إشارة')):
            continue
        prev_conj = s.ui > 0
        pw = toks[idx[(s.wi, 0)] - 1] if idx[(s.wi, 0)] > 0 else None
        mabni_start = (s.mcat in ('separate_pronoun', 'demonstrative') or s.lex == 'مبني') and \
            not (pw is not None and pw.pos == 'فعل') and \
            not (pw is not None and pw.pos != 'فعل' and 'جذع' in pw.types and not pw.tanwin and 'أل' not in pw.types and not pw.enclitic)
        # الضمير بعد الفعل تأكيدٌ لفاعله أو فاعلٌ (يُمِلَّ هُوَ)، والإشارة بعد اسمٍ بلا أل ولا تنوين مضافٌ إليه (دَابِرَ هَٰٓؤُلَآءِ)
        if not (s.wi == 0 or prev_conj or mabni_start):
            continue                                  # أول الكلام: أول الآية، أو بعد عاطف في كلمته، أو ضميرٌ وإشارة
        if s.k in governed:
            continue
        nom, nom_why = s.nominative()
        dfn, dfn_why = s.definite()
        fe = frame_end(i)
        j = i + 1
        while j < fe and toks[j].enclitic and toks[j].wi == s.wi:
            j += 1
        mid = []
        while oblique_at(j) and j < fe:
            o_ = oblique_at(j)
            mid.append(o_)
            j = o_[2]
        p = toks[j] if j < fe else None
        after_op = p is not None and (p.lex or '').startswith('عامل') and not p.nounish()
        if after_op:
            p = None                                  # عاملٌ بعده (مِمَّنْ، إِذَا، لَا): ليس مسنداً مفرداً
        base_prem = [f'«{s.text}» أول الكلام ({"بعد عاطف" if prev_conj else "أول الآية" if s.wi == 0 else "ضميرٌ أو إشارة"})',
                     f'«{s.text}»: {nom_why}', f'«{s.text}»: {dfn_why}']
        rival = coord_rival(s) if prev_conj else None
        if nom is False:
            continue
        if p is None and mid and len(mid) == 1:
            # N02: معرفةٌ مرفوعة ثم شبه جملة في آخر الإطار
            deriv = (s.feats.get('derivation') or {}).get('v') in ('اسم فاعل', 'اسم مفعول', 'مصدر') or \
                'derivation_candidates' in s.feats
            by_sadara = fe < len(toks) and not toks[fe].conj
            if after_op:
                st_, why = DEFERRED, 'بعد شبه الجملة عاملٌ في الإطار نفسه (لَا، مِمَّنْ…): قد تتعلّق به والخبر ما بعده'
            elif by_sadara:
                st_, why = DEFERRED, f'الإطار انقطع بما له الصدارة «{toks[fe].text}» لا بعاطفٍ ولا بآخر الآية: قد يكون المسند بعده'
            elif deriv:
                st_, why = DEFERRED, f'«{s.text}» وصفٌ أو مصدرٌ يعمل: قد تتعلّق شبه الجملة به لا أن تكون خبراً'
            elif s.shape_only:
                st_, why = DEFERRED, f'اسمية «{s.text}» من شكل التنوين وحده (العقد T19): لا يُرخَّص بها إسناد'
            elif rival is not None:
                st_, why = DEFERRED, (f'منافس العطف: «{rival.text}» ({rival.loc}) مرفوعٌ قبل العاطف، فقد يكون «{s.text}» معطوفاً عليه '
                                      'وشبه الجملة نعتاً له أو متعلّقةً به، لا خبراً')
            elif not dfn:
                st_, why = DEFERRED, 'أهلية الابتداء غير مثبتة'
            else:
                st_, why = LICENSED, 'معرفةٌ في أول الكلام ثم شبه جملةٍ تختم الإطار'
            R.append(_rec(ref, 'PREDICATIVE_PP', 'N02', {'subject': s, 'predicate_pp': mid[0][1][0]},
                          {'subject': [s], 'predicate_pp': mid[0][1]}, st_, why,
                          alternatives=['معطوفٌ على ما قبل العاطف، وشبه الجملة متعلّقةٌ به أو نعت'] if prev_conj else [],
                          premises=base_prem + [mid[0][0]['relation_id'], 'لا مضيف بعد شبه الجملة داخل الإطار'],
                          nucleus_complete=st_ == LICENSED,
                          display_convention='شبه الجملة خبر (أو متعلّقٌ بخبرٍ محذوف)؛ ولا يُكتب المحذوف'))
            if st_ == LICENSED:                     # المؤجَّل لا يحجب مرشّحات التعلّق: الوجه الآخر يبقى ظاهراً في A01
                used_as_pred.add(mid[0][0]['relation_id'])
                licensed_subjects.add(s.k)
            continue
        if p is None:
            if not mid:
                R.append(_rec(ref, 'PREDICATION', 'N01', {'subject': s}, {'subject': [s]}, DEFERRED,
                              'مسندٌ إليه محتمل بلا مسندٍ في إطاره: لا يُختلق خبر', premises=base_prem, nucleus_complete=False,
                              alternatives=['معطوفٌ على ما قبل العاطف'] if prev_conj else []))
            continue
        heads = {'subject': s, 'predicate': p}
        members = {'subject': [s], 'predicate': [p]}
        prem = base_prem + [m[0]['relation_id'] for m in mid]
        alts = ['معطوفٌ على ما قبل العاطف (لا مبتدأ)'] if prev_conj else []
        if rival is not None:
            alts.append(f'«{s.text}» معطوفٌ على «{rival.text}» ({rival.loc})، والمسند لهما أو لغيرهما')
        if s.shape_only:
            st_, why = DEFERRED, f'اسمية «{s.text}» من شكل التنوين وحده (العقد T19): لا يُرخَّص بها إسناد'
        elif not p.nounish():
            st_, why = DEFERRED, f'اسمية «{p.text}» غير مثبتة في هذا التحليل' + \
                (' (أَفْعَل: اسم تفضيلٍ مرشّح، أو مضارع المتكلم)' if 'elative' in p.feats else '') + \
                (': من شكل التنوين وحده (العقد T19)' if p.shape_only else '')
        elif p.elative_proof() and j + 1 < fe and toks[j + 1].nounish() and toks[j + 1].case == 'جر':
            st_, why = DEFERRED, f'«{p.text}» أَفْعَل بعده مجرور: مضافٌ محتمل، وتعريفه غير محسوم'
        elif p.case in ('نصب', 'جر') or p.case and p.case not in ('رفع',):
            st_, why = REJECTED, f'«{p.text}» {p.case} كتابةً: لا يُرخَّص خبراً مفرداً مرفوعاً في هذا الوجه (ولا يُحكم على النص كله)'
        elif p.case != 'رفع':
            st_, why = DEFERRED, f'رفع «{p.text}» غير مثبت كتابةً'
        elif p.k in governed:
            st_, why = REJECTED, f'«{p.text}» معمولٌ لعاملٍ مقبول'
        elif dfn is not True:
            st_, why = DEFERRED, 'أهلية الابتداء غير مثبتة: المسند إليه ' + dfn_why + ' (والعلم بلا جردٍ لا يثبت)'
            alts.append('نعتٌ ومنعوت (نكرتان مرفوعتان)')
        elif p.definite()[0] is not False:
            st_, why = DEFERRED, 'الطرفان معرفتان أو تعريف المسند غير منفيّ: خبرٌ معرفة، أو نعت، أو بدل — خارج تغطية N01 v1'
            alts += ['نعت', 'بدل', 'خبرٌ معرفة']
        else:
            nn = toks[j + 1] if j + 1 < fe else None
            if nn is not None and not nn.enclitic and (nn.nounish() or nn.shape_only) and nn.case == 'رفع':
                st_, why = DEFERRED, f'بعد «{p.text}» مرفوعٌ آخر «{nn.text}»: خبرٌ جملة أو تعدّد أو نعت — خارج القاعدة البسيطة'
                alts.append('خبرٌ جملة اسمية')
            else:
                st_, why = LICENSED, 'معرفةٌ مرفوعة في أول الكلام ومسندٌ نكرةٌ مرفوعٌ كتابةً'
                prem.append(f'«{p.text}»: الرفع مكتوب، والتنكير مثبت' + (f' ({p.definite()[1]})' if p.elative_proof() else ''))
                if p.elative_proof():
                    prem.append(p.elative_proof())
        if mid:
            alts.append('شبه الجملة بين الطرفين خبرٌ أول أو متعلّقٌ بالمسند: انظر A01')
        R.append(_rec(ref, 'PREDICATION', 'N01', heads, members, st_, why, premises=prem,
                      checked=['ناسخٌ مثبت عامل فيهما', 'عاملٌ مقبول في المسند إليه', 'علامةٌ مخالفة في المسند'],
                      alternatives=alts, nucleus_complete=st_ == LICENSED,
                      clause_complete=None if mid else None,
                      edges=[('PREDICATION', s.uid, p.uid)] if st_ == LICENSED else []))
        if st_ == LICENSED:
            R[-1]['roles'] = {'subject': 'مبتدأ', 'predicate': 'خبر'}
            nuclei.append(dict(rec=R[-1], s=s, p=p, lo=i, hi=fe))
            licensed_subjects.add(s.k)
    # N02: شبه جملة في أول الكلام ثم نكرةٌ مرفوعة تختم الإطار (في الدار رجلٌ)
    for i, t in enumerate(toks):
        if not word_start(t) or t.k in bound or not (t.wi == 0 or t.ui > 0 and toks[i - 1].conj):
            continue
        ob = oblique_at(i)
        if not ob:
            continue
        j = ob[2]
        fe = frame_end(i)
        s = toks[j] if j < fe else None
        if s is None or not (s.nounish() or s.shape_only) or s.k in bound or s.k in governed or j + 1 != fe:
            continue
        nom, nwhy = s.nominative()
        dfn, dwhy = s.definite()
        if nom is not True:
            continue
        st_ = LICENSED if dfn is False and not s.shape_only else DEFERRED
        if s.shape_only:
            dwhy += '؛ واسميته من شكل التنوين وحده (العقد T19)'
        R.append(_rec(ref, 'PREDICATIVE_PP', 'N02', {'subject': s, 'predicate_pp': ob[1][0]}, {'subject': [s], 'predicate_pp': ob[1]},
                      st_, 'شبه جملةٍ مقدَّمة ونكرةٌ مرفوعة تختم الإطار' if st_ == LICENSED else
                      f'اسمية «{s.text}» من شكل التنوين وحده (العقد T19)' if s.shape_only else
                      'المرفوع بعد شبه الجملة معرفة خارج إطار صلةٍ مثبت: خارج تغطية N02 v1',
                      premises=[ob[0]['relation_id'], f'«{s.text}»: {nwhy}', f'«{s.text}»: {dwhy}'],
                      nucleus_complete=st_ == LICENSED,
                      display_convention='شبه الجملة خبرٌ مقدَّم (أو متعلّقٌ بخبرٍ محذوف)؛ ولا يُكتب المحذوف'))
        if st_ == LICENSED:
            used_as_pred.add(ob[0]['relation_id'])
    # A01 توليد مرشّحات التعلّق
    for hk, (orec, ous) in obliques.items():
        if orec['status'] != LICENSED or orec['relation_id'] in used_as_pred:
            continue
        i0 = idx[ous[0].k]
        cont = next((cid for cid, us in containers.items() if any(u.k == ous[0].k for u in us)), None)
        lo, hi = 0, len(toks)
        if cont:
            us = containers[cont]
            lo, hi = idx[us[0].k], idx[us[-1].k] + 1
        else:
            from .algebra import clause_start
            for j in range(i0, -1, -1):
                if toks[j].ui == 0 and (toks[j].conj or clause_start(a, toks[j].wi)) or j == 0:
                    lo = j
                    break
            hi = frame_end(i0)
        hosts = []
        for j in range(lo, hi):
            h = toks[j]
            if h.k in span_of and span_of[h.k] == hk or h.enclitic or h.conj:
                continue
            kind = None
            if h.pos == 'فعل' and h.pos_st == 'مثبت' and 'operator' not in h.feats:
                kind = 'فعل'
            elif h.feats.get('derivation', {}).get('v') in ('اسم فاعل', 'اسم مفعول', 'مصدر') and h.feats['derivation'].get('st') == 'مثبت':
                kind = h.feats['derivation']['v']
            elif 'elative' in h.feats:
                kind = 'أَفْعَل (تفضيلٌ مرشّح)'
            elif 'derivation_candidates' in h.feats or (h.feats.get('pattern') or {}).get('st') == 'مثبت':
                kind = 'وصفٌ محتمل (قالب)'
            if kind:
                hosts.append(dict(host=h.uid, host_text=h.text, host_position=h.loc, host_kind=kind, status=DEFERRED,
                                  reason='إطار تعلّق المضيف بهذا الحرف أو الظرف غير مسجَّل في المشروع (لا جرد أطر)'))
        pv = toks[i0 - 1] if i0 > 0 else None
        if pv is not None and pv.nounish() and pv.definite()[0] is False and span_of.get(pv.k) != hk:
            hosts.append(dict(host=pv.uid, host_text=pv.text, host_position=pv.loc, host_kind='نعتٌ للنكرة قبله (متعلّقٌ بمحذوف)',
                              status=DEFERRED, reason='شبه الجملة بعد نكرة تحتمل الوصف؛ والمحذوف لا يُكتب ولا يُعيَّن لفظه'))
        # A02 v1 (مقترحة): شبه الجملة أو الظرف بين طرفي نواةٍ مرخَّصة (N01)، قبل الخبر لا بعده، والإطار خالٍ من فعلٍ ولو محتمل،
        # والخبر وصفٌ هو المضيف الوحيد الذي يولّده A01: تتعلّق به (وَٱللَّهُ بِكُلِّ شَيۡءٍ عَلِيمٌ، وَهُوَ عِندَ ٱللَّهِ عَظِيمٌ).
        # والتقدّم على الخبر مانعٌ مكتوب من وجه النعت (النعت يتلو منعوته)؛ وما بعد الخبر يبقى في A01 لأن وجه النعت فيه قائمٌ بلا مانع
        nuc = next((n for n in nuclei if n['lo'] <= i0 < n['hi']), None)
        uidx = {t.uid: n for n, t in enumerate(toks)}
        pre_p = nuc is not None and uidx[nuc['s'].uid] < i0 and uidx[ous[-1].uid] < uidx[nuc['p'].uid]
        if nuc is not None and not cont and pre_p:
            frame_verbs = [toks[j] for j in range(nuc['lo'], nuc['hi'])
                           if toks[j].pos == 'فعل' or 'فعل' in ((toks[j].feats.get('pos') or {}).get('alt') or []) and
                           not toks[j].nounish() and toks[j].k not in span_of]
            # ما أُثبتت اسميته بنفي البدائل (E01)، وأعضاء شبه الجملة المرخَّصة (عِنْدَ)، ليست أفعالاً محتملة
            others = [h for h in hosts if h['host'] != nuc['p'].uid and nuc['lo'] <= uidx[h['host']] < nuc['hi']]
            p_is_host = any(h['host'] == nuc['p'].uid for h in hosts) or bool(nuc['p'].elative_proof())
            pf = nuc['p'].feats
            # الخبر وصفٌ بدليله: اسم فاعلٍ أو مفعولٍ مثبت، أو مرشّحات اشتقاقٍ وصفي (فَعِيل)، أو أَفْعَل بـE01؛ لا قالبٌ اسمي وحده (خِزْيٌ) ولا مصدر
            p_wasf = (pf.get('derivation') or {}).get('v') in ('اسم فاعل', 'اسم مفعول') and pf['derivation'].get('st') == 'مثبت' or \
                'derivation_candidates' in pf or bool(nuc['p'].elative_proof())
            if not frame_verbs and not others and p_is_host and p_wasf:
                pr = nuc['p']
                R.append(_rec(ref, 'ATTACH', 'A02', {'oblique': ous[0], 'host': pr}, {'oblique': ous, 'host': [pr]}, LICENSED,
                              f'شبه الجملة بين طرفي النواة المرخَّصة قبل الخبر، ولا فعل في الإطار، والخبر الوصف «{pr.text}» مضيفها الوحيد',
                              premises=[nuc['rec']['relation_id'], orec['relation_id'],
                                        f'الإطار {toks[nuc["lo"]].loc}–{toks[nuc["hi"] - 1].loc}: لا فعل ولا فعل محتمل',
                                        f'مضيفو A01 في الإطار: «{pr.text}» وحده'] + ([pr.elative_proof()] if pr.elative_proof() else []),
                              checked=['فعلٌ في الإطار (ولو محتمل)', 'وصفٌ آخر في الإطار', 'حدّ حاوية',
                                       'وجه النعت: شبه الجملة قبل الخبر، والنعت لا يتقدّم منعوته'],
                              alternatives=['شبه الجملة خبرٌ أول وتعدّد الخبر: خارج تغطية v1 (مؤجَّل لا مرفوض)',
                                            'شبه الجملة حالٌ مقدَّمة من الخبر النكرة: خارج تغطية v1 (مؤجَّل لا مرفوض)'] +
                              [dict(h, status=DEFERRED, reason='خارج إطار النواة: لا يُعبر إليه في A02') for h in hosts
                               if h['host'] != pr.uid],
                              search_status=SEARCH_COMPLETE, search_scope=dict(rule='A02 v1', frame=[toks[nuc['lo']].loc, toks[nuc['hi'] - 1].loc]),
                              edges=[('ATTACH', ous[0].uid, pr.uid)]))
                continue
        R.append(_rec(ref, 'ATTACH', 'A01', {'oblique': ous[0]}, {'oblique': ous}, DEFERRED,
                      ('لا مضيف ممكن في الإطار' if not hosts else f'{len(hosts)} مضيفاً ممكناً، ولا إطار تعلّقٍ مثبت لأيٍّ منها') +
                      '؛ والبحث غير مكتمل: لا جرد لأطر التعلّق',
                      premises=[orec['relation_id']], alternatives=hosts, container=cont, search_status=SEARCH_INCOMPLETE,
                      search_scope=dict(frame=[toks[lo].loc, toks[hi - 1].loc] if hi > lo else [], container=cont)))
    # أدوار العمل من العلاقات المرخَّصة وحدها (لا من المؤجَّل): الابتداء، والخبر، وخبر الناسخ
    by_uid = {t.uid: t for t in toks}
    for rec in R:
        if rec['status'] != LICENSED:
            continue
        hd = rec['heads']
        if rec['type'] in ('PREDICATION', 'PREDICATIVE_PP') and hd.get('subject') in by_uid:
            by_uid[hd['subject']].roles.append(dict(src='ibtida', expected='رفع', rid=rec['relation_id']))
        if rec['type'] == 'PREDICATION' and hd.get('predicate') in by_uid:
            by_uid[hd['predicate']].roles.append(dict(src='khabar', expected='رفع', rid=rec['relation_id'],
                                                      of=by_uid[hd['subject']].text))
        if rec['type'] == 'ADVP' and hd.get('complement') in by_uid:
            by_uid[hd['complement']].roles.append(dict(src='idafa', expected='جر', rid=rec['relation_id'],
                                                       of=by_uid[hd['adverb']].text))
        if rec['type'] == 'NASIKH' and hd.get('khabar') in by_uid and rec.get('members', {}).get('khabar') == [hd['khabar']]:
            kt = by_uid[hd['khabar']]
            if kt.k not in span_of:
                kt.roles.append(dict(src='nasikh', expected='نصب' if rec.get('nasikh_group') == NASIKH_KANA else 'رفع',
                                     rid=rec['relation_id'], of=by_uid[hd['nasikh']].text))
    return dict(records=R, tokens=[(t.uid, t.loc, t.text) for t in toks],
                axes={t.uid: t.axes(toks[i + 1] if i + 1 < len(toks) else None) for i, t in enumerate(toks)})


def check_inflection(axes, tokens=None):
    """فاحصٌ مستقل لمحور الإعراب، لا يستدعي قارئ العلامة: → [الخلل].
    ١ الهوية: السجل لوحدته (uid والنص). ٢ العبارة تُفكَّك وتُطابَق بمقتضى العامل المسجَّل وبالعلامة المسجَّلة.
    ٣ العلامة تُقرأ ثانيةً من النص نفسه بقراءةٍ مستقلة (الحرف والحركة على الآخر). ٤ موانع: فعلٌ مجرور، أو فعلٌ في محلّ،
    أو عبارة إعرابٍ بلا اتفاق، أو قدرة عاملٍ لا تشمل الحالة"""
    txt = {u: x for u, _, x in tokens} if tokens else {}
    MARK_CH = {'الكسرة': {KASRA, KASRATAN}, 'الفتحة': {FATHA, FATHATAN}, 'الضمة': {DAMMA, DAMMATAN}, 'السكون': {SUKUN}}
    bad = []
    for uid, ax in axes.items():
        inf = ax.get('inflection') or {}
        if inf.get('uid') not in (None, uid):
            bad.append(f'{uid}: سجل الإعراب لوحدةٍ أخرى ({inf.get("uid")})')
        if txt and inf.get('text') is not None and inf.get('text') != txt.get(uid):
            bad.append(f'{uid}: نص السجل «{inf.get("text")}» غير نص الوحدة «{txt.get(uid)}»')
        st, g, mk = inf.get('statement'), inf.get('governor') or {}, inf.get('mark')
        exp = g.get('expected')
        if g.get('target_uid') not in (None, uid):
            bad.append(f'{uid}: العامل معمولُه وحدةٌ أخرى ({g.get("target_uid")})')
        if g.get('capacity') and exp not in g['capacity']:
            if inf.get('agreement') != 'CONFLICT':
                bad.append(f'{uid}: قدرة «{g.get("operator")}» {g["capacity"]} لا تشمل «{exp}» ولم يُسجَّل تعارض')
        if inf.get('agreement') == 'AGREE':
            if inf.get('mark_kind') == 'محلّي':
                if not st or f'في محلّ {exp}' not in st:
                    bad.append(f'{uid}: العبارة «{st}» لا تذكر المحلّ «{exp}»')
                if ax.get('word_class', (None,))[0] == 'فعل':
                    bad.append(f'{uid}: فعلٌ في محلّ إعراب')
            else:
                if not st or STATE_ADJ.get(exp, '#') not in st or not mk or mk[0].split(' ')[0] not in st:
                    bad.append(f'{uid}: العبارة «{st}» لا توافق العامل ({exp}) أو العلامة ({mk and mk[0]})')
                if any(w in (st or '') for w in STATE_ADJ.values() if w != STATE_ADJ.get(exp)):
                    bad.append(f'{uid}: العبارة تذكر حالةً غير مقتضى العامل')
                tl = letters(txt.get(uid) or inf.get('text') or '')
                if tl and mk:
                    nm = mk[0]
                    if nm in MARK_CH and not tl[-1][1] & MARK_CH[nm] and not (len(tl) > 1 and nm == 'الفتحة' and tl[-1][0] == 'ا'
                                                                           and tl[-2][1] & {FATHATAN}):
                        bad.append(f'{uid}: العلامة «{nm}» غير مكتوبة على آخر «{txt.get(uid) or inf.get("text")}»')
                    if nm == 'الياء' and 'ي' not in ''.join(c for c, _ in tl[-2:]):
                        bad.append(f'{uid}: العلامة «الياء» ولا ياء في الآخر')
                    if nm == 'حذف النون' and tl[-1][0] == 'ن':
                        bad.append(f'{uid}: «حذف النون» والنون مكتوبة')
                    if nm == 'ثبوت النون' and tl[-1][0] != 'ن':
                        bad.append(f'{uid}: «ثبوت النون» ولا نون')
            if g.get('kind') == 'عامل' and g.get('observed') not in (exp, None, 'محلاً') and \
                    not (g.get('observed') == 'حذف النون' and exp in ('نصب', 'جزم')) and \
                    not (g.get('observed') in ('جر أو نصب', 'نصب أو جر') and exp in ('جر', 'نصب')):
                bad.append(f'{uid}: المشاهَد في المرحلة ١١ «{g.get("observed")}» يخالف المقتضى «{exp}» مع AGREE')
            if ax.get('word_class', (None,))[0] == 'فعل' and exp == 'جر' or 'فعل' in (st or '') and 'مجرور' in (st or ''):
                bad.append(f'{uid}: فعلٌ مجرور')
        elif st and any(w in st for w in STATE_ADJ.values()) and 'محلّ' not in st:
            bad.append(f'{uid}: عبارة إعرابٍ بلا اتفاق ({inf.get("agreement")})')
    return bad


def check_records(records, tokens):
    """فاحصٌ بنيوي مستقل: → [الخلل]. الرأس من طرفه، والوحدات موجودةٌ ومواضعها توافقها، والمعرّفات فريدة،
    والمقبول له مقدّمات، والمقدّمات المشيرة إلى علاقاتٍ موجودةٌ بلا دوران، وأعضاء الحاوية داخل امتدادها"""
    errs = []
    loc = {u: l for u, l, _ in tokens}
    ids = {}
    for r in records:
        if r['relation_id'] in ids:
            errs.append(f"معرّفٌ مكرَّر: {r['relation_id']}")
        ids[r['relation_id']] = r
    for r in records:
        rid = r['relation_id']
        for role, h in r['heads'].items():
            if h not in r['members'].get(role, []):
                errs.append(f'{rid}: الرأس «{role}» ليس من أعضاء طرفه')
        for role, us in r['members'].items():
            for u, p in zip(us, r['positions'].get(role, [])):
                if u not in loc:
                    errs.append(f'{rid}: وحدةٌ غير موجودة {u}')
                elif loc[u] != p:
                    errs.append(f'{rid}: موضع {u} المسجَّل {p} لا يوافق المصدر {loc[u]}')
        if r['status'] == LICENSED and not r['premises']:
            errs.append(f'{rid}: مرخَّصٌ بلا مقدّمات')
        if r.get('container_id'):
            c = ids.get(r['container_id'])
            if c is None:
                errs.append(f'{rid}: حاويةٌ غير موجودة')
            else:
                ext = set(c.get('extent') or [])
                for us in r['members'].values():
                    for u in us:
                        if u not in ext:
                            errs.append(f'{rid}: العضو {u} خارج امتداد حاويته')
    # الدوران في المقدّمات: كل مقدّمةٍ هي معرّف علاقة يجب أن تنتهي إلى حقائق مصدرية
    graph = {r['relation_id']: [p for p in r['premises'] if p in ids] for r in records}
    state = {}

    def dfs(n, stack):
        if state.get(n) == 1:
            errs.append('برهانٌ دائري: ' + ' ← '.join(stack + [n]))
            return
        if state.get(n) == 2:
            return
        state[n] = 1
        for m in graph.get(n, []):
            dfs(m, stack + [n])
        state[n] = 2
    for n in graph:
        dfs(n, [])
    for r in records:
        if r['status'] == LICENSED and r['premises'] and all(p in ids for p in r['premises']):
            errs.append(f"{r['relation_id']}: مقدّماته كلها علاقاتٌ بلا حقيقةٍ مصدرية مستقلة")
    return errs
