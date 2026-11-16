#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E3 (MASAQ-E3): توافق الجذع مع مرشّح الجذر عبر align_radicals (تحقيق §٤)، مربوطاً بهويّة الوجه.
   - SUPPORTED: تحاذت الأصول بترتيبها (مع إعلال/إدغام مرخَّص إن وُجد، محفوظاً في transformations).
   - CONTRADICTED: أصلٌ لا تقابله خليّة — دليلٌ موجبٌ (السبب محفوظ)؛ لا يُشتق من قصور _verb_licensed.
   - UNRESOLVED: تعذّرت المحاذاة — غياب الدعم تأجيلٌ لا خطأ.
   الترتيب تسلسلٌ لا اختيار: الأوجه المتعدّدة تبقى بحالاتها، ولا يُفرض جذرٌ واحد."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sarf.root import morph, morph_faces, stem_root_verdict

ok = True
def check(cond, msg):
    global ok
    print(('PASS ' if cond else 'FAIL ') + msg)
    ok = ok and cond

# 1) الحكم مربوطٌ بكل وجه (هويّة الوجه = الجذر والوزن)، ولا وجهَ بلا حكم
out = morph('يُنصَرُونَ')
faces = morph_faces('يُنصَرُونَ', out)
check(all('stem_root' in f and f['stem_root'].get('state') for f in faces),
      'كل وجهٍ يحمل حكم stem_root مربوطاً بهويّته: ' + ', '.join('%s/%s=%s' % (f['root'], f['form_class'], f['stem_root']['state']) for f in faces))

# 2) SUPPORTED بلا تحويل (جذرٌ صحيحٌ سالم)
v = stem_root_verdict('كَتَبْ', 'كتب')
check(v['state'] == 'SUPPORTED' and not v.get('transformations'), 'كَتَبْ/كتب SUPPORTED بلا تحويل: %s' % v)

# 3) SUPPORTED بإدغامٍ مرخَّص (مضعَّف): تضعيف الجذر محفوظٌ في التحويل
v = stem_root_verdict('ظَنَنْ', 'ظنن')
check(v['state'] == 'SUPPORTED', 'ظَنَنْ/ظنن SUPPORTED (مضعَّف): %s' % v)
v = stem_root_verdict('مَدّ', 'مدد')
check(v['state'] == 'SUPPORTED' and any('إدغام' in t for t in v.get('transformations', [])), 'مَدّ/مدد SUPPORTED بإدغام: %s' % v)

# 4) SUPPORTED بإعلالٍ مرخَّص (أجوف): الأصل المعتل يجوز ألا تقابله خليّة
v = stem_root_verdict('قَالْ', 'قول')
check(v['state'] == 'SUPPORTED' and any('إعلال' in t for t in v.get('transformations', [])), 'قَالْ/قول SUPPORTED بإعلال: %s' % v)

# 5) CONTRADICTED: أصلٌ صحيحٌ لا تقابله خليّة — دليلٌ موجبٌ (لا قصور أداة)
v = stem_root_verdict('كَتَبْ', 'جعل')
check(v['state'] == 'CONTRADICTED' and v.get('reason'), 'كَتَبْ/جعل CONTRADICTED بدليل: %s' % v)
v = stem_root_verdict('تَنْ', 'تنن')
check(v['state'] == 'CONTRADICTED', 'تَنْ/تنن CONTRADICTED (الأصل r3 بلا خليّة): %s' % v)

# 6) UNRESOLVED: لا جذر — تأجيلٌ لا خطأ
v = stem_root_verdict('كَتَبْ', '')
check(v['state'] == 'UNRESOLVED', 'جذرٌ فارغ UNRESOLVED (تأجيل): %s' % v)

# 7) الترتيب تسلسلٌ لا اختيار: يَمُدُّ مؤجَّلٌ، ومرشّحاته محفوظةٌ كلها بحالتها، لا يُفرض اختيار
out = morph('يَمُدُّ')
faces = morph_faces('يَمُدُّ', out)
states = {(f['root'], f['form_class']): f['stem_root']['state'] for f in faces}
check(out.get('status') == 'deferred' and ('مدد', 'I') in states and len(states) >= 2,
      'يَمُدُّ مؤجَّلٌ ومرشّحاته محفوظةٌ بحالاتها (لا اختيار): %s' % states)

# 8) ثبات الحكم عبر البذور: الحكم تحليلٌ لا ترتيب عشوائي
import subprocess, json
WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
hashes = set()
for seed in ('0', '1', '7'):
    r = subprocess.run([sys.executable, '-c',
        'import sys,hashlib,json; sys.path.insert(0,%r);'
        'from sarf.root import morph, morph_faces;'
        'h=hashlib.sha256();\n'
        'import os\n'
        'words=["يُنصَرُونَ","يَمُدُّ","قَالُوا","ظَنَنْ","كَتَبُوا"]\n'
        'for w in words:\n'
        '    o=morph(w)\n'
        '    if not o: continue\n'
        '    for f in morph_faces(w,o): h.update(json.dumps([f["root"],f["form_class"],f.get("stem_root")],ensure_ascii=False,sort_keys=True).encode())\n'
        'print(h.hexdigest())' % WT],
        capture_output=True, text=True, env={**os.environ, 'PYTHONHASHSEED': seed})
    hashes.add(r.stdout.strip())
check(len(hashes) == 1, 'حكم stem_root ثابتٌ عبر البذور 0/1/7: %s' % hashes)

print('ALL_PASS:', ok)
sys.exit(0 if ok else 1)
