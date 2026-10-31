# -*- coding: utf-8 -*-
"""
sarf.protected — بوابة الحماية الدستورية (حكم صاحب النظرية، 31 أكتوبر):

    لا يُستخرج جذرٌ للعوامل المائة، ولا للمبنيات، ولا للأسماء الذهبية (Golden Names)، ومنها لفظ الجلالة
    وإبراهيم وإسحاق وداود وأشباهها المحددة في الجرد المعتمد. وتُحفظ هذه الوحدات بهويتها المعجمية ورسمها
    وخصائصها، دون فرض تحليل جذري وزني عليها. وهذا حكم تمثيلٍ داخل المشروع لا يتوقف على جذرٍ تقترحه مدوّنةٌ خارجية.

تُطبَّق البوابة قبل توليد مرشّحات الجذر، على صيغ الوحدة المحمية (تصريف العوامل الفعلية: لَسۡتُمۡ، كُنتُمۡ، يَكَادُ)
وعلى اتصال السوابق (وَ، فَ، أَ، لَ، بِ، كَ، سَ، يَا) والضمائر المتصلة بها (إِنَّا، لَعَلَّكُمۡ، رَأَيۡتَهُمۡ)، لا بمطابقة
الكلمة كاملةً وحدها. والمطابقة بالحروف والحركات معاً (يُمنع تجريد الكلمة من الحركات).

→ protected(text) = None، أو dict(cls, identity, form, proclitics, enclitic, ambiguous, alternative, source)
   والسجل: root_status = NOT_APPLICABLE، reason = CONSTITUTIONAL_PROTECTED_CLASS؛ فإن احتمل الموضع وحدةً محمية
   وتحليلاً آخر (أفعال القلوب، وساء، وما يشترك لفظه من الأعلام) حُفظ البديل وأُجِّل تعيين الفئة، والحماية باقية
"""
import os, json
from functools import lru_cache
from .chars import FATHA, DAMMA, KASRA, SUKUN, SHADDA
from .match import match_letters
from .divine import divine_name

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
NOT_APPLICABLE = 'NOT_APPLICABLE'
REASON = 'CONSTITUTIONAL_PROTECTED_CLASS'
CLASS_OPERATOR, CLASS_MABNI, CLASS_GOLDEN = 'عامل من العوامل المائة', 'مبني', 'اسم ذهبي'

# ---------- الأسماء الذهبية: الجرد المعتمد (أعلام القرآن بأصولها، والآخر بلا حركة: يقبل كل حركة إعراب) ----------
GOLDEN = ('إِبْرَٰهِيم', 'إِبْرَٰهِم', 'إِبْرَاهِيم', 'إِسْمَٰعِيل', 'إِسْحَٰق', 'يَعْقُوب', 'يُوسُف', 'دَاوُۥد', 'دَاوُد',
          'سُلَيْمَٰن', 'أَيُّوب', 'يُونُس', 'زَكَرِيَّا', 'يَحْيَى', 'إِلْيَاس', 'إِلْيَاسِين', 'ٱلْيَسَع', 'يَسَع',
          'لُوط', 'نُوح', 'هُود', 'صَٰلِح', 'شُعَيْب', 'مُوسَى', 'هَٰرُون', 'عِيسَى', 'مَرْيَم', 'عِمْرَٰن', 'ءَادَم',
          'إِدْرِيس', 'ذَا ٱلْكِفْل', 'عُزَيْر', 'لُقْمَٰن', 'مُحَمَّد', 'أَحْمَد', 'ءَازَر', 'جِبْرِيل', 'مِيكَىٰل', 'إِبْلِيس',
          'فِرْعَوْن', 'هَٰمَٰن', 'قَٰرُون', 'طَالُوت', 'جَالُوت', 'هَٰرُوت', 'مَٰرُوت', 'يَأْجُوج', 'مَأْجُوج', 'تُبَّع',
          'إِسْرَٰءِيل', 'إِسْرَٰٓءِيل', 'ثَمُود', 'عَاد', 'مَدْيَن', 'إِرَم', 'مِصْر', 'بَابِل', 'بَكَّة', 'مَكَّة', 'يَثْرِب',
          'سَيْنَاء', 'سِينِين', 'آدَم', 'ءَادَم', 'طُوًى', 'ٱلْجُودِيّ', 'عَرَفَٰت', 'ٱلرُّوم', 'قُرَيْش', 'ٱللَّٰت', 'ٱلْعُزَّىٰ', 'مَنَوٰة',
          'يَغُوث', 'يَعُوق', 'سُوَاع', 'بَعْل', 'ٱلسَّامِرِيّ', 'رَمَضَان', 'ٱلْأَيْكَة', 'لَيْكَة')
