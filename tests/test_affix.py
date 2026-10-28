#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبارات مقشِّر الزوائد (sarf.affix) ونفي المرشَّح بالكتابة المبني عليه (sarf.evidence).

    python3 tests/test_affix.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarf.affix import stem_info
from sarf.catalog import Catalog
from sarf.pipeline import Pipeline

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPE = Pipeline(Catalog([os.path.join(HERE, 'operators_catalog.jsonl'),
                         os.path.join(HERE, 'operators_catalog_split_vocalized.csv')]))

# (الجذع، النوع، الصيغة، علامة الآخر، اللاحقة)
STEMS = [
    ('يَكْتُبْ', 'verb', 'mudari', 'جزم', None),
    ('يَعْلَمُونَ', 'verb', 'mudari', 'رفع', 'نون الرفع'),
    ('أَكِيدَنَّ', 'verb', 'mudari', 'مبني', 'نون التوكيد'),
    ('تَقُولُوا', 'verb', 'mudari', 'حذف النون', 'وا'),
    ('امْسَحُوا', 'verb', 'amr', None, 'وا'),
    ('قَالُوا', 'verb', 'madi', None, 'وا'),
    ('تَدَايَنْتُمْ', 'verb', 'madi', None, 'تُمْ'),
    ('يُعَذِّبَهُمْ', None, 'mudari', 'نصب', None),          # بلا دليل قاطع على الفعل
    ('نَبِيُّونَ', None, 'mudari', 'رفع', 'نون الرفع'),      # نون الرفع مع النون تلتبس بجمع الاسم
    ('دَيْنٍ', 'noun', None, None, None),
    ('الْعَدْلِ', 'noun', None, None, None),
    ('مَوْتِ', None, None, None, None),                      # التاء بعد ساكن ليست ضمير رفع
    ('أَنْتَ', None, None, None, None),                      # ضمير منفصل
    # الأمر بلا همزة وصل: سكون الآخر بلا حرف مضارعة
    ('قُلْ', 'verb', 'amr', None, None),
    ('عَلِّمْ', 'verb', 'amr', None, None),
    ('قَدْ', None, None, None, None),                        # في ملف المبنيات: سكون بناء
    ('كُمْ', None, None, None, None),
    ('لَدُنْ', None, None, None, None),                      # أُضيف إلى ملف المبنيات بتصحيح
    ('قُولُوا', 'verb', 'amr', None, 'وا'),
    ('فَقُولُوا', 'verb', 'amr', None, 'وا'),
    ('قُتِلُوا', 'verb', 'madi', None, 'وا'),
    ('اكْتُبُو', 'verb', 'amr', None, 'و'),                   # بعد فصل الضمير: اكْتُبُو | هُ
    # تاء التأنيث الساكنة
    ('تَبَّتْ', 'verb', 'madi', None, 'تْ'),
    # ياء المخاطبة
    ('تَكْتُبِي', None, 'mudari', 'حذف النون', 'ي'),
    ('اسْجُدِى', 'verb', 'amr', None, 'ي'),
    ('نَفْسِى', None, 'mudari', None, None),                  # ياء المتكلم: لا تُقشَّر
    ('تَحْزَنِى', None, 'mudari', 'حذف النون', 'ي'),          # النون جذرية لا نون وقاية
    # من اختبار جزء عمّ: همزة الوصل في الماضي والمصدر لا في الأمر وحده
    ('اتَّخَذَ', 'verb', 'madi', None, None),
    ('انْكَدَرَتْ', 'verb', 'madi', None, 'تْ'),
    ('انْقَلَبُوا', 'verb', 'madi', None, 'وا'),
    ('اسْتَغْفِرُوا', 'verb', 'amr', None, 'وا'),            # «است» اسمٌ بالمطابقة لا «يبدأ بـ»
    ('اسْمَعُوا', 'verb', 'amr', None, 'وا'),
    ('ابْتِغَاءَ', None, None, None, None),                   # مصدر
    ('اسْمُهُ', None, None, None, None),
    # «نَا» بعد ساكن فاعلٌ في الماضي، لا مفعول
    ('بَنَيْنَا', 'verb', 'madi', None, 'نَا'),
    ('عَلَيْنَا', None, None, None, None),
    # سكون الآخر ليس أمراً: الضمير الساكن، وهاء السكت، والمبني بعد سابقة
    ('لَهُمْ', None, None, None, None),
    ('هِيَهْ', None, None, None, None),
    ('لَقَدْ', None, None, None, None),
    ('فَأَنْتَ', None, None, None, None),
    ('فَبَشِّرْهُمْ', 'verb', 'amr', None, None),
    # هاء الضمير المكسورة لا تقع بعد فتح: الهاء أصلية (يَنتَهِ)
    ('يَنْتَهِ', None, 'mudari', None, None),
]

