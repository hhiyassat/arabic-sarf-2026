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
COORD_PARTICLES = ('ثُمَّ', 'أَوْ', 'أَمْ', 'بَلْ', 'لَكِنْ', 'لَكِنَّ', 'حَتَّى')
REL_SPECIFIC = ('الَّذِي', 'الَّتِي', 'الَّذِينَ', 'اللَّذَانِ', 'اللَّتَانِ', 'اللَّذَيْنِ', 'اللَّتَيْنِ', 'اللَّاتِي', 'اللَّائِي', 'اللَّٰتِي')
REL_AGR = {'الَّذِي': (3, 'singular', 'masc'), 'الَّتِي': (3, 'singular', 'fem'), 'الَّذِينَ': (3, 'plural', 'masc')}


def _voice_faces(text):
    """F02 (مقترحة): أوجه البناء للمعلوم والمجهول في المضارع، كلٌّ بتحقيقه للمكتوب (حرفاً وحركة)، لا بالافتراض.
    يُفَالُّ (المضعّف بعد الألف): يُفَاعِلُ ويُفَاعَلُ يُدغمان فتخفى الحركة الفارقة ← الوجهان يحقّقان المكتوب.
    يُفَالُ (الأجوف): المجهول في الثلاثي والمزيد بالهمزة؛ والمعلوم يَفُولُ/يَفِيلُ/يَفَالُ بفتح حرف المضارعة، أو يُفِيلُ بالياء ← لا يحقّقه.
    → [{id, voice, status, why}] أو None إن لم يكن الرسم من هذين"""
    marks = set(chr(c) for c in range(0x064B, 0x0653)) | {'\u0670'}
    g = []
    for ch in text:
        if ch in marks and g:
            g[-1][1].add(ch)
        elif ch not in marks:
            g.append([ch, set()])
    if len(g) != 4 or g[0][0] not in 'يتنأ' or DAMMA not in g[0][1] or FATHA not in g[1][1] or g[2][0] not in 'اآ':
        return None
    if SHADDA in g[3][1]:
        return [dict(id='V1', voice='معلوم', status=LICENSED,
                     why='يُفَاعِلُ من المضعّف (كسرة العين) يُدغم فيُكتب «يُفَالُّ»: يحقّق المكتوب، والحركة الفارقة لا تظهر'),
                dict(id='V2', voice='مجهول', status=LICENSED,
                     why='يُفَاعَلُ من المضعّف (فتحة العين) يُدغم فيُكتب «يُفَالُّ»: يحقّق المكتوب، والحركة الفارقة لا تظهر')]
    return [dict(id='V1', voice='معلوم', status=REJECTED,
                 why='المعلوم من الأجوف يَفُولُ أو يَفِيلُ أو يَفَالُ بفتح حرف المضارعة (الثلاثي)، أو يُفِيلُ بالياء (المزيد بالهمزة): '
                     'لا يحقّق المكتوب «يُفَالُ» (ضمة حرف المضارعة، وفتحة الفاء، وألفٌ بعدها)'),
            dict(id='V2', voice='مجهول', status=LICENSED,
                 why='يُفَالُ مجهول الأجوف في الثلاثي والمزيد بالهمزة: يحقّق المكتوب حرفاً وحركة')]


def _pron_ar(d):
    """ضمير الصيغة بالعربية: الشخص والعدد والجنس (والقيمة غير المعيَّنة «—»)."""
    if not isinstance(d, dict):
        return str(d)
    P = {1: 'متكلم', 2: 'مخاطب', 3: 'غائب'}
    N = {'singular': 'مفرد', 'dual': 'مثنى', 'plural': 'جمع'}
    G = {'masc': 'مذكر', 'fem': 'مؤنث', 'common': 'مشترك'}
    return '، '.join(m.get(d.get(k), '—' if d.get(k) is None else str(d.get(k)))
                     for k, m in (('person', P), ('number', N), ('gender', G)))


def subject_pronoun_written(sig, tense):
    """S01.p: هل ضمير الرفع في هذه الصيغة مكتوبٌ متصل، أم مستتر؟ → ('WRITTEN'|'HIDDEN_OBLIGATORY'|'HIDDEN_OR_OVERT'، السند)
    المضارع: المكتوب ألف الاثنين وواو الجماعة وياء المخاطبة ونون النسوة وحدها؛ وحرف المضارعة ليس ضميراً. فالمتكلم (أَفعل، نَفعل)
    والمخاطب المفرد المذكر (تَفعل) مستترٌ وجوباً، والغائب المفرد (يَفعل، تَفعل للغائبة) ظاهرٌ أو مستترٌ جوازاً.
    الأمر: المفرد المذكر مستترٌ وجوباً، وما سواه مكتوب. الماضي: الغائب المفرد (فَعَلَ، فَعَلَتْ) ظاهرٌ أو مستتر، وما سواه مكتوب (تُ، نا…).
    السند: الألفية «ومن ضمير الرفع ما يستتر * كافعلْ أوافقْ نغتبطْ إذ تشكرُ» وشرح ابن عقيل عليه (المستتر وجوباً في الأمر للواحد،
    والمضارع المبدوء بالهمزة والنون وتاء الخطاب للواحد)؛ وباب الفاعل في شرح قطر الندى."""
    if not isinstance(sig, dict):
        return None, None
    p_, n_, g_ = sig.get('person'), sig.get('number'), sig.get('gender')
    SANAD = 'الألفية وشرح ابن عقيل: «ومن ضمير الرفع ما يستتر كافعلْ أوافقْ نغتبطْ إذ تشكرُ»'
    if tense == 'مضارع':
        if p_ == 1:
            return 'HIDDEN_OBLIGATORY', SANAD + ' — حرف المضارعة (أ، ن) ليس ضميراً'
        if p_ == 2 and n_ == 'singular' and g_ == 'masc':
            return 'HIDDEN_OBLIGATORY', SANAD + ' — تاء الخطاب للواحد'
        if p_ == 3 and n_ == 'singular':
            return 'HIDDEN_OR_OVERT', 'الغائب المفرد: فاعله ظاهرٌ بعده أو مستترٌ جوازاً (باب الفاعل)'
        if n_ in ('dual', 'plural') or (p_ == 2 and g_ == 'fem'):
            return 'WRITTEN', 'ألف الاثنين أو واو الجماعة أو ياء المخاطبة أو نون النسوة: ضميرٌ متصل مكتوب'
        return None, None
    if tense == 'أمر':
        if n_ == 'singular' and g_ == 'masc':
            return 'HIDDEN_OBLIGATORY', SANAD + ' — الأمر للواحد'
        return ('WRITTEN', 'ضمير الأمر المتصل المكتوب (ياء المخاطبة، ألف الاثنين، واو الجماعة، نون النسوة)') if n_ else (None, None)
    if tense == 'ماضٍ':
        if p_ == 3 and n_ == 'singular':
            return 'HIDDEN_OR_OVERT', 'الغائب المفرد في الماضي: فاعله ظاهرٌ أو مستترٌ جوازاً'
        return ('WRITTEN', 'ضمير الرفع المتصل المكتوب في الماضي (تُ، تَ، تِ، نَا، تُمْ، وا، ا، نَ…)') if p_ else (None, None)
    return None, None


def tense_safe_for_isnad(v, tf, governed=()):
    """مانع S01.p/S01.f: مضارع تَفَعَّلَ وتَفَاعَلَ بحذف إحدى التاءين يُكتب كماضيهما (تَشَٰبَهَ، تَوَلَّوۡا).
    الالتباس يُثبت في المكتوب نفسه (مراجعة 046): تاءٌ واحدة في أوله (لا «تَتَ…»)، ولا عاملَ مقبولٌ فيه يحسم المضارعة (لَن تَتَعَلَّمَ
    محفوظةُ التاءين، و«لَن» دليلٌ مستقل) → (آمن، السبب)"""
    P = ((getattr(v, 'G', None) and v.G.Theta.get('P')) or '')
    lt = [L for L, _m in letters(v.text)]
    single_ta = lt[:1] == ['ت'] and lt[1:2] != ['ت']
    by_operator = getattr(v, 'k', None) in (governed or ())
    if tf.get('v') == 'مضارع' and P in ('V', 'VI') and single_ta and not by_operator:
        return False, (f'«{v.text}» على {P} أوله تاء: يلتبس مضارعه المحذوف إحدى تاءيه بالماضي كتابةً، '
                       'فلا يُرخَّص طرف الإسناد بالصيغة حتى يُحسم الزمن (TENSE_V_VI_AMBIGUOUS)')
    return True, None


IMPLICIT_KEYS = ('implicit_id', 'implicit', 'source_span', 'owner_verb_id', 'syntactic_face_id', 'person', 'number', 'gender', 'role',
                 'licensing_rule_id', 'evidence_ids', 'reference_status')


def implicit_subject(owner, face_id, sig, role, rule, evidence):
    """المستتر وحدةٌ بنيوية غير مكتوبة بهويتها (مراجعة 046): مرتبطةٌ بالفعل والوجه، بخصائصها ودليل ترخيصها وحالة مرجعها، ولا مجال لها"""
    sig = sig or {}
    return dict(implicit_id=f'{owner}#IMPLICIT_SUBJECT@{face_id}', implicit=True, source_span=None, owner_verb_id=owner,
                syntactic_face_id=face_id, person=sig.get('person'), number=sig.get('number'), gender=sig.get('gender'), role=role,
                licensing_rule_id=rule, evidence_ids=[e for e in evidence if e], reference_status='UNRESOLVED')


def validate_implicit(x, owner=None, face_id=None):
    """→ (سليم، السبب): الحقول كلها، ولا مجال مصدر، ومالكٌ ووجهٌ مطابقان، وقاعدةٌ ودليل"""
    if not isinstance(x, dict):
        return False, 'لا سجلّ للمستتر'
    miss = [k for k in IMPLICIT_KEYS if k not in x]
    if miss:
        return False, 'حقولٌ ناقصة: ' + '، '.join(miss)
    if x['source_span'] is not None or not x['implicit']:
        return False, 'للمستتر مجالٌ مصدري أو وُسم مكتوباً'
    if owner and x['owner_verb_id'] != owner or face_id and x['syntactic_face_id'] != face_id:
        return False, 'المستتر لفعلٍ آخر أو لوجهٍ آخر'
    if not x['licensing_rule_id'] or not x['evidence_ids']:
        return False, 'بلا قاعدة ترخيصٍ أو دليل'
    return True, None


def verify_subject_face(x, tense, owner=None):
    """فاحص الوجه (مراجعة 046): الوجه لا يُعدّ مستوفى بحالته المكتوبة؛ يُتحقّق من قاعدته ومقدّماتها: نوع الطرف يوافق حكم الصيغة
    (S01.p)، والظاهر وحدةٌ معيَّنة، والمستتر سجلٌّ سليم، ولا عائقٌ قائم → (سليم، السبب)"""
    if x.get('status') != LICENSED:
        return False, 'الوجه غير مرخَّص'
    if x.get('blocked_by'):
        return False, f"عائق الوجه قائم ({x['blocked_by']})"
    kw, _ = subject_pronoun_written(x.get('signature'), tense)
    kind = x.get('kind') or ''
    if kind == 'ضمير متصل مكتوب':
        good = kw == 'WRITTEN'
    elif 'وجوباً' in kind:
        good = kw == 'HIDDEN_OBLIGATORY'
    elif 'جوازاً' in kind:
        good = kw == 'HIDDEN_OR_OVERT' and x.get('rule') == 'S01.h'
    elif kind == 'اسم ظاهر':
        good = kw == 'HIDDEN_OR_OVERT' and bool(x.get('unit'))
    else:
        good = False
    if not good:
        return False, f'نوع الطرف «{kind}» لا يوافق حكم الصيغة ({kw}) أو مقدّمته ناقصة'
    if 'مستتر' in kind:
        return validate_implicit(x.get('implicit_subject'), owner, x.get('face_id'))
    return True, None


def _join_ar(x):
    """قائمة قيمٍ نصية بفاصلةٍ عربية بدل تمثيل بايثون."""
    return '، '.join(str(i) for i in x) if isinstance(x, (list, tuple)) else str(x)


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
        self.mabni_state = None                         # حالة المبني بلا دور: NO_MAHALL، MAHALL_UNRESOLVED، ROLE_RULE_NOT_IMPLEMENTED، EVIDENCE_NOT_ADOPTED
        self.usage = None                               # استعمال العامل في هذا التحليل (للوحدة العاملة)
        self.frame_cands = None                         # مرشّحات إطار الفعل القائمة والممنوعة (F01)
        self.voice_faces = None                         # أوجه البناء بتحقيقها للمكتوب (F02)

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
        """محاور مستقلة لا يُغني أحدها عن الآخر، كلٌّ بدليله أو «غير محسوم»:
        صنف الكلمة، والبناء والإعراب، والدور النحوي (بعلاقته وحالة دليلها)، والحالة أو المحلّ، والحماية (نطاقها وسببها ومصدرها)،
        والعمل (واستعمال العامل في هذا التحليل). فـ«مبني» وصف البناء، وAGREE وUNGOVERNED وصفا العلاقة: لا يتنافسان على محورٍ واحد"""
        wc = ('اسم', self.noun_ev if (self.pos == 'اسم' and self.pos_st == 'مثبت' and not self.shape_only or self.divine) and self.noun_ev else
                   'لفظ الجلالة' if self.divine else 'اسمٌ ذهبي' if self.golden else self.elative_proof()) \
            if self.nounish() else \
            ('اسم', f'ملف المبنيات: {CAT_AR.get(self.mcat, self.mcat)} ({self.mcat})') if self.mcat in ('separate_pronoun', 'demonstrative', 'relative', 'attached_pronoun') else \
            ('اسم', f'ظرفٌ من جرد المشروع (sarf.algebra.ZURUF_V) في علاقة P02 مرخَّصة: الظرف اسم') if self.adverb == 'P02:LICENSED' else \
            ('اسم', '«أيّ» منادى في V02 (و«ها» حرف تنبيه في الوحدة نفسها)') if any(r['src'] == 'munada' for r in self.roles) else \
            ('حرف + اسم', 'وحدةٌ مكتوبة مندمجة (sarf.protected.MERGED): حرف جرٍّ واسمٌ مبني، P03') if any(r['src'] == 'merged_pp' for r in self.roles) else \
            ('فعل', 'فعلٌ في كل المرشّحات القائمة (F01): ' + '، '.join(f"{c_['id']} {c_['tense']} {c_['voice']}" for c_ in self.frame_cands['live']) +
             ('؛ وصيغة المرحلة ١٣ «' + str((self.feats.get('pos') or {}).get('ev')) + '» من وجهٍ ممنوع' if self.frame_cands['rejected'] else '')) \
            if self.pos == 'فعل' and self.pos_st == 'مثبت' and self.frame_cands else \
            ('فعل', (self.feats.get('pos') or {}).get('ev')) if self.pos == 'فعل' and self.pos_st == 'مثبت' else \
            ('حرف', f'ملف المبنيات: {CAT_AR.get(self.mcat, self.mcat)} ({self.mcat})') if self.mcat == 'particle' else \
            ('حرف', (self.mabni_state or {}).get('text')) if (self.mabni_state or {}).get('code') == 'NO_MAHALL' and self.pos != 'فعل' else \
            (None, 'الاسمية من شكل التنوين وحده: غير محسوم في هذه الطبقة (العقد T19)؛ وسمة المرحلة ١٣ «اسم» بدليل التنوين '
                   'قديمةٌ (LEGACY) لم تُغيَّر، وهذا المحور يصحّحها إلى التأجيل' if self.shape_only else 'غير محسوم')
        inf = _inflection(self, nxt)
        th = self.G.Theta
        prot = th.get('protected') or {}
        if prot.get('cls'):
            pr = (prot['cls'], f"الجرد المعتمد: «{prot.get('identity')}» (root_status={th.get('root_status')})")
            src = 'sarf/protected.py: ' + ('GOLDEN' if prot.get('cls') == 'اسم ذهبي' else 'MERGED أو VERBAL أو جرد العوامل')
        elif self.divine or th.get('lex') == 'لفظ الجلالة':
            pr, src = ('لفظ الجلالة', 'sarf/divine.py: لا جذر'), 'sarf/divine.py'
        elif self.golden:
            pr, src = ('اسم ذهبي', 'الجرد GOLDEN: لا جذر'), 'sarf/protected.py: GOLDEN'
        elif (self.lex or '') in ('مبني', 'عامل', 'مبني+عامل'):
            pr = ('مبني أو عامل' if self.lex != 'عامل' else 'عامل من العوامل المائة',
                  f'وحدةٌ معجمية مغلقة (lex={self.lex}) قبل توليد الجذر: CONSTITUTIONAL_PROTECTED_CLASS')
            src = {'مبني': 'lexicon/mabniyat_lexicon.jsonl', 'عامل': 'operators_catalog.jsonl'}.get(
                self.lex, 'lexicon/mabniyat_lexicon.jsonl وoperators_catalog.jsonl')
        else:
            pr, src = (None, 'غير محمية: يُستخرج جذرها'), None
        op = (self.lex or '').startswith('عامل') or 'عامل' in (self.lex or '')
        g = inf.get('governor') or {}
        role = (g.get('role_name'), (f"{g.get('role_rule') or ''} {g.get('relation_id') or ''}".strip() or g.get('relation')) +
                (f"؛ {g['face_note']}" if g.get('face_note') else '')) \
            if g.get('role_name') else (None, (self.mabni_state or {}).get('text') or
                                        ('لا دور نحوي مرخَّص في هذا التحليل' if inf['build'][0] else 'غير محسوم'))
        st = inf.get('state') or (None, '')
        mk = inf.get('mark_kind')
        case_axis = (st[0], 'محلّي' if mk == 'محلّي' else 'تقديري' if mk == 'مقدّرة' else 'لفظي') if st[0] and \
            inf['agreement'] == 'AGREE' else \
            ('لا محلّ له (غير منطبق)', (self.mabni_state or {}).get('text') or 'الفعل المبني وحده لا محلّ له من الإعراب') \
            if (self.mabni_state or {}).get('code') == 'NO_MAHALL' or self.pos == 'فعل' and inf['build'][0] == 'مبني' else \
            (None, (self.mabni_state or {}).get('text') or st[1])
        ident = dict(analysis_id=f'{self.uid}@{VERSION}', unit=self.uid, loc=self.loc, text=self.text,
                     slots=[s_['index'] for s_ in self.slots],
                     stage11=[f"A{self.loc.rsplit(':', 1)[0]}:{self.wi + 1}.{s_['index']}" for s_ in self.slots],
                     parts=[p_['part_id'] for p_ in (getattr(self, 'parts', None) or [])],
                     morph_candidate=getattr(self, 'morph_candidate', None))
        return dict(identity=ident, word_class=wc, build=inf['build'], inflection=inf,
                    role=role, role_status=g.get('relation_status') if g.get('role_name') else None,
                    case_axis=case_axis, mabni_state=self.mabni_state,
                    protection=(pr[0], pr[1] + ('؛ والحماية من الجذر لا تمنع التحليل النحوي' if pr[0] else '')),
                    protection_detail=dict(scope='لا جذر ولا وزن؛ والهوية والرسم محفوظان؛ ولا تُمنع الوظيفة النحوية' if pr[0] else None,
                                           reason='CONSTITUTIONAL_PROTECTED_CLASS' if pr[0] else None, source=src, cls=pr[0]),
                    operator=(True, f'خانة {self.lex}') if op else (False, '—'), operator_usage=self.usage,
                    parts=getattr(self, 'parts', None))

    def definite(self):
        """→ (معرفة؟، الدليل) من السمات القائمة؛ وNone إن لم يثبت"""
        if self.divine:
            return True, 'لفظ الجلالة (علم)'
        if self.golden:
            return True, 'اسمٌ ذهبي في الجرد المعتمد (علم)'
        if self.mcat in ('separate_pronoun', 'demonstrative'):
            return True, f'ملف المبنيات: {CAT_AR.get(self.mcat, self.mcat)} ({self.mcat})'
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
            # مصدر العلامة واحد: قارئ المحور نفسه (_written_mark)؛ فإن خالفت قراءتُه الحالةَ المسجَّلة فالرفع غير مثبت والتعارض معلن
            nm, cs, _ = _written_mark(self)
            if 'رفع' in cs:
                return True, f'الرفع مكتوب ({nm})'
            return None, (f'تعارض قارئين: الحالة المسجَّلة «رفع» (sarf.algebra.word_case)، والعلامة المقروءة بالصنف «{nm}» تدلّ على '
                          f'{"، ".join(sorted(cs))}: الرفع غير مثبت' if cs else
                          f'الحالة المسجَّلة «رفع»، والعلامة المقروءة بالصنف «{nm or "—"}» لا تعيّن حالة: الرفع غير مثبت')
        if self.case in ('نصب', 'جر', 'نصب أو جر', 'جر أو نصب'):
            return False, f'العلامة المكتوبة {self.case}'
        if self.lex == 'مبني' or self.mcat or self.dkind in ('معرفة: ضمير', 'معرفة: اسم إشارة', 'معرفة: اسم موصول'):
            return None, 'مبنيٌّ: المحلّ يُعيَّن بموقعه'
        return None, 'لا علامة إعرابٍ مكتوبةٌ تدلّ'


STATE_ADJ = {'رفع': 'مرفوع', 'نصب': 'منصوب', 'جر': 'مجرور', 'جزم': 'مجزوم'}
STATE_NOUN = {'رفع': 'رفعه', 'نصب': 'نصبه', 'جر': 'جرّه', 'جزم': 'جزمه'}
_EFFECT = {'جر ما بعده': 'جر', 'نصب الفعل المضارع': 'نصب', 'جزم المضارع': 'جزم'}
def _cases_in(e):
    return {c for c, ws in (('جر', ('جر', 'مجرور')), ('نصب', ('نصب', 'منصوب', 'تنصب', 'ينصب')), ('رفع', ('رفع', 'مرفوع', 'ترفع')),
                            ('جزم', ('جزم', 'مجزوم', 'تجزم'))) if any(w in e for w in ws)}


def _effect_parts(effect):
    """أثر العامل في الجرد مفصولاً من نصّه، بلا استنتاج غير المذكور:
    lafzi: ما يُحدثه لفظاً في معموله؛ mahall_of_complement: محلّ المعمول الأصلي الذي يذكره الجرد (الباء ومن الزائدتان)؛
    mediated: ما يُحدثه بوساطة («بأن مضمرة»)؛ none: لا أثر («لا تؤثر»، «لا تجزم»)"""
    e = effect or ''
    out = dict(lafzi=set(), mahall_of_complement=set(), mediated=set(), none=False)
    if e.startswith('لا '):
        out['none'] = True
        return out
    head, _, tail = e.partition('—')
    if 'مضمرة' in e:
        out['mediated'] = _cases_in(e)
        return out
    out['lafzi'] = _cases_in(head)
    if 'محل' in tail:
        out['mahall_of_complement'] = {'الأصلي'} if 'الأصلي' in tail else (_cases_in(tail) or {'الأصلي'})
    elif 'محل' in head and 'لا محلي' not in head:
        out['mahall_of_complement'] = {'الأصلي'}
    return out


