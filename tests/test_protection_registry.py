"""tests/test_protection_registry.py — سجل حماية الإصلاحات السابقة (§٣ من الجولة 04، و§٩ من الجولة 05): لكل بندٍ فحوصٌ سلوكية بعينها.

يفشل إن صار بندٌ بلا فحص، أو كان فحصٌ مرتبط غير ناجحٍ في التشغيل الذي وُلِّد منه السجل، أو حُذف ملف اختباره.
والفحوص نفسها هي التي تفشل إن عاد الخلل."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL = []


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {got}'))
    if not cond:
        FAIL.append(name)


reg = json.load(open(os.path.join(ROOT, 'tests', 'protection_registry.json'), encoding='utf-8'))
check('PR00 الربط سلوكيٌّ مسمّى لا كلماتٌ مفتاحية', 'سلوكي' in reg.get('method', ''), reg.get('method'))
for it in reg['items']:
    missing_file = [t['test'] for t in it['tests'] if not os.path.exists(os.path.join(ROOT, 'tests', t['test'] + '.py'))]
    not_pass = [f"{t['test']}:{t['check_id']} ({t['observed']})" for t in it['tests'] if t['observed'] != 'PASS']
    check(f"{it['id']} {it['description']}: {it['n_tests']} فحصاً سلوكياً ناجحاً", it['tests'] and not missing_file and not not_pass,
          missing_file + not_pass)
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