# ما يشترك لفظه بالعلم وغيره (صَٰلِحًا صفة، هُودًا اليهود، وَدًّا وَنَسۡرًا): الحماية مرشَّحة والفئة مؤجَّلة
GOLDEN_AMBIGUOUS = {'صَٰلِح', 'هُود', 'بَعْل', 'عَاد', 'طُوًى', 'يَحْيَى'}

# ---------- العوامل الفعلية: تصريفها (العامل محمي بكل صيغه) ----------
def _madi(s3, s1):
    out = [s3 + FATHA, s3 + FATHA + 'ا', s3 + DAMMA + 'وا', s3 + FATHA + 'تْ', s3 + FATHA + 'تَا']
    for suf in ('تُ', 'تَ', 'تِ', 'تُمَا', 'تُمْ', 'تُنَّ', 'نَا', 'نَ', 'تُمُو'):
        if s1.endswith('ن') and suf.startswith('ن'):
            out.append(s1 + SHADDA + suf[1:])          # كُنَّا، كُنَّ
        else:
            out.append(s1 + SUKUN + suf)
    return out


def _mudari(v, m, j):
    out = []
    for p in ('ي', 'ت', 'أ', 'ن'):
        pre = p + v
        out += [pre + m + DAMMA, pre + m + FATHA, pre + m + DAMMA + 'ونَ', pre + m + DAMMA + 'وا', pre + m + FATHA + 'انِ',
                pre + m + FATHA + 'ا', pre + m + KASRA + 'ينَ', pre + m + KASRA + 'ي', pre + j,
                pre + m + FATHA + 'نَّ', pre + m + DAMMA + 'نَّ', pre + m + KASRA + 'نَّ']   # نون التوكيد: تَكُونَنَّ
    return out


