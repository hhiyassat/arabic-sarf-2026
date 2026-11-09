#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_round006.py — جولة SARF_RESULT_006_RECONCILIATION_AND_RELATIONS_01 وملحقها.

اختبارات استقلال المحاور (الصنف، البناء، الدور، الحالة أو المحلّ، حالة الدليل، الحماية) بهوية التحليل نفسها،
واختبارات إفساد (العلامة، والدور، والعامل، وهوية المعمول، وحدّ المكوّن، ورتبة الدليل) يجب أن يكشفها الفاحص
ولو بدت العبارة سليمة. والمدخل نصٌّ مشكول من مصحف المجمّع (data/quran_hafs.tsv) أو شاهدٌ مكتوب؛ ولا تُمرَّر القيم المتوقعة.
"""
import copy, os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
os.environ.setdefault('SARF_QURAN', 'hafs_kfgqpc')
from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.algebra import Trace, sentence_geo, linguistic_layer
from sarf.features import unit_features
from sarf.relations import verse_relations, check_inflection, check_records, check_cross, _written_mark
from sarf.evidence import jazm_faces

CAT = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
FAIL = []


def verse_text(s, v):
    for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 3 and p[0] == str(s) and p[1] == str(v):
            return p[2]


def run(text, ref='t', cond=False, s=0, v=0):
    a = analyze(CAT, text, 'auto')
    S, U = sentence_geo(a, 'Q' + ref, Trace())
    F = unit_features(a, U)
    C = Rl = None
    if cond:
        C, Rl = [], []
        linguistic_layer([(s, v, a, U, S)], Trace(), 'test', cond_out=C, rel_out=Rl)
    return a, verse_relations(a, U, F, ref, legacy_cond=C, legacy_rel=Rl)


def at(o, loc, text):
    hits = [u for u, l, t in o['tokens'] if l == loc and t == text]
    assert hits, f'لا وحدة «{text}» في {loc}: {[(l, t) for _, l, t in o["tokens"] if l == loc]}'
    return hits[0], o['axes'][hits[0]]


def rec(o, typ, **heads):
    out = [r for r in o['records'] if r['type'] == typ and all(r['heads'].get(k) == v for k, v in heads.items())]
    return out[0] if out else None


def check(name, cond, got=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {got}'))
    if not cond:
        FAIL.append(name)


def clean(o):
    return check_records(o['records'], o['tokens']) + check_cross(o['records'], o['axes']) + check_inflection(o['axes'], o['tokens'])


T282 = verse_text(2, 282)
a, o = run(T282, '2:282', cond=True, s=2, v=282)
check('B00 2:282 بلا خللٍ في الفواحص الثلاثة (البنيوي، والعابر للطبقات، والإعراب)', not clean(o), clean(o))

# ١ «الذين» 2:282:2: الصنف والبناء والحماية ثابتة، والدور من V02 مستقلٌّ عنها
u2, ax2 = at(o, '2:282:2', 'الَّذِينَ')
check('X01 «الذين»: اسم (ملف المبنيات: relative)، مبني، محمي — ثلاثة محاور مستقلة',
      ax2['word_class'][0] == 'اسم' and ax2['build'][0] == 'مبني' and ax2['protection_detail']['reason'] == 'CONSTITUTIONAL_PROTECTED_CLASS'
      and ax2['protection_detail']['source'] == 'lexicon/mabniyat_lexicon.jsonl', (ax2['word_class'], ax2['build'], ax2['protection_detail']))
fol = rec(o, 'VOC_FOLLOWER', follower=u2)
check('X02 «الذين» تابعٌ لـ«أيّ» بقاعدة V02 مرخَّصة، ونوع التابع مؤجَّلٌ ببدائله الثلاثة',
      fol and fol['status'] == 'LICENSED' and fol['kind_status'] == 'DEFERRED' and len(fol['alternatives']) == 3, fol)
check('X03 الدور والمحلّ محوران مستقلّان: الدور «تابعٌ لـ«أيّ»» [LICENSED]، والمحلّ «في محلّ رفع» محلّي، والبناء «مبني» لم يتغيّر',
      ax2['role'][0].startswith('تابعٌ لـ«أيّ»') and ax2['role_status'] == 'LICENSED' and ax2['case_axis'] == ('في محلّ رفع', 'محلّي')
      and ax2['inflection']['agreement'] == 'AGREE', (ax2['role'], ax2['case_axis']))
_, o0 = run('ٱلَّذِينَ ءَامَنُوٓاْ', 't0')
_, ax0 = at(o0, 't0:1', 'الَّذِينَ')
check('X04 بلا تركيب النداء: الدور غائب، والفجوة معلنة («دوره ومحلّه … لم يُرخَّصا»)، والصنف والبناء والحماية باقية بلا محلٍّ مخترع',
      ax0['role'][0] is None and ax0['mabni_state']['code'] == 'ROLE_RULE_NOT_IMPLEMENTED' and 'لم يُرخَّصا' in ax0['mabni_state']['text']
      and ax0['word_class'][0] == 'اسم' and ax0['build'][0] == 'مبني' and ax0['protection_detail']['cls'] and ax0['case_axis'][0] is None
      and ax0['inflection']['agreement'] == 'UNGOVERNED', (ax0['role'], ax0['mabni_state'], ax0['case_axis']))
u1, ax1 = at(o, '2:282:1', 'أَيُّهَا')
check('X05 «أيّ» منادى مبني على الضم في محلّ نصب (V02)، و«ها» حرف تنبيه',
      ax1['role'][0] == 'منادى' and ax1['case_axis'] == ('في محلّ نصب', 'محلّي'), (ax1['role'], ax1['case_axis']))

# ٢ امرأتان: مصدر العلامة واحد في كل الطبقات
u61, ax61 = at(o, '2:282:61', 'امْرَأَتَانِ')
prem61 = [p for r in o['records'] if any(u61 in us for us in r['members'].values()) for p in r['premises'] if 'الرفع مكتوب' in str(p)]
check('X06 «امرأتان»: العلامة «الألف» في المحور، وفي مقدّمات كل علاقةٍ تسمّيها، لا «الضمة»',
      ax61['inflection']['mark'][0] == 'الألف' and prem61 and all('(الألف)' in p for p in prem61), (ax61['inflection']['mark'], prem61))
m = copy.deepcopy(o)
for r in m['records']:
    r['premises'] = [p.replace('الرفع مكتوب (الألف)', 'الرفع مكتوب (الضمة)') for p in r['premises']]
check('M01 إفساد العلامة في المقدّمة («الضمة» بدل «الألف») يكشفه الفاحص العابر للطبقات والعبارة سليمة', bool(check_cross(m['records'], m['axes'])))
m = copy.deepcopy(o)
r_ = next(r for r in m['records'] if any(u61 in us for us in r['members'].values()) and any('الرفع مكتوب' in p for p in r['premises']))
uid_other = at(o, '2:282:60', 'رَجُلٌ')[0]
r_['members'] = {k: [uid_other if u == u61 else u for u in us] for k, us in r_['members'].items()}
check('M02 إفساد هوية الوحدة في السجل (رَجُلٌ بدل امرأتان) يكشفه الفاحص (الموضع أو العلامة)',
      bool(check_records(m['records'], m['tokens']) + check_cross(m['records'], m['axes'])))

# ٣ ضمائر الإضافة والمفعول: الدليل السابق موصولٌ بقاعدة، والمحلّ مستقلٌّ عن حركة البناء
for loc, host, pr, typ, case, vowel in (('2:282:55', 'رِّجَالِ', 'كُمْ', 'IDAFA', 'جر', 'السكون'), ('2:282:81', 'تَكْتُبُو', 'هُ', 'OBJECT', 'نصب', 'الضم'),
                                        ('2:282:86', 'أَجَلِ', 'هِ', 'IDAFA', 'جر', 'الكسر')):
    up, axp = at(o, loc, pr)
    r = next((r for r in o['records'] if r['type'] == typ and up in sum(r['members'].values(), [])), None)
    st = axp['inflection']['statement'] or ''
    check(f'X07 «{pr}» في {loc}: علاقة {typ} مرخَّصة بقاعدتها، ومقدّمتها سمة المرحلة ١٣ موصولة، والمحلّ «{case}» مستقلٌّ عن البناء على {vowel}',
          r and r['status'] == 'LICENSED' and any('enclitic_case' in p for p in r['premises']) and axp['case_axis'][0] == f'في محلّ {case}'
          and f'مبني على {vowel}' in st, (r and r['status'], axp['case_axis'], st))
for loc, verb, pr in (('2:282:10', 'اكْتُبُو', 'هُ'), ('2:282:21', 'عَلَّمَ', 'هُ'), ('2:282:101', 'تُدِيرُونَ', 'هَا'), ('2:282:107', 'تَكْتُبُو', 'هَا'),
                      ('2:282:123', 'يُعَلِّمُ', 'كُمُ')):
    up, _ = at(o, loc, pr)
    uv, _ = at(o, loc, verb)
    r = rec(o, 'OBJECT', verb=uv, object=up)
    check(f'X08 «{verb}{pr}» ({loc}): مفعولٌ متصل مرخَّص (O01) بمضيفه وحدوده', r and r['status'] == 'LICENSED', r)

# ٤ قدرة العامل باستعماله: «إن» 2:282:116
ut, axt = at(o, '2:282:117', 'تَفْعَلُوا')
g = axt['inflection']['governor']
check('X09 «إنْ» في «تفعلوا»: القدرة «جزم» من الاستعمال الشرطي وحده، والحجازية (رفع ونصب) بديلٌ معجمي لا يدخل القدرة',
      g['capacity'] == ['جزم'] and 'الشرطية الجازمة' in g['capacity_source'] and
      any(x['capacity'] == ['رفع', 'نصب'] for x in g['lexical_alternatives']), (g['capacity'], g['capacity_source'], g['lexical_alternatives']))
m = copy.deepcopy(o)
m['axes'][ut]['inflection']['governor']['expected'] = 'نصب'
m['axes'][ut]['inflection']['statement'] = 'فعل مضارع منصوب بـ«إِنْ» وعلامة نصبه حذف النون'
check('M03 إفساد مقتضى العامل إلى أثر بديله المعجمي (نصب) يكشفه الفاحص: اتحاد المعاني لا يثبت الاتفاق',
      bool(check_inflection(m['axes'], m['tokens'])))
m = copy.deepcopy(o)
m['axes'][ut]['inflection']['governor']['operator'] = 'لَمْ'
check('M04 إفساد العامل (اسمه في السجل) يكشفه الفاحص والعبارة على حالها', bool(check_inflection(m['axes'], m['tokens'])))
m = copy.deepcopy(o)
m['axes'][ut]['inflection']['governor']['target_uid'] = u61
check('M05 إفساد هوية المعمول في سجل العامل يكشفه الفاحص', bool(check_inflection(m['axes'], m['tokens'])))

# ٥ المبني بلا محلّ: أربع حالاتٍ متمايزة
codes = {}
for loc, tx in (('2:282:6', 'بِ'), ('2:282:4', 'إِذَا'), ('2:282:96', 'إِلَّا'), ('2:282:25', 'الَّذِي'), ('2:282:48', 'هُوَ')):
    codes[tx] = (at(o, loc, tx)[1].get('mabni_state') or {}).get('code')
check('X10 المبني بلا دور: «بِ» لا محلّ له مثبت، و«إذا» قاعدة الدور غير منفّذة، و«إلّا» مدخلٌ معجمي ناقص، و«الذي» (25) محلٌّ غير محسوم، '
      'و«هو» محلٌّ غير محسوم (مرشّح فاعلٍ مؤجَّل لـ«يُمِلَّ»)',
      codes == {'بِ': 'NO_MAHALL', 'إِذَا': 'ROLE_RULE_NOT_IMPLEMENTED', 'إِلَّا': 'LEXICAL_ENTRY_MISSING', 'الَّذِي': 'MAHALL_UNRESOLVED',
                'هُوَ': 'MAHALL_UNRESOLVED'}, codes)

# ٦ لِلشَّهَٰدَةِ: الوحدة المكتوبة محفوظة، وأجزاؤها بهوياتها
u92, ax92 = at(o, '2:282:92', 'لِلشَّهَٰدَةِ')
p01 = rec(o, 'PP', preposition=u92)
parts = {p['part']: p for p in (p01 or {}).get('parts') or []}
check('X11 «للشهادة»: الجار «لِ» (خانة 0، المقطع 0) والمجرور «شَّهَٰدَةِ» (خانة 2) جزءان بمعرّفين، واللام الشمسية بلا مقطع، والعبارة شبه جملة',
      p01 and p01['merged_unit'] and parts['حرف جر']['text'] == 'لِ' and parts['حرف جر']['slot'] == 0 and parts['حرف جر']['syllables'] == [0]
      and parts['اسم مجرور']['slot'] == 2 and parts['أداة تعريف']['syllables'] == [] and parts['أداة تعريف']['note']
      and p01['part_heads']['preposition'] != p01['part_heads']['complement'] and p01['texts']['preposition'] == 'لِ'
      and p01['phrase']['unit'] == u92 and ax92['word_class'][0] == 'اسم', parts)

# ٧ بكل شيء: الإضافة سجلٌّ مستقل، وامتداد العبارة مقدّمةٌ بسجلّها، والرتبة تتبع المقدّمة
uk, _ = at(o, '2:282:126', 'كُلِّ')
us_, axs = at(o, '2:282:127', 'شَيْءٍ')
i03 = rec(o, 'IDAFA', mudaf=uk)
pp = next(r for r in o['records'] if r['type'] == 'PP' and r['heads'].get('complement') == uk)
a02 = next((r for r in o['records'] if r['rule_id'] == 'A02'), None)
check('X12 «كُلِّ ← شَيْءٍ» إضافةٌ مرخَّصة بـI03 مستقلة، والجار ومجروره «بِكُلِّ» لبٌّ، والامتداد بمقدّمة I03، وA02 يقوم على P01 المرخَّص',
      i03 and i03['status'] == 'LICENSED' and pp['core'] == [pp['heads']['preposition'], uk] and i03['relation_id'] in pp['premises']
      and a02 and a02['status'] == 'LICENSED' and pp['relation_id'] in a02['premises'] and axs['role'][0] == 'مضاف إليه', (i03, pp.get('core')))
m = copy.deepcopy(o)
next(r for r in m['records'] if r['relation_id'] == i03['relation_id'])['status'] = 'DEFERRED'
check('M06 إفساد رتبة الدليل (الإضافة مؤجَّلة والشبه جملة مرخَّصة بامتدادها) يكشفه الفاحص البنيوي',
      any('غير مرخَّصة' in e for e in check_records(m['records'], m['tokens'])), check_records(m['records'], m['tokens']))
m = copy.deepcopy(o)
r_ = next(r for r in m['records'] if r['relation_id'] == pp['relation_id'])
r_['premises'] = [p for p in r_['premises'] if p != i03['relation_id']]
check('M07 إفساد حدّ المكوّن (امتدادٌ بلا مقدّمة إضافة) يكشفه الفاحص العابر للطبقات', bool(check_cross(m['records'], m['axes'])))
_, oz = run('وَٱللَّهُ بِكُلِّ طَرْسَبٍ عَلِيمٌ', 'tz')
ukz, _ = at(oz, 'tz:2', 'كُلِّ')
iz = rec(oz, 'IDAFA', mudaf=ukz)
ppz = next(r for r in oz['records'] if r['type'] == 'PP' and r['heads'].get('complement') == ukz)
check('X13 المقدّمة المرشّحة لا تصير مثبتة بالاستعمال: «طَرْسَبٍ» (شاهدٌ مصنوع) اسميته من التنوين وحده ← I03 مؤجَّلة، والامتداد غائب، والسجل يسمّيها مرشّحة',
      iz and iz['status'] == 'DEFERRED' and 'complement_ext' not in ppz['members'] and ppz['ext_candidate'] == iz['relation_id'], (iz, ppz['members']))

# ٨ الظرف: صنفه من القاعدة المحلية، وعبارته بدوره
for loc, tx in (('2:282:89', 'عِنْدَ'), ('2:282:102', 'بَيْنَ')):
    _, axz = at(o, loc, tx)
    check(f'X14 «{tx}» ({loc}): الصنف اسم بقاعدة P02 المرخَّصة، والدور ظرف منصوب على الظرفية، بلا جذرٍ ولا معنى سياقي',
          axz['word_class'][0] == 'اسم' and 'P02' in axz['word_class'][1] and (axz['inflection']['statement'] or '').startswith('ظرف منصوب على الظرفية'),
          (axz['word_class'], axz['inflection']['statement']))

# ٩ العبارة بالدور
for loc, tx, head in (('2:282:105', 'جُنَاحٌ', 'اسم «لَيْسَ» مرفوع'), ('2:282:40', 'سَفِيهًا', 'خبر «كَانَ» منصوب'), ('2:282:37', 'الَّذِي', 'في محلّ رفع اسم «كَانَ»'),
                       ('2:282:125', 'اللَّهُ', 'مبتدأ مرفوع بالابتداء'), ('2:282:128', 'عَلِيمٌ', 'خبر مرفوع'), ('2:282:127', 'شَيْءٍ', 'مضاف إليه مجرور'),
                       ('2:282:13', 'كَاتِبٌ', 'فاعل مرفوع')):
    _, axr = at(o, loc, tx)
    check(f'X15 «{tx}» ({loc}): العبارة بالدور «{head}»', head in (axr['inflection']['statement'] or ''), axr['inflection']['statement'])
uj, _ = at(o, '2:282:105', 'جُنَاحٌ')
m = copy.deepcopy(o)
m['axes'][uj]['inflection']['governor']['role_name'] = 'خبر «لَيْسَ»'
check('M08 إفساد الدور (خبر بدل اسم) يكشفه الفاحص والعبارة على حالها', bool(check_inflection(m['axes'], m['tokens'])))

# ١٠ موانع الجزم (M01): الحركة الأخيرة وحدها ليست مانعاً
lam = {(f['word_index'] + 1, f['group']): f for f in a['operators'] if f['operator'] == 'لَا'}
check('X16 «لا يأبَ» (16 و73): وجه الجزم غير ممنوع؛ مؤجَّلٌ بأوجهه (حذف حرف العلة) لا مقبولٌ تلقائياً',
      all(lam[(w, '6')]['status'] == 'deferred' and lam[(w, '6')].get('mood_faces', {}).get('rule') == 'M01.2' for w in (15, 72)),
      [(lam[(w, '6')]['status'], lam[(w, '6')].get('reject_reason')) for w in (15, 72)])
check('X17 «لا يضارَّ» (112): المضعّف المدغم يُبقي الجزم والنصب وجهين، ولا يُمنع ولا يُقبل',
      lam[(111, '6')]['status'] == 'deferred' and lam[(111, '6')]['mood_faces']['rule'] == 'M01.1' and len(lam[(111, '6')]['mood_faces']['faces']) == 2,
      lam[(111, '6')].get('mood_faces'))
a_n, _ = run('وَلَا يَكْتُبَ', 'tn')
ln = next(f for f in a_n['operators'] if f['operator'] == 'لَا' and f['group'] == '6')
check('X18 مقابل: «لا يكتبَ» (الصحيح الآخر) يبقى ممنوعاً بالفتحة: علامة نصبٍ لا تحتمل الجزم', ln['status'] == 'blocked', ln.get('reject_reason'))
check('X19 «يَدۡعُ» (الناقص): الضمة حركة العين بعد حذف اللام، و«يَعِدَ» (المثال) و«يَكۡتُبَ» لا يحتملان الجزم بالبنية',
      (jazm_faces('يَدْعُ') or {}).get('rule') == 'M01.2' and jazm_faces('يَعِدَ') is None and jazm_faces('يَكْتُبَ') is None,
      (jazm_faces('يَدْعُ'), jazm_faces('يَعِدَ'), jazm_faces('يَكْتُبَ')))
u28, ax28 = at(o, '2:282:28', 'يَتَّقِ')
u24, ax24 = at(o, '2:282:24', 'يُمْلِلِ')
check('X20 «يتقِ» مجزومٌ بحذف حرف العلة، و«يمللِ» بالسكون المحرَّك بالكسر لالتقاء الساكنين: سببان مختلفان للكسرة',
      ax28['inflection']['mark'][0] == 'حذف حرف العلة' and ax24['inflection']['mark'][0].startswith('السكون (حُرِّك بالكسر'),
      (ax28['inflection']['mark'], ax24['inflection']['mark']))

# ١١ إطار الفعل والفاعل ونائبه
u77, _ = at(o, '2:282:77', 'دُعُوا')
fr = rec(o, 'VERB_FRAME', verb=u77)['frame']
c1 = next((c for c in fr['candidates'] if c['id'] == 'F01.c1'), None)
check('X21 «دُعُوا»: الماضي المبني للمجهول مرشّحٌ كامل (زمن، بناء، ضمير، دور نائب الفاعل، تحقيق، جذر)، والإطار مؤجَّل بلا اختيار',
      c1 and c1['tense'] == 'ماضٍ' and c1['voice'] == 'مجهول' and c1['subject_role'] == 'نائب فاعل' and c1['realization'] and c1['roots']
      and rec(o, 'VERB_FRAME', verb=u77)['status'] == 'DEFERRED' and rec(o, 'VERB_FRAME', verb=u77)['selected_analysis'] is None, fr)
_, os_ = run('يَكْتُبُ ٱلرَّجُلُ ٱلْكَاتِبُ', 'ts')
uv, _ = at(os_, 'ts:1', 'يَكْتُبُ')
sr = rec(os_, 'SUBJECT', verb=uv)
check('X22 لا يُختار أقرب مرفوع إذا نافسه مرفوعٌ آخر: الفاعل مؤجَّل بمرشّحيه', sr and sr['status'] == 'DEFERRED', sr)
uk17, _ = at(o, '2:282:17', 'كَاتِبٌ')
check('X23 «ولا يأب كاتبٌ»: الفاعل الظاهر مرخَّص (S01) بلا منافس، ومقدّمته علامته المكتوبة',
      rec(o, 'SUBJECT', subject=uk17) and rec(o, 'SUBJECT', subject=uk17)['status'] == 'LICENSED', rec(o, 'SUBJECT', subject=uk17))
u29, _ = at(o, '2:282:29', 'اللَّهَ')
check('X24 المنصوب كتابةً لا يكون مرشّح فاعل («وليتق اللهَ»)', not any(u29 in sum(r['members'].values(), []) for r in o['records'] if r['type'] == 'SUBJECT'))
u36, _ = at(o, '2:282:36', 'كَانَ')
f36 = rec(o, 'VERB_FRAME', verb=u36)['frame']
check('X25 «كان» ناسخٌ مقبول: الإطار يطلب اسم الناسخ لا فاعلاً، ولا سجل فاعل له', f36['usage'].startswith('ناسخ') and f36['subject_requirement'] == 'اسم الناسخ'
      and not rec(o, 'SUBJECT', verb=u36), f36)

# ١٢ الشرط: نقلٌ بهوياته ومقدّماته من الطبقة القديمة
c4 = next((r for r in o['records'] if r['type'] == 'CONDITION' and r['positions']['tool'] == ['2:282:4']), None)
c56 = next((r for r in o['records'] if r['type'] == 'CONDITION' and r['positions']['tool'] == ['2:282:56']), None)
check('X26 «إذا تداينتم … فاكتبوه»: الأداة وفعل الشرط والجواب ورابطه منقولةٌ مرخَّصة بمقدّمات المرحلة ١٤، وبديل الظرفية محفوظ',
      c4 and c4['status'] == 'LICENSED' and c4['positions']['answer'] == ['2:282:10'] and 'linker' in c4['heads'] and c4['alternatives'],
      c4)
check('X27 «فإن لم يكونا … فرجل»: الجواب مرشّحٌ هناك فيُنقل مؤجَّلاً لا مرخَّصاً (لا تُرفع الرتبة بالنقل)',
      c56 and c56['status'] == 'DEFERRED' and c56['parts_status']['answer'] == 'DEFERRED', c56)

# ١٣ حدود M01: سؤالٌ واحد (هل تنفي الحركة الجزم؟) لا يمسّ الناصب، والمرحلة ١١ تقرأ الوجه نفسه بلا عبارةٍ تقريرية
_, ax47 = at(o, '2:282:47', 'يُمِلَّ')
check('X28 «أن يُمِلَّ» (المضعّف بعد الناصب): الفتحة علامة النصب، والاتفاق قائم (M01 لا يُطبَّق على الناصب)',
      ax47['inflection']['agreement'] == 'AGREE' and 'منصوب بـ«أَنْ»' in (ax47['inflection']['statement'] or ''), ax47['inflection']['statement'])
r15 = lam[(15, '6')].get('relation') or {}
check('X29 المرحلة ١١ في «لا يأبَ»: المشاهَد «جزم (حذف حرف العلة)»، والاتساق غير معيَّن، والدور «وجهٌ مرشّح» لا عبارةٌ تقريرية',
      r15.get('observed') == 'جزم (حذف حرف العلة)' and r15.get('consistent') is None and str(r15.get('role')).startswith('وجهٌ مرشّح'), r15)

# ١٤ توزيع الأدوار مع النواسخ، والعائد
u58, _ = at(o, '2:282:58', 'يَكُونَا')
f58 = rec(o, 'VERB_FRAME', verb=u58)['frame']
check('X30 «يكونا» من صيغ «كان» (VERBAL) ولم يُقبل ناسخاً: ضميره «اسم الناسخ أو فاعل التامّ» لا «فاعل» — والمسند إليه ألف الاثنين '
      'المكتوبة في الوجهين، بنيةٌ مشتركة مرخَّصة، والاستعمال باقٍ مؤجَّلاً (عُدّل لعقد SARF_MUDARI_AGREEMENT_AND_ISNAD_01)',
      f58['subject']['status'] == 'LICENSED' and f58['subject']['role'] == 'اسم الناسخ أو فاعل التامّ' and
      f58['subject'].get('shared_across') == ['ناقص', 'تامّ'] and 'VERBAL' in f58['usage'] and
      any('غير محسوم' in x for x in (f58.get('open') or [])), f58['subject'])
f36b = rec(o, 'VERB_FRAME', verb=u36)
check('X31 «كان» الناسخ المقبول: الإطار متّسق (البناء للمجهول لا ينطبق عليه)، وإسناده «اسم الناسخ (V01)»',
      f36b['status'] == 'LICENSED' and f36b['frame']['subject']['kind'] == 'اسم الناسخ (V01)', (f36b['status'], f36b['frame']['subject']))
s2 = next(r for r in o['records'] if r['type'] == 'SILAH' and r['heads'].get('relative') == u2)
check('X32 صلة «الذين آمنوا» مرخَّصة بنطاقها، والعائد مؤجَّل: ضمير الصيغة في «آمنوا» مرشّح، والمطابقة على مرشّحٍ لا تثبت المرجع',
      s2['status'] == 'LICENSED' and s2['resumptive']['status'] == 'DEFERRED' and 'مرشّح' in s2['resumptive']['note'], s2['resumptive'])
u62, ax62 = at(o, '2:282:62', 'مِمَّنْ')
p3 = rec(o, 'PP', preposition=u62)
check('X33 «مِمَّنْ» = «مِنْ» + «مَنْ»: جزآن بهويتين، و«مَنْ» في محلّ جر (P03)، ونوعه بدائل، وصلته «ترضون» مؤجَّلة',
      p3 and p3['rule_id'] == 'P03' and len(p3['parts']) == 2 and ax62['case_axis'][0] == 'في محلّ جر' and p3['kind_status'] == 'DEFERRED'
      and any(r['type'] == 'SILAH' and r['heads'].get('relative') == u62 and r['status'] == 'DEFERRED' for r in o['records']), p3)

# ١٥ أخطاءٌ كشفتها مراجعة عينة المصحف (بعد 010)، وحدودها
_, oq = run(verse_text(2, 193), '2:193')
uq, _ = at(oq, '2:193:1', 'هُمْ')
check('X34 «وَقَٰتِلُوهُمۡ» (2:193): «ـُو + ضمير» فعلٌ بواو الجماعة أو جمعٌ مضاف — I01 مؤجَّل لا مضافٌ إليه مرخَّص',
      not any(r['type'] == 'IDAFA' and r['status'] == 'LICENSED' and uq in sum(r['members'].values(), []) for r in oq['records']))
_, oq = run(verse_text(19, 20), '19:20')
ug, _ = at(oq, '19:20:5', 'غُلَٰمٌ')
check('X35 «قَالَتۡ أَنَّىٰ يَكُونُ لِي غُلَٰمٌ» (19:20): لا يُعبر فعلٌ آخر إلى مرشّح الفاعل',
      not any(r['type'] == 'SUBJECT' and r['status'] == 'LICENSED' and r['heads'].get('subject') == ug for r in oq['records']))
_, oq = run(verse_text(6, 73), '6:73')
ua, _ = at(oq, '6:73:19', 'عَٰلِمُ')
check('X36 «يُنفَخُ فِي ٱلصُّورِ … عَٰلِمُ» (6:73): شبه الجملة بعد المبني للمجهول قد تكون نائب الفاعل، فلا يُرخَّص الاسم بعدها',
      not any(r['type'] == 'SUBJECT' and r['status'] == 'LICENSED' and r['heads'].get('subject') == ua for r in oq['records']))

_, oq = run(verse_text(17, 20), '17:20')
ukk, _ = at(oq, '17:20:7', 'كَ')
check('X37 حدّ المكوّن: امتداد شبه الجملة بالإضافة يضمّ ضمير المضاف إليه من كلمته (عَطَآءِ رَبِّكَ)، فلا يُجعل الضمير مسنداً',
      not any(r['type'] == 'PREDICATION' and r['heads'].get('predicate') == ukk for r in oq['records']) and
      any(r['type'] == 'PP' and ukk in r['members'].get('complement_ext', []) for r in oq['records']))

# ١٦ إصلاحات ما قبل الاعتماد (بعد 013): نوع الصلة والعائد، وتسرّب المرشّح الممنوع، والتزامات الناسخ، وأجزاء الأطراف، وهوية التحليل
u25 = at(o, '2:282:25', 'الَّذِي')[0]
s25 = next(r for r in o['records'] if r['type'] == 'SILAH' and r['heads'].get('relative') == u25)
c25 = next(r for r in o['records'] if r['type'] == 'CONTAINER_RELATIVE' and r['heads'].get('relative') == u25)
check('X38 «الذي عليه الحق»: نوع الصلة مؤجَّلٌ بوجهيه (اسمية بـR01، وشبه جملة في الطبقة القديمة)، والربط مرخَّص، وR01 يحفظ الوجه الآخر بديلاً',
      s25['status'] == 'LICENSED' and s25['kind_status'] == 'DEFERRED' and len(s25['silah_kinds']) == 2 and c25['alternatives'], s25.get('silah_kinds'))
cands25 = s25['resumptive']['candidates']
check('X39 العائد سجلٌّ واحد بمرشّحي الطبقتين («هِ» من R01، والمستتر من الطبقة القديمة)، مؤجَّل، ولا يُسقط أحدهما الآخر',
      s25['resumptive']['status'] == 'DEFERRED' and len(cands25) == 2 and any(x['unit'] for x in cands25), cands25)
f77 = rec(o, 'VERB_FRAME', verb=u77)
_, ax77 = at(o, '2:282:77', 'دُعُوا')
check('X40 «دُعُوا»: المرشّح الممنوع (الأمر) لا يتسرّب — زمن الإطار وبناؤه من القائم، وصنف المحور وبناؤه يسمّيانه ممنوعاً، والشرط يُصالَح به بلا رفع رتبة',
      f77['frame']['tense'][0] == 'ماضٍ' and f77['frame']['voice'][0] == 'مجهول' and 'ممنوع' in f77['frame']['stage8']['note']
      and f77['frame']['subject_requirement'] == 'نائب فاعل' and not any(p.startswith('الزمن: أمر') for p in f77['premises'])
      and 'F01.c1' in ax77['word_class'][1] and 'أمر' not in ax77['inflection']['build'][1].split('الممنوع')[0]
      and any('المصالحة مع F01' in p for r in o['records'] if r['type'] == 'CONDITION' and r['heads'].get('condition_verb') == u77
              for p in r['premises']), (f77['frame']['tense'], ax77['word_class'], ax77['inflection']['build']))
f36c = rec(o, 'VERB_FRAME', verb=u36)['frame']
u103 = at(o, '2:282:103', 'لَيْسَ')[0]
f103 = rec(o, 'VERB_FRAME', verb=u103)['frame']
check('X41 التزامات الناسخ تُسوّى بسجلّ V01: «كان» و«ليس» المرخَّصان باسمهما وخبرهما لا التزام مفتوحاً لهما، و«يكونا» يسمّي خبره المرشّح',
      f36c['open'] == [] and f103['open'] == [] and f36c['subject'].get('v01') and 'رَجُلَيْنِ' in ' '.join(rec(o, 'VERB_FRAME', verb=u58)['frame']['open']), (f36c['open'], f103['open']))
pp92 = rec(o, 'PP', preposition=u92)
vo1 = next(r for r in o['records'] if r['type'] == 'VOCATIVE')
check('X42 الأطراف بهويات أجزائها: «لِ» و«الشَّهَٰدَةِ» جزآن من وحدة «لِلشَّهَٰدَةِ»، و«أيّ» جزءٌ من «أَيُّهَا»، وكلها في سجلّ الأجزاء',
      pp92['head_parts']['preposition'] != pp92['head_parts']['complement'] and all(pid in o['parts'] for pid in pp92['head_parts'].values())
      and vo1['head_parts']['munada'] in o['parts'] and o['parts'][vo1['head_parts']['munada']]['text'] == 'أَيُّ', (pp92['head_parts'], vo1['head_parts']))
m = copy.deepcopy(o)
next(r for r in m['records'] if r['relation_id'] == pp92['relation_id'])['head_parts']['complement'] = vo1['head_parts']['munada']
check('M09 إفساد جزء الطرف (جزءٌ من وحدةٍ أخرى) يكشفه الفاحص البنيوي', bool(check_records(m['records'], m['tokens'], m['parts'])))
idn = o['axes'][u2]['identity']
check('X43 هوية التحليل واحدة في المحاور: لكل وحدةٍ analysis_id وخاناتها ومعرّفات المرحلة ١١، وعلاقة دورها تحمل الهوية نفسها',
      idn['analysis_id'] == f'{u2}@v1' and idn['stage11'] and idn['analysis_id'] in fol['analysis_id'], idn)
m = copy.deepcopy(o)
m['axes'][ut]['inflection']['governor']['target_slot'] = 99
check('M10 إفساد هوية المعمول في المرحلة ١١ (خانةٌ ليست من الوحدة) يكشفه الفاحص العابر للطبقات', bool(check_cross(m['records'], m['axes'])))
m = copy.deepcopy(o)
r_ = next(r for r in m['records'] if r['relation_id'] == fol['relation_id'])
r_['analysis_id'] = 'X@v1'
r_['members'] = {k: [x for x in v if x != u2] for k, v in r_['members'].items()}
check('M11 إفساد هوية التحليل في علاقة الدور يكشفه الفاحص العابر للطبقات', bool(check_cross(m['records'], m['axes'])))

# ١٧ إدارة الأوجه: ترخيص الوجه غير اختياره، وكل وجهٍ ومرشّحٍ بحالة دليله، وربط المقدّمات بمرشّحها وعلاقتها؛ وأجزاء الشرط، والسمات بالعربية
u27 = at(o, '2:282:27', 'الْحَقُّ')[0]
n27 = next(r for r in o['records'] if r['type'] == 'PREDICATIVE_PP' and r['heads'].get('subject') == u27)
ax27 = o['axes'][u27]
v36 = rec(o, 'NASIKH', nasikh=u36)
check('X44 ترخيص الوجه غير اختياره: «الحق» مبتدأٌ مرخَّص في وجه R01 (N02 LICENSED، والاختيار مؤجَّل)، وحكم الرفع AGREE بعبارةٍ تسمّي الوجه؛ وحدّ الصلة و«كان» V01 مرخَّصان',
      n27['status'] == 'LICENSED' and n27.get('selection') == 'DEFERRED' and n27.get('face') == 'R01' and n27.get('nucleus_complete') is True
      and ax27['role'][0] == 'مبتدأ' and 'غير مختار' in ax27['role'][1] and ax27['inflection']['agreement'] == 'AGREE'
      and 'في وجه R01 المرخَّص، والوجه غير مختار' in ax27['inflection']['statement']
      and c25['status'] == 'LICENSED' and c25.get('selection') == 'DEFERRED' and v36['status'] == 'LICENSED',
      (n27['status'], n27.get('selection'), ax27['role'], ax27['inflection']['statement']))
k25 = {k['layer']: k for k in s25['silah_kinds']}
check('X49 كل وجهٍ بحالة دليله لا بوجود منافسه: K1 (R01) LICENSED كحاويته، وK2 (الطبقة القديمة) مؤجَّلٌ لأنه لا يذكر المرفوع «الحق»؛ '
      'والبديل المحفوظ لا يُنسب إليه ما لم يقله (لا «الحق فاعله»)',
      k25['R01']['status'] == c25['status'] == 'LICENSED' and k25['LEGACY']['status'] == 'DEFERRED' and 'لا يذكر هذا الوجه دور المرفوع' in k25['LEGACY']['why']
      and not any('فاعله (وجه الطبقة القديمة)' in a_ for a_ in c25['alternatives'] + n27['alternatives'])
      and any('وجه الطبقة القديمة' in a_ and 'لا يذكر دور المرفوع' in a_ for a_ in c25['alternatives']), (k25, c25['alternatives']))
m = copy.deepcopy(o)
next(r for r in m['records'] if r['relation_id'] == n27['relation_id']).pop('selection')
check('M12 إفساد الاختيار (إسنادٌ مرخَّص في وجهٍ غير مختار بلا اختيارٍ مؤجَّل) يكشفه الفاحص العابر للطبقات', bool(check_cross(m['records'], m['axes'])))
m = copy.deepcopy(o)
next(k for r in m['records'] if r['relation_id'] == s25['relation_id'] for k in r['silah_kinds'] if k['layer'] == 'R01')['status'] = 'DEFERRED'
check('M13 إفساد ترخيص الوجه (تنزيل وجه R01 لوجود منافسه، وحاويته مرخَّصة) يكشفه الفاحص العابر للطبقات', bool(check_cross(m['records'], m['axes'])))
cands25 = s25['resumptive']['candidates']
lk25 = s25['premise_links']
check('X45 العائد: لكل مرشّحٍ ترخيصه من دليله ووجهه («هِ» في K1، والمستتر في K2)، والاختيار مؤجَّل؛ وكل مقدّمةٍ مربوطةٌ بمرشّحها وعلاقتها الفعلية وحالتها',
      s25['resumptive']['status'] == 'DEFERRED' and {x['face'] for x in cands25} == {'K1', 'K2'}
      and all(any(l_['premise'] == p_ for l_ in lk25) for p_ in s25['premises'])
      and any(l_['relation'] == c25['relation_id'] and l_['candidate'] == 'K1' and l_['status'] == 'LICENSED' for l_ in lk25)
      and any(l_['layer'] == 'LEGACY' and l_['candidate'] == 'K2' for l_ in lk25)
      and all('في الطبقة القديمة' in p_ for p_ in s25['premises'] if p_.startswith('المرحلة ١٤')), (cands25, lk25))
m = copy.deepcopy(o)
next(l_ for r in m['records'] if r['relation_id'] == n27['relation_id'] for l_ in r['premise_links'] if l_['relation'])['relation'] = s25['relation_id']
check('M14 إفساد ربط المقدّمة (مقدّمةٌ مربوطة بعلاقةٍ غير علاقتها) يكشفه الفاحص العابر للطبقات', bool(check_cross(m['records'], m['axes'])))
m = copy.deepcopy(o)
next(l_ for r in m['records'] if r['relation_id'] == s25['relation_id'] for l_ in r['premise_links'] if l_['relation'])['status'] = 'DEFERRED'
check('M15 إفساد حالة المقدّمة المربوطة (غير حالة علاقتها الفعلية) يكشفه الفاحص العابر للطبقات', bool(check_cross(m['records'], m['axes'])))
cr = [r for r in o['records'] if r['type'] == 'CONDITION' and r['status'] == 'DEFERRED']
check('X46 أجزاء الشرط في السبب بأسمائها العربية (فعل الشرط، الجواب)، بلا مفاتيح داخلية',
      cr and all('=' not in r['reason'] and 'answer' not in r['reason'] and 'condition_verb' not in r['reason'] for r in cr), [r['reason'] for r in cr])
import re as _re
leak = [p for r in o['records'] for p in r['premises'] + [r['reason']] + list(r.get('alternatives') or [])
        if isinstance(p, str) and _re.search(r"\b(singular|dual|plural|masc|fem|common)\b|\{'|\['|ملف المبنيات: [a-z_]+(?! \()", p)]
check('X47 لا سماتٌ بالإنجليزية ولا تمثيل بايثون في سبب العلاقات ومقدّماتها وبدائلها', not leak, leak[:3])

noev = [(o['tokens'][i][1], o['tokens'][i][2]) for i, (u, l, t) in enumerate(o['tokens'])
        if o['axes'][u]['word_class'][0] and not o['axes'][u]['word_class'][1]]
check('X48 لا صنفَ بلا دليل: دليل الاسم من أساس الحكم نفسه (سمة المرحلة ١٣ المثبتة، أو لفظ الجلالة، أو الاسم الذهبي، أو E01)', not noev, noev[:5])

# ١٨ البناء: كل وجهٍ بتحقيقه للمكتوب (F02)، لا بالافتراض
from sarf.relations import _voice_faces
vf_t = {w: [(f['voice'], f['status']) for f in (_voice_faces(w) or [])] for w in ('يُضَارَّ', 'تُضَآرَّ', 'يُقَالُ', 'يُغَاثُ', 'يَقُولُ', 'يُقَاتِلُ')}
check('X51 F02: «يُفَالُّ» (المضعّف) يحقّق الوجهين فيبقيان مرخَّصين؛ و«يُفَالُ» (الأجوف) يمنع المعلوم بمانعٍ مكتوب؛ وما ليس من الرسمين لا يُفحص',
      vf_t['يُضَارَّ'] == vf_t['تُضَآرَّ'] == [('معلوم', 'LICENSED'), ('مجهول', 'LICENSED')]
      and vf_t['يُقَالُ'] == vf_t['يُغَاثُ'] == [('معلوم', 'REJECTED'), ('مجهول', 'LICENSED')] and vf_t['يَقُولُ'] == vf_t['يُقَاتِلُ'] == [], vf_t)
a1249, o1249 = run(verse_text(12, 49), '12:49')
s1249 = next(r for r in o1249['records'] if r['type'] == 'SUBJECT' and r['status'] == 'LICENSED' and r['texts'].get('verb') == 'يُغَاثُ')
u1249 = s1249['heads']['subject']
ax1249 = o1249['axes'][u1249]
f1249 = next(r for r in o1249['records'] if r['type'] == 'VERB_FRAME' and r['texts'].get('verb') == 'يُغَاثُ')
check('X50 «يُغَاثُ النَّاسُ»: المعلوم ممنوعٌ بالرسم (F02)، فالبناء مجهولٌ مثبت، و«النَّاسُ» نائب فاعلٍ مرخَّص بدليله، لا «فاعل» بالافتراض ولا وجهان متساويان',
      s1249['role_name'] == 'نائب فاعل' and not s1249.get('selection') and f1249['frame']['voice'][0] == 'مجهول'
      and any(p.startswith('البناء بأوجهه: F02') for p in f1249['premises']) and ax1249['inflection']['agreement'] == 'AGREE'
      and ax1249['inflection']['statement'].startswith('نائب فاعل') and not clean(o1249), (s1249.get('role_name'), f1249['frame']['voice']))
m = copy.deepcopy(o1249)
next(r for r in m['records'] if r['relation_id'] == s1249['relation_id'])['selection'] = 'DEFERRED'
check('M16 إفساد الاختيار (دورٌ من علاقةٍ اختيارها مؤجَّل بلا تسمية وجه) يكشفه الفاحص العابر للطبقات', bool(check_cross(m['records'], m['axes'])))

# ١٩ هوية المرشّح في الطبقات: الزمن والبناء والعامل والدور من مرشّحٍ واحد
check('X52 هوية المرشّح: 2:282 و12:49 بلا خلطٍ بين الإطار والمحور والعامل والدور', not clean(o) and not clean(o1249), (clean(o)[:2], clean(o1249)[:2]))
f19 = rec(o, 'VERB_FRAME', verb=at(o, '2:282:19', 'يَكْتُبَ')[0])
m = copy.deepcopy(o)
next(r for r in m['records'] if r['relation_id'] == f19['relation_id'])['frame']['tense'] = ('ماضٍ', 'مثبت', None)
check('M17 إفساد الزمن في الإطار (ماضٍ مثبت ومحوره معرب منصوبٌ بـ«أن») يكشفه الفاحص العابر للطبقات', bool(check_cross(m['records'], m['axes'])))
m = copy.deepcopy(o1249)
next(r for r in m['records'] if r['relation_id'] == s1249['relation_id'])['role_name'] = 'فاعل'
check('M18 إفساد الدور (فاعل لفعلٍ بناؤه المجهول مثبت) يكشفه الفاحص العابر للطبقات', bool(check_cross(m['records'], m['axes'])))

# ٢٠ كاشف المكمّل بحدوده (مراجعة 025): لا يعبر أداةً ولا فعلاً ولا يجعل خبر الناسخ مفعولاً، ولا ينفي ما لم يكشفه
def _oreq(loc, txt):
    return rec(o, 'VERB_FRAME', verb=at(o, loc, txt)[0])['frame'].get('object_requirement') or {}
q95, q79, q58, q98 = _oreq('2:282:95', 'تَرْتَابُوا'), _oreq('2:282:79', 'تَسْءَمُوا'), _oreq('2:282:58', 'يَكُونَا'), _oreq('2:282:98', 'تَكُونَ')
q45, q28, q63 = _oreq('2:282:45', 'يَسْتَطِيعُ'), _oreq('2:282:28', 'يَتَّقِ'), _oreq('2:282:63', 'تَرْضَوْنَ')
check('X53 «ترتابوا إلّا أن تكون تجارةً»: يقف الكاشف عند «إلّا» ولا يُسند «تجارةً» إلى «ترتابوا»',
      q95.get('kind') == 'NOT_FOUND_IN_SCOPE' and 'إِلَّا' in q95['note'] and 'تِجَٰرَةً' not in q95['note'], q95)
check('X56 «تسأموا أن تكتبوه صغيراً»: «أن تكتبوه» مكمّلٌ مكتوب غير محلَّل، ولا يُشخَّص «صغيراً» مفعولاً لـ«تسأموا»',
      q79.get('kind') == 'UNANALYZED_COMPLEMENT' and 'صَغِيرًا' not in q79['note'], q79)
check('X57 «يكونا رجلين» و«تكون تجارةً»: خبرٌ مرشّح في وجه الناقص، لا مفعول',
      q58.get('kind') == q98.get('kind') == 'KHABAR_CANDIDATE' and 'رَجُلَيْنِ' in q58['note'] and 'تِجَٰرَةً' in q98['note'], (q58, q98))
check('X58 «يستطيع أن يُملّ»: مكمّلٌ غير محلَّل مُعلَن، لا «لا مفعول مكتوب»؛ و«ترضون من الشهداء أن تضلّ»: الحدّ بعد شبه الجملة لا يُنسب إليه',
      q45.get('kind') == 'UNANALYZED_COMPLEMENT' and q63.get('kind') == 'NOT_FOUND_IN_SCOPE' and 'لا يُنسب' in q63['note'], (q45, q63))
# C063 (§٦): «اللَّهَ» بعد «يتق» مفعولٌ مرشّح في سجلّ O03 مؤجَّل (التعدّي مرشّح غير مثبت)، لا «غير مربوط» ولا مرخَّص
o28 = next((r for r in o['records'] if r['type'] == 'OBJECT' and r['rule_id'] == 'O03' and r['texts'].get('verb') == 'يَتَّقِ'), None)
check('X59 «يتق الله»: مفعولٌ مرشّح مؤجَّل (O03) بلا ترخيص؛ ولا «لازم» ولا «محذوف» في أيّ تشخيص',
      q28.get('kind') == 'OBJECT_CANDIDATE_DEFERRED' and 'اللَّهَ' in q28['note'] and o28 is not None and o28['status'] == 'DEFERRED'
      and q28.get('relation_id') == o28['relation_id'] and 'تعدّيه مرشّحٌ غير مثبت' in o28['reason']
      and 'مرشّحٌ للمكمّلية' in q45['note'] and 'موجودٌ' not in q45['note']
      and not any('لازمٌ في هذا الاستعمال' in str((r['frame'].get('object_requirement') or {}).get('note')) for r in o['records'] if r['type'] == 'VERB_FRAME'),
      q28)
f112 = next((r for r in o['records'] if r['type'] == 'VERB_FRAME' and r['texts'].get('verb') == 'يُضَارَّ'), None)
s112 = next((r for r in o['records'] if r['type'] == 'SUBJECT' and r['texts'].get('verb') == 'يُضَارَّ'), None)
check('X60 «يُضَآرَّ كاتبٌ» (إن كان فعلاً في المعجم): الوجهان باقيان والرفع مشترك بلا اختيارٍ خفي',
      f112 is None or (s112 and s112['role_name'] == 'فاعل أو نائب فاعل' and s112.get('selection') == 'DEFERRED'
                       and {f_['voice'] for f_ in s112.get('voice_face_evidence') or []} == {'معلوم', 'مجهول'}), s112 and s112.get('role_name'))
c77 = next(r for r in o['records'] if r['type'] == 'CONDITION' and r['heads'].get('condition_verb') == u77)
check('X54 شرط «إذا ما دُعُوا»: المصالحة مع F01 أولُ المقدّمات، ومقدّمة الطبقة القديمة القائمة على وجه الأمر الممنوع موسومةٌ بأنه لا يُبنى عليها',
      c77['premises'][0].startswith('المصالحة مع F01') and any('قائمةٌ على وجهٍ ممنوع في F01' in p for p in c77['premises'][1:]), c77['premises'])

# ٢١ الأجزاء: مجالاتها ومقاطعها بنظام إحداثيات واحد، ومعرّف العلاقة بهوية الجزء
vo_ = next(r for r in o['records'] if r['type'] == 'VOCATIVE')
p03_ = next(r for r in o['records'] if r['type'] == 'PP' and r['rule_id'] == 'P03')
check('X55 أجزاء «أيّها» و«مِمَّنْ» بمجالات المحارف (الحروف المجمَّعة في نص الوحدة، نصف مفتوح) ومقاطعها، والمدغم المشترك معلَن؛ ومعرّفات العلاقات بهوية الجزء',
      [p_['span'] for p_ in vo_['parts']] == [[0, 2], [2, 4]] and all(p_.get('syllables') for p_ in vo_['parts'])
      and [p_['span'] for p_ in p03_['parts']] == [[0, 2], [1, 3]] and 'مشترك' in (p03_['parts'][0].get('note') or '')
      and '/s0' in pp92['relation_id'] and '/p0' in vo_['relation_id'] and '/p1' in p03_['relation_id'],
      ([p_.get('span') for p_ in vo_['parts']], [p_.get('span') for p_ in p03_['parts']], pp92['relation_id']))
m = copy.deepcopy(o)
r_ = next(r for r in m['records'] if r['relation_id'] == pp92['relation_id'])
r_['relation_id'] = r_['relation_id'].replace('/s2', '').replace('/s0', '')
check('M19 إفساد معرّف العلاقة (بالوحدة لا بالجزء) يكشفه الفاحص البنيوي', bool(check_records(m['records'], m['tokens'], m['parts'])))

print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
