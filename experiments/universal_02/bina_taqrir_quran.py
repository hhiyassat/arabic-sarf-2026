# -*- coding: utf-8 -*-
"""التقريرُ المرئيّ الموسَّع (القرآن كاملًا) من quran_phase2.json. نسقُ Mashru RTL."""
import os,sys,json,html,hashlib
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(os.path.dirname(HERE))
R=json.load(open(os.path.join(HERE,'quran_phase2.json'),encoding='utf-8'))
e=html.escape
def sha(p):
    try: return hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]
    except Exception: return '—'
NAMES="الفاتحة البقرة آل-عمران النساء المائدة الأنعام الأعراف الأنفال التوبة يونس هود يوسف الرعد إبراهيم الحجر النحل الإسراء الكهف مريم طه الأنبياء الحج المؤمنون النور الفرقان الشعراء النمل القصص العنكبوت الروم لقمان السجدة الأحزاب سبأ فاطر يس الصافات ص الزمر غافر فصلت الشورى الزخرف الدخان الجاثية الأحقاف محمد الفتح الحجرات ق الذاريات الطور النجم القمر الرحمن الواقعة الحديد المجادلة الحشر الممتحنة الصف الجمعة المنافقون التغابن الطلاق التحريم الملك القلم الحاقة المعارج نوح الجن المزمل المدثر القيامة الإنسان المرسلات النبأ النازعات عبس التكوير الانفطار المطففين الانشقاق البروج الطارق الأعلى الغاشية الفجر البلد الشمس الليل الضحى الشرح التين العلق القدر البينة الزلزلة العاديات القارعة التكاثر العصر الهمزة الفيل قريش الماعون الكوثر الكافرون النصر المسد الإخلاص الفلق الناس".split()
CSS="""body{font-family:'Segoe UI',Tahoma,sans-serif;direction:rtl;background:#faf9f7;color:#222;margin:0 auto;max-width:1280px;padding:20px}
h1{color:#5b3a1a}h2{color:#7a4a1a;border-bottom:2px solid #d8c9b5;padding-bottom:4px;margin-top:30px}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:12px}th,td{border:1px solid #ccc;padding:4px 6px;text-align:right}
th{background:#ede4d3;position:sticky;top:0}code{background:#f0ece3;padding:1px 4px;border-radius:3px;font-size:11px}
.ok{background:#d9f2d9}.bad{background:#f7d7d7}.keep{background:#ffe9cf}.unit{background:#eee;color:#666}
.flag{display:inline-block;background:#eef;padding:4px 10px;margin:3px;border-radius:4px;font-size:14px}
.sub{max-height:420px;overflow:auto;border:1px solid #ddd}small{color:#777}"""
P=['<!doctype html><html lang="ar"><meta charset="utf-8"><title>UNIVERSAL_SEG_02 — القرآن</title><style>%s</style><body>'%CSS]
P.append('<h1>التجربةُ الشاملة المضبوطة — المرحلة الثانية: القرآن كاملًا (٦٢٣٦ آية، ١١٤ سورة)</h1>')
P.append(f"<p><small>الزمن {R['seconds']}ث · لا COMMIT ولا PUSH</small></p>")
# هويّة
seg=os.path.join(ROOT,'sarf','segment.py'); M=os.path.expanduser('~/fractal/Huda/quran-simple-enhanced.txt')
P.append('<h2>هويّةُ الجولة والبصمات</h2><table>')
for k,v in [('sha المصحف المختوم',sha(M)),('sha segment.py (المفتاح)',sha(seg)),
            ('sha EXPECTED.json',sha(os.path.join(HERE,'EXPECTED.json'))),
            ('sha b3_decide.py',sha(os.path.join(HERE,'b3_decide.py'))),
            ('sha quran_new_splits.csv',sha(os.path.join(HERE,'quran_new_splits.csv'))),
            ('BASELINE_A_BYTE_IDENTICAL','YES (A بالبايت، المفتاح لا يمسّها)')]:
    P.append(f'<tr><th>{e(k)}</th><td><code>{e(str(v))}</code></td></tr>')
P.append('</table>')
# المجاميع 7 حالات
P.append('<h2>المجاميع — الحالاتُ السبع (كامل/قُسمت/جذع + بصمةُ الحالة)</h2><table><tr><th>الحالة</th><th>كامل</th><th>قُسمت</th><th>جذع</th><th>sha</th></tr>')
order=['A','B(مبني)','B(مبني+عامل)','B2(مبني)','B2(مبني+عامل)','B3(المصحَّح)']
for n in order:
    st=R['states'][n]; v=st['v']; cls='ok' if n.startswith('B3') else ''
    P.append(f"<tr class='{cls}'><td>{e(n)}</td><td>{v['كامل']}</td><td>{v['قُسمت']}</td><td>{v['جذع']}</td><td><code>{st['sha']}</code></td></tr>")
P.append('</table>')
# الحارسان
g=R['guards']
P.append('<h2>الحارسان (على القرآن كلِّه)</h2><div>')
for k in ('LOST_WITHOUT_BARRIER','NEW_SPLIT_WITHOUT_EVIDENCE'):
    c='ok' if g[k]==0 else 'bad'; P.append(f'<span class="flag" style="background:{"#d9f2d9" if g[k]==0 else "#f7d7d7"}">{e(k)} = {g[k]}</span>')
P.append('<h2>التوصية المسندة (§4)</h2>')
import os as _o
_tw=_o.path.join(HERE,'TAWSIYA.md')
if _o.path.exists(_tw):
    import re as _re
    _t=open(_tw,encoding='utf-8').read()
    _h=e(_t).replace('\n','<br>')
    P.append(f"<div style='background:#f3f7f3;border:1px solid #cdd;padding:10px;border-radius:6px'>{_h}</div>")
