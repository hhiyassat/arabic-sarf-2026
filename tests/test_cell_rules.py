#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
قواعد الخلايا المعتمدة من صاحب النظرية: اختبارات قبول.

١. الألف الخنجرية مع الألف المقصورة «ىٰ» (3 نوفمبر): تُحذف الخنجرية من التمثيل التحليلي وتبقى «ى»؛
   ولا يُعمَّم الحذف على الخنجرية في غير هذا الموضع؛ ولا تُحوَّل «ى» إلى «ا» ولا تُنشأ ألفٌ ثانية؛
   ويبقى المصدر محفوظاً، ويُسجَّل الحذف وموضعه في أثر التحويل.

    python3 tests/test_cell_rules.py
"""
import os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.normalize_trace import normalize_traced, reconstruct_source

bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

DAG = 'ٰ'
for src, want in (('مُوسَىٰ', 'مُوسَى'), ('إِلَىٰ', 'إِلَى'), ('إِحۡدَىٰهُمَا', 'إِحْدَىهُمَا')):
    r = normalize_traced(src)
    a = r['analysis']
    ops = [o for o in r['ops_analysis'] if o['rule_id'] == 'N-DAGGER-MAQSURA']
    check(f'«{src}» ← «{want}» في التمثيل التحليلي', a == want, a)
    check(f'«{src}»: «ى» باقية، ولا «ا» منشأة', 'ى' in a and a.count('ا') == want.count('ا'), a)
    check(f'«{src}»: الحذف مسجَّلٌ بقاعدته وموضعه في المصدر', len(ops) == 1 and ops[0]['source_spans'] and
          DAG in ''.join(src[x:y] for x, y in ops[0]['source_spans']), ops)
    cells = r['cells_analysis']
    rec = reconstruct_source(cells, r['ops_analysis'], r['source_length'])
    check(f'«{src}»: المصدر يُستعاد حرفياً', (rec[0] if isinstance(rec, tuple) else rec) == src, rec)
for src in ('ذَٰلِكَ', 'ٱلرَّحۡمَٰنِ', 'هَٰذَا'):
    r = normalize_traced(src)
    check(f'«{src}»: الخنجرية في غير «ىٰ» باقية في التمثيل التحليلي', DAG in r['analysis'] and
          not any(o['rule_id'] == 'N-DAGGER-MAQSURA' for o in r['ops_analysis']), r['analysis'])
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