def _caps(effect):
    """القدرة اللفظية وحدها (الأثر المباشر في لفظ المعمول)"""
    return _effect_parts(effect)['lafzi']


def _capacity(o):
    """قدرة العامل عبر معانيه في الجرد: لفظية، ومحلّ معمولٍ أصلي، وبوساطة؛ كلٌّ مجموعةٌ مستقلة"""
    cap = dict(lafzi=set(), mahall_of_complement=set(), mediated=set())
    for x in o.get('meanings') or []:
        pt = _effect_parts(x.get('effect'))
        for k in cap:
            cap[k] |= pt[k]
    return {k: sorted(v) for k, v in cap.items()}


def _mark_dims(name, cap=None):
    """أبعاد وصف العلامة مستقلة: الحامل (حركة، حرف، حذف، سكون)، والظهور (ظاهرة، مقدّرة، غير ظاهرة)، والأصالة (أصلية، فرعية نيابةً)،
    وسبب الفرعية أو التقدير"""
    if not name:
        return None
    if name.startswith('مقدّرة'):
        return dict(carrier='حركة', visibility='مقدّرة', originality='أصلية', reason='التعذّر: الألف لا تقبل الحركة')
    if name.startswith('السكون ('):
        return dict(carrier='سكون', visibility='غير ظاهرة', originality='أصلية',
                    reason='حُرِّك آخره بالكسر لالتقاء الساكنين: الكسرة حركة تخلّص لا علامة')
    if name == 'السكون':
        return dict(carrier='سكون', visibility='ظاهرة', originality='أصلية', reason=None)
    if name in ('الكسرة', 'الفتحة', 'الضمة'):
        sub = (name == 'الكسرة' and cap == 'نصب') or (name == 'الفتحة' and cap == 'جر')
        return dict(carrier='حركة', visibility='ظاهرة', originality='فرعية (نيابة)' if sub else 'أصلية',
                    reason=('جمع المؤنث السالم يُنصب بالكسرة' if name == 'الكسرة' else 'الممنوع من الصرف يُجرّ بالفتحة') if sub else None)
    if name.startswith('حذف'):
        return dict(carrier='حذف', visibility='—', originality='فرعية (نيابة)',
                    reason='الأفعال الخمسة' if 'النون' in name else 'المضارع المعتلّ الآخر')
    if name in ('الألف', 'الواو', 'الياء', 'ثبوت النون'):
        return dict(carrier='حرف', visibility='ظاهرة', originality='فرعية (نيابة)',
                    reason='الأفعال الخمسة' if name == 'ثبوت النون' else 'المثنى أو جمع المذكر السالم')
    return dict(carrier=None, visibility=None, originality=None, reason='العلامة غير معيَّنة')


ROLE_AR = {'ibtida': 'الابتداء', 'khabar': 'الخبرية للمبتدأ', 'nasikh': 'الخبرية للناسخ', 'idafa': 'الإضافة', 'object': 'المفعولية',
           'subject': 'الفاعلية', 'zarf': 'الظرفية', 'voc_follower': 'التبعية في النداء'}
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
        five_ev = f"ضمير الصيغة ({_pron_ar(sv)})"
        if five and tl[0][0] in 'يتأن':
            if L == 'ن' and p[0] in 'اوي' and (FATHA in m or KASRA in m):
                return 'ثبوت النون', frozenset({'رفع'}), f'الأفعال الخمسة ({five_ev}): النون ثابتة'
            if L == 'ا' and p[0] in 'و' or L == 'و' and DAMMA in p[1] or L == 'ا' and FATHA in p[1] or L == 'ي' and KASRA in p[1]:
                return 'حذف النون', frozenset({'نصب', 'جزم'}), f'الأفعال الخمسة ({five_ev}): النون محذوفة'
        if len(R) == 3 and R[2] in 'وي' and L not in 'اويى' and L == R[1] and tl[0][0] in 'يتأن':
            return 'حذف حرف العلة', frozenset({'جزم'}), f'لام الجذر «{R[2]}» محذوفة من آخر المضارع ({R})'
        from .evidence import jazm_faces
        jf = jazm_faces(t.text) if not (len(R) == 3 and R[2] in 'وي') else None
        if jf and jf['rule'] == 'M01.2':
            return 'حذف حرف العلة', frozenset({'جزم'}), 'M01: ' + jf['why']
        if jf and jf['rule'] == 'M01.1' and not (len(R) == 3 and R[1] == R[2]):
            return 'الفتحة', frozenset({'نصب', 'جزم'}), 'M01: ' + jf['why'] + '؛ والفتحة علامة النصب'
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
            known = R or (t.G.Theta.get('protected') or {}).get('identity')   # الصيغة المحمية معروفة الهوية (تَكُونَ ← كَانَ)
            return 'الفتحة', frozenset({'نصب'}), 'الفتحة على الآخر' + ('' if known else
                                                                         '؛ والجذر غير مثبت: إن كانت لامه حرف علة محذوفاً فالفتحة '
                                                                         'حركة العين لا علامة النصب، فلا يُنفى الجزم بها')
        if KASRA in m:
            return 'الكسرة', frozenset(), 'الكسرة لا تكون علامة إعرابٍ في الفعل' + ('' if R else '؛ والجذر غير مثبت: قد تكون اللام محذوفة')
        return None, frozenset(), 'لا علامة على الآخر'
    nf = t.feats.get('number') or {}
    num = nf.get('v') if nf.get('st') == 'مثبت' else None   # العدد المرشّح لا يُقرأ به حرف الإعراب (ٱلۡقُرۡءَانِ ليس مثنى)
    cand = nf.get('v') if nf.get('st') != 'مثبت' else None
    if L == 'ن' and p[0] in 'اوي' and cand in ('dual', 'plural') and (FATHA in m or KASRA in m):
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
    out = dict(uid=t.uid, text=t.text, notes=[], build=(None, 'غير محسوم'), governor=None, state=(None, 'غير محسوم'), mark=None,
               mark_kind=None, cause=None, statement=None, agreement='N/A', conflicts=[],
               note='الاتفاق اتساقٌ بين العامل والعلامة والعبارة، لا إثباتٌ مستقل لوظيفة العامل: '
                    'العامل مقبولٌ في المرحلة ١١ بأدلته، والعلامة تُقرأ هنا من النص بصنف الكلمة')
    tense = (t.feats.get('tense') or {})
    lex = t.lex or ''
    mabni_unit = lex in ('مبني', 'مبني+عامل') or t.mcat is not None or t.enclitic
    mpp = next((r for r in t.roles if r['src'] == 'merged_pp'), None)
    if mpp is not None:
        # P03: الوحدة المكتوبة = حرف جرٍّ + اسمٌ مبني؛ والمحلّ للجزء الثاني، والبناء والدور لكلٍّ من الجزأين
        p0, p1 = mpp['parts']
        out['build'] = ('مبني', f'«{p0}» حرفٌ مبني، و«{p1}» اسمٌ مبني (ملف المبنيات)')
        out['governor'] = dict(kind='عامل', operator=p0, expected='جر', role_name='مجرور بحرف الجر', role_rule='P03',
                               relation_id=mpp['rid'], relation_status=LICENSED, target_uid=t.uid, relation='مباشر',
                               capacity=['جر'], capacity_mediated=[], capacity_source='حرف الجر في الجرد المعتمد (MERGED)')
        out['state'] = ('في محلّ جر', f'«{p1}» مبني في محلّ جر بـ«{p0}» (P03)')
        out['mark_kind'] = 'محلّي'
        out['mark_dims'] = dict(carrier=None, visibility='محلّي', originality=None, reason='المبني لا تظهر عليه علامة إعراب')
        out['cause'] = f'«{p1}» مبني على السكون؛ والحكم إعرابٌ محلّي'
        out['statement'] = (f'«{p0}» حرف جر، و«{p1}» اسم مبني على السكون في محلّ جر بـ«{p0}»، مجرور بحرف الجر'
                            f'؛ ونوعه ({"، ".join(mpp["kinds"])}) غير مختار')
        out['effect'] = dict(lafzi=None, mahalli='جر', relation='مباشر')
        return _finish(out)
    mun = next((r for r in t.roles if r['src'] == 'munada'), None)
    if mun is not None:
        # V02: «أيّ» المنادى في وحدة «أَيُّهَا» مع «ها» التنبيه؛ البناء على الضم وصفُ بناء، والمحلّ بالنداء وصفُ علاقة
        out['build'] = ('مبني', '«أيّ» منادى نكرةٌ مقصودة: مبني على الضم (V02)')
        out['governor'] = dict(kind='النداء', relation_id=mun['rid'], expected='نصب', role_name='منادى', role_rule='V02',
                               relation_status=mun.get('status', LICENSED), target_uid=t.uid, relation='بحرف النداء')
        out['state'] = ('في محلّ نصب', 'مبني على الضم، ومحلّه النصب بالنداء (V02)')
        out['mark_kind'] = 'محلّي'
        out['mark_dims'] = dict(carrier=None, visibility='محلّي', originality=None, reason='المنادى المبني لا تظهر عليه علامة النصب')
        out['cause'] = '«أيّ» مبني على الضم: الضمة حركة بناء لا علامة رفع؛ والحكم إعرابٌ محلّي'
        out['statement'] = '«أيّ» منادى مبني على الضم في محلّ نصب، و«ها» حرف تنبيه'
        out['effect'] = dict(lafzi=None, mahalli='نصب', relation='بحرف النداء')
        return _finish(out)
    # ١ البناء: من نوع الكلمة وزمن الفعل
    opsrc = next((r for r in t.roles if r['src'] == 'operator'), None)
    mood_op = opsrc is not None and opsrc['r'].get('expected') in ('نصب', 'جزم') and \
        (opsrc['r'].get('target') or {}).get('pos') == 'verb'
    if t.pos == 'فعل':
        tv, tst = tense.get('v'), tense.get('st')
        if tst != 'مثبت' and mood_op:
            out['build'] = ('معرب', f'العامل «{opsrc["o"]["operator"]}» مقبولٌ عاملاً في المضارع: المعمول مضارع معرب '
                                    f'(وسمة الزمن في المرحلة ١٣ «{tv}» مرشّحة: تُصالَح بهذا العامل)')
        elif tst != 'مثبت' and getattr(t, 'frame_cands', None):
            fc = t.frame_cands
            out['build'] = (None, 'زمن الفعل غير مثبت: المرشّح القائم ' + '، '.join(
                f"{c_['id']} ({c_['tense']}، {c_['voice']})" for c_ in fc['live']) + (
                '؛ والممنوع: ' + '، '.join(f"{c_['id']} ({c_['tense']})" for c_ in fc['rejected']) if fc['rejected'] else '') +
                ' (F01): البناء يتبعه')
            out['state'] = (None, 'زمن الفعل غير مثبت؛ والمرشّح القائم ' + '، '.join(c_['id'] for c_ in fc['live']))
            out['agreement'] = 'UNVERIFIED'
            return out
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
        out['state'] = (None, (t.mabni_state or {}).get('text') or 'أداةٌ مبنية؛ ومحلّها (إن كان) لا يُعيَّن في هذا المحور')
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
            ms = t.mabni_state or {}
            out['state'] = (None, ms.get('text') or 'مبني: المحلّ يُعيَّن بالعامل أو بدورٍ في علاقة، ولا عامل مثبت فيه ولا دور مرخَّص')
        elif cases:
            out['state'] = (None, f'العلامة المكتوبة «{name}» تحتمل: {"، ".join(sorted(cases))}؛ ولا عامل مقبول ولا دور مرخَّص: لا يُقال')
        else:
            out['state'] = (None, f'{ev}؛ ولا عامل مقبول ولا دور مرخَّص')
        out['agreement'] = 'UNGOVERNED'
        return out
    if src['src'] == 'operator':
        o, r, op = src['o'], src['r'], src['op']
        cap = r.get('expected')
        capd, usage, alts_ = _usage_capacity(o, cap)
        caps = set(capd['lafzi'])
        cap_src = ('الاستعمال المتّسق مع العلاقة المقبولة: ' + '، '.join(f'«{u}»' for u in usage)) if usage else \
            ('المعنى المرفق في المرحلة ١١' if len(o.get('meanings') or []) <= 1 else 'لا معنى مرفقٌ يذكر هذا الأثر')
        if not caps and not capd['mediated'] and cap in _cases_in(o.get('operator_class') or ''):
            caps = {cap}                                # فئة العامل في الجرد تذكر أثره، والمعاني المرفقة لا تذكره
            cap_src = f'فئة العامل «{o.get("operator_class")}»'
            out['notes'] = [f'تعارضٌ داخلي في المرحلة ١١: المعاني المرفقة بالعامل '
                            f'({"، ".join(str(x.get("id")) for x in o.get("meanings") or [])}) لا تذكر «{cap}»، وفئته تذكره']
        g_ = str(o['group'])
        role_name, rule_ = None, None
        pp_ = next((x for x in t.roles if x['src'] == 'pp'), None)
        if g_ == NASIKH_KANA and cap == 'رفع' or g_ == NASIKH_INNA and cap == 'نصب':
            role_name, rule_ = f'اسم «{o["operator"]}»', f'حكم الناسخ في المرحلة ١١ (مج {g_})'
        elif pp_ and cap == 'جر':
            # مكمّل الجار في P01 المرخَّصة: دوره «مجرور بحرف الجر» من العلاقة نفسها (كما في P03)، لا «لا دور»
            role_name, rule_ = 'مجرور بحرف الجر', 'P01'
        out['governor'] = dict(kind='عامل', operator=o['operator'], position=op.loc, group=o['group'], expected=cap,
                               observed=r.get('observed'), consistent=r.get('consistent'), role=r.get('role'),
                               target_uid=t.uid, operator_proof=list((o.get('judgement') or {}).get('proof') or []),
                               capacity=sorted(caps), capacity_source=cap_src,
                               capacity_mahall_of_complement=capd['mahall_of_complement'],
                               capacity_mediated=capd['mediated'], lexical_alternatives=alts_,
                               target_slot=(r.get('target') or {}).get('slot'), target_word=(r.get('target') or {}).get('word_index'),
                               level='محلّي' if r.get('observed') == 'محلاً' else 'لفظي',
                               role_name=role_name, role_rule=rule_, relation_status=LICENSED if role_name else None,
                               **(dict(relation_id=pp_['rid']) if rule_ == 'P01' else {}),
                               relation='مباشر' if cap in caps else
                               'بوساطة (في الجرد)' if cap in capd['mediated'] else 'غير مرخَّص في الجرد')
        gov_txt = f'بـ«{o["operator"]}»' if cap not in capd['mediated'] or cap in caps else \
            f'بـ«أن» مضمرةً بعد «{o["operator"]}» (وساطةٌ في الجرد)'
        obs = r.get('observed')
        obs_cases = {'حذف النون': {'نصب', 'جزم'}, 'جر أو نصب': {'جر', 'نصب'}, 'نصب أو جر': {'جر', 'نصب'}}.get(
            obs, {obs} if obs in STATE_ADJ else None)
        if obs_cases is not None and cap not in obs_cases:
            out['conflicts'].append(f'المرحلة ١١ سجّلت المشاهَد «{obs}» والمقتضى «{cap}»')
        if cap and (caps or capd['mediated']) and cap not in caps and cap not in capd['mediated']:
            out['conflicts'].append(f'قدرة العامل في الجرد {sorted(caps)} لا تشمل ما سُجّل له «{cap}»، ولا وساطة له في الجرد')
    else:
        cap = src['expected']
        out['governor'] = dict(kind=ROLE_AR.get(src['src'], src['src']), relation_id=src['rid'], expected=cap, of=src.get('of'),
                               role_name=src.get('role_name') or ROLE_NAME.get(src['src']), role_rule=src.get('rule'),
                               relation_status=src.get('status', LICENSED), target_uid=t.uid,
                               face=src.get('face'), face_note=src.get('face_note'),
                               relation=ROLE_REL.get(src['src']))
        gov_txt = {'ibtida': 'بالابتداء', 'khabar': f'خبراً للمبتدأ «{src.get("of")}»',
                   'nasikh': f'خبراً لـ«{src.get("of")}»', 'idafa': f'مضافاً إليه لـ«{src.get("of")}»'}.get(src['src'], '')
    g = out['governor']
    if out['build'][0] == 'مبني':
        kw = MCAT_KW.get('attached_pronoun' if t.enclitic else t.mcat, 'اسم')
        # حركة البناء تُذكر للضمير والموصول المختصّ وحدهما: آخر الوحدة في غيرهما قد يكون لاحقةً لا آخر المبني (ذَٰلِكُمْ: الميم حرف خطاب)
        bv = _build_vowel(t) if kw.startswith('ضمير') or t.text in REL_AGR else None
        out['state'] = (f'في محلّ {cap}', f'مبني، ومحلّه ' + (f'بالعامل {gov_txt}' if g.get('kind') == 'عامل' or not g.get('role_name')
                                                            else f'بدوره «{g["role_name"]}» في علاقةٍ مرخَّصة ({g.get("role_rule")})'))
        out['mark_kind'] = 'محلّي'
        out['mark_dims'] = dict(carrier=None, visibility='محلّي', originality=None,
                                reason='المبني لا تظهر عليه علامة إعراب؛ وحركة آخره حركة بناء')
        out['cause'] = f'{kw} مبني' + (f' على {bv}: حركة آخره حركة بناءٍ لا علامة إعراب' if bv else '') + \
            '؛ والحكم إعرابٌ محلّي'
        role_part = g.get('role_name') or ''
        if g.get('role_rule') == 'P01':
            tail = f'، مجرور بحرف الجر «{g.get("operator")}»'
        elif g.get('kind') == 'عامل' and not role_part:
            tail = f' {gov_txt}'
        else:
            tail = f' {role_part}' + (f'، والمضاف «{src.get("of")}»' if src.get('src') in ('idafa',) and src.get('of') else
                                      f' لـ«{src.get("of")}»' if src.get('src') == 'object' and src.get('of') else '')
        out['statement'] = f'{kw} مبني' + (f' على {bv}' if bv else '') + f' في محلّ {cap}' + tail
        if src['src'] == 'operator' and src['r'].get('observed') not in ('محلاً', None):
            out['conflicts'].append(f'المرحلة ١١ قرأت على المبني علامةً «{src["r"].get("observed")}»')
        out['effect'] = dict(lafzi=None, mahalli=cap, relation=g.get('relation'))
        return _finish(out)
    name, cases, ev = _written_mark(t, nxt)
    out['mark'] = (name, ev) if name else None
    if t.pos == 'فعل' and cap == 'جر':
        out['conflicts'].append('العامل يقتضي الجرّ والمعمول فعل: الفعل لا يُجرّ')
    out['mark_dims'] = _mark_dims(name, cap) if name else None
    if not name or not cases:
        out['state'] = (cap, f'مقتضى العامل {gov_txt}؛ والعلامة غير مقروءة بالصنف ({ev}): المطابقة غير مثبتة')
        if not out['conflicts']:
            out['agreement'] = 'UNVERIFIED'
            return out
        return _finish(out)
    if cap not in cases:
        out['conflicts'].append(f'العلامة «{name}» تدلّ على {"، ".join(sorted(cases))} والعامل يقتضي {cap}')
    if out['conflicts']:
        return _finish(out)
    if g.get('relation') == 'غير مرخَّص في الجرد':
        out['state'] = (cap, f'قدرة «{g["operator"]}» على «{cap}» غير مذكورة في الجرد (لا في معانيه ولا في فئته): '
                             f'الاتفاق غير مثبت، والعلامة «{name}»')
        out['agreement'] = 'UNVERIFIED'
        return out
    kind = 'فعل مضارع' if t.pos == 'فعل' else 'اسم'
    out['state'] = (cap, f'العامل {gov_txt} يقتضي {cap}، والعلامة «{name}» تدلّ عليه ({ev})' if g.get('kind') == 'عامل' else
                    f'الدور «{g.get("role_name")}» يقتضي {cap}، والعلامة «{name}» تدلّ عليه ({ev})')
    out['mark_kind'] = _mark_kind(name)
    out['cause'] = ev.split('؛ والجذر غير مثبت')[0]   # احتمال حذف اللام لا يخصّ وجهاً اتفق فيه العامل والعلامة
    mp = _mark_phrase(name, cap)
    rn = g.get('role_name')
    if rn and g.get('role_rule') == 'P01':
        out['statement'] = f'{kind} مجرور بحرف الجر «{g.get("operator")}» وعلامة {STATE_NOUN[cap]} {mp}'
    elif rn and src['src'] == 'operator':
        out['statement'] = f'{rn} {STATE_ADJ[cap]} وعلامة {STATE_NOUN[cap]} {mp}'
    elif rn:
        lead = {'ibtida': f'{rn} {STATE_ADJ[cap]} بالابتداء', 'zarf': f'{rn} {STATE_ADJ[cap]} على الظرفية'}.get(
            src['src'], f'{rn} {STATE_ADJ[cap]}')
        tail = {'khabar': f'، والمبتدأ «{src.get("of")}»', 'idafa': f'، والمضاف «{src.get("of")}»',
                'object': f'، والفعل «{src.get("of")}»', 'subject': f'، والفعل «{src.get("of")}»',
                'nasikh': ''}.get(src['src'], '')
        out['statement'] = f'{lead} وعلامة {STATE_NOUN[cap]} {mp}{tail}' + \
            ((f' — {src["face_note"]}؛ والوجه غير مختار' if src['src'] == 'subject' and src.get('face_note') else
              f' — في وجه {src["face"]} المرخَّص، والوجه غير مختار (بديله محفوظ)') if src.get('face') else '')
    else:
        out['statement'] = f'{kind} {STATE_ADJ[cap]} {gov_txt} وعلامة {STATE_NOUN[cap]} {mp}'
    dims = out['mark_dims'] or {}
    out['effect'] = dict(lafzi=cap if dims.get('visibility') != 'مقدّرة' else None,
                         taqdiri=cap if dims.get('visibility') == 'مقدّرة' else None, mahalli=None,
                         mahall_of_complement_in_inventory=g.get('capacity_mahall_of_complement') or None,
                         relation=g.get('relation'))
    out['agreement'] = 'AGREE'
    return out


CAT_AR = {'relative': 'اسم موصول', 'conditional_noun': 'اسم شرط', 'interrogative_noun': 'اسم استفهام', 'particle': 'حرف',
          'adverb': 'ظرف', 'demonstrative': 'اسم إشارة', 'attached_pronoun': 'ضمير متصل', 'separate_pronoun': 'ضمير منفصل',
          'verb_name': 'اسم فعل'}
MCAT_KW = {'relative': 'اسم موصول', 'demonstrative': 'اسم إشارة', 'separate_pronoun': 'ضمير منفصل', 'attached_pronoun': 'ضمير متصل'}
COND_PART_AR = {'tool': 'الأداة', 'condition_verb': 'فعل الشرط', 'answer': 'الجواب', 'linker': 'الرابط'}
ROLE_NAME = {'ibtida': 'مبتدأ', 'khabar': 'خبر', 'idafa': 'مضاف إليه', 'object': 'مفعول به', 'subject': 'فاعل',
             'zarf': 'ظرف', 'voc_follower': 'تابعٌ لـ«أيّ» في النداء (نعتٌ أو عطف بيانٍ أو بدل)'}
