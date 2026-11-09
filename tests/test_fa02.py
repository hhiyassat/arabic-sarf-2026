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
# §G3 السمات النهائية يستهلكها مسار العلاقات (المرحلة relations_final)، والشهادات تقرأ ناتجها؛ بلا دورة، وبمراجعةٍ مضبوطة
import copy
from sarf.stages import ENGINE, p_relations_final
C3 = run_ref('2:282')
check('G3.1 الشهادات والفقرات تقرأ «records» من relations_final، وهي تقرأ features_final؛ والمصالحة تقرأ records_initial (لا دورة)',
      ENGINE.producer_of['records'] == 'relations_final' and 'features_final' in ENGINE.stages['relations_final'].requires
      and 'records_initial' in ENGINE.stages['face_reconciliation'].requires and 'records' in ENGINE.stages['certificates'].requires)
check('G3.2 المراجعة المضبوطة: حالة الثبات معلنةٌ لكل آية، والفاحص المستقل سليمٌ على الناتج النهائي في 2:282',
      C3.get('revision')['convergence']['2:282']['state'] == 'CONVERGED' and not C3.get('revision')['errors_final']['2:282'],
      C3.get('revision'))
d = {k: C3.get(k) for k in ENGINE.stages['relations_final'].requires}
d['features_final'] = copy.deepcopy(d['features_final'])
V3 = C3.get('records')['2:282']
u76 = next(u for u, l, t in V3['tokens'] if t == 'يَسْتَطِيعُ')
k76 = tuple(int(x) for x in u76.rsplit('.w', 1)[1].split('.u'))
d['features_final']['2:282'][k76]['pos'] = dict(v=None, st='مؤجَّل', ev='إفساد اختباري', alt=['فعل', 'اسم'])
Vm = p_relations_final(None, d)['records']['2:282']
check('G3.3 إفساد: تغيير صنف «يَسْتَطِيعُ» في features_final وحدها يغيّر العلاقات النهائية (تسقط V-RAF1 عنه) — فهي مستهلَكة فعلاً',
      any(r['type'] == 'MOOD' and r['texts'].get('verb') == 'يَسْتَطِيعُ' for r in V3['records'])
      and not any(r['type'] == 'MOOD' and r['texts'].get('verb') == 'يَسْتَطِيعُ' for r in Vm['records']))
# §G4 إثبات العلامة غير إثبات الموضع: MOOD لا يدخل by_member، والموضع من وقوعات النصّ
from sarf.algebra import positional, closure_certificate, sentence_units
from sarf.stages import _sentences
recs3 = [r for v in C3.get('records').values() for r in v['records']]
mood3 = [r for r in recs3 if r['type'] == 'MOOD' and r['status'] == 'LICENSED']
check('G4.1 علاقة MOOD المرخَّصة ليست موضعية، وإطار الفعل بدورٍ واحد ليس موضعياً، والفاعل بطرفيه موضعي',
      mood3 and not any(positional(r) for r in mood3) and not positional(dict(type='VERB_FRAME', members=dict(verb=['x'])))
      and positional(dict(type='SUBJECT', members=dict(verb=['x'], subject=['y']))))
# فعلٌ مرفوعٌ لتجرّده تُحذف كل علاقةٍ موضعية مرخَّصة تضعه (إفساد) ويبقى سجلّ MOOD وحده: فلا يضعه MOOD
u_st = mood3[0]['members']['verb'][0]
recs3m = [r for r in recs3 if r['type'] == 'MOOD' or not (r['status'] == 'LICENSED' and positional(r)
                                                         and any(u_st in us for us in r['members'].values()))]
J_st = next(J for J in _sentences(C3.get('sentences')['LT']) if u_st in sentence_units(J))
cst = closure_certificate(J_st, recs3m)
plc = next(o for o in cst['obligations'] if o['name'] == 'موضع كل وقوع (14أ)')
check(f'G4.2 فعلٌ مرفوعٌ لتجرّده ({u_st}) لا يبقى له إلا V-RAF1 ← غير مستوفى الموضع (لا يُحسب MOOD استيفاءً)',
      u_st in plc['occurrences'] and any(u_st in v for v in plc['unplaced_by_class'].values())
      and not any(x['unit'] == u_st for x in plc['satisfied_by']), plc)
