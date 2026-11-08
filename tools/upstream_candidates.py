"""tools/upstream_candidates.py — الاستهلاك المرشّح للمصادر الحديثة (SARF_UPSTREAM_CONSUMPTION_2026_11_08، الوضع «ب»).

يمرّ على المصحف بالمحلّل كما هو (الأساس: HFN release_v36 كما يقرؤه sarf/root.py)، ويجمع لكل وقوعٍ فعلي وجهه الصرفي وهويته وجذره ووزنه
ولمّته المشكولة من HFN الأساس، ثم يسأل المصادر الأربع المثبتة في عمليةٍ فرعية معزولة، ويكتب ما يجيب به كل مصدرٍ في حقولٍ جديدة منفصلة
في ملفٍّ جانبي. لا يغيّر مخرجاً قائماً: المحلّل لا يستورد هذا الملف، ولا يدخل شيءٌ منه اختيار التقسيم أو الصنف أو الجذر أو الوزن أو العامل
أو التعلّق أو الإغلاق؛ وكل سمةٍ CANDIDATE.

    SARF_HFN=…/release_v36 SARF_UP_PINS=tools/upstream/pins_2026_11_08.json SARF_UP_HFN=… SARF_UP_WAZN=… SARF_UP_AMLN=… SARF_UP_MAQ=… \
    PYTHONHASHSEED=0 python3 -s tools/upstream_candidates.py OUT.jsonl.gz SUMMARY.json [--verses 2:282,112:3] [--jobs N]

خريطة المسار (من المدخل العام إلى التقرير):
  frames() المستهلك العام ← lemma_status() بوابة الحماية والأهلية ← هوية التحليل (analysis_id) واللمّة ← client.call() العامل المعزول ←
  match_class() فحص المطابقة + ROUTES/BLOCKED المسلك ← feature_rows() السمة المرشّحة وأدلّتها ← OUT.jsonl.gz / evidence_records() ← التقرير
"""
import collections, gzip, itertools, json, math, multiprocessing as mp, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'upstream'))
os.chdir(ROOT)