VERBAL = {   # الفعل ← (الصيغ، ملتبسٌ بفعلٍ تامٍّ غير عامل؟)
    'كَانَ': (_madi('كَان', 'كُن') + _mudari(FATHA, 'كُون', 'كُنْ') + ['كُنْ', 'كُونُوا', 'كُونِي', 'كُونَا', 'يَكُ', 'تَكُ',
                                                                     'أَكُ', 'نَكُ'], False),
    'صَارَ': (_madi('صَار', 'صِر') + _mudari(FATHA, 'صِير', 'صِرْ'), False),
    'أَصْبَحَ': (_madi('أَصْبَح', 'أَصْبَح') + _mudari(DAMMA, 'صْبِح', 'صْبِحْ'), False),
    'أَمْسَى': (['أَمْسَى', 'أَمْسَوْا', 'أَمْسَتْ', 'أَمْسَيْتُ', 'أَمْسَيْتُمْ', 'يُمْسِي', 'تُمْسُونَ', 'تُمْسِي'], False),
    'أَضْحَى': (['أَضْحَى', 'أَضْحَوْا', 'أَضْحَتْ', 'يُضْحِي'], False),
    'ظَلَّ': (['ظَلَّ', 'ظَلَّتْ', 'ظَلُّوا', 'ظَلْتَ', 'ظَلْتُمْ', 'ظَلِلْتُمْ', 'ظَلِلْتَ', 'ظَلَلْتُ', 'يَظَلُّ', 'تَظَلُّ',
              'يَظْلَلْنَ', 'نَظَلُّ', 'فَنَظَلُّ'], False),
    'بَاتَ': (_madi('بَات', 'بِت') + _mudari(FATHA, 'بِيت', 'بِتْ'), False),
    'زَالَ': (_madi('زَال', 'زِل') + _mudari(FATHA, 'زَال', 'زَلْ'), False),
    'بَرِحَ': (_madi('بَرِح', 'بَرِح') + _mudari(FATHA, 'بْرَح', 'بْرَحْ'), False),
    'فَتِئَ': (_madi('فَتِئ', 'فَتِئ') + _mudari(FATHA, 'فْتَأ', 'فْتَأْ') + ['تَفْتَؤُا'], False),
    'دَامَ': (_madi('دَام', 'دُم'), False),
    'لَيْسَ': (_madi('لَيْس', 'لَس'), False),
    'عَسَى': (['عَسَى', 'عَسَيْتُمْ', 'عَسَيْتُ', 'عَسَيْنَا'], False),
    'كَادَ': (_madi('كَاد', 'كِد') + _mudari(FATHA, 'كَاد', 'كَدْ'), False),
    'كَرَبَ': (_madi('كَرَب', 'كَرَب'), False),
    'أَوْشَكَ': (_madi('أَوْشَك', 'أَوْشَك') + _mudari(DAMMA, 'وشِك', 'وشِكْ'), False),
    'نِعْمَ': (['نِعْمَ', 'نِعِمَّا'], False),
    'بِئْسَ': (['بِئْسَ', 'بِئْسَمَا'], False),
    'حَبَّذَا': (['حَبَّذَا'], False),
    'سَاءَ': (['سَاءَ', 'سَاءَتْ', 'سَاءُوا', 'يَسُوءُ', 'تَسُؤْ', 'يَسُؤْ'], True),
    # أفعال القلوب: تعمل في المبتدأ والخبر، وتكون أفعالاً تامّة (رأى: أبصر، علم: عرف، وجد: لقي)
    'حَسِبَ': (_madi('حَسِب', 'حَسِب') + _mudari(FATHA, 'حْسَب', 'حْسَبْ'), True),
    'خَالَ': (_madi('خَال', 'خِل') + _mudari(FATHA, 'خَال', 'خَلْ'), True),
    'ظَنَّ': (_madi('ظَنّ', 'ظَنَن') + _mudari(FATHA, 'ظُنّ', 'ظُنّ'), True),
    'رَأَى': (['رَأَى', 'رَءَا', 'رَأَوْا', 'رَأَتْ', 'رَأَيْتَ', 'رَأَيْتُ', 'رَأَيْتِ', 'رَأَيْتُمْ', 'رَأَيْنَا', 'رَأَيْنَ', 'يَرَى',
              'يَرَوْنَ', 'يَرَوْا', 'تَرَى', 'تَرَوْنَ', 'تَرَوْا', 'تَرَيِنَّ', 'أَرَى', 'نَرَى', 'يَرَ', 'تَرَ', 'نَرَ', 'أَرَ',
              'تَرَيْنَ', 'رَأَيْتُمُو'], True),
    'عَلِمَ': (_madi('عَلِم', 'عَلِم') + _mudari(FATHA, 'عْلَم', 'عْلَمْ') + ['اعْلَمْ', 'اعْلَمُوا', 'اعْلَمِي', 'عَلِمْتُمُو'], True),
    'وَجَدَ': (_madi('وَجَد', 'وَجَد') + _mudari(FATHA, 'جِد', 'جِدْ') + ['وَجَدْتُّمْ', 'وَجَدْتُّمُو'], True),
    'زَعَمَ': (_madi('زَعَم', 'زَعَم') + _mudari(FATHA, 'زْعُم', 'زْعُمْ'), True),
}