recs_nomood = [r for r in recs3m if r['type'] != 'MOOD']
cst2 = closure_certificate(J_st, recs_nomood)
plc2 = next(o for o in cst2['obligations'] if o['name'] == 'موضع كل وقوع (14أ)')
check('G4.3 حذف سجلات MOOD كلها لا يغيّر التزام الموضع ولا أدلّته (الاستيفاء بالهوية، لا بالحالة وحدها)',
      (plc2['status'], plc2['unplaced_by_class'], plc2['discharge_evidence_id'], plc2['satisfied_by'])
      == (plc['status'], plc['unplaced_by_class'], plc['discharge_evidence_id'], plc['satisfied_by']))
# §G5 بصمة المحرّك بالمحتوى لا بالمعرّف
from sarf.engine import fingerprint


class _O:
    def __init__(self, id_, O):
        self.id, self.O = id_, O


check('G5.1 كائنان بالمعرّف نفسه ومحتوى مختلف ← بصمتان مختلفتان (كانت «OBJ:معرّف» فتتساويان)',
      fingerprint(_O('J1', {'a': 1})) != fingerprint(_O('J1', {'a': 2})) and fingerprint(_O('J1', {'a': 1})) == fingerprint(_O('J1', {'a': 1})))
cyc = _O('J2', {})
cyc.O['self'] = cyc
check('G5.2 الدورة تُسمّى ولا تُسقط المحتوى: بصمة كائنٍ يحيل إلى نفسه محسوبة، وتتغيّر بتغيّر حقلٍ فيه', (lambda a: (cyc.O.__setitem__('x', 1),
      a != fingerprint(cyc))[1])(fingerprint(cyc)))
C18 = run_ref('18:34')
C18b = run_ref('18:34')
check('G5.3 البصمة حتمية: تشغيلان للمدخل نفسه ← بصماتٌ متساوية لكل الخانات', {n: x.fp for n, x in C18.slots.items()} == {n: x.fp for n, x in C18b.slots.items()})
units2 = copy.copy(C18.get('units'))
k18 = '18:34'
U2 = dict(units2[k18]['units'])
gk = next(iter(U2))
G2 = copy.copy(U2[gk])
G2.O = dict(G2.O, _mutation='إفساد اختباري')
U2[gk] = G2
units2[k18] = dict(units2[k18], units=U2)
ENGINE.revise(C18, 'units', units2, 'اختبار البصمة: محتوى وحدةٍ تغيّر ومعرّفها ثابت')
rv = C18.revisions[-1]
check('G5.4 المراجعة: تغيّر محتوى وحدةٍ بمعرّفها نفسه يغيّر بصمة الخانة، فيُعاد حساب التابعين', rv['previous'] != rv['new'] and 'features' in rv['recomputed'],
      rv)
# §G8 العطف في 14أ (COORD) من سجلّ موضع العطف، وحدّ الفقرة PB-L1 بلا حدّ المصدر
co = [r for r in V3['records'] if r['type'] == 'COORD']
lic = [r for r in co if r['status'] == 'LICENSED']
check('G8.1 «سَفِيهًا أَوْ ضَعِيفًا» (2:282): COORD مرخَّصة بطرفين معيَّنين وحرفها، ومقدّماتها شروط القبول من sarf.coord',
      any(r['texts'].get('conj') == 'أَوْ' and r['texts'].get('coordinated_on') == 'سَفِيهًا' and r['texts'].get('coordinated') == 'ضَعِيفًا'
          and any(p_.startswith('A1') for p_ in r['premises']) for r in lic), [(r['status'], r['texts']) for r in co[:10]])
check('G8.2 الموضع المتعدّد المستوفي (D2) مؤجَّل بمرشّحيه كلهم، ولا طرفٌ سابق معيَّن فيه',
      any(r['status'] == 'DEFERRED' and 'D2' in (r.get('decision_codes') or []) and len(r['alternatives']) >= 2 and 'coordinated_on' not in r['members']
          for r in co))
check('G8.3 كل COORD مرخَّصة: قرارها تثبيتٌ أو ترخيص، ووظيفتها عطف، وأعضاؤها الثلاثة معيَّنون (لا ترخيص بالقرب ولا بالتطابق)',
      lic and all(r['decision'] in ('تثبيت ضمن النطاق المعلن', 'ترخيص الأول وتأجيل الحسم النهائي') and str(r['coord_function']).startswith('عطف')
                  and all(r['members'].get(k_) for k_ in ('conj', 'coordinated_on', 'coordinated')) for r in lic))
from sarf.relations import verse_relations
cr_mut = copy.deepcopy(C3.get('legacy')['coord'])
for x in cr_mut:
    x['decision'] = 'حفظ المستوفيات وتأجيل الانفراد'
