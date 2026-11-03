#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_inflection.py — محور البناء والإعراب: اتساق العامل والمعمول والعبارة، اختباراتٌ عابرة للطبقات واختبارات إفساد.

المدخل نصٌّ مشكول وحده؛ ولا تُمرَّر القيم المتوقعة إلى المحلّل.
- الشواهد: في البيتِ، في البيتينِ، عليهِ، علَّمَ، ليتقِ، أن تكونَ (ملحق المالك)؛ وصفوف تدقيق 2:282 (F03، F04، F05، F09، F22).
- عابرٌ للطبقات بهوية التحليل نفسها: سجل العامل في المرحلة ١١، وسمة الصنف والزمن في المرحلة ١٣، وسجل العلاقة، والنص في
  صفحة التتبّع، لكل وحدةٍ بمعرّفها.
- إفساد: تغيير العلامة أو العبارة أو هوية المعمول أو مقتضى العامل أو النص؛ ويجب أن يكشفه الفاحص.
"""
import copy, os, subprocess, sys, tempfile

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.algebra import Trace, sentence_geo
from sarf.features import unit_features
from sarf.relations import verse_relations, check_inflection

CAT = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
FAIL = []


def run(text, ref='t'):
    a = analyze(CAT, text)
    _, U = sentence_geo(a, 'Q' + ref, Trace())
    F = unit_features(a, U)
    return a, U, F, verse_relations(a, U, F, ref)


def unit(o, text):
    hits = [(u, o['axes'][u]) for u, _, t in o['tokens'] if t == text]
    assert hits, f'لا وحدة «{text}» في {[t for _, _, t in o["tokens"]]}'
    return hits[0]


def check(name, cond, got):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f' — {got}'))
    if not cond:
        FAIL.append(name)


def verse_text(s, v):
    # هذا الملف مثبَّتٌ على مصحف المجمّع (مواضعه وصيغه من تدقيق 2:282)؛ والمصحف المعتمد الجديد له tests/test_quran_source.py
    for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 3 and p[0] == str(s) and p[1] == str(v):
            return p[2]


# ١ شواهد الملحق
_, _, _, o = run('فِي ٱلۡبَيۡتِ')
_, ax = unit(o, 'الْبَيْتِ')
i = ax['inflection']
check('I01 في البيتِ: مجرور بفي وعلامة جره الكسرة الظاهرة',
      i['agreement'] == 'AGREE' and i['statement'] == 'اسم مجرور بـ«فِي» وعلامة جرّه الكسرة الظاهرة' and i['mark_kind'] == 'ظاهرة'
      and ax['word_class'][0] == 'اسم' and i['build'][0] == 'معرب', (i['statement'], i['agreement']))

_, _, _, o = run('فِي ٱلۡبَيۡتَيۡنِ')
_, ax = unit(o, 'الْبَيْتَيْنِ')
i = ax['inflection']
check('I02 في البيتينِ: الجر بالياء لا بكسرة النون',
      i['agreement'] == 'AGREE' and i['mark'][0] == 'الياء' and 'الكسرة' not in (i['statement'] or '') and
      i['mark_kind'] == 'بالحرف نيابةً عن الحركة', (i['statement'], i['mark'], i['agreement'], i['state']))

_, _, _, o = run('عَلَيۡهِ')
_, ax = unit(o, 'هِ')
i = ax['inflection']
check('I03 عليهِ: الضمير في محل جر، وكسرة الهاء ليست علامة إعرابه',
      i['agreement'] == 'AGREE' and i['mark'] is None and i['mark_kind'] == 'محلّي' and 'في محلّ جر' in i['statement']
      and 'مبني على الكسر' in i['statement'] and 'وعلامة' not in i['statement'], (i['statement'], i['mark']))

_, _, _, o = run('كَمَا عَلَّمَهُ ٱللَّهُ')
_, ax = unit(o, 'عَلَّمَ')
i = ax['inflection']
check('I04 علَّمَ: ماضٍ مبني على الفتح، لا حالة إعراب',
      i['build'][0] == 'مبني' and i['statement'] == 'فعل ماضٍ مبني على الفتح' and i['state'][0] is None and i['mark'] is None,
      (i['build'], i['statement'], i['state']))

_, _, _, o = run('وَلۡيَتَّقِ ٱللَّهَ رَبَّهُۥ')
_, ax = unit(o, 'يَتَّقِ')
i = ax['inflection']
check('I05 ليتقِ: مجزوم بحذف حرف العلة، والكسرة ليست جرّاً',
      i['agreement'] == 'AGREE' and i['mark'][0] == 'حذف حرف العلة' and 'مجزوم' in i['statement'] and 'مجرور' not in i['statement']
      and i['mark_kind'] == 'بالحذف', (i['statement'], i['mark']))

_, _, _, o = run('إِلَّآ أَن تَكُونَ تِجَٰرَةً حَاضِرَةࣰ')
_, ax = unit(o, 'تَكُونَ')
i = ax['inflection']
check('I06 أن تكونَ: منصوب بالفتحة، والنون أصلية لا نون رفع',
      i['agreement'] == 'AGREE' and i['mark'][0] == 'الفتحة' and 'منصوب بـ«أَنْ»' in i['statement'] and 'النون' not in i['statement'],
      (i['statement'], i['mark']))

# ٢ صفوف تدقيق 2:282، وعابرٌ للطبقات بهوية التحليل نفسها
T = verse_text(2, 282)
a, U, F, o = run(T, '2:282')
axes = o['axes']
check('I07 الفاحص المستقل نظيف على 2:282', not check_inflection(axes, o['tokens']), check_inflection(axes, o['tokens'])[:3])
verbs_jarr = [(l, t) for u, l, t in o['tokens'] if axes[u]['word_class'][0] == 'فعل' and
              ('مجرور' in (axes[u]['inflection']['statement'] or '') or axes[u]['inflection']['state'][0] == 'جر')]
check('I08 لا فعل مجروراً (F04)', not verbs_jarr, verbs_jarr)
prot = {t: axes[u]['protection'][0] for u, _, t in o['tokens'] if t in ('اللَّهُ', 'الَّذِي', 'كَانَ', 'لَيْسَ')}
check('I09 الحماية تنتقل إلى المحور (F09): الله والذي وكان وليس', all(prot.get(x) for x in ('اللَّهُ', 'الَّذِي', 'كَانَ', 'لَيْسَ')), prot)
_, ax = unit(o, 'امْرَأَتَانِ')
check('I10 امرأتان: العلامة الألف رفعاً (F22)، ولا عبارة بلا عامل', ax['inflection']['mark'][0] == 'الألف' and
      ax['inflection']['statement'] is None, ax['inflection']['mark'])
n_imr = next(r_ for r_ in o['records'] if r_['type'] == 'PREDICATION' and r_['texts'].get('subject') == 'امْرَأَتَانِ')
check('I16 عابر: سجل الإسناد يقرأ علامة المثنى كما يقرؤها المحور (لا «لا علامة»)',
      any('الرفع مكتوب' in x for x in n_imr['premises']) and not any('لا علامة' in x for x in n_imr['premises']), n_imr['premises'][:3])
_, _, _, o3 = run('تِلۡكَ ءَايَٰتُ ٱلۡقُرۡءَانِ')
_, ax3 = unit(o3, 'الْقُرْءَانِ')
check('I17 القرآنِ ليس مثنى: العدد المرشّح لا يُقرأ به الألف رفعاً', (ax3['inflection']['mark'] or ('',))[0] != 'الألف',
      ax3['inflection']['mark'])
_, axd = unit(o, 'ذَٰلِكُمْ')
check('I18 ذلكم: لا تُذكر حركة بناءٍ من ميم الخطاب', 'السكون' not in (axd['inflection']['statement'] or ''),
      axd['inflection']['statement'])
_, _, _, o4 = run('إِنَّ ٱللَّهَ لَا يُحِبُّ ٱلظَّٰلِمِينَ')
_, ax4 = unit(o4, 'الظَّٰلِمِينَ')
check('I19 العدد المرشّح: العلامة غير معيَّنة، فلا AGREE ولا CONFLICT زائف', ax4['inflection']['agreement'] in ('UNGOVERNED', 'UNVERIFIED')
      and ax4['inflection']['statement'] is None, (ax4['inflection']['agreement'], ax4['inflection']['mark']))
_, ax = unit(o, 'يَأْبَ')
check('I11 يأبَ: لا عامل مقبول، فلا عبارة نصب (F06 مؤجَّل لا مقلوب)', ax['inflection']['statement'] is None and
      ax['inflection']['agreement'] == 'UNGOVERNED', ax['inflection']['statement'])

# عابر: لكل AGREE بعاملٍ: سجل العامل في المرحلة ١١ هو نفسه (المعمول بالوحدة نفسها، والمقتضى نفسه)، والصنف من المرحلة ١٣
uid_of = {k: U[k].id for k in U}
bad = []
for o_ in a['operators']:
    r = o_.get('relation') or {}
    t = r.get('target') or {}
    if o_.get('status') != 'accepted' or not t:
        continue
    seg = a['segments'][t['word_index']]
    ui = next((n for n, u in enumerate(seg['units']) if t['slot'] in u.get('slots', [])), None)
    uid = uid_of.get((t['word_index'], ui))
    if uid is None or uid not in axes:
        continue
    g = axes[uid]['inflection']['governor'] or {}
    if g.get('kind') != 'عامل' or g.get('operator') != o_['operator'] or g.get('expected') != r.get('expected') or g.get('target_uid') != uid:
        bad.append((uid, o_['operator'], r.get('expected'), g.get('operator'), g.get('expected')))
    pos = (F.get((t['word_index'], ui)) or {}).get('pos', {}).get('v')
    wc = axes[uid]['word_class'][0]
    if wc == 'فعل' and pos != 'فعل' or pos == 'فعل' and axes[uid]['word_class'][0] not in ('فعل', None):
        bad.append((uid, 'صنف', pos, wc))
check('I12 عابر: عامل المحور = سجل المرحلة ١١ بالمعمول نفسه، والصنف = المرحلة ١٣', not bad, bad[:5])
# عابر: علاقة الابتداء المرخَّصة ← دور المعمول في المحور
rel_bad = [r_['relation_id'] for r_ in o['records'] if r_['status'] == 'LICENSED' and r_['type'] == 'PREDICATION'
           and (axes[r_['heads']['subject']]['inflection']['governor'] or {}).get('relation_id') != r_['relation_id']]
check('I13 عابر: الإسناد المرخَّص هو مصدر رفع المبتدأ في المحور (بمعرّفه)', not rel_bad, rel_bad)

# عابر: العبارة نفسها في صفحة التتبّع للوحدة نفسها
with tempfile.TemporaryDirectory() as d:
    out = os.path.join(d, 't.html')
    subprocess.run([sys.executable, H + 'tools/pipeline_trace.py', '2:282', '-o', out, '--quiet'], check=True,
                   capture_output=True, env=dict(os.environ, SARF_QURAN='hafs_kfgqpc'))   # المصدر نفسه الذي يقرؤه هذا الملف
    page = open(out, encoding='utf-8').read()
import html as _h
missing = [(u, axes[u]['inflection']['statement']) for u, _, _ in o['tokens'] if axes[u]['inflection']['statement'] and
           _h.escape(axes[u]['inflection']['statement']) not in page]
check('I14 عابر: كل عبارةٍ في المحور معروضةٌ في صفحة التتبّع', not missing, missing[:3])

# ٣ إفساد: يجب أن يكشفه الفاحص
u_dayn = unit(o, 'دَيْنٍ')[0]
u_kum = unit(o, 'الْعَدْلِ')[0]


def mutated(fn):
    m = copy.deepcopy(axes)
    fn(m)
    return check_inflection(m, o['tokens'])


check('M01 إفساد العلامة (الكسرة ← الفتحة) يُكشف',
      bool(mutated(lambda m: m[u_dayn]['inflection'].update(mark=('الفتحة', 'مفسَد'),
                                                            statement='اسم مجرور بـ«بِ» وعلامة جرّه الفتحة الظاهرة'))), '')
check('M02 إفساد العبارة (مجرور ← منصوب) يُكشف',
      bool(mutated(lambda m: m[u_dayn]['inflection'].update(statement='اسم منصوب بـ«بِ» وعلامة نصبه الكسرة الظاهرة'))), '')
check('M03 إفساد هوية المعمول (تبادل سجلين) يُكشف',
      bool(mutated(lambda m: (m[u_dayn].__setitem__('inflection', copy.deepcopy(axes[u_kum]['inflection']))))), '')
check('M04 إفساد مقتضى العامل (جر ← نصب) يُكشف',
      bool(mutated(lambda m: m[u_dayn]['inflection']['governor'].update(expected='نصب'))), '')
check('M05 إفساد النص (دَيْنٍ ← دَيْنَ) يُكشف',
      bool(mutated(lambda m: m[u_dayn]['inflection'].update(text='دَيْنَ'))), '')
check('M06 عبارة إعرابٍ على وحدةٍ بلا اتفاق تُكشف',
      bool(mutated(lambda m: m[unit(o, 'يَأْبَ')[0]]['inflection'].update(statement='فعل مضارع منصوب وعلامة نصبه الفتحة الظاهرة'))), '')

# ٣ب فصل الأثر والمحلّ والعامل والوساطة، وأبعاد العلامة
_, ax = unit(o, 'كُمْ') if False else (None, axes[[u for u, l, t in o['tokens'] if t == 'كُمْ' and l == '2:282:120'][0]])
g = ax['inflection']['governor']
check('I20 «بِكُمْ»: القدرة اللفظية «جر» منفصلةٌ عن محلّ المعمول الأصلي في الجرد (رفع، نصب) وعن الوساطة',
      g['capacity'] == ['جر'] and set(g['capacity_mahall_of_complement']) == {'رفع', 'نصب'} and g['capacity_mediated'] == []
      and g['relation'] == 'مباشر' and ax['inflection']['effect']['mahalli'] == 'جر' and ax['inflection']['effect']['lafzi'] is None,
      (g['capacity'], g['capacity_mahall_of_complement'], g['relation'], ax['inflection']['effect']))
DIMS = [('فِي ٱلۡبَيۡتِ', 'الْبَيْتِ', ('حركة', 'ظاهرة', 'أصلية')), ('فِي ٱلۡبَيۡتَيۡنِ', 'الْبَيْتَيْنِ', ('حرف', 'ظاهرة', 'فرعية (نيابة)')),
        ('عَلَيۡهِ', 'هِ', (None, 'محلّي', None)), ('وَلۡيَتَّقِ ٱللَّهَ رَبَّهُۥ', 'يَتَّقِ', ('حذف', '—', 'فرعية (نيابة)')),
        ('إِلَّآ أَن تَكُونَ تِجَٰرَةً حَاضِرَةࣰ', 'تَكُونَ', ('حركة', 'ظاهرة', 'أصلية'))]
bad = []
for txt_, w_, exp_ in DIMS:
    _, _, _, oo = run(txt_)
    d_ = unit(oo, w_)[1]['inflection']['mark_dims'] or {}
    if (d_.get('carrier'), d_.get('visibility'), d_.get('originality')) != exp_:
        bad.append((w_, d_))
check('I21 أبعاد العلامة مستقلة (الحامل، الظهور، الأصالة) لشواهد الملحق', not bad, bad)
_, _, _, o5 = run('وَلۡيُمۡلِلِ ٱلَّذِي عَلَيۡهِ ٱلۡحَقُّ')
d5 = unit(o5, 'يُمْلِلِ')[1]['inflection']['mark_dims']
check('I22 «وَلۡيُمۡلِلِ»: السكون غير ظاهر، والكسرة حركة تخلّص لا علامة', d5['carrier'] == 'سكون' and d5['visibility'] == 'غير ظاهرة', d5)
_, _, _, o6 = run(verse_text(2, 102), '2:102')
i6 = unit(o6, 'يَقُولَا')[1]['inflection']
check('I23 «حَتَّىٰ يَقُولَآ»: النصب بوساطةٍ مذكورة في الجرد (أن مضمرة)، والعلاقة «بوساطة»',
      i6['agreement'] == 'AGREE' and i6['governor']['relation'] == 'بوساطة (في الجرد)' and 'مضمرة' in i6['statement'], (i6['agreement'], i6['statement']))
_, _, _, o7 = run(verse_text(2, 11), '2:11')
i7 = unit(o7, 'هُمْ')[1]['inflection']
check('I24 «لَهُمۡ»: القدرة من فئة العامل، ومعانيه المرفقة لا تذكرها: ملاحظة تعارضٍ داخلي ظاهرة',
      i7['governor']['capacity_source'].startswith('فئة العامل') and i7['notes'], (i7['governor'].get('capacity_source'), i7['notes']))

g55 = axes[[u for u, l, t in o['tokens'] if t == 'رِّجَالِ' and l == '2:282:55'][0]]['inflection']['governor']
check('I25 «مِنۡ»: محلّ المعمول في الجرد «الأصلي» لا «جر» (لا يُقرأ «المجرور» من نصّ الأثر حالةً)',
      g55['capacity_mahall_of_complement'] == ['الأصلي'], g55['capacity_mahall_of_complement'])
i98 = unit(o, 'تَكُونَ')[1]['inflection']
check('I26 «تَكُونَ»: لا ملاحظة «حركة العين» في وجهٍ متفق، والهوية المحمية تعرّف جذرها', 'حركة العين' not in (i98['cause'] or ''),
      i98['cause'])

# ٤ تأجيلٌ ومانع: لام التعليل لا تنصب (قدرتها الجر)، فالتعارض يُسجَّل ولا تُقال العبارة
_, _, _, o2 = run(verse_text(2, 143), '2:143')
_, ax = unit(o2, 'نَعْلَمَ')
i = ax['inflection']
check('I15 لِنَعلمَ: قدرة «لِ» الجر، والمسجَّل نصب ← CONFLICT بلا عبارة، موصوفٌ تعارضاً داخلياً بمرشّحات سببه لا خطأً لغوياً',
      i['agreement'] == 'CONFLICT' and i['statement'] is None and any('قدرة العامل' in c for c in i['conflicts'])
      and i['conflict_nature'] and i['conflict_nature'][0]['kind'] == 'INTERNAL' and len(i['conflict_nature'][0]['candidate_causes']) >= 2,
      (i['agreement'], i['conflicts'], i.get('conflict_nature')))
u6 = unit(o6, 'يَقُولَا')[0]
m6 = copy.deepcopy(o6['axes'])
m6[u6]['inflection']['governor']['capacity_mediated'] = []
check('M07 إفساد الوساطة (حذفها من سجل «حَتَّىٰ») يُكشف', bool(check_inflection(m6, o6['tokens'])), '')

print('ALL OK' if not FAIL else f'FAILED {len(FAIL)}: {FAIL}')
sys.exit(1 if FAIL else 0)