def wilson(k, n, z=1.959964):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    return round((p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d, 3)


H8 = 'HANDOFF_SARF_UPSTREAM_2026-11-08 §3.4'
H6 = 'HANDOFF_SARF_UPSTREAM_2026-11-06 (أحكامه باقية: 11-08 §1)'
# سجلّ المسالك المقبولة بقياسها ومصدر القياس. قبول المسلك لا يثبت ملاءمة النتيجة للوقوع: كل مخرجٍ CANDIDATE
ROUTES = {
    ('AMLN', 'R1'): dict(status='ACCEPTED_ROUTE', precision=0.964, wilson_low=0.877, source=H8, sanad='كشف الأسرار:9670', file='ahdath/rules_R1.tsv'),
    ('AMLN', 'R1W'): dict(status='ACCEPTED_ROUTE', precision=0.930, wilson_low=0.833, source=H8, sanad='الكليات:27626–27627', file='ahdath/mutawaa_R1W_pool.tsv'),
    ('AMLN', 'T_JAL'): dict(status='ACCEPTED_ROUTE', precision=1.0, wilson_low=0.867, source=H8 + ' (25 من 25)', sanad='الكتاب:16451–16455',
                            file='ahdath/taadiya_T_JAL.tsv'),
    ('AMLN', 'J_SAJIYYA'): dict(status='ACCEPTED_ROUTE', precision=1.0, wilson_low=0.890, source=H6 + '؛ word_tree/ahdath.py JIHA_ROUTES',
                                sanad='الكتاب:16143–16144', file='ahdath/jiha_pool.tsv'),
    ('AMLN', 'J_DAA'): dict(status='ACCEPTED_ROUTE', precision=0.975, wilson_low=0.871, source=H6 + '؛ word_tree/ahdath.py JIHA_ROUTES',
                            sanad='الكتاب:16016؛ 16108', file='ahdath/jiha_pool.tsv'),
    ('WAZN', 'R1_QABILIYYAT'): dict(status='ACCEPTED_ROUTE', precision=0.964, wilson_low=0.877, source='engines/mutawaa_engine.py (docstring)',
                                    sanad='كشف الأسرار:9670', file='data/mutawaa_v7.tsv'),
    ('WAZN', 'LEX_FORMULA'): dict(status='ACCEPTED_ROUTE', precision=round(56 / 59, 3), wilson_low=0.861, source='engines/mutawaa_engine.py (docstring)',
                                  sanad='المعاجم (صيغة «فعلته فانفعل»)', file='data/mutawaa_v7.tsv'),
    ('WAZN', 'R1W_WASIT'): dict(status='ACCEPTED_ROUTE', precision=0.930, wilson_low=0.833, source='engines/mutawaa_engine.py (docstring)',
                                sanad='الكليات:27626–27627', file='data/mutawaa_v7.tsv'),
    ('WAZN', 'T_JAL'): dict(status='ACCEPTED_ROUTE', precision=1.0, wilson_low=0.867, source=H8, sanad='الكتاب:16451–16455', file='engines/taadiya_engine.py'),
    ('WAZN', 'TRANSITIVITY_WASIT_V5'): dict(status='ACCEPTED_ROUTE', precision=None, wilson_low=None,
                                            source='HANDOFF 11-08 §3.3: v5 = v1 مصحَّحاً حيث اتّفق القارئان (201 تغيير)؛ للمجرّد وحده',
                                            sanad='المعجم الوسيط (M11)', file='data/transitivity_wasit_v5.tsv', scope='المجرّد وحده'),
    ('WAZN', 'SIFAT_V2'): dict(status='INFORMATION_CANDIDATE', precision=None, wilson_low=None, source='HANDOFF 11-08 §3.3: على v45، وأحكام التعدّي فيه نفس v1',
                               sanad='المعجم الوسيط', file='data/sifat_v2.tsv', note='معلومةٌ مرشّحة: لا يُستنتج منها نوع اشتقاقٍ ولا وزنٌ مختار'),
    ('HFN', 'RELEASE_V47_EVENT'): dict(status='RELEASE_CANDIDATE', precision=None, wilson_low=None, source='HFN release_v47 (verify PASS، الإفسادات 14/14)',
                                       sanad='HFN-D060…D075', file='release/release_v47/events.csv',
                                       note='إصدارٌ غير معتمد أساساً للمحلّل (HFN_V47_ADOPTED = NO): سمةٌ مرشّحة بجانب قيمة v36'),
}
# المحجوب: لا يُستعمل، ويُحفظ في سجلّه بسببه
BLOCKED = {
    ('AMLN', 'R2'): 'BLOCK: متعدٍّ بلا مطاوع ← مؤثّر؛ آخر قياس 0.719، ويلسون 0.59 (HANDOFF 11-08 §3.4)',
    ('AMLN', 'R2w'): 'BLOCK: v3–v5 (HANDOFF 11-08 §3.4)',
    ('AMLN', 'T'): 'BLOCK: ويلسون 0.488 (11-06)', ('AMLN', 'T_TAD'): 'BLOCK: ويلسون 0.458 (11-06)',
    ('AMLN', 'J_LAWN'): 'BLOCK: ويلسون 0.742، الحوض 30', ('AMLN', 'J_MUTAWAA'): 'BLOCK: ويلسون 0.656',
    ('WAZN', 'TRANSITIVITY_WASIT_MAZID'): 'BLOCK: تعدّي المزيد من الوسيط محجوب (0.746) (HANDOFF 11-08 §3.3، §5)',
    ('WAZN', 'TRANSITIVITY_WASIT_V4'): 'BLOCK: لا يُستعمل للمجرّد (HANDOFF 11-08 §3.3)',
    ('WAZN', 'TRANSITIVITY_WASIT:مشترك'): 'BLOCK: «مشترك» محجوب (0.75) (11-06)',
    ('WAZN', 'MUTAWAA:BASE_UNRESOLVED'): 'BLOCK: أصلٌ غير محسوم',
}
# حكم الأين (المالك 2026-11-08): يُسجَّل بسنده، ولا يوسَّع إلى المسالك المحجوبة (R2 وأخواته)
OWNER_RULINGS = [dict(id='AYN_2026_11_08', text='تغيّر الأين في المفعول أثرٌ فيه، فيُعدّ مؤثّراً',
                      sanad='المناوي، التوقيف، ص68؛ والغزالي، معيار العلم، ص242', source=H8,
                      scope='معيار «المؤثّر» في المسالك المقبولة (R1، R1W) كما قيست؛ لا يرفع حجب R2/R2w ولا يُنقل إلى مسلكٍ آخر')]
MUJARRAD_FORMS = ('فَعَلَ', 'فَعِلَ', 'فَعُلَ')
# الحالات (§٤)
ST = dict(PROTECTED='PROTECTED_NOT_QUERIED', UNRESOLVED='IDENTITY_OR_LEMMA_UNRESOLVED', NO_RESULT='QUERY_OK_NO_RESULT',
          MATCH='CANDIDATE_MATCH', NON_MATCH='NON_MATCH', BLOCKED='ROUTE_BLOCKED', WITHDRAWN='WITHDRAWN_RECORD',
          MISSING='RESOURCE_MISSING', ERROR='INTERFACE_OR_CONFIG_ERROR', UNSUPPORTED='UNSUPPORTED_FORM')
ST.update(CONFLICT='LEXEME_IDENTITY_CONFLICT', EVENT_MISMATCH='EVENT_ID_FIELD_MISMATCH', UNDETERMINED='IDENTITY_UNDETERMINED')
RANK = ('CANDIDATE', 'مرشّح: لا يدخل الإغلاق ولا الاستدلال')
# هوية الدليل (SARF_UPSTREAM_CONSUMER_REPAIR_02 §٣): بصمة sha256 على ترميز JSON قانوني (مفاتيح مرتّبة، UTF-8، بلا فراغات) لحقول الهوية والحمولة،
# فلا يحيل معرّفٌ واحد إلى محتويين، ولا يتوقّف على ترتيب الصفوف
EVIDENCE_ID_ALGO = 'sha256(canonical_json_v1)[:32]'
EVIDENCE_ID_FIELDS = ('occurrence_id', 'morph_candidate_id', 'analysis_id', 'source_key', 'provider', 'route_id', 'source_commit', 'release_id',
                      'source_file_sha256', 'source_row_id', 'payload')


def canonical(d):
    return json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def evidence_id(content):
    import hashlib
    return 'UPEV-' + hashlib.sha256(canonical({k: content.get(k) for k in EVIDENCE_ID_FIELDS}).encode('utf-8')).hexdigest()[:32]


def verify_evidence_registry(records):
    """→ قائمة الأخطاء: معرّفٌ لا يطابق بصمة محتواه، أو معرّفٌ واحد بمحتويين"""
    errs, seen = [], {}
    for e in records:
        if evidence_id(e) != e['evidence_id']:
            errs.append(('ID_DOES_NOT_MATCH_CONTENT', e['evidence_id']))
        c = canonical({k: e.get(k) for k in EVIDENCE_ID_FIELDS})
        if seen.setdefault(e['evidence_id'], c) != c:
            errs.append(('SAME_ID_DIFFERENT_CONTENT', e['evidence_id']))
    return errs


def identity(fr, row_root, row_form, row_verb, ev, xw):
    """هوية صفّ المصدر مقابل الوجه (§٢): الجذر، والبناء (تصنيف sarf نفسه hfn_class، وجدول wazn-net hfn_form_crosswalk شاهداً ثانياً)،
    ومعرّف الحدث وحقوله وحالة سحبه. → (الحالة، التفصيل). لا يُنسخ جذرٌ فوق جذر، ونقص المعلومة تأجيل"""
    from sarf.root import hfn_class
    from worker import letters
    K = lambda r_: query_key(r_)[0]
    d = dict(face_root=fr['root'], face_class=fr['pattern'], row_root=row_root or None, row_form=row_form or None, row_verb=row_verb, event_ref=ev)
    if ev and ev.get('ambiguous'):
        return ST['UNDETERMINED'], dict(d, reason='EVENT_ID_AMBIGUOUS_IN_SOURCE_TABLE')
    if ev and ev.get('found') is False:
        return ST['UNDETERMINED'], dict(d, reason='EVENT_ID_NOT_IN_PINNED_RELEASE')
    if ev and ev.get('withdrawn'):
        return ST['WITHDRAWN'], dict(d, reason='EVENT_WITHDRAWN')
    if ev:
        mis = []
        if row_root and K(row_root) != K(ev['root_K']):
            mis.append('root')
        if row_form and hfn_class(row_form) != hfn_class(ev['form']):
            mis.append('form')
        if row_verb and letters(row_verb) != letters(ev['verb']):
            mis.append('verb')
        if mis:
            return ST['EVENT_MISMATCH'], dict(d, reason='EVENT_ID_FIELDS_DISAGREE: ' + ','.join(mis))
    src_root = row_root or (ev or {}).get('root_K')
    src_form = row_form or (ev or {}).get('form')
    if not src_root or not src_form:
        return ST['UNDETERMINED'], dict(d, reason='MISSING_' + ('ROOT' if not src_root else 'FORM'))
    sc, xc = hfn_class(src_form), (xw or {}).get(src_form) or None
    d.update(source_root=src_root, source_form=src_form, source_class=sc, crosswalk_code=xc,
             event_linked_to_face=bool(ev) and ev.get('event_id') in {e['event_id'] for e in fr['hfn_events']})
    if sc is None:
        return ST['UNDETERMINED'], dict(d, reason='FORM_CLASS_UNKNOWN')
    if xc and xc != sc:
        return ST['UNDETERMINED'], dict(d, reason=f'CROSSWALK_DISAGREES ({xc} ≠ {sc})')
    if K(src_root) != K(fr['root']) or sc != fr['pattern']:
        return ST['CONFLICT'], dict(d, reason=('ROOT ' if K(src_root) != K(fr['root']) else '') + ('FORM' if sc != fr['pattern'] else ''))
    return 'IDENTITY_OK', dict(d, reason=None)


def query_key(root):
    """مفتاح السؤال عن معنى الجذر (K في البنك) من جذر sarf، بتحويلٍ معلوم وحده؛ وجذر sarf نفسه لا يتغيّر.
    → (المفتاح أو None، القاعدة)"""
    if not root:
        return None, 'NO_ROOT'
    k, rules = root, []
    seats = str.maketrans({'أ': 'ء', 'إ': 'ء', 'ؤ': 'ء', 'ئ': 'ء', 'آ': 'ء'})
    if set(k) & set('أإؤئآ'):
        k = k.translate(seats)
        rules.append('HAMZA_SEAT→ء')
    if set(k) & set('اى'):
        return None, 'AMBIGUOUS_ALIF: لا يُخمَّن واوٌ أو ياء من ألفٍ مبهمة'
    if len(k) == 2:
        k = k + k[-1]
        rules.append('DOUBLED_2→3 (المضاعف بثلاثة أحرف)')
    if len(k) not in (3, 4):
        return None, f'LENGTH_{len(k)}'
    return k, '+'.join(rules) or 'IDENTITY'


def frames(items):
    """→ لكل آية: أطر الفعل بوجهها الصرفي (المرشّح ومعرّف التحليل وحالة اختياره) وجذرها ووزنها، ولمّاتها المشكولة من HFN الأساس"""
    from sarf.catalog import Catalog
    from sarf.analyze import analyze
    from sarf.algebra import Trace, sentence_geo, linguistic_layer
    from sarf.features import unit_features
    from sarf import relations as RL, quran_source
    from sarf.root import hfn
    from sarf.protected import protected
    CAT = Catalog([os.path.join(ROOT, 'operators_catalog.jsonl'), os.path.join(ROOT, 'operators_catalog_split_vocalized.csv')])
    its, per = [], []
    for s, v, text in items:
        a = analyze(CAT, text, quran_source.uthmani_mode())
        S_, U = sentence_geo(a, f'Q{s}:{v}', Trace())
        its.append((s, v, a, U, S_))
        per.append((s, v, a, U, unit_features(a, U)))
    C, Rl = [], []
    linguistic_layer(its, Trace(), 'up', cond_out=C, rel_out=Rl)
    H = hfn()
    out = []
    for s, v, a, U, F in per:
        o = RL.verse_relations(a, U, F, f'{s}:{v}', legacy_cond=C, legacy_rel=Rl)
        for r in o['records']:
            if r['type'] != 'VERB_FRAME':
                continue
            f_ = r.get('frame') or {}
            c_ = f_.get('candidate') or {}
            R_, P_ = f_.get('root'), f_.get('pattern')
            cid = c_.get('id') or ''
            wi = int(cid.split('.w')[1].split('.')[0]) if '.w' in cid else None
            ms = [m for m in a['morph'] if m['word_index'] == wi and m.get('root') == R_ and m.get('form_class') == P_] if wi is not None else []
            ev = [dict(event_id=e['event_id'], verb=e['verb'], form=e.get('form'), transitivity=e.get('transitivity'))
                  for e in H.index.get((R_, P_), [])] if R_ and P_ else []
            pr = protected(r['texts'].get('verb'))
            out.append(dict(verse=f'{s}:{v}', word_index=wi, relation_id=r['relation_id'], unit=r['heads'].get('verb'), text=r['texts'].get('verb'),
                            protected=(dict(cls=pr['cls'], identity=pr['identity'], ambiguous=pr.get('ambiguous', False)) if pr else None),
                            morph_candidate_id=cid or None, analysis_id=(ms[0].get('analysis_id') if len(ms) == 1 else None),
                            analysis_selection=((ms[0].get('statuses') or {}).get('analysis_selection_status') if len(ms) == 1 else
                                                ('NO_MORPH_ENTRY' if not ms else 'MULTIPLE_MORPH_ENTRIES')),
                            root=R_, pattern=P_, voice=c_.get('voice'), tense=c_.get('tense'), hfn_base_release=os.path.basename(H.path or ''),
                            hfn_events=ev))
    return out


def lemma_status(fr):
    """بوابة الحماية ثم الأهلية: لا يُسأل مصدرٌ عن وحدةٍ محمية؛ ولا تُرفق سمةٌ إلا بوجهٍ مختار ولمّةٍ واحدة"""
    ev = fr['hfn_events']
    if fr.get('protected'):
        return ST['PROTECTED'], ('وحدةٌ محمية دستورياً (' + fr['protected']['cls'] + '، ' + fr['protected']['identity'] + ')' +
                                 ('؛ والفئة مؤجَّلة فلا يُسأل عن البديل' if fr['protected']['ambiguous'] else ''))
    if not fr['root'] or not fr['pattern']:
        return ST['UNRESOLVED'], 'لا جذر ولا وزن مقبولان للمرشّح'
    if not ev:
        return ST['UNRESOLVED'], f"لا حدث في HFN {fr.get('hfn_base_release')} للجذر والوزن"
    if len({e['verb'] for e in ev}) > 1:
        return ST['UNRESOLVED'], 'أكثر من لمّة مشكولة في HFN الأساس للجذر والوزن: ' + '، '.join(sorted({e['verb'] for e in ev}))
    if fr.get('analysis_selection') != 'SELECTED':
        return ST['UNRESOLVED'], f"وجه التحليل غير مختار ({fr.get('analysis_selection')}): السمة لا تُنقل إلى الكلمة كلها"
    return 'LEMMA_ESTABLISHED', 'وجهٌ مختار ولمّةٌ واحدة في HFN الأساس للجذر والوزن'


def _state(match, route_ok):
    if not route_ok:
        return ST['BLOCKED']
    return ST['MATCH'] if match == 'EXACT' else ST['NON_MATCH']


def feature_rows(fr, lem, W, res, pins):
    """→ صفوف السمات لِلمّةٍ واحدة من جواب العامل: كل صفٍّ بحالته (§٤)، مربوطٌ بالوقوع والوجه واللمّة، ومعه النص الأصلي ونص السؤال ونص الجواب"""
    P, RS = res['provenance'], res['resources']
    rows = []

    XW = res.get('form_crosswalk') or {}

    def base(provider, route, source_key, file_key, row_id, row_verb, match, diff, scope, extra, state=None, route_ok=True, idn=None):
        meta = ROUTES.get((provider, route)) or {}
        pv = {'AMLN': 'amln', 'WAZN': 'wazn', 'HFN': 'hfn'}[provider]
        ist, idd = identity(fr, *idn, XW) if idn is not None else (ST['UNDETERMINED'], dict(reason='NO_IDENTITY_FIELDS'))
        # الأولوية: المسحوب، ثم المسلك المحجوب، ثم تعارض معرّف الحدث، ثم تعارض الهوية، ثم الهوية غير المحسومة، ثم المطابقة حرفاً وحركة
        if state:
            st = state
        elif ist == ST['WITHDRAWN']:
            st = ST['WITHDRAWN']
        elif not route_ok:
            st = ST['BLOCKED']
        elif ist != 'IDENTITY_OK':
            st = ist
        else:
            st = _state(match, route_ok)
        extra = dict(extra, identity_status=ist, identity=idd)
        rows.append(dict(occurrence=dict(verse=fr['verse'], word_index=fr['word_index'], unit=fr['unit'], relation_id=fr['relation_id'], text=fr['text']),
                         face=dict(morph_candidate_id=fr['morph_candidate_id'], analysis_id=fr['analysis_id'], root=fr['root'], pattern=fr['pattern']),
                         vocalized_lemma=lem, query_text=lem, row_text=row_verb, provider=provider, source_key=source_key, route_id=route,
                         route_status=meta.get('status') if route_ok else 'BLOCKED', route_measure=dict(precision=meta.get('precision'),
                                                                                                        wilson_low=meta.get('wilson_low'), source=meta.get('source')),
                         commit=P[pv]['commit'], file=file_key, file_sha256=(RS.get(file_key) or {}).get('sha256'), row_id=row_id,
                         match=match, diff=diff, state=st, rank=RANK[0], is_fact=False, consumer_scope=scope,
                         owner_status='CANDIDATE_PENDING_OWNER' + ('' if match in ('EXACT', None) else f' ({match}: حكمه للمالك)'),
                         **extra))

    def missing(source_key, d):
        rows.append(dict(occurrence=dict(verse=fr['verse'], word_index=fr['word_index'], unit=fr['unit'], relation_id=fr['relation_id'], text=fr['text']),
                         face=dict(morph_candidate_id=fr['morph_candidate_id'], analysis_id=fr['analysis_id'], root=fr['root'], pattern=fr['pattern']),
                         vocalized_lemma=lem, source_key=source_key,
                         state={'QUERY_OK_NO_RESULT': ST['NO_RESULT'], 'RESOURCE_MISSING': ST['MISSING']}.get(d.get('status'), ST['ERROR']),
                         detail=d.get('status') + (': ' + d['detail'] if d.get('detail') else ''), rank=RANK[0]))

    v36 = {e['event_id'] for e in fr['hfn_events']}
    # ---- HFN v47 ----
    d = W['hfn47']
    if d.get('rows'):
        for x in d['rows']:
            st = ST['WITHDRAWN'] if x['withdrawn'] else None
            base('HFN', 'RELEASE_V47_EVENT', 'hfn47', f"HFN:release/{pins['hfn_release']}/events.csv", x['event_id'], x['verb'], x['match'], x['diff'],
                 'hfn_v47_event: الحدث في الإصدار الحديث بجانب قيمة الأساس (لا تحلّ محلّها)',
                 dict(value=dict(event_id=x['event_id'], form=x['form'], transitivity=x['transitivity'], masdar=x['masdar'],
                                 masdar_wasit_v37=x.get('masdar_wasit_v37'), transitivity_wasit_v37=x.get('transitivity_wasit_v37')),
                      event_id_in_base=x['event_id'] in v36, event_review=x['event_review'],
                      exclusion_reason=('حدثٌ مسحوب (event_review_v36 يبدأ بـWITHDRAWN): لا يُقرأ حدثاً حياً' if x['withdrawn'] else None)), state=st,
                 idn=(x['root_K'], x['form'], x['verb'], x.get('event_ref')))
    else:
        missing('hfn47', d)
    # ---- wazn: المطاوعة ----
    for key, side in (('mutawaa', 'base'), ('mutawaa_base', 'mutawaa')):
        d = W[key]
        if not d.get('rows'):
            missing(key, d)
            continue
        for x in d['rows']:
            unresolved = not x['base']
            routes = x['route'].split('+')
            ok = not unresolved and all(('WAZN', r_) in ROUTES for r_ in routes)
            base('WAZN', x['route'], key, 'WAZN:data/' + pins['mutawaa_table'], f"{x['root']}:{x['base']}→{x['mutawaa']}", x['row_verb'], x['match'], x['diff'],
                 'mutawaa: ' + ('اللمّة أصلٌ له مطاوع' if side == 'base' else 'اللمّة مطاوِعٌ لأصل'),
                 dict(value=dict(base=x['base'], base_form=x['base_form'], mutawaa=x['mutawaa'], mutawaa_form=x['mutawaa_form'], athar=x['athar']),
                      lemma_side=side, block_reason=(BLOCKED[('WAZN', 'MUTAWAA:BASE_UNRESOLVED')] if unresolved else
                                                     None if ok else 'UNREGISTERED_ROUTE: ' + x['route'])), route_ok=ok,
                 idn=(x['root'], x['base_form'] if side == 'base' else x['mutawaa_form'], x['row_verb'], x.get('event_ref')))
    # ---- wazn: التعدية بالهمزة ----
    d = W['taadiya_T_JAL']
    if d.get('rows'):
        for x in d['rows']:
            base('WAZN', 'T_JAL', 'taadiya_T_JAL', 'WAZN:engines/taadiya_engine.py', f"{x.get('lazim')}→{x.get('mutaaddi')}", x['row_verb'], x['match'], x['diff'],
                 'taadiya: اللمّة لازمٌ له متعدٍّ مسموع — لا يدخل قرار التعدية', dict(value={k: x.get(k) for k in ('lazim', 'mutaaddi', 'sifa', 'maful', 'form')}),
                 idn=(None, None, x.get('lazim'), x.get('event_ref')))
    else:
        missing('taadiya_T_JAL', d)
    # ---- wazn: تعدّي الوسيط v5 (المجرّد وحده) ----
    d = W['transitivity_wasit_v5']
    if d.get('rows'):
        for x in d['rows']:
            tv, mujarrad = x['transitivity_wasit'], x['form'] in MUJARRAD_FORMS
            ok = mujarrad and tv != 'مشترك'
            why = None if ok else (BLOCKED[('WAZN', 'TRANSITIVITY_WASIT_MAZID')] if not mujarrad else BLOCKED[('WAZN', 'TRANSITIVITY_WASIT:مشترك')])
            st = None if not ok or tv in ('لازم', 'متعدي') else ST['NO_RESULT']
            base('WAZN', 'TRANSITIVITY_WASIT_V5', 'transitivity_wasit_v5', 'WAZN:data/transitivity_wasit_v5.tsv', x['event_id'], x['verb'], x['match'], x['diff'],
                 'transitivity_shadow: تعدّي المجرّد من الوسيط v5 — يُقارن بالحكم القائم ولا يدخل قرار التعدّي في algebra.py',
                 dict(value=tv, harf=x['harf'] or None, basis_v5=x['basis_v5'], transitivity_v1=x['transitivity_v1'], harf_v1=x['harf_v1'] or None,
                      changed_from_v1=(tv != x['transitivity_v1'] or (x['harf'] or '') != (x['harf_v1'] or '')), hfn_transitivity=x['hfn_transitivity'],
                      upstream_event_id=x['event_id'], event_id_in_base=x['event_id'] in v36, block_reason=why,
                      no_value_reason=(None if st is None else f'قيمة الوسيط «{tv}» ليست لازماً ولا متعدياً')), state=st, route_ok=ok,
                 idn=(x['root'], x['form'], x['verb'], x.get('event_ref')))
    else:
        missing('transitivity_wasit_v5', d)
    # ---- wazn: الصفات v2 (معلومة مرشّحة) ----
    d = W['sifat_v2']
    if d.get('rows'):
        for x in d['rows']:
            base('WAZN', 'SIFAT_V2', 'sifat_v2', 'WAZN:data/sifat_v2.tsv', f"{x['event_id']}:{x['word']}", x['verb'], x['match'], x['diff'],
                 'sifat (معلومة مرشّحة): لا يُستنتج منها نوع اشتقاقٍ ولا وزنٌ مختار',
                 dict(value=dict(word=x['word'], template=x['template'], kind=x['kind'], transitivity_wasit=x['transitivity_wasit']),
                      upstream_event_id=x['event_id'], event_id_in_base=x['event_id'] in v36), idn=(x['root'], x['form'], x['verb'], x.get('event_ref')))
    else:
        missing('sifat_v2', d)
    # ---- AMLN: الحدث وأثره، وجهة الفاعل ----
    for key in ('ahdath', 'jiha'):
        d = W[key]
        if not d.get('rows'):
            missing(key, d)
            continue
        for x in d['rows']:
            ok = ('AMLN', x['route']) in ROUTES
            extra = (dict(value=dict(fail=x.get('fail'), maful=x.get('maful'), mutawi=x.get('mutawi'), athar=x.get('athar'), sifa=x.get('sifa'),
                                     label=x.get('label_ar')))
                     if key == 'ahdath' else
                     dict(value=dict(jiha=x.get('jiha'), sifa=x.get('sifa')),
                          musabbib_verb=dict(value=x.get('musabbib_verb') or None, route=x.get('musabbib_route') or None,
                                             note='علاقةٌ معجمية مرشّحة، لا إثبات مسبِّبٍ محذوف في الجملة')))
            base('AMLN', x['route'], key, ROUTES.get(('AMLN', x['route']), {}).get('file') and 'AMLN:' + ROUTES[('AMLN', x['route'])]['file'],
                 x.get('event_id'), x['row_verb'], x['match'], x['diff'],
                 'event_effect: الحدث وأثره — ليس حكم تعدٍّ نحوي' if key == 'ahdath' else
                 'subject_semantic_side: جهة الفاعل الدلالية — لا تغيّر دوره النحوي',
                 dict(extra, upstream_event_id=x.get('event_id'), event_id_in_base=x.get('event_id') in v36,
                      upstream_vowel_judgement=dict(match=x.get('upstream_match'), keep=x.get('upstream_keep'),
                                                    note='حكم الواجهة المتسامح محفوظ للفحص؛ والحالة هنا من إعادة الفحص حرفاً وحركة'),
                      block_reason=None if ok else BLOCKED.get(('AMLN', x['route']), 'UNREGISTERED_ROUTE')), route_ok=ok,
                 idn=(x.get('root') or None, None, x['row_verb'], x.get('event_ref')))
    return rows


def root_rows(fr, rm):
    """معنى الجذر: سجلّ sarf كما هو، ومفتاح السؤال وقاعدته؛ والبنك v11 وmaqayis عبر جدول الربط؛ وhost_refs إحالةٌ منفصلة"""
    if rm is None:
        return None
    return dict(sarf_root=fr['root'], query_key=rm['query_key'], key_rule=rm['key_rule'],
                bank_v11=rm['root_meaning'], maqayis_fallback=rm['maqayis'],
                host_refs=dict(value=(rm['root_meaning'] or {}).get('host_refs'),
                               note='شاهد إحالة (مداخل جذرٍ آخر تعالج الكلمة)، لا مادّة الجذر نفسه'),
                note='معنى الجذر ليس المعنى السياقي المختار للكلمة؛ والنصوص OCR غير محقّق', rank=RANK[0])


def evidence_records(fr, feats, rr, prov, pins=None):
    """سمات المنبع في نظام الأدلّة (للتقرير وشهادة الإغلاق): تُعرض ولا تستوفي التزاماً ولا تغلق وجهاً. المعرّف بصمة المحتوى (EVIDENCE_ID_ALGO)"""
    out = []
    occ = f"{fr['unit']}|{fr['relation_id']}"
    rel = lambda x: (pins or {}).get('hfn_release') if x['provider'] == 'HFN' else x.get('file')
    for x in feats:
        if x['state'] != ST['MATCH']:
            continue
        c = dict(occurrence_id=occ, morph_candidate_id=fr['morph_candidate_id'], analysis_id=fr['analysis_id'], source_key=x['source_key'],
                 provider=x['provider'], route_id=x['route_id'], source_commit=x.get('commit'), release_id=rel(x), source_file_sha256=x.get('file_sha256'),
                 source_row_id=x.get('row_id'), payload=dict(value=x.get('value'), lemma=x['vocalized_lemma'], row_text=x.get('row_text'), match=x['match']))
        c['evidence_id'] = evidence_id(c)
        x['evidence_id'] = c['evidence_id']
        out.append(dict(c, id=c['evidence_id'], unit=fr['unit'], feature=x['source_key'], route=x['route_id'], commit=(x.get('commit') or '')[:7],
                        rank='مرشّح من مصدرٍ خارجي', rank_code='EXTERNAL_CANDIDATE', value=x.get('value'), face=x['face'], lemma=x['vocalized_lemma'],
                        match=x['match'], route_status=x['route_status'], wilson_low=x['route_measure']['wilson_low'],
                        discharges_obligation=False, closes_face=False, conditions_met=False))
    mq = ((rr or {}).get('maqayis_fallback') or {})
    if mq.get('status') == 'OK':
        c = dict(occurrence_id=occ, morph_candidate_id=fr['morph_candidate_id'], analysis_id=fr['analysis_id'], source_key='root_meaning', provider='MAQAYIS',
                 route_id='MAQAYIS_CROSSWALK', source_commit=prov.get('maq', {}).get('commit'), release_id='output/maqayis_all_roots.json',
                 source_file_sha256=(pins or {}).get('files', {}).get('MAQ:output/maqayis_all_roots.json'), source_row_id='|'.join(sorted(str(r_['entry_id']) for r_ in mq['records'])),
                 payload=dict(query_key=rr['query_key'], records=[dict(entry_id=r_['entry_id'], display=r_.get('display'), axes=r_.get('semantic_axes'))
                                                                for r_ in mq['records']]))
        c['evidence_id'] = evidence_id(c)
        out.append(dict(c, id=c['evidence_id'], unit=fr['unit'], feature='root_meaning', route='MAQAYIS_CROSSWALK', commit=(c['source_commit'] or '')[:7],
                        rank='شاهد OCR غير محقّق', rank_code='OCR_UNVERIFIED_WITNESS', value=c['payload'],
                        note='معنى الجذر ليس المعنى المختار في السياق', discharges_obligation=False, closes_face=False, conditions_met=False))
    return out


def load_evidence(path):
    """→ {الوحدة: [سجلات أدلّة UPSTREAM]} من مخرج هذه الأداة"""
    out = collections.defaultdict(list)
    for l in gzip.open(path, 'rt', encoding='utf-8'):
        r = json.loads(l)
        if r.get('unit'):
            out[r['unit']] += r.get('evidence') or []
    return dict(out)


def run(FR, pins):
    """من الأطر إلى الصفوف: البوابة قبل الاستدعاء (لا لمّة ولا جذر من وقوعٍ محمي يصل إلى العامل)، ثم استدعاءٌ واحد للعامل"""
    import client
    lemmas = sorted({e['verb'] for fr in FR if lemma_status(fr)[0] != ST['PROTECTED'] for e in fr['hfn_events']})
    roots = sorted({fr['root'] for fr in FR if fr['root'] and lemma_status(fr)[0] != ST['PROTECTED']})
    rq = [dict(root=r_, query_key=query_key(r_)[0], key_rule=query_key(r_)[1]) for r_ in roots]
    res = client.call([dict(lemma=l) for l in lemmas], rq, pins=pins, origin='upstream_candidates.run')
    out = []
    for fr in FR:
        st, why = lemma_status(fr)
        rows = []
        if st != ST['PROTECTED']:
            for lem in sorted({e['verb'] for e in fr['hfn_events']}):
                for x in feature_rows(fr, lem, res['lemma'][lem], res, pins):
                    if st != 'LEMMA_ESTABLISHED' and x['state'] in (ST['MATCH'], ST['NON_MATCH']):
                        x = dict(x, state=ST['UNRESOLVED'], unresolved_reason=why)
                    rows.append(x)
        rr = root_rows(fr, res['root'].get(fr['root'])) if fr['root'] and st != ST['PROTECTED'] else None
        feats = [x for x in rows if x['state'] == ST['MATCH']]
        out.append(dict(fr, lemma_status=st, lemma_reason=why, query_status=('NOT_QUERIED: ' + why) if st == ST['PROTECTED'] else 'QUERIED',
                        evidence=evidence_records(fr, feats, rr, res['provenance'], pins),
                        upstream_candidates=dict(rows=rows, root_meaning=rr)))
    return out, res, lemmas, rq


def main():
    import client
    out_path, sum_path = sys.argv[1], sys.argv[2]
    from sarf import quran_source
    pins = client.load_pins()
    client.paths(pins)                                   # يفشل قبل أي تحليل إن غاب التثبيت أو اختلف
    V = quran_source.rows()
    if '--verses' in sys.argv:
        want = set(sys.argv[sys.argv.index('--verses') + 1].split(','))
        V = [x for x in V if f'{x[0]}:{x[1]}' in want]
    groups = [list(g) for _, g in itertools.groupby(V, key=lambda x: x[0])]
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 2
    with mp.get_context('fork').Pool(jobs) as P:
        FR = [x for g in P.map(frames, groups, chunksize=1) for x in g]
    OUT, res, lemmas, rq = run(FR, pins)
    S = collections.Counter()
    with gzip.open(out_path, 'wt', encoding='utf-8') as f:
        for r in OUT:
            S['occurrences'] += 1
            S['lemma_status:' + r['lemma_status']] += 1
            for x in r['upstream_candidates']['rows']:
                S[f"rows:{x['source_key']}:{x['state']}"] += 1
                if x.get('match'):
                    S[f"match:{x['source_key']}:{x['match']}"] += 1
            rr = r['upstream_candidates']['root_meaning']
            if rr:
                S['root:key_rule:' + rr['key_rule'].split(':')[0]] += 1
                S['root:bank_v11:' + (rr['bank_v11'] or {}).get('status', '?')] += 1
                S['root:maqayis:' + (rr['maqayis_fallback'] or {}).get('status', '?')] += 1
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    summary = dict(counts=dict(sorted(S.items())), resources=res['resources'], interfaces=res['interfaces'], provenance=res['provenance'],
                   api_sources=res.get('api_sources'), import_origins=res['import_origins'], isolation=res['isolation'],
                   hfn47_counts=res.get('hfn47_counts'), hfn47_form_support=res.get('hfn47_form_support'),
                   maqayis_unmapped_entries=res.get('maqayis_unmapped_entries'), pins=pins,
                   routes={f'{a}:{b}': v for (a, b), v in ROUTES.items()}, blocked={f'{a}:{b}': v for (a, b), v in BLOCKED.items()},
                   owner_rulings=OWNER_RULINGS, n_lemmas=len(lemmas), n_roots=len(rq), worker_calls=client.CALLS)
    json.dump(summary, open(sum_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(dict(occurrences=S['occurrences'], lemmas=len(lemmas), roots=len(rq),
                          writes=res['isolation'].get('resource_writes')), ensure_ascii=False))


if __name__ == '__main__':
    main()
