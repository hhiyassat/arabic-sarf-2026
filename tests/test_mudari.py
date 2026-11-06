"""tests/test_mudari.py — SARF_MUDARI_AGREEMENT_AND_ISNAD_01: دلالة الصيغة على طرف الإسناد، وانتقالها بهوية الوجه إلى العلاقة والشهادة."""
import copy, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tests'))
os.chdir(ROOT)
from mudari_probe import analyze_text
from sarf.relations import subject_pronoun_written
from sarf.algebra import closure_certificate
FAIL = []


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {got}'))
    if not cond:
        FAIL.append(name)


def frame(text, verb=None, ref='T'):
    o = analyze_text(text, ref)
    fr = [r for r in o['records'] if r['type'] == 'VERB_FRAME' and (verb is None or r['texts'].get('verb') == verb)]
    return o, (fr[0] if fr else None)


def subj(text, verb=None):
    _, f = frame(text, verb)
    return (f['frame'].get('subject') or {}) if f else None


# ---------- القاعدة S01.p نفسها (جدول الصيغة) ----------
T = [(dict(person=1, number='singular', gender='common'), 'مضارع', 'HIDDEN_OBLIGATORY'),
     (dict(person=1, number='plural', gender='common'), 'مضارع', 'HIDDEN_OBLIGATORY'),
     (dict(person=2, number='singular', gender='masc'), 'مضارع', 'HIDDEN_OBLIGATORY'),
     (dict(person=2, number='singular', gender='fem'), 'مضارع', 'WRITTEN'),
     (dict(person=3, number='singular', gender='masc'), 'مضارع', 'HIDDEN_OR_OVERT'),
     (dict(person=3, number='singular', gender='fem'), 'مضارع', 'HIDDEN_OR_OVERT'),
     (dict(person=2, number='dual', gender='common'), 'مضارع', 'WRITTEN'),
     (dict(person=3, number='plural', gender='fem'), 'مضارع', 'WRITTEN'),
     (dict(person=2, number='singular', gender='masc'), 'أمر', 'HIDDEN_OBLIGATORY'),
     (dict(person=2, number='singular', gender='fem'), 'أمر', 'WRITTEN'),
     (dict(person=1, number='singular', gender='common'), 'ماضٍ', 'WRITTEN'),
     (dict(person=3, number='singular', gender='fem'), 'ماضٍ', 'HIDDEN_OR_OVERT')]
bad = [(s_, t_, w_, subject_pronoun_written(s_, t_)[0]) for s_, t_, w_ in T if subject_pronoun_written(s_, t_)[0] != w_]
check('P01 جدول S01.p: أَفعل ونَفعل وتَفعل (للمخاطب) والأمر للواحد مستترٌ وجوباً؛ وياء المخاطبة وألف الاثنين وواو الجماعة ونون النسوة '
      'وضمائر الماضي مكتوبة؛ والغائب المفرد ظاهرٌ أو مستتر', not bad, bad)
check('P02 لكل حكمٍ سند (الألفية وشرح ابن عقيل للمستتر وجوباً)', all(subject_pronoun_written(s_, t_)[1] for s_, t_, _ in T) and
      'ابن عقيل' in subject_pronoun_written(T[0][0], 'مضارع')[1])

# ---------- الشواهد ----------
s = subj('نَكْتُبُ الدَّرْسَ')
check('W01 «نَكۡتُبُ الدَّرۡسَ»: فاعله مستترٌ وجوباً (نحن)، لا «ضميرٌ متصل مكتوب» (كان خطأً: لا ضمير مكتوب في الكلمة)',
      s and s['status'] == 'LICENSED' and 'وجوباً' in s['kind'] and s.get('implicit') is True and s.get('rule') == 'S01.p', s)
for w in ('تَكْتُبِينَ', 'لَنْ تَكْتُبِي'):
    s = subj(w)
    check(f'W02 «{w}»: ياء المخاطبة ضميرٌ مكتوب، لا مستتر (كان خطأً)', s and s['status'] == 'LICENSED' and s['kind'] == 'ضمير متصل مكتوب'
          and not s.get('implicit'), s)
for w in ('يَكْتُبُونَ', 'يَكْتُبْنَ', 'تَكْتُبُونَ', 'لَنْ تَكْتُبُوا', 'لَمْ يَكْتُبُوا', 'لَمْ يَكْتُبَا', 'تَكْتُبَانِ'):
    s = subj(w)
    check(f'W03 «{w}»: الضمير المتصل المكتوب فاعلٌ مرخَّص', s and s['status'] == 'LICENSED' and s['kind'] == 'ضمير متصل مكتوب', s)
