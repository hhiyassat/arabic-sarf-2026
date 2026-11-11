# -*- coding: utf-8 -*-
"""تثبيت الإصدار في العامل المعزول وطبقات AMLN/wazn-net (SARF_HFN_V48_VALIDATION_COMPLETION_02 §٤).
- العامل مثبَّت على إصدار HFN في ملفّ التثبيت (SARF_UP_PINS)، وSARF على إصدار إعداده (الإنتاجي v47 أو التجريبي v48).
- تطابقهما مقبول؛ واختلافهما إخفاق هويةٍ مسمّى، إلا بإذن ظلٍّ صريح (SARF_UP_HFN_SHADOW_OK=<إصدار العامل>).
- طبقات AMLN وواجهتها تُعطى AMLN_HFN_RELEASE وARABIC_NET_HFN_RELEASE على إصدار التثبيت، لا «أحدث إصدار».
يحتاج SARF_UP_PINS وSARF_HFN_V48_DIR؛ وبغيابهما NOT_RUN (رمز 2)."""
import os, subprocess, sys
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PINS, V48 = os.environ.get('SARF_UP_PINS', ''), os.environ.get('SARF_HFN_V48_DIR', '')
if not (os.path.isfile(PINS) and os.path.isdir(V48)):
    print('NOT_RUN: SARF_UP_PINS أو SARF_HFN_V48_DIR غير متاح'); sys.exit(2)
FAIL, N = [], [0]


def check(name, ok, got=''):
    N[0] += 1
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:400]}'))
    if not ok:
        FAIL.append(name)


CODE = "import sys; sys.path.insert(0, 'tools/upstream'); import client; p = client.load_pins(); print('PINS', p['hfn_release'])"


def run(extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith(('SARF_HFN_TARGET', 'SARF_HFN_EXPERIMENTAL', 'SARF_UP_HFN_SHADOW'))}
    env.update(extra)
    p = subprocess.run([sys.executable, '-s', '-c', CODE], cwd=H, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


E48 = dict(SARF_HFN=V48, SARF_HFN_TARGET_CONFIG='config/hfn_target_v48_experimental.json', SARF_HFN_EXPERIMENTAL_OK='release_v48')
rc, out, err = run({})
check('U01 الإعداد الإنتاجي (v47) والعامل مثبَّت على release_v47: مقبول', rc == 0 and 'PINS release_v47' in out, err[-300:])
rc, out, err = run(E48)
check('U02 SARF على v48 التجريبي والعامل على v47 بلا إذن ظلّ: HFN_IDENTITY_MISMATCH', rc != 0 and 'HFN_IDENTITY_MISMATCH' in err, err[-300:])
rc, out, err = run(dict(E48, SARF_UP_HFN_SHADOW_OK='release_v46'))
check('U03 إذن ظلٍّ بإصدارٍ آخر غير إصدار العامل: مرفوض', rc != 0 and 'HFN_IDENTITY_MISMATCH' in err, err[-300:])
rc, out, err = run(dict(E48, SARF_UP_HFN_SHADOW_OK='release_v47'))
check('U04 إذن ظلٍّ صريح بإصدار العامل (release_v47): مقبولٌ ومعلن', rc == 0 and 'PINS release_v47' in out, err[-300:])
src = open(os.path.join(H, 'tools', 'upstream', 'client.py'), encoding='utf-8').read()
check('U05 العامل يعطي طبقات AMLN وواجهتها إصدار التثبيت صراحةً (AMLN_HFN_RELEASE، ARABIC_NET_HFN_RELEASE)، ويُشغَّل معزولاً (-I)',
      "AMLN_HFN_RELEASE=pins['hfn_release']" in src and 'ARABIC_NET_HFN_RELEASE=rel_dir' in src and "'-I', '-B'" in src)
print(f'CHECKS pass={N[0] - len(FAIL)} fail={len(FAIL)} total={N[0]}')
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