Vx = verse_relations(C3.get('analysis')['2:282'], C3.get('units')['2:282']['units'], C3.get('features_final')['2:282'], '2:282',
                     legacy_cond=C3.get('legacy')['cond'], legacy_rel=C3.get('legacy')['rel'], F13=C3.get('features')['2:282'], legacy_coord=cr_mut)
check('G8.4 إفساد: قرار الموضع «تأجيل الانفراد» في كل المواضع ← لا COORD مرخَّصة (الترخيص من القرار لا من وجود مرشّح)',
      not any(r['type'] == 'COORD' and r['status'] == 'LICENSED' for r in Vx['records']))
u_aw = next(u for r in lic if r['texts'].get('conj') == 'أَوْ' for u in r['members']['conj'])
J_aw = next(J for J in _sentences(C3.get('sentences')['LT']) if u_aw in sentence_units(J))
pl_aw = next(o for o in closure_certificate(J_aw, recs3)['obligations'] if o['name'] == 'موضع كل وقوع (14أ)')
check('G8.5 حرف العطف المرخَّص «أَوْ» وطرفاه موضوعون في التزام الموضع بعلاقة COORD', any(x['unit'] == u_aw and ':COORD:' in x['relation']
                                                                                    for x in pl_aw['satisfied_by']), pl_aw['unplaced_by_class'])
C112 = run_ref('112:3')
V112 = C112.get('records')['112:3']
gv = [r for r in V112['records'] if r['type'] == 'GOVERN']
check('G8.6 «لَمْ يَلِدْ» (112:3): GOVERN مرخَّصة بين «لَمْ» و«يَلِدْ» (عاملٌ مقبول، والجزم في قدرته، والسكون المكتوب يوافقه)',
      any(r['status'] == 'LICENSED' and r['texts'] == {'operator': 'لَمْ', 'governed': 'يَلِدْ'} for r in gv), [(r['status'], r['texts']) for r in gv])
c112 = {k: x for k, x in C112.get('certificates').items()}
pl112 = [o for x in c112.values() for o in x['obligations'] if o['name'] == 'موضع كل وقوع (14أ)']
check('G8.7 «لَمْ يَلِدْ» كل وقوعاتها موضوعة: «لَمْ» بـGOVERN، و«يَلِدْ» نواةٌ بفاعلٍ مستترٍ مرخَّص في إطاره (لا بـMOOD)',
      pl112 and pl112[0]['status'] == 'MET' and {x['relation'].split(':')[2] for x in pl112[0]['satisfied_by']} <= {'GOVERN', 'VERB_FRAME', 'COORD'},
      [(o['status'], o['unplaced_by_class']) for o in pl112])
from sarf.algebra import inter_clause
check('G8.8 عطف الجمل رابطٌ بين جمل (لا يمدّ الإسناد المحلي)، وعطف المفرد علاقةٌ محلية',
      inter_clause(dict(type='COORD', coord_levels=['جملة'])) and not inter_clause(dict(type='COORD', coord_levels=['مفرد']))
      and not inter_clause(dict(type='COORD', coord_levels=['جملة', 'مفرد'])))
# §G8 (قياس G8 على المصحف): الفاعل الضمير المتصل المكتوب نواةٌ كالمستتر، والعلاقة المرخَّصة العابرة لحدّ الجملة تضع طرفها الداخلي
check('G8.9 إطار فعلٍ فاعله ضميرٌ متصل مكتوب مرخَّص موضعيٌّ كالمستتر؛ وغير المرخَّص، وما لفاعله وحدةٌ مستقلة، لا',
      positional(dict(type='VERB_FRAME', members=dict(verb=['x']), frame=dict(subject=dict(kind='ضمير متصل مكتوب', status='LICENSED', unit=None))))
      and not positional(dict(type='VERB_FRAME', members=dict(verb=['x']), frame=dict(subject=dict(kind='ضمير متصل مكتوب', status='DEFERRED', unit=None))))
      and not positional(dict(type='VERB_FRAME', members=dict(verb=['x']), frame=dict(subject=dict(kind='ضمير متصل مكتوب', status='LICENSED', unit='y')))))
