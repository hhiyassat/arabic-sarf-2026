#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار صلاح الخبيئة والإجازة (مراجعة التقرير الخامسة ٤–٥)، في نسخةٍ مؤقتة من المستودع لا تمسّ الملفات الحقيقية:
  ١. تشغيلٌ يكتب ملف جمل الفاتحة وخبيئتها، ثم إجازتها
  ٢. تشغيلٌ بالاعتماديات نفسها: تُحمَّل الفاتحة من الخبيئة، وجملها هي المجازة
  ٣. تغييرُ قاعدةٍ مؤثرة في sarf/algebra.py: تبطل الخبيئة، ويُعاد التحليل، ويُكشف الفرق «تغيّراً يحتاج مراجعة»،
     ويبقى الملف المجاز كما هو بايتاً ببايت

    python3 tests/test_cache.py      (نحو ثلاث دقائق)
"""
import os, sys, json, shutil, subprocess, tempfile, hashlib

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bad = 0


def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)


tmp = tempfile.mkdtemp(prefix='sarf_cache_')
for d in ('sarf', 'tools', 'lexicon'):
    shutil.copytree(os.path.join(H, d), os.path.join(tmp, d), ignore=shutil.ignore_patterns('__pycache__'))
for f in ('operators_catalog.jsonl', 'operators_catalog_split_vocalized.csv'):
    shutil.copy(os.path.join(H, f), tmp)
os.makedirs(os.path.join(tmp, 'data'))
for x in os.listdir(os.path.join(H, 'data')):
    if x != 'cache':
        os.symlink(os.path.join(H, 'data', x), os.path.join(tmp, 'data', x))
os.makedirs(os.path.join(tmp, 'reports'))
subprocess.run(['git', 'init', '-q', tmp])


def run(tag):
    m = os.path.join(tmp, f'm_{tag}.json')
    subprocess.run([sys.executable, 'tools/algebra_quran.py', '--limit', '7', '--no-cross'], cwd=tmp,
                   env=dict(os.environ, SARF_ALG_METRICS=m), capture_output=True, check=True)
    return json.load(open(m, encoding='utf-8'))


M1 = run('1')
csv1 = os.path.join(tmp, 'reports/sentences/surah_001.csv')
check('١: كُتب ملف جمل الفاتحة وخبيئتها', os.path.exists(csv1) and os.path.exists(os.path.join(tmp, 'data/cache/surah_001.pkl.gz')))
subprocess.run([sys.executable, 'tools/approve_surah.py', '1'], cwd=tmp, check=True, capture_output=True)
approved = open(csv1, 'rb').read()
M2 = run('2')
c2 = M2['counts']
check('٢: بالاعتماديات نفسها تُحمَّل الفاتحة من الخبيئة، وجملها هي المجازة',
      c2.get('surahs_from_cache') == 1 and c2.get('approved_same') == 1 and not c2.get('cache_invalidated'), c2)
# تغيير قاعدةٍ مؤثرة في ملف الفاتحة: سببُ التزام «استقلال الحدّ لفظاً»
p = os.path.join(tmp, 'sarf/algebra.py')
src = open(p, encoding='utf-8').read()
assert "'حدّ الآية أو السورة غير مفحوص لفظاً'" in src
open(p, 'w', encoding='utf-8').write(src.replace("'حدّ الآية أو السورة غير مفحوص لفظاً'",
                                                 "'حدّ الآية أو السورة غير مفحوص لفظاً (اختبار تغيّر القاعدة)'"))
open(p, 'a', encoding='utf-8').write('\n# تغيير اختبار\n')
M3 = run('3')
c3 = M3['counts']
check('٣: تغيّرت الاعتماديات فبطلت الخبيئة وأُعيد تحليل الفاتحة', c3.get('cache_invalidated') == 1 and
      not c3.get('surahs_from_cache'), c3)
drift = os.path.join(tmp, 'reports/sentences/drift/surah_001.csv')
check('وكُشف الفرق «تغيّراً يحتاج مراجعة»، والجديد في drift/', c3.get('approved_changed') == 1 and os.path.exists(drift) and
      any('تغيّرٌ يحتاج مراجعة' in x for x in M3['failures'].get('approved_changed', [])), M3['failures'])
check('وبقي الملف المجاز كما هو بايتاً ببايت', open(csv1, 'rb').read() == approved,
      hashlib.sha256(open(csv1, 'rb').read()).hexdigest())
shutil.rmtree(tmp, ignore_errors=True)
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
