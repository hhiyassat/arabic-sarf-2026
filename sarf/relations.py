# -*- coding: utf-8 -*-
"""
sarf.relations — عقد النواة الاسمية والتعلّق، الإصدار المقترح ١ (3 نوفمبر 2026): سجلات علاقاتٍ قابلة للتحقق
فوق طبقة الآية، لا تغيّر شيئاً مما قبلها (تُقرأ منها: analyze، والوحدات الجبرية، والسمات).

القواعد (كلٌّ بمعرّفه وإصداره، وسجلّ مقدّماته وموانعه المفحوصة وبدائله):
  P01 v1  بناء الجار والمجرور: حرف جرٍّ مقبول الحكم ومعموله ← PP وحافة GOVERN. لا يثبت متعلَّقه.
  P02 v1  الظرف: ظرفٌ من جرد المشروع (sarf.algebra.ZURUF_V) يليه مضافٌ إليه (ضميرٌ متصل أو اسمٌ مجرور) ← ADVP
  V01 v1  وصلة الناسخ: كان وأخواتها (مج 10) وإنّ وأخواتها (مج 2) المقبولة: اسمها معمولها المربوط، وخبرها
          بشرطه (المنصوب كتابةً لكان، والمرفوع كتابةً لإنّ، أو شبه جملةٍ مقدَّمة قبل الاسم النكرة)
  R01 v1  إطار الصلة المحدود: موصولٌ مختصّ (الذي وأخواته) تليه شبه جملة ثم اسمٌ مرفوع ← حاويةٌ وفيها نواة N02؛
          والعائد علاقةٌ مستقلة بالمطابقة
  N01 v1  إسنادٌ اسمي بخبرٍ مفرد: مسندٌ إليه معرفةٌ مرفوع (أو مبنيٌّ في محلّ رفع) في أول الكلام، ومسندٌ اسمٌ نكرةٌ مرفوع
  N02 v1  إسنادٌ بشبه جملة: معرفةٌ مرفوعة ثم شبه جملة في آخر الإطار، أو شبه جملة ثم نكرةٌ مرفوعة في آخره
  A01 v1  توليد مرشّحات التعلّق: كل مضيفٍ ممكن في الإطار (فعل، أو وصف، أو مصدر)، ويُفحص إطار تعلّقه؛
          ولا جرد لأطر التعلّق في المشروع بعد، فالبحث SEARCH_INCOMPLETE ولا يُرخَّص تعلّق

الحالات: LICENSED (علاقة محلية جائزة بمقدّماتٍ مثبتة)، REJECTED (مانعٌ مثبت)، DEFERRED (نقص دليل)، CONFLICT (تعارضٌ مثبت).
وحقولٌ مستقلة: selected_analysis، nucleus_complete، clause_complete، boundary_proven، sentence_closed:
قبول العلاقة لا يرفعها إلى اختيارٍ نهائي ولا إلى إغلاق الجملة. والحماية الدستورية لا تعطّل الموقع النحوي.
"""
from .chars import letters, FATHA, DAMMA, KASRA, SUKUN, FATHATAN, DAMMATAN, KASRATAN

VERSION = 'v1'
LICENSED, REJECTED, DEFERRED, CONFLICT = 'LICENSED', 'REJECTED', 'DEFERRED', 'CONFLICT'
SEARCH_INCOMPLETE, SEARCH_COMPLETE = 'SEARCH_INCOMPLETE', 'SEARCH_COMPLETE'
NASIKH_KANA, NASIKH_INNA, JARR = '10', '2', '1'
REL_SPECIFIC = ('الَّذِي', 'الَّتِي', 'الَّذِينَ', 'اللَّذَانِ', 'اللَّتَانِ', 'اللَّذَيْنِ', 'اللَّتَيْنِ', 'اللَّاتِي', 'اللَّائِي', 'اللَّٰتِي')
REL_AGR = {'الَّذِي': (3, 'singular', 'masc'), 'الَّتِي': (3, 'singular', 'fem'), 'الَّذِينَ': (3, 'plural', 'masc')}


def _fv(F, k, key):
    r = (F.get(k) or {}).get(key) or {}
    return r.get('v'), r.get('st')


