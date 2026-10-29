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
    check('البقرة ٢٨٢: قبل «وَٱتَّقُواْ» نهاية جملة قبل الواو (حكم صاحب النظرية)، وما بعدها بدائل محفوظة',
          at.get(120, {}).get('J') == 'proven' and at[120]['J_why'].startswith('نهاية جملة قبل الواو'), at.get(120))
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
    check('النمل ٩٢: لا حدّ بين «فَمَنِ» وفعلها، والفاء بعدها جوابٌ محتمل (فَمَنِ ٱهۡتَدَىٰ ‖ فَإِنَّمَا)',
          e.get(3, {}).get('J') is None and e.get(4, {}).get('J') == 'possible', [(k, r['J']) for k, r in e.items()])
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
