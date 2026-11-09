"""tests/test_reconcile.py — وحدة الحقيقة بين المراحل (SARF_COMPLETION_FROM_REPORT_063 §٢، ومراجعة SARF_FINAL_COMPLETION_AND_ACCEPTANCE_01 §٢):
السمات النهائية من الأوجه الحيّة مجتمعةً، والفاحص المستقل يشترط أن تتحقّق القيم المسندة معاً في وجهٍ حيّ."""
import copy, itertools, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from sarf.reconcile import reconcile_features, check_consistency, UnknownFaceStatus
FAIL = []


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:300]}'))
    if not ok:
        FAIL.append(name)


S3 = {'person': 3, 'number': 'plural', 'gender': 'masc'}
S2 = {'person': 2, 'number': 'plural', 'gender': 'masc'}
S3m = {'person': 3, 'number': 'singular', 'gender': 'masc'}
U = 'Q1:1.w5.u0'


def feat(tense, voice, subj, alt_t=None, alt_v=None, alt_s=None):
    return {(5, 0): dict(pos=dict(v='فعل', st='مثبت'), tense=dict(v=tense, st='مرشّح', alt=alt_t),
                         voice=dict(v=voice, st='مرشّح', alt=alt_v), subject=dict(v=subj, st='مرشّح', alt=alt_s))}


def frame(cands, n='F01', unit=U):
    return dict(type='VERB_FRAME', relation_id=f'1:1:VERB_FRAME:{n}:verb={unit}', status='DEFERRED', heads=dict(verb=unit),
                frame=dict(candidates=cands))


def face(i, t, v, s, st='DEFERRED', reason=None):
    return dict(id=i, tense=t, voice=v, subject=s, subject_role='نائب فاعل' if v == 'مجهول' else 'فاعل', status=st, reason=reason)


val = lambda o, f: o[(5, 0)][f]['v']

# ١ وجهٌ حيّ واحد (دُعُوا): قيمه كلها، والممنوع مستبعدٌ بوجهه وسببه
FEAT = feat('أمر', 'معلوم', S2, ['ماضٍ', 'أمر', 'مضارع'], ['معلوم', 'مجهول'], [S3])
REC = [frame([face('F01.c1', 'ماضٍ', 'مجهول', S3), face('F01.c2', 'أمر', 'معلوم', S2, 'REJECTED', 'مانعٌ مثبت')])]
out, log = reconcile_features(FEAT, REC)
check('C01 وجهٌ حيّ واحد: قيمه كلها (ماضٍ، مجهول، الغائب)', (val(out, 'tense'), val(out, 'voice'), val(out, 'subject')) == ('ماضٍ', 'مجهول', S3), out)
check('C02 قيمة الوجه الممنوع مستبعدةٌ بوجهها وسببها وإطارها', any(e['value'] == 'أمر' and e['faces'] == ['F01.c2'] and e['reason'] == 'مانعٌ مثبت'
                                                               for e in out[(5, 0)]['tense']['excluded']))
check('C03 ما لا يحمله وجهٌ حيّ (مضارع) مستبعدٌ بسببه', any(e['value'] == 'مضارع' and e['faces'] is None for e in out[(5, 0)]['tense']['excluded']))
check('C04 مخرج المرحلة ١٣ محفوظٌ موسوماً، والأصل لا يتغيّر', out[(5, 0)]['tense']['stage13']['v'] == 'أمر' and FEAT[(5, 0)]['tense']['v'] == 'أمر'
      and 'تجاوزه' in out[(5, 0)]['tense']['stage13']['note'])
check('C05 الفاحص سليمٌ على الناتج', not check_consistency(out, REC), check_consistency(out, REC))
check('C06 إفساد: السمات قبل المصالحة ← LIVE_VALUE_FROM_EXCLUDED_FACE', any(e[0] == 'LIVE_VALUE_FROM_EXCLUDED_FACE' for e in check_consistency(FEAT, REC)))