s1, s2 = subj('اكْتُبْ'), subj('اكْتُبِي')
check('W04 الأمر: «اكۡتُبۡ» مستترٌ وجوباً، و«اكۡتُبِي» ياء المخاطبة مكتوبة', s1 and 'وجوباً' in s1['kind'] and s2 and s2['kind'] == 'ضمير متصل مكتوب',
      (s1, s2))
s1, s2 = subj('كَتَبْتُ'), subj('كَتَبْنَا')
check('W05 الماضي: «كَتَبۡتُ» و«كَتَبۡنَا» ضمير الرفع مكتوب', s1['kind'] == s2['kind'] == 'ضمير متصل مكتوب', (s1, s2))
s = subj('أَكُونُ حَاضِرًا')
check('W06 «أَكُونُ حَاضِرًا»: المسند إليه مستترٌ وجوباً (أنا) في وجهي الناقص والتامّ، بنيةٌ مشتركة؛ والاستعمال مؤجَّل لا مختار',
      s and s['status'] == 'LICENSED' and s['role'] == 'اسم الناسخ أو فاعل التامّ' and s.get('shared_across') == ['ناقص', 'تامّ'], s)
o, f = frame('يَكْتُبُ الرِّجَالُ')
s = f['frame']['subject']
check('W07 «يَكۡتُبُ الرِّجَالُ»: الفعل مفردٌ والفاعل جمعٌ ظاهر مرفوع — لا يُرفض بمساواة العدد (الفعل مع الظاهر يُفرد)',
      s['status'] == 'LICENSED' and s['kind'] == 'اسم ظاهر', s)
s = subj('الرِّجَالُ يَكْتُبُونَ')
check('W08 «الرِّجَالُ يَكۡتُبُونَ»: الفاعل واو الجماعة المكتوبة، لا «الرجال» (بنيةٌ أخرى: مبتدأٌ وخبرٌ جملة)',
      s['kind'] == 'ضمير متصل مكتوب' and not s.get('unit'), s)
# مراجعة 046: «عدم التحليل الخاطئ» منفصلٌ عن «إثبات التحليل الصحيح»؛ وما لم يُثبت يُطبع فجوةً (GAP) ولا يُعدّ نجاحاً
GAPS = []
for w in ('أَكْرَمَ زَيْدٌ عَمْرًا', 'تَعَلَّمَ زَيْدٌ', 'نَظَرَ زَيْدٌ'):
    o, f = frame(w)
    c_ = ((f or {}).get('frame') or {}).get('candidate') or {}
    check(f'W09 لا تحليل خاطئ: «{w.split()[0]}» لا يُعدّ مضارعاً بحرفه الأول', c_.get('tense') != 'مضارع', c_)
    if c_.get('tense') == 'ماضٍ':
        check(f'W09+ إثبات التحليل الصحيح: «{w.split()[0]}» ماضٍ بإطار فعلٍ وفاعلٍ ظاهر', f['frame']['subject'].get('kind') == 'اسم ظاهر', f['frame']['subject'])
    else:
        GAPS.append(f'W09+ «{w.split()[0]}»: لا إطار فعل (لم يثبت بالكتابة أنه فعل) — الماضي الصحيح غير مثبت')
o, f = frame('لَيَكْتُبَنَّ زَيْدٌ')
check('W11 نون التوكيد: «لَيَكۡتُبَنَّ زَيۡدٌ» مضارعٌ مبني، وفاعله ظاهرٌ مرخَّص', f and f['frame']['candidate']['tense'] == 'مضارع' and
      f['frame']['subject']['kind'] == 'اسم ظاهر' and f['frame']['subject']['status'] == 'LICENSED', f and f['frame']['subject'])
o, f = frame('يُكْتَبُ الدَّرْسُ')
check('W12 المجهول: «يُكۡتَبُ الدَّرۡسُ» نائب فاعلٍ ظاهر، لا فاعل', f and f['frame']['candidate']['voice'] == 'مجهول' and
      f['frame']['subject']['role'] == 'نائب فاعل' and f['frame']['subject']['status'] == 'LICENSED', f and f['frame']['subject'])
o, f = frame('لَنْ تَتَعَلَّمَ')
check('W13 «لَنۡ تَتَعَلَّمَ» محفوظة التاءين: لا مانع التباس، وطرف الإسناد مرخَّصٌ في كل وجه (المخاطب وجوباً، والغائبة جوازاً)',
      f and f['frame']['subject']['status'] == 'LICENSED' and all(x['status'] == 'LICENSED' for x in f['frame']['subject']['subject_faces']),
      f and f['frame']['subject'])