# الأدوات المندمجة رسماً بـ«ما» أو «مَن» أو «لا» (مِمَّا = مِنۡ + مَا): تُحلَّل إلى وحداتها، وكلّها محمية
MERGED = {'مِمَّا': ('مِنْ', 'مَا'), 'مِمَّنْ': ('مِنْ', 'مَنْ'), 'عَمَّا': ('عَنْ', 'مَا'), 'عَمَّنْ': ('عَنْ', 'مَنْ'),
          'إِمَّا': ('إِنْ', 'مَا'), 'أَمَّا': ('أَمَّا',), 'أَلَّا': ('أَنْ', 'لَا'), 'لِئَلَّا': ('لِ', 'أَنْ', 'لَا'),
          'إِلَّا': ('إِلَّا',), 'إِنَّمَا': ('إِنَّ', 'مَا'), 'أَنَّمَا': ('أَنَّ', 'مَا'), 'كَأَنَّمَا': ('كَأَنَّ', 'مَا'),
          'لَكِنَّمَا': ('لَكِنَّ', 'مَا'), 'أَيْنَمَا': ('أَيْنَ', 'مَا'), 'حَيْثُمَا': ('حَيْثُ', 'مَا'), 'فِيمَ': ('فِي', 'مَا'),
          'لِمَ': ('لِ', 'مَا'), 'عَمَّ': ('عَنْ', 'مَا'), 'بِمَ': ('بِ', 'مَا'), 'مِمَّ': ('مِنْ', 'مَا'), 'رُبَمَا': ('رُبَّ', 'مَا'),
          'رُّبَمَا': ('رُبَّ', 'مَا'), 'ذِي': ('ذُو',), 'فِيمَا': ('فِي', 'مَا'), 'أُولُو': ('أُولُو',), 'أُولِي': ('أُولُو',),
          'أُولَاتُ': ('أُولُو',), 'ذَوِي': ('ذُو',), 'ذَا': ('ذُو',), 'ذَوَاتَا': ('ذُو',), 'إِذًا': ('إِذًا',), 'أَيُّهَا': ('أَيُّ', 'هَا'), 'أَيَّتُهَا': ('أَيَّةُ', 'هَا'),
          'يَٰٓأَيُّهَا': ('يَا', 'أَيُّ', 'هَا'), 'هَٰٓأَنتُمْ': ('هَا', 'أَنْتُمْ'), 'لَقَدْ': ('لَ', 'قَدْ'), 'لَمَّا': ('لَمَّا',),
          'كَيْلَا': ('كَيْ', 'لَا'), 'لِكَيْلَا': ('لِ', 'كَيْ', 'لَا'), 'لَوْلَا': ('لَوْلَا',), 'لَوْمَا': ('لَوْمَا',),
          'هَلَّا': ('هَلَّا',), 'أَلَا': ('أَلَا',), 'أَمَا': ('أَمَا',), 'ذَٰلِكَ': ('ذَا', 'لِ', 'كَ'), 'ذَٰلِكُمْ': ('ذَا', 'لِ', 'كُمْ')}
# الضمائر المتصلة بعد الأداة أو العامل (إِنَّهُمۡ، لَعَلَّكُمۡ، عَلَيۡهِمۡ)، ونونا الوقاية والإدغام في «إِنَّا»
ENCLITICS = ('هُمَا', 'هِمَا', 'كُمَا', 'هُنَّ', 'هِنَّ', 'كُنَّ', 'هُمْ', 'هِمْ', 'كُمْ', 'هُمُ', 'هِمُ', 'كُمُ', 'هُ', 'هِ', 'هُو',
             'هِي', 'هَا', 'كَ', 'كِ', 'نَا', 'نِي', 'يَ', 'نِ')
# ما يقبل الضمير المتصل بعده: حروف الجر، وإنّ وأخواتها، والعوامل الفعلية، والظروف المبنية التي تُضاف إلى الضمير
SHORT_AFTER_HAMZA = ('لَمْ', 'لَا', 'مَا', 'مَنْ', 'لَنْ', 'إِنْ', 'إِنَّ', 'لَوْ', 'لَيْسَ', 'هَلْ')
PRON_HOSTS = {'إِنَّ', 'أَنَّ', 'لَكِنَّ', 'لَيْتَ', 'لَعَلَّ', 'كَأَنَّ', 'لَدَى', 'لَدُنْ', 'لَدَيْ', 'إِيَّا', 'عَلَى', 'إِلَى',
              'فِي', 'عَنْ', 'مِنْ', 'لَ', 'لِ', 'بِ', 'عِنْدَ', 'مَعَ', 'حَتَّى', 'دُونَ', 'بَيْنَ', 'عَسَى', 'لَيْسَ'}
# السوابق بمراتبها: همزة الاستفهام، ثم العاطف، ثم الجارّ أو لام التوكيد أو السين أو التاء أو حرف النداء أو التنبيه
PROCLITICS = (('أَ', 0), ('ءَ', 0), ('وَ', 1), ('فَ', 1), ('لَ', 2), ('لِ', 2), ('بِ', 2), ('كَ', 2), ('سَ', 2), ('تَ', 2),
              ('يَا', 2), ('هَا', 2), ('لْ', 2))


def _toks(t, expand=True):
    return [(L, frozenset(m)) for L, m in match_letters(t, expand)]


_HAMZA = str.maketrans('أإآؤئٱ', 'ءءءءءا')


def _key(toks):
    # تسوية صور الهمزة وهمزة الوصل وحدها؛ والألف المقصورة غير الياء (عَلَى ≠ عَلَي)
    return ''.join(L for L, _ in toks).translate(_HAMZA)


