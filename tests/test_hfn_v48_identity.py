# -*- coding: utf-8 -*-
"""عزل الإصدارين v47 وv48 (SARF_HFN_V48_COMPARATIVE_VALIDATION_01 §٢، وSARF_HFN_V48_VALIDATION_COMPLETION_02 §٣).

الإصلاح عن النسخة السابقة: كان المتتبّع يطبع basename ثم يبحث I07 عن مسار v47 الكامل في نصٍّ حُذف منه المسار، فلا يسقط أبداً.
الآن: يُسجَّل لكل فتحٍ المسار المطلوب والمطلق والمحلول (بالروابط الرمزية) والنمط والإطار الذي فتحه (tools/hfn_isolation)،
ويُنسب الإصدار بالمسار المحلول إلى جذرٍ مثبَّت، ويُصنَّف الغرض بالإطار (بصمة، بيان، تحميل صفوف)، لا بنمط rb وحده.
واختبارات الإفساد X1–X7 تحقن قراءةً من الإصدار الآخر أو تخلط الهوية، ويجب أن يُسقطها الفاحص.
يحتاج SARF_HFN_V47_DIR وSARF_HFN_V48_DIR؛ وبغيابهما NOT_RUN (رمز 2)، لا نجاح."""
import json, os, shutil, subprocess, sys, tempfile, threading
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V47, V48 = os.environ.get('SARF_HFN_V47_DIR', ''), os.environ.get('SARF_HFN_V48_DIR', '')
if not (os.path.isdir(V47) and os.path.isdir(V48)):
    print('NOT_RUN: SARF_HFN_V47_DIR وSARF_HFN_V48_DIR غير معيَّنين أو غير موجودين')
    sys.exit(2)
sys.path.insert(0, os.path.join(H, 'tools', 'hfn_isolation'))
import check as ISO
FAIL, PASSN = [], [0]
EXP = 'config/hfn_target_v48_experimental.json'
ROOTS = dict(release_v47=V47, release_v48=V48)
TMP = tempfile.mkdtemp(prefix='hfn_iso_')
OUT = os.environ.get('SARF_ISO_OUT')          # مجلّدٌ تُحفظ فيه سجلات الفتح والنتائج المنظَّمة (اختياري)
RESULTS = []


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:500]}'))
    RESULTS.append(dict(name=name, ok=bool(ok), got=None if ok else str(got)[:2000]))
    if ok:
        PASSN[0] += 1
    else:
        FAIL.append(name)


CODE = r'''
import sys
from sarf.root import hfn
from sarf.stages import run_ref
h = hfn()
run_ref('112:1', None, ['certificates'])
print('PIN', h.pin.get('release'), h.pin.get('config_mode'), (h.pin.get('manifest_sha256') or '')[:12], h.path)
'''


def run(tag, env_extra, inject=None, roots=None, code=CODE):
    env = {k: v for k, v in os.environ.items() if not k.startswith(('SARF_HFN', 'SARF_AJNAS', 'SARF_OPEN'))}
    log = os.path.join(TMP, tag)
    env.update(PYTHONHASHSEED='0', PYTHONPATH=os.path.join(H, 'tools', 'hfn_isolation'), SARF_OPEN_LOG=log,
               SARF_OPEN_ROOTS=':'.join((roots or ROOTS).values()), **env_extra)
    if inject:
        env['SARF_OPEN_INJECT'] = inject
    p = subprocess.run([sys.executable, '-s', '-c', code], cwd=H, capture_output=True, text=True, env=env)
    recs = ISO.load(log)
    return p.returncode, p.stdout, p.stderr, recs


def audit(tag, recs, expected, roots=None, allow=None):
    res = ISO.check(recs, roots or ROOTS, expected, allow)
    if OUT:
        os.makedirs(OUT, exist_ok=True)
        json.dump(dict(tag=tag, expected=expected, summary=ISO.summary(res), violations=res['violations']),
                  open(os.path.join(OUT, f'iso_{tag}.json'), 'w'), ensure_ascii=False, indent=1)
    return res


def loads(res, fname, rel):
    return [r for r in res['records'] if os.path.basename(r['realpath']) == fname and r['release'] == rel and r['purpose'] == 'LOAD_ROWS']


