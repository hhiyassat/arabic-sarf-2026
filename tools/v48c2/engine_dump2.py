"""engine_dump2.py — تفريغ المحرّك ومقارنته بالمحتوى (SARF_HFN_V48_VALIDATION_COMPLETION_02 §٦ و§١٢).

  dump <root> <OUT.jsonl.gz> [--jobs N]     لكل سورة: بصمة كل منتَج، وبصمة كل مفتاحٍ فيه (الآية أو الجملة أو العنصر)،
                                             وسجلّ جملٍ مضغوط (المدى والحكم والتزامات كل جملةٍ بحالتها وسند استيفائها)،
                                             وحالة الاستقرار والأخطاء النهائية لكل آية، وإحصاء الأنواع المسلسلة بـ repr.
  cmp <A> <B> <OUT.json>                     الفروق بمواضعها: منتَج/مفتاح، والجمل مقابلةً بالمدى (تساوٍ، تغيّر، انقسام، دمج، إضافة، حذف)،
                                             وسند الالتزامات وإن بقيت الحالة نفسها.

إصلاحاتٌ عن engine_dump.py السابق:
- كانت مرحلةٌ فاشلة تُفرغ نصّ الخطأ «<<unavailable>>» في الطرفين فيتساويان: الآن أي مرحلةٍ لم تُنفَّذ أو منتَجٍ غير منتَج يُسقط التفريغ.
- حارس الهوية (tools/hfn_isolation/guard.py) في كل عاملٍ قبل التحليل وبعده، وهوية HFN المحمَّلة تُكتب مع كل سورة.
- التسلسل بالمحتوى: الكائنات بحقولها (__dict__ و__slots__)، وrepr الذي يحمل عنوان ذاكرة (« at 0x») خطأ؛ وتُحصى أنواع repr الباقية.
- مقارنة بالمفتاح لا بالمجموع وحده، والجمل بالمدى مع رفض المفاتيح المكررة."""
import base64, gzip, hashlib, itertools, json, multiprocessing as mp, os, sys, zlib
from collections import Counter

PRODUCTS = ['source', 'normalization', 'analysis', 'cells', 'syllables', 'protection', 'units', 'features', 'sentences', 'legacy',
            'records_initial', 'features_final', 'reconciliation', 'records', 'revision', 'evidence_audit', 'certificates',
            'paragraphs', 'references']
TARGETS = ['references', 'cells', 'syllables', 'protection', 'reconciliation', 'revision']
_ROOT = []


class DumpError(RuntimeError):
    pass