def _variants(f):
    out = {f}
    if 'أَ' in f:
        out.add(f.replace('أَ', 'ءَ'))
    if f.endswith('وا'):
        out.add(f[:-1])                              # جَآءُو: واو الجماعة بلا ألفٍ في الرسم
    if f.startswith('ا') and len(f) > 2:
        out.add('ٱ' + f[1:])
        if f.startswith('ال'):
            out.add(f[1:])                               # لِّلَّذِينَ: سقطت ألف «ال» بعد اللام رسماً
    if 'أُو' in f:
        out.add(f.replace('أُو', 'أُ'))                    # أُوْلَٰٓئِكَ، أُوْلُواْ: بلا واوٍ في التسوية
    return out


@lru_cache(maxsize=1)
def _index():
    """فهرس الصيغ المحمية: الحروف (بالتسوية الخفيفة للهمزات والألف) ← [(الرموز، الهوية)]"""
    idx = {}

    def add(form, info):
        for v in _variants(form):
            tk = _toks(v)
            if tk:
                idx.setdefault(_key(tk), []).append((tk, info))
    try:
        for l in open(H + 'operators_catalog.jsonl', encoding='utf-8'):
            r = json.loads(l)
            add(r['vocalized_form'], dict(cls=CLASS_OPERATOR, identity=r['vocalized_form'], group=r['group_number'],
                                          source='operators_catalog.jsonl: ' + r['operator_id']))
    except OSError:
        pass
    # ما يشترك لفظه بفعلٍ تامّ: «خَلَا» و«عَدَا» و«حَاشَا» أدوات استثناءٍ أو أفعال (خَلَا بَعۡضُهُمۡ)
    for f in ('خَلَا', 'عَدَا', 'حَاشَا'):
        for tk, info in idx.get(_key(_toks(f)), []):
            info['ambiguous'] = True
    for lemma, (forms, amb) in VERBAL.items():
        for f in forms:
            add(f, dict(cls=CLASS_OPERATOR, identity=lemma, ambiguous=amb,
                        source=f'تصريف العامل «{lemma}» (sarf/protected.py VERBAL)'))
    try:
        for l in open(H + 'lexicon/mabniyat_lexicon.jsonl', encoding='utf-8'):
            r = json.loads(l)
            add(r['form'], dict(cls=CLASS_MABNI, identity=r['form'], category=r['category'],
                                source='lexicon/mabniyat_lexicon.jsonl: ' + r['entry_id']))
    except OSError:
        pass
    for f, units in MERGED.items():
        add(f, dict(cls=CLASS_OPERATOR if units[0] in ('مِنْ', 'عَنْ', 'إِنْ', 'أَنْ', 'لِ', 'إِنَّ', 'أَنَّ', 'كَأَنَّ',
                                                         'لَكِنَّ', 'فِي', 'بِ', 'رُبَّ', 'كَيْ', 'يَا', 'لَ')
                    else CLASS_MABNI, identity=f, units=list(units), source='أداةٌ مندمجة رسماً (sarf/protected.py MERGED)'))
    for g in GOLDEN:
        add(g, dict(cls=CLASS_GOLDEN, identity=g, ambiguous=g in GOLDEN_AMBIGUOUS,
                    source='الجرد المعتمد للأسماء الذهبية (sarf/protected.py GOLDEN)'))
    return idx


@lru_cache(maxsize=1)
def _hosts():
    return {tuple(_toks(h)) for h in PRON_HOSTS}


def _host(info):
    return tuple(_toks(info.get('identity') or '')) in _hosts() or info['cls'] == CLASS_OPERATOR and (
        info.get('group') in ('1', '2', '10', '11', '13') or info.get('identity') in VERBAL)


