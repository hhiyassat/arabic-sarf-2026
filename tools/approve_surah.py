#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/approve_surah.py — إجازة سورةٍ بعد مراجعة ملف جملها (اقتراح صاحب النظرية): يُسجَّل في approved/surahs.csv
رقمها، وتاريخ الإجازة، ونسخة الكود التي أنتجت الملف، وبصمة الملف (sha256). وبعدها لا يُعاد تحليلها في التشغيل
(يُحمَّل من data/cache/)، وتُقارن جملها في كل تشغيلٍ بالملف المجاز: فإن اختلفت بُلِّغ بذلك ولم يُكتب فوقه.

    python3 tools/approve_surah.py 1            # إجازة الفاتحة
    python3 tools/approve_surah.py --revoke 1   # إلغاء إجازتها (حين يُكتشف خطأٌ يمسّها)
    python3 tools/algebra_quran.py --all        # إعادة التحليل كله، والمجاز معه
"""
import sys, os, csv, hashlib, subprocess, datetime

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
P = H + 'approved/surahs.csv'
COLS = ['surah', 'approved_at', 'code_version', 'sha256', 'sentences', 'note']

args = sys.argv[1:]
revoke = '--revoke' in args
nums = [int(x) for x in args if x.isdigit()]
rows = {int(r['surah']): r for r in csv.DictReader(open(P, encoding='utf-8'))} if os.path.exists(P) else {}
ver = subprocess.run(['git', '-C', H, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
for s in nums:
    if revoke:
        rows.pop(s, None)
        print(f'أُلغيت إجازة السورة {s}')
        continue
    f = H + f'reports/sentences/surah_{s:03d}.csv'
    if not os.path.exists(f):
        sys.exit(f'لا ملف جمل للسورة {s}: شغّل tools/algebra_quran.py أولاً')
    if not os.path.exists(H + f'data/cache/surah_{s:03d}.pkl.gz'):
        sys.exit(f'لا خبيئة تحليل للسورة {s}: شغّل tools/algebra_quran.py أولاً')
    data = open(f, 'rb').read()
    n = max(0, data.decode('utf-8').count('\n') - 1)
    rows[s] = dict(surah=s, approved_at=datetime.date.today().isoformat(), code_version=ver,
                   sha256=hashlib.sha256(data).hexdigest(), sentences=n, note='')
    print(f'أُجيزت السورة {s}: {n} جملة، بنسخة الكود {ver}')
os.makedirs(os.path.dirname(P), exist_ok=True)
with open(P, 'w', encoding='utf-8', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=COLS)
    w.writeheader()
    for s in sorted(rows):
        w.writerow({k: rows[s].get(k, '') for k in COLS})