# (النص، العامل، المجموعة، الحكم)
REJECT = [
    ('وَٱمْسَحُوا۟', 'وَ', '1', 'blocked'),
    ('وَلَمْ يُولَدْ', 'وَ', '4', 'blocked'),
    ('وَأَنتَ فِيهِمْ', 'وَ', '1', 'blocked'),
    ('وَلْيَكْتُبْ', 'لِ', '6', 'deferred'),                # لام الأمر بعد الواو
    ('وَتَٱللَّهِ', 'تَ', '1', 'deferred'),                  # تاء القسم بعد الواو
    ('لَأَكِيدَنَّ', 'لِ', '1', 'blocked'),                 # اللام المفتوحة قبل الفعل
    ('لَكُمْ', 'لِ', '1', 'deferred'),
    ('لَا يَعْلَمُونَ', 'لَا', '6', 'blocked'),
    ('لَا رَيْبَ', 'لَا', '6', 'blocked'),
    ('لَا تَحْزَنْ', 'لَا', '6', 'deferred'),
    ('كَانُوا۟', 'كَانَ', '10', 'deferred'),                 # كان مع واو الجماعة
    # R6: حرف الجر وواو المعية لا يليهما مرفوع
    ('وَيۡلࣱ لِّلۡمُطَفِّفِينَ', 'وَ', '1', 'blocked'),
    ('وَٱللَّهُ أَعۡلَمُ', 'وَ', '1', 'blocked'),
    ('وَٱللَّهِ', 'وَ', '1', 'deferred'),
    # R7: أداة الشرط لا يليها مرفوع
    ('مَا تَفۡعَلُونَ', 'مَا', '7', 'blocked'),
    ('مَا ٱلۡقَارِعَةُ', 'مَا', '7', 'blocked'),
    ('إِن كُلُّ نَفۡسࣲ', 'إِنْ', '6', 'blocked'),
    # R8: أول البقية ساكن أو مشدَّد: الحرف أصلي
    ('كَذَّبَتۡ', 'كَ', '1', 'blocked'),
    ('بِسۡمِ', 'بِ', '1', 'deferred'),                       # حذف ألف «اسم» خطاً
    ('فَلۡيَنظُرِ', 'لِ', '6', 'deferred'),
    # R9: الكاف الجارّة لا تدخل على الفعل
    ('كَفَرُواْ', 'كَ', '1', 'blocked'),
    # R7: أداة الشرط لا يليها ضمير رفع منفصل
    ('إِنۡ هُوَ إِلَّا ذِكۡرࣱ', 'إِنْ', '6', 'blocked'),
    ('وَمَا هُوَ بِٱلۡهَزۡلِ', 'مَا', '7', 'blocked'),
]

bad = 0
for text, pos, kind, mood, suf in STEMS:
    i = stem_info(text)
    got = (i['pos'], i['kind'], i['mood'], i['suffix'])
    ok = got == (pos, kind, mood, suf)
    bad += not ok
    print('OK ' if ok else 'BAD', text, got if not ok else '')
for text, op, grp, want in REJECT:
    ops = PIPE.run(text, until='evidence').candidates
    got = next((f['status'] for f in ops if f['operator'] == op and f['group'] == grp), 'absent')
    ok = got == want
    bad += not ok
    print('OK ' if ok else 'BAD', text, op, grp, got if not ok else '')

# حكم T09 بعد طبقة الحكم: (النص، العامل، المجموعة، الحالة)
JUDGE = [
    ('لَمْ يَلِدْ', 'لَمْ', '6', 'accepted'),
    ('لَا تَحْزَنْ', 'لَا', '6', 'deferred'),                # منافس على الخانة (نافية/ناهية)
    ('لَيْسَ كَمِثْلِهِۦ شَىْءٌ', 'لَيْسَ', '10', 'accepted'),
    # الكاف السابقة لا تُقبل إلا إذا تلتها «أل» أو مبني: كَرِيمٍ قد تكون كافها أصلية
    ('رَسُولࣲ كَرِيمࣲ', 'كَ', '1', 'deferred'),
    ('كَٱلۡفَرَاشِ ٱلۡمَبۡثُوثِ', 'كَ', '1', 'accepted'),
    # كان: المنصوب بعدها خبرها، واسمها مستتر
    ('إِنَّ جَهَنَّمَ كَانَتۡ مِرۡصَادࣰا', 'كَانَ', '10', 'accepted'),
]
for text, op, grp, want in JUDGE:
    ops = PIPE.run(text).candidates
    got = next((f['status'] for f in ops if f['operator'] == op and f['group'] == grp), 'absent')
    ok = got == want
    bad += not ok
    print('OK ' if ok else 'BAD', 'T09', text, op, grp, got if not ok else '')

# الإعراب المعروض لكل كلمة
from sarf.output_text import word_irab
from sarf.analyze import analyze
IRAB = [
    ('لَيْسَ كَمِثْلِهِۦ شَىْءٌ', 1, 'حرف جر زائد للتوكيد'),
    ('لَيْسَ كَمِثْلِهِۦ شَىْءٌ', 1, 'خبر «لَيْسَ» مقدَّم في محلّ نصب'),
    ('لَيْسَ كَمِثْلِهِۦ شَىْءٌ', 2, 'اسم «لَيْسَ» مرفوع مؤخَّر'),
    ('قُلْ هُوَ ٱللَّهُ أَحَدٌ', 0, 'فعل أمر مبني على السكون'),
    ('لَمْ تَكْتُبِى', 1, 'مضارع مجزوم بـ«لَمْ» وعلامة جزمه حذف النون'),
    ('وَٱسْجُدِى', 0, 'فعل أمر مبني على حذف النون، وياء المخاطبة فاعل'),
    ('تَبَّتْ يَدَآ', 0, 'فعل ماضٍ مبني، والتاء للتأنيث'),
]
for text, wi, want in IRAB:
    a = analyze(PIPE.cat, text)
    roles = [r for _, r, _ in word_irab(a, wi)]
    ok = any(want in r for r in roles)
    bad += not ok
    print('OK ' if ok else 'BAD', 'إعراب', text, wi, want, roles if not ok else '')
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