C2277 = run_ref('22:77')
r2277 = [r for v in C2277.get('records').values() for r in v['records']]
J_sj = next(J for J in _sentences(C2277.get('sentences')['LT']) if 'Q22:77.w4.u1' in sentence_units(J))
pl_sj = next(o for o in closure_certificate(J_sj, r2277)['obligations'] if o['name'] == 'موضع كل وقوع (14أ)')
check('G8.10 «وَاسْجُدُوا» (22:77): الفعل موضوعٌ بإطاره (واو الجماعة)، والواو موضوعةٌ بعطفٍ مرخَّص طرفه الأول «ارْكَعُوا» خارج المدى (placed_outward)',
      pl_sj['status'] == 'MET' and any(x['unit'] == 'Q22:77.w4.u1' and ':VERB_FRAME:' in x['relation'] for x in pl_sj['satisfied_by'])
      and any(x['unit'] == 'Q22:77.w4.u0' and ':COORD:' in x['relation'] for x in pl_sj['placed_outward']), pl_sj)
r2277x = [dict(r, status='DEFERRED') if r['type'] == 'COORD' else r for r in r2277]
pl_sjx = next(o for o in closure_certificate(J_sj, r2277x)['obligations'] if o['name'] == 'موضع كل وقوع (14أ)')
check('G8.11 إفساد: العطف العابر نفسه مؤجَّلاً ← الواو غير موضوعة (SELECTION)، فالعابر لا يضع إلا مرخَّصاً',
      pl_sjx['status'] != 'MET' and 'Q22:77.w4.u0' in (pl_sjx['unplaced_by_class'].get('SELECTION') or []) and not pl_sjx['placed_outward'], pl_sjx)
# §V-RAF1 (تقييم 3826 سجلاً مقابل QAC): خطآن مثبتان بالكتابة — نون النسوة، والضمير الملتصق بإدغامٍ عبر الحدّ
def _mood(ref):
    V_ = run_ref(ref, None, ['relations_final']).get('records')[ref]
    return {r['texts']['verb'] for r in V_['records'] if r['type'] == 'MOOD' and r['status'] == 'LICENSED'}
m478, m1676, m3359 = _mood('4:78'), _mood('16:76'), _mood('33:59')
check('G10.1 «يُدْرِكْكُّمُ» (4:78) و«يُوَجِّهْهُّ» (16:76): الحرف الساكن يليه مثله مشدَّداً إدغامٌ عبر الحدّ، فالضمة للضمير ولا V-RAF1',
      'يُدْرِكْكُّمُ' not in m478 and 'يُوَجِّهْهُّ' not in m1676, (m478, m1676))
check('G10.2 «يُؤْذَيْنَ» (33:59): المسند إلى نون النسوة مبنيّ، لا «ثبوت النون» ولا V-RAF1', 'يُؤْذَيْنَ' not in m3359, m3359)
m244, m2113 = _mood('2:44'), _mood('2:113')
check('G10.3 مقابل: «تَنْسَوْنَ» (2:44، واو الجماعة) و«يَحْكُمُ» (2:113، ميمٌ أصلية بلا إدغامٍ عبر الحدّ) باقيان مرفوعين لتجرّدهما',
      'تَنْسَوْنَ' in m244 and 'يَحْكُمُ' in m2113, (m244, m2113))
# §G11 (قياس G10 على المصحف): تسعة أفعالٍ مسندةٍ إلى نون النسوة كانت «منصوبة وعلامة نصبها الفتحة» — والفتحة حركة الضمير
from sarf.affix import stem_info
def _inf(ref, txt):
    V_ = run_ref(ref, None, ['relations_final']).get('records')[ref]
    u = next(u for u, loc, t in V_['tokens'] if t == txt)
    return V_['axes'][u].get('inflection') or {}
i2222, i3372 = _inf('2:222', 'يَطْهُرْنَ'), _inf('33:72', 'يَحْمِلْنَ')
check('G11.1 «يَطْهُرْنَ» (2:222) و«يَحْمِلْنَ» (33:72): مضارعٌ مبنيٌّ على السكون في محلّ نصب، والإعراب محلّي لا «الفتحة الظاهرة»',
      all(i['build'][0] == 'مبني' and i['mark_kind'] == 'محلّي' and i['state'][0] == 'في محلّ نصب' and i['agreement'] == 'AGREE'
          and 'نون النسوة' in i['statement'] and 'الفتحة' not in i['statement'] for i in (i2222, i3372)), (i2222.get('statement'), i3372.get('statement')))
check('G11.2 المرحلة ١١: أثر «أَنْ» في «يَحْمِلْنَ» محلّي (observed=محلاً)، لا «نصب» مقروءاً من الفتحة',
      i3372['governor'].get('observed') == 'محلاً' and i3372['governor'].get('level') == 'محلّي', i3372['governor'])