def _strict(word, form, start=False, iltiqa=True):
    """تطابق الحركات حرفاً حرفاً: الحركة والسكون والشدة في الصيغة يلزم مثلها في الكلمة؛ والحرف بلا علامة في
    الصيغة يقبل كل حركة (آخر الاسم الذهبي)، وشدة الإدغام على الحرف الأول متسامَحٌ فيها (مِّنۡ)"""
    if len(word) != len(form):
        return False
    for i, ((_, wm), (_, fm)) in enumerate(zip(word, form)):
        if not fm:
            continue
        wv = {x for x in wm if x in (FATHA, DAMMA, KASRA, SUKUN, 'ً', 'ٌ', 'ٍ')}
        fv = {x for x in fm if x in (FATHA, DAMMA, KASRA, SUKUN, 'ً', 'ٌ', 'ٍ')}
        # التقاء الساكنين: ساكن الآخر في الصيغة يُحرَّك في الكلمة (لَيۡسَتِ، هُمُ، وَإِذِ، رَأَوُا ٱلۡعَذَابَ)
        # والحركة كسرةٌ إلا ميم الجمع فتُضمّ (هُمُ، عَلِمۡتُمُ) و«مِنَ» فتُفتح؛ ولا تنوين
        last = i == len(form) - 1 or i == len(form) - 2 and form[-1][0] == 'ا' and not form[-1][1]
        L = form[i][0]
        if fv == {SUKUN} and wv and last and iltiqa and (SHADDA in fm) == (SHADDA in wm) and \
                not wm & {'ً', 'ٌ', 'ٍ'} and (wv == {KASRA} or wv == {DAMMA} and L in 'مو' or
                                               wv == {FATHA} and _key(form) == 'من'):
            continue
        if fv and wv and fv != wv:
            return False
        if fv and not wv and SUKUN not in fv and i != len(form) - 1:
            return False                                 # الصيغة متحركة والكلمة بلا حركةٍ في الحشو
        if (SHADDA in fm) != (SHADDA in wm) and (i > 0 or not start) and (fv or wv):
            return False
    return True


ILTIQA = [True]


def _lookup(toks, golden_only=False, start=False, host=False):
    for tk, info in _index().get(_key(toks), []):
        if golden_only and info['cls'] != CLASS_GOLDEN or host and not _host(info):
            continue
        if _strict(toks, tk, start, iltiqa=ILTIQA[0] and not host):
            return info
    return None


def _strip_case(toks):
    """الاسم الذهبي يقبل كل حركة إعرابٍ وتنوينٍ في آخره (إِبۡرَٰهِيمُ، إِبۡرَٰهِيمَ، مُحَمَّدٌ)"""
    if not toks:
        return toks
    L, m = toks[-1]
    return toks[:-1] + [(L, frozenset(x for x in m if x in (SHADDA,)))]


def _match_core(toks, start=False):
    """الوحدة نفسها، أو الوحدة وبعدها ضميرٌ متصل (إِنَّا = إِنَّ + نَا بالإدغام)"""
    info = _lookup(toks, start=start)
    if info:
        return info, None
    g = _lookup(_strip_case(toks), golden_only=True, start=start)
    if g:
        return g, None
    for e in ENCLITICS:
        et = _toks(e)
        if len(toks) <= len(et):
            continue
        tail = toks[-len(et):]
        if any(m & {'ً', 'ٌ', 'ٍ'} for _, m in tail) or \
                any(SHADDA in m and SHADDA not in em for (_, m), (_, em) in zip(tail[1:], et[1:])):
            continue                                       # التنوين أو الشدة في الحشو: ليس ضميراً متصلاً
        if _key(tail) == _key(et) and _strict([(tail[0][0], tail[0][1] - {SHADDA})] + tail[1:], et):
            head = toks[:-len(et)]
            first = toks[-len(et)]
            if len(head) == 1 and head[0][0] in 'وف':
                continue                                  # وَهُوَ: الواو سابقةٌ والضمير منفصل، لا عاملٌ بضميرٍ متصل
            info = None
            if SHADDA in first[1] and head:
                # الإدغام: إِنَّا = إِنَّ + نَا، لَٰكِنَّا = لَٰكِنَّ + نَا، إِنِّي = إِنَّ + نِي
                info = _lookup(head + [(first[0], frozenset({SHADDA, FATHA}))], host=True, start=start) or \
                    _lookup(head + [(first[0], frozenset({SUKUN}))], host=True, start=start)      # مِنِّي = مِنۡ + نِي
            if not info:
                info = _lookup(head, start=start, host=True)                              # الضمير المتصل لا يلحق إلا ما يقبله (إِنَّهُمۡ، عَلَيۡهِ، كَانُوهُ)
            if not info and head and head[-1][0] == 'ي' and SUKUN in head[-1][1]:
                # عَلَيۡهِمۡ، إِلَيۡكَ: الألف تنقلب ياءً قبل الضمير
                info = _lookup(head[:-1] + [('ى', frozenset())], host=True, start=start)
            if info:
                return info, e
    return None, None


