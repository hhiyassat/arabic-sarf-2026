#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار T19a–T19c: الخلية، والجذر والصيغة المرخَّصان بشهادة HFN.
يحتاج HFN release_v18 (SARF_HFN، أو ../husseinframenet/release/release_v18، أو
~/arabic-net/HusseinFrameNet/release/release_v18)؛ وبدونه تُختبر الخلايا وحدها.

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
        ('يُؤْمِنُونَ', 'accepted', 'root', 'ءمن', 'IV'),          # الجذر في HFN ولا حدث «آمَنَ»
        ('اتَّقُوا', 'accepted', 'root', 'وقي', 'VIII'),
        ('خِفْتُمْ', 'deferred', None, None, None),               # خوف أم خيف: لا تفصل الكتابة
        ('كَتَبَ', 'deferred', 'lemma', None, None),              # يطابق فعلاً، ولم يثبت أنه فعل
        ('تَدَايَنْتُمْ', 'accepted', 'root', 'دين', 'VI'),         # العين المتحركة كما كُتبت: لا «دون»
        ('تُحِبُّونَ', 'accepted', 'root', 'حبب', 'IV'),           # الحاء مكسورة: أَفۡعَلَ المضعَّف لا فَعَّلَ
        ('قُلِ', 'accepted', 'event', 'قول', 'I'),               # الكسر لالتقاء الساكنين
    ]
    for w, st, lv, root, cls in CASES:
        m = morph(w)
        got = (m['status'], m.get('level'), m.get('root'), m.get('form_class')) if m else None
        check(f'Morph({w})', got == (st, lv, root, cls), got)
    # لا يتسرّب حكم كلمة إلى ما بعدها: «قَالُوا» بعد «قُلْ» كما هي وحدها
    morph('قُلْ')
    m = morph('قَالُوا')
    check('قَالُوا بعد قُلْ: مقبول (لا حالة مشتركة بين الكلمات)', m['status'] == 'accepted' and m['root'] == 'قول', m.get('reason'))
    # الفعلية بالعامل المقبول: لَنۡ نَّبۡرَحَ
    from sarf.analyze import analyze
    from sarf.catalog import Catalog
    a = analyze(Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv']),
                'لَن نَّبْرَحَ عَلَيْهِ عَٰكِفِينَ حَتَّىٰ يَرْجِعَ إِلَيْنَا مُوسَىٰ')
    got = {m['word_index']: (m['status'], m['root']) for m in a['morph']}
    check('لَنۡ نَّبۡرَحَ، حَتَّىٰ يَرۡجِعَ: فعلان بالعامل، والجذر مقبول', got.get(1) == ('accepted', 'برح') and
          got.get(5) == ('accepted', 'رجع'), got)
    check('مُوسَىٰ: لا جذر مقبول (لم يثبت أنه فعل)', got.get(7, ('deferred',))[0] != 'accepted', got)
    agr = {g['word_index']: g['pronouns'] for g in a['agreement']}
    check('الفاعل بالعامل: نَحۡنُ، هُوَ', agr.get(1) == ['نَحْنُ'] and agr.get(5) == ['هُوَ'], agr)
    m = morph('قُلْ')
    check('الشاهد: الحدث ومصدره', m['licensed'] and m['licensed'][0]['verb'] == 'قَالَ' and
          m['licensed'][0]['event_id'].startswith('HFN-E-'), m['licensed'][:1])
    # مراجعة التقرير الخامسة (٣): القوة الأرجح تُنتج ترجيحاً لا إثباتاً، والمنافس محفوظ بسببه
    m = morph('وَلَسْتُمْ')
    check('وَلَسۡتُمۡ: «ولس» مرجَّحٌ بالمطابقة لا مثبت، و«ليس» محفوظٌ بين البدائل',
          m['status'] == 'accepted' and m['level'] == 'ranked' and 'ليس/I' in m['selection'].get('alternatives', []), m)
    m = morph('فَجَعَلْتُمْ')
    check('فَجَعَلۡتُمۡ: لا منافس، فالجذر مثبت (لا مرجَّح)', m['status'] == 'accepted' and m['level'] == 'event', m)
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
