#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
عقد النواة الاسمية والتعلّق (الإصدار المقترح ١): مصفوفة الاختبارات T01–T30 على واجهة المشروع الفعلية
(analyze ← الوحدات الجبرية ← السمات ← sarf.relations). لكل حالة: توقّع العقد، وما يُفحص فعلاً، والنتيجة:

    PASS     السلوك يوافق توقّع العقد
    DIFFERS  السلوك مخالفٌ لتوقّع العقد بسببٍ موثَّق (يُفحص السلوك الموثَّق نفسه، ويُعلن الخلاف)
    FAIL     لا هذا ولا ذاك

لا تُمرَّر القيم المتوقعة إلى المحلّل: المدخل نصٌّ مشكول وحده. والنتائج تُكتب في reports/nominal_nucleus_01/tests.json.

    PYTHONHASHSEED=0 python3 tests/test_relations.py
"""
import copy, json, os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
sys.path.insert(0, H + 'tools')
from sarf.root import hfn

RESULTS = []


def case(tid, inp, expectation, fn):
    try:
        status, got = fn()
    except Exception as e:                          # الاختبار نُفِّذ وانهار: فاشل، ويُسجَّل سببه
        status, got = 'FAIL', f'{type(e).__name__}: {e}'
    RESULTS.append(dict(id=tid, input=inp, contract_expectation=expectation, executed=True, result=status, observed=got))
    print(f'{status:<8} {tid} {inp} — {got if status != "PASS" else ""}'[:300])


if not hfn():
    print('HFN غير موجود: لا تُنفَّذ الاختبارات')
    sys.exit(0)

from sarf.catalog import Catalog
from sarf.analyze import analyze
from sarf.algebra import Trace, sentence_geo
from sarf.features import unit_features
from sarf.relations import verse_relations, check_records, LICENSED, DEFERRED, REJECTED, SEARCH_INCOMPLETE

CAT = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])


def run(text, ref='t'):
    a = analyze(CAT, text)
    _, U = sentence_geo(a, ref, Trace())
    F = unit_features(a, U)
    out = verse_relations(a, U, F, ref)
    return a, U, F, out


def recs(out, typ=None, rule=None):
    return [r for r in out['records'] if (typ is None or r['type'] == typ) and (rule is None or r['rule_id'] == rule)]


def one(out, typ, **texts):
    for r in recs(out, typ):
        if all(r['texts'].get(k) == v for k, v in texts.items()):
            return r
    return None


def ok(cond, got=''):
    return ('PASS' if cond else 'FAIL'), got


Q282 = next(l.split('\t')[2].strip() for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8') if l.startswith('2\t282\t'))
A282, U282, F282, R282 = run(Q282, '2:282')


def t01():
    _, _, _, o = run('زَيۡدٌ قَائِمٌ')
    r = one(o, 'PREDICATION', subject='زَيْدٌ', predicate='قَائِمٌ')
    _, _, _, o2 = run('ٱلرَّجُلُ قَائِمٌ')
    r2 = one(o2, 'PREDICATION', subject='الرَّجُلُ', predicate='قَائِمٌ')
    if r and r['status'] == DEFERRED and 'أهلية الابتداء' in r['reason'] and r2 and r2['status'] == LICENSED and not r2['boundary_proven']:
        return 'DIFFERS', ('«زَيْدٌ» نكرةٌ بالتنوين ولا جرد أعلامٍ يثبت علميته: N01 مؤجَّل (أهلية الابتداء)؛ '
                           'والنمط نفسه بمعرفةٍ مثبتة «الرَّجُلُ قَائِمٌ» مرخَّص بلا شهادة حدّ')
    return 'FAIL', (r, r2)


def t02():
    _, _, _, o = run('فِي ٱلدَّارِ رَجُلٌ')
    pp = one(o, 'PP')
    n = one(o, 'PREDICATIVE_PP', subject='رَجُلٌ')
    return ok(pp and pp['status'] == LICENSED and n and n['status'] == LICENSED and not n['boundary_proven'] and
              not n['sentence_closed'], (pp and pp['status'], n and n['status']))


def t03():
    _, _, _, o = run('زَيۡدٌ فِي ٱلدَّارِ')
    n = one(o, 'PREDICATIVE_PP', subject='زَيْدٌ')
    _, _, _, o2 = run('ٱلرَّجُلُ فِي ٱلدَّارِ')
    n2 = one(o2, 'PREDICATIVE_PP', subject='الرَّجُلُ')
    if n and n['status'] == DEFERRED and n2 and n2['status'] == LICENSED:
        return 'DIFFERS', '«زَيْدٌ» بلا دليل علمية: N02 مؤجَّل؛ و«ٱلرَّجُلُ فِي ٱلدَّارِ» مرخَّص بـN02'
    return ok(n and n['status'] == LICENSED, (n, n2))


def t04():
    _, _, _, o = run('ٱللَّهُ ٱلصَّمَدُ')
    r = one(o, 'PREDICATION', subject='اللَّهُ')
    return ok(r is not None and r['status'] == DEFERRED and 'خارج تغطية' in r['reason'], r and (r['status'], r['reason']))


def t05():
    _, _, _, o = run('زَيۡدٌ')
    r = one(o, 'PREDICATION', subject='زَيْدٌ')
    return ok(r and r['status'] == DEFERRED and 'predicate' not in r['heads'] and not r['sentence_closed'], r and r['reason'])


def t06():
    _, _, _, o = run('زَيۡدٌ قَائِمًا')
    r = one(o, 'PREDICATION', subject='زَيْدٌ', predicate='قَائِمًا')
    return ok(r and r['status'] == REJECTED and 'ولا يُحكم على النص كله' in r['reason'] and
              not any(x['status'] == REJECTED for x in o['records'] if x is not r), r and r['reason'])


def t07():
    _, _, _, o = run('كَانَ زَيۡدٌ قَائِمًا')
    v = one(o, 'NASIKH', nasikh='كَانَ', ism='زَيْدٌ', khabar='قَائِمًا')
    return ok(v and v['status'] == LICENSED and not recs(o, 'PREDICATION'), v and v['status'])


def t08():
    _, _, _, o = run('إِنَّ زَيۡدًا قَائِمٌ')
    v = one(o, 'NASIKH', nasikh='إِنَّ', ism='زَيْدًا', khabar='قَائِمٌ')
    return ok(v and v['status'] == LICENSED and not recs(o, 'PREDICATION'), v and v['status'])


def t09():
    _, _, _, o = run('ٱلَّذِي عَلَيۡهِ ٱلۡحَقُّ')
    c = one(o, 'CONTAINER_RELATIVE', relative='الَّذِي')
    n = one(o, 'PREDICATIVE_PP', subject='الْحَقُّ')
    pp = one(o, 'PP', complement='هِ')
    rs = recs(o, 'RESUMPTIVE')
    return ok(c and c['status'] == LICENSED and n and n['container_id'] == c['relation_id'] and
              pp and any('محلاً' in p for p in pp['premises']) and len(rs) == 1 and rs[0]['relation_id'] != n['relation_id'],
              dict(container=c and c['status'], nucleus=n and n['status'], resumptive=rs and rs[0]['status']))


def t10():
    _, _, _, o = run('فَإِن كَانَ ٱلَّذِي عَلَيۡهِ ٱلۡحَقُّ سَفِيهًا')
    c = one(o, 'CONTAINER_RELATIVE', relative='الَّذِي')
    v = one(o, 'NASIKH', nasikh='كَانَ')
    ext = set(c['extent']) if c else set()
    kh = v and v['heads'].get('khabar')
    return ok(c and kh and kh not in ext and v['texts'].get('khabar') == 'سَفِيهًا' and c['relation_id'] in v['premises'],
              dict(extent=c and c['texts'], khabar=v and v['texts'].get('khabar')))


def t11():
    _, _, _, o = run('فَلَيۡسَ عَلَيۡكُمۡ جُنَاحٌ')
    v = one(o, 'NASIKH', nasikh='لَيْسَ', ism='جُنَاحٌ')
    return ok(v and v['status'] == LICENSED and v['texts'].get('khabar') == 'عَلَيْ كُمْ' and not v['sentence_closed'] and
              not recs(o, 'PREDICATION'), v and (v['status'], v['texts']))


def t12():
    a, _, _, o = run('وَٱللَّهُ بِكُلِّ شَيۡءٍ عَلِيمٌ')
    n = one(o, 'PREDICATION', subject='اللَّهُ', predicate='عَلِيمٌ')
    at = recs(o, 'ATTACH')
    hosts = [h['host_text'] for x in at for h in x['alternatives']]
    no_root = not any(m.get('status') == 'accepted' for m in a['morph'] if a['segments'][m['word_index']]['word'].endswith('للَّهُ'))
    return ok(n and n['status'] == LICENSED and n['nucleus_complete'] and at and 'عَلِيمٌ' in hosts and
              at[0]['status'] == DEFERRED and no_root, dict(nucleus=n and n['status'], hosts=hosts))


def t13():
    _, _, _, o = run('ذَٰلِكُمۡ أَقۡسَطُ عِندَ ٱللَّهِ')
    adv = one(o, 'ADVP', adverb='عِنْدَ')
    n = one(o, 'PREDICATION', subject='ذَٰلِكُمْ')
    at = recs(o, 'ATTACH')
    return ok(adv and adv['status'] == LICENSED and not one(o, 'PP') and n and at and
              n['relation_id'] != at[0]['relation_id'], dict(advp=adv and adv['status'], nucleus=n and (n['status'], n['reason'][:80])))


def t14():
    _, _, _, o = run('مَرَرۡتُ بِرَجُلٍ فِي ٱلدَّارِ')
    at = next((x for x in recs(o, 'ATTACH') if x['texts']['oblique'] == 'فِي الدَّارِ'), None)
    kinds = [h['host_kind'] for h in (at or {}).get('alternatives', [])]
    return ok(at and at['status'] == DEFERRED and len(kinds) >= 2 and any('نعت' in k for k in kinds) and any(k == 'فعل' for k in kinds),
              kinds)


def t15():
    _, _, _, o = run('مُحَمَّدٌ أَخُوهُ حَاضِرٌ')
    lic = [r for r in recs(o, 'PREDICATION') if r['status'] == LICENSED]
    return ok(not lic, [r['texts'] for r in recs(o, 'PREDICATION')])


def t16():
    bad = [(U282[k].O['text'], U282[k].O.get('deferred')) for k in ((52, 0), (58, 0), (60, 1))
           if 'لم تثبت الاسمية' in str(U282[k].O.get('deferred'))]
    return ok(not bad and all(F282[k]['pos']['v'] == 'اسم' for k in ((52, 0), (58, 0), (60, 1))), bad)


def t17():
    g81, g107 = U282[(80, 0)], U282[(106, 0)]
    return ok(g81.closed and g81.Theta.get('R') == 'كتب' and g107.closed and g107.Theta.get('R') == 'كتب' and
              F282[(80, 0)]['pos']['v'] == 'فعل', ((g81.closed, g81.Theta.get('R')), (g107.closed, g107.Theta.get('R'))))


def t18():
    _, _, _, o = run('هُوَ قَائِمٌ')
    r = one(o, 'PREDICATION', subject='هُوَ', predicate='قَائِمٌ')
    return ok(r and r['status'] == LICENSED and any('المحلّ' in p for p in r['premises']), r and r['premises'])


def t19():
    _, _, _, o = run('رَجُلٌ قَائِمٌ')
    r = one(o, 'PREDICATION', subject='رَجُلٌ')
    if r and r['status'] != LICENSED and any('التنوين' in p for p in r['premises']):
        return 'DIFFERS', ('الاسمية في المشروع تثبت بالتنوين المكتوب (حكمٌ قائم في sarf.features)، والعقد يمنعه شاهداً وحده: '
                           'تعارضٌ معروض على صاحب النظرية؛ والدليل ظاهرٌ في المقدّمات، والإسناد غير مرخَّص هنا')
    return ok(False, r)


def t20():
    r = copy.deepcopy(next(x for x in R282['records'] if x['type'] == 'PREDICATIVE_PP'))
    r['members']['subject'] = [R282['tokens'][0][0]]
    r['positions']['subject'] = [R282['tokens'][0][1]]
    e = check_records([r], R282['tokens'])
    return ok(any('ليس من أعضاء طرفه' in x for x in e), e)


def t21():
    cs = [x for x in R282['records'] if x['type'] == 'CONTAINER_RELATIVE']
    n = copy.deepcopy(next(x for x in R282['records'] if x['type'] == 'PREDICATIVE_PP' and x['container_id'] == cs[0]['relation_id']))
    n['container_id'] = cs[1]['relation_id']
    e = check_records(cs + [n], R282['tokens'])
    return ok(len(cs) == 2 and any('خارج امتداد حاويته' in x for x in e), e[:2])


def t22():
    base = copy.deepcopy(next(x for x in R282['records'] if x['type'] == 'PP'))
    a_, b_ = copy.deepcopy(base), copy.deepcopy(base)
    a_['relation_id'], b_['relation_id'] = 'X1', 'X2'
    a_['premises'], b_['premises'] = ['X2'], ['X1']
    e = check_records([a_, b_], R282['tokens'])
    return ok(any('برهانٌ دائري' in x for x in e) and any('بلا حقيقةٍ مصدرية' in x for x in e), e[:3])


def t23():
    one_host = [x for x in R282['records'] if x['type'] == 'ATTACH' and len(x['alternatives']) == 1]
    return ok(one_host and all(x['status'] == DEFERRED and x['search_status'] == SEARCH_INCOMPLETE and
                               x['selected_analysis'] is None for x in one_host), len(one_host))


def t24():
    cs = [x for x in R282['records'] if x['type'] == 'CONTAINER_RELATIVE']
    ids = {x['relation_id'] for x in cs}
    heads = {x['heads']['relative'] for x in cs}
    sw = copy.deepcopy(cs)
    sw[0]['positions']['relative'], sw[1]['positions']['relative'] = sw[1]['positions']['relative'], sw[0]['positions']['relative']
    e = check_records(sw, R282['tokens'])
    return ok(len(cs) == 2 and len(ids) == 2 and len(heads) == 2 and any('لا يوافق المصدر' in x for x in e),
              dict(positions=[x['positions']['relative'] for x in cs], detected=len(e)))


def t25():
    from sarf.normalize_trace import normalize_traced
    a = normalize_traced('إِلَىٰ')['analysis']
    b = normalize_traced('ذَٰلِكَ')['analysis']
    return ok(a == 'إِلَى' and 'ٰ' in b, (a, b))


def t26():
    _, _, _, o = run('وَٱللَّهُ بِكُلِّ شَيۡءٍ عَلِيمٌ')
    n = one(o, 'PREDICATION', subject='اللَّهُ')
    return ok(n and n['nucleus_complete'] is True and n['clause_complete'] is not True and recs(o, 'ATTACH')[0]['status'] == DEFERRED,
              n and (n['nucleus_complete'], n['clause_complete']))


def t27():
    last = [x for x in R282['records'] if any(p.endswith(':128') for ps in x['positions'].values() for p in ps)]
    return ok(last and all(not x['boundary_proven'] and not x['sentence_closed'] for x in last), [x['type'] for x in last])


def t28():
    pp = [x for x in R282['records'] if x['type'] == 'PP' and x['texts'].get('complement') == 'هِ']
    return ok(pp and all(x['status'] == LICENSED for x in pp), [x['texts'] for x in pp])


def t29():
    import snapshot_outputs as so
    A = {'1:1': {'a': {'morph': [{'status': 'accepted', 'root': 'كتب'}]}}}
    B = copy.deepcopy(A)
    B['1:1']['a']['morph'][0]['status'] = 'deferred'
    B['1:1']['a']['extra'] = [1, 2, 3]
    v, ad = so.compare(A, B)
    return ok(len(v) == 1 and ad, (v, dict(ad)))


def t30():
    at = [x for x in R282['records'] if x['type'] == 'ATTACH']
    return ok(at and all(x['search_status'] == SEARCH_INCOMPLETE and x['status'] != REJECTED for x in at), len(at))


for tid, inp, exp, fn in [
        ('T01', 'زيدٌ قائمٌ', 'إسناد اسمي محلي؛ لا شهادة حد', t01),
        ('T02', 'في الدار رجلٌ', 'PP ونواة في الوجه الخبري', t02),
        ('T03', 'زيدٌ في الدار', 'نواة بخبر شبه جملة (N02)', t03),
        ('T04', 'الله الصمد', 'لا رفض لتعريف الخبر؛ قاعدة أو تأجيل', t04),
        ('T05', 'زيدٌ', 'مسند إليه محتمل؛ لا خبر ولا إغلاق', t05),
        ('T06', 'زيدٌ قائمًا', 'رفض مرشّح الخبر المرفوع وحده', t06),
        ('T07', 'كان زيدٌ قائمًا', 'وصلة ناسخ؛ لا مبتدأ وخبر', t07),
        ('T08', 'إن زيدًا قائمٌ', 'اسم إن وخبرها', t08),
        ('T09', 'الذي عليه الحق', 'نواة في الصلة؛ الهاء محل جر؛ العائد مستقل', t09),
        ('T10', 'كان الذي عليه الحق سفيهًا', 'الصلة لا تبتلع سفيهًا؛ خبر كان', t10),
        ('T11', 'فليس عليكم جناح', 'وصلة ليس أو تأجيل محدد؛ لا إغلاق', t11),
        ('T12', 'والله بكل شيء عليم', 'نواة محلية، والتعلق مستقل؛ لا جذر للفظ الجلالة', t12),
        ('T13', 'ذلكم أقسط عند الله', 'الإسناد غير التعلق؛ عند ظرف لا جار', t13),
        ('T14', 'مررت برجل في الدار', 'حفظ بدائل التعلق والوصف', t14),
        ('T15', 'محمدٌ أخوه حاضرٌ', 'لا وصل آلي لأول اسمين', t15),
        ('T16', 'شهيدين / رجلين / امرأتان', 'مصالحة الاسمية مع سبب الإغلاق', t16),
        ('T17', 'تكتبوه / تكتبوها', 'مصالحة الفعلية مع الوصف القديم', t17),
        ('T18', 'اسم مبني في محل رفع', 'دليل المحل كافٍ', t18),
        ('T19', 'تنوين بلا وظيفة معيّنة', 'لا اسمية من الشكل وحده', t19),
        ('T20', 'إزاحة كلمة من طرف', 'كشف عدم احتواء الرأس', t20),
        ('T21', 'نقل علاقة إلى حاوية مجاورة', 'كشف العبور', t21),
        ('T22', 'برهان دائري', 'لا ترخيص نهائي', t22),
        ('T23', 'مرشح واحد وبحث ناقص', 'DEFERRED للانفراد', t23),
        ('T24', 'تكرار اللفظ في موضعين', 'هويتان مختلفتان', t24),
        ('T25', 'ىٰ / خنجرية على غير ى', 'حذف في الأولى فقط', t25),
        ('T26', 'نواة مكتملة ومتعلّق مؤجَّل', 'nucleus_complete دون clause_complete', t26),
        ('T27', 'نهاية آية مع التزام مفتوح', 'حد مصدر لا اكتمال', t27),
        ('T28', 'عليه بمعنى غير محسوم', 'PP يُبنى بمقدماته', t28),
        ('T29', 'مثبت قديم فُقد', 'يظهر في المقارنة', t29),
        ('T30', 'توقف البحث', 'SEARCH_INCOMPLETE لا رفض', t30)]:
    case(tid, inp, exp, fn)

os.makedirs(H + 'reports/nominal_nucleus_01', exist_ok=True)
json.dump(RESULTS, open(H + 'reports/nominal_nucleus_01/tests.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
n = {k: sum(r['result'] == k for r in RESULTS) for k in ('PASS', 'DIFFERS', 'FAIL')}
print(n)
print('ALL OK' if not n['FAIL'] else f'FAILED {n["FAIL"]}')
sys.exit(1 if n['FAIL'] else 0)