for w in ('تَجْرِي الْأَنْهَارُ', 'كُتِبَ الدَّرْسُ', 'أَكْتُبُ الدَّرْسَ', 'تَكْتُبُ هِنْدٌ الدَّرْسَ', 'أُكْرَمُ', 'تَكْتُبْنَ'):
    o, f = frame(w)
    if not f:
        GAPS.append(f'«{w}»: لا إطار فعل (إثبات الفعل بلا عاملٍ في السياق غير منفّذ)')
o = analyze_text('يَدٌ')
check('W10 «يَدٌ»: الياء ليست حرف مضارعة، ولا إطار فعل', not [r for r in o['records'] if r['type'] == 'VERB_FRAME'])

# ---------- آية الدين ----------
from sarf import quran_source
o = analyze_text(next(x for a, b, x in quran_source.rows() if (a, b) == (2, 282)), '2:282')
FR = {r['texts'].get('verb'): r for r in o['records'] if r['type'] == 'VERB_FRAME'}
for v_ in ('تَضِلَّ', 'تُذَكِّرَ'):
    s = FR[v_]['frame']['subject']
    fx = {x['signature']['person']: x for x in s['subject_faces']}
    check(f'D01 «{v_}»: وجه المخاطب مستترٌ وجوباً مرخَّصٌ في وجهه، ووجه الغائبة مؤجَّل بعائق الاسم («إحدى» غير محسوم)، لا بقاعدة المضارعة؛ ولا اختيار',
          s['status'] == 'DEFERRED' and s.get('selection') == 'DEFERRED' and fx[2]['status'] == 'LICENSED' and fx[3]['status'] == 'DEFERRED'
          and fx[3]['blocked_by'] == 'NOUN_CLASS_UNRESOLVED' and all(x['face_id'].startswith(FR[v_]['heads']['verb'] + '#T=') for x in fx.values()), s)
s = FR['يَكُونَا']['frame']['subject']
check('D02 «يَكُونَا»: ألف الاثنين المكتوبة مسندٌ إليه في الوجهين، والاستعمال مؤجَّل', s['status'] == 'LICENSED' and s.get('shared_across'), s)
s = FR['يُمِلَّ']['frame']['subject']
check('D03 «أَن يُمِلَّ هُوَ»: الغائب المفرد: «هو» مرشّحٌ أو مستتر — مؤجَّل (أعاقه تحليل الضمير المنفصل لا قاعدة المضارعة)', s['status'] == 'DEFERRED', s)

# ---------- المستهلك: الشهادة ----------
o = analyze_text('نَكْتُبُ الدَّرْسَ')
ob = [x for c in o['certs'] for x in c['obligations'] if x['requirement_kind'] in ('SUBJECT', 'SUBJECT_OR_PASSIVE_AGENT')]
check('C01 الشهادة تستهلك S01.p: التزام فاعل «نَكۡتُبُ» مستوفى بإطار 14أ بهوية وجهٍ آلية ومرشّحٍ صرفي، لا بالطبقة القديمة وحدها',
      ob and all(x['met'] and x['source'] == '14أ' and str(x['face_id']).startswith('FACE:') and x['morph_candidate_id'] for x in ob), ob)
D = {x['name']: x for c in o_c for x in c['obligations']} if (o_c := analyze_text(next(x for a, b, x in quran_source.rows() if (a, b) == (2, 282)),
                                                                                    '2:282')['certs']) else {}
dz = D.get('فاعل «تَضِلَّ»')
check('C02 فاعل «تَضِلَّ» في الشهادة: خريطة أوجهٍ صريحة (وجهان بهويتين)، ووجه الغائبة بلا علاقة، فلا استيفاء في كل الأوجه',
      dz and len(dz['face_map']) == 2 and dz['status'] in ('SELECTION', 'CONFLICT') and not dz['met'] and
      sum(bool(x['relations']) for x in dz['face_map']) == 1, dz)