check('G11.3 stem_info: نون النسوة بعد ساكن مبنيّ؛ ومقابلٌ: «يَكُونَ» و«يَسْكُنَ» (النون لام الفعل) منصوبان بالفتحة',
      stem_info('يَطْهُرْنَ')['mood'] == 'مبني' and stem_info('يَكُونَ')['mood'] != 'مبني' and stem_info('يَسْكُنَ')['mood'] == 'نصب',
      (stem_info('يَطْهُرْنَ'), stem_info('يَكُونَ'), stem_info('يَسْكُنَ')))
_si = {w: stem_info(w) for w in ('يَرَوْنَ', 'يُنَادَوْنَ', 'تَرَكْنَ', 'يَئِسْنَ', 'يَضَعْنَ', 'يَرْضَيْنَ', 'تَرْضَيْنَ')}
check('G11.4 قياس G11: واو الجماعة الساكنة قبل النون نون رفع لا نون نسوة (يَرَوْنَ، يُنَادَوْنَ)؛ وذو الأحرف الأربعة لا تثبت فعليته بالشكل '
      '(تَرَكْنَ، يَئِسْنَ ماضيان)، ونونه نون النسوة؛ و«تَـ…ـيْنَ» لا يُحكم فيها (ياء المخاطبة)',
      all(_si[w]['suffix'] == 'نون الرفع' and _si[w]['mood'] == 'رفع' for w in ('يَرَوْنَ', 'يُنَادَوْنَ'))
      and all(_si[w]['pos'] is None and _si[w]['suffix'] == 'نون النسوة' for w in ('تَرَكْنَ', 'يَئِسْنَ', 'يَضَعْنَ'))
      and _si['يَرْضَيْنَ']['mood'] == 'مبني' and _si['تَرْضَيْنَ']['suffix'] != 'نون النسوة',
      {w: (x['pos'], x['suffix'], x['mood']) for w, x in _si.items()})
# §G12 (مقارنة الشهادات FA01→G10): عطفٌ مرخَّص خاطئ ظهر بعد ربط السجلات (G3) — «وَمَا ضَعُفُوا» معطوفاً مفرداً على «لِمَا أَصَابَهُمْ»
C3146 = run_ref('3:146', None, ['relations_final'])
co3146 = {r['heads'].get('conj'): r for r in C3146.get('records')['3:146']['records'] if r['type'] == 'COORD'}
check('G12.1 «وَمَا ضَعُفُوا» و«وَمَا اسْتَكَانُوا» (3:146): «ما» قبل الفعل تحتمل النفي، فعطف الموصول مؤجَّل لا مرخَّص',
      all(co3146[u]['status'] == 'DEFERRED' for u in ('Q3:146.w14.u0', 'Q3:146.w16.u0')),
      {u: co3146[u]['status'] for u in ('Q3:146.w14.u0', 'Q3:146.w16.u0') if u in co3146})
from sarf.coord import _ma_neg_rival, MA_NEG_DEFER
class _X:
    def __init__(s, words, verbs):
        s.feats = [dict(text=w, verb=v) for w, v in zip(words, verbs)]; s.nset = set()
    def next_stop(s, p): return len(s.feats)
check('G12.2 الحكم: «وَمَا» يليها فعلٌ وقبلها نظيرٌ منفيّ غير المعطوف عليه ← منافس؛ ومقابلات: لا نظير (2:4)، والنظير هو المعطوف عليه (64:4)، و«وَمَنْ»',
      _ma_neg_rival(_X(['فَمَا', 'وَهَنُوا', 'لِمَا', 'أَصَابَهُمْ', 'وَمَا', 'ضَعُفُوا'], [0, 1, 0, 1, 0, 1]), 4, 6, 2)
      and not _ma_neg_rival(_X(['بِمَا', 'أُنْزِلَ', 'وَمَا', 'أُنْزِلَ'], [0, 1, 0, 1]), 2, 4, 0)
      and not _ma_neg_rival(_X(['مَا', 'تُسِرُّونَ', 'وَمَا', 'تُعْلِنُونَ'], [0, 1, 0, 1]), 2, 4, 0)
      and not _ma_neg_rival(_X(['فَمَا', 'وَهَنُوا', 'لِمَنْ', 'يَشَاءُ', 'وَمَنْ', 'يَعْمَلْ'], [0, 1, 0, 1, 0, 1]), 4, 6, 2) and MA_NEG_DEFER[0] == 'D9')
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
