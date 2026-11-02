# -*- coding: utf-8 -*-
"""يبني index.html من results.json وحدَه. نسقُ Mashru: RTL، ألوان."""
import os,json,html
HERE=os.path.dirname(os.path.abspath(__file__))
R=json.load(open(os.path.join(HERE,'results.json'),encoding='utf-8'))
e=html.escape
def tsv(name):
    p=os.path.join(HERE,name)
    if not os.path.exists(p): return None
    return [l.rstrip('\n').split('\t') for l in open(p,encoding='utf-8') if l.strip()]
CSS="""body{font-family:'Segoe UI',Tahoma,sans-serif;direction:rtl;background:#faf9f7;color:#222;margin:0 auto;max-width:1240px;padding:20px}
h1{color:#5b3a1a}h2{color:#7a4a1a;border-bottom:2px solid #d8c9b5;padding-bottom:4px;margin-top:30px}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13px}th,td{border:1px solid #ccc;padding:5px 7px;text-align:right}
th{background:#ede4d3}code{background:#f0ece3;padding:1px 4px;border-radius:3px;font-size:12px}
.ok{background:#d9f2d9}.bad{background:#f7d7d7}.keep{background:#ffe9cf}.unit{background:#eee;color:#666}
tr.changed td{box-shadow:inset 0 0 0 2px #d4af37}.flag{display:inline-block;background:#eef;padding:4px 10px;margin:3px;border-radius:4px;font-size:14px}
small{color:#777}"""
col={'مطابق':'ok','مخالف':'bad','وحدة بالفهرس':'unit','خارج الفهرس':''}
ab={'ثابت':'','فُصل بنصّ':'ok','أُسقط بمانع':'keep','أُسقط بلا مانع':'bad'}
P=['<!doctype html><html lang="ar"><meta charset="utf-8"><title>UNIVERSAL_SEG_02</title><style>%s</style><body>'%CSS]
P.append('<h1>تجربةُ التقطيع الشاملة المضبوطة — UNIVERSAL_SEGMENTATION_CONTROLLED_EXPERIMENT_02</h1>')
i=R['identity']
P.append('<h2>هويّةُ الجولة</h2><table>')
for k,v in [('HEAD',i['head']),('sha segment.py',i['segment_sha']),('sha المصدر',i['source_sha']),
            ('سطر 2:282',i['source_line']),('sha المورد zip',i['zip_sha']),('sha المورد JSON',i['resource_json_sha']),
            ('EXPECTED sha',i['expected_sha']),('أمر التشغيل',i['run_cmd'])]:
    P.append(f'<tr><th>{e(k)}</th><td><code>{e(str(v))}</code></td></tr>')
P.append('</table>')
P.append('<h2>الملخّص (الأعداد لكلّ حالة)</h2><table><tr><th>الحالة</th><th>كامل</th><th>قُسمت</th><th>جذع</th></tr>')
for s in R['summary']:
    v=s['v']; P.append(f"<tr><td>{e(s['state'])}</td><td>{v['كامل']}</td><td>{v['قُسمت']}</td><td>{v['جذع']}</td></tr>")
P.append('</table>')
ab3=R['flags']['A_TO_B3']
def g(k): return ab3.get(k,0)
P.append('<h2>A → B3</h2><table><tr><th>ثابت</th><th>فُصل بنصّ</th><th>فُصل تقديرًا</th><th>أُسقط بمانع</th><th>أُسقط بلا دليل/مانع</th></tr>'
         f"<tr><td class='unit'>{g('ثابت')}</td><td class='ok'>{g('فُصل بنصّ')}</td><td class='keep'>{g('فُصل تقديرًا')}</td><td class='keep'>{g('أُسقط بمانع')}</td><td class='bad'>{g('أُسقط بلا مانع')+g('فُصل بلا دليل')}</td></tr></table>")
