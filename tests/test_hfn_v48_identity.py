# -*- coding: utf-8 -*-
"""SARF_HFN_V48_COMPARATIVE_VALIDATION_01 §٢: لا خلط بين الإصدارين.
- تشغيل v47 يقرأ v47 فعلاً، ولا يقرأ ملف روابط v48 (ولا يوجد في مجلّده)؛
- تشغيل v48 لا يُقرأ إلا بالإعداد التجريبي والإذن الصريح معاً، ويقرأ v48 فعلاً؛
- كل اختلافٍ بين المطلوب والمخدوم إخفاق هويةٍ مسمّى؛ ومجلّدٌ باسم إصدارٍ ومحتوى غيره يُرفض ببصمة MANIFEST.
يحتاج SARF_HFN_V47_DIR وSARF_HFN_V48_DIR؛ وبغيابهما «غير منفّذ» (رمز 2)، لا نجاح."""
import os, subprocess, sys, tempfile
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V47, V48 = os.environ.get('SARF_HFN_V47_DIR', ''), os.environ.get('SARF_HFN_V48_DIR', '')
if not (os.path.isdir(V47) and os.path.isdir(V48)):
    print('NOT_RUN: SARF_HFN_V47_DIR وSARF_HFN_V48_DIR غير معيَّنين أو غير موجودين')
    sys.exit(2)
FAIL = []
EXP = 'config/hfn_target_v48_experimental.json'


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:400]}'))
    if not ok:
        FAIL.append(name)


TRACER = r'''
import builtins, os, sys
seen = []
_o = builtins.open
def _open(f, *a, **k):
    m = a[0] if a else k.get('mode', 'r')
    try:
        p = os.path.abspath(os.fspath(f))
    except Exception:
        p = None
    if p and '/release_v' in p:
        seen.append((m, p))
    return _o(f, *a, **k)
builtins.open = _open
from sarf.root import HFN
from sarf.stages import run_ref
h = HFN()
run_ref('112:1', None, ['certificates'])
print('PIN', h.pin.get('release'), h.pin.get('config_mode'), h.pin.get('manifest_sha256', '')[:12])
for m, p in sorted(set(seen)):
    print('OPEN', m, os.path.basename(p))
'''


def run(env_extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith(('SARF_HFN', 'SARF_AJNAS'))}
    env.update(PYTHONHASHSEED='0', **env_extra)
    p = subprocess.run([sys.executable, '-s', '-c', TRACER], cwd=H, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


rc, out, err = run(dict(SARF_HFN=V47))
check('I01 الإعداد الإنتاجي مع v47: يُقرأ release_v47 بالإعداد الإنتاجي', rc == 0 and 'PIN release_v47 PRODUCTION aca692e38785' in out, err[-400:] or out)
check('I02 تشغيل v47 لا يقرأ ahdath_ajnas بأي صيغة (ولا يوجد في مجلّده)', 'ahdath_ajnas' not in out and not os.path.exists(os.path.join(V47, 'ahdath_ajnas.csv')), out)
check('I03 تشغيل v47 يقرأ محتوى events وlexical_units وform_meanings من v47',
      all(f'OPEN r {f}' in out for f in ('events.csv', 'lexical_units.csv', 'form_meanings.csv')), out)
rc, out, err = run(dict(SARF_HFN=V48))
check('I04 v48 بالإعداد الإنتاجي مرفوض', rc != 0 and 'ليس الإصدار المستهدف' in err, err[-300:])
rc, out, err = run(dict(SARF_HFN=V48, SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v48'))
check('I05 الإعداد التجريبي والإذن الصريح: يُقرأ release_v48 بالإعداد التجريبي', rc == 0 and 'PIN release_v48 EXPERIMENTAL 6cd85dc63b1e' in out, err[-400:] or out)
check('I06 تشغيل v48 يفتح ahdath_ajnas للتحقق من بصمته وحده (rb)، ولا يقرأ محتواه',
      'OPEN rb ahdath_ajnas.csv' in out and 'OPEN r ahdath_ajnas.csv' not in out, out)
check('I07 تشغيل v48 يقرأ محتوى events وlexical_units وform_meanings من v48، ولا يفتح شيئاً من v47',
      all(f'OPEN r {f}' in out for f in ('events.csv', 'lexical_units.csv', 'form_meanings.csv')) and V47 not in out, out)
for name, env, needle in (
        ('I08 الإعداد التجريبي بلا إذن', dict(SARF_HFN=V48, SARF_HFN_TARGET_CONFIG=EXP), 'HFN_IDENTITY_MISMATCH'),
        ('I09 الإذن بلا إعداد', dict(SARF_HFN=V47, SARF_HFN_EXPERIMENTAL_OK='release_v48'), 'HFN_IDENTITY_MISMATCH'),
        ('I10 إذنٌ بإصدارٍ غير إصدار الإعداد', dict(SARF_HFN=V48, SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v47'), 'HFN_IDENTITY_MISMATCH'),
        ('I11 الإعداد التجريبي مع مجلّد v47', dict(SARF_HFN=V47, SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v48'), 'ليس الإصدار المستهدف')):
    rc, out, err = run(env)
    check(name + ': إخفاق هويةٍ مسمّى', rc != 0 and needle in err, err[-300:])
# مجلّدٌ اسمه release_v48 ومحتواه v47
t = tempfile.mkdtemp(prefix='fake_v48_')
fake = os.path.join(t, 'release_v48'); os.makedirs(fake)
for f in os.listdir(V47):
    os.symlink(os.path.join(V47, f), os.path.join(fake, f))
rc, out, err = run(dict(SARF_HFN=fake, SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v48'))
check('I12 مجلّد باسم release_v48 ومحتوى v47: مرفوضٌ ببصمة MANIFEST', rc != 0 and 'بصمة MANIFEST' in err, err[-300:])
check('I13 الإعداد الإنتاجي لم يتغيّر (release_v47، التزام 22dcb06، MANIFEST aca692e3)',
      open(os.path.join(H, 'config', 'hfn_target.json'), encoding='utf-8').read().count('aca692e38785573f811e93b4e2cab531a239642f3cac5d5225664645e987b919') == 1
      and '"release": "release_v47"' in open(os.path.join(H, 'config', 'hfn_target.json'), encoding='utf-8').read())
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