ROLE_REL = {'ibtida': 'معنوي (الابتداء)', 'khabar': 'بالمبتدأ', 'nasikh': 'بالناسخ', 'idafa': 'بالمضاف', 'object': 'بالفعل',
            'subject': 'بالفعل', 'zarf': 'على الظرفية (ومتعلَّقه غير مثبت)', 'voc_follower': 'بالتبعية للفظ «أيّ»'}


def _usage_capacity(o, cap):
    """قدرة العامل في استعماله في هذا التحليل، لا اتحاد معانيه: المعاني المرفقة التي يذكر أثرُها ما سُجّل له (cap)
    هي الاستعمال المتّسق مع العلاقة المقبولة؛ والبقية بدائل معجمية بقدراتها، لا تُثبت الاتفاق ولا تنفيه.
    → (القدرة {lafzi, mahall_of_complement, mediated}، أسماء الاستعمال، البدائل [{meaning, capacity}])"""
    ms = o.get('meanings') or []
    use, alts = [], []
    for x in ms:
        pt = _effect_parts(x.get('effect'))
        (use if cap and (cap in pt['lafzi'] or cap in pt['mediated']) else alts).append((x, pt))
    if not use:
        return _capacity(o), [], [dict(meaning=x.get('label') or x.get('id'), effect=x.get('effect'),
                                       capacity=sorted(pt['lafzi'] | pt['mediated'])) for x, pt in alts]
    cap_ = dict(lafzi=set(), mahall_of_complement=set(), mediated=set())
    for _, pt in use:
        for k in cap_:
            cap_[k] |= pt[k]
    return ({k: sorted(v) for k, v in cap_.items()}, [x.get('label') or x.get('id') for x, _ in use],
            [dict(meaning=x.get('label') or x.get('id'), effect=x.get('effect'), capacity=sorted(pt['lafzi'] | pt['mediated']))
             for x, pt in alts])


CONFLICT_NATURE = (
    ('لا تشمل ما سُجّل', 'عاملٌ نُسب إليه في المرحلة ١١ أثرٌ لا يذكره الجرد له لفظاً ولا بوساطة',
     ['وساطةٌ غير ممثَّلة في الجرد (أن مضمرة بعد لام التعليل مثلاً)', 'نسبة الأثر إلى غير عامله في المرحلة ١١']),
    ('قرأت على المبني', 'المرحلة ١١ قرأت علامةً على وحدةٍ عُدّت مبنية',
     ['تعرّف الوحدة (لفظ الجلالة بشدّة اللام، أو تقطيعٌ أنشأ وحدةً مبنية)', 'قراءة العلامة في المرحلة ١١']),
    ('تدلّ على', 'العلامة المقروءة بصنف الكلمة تخالف مقتضى العامل',
     ['تقطيع الوحدة', 'صنفها أو جذرها', 'قبول العامل في المرحلة ١١']),
    ('الفعل لا يُجرّ', 'عاملٌ جارّ معموله فعل', ['قبول العامل', 'صنف المعمول']),
    ('المشاهَد', 'ما شاهدته المرحلة ١١ يخالف ما قضت به', ['قراءة العلامة في المرحلة ١١']))


def _finish(out):
    """يُغلق السجل: اتفاق، أو تعارضٌ داخلي موصوفٌ بطبيعته ومرشّحات سببه (لا حكمٌ لغويٌّ بالخطأ)"""
    if not out['conflicts']:
        out['agreement'] = 'AGREE'
        return out
    out['state'] = (None, 'تعارض: ' + '؛ '.join(out['conflicts']))
    out['statement'] = None
    out['agreement'] = 'CONFLICT'
    out['conflict_nature'] = [dict(kind='INTERNAL', what=w, candidate_causes=c,
                                   note='تعارضٌ داخلي بين الطبقات أو مع الجرد: يُكشف ويُسجَّل، ولا يُعدّ خطأً لغوياً بذاته')
                              for msg in out['conflicts'] for k, w, c in CONFLICT_NATURE if k in msg][:len(out['conflicts'])]
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
    hp = kw.get('head_parts') or {}
    # طرفٌ هو جزءٌ من وحدةٍ مكتوبة (لِ في لِلشَّهَٰدَةِ، أيّ في أيّها): معرّف العلاقة بهوية الجزء لا بالوحدة كلها
    rid = f'{ref}:{typ}:{rule}:' + '+'.join(f'{r}={hp.get(r) or u.uid}' for r, u in sorted(heads.items()))
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


