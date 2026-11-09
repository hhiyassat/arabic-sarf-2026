"""tests/test_reconcile.py — وحدة الحقيقة بين المراحل (SARF_COMPLETION_FROM_REPORT_063 §٢): السمات النهائية من أوجه إطار الفعل الحيّة."""
import copy, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from sarf.reconcile import reconcile_features, check_consistency
FAIL = []


def check(name, ok, got=''):
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f' — {str(got)[:300]}'))
    if not ok:
        FAIL.append(name)


S3 = {'person': 3, 'number': 'plural', 'gender': 'masc'}
S2 = {'person': 2, 'number': 'plural', 'gender': 'masc'}
FEAT = {(5, 0): dict(pos=dict(v='فعل', st='مثبت'), tense=dict(v='أمر', st='مرشّح', alt=['ماضٍ', 'أمر', 'مضارع']),
                     voice=dict(v='معلوم', st='مرشّح', alt=['معلوم', 'مجهول']), subject=dict(v=S2, st='مرشّح', alt=[S3]))}
REC = [dict(type='VERB_FRAME', relation_id='1:1:VERB_FRAME:F01:verb=Q1:1.w5.u0', status='DEFERRED', heads=dict(verb='Q1:1.w5.u0'),
            frame=dict(candidates=[dict(id='F01.c1', tense='ماضٍ', voice='مجهول', subject=S3, subject_role='نائب فاعل', status='DEFERRED'),
                                   dict(id='F01.c2', tense='أمر', voice='معلوم', subject=S2, subject_role='فاعل', status='REJECTED', reason='مانعٌ مثبت')]))]
out, log = reconcile_features(FEAT, REC)
f = out[(5, 0)]
check('C01 القيم النهائية من الوجه الحيّ الواحد نفسه (ماضٍ، مجهول، الغائب)', (f['tense']['v'], f['voice']['v'], f['subject']['v']) == ('ماضٍ', 'مجهول', S3), f)
check('C02 قيم الوجه الممنوع مستبعدةٌ بوجهها وسببها ومعرّف العلاقة، لا محذوفة', any(e['value'] == 'أمر' and e['face'] == 'F01.c2' and e['reason'] == 'مانعٌ مثبت'
                                                                              and e['relation_id'] == REC[0]['relation_id'] for e in f['tense']['excluded']))
check('C03 ما لا يحمله وجهٌ حيّ (مضارع) مستبعدٌ بسببه', any(e['value'] == 'مضارع' and e['face'] is None for e in f['tense']['excluded']))
check('C04 مخرج المرحلة ١٣ محفوظٌ موسوماً بأن الدليل اللاحق تجاوزه', f['tense']['stage13']['v'] == 'أمر' and 'تجاوزه' in f['tense']['stage13']['note'])
check('C05 الأصل لا يتغيّر (نسخة)، والفاحص سليم على الناتج', FEAT[(5, 0)]['tense']['v'] == 'أمر' and not check_consistency(out, REC))
errs = check_consistency(FEAT, REC)
check('C06 إفساد: السمات قبل المصالحة (الأمر حيّ) ← LIVE_VALUE_FROM_EXCLUDED_FACE', any(e[0] == 'LIVE_VALUE_FROM_EXCLUDED_FACE' for e in errs), errs)
mixed = copy.deepcopy(out)
mixed[(5, 0)]['voice']['v'] = 'معلوم'
check('C07 إفساد: بناءٌ من وجهٍ وزمنٌ من آخر ← يُكشف', check_consistency(mixed, REC), check_consistency(mixed, REC))
two = copy.deepcopy(REC)
two[0]['frame']['candidates'][1]['status'] = 'DEFERRED'
o2, _ = reconcile_features(FEAT, two)
check('C08 وجهان حيّان: لا يُختار أحدهما — القيمة None والبدائل محفوظة', o2[(5, 0)]['tense']['v'] is None and set(o2[(5, 0)]['tense']['alt']) == {'ماضٍ', 'أمر'})
none = [dict(REC[0], frame=dict(candidates=[]))]
o3, l3 = reconcile_features(FEAT, none)
check('C09 إطارٌ بلا أوجه: لا تغيير', o3 == FEAT and not l3)
# من المسار العام: «دُعُوا» (2:282)
from sarf.stages import run_ref
C = run_ref('2:282')
FF = C.get('features_final')['2:282'][(76, 0)]
check('C10 «دُعُوا» من run(): ماضٍ مجهول نائب فاعلٍ للغائبين، والأمر مستبعدٌ بمانعه في F01', FF['tense']['v'] == 'ماضٍ' and FF['voice']['v'] == 'مجهول' and
      FF['subject']['v'] == S3 and any(e['value'] == 'أمر' and e['face'] == 'F01.c2' for e in FF['tense']['excluded']), FF['tense'])
check('C11 لا تناقض بين السمات النهائية وأوجه الإطار في 2:282', not C.get('reconciliation')['errors']['2:282'], C.get('reconciliation')['errors'])
check('C12 مخرج المرحلة ١٣ نفسه باقٍ كما هو (للأثر المرحلي)', C.get('features')['2:282'][(76, 0)]['tense']['v'] == 'أمر')
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
