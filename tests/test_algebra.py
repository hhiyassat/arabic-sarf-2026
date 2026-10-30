#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
الجبر اللساني: التعريفات والمبرهنات على أمثلة بعينها (تجربة على الفرع experiment).

    python3 tests/test_algebra.py
"""
import os, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/'
sys.path.insert(0, H)
from sarf.algebra import (Trace, Geo, Evidence, Obligation, CloseError, extend, close, cells_of, render_cells,
                          syllabify, cv, align_alpha, flatten, equal_under, proj_root, proj_cells, sentence_geo,
                          render_sentence, SENTENCE, UNIT)
from sarf.root import hfn

bad = 0
def check(name, ok, got=''):
    global bad
    bad += not ok
    print('OK ' if ok else 'BAD', name, '' if ok else got)

T = Trace()

# الخلايا وβ: كَتَّبَ = ⟨ك,a⟩⟨ت,∅⟩⟨ت,a⟩⟨ب,a⟩، والمقاطع كَتْ.تَ.بَ
cells, _ = cells_of('كَتَّبَ', 'k')
check('Cells(كَتَّبَ)', [c.key() for c in cells] == [('ك', 'a', 1), ('ت', '∅', 1), ('ت', 'a', 1), ('ب', 'a', 1)],
      [c.show() for c in cells])
S, stray = syllabify(cells, 'k', T)
check('β(كَتَّبَ) = كَتْ.تَ.بَ', [cv(x) for x in S] == ['CVC', 'CV', 'CV'] and not stray, [cv(x) for x in S])
check('Flatten(β) = الخلايا', [c for x in S for c in x.A] == cells)
check('خليتا الشدة وقوعان مختلفان من موضع رسم واحد',
      cells[1].id != cells[2].id and cells[1].O['tok'] == cells[2].O['tok'])
# α: ⟨r1, r2, r2, r3⟩
alpha, ops = align_alpha(cells, 'كتب', 'II', 'madi')
check('α(كَتَّبَ) = ⟨r1, r2, r2, r3⟩', alpha == ['r1', 'r2', 'r2', 'r3'], alpha)
# كَاتَبَ: الألف طول في القالب
c2, _ = cells_of('كَاتَبَ', 'k2')
alpha2, _ = align_alpha(c2, 'كتب', 'III', 'madi')
check('α(كَاتَبَ) = ⟨r1, r2, r3⟩ والألف طولُ r1', alpha2 == ['r1', 'r2', 'r3'] and c2[0].L == 2, alpha2)
check('كَتَبَ لا يطابق قالب فَاعَلَ (لا طول)', align_alpha(cells_of('كَتَبَ', 'k3')[0], 'كتب', 'III', 'madi')[0] is None)

# المساواة من جهة: Root(كَتَبَ) = Root(كَاتَبَ)، والخلايا مختلفة
g1 = Geo('a', (UNIT, 't'), A=cells_of('كَتَبَ', 'a')[0], Theta=dict(R='كتب'))
g2 = Geo('b', (UNIT, 't'), A=c2, Theta=dict(R='كتب'))
check('Root(كَتَبَ) = Root(كَاتَبَ)', equal_under(proj_root, g1, g2))
check('Cells(كَتَبَ) ≠ Cells(كَاتَبَ)', not equal_under(proj_cells, g1, g2))

# المبرهنة الرابعة: لا إغلاق بلا شهادتين، ولا مع التزام لازم مفتوح، ولا امتداد بلا دليل
G = Geo('g', (UNIT, 't'), Omega=[Obligation('هوية اللفظ')])
for name, fn in [('إغلاق بلا شهادة حدّ', lambda: close(G, Evidence('x', ['y']), None, T)),
                 ('إغلاق مع التزام لازم مفتوح', lambda: close(G, Evidence('x', ['y']), Evidence('z', ['w']), T)),
                 ('امتداد بلا سبب', lambda: extend(G, cells[0], None, Evidence(''), T)),
                 ('امتداد بوحدة غير مغلقة', lambda: extend(G, Geo('h', (UNIT, 't')), 'r', Evidence('x', ['y']), T))]:
    try:
        fn()
        check(name + ': مرفوض', False, 'قُبل')
    except CloseError:
        check(name + ': مرفوض', True)

# Render: الرسم يعود كما كان، والحرف الذي لا يُنطق يحفظه O
for w in ['ٱلصَّلَوٰةَ', 'قَالُوا', 'يُسْرًا', 'مُّسَمًّى', 'السَّمِيعُ']:
    from sarf.normalize import uthmani_normalize
    t = uthmani_normalize(w)
    cs, _ = cells_of(t, 'r')
    check(f'Render(Cells({t})) = {t}', render_cells(cs, t)[0] == t, render_cells(cs, t)[0])
check('ٱلصَّلَوٰةَ: الواو كرسيّ ألف، فاللام طويلة',
      [c.show() for c in cells_of(uthmani_normalize('ٱلصَّلَوٰةَ'), 'r')[0]][3] == '⟨ل,aː⟩')

# في الآية: لَمۡ يَلِدۡ وَلَمۡ يُولَدۡ تُغلق جملةً، وRender يعيدها
if hfn():
    from sarf.analyze import analyze
    from sarf.catalog import Catalog
    cat = Catalog([H + 'operators_catalog.jsonl', H + 'operators_catalog_split_vocalized.csv'])
    a = analyze(cat, 'لَمْ يَلِدْ وَلَمْ يُولَدْ')
    Sg, units = sentence_geo(a, 'Q112:3', Trace())
    check('لَمۡ يَلِدۡ وَلَمۡ يُولَدۡ: الجملة مغلقة', Sg.closed and Sg.level == SENTENCE,
          [o.name for o in Sg.open_required()])
    check('Render(الآية) = النص', render_sentence(Sg, units) == a['normalized'])
    rel = sorted(b[0] for b in Sg.B)
    check('علاقاتها: جزمان وإسنادان', rel.count('إسناد') == 2 and sum('مجزوم' in r for r in rel) == 2, rel)
    a = analyze(cat, 'فَلْيَكْتُبْ بَّيْنَكُمْ كَاتِبٌۢ بِٱلْعَدْلِ')
    Sg, units = sentence_geo(a, 'v', Trace())
    k = next(G for G in units.values() if G.O['text'] == 'كَاتِبٌ')
    check('كَاتِبٌ = Realize(ك ت ب، اسم فاعل من فَعَلَ)', k.closed and k.Theta['R'] == 'كتب' and 'فاعل' in k.Theta['P'],
          k.O.get('deferred'))
    check('ما لم يُغلق محفوظ: كل خلية يبلغها البناء',
          {c.id for c in flatten(Sg)} == {c.id for G in units.values() for c in G.O['cells']})
    check('والجملة غير المكتملة مؤجَّلة لا مغلقة', not Sg.closed and Sg.open_required())
# اسم الفاعل من الأجوف: «يعتلّ باعتلال فعله» — الهمزة بدلٌ من العين إن كان الفعل معلّ العين
if hfn():
    from sarf.algebra import participle_analyses, sibawayh_analyses, _verb_ilal
    H_ = hfn()
    check('قَامَ معلّ العين، فقَائِم يحتمل «ق و م»', _verb_ilal(H_, 'قوم') in ('معلّ', 'كلاهما') and
          'قوم' in {p[0] for p in participle_analyses(cells_of('قَائِمٌ', 'q')[0])})
    check('عَاوِر: العين صحيحة لأن الفعل عَوِرَ صحيح العين', {p[0] for p in participle_analyses(cells_of('عَاوِرٌ', 'q')[0])} == {'عور'})
    check('كَاتِب لا همزة فيه فلا أجوف', {p[0] for p in participle_analyses(cells_of('كَاتِبٌ', 'q')[0])} == {'كتب'})
    # أبنية سيبويه للاسم
    for w, root, pat in [('كِتَابٌ', 'كتب', 'فِعَالٌ'), ('رَبِّ', 'ربب', 'فَعْلٌ'), ('أَزْوَٰجًا', 'زوج', 'أَفْعَالٌ')]:
        r = sibawayh_analyses(cells_of(w, 's')[0])
        check(f'{w} = Realize({root}, {pat}) من أبنية سيبويه', {x[0] for x in r} == {root} and pat in {x[3] for x in r},
              [(x[0], x[3]) for x in r])
# الطبقتان: الآية وحدة مصحفية ثابتة، والجملة وحدة لغوية؛ ونهاية الآية لا تُغلق الجملة
if hfn():
    from sarf.algebra import linguistic_layer, mushaf_layer, waqf_of
    rows = {(int(x[0]), int(x[1])): x[2] for x in (l.rstrip('\n').split('\t') for l in open(H + 'data/quran_hafs.tsv', encoding='utf-8'))} \
        if os.path.exists(H + 'data/quran_hafs.tsv') else {}
    def layers(refs):
        from sarf.algebra import cross_ayah_links
        T_ = Trace(); items = []; cr = []; prev_ = None
        for s_, v_ in refs:
            a = analyze(cat, rows[(s_, v_)])
            S_, u_ = sentence_geo(a, f'Q{s_}:{v_}', T_)
            items.append((s_, v_, a, u_, S_))
            cur_ = dict(s=s_, v=v_, text=rows[(s_, v_)], a=a, units=u_, S=S_)
            if prev_ and prev_['s'] == s_:
                cr += cross_ayah_links(lambda t: analyze(cat, t), prev_, cur_)
            prev_ = cur_
        return mushaf_layer([x[:4] for x in items], T_), linguistic_layer(items, T_, cross=cr)[:2]
    if rows:
        MU, (LT, st) = layers([(37, 137), (37, 138)])
        D0 = (LT[0].A + LT[0].O['pending'])[0]
        check('الصافات ١٣٧–١٣٨: وحدة خطابية تعبر حدّ الآية إلى «وَبِٱلَّيۡلِۚ»',
              D0.O['ayahs'] == [(37, 137), (37, 138)] and D0.O['location'][-1] == (37, 138, 0), D0.O['location'])
        check('والآيتان مغلقتان في الطبقة المصحفية', MU.closed and all(ay.closed for su in MU.A for ay in su.A))
        check('نهاية الآية ١٣٧ ليست حدّاً: لا علامة وقف عليها', waqf_of(rows[(37, 137)])[-1] is None)
        MU, (LT, st) = layers([(2, 282)])
        Ds = LT[0].A + LT[0].O['pending']
        check('البقرة ٢٨٢: الحدود من الخانات (ما له الصدارة، والواو والفاء بعد جملة تامّة)، لا من العلامات',
              len(Ds) > 1 and MU.closed and all(D.O['boundary'].get('J') == 'proven' for D in Ds), len(Ds))
        check('ولا رابطة تعبر حدّ وحدة خطابية', st['bond_cross_du'] == 0, st)
# سجل الحدّ B(b | a, q, c) = ⟨F, L, M, W, I, E⟩: جواز الوقف لا يساوي انغلاق العلاقة
if hfn() and rows:
    def recs(refs):
        T_ = Trace(); items = []
        for s_, v_ in refs:
            a = analyze(cat, rows[(s_, v_)])
            S_, u_ = sentence_geo(a, f'Q{s_}:{v_}', T_)
            items.append((s_, v_, a, u_, S_))
        return linguistic_layer(items, T_, 'test')[2]
    R = recs([(2, 282)])
    at = {r['location'][2]: r for r in R}
    # موضع الكلمة قبل «وَٱتَّقُواْ» (لا رقمٌ ثابت: دمج «مُّسَمࣰّ ى» كلمةً واحدة يغيّر الترقيم)
    i282 = [s_['word'] for s_ in analyze(cat, rows[(2, 282)])['segments']].index('وَاتَّقُوا') - 1
    check('البقرة ٢٨٢: قبل «وَٱتَّقُواْ» نهاية جملة قبل الواو (حكم صاحب النظرية)، وما بعدها بدائل محفوظة',
          at.get(i282, {}).get('J') == 'proven' and at[i282]['J_why'].startswith('نهاية جملة قبل الواو'), at.get(i282))
    at98 = {r['location'][2]: r for r in recs([(37, 98)])}
    check('الصافات ٩٨: «فَأَرَادُواْ بِهِۦ كَيۡدࣰا» جملة صحيحة تنتهي قبل الفاء الملتصقة بـ«فَجَعَلۡنَٰهُمُ»',
          at98.get(2, {}).get('J') == 'proven' and at98[2]['J_why'].startswith('نهاية جملة قبل الفاء'), at98.get(2))
    ato = {r['location'][2]: r for r in recs([(2, 74)])}
    check('البقرة ٧٤: نهاية الجملة قبل «أَوۡ» مقبولة (فَهِيَ كَٱلۡحِجَارَةِ ‖ أَوۡ أَشَدُّ قَسۡوَةࣰ)',
          any(r['J'] == 'proven' and '«أو»' in r['J_why'] for r in ato.values()), [(k, r['J'], r['J_why'][:30]) for k, r in ato.items()])
    def ends(ref):
        return {r['location'][2]: r for r in recs([ref])}
    e = ends((17, 49))
    check('الإسراء ٤٩: «عِظَٰمࣰا ‖ وَرُفَٰتًا» اسمٌ معطوف على مفرد، ليس جملة: لا حدّ', e.get(3, {}).get('J') != 'proven',
          [(k, r['J'], r['J_why'][:25]) for k, r in e.items()])
    e = ends((18, 29))
    check('الكهف ٢٩: «وَمَن شَآءَ ‖ فَلۡيَكۡفُرۡ» فاء الجواب: لا حدّ ثابت',
          not any(r['J'] == 'proven' and 'الفاء' in r['J_why'] and 'فَلْيَكْفُرْ' in str(r) for r in e.values()) and
          all(r['J'] != 'proven' for k, r in e.items() if r['J_why'].startswith('نهاية جملة قبل الفاء') and k in (8, 9)),
          [(k, r['J'], r['J_why'][:25]) for k, r in e.items()])
    e = ends((17, 103))
    check('الإسراء ١٠٣: «فَأَغۡرَقۡنَٰهُ ‖ وَمَن مَّعَهُۥ» معطوفٌ على المفعول، ليس جملة: لا حدّ', e.get(5, {}).get('J') != 'proven',
          [(k, r['J'], r['J_why'][:25]) for k, r in e.items()])
    e = ends((6, 46))
    check('الأنعام ٤٦: «ثُمَّ» كالفاء: نهاية جملة قبلها وما بعدها جملة (ثُمَّ هُمۡ يَصۡدِفُونَ)',
          e.get(19, {}).get('J') == 'proven' and '«ثُمَّ»' in e[19]['J_why'], e.get(19))
    e = ends((26, 158))
    check('الشعراء ١٥٨: نفيٌ بعد العاطف يبدأ جملة (لَأٓيَةࣰ ‖ وَمَا كَانَ)', e.get(5, {}).get('J') == 'proven', e.get(5))
    e = ends((27, 58))
    check('النمل ٥٨: فعلُ الذمّ العامل بعد الفاء يبدأ جملة (مَّطَرࣰا ‖ فَسَآءَ)', e.get(2, {}).get('J') == 'proven', e.get(2))
    e = ends((27, 92))
    check('النمل ٩٢: الشرط وجوابه مكوّنٌ واحد: لا حدّ بين «فَمَنِ» وفعلها، ولا قبل فاء الجواب الرابطة (فَمَنِ ٱهۡتَدَىٰ فَإِنَّمَا)',
          e.get(3, {}).get('J') is None and e.get(4, {}).get('J') is None, [(k, r['J']) for k, r in e.items()])
    def structs(ref):
        recs([ref])
        return linguistic_layer.samples
    sm = structs((2, 274))
    r0 = sm['rel'][0] if sm['rel'] else {}
    check('البقرة ٢٧٤: «ٱلَّذِينَ يُنفِقُونَ» صلةٌ فعلية، والعائد فاعلها المطابق (هم)',
          r0.get('silah') == 'جملة فعلية' and all(o[1] for o in r0.get('obligations', [])), r0)
    e = ends((2, 23))
    check('البقرة ٢٣: «وَإِن كُنتُمۡ … فَأۡتُواْ»: الفاء رابطة الجواب، فلا حدّ قبلها', e.get(7, {}).get('J') is None,
          [(k, r['J'], r['J_why'][:20]) for k, r in e.items()])
    sm = structs((2, 20))
    lw = [x for x in sm['cond'] if x['tool'] == 'لَوْ']
    check('البقرة ٢٠: جواب «لَوۡ» باللام المفتوحة على الماضي (لَذَهَبَ)', lw and lw[0]['obligations'][1][1], lw)
    sm = structs((2, 11))
    iz = [x for x in sm['cond'] if x['tool'] == 'إِذَا']
    check('البقرة ١١: «وَإِذَا قِيلَ لَهُمۡ … قَالُوٓاْ»: جواب «إذا» ماضٍ بعد جملة الشرط (حكم صاحب النظرية)',
          iz and iz[0]['obligations'][1][1] and 'قَالُوا' in iz[0]['text'], iz)
    # مراجعة التقرير (٥): رأس جملة الشرط يلي الأداة، لا فعلٌ داخل المقول ولا الجواب نفسه
    check('البقرة ١١: فعل الشرط «قِيلَ»، لا «تُفۡسِدُواْ» داخل المقول',
          iz and iz[0]['obligations'][0][2].startswith('«قِيلَ»'), iz and iz[0]['obligations'])
    sm = structs((2, 20))
    iz = [x for x in sm['cond'] if x['tool'] == 'إِذَا']
    check('البقرة ٢٠: «وَإِذَآ أَظۡلَمَ عَلَيۡهِمۡ قَامُواْ»: الشرط «أَظۡلَمَ»، والجواب «قَامُواْ»',
          iz and iz[0]['obligations'][0][2].startswith('«أَظْلَمَ»') and iz[0]['obligations'][1][1] and
          'قَامُوا' in iz[0]['text'], iz and iz[0]['obligations'])
    sm = structs((2, 9))
    check('البقرة ٩: «وَمَا يَخۡدَعُونَ»: «ما» نافية، والمضارع مرفوعٌ بثبوت النون، فلا شرط',
          not [x for x in sm['cond'] if 'مَا' in x['tool']], sm['cond'])
    # مراجعة التقرير (٦، ٧): الخبر الجملي نواةٌ مرتبطة لا مشكلة حدود؛ وطرفا عطف الجملة معيَّنان؛ وشبه الجملة المعطوف مفرد
    MU, (LT, st_) = layers([(2, 52)])
    Js = [J for D in LT[0].A + LT[0].O['pending'] for J in D.A + D.O['pending']]
    jl = next((J for J in Js if any(x.startswith('ناسخ') for x in J.O.get('nuclei', []))), None)
    check('البقرة ٥٢: «لَعَلَّكُمۡ تَشۡكُرُونَ»: «تَشۡكُرُونَ» خبر «لعل» مرتبط، فلا التزام بحدود الجمل',
          jl is not None and any(b.startswith('خبر «') for _, b in jl.O.get('bound', [])) and
          not any(o.name in ('حدود الجمل', 'نوى غير مرتبطة') for o in jl.Omega), jl and (jl.O.get('bound'), [o.name for o in jl.Omega]))
    sm = structs((2, 8))
    cy = [x for x in sm['coord'] if x['B'].startswith('وَبِالْيَوْم')]
    check('البقرة ٨: «وَبِٱلۡيَوۡمِ ٱلۡأٓخِرِ» جارٌّ ومجرور معطوفٌ مفرد (على «بِٱللَّهِ»)، لا جملة', cy and cy[0]['level'] == 'مفرد', cy)
    sm = structs((2, 3))
    cj = [x for x in sm['coord'] if x['level'] == 'جملة']
    check('البقرة ٣: عطف الجملة طرفاه معيَّنان بنواتيهما ونطاقيهما (لا «الجملة قبله»)',
          cj and all(a_.startswith('«') and 'رأسها' in a_ for x in cj for a_ in x['A']), cj)
    c3 = [x for x in cj if x['B'] == 'وَيُقِيمُونَ']
    check('البقرة ٣: «وَيُقِيمُونَ» معطوفةٌ على الصلة «يُؤۡمِنُونَ بِٱلۡغَيۡبِ»، والموصول «ٱلَّذِينَ» حاويها لا نواتها',
          c3 and c3[0]['A'][0].startswith('«يُؤْمِنُونَ بِالْغَيْبِ» (صلة') and 'الموصول «الَّذِينَ»' in c3[0]['A'][0], c3)
    sm = structs((2, 4))
    c4b = [x for x in sm['coord'] if x['B'] == 'وَبِالْآخِرَةِ']
    check('البقرة ٤: «وَبِٱلۡأٓخِرَةِ» معطوفةٌ على صلة «وَٱلَّذِينَ»، لا على نطاقٍ يضمّ «يُنفِقُونَ»',
          c4b and c4b[0]['A'] and '(صلة' in c4b[0]['A'][0] and 'يُنْفِقُونَ' not in c4b[0]['A'][0], c4b)
    # الفاحص المستقل (مراجعة التقرير ٩، ١١): يقبل الجملة المغلقة، ويرفضها إن زُيِّفت شهادتها أو حُذف التزامٌ لازم عمداً
    import copy
    from sarf.checker import check_sentence
    T_ = Trace(); items_ = []; an_ = {}
    for v_ in range(50, 55):
        a_ = analyze(cat, rows[(2, v_)]); S_, u_ = sentence_geo(a_, f'Q2:{v_}', T_)
        items_.append((2, v_, a_, u_, S_)); an_[(2, v_)] = a_
    LT_ = linguistic_layer(items_, T_, 't')[0]
    Jc = next((J for D in LT_[0].A for J in D.A if J.closed and any(o.name.startswith('معمول') for o in J.Omega)), None)
    check('الفاحص يقبل جملةً مغلقة بشهادتين صحيحتين (البقرة ٥٤: فَتُوبُوٓاْ إِلَىٰ بَارِئِكُمۡ)',
          Jc is not None and check_sentence(Jc, an_) == [], Jc and check_sentence(Jc, an_))
    if Jc is not None:
        J1 = copy.deepcopy(Jc); J1.Omega = [o for o in J1.Omega if not o.name.startswith('معمول')]
        check('ويرفضها إن حُذف منها التزامٌ يلزم بالتحليل (معمول العامل المقبول)',
              any('لم يُولَّد' in w for w in check_sentence(J1, an_)), check_sentence(J1, an_))
        J2 = copy.deepcopy(Jc); J2.ec = Evidence('', [])
        check('ويرفضها إن خلت شهادة الإكمال', any('شهادة الإكمال' in w for w in check_sentence(J2, an_)), check_sentence(J2, an_))
        J3 = copy.deepcopy(Jc); J3.Omega[0].met = False
        check('ويرفضها إن بقي التزامٌ لازم غير مستوفى', any('غير مستوفى' in w for w in check_sentence(J3, an_)), check_sentence(J3, an_))
        J4 = copy.deepcopy(Jc); J4.O['unplaced'] = ['رَحِيمٌ']
        check('ويرفضها إن بقيت كلمةٌ بلا موضعٍ مرخَّص', any('بلا موضع' in w for w in check_sentence(J4, an_)), check_sentence(J4, an_))
    # مراجعة التقرير الثانية (٢): الأنفال ٣٣ «وَمَا كَانَ ٱللَّهُ لِيُعَذِّبَهُمۡ»: لام الجحود، وطرف خبر «كان» الفعل لا «هُمۡ»؛
    # والفاحص يرفض رابطاً مكتمل الحقول طرفه من النوع الخطأ
    from sarf.checker import relation_problems
    T_ = Trace(); a_ = analyze(cat, rows[(8, 33)]); S_, u_ = sentence_geo(a_, 'Q8:33', T_)
    kb = [b for b in S_.B if b[0].startswith('خبر «كَانَ»') and 'w3' in str(b[2])]
    check('الأنفال ٣٣: خبر «كان» لام الجحود، وطرفه «يُعَذِّبَ» لا الضمير «هُمۡ»',
          kb and 'لام الجحود' in kb[0][0] and u_[(3, 1)].id == kb[0][2], kb)
    LT_ = linguistic_layer([(8, 33, a_, u_, S_)], T_, 't')[0]
    J8 = next(J for D in LT_[0].A + LT_[0].O['pending'] for J in D.A + D.O['pending'] if (8, 33, 3) in J.O['location'])
    check('والجملة نفسها بلا خطأ نوعٍ في روابطها', relation_problems(J8) == [], relation_problems(J8))
    if J8.closed:
        check('الأنفال ٣٣: إغلاق «لِيُعَذِّبَهُمۡ» محليٌّ في مستوى الجملة، والخلوّ من التعلّق بما بعده (وَأَنتَ فِيهِمۡ: حال) غير مثبت',
              J8.O.get('closure', {}).get('external', '').startswith('غير مثبت') and 'حال' in J8.O['closure']['external'] and
              not any('L = ∅ مفحوص' == c for c in J8.eb.conditions), J8.O.get('closure'))
    J9 = copy.deepcopy(J8)
    J9.B = [(b[0].replace('لام الجحود', 'جملة فعلية'), b[1], u_[(3, 2)].id, b[3]) if b[0].startswith('خبر «كَانَ»') and 'w3' in str(b[2])
            else b for b in J9.B]
    check('والفاحص يرفض تبديل طرف الخبر الجملي بضمير المفعول مع بقاء الحقول مكتملة',
          any('نوع الطرف' in w or 'خبرٌ ومفعولٌ' in w for w in relation_problems(J9)), relation_problems(J9))
    # مراجعة التقرير الثانية (٥، ٦): ملكية الجواب، والشرط المنفي
    sm = structs((2, 16))
    check('البقرة ١٦: «فَمَا رَبِحَت» و«وَمَا كَانُواْ»: «ما» نافية، فلا قراءة شرطية', not sm['cond'], sm['cond'])
    sm = structs((2, 17))
    lm = [x for x in sm['cond'] if x['tool'] == 'لَمَّا']
    check('البقرة ١٧: جواب «لَمَّا» «ذَهَبَ» (ماضٍ بعد جملة الشرط)، لا فاءٌ بعيدة',
          lm and lm[0]['obligations'][1][1] and lm[0]['obligations'][1][2].startswith('ماضٍ'), lm)
    sm = structs((2, 23))
    last = [x for x in sm['cond'] if x['location'].endswith(':17')]
    check('البقرة ٢٣: «إِن كُنتُمۡ صَٰدِقِينَ» لا يستوفي جوابه «فَإِن» التالية (شرطٌ جديد)، وجوابه محذوفٌ مرشَّح',
          last and not last[0]['obligations'][1][1] and 'محذوف' in last[0]['obligations'][1][2], last)
    sm = structs((2, 24))
    ng = [x for x in sm['cond'] if x['location'].endswith(':0')]
    check('البقرة ٢٤: «فَإِن لَّمۡ تَفۡعَلُواْ»: جملة الشرط منفيّة ورأسها «تَفۡعَلُواْ»، والجواب «فَٱتَّقُواْ»',
          ng and ng[0]['obligations'][0][2].startswith('منفيٌّ') and 'تَفْعَلُوا' in ng[0]['obligations'][0][2] and
          ng[0]['obligations'][1][1], ng)
    # مراجعة التقرير الثانية (٤): نطاق الطرف A في عطف الجملة لا يعبر إلى جملةٍ قبله
    sm = structs((2, 5))
    c5 = [x for x in sm['coord'] if x['B'].startswith('وَأُ')]
    check('البقرة ٥: «وَأُوْلَٰٓئِكَ» معطوفةٌ على «أُوْلَٰٓئِكَ عَلَىٰ هُدࣰى…» (رأسها اسم الإشارة)، لا «يُوقِنُونَ…»',
          c5 and c5[0]['A'] and c5[0]['A'][0].startswith('«أُلَٰئِكَ عَلَى'), c5)
    MU, (LT, st_) = layers([(2, 6), (2, 7)])
    c7 = [x for x in linguistic_layer.samples['coord'] if x['location'] == '2:7:6']
    check('البقرة ٧: «وَعَلَىٰٓ أَبۡصَٰرِهِمۡ» طرفها «خَتَمَ ٱللَّهُ…» بنواتها «خَتَمَ»، لا «يُؤۡمِنُونَ خَتَمَ…»',
          c7 and c7[0]['A'] and c7[0]['A'][0].startswith('«خَتَمَ') and 'يُؤْمِنُونَ' not in c7[0]['A'][0], c7)
    sm = structs((2, 4))
    c4 = [x for x in sm['coord'] if x['location'] == '2:4:5']
    check('البقرة ٤: «وَمَآ أُنزِلَ مِن قَبۡلِكَ» موصولةٌ معطوفة على «بِمَآ»، لا جملة', c4 and c4[0]['level'] == 'مفرد', c4)
    # مراجعة التقرير الثالثة (١): الشاهد يقابل الخلايا؛ «تُوبُوا» لاحقتها المكتوبة «وا»، و«ون» صنفها
    from sarf.checker import witness_problems
    if Jc is not None:
        fo = next((o for o in Jc.Omega if o.name.startswith('فاعل') and o.ev), None)
        check('البقرة ٥٤: شاهد فاعل «تُوبُوا» اللاحقة المكتوبة «وا»، والفاحص يقبله',
              fo is not None and '«وا»' in ' '.join(fo.ev.conditions) and witness_problems(Jc) == [],
              (fo and fo.ev.conditions, witness_problems(Jc)))
        J5 = copy.deepcopy(Jc)
        for o in J5.Omega:
            if o.name.startswith('فاعل') and o.ev:
                o.ev.conditions = ['جدول الإسناد', 'لاحقة الأمر «ون»']
        check('والفاحص يرفض شاهداً لا يقابل الخلايا (لاحقة «ون» في «تُوبُوا»)',
              any('لا يقابل الخلايا' in w for w in check_sentence(J5, an_)), check_sentence(J5, an_))
    sm = structs((17, 49))
    cw = [x for x in sm['coord'] if x['B'].startswith('وَرُفَٰت')]
    check('الإسراء ٤٩: «وَرُفَٰتًا» معطوفٌ مفرد على «عِظَٰمࣰا» (موافقةٌ في النصب)، والواو لمطلق الجمع',
          cw and cw[0]['level'] == 'مفرد' and cw[0]['A'] == ['عِظَٰمًا'] and cw[0]['effect'].startswith('مطلق'), cw)
    sm = structs((2, 164))
    cw = [x for x in sm['coord'] if x['B'] == 'وَالنَّهَارِ']
    check('البقرة ١٦٤: «وَٱلنَّهَارِ» مرشَّحاه بالجرّ، أقربهما «ٱلَّيۡلِ»، والبدائل محفوظة', cw and cw[0]['A'][:1] == ['الَّيْلِ'], cw)
    at26 = {r['location'][2]: r for r in recs([(4, 26)])}
    check('النساء ٢٦: الجملة تنتهي قبل «وَٱللَّهُ عَلِيمٌ حَكِيمٌ» (عطفٌ على جملةٍ تامّة يشاركها التمام)',
          at26.get(10, {}).get('J') == 'proven', at26.get(10))
    check('البقرة ٢٨٢: الشرط بعد جملة تامّة لا يثبت به الحدّ (وَلَا يَأۡبَ ٱلشُّهَدَآءُ إِذَا مَا دُعُواْ)',
          at.get(74, {}).get('J') != 'proven', at.get(74))
    R = {r['location']: r for r in recs([(37, 137), (37, 138)])}
    r = R[(37, 137, 3)]
    check('رأس الآية ١٣٧: W رأس آية، وL من نص الداني، فلا يُبتدأ بما بعده',
          r['W'].startswith('رأس آية') and any('الداني' in x for x in r['L']) and r['I'].startswith('لا يُبتدأ'), r)
    r = R[(37, 138, 0)]
    check('بعد «وَبِٱلَّيۡلِ»: الداني «تام»، ومعه حكم المصحف «ج»، محفوظان في E',
          {e['scholar'] for e in r['E']} == {'لجنة مصحف المجمّع', 'أبو عمرو الداني'} and r['M'] == [], r['E'])
    R = {r['location']: r for r in recs([(3, 167)])}
    r = R[(3, 167, 28)]
    check('آل عمران ١٦٧: وقف جائز مع تعلّق لفظي عابر، فلا ابتداء مستقلاً ولا إغلاق للجملة',
          r['W'] == 'وقف جائز' and r['L'] and r['I'].startswith('لا يُبتدأ'), r)
# الروابط عبر حدّ الآية
if hfn() and rows:
    from sarf.algebra import cross_ayah_links
    def cross(p1, p2):
        out = []
        for r_ in (p1, p2):
            a = analyze(cat, rows[r_])
            S_, u_ = sentence_geo(a, f'Q{r_[0]}:{r_[1]}', Trace())
            out.append(dict(s=r_[0], v=r_[1], text=rows[r_], a=a, units=u_, S=S_))
        return cross_ayah_links(lambda t: analyze(cat, t), out[0], out[1])
    c = cross((37, 137), (37, 138))
    check('الصافات ١٣٧–١٣٨: «وَبِٱلَّيۡلِ» وحدها إلى «ج»: تعلّقٌ ثابت بما قبل حدّ الآية',
          any(x['proven'] and x['rel'].startswith('تعلّق شبه الجملة') for x in c), c)
    c = cross((103, 2), (103, 3))
    check('العصر ٢–٣: «إِلَّا» في أول الآية استثناءٌ ثابت مما قبلها', any(x['proven'] and x['rel'] == 'استثناء' for x in c), c)
    c = cross((2, 9), (2, 10))
    check('البقرة ٩–١٠: «فِي قُلُوبِهِم مَّرَضٌ» جملة مستقلة، فلا تعلّق ثابت', not any(x['proven'] for x in c), c)
# الخبر والمفعول بالعلامة المكتوبة
if hfn():
    def obl(v, prefix):
        a = analyze(cat, v)
        S_, _ = sentence_geo(a, 'v', Trace())
        return [(o.name, o.met) for o in S_.Omega if o.name.startswith(prefix)]
    check('إِنَّ ٱللَّهَ غَفُورٌ: الخبر مرفوعٌ بعد الاسم', obl('إِنَّ ٱللَّهَ غَفُورٌ رَّحِيمٌ', 'خبر') == [('خبر «إِنَّ»', True)])
    check('إِنَّ ٱلَّذِينَ كَفَرُوا۟ سَوَآءٌ: الصلة لا تكون خبراً', obl('إِنَّ ٱلَّذِينَ كَفَرُوا۟ سَوَآءٌ عَلَيْهِمْ', 'خبر') == [('خبر «إِنَّ»', True)])
    check('وَإِنَّكُمْ لَتَمُرُّونَ: الخبر باللام المزحلقة', obl('وَإِنَّكُمْ لَتَمُرُّونَ عَلَيْهِم مُّصْبِحِينَ', 'خبر') == [('خبر «إِنَّ»', True)])
    check('وَكَانَ ٱللَّهُ عَلِيمًا: خبر كان منصوب', obl('وَكَانَ ٱللَّهُ عَلِيمًا حَكِيمًا', 'خبر') == [('خبر «كَانَ»', True)])
    check('لَقَدْ خَلَقْنَا ٱلْإِنسَٰنَ: مفعول به', obl('لَقَدْ خَلَقْنَا ٱلْإِنسَٰنَ', 'مفعول') == [('مفعول «خَلَقْنَا»', True)])
    check('فَٱعْبُدُوهُ: المفعول ضمير متصل', obl('فَٱعْبُدُوهُ', 'مفعول') == [('مفعول «اعْبُدُو»', True)])
if hfn():
    def objs(v):
        a = analyze(cat, v)
        S_, u_ = sentence_geo(a, 'v', Trace())
        txt = {G.id: G.O['text'] for G in u_.values()}
        return {o.name: txt.get(o.units[-1]) for o in S_.Omega if o.name.startswith('مفعول') and o.met}
    o = objs('قَالُواْ نَعۡبُدُ إِلَٰهَكَ')
    check('«قَالُواْ»: مقول القول جملة لا مفعول', not any('قَال' in k for k in o), o)
    o = objs('وَتَرَكۡنَا يُوسُفَ عِندَ مَتَٰعِنَا فَأَكَلَهُ ٱلذِّئۡبُ')
    check('«فَأَكَلَهُ» فعلٌ وضمير، لا مفعول لـ«تَرَكۡنَا»', o.get('مفعول «تَرَكْنَا»') != 'فَأَكَلَ', o)
    o = objs('يَعۡرِفُونَهُۥ كَمَا يَعۡرِفُونَ أَبۡنَآءَهُمۡ')
    check('المفعول «أَبۡنَآءَ» جذعاً لا ضميره', 'أَبْنَاءَ' in o.values(), o)
if hfn() and rows:
    c = cross((1, 3), (1, 4))
    check('الفاتحة ٣–٤: «مَٰلِكِ» مجرورٌ أولَ الآية بلا جارّ: تابعٌ لما قبل الحدّ', any(x['proven'] and 'جرّ' in x['rel'] for x in c), c)
    c = cross((91, 1), (91, 2))
    check('الشمس ١–٢: «وَٱلۡقَمَرِ» بعد واو: عطفٌ أو قسم، محتمل لا ثابت', c and not any(x['proven'] for x in c), c)
    c = cross((1, 6), (1, 7))
    check('الفاتحة ٦–٧: «صِرَٰطَ» منصوبٌ يوافق «ٱلصِّرَٰطَ»: بدلٌ محتمل', any(not x['proven'] and 'بدل' in x['rel'] for x in c), c)
    # تدقيق الخرج: فعلٌ أو منادى أولَ الآية لا يُقرأ حركةُ آخره إعراباً
    for r1, r2, w in [((55, 1), (55, 2), 'عَلَّمَ'), ((17, 77), (17, 78), 'أَقِمِ'), ((40, 28), (40, 29), 'يَٰقَوۡمِ'),
                      ((30, 1), (30, 2), 'غُلِبَتِ'), ((36, 29), (36, 30), 'يَٰحَسۡرَةً'), ((69, 17), (69, 18), 'يَوۡمَئِذࣲ'),
                      ((5, 4), (5, 5), 'ٱلۡيَوۡمَ'), ((17, 19), (17, 20), 'كُلࣰّا نُّمِدُّ')]:
        c = cross(r1, r2)
        check(f'{r1[0]}:{r2[1]} «{w}»: لا رابطَ إعرابياً ثابت', not any(x['proven'] and ('جرّ' in x['rel'] or 'منصوب' in x['rel'])
                                                                    for x in c), c)
if hfn():
    def khabar(v):
        a = analyze(cat, v)
        S_, _ = sentence_geo(a, 'v', Trace())
        return [(o.name, o.met, o.ev and o.ev.cause) for o in S_.Omega if o.name.startswith('خبر')]
    k = khabar('إِنَّ ٱلۡكَٰفِرِينَ كَانُواْ لَكُمۡ عَدُوࣰّا مُّبِينࣰا')
    check('النساء ١٠١: «لَكُمۡ» لام جرّ لا مزحلقة، والخبر جملة «كَانُواْ»',
          not any('المزحلقة' in str(x) for x in k) and ('خبر «إِنَّ»', True, 'خبر «إِنَّ» جملة فعلية (كان وأخواتها)') in k, k)
    k = khabar('إِنَّ ٱللَّهَ يُحِبُّ ٱلَّذِينَ يُقَٰتِلُونَ')
    check('الصف ٤: «يُحِبُّ» لا يُعدّ خبراً مفرداً', k and not any(str(x[2]).endswith('مفرد') for x in k), k)
if hfn():
    a = analyze(cat, 'وَلَآ أَنَا۠ عَابِدࣱ مَّا عَبَدتُّمۡ')
    S_, u_ = sentence_geo(a, 'v', Trace())
    G = [G for G in u_.values() if G.Theta.get('R') == 'عبد' and G.Theta.get('P') == 'I']
    check('«عَبَدتُّمۡ»: الدال خليةٌ ساكنة كما كُتبت والمشدَّد خليتان (حكم صاحب النظرية): عَ.بَدْتْ.تُمْ، والجذر عبد، I',
          G and [cv(x) for x in G[0].A] == ['CV', 'CVCC', 'CVC'], [(G.O['text'], G.Theta.get('R')) for G in u_.values()])
    c_, _ = cells_of('قَالْتْ', 'x')
    check('CVCC بلا مشدَّد لا يقع داخل الكلمة (Rem_M بالموضع)', [cv(x) for x in syllabify(c_, 'x', Trace(), False)[0]] == ['CVVC'])
print('ALL OK' if not bad else f'FAILED {bad}')
sys.exit(1 if bad else 0)