# ٢ حالة المراجعة: وجهان حيّان (ماضٍ مجهول، مضارع معلوم)، والسمات القديمة «ماضٍ معلوم» بلا بدائل
FX = feat('ماضٍ', 'معلوم', S3m)
RX = [frame([face('A', 'ماضٍ', 'مجهول', S3m), face('B', 'مضارع', 'معلوم', S3m)])]
check('C07 حالة المراجعة على السمات القديمة: «ماضٍ معلوم» لا يحمله وجهٌ مجتمعاً ← MIXED_FACES (والفاحص لا يكتفي بانتماء كل سمةٍ منفردة)',
      any(e[0] == 'MIXED_FACES' for e in check_consistency(FX, RX)), check_consistency(FX, RX))
ox, _ = reconcile_features(FX, RX)
check('C08 المصالحة لا تُبقي التركيب المختلط: الزمن والبناء بلا قيمة، والبدائل محفوظة، والمشترك (الضمير) يُعرض بدليل اشتراكه',
      val(ox, 'tense') is None and val(ox, 'voice') is None and set(ox[(5, 0)]['tense']['alt']) == {'ماضٍ', 'مضارع'}
      and set(ox[(5, 0)]['voice']['alt']) == {'مجهول', 'معلوم'} and val(ox, 'subject') == S3m and 'مشتركة' in ox[(5, 0)]['subject']['ev'], ox)
check('C09 والفاحص سليمٌ بعد المصالحة', not check_consistency(ox, RX), check_consistency(ox, RX))
for i, f in enumerate(('tense', 'voice')):
    bad = copy.deepcopy(ox)
    bad[(5, 0)][f]['v'] = ['ماضٍ', 'معلوم'][i]
    check(f'C10.{f} إفساد: انتقاء قيمة وجهٍ من وجهين مختلفين ({f}) ← SELECTED_WITHOUT_EVIDENCE', any(e[0] == 'SELECTED_WITHOUT_EVIDENCE' for e in check_consistency(bad, RX)))
mixed = copy.deepcopy(ox)
mixed[(5, 0)]['tense']['v'], mixed[(5, 0)]['voice']['v'] = 'ماضٍ', 'معلوم'
check('C11 إفساد: زمنٌ من وجهٍ وبناءٌ من آخر ← MIXED_FACES مع وجهين حيّين', any(e[0] == 'MIXED_FACES' for e in check_consistency(mixed, RX)))

# ٣ وجهان متوافقان جزئياً، وقيمةٌ مشتركة كاملة
RP = [frame([face('A', 'ماضٍ', 'مجهول', S3), face('B', 'ماضٍ', 'معلوم', S3)])]
op, _ = reconcile_features(FX, RP)
check('C12 وجهان يتّفقان في الزمن والضمير ويختلفان في البناء: المشترك يُعرض، والمختلف بلا قيمة', val(op, 'tense') == 'ماضٍ'
      and val(op, 'subject') == S3 and val(op, 'voice') is None and not check_consistency(op, RP), op)

# ٤ كل الأوجه ممنوعة
RA = [frame([face('A', 'ماضٍ', 'مجهول', S3, 'REJECTED', 'م١'), face('B', 'أمر', 'معلوم', S2, 'REJECTED', 'م٢')])]
oa, _ = reconcile_features(FX, RA)
check('C13 كل الأوجه ممنوعة: لا قيمة في الحقول الثلاثة، والحالة ALL_FACES_REJECTED', all(val(oa, f) is None for f in ('tense', 'voice', 'subject'))
      and oa[(5, 0)]['_faces']['state'] == 'ALL_FACES_REJECTED' and not check_consistency(oa, RA), oa[(5, 0)])
check('C14 إفساد: قيمةٌ مع كل الأوجه ممنوعة ← VALUE_WITH_ALL_FACES_REJECTED', any(e[0] == 'VALUE_WITH_ALL_FACES_REJECTED' for e in check_consistency(FX, RA)))

