#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار T19a–T19c: الخلية، والجذر والصيغة المرخَّصان بشهادة HFN.
يحتاج HFN release_v36 (SARF_HFN، أو ../husseinframenet/release/release_v36، أو
~/arabic-net/HusseinFrameNet/release/release_v36)؛ وبدونه تُختبر الخلايا وحدها.

    python3 tests/test_root.py
"""
import os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.root import cells, cell_code, morph, hfn, soundness

bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

# T19a/T19b: الخلايا، والشدة صامتان أولهما ساكن (أمثلة الوثيقة)
for w, want in [('كَتَبَ', 'كva + تva + بva'), ('كَاتَبَ', 'كvA + تva + بva'),
                ('كَتَّبَ', 'كva + ت∅ + تva + بva'), ('كُتِبَ', 'كvo + تvi + بva'), ('بَيْ', 'بva + ي∅')]:
    got = cell_code(cells(w))
    check(f'الخلايا: {w}', got == want, got)
check('السلامة والاعتلال', [soundness(r) for r in ('كتب', 'ولد', 'قول', 'دعو', 'مدد', 'ءمن', 'وقي')] ==
      ['salim', 'mithal', 'ajwaf', 'naqis', 'mudaaf', 'mahmuz', 'lafif_mafruq'])

if not hfn():
    print('HFN غير موجود: تُتجاوز اختبارات الرخصة')
else:
    # (الكلمة، الحالة، المستوى، الجذر، الوزن)
    CASES = [
        ('قُلْ', 'accepted', 'event', 'قول', 'I'),               # الأجوف المحذوف: الضمة ← و
        ('يَلِدْ', 'accepted', 'event', 'ولد', 'I'),             # المثال المحذوف الفاء
        ('يَدْعُوا', 'accepted', 'event', 'دعو', 'I'),
        ('كَذَّبُوا', 'accepted', 'event', 'كذب', 'II'),           # الشدة حرفان
        ('يَتَكَلَّمُونَ', 'accepted', 'event', 'كلم', 'V'),
        ('اسْتَغْفِرُوا', 'accepted', 'event', 'غفر', 'X'),
        ('أَنْزَلْنَا', 'accepted', 'event', 'نزل', 'IV'),
        ('يُخَٰدِعُونَ', 'accepted', 'event', 'خدع', 'III'),       # الخنجرية ألف
        ('كُلُوا', 'accepted', 'event', 'ءكل', 'I'),              # أمر المهموز الفاء
        ('فَقُلْ', 'accepted', 'event', 'قول', 'I'),               # بعد نزع الفاء
        ('اكْتُبُو', 'accepted', 'event', 'كتب', 'I'),             # تاء الافتعال مفتوحة: ليس «كبو»
        ('يُؤْمِنُونَ', 'accepted', 'event', 'ءمن', 'IV'),         # v36: حدث «آمَنَ» مسجَّل (وكان في v18 الجذر وحده)
        ('اتَّقُوا', 'accepted', 'event', 'وقي', 'VIII'),          # v36: حدث «اتَّقَى»
        ('خِفْتُمْ', 'deferred', None, None, None),               # خوف أم خيف: لا تفصل الكتابة
        ('كَتَبَ', 'deferred', 'lemma', None, None),              # يطابق فعلاً، ولم يثبت أنه فعل
        ('تَدَايَنْتُمْ', 'accepted', 'event', 'دين', 'VI'),        # العين المتحركة كما كُتبت: لا «دون»؛ وv36: حدث «تَدَايَنَ»
        ('تُحِبُّونَ', 'accepted', 'event', 'حبب', 'IV'),          # الحاء مكسورة: أَفۡعَلَ المضعَّف لا فَعَّلَ؛ وv36: حدث «أَحَبَّ»
        ('قُلِ', 'accepted', 'event', 'قول', 'I'),               # الكسر لالتقاء الساكنين
    ]
    for w, st, lv, root, cls in CASES:
        m = morph(w)
        got = (m['status'], m.get('level'), m.get('root'), m.get('form_class')) if m else None
        check(f'Morph({w})', got == (st, lv, root, cls), got)
    # لا يتسرّب حكم كلمة إلى ما بعدها: «قَالُوا» بعد «قُلْ» كما هي وحدها
    from tests._release import RELEASE, DATA_REASONS
    alone = morph('قَالُوا')
    morph('قُلْ')
    m = morph('قَالُوا')
    if RELEASE == 'release_v36':
        check('قَالُوا بعد قُلْ: مقبول (لا حالة مشتركة بين الكلمات)', m['status'] == 'accepted' and m['root'] == 'قول', m.get('reason'))
    else:
        # الإصدار المستهدف: DATA_REASONS['QAWL_QAYL'] — «قَالُوا» ملتبسةٌ بين قول وقيل بلا اختيار، والحكم بعد «قُلْ» هو حكمها وحدها
        check('قَالُوا بعد قُلْ: حكمها وحدها (لا حالة مشتركة)، وهو التباسٌ صحيح بين قول وقيل (v47)',
              (m['status'], m.get('reason')) == (alone['status'], alone.get('reason')) and m['status'] == 'deferred'
              and 'قول' in (m.get('reason') or '') and 'قيل' in (m.get('reason') or ''), m.get('reason'))
        q = morph('قُلْنَا')
        check('قُلْنَا بعد قُلْ: مقبول قول (ضمة الفاء)', q['status'] == 'accepted' and q['root'] == 'قول', q.get('reason'))
    # الفعلية بالعامل المقبول: لَنۡ نَّبۡرَحَ
    from sarf.analyze import analyze
    from sarf.catalog import Catalog
    a = analyze(Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv']),
                'لَن نَّبْرَحَ عَلَيْهِ عَٰكِفِينَ حَتَّىٰ يَرْجِعَ إِلَيْنَا مُوسَىٰ')
    got = {m['word_index']: (m['status'], m['root']) for m in a['morph']}
    check('لَنۡ نَّبۡرَحَ، حَتَّىٰ يَرۡجِعَ: «نبرح» عاملٌ محمي (برح من أخوات كان) لا جذر له، و«يرجع» جذره مقبول',
          got.get(1) == ('not_applicable', None) and got.get(5) == ('accepted', 'رجع'), got)
    check('مُوسَىٰ: اسمٌ ذهبي لا جذر له', got.get(7, ('not_applicable',))[0] in ('not_applicable',), got)
    agr = {g['word_index']: g['pronouns'] for g in a['agreement']}
    check('الفاعل بالعامل: نَحۡنُ، هُوَ', agr.get(1) == ['نَحْنُ'] and agr.get(5) == ['هُوَ'], agr)
    m = morph('قُلْ')
    check('الشاهد: الحدث ومصدره', m['licensed'] and m['licensed'][0]['verb'] == 'قَالَ' and
          m['licensed'][0]['event_id'].startswith('HFN-E-'), m['licensed'][:1])
    # مراجعة التقرير الخامسة (٣): القوة الأرجح تُنتج ترجيحاً لا إثباتاً، والمنافس محفوظ بسببه
    m = morph('وَلَسْتُمْ')
    check('وَلَسۡتُمۡ: «ليس» عاملٌ محمي دستورياً، فلا يدخل مسار الجذر (NOT_APPLICABLE)',
          m['status'] == 'not_applicable' and m['root_status'] == 'NOT_APPLICABLE' and
          m['reason'] == 'CONSTITUTIONAL_PROTECTED_CLASS' and not m['candidates'] and m['protected']['identity'] == 'لَيْسَ', m)
    m = morph('تَهِنُوا')
    check('تَهِنُواْ: الترجيح بالمطابقة «مرجَّح» لا مقبول، والمنافس «وهن» محفوظ', m['status'] == 'ranked' and
          'وهن/I' in m['selection'].get('alternatives', []), m.get('status'))
    m = morph('عَلِمَ')
    check('عَلِمَ: فعلٌ قلبيّ محمي مرشّح أو فعلٌ تامّ: الفئة مؤجَّلة، والحماية باقية، والبديل محفوظ',
          m['status'] == 'class_deferred' and m['protected']['identity'] == 'عَلِمَ' and m['alternative'], m.get('status'))
    m = morph('فَجَعَلْتُمْ')
    check('فَجَعَلۡتُمۡ: لا منافس، فالجذر مثبت (لا مرجَّح)', m['status'] == 'accepted' and m['level'] == 'event', m)
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
