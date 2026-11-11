"""ajnas_sidecar — إرفاق روابط ahdath_ajnas (HFN v48) مرشّحاتٍ جانبية بوقوعات التحليل (SARF_HFN_V48_VALIDATION_COMPLETION_02 §٩).
يقرأ سياق المحرّك ولا يكتب فيه شيئاً، ويستهلك الروابط عبر tools/ajnas/consumer.py وحده (هويةٌ مثبَّتة، ومسحوبٌ محجوب بسجلّه).

لكل وقوع:
- جانب الحدث: الوقوع الذي قبل التحليلُ له حدثاً واحداً (status=accepted، level=event) تُرفق به روابط ذلك الحدث كلها مرشّحات،
  مع قيود المطابقة (الجذر والوزن والمستوى والحالة من التحليل). والمؤجَّل والمرجَّح ومؤجَّل الصنف لا يُرفق به شيء: لا هوية حدثٍ واحدة،
  ولا يُختار أول المرشّحات (DEFERRED_NO_EVENT_IDENTITY)؛ وغير المنطبق (المحمي دستورياً وغيره) NOT_APPLICABLE.
- جانب الذات: الاسم يُسترجَع له بمفتاح الواجهة (حذف التشكيل و«ال») ما يوافقه؛ وهذا استرجاعٌ لا شهادة مطابقة
  (RETRIEVED_BY_STRIPPED_KEY_NOT_EVIDENCE)، ولا يوحَّد مفردٌ بجمع. ويُحفظ السؤال الأصلي وتحويلاته.
- لا يُنشئ الإرفاق علاقةً ولا تعديةً ولا عدد مفاعيل ولا مرجعاً ولا حدّاً ولا معنىً سياقياً، ولا يحسم صنفاً أو جذراً أو حدثاً،
  ولا يستوفي التزاماً ولا يرفع شهادة؛ و«محلّ» ليس فاعلاً نحوياً.
leak_scan(C): يبحث في منتجات المحرّك كلها عن أثرٍ للروابط (معرّف HFN-AJ- أو ahdath_ajnas)؛ ووجوده تسرّبٌ مسمّى."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'ajnas'))
import consumer as AC

GUARD = ['NOT_A_FACT: rank=CANDIDATE, is_fact=False', 'OWNER_RULING: NONE', 'ABSENCE_IS_NOT_NEGATIVE', 'LINK_IS_FOR_THE_BAB_SENSE',
         'ROLE_IS_SEMANTIC_NOT_GRAMMATICAL (محلّ ليس فاعلاً نحوياً)', 'NO_TRANSITIVITY_NO_VALENCE_COUNT',
         'NO_CLASS_ROOT_EVENT_OR_CONTEXTUAL_SENSE_DECISION', 'NO_LICENSED_RELATION', 'NO_REFERENCE_NO_BOUNDARY_NO_PARAGRAPH',
         'NO_OBLIGATION_DISCHARGE_NO_CERTIFICATE_EFFECT', 'STRIPPED_KEY_IS_RETRIEVAL_NOT_EVIDENCE', 'NO_SINGULAR_PLURAL_UNIFICATION']
_CL = {}


def consumer():
    if 'c' not in _CL:
        rel = os.environ['SARF_AJNAS_RELEASE']
        api = os.environ.get('SARF_AJNAS_API') or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(rel))), 'api')
        _CL['c'] = AC.AjnasConsumer(AC.DirectBackend(rel, api), os.environ['SARF_AJNAS_EXPECT_RELEASE'], os.environ['SARF_AJNAS_EXPECT_MANIFEST'])
    return _CL['c']


def link_view(l, constraints, why):
    return dict(link_id=l['link_id'], event_id=l['event_id'], verb=l['verb'], semantic_role=l['role'], dalala=l['dalala'],
                luzum=dict(naw=l['luzum_naw'], martaba=l['luzum_martaba']), dhat=l['dhat'], dhat_K=l['dhat_K'], dhat_readers=l['dhat_readers'],
                bab=dict(book=l['mukhassas_book'], bab=l['mukhassas_bab']), source=dict(sid=l['mukhassas_sid'], shahid_line=l['shahid_line'],
                                                                                         method=l['method'], qawl=l['qawl']),
                residual=l['residual'], rank=l['rank'], is_fact=l['is_fact'], owner_ruling='NONE (لم يحكم المالك)',
                status='CANDIDATE', match_constraints=constraints, why=why)


def attach(C):
    c = consumer()
    an = C.get('analysis'); ff = C.get('features_final')
    out, dhat_index = {}, {}
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
            rec = dict(occurrence=f"{vk}:w{wi}.s{si}", text=text, analysis_id=m.get('analysis_id'), morph_status=m.get('status'))
            ev = (m.get('event') or {}).get('event_id') if m.get('status') == 'accepted' and m.get('level') == 'event' else None
            if ev:
                cons = dict(event_id=ev, root=m.get('root'), form=m.get('form') or m.get('class'), level=m.get('level'), status=m.get('status'))
                r = c.query('event', ev)
                rec['event_side'] = dict(event_id=ev, served_by=r['served_by_release'], api_residuals=r['residuals'],
                                         decision='ATTACHED_CANDIDATES' if r['links'] else 'NO_AJNAS_LINK (not a negative)',
                                         excluded_withdrawn=[x['link_id'] for x in r['excluded']],
                                         links=[link_view(l, cons, 'هوية الحدث من التحليل المقبول (analysis_id)؛ ومعنى الوقوع السياقي غير محسوم، '
                                                                   'والرابط لمعنى بابه لا لكل معاني الحدث') for l in r['links']])
            elif m.get('status') in ('deferred', 'ranked', 'class_deferred'):
                rec['event_side'] = dict(decision='DEFERRED_NO_EVENT_IDENTITY', why='الجذر أو الوزن أو الصنف مؤجَّل في التحليل: لا هوية حدثٍ واحدة، '
                                                                                 'ولا يُختار أول المرشّحات', reason=m.get('reason'))
            elif m.get('status') == 'not_applicable':
                rec['event_side'] = dict(decision='NOT_APPLICABLE', why=m.get('reason'))
            pos = (F.get((wi, si)) or {}).get('pos') or {}
            if text and pos.get('v') == 'اسم':
                r = c.query('dhat', text)
                k = r['transforms'][-1]['value'] if r.get('transforms') else None
                if k not in dhat_index:
                    dhat_index[k] = dict(dhat_K=k, n_links=len(r['links']), link_ids=[l['link_id'] for l in r['links']],
                                         events=r.get('events'), api_residuals=r['residuals'], excluded_withdrawn=[x['link_id'] for x in r['excluded']])
                rec['dhat_side'] = dict(query=text, transforms=r.get('transforms'), key=k, pos_status=pos.get('st'), n_links=len(r['links']),
                                        status='RETRIEVED_BY_STRIPPED_KEY_NOT_EVIDENCE' if r['links'] else 'NO_AJNAS_LINK (not a negative)',
                                        why='مفتاح الواجهة يحذف «ال» والتشكيل؛ ولفظ الذات في الملف غير مشكول: استرجاعٌ لا مطابقةٌ مقبولة، '
                                            'ولا يوحَّد مفردٌ بجمع')
            if 'event_side' in rec or 'dhat_side' in rec:
                occ.append(rec)
        out[vk] = occ
    return dict(sidecar=out, dhat_index=dhat_index, withdrawn_excluded=c.audit_log[n_audit0:], guard=GUARD,
                release=c.b.release, manifest_sha256=c.b.manifest_sha256)


def leak_scan(C, products):
    """أي ذكرٍ لمعرّف رابط (HFN-AJ-) أو لملف الروابط في منتجات المحرّك = تسرّب. → [(المنتَج، المسار، المقتطف)]"""
    hits = []

    def walk(x, path, p):
        if len(hits) > 50:
            return
        if isinstance(x, str):
            if 'HFN-AJ-' in x or 'ahdath_ajnas' in x:
                hits.append((p, path, x[:160]))
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(k if isinstance(k, str) else repr(k), path + '/key', p); walk(v, f'{path}/{k}', p)
        elif isinstance(x, (list, tuple, set, frozenset)):
            for i, v in enumerate(x):
                walk(v, f'{path}[{i}]', p)
        elif hasattr(x, '__dict__'):
            walk(vars(x), path, p)
    for p in products:
        walk(C.get(p), '', p)
    return hits