# ٥ حقلٌ ناقص في وجهٍ حيّ
RM = [frame([face('A', 'ماضٍ', 'مجهول', S3), dict(id='B', tense='ماضٍ', voice=None, subject=S3, status='DEFERRED')])]
om, _ = reconcile_features(FX, RM)
check('C15 حقلٌ ناقص في وجهٍ حيّ: لا يُعرض المشترك الظاهري (البناء بلا قيمة، وسببه النقص)', val(om, 'voice') is None and 'ناقص' in om[(5, 0)]['voice']['ev']
      and val(om, 'tense') == 'ماضٍ', om[(5, 0)]['voice'])

# ٦ إطارٌ بلا أوجه، وحالةٌ غير معروفة
o0, l0 = reconcile_features(FX, [frame([])])
check('C16 إطارٌ بلا أوجه: لا تغيير', o0 == FX and not l0)
try:
    reconcile_features(FX, [frame([face('A', 'ماضٍ', 'مجهول', S3, 'MAYBE')])])
    check('C17 حالة وجهٍ غير معروفة ← خطأٌ صريح', False)
except UnknownFaceStatus:
    check('C17 حالة وجهٍ غير معروفة ← خطأٌ صريح', True)
check('C18 والفاحص يسمّيها UNKNOWN_FACE_STATUS', any(e[0] == 'UNKNOWN_FACE_STATUS' for e in check_consistency(FX, [frame([face('A', 'ماضٍ', 'مجهول', S3, 'MAYBE')])])))

# ٧ إطاران للوحدة نفسها، والاستقلال عن الترتيب
R2f = [frame([face('A', 'ماضٍ', 'مجهول', S3), face('B', 'مضارع', 'معلوم', S3)], 'F01'),
       frame([face('B2', 'مضارع', 'معلوم', S3, 'REJECTED', 'مانع الإطار الثاني')], 'F09')]
o2, _ = reconcile_features(FX, R2f)
check('C19 إطاران: الوجه الممنوع في أيّهما ممنوع، فيبقى وجهٌ حيّ واحد (ماضٍ مجهول) — لا يفوز الأخير', (val(o2, 'tense'), val(o2, 'voice')) == ('ماضٍ', 'مجهول')
      and not check_consistency(o2, R2f), o2[(5, 0)])
base_out = None
ok_order = True
for perm in itertools.permutations(R2f):
    for rec in ([dict(r, frame=dict(candidates=list(reversed(r['frame']['candidates'])))) for r in perm], list(perm)):
        o_, _ = reconcile_features(FX, rec)
        sig = {f: o_[(5, 0)][f]['v'] for f in ('tense', 'voice', 'subject')}
        alts = {f: o_[(5, 0)][f].get('alt') for f in ('tense', 'voice', 'subject')}
        if base_out is None:
            base_out = (sig, alts)
        ok_order &= (sig, alts) == base_out
check('C20 الحكم مستقلٌّ عن ترتيب الأطر وترتيب الأوجه (كل التباديل)', ok_order, base_out)

# ٨ من المسار العام: «دُعُوا» (2:282) على الإصدار المستهدف
from sarf.stages import run_ref
C = run_ref('2:282')
FF = C.get('features_final')['2:282'][(76, 0)]
check('C21 «دُعُوا» من run(): ماضٍ مجهول، والأمر مستبعدٌ بوجهه F01.c2', FF['tense']['v'] == 'ماضٍ' and FF['voice']['v'] == 'مجهول'
      and any(e['value'] == 'أمر' and 'F01.c2' in (e['faces'] or []) for e in FF['tense']['excluded']), FF['tense'])
check('C22 لا تناقض بين السمات النهائية وأوجه الإطار في 2:282', not C.get('reconciliation')['errors']['2:282'], C.get('reconciliation')['errors'])
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
