#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار T19a–T19c: الخلية، والجذر والصيغة المرخَّصان بشهادة HFN.
يحتاج HFN release_v18 (SARF_HFN، أو ../husseinframenet/release/release_v18، أو
~/arabic-net/HusseinFrameNet/release/release_v18)؛ وبدونه تُختبر الخلايا وحدها.

    python3 tests/test_root.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    ]
    for w, st, lv, root, cls in CASES:
        m = morph(w)
        got = (m['status'], m.get('level'), m.get('root'), m.get('form_class')) if m else None
        check(f'Morph({w})', got == (st, lv, root, cls), got)
    m = morph('قُلْ')
    check('الشاهد: الحدث ومصدره', m['licensed'] and m['licensed'][0]['verb'] == 'قَالَ' and
          m['licensed'][0]['event_id'].startswith('HFN-E-'), m['licensed'][:1])
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