class _Tok:
    """وحدةٌ تحليلية بهويتها وما يلزم القواعد منها، من الطبقات القائمة (لا يُحسب هنا شيءٌ جديد عنها)"""
    def __init__(self, a, G, k, F, seg, ref):
        from .algebra import word_case
        self.k, self.G, self.wi, self.ui = k, G, k[0], k[1]
        self.uid = G.id
        self.loc = f'{ref}:{k[0] + 1}'
        self.text = G.O.get('text') or ''
        u = seg['units'][k[1]]
        self.slots = [seg['slots'][i] for i in u.get('slots', [])]
        self.types = [s['type'] for s in self.slots]
        self.lex = G.Theta.get('lex')
        self.pos, self.pos_st = _fv(F, k, 'pos')
        self.defin, self.defin_st = _fv(F, k, 'definiteness')
        self.dkind, _ = _fv(F, k, 'definiteness_kind')
        self.enclitic = bool(self.slots) and all(s['type'] == 'مبني' and s.get('role') == 'enclitic' for s in self.slots)
        # العاطف أو الرابط في أول الكلمة (وَ، فَ) وحده أو مدموجاً بأداةٍ بعده في وحدةٍ واحدة (وَلْ، فَلْ)
        self.conj = k[1] == 0 and len(seg['units']) > 1 and (self.text in ('وَ', 'فَ') or
                                                             self.text[:2] in ('وَ', 'فَ') and self.lex == 'مبني+عامل')
        stem_last = k[1] == max(i for i, x in enumerate(seg['units']) if any(seg['slots'][j]['type'] in ('جذع', 'لفظ الجلالة')
                                                                             for j in x.get('slots', []))) \
            if any(s['type'] in ('جذع', 'لفظ الجلالة') for s in seg['slots']) else False
        self.case = word_case(a, k[0]) if stem_last and any(t in ('جذع', 'لفظ الجلالة') for t in self.types) else None
        self.divine = 'لفظ الجلالة' in self.types
        tl = letters(self.text)
        self.tanwin = bool(tl) and bool(tl[-1][1] & {FATHATAN, DAMMATAN, KASRATAN})
        self.feats = F.get(k) or {}

        prot = G.Theta.get('protected') or {}
        self.golden = prot.get('cls') == 'اسم ذهبي'
        self.mcat = _mabni_cat(self.text, prot.get('identity')) if self.lex == 'مبني' or prot.get('cls') == 'مبني' else None

    def nounish(self):
        return self.pos == 'اسم' and self.pos_st == 'مثبت' or self.divine or self.golden

    def definite(self):
        """→ (معرفة؟، الدليل) من السمات القائمة؛ وNone إن لم يثبت"""
        if self.divine:
            return True, 'لفظ الجلالة (علم)'
        if self.golden:
            return True, 'اسمٌ ذهبي في الجرد المعتمد (علم)'
        if self.mcat in ('separate_pronoun', 'demonstrative'):
            return True, f'ملف المبنيات: {self.mcat}'
        if self.dkind:
            return True, f'نوع المعرفة: {self.dkind}'
        if self.defin == 'معرفة' and self.defin_st == 'مثبت':
            return True, 'التعريف مثبت'
        if self.defin == 'نكرة' and self.defin_st == 'مثبت':
            return False, 'التنكير مثبت (التنوين)'
        return None, 'التعريف والتنكير غير مثبتين'

    def nominative(self):
        """→ (مرفوعٌ أو في محلّ رفع؟، الدليل)"""
        if self.case == 'رفع':
            return True, 'الرفع مكتوب (الضمة)'
        if self.case in ('نصب', 'جر', 'نصب أو جر', 'جر أو نصب'):
            return False, f'العلامة المكتوبة {self.case}'
        if self.lex == 'مبني' or self.mcat or self.dkind in ('معرفة: ضمير', 'معرفة: اسم إشارة', 'معرفة: اسم موصول'):
            return None, 'مبنيٌّ: المحلّ يُعيَّن بموقعه'
        return None, 'لا علامة إعرابٍ مكتوبةٌ تدلّ'


_LEX = []


def _mabni_cat(text, identity=None):
    """فئة المبني من ملف المبنيات بصورته المكتوبة، أو بهويته المحمية؛ إن اتّفقت مداخله"""
    if not _LEX:
        from .lexicon import MabniLexicon
        _LEX.append(MabniLexicon())
    for t in (text, identity):
        cats = {e.get('category') for e in (_LEX[0].lookup(t) or [])} if t else set()
        if len(cats) == 1:
            return next(iter(cats))
    # المندمج رسماً في الجرد المعتمد (sarf.protected.MERGED): «ذَٰلِكَ، ذَٰلِكُمْ» = ذَا + لِ + كاف الخطاب: إشارة
    from .protected import MERGED
    parts = MERGED.get(identity or text)
    if parts and len(parts) == 3 and parts[0] == 'ذَا' and parts[1] == 'لِ':
        return 'demonstrative'
    return None


def _pron_feats(text):
    """(الشخص، العدد، الجنس) للضمير المتصل من ملف المبنيات المعتمد، إن اتّفقت مداخله؛ وإلا (None، None، None)"""
    if not _LEX:
        from .lexicon import MabniLexicon
        _LEX.append(MabniLexicon())
    ents = [e for e in (_LEX[0].lookup(text) or []) if e.get('category') == 'attached_pronoun']
    vals = {(e.get('extra') or {}).get('person') and ((e.get('extra') or {}).get('person'), (e.get('extra') or {}).get('number'),
                                                     (e.get('extra') or {}).get('gender')) for e in ents}
    vals.discard(None)
    return next(iter(vals)) if len(vals) == 1 else (None, None, None)


def _rec(ref, typ, rule, heads, members, status, reason, premises=(), checked=(), alternatives=(), container=None, **kw):
    rid = f'{ref}:{typ}:{rule}:' + '+'.join(f'{r}={u.uid}' for r, u in sorted(heads.items()))
    out = dict(relation_id=rid, source_id=ref, type=typ, rule_id=rule, rule_version=VERSION,
               analysis_id='+'.join(f'{u.uid}@{VERSION}' for _, u in sorted(heads.items())),
               container_id=container, heads={r: u.uid for r, u in heads.items()},
               members={r: [u.uid for u in us] for r, us in members.items()},
               positions={r: [u.loc for u in us] for r, us in members.items()},
               texts={r: ' '.join(u.text for u in us) for r, us in members.items()},
               premises=list(premises), checked=list(checked), alternatives=list(alternatives),
               status=status, reason=reason, selected_analysis=None, nucleus_complete=None, clause_complete=None,
               boundary_proven=False, sentence_closed=False)
    out.update(kw)
    return out