# ── التشغيل السليم ──
rc, out, err, recs = run('v47', dict(SARF_HFN=V47))
r47 = audit('v47', recs, 'release_v47')
check('I01 الإعداد الإنتاجي مع v47: يُقرأ release_v47 بالإعداد الإنتاجي', rc == 0 and 'PIN release_v47 PRODUCTION aca692e38785' in out, err[-400:] or out)
check('I02 تشغيل v47: صفر مخالفات بالمسار المحلول، ولا فتح لأي ملفٍّ من v48 (ولا ahdath_ajnas)',
      not r47['violations'] and r47['records'] and not any(r['release'] == 'release_v48' or 'ahdath_ajnas' in r['realpath'] for r in r47['records']),
      r47['violations'][:3] or 'لا سجلات')
check('I03 تشغيل v47 يحمّل صفوف events وlexical_units وform_meanings من release_v47 (بالمسار المحلول والإطار)',
      all(loads(r47, f, 'release_v47') for f in ('events.csv', 'lexical_units.csv', 'form_meanings.csv')), ISO.summary(r47)['by_file_purpose'])
rc, out, err, recs = run('v48_prod', dict(SARF_HFN=V48))
check('I04 v48 بالإعداد الإنتاجي مرفوض', rc != 0 and 'ليس الإصدار المستهدف' in err, err[-300:])
rc, out, err, recs = run('v48', dict(SARF_HFN=V48, SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v48'))
r48 = audit('v48', recs, 'release_v48')
check('I05 الإعداد التجريبي والإذن الصريح: يُقرأ release_v48 بالإعداد التجريبي', rc == 0 and 'PIN release_v48 EXPERIMENTAL 6cd85dc63b1e' in out, err[-400:] or out)
aj = [r for r in r48['records'] if os.path.basename(r['realpath']) == 'ahdath_ajnas.csv']
check('I06 تشغيل v48: ahdath_ajnas يُفتح لحساب البصمة وحده (الإطار hfn_pin._sha)، ولا تُحمَّل صفوفه',
      aj and all(r['purpose'] == 'HASH_VERIFY' for r in aj), [(r['mode'], r['caller'], r['purpose']) for r in aj])
check('I07 تشغيل v48: صفر مخالفات بالمسار المحلول، وتحميل الصفوف الثلاثة من release_v48، ولا فتح لأي ملفٍّ من v47',
      not r48['violations'] and all(loads(r48, f, 'release_v48') for f in ('events.csv', 'lexical_units.csv', 'form_meanings.csv'))
      and not any(r['release'] == 'release_v47' for r in r48['records']), r48['violations'][:3])
for name, env, needle in (
        ('I08 الإعداد التجريبي بلا إذن', dict(SARF_HFN=V48, SARF_HFN_TARGET_CONFIG=EXP), 'HFN_IDENTITY_MISMATCH'),
        ('I09 الإذن بلا إعداد', dict(SARF_HFN=V47, SARF_HFN_EXPERIMENTAL_OK='release_v48'), 'HFN_IDENTITY_MISMATCH'),
        ('I10 إذنٌ بإصدارٍ غير إصدار الإعداد', dict(SARF_HFN=V48, SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v47'), 'HFN_IDENTITY_MISMATCH'),
        ('I11 الإعداد التجريبي مع مجلّد v47', dict(SARF_HFN=V47, SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v48'), 'ليس الإصدار المستهدف')):
    rc, out, err, recs = run('neg', env)
    check(name + ': إخفاق هويةٍ مسمّى', rc != 0 and needle in err, err[-300:])
cfg = open(os.path.join(H, 'config', 'hfn_target.json'), encoding='utf-8').read()
check('I13 الإعداد الإنتاجي لم يتغيّر (release_v47، التزام 22dcb06، MANIFEST aca692e3)',
      cfg.count('aca692e38785573f811e93b4e2cab531a239642f3cac5d5225664645e987b919') == 1 and '"release": "release_v47"' in cfg
      and '22dcb06e21221750b41879f2f598bb28a23f440a' in cfg, cfg[:300])

# ── الإفساد: كل واحدٍ منها يجب أن يُسقطه الفاحص أو البوابة ──
# X1 تشغيل v48 يفتح عمداً ملفاً من v47 بالاسم نفسه
rc, out, err, recs = run('x1', dict(SARF_HFN=V48, SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v48'),
                         inject=os.path.join(V47, 'events.csv'))
x1 = audit('x1', recs, 'release_v48')
check('X1 قراءةٌ محقونة من v47/events.csv في تشغيل v48: يسقطها الفاحص (READ_FROM_OTHER_RELEASE)',
      rc == 0 and any('READ_FROM_OTHER_RELEASE:release_v47' in v['why'] for v in x1['violations']), x1['violations'][:2] or 'لم تُكشف')
# X2 تشغيل v47 يفتح ملفاً من v48
rc, out, err, recs = run('x2', dict(SARF_HFN=V47), inject=os.path.join(V48, 'events.csv'))
x2 = audit('x2', recs, 'release_v47')
check('X2 قراءةٌ محقونة من v48/events.csv في تشغيل v47: يسقطها الفاحص',
      rc == 0 and any('READ_FROM_OTHER_RELEASE:release_v48' in v['why'] for v in x2['violations']), x2['violations'][:2] or 'لم تُكشف')
# X3 رابطٌ رمزي داخل مجلّد إصدار v48 يشير إلى v47 (والملف متطابق البايتات، فبصمة MANIFEST وحدها لا تكشفه)
fake48 = os.path.join(TMP, 'x3', 'release_v48'); os.makedirs(fake48)
for f in os.listdir(V48):
    s = os.path.join(V48, f)
    if os.path.isdir(s):
        shutil.copytree(s, os.path.join(fake48, f))
    else:
        shutil.copy2(s, os.path.join(fake48, f))
os.remove(os.path.join(fake48, 'lexical_units.csv'))
os.symlink(os.path.join(V47, 'lexical_units.csv'), os.path.join(fake48, 'lexical_units.csv'))
roots3 = dict(release_v47=V47, release_v48=fake48)
rc, out, err, recs = run('x3', dict(SARF_HFN=fake48, SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v48'), roots=roots3)
x3 = audit('x3', recs, 'release_v48', roots3)
check('X3 رابطٌ رمزي في مجلّد v48 إلى ملف v47: بوابة البصمة تجتازه (الملف متطابق)، والفاحص يسقطه (SYMLINK_CROSS)',
      rc == 0 and any(any(w.startswith('SYMLINK_CROSS:release_v48->release_v47') for w in v['why']) for v in x3['violations']),
      (rc, err[-200:], x3['violations'][:2]))
# X4 مجلّدٌ اسمه release_v48 ومحتواه v47
fake = os.path.join(TMP, 'x4', 'release_v48'); os.makedirs(fake)
for f in os.listdir(V47):
    os.symlink(os.path.join(V47, f), os.path.join(fake, f))
rc, out, err, recs = run('x4', dict(SARF_HFN=fake, SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v48'))
check('X4 مجلّد باسم release_v48 ومحتوى v47: مرفوضٌ ببصمة MANIFEST قبل أي تحميل', rc != 0 and 'بصمة MANIFEST' in err, err[-300:])
# X5 ملفٌّ صحيح الاسم ببصمةٍ مختلفة
fake5 = os.path.join(TMP, 'x5', 'release_v48'); shutil.copytree(fake48, fake5, symlinks=False)
with open(os.path.join(fake5, 'events.csv'), 'a', encoding='utf-8') as f:
    f.write('\n')
rc, out, err, recs = run('x5', dict(SARF_HFN=fake5, SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v48'))
x5 = audit('x5', recs, 'release_v48', dict(release_v47=V47, release_v48=fake5))
check('X5 events.csv صحيح الاسم ببصمةٍ أخرى: مرفوضٌ قبل تحميل صفوفه', rc != 0 and 'ببصمةٍ أخرى' in err and 'events.csv' in err
      and not any(r['purpose'] == 'LOAD_ROWS' for r in x5['records']), (err[-300:], [r['purpose'] for r in x5['records']][:5]))
# X6 الإصدار المطلوب غير الإصدار الذي تخدمه الواجهة
sys.path.insert(0, os.path.join(H, 'tools', 'ajnas'))
import consumer as AC
API = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(V48))), 'api')
try:
    AC.AjnasConsumer(AC.DirectBackend(V47, API), 'HFN_release_v48', '6cd85dc63b1e920420b09e6d4be748188e37cfc32fe780a05fa2568534119a75')
    x6 = 'لم يُرفض'
except AC.AjnasIdentityError as e:
    x6 = str(e)
check('X6 مستهلك الروابط يطلب v48 والواجهة تخدم v47: HFN_IDENTITY_MISMATCH', x6.startswith('HFN_IDENTITY_MISMATCH'), x6)
try:
    AC.DirectBackend(None, API); x6b = 'لم يُرفض'
except AC.AjnasIdentityError as e:
    x6b = str(e)
check('X6b بلا مسار إصدارٍ صريح لا يُخدم «أحدث إصدار»', x6b.startswith('HFN_IDENTITY_MISMATCH'), x6b)
# X7 تشغيلان متوازيان بإصدارين: لا تسرّب، والفاحص يميّز
res = {}
def _t(tag, env, exp):
    res[tag] = (run(tag, env), exp)
ts = [threading.Thread(target=_t, args=('p47', dict(SARF_HFN=V47), 'release_v47')),
      threading.Thread(target=_t, args=('p48', dict(SARF_HFN=V48, SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v48'), 'release_v48'))]
[t.start() for t in ts]; [t.join() for t in ts]
ok7 = all(res[t][0][0] == 0 and not audit(t, res[t][0][3], res[t][1])['violations'] for t in res)
cross = audit('p48_as_v47', res['p48'][0][3], 'release_v47')
check('X7 تشغيلان متوازيان (v47 وv48): كلٌّ يقرأ إصداره وحده، وسجلّ v48 مفحوصاً على أنه v47 يُسقَط',
      ok7 and len(cross['violations']) > 0, (ok7, len(cross['violations'])))
# X7b عملية v48 تُطلق عمليةً فرعية لـ v47 وترثها متغيّرات الإعداد التجريبي: إخفاق هويةٍ مسمّى لا خلط
rc, out, err, recs = run('x7b', dict(SARF_HFN=V47, SARF_HFN_RELEASE_OK='release_v47', SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v48'))
check('X7b إعدادٌ موروث من تشغيلٍ سابق (v48) في عمليةٍ لـ v47: مرفوض بالاسم', rc != 0 and 'ليس الإصدار المستهدف' in err, err[-200:])
# X7c داخل العملية الواحدة: hfn() مخزَّن؛ تغيير SARF_HFN بعد التحميل لا يبدّل الإصدار، وحارس الهوية يكشف الاختلاف
code7 = r'''
import os, sys
sys.path.insert(0, 'tools/hfn_isolation')
from sarf.root import hfn
import guard
a = hfn().release
os.environ['SARF_HFN'] = os.environ['X7_OTHER']
b = hfn().release
try:
    guard.assert_identity(); print('GUARD', 'PASSED', a, b)
except guard.HFNIdentityError as e:
    print('GUARD', 'REFUSED', a, b, str(e)[:120])
'''
rc, out, err, recs = run('x7c', dict(SARF_HFN=V48, SARF_HFN_TARGET_CONFIG=EXP, SARF_HFN_EXPERIMENTAL_OK='release_v48', X7_OTHER=V47), code=code7)
check('X7c تبديل SARF_HFN داخل عمليةٍ واحدة: الإصدار المحمَّل يبقى v48 (لا خلط صامت)، والحارس يرفض استمرار التشغيل',
      rc == 0 and 'GUARD REFUSED release_v48 release_v48' in out, (out, err[-300:]))
if OUT:
    json.dump(RESULTS, open(os.path.join(OUT, 'test_hfn_v48_identity.results.json'), 'w'), ensure_ascii=False, indent=1)
shutil.rmtree(TMP, ignore_errors=True)
print(f'CHECKS pass={PASSN[0]} fail={len(FAIL)} total={PASSN[0] + len(FAIL)}')
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