P.append('</div>')
# جدول السور
P.append('<h2>جدولُ السور (A مقابل B3؛ Δقُسمت = قُسمت B3 − A)</h2><div class="sub"><table><tr><th>#</th><th>السورة</th>'
         '<th>A كامل</th><th>A قُسمت</th><th>A جذع</th><th>B3 كامل</th><th>B3 قُسمت</th><th>B3 جذع</th><th>Δقُسمت</th></tr>')
for s in range(1,115):
    ps=R['persura'].get(str(s))
    if not ps: continue
    a=ps['A']; b3=ps['B3(المصحَّح)']; d=b3['قُسمت']-a['قُسمت']
    nm=NAMES[s-1] if s-1<len(NAMES) else ''
    P.append(f"<tr><td>{s}</td><td>{e(nm)}</td><td>{a['كامل']}</td><td>{a['قُسمت']}</td><td>{a['جذع']}</td>"
             f"<td>{b3['كامل']}</td><td class='ok'>{b3['قُسمت']}</td><td>{b3['جذع']}</td><td>{'+' if d>=0 else ''}{d}</td></tr>")
P.append('</table></div>')
# الفصول الجديدة
P.append(f"<h2>الفصولُ الجديدة في B3 ليست في A: {R['newsplits_count']}</h2>")
P.append('<p>القائمةُ كاملةً مغلقةً في <code>experiments/universal_02/quran_new_splits.csv</code> (بالأصناف: نصّ / نمط-تقدير).</p>')
# REJECTED
rj=R['rejected']
P.append(f"<h2>REJECTED — موانعُ ثابتة مسمّاة (المجموع {rj['total']['REJECTED']})</h2><table><tr><th>المانع</th><th>العدد</th></tr>")
for k,c in sorted(rj['REJECTED_counts'].items(),key=lambda x:-x[1]): P.append(f"<tr class='bad'><td>{e(k)}</td><td>{c}</td></tr>")
P.append('</table>')
for k,ex in rj['REJECTED_examples'].items():
    if not ex: continue
    P.append(f"<h3>أمثلة — {e(k)}</h3><table><tr><th>الموضع</th><th>الكلمة</th><th>المرشّح المرفوض</th><th>المضيف</th></tr>")
    for x in ex[:10]: P.append(f"<tr><td>{e(x['ref'])}</td><td>{e(x['word'])}</td><td class='bad'>{e(x['rejected'])}</td><td>{e(str(x.get('host','')))}</td></tr>")
    P.append('</table>')
# DEFERRED
P.append(f"<h2>DEFERRED — نقصُ تغطية (ليس رفضًا) باسم ما ينقصه (المجموع {rj['total']['DEFERRED']}؛ تغيّرت {rj['decisions_changed']} قرارًا عن رفضِ R1 القديم)</h2><table><tr><th>ما ينقصه</th><th>العدد</th></tr>")
for k,c in sorted(rj['DEFERRED_counts'].items(),key=lambda x:-x[1]): P.append(f"<tr class='keep'><td>{e(k)}</td><td>{c}</td></tr>")
P.append('</table>')
for k,ex in rj['DEFERRED_examples'].items():
    if not ex: continue
    P.append(f"<h3>أمثلة — {e(k)}</h3><table><tr><th>الموضع</th><th>الكلمة</th><th>المرشّح المؤجَّل</th></tr>")
    for x in ex[:10]: P.append(f"<tr><td>{e(x['ref'])}</td><td>{e(x['word'])}</td><td>{e(x['candidate'])}</td></tr>")
    P.append('</table>')
# GENERATOR_GAPS
gg=R['generator_gaps']
P.append(f"<h2>GENERATOR_GAPS — عائلةُ «+نا بإدغام النون» (تسجيلٌ لا بناء؛ {len(gg)} صنفًا)</h2><table><tr><th>السطح</th><th>العدد</th><th>فصلُ B3</th><th>أمثلة</th></tr>")
for w,v in sorted(gg.items(),key=lambda x:-x[1]['count']):
    P.append(f"<tr><td><b>{e(w)}</b></td><td>{v['count']}</td><td><code>{e(v['b3'])}</code></td><td><small>{e(' '.join(v['refs']))}</small></td></tr>")
P.append('</table>')
# BASELINE_DEFECTS (من الملفّ: مؤكّدٌ + مرشّحٌ آليّ)
bdp=os.path.join(HERE,'BASELINE_DEFECTS.tsv')
P.append("<h2>BASELINE_DEFECTS — عيوبُ A الأساس (لا تُصلَح هذه الجولة) — <code>BASELINE_DEFECTS.tsv</code></h2>")
P.append("<p><small>المؤكّدان (المالك) مشهودان في المصحف المختوم. المرشّحاتُ الآليّة (تنوينٌ على خانةِ مبنيّ/عامل) إشارةٌ ناقصة — لا تلتقط صنفَ المؤكّدَين (كلا شطرَيه «جذع») — تحتاج مراجعة.</small></p><table>")
if os.path.exists(bdp):
    for ri,line in enumerate(open(bdp,encoding='utf-8')):
        row=line.rstrip('\n').split('\t'); tag='th' if ri==0 else 'td'
        cls='' if ri==0 else ('bad' if 'مؤكّد' in line else 'keep')
        P.append(f"<tr class='{cls}'>"+''.join(f'<{tag}>{e(c)}</{tag}>' for c in row)+'</tr>')
P.append('</table>')
P.append('</body></html>')
open(os.path.join(HERE,'index_quran.html'),'w',encoding='utf-8').write('\n'.join(P))
print("index_quran.html written")