def verse_relations(a, units, F, ref, legacy_cond=None, legacy_rel=None):
    """→ dict(records=[…], tokens=[(uid، الموضع، النص)]، axes) لآيةٍ واحدة.
    legacy_cond: سجلات الشرط من الطبقة القديمة (sarf.algebra.linguistic_layer(cond_out=…)) لهذه الآية، تُنقل بقاعدة C01 بهوياتها"""
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
        from .algebra import clause_start, idha_reading
        # «إذا» الفجائية تبدأ جملتها الاسمية (SARF_COMPREHENSIVE_REPAIR_04 §٧): لا شرط بها، لكنها حدّ إطارٍ كالشرطية
        # والقرينة وحدها تكفي هنا: الوجهان (الشرطية والفجائية) كلاهما يبدأ جملته، فهو حدّ إطارٍ في كلٍّ منهما
        fuj = {f_['word_index'] for f_ in a['operators'] if idha_reading(a, f_)}
        for j in range(i + 1, len(toks)):
            t = toks[j]
            if t.ui == 0 and (t.conj or clause_start(a, t.wi) or t.wi in fuj):
                return j
        return len(toks)

    # استعمال العامل في هذا التحليل: المقبول بأثره في معموله المعيَّن ومستواه، والبدائل المعجمية بقدراتها (لا اتحادها)
    for o in a['operators']:
        sl = o.get('slot') or {}
        ot = by_k.get((o['word_index'], sl.get('unit')))
        if ot is None:
            continue
        if ot.usage is None:
            ot.usage = dict(accepted=[], alternatives=[])
        r = o.get('relation') or {}
        tg = r.get('target') or {}
        tk = None
        if tg:
            seg_ = a['segments'][tg['word_index']]
            ui_ = next((i for i, u in enumerate(seg_['units']) if tg['slot'] in u.get('slots', [])), None)
            tk = by_k.get((tg['word_index'], ui_))
        if o.get('status') == 'accepted':
            capd, use, alts_ = _usage_capacity(o, r.get('expected'))
            ot.usage['accepted'].append(dict(
                operator=o['operator'], group=o['group'], operator_class=o.get('operator_class'), usage=use,
                effect_in_analysis=r.get('expected'), target=tk.uid if tk else None, target_text=tk.text if tk else None,
                target_role=r.get('role'), level='محلّي' if r.get('observed') == 'محلاً' else 'لفظي' if r.get('expected') else None,
                mediation=capd['mediated'] or None, lexical_alternatives=alts_))
        else:
            ot.usage['alternatives'].append(dict(operator=o['operator'], group=o['group'], status=o.get('status'),
                                                 capacity=_capacity(o), reason=o.get('reject_reason') or
                                                 '؛ '.join((o.get('judgement') or {}).get('deferred_because') or [])))
    idafa_of = {}                                   # المضاف ← سجل الإضافة (I01، I03)

    # I01 v1 (مقترحة): الضمير المتصل باسمٍ مثبت الاسمية في كلمته مضافٌ إليه في محلّ جر؛ دليل المرحلة ١٣ (محلّ الضمير) يُوصَل هنا
    # بقاعدةٍ تعيد فحص المضيف في هذه الطبقة (الاسمية بغير شكل التنوين، وليس عاملاً، وليس ظرفاً تتولّاه P02)، لا بنقل الحكم
    # O01 v1 (مقترحة): ضمير النصب المتصل بفعلٍ مثبت غير ناسخ مفعولٌ به في محلّ نصب؛ و«نَا» لا تُعيَّن (فاعلٌ أو مفعول)
    from .features_ext import OBJ_PRON
    for i, t in enumerate(toks):
        if not t.enclitic or i == 0:
            continue
        h_ = toks[i - 1]
        if h_.wi != t.wi:
            continue
        ec = t.feats.get('enclitic_case') or {}
        nasikh_host = any(str(o_['group']) in (NASIKH_KANA, NASIKH_INNA) and o_.get('status') == 'accepted'
                          and o_['word_index'] == h_.wi for o_ in a['operators'])
        if is_form(h_.text, ZURUF_V, i3rab=True):
            continue                                # الظرف ومضافه: P02
        if 'عامل' in (h_.lex or '') or h_.pos == 'عامل' or str(h_.pos or '').startswith('عامل'):
            continue                                # الضمير بعد عامله (عَلَيْهِ، إِنَّهُ): معموله في المرحلة ١١
        prem = [f'«{t.text}» ضميرٌ متصل (ملف المبنيات) في كلمة «{h_.text}»']
        if ec.get('v'):
            prem.append(f'المرحلة ١٣ (sarf.features_ext.enclitic_case): {ec.get("v")} {ec.get("st")} — {ec.get("ev")}')
        hl = letters(h_.text)
        waw_host = len(hl) >= 2 and hl[-1][0] == 'و' and not (hl[-1][1] - {SUKUN}) and DAMMA in hl[-2][1]
        if h_.nounish() and waw_host:
            # «ـُو + ضمير» (قَٰتِلُوهُمۡ): واو الجماعة وضمير المفعول، أو جمعٌ مذكر سالم مضاف حُذفت نونه؛ والكتابة لا تفصل
            R.append(_rec(ref, 'IDAFA', 'I01', {'host': h_, 'pronoun': t}, {'host': [h_], 'pronoun': [t]}, DEFERRED,
                          f'«{h_.text}» آخره واوٌ بعد ضمة قبل الضمير: فعلٌ بواو الجماعة وضميرُ مفعول، أو جمعٌ مذكر مضاف؛ والاسمية '
                          f'({h_.noun_ev}) قالبٌ يشمل الوجهين', premises=prem,
                          alternatives=['فعل بواو الجماعة، والضمير مفعولٌ به (O01)', 'جمع مذكر سالم مضاف، والضمير مضافٌ إليه']))
        elif h_.nounish():
            st_, why = LICENSED, f'ضميرٌ متصل باسمٍ مثبت الاسمية «{h_.text}» ({h_.noun_ev or "اسم"}): مضافٌ إليه'
            rec = _rec(ref, 'IDAFA', 'I01', {'mudaf': h_, 'mudaf_ilayh': t}, {'mudaf': [h_], 'mudaf_ilayh': [t]}, st_, why,
                       premises=prem + [f'«{h_.text}»: {h_.noun_ev}'], checked=['المضيف ليس عاملاً ولا ظرفاً', 'المضيف ليس فعلاً'],
                       edges=[('IDAFA', h_.uid, t.uid)])
            R.append(rec)
            idafa_of[h_.k] = rec
        elif h_.pos == 'فعل' and h_.pos_st == 'مثبت':
            if nasikh_host:
                R.append(_rec(ref, 'OBJECT', 'O01', {'verb': h_, 'object': t}, {'verb': [h_], 'object': [t]}, DEFERRED,
                              f'المضيف «{h_.text}» ناسخٌ مقبول: الضمير اسمه أو خبره لا مفعوله', premises=prem))
            elif t.text in OBJ_PRON:
                R.append(_rec(ref, 'OBJECT', 'O01', {'verb': h_, 'object': t}, {'verb': [h_], 'object': [t]}, LICENSED,
                              f'ضمير نصبٍ متصل «{t.text}» بفعلٍ مثبت غير ناسخ: مفعولٌ به',
                              premises=prem + [f'«{h_.text}»: فعل مثبت ({(h_.feats.get("pos") or {}).get("ev")})'],
                              checked=['المضيف ناسخٌ مقبول', 'الضمير من ضمائر الرفع (تُ، وا، نَ…)', '«نَا» تحتمل الرفع والنصب'],
                              edges=[('OBJECT', h_.uid, t.uid)]))
            else:
                R.append(_rec(ref, 'OBJECT', 'O01', {'verb': h_, 'object': t}, {'verb': [h_], 'object': [t]}, DEFERRED,
                              f'«{t.text}» بعد الفعل لا تعيّنه الكتابة مفعولاً (ليس من ضمائر النصب المعتمدة، أو «نَا»)', premises=prem))
        elif ec.get('v'):
            # دليلٌ سابق غير موصول: المرحلة ١٣ تحكم بالمحلّ، والمضيف غير مثبت الصنف في هذه الطبقة
            R.append(_rec(ref, 'IDAFA' if ec.get('v') == 'جر' else 'OBJECT', 'I01' if ec.get('v') == 'جر' else 'O01',
                          {'host': h_, 'pronoun': t}, {'host': [h_], 'pronoun': [t]}, DEFERRED,
                          f'دليلٌ سابق غير موصول: المرحلة ١٣ تجعل «{t.text}» في محلّ {ec.get("v")}، وصنف مضيفه «{h_.text}» غير مثبت في '
                          f'هذه الطبقة' + (' (اسميته من شكل التنوين وحده، العقد T19)' if h_.shape_only else ''), premises=prem))

    # I03 v1 (مقترحة): الإضافة اللفظية بين اسمين: اسمٌ معرب مثبت الاسمية آخره كسرةٌ بلا تنوين ولا «أل» (ولا هو مثنى ولا جمع بالنون)،
    # تليه كلمةٌ اسمٌ مجرورٌ كتابةً: سقوط التنوين مع الكسرة لا يكون إلا بالإضافة (الممنوع من الصرف يُجرّ بالفتحة، و«أل» غائبة)
    for i, t in enumerate(toks):
        n = nxt(i)
        if n is None or n.wi != t.wi + 1 or not word_start(n) or n.conj or t.k in idafa_of:
            continue
        tl_ = letters(t.text)
        if not tl_ or 'أل' in t.types or t.tanwin or t.divine or not t.nounish() or t.mcat or t.lex == 'مبني':
            continue
        L_, m_ = tl_[-1]
        if KASRA not in m_ or m_ & {KASRATAN, SHADDA} and L_ == 'ن' or L_ in 'يى' or \
                L_ == 'ن' and len(tl_) > 1 and tl_[-2][0] in 'اوي':
            continue
        if not (n.case in ('جر', 'جر أو نصب') or n.divine and n.case == 'جر'):
            continue
        prem = [f'«{t.text}»: آخره كسرةٌ بلا تنوين ولا «أل»، واسميته بغير شكل التنوين ({t.noun_ev or "اسم"})',
                f'«{n.text}» مجرورٌ كتابةً بعده بلا جار']
        if n.shape_only:
            rec = _rec(ref, 'IDAFA', 'I03', {'mudaf': t}, {'mudaf': [t], 'mudaf_ilayh_candidate': [n]}, DEFERRED,
                       f'المضاف إليه «{n.text}» اسميته من شكل التنوين وحده (العقد T19): الإضافة مرشّحة', premises=prem,
                       alternatives=[f'«{n.text}» مضافٌ إليه'])
        else:
            rec = _rec(ref, 'IDAFA', 'I03', {'mudaf': t, 'mudaf_ilayh': n}, {'mudaf': [t], 'mudaf_ilayh': [n]}, LICENSED,
                       'اسمٌ بكسرةٍ بلا تنوين ولا «أل»، يليه اسمٌ مجرور: إضافة', premises=prem,
                       checked=['«أل» في المضاف', 'التنوين', 'المثنى والجمع بالنون', 'الممنوع من الصرف (يُجرّ بالفتحة)', 'لفظ الجلالة مضافاً'],
                       alternatives=[f'المرحلة ١٣: {_join_ar((n.feats.get("idafa") or {}).get("alt"))}'] if (n.feats.get('idafa') or {}).get('alt') else [],
                       edges=[('IDAFA', t.uid, n.uid)])
        R.append(rec)
        idafa_of[t.k] = rec

    # P01 الجار والمجرور
    obliques = {}
    for k, (op_t, o, r) in governed.items():
        if str(o['group']) != JARR or k not in by_k:
            continue
        comp = [by_k[k]] if by_k[k] is not op_t else []   # الجار والمجرور في وحدةٍ واحدة (لِلشَّهَٰدَةِ): الوحدة نفسها
        i = idx[k]
        if not comp:
            parts = _parts_map(op_t, a['segments'][op_t.wi])
            op_t.parts = parts
            rec = _rec(ref, 'PP', 'P01', {'preposition': op_t, 'complement': op_t},
                       {'preposition': [op_t], 'complement': [op_t]}, LICENSED,
                       'حرف جرٍّ مقبول ومعموله في وحدةٍ مكتوبةٍ واحدة: الجار جزءٌ منها والمجرور جزءٌ آخر',
                       premises=[f'حكم العامل «{o["operator"]}» (مج 1): مقبول', f'العلامة في المعمول: {r.get("observed")}'],
                       merged_unit=True, attachment='غير مثبت: انظر A01', parts=parts,
                       part_heads=dict(preposition=next((p_['part_id'] for p_ in parts if p_['part'] == 'حرف جر'), None),
                                       complement=next((p_['part_id'] for p_ in parts if p_['part'] == 'اسم مجرور'), None)),
                       head_parts=dict(preposition=next((p_['part_id'] for p_ in parts if p_['part'] == 'حرف جر'), None),
                                       complement=next((p_['part_id'] for p_ in parts if p_['part'] == 'اسم مجرور'), None)),
                       phrase=dict(kind='شبه جملة (جار ومجرور)', unit=op_t.uid, text=op_t.text))
            rec['texts'] = dict(preposition=next((p_['text'] for p_ in parts if p_['part'] == 'حرف جر'), op_t.text),
                                complement=''.join(p_['text'] for p_ in parts if p_['part'] in ('أداة تعريف', 'اسم مجرور')) or op_t.text)
            R.append(rec)
            obliques[op_t.k] = (rec, [op_t])
            continue
        ext = []
        if nxt(i) is not None and nxt(i).wi == comp[0].wi and nxt(i).enclitic and comp[0].nounish():
            comp.append(nxt(i))                      # المضاف إلى ضميرٍ متصل في كلمته (رِجَالِكُمْ)
        ext_rec = idafa_of.get(comp[0].k)
        if ext_rec is not None and ext_rec['rule_id'] != 'I03':
            ext_rec = None                           # الضمير المتصل (I01) داخل المكمّل نفسه، لا امتدادٌ له
        if ext_rec is not None and ext_rec['status'] == LICENSED and 'mudaf_ilayh' in ext_rec['heads'] and \
                nxt(i) is not None and nxt(i).uid == ext_rec['heads']['mudaf_ilayh']:
            ext = [nxt(i)]                           # امتداد المكمّل بإضافةٍ مرخَّصة (I03): دليله سجلّها، لا الموضع
            j_ = i + 2
            while j_ < len(toks) and toks[j_].wi == ext[0].wi and toks[j_].enclitic:
                ext.append(toks[j_])                # والضمير المتصل بالمضاف إليه من كلمته (عَطَآءِ رَبِّكَ): حدّ المكوّن آخر الكلمة
                j_ += 1
        members = {'preposition': [op_t], 'complement': comp}
        if ext:
            members['complement_ext'] = ext
        rec = _rec(ref, 'PP', 'P01', {'preposition': op_t, 'complement': comp[0]},
                   members, LICENSED, 'حرف جرٍّ مقبول ومعموله' + ('، ومضافٌ إليه مرخَّص (I03) يمدّ المكمّل' if ext else ''),
                   premises=[f'حكم العامل «{o["operator"]}» (مج 1): مقبول — ' + '؛ '.join((o.get('judgement') or {}).get('proof') or []),
                             f'العلامة في المعمول: {r.get("observed")}'],
                   core=[op_t.uid, comp[0].uid], span_proof=(ext_rec['relation_id'] if ext else None),
                   span_premises=([ext_rec['relation_id']] if ext else []),
                   ext_candidate=(ext_rec['relation_id'] if ext_rec is not None and not ext else None),
                   checked=['R6 المرفوع بعد الجار (في حكم العامل)'],
                   edges=[('GOVERN', op_t.uid, comp[0].uid)], attachment='غير مثبت: انظر A01')
        if ext:
            rec['premises'].append(ext_rec['relation_id'])  # امتداد العبارة مقدّمةٌ مرخَّصة بسجلّها
        R.append(rec)
        obliques[op_t.k] = (rec, [op_t] + comp + ext)
    # P02 الظرف
    for i, t in enumerate(toks):
        if 'جذع' not in t.types or not is_form(t.text, ZURUF_V, i3rab=True):
            continue
        n = nxt(i)
        comp = None
        tl_a = letters(t.text)
        cut = bool(tl_a) and DAMMA in tl_a[-1][1] and not tl_a[-1][1] & {DAMMATAN}
        if cut:
            n = None                                # الظرف المبني على الضم مقطوعٌ عن الإضافة لفظاً (مِن بَعۡدُ): لا مضاف إليه بعده
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
        t.adverb = 'P02:' + rec['status']
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
    # V02 v1 (مقترحة): النداء بـ«أيّ»: «يا» ثم «أيّها/أيّهَ» ثم تابعٌ معرَّف بـ«أل» أو موصولٌ مختصّ أو اسم إشارة.
    # «أيّ» نكرةٌ مقصودة منادى مبني على الضم في محلّ نصب، و«ها» للتنبيه؛ ولا بدّ لها من تابعٍ مرفوعٍ تبعاً للفظها (ابن مالك وابن عقيل).
    # ونوع التابع (نعتٌ أو عطف بيانٍ أو بدل) بدائل محفوظة لا يُختار منها؛ والتبعية نفسها مرخَّصة بهذه القاعدة
    for i, t in enumerate(toks[:-1]):
        if t.text not in ('يَٰ', 'يَا', 'يَٰا') or toks[i + 1].text not in ('أَيُّهَا', 'أَيُّهَ'):
            continue
        ay = toks[i + 1]
        f_ = toks[i + 2] if i + 2 < len(toks) else None
        ay.parts = [dict(part='منادى', text='أَيُّ', part_id=f'{ay.uid}/p0', unit=ay.uid, source='sarf.protected.MERGED («أَيُّهَا» = أَيُّ + هَا)'),
                    dict(part='حرف تنبيه', text='هَا', part_id=f'{ay.uid}/p1', unit=ay.uid, source='sarf.protected.MERGED')]
        for p_, x_ in zip(ay.parts, _merged_part_spans(ay, a['segments'][ay.wi], ['أَيُّ', 'هَا']) or []):
            p_.update(span=x_[0], syllables=x_[1], **({'note': x_[2]} if x_[2] else {}))
        nida = _rec(ref, 'VOCATIVE', 'V02', {'particle': t, 'munada': ay}, {'particle': [t], 'munada': [ay]}, LICENSED,
                    '«يا» حرف نداء، و«أيّ» بعدها منادى نكرةٌ مقصودة مبني على الضم في محلّ نصب، و«ها» للتنبيه',
                    premises=[f'«{t.text}» عامل النداء (الجرد: مج {next((o_["group"] for o_ in a["operators"] if o_["word_index"] == t.wi and o_["operator"].startswith("يَ")), "?")})',
                              f'«{ay.text}» في الجرد المعتمد «يَٰٓأَيُّهَا» (الحماية لا تمنع الوظيفة)'],
                    checked=['«أيّ» لا تكون هنا استفهاماً ولا شرطاً ولا موصولاً: تليها «ها» التنبيه بعد حرف النداء'],
                    head_parts=dict(munada=ay.parts[0]['part_id']), parts=ay.parts)
        R.append(nida)
        ay.roles.append(dict(src='munada', expected='نصب', rid=nida['relation_id'], role_name='منادى', rule='V02',
                             status=LICENSED))
        if f_ is None or not word_start(f_):
            continue
        ok_f = f_.mcat in ('relative', 'demonstrative') or 'أل' in f_.types and (f_.nounish() or f_.shape_only)
        why_f = (f'«{f_.text}» موصولٌ مختصّ (ملف المبنيات)' if f_.mcat == 'relative' else f'«{f_.text}» اسم إشارة (ملف المبنيات)'
                 if f_.mcat == 'demonstrative' else f'«{f_.text}» معرَّفٌ بـ«أل»')
        R.append(_rec(ref, 'VOC_FOLLOWER', 'V02', {'munada': ay, 'follower': f_}, {'munada': [ay], 'follower': [f_]},
                      LICENSED if ok_f else DEFERRED,
                      ('تابعٌ لـ«أيّ» في النداء، مرفوعٌ تبعاً للفظها: ' + why_f) if ok_f else
                      f'ما بعد «أيّ» «{f_.text}» ليس معرَّفاً بأل ولا موصولاً ولا إشارةً في هذه الطبقة: التابع غير مثبت',
                      premises=[nida['relation_id'], why_f], container=None,
                      alternatives=['نعتٌ لـ«أيّ»', 'عطف بيان', 'بدل'], kind_status=DEFERRED, head_parts=dict(munada=ay.parts[0]['part_id']),
                      kind_note='نوع التابع غير مختار: البدائل الثلاثة محفوظة، ولا يتوقف عليها المحلّ'))
        if ok_f:
            bound[f_.k] = R[-1]['relation_id']
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
                    face='R01', selection=None,
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
                    container=cid, nucleus_complete=True, face='R01', selection=None,
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
    # F01 v1 (مقترحة): إطار الفعل — عقدةٌ لكل فعلٍ مثبت الصنف، بسماتٍ من تحليلٍ واحد (لا يُجمع زمنٌ من مرشّحٍ وبناءٌ من آخر):
    # الهوية والصيغة، والزمن والبناء للمعلوم أو المجهول بدرجتيهما، والاستعمال (ناسخ بحكم المرحلة ١١ أو غير ناسخ)، ومتطلبات الإسناد
    # والتعدية المثبتة، والضمائر المتصلة، والالتزامات المفتوحة بمصادرها. ويُبنى منه:
    # S01 الفاعل (أو نائبه): الضمير المتصل المكتوب، أو المستتر وجوباً (المتكلم والمخاطب المفرد)، أو اسمٌ ظاهرٌ مرفوعٌ كتابةً هو المرشّح
    #     الوحيد في إطار الفعل بعده (لا يُختار أقرب مرفوع إذا نافسه آخر)؛ وما سوى ذلك مرشّحاتٌ مؤجَّلة
    # O02 المفعول الظاهر: اسمٌ معرفةٌ منصوبٌ كتابةً بعد فعلٍ مثبت التعدّي غير ناسخ، ولا مفعول متصل قبله؛ والنكرة المنصوبة مؤجَّلة (حال، تمييز، مفعول مطلق)
    # M02 v1 (مقترحة): المصدر المؤوَّل من «أَنْ» الناصبة والمضارع. «أَنْ» التي تنصب المضارع مصدريةٌ دائماً؛ فإذا قبلها المرحلة ١١
    # عاملاً في مضارعٍ بعدها بنصبٍ متّسق، فالتركيب المكتوب «أَنْ + الفعل» في تأويل مصدر: مرخَّصٌ بوصفه تركيباً.
    # ووظيفته (محلّه) لا تُعيَّن إلا بدليلٍ مكتوب: حرف جرٍّ مقبولٌ قبله مباشرةً يجعله مجروراً به؛ وما سوى ذلك مؤجَّل بأبوابه
    # (فاعل، مفعول به، مبتدأ، خبر) أبواباً للفحص لا أوجهاً ثبت جوازها. ولا يُحكم بحرف جرٍّ محذوف بلا قاعدة
    masdar = {}
    unit_of = lambda wi, si: next((ui for ui, u in enumerate(a['segments'][wi]['units']) if si in u.get('slots', [])), None)
    for o in a['operators']:
        r_ = o.get('relation') or {}
        tg = r_.get('target') or {}
        if not (o.get('status') == 'accepted' and str(o.get('group')) == '5' and o['operator'] in ('أَنْ', 'أَن') and
                tg.get('pos') == 'verb' and r_.get('consistent') and r_.get('expected') == 'نصب'):
            continue
        an = by_k.get((o['word_index'], (o.get('slot') or {}).get('unit', 0)))
        vt = by_k.get((tg['word_index'], unit_of(tg['word_index'], tg['slot'])))
        if an is None or vt is None:
            continue
        pv = toks[idx[an.k] - 1] if idx[an.k] > 0 else None
        # حرف الجر قبله مباشرةً: مقبولٌ في المرحلة ١١، أو مؤجَّلٌ وهدفه «أَنْ» نفسها (لأنها ليست اسماً)؛ والجار لا يدخل إلا على
        # اسم، والمصدر المؤوَّل اسمٌ في التأويل، فهو مجروره
        # والحكم بهدف الحرف في المرحلة ١١ نفسه: هدفه «أَنْ» هذه، لا مجرورٌ له قبلها (بِهِۦٓ أَن يُوصَلَ، لِيٓ أَنۡ أَقُولَ،
        # لِلَّهِ أَن يَتَّخِذَ: للحرف مجروره، فلا يُجرّ به المصدر)
        def _tg(o2):
            return (o2.get('relation') or {}).get('target') or {}
        jop = next((o2 for o2 in a['operators'] if pv is not None and o2['word_index'] == pv.wi and str(o2['group']) == JARR and
                    _tg(o2).get('word_index') == an.wi and str(_tg(o2).get('text') or '').startswith('أَن')), None)
        jar = jop is not None and not any(t_.wi == pv.wi and idx[t_.k] > idx[pv.k] and t_.k != an.k for t_ in toks if t_.wi == pv.wi)
        fn = (f'مجرورٌ محلاً بحرف الجر «{pv.text}» قبله مباشرةً' +
              (' (مقبولٌ في المرحلة ١١)' if jop.get('status') == 'accepted' else
               ' (مؤجَّلٌ في المرحلة ١١ لأن ما يليه «أَنْ» لا اسم؛ والمصدر المؤوَّل هو الاسم المجرور)') if jar else
              'محلّه غير معيَّن: أبواب الفحص فاعل، أو مفعول به، أو مبتدأ، أو خبر؛ لا أوجهٌ ثبت جوازها')
        rec = _rec(ref, 'MASDAR', 'M02', {'harf': an, 'verb': vt}, {'harf': [an], 'verb': [vt]}, LICENSED,
                   f'«{an.text} {vt.text}» في تأويل مصدر: «أَنْ» الناصبة للمضارع مصدرية؛ والوظيفة: {fn}',
                   premises=[f'المرحلة ١١: «{an.text}» (مج 5) مقبولٌ عاملاً في «{vt.text}» ({tg.get("text")})، والنصب متّسق '
                             f'({r_.get("observed")})'] + ([f'«{pv.text}» حرف جرٍّ مقبول قبله مباشرةً'] if jar else []),
                   checked=['قبول العامل في المرحلة ١١', 'اتّساق النصب', 'حرف جرٍّ قبله مباشرةً'],
                   alternatives=[] if jar else ['فاعل', 'مفعول به', 'مبتدأ', 'خبر'],
                   function=dict(status=LICENSED if jar else DEFERRED, text=fn, governor=pv.uid if jar else None),
                   edges=[('MASDAR', an.uid, vt.uid)])
        R.append(rec)
        masdar[an.uid] = rec
    # M02.b (مقترحة): «أَلَّا» المندمجة رسماً (MERGED: أَنْ + لَا) لا تحكم عليها المرحلة ١١؛ فإذا تلاها مضارعٌ نصبُه مكتوبٌ لا يحتمل الرفع
    # (الفتحة، أو حذف النون) فـ«أَنْ» فيها ناصبةٌ مصدرية، والتركيب «أَنْ لا + الفعل» في تأويل مصدرٍ منفي. والدليل العلامة المكتوبة
    # على الفعل، لا حكم عاملٍ بُني عليها
    for t_i, an in enumerate(toks):
        if an.text != 'أَلَّا' or an.uid in masdar or t_i + 1 >= len(toks):
            continue
        vt = toks[t_i + 1]
        wm_ = _written_mark(vt)
        if vt.pos != 'فعل' or 'نصب' not in (wm_[1] or ()) or 'رفع' in (wm_[1] or ()) or (vt.feats.get('tense') or {}).get('v') == 'ماضٍ':
            continue
        fn = 'محلّه غير معيَّن: أبواب الفحص فاعل، أو مفعول به، أو مبتدأ، أو خبر، أو مجرورٌ بحرفٍ قبله؛ لا أوجهٌ ثبت جوازها'
        # النصب الخالص (الفتحة) يحسم المصدرية؛ و«حذف النون» علامة نصبٍ أو جزم، فيبقى معه وجه «أَنْ» المفسّرة و«لا» الناهية (أَلَّا تَعۡبُدُوٓاْ)
        excl = set(wm_[1] or ()) == {'نصب'}
        # وجه المصدرية والنفي استوفى شروطه المكتوبة فيُرخَّص في وجهه؛ وفرضية المفسّرة غير المفحوصة تمنع ادعاء الانفراد (الاختيار مؤجَّل)
        # ولا تمنع الترخيص المحلي (مراجعة 038)
        rec = _rec(ref, 'MASDAR', 'M02', {'harf': an, 'verb': vt}, {'harf': [an], 'verb': [vt]}, LICENSED,
                   (f'«{an.text} {vt.text}» = «أَنْ لَا {vt.text}» في تأويل مصدرٍ منفي: «أَنْ» في «أَلَّا» ناصبةٌ مصدرية، بدليل النصب الخالص المكتوب '
                    f'على الفعل ({wm_[0]})؛ والوظيفة: {fn}') if excl else
                   (f'«{an.text} {vt.text}»: «{wm_[0]}» لا يحسم النصب أو الجزم. وجه المصدرية والنفي استوفى شروطه المكتوبة، فهو مرخَّصٌ في وجهه؛ '
                    f'ووجه «أَنْ» المفسّرة و«لا» الناهية فرضيةٌ لم يُفحص شرطها (جملةٌ قبلها فيها معنى القول دون حروفه)، فلا يُدّعى انفراد '
                    f'الوجه الأول: اختياره مؤجَّل، والفرضية ليست وجهاً مكافئاً'),
                   premises=[f'«{an.text}» في الجرد المعتمد MERGED: أَنْ + لَا',
                             f'«{vt.text}»: النصب مكتوب ({wm_[0]})، والفتحة لا تحتمل الجزم ولا الرفع' if excl else
                             f'«{vt.text}»: {wm_[0]} متحقّق، ولا يحسم وحده النصب أو الجزم؛ وتعيين الحالة تابعٌ لتحليل الأداة'],
                   faces=[dict(face='أَنْ المصدرية + لا النافية + المضارع المنصوب (مصدرٌ مؤوَّل)', status='CONDITIONS_MET',
                               note='شروطه المكتوبة مستوفاة: «أَنْ» في الجرد، والعلامة تحتمل النصب')] +
                         ([] if excl else [dict(face='أَنْ المفسّرة + لا الناهية + المضارع المجزوم', status='HYPOTHESIS_UNCHECKED',
                                                note='فرضيةٌ تنتظر فحص شرطها (جملةٌ قبلها فيها معنى القول دون حروفه)؛ لم يُفحص، فليست وجهاً '
                                                     'مكافئاً لوجهٍ استوفى شروطه')]),
                   checked=['الجرد المعتمد MERGED', 'العلامة المكتوبة على الفعل', 'الماضي (لا تنصبه أَنْ)'],
                   alternatives=['فاعل', 'مفعول به', 'مبتدأ', 'خبر', 'مجرورٌ بحرفٍ قبله'] if excl else
                   ['أَنْ المصدرية + لا النافية + المنصوب (مصدرٌ مؤوَّل)', 'أَنْ المفسّرة + لا الناهية + المجزوم'],
                   function=dict(status=DEFERRED, text=fn, governor=None), negation='لَا (جزءٌ من «أَلَّا»)', rule_part='M02.b',
                   **({} if excl else dict(face='أَنْ المصدرية + لا النافية', selection=DEFERRED,
                                           face_note='وجهٌ استوفى شروطه المكتوبة، ومنافسه فرضيةٌ غير مفحوصة (المفسّرة): الترخيص محلي والاختيار مؤجَّل',
                                           search_status=SEARCH_INCOMPLETE,
                                           search_scope=dict(rule='M02.b', outside_coverage=['فحص شرط «أَنْ» المفسّرة (جملةٌ قبلها فيها معنى القول)']))),
                   edges=[('MASDAR', an.uid, vt.uid)])
        R.append(rec)
        masdar[an.uid] = rec
    frames = {}
    by_uid_ = {t.uid: t for t in toks}
    for i, v in enumerate(toks):
        if v.pos != 'فعل' or v.pos_st != 'مثبت':
            continue
        fe_ = frame_end(i)
        tf, vf, sf, trf = (v.feats.get(k) or {} for k in ('tense', 'voice', 'subject', 'transitivity'))
        nas = next((o_ for o_ in a['operators'] if o_['word_index'] == v.wi and str(o_['group']) == NASIKH_KANA and
                    o_.get('status') == 'accepted' and (o_.get('slot') or {}).get('unit') == v.ui), None)
        from .protected import VERBAL
        pid = (v.G.Theta.get('protected') or {}).get('identity')
        vb = next((k_ for k_, (forms, _) in VERBAL.items() if v.text in forms or pid in forms or pid == k_), None)
        usage = f'ناسخ «{nas["operator"]}» (مج 10، حكم المرحلة ١١)' if nas else \
            (f'صيغةٌ من صيغ «{vb}» في الجرد المعتمد (VERBAL): ناسخٌ أو تامّ، غير محسوم في حكم المرحلة ١١' if vb else
             'غير ناسخ في حكم المرحلة ١١')
        # F02: البناء غير المثبت في المرحلة ١٣ يُفحص بأوجهه، كلٌّ بتحقيقه للمكتوب؛ فإن منع الرسمُ وجهاً بمانعٍ مثبت ثبت الآخر
        v.voice_faces = None
        if vf.get('st') != 'مثبت' and not nas and 'مجهول' in (vf.get('alt') or []):
            v.voice_faces = _voice_faces(v.text)
            live_v = [f_ for f_ in v.voice_faces or [] if f_['status'] == LICENSED]
            if v.voice_faces and len(live_v) == 1:
                vf = dict(v=live_v[0]['voice'], st='مثبت', ev=f'F02: {live_v[0]["why"]}؛ والوجه الآخر ممنوع: ' +
                          next(f_['why'] for f_ in v.voice_faces if f_['status'] == REJECTED))
        # البناء للمعلوم أو المجهول لا ينطبق على الفعل العامل من الجرد (كان، ليس): غيابه ليس نقصاً
        coherent = all(x.get('st') == 'مثبت' for x in (tf, sf)) and (vf.get('st') == 'مثبت' or not vf and (nas or vb))
        cands = []
        tl_ = letters(v.text)
        if len(tl_) == 4 and DAMMA in tl_[0][1] and DAMMA in tl_[1][1] and tl_[2][0] == 'و' and tl_[3][0] == 'ا' and \
                tl_[0][0] not in 'يتنأ':
            # الماضي المبني للمجهول من الناقص مع واو الجماعة (دُعُوا): فُعِلُوا ← دُعِيُوا/دُعِوُوا ← دُعُوا
            from .root import hfn
            H = hfn()
            rts = [tl_[0][0] + tl_[1][0] + w for w in 'وي' if H is not None and tl_[0][0] + tl_[1][0] + w in H.roots]
            hz = H is not None and 'ء' + tl_[0][0] + tl_[1][0] in H.roots
            cands.append(dict(id='F01.c1', tense='ماضٍ', voice='مجهول', subject=dict(person=3, number='plural', gender='masc'),
                              subject_role='نائب فاعل', subject_unit='واو الجماعة (في الوحدة)', roots=rts,
                              realization=f'فُعِلُوا من الناقص: لام الفعل حُذفت قبل واو الجماعة وضُمّ ما قبلها ({v.text})',
                              status=DEFERRED if rts else REJECTED,
                              reason='مرشّحٌ كامل بزمنه وبنائه وضميره ودوره وتحقيقه؛ ولا يُختار بإطار الشرط ولا بترتيب المرشّحات' if rts
                              else 'لا جذر ناقص «' + tl_[0][0] + tl_[1][0] + 'و/ي» في HFN'))
            cands.append(dict(id='F01.c2', tense=tf.get('v'), voice=vf.get('v'), subject=sf.get('v'), subject_role='فاعل',
                              source='المرحلة ٨ والسمات (مرشّح)',
                              status=DEFERRED,
                              reason=('أمر الثلاثي ساكن الفاء يُبدأ بهمزة وصل ولا همزة مكتوبة؛ وأمر مهموز الفاء بلا همزة (خُذُوا) يقتضي جذراً «ء' +
                                      tl_[0][0] + tl_[1][0] + '»: ' + ('موجودٌ في HFN، فالوجه قائم' if hz else 'غير موجود في HFN، فالوجه ممنوعٌ في نطاق HFN'))
                              if tf.get('v') == 'أمر' else 'وجه المرحلة ٨'))
            if not hz and tf.get('v') == 'أمر':
                cands[-1]['status'] = REJECTED
            coherent = False
            live = [c_ for c_ in cands if c_['status'] != REJECTED]
            v.frame_cands = dict(live=live, rejected=[c_ for c_ in cands if c_['status'] == REJECTED])
        opn = []
        subj = None
        sp = sf.get('v') if isinstance(sf.get('v'), dict) else {}
        passive = vf.get('v') == 'مجهول' and vf.get('st') == 'مثبت'
        voice_known = vf.get('st') == 'مثبت'
        # البناء غير المثبت لا يُعامَل معلوماً بالافتراض: الدور وجهان (فاعل في المعلوم، ونائب فاعل في المجهول)،
        # والمشترك بينهما مثبت (مسندٌ إليه مرفوع)، والاختيار مؤجَّل بتأجيل البناء
        srole = 'نائب فاعل' if passive else 'فاعل' if voice_known or nas else 'فاعل أو نائب فاعل'
        vfl = v.voice_faces or []
        voice_faces = None if voice_known or nas else dict(
            معلوم='فاعل', مجهول='نائب فاعل',
            faces=[dict(f_, role='فاعل' if f_['voice'] == 'معلوم' else 'نائب فاعل') for f_ in vfl] or None,
            note=f'بناء «{v.text}» غير مثبت ({vf.get("st") or "مؤجَّل"}): ' +
                 ('؛ '.join(f'{"فاعلٌ" if f_["voice"] == "معلوم" else "نائب فاعلٍ"} في وجه {f_["voice"]} ({f_["id"]} {f_["status"]}: {f_["why"]})'
                            for f_ in vfl) if vfl else
                  'فاعلٌ إن كان مبنياً للمعلوم، ونائب فاعلٍ إن كان مبنياً للمجهول، ولم يُفحص تحقيق الوجهين') +
                 '؛ والرفع مشتركٌ بين الوجهين')
        scan = {}

        def overt_after(i):
            """المرشّحات الاسمية الظاهرة بعد الفعل في إطاره، بلا عبور فعلٍ آخر أو عاطفٍ أو عامل؛ وتُسجَّل في scan علّة التوقف
            (حدّ الإطار، أو فعل، أو عاطف، أو عامل) وما مرّ به البحث من وحدةٍ صنفها غير محسوم"""
            ov = []
            scan.update(stop='حدّ الإطار', unresolved=[])
            j = i + 1
            while j < fe_:
                u = toks[j]
                if u.wi == v.wi or u.k in span_of or u.enclitic or u.k in bound and ov:
                    j += 1
                    continue                        # وما في صلة المرشّح الأول أو حاويةٍ مرخَّصة ليس منافساً
                if u.conj or (u.lex or '').startswith('عامل') and not u.nounish():
                    scan['stop'] = 'عاطف' if u.conj else f'عامل «{u.text}»'
                    break
                if word_start(u) and u.mcat == 'particle' and u.text in COORD_PARTICLES:
                    scan['stop'] = 'عاطف'
                    break                           # عاطفٌ مستقل (ثُمَّ، أَوْ، بَلْ…): ما بعده معطوفٌ أو جملةٌ أخرى، لا منافسٌ في هذا الإسناد
                if u.pos == 'فعل' or 'فعل' in ((u.feats.get('pos') or {}).get('alt') or []) and not u.nounish():
                    scan['stop'] = 'فعل' if u.pos == 'فعل' else 'فعلٌ محتمل'
                    if u.pos != 'فعل':
                        scan['unresolved'].append(u)    # صنفه غير محسوم (اسم أو فعل): لا يُعدّ حدّاً مثبتاً ولا يُغفل منافساً
                    break                           # فعلٌ آخر قبل المرشّح: ما بعده في إسناده لا في إسناد هذا الفعل (قَالَتۡ أَنَّىٰ يَكُونُ … غُلَٰمٌ)
                if word_start(u) and (u.nounish() or u.divine or u.mcat in ('relative', 'demonstrative', 'separate_pronoun')) \
                        and u.k not in governed and u.case not in ('نصب', 'جر', 'نصب أو جر', 'جر أو نصب'):
                    ov.append(u)                    # المنصوب والمجرور كتابةً لا يكونان فاعلاً
                elif word_start(u) and u.pos is None and u.mcat is None and not u.lex and u.k not in governed:
                    scan['unresolved'].append(u)
                j += 1
            return ov

        if nas:
            # التزامات الناسخ تُسوّى بسجلّ V01 نفسه: ما رخّصه لا يبقى مفتوحاً، وما نقص يُسمّى بسببه
            v01 = next((r_ for r_ in R if r_['type'] == 'NASIKH' and r_['heads'].get('nasikh') == v.uid), None)
            if v01 is None:
                opn.append('اسم الناسخ وخبره: لا سجلّ V01 لهذا الناسخ')
                subj = dict(kind='اسم الناسخ', role='اسم الناسخ', status=DEFERRED, why='لا سجلّ V01')
            else:
                has_k = 'khabar' in v01['heads']
                if v01['status'] != LICENSED or not has_k:
                    opn.append(f'الخبر غير مرخَّص في V01 ({v01["status"]}): {v01["reason"]}')
                subj = dict(kind='اسم الناسخ (V01)', role='اسم الناسخ', status=v01['status'] if 'ism' in v01['heads'] else DEFERRED,
                            why=f'V01 {v01["status"]}: الاسم «{v01["texts"].get("ism", "—")}»' +
                                (f'، والخبر «{v01["texts"].get("khabar")}»' if has_k else '، والخبر غير مربوط'),
                            v01=v01['relation_id'])
        elif vb:
            kw_, sanad_ = subject_pronoun_written(sp, tf.get('v')) if sf.get('st') == 'مثبت' and tf.get('st') == 'مثبت' else (None, None)
            if kw_ in ('WRITTEN', 'HIDDEN_OBLIGATORY'):
                # المسند إليه ثابتٌ بالصيغة في الوجهين (اسم الناسخ في الناقص، والفاعل في التامّ): بنيةٌ مشتركة مثبتة؛ والاستعمال مؤجَّل
                fidk = f'{v.uid}|USE=ناقص+تامّ'
                subj = dict(kind='ضمير متصل مكتوب' if kw_ == 'WRITTEN' else 'ضمير مستتر وجوباً (غير مكتوب)', role='اسم الناسخ أو فاعل التامّ',
                            status=LICENSED, rule='S01.p', sanad=sanad_, implicit=kw_ != 'WRITTEN', shared_across=['ناقص', 'تامّ'],
                            face_id=fidk, signature=sp,
                            implicit_subject=implicit_subject(v.uid, fidk, sp, 'اسم الناسخ أو فاعل التامّ', 'S01.p',
                                                              [f'{v.uid}#signature', f'{v.uid}#tense']) if kw_ != 'WRITTEN' else None,
                            why=f'S01.p: «{v.text}» ({_pron_ar(sp)}): المسند إليه ' +
                                ('الضمير المتصل المكتوب' if kw_ == 'WRITTEN' else 'ضميرٌ مستتر وجوباً') +
                                ' في الوجهين، اسمُ الناسخ إن كان ناقصاً وفاعلٌ إن كان تامّاً؛ والاستعمال غير محسوم')
            else:
                subj = dict(kind='ضمير الصيغة أو اسمٌ ظاهر', role='اسم الناسخ أو فاعل التامّ', status=DEFERRED,
                            why=f'«{v.text}» من صيغ «{vb}» ولم يُقبل ناسخاً في المرحلة ١١: ضميره اسم الناسخ إن كان ناقصاً، وفاعلٌ إن كان تامّاً؛ '
                                'فلا يُسمّى فاعلاً قبل حسم الاستعمال')
            nk = next((toks[j_] for j_ in range(i + 1, fe_) if toks[j_].wi != v.wi and word_start(toks[j_]) and not toks[j_].conj
                       and (toks[j_].nounish() or toks[j_].shape_only)), None)
            kc = nk is not None and (nk.case in ('نصب', 'جر أو نصب', 'نصب أو جر'))
            opn.append('الاستعمال (ناسخ أو تامّ) غير محسوم: ' + (f'«{nk.text}» ({nk.loc}) منصوبٌ أو محتمل النصب كتابةً، خبرٌ مرشّح إن كان ناقصاً'
                                                              if kc else 'لا خبرَ مرشّحٌ منصوبٌ بعده في الإطار'))
        elif sf.get('st') == 'مثبت' and tf.get('st') == 'مثبت' and tense_safe_for_isnad(v, tf, governed)[0] and \
                subject_pronoun_written(sp, tf.get('v'))[0] in ('WRITTEN', 'HIDDEN_OBLIGATORY'):
            # S01.p: الصيغة تثبت طرف الإسناد في وجهها قبل البحث عن ظاهر (الترخيص المبكر)؛ والزمن مثبتٌ شرطاً، فلا يُستدلّ بالسابقة وحدها
            kw_, sanad_ = subject_pronoun_written(sp, tf.get('v'))
            fid_ = f'{v.uid}#T={tf.get("v")}|V={vf.get("v") or "—"}|S={sp.get("person")}{sp.get("number")}{sp.get("gender")}'
            subj = dict(kind='ضمير متصل مكتوب' if kw_ == 'WRITTEN' else 'ضمير مستتر وجوباً (غير مكتوب)', role=srole, status=LICENSED,
                        rule='S01.p', sanad=sanad_, implicit=kw_ != 'WRITTEN', face_id=fid_,
                        implicit_subject=implicit_subject(v.uid, fid_, sp, srole, 'S01.p', [f'{v.uid}#signature', f'{v.uid}#tense'])
                        if kw_ != 'WRITTEN' else None,
                        why=(f'ضمير الصيغة المكتوب ({_pron_ar(sp)}): {sf.get("ev")}' if kw_ == 'WRITTEN' else
                             f'S01.p: {_pron_ar(sp)} في {tf.get("v")}: الفاعل مستترٌ وجوباً، فلا يكون اسمٌ ظاهرٌ بعده فاعلَه ({sf.get("ev")})'))
        elif sf.get('st') == 'مثبت' and sp.get('person') == 3 and sp.get('number') == 'singular' and not cands:
            ov = overt_after(i)
            raf = [u for u in ov if u.nominative()[0] is True and (u.nounish() or u.divine)]   # الرفع من مصدر العلامة الواحد
            pp_between = bool(ov) and any(toks[j_].k in span_of for j_ in range(i + 1, idx[ov[0].k]))
            # المنافس المحتمل: وحدةٌ بعد المرشّح صنفها غير محسوم وعلى آخرها علامة رفعٍ مكتوبة (رَبُّنَا، كُلُّهُۥ)؛ فلا يُقال «لا منافس»
            # وقد غاب الدليل على صنفها (لا نتيجة صحيحة بشهادةٍ ناقصة)
            unres_raf = [u for u in scan.get('unresolved') or [] if ov and idx[u.k] > idx[ov[0].k] and 'رفع' in (_written_mark(u)[1] or ())
                         and DAMMA in (letters(u.text)[-1][1] if letters(u.text) else set())]
            if passive and pp_between and len(raf) == 1:
                subj = dict(kind='غير معيَّن', role=srole, status=DEFERRED,
                            why=f'بين الفعل المبني للمجهول و«{raf[0].text}» شبه جملة: قد تكون هي نائب الفاعل', candidates=[raf[0].uid])
            elif len(raf) == 1 and ov and ov[0] is raf[0] and unres_raf:
                subj = dict(kind='غير معيَّن', role=srole, status=DEFERRED,
                            why=f'«{raf[0].text}» المرشّح الاسمي الأول بعد الفعل مرفوعٌ كتابةً، وبعده ' +
                                '، '.join(f'«{u.text}» ({u.loc})' for u in unres_raf) + ' مرفوعٌ كتابةً صنفه غير محسوم: منافسٌ محتمل أو تابع، '
                                'فلا يُقال «لا منافس» بلا دليل صنفه', candidates=[raf[0].uid])
            elif len(raf) == 1 and ov and ov[0] is raf[0] and raf[0].k not in bound and raf[0].k not in licensed_subjects:
                u = raf[0]
                subj = dict(kind='اسم ظاهر', role=srole, status=LICENSED, unit=u,
                            why=f'«{u.text}» المرشّح الاسمي الأول بعد الفعل في إطاره، مرفوعٌ كتابةً ({u.nominative()[1]})، ولا منافس مرفوعٌ غيره',
                            mark=_written_mark(u)[0])
            elif not ov and scan.get('stop') in ('حدّ الإطار', 'فعل', 'عاطف') and not scan.get('unresolved'):
                # S01.h (مقترحة): لا اسم ظاهر في إطاره، والبحث بلغ حدّ الإطار أو فعلاً آخر أو عاطفاً، ولم يمرّ بوحدةٍ صنفها غير محسوم:
                # فالفاعل ضميرٌ مستتر في كل الأوجه (والاسم المتقدّم إن وُجد مبتدأٌ يعود إليه الضمير)؛ والمرجع غير معيَّن
                fidh = f'{v.uid}#T={tf.get("v")}|V={vf.get("v") or "—"}|S={sp.get("person")}{sp.get("number")}{sp.get("gender")}'
                subj = dict(kind='ضمير مستتر جوازاً (غير مكتوب)', role=srole, status=LICENSED, rule='S01.h', implicit=True, face_id=fidh,
                            implicit_subject=implicit_subject(v.uid, fidh, sp, srole, 'S01.h',
                                                              [f'{v.uid}#signature', f'{v.uid}#search_stop:{scan.get("stop")}']),
                            why=f'S01.h (مقترحة): لا اسم ظاهر بعد «{v.text}» في إطاره، والبحث توقّف عند {scan["stop"]} لا عند عامل، ولم يمرّ '
                                f'بوحدةٍ صنفها غير محسوم: فالفاعل ضميرٌ مستتر في كل الأوجه، ومرجعه غير معيَّن ({_pron_ar(sp)})')
            else:
                subj = dict(kind='غير معيَّن', role=srole, status=DEFERRED,
                            why=('المرشّحات: ' + '، '.join(f'«{u.text}» ({u.loc})' for u in ov) + '، أو ضميرٌ مستتر'
                                 if ov else 'لا اسم ظاهر بعده في إطاره: مستترٌ جوازاً، أو الفاعل متقدّمٌ مبتدأً' +
                                 (f'؛ والبحث توقّف عند {scan.get("stop")}، فقد يكون الفاعل بعده' if str(scan.get('stop', '')).startswith('عامل') else '') +
                                 ('؛ ومرّ البحث بما صنفه غير محسوم: ' + '، '.join(f'«{u.text}»' for u in scan.get('unresolved') or [])
                                  if scan.get('unresolved') else '')) +
                            ('؛ ومنافسٌ مرفوعٌ آخر' if len(raf) > 1 else ''), candidates=[u.uid for u in ov])
        else:
            # الأوجه كلها: المرشّح (sf.v) وبدائله؛ ولكلٍّ فاعله بحسب الصيغة: ضميرٌ متصل مكتوب في المثنى والجمع، ومستترٌ وجوباً
            # في المتكلم والمخاطب المفرد، وظاهرٌ مرشّح أو مستترٌ جوازاً في الغائب المفرد
            alts = [x for x in ([sf.get('v')] if isinstance(sf.get('v'), dict) else []) + list(sf.get('alt') or []) if isinstance(x, dict)]
            ov_ = overt_after(i) if any(x.get('person') == 3 and x.get('number') == 'singular' for x in alts) else []

            def _face(x):
                if x.get('number') in ('plural', 'dual'):
                    return f'{_pron_ar(x)}: فاعله الضمير المتصل المكتوب في الصيغة'
                if x.get('person') in (1, 2):
                    return f'{_pron_ar(x)}: فاعله مستترٌ وجوباً، وما بعده ليس فاعله'
                return (f'{_pron_ar(x)}: فاعله «{ov_[0].text}» ({ov_[0].loc}) مرشّحٌ ظاهر، أو مستترٌ جوازاً' if ov_ else
                        f'{_pron_ar(x)}: فاعله مستترٌ جوازاً أو ظاهرٌ بعده')
            if alts and all(x.get('number') in ('plural', 'dual') for x in alts) and \
                    len({(x.get('number'), x.get('gender')) for x in alts}) == 1:
                # المشترك المثبت بين الأوجه يُحفظ: الفاعل في كلها الضمير المتصل المكتوب (واو الجماعة أو ألف الاثنين أو نون النسوة)،
                # والمختلف بينها الشخص وحده؛ فالإسناد مرخَّص، والشخص مؤجَّل بأوجهه
                subj = dict(kind='ضمير متصل مكتوب', role=srole, status=LICENSED,
                            why=f'الفاعل الضمير المتصل المكتوب في كل أوجه الصيغة ({" / ".join(_pron_ar(x) for x in alts)})، '
                                f'والمختلف بينها الشخص وحده، فهو مؤجَّل: {sf.get("ev")}')
            else:
                # S01.f: لكل وجهٍ من أوجه الصيغة طرفُ إسناده بقاعدته (S01.p)، بهوية وجهٍ آلية من المرشّح الكامل؛ ولا يُختار وجه.
                # الظاهر يُرخَّص في وجه الغائب المفرد وحده، ولا يُعدّ فاعلاً في وجهٍ فاعلُه مستترٌ وجوباً أو مكتوب
                raf_ = [u for u in ov_ if u.nominative()[0] is True and (u.nounish() or u.divine)]
                unres_ = [u for u in scan.get('unresolved') or [] if 'رفع' in (_written_mark(u)[1] or ())]
                faces_ = []
                barred_ = []
                R_ = (v.G.Theta.get('R') or '') if getattr(v, 'G', None) is not None else ''
                wa_amb = any(x.get('number') == 'plural' for x in alts) and any(x.get('number') == 'singular' for x in alts) and \
                    v.text.rstrip('\u0652\u064e\u064f\u0650\u0670').endswith(('وا', 'و'))
                for x in list(alts):
                    if wa_amb and x.get('number') == 'singular' and R_ and not R_.endswith('و'):
                        # الواو آخرَ الصيغة لامُ الناقص الواوي أو واو الجماعة؛ والجذر «R_» ليس ناقصاً واوياً، فوجه المفرد ممتنعٌ بمانعٍ مثبت
                        barred_.append(dict(signature=x, barrier=f'الواو ليست لام الجذر «{R_}»: فهي واو الجماعة، ولا وجه للمفرد',
                                            status=REJECTED, rule='S01.f/wa'))
                        alts.remove(x)
                for x in alts:
                    fid = f'{v.uid}#T={tf.get("v")}|V={vf.get("v") or "—"}|S={x.get("person")}{x.get("number")}{x.get("gender")}'
                    safe_, unsafe_why = tense_safe_for_isnad(v, tf, governed)
                    kw_, sanad_ = subject_pronoun_written(x, tf.get('v')) if tf.get('st') == 'مثبت' and safe_ else (None, None)
                    if kw_ in ('WRITTEN', 'HIDDEN_OBLIGATORY'):
                        faces_.append(dict(face_id=fid, signature=x, kind='ضمير متصل مكتوب' if kw_ == 'WRITTEN' else 'ضمير مستتر وجوباً (غير مكتوب)',
                                           status=LICENSED, rule='S01.p', implicit=kw_ != 'WRITTEN', unit=None, sanad=sanad_,
                                           implicit_subject=implicit_subject(v.uid, fid, x, srole, 'S01.p', [f'{v.uid}#signature', f'{v.uid}#tense'])
                                           if kw_ != 'WRITTEN' else None))
                    elif kw_ == 'HIDDEN_OR_OVERT' and len(raf_) == 1 and ov_ and ov_[0] is raf_[0] and not unres_ and \
                            raf_[0].k not in bound and raf_[0].k not in licensed_subjects:
                        faces_.append(dict(face_id=fid, signature=x, kind='اسم ظاهر', status=LICENSED, rule='S01.f', unit=raf_[0].uid,
                                           unit_text=raf_[0].text, implicit=False,
                                           why=f'«{raf_[0].text}» المرشّح الاسمي الأول بعده مرفوعٌ كتابةً، ولا منافس مرفوعٌ غيره'))
                    elif kw_ == 'HIDDEN_OR_OVERT' and not ov_ and scan.get('stop') in ('حدّ الإطار', 'فعل', 'عاطف') and not scan.get('unresolved'):
                        faces_.append(dict(face_id=fid, signature=x, kind='ضمير مستتر جوازاً (غير مكتوب)', status=LICENSED, rule='S01.h',
                                           implicit=True, unit=None,
                                           implicit_subject=implicit_subject(v.uid, fid, x, srole, 'S01.h', [f'{v.uid}#signature',
                                                                                                         f'{v.uid}#search_stop:{scan.get("stop")}'])))
                    else:
                        faces_.append(dict(face_id=fid, signature=x, kind='غير معيَّن', status=DEFERRED, rule='S01.f', unit=None,
                                           blocked_by=('TENSE_V_VI_AMBIGUOUS' if not safe_ else
                                                       'NOUN_CLASS_UNRESOLVED' if scan.get('unresolved') else 'TENSE_NOT_PROVEN' if tf.get('st') != 'مثبت'
                                                       else 'COMPETING_OVERT' if len(raf_) > 1 or unres_ else 'SEARCH_BOUNDARY'),
                                           why=_face(x) + ('' if tf.get('st') == 'مثبت' else '؛ والزمن غير مثبت') + (f'؛ {unsafe_why}' if not safe_ else '') +
                                               ('؛ أعاقه تحليل الاسم لا قاعدة المضارعة: صنف ' + '، '.join(f'«{u.text}»' for u in scan.get('unresolved'))
                                                + ' غير محسوم' if scan.get('unresolved') else '')))
                all_ok = faces_ and all(f_['status'] == LICENSED for f_ in faces_)
                if barred_ and len(faces_) == 1 and faces_[0]['status'] == LICENSED:
                    # بقي وجهٌ واحد بعد المانع: طرف الإسناد مثبتٌ فيه، لا «في كل الأوجه»
                    all_ok = True
                subj = dict(kind=(faces_[0]['kind'] if barred_ and len(faces_) == 1 else 'في كل أوجه الصيغة') if all_ok else 'غير معيَّن',
                            role=srole, status=LICENSED if all_ok else DEFERRED, unit=None,
                            rule='S01.f', subject_faces=faces_, rejected_faces=barred_ or None,
                            selection='DEFERRED' if len(faces_) > 1 else 'SINGLE_FACE_AFTER_BARRIER',
                            why=(f'ضمير الصيغة غير مثبت ({sf.get("st")}): {sf.get("ev")}؛ ' +
                                 ('وطرف الإسناد مرخَّصٌ في كل وجه: ' if all_ok else 'والأوجه: ') +
                                 '؛ '.join(f"{_pron_ar(f_['signature'])}: {f_['kind']}" + (f" «{f_.get('unit_text')}»" if f_.get('unit_text') else '') +
                                           f" ({f_['status']})" for f_ in faces_) + '؛ ولا يُختار وجهٌ بلا دليل'),
                            candidates=[u.uid for u in ov_])
        objs = [r_ for r_ in R if r_['type'] == 'OBJECT' and r_['heads'].get('verb') == v.uid]
        obj2 = None
        obj_req = None
        if not nas and trf.get('st') == 'مثبت' and trf.get('v') == 'متعدٍّ' and not any(o_['status'] == LICENSED for o_ in objs):
            j = i + 1
            start = idx[subj['unit'].k] + 1 if subj and subj.get('unit') else i + 1
            j = start
            while j < fe_ and (toks[j].wi == v.wi or toks[j].k in span_of or toks[j].enclitic):
                j += 1
            u = toks[j] if j < fe_ else None
            if u is not None and word_start(u) and not u.conj and u.nounish() and u.k not in governed and u.k not in bound \
                    and u.case == 'نصب':
                df = u.definite()[0]
                obj2 = _rec(ref, 'OBJECT', 'O02', {'verb': v, 'object': u}, {'verb': [v], 'object': [u]},
                            LICENSED if df is True else DEFERRED,
                            f'«{u.text}» معرفةٌ منصوبة كتابةً بعد فعلٍ مثبت التعدّي: مفعولٌ به' if df is True else
                            f'«{u.text}» نكرةٌ منصوبة أو تعريفها غير مثبت: مفعولٌ به أو حالٌ أو تمييزٌ أو مفعولٌ مطلق',
                            premises=[f'«{v.text}»: التعدّي {trf.get("v")} {trf.get("st")} — {trf.get("ev")}',
                                      f'«{u.text}»: النصب مكتوب ({_written_mark(u)[0]})', f'«{u.text}»: {u.definite()[1]}'],
                            checked=['الفعل ناسخ', 'مفعولٌ متصل قبله', 'العامل المقبول في المنصوب'],
                            alternatives=[] if df is True else ['حال', 'تمييز', 'مفعول مطلق'],
                            mark_fact=dict(uid=u.uid, mark=_written_mark(u)[0]), edges=[('OBJECT', v.uid, u.uid)])
                R.append(obj2)
        if not nas and not any(o_['status'] == LICENSED for o_ in objs) and not (obj2 and obj2['status'] == LICENSED) \
                and trf.get('v') != 'لازم':
            # كاشف المكمّل بحدوده: يبدأ بعد الفعل (أو فاعله الظاهر)، ويتجاوز شبه الجملة (الجار ومجروره) وحدها،
            # ويقف عند أول ما سواها: فعلٌ آخر، أو أداةٌ غير الجار (أنْ، إلّا، لا…)، أو عاطف، أو حدّ الإطار.
            # ولا يقول «لازم» ولا «محذوف» بلا قاعدة: غياب الاكتشاف ليس دليل غياب المكمّل
            st0 = idx[subj['unit'].k] + 1 if subj and subj.get('unit') else i + 1
            trs = f'التعدّي {trf.get("v") or "غير معروف"} ({trf.get("st") or "مؤجَّل"})'
            jarr_w = {o_['word_index'] for o_ in a['operators'] if str(o_['group']) == JARR and o_.get('status') == 'accepted'}
            first, stop, j_, skipped = None, None, st0, False
            while j_ < fe_:
                t_ = toks[j_]
                if t_.wi == v.wi or t_.enclitic:
                    j_ += 1
                    continue
                if t_.conj:
                    stop = (t_, 'عاطف')
                    break
                is_op = 'عامل' in (t_.lex or '') or str(t_.pos or '').startswith('عامل')
                if is_op and t_.wi in jarr_w:
                    # شبه جملةٍ تُتجاوز: الجار ومجروره (في كلمته أو الكلمة التالية)
                    nxt_ = toks[j_ + 1] if j_ + 1 < fe_ else None
                    j_ += 2 if nxt_ is not None and nxt_.k in governed and governed[nxt_.k][0] is t_ else 1
                    skipped = True
                    continue
                if t_.k in governed and str(governed[t_.k][1]['group']) == JARR:
                    j_ += 1
                    skipped = True
                    continue
                if is_op or t_.pos == 'فعل':
                    stop = (t_, 'أداة' if is_op else 'فعلٌ آخر')
                    break
                first = t_
                break
            if vb:
                obj_req = dict(kind='KHABAR_CANDIDATE', status='ليس متطلَّب مفعول',
                               note=f'«{v.text}» من صيغ «{vb}» (VERBAL): ناقصٌ أو تامّ غير محسوم' +
                                    (f'؛ و«{first.text}» ({first.loc}) خبرٌ مرشّح في وجه الناقص، لا مفعول' if first else '') +
                                    '؛ والتامّ منه لا يطلب مفعولاً')
            elif first is not None and first.nounish() and (first.case == 'نصب' or 'نصب' in (_written_mark(first)[1] or ()) and
                                                             'رفع' not in (_written_mark(first)[1] or ())) \
                    and first.k not in governed and first.k not in bound and not (obj2 and obj2['heads'].get('object') == first.uid):
                obj_req = dict(kind='UNLINKED_CANDIDATE', status='مرشّح غير مربوط',
                               note=f'«{first.text}» ({first.loc}) منصوبٌ مكتوب يلي الفعل في إطاره، مرشّحُ مكمّلٍ غير مربوط؛ '
                                    f'ووظائف لم تُفحص بعد (مفعول به، حال، تمييز، مفعول مطلق): أبوابٌ للفحص لا أوجهٌ ثبت جوازها؛ '
                                    f'و{trs}: لا ترخيص بلا دليل الوظيفة')
            elif stop is not None and stop[1] == 'أداة' and stop[0].text.startswith('أَن') and not skipped and j_ + 1 < fe_ \
                    and toks[j_ + 1].pos == 'فعل':
                obj_req = dict(kind='UNANALYZED_COMPLEMENT', status='مكمّلٌ غير محلَّل',
                               note=f'بعد الفعل «{stop[0].text} {toks[j_ + 1].text}» ({stop[0].loc}): تركيبٌ مكتوب مرشّحٌ للمكمّلية؛ ' +
                                    (f'وهو مصدرٌ مؤوَّل مرخَّص تركيباً ({masdar[stop[0].uid]["relation_id"]})، ' if stop[0].uid in masdar else
                                     '(لا سجلّ M02 له)، ') +
                                    'ووظيفته وتعلّقه بهذا الفعل غير محلَّلين؛ ولا يُنفى المكمّل',
                               masdar=masdar[stop[0].uid]['relation_id'] if stop[0].uid in masdar else None)
            elif first is not None and first.nounish() and first.k not in governed and first.k not in bound and \
                    {'رفع', 'نصب'} <= set(_written_mark(first)[1] or ()):
                obj_req = dict(kind='CASE_NOT_WRITTEN', status='حالةٌ غير مكتوبة',
                               note=f'«{first.text}» ({first.loc}) اسمٌ يلي الفعل في إطاره وعلامته غير ظاهرة ({_written_mark(first)[0]}): '
                                    f'الكتابة لا تعيّن رفعه ولا نصبه، فهو مرشّحٌ للفاعلية وللمكمّلية معاً؛ و{trs}: لا ترخيص بلا دليل')
            elif first is not None:
                obj_req = dict(kind='NOT_FOUND_IN_SCOPE', status='لم يُكتشف ضمن النطاق',
                               note=f'أول ما يلي الفعل في إطاره «{first.text}» ({first.loc}) ' +
                                    ('ليس منصوباً مرشّحاً' if first.nounish() or first.pos == 'فعل' else
                                     'صنفه غير محسوم، فلا يُفحص مرشّحاً للمكمّل ولا يُنفى') + f'؛ و{trs}: '
                                    'لا يُحكم بلزومٍ ولا بحذفٍ بلا قاعدة')
            else:
                obj_req = dict(kind='NOT_FOUND_IN_SCOPE', status='لم يُكتشف ضمن النطاق',
                               note=('وقف البحث عند ' + (f'{stop[1]} «{stop[0].text}» ({stop[0].loc})' if stop else 'حدّ الإطار')) +
                                    ('، بعد شبه جملةٍ تجاوزها؛ وما بعد الحدّ تركيبٌ لا يُنسب إلى هذا الفعل بلا قاعدة' if skipped and stop else '') +
                                    f'، ولم يُكتشف مكمّلٌ منصوب قبله؛ و{trs}: لا يُحكم بلزومٍ ولا بحذفٍ بلا قاعدة')
        if cands:
            live = [c_ for c_ in cands if c_['status'] != REJECTED]
            subj = dict(kind='من المرشّح القائم' if len(live) == 1 else 'مرشّحات متنافسة',
                        role='، '.join(sorted({c_['subject_role'] for c_ in live})) or srole, status=DEFERRED,
                        why='؛ '.join(f"{c_['id']}: {c_['subject_role']} ({c_.get('subject_unit') or 'ضمير الصيغة'})" for c_ in live) +
                        ('؛ والممنوع: ' + '، '.join(c_['id'] for c_ in cands if c_['status'] == REJECTED) if len(live) < len(cands) else ''))
        heads = {'verb': v}
        members = {'verb': [v]}
        if subj and subj.get('unit') and subj['status'] == LICENSED:
            heads['subject'] = subj['unit']
            members['subject'] = [subj['unit']]
        # هوية المرشّح الصرفي (SARF_MAJOR_CLOSURE_01 §4): زمنه وبناؤه وضمير صيغته من تحليلٍ واحد، والأزمنة القائمة والممنوعة بأسبابها؛
        # ويحمل محور الوحدة الهوية نفسها، فلا يُجمع زمنٌ من مرشّحٍ وبناءٌ أو ضميرٌ من آخر
        _sv = sf.get('v') if isinstance(sf.get('v'), dict) else {}
        cand_rec = dict(
            id=f"{v.uid}#T={tf.get('v')}|V={vf.get('v')}|S={_sv.get('person')}{_sv.get('number')}{_sv.get('gender')}" if not cands else
               f"{v.uid}#" + '+'.join(c_['id'] for c_ in cands if c_['status'] != REJECTED),
            tense=tf.get('v') if not cands else None, tense_status=tf.get('st') if not cands else 'مرشّح',
            tense_live=([tf.get('v')] if tf.get('st') == 'مثبت' else list(tf.get('alt') or [tf.get('v')])) if not cands else
                       sorted({c_['tense'] for c_ in cands if c_['status'] != REJECTED} - {None}),
            tense_rejected=dict(tf.get('rejected') or {}) if not cands else
                           {c_['tense']: c_['reason'] for c_ in cands if c_['status'] == REJECTED and c_.get('tense')},
            tense_evidence=tf.get('ev'), realization=tf.get('realization'),
            voice=vf.get('v') if not cands else None, subject=_sv or None)
        v.morph_candidate = cand_rec['id']
        fr = _rec(ref, 'VERB_FRAME', 'F01', heads, members, LICENSED if coherent else DEFERRED,
                  'سمات الفعل كلها مثبتة من تحليلٍ واحد' if coherent else
                  ('مرشّحاتٌ صرفية كاملة متنافسة' if cands else 'بعض سمات الفعل مرشّحة: لا تُجمع من مرشّحاتٍ متفرقة'),
                  premises=([f'الصنف: فعل — {(v.feats.get("pos") or {}).get("ev")}'] +
                            [f'{n_}: {_pron_ar(x.get("v")) if isinstance(x.get("v"), dict) else (x.get("v") or "—")} ({x.get("st") or "مؤجَّل"})'
                             for n_, x in (('الزمن', tf), ('البناء', vf), ('ضمير الصيغة', sf)) if x]) +
                            ([f'البناء بأوجهه: {vf["ev"]}'] if str(vf.get('ev') or '').startswith('F02') else
                             [f'البناء بأوجهه (F02): ' + '؛ '.join(f'{f_["id"]} {f_["voice"]} [{f_["status"]}]: {f_["why"]}' for f_ in v.voice_faces)]
                             if v.voice_faces else [])
                  if not cands else
                  ['الصنف: فعل في كل المرشّحات القائمة'] +
                  [f'المرشّح القائم {c_["id"]}: {c_["tense"]}، {c_["voice"]}، {c_["subject_role"]}' for c_ in cands if c_['status'] != REJECTED] +
                  [f'الوجه الممنوع {c_["id"]} ({c_["tense"]}): {c_["reason"]} — لا يُبنى عليه' for c_ in cands if c_['status'] == REJECTED],
                  frame=dict(identity=v.text, root=v.G.Theta.get('R'), pattern=v.G.Theta.get('P'), candidate=cand_rec,
                             tense=(tf.get('v'), tf.get('st'), tf.get('alt')) if not cands else
                             ('، '.join(sorted({c_['tense'] for c_ in cands if c_['status'] != REJECTED} - {None})) or None, 'مرشّح', None),
                             voice=(vf.get('v'), vf.get('st'), vf.get('alt')) if not cands else
                             ('، '.join(sorted({c_['voice'] for c_ in cands if c_['status'] != REJECTED} - {None})) or None, 'مرشّح', None),
                             stage8=dict(tense=tf.get('v'), voice=vf.get('v'), subject=sf.get('v'),
                                         note='سمات المرحلة ٨ والسمات: ' + ('وجهٌ ممنوعٌ في F01، لا يدخل الإطار' if any(
                                             c_['status'] == REJECTED and c_.get('tense') == tf.get('v') for c_ in cands) else 'كما هي')) if cands else None,
                             usage=usage, subject_requirement='اسم الناسخ' if nas else 'اسم الناسخ أو الفاعل' if vb else
                             ('، '.join(sorted({c_['subject_role'] for c_ in cands if c_['status'] != REJECTED})) if cands else srole),
                             transitivity=(trf.get('v'), trf.get('st'), trf.get('ev')),
                             subject=dict({k: x for k, x in (subj or {}).items() if k != 'unit'},
                                          unit=(subj or {}).get('unit').uid if (subj or {}).get('unit') else None) if subj else None,
                             objects=[o_['relation_id'] for o_ in objs] + ([obj2['relation_id']] if obj2 else []),
                             candidates=cands, open=opn, object_requirement=obj_req))
        R.append(fr)
        frames[v.k] = fr
        if subj and subj.get('candidates') and (subj['status'] != LICENSED or subj.get('subject_faces')):
            # الظاهر المرخَّص في وجهٍ واحد من أوجه الصيغة لا يُرخَّص مطلقاً: يبقى سجلّه مؤجَّلاً، ويحمل هوية الوجه الذي رُخّص فيه
            cu = [by_uid_[u_] for u_ in subj['candidates']]
            fz_ = [f_['face_id'] for f_ in subj.get('subject_faces') or [] if f_.get('unit') in subj['candidates'] and f_['status'] == LICENSED]
            R.append(_rec(ref, 'SUBJECT', 'S01', {'verb': v}, {'verb': [v], 'subject_candidate': cu}, DEFERRED,
                          subj['why'] + (('؛ والظاهر مرخَّصٌ في الوجه ' + '، '.join(fz_) + ' وحده، والوجه غير مختار') if fz_ else ''),
                          premises=[f'«{v.text}»: ضمير الصيغة غائبٌ مفرد ({sf.get("st")})'], role_name=srole, verb_candidate=cand_rec['id'],
                          alternatives=[f'«{u_.text}» {srole}' for u_ in cu] + ['ضميرٌ مستتر'], licensed_in_faces=fz_ or None))
        if subj and subj.get('unit') and subj['status'] == LICENSED:
            u = subj['unit']
            R.append(_rec(ref, 'SUBJECT', 'S01', {'verb': v, 'subject': u}, {'verb': [v], 'subject': [u]}, LICENSED, subj['why'],
                          premises=[fr['relation_id'] if coherent else f'«{v.text}»: ضمير الصيغة غائبٌ مفرد مثبت ({sf.get("ev")})',
                                    f'«{u.text}»: {u.nominative()[1]}'],
                          checked=['منافسٌ مرفوعٌ في الإطار', 'عاملٌ مقبول في المرفوع', 'طرفٌ في علاقةٍ أخرى'],
                          role_name=srole, verb_candidate=cand_rec['id'], mark_fact=dict(uid=u.uid, mark=subj.get('mark')), edges=[('SUBJECT', v.uid, u.uid)],
                          **(dict(face='المعلوم أو المجهول', selection=DEFERRED, face_note=voice_faces['note'],
                                  voice_faces={k_: v_ for k_, v_ in voice_faces.items() if k_ not in ('note', 'faces')},
                                  voice_face_evidence=voice_faces.get('faces'),
                                  alternatives=[f'«{u.text}» نائب فاعل (إن كان «{v.text}» مبنياً للمجهول)',
                                                f'«{u.text}» فاعل (إن كان «{v.text}» مبنياً للمعلوم)'])
                             if voice_faces else {})))
            bound[u.k] = R[-1]['relation_id']

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
                # الترخيص وجهٌ لا اختيار: وجها الخبر المتعدّد والحال المقدَّمة خارج التغطية، فلا يُقال «المضيف الوحيد» ولا يكتمل البحث
                R.append(_rec(ref, 'ATTACH', 'A02', {'oblique': ous[0], 'host': pr}, {'oblique': ous, 'host': [pr]}, LICENSED,
                              f'شبه الجملة بين طرفي النواة المرخَّصة قبل الخبر، ولا فعل في الإطار، والخبر الوصف «{pr.text}» '
                              'المضيفُ الوحيد بين مضيفي A01 في الإطار: وجه التعلّق به مرخَّص؛ واختياره مؤجَّل، '
                              'لأن وجهي الخبر المتعدّد والحال المقدَّمة خارج التغطية لم يُفحصا',
                              face='التعلّق بالخبر الوصف', selection=DEFERRED,
                              face_note='وجهٌ مرخَّص غير مختار: وجها شبه الجملة خبراً أول (تعدّد الخبر) وحالاً مقدَّمة خارج تغطية A02 v1، '
                                        'مؤجَّلان لا مرفوضان',
                              premises=[nuc['rec']['relation_id'], orec['relation_id'],
                                        f'الإطار {toks[nuc["lo"]].loc}–{toks[nuc["hi"] - 1].loc}: لا فعل ولا فعل محتمل',
                                        f'مضيفو A01 في الإطار: «{pr.text}» وحده (لا يشمل وجهي الخبر المتعدّد والحال)'] + ([pr.elative_proof()] if pr.elative_proof() else []),
                              checked=['فعلٌ في الإطار (ولو محتمل)', 'وصفٌ آخر في الإطار', 'حدّ حاوية',
                                       'وجه النعت: شبه الجملة قبل الخبر، والنعت لا يتقدّم منعوته'],
                              alternatives=['شبه الجملة خبرٌ أول وتعدّد الخبر: خارج تغطية v1 (مؤجَّل لا مرفوض)',
                                            'شبه الجملة حالٌ مقدَّمة من الخبر النكرة: خارج تغطية v1 (مؤجَّل لا مرفوض)'] +
                              [dict(h, status=DEFERRED, reason='خارج إطار النواة: لا يُعبر إليه في A02') for h in hosts
                               if h['host'] != pr.uid],
                              search_status=SEARCH_INCOMPLETE, search_scope=dict(rule='A02 v1', frame=[toks[nuc['lo']].loc, toks[nuc['hi'] - 1].loc],
                                                                                 outside_coverage=['خبرٌ أول (تعدّد الخبر)', 'حالٌ مقدَّمة']),
                              edges=[('ATTACH', ous[0].uid, pr.uid)]))
                continue
        R.append(_rec(ref, 'ATTACH', 'A01', {'oblique': ous[0]}, {'oblique': ous}, DEFERRED,
                      ('لا مضيف ممكن في الإطار' if not hosts else f'{len(hosts)} مضيفاً ممكناً، ولا إطار تعلّقٍ مثبت لأيٍّ منها') +
                      '؛ والبحث غير مكتمل: لا جرد لأطر التعلّق',
                      premises=[orec['relation_id']], alternatives=hosts, container=cont, search_status=SEARCH_INCOMPLETE,
                      search_scope=dict(frame=[toks[lo].loc, toks[hi - 1].loc] if hi > lo else [], container=cont)))
    # P03 v1 (مقترحة): المندمج رسماً من حرف جرٍّ واسمٍ مبني (مِمَّنْ = مِنْ + مَنْ، مِمَّا، عَمَّا، فِيمَا…) في الجرد المعتمد MERGED:
    # الوحدة المكتوبة محفوظة، والجزءان بهويتيهما؛ والاسم مجرورٌ محلاً بالحرف (كل مداخله في ملف المبنيات أسماء)، ونوعه (موصول،
    # استفهام، شرط) بدائل لا يُختار منها؛ والصلة إن كان موصولاً علاقةٌ مؤجَّلة
    from .protected import MERGED
    for i, t in enumerate(toks):
        mg = MERGED.get((t.G.Theta.get('protected') or {}).get('identity') or t.text)
        if not mg or len(mg) != 2 or mg[0] not in ('مِنْ', 'عَنْ', 'فِي', 'بِ', 'لِ') or mg[1] not in ('مَنْ', 'مَا'):
            continue
        if not _LEX:
            from .lexicon import MabniLexicon
            _LEX.append(MabniLexicon())
        kinds = sorted({CAT_AR.get(e.get('category'), e.get('category')) for e in (_LEX[0].lookup(mg[1]) or [])})
        nominal = bool(kinds) and all(k_ != CAT_AR['particle'] for k_ in kinds)
        t.parts = [dict(part='حرف جر', text=mg[0], part_id=f'{t.uid}/p0', unit=t.uid, source='sarf.protected.MERGED'),
                   dict(part='اسم مبني', text=mg[1], part_id=f'{t.uid}/p1', unit=t.uid, kinds=kinds, source='sarf.protected.MERGED')]
        for p_, x_ in zip(t.parts, _merged_part_spans(t, a['segments'][t.wi], list(mg)) or []):
            p_.update(span=x_[0], syllables=x_[1], **({'note': x_[2]} if x_[2] else {}))
        R.append(_rec(ref, 'PP', 'P03', {'preposition': t, 'complement': t}, {'preposition': [t], 'complement': [t]},
                      LICENSED if nominal else DEFERRED,
                      f'«{t.text}» = «{mg[0]}» + «{mg[1]}» في الجرد المعتمد: حرف جرٍّ ومجروره المبني في محلّ جر' if nominal else
                      f'«{mg[1]}» له في ملف المبنيات مدخلٌ حرفي: الجرّ المحلّي غير مثبت',
                      premises=[f'sarf.protected.MERGED: «{t.text}» = {" + ".join(mg)}', f'ملف المبنيات: «{mg[1]}» ← {"، ".join(kinds) or "—"}'],
                      alternatives=[f'«{mg[1]}» {k_}' for k_ in kinds], merged_unit=True, parts=t.parts,
                      part_heads=dict(preposition=t.parts[0]['part_id'], complement=t.parts[1]['part_id']),
                      head_parts=dict(preposition=t.parts[0]['part_id'], complement=t.parts[1]['part_id']),
                      kind_status=DEFERRED if len(kinds) > 1 else LICENSED,
                      kind_note='نوع الاسم المبني غير مختار: البدائل محفوظة، ولا يتوقف عليها الجرّ المحلّي'))
        if nominal:
            t.roles.append(dict(src='merged_pp', expected='جر', rid=R[-1]['relation_id'], role_name='مجرور بحرف الجر', rule='P03',
                                status=LICENSED, parts=mg, kinds=kinds))
        n_ = nxt(i)
        if CAT_AR['relative'] in kinds and n_ is not None and n_.pos == 'فعل':
            R.append(_rec(ref, 'SILAH', 'R02', {'relative': t, 'silah_head': n_}, {'relative': [t], 'silah_head': [n_]}, DEFERRED,
                          f'إن كانت «{mg[1]}» موصولة فصلتها الجملة الفعلية «{n_.text}» بعدها؛ ونوعها غير مختار (البدائل: {"، ".join(kinds)})',
                          premises=[R[-1]['relation_id']], alternatives=[f'«{mg[1]}» {k_}' for k_ in kinds if k_ != CAT_AR['relative']],
                          resumptive=dict(status=DEFERRED, note='العائد إن كانت موصولة: مفعولٌ منصوب محذوف بعد «' + n_.text +
                                          '» أو ضمير؛ ولا يُكتب المحذوف')))

    # R02 (جسر): الصلة الفعلية والاسمية من الطبقة القديمة (sarf.algebra.relative_structs) بنطاقها ودليلها، والعائد التزامٌ يُفحص:
    # المطابقة شرطٌ لا يثبت المرجع وحده، فالعائد مؤجَّل إلا أن يكون فاعلاً مكتوباً للغائب في فعل الصلة الأول ولا ضمير غيره في نطاقها
    for c in legacy_rel or []:
        if not c['head'].startswith(ref + ':'):
            continue
        wloc = lambda l: int(l.split(':')[2]) - 1
        rel_t = next((t for t in toks if t.wi == wloc(c['head']) and t.mcat == 'relative'), None)
        if rel_t is None:
            continue
        span = [t for t in toks if wloc(c['start']) <= t.wi <= wloc(c['last'])]
        if not span:
            continue
        sil = {o_[0]: o_ for o_ in c['obligations']}
        s_ok = sil.get('صلة', [None, 'False'])[1] == 'True'
        rh = sil.get('عائد', [None, 'False', ''])
        head_ = next((t for t in span if t.pos == 'فعل'), span[0])
        st_ = LICENSED if s_ok else DEFERRED
        bnd = 'آخر الآية (حدّ مصدر)' if c['end_is_text_end'] else f'قبل «{c["end_word"]}»'
        prons = [t for t in span if t.enclitic]
        rv = DEFERRED
        rnote = (rh[2] if len(rh) > 2 else '') or 'لم يُكشف'
        sf_ = head_.feats.get('subject') or {}
        sp_ = sf_.get('v') if isinstance(sf_.get('v'), dict) else {}
        if rh[1] == 'True' and 'فاعل' in rnote and not prons and head_.pos == 'فعل':
            if sf_.get('st') == 'مثبت' and sp_.get('person') == 3:
                rv, rnote = LICENSED, rnote + '؛ وضمير الصيغة غائبٌ مثبت، ولا ضمير غيره في نطاق الصلة: هو العائد بالحصر'
            else:
                rnote += f'؛ لكن ضمير الصيغة في «{head_.text}» {sf_.get("st") or "غير مثبت"} (الشخص {sp_.get("person")}): ' \
                         'المطابقة على مرشّحٍ لا تثبت العائد'
        # المصالحة مع R01: إن بنى R01 للموصول نفسه حاويةً اسمية، فنوع الصلة وجهان (اسمية بـR01، أو شبه جملة متعلّقها محذوف في
        # الطبقة القديمة)؛ والربط بين الموصول وصلته مرخَّص، والنوع مؤجَّلٌ بوجهيه؛ ومرشّحات العائد سجلٌّ واحد من الطبقتين
        cont_ = next((r_ for r_ in R if r_['type'] == 'CONTAINER_RELATIVE' and r_['heads'].get('relative') == rel_t.uid), None)
        res01 = [r_ for r_ in R if r_['type'] == 'RESUMPTIVE' and r_['heads'].get('relative') == rel_t.uid]
        LEG = 'المرحلة ١٤ (sarf.algebra.relative_structs)'
        # الأوجه: ترخيص كل وجهٍ من دليله هو، والاختيار بينها مستقلٌّ عنه. فوجود وجهٍ قديم لا يُسقط وجهاً مرخَّصاً،
        # ولا يُرقّى وجهٌ بما لم يقله مصدره
        kinds_ = []
        if cont_:
            kinds_.append(dict(id='K1', kind='جملة اسمية: شبه الجملة خبرٌ مقدَّم، والمرفوع مبتدأٌ مؤخَّر', source=cont_['relation_id'],
                               layer='R01', status=cont_['status'], why=cont_['reason']))
        unacc = [t for t in span if t.case == 'رفع' and t.pos == 'اسم' and not t.enclitic] if cont_ else []
        leg_st = st_
        leg_why = f'{LEG}: الصلة {c["silah"]}' + (f'، والعائد {rnote.split("؛")[0]}' if rh[2:3] and rh[2] else '')
        if unacc and 'شبه جملة' in c['silah']:
            leg_st = DEFERRED
            leg_why += ('؛ ولا يذكر هذا الوجه دور المرفوع «' + '»، «'.join(t.text for t in unacc) +
                        '» في الصلة: دليله ناقصٌ عنه (لا مانعٌ مثبت يرفضه)')
        kinds_.append(dict(id='K2' if cont_ else 'K1', kind=c['silah'], source=LEG, layer='LEGACY', status=leg_st, why=leg_why))
        if len({k_['kind'] for k_ in kinds_}) > 1:
            kind_status = DEFERRED                          # الاختيار: لا يُختار وجهٌ ومنافسه غير مرفوضٍ بمانعٍ مثبت
        else:
            kind_status = kinds_[0]['status']
        if cont_ and kind_status == DEFERRED:
            # الحاوية ونواتها مرخَّصتان في وجههما، والاختيار مؤجَّل؛ ويُحفظ الوجه الآخر بديلاً بما يقوله مصدره وحده
            for r_ in [cont_] + [n2 for n2 in R if n2['type'] == 'PREDICATIVE_PP' and n2.get('container_id') == cont_['relation_id']]:
                r_['selection'] = DEFERRED
                r_['face_note'] = 'وجه R01 مرخَّصٌ في وجهه، والوجه غير مختار: الاختيار بين وجهَي الصلة مؤجَّل (R02)'
                alt_ = f'صلةٌ شبه جملة متعلّقها محذوف، والعائد {rnote.split("؛")[0]} — وجه الطبقة القديمة ({LEG})؛ ولا يذكر دور المرفوع'
                if alt_ not in (r_.get('alternatives') or []):
                    r_['alternatives'] = list(r_.get('alternatives') or []) + [alt_]
        cands_ = []
        for r_ in res01:
            cands_.append(dict(id=f'C{len(cands_) + 1}', candidate=r_['texts'].get('pronoun'), unit=r_['heads'].get('pronoun'),
                               source=r_['relation_id'], face='K1', status=r_['status'], why=r_['reason']))
        if rh[2:3] and rh[2]:
            cands_.append(dict(id=f'C{len(cands_) + 1}', candidate=rnote.split('؛')[0], unit=None, source=LEG,
                               face=kinds_[-1]['id'], status=rv, why='وجه الطبقة القديمة'))
        # ترخيص كل مرشّحٍ للعائد من دليله؛ والاختيار بينها مؤجَّل ما تعدّدت ولم يُرفض أحدها بمانعٍ مثبت
        res_sel = cands_[0]['status'] if len(cands_) == 1 else DEFERRED if cands_ else rv
        if len(cands_) > 1:
            rnote = ('مرشّحان من وجهين: ' + '، و'.join(f'«{x["candidate"]}» ({x["face"]}، {x["status"]})' for x in cands_) +
                     '؛ والاختيار مؤجَّلٌ بتأجيل نوع الصلة')
        prem_ = []
        links_ = []
        for o_ in c['obligations']:
            p_ = f'{LEG}: {o_[0]} — {o_[2]} → {"مستوفى" if o_[1] == "True" else "مفتوح"} في الطبقة القديمة'
            prem_.append(p_)
            links_.append(dict(premise=p_, candidate=kinds_[-1]['id'] if o_[0] == 'صلة' else
                               next((x['id'] for x in cands_ if x['source'] == LEG), None), relation=None, layer='LEGACY'))
        if cont_ and cont_['status'] == LICENSED:
            prem_.append(cont_['relation_id'])
            links_.append(dict(premise=cont_['relation_id'], candidate='K1', relation=cont_['relation_id'], layer='R01'))
        for x in cands_:
            if x['source'] != LEG:
                links_.append(dict(premise=None, candidate=x['id'], relation=x['source'], layer='R01'))
        R.append(_rec(ref, 'SILAH', 'R02', {'relative': rel_t, 'silah_head': head_}, {'relative': [rel_t], 'silah_head': [head_], 'silah': span}, st_,
                      (f'صلة «{rel_t.text}» من «{span[0].text}» إلى «{span[-1].text}» (الحدّ: {bnd})؛ ونوعها ' +
                       ('غير مختار بين وجهين: ' + ' / '.join(f'{k_["kind"]} ({k_["layer"]}، {k_["status"]})' for k_ in kinds_)
                        if kind_status == DEFERRED and len(kinds_) > 1 else c['silah'])
                       if s_ok else 'الصلة غير مكشوفة في الطبقة القديمة'),
                      premises=prem_, premise_links=links_,
                      extent=[t.uid for t in [rel_t] + span], boundary_proven=bool(c['end_is_text_end']),
                      silah_kinds=kinds_, kind_status=kind_status,
                      kind_note='ترخيص الوجه غير اختياره: الوجهان محفوظان كلٌّ بحالة دليله، ولا يتوقف عليهما ربط الموصول بصلته'
                      if kind_status == DEFERRED and len(kinds_) > 1 else None,
                      shared=dict(boundary=f'من «{span[0].text}» إلى «{span[-1].text}»', members=[t.uid for t in span],
                                  note='حدّ الصلة وأعضاؤها مشتركةٌ بين الأوجه، مثبتةٌ بربط R02') if len(kinds_) > 1 else None,
                      resumptive=dict(status=res_sel, note=rnote, rule='المطابقة شرط، والحصر دليل', candidates=cands_),
                      alternatives=[] if res_sel == LICENSED else [f'العائد «{x["candidate"]}» ({x["face"]}، {x["status"]})' for x in cands_] or
                      ['العائد ضميرٌ آخر في النطاق', 'العائد محذوفٌ بقاعدة']))

    # C01 (جسر): علاقات الشرط من الطبقة القديمة (المرحلة ١٤) تُنقل بهوياتها ومقدّماتها، لا يُعاد اشتقاقها ولا تُرفع رتبتها:
    # الأداة، وفعل الشرط، والجواب ورابطه، وملكية الجواب؛ ومرخّصة هناك ← LICENSED، ومرشّحة ← DEFERRED
    for c in legacy_cond or []:
        if not c['head'].startswith(ref + ':'):
            continue
        wloc = lambda l: int(l.split(':')[2]) - 1 if l else None
        hw = wloc(c['head'])
        tool = next((t for t in toks if t.wi == hw and 'عامل' in (t.lex or '') and t.text.endswith(c['tool'][-1:]) or
                     t.wi == hw and t.text == c['tool']), None) or next((t for t in toks if t.wi == hw and not t.conj), None)
        if tool is None:
            continue
        heads, members, prem, parts_st = {'tool': tool}, {'tool': [tool]}, [], {}
        for why, role in (('فعل الشرط', 'condition_verb'), ('جواب الشرط', 'answer')):
            pt = c['parts'].get(why)
            if not pt:
                parts_st[role] = ('غائب', 'لم يُكشف في الطبقة القديمة')
                continue
            nw = wloc(pt.get('nucleus') or pt.get('word'))
            u = next((t for t in toks if t.wi == nw and t.pos == 'فعل'), None) or \
                next((t for t in toks if t.wi == nw and not t.conj and not t.enclitic), None)
            if u is None:
                continue
            heads[role], members[role] = u, [u]
            parts_st[role] = (LICENSED if pt['status'] == 'مرخّصة' and pt.get('owned') else DEFERRED,
                              pt.get('bound_text') or '')
            prem.append(f'المرحلة ١٤ (LEGACY): {why} «{c["tool"]}» ← {pt.get("nucleus") or pt.get("word")}{f' [{pt.get("premise")}]' if pt.get("premise") else ''} → {pt["status"]}'
                        + ('' if pt.get('owned') else '؛ والموضع مملوكٌ لعلاقةٍ أخرى هناك'))
            if role == 'answer':
                lk = next((t for t in toks if t.wi == wloc(pt.get('word')) and t.conj), None)
                if lk is not None and 'فاء' in str(c.get('q_kind') or ''):
                    heads['linker'], members['linker'] = lk, [lk]
        ok = all(parts_st.get(r_, ('',))[0] == LICENSED for r_ in ('condition_verb', 'answer')) and not c['amb']
        # «إذا» بقرينة الفجائية (§٩): وجهان محفوظان، الشرطية والفجائية، والاختيار مؤجَّل؛ ولا ترخيص للشرط ووجه الفجائية منافسٌ قائم
        idha_faces = None
        if c['tool'].startswith('إِذَا'):
            from .algebra import idha_reading, IDHA_ROUTE
            op_ = next((o_ for o_ in a['operators'] if o_['word_index'] == tool.wi and o_['operator'] == 'إِذَا'), None)
            rd_ = idha_reading(a, op_) if op_ else None
            if rd_:
                idha_faces = [dict(face=x['face'], status=x['status'], why=x['why']) for x in rd_['faces']]
                if any(x['face'] == 'FUJAIYYA' and x['status'] in ('CONDITIONS_MET', 'CANDIDATE') for x in rd_['faces']):
                    ok = False
                prem.append(f"قرينة «إذا»: {rd_['cue']} — القرار {rd_['decision']}؛ ومسلك الفجائية غير مقبول "
                            f"(ويلسون {IDHA_ROUTE['wilson_low']} دون {IDHA_ROUTE['threshold']})، فلا يحذف الشرط")
        cv = heads.get('condition_verb')
        fc = getattr(cv, 'frame_cands', None) if cv is not None else None
        if fc:
            # المصالحة أولاً؛ ومقدّمة الطبقة القديمة القائمة على وجهٍ ممنوع في F01 تُوسَم به، فلا يبدأ السجلّ بتعليلٍ مُبطَل
            rej_t = {c_['tense'] for c_ in fc['rejected']}
            prem[:] = [p_ + (f' — قائمةٌ على وجهٍ ممنوع في F01 ({"، ".join(c_["id"] for c_ in fc["rejected"])}): لا يُبنى عليها'
                             if any(t_ and t_ in p_ for t_ in rej_t) and p_.startswith('المرحلة ١٤') else '') for p_ in prem]
            prem.insert(0, 'المصالحة مع F01: ' + ('المرشّح القائم ' + '، '.join(f"{c_['id']} ({c_['tense']}، {c_['voice']})" for c_ in fc['live'])) +
                        ('؛ ووجه ' + '، '.join(f"{c_['id']} ({c_['tense']})" for c_ in fc['rejected']) + ' ممنوعٌ في F01، فلا يُبنى عليه' if fc['rejected'] else '') +
                        '؛ ولا تُرفع رتبة الشرط بهذه المصالحة')
        R.append(_rec(ref, 'CONDITION', 'C01', heads, members, LICENSED if ok else DEFERRED,
                      ('الأداة وفعل الشرط والجواب مرخَّصةٌ في الطبقة القديمة بأدلتها، والجواب مملوكٌ للأداة' if ok else
                       'بعض أجزاء الشرط مرشّحةٌ أو غائبة في الطبقة القديمة: ' +
                       '، '.join(f'{COND_PART_AR.get(k_, k_)} {v_[0]}' for k_, v_ in parts_st.items() if v_[0] != LICENSED)) +
                      ('؛ والأداة ملتبسة (شرطية أو موصولة أو استفهامية)' if c['amb'] else ''),
                      premises=prem or [f'المرحلة ١٤: أداة شرط «{c["tool"]}» ({c["head"]})'],
                      parts_status={k_: v_[0] for k_, v_ in parts_st.items()}, legacy=dict(head=c['head'], q_kind=c.get('q_kind'),
                                                                                         obligations=c.get('obligations')),
                      alternatives=(['«إذا» ظرفٌ لما يُستقبل من الزمان متضمّنٌ معنى الشرط، وجوابه متعلَّقه أو دليله']
                                    if c['tool'].startswith('إِذَا') else []) +
                                   (['«إذا» الفجائية: تدخل على الجملة الاسمية ولا جواب لها'] if idha_faces else []),
                      **(dict(faces=idha_faces, selection=DEFERRED) if idha_faces else {})))

    # رتبة المقدّمات: العلاقة المرخَّصة لا تقوم على مقدّمةٍ غير مرخَّصة؛ وما قام عليها يُنزَّل إلى التأجيل بسببه (إلى الثبات)
    ids = {r_['relation_id']: r_ for r_ in R}
    changed = True
    while changed:
        changed = False
        for r_ in R:
            if r_['status'] != LICENSED:
                continue
            bad = [p_ for p_ in r_['premises'] if p_ in ids and ids[p_]['status'] != LICENSED]
            if bad:
                r_['reason_before_rank'] = r_['reason']
                r_['status'] = DEFERRED
                r_['reason'] = 'مقدّمةٌ غير مرخَّصة: ' + '، '.join(f'{p_} ({ids[p_]["status"]})' for p_ in bad) + \
                    ' — والعلاقة تحمل رتبة مقدّماتها'
                changed = True

    # ربط كل مقدّمةٍ بمرشّحها وعلاقتها الفعلية وحالتها (بعد رتبة المقدّمات): ما لم يربطه سجلُّه صراحةً يُربط بالسجل نفسه
    ids = {r_['relation_id']: r_ for r_ in R}
    for r_ in R:
        lk = r_.get('premise_links')
        if lk is None:
            lk = r_['premise_links'] = [dict(premise=p_, candidate='self', relation=p_ if p_ in ids else None,
                                             layer=None) for p_ in r_['premises']]
        for l_ in lk:
            if l_.get('relation') in ids:
                l_['status'] = ids[l_['relation']]['status']
    # امتداد المصدر المؤوَّل (SARF_MAJOR_CLOSURE_01 §6): المثبت منه أعضاءٌ بعلاقاتٍ مرخَّصة — الحرف، والفعل وضمائره المتصلة في كلمته،
    # والفاعل الظاهر المرخَّص، والمفاعيل المرخَّصة؛ وما بعدها إلى حدّ إطار الفعل امتدادٌ مرشّح حدّه غير مثبت. ولكلّ عضوٍ هويته
    for rec in [r_ for r_ in R if r_['type'] == 'MASDAR']:
        vt = by_uid_.get(rec['heads']['verb'])
        an = by_uid_.get(rec['heads']['harf'])
        if vt is None or an is None:
            continue
        fr_ = frames.get(vt.k)
        mem = [an.uid, vt.uid] + [t.uid for t in toks if t.wi == vt.wi and idx[t.k] > idx[vt.k]]
        why = ['الحرف والفعل (M02)'] + ([f'الضمير المتصل في كلمة الفعل'] if len(mem) > 2 else [])
        sj_ = ((fr_ or {}).get('frame') or {}).get('subject') or {}
        if sj_.get('status') == LICENSED and sj_.get('unit'):
            mem.append(sj_['unit'])
            why.append(f'الفاعل المرخَّص في الإطار ({fr_["relation_id"]})')
        for o_ in R:
            if o_['type'] == 'OBJECT' and o_['status'] == LICENSED and o_['heads'].get('verb') == vt.uid and o_['heads'].get('object') not in mem:
                mem.append(o_['heads']['object'])
                why.append(f'المفعول المرخَّص ({o_["relation_id"]})')
        mem = sorted(set(mem), key=lambda u: idx[by_uid_[u].k])
        fe2 = frame_end(idx[vt.k])
        last = max(idx[by_uid_[u].k] for u in mem)
        cand = [toks[j] for j in range(last + 1, fe2)]
        # حدّ الإطار ليس حدّ المصدر: نهاية الآية حدُّ مصدرٍ لا حدٌّ لغوي، والعاطف قد يعطف فعلاً داخل المصدر (أَنْ تَفۡعَلَ وَتَفۡعَلَ)،
        # وما له الصدارة يبدأ إطاراً بلا دليلٍ على انتهاء المصدر قبله (مراجعة 036)
        fe_why = ('نهاية الآية (حدُّ مصدرٍ لا حدٌّ لغوي)' if fe2 >= len(toks) else
                  f'عاطفٌ «{toks[fe2].text}» ({toks[fe2].loc}) يبدأ إطاراً، وقد يُعطف به فعلٌ داخل المصدر' if toks[fe2].conj else
                  f'«{toks[fe2].text}» ({toks[fe2].loc}) يبدأ إطاراً بالصدارة، ولا يثبت به انتهاء المصدر')
        rec['members']['extent'] = mem
        rec['positions']['extent'] = [by_uid_[u].loc for u in mem]
        rec['texts']['extent'] = ' '.join(by_uid_[u].text for u in mem)
        rec['extent'] = dict(proven=mem, proven_text=rec['texts']['extent'], evidence=why,
                             candidate=[t.uid for t in cand], candidate_text=' '.join(t.text for t in cand),
                             boundary_status=DEFERRED, frame_end=fe_why,
                             membership_note='عضوية الامتداد المثبت تعني علاقةً مرخَّصة بالفعل لكل عضو، ولا تثبت وحدها وظائف الأعضاء داخل المصدر ولا محلّه',
                             boundary_note=(f'لا شيء بعد الأعضاء المرخَّصة إلى حدّ إطار الفعل، وحدّ الإطار {fe_why}: نفاد البحث داخل الإطار '
                                            'لا يثبت حدّ المصدر' if not cand else
                                            f'ما بعد الأعضاء المرخَّصة إلى حدّ إطار الفعل ({cand[0].loc}–{cand[-1].loc}) امتدادٌ مرشّح لم تثبت '
                                            f'علاقاتُه بالفعل؛ وحدّ الإطار {fe_why}'))

    # أدوار العمل من العلاقات المرخَّصة وحدها (لا من المؤجَّل)
    by_uid = {t.uid: t for t in toks}
    for rec in R:
        if rec['status'] != LICENSED:
            continue
        hd = rec['heads']
        rid = rec['relation_id']
        if rec['type'] in ('PREDICATION', 'PREDICATIVE_PP') and hd.get('subject') in by_uid:
            by_uid[hd['subject']].roles.append(dict(src='ibtida', expected='رفع', rid=rid, role_name='مبتدأ', rule=rec['rule_id'],
                                                    face=rec.get('face') if rec.get('selection') == DEFERRED else None,
                                                    face_note=rec.get('face_note') if rec.get('selection') == DEFERRED else None))
        if rec['type'] == 'PREDICATION' and hd.get('predicate') in by_uid:
            by_uid[hd['predicate']].roles.append(dict(src='khabar', expected='رفع', rid=rid, role_name='خبر', rule=rec['rule_id'],
                                                      of=by_uid[hd['subject']].text))
        if rec['type'] == 'PP' and rec['rule_id'] == 'P01' and hd.get('complement') in by_uid:
            by_uid[hd['complement']].roles.append(dict(src='pp', expected='جر', rid=rid, role_name='مجرور بحرف الجر', rule='P01'))
        if rec['type'] == 'ADVP' and hd.get('complement') in by_uid:
            by_uid[hd['complement']].roles.append(dict(src='idafa', expected='جر', rid=rid, role_name='مضاف إليه', rule='P02',
                                                       of=by_uid[hd['adverb']].text))
        if rec['type'] == 'ADVP' and hd.get('adverb') in by_uid and 'نصب' in _written_mark(by_uid[hd['adverb']])[1]:
            # الظرفية دورٌ للظرف المنصوب كتابةً؛ والمجرور بجارٍّ قبله (مِن بَيۡنِ) اسمٌ مجرور لا ظرف
            by_uid[hd['adverb']].roles.append(dict(src='zarf', expected='نصب', rid=rid, role_name='ظرف', rule='P02'))
        if rec['type'] == 'IDAFA' and hd.get('mudaf_ilayh') in by_uid:
            by_uid[hd['mudaf_ilayh']].roles.append(dict(src='idafa', expected='جر', rid=rid, role_name='مضاف إليه', rule=rec['rule_id'],
                                                        of=by_uid[hd['mudaf']].text))
        if rec['type'] == 'OBJECT' and hd.get('object') in by_uid:
            by_uid[hd['object']].roles.append(dict(src='object', expected='نصب', rid=rid, role_name='مفعول به', rule=rec['rule_id'],
                                                   of=by_uid[hd['verb']].text))
        if rec['type'] == 'SUBJECT' and hd.get('subject') in by_uid:
            by_uid[hd['subject']].roles.append(dict(src='subject', expected='رفع', rid=rid, role_name=rec.get('role_name') or 'فاعل',
                                                    rule='S01', of=by_uid[hd['verb']].text,
                                                    face=rec.get('face') if rec.get('selection') == DEFERRED else None,
                                                    face_note=rec.get('face_note') if rec.get('selection') == DEFERRED else None))
        if rec['type'] == 'VOC_FOLLOWER' and hd.get('follower') in by_uid:
            by_uid[hd['follower']].roles.append(dict(src='voc_follower', expected='رفع', rid=rid, rule='V02',
                                                     role_name=ROLE_NAME['voc_follower']))
        if rec['type'] == 'NASIKH' and hd.get('khabar') in by_uid and rec.get('members', {}).get('khabar') == [hd['khabar']]:
            kt = by_uid[hd['khabar']]
            if kt.k not in span_of:
                kt.roles.append(dict(src='nasikh', expected='نصب' if rec.get('nasikh_group') == NASIKH_KANA else 'رفع', rule='V01',
                                     rid=rid, of=by_uid[hd['nasikh']].text, role_name=f'خبر «{by_uid[hd["nasikh"]].text}»'))
    # المبني بلا دور: أربع حالاتٍ لا تُخلط — لا محلّ مثبت (حرفٌ أو فعل)، ومحلٌّ غير محسوم (علاقةٌ مؤجَّلة تسمّيه)،
    # وقاعدة الدور غير منفّذة، ودليلٌ سابق غير موصول (سمةٌ مثبتة في المرحلة ١٣ لم تستوفِ قاعدة هذه الطبقة)
    ROLE_BEARING = ('SUBJECT', 'OBJECT', 'IDAFA', 'NASIKH', 'PREDICATION', 'PREDICATIVE_PP', 'VOC_FOLLOWER', 'ADVP')
    for t in toks:
        mabni = (t.lex or '') in ('مبني', 'مبني+عامل') or t.mcat is not None or t.enclitic
        op_unit = ('عامل' in (t.lex or '') or str(t.pos or '').startswith('عامل')) and not t.nounish() and t.pos != 'فعل'
        if not (mabni or op_unit) or t.roles:
            continue
        kw = MCAT_KW.get('attached_pronoun' if t.enclitic else t.mcat, 'مبني')
        pend = [r_ for r_ in R if r_['status'] != LICENSED and r_['type'] in ROLE_BEARING and
                any(t.uid in us for k_, us in r_['members'].items() if k_ not in ('relative',))]
        ec = t.feats.get('enclitic_case') or {}
        if op_unit or t.mcat == 'particle' or t.conj:
            us_ = t.usage or {}
            from .protected import MERGED
            mg = MERGED.get((t.G.Theta.get('protected') or {}).get('identity') or t.text)
            ids_ = list(mg) if mg else [s_['text'] for s_ in t.slots if s_['type'] == 'مبني'] + \
                sorted({u['operator'] for u in us_.get('accepted', [])} or
                       {u['operator'] for u in us_.get('alternatives', []) if u.get('status') != 'blocked'}) or [t.text]
            acc = [u['group'] for u in (t.usage or {}).get('accepted', [])]
            if not _LEX:
                from .lexicon import MabniLexicon
                _LEX.append(MabniLexicon())
            cats = [{e.get('category') for e in (_LEX[0].lookup(x) or [])} for x in ids_]
            if all(c_ == {'particle'} for c_ in cats):
                t.mabni_state = dict(code='NO_MAHALL', text='حرفٌ مبني لا محلّ له من الإعراب (ملف المبنيات: كل مداخل «' +
                                     '»، «'.join(ids_) + '» حروف)', evidence='lexicon/mabniyat_lexicon.jsonl')
            elif all('particle' in c_ for c_ in cats) and acc and all(str(g_) == JARR for g_ in acc):
                t.mabni_state = dict(code='NO_MAHALL', text=f'حرف جرٍّ في استعماله المقبول (مج 1)، وله في ملف المبنيات مدخلٌ حرفي: لا محلّ له',
                                     evidence='المرحلة ١١ + ملف المبنيات')
            elif any(c_ - {'particle'} for c_ in cats):
                t.mabni_state = dict(code='ROLE_RULE_NOT_IMPLEMENTED',
                                     text='للأداة في ملف المبنيات مداخل اسمية (' + '، '.join(sorted(CAT_AR.get(c_, c_) for c_ in set().union(*cats) - {'particle'})) +
                                     '): محلّها إن كانت اسماً لم يُعيَّن، وقاعدة تعيينه غير منفّذة', evidence=None)
            else:
                t.mabni_state = dict(code='LEXICAL_ENTRY_MISSING', text='لا مدخل لها في ملف المبنيات: صنفها ومحلّها غير معيَّنين (مدخلٌ معجمي ناقص)',
                                     evidence=None)
        elif ec.get('v') and ec.get('st') == 'مثبت':
            t.mabni_state = dict(code='EVIDENCE_NOT_ADOPTED',
                                 text=f'دليلٌ سابق غير موصول: المرحلة ١٣ تحكم بمحلّ {ec["v"]} ({ec.get("ev")})، ولم تستوفِ قاعدة هذه الطبقة: ' +
                                 ('؛ '.join(r_['reason'] for r_ in pend) or 'لا قاعدة تربط مضيفه'),
                                 evidence=[r_['relation_id'] for r_ in pend])
        elif pend:
            t.mabni_state = dict(code='MAHALL_UNRESOLVED', text='المحلّ غير محسوم: علاقةٌ مؤجَّلة تسمّيه — ' +
                                 '؛ '.join(f'{r_["rule_id"]}: {r_["reason"]}' for r_ in pend[:2]), evidence=[r_['relation_id'] for r_ in pend])
        else:
            t.mabni_state = dict(code='ROLE_RULE_NOT_IMPLEMENTED',
                                 text=f'{kw} مبني؛ دوره ومحلّه في هذا التركيب لم يُرخَّصا بعد في النظام (قاعدة الدور غير منفّذة)', evidence=None)
    parts_reg = {p_['part_id']: dict(unit=t.uid, text=p_['text'], part=p_['part'], slot=p_.get('slot'))
                 for t in toks for p_ in (getattr(t, 'parts', None) or [])}
    return dict(records=R, tokens=[(t.uid, t.loc, t.text) for t in toks], parts=parts_reg,
                axes={t.uid: t.axes(toks[i + 1] if i + 1 < len(toks) else None) for i, t in enumerate(toks)})