# ---------- الإفساد ----------
# ١ المستتر بلا مجال مكتوب: لا وحدة ولا مدى نصّي له
hid = [x for r in o['records'] if r['type'] == 'VERB_FRAME' for x in [r['frame'].get('subject') or {}] if x.get('implicit')]
check('X01 المستتر وحدةٌ بنيوية غير مكتوبة: لا unit ولا مجال محارف', hid and all(not x.get('unit') for x in hid), hid[:1])
# ٢ تغيير الشخص إلى قيمةٍ غير متوافقة: نَكۡتُبُ (المتكلم) يُفسَد إلى غائبٍ مفرد — لا يبقى «مستتراً وجوباً»
check('X02 إفساد الشخص: غائبٌ مفرد بدل المتكلم في «نَكۡتُبُ» يُسقط الترخيص المبكر (لا مستتر وجوباً بلا صيغته)',
      subject_pronoun_written(dict(person=3, number='singular', gender='masc'), 'مضارع')[0] == 'HIDDEN_OR_OVERT')
# ٣ الزمن غير المثبت لا يُرخّص بالسابقة وحدها: S01.p يشترط الزمن المثبت
o142 = analyze_text(next(x for a, b, x in quran_source.rows() if (a, b) == (2, 142)), '2:142')
unp = [r['frame']['subject'] for r in o142['records'] if r['type'] == 'VERB_FRAME' and (r['frame'].get('candidate') or {}).get('tense_status') != 'مثبت'
       and (r['frame'].get('subject') or {}).get('subject_faces')]
check('X03 لا استدلال بالسابقة وحدها: حيث الزمن غير مثبت (2:142) لا يُرخَّص طرف الإسناد بالصيغة في أي وجه (TENSE_NOT_PROVEN)',
      unp and all(x['status'] == 'DEFERRED' and x.get('blocked_by') == 'TENSE_NOT_PROVEN' for s_ in unp for x in s_['subject_faces']),
      [[(x['status'], x.get('blocked_by')) for x in s_['subject_faces']] for s_ in unp])
# ٤ ربط العلاقة بوجهٍ آخر: إفساد خريطة أوجه «تَضِلَّ» بجعل الوجه المؤجَّل مرخَّصاً بلا علاقة يُسقطه الفاحص؟ — نُفسد السجل فيصير الوجهان مرخَّصين
from mudari_probe import analyze_text as _at
o2 = _at(next(x for a, b, x in quran_source.rows() if (a, b) == (2, 282)), '2:282')
recs = copy.deepcopy(o2['records'])
fz = next(r for r in recs if r['type'] == 'VERB_FRAME' and r['texts'].get('verb') == 'تَضِلَّ')
faces = fz['frame']['subject']['subject_faces']
faces[1]['status'] = 'LICENSED'
fz['frame']['subject']['status'] = 'LICENSED'
JZ = next(J for J in o2['Js'] if any(x.name == 'فاعل «تَضِلَّ»' for x in J.Omega))
obz0 = next(x for x in closure_certificate(JZ, o2['records'])['obligations'] if x['name'] == 'فاعل «تَضِلَّ»')
obz1 = next(x for x in closure_certificate(JZ, recs)['obligations'] if x['name'] == 'فاعل «تَضِلَّ»')
check('X04 إفساد سجلّ الوجه (مراجعة 046): وجه الغائبة يُدّعى مرخَّصاً وسبب تأجيله قائم (صنف «إحدى»، والنوع «غير معيَّن») — '
      'الفاحص يكشفه (FACE_EVIDENCE_INVALID) ولا يُستوفى الالتزام', not obz0['met'] and not obz1['met'] and obz1.get('evidence_invalid')
      and 'FACE_EVIDENCE_INVALID' in obz1['residual_reason'], (obz1['status'], obz1.get('evidence_invalid')))
# ضابطٌ موجب: الوجه نفسه بدليلٍ تامّ (مستترٌ جوازاً بقاعدة S01.h وسجلّ مستترٍ سليم وبلا عائق) يُقبل
from sarf.relations import implicit_subject
recs2 = copy.deepcopy(o2['records'])
fz2 = next(r for r in recs2 if r['type'] == 'VERB_FRAME' and r['texts'].get('verb') == 'تَضِلَّ')
f3 = next(x for x in fz2['frame']['subject']['subject_faces'] if x['signature']['person'] == 3)
f3.update(status='LICENSED', kind='ضمير مستتر جوازاً (غير مكتوب)', rule='S01.h', blocked_by=None,
          implicit_subject=implicit_subject(fz2['heads']['verb'], f3['face_id'], f3['signature'], 'فاعل', 'S01.h', ['TEST#evidence']))