class Canon:
    def __init__(self):
        self.repr_types = Counter()

    def __call__(self, x):
        if isinstance(x, dict):
            return {(k if isinstance(k, str) else repr(k)): self(v) for k, v in sorted(x.items(), key=lambda kv: repr(kv[0]))}
        if isinstance(x, (list, tuple)):
            return [self(v) for v in x]
        if isinstance(x, (set, frozenset)):
            return sorted((self(v) for v in x), key=lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True))
        if isinstance(x, (str, int, float, bool)) or x is None:
            return x
        d = {}
        if hasattr(x, '__dict__'):
            d.update(vars(x))
        for s in getattr(type(x), '__slots__', ()) or ():
            if hasattr(x, s):
                d[s] = getattr(x, s)
        if d:
            return {'__cls__': type(x).__name__, **{k: self(v) for k, v in sorted(d.items())}}
        r = repr(x)
        if ' at 0x' in r:
            raise DumpError(f'IDENTITY_REPR: {type(x).__name__} يُسلسل بعنوان ذاكرة: {r[:120]}')
        self.repr_types[type(x).__module__ + '.' + type(x).__name__] += 1
        return r


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def js(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def fingerprint(C, canon=None):
    """→ (products, sentences, stability) من سياق محرّكٍ مكتمل؛ وأي مرحلةٍ غير منفّذة أو منتَجٍ غائب خطأٌ مسمّى."""
    canon = canon or Canon()
    bad = {k: v for k, v in C.status.items() if v[0] != 'EXECUTED'}
    if bad:
        raise DumpError(f'STAGE_NOT_EXECUTED: {bad}')
    prods = {}
    for p in PRODUCTS:
        try:
            v = C.get(p)
        except KeyError as e:
            raise DumpError(f'PRODUCT_MISSING: {p}: {e}')
        cv = canon(v)
        full = js(cv)
        keys = cv if isinstance(cv, dict) else {str(i): x for i, x in enumerate(cv)} if isinstance(cv, list) else {}
        prods[p] = dict(sha=sha(full), n=len(full), keys={k: sha(js(x)) for k, x in keys.items()})
    sents = {}
    for sid, c in C.get('certificates').items():
        obs = []
        for o in c.get('obligations') or []:
            obs.append(dict(id=o.get('obligation_id'), name=o.get('name'), status=o.get('status'), required=o.get('required'),
                            owner=o.get('owner'), face=o.get('face_id'), discharge_relation=o.get('discharge_relation_id'),
                            discharge_evidence=o.get('discharge_evidence_id'),
                            satisfied_by=sorted(str(s.get('id')) for s in (o.get('satisfied_by') or [])),
                            sha=sha(js(canon(o)))))
        b = c.get('boundary') or {}
        sents[sid] = dict(span=list(c.get('span') or []), verdict=c.get('verdict'), level=c.get('verdict_level'),
                          by_level=canon(c.get('verdict_by_level')), boundary=dict(proven=b.get('proven'), levels=canon(b.get('levels')),
                                                                                   rule=b.get('rule_id'), evidence=b.get('evidence_id')),
                          obligations=obs, sha=sha(js(canon(c))))
    rv = C.get('revision')
    stab = {vk: dict(state=(cv or {}).get('state'), units=len((cv or {}).get('units') or []),
                     errors_final=len((rv.get('errors_final') or {}).get(vk) or []),
                     recon_errors=len((C.get('reconciliation').get('errors') or {}).get(vk) or []))
            for vk, cv in (rv.get('convergence') or {}).items()}
    return prods, sents, stab


def one(items):
    sys.path.insert(0, _ROOT[0]); os.chdir(_ROOT[0])
    sys.path.insert(0, os.path.join(_ROOT[0], 'tools', 'hfn_isolation'))
    import guard
    ident = guard.assert_identity()
    from sarf.stages import run
    C = run(items, None, TARGETS)
    canon = Canon()
    prods, sents, stab = fingerprint(C, canon)
    out = dict(products=prods, sentences=sents, stability=stab, repr_types=dict(canon.repr_types), hfn=ident)
    if os.environ.get('SARF_AJNAS_SIDECAR') == '1':
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import ajnas_sidecar
        sc = ajnas_sidecar.attach(C)
        s = js(Canon()(sc))
        out['ajnas_sidecar'] = dict(sha=sha(s), z=base64.b64encode(zlib.compress(s.encode(), 6)).decode())
        out['leak_scan'] = ajnas_sidecar.leak_scan(C, PRODUCTS)
        prods2, sents2, stab2 = fingerprint(C, Canon())      # بعد الإرفاق: يجب أن يبقى كل شيءٍ كما هو في السياق نفسه
        out['post_attach_same_context'] = dict(products=all(prods2[p]['sha'] == prods[p]['sha'] for p in PRODUCTS),
                                               sentences=sents2 == sents, stability=stab2 == stab)
    if guard.assert_identity() != ident:
        raise DumpError('HFN_IDENTITY_CHANGED_DURING_RUN')
    return out


def dump(root, path, jobs):
    _ROOT.append(os.path.abspath(root)); sys.path.insert(0, _ROOT[0])
    from sarf import quran_source
    groups = [list(g) for _, g in itertools.groupby(quran_source.rows(), key=lambda x: x[0])]
    only = set(filter(None, os.environ.get('SARF_DUMP_SURAHS', '').split(',')))
    if only:
        groups = [g for g in groups if str(g[0][0]) in only]
    with mp.get_context('spawn').Pool(jobs, initializer=_init, initargs=(_ROOT[0],)) as P, gzip.open(path, 'wt', encoding='utf-8') as f:
        for i, r in enumerate(P.imap(one, groups, chunksize=1)):
            f.write(json.dumps(dict(surah=groups[i][0][0], verses=len(groups[i]), **r), ensure_ascii=False) + '\n')
    print('dumped', len(groups), 'surahs', sum(len(g) for g in groups), 'verses')


def _init(root):
    if not _ROOT:
        _ROOT.append(root)


def load(p):
    return {d['surah']: d for d in (json.loads(l) for l in gzip.open(p, 'rt', encoding='utf-8'))}


def match_sentences(SA, SB):
    """مقابلة الجمل بالمدى (قائمة الوقوعات). المفاتيح المكررة مرفوضة. → dict(same, changed, split, merge, added, removed, duplicate_spans)"""
    def by_span(S):
        m, dup = {}, []
        for sid, s in S.items():
            k = tuple(s['span'])
            if k in m:
                dup.append(dict(span=k, ids=[m[k][0], sid]))
            m[k] = (sid, s)
        return m, dup
    A, da = by_span(SA)
    B, db = by_span(SB)
    out = dict(same=0, changed=[], split=[], merge=[], added=[], removed=[], duplicate_spans=da + db)
    for k in set(A) & set(B):
        a, b = A[k][1], B[k][1]
        if a['sha'] == b['sha']:
            out['same'] += 1
            continue
        d = dict(span=[k[0], k[-1]] if k else [], a=A[k][0], b=B[k][0], fields={})
        for f in ('verdict', 'level', 'by_level', 'boundary'):
            if a[f] != b[f]:
                d['fields'][f] = [a[f], b[f]]
        oa, ob = {o['id']: o for o in a['obligations']}, {o['id']: o for o in b['obligations']}
        d['obligations'] = [dict(id=i, a=oa.get(i), b=ob.get(i), kind='ADDED' if i not in oa else 'REMOVED' if i not in ob else
                                 'STATUS' if oa[i]['status'] != ob[i]['status'] else 'EVIDENCE_ONLY')
                            for i in sorted(set(oa) | set(ob)) if oa.get(i, {}).get('sha') != ob.get(i, {}).get('sha')]
        out['changed'].append(d)
    ra, rb = set(A) - set(B), set(B) - set(A)
    occ_b = {}
    for k in rb:
        for o in k:
            occ_b.setdefault(o, []).append(k)

    def tiles(big, parts):
        flat = [o for p in sorted(parts, key=lambda p: list(big).index(p[0]) if p[0] in big else 10 ** 9) for o in p]
        return flat == list(big)
    used_b = set()
    for k in sorted(ra):
        parts = {p for o in k for p in occ_b.get(o, [])}
        if parts and all(set(p) <= set(k) for p in parts) and tiles(k, parts):
            out['split'].append(dict(a=A[k][0], span=[k[0], k[-1]], into=[B[p][0] for p in parts])); used_b |= parts
        else:
            out['removed'].append(dict(id=A[k][0], span=[k[0], k[-1]] if k else []))
    occ_a = {}
    for k in ra:
        for o in k:
            occ_a.setdefault(o, []).append(k)
    for k in sorted(rb - used_b):
        parts = {p for o in k for p in occ_a.get(o, [])}
        if parts and all(set(p) <= set(k) for p in parts) and tiles(k, parts):
            out['merge'].append(dict(b=B[k][0], span=[k[0], k[-1]], from_=[A[p][0] for p in parts]))
            out['removed'] = [r for r in out['removed'] if r['id'] not in {A[p][0] for p in parts}]
        else:
            out['added'].append(dict(id=B[k][0], span=[k[0], k[-1]] if k else []))
    return out


def cmp(pa, pb, outp):
    A, B = load(pa), load(pb)
    rep = dict(surahs_a=len(A), surahs_b=len(B), missing=sorted(set(A) ^ set(B)), verses_a=sum(d['verses'] for d in A.values()),
               verses_b=sum(d['verses'] for d in B.values()), hfn_a=sorted({json.dumps(d['hfn'], sort_keys=True) for d in A.values()}),
               hfn_b=sorted({json.dumps(d['hfn'], sort_keys=True) for d in B.values()}), by_product={}, key_diffs=[],
               sentences=dict(same=0, changed=[], split=[], merge=[], added=[], removed=[], duplicate_spans=[]),
               stability=dict(a=Counter(), b=Counter(), transitions=[]), repr_types_a=Counter(), repr_types_b=Counter())
    for s in sorted(set(A) & set(B)):
        a, b = A[s], B[s]
        for p in PRODUCTS:
            r = rep['by_product'].setdefault(p, dict(equal_surahs=0, differ_surahs=0, keys_compared=0, keys_differ=0))
            pa_, pb_ = a['products'][p], b['products'][p]
            r['equal_surahs' if pa_['sha'] == pb_['sha'] else 'differ_surahs'] += 1
            ka, kb = pa_['keys'], pb_['keys']
            r['keys_compared'] += len(set(ka) | set(kb))
            for k in sorted(set(ka) | set(kb)):
                if ka.get(k) != kb.get(k):
                    r['keys_differ'] += 1
                    rep['key_diffs'].append(dict(surah=s, product=p, key=k, kind='ADDED' if k not in ka else 'REMOVED' if k not in kb else 'CHANGED'))
            if pa_['sha'] != pb_['sha'] and ka == kb:
                rep['key_diffs'].append(dict(surah=s, product=p, key=None, kind='WHOLE_ONLY'))
        m = match_sentences(a['sentences'], b['sentences'])
        rep['sentences']['same'] += m['same']
        for k in ('changed', 'split', 'merge', 'added', 'removed', 'duplicate_spans'):
            rep['sentences'][k] += [dict(x, surah=s) for x in m[k]]
        for vk in sorted(set(a['stability']) | set(b['stability'])):
            sa, sb = a['stability'].get(vk), b['stability'].get(vk)
            rep['stability']['a'][json.dumps(sa and [sa['state'], sa['errors_final'] > 0, sa['recon_errors'] > 0])] += 1
            rep['stability']['b'][json.dumps(sb and [sb['state'], sb['errors_final'] > 0, sb['recon_errors'] > 0])] += 1
            if sa != sb:
                rep['stability']['transitions'].append(dict(verse=vk, a=sa, b=sb))
        rep['repr_types_a'].update(a['repr_types']); rep['repr_types_b'].update(b['repr_types'])
    rep['sentences_total_a'] = sum(len(d['sentences']) for d in A.values())
    rep['sentences_total_b'] = sum(len(d['sentences']) for d in B.values())
    rep['obligations_total_a'] = sum(len(s['obligations']) for d in A.values() for s in d['sentences'].values())
    extra = sorted({k for d in list(A.values()) + list(B.values()) for k in d if k not in ('surah', 'verses', 'products', 'sentences', 'stability', 'repr_types', 'hfn', 'leak_scan', 'post_attach_same_context')})
    rep['added_fields'] = {k: dict(in_a=sum(k in d for d in A.values()), in_b=sum(k in d for d in B.values())) for k in extra}
    rep['leak_hits'] = [dict(surah=s, hits=d['leak_scan']) for s, d in B.items() if d.get('leak_scan')]
    rep['post_attach_same_context'] = Counter(json.dumps(d.get('post_attach_same_context'), sort_keys=True) for d in B.values() if 'post_attach_same_context' in d)
    rep['identical_all'] = (not rep['missing'] and not rep['key_diffs'] and all(not rep['sentences'][k] for k in ('changed', 'split', 'merge', 'added', 'removed', 'duplicate_spans'))
                            and not rep['stability']['transitions'] and not rep['leak_hits'] and all(r['differ_surahs'] == 0 for r in rep['by_product'].values()))
    for k in ('a', 'b'):
        rep['stability'][k] = dict(rep['stability'][k])
    json.dump(rep, open(outp, 'w'), ensure_ascii=False, indent=1, default=list)
    print(json.dumps(dict(identical_all=rep['identical_all'], verses=[rep['verses_a'], rep['verses_b']], key_diffs=len(rep['key_diffs']),
                          sentences=dict(same=rep['sentences']['same'], **{k: len(rep['sentences'][k]) for k in ('changed', 'split', 'merge', 'added', 'removed', 'duplicate_spans')}),
                          stability_transitions=len(rep['stability']['transitions']), added_fields=rep['added_fields']), ensure_ascii=False))


if __name__ == '__main__':
    if sys.argv[1] == 'dump':
        j = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 1
        dump(sys.argv[2], sys.argv[3], j)
    else:
        cmp(sys.argv[2], sys.argv[3], sys.argv[4])