def _letter_syllables(t, seg):
    """لكل حرفٍ مجمَّع (الحرف بحركاته) في نص الوحدة: أرقام مقاطعه في الوحدة. ولام «أل» الشمسية بلا مقطع، والمشدَّد في مقطعين"""
    syl = (seg['units'][t.ui].get('syllables') or [])
    # المقاطع تكتب الهمزة «ء» على كل كرسيّ: تُقابَل صور الهمزة بها في هذه المحاذاة وحدها (والحركات كما هي)
    hz = {'أ': 'ء', 'إ': 'ء', 'آ': 'ء', 'ؤ': 'ء', 'ئ': 'ء'}
    lt = [(hz.get(c, c), m) for c, m in letters(t.text)]
    sylL = [[hz.get(c, c) for c, _ in letters(x['syl'])] for x in syl]
    flat = [(n, c) for n, cs in enumerate(sylL) for c in cs]
    out_map, fi = [], 0
    for n, (c, m) in enumerate(lt):
        hit = []
        if c == 'ل' and n + 1 < len(lt) and SHADDA in lt[n + 1][1] and not m - {SUKUN} and n > 0:
            out_map.append([])
            continue
        for _ in range(2 if SHADDA in m else 1):
            while fi < len(flat) and flat[fi][1] != c and c not in 'اوىي':
                fi += 1
            if fi < len(flat) and flat[fi][1] == c:
                hit.append(flat[fi][0])
                fi += 1
        out_map.append(sorted(set(hit)))
    return out_map