obz2 = next(x for x in closure_certificate(JZ, recs2)['obligations'] if x['name'] == 'فاعل «تَضِلَّ»')
check('X04b ضابطٌ موجب: الوجه بدليلٍ تامّ (قاعدة S01.h، ومستترٌ سليم الهوية، ولا عائق) يُغطّى — فالفاحص يفرّق الدليل من الادّعاء',
      obz2['status'] == 'MET_IN_ALL_FACES' and not obz2.get('evidence_invalid'), (obz2['status'], obz2.get('evidence_invalid')))
# المستتر: هويةٌ كاملة، وإفساده بمجالٍ مصدري يُكشف
o_n = analyze_text('نَكْتُبُ الدَّرْسَ')
sjn = next(r for r in o_n['records'] if r['type'] == 'VERB_FRAME')['frame']['subject']
from sarf.relations import validate_implicit, IMPLICIT_KEYS
check('X01b المستتر سجلٌّ كامل الهوية: مالكه الفعل، ووجهه، وخصائصه، وقاعدته ودليله، ومرجعه غير معيَّن، ولا مجال مصدر',
      validate_implicit(sjn['implicit_subject'], next(r for r in o_n['records'] if r['type'] == 'VERB_FRAME')['heads']['verb'], sjn['face_id'])[0]
      and all(k in sjn['implicit_subject'] for k in IMPLICIT_KEYS) and sjn['implicit_subject']['reference_status'] == 'UNRESOLVED', sjn.get('implicit_subject'))
rn = copy.deepcopy(o_n['records'])
fn = next(r for r in rn if r['type'] == 'VERB_FRAME')
fn['frame']['subject']['implicit_subject']['source_span'] = [0, 3]
Jn = o_n['Js'][0]
okn0 = [x for x in closure_certificate(Jn, o_n['records'])['obligations'] if x['requirement_kind'] == 'SUBJECT']
okn1 = [x for x in closure_certificate(Jn, rn)['obligations'] if x['requirement_kind'] == 'SUBJECT']
check('X01c إفساد: مجالٌ مصدري مصطنع للمستتر في «نَكۡتُبُ» يُكشف، فيسقط الاستيفاء (وبدونه مستوفى)',
      okn0 and okn0[0]['met'] and okn1 and not okn1[0]['met'] and okn1[0].get('evidence_invalid'), (okn0[0]['status'], okn1[0]['status']))
# ٥ توليد وجهٍ غير موجود من حاصل الضرب: أوجه «تَضِلَّ» اثنان (مخاطب مذكر، غائبة) لا أربعة
check('X05 لا حاصل ضرب: أوجه «تَضِلَّ» اثنان من بدائل الصيغة نفسها، لا (مخاطب/غائب × مذكر/مؤنث)',
      len(FR['تَضِلَّ']['frame']['subject']['subject_faces']) == 2)

# ---------- مانعان من مراجعة الانتقالات ----------
def qframe(vs, w):
    a, b = map(int, vs.split(':'))
    o_ = analyze_text(next(x for s_, v_, x in quran_source.rows() if (s_, v_) == (a, b)), vs)
    return next(r for r in o_['records'] if r['type'] == 'VERB_FRAME' and r['texts'].get('verb') == w)['frame']['subject']
s = qframe('2:216', 'تُحِبُّوا')
check('B01 «تُحِبُّوا»: الواو ليست لام الجذر «حبب»، فوجه المفرد ممتنعٌ بمانعٍ مثبت، والفاعل واو الجماعة المكتوبة (وجهٌ واحد)',
      s['status'] == 'LICENSED' and s['kind'] == 'ضمير متصل مكتوب' and len(s['subject_faces']) == 1 and s.get('rejected_faces'), s)
s = qframe('2:70', 'تَشَٰبَهَ')
check('B02 «تَشَٰبَهَ» (2:70): تَفَاعَلَ أوله تاء يلتبس مضارعه المحذوف التاء بماضيه كتابةً: لا يُرخَّص الإسناد بالصيغة (TENSE_V_VI_AMBIGUOUS)',
      s['status'] == 'DEFERRED' and all(x.get('blocked_by') == 'TENSE_V_VI_AMBIGUOUS' for x in s['subject_faces']), s)
s = qframe('4:149', 'تَعْفُوا')
check('B03 مقابلة B01: «تَعۡفُوا» جذره «عفو» ناقصٌ واوي، فوجه المفرد باقٍ ولا يُمنع', any(x['signature']['number'] == 'singular' for x in s['subject_faces']), s)

# ---------- مراجعة 046: الحرّاس العامة ----------
from sarf.relations import tense_safe_for_isnad
class _V:
    def __init__(s_, text, P, k='K'):
        s_.text = text; s_.k = k
        class G: pass
        s_.G = G(); s_.G.Theta = dict(P=P)
