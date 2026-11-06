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
for w, t_ in (('أَكْرَمَ زَيْدٌ عَمْرًا', None), ('تَعَلَّمَ زَيْدٌ', 'ماضٍ'), ('نَظَرَ زَيْدٌ', None)):
    o, f = frame(w)
    c_ = ((f or {}).get('frame') or {}).get('candidate') or {}
    check(f'W09 مانع التعميم: «{w.split()[0]}» ليس مضارعاً بحرفه الأول (الزمن {c_.get("tense")})',
          c_.get('tense') != 'مضارع' and (t_ is None or c_.get('tense') == t_), c_)
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
src = open(os.path.join(ROOT, 'sarf', 'relations.py'), encoding='utf-8').read()
check('X03 لا استدلال بالسابقة وحدها: S01.p مشروطٌ بزمنٍ مثبت (tf.st == مثبت) في الفرع الرئيس وأوجه الصيغة',
      "sf.get('st') == 'مثبت' and tf.get('st') == 'مثبت'" in src and "if tf.get('st') == 'مثبت' else (None, None)" in src)
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
check('X04 إفساد سجلّ الوجه: ادّعاء وجه الغائبة مرخَّصاً يغيّر الشهادة (MET_IN_ALL_FACES)، وبدونه لا استيفاء — فالحكم تابعٌ لسجلّ الوجه '
      'بهويته، لا لعبارةٍ عامة', not obz0['met'] and obz1['status'] == 'MET_IN_ALL_FACES', (obz0['status'], obz1['status']))
# ٥ توليد وجهٍ غير موجود من حاصل الضرب: أوجه «تَضِلَّ» اثنان (مخاطب مذكر، غائبة) لا أربعة
check('X05 لا حاصل ضرب: أوجه «تَضِلَّ» اثنان من بدائل الصيغة نفسها، لا (مخاطب/غائب × مذكر/مؤنث)',
      len(FR['تَضِلَّ']['frame']['subject']['subject_faces']) == 2)

print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