P.append('<h2>كلمةً كلمة (129)</h2><table><tr><th>#</th><th>الكلمة</th><th>A</th><th>B</th><th>B2</th><th>B3</th><th>A→B3</th><th>قاعدة</th><th>البدائل</th><th>المرجع</th></tr>')
for r in R['rows']:
    tr='<tr class="changed">' if r['changed'] else '<tr>'
    alts='، '.join(r['alts']) or '—'
    reftxt=e(r['ref'])+(f" <small>{e(r['ref_id'])}</small>" if r['ref_id'] else '')
    P.append(f"{tr}<td>{r['n']}</td><td><b>{e(r['word'])}</b></td><td>{e(r['A'])}</td><td>{e(r['B'])}</td><td>{e(r['B2'])}</td>"
             f"<td class='{col.get(r['ref'],'')}'>{e(r['B3'])}</td><td class='{ab.get(r['a_b3'],'')}'>{e(r['a_b3'])}</td>"
             f"<td>{e(r['rule'])} <small>{e(r['qarina'])}</small></td><td class='keep'>{e(alts)}</td><td class='{col.get(r['ref'],'')}'>{reftxt}</td></tr>")
P.append('</table>')
P.append('<h2>اختبارات 3-د (على EXPECTED بلا تعديل)</h2><table><tr><th>الاختبار</th><th>المتوقَّع</th><th>النتيجة</th></tr>')
exp=R['expected']['tests']
import difflib
def findexp(k):
    for ek,ev in exp.items():
        if ek.split('_')[0]==k.split('_')[0]: return ev.get('expect','—')
    return '—'
for k in sorted(R['tests']):
    ok=R['tests'][k]
    P.append(f"<tr class='{'ok' if ok else 'bad'}'><td>{e(k)}</td><td>{e(findexp(k))}</td><td>{'PASS' if ok else 'FAIL'}</td></tr>")
P.append('</table>')
P.append('<h2>سجلُّ الموانع</h2><table><tr><th>الكلمة</th><th>مرشّح مرفوض</th><th>الموانع</th></tr>')
nrej=0
for r in R['rows']:
    for rj in r['rejected']:
        nrej+=1; bar='، '.join(f"{bn}: {st}" for bn,st in rj['barriers'])
        P.append(f"<tr><td>{e(r['word'])}</td><td class='bad'>{e(rj['parts'])}</td><td>{e(bar)}</td></tr>")
if not nrej: P.append('<tr><td colspan=3><small>لا مرشّحَ مرفوضًا في الآية</small></td></tr>')
P.append('</table>')
for nm,title in [('BASELINE_DEFECTS.tsv','عيوبُ A الأساس (لا تُصلَح هذه الجولة)'),('KHILAF.tsv','الخلافُ المعتبر')]:
    t=tsv(nm)
    if t:
        P.append(f'<h2>{e(title)} — <code>{e(nm)}</code></h2><table>')
        for ri,row in enumerate(t):
            tag='th' if ri==0 else 'td'
            P.append('<tr>'+''.join(f'<{tag}>{e(c)}</{tag}>' for c in row)+'</tr>')
        P.append('</table>')
f=R['flags']
P.append('<h2>أعلامُ الختام</h2><div>')
for k in ['BASELINE_A_BYTE_IDENTICAL','TESTS','MATCHES','PATTERN_MATCHES','MISMATCHES','DEFERRED_AS_UNIT','LOST_WITHOUT_BARRIER','NEW_SPLIT_WITHOUT_EVIDENCE']:
    P.append(f'<span class="flag">{e(k)} = {e(str(f[k]))}</span>')
P.append('</div>')
P.append('<h2>لم يُنفَّذ</h2><ul>'+''.join(f'<li>{e(x)}</li>' for x in R['not_run'])+'</ul>')
P.append('</body></html>')
open(os.path.join(HERE,'index.html'),'w',encoding='utf-8').write('\n'.join(P))
print("index.html rows:",len(R['rows']),"| flags:",f['TESTS'],"MATCHES",f['MATCHES'],"LOST",f['LOST_WITHOUT_BARRIER'])