check('G01 مانع الالتباس مضيَّق: «لَنۡ تَتَعَلَّمَ» محفوظة التاءين آمنة، و«تَعَلَّمَ» مضارعاً بلا عاملٍ وبتاءٍ واحدة ملتبسة، '
      'و«تَعَلَّمَ» بعاملٍ مقبول آمنة', tense_safe_for_isnad(_V('تَتَعَلَّمَ', 'V'), dict(v='مضارع'))[0] and
      not tense_safe_for_isnad(_V('تَعَلَّمَ', 'V'), dict(v='مضارع'))[0] and tense_safe_for_isnad(_V('تَعَلَّمَ', 'V'), dict(v='مضارع'), governed={'K'})[0])
from sarf.algebra import _frame_faces, _face_cover, _rel_face_id
ff = _frame_faces(dict(heads=dict(verb='U'), frame=dict(candidate=dict(id='U#c', tense_live=['ماضٍ', 'أمر']), voice=(None, 'مؤجَّل', ['معلوم', 'مجهول']))))
check('G02 _frame_faces بلا حاصل ضربٍ ممتنع: لا «أمر مبني للمجهول»', ('أمر', 'مجهول') not in [(f['tense'], f['voice']) for f in ff] and len(ff) == 3, ff)
ff2 = _frame_faces(dict(heads=dict(verb='U'), frame=dict(candidate=dict(id='U#c'), candidates=[dict(id='c1', status='DEFERRED', tense='ماضٍ', voice='مجهول'),
                                                                                             dict(id='c2', status='REJECTED', tense='أمر', voice='معلوم')])))
check('G03 _frame_faces من المرشّحات الكاملة الحيّة وحدها، بهوية مرشّحها (دُعُوا: الماضي المجهول؛ والأمر الممنوع لا وجه له)',
      [(f['tense'], f['voice'], f['morph_candidate_id']) for f in ff2] == [('ماضٍ', 'مجهول', 'U#c1')], ff2)
fm = _face_cover([dict(face_id='F1', label='', voice='معلوم', unit='U', morph_candidate_id='U#c')],
                 [dict(relation='R_other', role='فاعل', verb='OTHER'), dict(relation='R_face', role='فاعل', verb='U', faces=['F2']),
                  dict(relation='R_def', role='فاعل', verb='U', status='DEFERRED'), dict(relation='R_ok', role='فاعل', verb='U', status='LICENSED')])
check('G04 _face_cover لا يقبل علاقةً لفعلٍ آخر، ولا لوجهٍ آخر، ولا مؤجَّلة، ولو وافق وصف الدور والبناء', fm[0]['relations'] == ['R_ok'], fm)
check('G05 _rel_face_id لا يعيد الوجه الأول افتراضاً حين لا وجه استوفى شروطه',
      _rel_face_id(dict(relation_id='R', faces=[dict(status='HYPOTHESIS_UNCHECKED')])) is None and
      _rel_face_id(dict(relation_id='R', faces=[dict(status='X'), dict(status='CONDITIONS_MET')])) == 'FACE:R#face1')
# «يكونا» في الشهادة: التفكيك
ok_ = next(x for c in o_c for x in c['obligations'] if x['name'] == 'فاعل «يَكُونَا»') if (o_c := analyze_text(
    next(x for a, b, x in quran_source.rows() if (a, b) == (2, 282)), '2:282')['certs']) else None
um = {x['face_id'].split('USE=')[1]: x for x in ok_['face_map']}
check('K01 «يَكُونَا» في الشهادة مفكَّك: طرف الإسناد المشترك مثبتٌ بدليله، ووظيفته اسم الناسخ في الناقص والفاعل في التامّ، '
      'ومتطلّب الناقص الخبر (مرشّح «رجلين»)، والاختيار مؤجَّل — ولا استيفاء ولا إغلاق',
      ok_['shared_subject']['status'] == 'PROVEN' and ok_['usage_selection'] == 'DEFERRED' and um['ناقص']['relations'] and um['تامّ']['relations']
      and um['ناقص']['function'] == 'اسم الناسخ' and um['تامّ']['function'] == 'فاعل' and um['ناقص']['requirements'][0]['status'] == 'CANDIDATE'
      and ok_['status'] == 'SELECTION' and not ok_['met'], ok_)

for g_ in GAPS:
    print('GAP ' + g_)
print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