def _merged_part_spans(t, seg, texts):
    """مجالات أجزاء الوحدة المندمجة رسماً (أَيُّهَا = أَيُّ + هَا، مِمَّنْ = مِنْ + مَنْ) بنظام المحارف نفسه (الحروف المجمَّعة
    في نص الوحدة، نصف مفتوح)، ومقاطعها. فإن زاد مجموع حروف الأجزاء على حروف الوحدة بحرفٍ مشدَّدٍ عند الحدّ، فالحرف المدغم
    مشتركٌ بين الجزأين ويُعلن ذلك. → [(span, syllables, note)] أو None"""
    lt = letters(t.text)
    ns = [len(letters(x)) for x in texts]
    om = _letter_syllables(t, seg)
    if len(ns) != 2:
        return None
    over = sum(ns) - len(lt)
    if over == 0:
        sp = [[0, ns[0]], [ns[0], len(lt)]]
        note = None
    elif over == 1 and ns[0] - 1 < len(lt) and SHADDA in lt[ns[0] - 1][1]:
        sp = [[0, ns[0]], [ns[0] - 1, len(lt)]]
        note = f'«{lt[ns[0] - 1][0]}» المشدَّد مشتركٌ بين الجزأين: آخر الأول مدغمٌ في أول الثاني'
    else:
        return None
    return [(x, sorted({s_ for n in range(x[0], x[1]) for s_ in (om[n] if n < len(om) else [])}), note) for x in sp]