def protected(text, iltiqa=True):
    """→ سجلّ الوحدة المحمية، أو None. تُجرَّب السوابق المتصلة (حتى ثلاث) قبل الوحدة"""
    if not text:
        return None
    if divine_name(text):
        return dict(cls=CLASS_GOLDEN, identity='لفظ الجلالة', form=text, proclitics=[], enclitic=None,
                    ambiguous=False, source='sarf/divine.py', root_status=NOT_APPLICABLE, reason=REASON)
    # الألف الخنجرية تُجرَّب ألفاً ثم محذوفة (يَٰٓأَيُّهَا، لَٰكِنَّا)
    best = None
    ILTIQA[0] = iltiqa
    try:
        for expand in ((True, False) if 'ٰ' in text else (True,)):
            best = _search(_toks(text, expand))
            if best:
                break
    finally:
        ILTIQA[0] = True
    if not best:
        return None
    info, pre, enc = best
    out = dict(info, form=text, proclitics=pre, enclitic=enc, root_status=NOT_APPLICABLE, reason=REASON)
    out.setdefault('ambiguous', False)
    if out['ambiguous']:
        out['alternative'] = ('فعلٌ تامّ غير عامل (يُحلَّل جذره بديلاً، ولا يُقبل حتى تُعيَّن الفئة)'
                              if out['cls'] == CLASS_OPERATOR else 'اسمٌ غير عَلَم يشترك معه لفظاً')
    return out


def _search(toks):
    best = None
    stack = [(toks, [])]
    seen = 0
    while stack and seen < 40:
        tk, pre = stack.pop(0)
        seen += 1
        info, enc = _match_core(tk, start=not pre)
        if info and info.get('group') == '1' and any(q in pre for q in ('لَ', 'لِ', 'بِ', 'كَ')):
            info = None                                   # لَعَنَّا فعلٌ: لا يدخل جارٌّ على جارّ
        if info:
            best = (info, pre, enc)
            break
        if len(pre) >= 3:
            continue
        rank = max((r for q, r in PROCLITICS if q in pre), default=-1)
        for p, r in PROCLITICS:
            if r <= rank:
                continue
            pt = _toks(p)
            if len(tk) > len(pt) + 1 and _key(tk[:len(pt)]) == _key(pt) and _strict(tk[:len(pt)], pt, start=not pre):
                rest = tk[len(pt):]
                if r == 0 and len(rest) < 3 and not any(_key(rest[:1]) == q for q in ('و', 'ف')) and \
                        not any(_strict(rest, _toks(q), iltiqa=False) for q in SHORT_AFTER_HAMZA):
                    continue                                  # أَمِنَ فعلٌ لا «أَ» + «مِنَ»: الاستفهام قبل قلبٍ قصير بلا عاطف
                stack.append((rest, pre + [p]))
                if p in ('لَ', 'لِ', 'بِ', 'كَ') and rest and rest[0][0] == 'ا':
                    stack.append((rest[1:], pre + [p]))           # بِٱلۡ: همزة الوصل تسقط بعد الجارّ
    return best


def protected_slot(seg, slot_text=None):
    """الكلمة كلها أولاً؛ ثم الجذع إن كان قلبَ الكلمة (ما سواه سوابق ولواحق لا جذعٌ آخر) وكان حرفين فأكثر،
    فلا تُحمى قطعةٌ من كلمةٍ قطّعها المقشِّر خطأً («ي» في ءَاتَيۡنَا)"""
    from .chars import letters
    p = protected(seg['word'])
    if p is not None:
        return p
    sl = seg.get('slots', [])
    stems = [x for x in sl if x['type'] == 'جذع']
    if len(stems) != 1 or any(x['type'] == 'أل' for x in sl):
        return None                                      # الاسم بعد «أل» ليس عاملاً ولا مبنياً (ٱلۡحَيَّ)
    k = sl.index(stems[0])
    if any(len(letters(x['text'])) > 2 for x in sl[:k]):
        return None                                      # ما قبل الجذع سوابق قصيرة لا كلمة
    t = slot_text or stems[0]['text']
    if len(letters(t)) < 2:
        return None
    p = protected(t, iltiqa=k + 1 == len(sl))
    return p if p is not None and not p['proclitics'] else None