def verse_relations(a, units, F, ref):
    """→ dict(records=[…], tokens=[(uid، الموضع، النص)]) لآيةٍ واحدة"""
    from .algebra import ZURUF_V, is_form
    toks = [_Tok(a, units[k], k, F, a['segments'][k[0]], ref) for k in sorted(units)]
    idx = {t.k: i for i, t in enumerate(toks)}
    by_k = {t.k: t for t in toks}
    R = []
    st = {(f['word_index'], f['operator'], f['group']): f.get('status') for f in a['operators']}
    governed = {}
    for o in a['operators']:
        r = o.get('relation') or {}
        t = r.get('target') or {}
        if o.get('status') == 'accepted' and t:
            seg = a['segments'][t['word_index']]
            ui = next((i for i, u in enumerate(seg['units']) if t['slot'] in u.get('slots', [])), None)
            sl = o.get('slot') or {}
            if ui is not None and (o['word_index'], sl.get('unit')) in by_k and (t['word_index'], ui) in by_k:
                governed[(t['word_index'], ui)] = (by_k[(o['word_index'], sl.get('unit'))], o, r)

    def nxt(i):
        return toks[i + 1] if i + 1 < len(toks) else None

    def word_start(t):
        return t.ui == 0 or all(x.conj for x in toks[idx[(t.wi, 0)]:idx[t.k]])

    def frame_end(i):
        """أول وحدةٍ بعد i تبدأ إطاراً جديداً: كلمةٌ أولها عاطف، أو ما له الصدارة؛ أو آخر الآية (حدّ مصدر لا حدّ تركيب)"""
        from .algebra import clause_start
        for j in range(i + 1, len(toks)):
            t = toks[j]
            if t.ui == 0 and (t.conj or clause_start(a, t.wi)):
                return j
        return len(toks)

    # P01 الجار والمجرور
    obliques = {}
    for k, (op_t, o, r) in governed.items():
        if str(o['group']) != JARR or k not in by_k:
            continue
        comp = [by_k[k]] if by_k[k] is not op_t else []   # الجار والمجرور في وحدةٍ واحدة (لِلشَّهَٰدَةِ): الوحدة نفسها
        i = idx[k]
        if not comp:
            rec = _rec(ref, 'PP', 'P01', {'preposition': op_t}, {'preposition': [op_t]}, LICENSED,
                       'حرف جرٍّ مقبول ومعموله في وحدةٍ واحدة', premises=[f'حكم العامل «{o["operator"]}» (مج 1): مقبول',
                                                                          f'العلامة في المعمول: {r.get("observed")}'],
                       merged_unit=True, attachment='غير مثبت: انظر A01')
            R.append(rec)
            obliques[op_t.k] = (rec, [op_t])
            continue
        ext = []
        if nxt(i) is not None and nxt(i).wi == comp[0].wi and nxt(i).enclitic and comp[0].nounish():
            comp.append(nxt(i))                      # المضاف إلى ضميرٍ متصل في كلمته (رِجَالِكُمْ)
        elif nxt(i) is not None and nxt(i).wi == comp[0].wi + 1 and (nxt(i).feats.get('idafa') or {}).get('v') == 'مضاف إليه' and \
                (comp[0].feats.get('idafa') or {}).get('v') == 'مضاف':
            ext = [nxt(i)]                           # مضافٌ إليه مرشّح (بِكُلِّ شَيْءٍ): جزءٌ من المكمّل، وحالته مرشّحة
        members = {'preposition': [op_t], 'complement': comp}
        if ext:
            members['complement_ext'] = ext
        rec = _rec(ref, 'PP', 'P01', {'preposition': op_t, 'complement': comp[0]},
                   members, LICENSED, 'حرف جرٍّ مقبول ومعموله' + ('، ومضافٌ إليه مرشّح يمدّ المكمّل' if ext else ''),
                   premises=[f'حكم العامل «{o["operator"]}» (مج 1): مقبول — ' + str((o.get('judgement') or {}).get('proof') or '')[:120],
                             f'العلامة في المعمول: {r.get("observed")}'],
                   checked=['R6 المرفوع بعد الجار (في حكم العامل)'],
                   edges=[('GOVERN', op_t.uid, comp[0].uid)], attachment='غير مثبت: انظر A01')
        R.append(rec)
        obliques[op_t.k] = (rec, [op_t] + comp + ext)
    # P02 الظرف
    for i, t in enumerate(toks):
        if 'جذع' not in t.types or not is_form(t.text, ZURUF_V, i3rab=True):
            continue
        n = nxt(i)
        comp = None
        if n is not None and n.wi == t.wi and n.enclitic:
            comp, why = [n], f'ضميرٌ متصل «{n.text}» مضافٌ إليه'
        elif n is not None and n.wi == t.wi + 1 and word_start(n) and not n.conj and (n.divine or n.nounish()) and \
                n.case in ('جر', 'جر أو نصب'):
            comp, why = [n], f'«{n.text}» مجرورٌ كتابةً بعده بلا جار'
        if comp:
            rec = _rec(ref, 'ADVP', 'P02', {'adverb': t, 'complement': comp[0]}, {'adverb': [t], 'complement': comp}, LICENSED,
                       'ظرفٌ من جرد المشروع ومضافٌ إليه', premises=['جرد الظروف sarf.algebra.ZURUF_V', why],
                       checked=['ليس حرف جر: الظرف اسمٌ منصوب على الظرفية والمضاف إليه بعده'],
                       edges=[('GOVERN', t.uid, comp[0].uid)], attachment='غير مثبت: انظر A01', phrase_kind='OBL/ADVP')
        else:
            rec = _rec(ref, 'ADVP', 'P02', {'adverb': t}, {'adverb': [t]}, DEFERRED, 'ظرفٌ بلا مضافٍ إليه مثبت بعده',
                       premises=['جرد الظروف sarf.algebra.ZURUF_V'], phrase_kind='OBL/ADVP')
        R.append(rec)
        obliques[t.k] = (rec, [t] + (comp or []))
    span_of = {}                                    # وحدة ← شبه الجملة التي تضمّها
    for hk, (rec, us) in obliques.items():
        for u in us:
            span_of[u.k] = hk

    def oblique_at(i):
        """→ (السجل، وحداته، فهرس ما بعدها) إن بدأت شبه جملةٍ مرخَّصة عند i"""
        if i < len(toks) and toks[i].k in obliques:
            rec, us = obliques[toks[i].k]
            if rec['status'] == LICENSED:
                return rec, us, idx[us[-1].k] + 1
        return None

    bound = {}                                      # وحدة ← السجل الذي جعلها طرفاً في ناسخ أو صلة (تمنع N01)
    used_as_pred = set()                            # شبه جملةٍ صارت خبراً في وجهٍ مرخَّص: لا تُرسل إلى A01 في هذا الوجه
    containers = {}
    # R01 إطار الصلة المحدود، وفيه نواة N02
    for i, t in enumerate(toks):
        if t.lex != 'مبني' or not is_form(t.text, REL_SPECIFIC):
            continue
        ob = oblique_at(i + 1)
        if not ob:
            continue
        prec, pus, j = ob
        s = toks[j] if j < len(toks) else None
        if s is None or not s.nounish() or s.k in governed or s.nominative()[0] is not True:
            continue
        rel_gov = governed.get(t.k)
        verbs_ = {(g['word_index'], g['slot']) for g in a.get('agreement', [])}
        verb_before = next((toks[x] for x in range(i - 1, -1, -1)
                            if toks[x].pos == 'فعل' or 'فعل' in ((toks[x].feats.get('pos') or {}).get('alt') or []) or
                            any((toks[x].wi, sl['index']) in verbs_ for sl in toks[x].slots)), None)   # الفعل المحتمل منافسٌ كافٍ للتأجيل
        if s.definite()[0] is not False and rel_gov and str(rel_gov[1]['group']) == JARR and verb_before is not None:
            R.append(_rec(ref, 'CONTAINER_RELATIVE', 'R01', {'relative': t}, {'relative': [t], 'content': pus + [s]}, DEFERRED,
                          f'الموصول مجرور، وقبله الفعل «{verb_before.text}»: المعرفة المرفوعة «{s.text}» قد تكون فاعله لا مسنداً في الصلة',
                          premises=[prec['relation_id']], alternatives=[f'«{s.text}» فاعل «{verb_before.text}»، والصلة شبه الجملة وحدها']))
            continue
        members = [t] + pus + [s]
        stop = toks[j + 1] if j + 1 < len(toks) else None
        stop_why = 'آخر الآية (حدّ مصدر)' if stop is None else \
            f'«{stop.text}» {"منصوب" if stop.case == "نصب" else "لا يتّصل بالصلة بقاعدةٍ في هذا الإصدار"}'
        crec = _rec(ref, 'CONTAINER_RELATIVE', 'R01', {'relative': t}, {'relative': [t], 'content': pus + [s]}, LICENSED,
                    'الموصول المختصّ تليه شبه جملة ثم مرفوع: صلةٌ اسمية (خبرها شبه الجملة المقدَّمة)',
                    premises=[f'«{t.text}» موصولٌ مختصّ (ملف المبنيات)', prec['relation_id'], f'«{s.text}» مرفوعٌ كتابةً'],
                    checked=[f'حدّ الصلة بعد «{s.text}»: {stop_why}'], container=None,
                    extent=[u.uid for u in members])
        R.append(crec)
        cid = crec['relation_id']
        containers[cid] = members
        used_as_pred.add(prec['relation_id'])
        nrec = _rec(ref, 'PREDICATIVE_PP', 'N02', {'subject': s, 'predicate_pp': pus[0]},
                    {'subject': [s], 'predicate_pp': pus}, LICENSED,
                    'في إطار الصلة: شبه الجملة المقدَّمة خبر، والمرفوع بعدها مسندٌ إليه',
                    premises=[crec['relation_id'], prec['relation_id'], f'«{s.text}»: {s.nominative()[1]}'],
                    checked=['الصلة لا تكون مفرداً: فالمرفوع بعد شبه الجملة ليس معطوفاً عليها ولا مضافاً إليها'],
                    container=cid, nucleus_complete=True,
                    display_convention='شبه الجملة خبرٌ في هذا الوجه (أو متعلّقٌ بخبرٍ محذوف)؛ ولا يُكتب المحذوف')
        R.append(nrec)
        for u in members:
            bound[u.k] = crec['relation_id']
        comp = pus[-1]
        if comp.enclitic and comp.text in ('هِ', 'هُ', 'هَا', 'هُمْ', 'هِمْ', 'هُمَا', 'هِمَا', 'هُنَّ', 'هِنَّ'):
            want = REL_AGR.get(t.text)
            got = _pron_feats(comp.text)
            if want and all(got) and got == want:
                st_, why = LICENSED, f'الضمير «{comp.text}» للغائب {got[1]} {got[2]} يطابق «{t.text}»'
            else:
                st_, why = DEFERRED, (f'ملف المبنيات لا يسجّل شخص «{comp.text}» وعدده وجنسه: المطابقة غير مثبتة'
                                      if not any(got) else f'المطابقة غير مثبتة (الموصول {want}، الضمير {got})')
            R.append(_rec(ref, 'RESUMPTIVE', 'R01', {'pronoun': comp, 'relative': t}, {'pronoun': [comp], 'relative': [t]}, st_, why,
                          premises=[crec['relation_id'], 'سمات الضمير من ملف المبنيات'], container=cid))
    # V01 وصلة الناسخ
    for k, (op_t, o, r) in governed.items():
        g = str(o['group'])
        if g not in (NASIKH_KANA, NASIKH_INNA) or k not in by_k:
            continue
        ism = by_k[k]
        i_n, i_s = idx[op_t.k], idx[k]
        if ism is op_t or ism.wi == op_t.wi and g == NASIKH_KANA:
            R.append(_rec(ref, 'NASIKH', 'V01', {'nasikh': op_t}, {'nasikh': [op_t]}, DEFERRED,
                          'الاسم المربوط هو الناسخ نفسه أو ضميرٌ في كلمته (كَانُوا): الاسم ضمير الصيغة، والخبر غير مربوطٍ بهذه القاعدة',
                          premises=[f'حكم الناسخ «{o["operator"]}» (مج {g})']))
            continue
        if g == NASIKH_KANA and ism.case == 'نصب':
            R.append(_rec(ref, 'NASIKH', 'V01', {'nasikh': op_t}, {'nasikh': [op_t], 'khabar_candidate': [ism]}, DEFERRED,
                          f'المربوط «{ism.text}» منصوبٌ كتابةً فلا يكون اسم «{o["operator"]}»: الاسم ضميرٌ مستتر، والمنصوب خبرٌ مرشّح',
                          premises=[f'حكم الناسخ «{o["operator"]}» (مج {g})', f'«{ism.text}»: النصب مكتوب'],
                          alternatives=[f'«{ism.text}» خبر «{o["operator"]}» واسمها ضمير الصيغة']))
            continue
        prem = [f'حكم الناسخ «{o["operator"]}» (مج {g}): مقبول، واسمه «{ism.text}» ({r.get("observed")})']
        khabar, kwhy, kst = None, 'لا خبر مثبتٌ بشرط هذا الإصدار', DEFERRED
        between = [toks[j] for j in range(i_n + 1, i_s) if not toks[j].enclitic or toks[j].wi != op_t.wi]
        ob = oblique_at(i_n + 1) if between else None
        if ob and ob[2] == i_s and ism.definite()[0] is False:
            khabar, kwhy, kst = ob[1], 'شبه جملةٍ مقدَّمة بين الناسخ واسمه النكرة: خبرٌ مقدَّم', LICENSED
            prem.append(ob[0]['relation_id'])
            used_as_pred.add(ob[0]['relation_id'])
        else:
            j = i_s + 1
            cont = next((cid for cid, us in containers.items() if us[0].k == ism.k), None)
            if cont:
                j = idx[containers[cont][-1].k] + 1   # الاسم موصولٌ وصلته حاويةٌ مستقلة الدليل (R01): الخبر بعدها
                prem.append(cont)
            while j < len(toks) and toks[j].enclitic:
                j += 1
            c = toks[j] if j < len(toks) else None
            want = 'نصب' if g == NASIKH_KANA else 'رفع'
            if c is not None and c.nounish() and c.case == want and c.k not in governed:
                khabar, kwhy, kst = [c], f'«{c.text}» اسمٌ {"منصوب" if want == "نصب" else "مرفوع"} كتابةً بعد الاسم' + \
                    (' وصلته' if cont else ''), LICENSED
            elif c is not None and c.nounish() and c.case in ('نصب', 'رفع', 'جر') and c.case != want:
                kwhy = f'«{c.text}» {c.case} كتابةً، والناسخ يقتضي {want}: لا يُرخَّص خبراً'
        heads = {'nasikh': op_t, 'ism': ism}
        members = {'nasikh': [op_t], 'ism': [ism]}
        if khabar:
            heads['khabar'] = khabar[0]
            members['khabar'] = khabar
        rec = _rec(ref, 'NASIKH', 'V01', heads, members, kst, kwhy, premises=prem,
                   checked=['N01 غير المنسوخة لا تُطبَّق على اسم الناسخ وخبره'], nucleus_complete=kst == LICENSED)
        R.append(rec)
        for us in members.values():
            for u in us:
                if u is not op_t:
                    bound[u.k] = rec['relation_id']
    # N01 وN02 خارج الحاويات
    for i, s in enumerate(toks):
        if s.conj or s.enclitic or not word_start(s) or s.k in bound or s.k in span_of:
            continue
        if not (s.nounish() or s.mcat in ('separate_pronoun', 'demonstrative') or
                s.lex == 'مبني' and s.dkind in ('معرفة: ضمير', 'معرفة: اسم إشارة')):
            continue
        prev_conj = s.ui > 0
        pw = toks[idx[(s.wi, 0)] - 1] if idx[(s.wi, 0)] > 0 else None
        mabni_start = (s.mcat in ('separate_pronoun', 'demonstrative') or s.lex == 'مبني') and \
            not (pw is not None and pw.pos == 'فعل') and \
            not (pw is not None and pw.pos != 'فعل' and 'جذع' in pw.types and not pw.tanwin and 'أل' not in pw.types and not pw.enclitic)
        # الضمير بعد الفعل تأكيدٌ لفاعله أو فاعلٌ (يُمِلَّ هُوَ)، والإشارة بعد اسمٍ بلا أل ولا تنوين مضافٌ إليه (دَابِرَ هَٰٓؤُلَآءِ)
        if not (s.wi == 0 or prev_conj or mabni_start):
            continue                                  # أول الكلام: أول الآية، أو بعد عاطف في كلمته، أو ضميرٌ وإشارة
        if s.k in governed:
            continue
        nom, nom_why = s.nominative()
        dfn, dfn_why = s.definite()
        fe = frame_end(i)
        j = i + 1
        while j < fe and toks[j].enclitic and toks[j].wi == s.wi:
            j += 1
        mid = []
        while oblique_at(j) and j < fe:
            o_ = oblique_at(j)
            mid.append(o_)
            j = o_[2]
        p = toks[j] if j < fe else None
        after_op = p is not None and (p.lex or '').startswith('عامل') and not p.nounish()
        if after_op:
            p = None                                  # عاملٌ بعده (مِمَّنْ، إِذَا، لَا): ليس مسنداً مفرداً
        base_prem = [f'«{s.text}» أول الكلام ({"بعد عاطف" if prev_conj else "أول الآية" if s.wi == 0 else "ضميرٌ أو إشارة"})',
                     f'«{s.text}»: {nom_why}', f'«{s.text}»: {dfn_why}']
        if nom is False:
            continue
        if p is None and mid and len(mid) == 1:
            # N02: معرفةٌ مرفوعة ثم شبه جملة في آخر الإطار
            deriv = (s.feats.get('derivation') or {}).get('v') in ('اسم فاعل', 'اسم مفعول', 'مصدر') or \
                'derivation_candidates' in s.feats
            by_sadara = fe < len(toks) and not toks[fe].conj
            if after_op:
                st_, why = DEFERRED, 'بعد شبه الجملة عاملٌ في الإطار نفسه (لَا، مِمَّنْ…): قد تتعلّق به والخبر ما بعده'
            elif by_sadara:
                st_, why = DEFERRED, f'الإطار انقطع بما له الصدارة «{toks[fe].text}» لا بعاطفٍ ولا بآخر الآية: قد يكون المسند بعده'
            elif deriv:
                st_, why = DEFERRED, f'«{s.text}» وصفٌ أو مصدرٌ يعمل: قد تتعلّق شبه الجملة به لا أن تكون خبراً'
            elif not dfn:
                st_, why = DEFERRED, 'أهلية الابتداء غير مثبتة'
            else:
                st_, why = LICENSED, 'معرفةٌ في أول الكلام ثم شبه جملةٍ تختم الإطار'
            R.append(_rec(ref, 'PREDICATIVE_PP', 'N02', {'subject': s, 'predicate_pp': mid[0][1][0]},
                          {'subject': [s], 'predicate_pp': mid[0][1]}, st_, why,
                          alternatives=['معطوفٌ على ما قبل العاطف، وشبه الجملة متعلّقةٌ به أو نعت'] if prev_conj else [],
                          premises=base_prem + [mid[0][0]['relation_id'], 'لا مضيف بعد شبه الجملة داخل الإطار'],
                          nucleus_complete=st_ == LICENSED,
                          display_convention='شبه الجملة خبر (أو متعلّقٌ بخبرٍ محذوف)؛ ولا يُكتب المحذوف'))
            used_as_pred.add(mid[0][0]['relation_id'])
            continue
        if p is None:
            if not mid:
                R.append(_rec(ref, 'PREDICATION', 'N01', {'subject': s}, {'subject': [s]}, DEFERRED,
                              'مسندٌ إليه محتمل بلا مسندٍ في إطاره: لا يُختلق خبر', premises=base_prem, nucleus_complete=False,
                              alternatives=['معطوفٌ على ما قبل العاطف'] if prev_conj else []))
            continue
        heads = {'subject': s, 'predicate': p}
        members = {'subject': [s], 'predicate': [p]}
        prem = base_prem + [m[0]['relation_id'] for m in mid]
        alts = ['معطوفٌ على ما قبل العاطف (لا مبتدأ)'] if prev_conj else []
        if not p.nounish():
            st_, why = DEFERRED, f'اسمية «{p.text}» غير مثبتة في هذا التحليل' + \
                (' (أَفْعَل: اسم تفضيلٍ مرشّح، أو مضارع المتكلم)' if 'elative' in p.feats else '')
        elif p.case in ('نصب', 'جر') or p.case and p.case not in ('رفع',):
            st_, why = REJECTED, f'«{p.text}» {p.case} كتابةً: لا يُرخَّص خبراً مفرداً مرفوعاً في هذا الوجه (ولا يُحكم على النص كله)'
        elif p.case != 'رفع':
            st_, why = DEFERRED, f'رفع «{p.text}» غير مثبت كتابةً'
        elif p.k in governed:
            st_, why = REJECTED, f'«{p.text}» معمولٌ لعاملٍ مقبول'
        elif dfn is not True:
            st_, why = DEFERRED, 'أهلية الابتداء غير مثبتة: المسند إليه ' + dfn_why + ' (والعلم بلا جردٍ لا يثبت)'
            alts.append('نعتٌ ومنعوت (نكرتان مرفوعتان)')
        elif p.definite()[0] is not False:
            st_, why = DEFERRED, 'الطرفان معرفتان أو تعريف المسند غير منفيّ: خبرٌ معرفة، أو نعت، أو بدل — خارج تغطية N01 v1'
            alts += ['نعت', 'بدل', 'خبرٌ معرفة']
        else:
            nn = toks[j + 1] if j + 1 < fe else None
            if nn is not None and not nn.enclitic and nn.nounish() and nn.case == 'رفع':
                st_, why = DEFERRED, f'بعد «{p.text}» مرفوعٌ آخر «{nn.text}»: خبرٌ جملة أو تعدّد أو نعت — خارج القاعدة البسيطة'
                alts.append('خبرٌ جملة اسمية')
            else:
                st_, why = LICENSED, 'معرفةٌ مرفوعة في أول الكلام ومسندٌ نكرةٌ مرفوعٌ كتابةً'
                prem.append(f'«{p.text}»: الرفع مكتوب، والتنكير مثبت')
        if mid:
            alts.append('شبه الجملة بين الطرفين خبرٌ أول أو متعلّقٌ بالمسند: انظر A01')
        R.append(_rec(ref, 'PREDICATION', 'N01', heads, members, st_, why, premises=prem,
                      checked=['ناسخٌ مثبت عامل فيهما', 'عاملٌ مقبول في المسند إليه', 'علامةٌ مخالفة في المسند'],
                      alternatives=alts, nucleus_complete=st_ == LICENSED,
                      clause_complete=None if mid else None,
                      edges=[('PREDICATION', s.uid, p.uid)] if st_ == LICENSED else []))
        if st_ == LICENSED:
            R[-1]['roles'] = {'subject': 'مبتدأ', 'predicate': 'خبر'}
    # N02: شبه جملة في أول الكلام ثم نكرةٌ مرفوعة تختم الإطار (في الدار رجلٌ)
    for i, t in enumerate(toks):
        if not word_start(t) or t.k in bound or not (t.wi == 0 or t.ui > 0 and toks[i - 1].conj):
            continue
        ob = oblique_at(i)
        if not ob:
            continue
        j = ob[2]
        fe = frame_end(i)
        s = toks[j] if j < fe else None
        if s is None or not s.nounish() or s.k in bound or s.k in governed or j + 1 != fe:
            continue
        nom, nwhy = s.nominative()
        dfn, dwhy = s.definite()
        if nom is not True:
            continue
        st_ = LICENSED if dfn is False else DEFERRED
        R.append(_rec(ref, 'PREDICATIVE_PP', 'N02', {'subject': s, 'predicate_pp': ob[1][0]}, {'subject': [s], 'predicate_pp': ob[1]},
                      st_, 'شبه جملةٍ مقدَّمة ونكرةٌ مرفوعة تختم الإطار' if st_ == LICENSED else
                      'المرفوع بعد شبه الجملة معرفة خارج إطار صلةٍ مثبت: خارج تغطية N02 v1',
                      premises=[ob[0]['relation_id'], f'«{s.text}»: {nwhy}', f'«{s.text}»: {dwhy}'],
                      nucleus_complete=st_ == LICENSED,
                      display_convention='شبه الجملة خبرٌ مقدَّم (أو متعلّقٌ بخبرٍ محذوف)؛ ولا يُكتب المحذوف'))
        used_as_pred.add(ob[0]['relation_id'])
    # A01 توليد مرشّحات التعلّق
    for hk, (orec, ous) in obliques.items():
        if orec['status'] != LICENSED or orec['relation_id'] in used_as_pred:
            continue
        i0 = idx[ous[0].k]
        cont = next((cid for cid, us in containers.items() if any(u.k == ous[0].k for u in us)), None)
        lo, hi = 0, len(toks)
        if cont:
            us = containers[cont]
            lo, hi = idx[us[0].k], idx[us[-1].k] + 1
        else:
            from .algebra import clause_start
            for j in range(i0, -1, -1):
                if toks[j].ui == 0 and (toks[j].conj or clause_start(a, toks[j].wi)) or j == 0:
                    lo = j
                    break
            hi = frame_end(i0)
        hosts = []
        for j in range(lo, hi):
            h = toks[j]
            if h.k in span_of and span_of[h.k] == hk or h.enclitic or h.conj:
                continue
            kind = None
            if h.pos == 'فعل' and h.pos_st == 'مثبت' and 'operator' not in h.feats:
                kind = 'فعل'
            elif h.feats.get('derivation', {}).get('v') in ('اسم فاعل', 'اسم مفعول', 'مصدر') and h.feats['derivation'].get('st') == 'مثبت':
                kind = h.feats['derivation']['v']
            elif 'elative' in h.feats:
                kind = 'أَفْعَل (تفضيلٌ مرشّح)'
            elif 'derivation_candidates' in h.feats or (h.feats.get('pattern') or {}).get('st') == 'مثبت':
                kind = 'وصفٌ محتمل (قالب)'
            if kind:
                hosts.append(dict(host=h.uid, host_text=h.text, host_position=h.loc, host_kind=kind, status=DEFERRED,
                                  reason='إطار تعلّق المضيف بهذا الحرف أو الظرف غير مسجَّل في المشروع (لا جرد أطر)'))
        pv = toks[i0 - 1] if i0 > 0 else None
        if pv is not None and pv.nounish() and pv.definite()[0] is False and span_of.get(pv.k) != hk:
            hosts.append(dict(host=pv.uid, host_text=pv.text, host_position=pv.loc, host_kind='نعتٌ للنكرة قبله (متعلّقٌ بمحذوف)',
                              status=DEFERRED, reason='شبه الجملة بعد نكرة تحتمل الوصف؛ والمحذوف لا يُكتب ولا يُعيَّن لفظه'))
        R.append(_rec(ref, 'ATTACH', 'A01', {'oblique': ous[0]}, {'oblique': ous}, DEFERRED,
                      ('لا مضيف ممكن في الإطار' if not hosts else f'{len(hosts)} مضيفاً ممكناً، ولا إطار تعلّقٍ مثبت لأيٍّ منها') +
                      '؛ والبحث غير مكتمل: لا جرد لأطر التعلّق',
                      premises=[orec['relation_id']], alternatives=hosts, container=cont, search_status=SEARCH_INCOMPLETE,
                      search_scope=dict(frame=[toks[lo].loc, toks[hi - 1].loc] if hi > lo else [], container=cont)))
    return dict(records=R, tokens=[(t.uid, t.loc, t.text) for t in toks])