def _parts_map(t, seg):
    """أجزاء الوحدة المكتوبة الواحدة (لِلشَّهَٰدَةِ = لِ + ال + شَّهَٰدَةِ): لكلّ جزءٍ هويته (الوحدة/الخانة)، ونصّه، ومجاله في محارف الكلمة،
    ونوعه، ومقاطعه بأرقامها في الوحدة. ولام «أل» قبل الحرف الشمسي المشدَّد مدغمةٌ فيه: لا مقطع لها، ويُذكر ذلك"""
    kinds = {'عامل': 'حرف جر', 'أل': 'أداة تعريف', 'جذع': 'اسم مجرور', 'لفظ الجلالة': 'اسم مجرور', 'مبني': 'مبني'}
    sl = t.slots
    syl = (seg['units'][t.ui].get('syllables') or [])
    # محاذاة الحروف بالمقاطع: الحرف الشمسي المشدَّد يُعدّ مرتين (ساكنٌ في آخر المقطع، ومتحرّكٌ في أول ما بعده)
    lt = letters(t.text)
    pos_syl, si, k = [], 0, 0
    sylL = [[c for c, _ in letters(x['syl'])] for x in syl]
    flat = [(n, c) for n, cs in enumerate(sylL) for c in cs]
    out_map = []
    fi = 0
    for n, (c, m) in enumerate(lt):
        hit = []
        if c == 'ل' and n + 1 < len(lt) and SHADDA in lt[n + 1][1] and not m - {SUKUN} and n > 0:
            out_map.append([])                      # لام «أل» الشمسية: لا تُنطق
            continue
        reps = 2 if SHADDA in m else 1
        for _ in range(reps):
            while fi < len(flat) and flat[fi][1] != c and c not in 'اوىي':
                fi += 1
            if fi < len(flat) and flat[fi][1] == c:
                hit.append(flat[fi][0])
                fi += 1
        out_map.append(sorted(set(hit)))
    parts = []
    for x in sl:
        a0, a1 = x.get('span') or (0, 0)
        sy = sorted({s_ for n in range(a0, min(a1, len(out_map))) for s_ in out_map[n]})
        parts.append(dict(part=kinds.get(x['type'], x['type']), text=x.get('text'), slot=x['index'], unit=t.uid, span=[a0, a1],
                          part_id=f'{t.uid}/s{x["index"]}', syllables=sy,
                          note='لام «أل» مدغمةٌ في الحرف الشمسي بعدها: لا مقطع لها، وأثرها الشدّة' if x['type'] == 'أل' and not sy else None))
    return parts


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
        if (g.get('capacity') or g.get('capacity_mediated')) and exp not in (g.get('capacity') or []) and \
                exp not in (g.get('capacity_mediated') or []):
            if inf.get('agreement') != 'CONFLICT':
                bad.append(f'{uid}: قدرة «{g.get("operator")}» {g["capacity"]} لا تشمل «{exp}» ولم يُسجَّل تعارض')
        if inf.get('agreement') == 'AGREE' and g.get('kind') == 'عامل' and exp not in (g.get('capacity') or []) and \
                exp not in (g.get('capacity_mediated') or []):
            bad.append(f'{uid}: AGREE و«{exp}» خارج قدرة استعمال «{g.get("operator")}» (لفظاً {g.get("capacity")}، '
                       f'وبوساطة {g.get("capacity_mediated")})')
        if inf.get('agreement') == 'AGREE' and g.get('relation') == 'بوساطة (في الجرد)' and exp not in (g.get('capacity_mediated') or []):
            bad.append(f'{uid}: العلاقة «بوساطة» ولا وساطة في سجل العامل')
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
            if g.get('kind') == 'عامل' and not g.get('role_name') and g.get('operator') and \
                    f'«{g["operator"]}»' not in (st or '') and 'مضمرةً بعد' not in (st or ''):
                bad.append(f'{uid}: العبارة «{st}» لا تسمّي العامل المسجَّل «{g["operator"]}»')
            if g.get('role_name') and g['role_name'] not in (st or ''):
                bad.append(f'{uid}: العبارة «{st}» لا تذكر الدور المرخَّص «{g["role_name"]}»')
            if g.get('role_name') and g.get('relation_status') not in (None, LICENSED):
                bad.append(f'{uid}: دورٌ من علاقةٍ غير مرخَّصة ({g.get("relation_status")}) مع AGREE')
        elif st and any(w in st for w in STATE_ADJ.values()) and 'محلّ' not in st:
            bad.append(f'{uid}: عبارة إعرابٍ بلا اتفاق ({inf.get("agreement")})')
    return bad


