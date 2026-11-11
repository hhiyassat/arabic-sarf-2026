"""ajnas_sidecar (v3) — إرفاق روابط ahdath_ajnas مرشّحاتٍ جانبية بعقدٍ صريح (SARF_HFN_V48_TARGETED_REPAIR_AND_CLOSURE_03 §٢–§٤).

العقد (CONTRACT_VERSION):
- يُرفق بالوقوع فقط إذا كان تحليله مختاراً في المحرّك: status=accepted، level=event، analysis_selection_status=SELECTED،
  ومعه analysis_id صادرٌ من المحرّك (sarf.root.analysis_id على مفتاح التحليل). لا هوية مشتقة: إن لم يختر المحرّك التحليل فلا تحليل
  يُعيَّن، ويؤجَّل الإرفاق بسبب مسمّى DEFERRED_ANALYSIS_NOT_SELECTED:<حالة الاختيار> (ومنه DEFERRED_MULTIPLE_LEMMAS؛ والمحرّك نفسه
  يعدّ هوية تحليلٍ مع اختيارٍ غير مثبت خطأً — sarf/face_check.py).
- قيود المطابقة، كلٌّ بمصدره، ولا يوضع أحدها مكان الآخر:
    analysis_id      ENGINE   morph.analysis_id                         مطلوب
    root             ENGINE   morph.root                                 مطلوب، ويساوي root_K للرابط وللحدث في المورد
    form_class       ENGINE   morph.form_class (فئة الصيغة: I، X …)       مطلوب، ويساوي فئة صيغة الحدث في المورد (hfn_class)
    lemma_pattern    ENGINE   morph.pattern.lemma_pattern (الميزان)       مطلوب حين lemma_pattern_status=SELECTED؛ وإلا يؤجَّل
                                                                         الإرفاق DEFERRED_PATTERN_NOT_SELECTED
    realized_pattern ENGINE   morph.pattern.realized_pattern (الوزن المتحقق) يُحفظ إن وُجد، وإلا NOT_APPLICABLE بسببه
    realized_word    ENGINE   نصّ الخانة في المقطع (الشكل المكتوب المتحقق)  مطلوب
    event_id         ENGINE   morph.event.event_id                      مطلوب، ويساوي event_id للرابط
    event_form       RESOURCE events.csv:form للحدث في الإصدار المثبّت     خاصيةٌ من المورد لا نتيجةٌ من المحلّل
- is_fact: القيمة الخام من CSV تُحفظ في is_fact_raw، وتُحوَّل بجدولٍ صريح {'False': false, 'True': true}؛ وغير المعروف يؤجَّل
  (DEFERRED_UNKNOWN_IS_FACT)؛ ورابطٌ مرشّح خامه True يُستبعد (EXCLUDED_CANDIDATE_MARKED_FACT). ولا bool(نص).
- الحدث المسحوب: يحجبه المستهلك ويُسجَّل (tools/ajnas/consumer.py).
- لا يُنشئ الإرفاق علاقةً ولا تعديةً ولا عدد مفاعيل ولا مرجعاً ولا حدّاً ولا معنىً سياقياً، ولا يحسم صنفاً أو جذراً أو حدثاً،
  ولا يستوفي التزاماً ولا يرفع شهادة؛ و«محلّ» ليس فاعلاً نحوياً."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'ajnas'))
import consumer as AC
import importlib.util as _iu
_sp = _iu.spec_from_file_location('ajnas_sidecar_v2', os.path.join(os.path.dirname(HERE), 'v48c2', 'ajnas_sidecar.py'))
_v2 = _iu.module_from_spec(_sp); _sp.loader.exec_module(_v2)
leak_scan = _v2.leak_scan          # فاحص التسرّب نفسه من v48c2، دون تغيير

CONTRACT_VERSION = 'AJNAS_SIDECAR_CONTRACT_v3'
IS_FACT = {'False': False, 'True': True}
REQUIRED_RESIDUALS = ('TWO_BLIND_READERS_AGREED_NOT_OWNER_RULED', 'EVENT_NOT_SENSE_SPECIFIC')
GUARD = ['NOT_A_FACT: rank=CANDIDATE, is_fact=false (boolean)', 'OWNER_RULING: NONE', 'ABSENCE_IS_NOT_NEGATIVE', 'LINK_IS_FOR_THE_BAB_SENSE',
         'ROLE_IS_SEMANTIC_NOT_GRAMMATICAL (محلّ ليس فاعلاً نحوياً)', 'NO_TRANSITIVITY_NO_VALENCE_COUNT',
         'NO_CLASS_ROOT_EVENT_OR_CONTEXTUAL_SENSE_DECISION', 'NO_LICENSED_RELATION', 'NO_REFERENCE_NO_BOUNDARY_NO_PARAGRAPH',
         'NO_OBLIGATION_DISCHARGE_NO_CERTIFICATE_EFFECT', 'STRIPPED_KEY_IS_RETRIEVAL_NOT_EVIDENCE', 'NO_SINGULAR_PLURAL_UNIFICATION',
         'ANALYSIS_ID_FROM_ENGINE_ONLY (no derived identity)']
_CL = {}


def consumer():
    if 'c' not in _CL:
        rel = os.environ['SARF_AJNAS_RELEASE']
        api = os.environ.get('SARF_AJNAS_API') or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(rel))), 'api')
        _CL['c'] = AC.AjnasConsumer(AC.DirectBackend(rel, api), os.environ['SARF_AJNAS_EXPECT_RELEASE'], os.environ['SARF_AJNAS_EXPECT_MANIFEST'])
    return _CL['c']


def hfn_class(form):
    from sarf.root import hfn_class as hc
    return hc(form)


def constraints(m, text, ev_row):
    """→ (القيود، سبب التأجيل أو None). القيود بمصادرها؛ ولا قيمة مختلقة."""
    st = (m.get('statuses') or {})
    sel = st.get('analysis_selection_status')
    if sel != 'SELECTED':
        return None, f'DEFERRED_ANALYSIS_NOT_SELECTED:{sel}'
    if not m.get('analysis_id'):
        return None, 'DEFERRED_SELECTED_WITHOUT_ENGINE_ANALYSIS_ID'
    p = m.get('pattern') or {}
    if p.get('lemma_pattern_status') != 'SELECTED' or not p.get('lemma_pattern'):
        return None, f'DEFERRED_PATTERN_NOT_SELECTED:{p.get("lemma_pattern_status")}'
    if not text:
        return None, 'DEFERRED_NO_REALIZED_WORD'
    ev = (m.get('event') or {}).get('event_id')
    c = dict(analysis_id=dict(value=m['analysis_id'], source='ENGINE', field='morph.analysis_id', derived=False),
             root=dict(value=m.get('root'), source='ENGINE', field='morph.root'),
             form_class=dict(value=m.get('form_class'), source='ENGINE', field='morph.form_class', kind='فئة الصيغة'),
             lemma_pattern=dict(value=p['lemma_pattern'], source='ENGINE', field='morph.pattern.lemma_pattern', kind='الميزان',
                                status=p.get('lemma_pattern_status'), alternatives=p.get('lemma_pattern_alternatives') or []),
             realized_pattern=(dict(value=p['realized_pattern'], source='ENGINE', field='morph.pattern.realized_pattern', kind='الوزن المتحقق',
                                    alternatives=p.get('realized_pattern_alternatives') or [])
                               if p.get('realized_pattern') else dict(value=None, not_applicable='NO_REALIZED_PATTERN_IN_ENGINE_OUTPUT')),
             realized_word=dict(value=text, source='ENGINE', field='analysis.segments[w].slots[s].text', kind='الشكل المكتوب'),
             event_id=dict(value=ev, source='ENGINE', field='morph.event.event_id'),
             event_form=dict(value=(ev_row or {}).get('form'), source='RESOURCE', field='events.csv:form', release=None,
                             note='خاصيةٌ من المورد للحدث الذي عيّنه المحرّك، لا نتيجةٌ مستقلة من المحلّل'),
             occurrence_source=dict(analysis_selection_status=sel, pattern_status=st.get('pattern_status'), root_status=st.get('root_status')))
    return c, None


def link_view(l, cons, why):
    raw = l.get('is_fact')
    return dict(link_id=l['link_id'], event_id=l['event_id'], root_K=l['root_K'], verb=l['verb'], semantic_role=l['role'], dalala=l['dalala'],
                luzum=dict(naw=l['luzum_naw'], martaba=l['luzum_martaba']), dhat=l['dhat'], dhat_K=l['dhat_K'], dhat_readers=l['dhat_readers'],
                bab=dict(book=l['mukhassas_book'], bab=l['mukhassas_bab']),
                source=dict(sid=l['mukhassas_sid'], shahid_line=l['shahid_line'], shahid=l['shahid'], method=l['method'], qawl=l['qawl']),
                residual=l['residual'], rank=l['rank'], is_fact=IS_FACT.get(raw), is_fact_raw=raw, owner_ruling='NONE',
                status='CANDIDATE', event_withdrawn_raw=l.get('event_withdrawn'), match_constraints=cons, why=why)


def attach(C):
    c = consumer()
    events = c.b.h.events
    an = C.get('analysis'); ff = C.get('features_final')
    out, dhat_index, excluded = {}, {}, []
    n_audit0 = len(c.audit_log)
    for vk, a in an.items():
        occ = []
        F = ff.get(vk, {}) if isinstance(ff, dict) else {}
        M = {(m.get('word_index'), m.get('slot')): m for m in a.get('morph') or []}
        nouns = {k for k, v in F.items() if isinstance(k, tuple) and ((v.get('pos') or {}).get('v') == 'اسم')}
        for wi, si in sorted(set(M) | nouns, key=lambda k: (k[0] if k[0] is not None else -1, k[1] if k[1] is not None else -1)):
            m = M.get((wi, si)) or {}
            try:
                text = a['segments'][wi]['slots'][si]['text']
            except (KeyError, IndexError, TypeError):
                text = None
            rec = dict(occurrence=f"{vk}:w{wi}.s{si}", text=text, analysis_id=m.get('analysis_id'), morph_status=m.get('status'),
                       analysis_selection_status=(m.get('statuses') or {}).get('analysis_selection_status'))
            ev = (m.get('event') or {}).get('event_id') if m.get('status') == 'accepted' and m.get('level') == 'event' else None
            if ev:
                cons, why_def = constraints(m, text, events.get(ev))
                if why_def:
                    rec['event_side'] = dict(event_id=ev, decision='DEFERRED', reason=why_def,
                                             why='لا تحليلٌ مختارٌ بهويةٍ من المحرّك أو لا ميزانٌ مختار: لا يُرفق، ولا تُملأ هويةٌ شكلية')
                else:
                    cons['event_form']['release'] = c.b.release
                    r = c.query('event', ev)
                    live, bad = [], []
                    for l in r['links']:
                        v = link_view(l, cons, 'هوية الحدث من التحليل المختار في المحرّك (analysis_id)؛ ومعنى الوقوع السياقي غير محسوم، '
                                               'والرابط لمعنى بابه لا لكل معاني الحدث')
                        if v['is_fact'] is None:
                            bad.append(dict(link_id=l['link_id'], reason='DEFERRED_UNKNOWN_IS_FACT', raw=l.get('is_fact')))
                        elif v['is_fact'] is True:
                            bad.append(dict(link_id=l['link_id'], reason='EXCLUDED_CANDIDATE_MARKED_FACT', raw=l.get('is_fact')))
                        else:
                            live.append(v)
                    excluded += [dict(b, occurrence=rec['occurrence']) for b in bad]
                    rec['event_side'] = dict(event_id=ev, served_by=r['served_by_release'], api_residuals=r['residuals'],
                                             decision='ATTACHED_CANDIDATES' if live else 'NO_AJNAS_LINK (not a negative)',
                                             excluded_withdrawn=[x['link_id'] for x in r['excluded']], excluded_contract=bad, links=live)
            elif m.get('status') in ('deferred', 'ranked', 'class_deferred'):
                rec['event_side'] = dict(decision='DEFERRED', reason='DEFERRED_NO_EVENT_IDENTITY:' + m.get('status'),
                                         why='الجذر أو الوزن أو الصنف مؤجَّل في التحليل: لا هوية حدثٍ واحدة، ولا يُختار أول المرشّحات')
            elif m.get('status') == 'not_applicable':
                rec['event_side'] = dict(decision='NOT_APPLICABLE', reason='NOT_APPLICABLE:' + str(m.get('reason')))
            pos = (F.get((wi, si)) or {}).get('pos') or {}
            if text and pos.get('v') == 'اسم':
                r = c.query('dhat', text)
                k = r['transforms'][-1]['value'] if r.get('transforms') else None
                if k not in dhat_index:
                    dhat_index[k] = dict(dhat_K=k, n_links=len(r['links']), link_ids=[l['link_id'] for l in r['links']],
                                         events=r.get('events'), api_residuals=r['residuals'], excluded_withdrawn=[x['link_id'] for x in r['excluded']])
                rec['dhat_side'] = dict(query=text, transforms=r.get('transforms'), key=k, pos_status=pos.get('st'), n_links=len(r['links']),
                                        status='RETRIEVED_BY_STRIPPED_KEY_NOT_EVIDENCE' if r['links'] else 'NO_AJNAS_LINK (not a negative)')
            if 'event_side' in rec or 'dhat_side' in rec:
                occ.append(rec)
        out[vk] = occ
    return dict(contract=CONTRACT_VERSION, sidecar=out, dhat_index=dhat_index, withdrawn_excluded=c.audit_log[n_audit0:],
                contract_excluded=excluded, guard=GUARD, release=c.b.release, manifest_sha256=c.b.manifest_sha256)