def check_records(records, tokens):
    """فاحصٌ بنيوي مستقل: → [الخلل]. الرأس من طرفه، والوحدات موجودةٌ ومواضعها توافقها، والمعرّفات فريدة،
    والمقبول له مقدّمات، والمقدّمات المشيرة إلى علاقاتٍ موجودةٌ بلا دوران، وأعضاء الحاوية داخل امتدادها"""
    errs = []
    loc = {u: l for u, l, _ in tokens}
    ids = {}
    for r in records:
        if r['relation_id'] in ids:
            errs.append(f"معرّفٌ مكرَّر: {r['relation_id']}")
        ids[r['relation_id']] = r
    for r in records:
        rid = r['relation_id']
        for role, h in r['heads'].items():
            if h not in r['members'].get(role, []):
                errs.append(f'{rid}: الرأس «{role}» ليس من أعضاء طرفه')
        for role, us in r['members'].items():
            for u, p in zip(us, r['positions'].get(role, [])):
                if u not in loc:
                    errs.append(f'{rid}: وحدةٌ غير موجودة {u}')
                elif loc[u] != p:
                    errs.append(f'{rid}: موضع {u} المسجَّل {p} لا يوافق المصدر {loc[u]}')
        if r['status'] == LICENSED and not r['premises']:
            errs.append(f'{rid}: مرخَّصٌ بلا مقدّمات')
        if r.get('container_id'):
            c = ids.get(r['container_id'])
            if c is None:
                errs.append(f'{rid}: حاويةٌ غير موجودة')
            else:
                ext = set(c.get('extent') or [])
                for us in r['members'].values():
                    for u in us:
                        if u not in ext:
                            errs.append(f'{rid}: العضو {u} خارج امتداد حاويته')
    # الدوران في المقدّمات: كل مقدّمةٍ هي معرّف علاقة يجب أن تنتهي إلى حقائق مصدرية
    graph = {r['relation_id']: [p for p in r['premises'] if p in ids] for r in records}
    state = {}

    def dfs(n, stack):
        if state.get(n) == 1:
            errs.append('برهانٌ دائري: ' + ' ← '.join(stack + [n]))
            return
        if state.get(n) == 2:
            return
        state[n] = 1
        for m in graph.get(n, []):
            dfs(m, stack + [n])
        state[n] = 2
    for n in graph:
        dfs(n, [])
    for r in records:
        if r['status'] == LICENSED and r['premises'] and all(p in ids for p in r['premises']):
            errs.append(f"{r['relation_id']}: مقدّماته كلها علاقاتٌ بلا حقيقةٍ مصدرية مستقلة")
    return errs
