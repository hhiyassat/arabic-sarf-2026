"""tests/test_fa02.py — تكليف الإصلاح FA02 (مراجعة المالك لـ 373f95e و5df2dbb): الصنف وهوية الوجه بين الطبقات."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from sarf.stages import run_ref
from sarf.features import elative_evidence
FAIL = []


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:400]}'))
    if not ok:
        FAIL.append(name)


def unit_of(C, ref, text):
    V = C.get('records')[ref]
    us = [u for u, l, t in V['tokens'] if t == text]
    F = C.get('features')[ref]
    keys = [k for k in F if any(u.endswith(f'.w{k[0]}.u{k[1]}') for u in us)]
    return V, us, [F[k] for k in keys]


# §G1 «أَكْثَرُ» (18:34 «أَنَا أَكْثَرُ مِنكَ مَالًا»): صنفٌ واحد في السمات والعلاقات، بدليل الكتابة (E01)
C = run_ref('18:34')
V, us, fs = unit_of(C, '18:34', 'أَكْثَرُ')
check('G1.1 السمات: «أَكْثَرُ» اسمٌ مثبت بدليل E01 (عين الماضي في HFN كَثُرَ/كَثَرَ والعين المكتوبة مفتوحة)، لا فعلٌ من حرف المضارعة',
      fs and all(f['pos']['v'] == 'اسم' and f['pos']['st'] == 'مثبت' and 'E01' in f['pos']['ev'] for f in fs), [f.get('pos') for f in fs])
check('G1.2 لا علاقة MOOD (V-RAF1) على «أَكْثَرُ»، والإسناد الاسمي «أنا أكثر» مرخَّص',
      not any(r['type'] == 'MOOD' and r['texts'].get('verb') == 'أَكْثَرُ' for r in V['records'])
      and any(r['type'] == 'PREDICATION' and r['status'] == 'LICENSED' and r['texts'].get('predicate') == 'أَكْثَرُ' for r in V['records']))
check('G1.3 محور الصنف في العلاقات بالدليل نفسه الذي في السمات (دالةٌ واحدة)',
      all(V['axes'][u]['word_class'][0] == 'اسم' and V['axes'][u]['word_class'][1] == elative_evidence('أَكْثَرُ') for u in us),
      [V['axes'][u].get('word_class') for u in us])
# مقابل: «لَا أَبْرَحُ» (18:60) — عين بَرِحَ حرف حلق وماضيه فَعِلَ، فلا ينفي E01 مضارع المتكلم: الصنف مؤجَّل بالوجهين، ولا V-RAF1
C2 = run_ref('18:60')
V2, us2, fs2 = unit_of(C2, '18:60', 'أَبْرَحُ')
check('G1.4 مقابل «أَبْرَحُ» (18:60): E01 لا يثبت، فالصنف مؤجَّل بين الفعل والاسم، لا مثبتٌ من حرف المضارعة وحده',
      elative_evidence('أَبْرَحُ') is None and fs2 and all(f['pos']['v'] is None and set(f['pos'].get('alt') or []) == {'فعل', 'اسم'} for f in fs2),
      [f.get('pos') for f in fs2])
check('G1.5 ولا يُبنى على وجه الفعل المؤجَّل مضارعٌ مرفوع لتجرّده', not any(r['type'] == 'MOOD' and r['texts'].get('verb') == 'أَبْرَحُ'
                                                                          for r in V2['records']))
C6 = run_ref('46:15')
V6, us6, fs6 = unit_of(C6, '46:15', 'أَعْمَلَ')
check('G1.6 مقابل «وَأَنْ أَعْمَلَ» (46:15): المفتوح الآخر خارج القاعدة، فيبقى فعلاً كما كان (لا إتلاف للصحيح)',
      fs6 and all(f['pos']['v'] == 'فعل' for f in fs6), [f.get('pos') for f in fs6])
# §G2 هوية الوجه الكاملة (حالة المالك: قول/E1 حيّ، وقيل/E2 ممنوع، بالسمات الثلاث نفسها)
from sarf.reconcile import reconcile_features, check_consistency
S = {'person': 3, 'number': 'singular', 'gender': 'masc'}
FX = {(5, 0): dict(tense=dict(v='ماضٍ', st='مرشّح'), voice=dict(v='معلوم', st='مرشّح'), subject=dict(v=S, st='مرشّح'))}
A = dict(id='A', root='قول', event='E1', tense='ماضٍ', voice='معلوم', subject=S, status='DEFERRED')
B = dict(id='B', root='قيل', event='E2', tense='ماضٍ', voice='معلوم', subject=S, status='REJECTED', reason='مانع B')
R = [dict(type='VERB_FRAME', relation_id='1:1:VERB_FRAME:F01:verb=Q1:1.w5.u0', heads=dict(verb='Q1:1.w5.u0'), frame=dict(candidates=[A, B]))]
o, _ = reconcile_features(FX, R)
fc = o[(5, 0)]['_faces']
check('G2.1 وجهان مختلفا الجذر والحدث لا يُدمجان: A حيّ وB ممنوع، والحالة LIVE_FACES، والسمات المشتركة قائمة',
      fc['state'] == 'LIVE_FACES' and len(fc['live']) == 1 and len(fc['rejected']) == 1 and fc['live'][0]['identity']['root'] == 'قول'
      and fc['rejected'][0]['identity']['root'] == 'قيل' and o[(5, 0)]['tense']['v'] == 'ماضٍ', fc)
check('G2.2 الفاحص المستقل لا يرى قيمةً مع «كل الأوجه ممنوعة»', not check_consistency(o, R), check_consistency(o, R))
R1 = [dict(R[0], frame=dict(candidates=[A]))]
check('G2.3 المانع يخصّ وجهه: الحكم بالوجهين كالحكم بالحيّ وحده', {k: o[(5, 0)][k]['v'] for k in ('tense', 'voice', 'subject')}
      == {k: reconcile_features(FX, R1)[0][(5, 0)][k]['v'] for k in ('tense', 'voice', 'subject')})
B2 = dict(A, id='A2', status='REJECTED', reason='مانع A2')
R2 = [dict(R[0], frame=dict(candidates=[A, B2]))]
o2, _ = reconcile_features(FX, R2)
check('G2.4 والوجه نفسه (الهوية كاملةً) ممنوعاً في موضعٍ آخر ممنوعٌ كلّه: ALL_FACES_REJECTED', o2[(5, 0)]['_faces']['state'] == 'ALL_FACES_REJECTED'
      and not check_consistency(o2, R2), o2[(5, 0)]['_faces'])
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
