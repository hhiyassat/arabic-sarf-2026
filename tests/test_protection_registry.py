"""tests/test_protection_registry.py — سجل حماية الإصلاحات السابقة (SARF_COMPREHENSIVE_REPAIR_04 §٣): لكل بندٍ اختبارٌ مرتبط باقٍ في ملفه.

يفشل إن صار بندٌ بلا اختبار، أو حُذف فحصٌ مرتبطٌ من ملف اختباره؛ والاختبارات نفسها هي التي تفشل إن عاد الخلل."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL = []


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {got}'))
    if not cond:
        FAIL.append(name)


reg = json.load(open(os.path.join(ROOT, 'tests', 'protection_registry.json'), encoding='utf-8'))
for it in reg['items']:
    missing = []
    for t in it['tests']:
        src = open(os.path.join(ROOT, 'tests', t['test'] + '.py'), encoding='utf-8').read()
        if t['check_id'] not in src:
            missing.append(f"{t['test']}:{t['check_id']}")
    check(f"{it['id']} {it['description']}: {it['n_tests']} فحصاً مرتبطاً باقياً في ملفاته", it['tests'] and not missing, missing or it['status'])
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
