#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
السمات المضافة من سجل التغطية (sarf.features_ext): قواعدها على أمثلة، وأنها إضافةٌ خالصة لا تغيّر سمةً قائمة.

    python3 tests/test_features_ext.py
"""
import os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.features_ext import root_class, final_form, _diptote, _elative
import sarf.features_ext as fx
from sarf.root import hfn

bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

# ١. صنف الجذر بأصوله
for R, want in [('كتب', ['سالم']), ('ملل', ['مضعّف']), ('وقي', ['لفيف مفروق']), ('طوع', ['أجوف']), ('دعو', ['ناقص']),
                ('وعد', ['مثال']), ('سءم', ['مهموز العين']), ('ءمن', ['مهموز الفاء']), ('قرء', ['مهموز اللام']),
                ('روي', ['لفيف مقرون']), ('ءبي', ['مهموز الفاء', 'ناقص']), ('زلزل', ['مضعّف رباعي'])]:
    got = root_class(R)
    check(f'صنف الجذر «{R}»: {"، ".join(want)}', got['kinds'] == want, got)
check('المعتل ما فيه حرف علة من أصوله، والصحيح ما خلا منه', root_class('وقي')['type'] == 'معتل' and root_class('سءم')['type'] == 'صحيح')
# ٢. صورة الآخر (مرشّحة)
for w, want in [('مُّسَمًّى', 'مقصور'), ('الْأُخْرَى', 'مقصور'), ('الدُّنْيَا', 'مقصور'), ('الشُّهَدَاءِ', 'ممدود'), ('نِسَاءً', 'ممدود'),
                ('الدَّاعِي', 'منقوص'), ('كَاتِبٌ', None), ('مَاءً', None), ('صَغِيرًا', None), ('كِتَابًا', None)]:
    got = final_form(w)
    check(f'صورة الآخر «{w}»: {want or "لا شيء"}', (got[0] if got else None) == want, got)
# ٣. الممنوع من الصرف (مرشّح): لا مع أل ولا مع الضمير ولا مع التنوين
check('مَسَاجِدَ: صيغة منتهى الجموع بلا تنوين', _diptote('مَسَاجِدَ', False, None) is not None)
check('أَصْدِقَاءَ: ألف التأنيث الممدودة بلا تنوين', _diptote('أَصْدِقَاءَ', False, None) is not None)
check('الْمَسَاجِدَ: لا (أل)', _diptote('الْمَسَاجِدَ', True, None) is None)
check('مَسَاجِدُهُمْ: لا (الضمير)', _diptote('مَسَاجِدَ', False, 'هُمْ') is None)
check('رِجَالٌ: لا (التنوين)', _diptote('رِجَالٌ', False, None) is None)
check('مَسَٰجِدَ: صيغة منتهى الجموع بالألف الخنجرية', _diptote('مَسَٰجِدَ', False, None) is not None)
check('أَسْمَاءِ بالكسرة: لا (الكسرة لا تشهد للممنوع)', _diptote('أَسْمَاءِ', False, None) is None)
from sarf.features_ext import nisba_tasghir
check('الْأُمِّيُّ: ياء النسب مرشّحة', [k for k, _ in nisba_tasghir('الْأُمِّيُّ')] == ['nisba'])
check('حُسَيْن: التصغير مرشّح (فُعَيْل)', [k for k, _ in nisba_tasghir('حُسَيْنٌ')] == ['diminutive'])
check('كَاتِب: لا نسب ولا تصغير', nisba_tasghir('كَاتِبٌ') == [])
from sarf.features_ext import DERIV_ALT
check('مَفْعَل ومَفْعِل: اسم مكان أو زمان أو مصدر ميمي (بدائل)', all('مصدر ميمي' in DERIV_ALT[k] for k in ('مَفْعَل', 'مَفْعِل')))
# ٤. أَفْعَل مرشّحاً للتفضيل
check('أَقْسَطُ: قالب أَفْعَل', _elative('أَقْسَطُ') is not None)
check('أَدْنَى: قالب أَفْعَل بالألف المقصورة', _elative('أَدْنَى') is not None)
check('أَشَدُّ: أَفَلّ المضعّف', _elative('أَشَدُّ') is not None)
check('أَقْسَطٌ بالتنوين: لا', _elative('أَقْسَطٌ') is None)
check('كَتَبَ: ليس على أَفْعَل', _elative('كَتَبَ') is None)

def by_any(cat, text, unit, key):
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo
    from sarf.features import unit_features
    a = analyze(cat, text)
    _, U = sentence_geo(a, 'q', Trace())
    for k, v in unit_features(a, U).items():
        if U[k].O['text'] == unit and key in v:
            return v[key]['v']
    return None


if hfn():
    from sarf.catalog import Catalog
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo
    from sarf.features import unit_features
    cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
    t = 'فَإِن كَانَ ٱلَّذِي عَلَيۡهِ ٱلۡحَقُّ سَفِيهًا أَوۡ ضَعِيفًا أَوۡ لَا يَسۡتَطِيعُ أَن يُمِلَّ هُوَ فَلۡيُمۡلِلۡ وَلِيُّهُۥ بِٱلۡعَدۡلِۚ وَلۡيَتَّقِ ٱللَّهَ رَبَّهُۥ'
    a = analyze(cat, t)
    _, U = sentence_geo(a, 't', Trace())
    F = unit_features(a, U)
    by = {U[k].O['text']: v for k, v in F.items()}
    check('يَسْتَطِيعُ: أجوف ثلاثي، وتحويله «إعلال r2 (و): قلب إلى مدّ»',
          by['يَسْتَطِيعُ']['root_class']['v']['kinds'] == ['أجوف'] and by['يَسْتَطِيعُ']['root_arity']['v'] == 'ثلاثي' and
          by['يَسْتَطِيعُ']['transformations']['v'] == ['إعلال r2 (و): قلب إلى مدّ'], by['يَسْتَطِيعُ'])
    check('يَتَّقِ: لفيف مفروق، وتحويلاه إبدال الواو تاءً وحذف اللام',
          by['يَتَّقِ']['root_class']['v']['kinds'] == ['لفيف مفروق'] and 'إبدال و ← ت' in by['يَتَّقِ']['transformations']['v'],
          by['يَتَّقِ'])
    check('يُمْلِلْ: مضعّف', by['يُمْلِلْ']['root_class']['v']['kinds'] == ['مضعّف'], by['يُمْلِلْ'])
    check('الْعَدْلِ: معرفة بأل، ولمّته «عَدْل» من HFN',
          by['الْعَدْلِ']['definiteness_kind']['v'] == 'معرفة بأل' and by['الْعَدْلِ']['lemma']['v'] == 'عَدْل', by['الْعَدْلِ'])
    check('اللَّهَ: علم', by['اللَّهَ']['definiteness_kind']['v'] == 'علم')
    check('سَفِيهًا: فَعِيل يحتمل أكثر من نوع اشتقاق (مؤجَّل ببدائله)',
          by['سَفِيهًا']['derivation_candidates']['st'] == 'مؤجَّل' and 'صفة مشبهة' in by['سَفِيهًا']['derivation_candidates']['alt'])
    check('كَانَ: تصرّفه مؤجَّل (لا جرد معتمد لتصرّف النواسخ)', by['كَانَ']['conjugability']['st'] == 'مؤجَّل')
    a2 = analyze(cat, 'فَلَيۡسَ عَلَيۡكُمۡ جُنَاحٌ')
    _, U2 = sentence_geo(a2, 't2', Trace())
    F2 = unit_features(a2, U2)
    a3 = analyze(cat, 'وَلَا يَأۡبَ كَاتِبٌ أَن يَكۡتُبَ')
    _, U3 = sentence_geo(a3, 't3', Trace())
    F3 = unit_features(a3, U3)
    check('أَنْ الناصبة المقبولة ومضارعها المنصوب: مصدر مؤوَّل', any(v.get('construction', {}).get('v') == 'مصدر مؤوَّل' for v in F3.values()))
    a4 = analyze(cat, 'لَمۡ يَلِدۡ وَلَمۡ يُولَدۡ')
    _, U4 = sentence_geo(a4, 't4', Trace())
    F4 = {U4[k].O['text']: v for k, v in unit_features(a4, U4).items()}
    check('«لَمْ» المقبولة: الفعل بعدها منفي', F4['يَلِدْ']['polarity']['v'] == 'منفي' and F4['يُولَدْ']['polarity']['v'] == 'منفي')
    check('نوع الإسناد: المعلوم إلى فاعل، والمجهول إلى نائب فاعل',
          F4['يَلِدْ']['subject_kind']['v'] == 'فاعل' and F4['يُولَدْ']['subject_kind']['v'] == 'نائب فاعل', (F4['يَلِدْ'], F4['يُولَدْ']))
    check('«لَا» الناهية المقبولة: منهيّ عنه', by_any(cat, 'وَلَا يَبۡخَسۡ مِنۡهُ شَيۡـࣰٔاۚ', 'يَبْخَسْ', 'polarity') == 'منهيّ عنه')
    check('الناسخ الفعلي لا يُعطى «فاعلاً» (مرفوعه اسمه)', by_any(cat, 'إِلَّآ أَن تَكُونَ تِجَٰرَةً', 'تَكُونَ', 'subject_kind') is None)
    check('ما بعد «يَا»: منادى مرشّح', by_any(cat, 'يَٰٓأَيُّهَا ٱلَّذِينَ ءَامَنُوٓاْ', 'أَيُّهَا', 'vocative') == 'منادى')
    check('الإضافة مرشّحة: بِكُلِّ شَيْءٍ', by_any(cat, 'وَٱللَّهُ بِكُلِّ شَيۡءٍ عَلِيمࣱ', 'كُلِّ', 'idafa') == 'مضاف' and
          by_any(cat, 'وَٱللَّهُ بِكُلِّ شَيۡءٍ عَلِيمࣱ', 'شَيْءٍ', 'idafa') == 'مضاف إليه')
    check('لَيْسَ: نفي', by_any(cat, 'فَلَيۡسَ عَلَيۡكُمۡ جُنَاحٌ', 'لَيْسَ', 'polarity') == 'منفي')
    check('لَيْسَ: جامد مثبت', any(v.get('conjugability', {}).get('v') == 'جامد' for v in F2.values()))
    # ٥. الإضافة خالصة: بلا السمات المضافة تبقى السمات القائمة كما هي بعينها
    keep = fx.extra_features
    fx.extra_features = lambda *a_, **k_: {}
    F0 = unit_features(a, U)
    fx.extra_features = keep
    same = all({k_: v_ for k_, v_ in F[k].items() if k_ in F0[k]} == F0[k] for k in F0)
    check('السمات المضافة لا تغيّر سمةً قائمة: ما في الناتج بدونها هو بعينه فيه معها', same)
from sarf.features_ext import enclitic_case
NOUN = {'pos': {'v': 'اسم', 'st': 'مثبت'}}
VERB = {'pos': {'v': 'فعل', 'st': 'مثبت'}}
check('الضمير بعد الاسم: جر', enclitic_case('كُمْ', NOUN)['v'] == 'جر')
check('ضمير النصب بعد الفعل: نصب', enclitic_case('هُ', VERB)['v'] == 'نصب')
check('ضمير الرفع بعد الفعل: رفع', enclitic_case('تُمْ', VERB)['v'] == 'رفع')
check('«نَا» بعد الفعل: مؤجَّل', enclitic_case('نَا', VERB)['st'] == 'مؤجَّل')
check('بعد مضيفٍ غير مثبت الصنف: لا حكم', enclitic_case('كُمْ', {'pos': {'v': None, 'st': 'مؤجَّل'}}) is None)
check('المطابقة بالحروف والحركات: «كُمُ» غير «كُمِ»', enclitic_case('كُمِ', VERB) is None)
from sarf.algebra import merge_split_shadda
check('إعادة التركيب: الشدة المفكوكة على حدّ خانتين تُعاد (كُنْ + نَ ← كُنَّ)', merge_split_shadda('كُنْ', 'نَ') == 'كُنَّ')
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