def check_records(records, tokens, parts=None):
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
        for role, pid in (r.get('head_parts') or {}).items():
            if parts is None:
                continue
            if pid not in parts:
                errs.append(f'{rid}: جزء الطرف «{role}» {pid} غير مسجَّل في أجزاء الوحدات')
            elif parts[pid]['unit'] != r['heads'].get(role):
                errs.append(f'{rid}: جزء الطرف «{role}» {pid} من وحدةٍ غير رأس الطرف ({parts[pid]["unit"]} ≠ {r["heads"].get(role)})')
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
        if r['status'] == LICENSED:
            for p in r['premises']:
                if p in ids and ids[p]['status'] != LICENSED:
                    errs.append(f"{r['relation_id']}: مرخَّصٌ ومقدّمته {p} غير مرخَّصة ({ids[p]['status']}): رتبة العلاقة فوق رتبة مقدّمتها")
    for r in records:
        if r['status'] == LICENSED and r['premises'] and all(p in ids for p in r['premises']):
            errs.append(f"{r['relation_id']}: مقدّماته كلها علاقاتٌ بلا حقيقةٍ مصدرية مستقلة")
    for r in records:
        for role_, pid_ in (r.get('head_parts') or {}).items():
            if pid_ and f'{role_}={pid_}' not in r['relation_id']:
                errs.append(f'{r["relation_id"]}: الطرف «{role_}» جزءٌ ({pid_}) ومعرّف العلاقة لا يحمل هويته')
    return errs


def check_cross(records, axes):
    """فاحصٌ عابرٌ للطبقات بهوية التحليل نفسها: → [الخلل].
    ١ العلامة في مقدّمة العلاقة (mark_fact، أو «الرفع مكتوب (X)») هي العلامة نفسها في محور الوحدة المسمّاة.
    ٢ دور المحور (role_name) مصدره علاقةٌ موجودة مرخَّصة، والوحدة من أعضائها.
    ٣ امتداد شبه الجملة (complement_ext) لا يكون بلا سجلّ إضافةٍ مرخَّص في مقدّماتها"""
    import re
    errs = []
    ids = {r['relation_id']: r for r in records}
    txt_uid = {}
    for r in records:
        for role, us in r['members'].items():
            for u, tx in zip(us, (r['texts'].get(role) or '').split(' ')):
                txt_uid.setdefault((r['relation_id'], tx), u)
    for r in records:
        facts = []
        if r.get('mark_fact'):
            facts.append((r['mark_fact']['uid'], r['mark_fact']['mark'], 'mark_fact'))
        for p in r['premises']:
            m = re.match(r'^«(.+?)»: الرفع مكتوب \((.+?)\)', str(p))
            if m:
                u = txt_uid.get((r['relation_id'], m.group(1)))
                if u:
                    facts.append((u, m.group(2), p))
        for u, mk, src in facts:
            inf = (axes.get(u) or {}).get('inflection') or {}
            am = inf.get('mark')
            if u not in axes:
                errs.append(f"{r['relation_id']}: مقدّمةٌ تسمّي وحدةً غير موجودة {u}")
            elif am and mk and am[0] != mk:
                errs.append(f"{r['relation_id']}: العلامة في المقدّمة «{mk}» غير علامة المحور «{am[0]}» للوحدة {u} ({src})")
        if r['members'].get('complement_ext') and not any(p in ids and ids[p]['type'] == 'IDAFA' and ids[p]['status'] == LICENSED
                                                           for p in r['premises']):
            errs.append(f"{r['relation_id']}: امتداد المكمّل بلا إضافةٍ مرخَّصة في مقدّماته")
    for u, ax in axes.items():
        g = (ax.get('inflection') or {}).get('governor') or {}
        idn = ax.get('identity') or {}
        if idn and idn.get('unit') != u:
            errs.append(f'{u}: هوية المحور لوحدةٍ أخرى ({idn.get("unit")})')
        if idn and g.get('kind') == 'عامل' and g.get('target_slot') is not None and g['target_slot'] not in idn.get('slots', []):
            errs.append(f'{u}: معمول العامل في المرحلة ١١ الخانة {g["target_slot"]}، وليست من خانات الوحدة {idn.get("slots")}')
        if idn and g.get('kind') == 'عامل' and g.get('target_word') is not None and \
                not any(x.startswith(f"A{idn['loc'].rsplit(':', 1)[0]}:{g['target_word'] + 1}.") for x in idn.get('stage11', [])):
            errs.append(f'{u}: معمول العامل في المرحلة ١١ في كلمةٍ أخرى ({g["target_word"] + 1})')
        if g.get('role_name') and g.get('relation_id') and g['relation_id'] in ids and idn:
            r_ = ids[g['relation_id']]
            if idn['analysis_id'] not in (r_.get('analysis_id') or '') and \
                    not any(u in us for k_, us in r_['members'].items()):
                errs.append(f'{u}: هوية التحليل {idn["analysis_id"]} غائبةٌ عن علاقة دوره')
        if g.get('role_name') and g.get('relation_id'):
            r = ids.get(g['relation_id'])
            if r is None:
                errs.append(f'{u}: الدور «{g["role_name"]}» من علاقةٍ غير موجودة {g["relation_id"]}')
            elif r['status'] != LICENSED:
                errs.append(f'{u}: الدور «{g["role_name"]}» من علاقةٍ {r["status"]}')
            elif not any(u in us for us in r['members'].values()):
                errs.append(f'{u}: الدور «{g["role_name"]}» من علاقةٍ ليست الوحدة من أعضائها')
    # ٥ ترخيص الوجه غير اختياره: الإسناد المرخَّص داخل صلةٍ نوعها غير مختار يحمل وجهه واختياره المؤجَّل،
    #   ودور محوره يسمّي الوجه؛ ولا يُنزَّل وجهٌ مرخَّص لوجود منافس، ولا يُرقّى وجهٌ فوق دليله
    for r in records:
        if r['type'] == 'SILAH' and r.get('kind_status') == DEFERRED and len(r.get('silah_kinds') or []) > 1:
            for k_ in r['silah_kinds']:
                src_ = ids.get(k_.get('source'))
                if src_ is not None and src_['status'] != k_['status']:
                    errs.append(f'{r["relation_id"]}: ترخيص الوجه {k_.get("id")} ({k_["status"]}) غير حالة علاقته {src_["relation_id"]} ({src_["status"]})')
                for n2 in records:
                    if n2['type'] == 'PREDICATIVE_PP' and n2.get('container_id') == k_.get('source') and n2['status'] == LICENSED \
                            and n2.get('selection') != DEFERRED:
                        errs.append(f'{n2["relation_id"]}: إسنادٌ مرخَّص في وجهٍ غير مختار بلا اختيارٍ مؤجَّل ({r["relation_id"]})')
    for u, ax in axes.items():
        g = (ax.get('inflection') or {}).get('governor') or {}
        r = ids.get(g.get('relation_id'))
        if r is not None and r.get('selection') == DEFERRED and g.get('role_name') and not g.get('face'):
            errs.append(f'{u}: الدور «{g["role_name"]}» من وجهٍ غير مختار ({r["relation_id"]}) بلا تسمية وجهه')
    # ٧ هوية المرشّح: لا تأخذ الوحدة سماتها في الطبقات من مرشّحين مختلفين — الزمن المثبت في الإطار يوافق البناء في المحور
    #   وأثر العامل، والبناء للمعلوم والمجهول المثبت يوافق دور المسند إليه
    for r in records:
        if r['type'] != 'VERB_FRAME':
            continue
        fr = r.get('frame') or {}
        vu = r['heads'].get('verb')
        ax = axes.get(vu) or {}
        inf = ax.get('inflection') or {}
        tense, tst = (fr.get('tense') or (None, None))[:2]
        voice, vst = (fr.get('voice') or (None, None))[:2]
        bld = (inf.get('build') or (None,))[0]
        if tst == 'مثبت' and tense in ('ماضٍ', 'أمر') and bld == 'معرب':
            errs.append(f'{vu}: الزمن المثبت في الإطار «{tense}» والمحور يقول «معرب» — سماتٌ من مرشّحين مختلفين')
        if tst == 'مثبت' and tense == 'مضارع' and bld == 'مبني' and 'نون' not in str((inf.get('build') or (None, ''))[1]):
            errs.append(f'{vu}: الزمن المثبت في الإطار «مضارع» والمحور يقول «مبني» بلا نونٍ مكتوبة — سماتٌ من مرشّحين مختلفين')
        g = inf.get('governor') or {}
        if tst == 'مثبت' and tense != 'مضارع' and g.get('kind') == 'عامل' and g.get('expected') in ('جزم', 'نصب'):
            errs.append(f'{vu}: عاملٌ يقتضي «{g.get("expected")}» على فعلٍ زمنه المثبت «{tense}» — سماتٌ من مرشّحين مختلفين')
        if vst == 'مثبت' and voice in ('معلوم', 'مجهول'):
            want = 'نائب فاعل' if voice == 'مجهول' else 'فاعل'
            for s_ in records:
                if s_['type'] == 'SUBJECT' and s_['heads'].get('verb') == vu and s_.get('role_name') and s_['role_name'] != want:
                    errs.append(f'{s_["relation_id"]}: الدور «{s_["role_name"]}» والبناء المثبت في الإطار «{voice}» — سماتٌ من مرشّحين مختلفين')
    # ٦ ربط المقدّمات: كل رابطٍ يسمّي علاقةً موجودة، ومقدّمته (إن كانت معرّف علاقة) هي العلاقة نفسها،
    #   وحالته المسجّلة حالتها الفعلية؛ ومرشّحه من مرشّحات السجل أو أوجهه
    for r in records:
        for l_ in r.get('premise_links') or []:
            rel_ = l_.get('relation')
            if rel_ is not None and rel_ not in ids:
                errs.append(f'{r["relation_id"]}: رابط مقدّمةٍ إلى علاقةٍ غير موجودة {rel_}')
            elif rel_ is not None and l_.get('premise') is not None and l_['premise'] != rel_:
                errs.append(f'{r["relation_id"]}: المقدّمة {l_["premise"]} مربوطةٌ بعلاقةٍ أخرى {rel_}')
            elif rel_ is not None and l_.get('status') is not None and l_['status'] != ids[rel_]['status']:
                errs.append(f'{r["relation_id"]}: حالة المقدّمة {rel_} المسجّلة {l_["status"]} غير حالتها {ids[rel_]["status"]}')
            cids = {x.get('id') for x in (r.get('silah_kinds') or []) + ((r.get('resumptive') or {}).get('candidates') or [])} | {'self'}
            if l_.get('candidate') is not None and l_['candidate'] not in cids:
                errs.append(f'{r["relation_id"]}: مقدّمةٌ مربوطة بمرشّحٍ غير موجود {l_["candidate"]}')
        for p_ in r['premises']:
            if r.get('premise_links') is not None and not any(l_.get('premise') == p_ for l_ in r['premise_links']):
                errs.append(f'{r["relation_id"]}: مقدّمةٌ بلا رابط: {str(p_)[:60]}')
    # ١٠ هوية المرشّح الصرفي: زمن الإطار هو زمن مرشّحه، ومن أزمنته القائمة لا الممنوعة؛ ومحور الفعل يحمل هوية مرشّح إطاره نفسها
    ax_c = {u: (ax.get('identity') or {}).get('morph_candidate') for u, ax in axes.items()}
    for r in records:
        if r['type'] != 'VERB_FRAME':
            continue
        fc = (r.get('frame') or {}).get('candidate') or {}
        if not fc:
            continue
        t_ = (r['frame'].get('tense') or (None,))[0]
        if fc.get('tense') is not None and t_ != fc['tense']:
            errs.append(f'{r["relation_id"]}: زمن الإطار «{t_}» غير زمن مرشّحه «{fc["tense"]}»')
        if t_ is not None and fc.get('tense') is not None and t_ in (fc.get('tense_rejected') or {}):
            errs.append(f'{r["relation_id"]}: زمن الإطار «{t_}» وجهٌ ممنوع: {fc["tense_rejected"][t_]}')
        if fc.get('tense') is not None and fc.get('tense_live') and fc['tense'] not in fc['tense_live']:
            errs.append(f'{r["relation_id"]}: زمن المرشّح «{fc["tense"]}» ليس من أزمنته القائمة {_join_ar(fc["tense_live"])}')
        vu = r['heads'].get('verb')
        if vu in ax_c and ax_c[vu] is not None and ax_c[vu] != fc.get('id'):
            errs.append(f'{r["relation_id"]}: هوية المرشّح في المحور «{ax_c[vu]}» غير هوية مرشّح الإطار «{fc.get("id")}»')
    # ٨ ما له بدائل خارج التغطية لا يكون مختاراً ولا مكتمل البحث (الترخيص وجهٌ لا اختيار)
    for r in records:
        if (r.get('search_scope') or {}).get('outside_coverage'):
            if r.get('selection') != DEFERRED:
                errs.append(f'{r["relation_id"]}: بدائل خارج التغطية ({_join_ar(r["search_scope"]["outside_coverage"])}) والاختيار غير مؤجَّل')
            if r.get('search_status') == SEARCH_COMPLETE:
                errs.append(f'{r["relation_id"]}: بدائل خارج التغطية والبحث موسومٌ بالاكتمال')
    # ٩ المصدر المؤوَّل: وظيفته المرخَّصة تسمّي حاكمها المكتوب
    for r in records:
        if r['type'] == 'MASDAR' and (r.get('function') or {}).get('status') == LICENSED and not r['function'].get('governor'):
            errs.append(f'{r["relation_id"]}: وظيفة المصدر المؤوَّل مرخَّصة بلا حاكمٍ مكتوب')
    return errs
